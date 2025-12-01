"""
Schema Mapping for Structured Data Import

Maps structured data (CSV, JSON) columns to knowledge graph entity and relation types
with support for property transformations.
"""

from typing import Dict, List, Optional, Any, cast, Callable
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType


class TransformationType(str, Enum):
    """Types of property transformations"""

    RENAME = "rename"  # Rename column to property
    TYPE_CAST = "type_cast"  # Cast value to different type
    COMPUTE = "compute"  # Compute value from multiple columns
    CONSTANT = "constant"  # Use constant value
    SKIP = "skip"  # Skip this column


class PropertyTransformation(BaseModel):
    """
    Property transformation configuration

    Defines how a source column/value is transformed into a target property.
    """

    transformation_type: TransformationType = Field(..., description="Type of transformation to apply")

    source_column: Optional[str] = Field(
        default=None,
        description="Source column name (for rename/type_cast/compute)",
    )

    target_property: str = Field(..., description="Target property name in entity/relation")

    target_type: Optional[PropertyType] = Field(default=None, description="Target property type (for type_cast)")

    constant_value: Optional[Any] = Field(
        default=None,
        description="Constant value (for constant transformation)",
    )

    compute_function: Optional[str] = Field(
        default=None,
        description="Function name for compute transformation (e.g., 'concat', 'sum')",
    )

    compute_args: Optional[List[str]] = Field(
        default=None,
        description="Additional column names for compute function",
    )

    @field_validator("transformation_type")
    @classmethod
    def validate_transformation_type(cls, v: TransformationType) -> TransformationType:
        """Validate transformation type"""
        return v

    def apply(self, row: Dict[str, Any]) -> Any:
        """
        Apply transformation to a data row

        Args:
            row: Dictionary of column name -> value

        Returns:
            Transformed value for target property
        """
        if self.transformation_type == TransformationType.RENAME:
            if self.source_column is None:
                raise ValueError("source_column required for rename transformation")
            return row.get(self.source_column)

        elif self.transformation_type == TransformationType.TYPE_CAST:
            if self.source_column is None:
                raise ValueError("source_column required for type_cast transformation")
            if self.target_type is None:
                raise ValueError("target_type required for type_cast transformation")

            value = row.get(self.source_column)
            if value is None:
                return None

            return self._cast_value(value, self.target_type)

        elif self.transformation_type == TransformationType.COMPUTE:
            if self.compute_function is None:
                raise ValueError("compute_function required for compute transformation")

            # Get source values
            source_values = []
            if self.source_column:
                source_values.append(row.get(self.source_column))
            if self.compute_args:
                source_values.extend([row.get(col) for col in self.compute_args])

            return self._compute_value(self.compute_function, source_values)

        elif self.transformation_type == TransformationType.CONSTANT:
            return self.constant_value

        elif self.transformation_type == TransformationType.SKIP:
            return None

        else:
            raise ValueError(f"Unknown transformation type: {self.transformation_type}")

    def _cast_value(self, value: Any, target_type: PropertyType) -> Any:
        """Cast value to target type"""
        try:
            if target_type == PropertyType.STRING:
                return str(value)
            elif target_type == PropertyType.INTEGER:
                if isinstance(value, bool):
                    raise ValueError(f"Cannot cast boolean {value} to integer")
                return int(float(value))  # Handle "123.0" -> 123
            elif target_type == PropertyType.FLOAT:
                if isinstance(value, bool):
                    raise ValueError(f"Cannot cast boolean {value} to float")
                return float(value)
            elif target_type == PropertyType.BOOLEAN:
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")
                return bool(value)
            elif target_type == PropertyType.LIST:
                if isinstance(value, list):
                    return value
                elif isinstance(value, str):
                    # Try to parse as JSON list or comma-separated
                    import json

                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return [v.strip() for v in value.split(",")]
                else:
                    return [value]
            elif target_type == PropertyType.DICT:
                if isinstance(value, dict):
                    return value
                elif isinstance(value, str):
                    import json

                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        # If not valid JSON, wrap as dict with "value" key
                        return {"value": value}
                else:
                    return {"value": value}
            else:
                return value  # ANY type or unknown
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to cast {value} to {target_type}: {e}")

    def _compute_value(self, function_name: str, values: List[Any]) -> Any:
        """Compute value using function"""
        # Remove None values for most functions
        non_none_values = [v for v in values if v is not None]

        if function_name == "concat":
            return "".join(str(v) for v in values if v is not None)
        elif function_name == "concat_space":
            return " ".join(str(v) for v in values if v is not None)
        elif function_name == "concat_comma":
            return ", ".join(str(v) for v in values if v is not None)
        elif function_name == "sum":
            return sum(float(v) for v in non_none_values if self._is_numeric(v))
        elif function_name == "avg" or function_name == "average":
            if not non_none_values:
                return None
            numeric_values = [float(v) for v in non_none_values if self._is_numeric(v)]
            if not numeric_values:
                return None
            return sum(numeric_values) / len(numeric_values)
        elif function_name == "max":
            if not non_none_values:
                return None
            numeric_values = [float(v) for v in non_none_values if self._is_numeric(v)]
            if not numeric_values:
                return max(non_none_values)
            return max(numeric_values)
        elif function_name == "min":
            if not non_none_values:
                return None
            numeric_values = [float(v) for v in non_none_values if self._is_numeric(v)]
            if not numeric_values:
                return min(non_none_values)
            return min(numeric_values)
        else:
            raise ValueError(f"Unknown compute function: {function_name}")

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        """Check if value is numeric"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False


class EntityMapping(BaseModel):
    """
    Entity mapping configuration

    Maps source data columns to an entity type with property transformations.
    """

    source_columns: List[str] = Field(..., description="Source column names to use for this entity")

    entity_type: str = Field(..., description="Target entity type name")

    property_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Simple column-to-property mapping (column_name -> property_name)",
    )

    transformations: List[PropertyTransformation] = Field(default_factory=list, description="Property transformations to apply")

    id_column: Optional[str] = Field(
        default=None,
        description="Column to use as entity ID (default: first column or generated)",
    )

    @field_validator("source_columns")
    @classmethod
    def validate_source_columns(cls, v: List[str]) -> List[str]:
        """Validate source columns are not empty"""
        if not v:
            raise ValueError("source_columns cannot be empty")
        return v

    def map_row_to_entity(self, row: Dict[str, Any], entity_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Map a data row to entity properties

        Args:
            row: Dictionary of column name -> value
            entity_id: Optional entity ID (if not provided, will use id_column or generate)

        Returns:
            Dictionary with entity properties
        """
        properties = {}

        # Apply simple property mappings first
        for column, property_name in self.property_mapping.items():
            if column in row:
                properties[property_name] = row[column]

        # Apply transformations
        for transformation in self.transformations:
            try:
                value = transformation.apply(row)
                if value is not None or transformation.transformation_type != TransformationType.SKIP:
                    properties[transformation.target_property] = value
            except Exception as e:
                # Log warning but continue
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Transformation failed for {transformation.target_property}: {e}")

        # Determine entity ID
        if entity_id is None:
            if self.id_column and self.id_column in row:
                entity_id = str(row[self.id_column])
            elif self.source_columns:
                # Use first column as ID
                entity_id = str(row.get(self.source_columns[0], ""))

        return {
            "id": entity_id,
            "type": self.entity_type,
            "properties": properties,
        }


