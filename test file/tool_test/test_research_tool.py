import os
import pytest
import asyncio
import tempfile
from typing import Dict, Any, List
import numpy as np
from unittest.mock import patch, MagicMock

from app.tools.research_tool import (
    ResearchTool, ResearchToolError, InputValidationError, 
    SecurityError, ResearchSettings
)

# Test fixtures
@pytest.fixture
def research_tool():
    """Create a ResearchTool instance with test configuration."""
    config = {
        "max_workers": 2,
        "cache_ttl_seconds": 10,
        "cache_max_items": 5,
        "spacy_model": "en_core_web_sm"
    }
    tool = ResearchTool(config=config)
    yield tool

@pytest.fixture
def mock_spacy():
    """Mock spaCy to avoid loading actual models during tests."""
    with patch('app.tools.research_tool.spacy') as mock_spacy:
        # Create a mock NLP object
        mock_nlp = MagicMock()
        mock_spacy.load.return_value = mock_nlp
        
        # Mock sentence tokenization
        mock_doc = MagicMock()
        mock_sent1 = MagicMock()
        mock_sent1.text = "This is a test sentence."
        mock_sent2 = MagicMock()
        mock_sent2.text = "Another test sentence."
        mock_doc.sents = [mock_sent1, mock_sent2]
        mock_nlp.return_value = mock_doc
        
        # Mock entities and tokens
        mock_token = MagicMock()
        mock_token.lemma_ = "test"
        mock_token.pos_ = "NOUN"
        mock_token.is_stop = False
        mock_doc.__iter__.return_value = [mock_token]
        
        mock_ent = MagicMock()
        mock_ent.text = "test"
        mock_doc.ents = [mock_ent]
        
        # Mock noun chunks
        mock_chunk = MagicMock()
        mock_chunk.text = "test"
        mock_doc.noun_chunks = [mock_chunk]
        
        yield mock_spacy

# Unit tests
@pytest.mark.asyncio
async def test_mill_agreement(research_tool):
    """Test Mill's Method of Agreement."""
    cases = [
        {"attrs": {"A": True, "B": False}, "outcome": True},
        {"attrs": {"A": True, "C": True}, "outcome": True}
    ]
    
    result = await research_tool.run(op='mill_agreement', cases=cases)
    
    assert isinstance(result, dict)
    assert "common_factors" in result
    assert "A" in result["common_factors"]
    assert "B" not in result["common_factors"]
    assert "C" not in result["common_factors"]

@pytest.mark.asyncio
async def test_mill_difference(research_tool):
    """Test Mill's Method of Difference."""
    positive_case = {"attrs": {"A": True, "B": False}, "outcome": True}
    negative_case = {"attrs": {"A": False, "B": False}, "outcome": False}
    
    result = await research_tool.run(
        op='mill_difference', 
        positive_case=positive_case, 
        negative_case=negative_case
    )
    
    assert isinstance(result, dict)
    assert "difference_factors" in result
    assert "A" in result["difference_factors"]
    assert "B" not in result["difference_factors"]

@pytest.mark.asyncio
async def test_mill_joint(research_tool):
    """Test Mill's Joint Method."""
    positive_cases = [{"attrs": {"A": True, "B": False}, "outcome": True}]
    negative_cases = [{"attrs": {"A": False, "B": False}, "outcome": False}]
    
    result = await research_tool.run(
        op='mill_joint', 
        positive_cases=positive_cases, 
        negative_cases=negative_cases
    )
    
    assert isinstance(result, dict)
    assert "causal_factors" in result
    assert "A" in result["causal_factors"]
    assert "B" not in result["causal_factors"]

@pytest.mark.asyncio
async def test_mill_residues(research_tool):
    """Test Mill's Method of Residues."""
    cases = [{"attrs": {"A": True, "B": True}, "effects": {"E1": True, "E2": True}}]
    known_causes = {"E1": ["A"]}
    
    result = await research_tool.run(
        op='mill_residues', 
        cases=cases, 
        known_causes=known_causes
    )
    
    assert isinstance(result, dict)
    assert "residual_causes" in result
    assert "E2" in result["residual_causes"]
    assert "B" in result["residual_causes"]["E2"]

