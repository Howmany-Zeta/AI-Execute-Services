"""
Example: Evidence-Based Reasoning

Demonstrates how to use evidence synthesis for robust reasoning with
multiple sources, confidence estimation, and contradiction detection.
"""

import asyncio
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.evidence import Evidence, EvidenceType
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.application.knowledge_graph.reasoning import (
    ReasoningEngine,
    EvidenceSynthesizer
)
from aiecs.tools.knowledge_graph import GraphReasoningTool
from aiecs.tools.knowledge_graph.graph_reasoning_tool import GraphReasoningInput


async def build_business_network():
    """Build a business network with multiple information sources"""
    graph = InMemoryGraphStore()
    await graph.initialize()
    
    # Companies
    tech_corp = Entity(id="tech_corp", entity_type="Company", properties={"name": "TechCorp", "reliability": "high"})
    data_inc = Entity(id="data_inc", entity_type="Company", properties={"name": "DataInc", "reliability": "high"})
    startup_x = Entity(id="startup_x", entity_type="Company", properties={"name": "StartupX", "reliability": "medium"})
    
    # People
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice", "role": "CEO"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob", "role": "CTO"})
    charlie = Entity(id="charlie", entity_type="Person", properties={"name": "Charlie", "role": "Engineer"})
    
    for entity in [tech_corp, data_inc, startup_x, alice, bob, charlie]:
        await graph.add_entity(entity)
    
    # Relations - from different sources/confidence levels
    relations = [
        ("alice", "tech_corp", "WORKS_FOR"),
        ("bob", "tech_corp", "WORKS_FOR"),
        ("charlie", "startup_x", "WORKS_FOR"),
        ("alice", "bob", "KNOWS"),
        ("bob", "charlie", "KNOWS"),
        ("tech_corp", "data_inc", "PARTNERS_WITH"),
    ]
    
    for i, (source, target, rel_type) in enumerate(relations, 1):
        await graph.add_relation(Relation(
            id=f"rel_{i}",
            source_id=source,
            target_id=target,
            relation_type=rel_type,
            properties={}
        ))
    
    return graph


async def example_1_collecting_evidence():
    """Example 1: Collecting evidence from multiple sources"""
    print("=" * 80)
    print("Example 1: Collecting Evidence from Multiple Sources")
    print("=" * 80)
    
    graph = await build_business_network()
    engine = ReasoningEngine(graph)
    
    # Ask a question that requires collecting evidence
    query = "What companies is Alice connected to?"
    print(f"\nQuery: {query}")
    print("-" * 80)
    
    result = await engine.reason(
        query=query,
        context={"start_entity_id": "alice"},
        max_hops=3,
        max_evidence=20
    )
    
    print(f"\nCollected {result.evidence_count} pieces of evidence:")
    for i, ev in enumerate(result.evidence[:5], 1):
        print(f"\n{i}. Evidence ID: {ev.evidence_id}")
        print(f"   Type: {ev.evidence_type.value}")
        print(f"   Confidence: {ev.confidence:.2f}")
        print(f"   Relevance: {ev.relevance_score:.2f}")
        print(f"   Source: {ev.source}")
        print(f"   Explanation: {ev.explanation}")
    
    print(f"\nAnswer: {result.answer}")
    print(f"Overall confidence: {result.confidence:.2f}")
    
    await graph.close()


