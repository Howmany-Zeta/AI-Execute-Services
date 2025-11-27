"""
Structured Data Pipeline

Import structured data (CSV, JSON) into knowledge graphs using schema mappings.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime

try:
    import pandas as pd  # type: ignore[import-untyped]

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
)


logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """
    Result of structured data import operation

    Attributes:
        success: Whether import completed successfully
        entities_added: Number of entities added to graph
        relations_added: Number of relations added to graph
        rows_processed: Number of rows processed
        rows_failed: Number of rows that failed to process
        errors: List of errors encountered
        warnings: List of warnings
        start_time: When import started
        end_time: When import ended
        duration_seconds: Total duration in seconds
    """

    success: bool = True
    entities_added: int = 0
    relations_added: int = 0
    rows_processed: int = 0
    rows_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0


class StructuredDataPipeline:
    """
    Pipeline for importing structured data (CSV, JSON) into knowledge graphs

    Uses SchemaMapping to map source data columns to entity and relation types.
    Supports batch processing, progress tracking, and error handling.

    Example:
        ```python
        # Define schema mapping
        mapping = SchemaMapping(
            entity_mappings=[
                EntityMapping(
                    source_columns=["id", "name", "age"],
                    entity_type="Person",
                    property_mapping={"id": "id", "name": "name", "age": "age"}
                )
            ],
            relation_mappings=[
                RelationMapping(
                    source_columns=["person_id", "company_id"],
                    relation_type="WORKS_FOR",
                    source_entity_column="person_id",
                    target_entity_column="company_id"
                )
            ]
        )

        # Create pipeline
        pipeline = StructuredDataPipeline(
            mapping=mapping,
            graph_store=store
        )

        # Import CSV
        result = await pipeline.import_from_csv("employees.csv")
        print(f"Added {result.entities_added} entities, {result.relations_added} relations")
        ```
    """

    def __init__(
        self,
        mapping: SchemaMapping,
        graph_store: GraphStore,
        batch_size: int = 100,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        skip_errors: bool = True,
    ):
        """
        Initialize structured data pipeline

        Args:
            mapping: Schema mapping configuration
            graph_store: Graph storage to save entities/relations
            batch_size: Number of rows to process in each batch
            progress_callback: Optional callback for progress updates (message, progress_pct)
            skip_errors: Whether to skip rows with errors and continue processing
        """
        # Validate mapping
        validation_errors = mapping.validate_mapping()
        if validation_errors:
            raise ValueError(f"Invalid schema mapping: {validation_errors}")

        self.mapping = mapping
        self.graph_store = graph_store
        self.batch_size = batch_size
        self.progress_callback = progress_callback
        self.skip_errors = skip_errors

        if not PANDAS_AVAILABLE:
            logger.warning("pandas not available. CSV import will use basic CSV reader. " "Install pandas for better performance: pip install pandas")

    async def import_from_csv(
        self,
        file_path: Union[str, Path],
        encoding: str = "utf-8",
        delimiter: str = ",",
        header: bool = True,
    ) -> ImportResult:
        """
        Import data from CSV file

        Args:
            file_path: Path to CSV file
            encoding: File encoding (default: utf-8)
            delimiter: CSV delimiter (default: comma)
            header: Whether file has header row (default: True)

        Returns:
            ImportResult with statistics
        """
        result = ImportResult(start_time=datetime.now())

        try:
            # Read CSV file
            if PANDAS_AVAILABLE:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=delimiter,
                    header=0 if header else None,
                )
                rows = df.to_dict("records")
            else:
                # Fallback to basic CSV reader
                import csv

                rows = []
                with open(file_path, "r", encoding=encoding) as f:
                    reader = csv.DictReader(f) if header else csv.reader(f)
                    if header:
                        for row in reader:
                            rows.append(row)
                    else:
                        # No header - use column indices
                        for row in reader:
                            rows.append({str(i): val for i, val in enumerate(row)})

            # Process rows
            result = await self._process_rows(rows, result)

        except Exception as e:
            error_msg = f"Failed to import CSV file {file_path}: {e}"
            logger.error(error_msg, exc_info=True)
            result.success = False
            result.errors.append(error_msg)

        finally:
            result.end_time = datetime.now()
            if result.start_time:
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()

        return result

    async def import_from_json(
        self,
        file_path: Union[str, Path],
        encoding: str = "utf-8",
        array_key: Optional[str] = None,
    ) -> ImportResult:
        """
        Import data from JSON file

        Supports:
        - Array of objects: [{"id": 1, "name": "Alice"}, ...]
        - Object with array: {"items": [{"id": 1, ...}, ...]}
        - Single object: {"id": 1, "name": "Alice"}

        Args:
            file_path: Path to JSON file
            encoding: File encoding (default: utf-8)
            array_key: If JSON is object with array, key containing the array

        Returns:
            ImportResult with statistics
        """
        result = ImportResult(start_time=datetime.now())

        try:
            # Read JSON file
            with open(file_path, "r", encoding=encoding) as f:
                data = json.load(f)

            # Extract rows
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                if array_key:
                    rows = data.get(array_key, [])
                    if not isinstance(rows, list):
                        raise ValueError(f"Key '{array_key}' does not contain an array")
                else:
                    # Single object - wrap in list
                    rows = [data]
            else:
                raise ValueError(f"JSON file must contain array or object, got {type(data)}")

            # Process rows
            result = await self._process_rows(rows, result)

        except Exception as e:
            error_msg = f"Failed to import JSON file {file_path}: {e}"
            logger.error(error_msg, exc_info=True)
            result.success = False
            result.errors.append(error_msg)

        finally:
            result.end_time = datetime.now()
            if result.start_time:
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()

        return result

    async def _process_rows(self, rows: List[Dict[str, Any]], result: ImportResult) -> ImportResult:
        """
        Process rows and convert to entities/relations

        Args:
            rows: List of row dictionaries
            result: ImportResult to update

        Returns:
            Updated ImportResult
        """
        total_rows = len(rows)

        if total_rows == 0:
            result.warnings.append("No rows to process")
            return result

        # Process in batches
        for batch_start in range(0, total_rows, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_rows)
            batch_rows = rows[batch_start:batch_end]

            # Update progress
            if self.progress_callback:
                progress_pct = (batch_end / total_rows) * 100
                self.progress_callback(
                    f"Processing rows {batch_start+1}-{batch_end} of {total_rows}",
                    progress_pct,
                )

            # Process batch
            batch_result = await self._process_batch(batch_rows)

            # Update result
            result.entities_added += batch_result.entities_added
            result.relations_added += batch_result.relations_added
            result.rows_processed += batch_result.rows_processed
            result.rows_failed += batch_result.rows_failed
            result.errors.extend(batch_result.errors)
            result.warnings.extend(batch_result.warnings)

        return result

    async def _process_batch(self, rows: List[Dict[str, Any]]) -> ImportResult:
        """
        Process a batch of rows

        Args:
            rows: List of row dictionaries

        Returns:
            ImportResult for this batch
        """
        batch_result = ImportResult()
        batch_result.rows_processed = len(rows)

        # Collect entities and relations
        entities_to_add: List[Entity] = []
        relations_to_add: List[Relation] = []

        for i, row in enumerate(rows):
            try:
                # Convert row to entities
                row_entities = await self._row_to_entities(row)
                entities_to_add.extend(row_entities)

                # Convert row to relations
                row_relations = await self._row_to_relations(row)
                relations_to_add.extend(row_relations)

            except Exception as e:
                error_msg = f"Failed to process row {i+1}: {e}"
                logger.warning(error_msg, exc_info=True)
                batch_result.rows_failed += 1

                if self.skip_errors:
                    batch_result.warnings.append(error_msg)
                else:
                    batch_result.errors.append(error_msg)
                    raise

        # Add entities to graph store
        for entity in entities_to_add:
            try:
                await self.graph_store.add_entity(entity)
                batch_result.entities_added += 1
            except Exception as e:
                error_msg = f"Failed to add entity {entity.id}: {e}"
                logger.warning(error_msg)
                batch_result.warnings.append(error_msg)
                if not self.skip_errors:
                    raise

        # Add relations to graph store
        for relation in relations_to_add:
            try:
                await self.graph_store.add_relation(relation)
                batch_result.relations_added += 1
            except Exception as e:
                error_msg = f"Failed to add relation {relation.id}: {e}"
                logger.warning(error_msg)
                batch_result.warnings.append(error_msg)
                if not self.skip_errors:
                    raise

        return batch_result

    async def _row_to_entities(self, row: Dict[str, Any]) -> List[Entity]:
        """
        Convert a row to entities based on entity mappings

        Args:
            row: Dictionary of column name -> value

        Returns:
            List of Entity objects
        """
        entities = []

        for entity_mapping in self.mapping.entity_mappings:
            try:
                # Map row to entity using mapping
                entity_data = entity_mapping.map_row_to_entity(row)

                # Create Entity object
                # Merge metadata into properties since Entity doesn't have a metadata field
                properties = entity_data["properties"].copy()
                properties["_metadata"] = {
                    "source": "structured_data_import",
                    "imported_at": datetime.now().isoformat(),
                }
                entity = Entity(
                    id=entity_data["id"],
                    entity_type=entity_data["type"],
                    properties=properties,
                )

                entities.append(entity)

            except Exception as e:
                error_msg = f"Failed to map row to entity type '{entity_mapping.entity_type}': {e}"
                logger.warning(error_msg)
                if not self.skip_errors:
                    raise ValueError(error_msg)

        return entities

    async def _row_to_relations(self, row: Dict[str, Any]) -> List[Relation]:
        """
        Convert a row to relations based on relation mappings

        Args:
            row: Dictionary of column name -> value

        Returns:
            List of Relation objects
        """
        relations = []

        for relation_mapping in self.mapping.relation_mappings:
            try:
                # Map row to relation using mapping
                relation_data = relation_mapping.map_row_to_relation(row)

                # Create Relation object
                # Merge metadata into properties since Relation doesn't have a metadata field
                rel_properties = relation_data["properties"].copy()
                rel_properties["_metadata"] = {
                    "source": "structured_data_import",
                    "imported_at": datetime.now().isoformat(),
                }
                relation = Relation(
                    id=f"{relation_data['source_id']}_{relation_data['type']}_{relation_data['target_id']}",
                    relation_type=relation_data["type"],
                    source_id=relation_data["source_id"],
                    target_id=relation_data["target_id"],
                    properties=rel_properties,
                )

                relations.append(relation)

            except Exception as e:
                error_msg = f"Failed to map row to relation type '{relation_mapping.relation_type}': {e}"
                logger.warning(error_msg)
                if not self.skip_errors:
                    raise ValueError(error_msg)

        return relations
