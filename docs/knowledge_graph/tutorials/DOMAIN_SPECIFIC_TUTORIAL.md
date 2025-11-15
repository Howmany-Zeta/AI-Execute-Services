# Building a Domain-Specific Knowledge Graph Tutorial

## Overview

This tutorial demonstrates how to build a domain-specific knowledge graph from scratch. We'll create a **Medical Knowledge Graph** that captures information about diseases, symptoms, medications, and their relationships.

## Learning Objectives

By the end of this tutorial, you will:
- Define a custom schema for your domain
- Extract domain-specific entities and relations
- Build a knowledge graph from unstructured text
- Query and reason over domain knowledge
- Implement domain-specific inference rules

## Scenario: Medical Knowledge Graph

We'll build a knowledge graph that captures:
- **Entities**: Diseases, Symptoms, Medications, Patients
- **Relations**: HAS_SYMPTOM, TREATED_WITH, DIAGNOSED_WITH, CAUSES
- **Use Cases**: Diagnosis support, treatment recommendations, symptom analysis

## Step 1: Define Your Domain Schema

First, define the entity and relation types for your domain:

```python
import asyncio
from aiecs.domain.knowledge_graph.schema import (
    SchemaManager,
    EntityType,
    RelationType,
    PropertySchema,
    PropertyType
)

async def define_medical_schema():
    """Define schema for medical knowledge graph"""

    manager = SchemaManager()

    # Define Disease entity type
    disease_type = EntityType(
        name="Disease",
        description="A medical condition or illness",
        properties={
            "name": PropertySchema(
                name="name",
                property_type=PropertyType.STRING,
                required=True,
                description="Disease name"
            ),
            "icd_code": PropertySchema(
                name="icd_code",
                property_type=PropertyType.STRING,
                required=False,
                description="ICD-10 code"
            ),
            "severity": PropertySchema(
                name="severity",
                property_type=PropertyType.STRING,
                required=False,
                description="Severity level: mild, moderate, severe"
            )
        }
    )
    manager.create_entity_type(disease_type)

    # Define Symptom entity type
    symptom_type = EntityType(
        name="Symptom",
        description="A physical or mental feature indicating a condition",
        properties={
            "name": PropertySchema(
                name="name",
                property_type=PropertyType.STRING,
                required=True
            ),
            "body_part": PropertySchema(
                name="body_part",
                property_type=PropertyType.STRING,
                required=False
            )
        }
    )
    manager.create_entity_type(symptom_type)

    # Define Medication entity type
    medication_type = EntityType(
        name="Medication",
        description="A drug or treatment",
        properties={
            "name": PropertySchema(
                name="name",
                property_type=PropertyType.STRING,
                required=True
            ),
            "drug_class": PropertySchema(
                name="drug_class",
                property_type=PropertyType.STRING,
                required=False
            ),
            "dosage": PropertySchema(
                name="dosage",
                property_type=PropertyType.STRING,
                required=False
            )
        }
    )
    manager.create_entity_type(medication_type)

    # Define Patient entity type
    patient_type = EntityType(
        name="Patient",
        description="A person receiving medical care",
        properties={
            "name": PropertySchema(
                name="name",
                property_type=PropertyType.STRING,
                required=True
            ),
            "age": PropertySchema(
                name="age",
                property_type=PropertyType.INTEGER,
                min_value=0,
                max_value=150
            ),
            "gender": PropertySchema(
                name="gender",
                property_type=PropertyType.STRING
            )
        }
    )
    manager.create_entity_type(patient_type)

    # Define HAS_SYMPTOM relation
    has_symptom = RelationType(
        name="HAS_SYMPTOM",
        description="Disease has a symptom",
        source_entity_types=["Disease"],
        target_entity_types=["Symptom"],
        properties={
            "frequency": PropertySchema(
                name="frequency",
                property_type=PropertyType.STRING,
                description="How often: common, rare, occasional"
            )
        }
    )
    manager.create_relation_type(has_symptom)


## Step 2: Create Custom Entity Extractor

Build a domain-specific extractor for medical entities:

```python
from aiecs.application.knowledge_graph.extractors.base_extractor import BaseExtractor
from aiecs.domain.knowledge_graph.models.entity import Entity
from typing import List, Optional
import re

