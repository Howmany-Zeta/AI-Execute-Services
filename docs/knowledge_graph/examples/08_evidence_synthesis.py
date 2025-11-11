"""
Example: Evidence Synthesis and Confidence Estimation

Demonstrates how to combine evidence from multiple sources,
estimate confidence, detect contradictions, and rank by reliability.
"""

import asyncio
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.evidence import Evidence, EvidenceType
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.application.knowledge_graph.reasoning.evidence_synthesis import EvidenceSynthesizer


async def main():
    print("=" * 70)
    print("Evidence Synthesis and Confidence Estimation")
    print("=" * 70)
    
    # Create some entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    company = Entity(id="company_x", entity_type="Company", properties={"name": "Company X"})
    
    # Create relations
    knows = Relation(
        id="rel1",
        source_id="alice",
        target_id="bob",
        relation_type="KNOWS",
        properties={}
    )
    works_at = Relation(
        id="rel2",
        source_id="bob",
        target_id="company_x",
        relation_type="WORKS_AT",
        properties={}
    )
    
    # ========================================================================
    # Example 1: Basic Evidence Synthesis
    # ========================================================================
    print("\n1. Basic Evidence Synthesis")
    print("-" * 70)
    
    # Evidence from different sources about same entities
    ev1 = Evidence(
        evidence_id="ev1",
        evidence_type=EvidenceType.PATH,
        entities=[alice, bob],
        relations=[knows],
        confidence=0.8,
        relevance_score=0.7,
        explanation="Alice knows Bob (from vector search)",
        source="vector_search"
    )
    
    ev2 = Evidence(
        evidence_id="ev2",
        evidence_type=EvidenceType.PATH,
        entities=[alice, bob],
        relations=[knows],
        confidence=0.9,
        relevance_score=0.8,
        explanation="Alice knows Bob (from graph traversal)",
        source="graph_traversal"
    )
    
    ev3 = Evidence(
        evidence_id="ev3",
        evidence_type=EvidenceType.PATH,
        entities=[alice, bob],
        relations=[knows],
        confidence=0.85,
        relevance_score=0.75,
        explanation="Alice knows Bob (from inference)",
        source="inference"
    )
    
    synthesizer = EvidenceSynthesizer(
        confidence_threshold=0.7,
        contradiction_threshold=0.3
    )
    
    evidence_list = [ev1, ev2, ev3]
    
    print(f"Original evidence count: {len(evidence_list)}")
    for ev in evidence_list:
        print(f"  - {ev.evidence_id}: confidence={ev.confidence:.2f}, source={ev.source}")
    
    # Synthesize overlapping evidence
    synthesized = synthesizer.synthesize_evidence(evidence_list, method="weighted_average")
    
    print(f"\nSynthesized evidence count: {len(synthesized)}")
    for ev in synthesized:
        print(f"  - {ev.evidence_id}: confidence={ev.confidence:.2f}, source={ev.source}")
        if ev.source == "synthesis":
            print(f"    Combined from {ev.metadata['source_count']} sources")
            print(f"    Confidence boost from agreement!")
    
    # ========================================================================
    # Example 2: Confidence Estimation
    # ========================================================================
    print("\n2. Overall Confidence Estimation")
    print("-" * 70)
    
    overall_confidence = synthesizer.estimate_overall_confidence(evidence_list)
    print(f"Overall confidence: {overall_confidence:.3f}")
    print(f"  - Base confidence (average): {sum(ev.confidence for ev in evidence_list) / len(evidence_list):.3f}")
    print(f"  - Source diversity bonus: Multiple sources increase confidence")
    print(f"  - Agreement bonus: Entity overlap across evidence")
    
    # ========================================================================
    # Example 3: Filtering by Confidence
    # ========================================================================
    print("\n3. Filtering by Confidence Threshold")
    print("-" * 70)
    
    # Add some low confidence evidence
    ev_low = Evidence(
        evidence_id="ev_low",
        evidence_type=EvidenceType.ENTITY,
        entities=[alice],
        confidence=0.4,
        relevance_score=0.5,
        explanation="Low confidence evidence",
        source="weak_source"
    )
    
    all_evidence = evidence_list + [ev_low]
    
    print(f"All evidence: {len(all_evidence)}")
    for ev in all_evidence:
        print(f"  - {ev.evidence_id}: confidence={ev.confidence:.2f}")
    
    # Filter by threshold
    high_confidence = synthesizer.filter_by_confidence(all_evidence, threshold=0.7)
    print(f"\nHigh confidence evidence (≥0.7): {len(high_confidence)}")
    for ev in high_confidence:
        print(f"  - {ev.evidence_id}: confidence={ev.confidence:.2f} ✓")
    
    # ========================================================================
    # Example 4: Contradiction Detection
    # ========================================================================
    print("\n4. Contradiction Detection")
    print("-" * 70)
    
    # Create contradictory evidence
    ev_high = Evidence(
        evidence_id="ev_high",
        evidence_type=EvidenceType.ENTITY,
        entities=[company],
        confidence=0.95,
        relevance_score=0.9,
        explanation="Company X is highly reliable",
        source="official_data"
    )
    
    ev_contra = Evidence(
        evidence_id="ev_contra",
        evidence_type=EvidenceType.ENTITY,
        entities=[company],
        confidence=0.3,
        relevance_score=0.8,
        explanation="Company X data is questionable",
        source="unverified_source"
    )
    
    contradictory_evidence = [ev_high, ev_contra]
    
    print("Evidence about Company X:")
    for ev in contradictory_evidence:
        print(f"  - {ev.evidence_id}: confidence={ev.confidence:.2f}, source={ev.source}")
    
    contradictions = synthesizer.detect_contradictions(contradictory_evidence)
    
    if contradictions:
        print(f"\n⚠️  {len(contradictions)} contradiction(s) detected:")
        for contra in contradictions:
            print(f"  Entity: {contra['entity_id']}")
            print(f"  Confidence range: {contra['confidence_range']}")
            print(f"  Evidence: {contra['evidence_ids']}")
            print(f"  Description: {contra['description']}")
    else:
        print("\n✓ No contradictions detected")
    
    # ========================================================================
    # Example 5: Ranking by Reliability
    # ========================================================================
    print("\n5. Ranking by Reliability")
    print("-" * 70)
    
    # Create diverse evidence
    diverse_evidence = [
        Evidence(
            evidence_id="ev_reliable",
            evidence_type=EvidenceType.PATH,
            entities=[alice, bob, company],
            relations=[knows, works_at],
            confidence=0.95,
            relevance_score=0.9,
            explanation="High quality multi-hop path",
            source="graph_traversal"
        ),
        Evidence(
            evidence_id="ev_medium",
            evidence_type=EvidenceType.RELATION,
            relations=[knows],
            confidence=0.75,
            relevance_score=0.7,
            explanation="Medium quality single relation",
            source="inference"
        ),
        Evidence(
            evidence_id="ev_synth",
            evidence_type=EvidenceType.ENTITY,
            entities=[alice],
            confidence=0.85,
            relevance_score=0.8,
            explanation="Synthesized from multiple sources",
            source="synthesis",
            metadata={"source_count": 3}
        ),
        Evidence(
            evidence_id="ev_low",
            evidence_type=EvidenceType.ENTITY,
            entities=[bob],
            confidence=0.6,
            relevance_score=0.5,
            explanation="Low quality entity match",
            source="weak_match"
        )
    ]
    
    print("Evidence before ranking:")
    for i, ev in enumerate(diverse_evidence, 1):
        reliability = (ev.confidence * 0.6) + (ev.relevance_score * 0.4)
        print(f"{i}. {ev.evidence_id}: reliability={reliability:.2f} (C={ev.confidence:.2f}, R={ev.relevance_score:.2f})")
    
    ranked = synthesizer.rank_by_reliability(diverse_evidence)
    
    print("\nEvidence after ranking (most reliable first):")
    for i, ev in enumerate(ranked, 1):
        reliability = (ev.confidence * 0.6) + (ev.relevance_score * 0.4)
        boost = ""
        if ev.source == "synthesis":
            boost = " [+10% synthesis boost]"
        if len(ev.entities) + len(ev.relations) > 3:
            boost += " [+5% multi-element boost]"
        print(f"{i}. {ev.evidence_id}: reliability={reliability:.2f}{boost}")
    
    # ========================================================================
    # Example 6: Different Synthesis Methods
    # ========================================================================
    print("\n6. Different Synthesis Methods")
    print("-" * 70)
    
    test_evidence = [
        Evidence(
            evidence_id="ev_a",
            evidence_type=EvidenceType.ENTITY,
            entities=[alice],
            confidence=0.7,
            relevance_score=0.6,
            explanation="Evidence A"
        ),
        Evidence(
            evidence_id="ev_b",
            evidence_type=EvidenceType.ENTITY,
            entities=[alice],
            confidence=0.9,
            relevance_score=0.8,
            explanation="Evidence B"
        ),
        Evidence(
            evidence_id="ev_c",
            evidence_type=EvidenceType.ENTITY,
            entities=[alice],
            confidence=0.8,
            relevance_score=0.7,
            explanation="Evidence C"
        )
    ]
    
    print("Original evidence:")
    for ev in test_evidence:
        print(f"  - {ev.evidence_id}: C={ev.confidence:.2f}, R={ev.relevance_score:.2f}")
    
    # Try different methods
    methods = ["weighted_average", "max", "voting"]
    
    for method in methods:
        synthesized = synthesizer.synthesize_evidence(test_evidence, method=method)
        combined = synthesized[0]
        print(f"\n{method.upper()} method:")
        print(f"  Confidence: {combined.confidence:.3f}")
        print(f"  Relevance: {combined.relevance_score:.3f}")
        print(f"  Method: {combined.metadata['synthesis_method']}")
    
    # ========================================================================
    # Example 7: Complete Workflow
    # ========================================================================
    print("\n7. Complete Evidence Synthesis Workflow")
    print("-" * 70)
    
    print("\nStep 1: Collect evidence from multiple sources")
    workflow_evidence = [ev1, ev2, ev3, ev_low]
    print(f"  Collected {len(workflow_evidence)} pieces of evidence")
    
    print("\nStep 2: Filter by confidence threshold")
    filtered = synthesizer.filter_by_confidence(workflow_evidence, threshold=0.7)
    print(f"  Retained {len(filtered)} high-confidence pieces")
    
    print("\nStep 3: Synthesize overlapping evidence")
    synthesized = synthesizer.synthesize_evidence(filtered, method="weighted_average")
    print(f"  Synthesized to {len(synthesized)} pieces")
    
    print("\nStep 4: Detect contradictions")
    contradictions = synthesizer.detect_contradictions(synthesized)
    print(f"  Found {len(contradictions)} contradictions")
    
    print("\nStep 5: Rank by reliability")
    ranked = synthesizer.rank_by_reliability(synthesized)
    print(f"  Ranked {len(ranked)} pieces by reliability")
    
    print("\nStep 6: Estimate overall confidence")
    overall = synthesizer.estimate_overall_confidence(ranked)
    print(f"  Overall confidence: {overall:.3f}")
    
    print("\nFinal result:")
    print(f"  Most reliable evidence: {ranked[0].evidence_id}")
    print(f"  Confidence: {ranked[0].confidence:.3f}")
    print(f"  Explanation: {ranked[0].explanation}")
    
    print("\n" + "=" * 70)
    print("Evidence Synthesis Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

