"""
Structured Data Pipeline

Import structured data (CSV, JSON, SPSS, Excel) into knowledge graphs using schema mappings.
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
from aiecs.application.knowledge_graph.builder.data_quality import (
    DataQualityValidator,
    ValidationConfig,
    QualityReport,
    RangeRule,
)
from aiecs.application.knowledge_graph.builder.import_optimizer import (
    PerformanceMetrics,
    BatchSizeOptimizer,
    ParallelBatchProcessor,
    MemoryTracker,
    StreamingCSVReader,
)

# Import InferredSchema for type hints (avoid circular import)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from aiecs.application.knowledge_graph.builder.schema_inference import InferredSchema


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
        quality_report: Data quality validation report (if validation enabled)
        start_time: When import started
        end_time: When import ended
        duration_seconds: Total duration in seconds
        performance_metrics: Detailed performance metrics (if tracking enabled)
    """

    success: bool = True
    entities_added: int = 0
    relations_added: int = 0
    rows_processed: int = 0
    rows_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    quality_report: Optional[QualityReport] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    performance_metrics: Optional[PerformanceMetrics] = None


class AggregationAccumulator:
    """
    Accumulator for incremental statistical aggregation

    Computes statistics incrementally as data is processed in batches.
    """

    def __init__(self):
        self.count = 0
        self.sum = 0.0
        self.sum_sq = 0.0  # Sum of squares for variance/std
        self.min_val = float('inf')
        self.max_val = float('-inf')
        self.values = []  # For median (if needed)

    def add(self, value: Any):
        """Add a value to the accumulator"""
        if value is None:
            return

        try:
            num_val = float(value)
        except (ValueError, TypeError):
            return

        self.count += 1
        self.sum += num_val
        self.sum_sq += num_val * num_val
        self.min_val = min(self.min_val, num_val)
        self.max_val = max(self.max_val, num_val)
        self.values.append(num_val)

    def get_mean(self) -> Optional[float]:
        """Get mean value"""
        if self.count == 0:
            return None
        return self.sum / self.count

    def get_std(self) -> Optional[float]:
        """Get standard deviation (sample std with Bessel's correction)"""
        if self.count < 2:
            return None
        mean = self.get_mean()
        if mean is None:
            return None
        # Use sample variance formula: sum((x - mean)^2) / (n - 1)
        # Which equals: (sum(x^2) - n*mean^2) / (n - 1)
        variance = (self.sum_sq - self.count * mean * mean) / (self.count - 1)
        return variance ** 0.5 if variance >= 0 else 0.0

    def get_variance(self) -> Optional[float]:
        """Get variance (sample variance with Bessel's correction)"""
        if self.count < 2:
            return None
        mean = self.get_mean()
        if mean is None:
            return None
        # Use sample variance formula: (sum(x^2) - n*mean^2) / (n - 1)
        return (self.sum_sq - self.count * mean * mean) / (self.count - 1)

    def get_min(self) -> Optional[float]:
        """Get minimum value"""
        if self.count == 0:
            return None
        return self.min_val

    def get_max(self) -> Optional[float]:
        """Get maximum value"""
        if self.count == 0:
            return None
        return self.max_val

    def get_sum(self) -> Optional[float]:
        """Get sum"""
        if self.count == 0:
            return None
        return self.sum

    def get_count(self) -> int:
        """Get count"""
        return self.count

    def get_median(self) -> Optional[float]:
        """Get median value"""
        if self.count == 0:
            return None
        sorted_vals = sorted(self.values)
        mid = self.count // 2
        if self.count % 2 == 0:
            return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
        return sorted_vals[mid]