async def example_2_evidence_synthesis():
    """Example 2: Synthesizing evidence from overlapping sources"""
    print("\n\n" + "=" * 80)
    print("Example 2: Evidence Synthesis")
    print("=" * 80)
    
    # Create multiple evidence pieces about the same entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    
    evidence_list = [
        Evidence(
            evidence_id="ev1",
            evidence_type=EvidenceType.PATH,
            entities=[alice, bob],
            confidence=0.8,
            relevance_score=0.7,
            explanation="Alice and Bob work at the same company (from HR records)",
            source="hr_database"
        ),
        Evidence(
            evidence_id="ev2",
            evidence_type=EvidenceType.PATH,
            entities=[alice, bob],
            confidence=0.9,
            relevance_score=0.8,
            explanation="Alice and Bob are colleagues (from org chart)",
            source="org_chart"
        ),
        Evidence(
            evidence_id="ev3",
            evidence_type=EvidenceType.PATH,
            entities=[alice, bob],
            confidence=0.85,
            relevance_score=0.75,
            explanation="Alice and Bob collaborate frequently (from email data)",
            source="email_analysis"
        ),
    ]
    
    print("\nOriginal evidence (3 sources about same entities):")
    for ev in evidence_list:
        print(f"  - {ev.source}: confidence={ev.confidence:.2f}")
    
    # Synthesize evidence
    synthesizer = EvidenceSynthesizer()
    synthesized = synthesizer.synthesize_evidence(
        evidence_list,
        method="weighted_average"
    )
    
    print(f"\nSynthesized to {len(synthesized)} piece(s):")
    for ev in synthesized:
        print(f"\n  Evidence ID: {ev.evidence_id}")
        print(f"  Confidence: {ev.confidence:.3f} (boosted by agreement)")
        print(f"  Source: {ev.source}")
        print(f"  Combined from: {ev.metadata['source_count']} sources")
        print(f"  Original sources: {', '.join(ev.metadata['source_evidence_ids'])}")


async def example_3_confidence_estimation():
    """Example 3: Estimating overall confidence from evidence"""
    print("\n\n" + "=" * 80)
    print("Example 3: Overall Confidence Estimation")
    print("=" * 80)
    
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    charlie = Entity(id="charlie", entity_type="Person", properties={"name": "Charlie"})
    
    # Evidence from multiple diverse sources
    evidence_list = [
        Evidence(
            evidence_id="ev1",
            evidence_type=EvidenceType.ENTITY,
            entities=[alice],
            confidence=0.9,
            relevance_score=0.85,
            explanation="Evidence about Alice",
            source="database_a"
        ),
        Evidence(
            evidence_id="ev2",
            evidence_type=EvidenceType.ENTITY,
            entities=[bob],
            confidence=0.85,
            relevance_score=0.8,
            explanation="Evidence about Bob",
            source="database_b"
        ),
        Evidence(
            evidence_id="ev3",
            evidence_type=EvidenceType.ENTITY,
            entities=[charlie],
            confidence=0.88,
            relevance_score=0.82,
            explanation="Evidence about Charlie",
            source="database_c"
        ),
        Evidence(
            evidence_id="ev4",
            evidence_type=EvidenceType.PATH,
            entities=[alice, bob],
            confidence=0.92,
            relevance_score=0.9,
            explanation="Evidence about Alice and Bob",
            source="graph_analysis"
        ),
    ]
    
    synthesizer = EvidenceSynthesizer()
    
    print("\nEvidence from 4 different sources:")
    for ev in evidence_list:
        print(f"  - {ev.source}: confidence={ev.confidence:.2f}")
    
    # Estimate overall confidence
    overall = synthesizer.estimate_overall_confidence(evidence_list)
    
    print(f"\nOverall confidence: {overall:.3f}")
    print("\nFactors contributing to high confidence:")
    print("  - Base confidence: High individual scores")
    print("  - Source diversity: 4 different sources")
    print("  - Entity agreement: Entities appear in multiple evidence")


