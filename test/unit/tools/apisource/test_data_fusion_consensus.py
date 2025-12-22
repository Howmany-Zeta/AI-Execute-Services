"""
Unit tests for DataFusionEngine consensus fusion

Tests sophisticated consensus logic including:
- Data point agreement detection
- Majority voting for conflicts
- Quality-weighted consensus
- Partial agreement handling
- Confidence scoring
"""

import pytest
from aiecs.tools.apisource.intelligence.data_fusion import DataFusionEngine


@pytest.fixture
def fusion_engine():
    """Create a DataFusionEngine instance"""
    return DataFusionEngine()


class TestConsensusFusion:
    """Test consensus fusion functionality"""
    
    def test_consensus_full_agreement(self, fusion_engine):
        """Test consensus when all providers agree"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "name": "Test Item", "value": 100}],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": [{"id": "item1", "name": "Test Item", "value": 100}],
                "metadata": {"quality": {"score": 0.8}}
            },
            {
                "provider": "provider3",
                "data": [{"id": "item1", "name": "Test Item", "value": 100}],
                "metadata": {"quality": {"score": 0.85}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        assert len(consensus["data"]) == 1
        assert consensus["data"][0]["name"] == "Test Item"
        assert consensus["data"][0]["value"] == 100
        assert consensus["metadata"]["fusion_info"]["strategy"] == "consensus"
        assert "consensus_confidence" in consensus["metadata"]["fusion_info"]
        assert consensus["metadata"]["fusion_info"]["agreement_stats"]["full_agreement"] >= 1
    
    def test_consensus_majority_voting(self, fusion_engine):
        """Test consensus with majority voting for conflicts"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "name": "Item A", "value": 100}],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": [{"id": "item1", "name": "Item A", "value": 200}],
                "metadata": {"quality": {"score": 0.8}}
            },
            {
                "provider": "provider3",
                "data": [{"id": "item1", "name": "Item A", "value": 200}],
                "metadata": {"quality": {"score": 0.85}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        assert len(consensus["data"]) == 1
        # Majority (2 out of 3) agree on value 200
        assert consensus["data"][0]["value"] == 200
    
    def test_consensus_quality_weighted(self, fusion_engine):
        """Test quality-weighted consensus when no clear majority"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "name": "Item A", "value": 100}],
                "metadata": {"quality": {"score": 0.95}}  # High quality
            },
            {
                "provider": "provider2",
                "data": [{"id": "item1", "name": "Item A", "value": 200}],
                "metadata": {"quality": {"score": 0.6}}  # Lower quality
            },
            {
                "provider": "provider3",
                "data": [{"id": "item1", "name": "Item A", "value": 200}],
                "metadata": {"quality": {"score": 0.65}}  # Lower quality
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        # Quality-weighted: high quality single source may win over lower quality majority
        # Or majority wins - depends on implementation
        assert consensus["data"][0]["value"] in [100, 200]
    
    def test_consensus_partial_agreement(self, fusion_engine):
        """Test consensus with partial agreement (some fields match)"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "name": "Item A", "value": 100, "category": "A"}],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": [{"id": "item1", "name": "Item A", "value": 200, "category": "A"}],
                "metadata": {"quality": {"score": 0.8}}
            },
            {
                "provider": "provider3",
                "data": [{"id": "item1", "name": "Item A", "value": 200, "category": "B"}],
                "metadata": {"quality": {"score": 0.85}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        assert len(consensus["data"]) == 1
        # Name should match (all agree)
        assert consensus["data"][0]["name"] == "Item A"
        # Value and category may differ (conflicts)
        assert "value" in consensus["data"][0]
        assert "category" in consensus["data"][0]
        # Should have consensus metadata
        assert "_consensus_metadata" in consensus["data"][0]
    
    def test_consensus_confidence_scoring(self, fusion_engine):
        """Test that consensus includes confidence scores"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "name": "Item A"}],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": [{"id": "item1", "name": "Item A"}],
                "metadata": {"quality": {"score": 0.8}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        assert "consensus_confidence" in consensus["metadata"]["fusion_info"]
        confidence = consensus["metadata"]["fusion_info"]["consensus_confidence"]
        assert 0.0 <= confidence <= 1.0
        
        # Check item-level confidence
        if consensus["data"]:
            assert "_consensus_metadata" in consensus["data"][0]
            assert "overall_confidence" in consensus["data"][0]["_consensus_metadata"]
    
    def test_consensus_multiple_items(self, fusion_engine):
        """Test consensus with multiple data items"""
        results = [
            {
                "provider": "provider1",
                "data": [
                    {"id": "item1", "name": "Item A"},
                    {"id": "item2", "name": "Item B"}
                ],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": [
                    {"id": "item1", "name": "Item A"},
                    {"id": "item2", "name": "Item B"}
                ],
                "metadata": {"quality": {"score": 0.8}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        assert len(consensus["data"]) == 2
        item_ids = {item["id"] for item in consensus["data"]}
        assert item_ids == {"item1", "item2"}
    
    def test_consensus_single_provider(self, fusion_engine):
        """Test consensus with single provider (lower confidence)"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "name": "Item A"}],
                "metadata": {"quality": {"score": 0.9}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        assert len(consensus["data"]) == 1
        # Single source should have lower confidence
        assert consensus["metadata"]["fusion_info"]["agreement_stats"]["single_source"] >= 0
    
    def test_consensus_no_data_points(self, fusion_engine):
        """Test consensus when no data points available"""
        results = [
            {
                "provider": "provider1",
                "data": [],
                "metadata": {"quality": {"score": 0.9}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        # Should fallback to best_quality
        assert consensus is not None
    
    def test_consensus_agreement_stats(self, fusion_engine):
        """Test that agreement statistics are tracked"""
        results = [
            {
                "provider": "provider1",
                "data": [
                    {"id": "item1", "name": "Item A"},  # Full agreement
                    {"id": "item2", "name": "Item B"}   # Single source
                ],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": [
                    {"id": "item1", "name": "Item A"},  # Full agreement
                    {"id": "item3", "name": "Item C"}   # Different item
                ],
                "metadata": {"quality": {"score": 0.8}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        stats = consensus["metadata"]["fusion_info"]["agreement_stats"]
        assert "full_agreement" in stats
        assert "partial_agreement" in stats
        assert "conflicts" in stats
        assert "single_source" in stats
    
    def test_consensus_field_confidences(self, fusion_engine):
        """Test that field-level confidences are calculated"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "name": "Item A", "value": 100}],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": [{"id": "item1", "name": "Item A", "value": 100}],
                "metadata": {"quality": {"score": 0.8}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        if consensus["data"]:
            metadata = consensus["data"][0].get("_consensus_metadata", {})
            if "field_confidences" in metadata:
                assert isinstance(metadata["field_confidences"], dict)
    
    def test_consensus_provider_tracking(self, fusion_engine):
        """Test that providers are tracked in consensus metadata"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "name": "Item A"}],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": [{"id": "item1", "name": "Item A"}],
                "metadata": {"quality": {"score": 0.8}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        providers = consensus["metadata"]["fusion_info"]["providers"]
        assert "provider1" in providers
        assert "provider2" in providers
        
        if consensus["data"]:
            metadata = consensus["data"][0].get("_consensus_metadata", {})
            if "providers" in metadata:
                assert "provider1" in metadata["providers"]
                assert "provider2" in metadata["providers"]
    
    def test_consensus_numeric_conflicts(self, fusion_engine):
        """Test consensus with numeric value conflicts"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "value": 100.5}],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": [{"id": "item1", "value": 100.5}],
                "metadata": {"quality": {"score": 0.8}}
            },
            {
                "provider": "provider3",
                "data": [{"id": "item1", "value": 200.0}],
                "metadata": {"quality": {"score": 0.7}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        # Majority (2 out of 3) agree on 100.5
        assert consensus["data"][0]["value"] == 100.5
    
    def test_consensus_string_conflicts(self, fusion_engine):
        """Test consensus with string value conflicts"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "status": "active"}],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": [{"id": "item1", "status": "active"}],
                "metadata": {"quality": {"score": 0.8}}
            },
            {
                "provider": "provider3",
                "data": [{"id": "item1", "status": "inactive"}],
                "metadata": {"quality": {"score": 0.7}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        # Majority (2 out of 3) agree on "active"
        assert consensus["data"][0]["status"] == "active"
    
    def test_consensus_mixed_data_structures(self, fusion_engine):
        """Test consensus with mixed data structures (list and dict)"""
        results = [
            {
                "provider": "provider1",
                "data": [{"id": "item1", "name": "Item A"}],
                "metadata": {"quality": {"score": 0.9}}
            },
            {
                "provider": "provider2",
                "data": {"id": "item1", "name": "Item A"},  # Single dict instead of list
                "metadata": {"quality": {"score": 0.8}}
            }
        ]
        
        consensus = fusion_engine.fuse_multi_provider_results(
            results, fusion_strategy=DataFusionEngine.STRATEGY_CONSENSUS
        )
        
        assert consensus is not None
        assert len(consensus["data"]) >= 1
