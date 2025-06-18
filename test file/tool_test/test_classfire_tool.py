import pytest
import asyncio
from unittest.mock import patch, MagicMock
import time

from app.tools.classfire_tool import (
    ClassifierTool,
    ClassifierToolError,
    InputValidationError,
    SecurityError,
    ClassifierSettings
)

# Mock imports for testing
import sys
from unittest.mock import MagicMock

# Mock pke if not available
if 'pke' not in sys.modules:
    sys.modules['pke'] = MagicMock()

# Fixtures
@pytest.fixture
def classifier_tool():
    """Create a ClassifierTool instance for testing."""
    tool = ClassifierTool({
        "max_workers": 2,
        "pipeline_cache_size": 2,
        "pipeline_cache_ttl": 60,
        "rate_limit_enabled": False  # Disable rate limiting for tests
    })
    return tool

@pytest.fixture
async def cleanup_tool(classifier_tool):
    """Fixture to ensure tool cleanup after tests."""
    yield classifier_tool
    await classifier_tool.cleanup()

# Basic functionality tests
@pytest.mark.asyncio
async def test_classify(cleanup_tool):
    """Test sentiment classification."""
    with patch('app.tools.classfire_tool.pipeline') as mock_pipeline:
        mock_pipeline.return_value = lambda text: [{'label': 'POSITIVE', 'score': 0.99}]
        result = await cleanup_tool.run(op='classify', text='I love this!', language='en')
        assert isinstance(result, list)
        assert 'label' in result[0]
        assert 'score' in result[0]
        assert result[0]['label'] == 'POSITIVE'

@pytest.mark.asyncio
async def test_tokenize_english(cleanup_tool):
    """Test English tokenization."""
    with patch('app.tools.classfire_tool.spacy.load') as mock_load:
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [
            type('Token', (), {'text': 'Hello'}),
            type('Token', (), {'text': 'world'}),
            type('Token', (), {'text': '!'})
        ]
        mock_nlp.return_value = mock_doc
        mock_load.return_value = mock_nlp
        
        result = await cleanup_tool.run(op='tokenize', text='Hello world!', language='en')
        assert isinstance(result, list)
        assert len(result) == 3
        assert result == ['Hello', 'world', '!']

@pytest.mark.asyncio
async def test_tokenize_chinese(cleanup_tool):
    """Test Chinese tokenization."""
    with patch('app.tools.classfire_tool.jieba.cut') as mock_cut:
        mock_cut.return_value = ['我', '爱', '编程']
        result = await cleanup_tool.run(op='tokenize', text='我爱编程', language='zh')
        assert isinstance(result, list)
        assert len(result) == 3
        assert '编程' in result

@pytest.mark.asyncio
async def test_pos_tag_english(cleanup_tool):
    """Test English part-of-speech tagging."""
    with patch('app.tools.classfire_tool.spacy.load') as mock_load:
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [
            type('Token', (), {'text': 'The', 'pos_': 'DET'}),
            type('Token', (), {'text': 'cat', 'pos_': 'NOUN'}),
            type('Token', (), {'text': 'runs', 'pos_': 'VERB'}),
            type('Token', (), {'text': '.', 'pos_': 'PUNCT'})
        ]
        mock_nlp.return_value = mock_doc
        mock_load.return_value = mock_nlp
        
        result = await cleanup_tool.run(op='pos_tag', text='The cat runs.', language='en')
        assert isinstance(result, list)
        assert len(result) == 4
        assert ('cat', 'NOUN') in result

@pytest.mark.asyncio
async def test_ner(cleanup_tool):
    """Test named entity recognition."""
    with patch('app.tools.classfire_tool.spacy.load') as mock_load:
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.ents = [
            type('Entity', (), {'text': 'Apple', 'label_': 'ORG', 'start_char': 0, 'end_char': 5}),
            type('Entity', (), {'text': 'California', 'label_': 'GPE', 'start_char': 12, 'end_char': 22})
        ]
        mock_nlp.return_value = mock_doc
        mock_load.return_value = mock_nlp
        
        result = await cleanup_tool.run(op='ner', text='Apple is in California.', language='en')
        assert isinstance(result, list)
        assert len(result) == 2
        assert any(ent['label'] == 'ORG' for ent in result)
        assert any(ent['text'] == 'Apple' for ent in result)