@pytest.mark.asyncio
async def test_mill_concomitant(research_tool):
    """Test Mill's Method of Concomitant Variations."""
    # Mock pearsonr to return a fixed correlation value
    with patch('app.tools.research_tool.pearsonr', return_value=(0.9, 0.05)):
        cases = [
            {"attrs": {"temp": 20, "speed": 50}},
            {"attrs": {"temp": 30, "speed": 60}}
        ]
        
        result = await research_tool.run(
            op='mill_concomitant', 
            cases=cases, 
            factor='temp', 
            effect='speed'
        )
        
        assert isinstance(result, dict)
        assert "correlation" in result
        assert "pvalue" in result
        assert result["correlation"] == 0.9
        assert result["pvalue"] == 0.05

@pytest.mark.asyncio
async def test_induction(research_tool, mock_spacy):
    """Test induction operation."""
    examples = ["The cat runs fast.", "The dog runs quickly."]
    
    result = await research_tool.run(op='induction', examples=examples, max_keywords=5)
    
    assert isinstance(result, dict)
    assert "patterns" in result
    assert len(result["patterns"]) > 0

@pytest.mark.asyncio
async def test_deduction(research_tool, mock_spacy):
    """Test deduction operation."""
    premises = ["All men are mortal.", "Socrates is a man."]
    conclusion = "Socrates is mortal."
    
    result = await research_tool.run(
        op='deduction', 
        premises=premises, 
        conclusion=conclusion
    )
    
    assert isinstance(result, dict)
    assert "valid" in result
    assert "conclusion" in result
    assert "reason" in result
    assert result["conclusion"] == conclusion

@pytest.mark.asyncio
async def test_summarize(research_tool, mock_spacy):
    """Test summarization operation."""
    text = "This is a long text that needs to be summarized. It contains multiple sentences with various information."
    
    result = await research_tool.run(op='summarize', text=text, max_length=50)
    
    assert isinstance(result, str)
    assert len(result) <= 50 or result.endswith('...')

@pytest.mark.asyncio
async def test_input_validation_error(research_tool):
    """Test input validation error handling."""
    with pytest.raises(InputValidationError):
        await research_tool.run(op='mill_agreement', cases=[])

@pytest.mark.asyncio
async def test_security_error(research_tool):
    """Test security error handling."""
    malicious_case = {
        "attrs": {"attack": "SELECT * FROM users;"},
        "outcome": True
    }
    
    with pytest.raises(SecurityError):
        await research_tool.run(op='mill_agreement', cases=[malicious_case])

@pytest.mark.asyncio
async def test_unsupported_operation(research_tool):
    """Test unsupported operation error handling."""
    with pytest.raises(ResearchToolError):
        await research_tool.run(op='nonexistent_operation')

@pytest.mark.asyncio
async def test_caching(research_tool):
    """Test result caching."""
    cases = [
        {"attrs": {"A": True, "B": False}, "outcome": True},
        {"attrs": {"A": True, "C": True}, "outcome": True}
    ]
    
    # First call
    result1 = await research_tool.run(op='mill_agreement', cases=cases)
    
    # Second call with same parameters should hit cache
    result2 = await research_tool.run(op='mill_agreement', cases=cases)
    
    assert result1 == result2
    assert research_tool._metrics.cache_hits >= 1

@pytest.mark.asyncio
async def test_metrics(research_tool):
    """Test metrics collection."""
    cases = [{"attrs": {"A": True}, "outcome": True}]
    
    await research_tool.run(op='mill_agreement', cases=cases)
    
    metrics = research_tool._metrics.to_dict()
    assert metrics["requests"] >= 1
    assert "avg_processing_time" in metrics
    assert metrics["avg_processing_time"] > 0