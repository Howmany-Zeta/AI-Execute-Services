"""
Schema Inference for Structured Data Import

Automatically infers schema mappings from data structure, reducing manual configuration effort.
"""

from typing import Dict, List, Optional, Any, Union, Set
from pathlib import Path
from dataclasses import dataclass
import re
import logging
import warnings

from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    RelationMapping,
)
from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType

logger = logging.getLogger(__name__)

# Check for pandas availability
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@dataclass
class InferredSchema:
    """
    Result of schema inference
    
    Contains inferred entity and relation mappings that can be reviewed and modified.
    """
    entity_mappings: List[EntityMapping]
    relation_mappings: List[RelationMapping]
    confidence_scores: Dict[str, float]  # Mapping name -> confidence score (0-1)
    warnings: List[str]
    
    def to_schema_mapping(self) -> SchemaMapping:
        """Convert to SchemaMapping for use in pipeline"""
        return SchemaMapping(
            entity_mappings=self.entity_mappings,
            relation_mappings=self.relation_mappings,
        )


class SchemaInference:
    """
    Automatic schema inference from structured data
    
    Analyzes data structure and content to automatically generate schema mappings.
    """
    
    # Common ID column patterns
    ID_PATTERNS = [
        r'^id$',
        r'^.*_id$',
        r'^key$',
        r'^.*_key$',
        r'^pk$',
        r'^.*_pk$',
    ]
    
    # Foreign key patterns (for relation inference)
    FK_PATTERNS = [
        r'^(.+)_id$',  # e.g., dept_id -> dept
        r'^(.+)_key$',  # e.g., dept_key -> dept
        r'^fk_(.+)$',  # e.g., fk_dept -> dept
    ]
    
    def __init__(self, sample_size: int = 1000):
        """
        Initialize schema inference
        
        Args:
            sample_size: Number of rows to sample for inference (default: 1000)
        """
        self.sample_size = sample_size
    
    def infer_from_dataframe(
        self,
        df: 'pd.DataFrame',
        entity_type_hint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> InferredSchema:
        """
        Infer schema from pandas DataFrame
        
        Args:
            df: DataFrame to analyze
            entity_type_hint: Optional hint for entity type name
            metadata: Optional metadata (e.g., SPSS variable labels)
        
        Returns:
            InferredSchema with entity and relation mappings
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for schema inference")
        
        warnings = []
        confidence_scores = {}
        
        # Sample data if too large
        if len(df) > self.sample_size:
            df_sample = df.sample(n=self.sample_size, random_state=42)
            warnings.append(f"Sampled {self.sample_size} rows from {len(df)} for inference")
        else:
            df_sample = df
        
        # Detect ID column
        id_column = self._detect_id_column(df_sample)
        if id_column:
            confidence_scores['id_column'] = 0.9
        else:
            warnings.append("No clear ID column detected, will use first column")
            id_column = df.columns[0] if len(df.columns) > 0 else None
            confidence_scores['id_column'] = 0.5
        
        # Infer property types
        property_types = self._infer_property_types(df_sample, metadata)
        
        # Determine entity type
        entity_type = entity_type_hint or self._infer_entity_type(df.columns.tolist(), id_column)
        
        # Create entity mapping
        entity_mapping = EntityMapping(
            source_columns=df.columns.tolist(),
            entity_type=entity_type,
            property_mapping={col: col for col in df.columns},
            id_column=id_column,
        )
        
        # Infer relations from foreign key patterns
        relation_mappings = self._infer_relations(df_sample, id_column)
        if relation_mappings:
            confidence_scores['relations'] = 0.7

        return InferredSchema(
            entity_mappings=[entity_mapping],
            relation_mappings=relation_mappings,
            confidence_scores=confidence_scores,
            warnings=warnings,
        )

    def _detect_id_column(self, df: 'pd.DataFrame') -> Optional[str]:
        """
        Detect ID column from DataFrame

        Looks for columns matching ID patterns or columns with unique values.

        Args:
            df: DataFrame to analyze

        Returns:
            Name of ID column, or None if not found
        """
        # Check for columns matching ID patterns
        for col in df.columns:
            col_lower = col.lower()
            for pattern in self.ID_PATTERNS:
                if re.match(pattern, col_lower):
                    return col

        # Check for columns with all unique values
        for col in df.columns:
            if df[col].nunique() == len(df):
                return col

        return None

    def _infer_property_types(
        self,
        df: 'pd.DataFrame',
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, PropertyType]:
        """
        Infer property types from DataFrame columns

        Args:
            df: DataFrame to analyze
            metadata: Optional metadata (e.g., SPSS variable labels)

        Returns:
            Dictionary mapping column name to PropertyType
        """
        property_types = {}

        for col in df.columns:
            # Get pandas dtype
            dtype = df[col].dtype

            # Infer PropertyType from pandas dtype
            if pd.api.types.is_integer_dtype(dtype):
                property_types[col] = PropertyType.INTEGER
            elif pd.api.types.is_float_dtype(dtype):
                property_types[col] = PropertyType.FLOAT
            elif pd.api.types.is_bool_dtype(dtype):
                property_types[col] = PropertyType.BOOLEAN
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                property_types[col] = PropertyType.DATETIME
            else:
                # Default to string, but check if it could be a date
                if self._could_be_date(df[col]):
                    property_types[col] = PropertyType.DATETIME
                else:
                    property_types[col] = PropertyType.STRING

        return property_types

    def _could_be_date(self, series: 'pd.Series') -> bool:
        """
        Check if a string series could be dates

        Args:
            series: Pandas series to check

        Returns:
            True if series looks like dates
        """
        # Sample a few non-null values
        sample = series.dropna().head(10)
        if len(sample) == 0:
            return False

        # Try to parse as dates
        # Suppress UserWarning about dateutil fallback - this is expected behavior
        # when pandas can't infer the date format automatically
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
            pd.to_datetime(sample, errors='raise')
            return True
        except (ValueError, TypeError):
            return False

    def _infer_entity_type(self, columns: List[str], id_column: Optional[str]) -> str:
        """
        Infer entity type name from column names

        Args:
            columns: List of column names
            id_column: Name of ID column (if detected)

        Returns:
            Inferred entity type name
        """
        # If ID column has a prefix, use that as entity type
        if id_column:
            # Try to extract entity type from ID column name
            for pattern in self.FK_PATTERNS:
                match = re.match(pattern, id_column.lower())
                if match:
                    entity_type = match.group(1)
                    # Capitalize first letter
                    return entity_type.capitalize()

        # Default to "Entity"
        return "Entity"

    def infer_from_csv(
        self,
        file_path: Union[str, Path],
        encoding: str = "utf-8",
    ) -> InferredSchema:
        """
        Infer schema from CSV file

        Args:
            file_path: Path to CSV file
            encoding: File encoding

        Returns:
            InferredSchema with entity and relation mappings
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for CSV schema inference")

        df = pd.read_csv(file_path, encoding=encoding, nrows=self.sample_size)
        return self.infer_from_dataframe(df)

    def infer_from_spss(
        self,
        file_path: Union[str, Path],
        encoding: str = "utf-8",
    ) -> InferredSchema:
        """
        Infer schema from SPSS file

        Uses SPSS variable labels as property names and value labels for categorical data.

        Args:
            file_path: Path to SPSS file
            encoding: File encoding

        Returns:
            InferredSchema with entity and relation mappings
        """
        try:
            import pyreadstat  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError("pyreadstat is required for SPSS schema inference")

        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for SPSS schema inference")

        # Read SPSS file with metadata
        df, meta = pyreadstat.read_sav(str(file_path), encoding=encoding, row_limit=self.sample_size)

        # Extract metadata
        metadata = {
            "column_names": meta.column_names if hasattr(meta, 'column_names') else [],
            "column_labels": meta.column_labels if hasattr(meta, 'column_labels') else [],
            "variable_value_labels": meta.variable_value_labels if hasattr(meta, 'variable_value_labels') else {},
        }

        return self.infer_from_dataframe(df, metadata=metadata)

    def _infer_relations(
        self,
        df: 'pd.DataFrame',
        id_column: Optional[str],
    ) -> List[RelationMapping]:
        """
        Infer relation mappings from foreign key patterns

        Detects columns that look like foreign keys and creates relation mappings.

        Args:
            df: DataFrame to analyze
            id_column: Name of ID column (source entity)

        Returns:
            List of inferred RelationMapping objects
        """
        if not id_column:
            return []

        relation_mappings = []

        # Look for foreign key columns
        for col in df.columns:
            if col == id_column:
                continue

            col_lower = col.lower()

            # Check if column matches FK pattern
            for pattern in self.FK_PATTERNS:
                match = re.match(pattern, col_lower)
                if match:
                    # Extract target entity type from FK column name
                    target_entity_type = match.group(1).capitalize()

                    # Infer relation type from column name
                    # e.g., "dept_id" -> "BELONGS_TO_DEPT" or "HAS_DEPT"
                    relation_type = self._infer_relation_type(id_column, col, target_entity_type)

                    # Create relation mapping
                    relation_mapping = RelationMapping(
                        source_columns=[id_column, col],
                        relation_type=relation_type,
                        source_entity_column=id_column,
                        target_entity_column=col,
                        property_mapping={},
                    )

                    relation_mappings.append(relation_mapping)
                    break

        return relation_mappings

    def _infer_relation_type(
        self,
        source_column: str,
        target_column: str,
        target_entity_type: str,
    ) -> str:
        """
        Infer relation type name from column names

        Args:
            source_column: Source entity column name
            target_column: Target entity (FK) column name
            target_entity_type: Inferred target entity type

        Returns:
            Inferred relation type name (e.g., "BELONGS_TO", "HAS")
        """
        # Common relation patterns
        # e.g., "emp_id" -> "dept_id" = "WORKS_IN" or "BELONGS_TO"

        # Extract base names
        source_base = source_column.lower().replace('_id', '').replace('_key', '')
        target_base = target_column.lower().replace('_id', '').replace('_key', '').replace('fk_', '')

        # Common relation verbs based on context
        if 'dept' in target_base or 'department' in target_base:
            return "WORKS_IN"
        elif 'manager' in target_base or 'supervisor' in target_base:
            return "REPORTS_TO"
        elif 'company' in target_base or 'organization' in target_base:
            return "BELONGS_TO"
        elif 'project' in target_base:
            return "ASSIGNED_TO"
        elif 'team' in target_base or 'group' in target_base:
            return "MEMBER_OF"
        else:
            # Generic relation type
            return f"HAS_{target_entity_type.upper()}"

    def merge_with_partial_schema(
        self,
        inferred: InferredSchema,
        partial_mapping: SchemaMapping,
    ) -> InferredSchema:
        """
        Merge inferred schema with user-provided partial schema

        User-defined mappings take precedence over inferred ones.

        Args:
            inferred: Inferred schema
            partial_mapping: User-provided partial schema mapping

        Returns:
            Merged InferredSchema
        """
        # Start with user-defined mappings
        entity_mappings = list(partial_mapping.entity_mappings)
        relation_mappings = list(partial_mapping.relation_mappings)

        # Get entity types already defined by user
        user_entity_types = {em.entity_type for em in partial_mapping.entity_mappings}

        # Add inferred entity mappings that don't conflict
        for inferred_em in inferred.entity_mappings:
            if inferred_em.entity_type not in user_entity_types:
                entity_mappings.append(inferred_em)

        # Get relation types already defined by user
        user_relation_types = {
            (rm.source_entity_column, rm.target_entity_column, rm.relation_type)
            for rm in partial_mapping.relation_mappings
        }

        # Add inferred relation mappings that don't conflict
        for inferred_rm in inferred.relation_mappings:
            key = (inferred_rm.source_entity_column, inferred_rm.target_entity_column, inferred_rm.relation_type)
            if key not in user_relation_types:
                relation_mappings.append(inferred_rm)

        return InferredSchema(
            entity_mappings=entity_mappings,
            relation_mappings=relation_mappings,
            confidence_scores=inferred.confidence_scores,
            warnings=inferred.warnings + ["Merged with user-provided partial schema"],
        )

