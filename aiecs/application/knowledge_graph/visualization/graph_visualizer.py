"""
Graph Visualization Utilities

Export knowledge graphs to various formats for visualization.
"""

from typing import List, Dict, Any
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path


class GraphVisualizer:
    """
    Visualize knowledge graphs in various formats

    Supports export to:
    - DOT format (Graphviz)
    - JSON for D3.js, Cytoscape.js, etc.
    - NetworkX-compatible format

    Example:
        ```python
        visualizer = GraphVisualizer()

        # Export to DOT
        dot = visualizer.to_dot(entities, relations)
        with open("graph.dot", "w") as f:
            f.write(dot)

        # Export to JSON
        json_data = visualizer.to_json(entities, relations)
        ```
    """

    def to_dot(
        self,
        entities: List[Entity],
        relations: List[Relation],
        graph_name: str = "knowledge_graph",
        include_properties: bool = True,
        max_label_length: int = 50,
    ) -> str:
        """
        Export graph to DOT format (Graphviz)

        Args:
            entities: List of entities
            relations: List of relations
            graph_name: Name of the graph
            include_properties: Include entity properties in labels
            max_label_length: Maximum label length

        Returns:
            DOT format string
        """
        lines = []
        lines.append(f"digraph {graph_name} {{")
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=rounded];")
        lines.append("")

        # Add nodes
        for entity in entities:
            label = self._create_entity_label(entity, include_properties, max_label_length)
            node_id = self._sanitize_id(entity.id)
            color = self._get_entity_color(entity.entity_type)

            lines.append(f'  {node_id} [label="{label}", fillcolor="{color}", style="rounded,filled"];')

        lines.append("")

        # Add edges
        for relation in relations:
            source_id = self._sanitize_id(relation.source_id)
            target_id = self._sanitize_id(relation.target_id)
            label = relation.relation_type

            lines.append(f'  {source_id} -> {target_id} [label="{label}"];')

        lines.append("}")
        return "\n".join(lines)

    def to_json(
        self,
        entities: List[Entity],
        relations: List[Relation],
        format: str = "d3",
    ) -> Dict[str, Any]:
        """
        Export graph to JSON format

        Args:
            entities: List of entities
            relations: List of relations
            format: JSON format ("d3", "cytoscape", "networkx")

        Returns:
            Dictionary suitable for JSON export
        """
        if format == "d3":
            return self._to_d3_json(entities, relations)
        elif format == "cytoscape":
            return self._to_cytoscape_json(entities, relations)
        elif format == "networkx":
            return self._to_networkx_json(entities, relations)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _to_d3_json(self, entities: List[Entity], relations: List[Relation]) -> Dict[str, Any]:
        """Export to D3.js force-directed graph format"""
        nodes = []
        for entity in entities:
            nodes.append(
                {
                    "id": entity.id,
                    "name": entity.properties.get("name", entity.id),
                    "type": entity.entity_type,
                    "properties": entity.properties,
                    "group": hash(entity.entity_type) % 10,  # Color group
                }
            )

        links = []
        for relation in relations:
            links.append(
                {
                    "source": relation.source_id,
                    "target": relation.target_id,
                    "type": relation.relation_type,
                    "properties": relation.properties,
                }
            )

        return {"nodes": nodes, "links": links}

    def _to_cytoscape_json(self, entities: List[Entity], relations: List[Relation]) -> Dict[str, Any]:
        """Export to Cytoscape.js format"""
        elements = []

        # Add nodes
        for entity in entities:
            elements.append(
                {
                    "data": {
                        "id": entity.id,
                        "label": entity.properties.get("name", entity.id),
                        "type": entity.entity_type,
                        "properties": entity.properties,
                    },
                    "group": "nodes",
                }
            )

        # Add edges
        for relation in relations:
            elements.append(
                {
                    "data": {
                        "id": relation.id,
                        "source": relation.source_id,
                        "target": relation.target_id,
                        "label": relation.relation_type,
                        "properties": relation.properties,
                    },
                    "group": "edges",
                }
            )

        return {"elements": elements}

    def _to_networkx_json(self, entities: List[Entity], relations: List[Relation]) -> Dict[str, Any]:
        """Export to NetworkX node-link format"""
        nodes = []
        for entity in entities:
            nodes.append(
                {
                    "id": entity.id,
                    "entity_type": entity.entity_type,
                    **entity.properties,
                }
            )

        links = []
        for relation in relations:
            links.append(
                {
                    "source": relation.source_id,
                    "target": relation.target_id,
                    "relation_type": relation.relation_type,
                    **relation.properties,
                }
            )

        return {
            "directed": True,
            "multigraph": False,
            "graph": {},
            "nodes": nodes,
            "links": links,
        }

    def to_mermaid(
        self,
        entities: List[Entity],
        relations: List[Relation],
        max_entities: int = 50,
    ) -> str:
        """
        Export graph to Mermaid diagram format

        Args:
            entities: List of entities
            relations: List of relations
            max_entities: Maximum entities to include

        Returns:
            Mermaid diagram string
        """
        lines = []
        lines.append("graph LR")

        # Limit entities for readability
        entities_subset = entities[:max_entities]
        entity_ids = {e.id for e in entities_subset}

        # Add nodes
        for entity in entities_subset:
            label = entity.properties.get("name", entity.id)
            label = label[:30]  # Truncate long labels
            node_id = self._sanitize_id(entity.id)
            lines.append(f'  {node_id}["{label}"]')

        # Add edges (only between included entities)
        for relation in relations:
            if relation.source_id in entity_ids and relation.target_id in entity_ids:
                source_id = self._sanitize_id(relation.source_id)
                target_id = self._sanitize_id(relation.target_id)
                label = relation.relation_type
                lines.append(f"  {source_id} -->|{label}| {target_id}")

        return "\n".join(lines)

    def export_path_to_dot(self, path: Path) -> str:
        """
        Export a single path to DOT format

        Args:
            path: Path to export

        Returns:
            DOT format string
        """
        lines = []
        lines.append("digraph path {")
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=rounded];")
        lines.append("")

        # Add nodes from path
        for entity in path.nodes:
            label = entity.properties.get("name", entity.id)
            node_id = self._sanitize_id(entity.id)
            lines.append(f'  {node_id} [label="{label}"];')

        lines.append("")

        # Add edges from path
        for relation in path.edges:
            source_id = self._sanitize_id(relation.source_id)
            target_id = self._sanitize_id(relation.target_id)
            label = relation.relation_type
            lines.append(f'  {source_id} -> {target_id} [label="{label}"];')

        lines.append("}")
        return "\n".join(lines)

    def _create_entity_label(self, entity: Entity, include_properties: bool, max_length: int) -> str:
        """Create label for entity node"""
        label_parts = [f"{entity.entity_type}: {entity.id}"]

        if include_properties and entity.properties:
            # Add key properties
            for key, value in list(entity.properties.items())[:3]:
                label_parts.append(f"{key}: {value}")

        label = "\\n".join(label_parts)

        if len(label) > max_length:
            label = label[:max_length] + "..."

        return label

    def _sanitize_id(self, id_str: str) -> str:
        """Sanitize ID for DOT format"""
        # Replace special characters
        sanitized = id_str.replace("-", "_").replace(":", "_").replace(" ", "_")
        # Ensure it starts with a letter
        if not sanitized[0].isalpha():
            sanitized = "n_" + sanitized
        return sanitized

    def _get_entity_color(self, entity_type: str) -> str:
        """Get color for entity type"""
        colors = {
            "Person": "lightblue",
            "Company": "lightgreen",
            "Product": "lightyellow",
            "Location": "lightcoral",
            "Event": "lightpink",
            "Document": "lightgray",
        }
        return colors.get(entity_type, "white")