@pytest.mark.asyncio
async def test_lemmatize(cleanup_tool):
    """Test lemmatization."""
    with patch('app.tools.classfire_tool.spacy.load') as mock_load:
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [
            type('Token', (), {'lemma_': 'the'}),
            type('Token', (), {'lemma_': 'cat'}),
            type('Token', (), {'lemma_': 'be'}),
            type('Token', (), {'lemma_': 'run'}),
            type('Token', (), {'lemma_': '.'})
        ]
        mock_nlp.return_value = mock_doc
        mock_load.return_value = mock_nlp
        
        result = await cleanup_tool.run(op='lemmatize', text='The cats are running.', language='en')
        assert isinstance(result, list)
        assert len(result) == 5
        assert result == ['the', 'cat', 'be', 'run', '.']

@pytest.mark.asyncio
async def test_dependency_parse(cleanup_tool):
    """Test dependency parsing."""
    with patch('app.tools.classfire_tool.spacy.load') as mock_load:
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_token1 = type('Token', (), {
            'text': 'The', 
            'head': type('Head', (), {'text': 'cat'}),
            'dep_': 'det',
            'pos_': 'DET'
        })
        mock_token2 = type('Token', (), {
            'text': 'cat', 
            'head': type('Head', (), {'text': 'runs'}),
            'dep_': 'nsubj',
            'pos_': 'NOUN'
        })
        mock_doc.__iter__.return_value = [mock_token1, mock_token2]
        mock_nlp.return_value = mock_doc
        mock_load.return_value = mock_nlp
        
        result = await cleanup_tool.run(op='dependency_parse', text='The cat runs.', language='en')
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['text'] == 'The'
        assert result[0]['head'] == 'cat'
        assert result[0]['dep'] == 'det'

@pytest.mark.asyncio
async def test_keyword_extract_basic(cleanup_tool):
    """Test basic keyword extraction without phrases."""
    with patch('app.tools.classfire_tool.spacy.load') as mock_load:
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [
            type('Token', (), {'text': 'The', 'pos_': 'DET'}),
            type('Token', (), {'text': 'cat', 'pos_': 'NOUN'}),
            type('Token', (), {'text': 'and', 'pos_': 'CCONJ'}),
            type('Token', (), {'text': 'dog', 'pos_': 'NOUN'}),
            type('Token', (), {'text': 'play', 'pos_': 'VERB'})
        ]
        mock_nlp.return_value = mock_doc
        mock_load.return_value = mock_nlp
        
        result = await cleanup_tool.run(op='keyword_extract', text='The cat and dog play.', top_k=3, language='en', extract_phrases=False)
        assert isinstance(result, list)
        assert len(result) <= 3
        assert 'cat' in result
        assert 'dog' in result

@pytest.mark.asyncio
async def test_keyword_extract_english_phrases(cleanup_tool):
    """Test English phrase extraction using RAKE."""
    with patch('app.tools.classfire_tool.Rake') as mock_rake_class:
        mock_rake = MagicMock()
        mock_rake.get_ranked_phrases_with_scores.return_value = [
            (9.0, 'cat and dog play'),
            (4.0, 'cat'),
            (4.0, 'dog')
        ]
        mock_rake_class.return_value = mock_rake
        
        result = await cleanup_tool.run(op='keyword_extract', text='The cat and dog play together.', top_k=3, language='en', extract_phrases=True)
        assert isinstance(result, list)
        assert len(result) <= 3
        assert 'cat and dog play' in result
        
        # Verify RAKE was called
        mock_rake.extract_keywords_from_text.assert_called_once()

@pytest.mark.asyncio
async def test_keyword_extract_chinese_phrases(cleanup_tool):
    """Test Chinese phrase extraction using PKE."""
    # Mock jieba fallback for Chinese
    with patch('app.tools.classfire_tool.extract_tags') as mock_extract_tags:
        mock_extract_tags.return_value = ['编程', '人工智能', '学习']
        
        # Mock PKE
        mock_pke = MagicMock()
        mock_extractor = MagicMock()
        mock_extractor.get_n_best.return_value = [
            ('人工智能技术', 0.8),
            ('编程学习', 0.6),
            ('计算机科学', 0.5)
        ]
        mock_pke.unsupervised.MultipartiteRank.return_value = mock_extractor
        
        with patch.dict('sys.modules', {'pke': mock_pke}):
            with patch('app.tools.classfire_tool.pke', mock_pke):
                result = await cleanup_tool.run(op='keyword_extract', text='人工智能技术和编程学习对计算机科学很重要。', top_k=3, language='zh', extract_phrases=True)
                
                assert isinstance(result, list)
                assert len(result) <= 3
                assert '人工智能技术' in result
                assert '编程学习' in result
                
                # Verify PKE was called
                mock_extractor.load_document.assert_called_once()
                mock_extractor.candidate_selection.assert_called_once()
                mock_extractor.candidate_weighting.assert_called_once()