async def example_4_filtering_evidence():
    """Example 4: Filtering evidence by confidence threshold"""
    print("\n\n" + "=" * 80)
    print("Example 4: Filtering Evidence by Confidence")
    print("=" * 80)
    
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    
    # Evidence with varying confidence levels
    evidence_list = [
        Evidence(
            evidence_id="ev1",
            evidence_type=EvidenceType.ENTITY,
            entities=[alice],
            confidence=0.95,
            relevance_score=0.9,
            explanation="High confidence evidence",
            source="verified_source"
        ),
        Evidence(
            evidence_id="ev2",
            evidence_type=EvidenceType.ENTITY,
            entities=[alice],
            confidence=0.75,
            relevance_score=0.7,
            explanation="Medium confidence evidence",
            source="secondary_source"
        ),
        Evidence(
            evidence_id="ev3",
            evidence_type=EvidenceType.ENTITY,
            entities=[alice],
            confidence=0.45,
            relevance_score=0.5,
            explanation="Low confidence evidence",
            source="unverified_source"
        ),
        Evidence(
            evidence_id="ev4",
            evidence_type=EvidenceType.ENTITY,
            entities=[alice],
            confidence=0.85,
            relevance_score=0.8,
            explanation="Good confidence evidence",
            source="reliable_source"
        ),
    ]
    
    print("\nAll evidence:")
    for ev in evidence_list:
        print(f"  - {ev.evidence_id}: confidence={ev.confidence:.2f}")
    
    synthesizer = EvidenceSynthesizer(confidence_threshold=0.7)
    
    # Filter by threshold
    filtered = synthesizer.filter_by_confidence(evidence_list, threshold=0.7)
    
    print(f"\nFiltered evidence (confidence ≥ 0.7):")
    for ev in filtered:
        print(f"  - {ev.evidence_id}: confidence={ev.confidence:.2f} ✓")
    
    print(f"\nRetained {len(filtered)}/{len(evidence_list)} pieces of evidence")


async def example_5_contradiction_detection():
    """Example 5: Detecting contradictions in evidence"""
    print("\n\n" + "=" * 80)
    print("Example 5: Contradiction Detection")
    print("=" * 80)
    
    tech_corp = Entity(id="tech_corp", entity_type="Company", properties={"name": "TechCorp"})
    
    # Contradictory evidence about the same entity
    evidence_list = [
        Evidence(
            evidence_id="ev_high",
            evidence_type=EvidenceType.ENTITY,
            entities=[tech_corp],
            confidence=0.95,
            relevance_score=0.9,
            explanation="TechCorp is highly profitable (verified financial reports)",
            source="official_financial_data"
        ),
        Evidence(
            evidence_id="ev_low",
            evidence_type=EvidenceType.ENTITY,
            entities=[tech_corp],
            confidence=0.3,
            relevance_score=0.8,
            explanation="TechCorp is struggling financially (unverified rumors)",
            source="social_media"
        ),
    ]
    
    print("\nEvidence about TechCorp:")
    for ev in evidence_list:
        print(f"  - {ev.source}:")
        print(f"    Confidence: {ev.confidence:.2f}")
        print(f"    Claim: {ev.explanation}")
    
    synthesizer = EvidenceSynthesizer(contradiction_threshold=0.3)
    
    # Detect contradictions
    contradictions = synthesizer.detect_contradictions(evidence_list)
    
    if contradictions:
        print(f"\n⚠️  {len(contradictions)} contradiction(s) detected:")
        for contra in contradictions:
            print(f"\n  Entity: {contra['entity_id']}")
            print(f"  Confidence range: {contra['confidence_range']}")
            print(f"  Conflicting evidence: {contra['evidence_ids']}")
            print(f"  Description: {contra['description']}")
            print("\n  Recommendation: Review sources and resolve conflict")
    else:
        print("\n✓ No contradictions detected")