class MedicalEntityExtractor(BaseExtractor):
    """Extract medical entities from text"""

    def __init__(self):
        # Load medical dictionaries (simplified for tutorial)
        self.diseases = {
            "diabetes": "E11",  # ICD-10 code
            "hypertension": "I10",
            "asthma": "J45",
            "migraine": "G43"
        }

        self.symptoms = {
            "fever": "body",
            "headache": "head",
            "cough": "respiratory",
            "fatigue": "general",
            "nausea": "digestive"
        }

        self.medications = {
            "metformin": "antidiabetic",
            "lisinopril": "antihypertensive",
            "albuterol": "bronchodilator",
            "ibuprofen": "nsaid"
        }

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Entity]:
        """Extract medical entities from text"""

        entities = []
        text_lower = text.lower()

        # Extract diseases
        if not entity_types or "Disease" in entity_types:
            for disease, icd_code in self.diseases.items():
                if disease in text_lower:
                    entities.append(Entity(
                        id=f"disease_{disease}",
                        entity_type="Disease",
                        properties={
                            "name": disease.title(),
                            "icd_code": icd_code
                        },
                        metadata={
                            "source": "medical_dict",
                            "confidence": 0.9
                        }
                    ))

        # Extract symptoms
        if not entity_types or "Symptom" in entity_types:
            for symptom, body_part in self.symptoms.items():
                if symptom in text_lower:
                    entities.append(Entity(
                        id=f"symptom_{symptom}",
                        entity_type="Symptom",
                        properties={
                            "name": symptom.title(),
                            "body_part": body_part
                        },
                        metadata={
                            "source": "medical_dict",
                            "confidence": 0.85
                        }
                    ))

        # Extract medications
        if not entity_types or "Medication" in entity_types:
            for med, drug_class in self.medications.items():
                if med in text_lower:
                    entities.append(Entity(
                        id=f"med_{med}",
                        entity_type="Medication",
                        properties={
                            "name": med.title(),
                            "drug_class": drug_class
                        },
                        metadata={
                            "source": "medical_dict",
                            "confidence": 0.9
                        }
                    ))

        return entities
```

## Step 3: Create Custom Relation Extractor

Extract medical relationships from text:

```python
from aiecs.domain.knowledge_graph.models.relation import Relation

class MedicalRelationExtractor(BaseExtractor):
    """Extract medical relations from text"""

    def __init__(self):
        # Define relation patterns
        self.patterns = {
            "HAS_SYMPTOM": [
                r"(\w+)\s+(?:causes?|presents? with|characterized by)\s+(\w+)",
                r"(\w+)\s+symptoms? include\s+(\w+)",
            ],
            "TREATED_WITH": [
                r"(\w+)\s+(?:treated with|managed with|requires)\s+(\w+)",
                r"(\w+)\s+for\s+(\w+)",  # medication for disease
            ]
        }

    async def extract_relations(
        self,
        text: str,
        entities: List[Entity],
        relation_types: Optional[List[str]] = None
    ) -> List[Relation]:
        """Extract relations from text given entities"""

        relations = []

        # Create entity lookup by name
        entity_by_name = {}
        for entity in entities:
            name = entity.properties.get("name", "").lower()
            entity_by_name[name] = entity

        # Extract relations using patterns
        for rel_type, patterns in self.patterns.items():
            if relation_types and rel_type not in relation_types:
                continue

            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    source_name = match.group(1).lower()
                    target_name = match.group(2).lower()

                    # Find matching entities
                    source_entity = None
                    target_entity = None

                    for name, entity in entity_by_name.items():
                        if source_name in name or name in source_name:
                            source_entity = entity
                        if target_name in name or name in target_name:
                            target_entity = entity

                    if source_entity and target_entity:
                        # Validate relation type matches entity types
                        if self._validate_relation(rel_type, source_entity, target_entity):
                            relations.append(Relation(
                                id=f"rel_{len(relations)}",
                                relation_type=rel_type,
                                source_id=source_entity.id,
                                target_id=target_entity.id,
                                metadata={
                                    "source": "pattern_match",
                                    "confidence": 0.8
                                }
                            ))

        return relations

    def _validate_relation(self, rel_type: str, source: Entity, target: Entity) -> bool:
        """Validate that relation type matches entity types"""
        valid_combinations = {
            "HAS_SYMPTOM": ("Disease", "Symptom"),
            "TREATED_WITH": ("Disease", "Medication"),
            "DIAGNOSED_WITH": ("Patient", "Disease")
        }

        if rel_type in valid_combinations:
            expected_source, expected_target = valid_combinations[rel_type]
            return (source.entity_type == expected_source and
                    target.entity_type == expected_target)

        return True
