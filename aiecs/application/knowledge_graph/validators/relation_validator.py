"""
Relation Validator

Validates relations against knowledge graph schema.
"""

from typing import List, Optional, Tuple
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema


class RelationValidator:
    """
    Validate relations against schema rules

    Ensures that:
    - Relation type exists in schema
    - Source and target entity types are compatible
    - Relation properties match schema
    - Required properties are present

    Example:
        ```python
        validator = RelationValidator(schema)

        is_valid, errors = validator.validate_relation(
            relation,
            source_entity,
            target_entity
        )

        if not is_valid:
            print(f"Invalid relation: {errors}")
        ```
    """

    def __init__(self, schema: Optional[GraphSchema] = None, strict: bool = False):
        """
        Initialize relation validator

        Args:
            schema: GraphSchema to validate against (optional)
            strict: If True, reject relations not in schema; if False, allow unknown types
        """
        self.schema = schema
        self.strict = strict

    def validate_relation(self, relation: Relation, source_entity: Entity, target_entity: Entity) -> Tuple[bool, List[str]]:
        """
        Validate a relation against schema

        Args:
            relation: Relation to validate
            source_entity: Source entity
            target_entity: Target entity

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Basic validation (always performed)
        if not relation.source_id:
            errors.append("Relation missing source_id")
        if not relation.target_id:
            errors.append("Relation missing target_id")
        if not relation.relation_type:
            errors.append("Relation missing relation_type")

        # Check entity IDs match
        if relation.source_id != source_entity.id:
            errors.append(f"Relation source_id '{relation.source_id}' does not match " f"source_entity id '{source_entity.id}'")
        if relation.target_id != target_entity.id:
            errors.append(f"Relation target_id '{relation.target_id}' does not match " f"target_entity id '{target_entity.id}'")

        # Schema-based validation (if schema provided)
        if self.schema:
            schema_errors = self._validate_against_schema(relation, source_entity, target_entity)
            errors.extend(schema_errors)

        return (len(errors) == 0, errors)

    def validate_relations(self, relations: List[Relation], entities: List[Entity]) -> List[Tuple[Relation, bool, List[str]]]:
        """
        Validate multiple relations

        Args:
            relations: List of relations to validate
            entities: List of entities (source and targets)

        Returns:
            List of (relation, is_valid, errors) tuples
        """
        # Build entity lookup
        entity_lookup = {e.id: e for e in entities}

        results = []
        for relation in relations:
            source = entity_lookup.get(relation.source_id)
            target = entity_lookup.get(relation.target_id)

            if not source or not target:
                is_valid = False
                errors = [f"Source or target entity not found for relation {relation.id}"]
            else:
                is_valid, errors = self.validate_relation(relation, source, target)

            results.append((relation, is_valid, errors))

        return results

    def filter_valid_relations(self, relations: List[Relation], entities: List[Entity]) -> List[Relation]:
        """
        Filter relations to only valid ones

        Args:
            relations: List of relations
            entities: List of entities

        Returns:
            List of valid relations
        """
        validation_results = self.validate_relations(relations, entities)
        return [relation for relation, is_valid, errors in validation_results if is_valid]

    def _validate_against_schema(self, relation: Relation, source_entity: Entity, target_entity: Entity) -> List[str]:
        """
        Validate relation against schema rules

        Args:
            relation: Relation to validate
            source_entity: Source entity
            target_entity: Target entity

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check if schema is available
        if self.schema is None:
            if self.strict:
                errors.append("Schema is required for strict validation")
            return errors

        # Check if relation type exists in schema
        if not self.schema.has_relation_type(relation.relation_type):
            if self.strict:
                errors.append(f"Relation type '{relation.relation_type}' not found in schema")
            # In non-strict mode, allow unknown relation types
            return errors

        # Get relation type schema
        rel_type_schema = self.schema.get_relation_type(relation.relation_type)

        # Skip validation if relation type schema not found
        if rel_type_schema is None:
            return errors

        # Validate source entity type
        if rel_type_schema.source_entity_types:
            if source_entity.entity_type not in rel_type_schema.source_entity_types:
                errors.append(f"Source entity type '{source_entity.entity_type}' not allowed for " f"relation '{relation.relation_type}'. " f"Allowed types: {rel_type_schema.source_entity_types}")

        # Validate target entity type
        if rel_type_schema.target_entity_types:
            if target_entity.entity_type not in rel_type_schema.target_entity_types:
                errors.append(f"Target entity type '{target_entity.entity_type}' not allowed for " f"relation '{relation.relation_type}'. " f"Allowed types: {rel_type_schema.target_entity_types}")

        # Validate relation properties against schema
        property_errors = self._validate_relation_properties(relation, rel_type_schema)
        errors.extend(property_errors)

        return errors

    def _validate_relation_properties(self, relation: Relation, rel_type_schema) -> List[str]:
        """
        Validate relation properties against schema

        Checks:
        - Required properties are present
        - Property types match schema definitions
        - Property values are within allowed ranges/values
        - Unknown properties are not present (in strict mode)

        Args:
            relation: Relation to validate
            rel_type_schema: RelationType schema to validate against

        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        relation_properties = relation.properties or {}

        # Check required properties are present
        for prop_name, prop_schema in rel_type_schema.properties.items():
            if prop_schema.required and prop_name not in relation_properties:
                available_props = list(rel_type_schema.properties.keys())
                errors.append(
                    f"Required property '{prop_name}' missing for relation type '{relation.relation_type}'. "
                    f"Available properties: {', '.join(available_props)}"
                )

        # Validate each provided property
        for prop_name, prop_value in relation_properties.items():
            # Check if property exists in schema
            if prop_name not in rel_type_schema.properties:
                if self.strict:
                    available_props = list(rel_type_schema.properties.keys())
                    errors.append(
                        f"Unknown property '{prop_name}' for relation type '{relation.relation_type}'. "
                        f"Available properties: {', '.join(available_props) if available_props else 'none'}"
                    )
                # In non-strict mode, allow unknown properties
                continue

            # Get property schema
            prop_schema = rel_type_schema.properties[prop_name]

            # Validate property value against schema
            try:
                prop_schema.validate_value(prop_value)
            except ValueError as e:
                # Convert ValueError to helpful error message
                error_msg = str(e)
                # Enhance error message with relation context
                if "Property" in error_msg and "'" in error_msg:
                    # Error already includes property name, just add relation context
                    errors.append(
                        f"Property validation failed for relation '{relation.relation_type}': {error_msg}"
                    )
                else:
                    errors.append(
                        f"Property '{prop_name}' validation failed for relation '{relation.relation_type}': {error_msg}"
                    )

        return errors
