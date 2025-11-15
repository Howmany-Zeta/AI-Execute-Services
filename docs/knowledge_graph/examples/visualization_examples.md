# Knowledge Graph Visualization Examples

## Overview

This guide demonstrates how to visualize knowledge graphs using the AIECS visualization utilities.

## Table of Contents

1. [Export to DOT (Graphviz)](#export-to-dot-graphviz)
2. [Export to JSON (D3.js)](#export-to-json-d3js)
3. [Export to Cytoscape.js](#export-to-cytoscapejs)
4. [Export to Mermaid](#export-to-mermaid)
5. [Visualize Paths](#visualize-paths)
6. [Interactive Visualizations](#interactive-visualizations)

## Export to DOT (Graphviz)

### Basic Export

```python
from aiecs.application.knowledge_graph.visualization import GraphVisualizer
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

# Get entities and relations from store
store = InMemoryGraphStore()
await store.initialize()

# Add some data
# ... (add entities and relations)

# Get all entities and relations
entities = await store.get_all_entities()
relations = await store.get_all_relations()

# Create visualizer
visualizer = GraphVisualizer()

# Export to DOT
dot_content = visualizer.to_dot(entities, relations)

# Save to file
with open("graph.dot", "w") as f:
    f.write(dot_content)
```

### Render with Graphviz

```bash
# Install Graphviz
sudo apt-get install graphviz  # Ubuntu/Debian
brew install graphviz          # macOS

# Render to PNG
dot -Tpng graph.dot -o graph.png

# Render to SVG
dot -Tsvg graph.dot -o graph.svg

# Render to PDF
dot -Tpdf graph.dot -o graph.pdf
```

### Customize DOT Output

```python
# Customize visualization
dot_content = visualizer.to_dot(
    entities,
    relations,
    graph_name="my_knowledge_graph",
    include_properties=True,  # Include entity properties
    max_label_length=100      # Maximum label length
)
```

## Export to JSON (D3.js)

### D3.js Force-Directed Graph

```python
import json

# Export to D3.js format
d3_data = visualizer.to_json(entities, relations, format="d3")

# Save to JSON file
with open("graph_d3.json", "w") as f:
    json.dump(d3_data, f, indent=2)
```

### HTML Visualization with D3.js

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        .node { stroke: #fff; stroke-width: 1.5px; }
        .link { stroke: #999; stroke-opacity: 0.6; }
        text { font: 10px sans-serif; pointer-events: none; }
    </style>
</head>
<body>
    <svg width="960" height="600"></svg>
    <script>
        d3.json("graph_d3.json").then(function(graph) {
            const svg = d3.select("svg");
            const width = +svg.attr("width");
            const height = +svg.attr("height");
            
            const simulation = d3.forceSimulation(graph.nodes)
                .force("link", d3.forceLink(graph.links).id(d => d.id))
                .force("charge", d3.forceManyBody().strength(-300))
                .force("center", d3.forceCenter(width / 2, height / 2));
            
            const link = svg.append("g")
                .selectAll("line")
                .data(graph.links)
                .enter().append("line")
                .attr("class", "link");
            
            const node = svg.append("g")
                .selectAll("circle")
                .data(graph.nodes)
                .enter().append("circle")
                .attr("class", "node")
                .attr("r", 5)
                .attr("fill", d => d3.schemeCategory10[d.group]);
            
            const text = svg.append("g")
                .selectAll("text")
                .data(graph.nodes)
                .enter().append("text")
                .text(d => d.name);
            
            simulation.on("tick", () => {
                link.attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                
                node.attr("cx", d => d.x)
                    .attr("cy", d => d.y);
                
                text.attr("x", d => d.x + 8)
                    .attr("y", d => d.y + 3);
            });
        });
    </script>
</body>
</html>
```

## Export to Cytoscape.js

### Export to Cytoscape Format

```python
# Export to Cytoscape.js format
cytoscape_data = visualizer.to_json(entities, relations, format="cytoscape")

# Save to JSON
with open("graph_cytoscape.json", "w") as f:
    json.dump(cytoscape_data, f, indent=2)
```

### HTML Visualization with Cytoscape.js

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.23.0/cytoscape.min.js"></script>
    <style>
        #cy { width: 100%; height: 600px; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <div id="cy"></div>
    <script>
        fetch('graph_cytoscape.json')
            .then(response => response.json())
            .then(data => {
                const cy = cytoscape({
                    container: document.getElementById('cy'),
                    elements: data.elements,
                    style: [
                        {
                            selector: 'node',
                            style: {
                                'background-color': '#666',
                                'label': 'data(label)'
                            }
                        },
                        {
                            selector: 'edge',
                            style: {
                                'width': 2,
                                'line-color': '#ccc',
                                'target-arrow-color': '#ccc',
                                'target-arrow-shape': 'triangle',
                                'label': 'data(label)',
                                'curve-style': 'bezier'
                            }
                        }
                    ],
                    layout: {
                        name: 'cose',
                        idealEdgeLength: 100,
                        nodeOverlap: 20
                    }
                });
            });
    </script>
</body>
</html>
```

## Export to Mermaid

### Generate Mermaid Diagram

```python
# Export to Mermaid format
mermaid_content = visualizer.to_mermaid(entities, relations, max_entities=20)

# Save to file
with open("graph.mmd", "w") as f:
    f.write(mermaid_content)
```

### Use in Markdown

````markdown
# My Knowledge Graph

```mermaid
graph LR
  person_1["Alice Smith"]
  company_1["Tech Corp"]
  person_1 -->|WORKS_FOR| company_1
```
````

### Render with Mermaid CLI

```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Render to PNG
mmdc -i graph.mmd -o graph.png

# Render to SVG
mmdc -i graph.mmd -o graph.svg
```

## Visualize Paths

### Export Single Path

```python
from aiecs.domain.knowledge_graph.models.path import Path

# Get a path from traversal
paths = await store.traverse("person_1", max_depth=3)
path = paths[0]

# Export path to DOT
path_dot = visualizer.export_path_to_dot(path)

# Save and render
with open("path.dot", "w") as f:
    f.write(path_dot)
```

## Interactive Visualizations

### Complete Example

```python
import asyncio
import json
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.application.knowledge_graph.visualization import GraphVisualizer

async def create_and_visualize():
    # Initialize store
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Add entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    company = Entity(id="tech_corp", entity_type="Company", properties={"name": "Tech Corp"})
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(company)
    
    # Add relations
    r1 = Relation(id="r1", relation_type="WORKS_FOR", source_id="alice", target_id="tech_corp")
    r2 = Relation(id="r2", relation_type="WORKS_FOR", source_id="bob", target_id="tech_corp")
    r3 = Relation(id="r3", relation_type="KNOWS", source_id="alice", target_id="bob")
    
    await store.add_relation(r1)
    await store.add_relation(r2)
    await store.add_relation(r3)
    
    # Get all data
    entities = await store.get_all_entities()
    relations = await store.get_all_relations()
    
    # Create visualizer
    visualizer = GraphVisualizer()
    
    # Export to multiple formats
    # 1. DOT
    with open("graph.dot", "w") as f:
        f.write(visualizer.to_dot(entities, relations))
    
    # 2. D3.js JSON
    with open("graph_d3.json", "w") as f:
        json.dump(visualizer.to_json(entities, relations, format="d3"), f, indent=2)
    
    # 3. Cytoscape JSON
    with open("graph_cytoscape.json", "w") as f:
        json.dump(visualizer.to_json(entities, relations, format="cytoscape"), f, indent=2)
    
    # 4. Mermaid
    with open("graph.mmd", "w") as f:
        f.write(visualizer.to_mermaid(entities, relations))
    
    print("Visualizations created!")
    print("- graph.dot (render with: dot -Tpng graph.dot -o graph.png)")
    print("- graph_d3.json (use with D3.js)")
    print("- graph_cytoscape.json (use with Cytoscape.js)")
    print("- graph.mmd (render with: mmdc -i graph.mmd -o graph.png)")

# Run
asyncio.run(create_and_visualize())
```

## See Also

- [Graph Visualizer API](../API_REFERENCE.md#graph-visualizer)
- [Performance Guide](../PERFORMANCE_GUIDE.md)
- [Troubleshooting Guide](../TROUBLESHOOTING.md)