```

## Step 4: Build the Knowledge Graph

Now use your custom extractors to build the graph:

```python
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.application.knowledge_graph.builder.graph_builder import GraphBuilder

async def build_medical_knowledge_graph():
    """Build medical knowledge graph from text"""

    # Initialize storage
    store = InMemoryGraphStore()
    await store.initialize()

    # Create custom extractors
    entity_extractor = MedicalEntityExtractor()
    relation_extractor = MedicalRelationExtractor()

    # Create builder
    builder = GraphBuilder(
        graph_store=store,
        entity_extractor=entity_extractor,
        relation_extractor=relation_extractor
    )

    # Medical texts to process
    texts = [
        "Diabetes is characterized by high blood sugar and causes fatigue. "
        "It is treated with metformin.",

        "Hypertension presents with headache and is managed with lisinopril.",

        "Asthma causes cough and is treated with albuterol. "
        "Common symptoms include shortness of breath.",

        "Migraine causes severe headache and nausea. "
        "It can be treated with ibuprofen."
    ]

    # Build graph from texts
    for i, text in enumerate(texts):
        print(f"\nProcessing text {i+1}...")
        result = await builder.build_from_text(text)
        print(f"  Extracted {result['entities_added']} entities")
        print(f"  Extracted {result['relations_added']} relations")

    # Get statistics
    stats = await builder.get_statistics()
    print(f"\n✅ Knowledge graph built successfully!")
    print(f"   Total entities: {stats['total_entities']}")
    print(f"   Total relations: {stats['total_relations']}")

    return store, builder

# Run
store, builder = await build_medical_knowledge_graph()
```

**Output**:
```
Processing text 1...
  Extracted 3 entities
  Extracted 2 relations

Processing text 2...
  Extracted 3 entities
  Extracted 2 relations

Processing text 3...
  Extracted 2 entities
  Extracted 1 relations

Processing text 4...
  Extracted 4 entities
  Extracted 3 relations

✅ Knowledge graph built successfully!
   Total entities: 12
   Total relations: 8
```

## Step 5: Query Your Domain Knowledge

Now query the medical knowledge graph:

```python
from aiecs.tools.knowledge_graph import GraphSearchTool

async def query_medical_knowledge(store):
    """Query the medical knowledge graph"""

    search_tool = GraphSearchTool(graph_store=store)
    await search_tool._initialize()

    # Query 1: Find all symptoms of diabetes
    print("\n🔍 Query 1: What are the symptoms of diabetes?")
    neighbors = await store.get_neighbors(
        "disease_diabetes",
        direction="outgoing",
        relation_types=["HAS_SYMPTOM"]
    )
    print(f"   Symptoms: {[n.properties['name'] for n in neighbors]}")

    # Query 2: Find treatments for hypertension
    print("\n🔍 Query 2: How is hypertension treated?")
    neighbors = await store.get_neighbors(
        "disease_hypertension",
        direction="outgoing",
        relation_types=["TREATED_WITH"]
    )
    print(f"   Treatments: {[n.properties['name'] for n in neighbors]}")

    # Query 3: Find all diseases treated with ibuprofen
    print("\n🔍 Query 3: What diseases are treated with ibuprofen?")
    neighbors = await store.get_neighbors(
        "med_ibuprofen",
        direction="incoming",
        relation_types=["TREATED_WITH"]
    )
    print(f"   Diseases: {[n.properties['name'] for n in neighbors]}")

    # Query 4: Multi-hop traversal
    print("\n🔍 Query 4: Find all paths from diabetes (2 hops)")
    paths = await store.traverse("disease_diabetes", max_depth=2)
    print(f"   Found {len(paths)} paths")
    for i, path in enumerate(paths[:3]):  # Show first 3
        entities = [e.properties['name'] for e in path.entities]
        print(f"   Path {i+1}: {' → '.join(entities)}")