@pytest.mark.asyncio
async def test_summarize(cleanup_tool):
    """Test text summarization."""
    with patch('app.tools.classfire_tool.pipeline') as mock_pipeline:
        mock_pipeline.return_value = lambda text, max_length, min_length, do_sample: [
            {'summary_text': 'Short summary.'}
        ]
        result = await cleanup_tool.run(op='summarize', text='Long text that needs summarization.', max_length=50, language='en')
        assert isinstance(result, str)
        assert result == 'Short summary.'

@pytest.mark.asyncio
async def test_batch_process(cleanup_tool):
    """Test batch processing."""
    with patch('app.tools.classfire_tool.pipeline') as mock_pipeline:
        mock_pipeline.return_value = lambda text: [{'label': 'POSITIVE', 'score': 0.99}]
        result = await cleanup_tool.run(
            op='batch_process', 
            texts=['I love this!', 'I hate this!'], 
            operation='classify', 
            language='en'
        )
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, list) for r in result)

# Error handling tests
@pytest.mark.asyncio
async def test_invalid_operation(cleanup_tool):
    """Test handling of invalid operations."""
    with pytest.raises(ClassifierToolError):
        await cleanup_tool.run(op='invalid_op', text='Some text')

@pytest.mark.asyncio
async def test_invalid_text(cleanup_tool):
    """Test handling of potentially malicious text."""
    with pytest.raises(SecurityError):
        await cleanup_tool.run(op='classify', text='SELECT * FROM users;')

@pytest.mark.asyncio
async def test_invalid_model(cleanup_tool):
    """Test handling of invalid model names."""
    with pytest.raises(InputValidationError):
        await cleanup_tool.run(op='classify', text='I love this!', model='invalid_model')

@pytest.mark.asyncio
async def test_text_too_long(cleanup_tool):
    """Test handling of text that exceeds maximum length."""
    long_text = "a" * (ClassifierSettings().max_text_length + 1)
    with pytest.raises(InputValidationError):
        await cleanup_tool.run(op='classify', text=long_text)

# Rate limiting tests
@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting functionality."""
    tool = ClassifierTool({
        "rate_limit_enabled": True,
        "rate_limit_requests": 2,
        "rate_limit_window": 60
    })
    
    try:
        # First two requests should succeed
        with patch('app.tools.classfire_tool.pipeline') as mock_pipeline:
            mock_pipeline.return_value = lambda text: [{'label': 'POSITIVE', 'score': 0.99}]
            
            await tool.run(op='classify', text='First request')
            await tool.run(op='classify', text='Second request')
            
            # Third request should fail due to rate limit
            with pytest.raises(ClassifierToolError) as excinfo:
                await tool.run(op='classify', text='Third request')
            
            assert "Rate limit exceeded" in str(excinfo.value)
    finally:
        await tool.cleanup()

# Resource management tests
@pytest.mark.asyncio
async def test_cleanup():
    """Test resource cleanup."""
    tool = ClassifierTool()
    
    # Mock the executor and cache
    tool._executor = MagicMock()
    tool._pipeline_cache = MagicMock()
    tool._spacy_nlp = MagicMock()
    
    await tool.cleanup()
    
    # Verify cleanup actions
    tool._executor.shutdown.assert_called_once()
    tool._pipeline_cache.clear.assert_called_once()
    tool._spacy_nlp.clear.assert_called_once()

@pytest.mark.asyncio
async def test_health_check(cleanup_tool):
    """Test health check functionality."""
    # Add some metrics data
    cleanup_tool._metrics['requests'] = 10
    cleanup_tool._metrics['cache_hits'] = 5
    cleanup_tool._metrics['processing_time'] = [0.1, 0.2, 0.3]
    
    health_data = await cleanup_tool.health_check()
    
    assert health_data['status'] == 'healthy'
    assert health_data['metrics']['requests'] == 10
    assert health_data['metrics']['cache_hits'] == 5
    assert health_data['metrics']['avg_processing_time'] == 0.2
    assert 'version' in health_data
    assert 'rate_limit' in health_data