class StructuredDataPipeline:
    """
    Pipeline for importing structured data (CSV, JSON, SPSS, Excel) into knowledge graphs

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
        enable_parallel: bool = False,
        max_workers: Optional[int] = None,
        auto_tune_batch_size: bool = False,
        enable_streaming: bool = False,
        use_bulk_writes: bool = True,
        track_performance: bool = True,
    ):
        """
        Initialize structured data pipeline

        Args:
            mapping: Schema mapping configuration
            graph_store: Graph storage to save entities/relations
            batch_size: Number of rows to process in each batch (ignored if auto_tune_batch_size=True)
            progress_callback: Optional callback for progress updates (message, progress_pct)
            skip_errors: Whether to skip rows with errors and continue processing
            enable_parallel: Enable parallel batch processing for faster imports
            max_workers: Maximum number of parallel workers (default: CPU count - 1)
            auto_tune_batch_size: Automatically tune batch size based on system resources
            enable_streaming: Enable streaming mode for large files (memory-efficient)
            use_bulk_writes: Use bulk write operations for better performance
            track_performance: Track detailed performance metrics
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

        # Performance optimization settings
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.auto_tune_batch_size = auto_tune_batch_size
        self.enable_streaming = enable_streaming
        self.use_bulk_writes = use_bulk_writes
        self.track_performance = track_performance

        # Initialize optimizers
        self._batch_optimizer = BatchSizeOptimizer() if auto_tune_batch_size else None
        self._memory_tracker = MemoryTracker() if track_performance else None

        # Initialize aggregation tracking
        self._aggregation_accumulators: Dict[str, Dict[str, Any]] = {}  # entity_type -> {property -> accumulator}

        # Initialize data quality validator if validation config is provided
        self.validator: Optional[DataQualityValidator] = None
        if mapping.validation_config:
            self.validator = self._create_validator_from_config(mapping.validation_config)

        if not PANDAS_AVAILABLE:
            logger.warning("pandas not available. CSV import will use basic CSV reader. " "Install pandas for better performance: pip install pandas")

    @staticmethod
    def infer_schema_from_csv(
        file_path: Union[str, Path],
        encoding: str = "utf-8",
        sample_size: int = 1000,
    ) -> 'InferredSchema':
        """
        Infer schema mapping from CSV file

        Analyzes CSV structure and content to automatically generate schema mappings.

        Args:
            file_path: Path to CSV file
            encoding: File encoding (default: utf-8)
            sample_size: Number of rows to sample for inference (default: 1000)

        Returns:
            InferredSchema with entity and relation mappings

        Example:
            ```python
            # Infer schema from CSV
            inferred = StructuredDataPipeline.infer_schema_from_csv("data.csv")

            # Review and modify if needed
            print(f"Inferred entity types: {[em.entity_type for em in inferred.entity_mappings]}")
            print(f"Warnings: {inferred.warnings}")

            # Use inferred schema
            mapping = inferred.to_schema_mapping()
            pipeline = StructuredDataPipeline(mapping, graph_store)
            ```
        """
        from aiecs.application.knowledge_graph.builder.schema_inference import SchemaInference

        inference = SchemaInference(sample_size=sample_size)
        return inference.infer_from_csv(file_path, encoding=encoding)

    @staticmethod
    def infer_schema_from_spss(
        file_path: Union[str, Path],
        encoding: str = "utf-8",
        sample_size: int = 1000,
    ) -> 'InferredSchema':
        """
        Infer schema mapping from SPSS file

        Uses SPSS variable labels and value labels to generate schema mappings.

        Args:
            file_path: Path to SPSS file
            encoding: File encoding (default: utf-8)
            sample_size: Number of rows to sample for inference (default: 1000)

        Returns:
            InferredSchema with entity and relation mappings
        """
        from aiecs.application.knowledge_graph.builder.schema_inference import SchemaInference

        inference = SchemaInference(sample_size=sample_size)
        return inference.infer_from_spss(file_path, encoding=encoding)

    @staticmethod
    def infer_schema_from_dataframe(
        df: 'pd.DataFrame',
        entity_type_hint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        sample_size: int = 1000,
    ) -> 'InferredSchema':
        """
        Infer schema mapping from pandas DataFrame

        Args:
            df: DataFrame to analyze
            entity_type_hint: Optional hint for entity type name
            metadata: Optional metadata (e.g., SPSS variable labels)
            sample_size: Number of rows to sample for inference (default: 1000)

        Returns:
            InferredSchema with entity and relation mappings
        """
        from aiecs.application.knowledge_graph.builder.schema_inference import SchemaInference

        inference = SchemaInference(sample_size=sample_size)
        return inference.infer_from_dataframe(df, entity_type_hint=entity_type_hint, metadata=metadata)

    @staticmethod
    def create_with_auto_reshape(
        file_path: Union[str, Path],
        graph_store: GraphStore,
        entity_type_hint: Optional[str] = None,
        reshape_threshold: int = 50,
        **kwargs,
    ) -> 'StructuredDataPipeline':
        """
        Create pipeline with automatic reshaping for wide format data

        Detects wide format data and automatically reshapes to normalized structure
        before creating the pipeline.

        Args:
            file_path: Path to data file (CSV, SPSS, Excel)
            graph_store: Graph storage to save entities/relations
            entity_type_hint: Optional hint for entity type name
            reshape_threshold: Minimum columns to trigger reshaping (default: 50)
            **kwargs: Additional arguments for StructuredDataPipeline

        Returns:
            StructuredDataPipeline configured for the data

        Example:
            ```python
            # Automatically detect and reshape wide format data
            pipeline = StructuredDataPipeline.create_with_auto_reshape(
                "wide_data.csv",
                graph_store,
                entity_type_hint="Sample"
            )

            # Import reshaped data
            result = await pipeline.import_from_csv("wide_data.csv")
            ```
        """
        from aiecs.application.knowledge_graph.builder.data_reshaping import DataReshaping
        from aiecs.application.knowledge_graph.builder.schema_inference import SchemaInference

        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for automatic reshaping")

        # Load data to analyze
        file_path_str = str(file_path)
        if file_path_str.endswith('.csv'):
            df = pd.read_csv(file_path, nrows=1000)  # Sample for analysis
        elif file_path_str.endswith(('.sav', '.por')):
            import pyreadstat
            df, _ = pyreadstat.read_sav(file_path_str, row_limit=1000)
        elif file_path_str.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path, nrows=1000)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

        # Check if data is in wide format
        is_wide = DataReshaping.detect_wide_format(df, threshold_columns=reshape_threshold)

        if is_wide:
            logger.info(f"Detected wide format data ({df.shape[1]} columns). Suggesting normalized structure.")

            # Suggest melt configuration
            melt_config = DataReshaping.suggest_melt_config(df)
            logger.info(f"Suggested melt config: id_vars={melt_config['id_vars']}, "
                       f"{len(melt_config['value_vars'])} value columns")

            # For wide format, we'll need to reshape during import
            # For now, infer schema from original data
            inference = SchemaInference()
            inferred = inference.infer_from_dataframe(df, entity_type_hint=entity_type_hint)

            # Add warning about wide format
            inferred.warnings.append(
                f"Wide format detected ({df.shape[1]} columns). "
                f"Consider using reshape_and_import() for normalized structure."
            )

            mapping = inferred.to_schema_mapping()
        else:
            # Normal format - infer schema directly
            inference = SchemaInference()
            inferred = inference.infer_from_dataframe(df, entity_type_hint=entity_type_hint)
            mapping = inferred.to_schema_mapping()

        return StructuredDataPipeline(mapping=mapping, graph_store=graph_store, **kwargs)

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

                # Run data quality validation if validator is configured
                if self.validator:
                    # Determine ID column for validation
                    id_column = None
                    for entity_mapping in self.mapping.entity_mappings:
                        if entity_mapping.id_column:
                            id_column = entity_mapping.id_column
                            break

                    quality_report = self.validator.validate_dataframe(df, id_column=id_column)
                    result.quality_report = quality_report

                    # Log quality issues
                    if quality_report.violations:
                        logger.warning(f"Data quality validation found {len(quality_report.violations)} violations")
                        for violation in quality_report.violations[:5]:  # Log first 5
                            logger.warning(f"  {violation.message}")
                        if len(quality_report.violations) > 5:
                            logger.warning(f"  ... and {len(quality_report.violations) - 5} more violations")

                    # Fail import if configured and validation failed
                    if not quality_report.passed:
                        result.success = False
                        result.errors.append(f"Data quality validation failed: {len(quality_report.violations)} violations")
                        return result

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

    async def import_from_csv_streaming(
        self,
        file_path: Union[str, Path],
        encoding: str = "utf-8",
        delimiter: str = ",",
        chunk_size: int = 10000,
    ) -> ImportResult:
        """
        Import data from CSV file using streaming mode.

        Memory-efficient import for large files (>1GB). Reads file in chunks
        without loading entire file into memory.

        Args:
            file_path: Path to CSV file
            encoding: File encoding (default: utf-8)
            delimiter: CSV delimiter (default: comma)
            chunk_size: Number of rows per chunk (default: 10000)

        Returns:
            ImportResult with statistics and performance metrics
        """
        import time

        result = ImportResult(start_time=datetime.now())

        # Initialize performance metrics
        metrics = PerformanceMetrics() if self.track_performance else None
        if metrics:
            metrics.start_time = time.time()
            if self._memory_tracker:
                self._memory_tracker.start_tracking()
                metrics.initial_memory_mb = self._memory_tracker.initial_memory_mb

        try:
            if not PANDAS_AVAILABLE:
                raise ImportError("pandas is required for streaming CSV import")

            # Count total rows for progress tracking
            streaming_reader = StreamingCSVReader(
                str(file_path),
                chunk_size=chunk_size,
                encoding=encoding,
                delimiter=delimiter,
            )
            total_rows = streaming_reader.count_rows()
            if metrics:
                metrics.total_rows = total_rows

            processed_rows = 0
            batch_count = 0

            # Process file in chunks
            async for chunk_df in streaming_reader.read_chunks():
                read_start = time.time()
                rows = chunk_df.to_dict("records")
                if metrics:
                    metrics.read_time_seconds += time.time() - read_start

                # Update progress
                if self.progress_callback:
                    progress_pct = (processed_rows / total_rows) * 100 if total_rows > 0 else 0
                    self.progress_callback(
                        f"Streaming chunk {batch_count + 1}: {processed_rows}/{total_rows} rows",
                        progress_pct,
                    )

                # Process chunk
                transform_start = time.time()
                for row in rows:
                    try:
                        row_entities = await self._row_to_entities(row)
                        row_relations = await self._row_to_relations(row)

                        # Add entities and relations
                        if self.use_bulk_writes and hasattr(self.graph_store, 'add_entities_bulk'):
                            added = await self.graph_store.add_entities_bulk(row_entities)
                            result.entities_added += added
                        else:
                            for entity in row_entities:
                                try:
                                    await self.graph_store.add_entity(entity)
                                    result.entities_added += 1
                                except ValueError:
                                    pass

                        if self.use_bulk_writes and hasattr(self.graph_store, 'add_relations_bulk'):
                            added = await self.graph_store.add_relations_bulk(row_relations)
                            result.relations_added += added
                        else:
                            for relation in row_relations:
                                try:
                                    await self.graph_store.add_relation(relation)
                                    result.relations_added += 1
                                except ValueError:
                                    pass

                        result.rows_processed += 1
                    except Exception as e:
                        result.rows_failed += 1
                        if not self.skip_errors:
                            raise
                        result.warnings.append(f"Row error: {e}")

                if metrics:
                    metrics.transform_time_seconds += time.time() - transform_start

                processed_rows += len(rows)
                batch_count += 1

                # Update memory tracking
                if self._memory_tracker:
                    self._memory_tracker.update()

            # Finalize metrics
            if metrics:
                metrics.end_time = time.time()
                metrics.batch_count = batch_count
                if self._memory_tracker:
                    metrics.peak_memory_mb = self._memory_tracker.peak_memory_mb
                metrics.calculate_throughput()
                result.performance_metrics = metrics

        except Exception as e:
            error_msg = f"Failed to import CSV file (streaming): {e}"
            logger.error(error_msg, exc_info=True)
            result.success = False
            result.errors.append(error_msg)

        finally:
            result.end_time = datetime.now()
            if result.start_time:
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()

        return result

    async def import_from_spss(
        self,
        file_path: Union[str, Path],
        encoding: str = "utf-8",
        preserve_metadata: bool = True,
    ) -> ImportResult:
        """
        Import data from SPSS file (.sav, .por)

        Uses pyreadstat library to read SPSS files and extract metadata.
        SPSS variable labels and value labels are preserved as entity properties.

        Args:
            file_path: Path to SPSS file (.sav or .por)
            encoding: File encoding (default: utf-8)
            preserve_metadata: Whether to preserve SPSS metadata (variable labels, value labels)

        Returns:
            ImportResult with statistics
        """
        result = ImportResult(start_time=datetime.now())

        try:
            # Import pyreadstat
            try:
                import pyreadstat  # type: ignore[import-untyped]
            except ImportError:
                raise ImportError(
                    "pyreadstat is required for SPSS import. "
                    "Install with: pip install pyreadstat"
                )

            if not PANDAS_AVAILABLE:
                raise ImportError("pandas is required for SPSS import. Install with: pip install pandas")

            # Read SPSS file
            df, meta = pyreadstat.read_sav(str(file_path), encoding=encoding)

            # Convert DataFrame to list of dictionaries
            rows = df.to_dict("records")

            # If preserve_metadata is True, add SPSS metadata to each row
            if preserve_metadata and meta:
                # Extract metadata
                spss_metadata = {
                    "column_names": meta.column_names if hasattr(meta, 'column_names') else [],
                    "column_labels": meta.column_labels if hasattr(meta, 'column_labels') else [],
                    "variable_value_labels": meta.variable_value_labels if hasattr(meta, 'variable_value_labels') else {},
                }

                # Store metadata in result for reference
                if spss_metadata.get('column_labels'):
                    result.warnings.append(f"SPSS metadata preserved: {len(spss_metadata['column_labels'])} variable labels")

                # Add metadata to each row's properties
                for row in rows:
                    row["_spss_metadata"] = spss_metadata

            # Process rows
            result = await self._process_rows(rows, result)

        except Exception as e:
            error_msg = f"Failed to import SPSS file {file_path}: {e}"
            logger.error(error_msg, exc_info=True)
            result.success = False
            result.errors.append(error_msg)

        finally:
            result.end_time = datetime.now()
            if result.start_time:
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()

        return result

    async def import_from_excel(
        self,
        file_path: Union[str, Path],
        sheet_name: Union[str, int, None] = 0,
        encoding: str = "utf-8",
        header: bool = True,
    ) -> ImportResult:
        """
        Import data from Excel file (.xlsx, .xls)

        Supports importing from specific sheets or all sheets.

        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name (str), sheet index (int), or None for all sheets (default: 0 = first sheet)
            encoding: File encoding (default: utf-8)
            header: Whether file has header row (default: True)

        Returns:
            ImportResult with statistics
        """
        result = ImportResult(start_time=datetime.now())

        try:
            if not PANDAS_AVAILABLE:
                raise ImportError("pandas is required for Excel import. Install with: pip install pandas openpyxl")

            # Read Excel file
            if sheet_name is None:
                # Read all sheets
                excel_data = pd.read_excel(
                    file_path,
                    sheet_name=None,  # Returns dict of sheet_name -> DataFrame
                    header=0 if header else None,
                )

                # Process each sheet
                all_rows = []
                for sheet_name_key, df in excel_data.items():
                    sheet_rows = df.to_dict("records")
                    # Add sheet name to each row for reference
                    for row in sheet_rows:
                        row["_excel_sheet"] = sheet_name_key
                    all_rows.extend(sheet_rows)

                rows = all_rows
                result.warnings.append(f"Imported {len(excel_data)} sheets from Excel file")

            else:
                # Read specific sheet
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=0 if header else None,
                )
                rows = df.to_dict("records")

            # Process rows
            result = await self._process_rows(rows, result)

        except Exception as e:
            error_msg = f"Failed to import Excel file {file_path}: {e}"
            logger.error(error_msg, exc_info=True)
            result.success = False
            result.errors.append(error_msg)

        finally:
            result.end_time = datetime.now()
            if result.start_time:
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()

        return result

    async def reshape_and_import_csv(
        self,
        file_path: Union[str, Path],
        id_vars: Optional[List[str]] = None,
        value_vars: Optional[List[str]] = None,
        var_name: str = 'variable',
        value_name: str = 'value',
        entity_type_hint: Optional[str] = None,
        encoding: str = "utf-8",
    ) -> ImportResult:
        """
        Reshape wide format CSV to normalized structure and import

        Automatically converts wide format data (many columns) to long format
        (normalized structure) before importing into the graph.

        Args:
            file_path: Path to CSV file
            id_vars: Columns to use as identifiers (auto-detected if None)
            value_vars: Columns to unpivot (auto-detected if None)
            var_name: Name for variable column (default: 'variable')
            value_name: Name for value column (default: 'value')
            entity_type_hint: Optional hint for entity type name
            encoding: File encoding (default: utf-8)

        Returns:
            ImportResult with statistics

        Example:
            ```python
            # Wide format: sample_id, option1, option2, ..., option200
            # Will be reshaped to: sample_id, variable, value

            result = await pipeline.reshape_and_import_csv(
                "wide_data.csv",
                id_vars=['sample_id'],
                var_name='option_name',
                value_name='option_value'
            )
            ```
        """
        from aiecs.application.knowledge_graph.builder.data_reshaping import DataReshaping

        result = ImportResult(start_time=datetime.now())

        try:
            if not PANDAS_AVAILABLE:
                raise ImportError("pandas is required for reshaping")

            # Read CSV
            df = pd.read_csv(file_path, encoding=encoding)

            # Auto-detect melt configuration if not provided
            if id_vars is None:
                melt_config = DataReshaping.suggest_melt_config(df)
                id_vars = melt_config['id_vars']
                if value_vars is None:
                    value_vars = melt_config['value_vars']
                result.warnings.append(f"Auto-detected id_vars: {id_vars}")

            # Reshape data
            reshape_result = DataReshaping.melt(
                df,
                id_vars=id_vars,
                value_vars=value_vars,
                var_name=var_name,
                value_name=value_name,
                dropna=True,
            )

            result.warnings.extend(reshape_result.warnings)
            result.warnings.append(
                f"Reshaped from {reshape_result.original_shape} to {reshape_result.new_shape}"
            )

            # Convert reshaped data to rows
            rows = reshape_result.data.to_dict("records")

            # Process rows
            result = await self._process_rows(rows, result)

        except Exception as e:
            error_msg = f"Failed to reshape and import CSV {file_path}: {e}"
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
        import time

        total_rows = len(rows)

        if total_rows == 0:
            result.warnings.append("No rows to process")
            return result

        # Initialize performance metrics if tracking enabled
        metrics = None
        if self.track_performance:
            metrics = PerformanceMetrics()
            metrics.start_time = time.time()
            metrics.total_rows = total_rows
            if self._memory_tracker:
                self._memory_tracker.start_tracking()
                metrics.initial_memory_mb = self._memory_tracker.initial_memory_mb

        # Determine batch size (auto-tune if enabled)
        batch_size = self.batch_size
        if self._batch_optimizer is not None:
            # Estimate column count from first row
            column_count = len(rows[0]) if rows else 10
            batch_size = self._batch_optimizer.estimate_batch_size(column_count)
            logger.debug(f"Auto-tuned batch size: {batch_size}")

        # Process in batches
        batch_count = 0
        for batch_start in range(0, total_rows, batch_size):
            batch_time_start = time.time() if metrics else 0

            batch_end = min(batch_start + batch_size, total_rows)
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
            batch_count += 1

            # Update result
            result.entities_added += batch_result.entities_added
            result.relations_added += batch_result.relations_added
            result.rows_processed += batch_result.rows_processed
            result.rows_failed += batch_result.rows_failed
            result.errors.extend(batch_result.errors)
            result.warnings.extend(batch_result.warnings)

            # Record batch time for adaptive tuning
            if self._batch_optimizer is not None:
                batch_time = time.time() - batch_time_start
                self._batch_optimizer.record_batch_time(batch_time, len(batch_rows))
                # Adjust batch size for next iteration
                batch_size = self._batch_optimizer.adjust_batch_size()

            # Update memory tracking
            if self._memory_tracker:
                self._memory_tracker.update()

        # Finalize performance metrics
        if metrics:
            metrics.end_time = time.time()
            metrics.batch_count = batch_count
            if self._memory_tracker:
                metrics.peak_memory_mb = self._memory_tracker.peak_memory_mb
            metrics.calculate_throughput()
            result.performance_metrics = metrics

        # Apply aggregations after all batches processed
        if self.mapping.aggregations:
            aggregation_results = await self._apply_aggregations()

            # Store aggregated values as summary entities
            for entity_type, properties in aggregation_results.items():
                try:
                    # Create a summary entity with aggregated statistics
                    summary_entity = Entity(
                        id=f"{entity_type}_summary",
                        entity_type=f"{entity_type}Summary",
                        properties=properties,
                    )

                    # Try to add the summary entity (may already exist from previous import)
                    try:
                        await self.graph_store.add_entity(summary_entity)
                        result.entities_added += 1
                    except ValueError:
                        # Entity already exists, try to update if method exists
                        if hasattr(self.graph_store, 'update_entity'):
                            await self.graph_store.update_entity(summary_entity)
                        else:
                            # For stores without update_entity, just skip
                            pass

                    result.warnings.append(
                        f"Applied aggregations to {entity_type}: {list(properties.keys())}"
                    )
                except Exception as e:
                    result.warnings.append(f"Failed to apply aggregations for {entity_type}: {e}")

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

        # Update aggregation accumulators
        if self.mapping.aggregations:
            self._update_aggregations(rows)

        # Add entities to graph store (use bulk writes if enabled)
        if self.use_bulk_writes and hasattr(self.graph_store, 'add_entities_bulk'):
            try:
                added = await self.graph_store.add_entities_bulk(entities_to_add)
                batch_result.entities_added = added
            except Exception as e:
                error_msg = f"Bulk entity add failed: {e}"
                logger.warning(error_msg)
                batch_result.warnings.append(error_msg)
                if not self.skip_errors:
                    raise
        else:
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

        # Add relations to graph store (use bulk writes if enabled)
        if self.use_bulk_writes and hasattr(self.graph_store, 'add_relations_bulk'):
            try:
                added = await self.graph_store.add_relations_bulk(relations_to_add)
                batch_result.relations_added = added
            except Exception as e:
                error_msg = f"Bulk relation add failed: {e}"
                logger.warning(error_msg)
                batch_result.warnings.append(error_msg)
                if not self.skip_errors:
                    raise
        else:
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

    def _update_aggregations(self, rows: List[Dict[str, Any]]):
        """
        Update aggregation accumulators with batch data

        Args:
            rows: List of row dictionaries
        """
        from aiecs.application.knowledge_graph.builder.schema_mapping import AggregationFunction

        for entity_agg in self.mapping.aggregations:
            entity_type = entity_agg.entity_type

            # Initialize accumulator for this entity type if needed
            if entity_type not in self._aggregation_accumulators:
                self._aggregation_accumulators[entity_type] = {}

            for agg_config in entity_agg.aggregations:
                target_prop = agg_config.target_property

                # Initialize accumulator for this property if needed
                if target_prop not in self._aggregation_accumulators[entity_type]:
                    self._aggregation_accumulators[entity_type][target_prop] = AggregationAccumulator()

                accumulator = self._aggregation_accumulators[entity_type][target_prop]

                # Add values from rows
                for row in rows:
                    value = row.get(agg_config.source_property)
                    if value is not None:
                        accumulator.add(value)

    async def _apply_aggregations(self) -> Dict[str, Dict[str, Any]]:
        """
        Apply aggregations and return computed statistics

        Returns:
            Dictionary of entity_type -> {property -> value}
        """
        from aiecs.application.knowledge_graph.builder.schema_mapping import AggregationFunction

        results = {}

        for entity_agg in self.mapping.aggregations:
            entity_type = entity_agg.entity_type

            if entity_type not in self._aggregation_accumulators:
                continue

            if entity_type not in results:
                results[entity_type] = {}

            for agg_config in entity_agg.aggregations:
                target_prop = agg_config.target_property

                if target_prop not in self._aggregation_accumulators[entity_type]:
                    continue

                accumulator = self._aggregation_accumulators[entity_type][target_prop]

                # Compute aggregated value based on function
                if agg_config.function == AggregationFunction.MEAN:
                    value = accumulator.get_mean()
                elif agg_config.function == AggregationFunction.STD:
                    value = accumulator.get_std()
                elif agg_config.function == AggregationFunction.MIN:
                    value = accumulator.get_min()
                elif agg_config.function == AggregationFunction.MAX:
                    value = accumulator.get_max()
                elif agg_config.function == AggregationFunction.SUM:
                    value = accumulator.get_sum()
                elif agg_config.function == AggregationFunction.COUNT:
                    value = accumulator.get_count()
                elif agg_config.function == AggregationFunction.MEDIAN:
                    value = accumulator.get_median()
                elif agg_config.function == AggregationFunction.VARIANCE:
                    value = accumulator.get_variance()
                else:
                    value = None

                if value is not None:
                    results[entity_type][target_prop] = value

        return results

    def _create_validator_from_config(self, config: Dict[str, Any]) -> DataQualityValidator:
        """
        Create DataQualityValidator from configuration dictionary

        Args:
            config: Validation configuration dictionary

        Returns:
            Configured DataQualityValidator
        """
        # Parse range rules
        range_rules = {}
        if "range_rules" in config:
            for prop, rule_dict in config["range_rules"].items():
                range_rules[prop] = RangeRule(
                    min_value=rule_dict.get("min"),
                    max_value=rule_dict.get("max")
                )

        # Parse required properties
        required_properties = set(config.get("required_properties", []))

        # Create validation config
        validation_config = ValidationConfig(
            range_rules=range_rules,
            required_properties=required_properties,
            detect_outliers=config.get("detect_outliers", False),
            fail_on_violations=config.get("fail_on_violations", False),
            max_violation_rate=config.get("max_violation_rate", 0.1)
        )

        return DataQualityValidator(validation_config)