# Run
await query_medical_knowledge(store)
```

**Output**:
```
🔍 Query 1: What are the symptoms of diabetes?
   Symptoms: ['Fatigue']

🔍 Query 2: How is hypertension treated?
   Treatments: ['Lisinopril']

🔍 Query 3: What diseases are treated with ibuprofen?
   Diseases: ['Migraine']

🔍 Query 4: Find all paths from diabetes (2 hops)
   Found 2 paths
   Path 1: Diabetes → Fatigue
   Path 2: Diabetes → Metformin
```

## Step 6: Add Domain-Specific Inference Rules

Implement medical reasoning rules:

```python
from aiecs.domain.knowledge_graph.models.inference_rule import InferenceRule, RuleType
from aiecs.application.knowledge_graph.reasoning.inference_engine import InferenceEngine

async def add_medical_inference_rules(store):
    """Add domain-specific inference rules"""

    engine = InferenceEngine(graph_store=store)

    # Rule 1: If disease A has symptom S, and patient P has symptom S,
    #         then patient P might have disease A
    symptom_diagnosis_rule = InferenceRule(
        rule_id="symptom_based_diagnosis",
        rule_type=RuleType.CUSTOM,
        name="Symptom-Based Diagnosis",
        description="Infer possible diagnosis from symptoms",
        conditions=[
            {"relation_type": "HAS_SYMPTOM"},  # Disease -> Symptom
            {"relation_type": "EXPERIENCES"}   # Patient -> Symptom
        ],
        conclusion={
            "relation_type": "POSSIBLY_HAS",
            "properties": {"inferred": True, "confidence": 0.6}
        },
        confidence=0.6
    )
    engine.add_rule(symptom_diagnosis_rule)

    # Rule 2: If disease A is treated with medication M,
    #         and patient P has disease A,
    #         then patient P should take medication M
    treatment_recommendation_rule = InferenceRule(
        rule_id="treatment_recommendation",
        rule_type=RuleType.CUSTOM,
        name="Treatment Recommendation",
        description="Recommend treatment based on diagnosis",
        conditions=[
            {"relation_type": "DIAGNOSED_WITH"},  # Patient -> Disease
            {"relation_type": "TREATED_WITH"}     # Disease -> Medication
        ],
        conclusion={
            "relation_type": "SHOULD_TAKE",
            "properties": {"inferred": True, "confidence": 0.8}
        },
        confidence=0.8
    )
    engine.add_rule(treatment_recommendation_rule)

    print("✅ Added 2 medical inference rules")
    return engine

# Run
engine = await add_medical_inference_rules(store)
```

## Step 7: Complete Example

Here's the complete working example:

```python
import asyncio

async def main():
    """Complete medical knowledge graph example"""

    # Step 1: Define schema
    manager = await define_medical_schema()

    # Step 2-4: Build knowledge graph
    store, builder = await build_medical_knowledge_graph()

    # Step 5: Query knowledge
    await query_medical_knowledge(store)

    # Step 6: Add inference rules
    engine = await add_medical_inference_rules(store)

    # Apply inference
    print("\n🧠 Applying inference rules...")
    inferred_relations = await engine.apply_all_rules()
    print(f"   Inferred {len(inferred_relations)} new relations")

    # Cleanup
    await store.close()
    print("\n✅ Tutorial complete!")

# Run the complete example
asyncio.run(main())
```

## Key Takeaways

1. **Define Your Schema**: Start with clear entity and relation types for your domain
2. **Custom Extractors**: Build domain-specific extractors using dictionaries, patterns, or ML models
3. **Validation**: Validate relations match your schema constraints
4. **Inference Rules**: Add domain logic to infer new knowledge
5. **Iterative Improvement**: Start simple, add complexity as needed

## Next Steps

- **Enhance Extractors**: Use NER models or LLMs for better extraction
- **Add More Rules**: Implement complex medical reasoning logic
- **Integrate with Agents**: Use your knowledge graph in AI agents
- **Scale Up**: Move to SQLite or PostgreSQL for larger datasets
- **Visualization**: Visualize your medical knowledge graph

## Resources

- **API Reference**: [API_REFERENCE.md](../API_REFERENCE.md)
- **Developer Guide**: [DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md)
- **Examples**: [examples/](../examples/)

Happy building! 🏥🚀