async def example_6_reliability_ranking():
    """Example 6: Ranking evidence by reliability"""
    print("\n\n" + "=" * 80)
    print("Example 6: Ranking Evidence by Reliability")
    print("=" * 80)
    
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    charlie = Entity(id="charlie", entity_type="Person", properties={"name": "Charlie"})
    
    evidence_list = [
        Evidence(
            evidence_id="ev1",
            evidence_type=EvidenceType.PATH,
            entities=[alice, bob, charlie],
            relations=[],
            confidence=0.95,
            relevance_score=0.9,
            explanation="Multi-hop path with high confidence",
            source="graph_analysis"
        ),
        Evidence(
            evidence_id="ev2",
            evidence_type=EvidenceType.ENTITY,
            entities=[alice],
            confidence=0.7,
            relevance_score=0.6,
            explanation="Single entity, lower confidence",
            source="weak_source"
        ),
        Evidence(
            evidence_id="ev3",
            evidence_type=EvidenceType.PATH,
            entities=[alice, bob],
            confidence=0.85,
            relevance_score=0.8,
            explanation="Synthesized from multiple sources",
            source="synthesis",
            metadata={"source_count": 3}
        ),
        Evidence(
            evidence_id="ev4",
            evidence_type=EvidenceType.RELATION,
            entities=[],
            confidence=0.8,
            relevance_score=0.75,
            explanation="Single relation evidence",
            source="database"
        ),
    ]
    
    print("\nEvidence before ranking:")
    for i, ev in enumerate(evidence_list, 1):
        reliability = (ev.confidence * 0.6) + (ev.relevance_score * 0.4)
        print(f"{i}. {ev.evidence_id}: reliability={reliability:.2f}")
    
    synthesizer = EvidenceSynthesizer()
    ranked = synthesizer.rank_by_reliability(evidence_list)
    
    print("\nEvidence after ranking (most reliable first):")
    for i, ev in enumerate(ranked, 1):
        reliability = (ev.confidence * 0.6) + (ev.relevance_score * 0.4)
        boosts = []
        if ev.source == "synthesis":
            boosts.append("+10% synthesis")
        if len(ev.entities) > 2:
            boosts.append("+5% multi-element")
        boost_str = f" ({', '.join(boosts)})" if boosts else ""
        print(f"{i}. {ev.evidence_id}: reliability={reliability:.2f}{boost_str}")


async def example_7_full_evidence_workflow():
    """Example 7: Complete evidence-based reasoning workflow"""
    print("\n\n" + "=" * 80)
    print("Example 7: Complete Evidence-Based Reasoning Workflow")
    print("=" * 80)
    
    graph = await build_business_network()
    tool = GraphReasoningTool(graph)
    
    # Use full reasoning with evidence synthesis
    print("\nQuery: How is Alice connected to other companies?")
    print("-" * 80)
    
    input_data = GraphReasoningInput(
        mode="full_reasoning",
        query="How is Alice connected to other companies?",
        start_entity_id="alice",
        max_hops=4,
        apply_inference=False,
        synthesize_evidence=True,
        synthesis_method="weighted_average",
        confidence_threshold=0.6,
        optimization_strategy="balanced"
    )
    
    result = await tool._execute(input_data)
    
    print("\nReasoning workflow steps:")
    for step in result['steps']:
        print(f"  {step['name']}:")
        if 'evidence_collected' in step:
            print(f"    - Evidence collected: {step['evidence_collected']}")
        if 'evidence_count' in step:
            print(f"    - Evidence count: {step['evidence_count']}")
        if 'original_evidence' in step:
            print(f"    - Original evidence: {step['original_evidence']}")
            print(f"    - Synthesized to: {step['synthesized_evidence']}")
            print(f"    - After filtering: {step['filtered_evidence']}")
            print(f"    - Overall confidence: {step['overall_confidence']:.3f}")
    
    print(f"\nFinal Answer: {result['answer']}")
    print(f"Final Confidence: {result['final_confidence']:.3f}")
    
    print("\nTop Evidence:")
    for i, ev in enumerate(result['top_evidence'], 1):
        print(f"{i}. {ev['explanation']}")
        print(f"   Confidence: {ev['confidence']:.2f}, Relevance: {ev['relevance_score']:.2f}")
    
    await graph.close()


async def main():
    """Run all examples"""
    await example_1_collecting_evidence()
    await example_2_evidence_synthesis()
    await example_3_confidence_estimation()
    await example_4_filtering_evidence()
    await example_5_contradiction_detection()
    await example_6_reliability_ranking()
    await example_7_full_evidence_workflow()
    
    print("\n\n" + "=" * 80)
    print("All Evidence-Based Reasoning Examples Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