class RelationMapping(BaseModel):
    """
    Relation mapping configuration

    Maps source data columns to a relation type between entities.
    """

    source_columns: List[str] = Field(..., description="Source column names to use for this relation")

    relation_type: str = Field(..., description="Target relation type name")

    source_entity_column: str = Field(..., description="Column name containing source entity ID")

    target_entity_column: str = Field(..., description="Column name containing target entity ID")

    property_mapping: Dict[str, str] = Field(default_factory=dict, description="Simple column-to-property mapping")

    transformations: List[PropertyTransformation] = Field(default_factory=list, description="Property transformations to apply")

    @field_validator("source_columns")
    @classmethod
    def validate_source_columns(cls, v: List[str]) -> List[str]:
        """Validate source columns are not empty"""
        if not v:
            raise ValueError("source_columns cannot be empty")
        return v

    @field_validator("source_entity_column", "target_entity_column")
    @classmethod
    def validate_entity_columns(cls, v: str) -> str:
        """Validate entity column names are provided"""
        if not v:
            raise ValueError("Entity column names cannot be empty")
        return v

    def map_row_to_relation(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map a data row to relation properties

        Args:
            row: Dictionary of column name -> value

        Returns:
            Dictionary with relation properties (source_id, target_id, type, properties)
        """
        # Get source and target entity IDs
        source_id = str(row.get(self.source_entity_column, ""))
        target_id = str(row.get(self.target_entity_column, ""))

        if not source_id or not target_id:
            raise ValueError(f"Missing entity IDs: source={source_id}, target={target_id}. " f"Columns: source={self.source_entity_column}, target={self.target_entity_column}")

        properties = {}

        # Apply simple property mappings
        for column, property_name in self.property_mapping.items():
            if column in row:
                properties[property_name] = row[column]

        # Apply transformations
        for transformation in self.transformations:
            try:
                value = transformation.apply(row)
                if value is not None or transformation.transformation_type != TransformationType.SKIP:
                    properties[transformation.target_property] = value
            except Exception as e:
                # Log warning but continue
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Transformation failed for {transformation.target_property}: {e}")

        return {
            "source_id": source_id,
            "target_id": target_id,
            "type": self.relation_type,
            "properties": properties,
        }


class AggregationFunction(str, Enum):
    """Statistical aggregation functions"""

    MEAN = "mean"
    STD = "std"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    SUM = "sum"
    MEDIAN = "median"
    VARIANCE = "variance"


class AggregationConfig(BaseModel):
    """
    Configuration for statistical aggregation during import

    Defines how to compute aggregated statistics from source data
    and store them as entity properties.
    """

    source_property: str = Field(..., description="Source property to aggregate")

    function: AggregationFunction = Field(..., description="Aggregation function to apply")

    target_property: str = Field(..., description="Target property name for aggregated value")

    group_by: Optional[List[str]] = Field(
        default=None,
        description="Columns to group by (for grouped aggregations)",
    )

    filter_condition: Optional[str] = Field(
        default=None,
        description="Optional filter condition (e.g., 'value > 0')",
    )


class EntityAggregation(BaseModel):
    """
    Aggregation configuration for an entity type

    Defines aggregations to compute for entities of a specific type.
    """

    entity_type: str = Field(..., description="Entity type to aggregate")

    aggregations: List[AggregationConfig] = Field(
        default_factory=list,
        description="List of aggregations to compute",
    )

    incremental: bool = Field(
        default=True,
        description="Whether to compute aggregations incrementally during batch processing",
    )


class SchemaMapping(BaseModel):
    """
    Schema mapping configuration

    Defines how structured data (CSV, JSON) maps to knowledge graph entities and relations.
    """

    entity_mappings: List[EntityMapping] = Field(default_factory=list, description="Entity type mappings")

    relation_mappings: List[RelationMapping] = Field(default_factory=list, description="Relation type mappings")

    aggregations: List[EntityAggregation] = Field(
        default_factory=list,
        description="Statistical aggregations to compute during import",
    )

    validation_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Data quality validation configuration",
    )

    description: Optional[str] = Field(default=None, description="Human-readable description of this mapping")

    def validate_mapping(self) -> List[str]:
        """
        Validate mapping consistency

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check entity mappings
        entity_type_names = set()
        for i, mapping in enumerate(self.entity_mappings):
            if not mapping.entity_type:
                errors.append(f"Entity mapping {i}: entity_type is required")

            if mapping.entity_type in entity_type_names:
                errors.append(f"Entity mapping {i}: duplicate entity_type '{mapping.entity_type}'")
            entity_type_names.add(mapping.entity_type)

            # Check that source columns are specified
            if not mapping.source_columns:
                errors.append(f"Entity mapping {i}: source_columns cannot be empty")

            # Check transformations
            for j, trans in enumerate(mapping.transformations):
                if not trans.target_property:
                    errors.append(f"Entity mapping {i}, transformation {j}: target_property is required")

                if trans.transformation_type == TransformationType.RENAME:
                    if not trans.source_column:
                        errors.append(f"Entity mapping {i}, transformation {j}: " f"source_column required for rename")

                elif trans.transformation_type == TransformationType.TYPE_CAST:
                    if not trans.source_column:
                        errors.append(f"Entity mapping {i}, transformation {j}: " f"source_column required for type_cast")
                    if not trans.target_type:
                        errors.append(f"Entity mapping {i}, transformation {j}: " f"target_type required for type_cast")

                elif trans.transformation_type == TransformationType.COMPUTE:
                    if not trans.compute_function:
                        errors.append(f"Entity mapping {i}, transformation {j}: " f"compute_function required for compute")

        # Check relation mappings
        relation_type_names = set()
        for i, relation_mapping in enumerate(self.relation_mappings):
            if not relation_mapping.relation_type:
                errors.append(f"Relation mapping {i}: relation_type is required")

            if relation_mapping.relation_type in relation_type_names:
                errors.append(f"Relation mapping {i}: duplicate relation_type '{relation_mapping.relation_type}'")
            relation_type_names.add(relation_mapping.relation_type)

            # Check entity columns
            if not relation_mapping.source_entity_column:
                errors.append(f"Relation mapping {i}: source_entity_column is required")
            if not relation_mapping.target_entity_column:
                errors.append(f"Relation mapping {i}: target_entity_column is required")

            # Check that source columns include entity columns
            if relation_mapping.source_entity_column not in relation_mapping.source_columns:
                errors.append(f"Relation mapping {i}: source_entity_column '{relation_mapping.source_entity_column}' " f"must be in source_columns")
            if relation_mapping.target_entity_column not in relation_mapping.source_columns:
                errors.append(f"Relation mapping {i}: target_entity_column '{relation_mapping.target_entity_column}' " f"must be in source_columns")

        return errors

    def is_valid(self) -> bool:
        """
        Check if mapping is valid

        Returns:
            True if mapping is valid
        """
        return len(self.validate_mapping()) == 0

    def get_entity_mapping(self, entity_type: str) -> Optional[EntityMapping]:
        """
        Get entity mapping by entity type name

        Args:
            entity_type: Entity type name

        Returns:
            Entity mapping or None if not found
        """
        for mapping in self.entity_mappings:
            if mapping.entity_type == entity_type:
                return mapping
        return None

    def get_relation_mapping(self, relation_type: str) -> Optional[RelationMapping]:
        """
        Get relation mapping by relation type name

        Args:
            relation_type: Relation type name

        Returns:
            Relation mapping or None if not found
        """
        for mapping in self.relation_mappings:
            if mapping.relation_type == relation_type:
                return mapping
        return None

    def get_aggregations(self, entity_type: str) -> Optional[EntityAggregation]:
        """
        Get aggregation configuration for entity type

        Args:
            entity_type: Entity type name

        Returns:
            EntityAggregation or None if not found
        """
        for agg in self.aggregations:
            if agg.entity_type == entity_type:
                return agg
        return None
