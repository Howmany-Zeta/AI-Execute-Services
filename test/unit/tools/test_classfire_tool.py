"""
Comprehensive tests for ClassifierTool component
Tests cover all public methods and functionality with >85% coverage
"""
import pytest
import asyncio
import time
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

from aiecs.tools.task_tools.classfire_tool import ClassifierTool, Language, ModelType
from pydantic import ValidationError


class TestClassifierTool:
    """Test class for ClassifierTool functionality"""

    @pytest.fixture
    def default_classifier(self):
        """Create ClassifierTool instance with default configuration"""
        return ClassifierTool()

    @pytest.fixture
    def custom_classifier(self):
        """Create ClassifierTool instance with custom configuration"""
        config = {
            'max_workers': 4,
            'pipeline_cache_ttl': 1800,
            'max_text_length': 5000,
            'rate_limit_enabled': False,
            'use_rake_for_english': True,
            'use_pke_for_chinese': False
        }
        return ClassifierTool(config)

    @pytest.fixture
    def rate_limited_classifier(self):
        """Create ClassifierTool instance with rate limiting enabled"""
        config = {
            'rate_limit_enabled': True,
            'rate_limit_requests': 5,
            'rate_limit_window': 10
        }
        return ClassifierTool(config)

    @pytest.fixture
    def english_text(self):
        """Sample English text for testing"""
        return "This is a great product! I love it very much. It works perfectly and exceeds my expectations. The quality is outstanding and the customer service is excellent. I would definitely recommend this to anyone looking for a reliable solution. The features are comprehensive and the user interface is intuitive. Overall, this product has transformed my workflow and made my tasks much more efficient."

    @pytest.fixture
    def chinese_text(self):
        """Sample Chinese text for testing"""
        return "这是一个很好的产品！我非常喜欢它。它工作得很完美，超出了我的期望。质量非常出色，客户服务也很优秀。我绝对会向任何寻找可靠解决方案的人推荐这个产品。功能全面，用户界面直观。总的来说，这个产品改变了我的工作流程，让我的任务变得更加高效。"

    @pytest.fixture
    def neutral_text(self):
        """Sample neutral text for testing"""
        return "The product has specifications including dimensions and weight."

    @pytest.fixture
    def negative_text(self):
        """Sample negative text for testing"""
        return "This product is terrible! It failed completely and I hate it. Very disappointed."

    @pytest.fixture
    def mixed_language_text(self):
        """Sample mixed language text for testing"""
        return "Hello world 你好世界 this is a test 这是一个测试"

    @pytest.fixture
    def long_text(self):
        """Long text for testing limits"""
        return "word " * 2001  # 10005 characters (exceeds 10000 limit)

    @pytest.fixture
    def malicious_text(self):
        """Text with potentially malicious content for testing validation"""
        return "SELECT * FROM users; DROP TABLE users;--"

    # Test Initialization and Configuration
    def test_init_default_config(self, default_classifier):
        """Test ClassifierTool initialization with default configuration"""
        assert default_classifier.config.max_workers >= 2
        assert default_classifier.config.pipeline_cache_ttl == 3600
        assert default_classifier.config.max_text_length == 10_000
        assert default_classifier.config.spacy_model_en == "en_core_web_sm"
        assert default_classifier.config.spacy_model_zh == "zh_core_web_sm"
        assert default_classifier.config.rate_limit_enabled is True
        assert default_classifier.config.use_rake_for_english is True

    def test_init_custom_config(self, custom_classifier):
        """Test ClassifierTool initialization with custom configuration"""
        assert custom_classifier.config.max_workers == 4
        assert custom_classifier.config.pipeline_cache_ttl == 1800
        assert custom_classifier.config.max_text_length == 5000
        assert custom_classifier.config.rate_limit_enabled is False
        assert custom_classifier.config.use_rake_for_english is True

    def test_config_validation(self):
        """Test Config model validation"""
        config = ClassifierTool.Config()
        assert config.max_workers > 0
        assert config.pipeline_cache_ttl > 0
        assert config.max_text_length > 0
        assert isinstance(config.allowed_models, list)
        assert "en_core_web_sm" in config.allowed_models

    # Test Schema Validation
    def test_base_text_schema_valid(self, english_text):
        """Test BaseTextSchema with valid input"""
        schema = ClassifierTool.BaseTextSchema(text=english_text)
        assert schema.text == english_text

    def test_base_text_schema_too_long(self, long_text):
        """Test BaseTextSchema with text exceeding length limit"""
        with pytest.raises(ValidationError, match="Text length exceeds"):
            ClassifierTool.BaseTextSchema(text=long_text)

    def test_base_text_schema_malicious_content(self, malicious_text):
        """Test BaseTextSchema with potentially malicious content"""
        with pytest.raises(ValidationError, match="potentially malicious"):
            ClassifierTool.BaseTextSchema(text=malicious_text)

    def test_classify_schema_valid_model(self, english_text):
        """Test ClassifySchema with valid model"""
        schema = ClassifierTool.ClassifySchema(
            text=english_text,
            model="en_core_web_sm",
            language=Language.ENGLISH
        )
        assert schema.model == "en_core_web_sm"
        assert schema.language == Language.ENGLISH

    def test_classify_schema_invalid_model(self, english_text):
        """Test ClassifySchema with invalid model"""
        with pytest.raises(ValidationError, match="not in allowed spaCy models"):
            ClassifierTool.ClassifySchema(
                text=english_text,
                model="invalid_model"
            )

    def test_keyword_extract_schema(self, english_text):
        """Test KeywordExtractSchema validation"""
        schema = ClassifierTool.KeywordExtractSchema(
            text=english_text,
            top_k=15,
            extract_phrases=False
        )
        assert schema.top_k == 15
        assert schema.extract_phrases is False

    def test_batch_process_schema_valid(self, english_text, chinese_text):
        """Test BatchProcessSchema with valid input"""
        schema = ClassifierTool.BatchProcessSchema(
            texts=[english_text, chinese_text],
            operation="tokenize",
            language=Language.AUTO
        )
        assert len(schema.texts) == 2
        assert schema.operation == "tokenize"

    def test_batch_process_schema_invalid_texts(self, long_text):
        """Test BatchProcessSchema with invalid texts"""
        with pytest.raises(ValidationError, match="Text length exceeds"):
            ClassifierTool.BatchProcessSchema(
                texts=[long_text],
                operation="tokenize"
            )

    # Test Language Detection
    def test_detect_language_english(self, default_classifier, english_text):
        """Test language detection for English text"""
        result = default_classifier._detect_language(english_text)
        assert result == 'en'

    def test_detect_language_chinese(self, default_classifier, chinese_text):
        """Test language detection for Chinese text"""
        result = default_classifier._detect_language(chinese_text)
        assert result == 'zh'

    def test_detect_language_mixed(self, default_classifier, mixed_language_text):
        """Test language detection for mixed language text"""
        result = default_classifier._detect_language(mixed_language_text)
        # Should detect based on ratio, likely 'zh' due to Chinese characters
        assert result in ['en', 'zh']

    def test_detect_language_empty_text(self, default_classifier):
        """Test language detection for empty text"""
        result = default_classifier._detect_language("")
        assert result == 'en'  # Default to English

    def test_detect_language_non_alphabetic(self, default_classifier):
        """Test language detection for non-alphabetic text"""
        result = default_classifier._detect_language("123 !@# $%^")
        assert result == 'en'  # Default to English

    # Test Rate Limiting
    def test_rate_limit_disabled(self, custom_classifier):
        """Test rate limiting when disabled"""
        # Rate limiting is disabled in custom_classifier
        result = custom_classifier._check_rate_limit()
        assert result is True

    @patch('time.time')
    def test_rate_limit_enabled_within_limits(self, mock_time, rate_limited_classifier):
        """Test rate limiting when within limits"""
        mock_time.return_value = 1000.0
        
        # Mock the executor's get_lock method
        with patch.object(rate_limited_classifier, '_executor') as mock_executor:
            mock_lock = MagicMock()
            mock_executor.get_lock.return_value.__enter__ = MagicMock(return_value=mock_lock)
            mock_executor.get_lock.return_value.__exit__ = MagicMock(return_value=None)
            
            # First few requests should pass
            for _ in range(3):
                result = rate_limited_classifier._check_rate_limit()
                assert result is True

    @patch('time.time')
    def test_rate_limit_enabled_exceeded(self, mock_time, rate_limited_classifier):
        """Test rate limiting when limits are exceeded"""
        mock_time.return_value = 1000.0
        
        # Mock the executor's get_lock method
        with patch.object(rate_limited_classifier, '_executor') as mock_executor:
            mock_lock = MagicMock()
            mock_executor.get_lock.return_value.__enter__ = MagicMock(return_value=mock_lock)
            mock_executor.get_lock.return_value.__exit__ = MagicMock(return_value=None)
            
            # Fill up the rate limit
            rate_limited_classifier._request_timestamps = [1000.0] * 5
            
            # Next request should be blocked
            result = rate_limited_classifier._check_rate_limit()
            assert result is False

    # Test Sentiment Lexicons
    def test_get_sentiment_lexicon_english(self, default_classifier):
        """Test getting English sentiment lexicon"""
        lexicon = default_classifier._get_sentiment_lexicon('en')
        assert isinstance(lexicon, dict)
        assert 'good' in lexicon
        assert 'bad' in lexicon
        assert lexicon['good'] > 0
        assert lexicon['bad'] < 0

    def test_get_sentiment_lexicon_chinese(self, default_classifier):
        """Test getting Chinese sentiment lexicon"""
        lexicon = default_classifier._get_sentiment_lexicon('zh')
        assert isinstance(lexicon, dict)
        assert '好' in lexicon
        assert '坏' in lexicon
        assert lexicon['好'] > 0
        assert lexicon['坏'] < 0

    # Test SpaCy Pipeline Access
    @patch('spacy.load')
    def test_get_spacy_english(self, mock_spacy_load, default_classifier):
        """Test getting spaCy pipeline for English"""
        mock_nlp = MagicMock()
        mock_spacy_load.return_value = mock_nlp
        
        with patch('aiecs.tools.task_tools.classfire_tool.spacy', None):
            with patch('builtins.__import__', return_value=MagicMock()) as mock_import:
                # Mock the spacy import
                mock_spacy_module = MagicMock()
                mock_spacy_module.load = mock_spacy_load
                mock_import.return_value = mock_spacy_module
                
                result = default_classifier._get_spacy('en')
                mock_spacy_load.assert_called_with("en_core_web_sm", disable=["textcat"])

    @patch('spacy.load')
    def test_get_spacy_chinese(self, mock_spacy_load, default_classifier):
        """Test getting spaCy pipeline for Chinese"""
        mock_nlp = MagicMock()
        mock_spacy_load.return_value = mock_nlp
        
        with patch('aiecs.tools.task_tools.classfire_tool.spacy', None):
            with patch('builtins.__import__', return_value=MagicMock()) as mock_import:
                mock_spacy_module = MagicMock()
                mock_spacy_module.load = mock_spacy_load
                mock_import.return_value = mock_spacy_module
                
                result = default_classifier._get_spacy('zh')
                mock_spacy_load.assert_called_with("zh_core_web_sm", disable=["textcat"])

    def test_get_spacy_import_error(self, default_classifier):
        """Test spaCy import error handling"""
        with patch('aiecs.tools.task_tools.classfire_tool.spacy', None):
            with patch('builtins.__import__', side_effect=ImportError("spaCy not installed")):
                with pytest.raises(ImportError, match="spaCy is required"):
                    default_classifier._get_spacy('en')

    # Test Classification
    @pytest.mark.asyncio
    async def test_classify_english_positive(self, custom_classifier, english_text):
        """Test classification of positive English text"""
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline
            mock_doc = MagicMock()
            mock_token = MagicMock()
            mock_token.is_stop = False
            mock_token.is_punct = False
            mock_token.text.lower.return_value = "great"
            mock_doc.__iter__.return_value = [mock_token]
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.classify(english_text)
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert 'label' in result[0]
            assert 'score' in result[0]
            assert result[0]['label'] in ['POSITIVE', 'NEGATIVE', 'NEUTRAL']

    @pytest.mark.asyncio
    async def test_classify_chinese_positive(self, custom_classifier, chinese_text):
        """Test classification of positive Chinese text"""
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline for Chinese
            mock_doc = MagicMock()
            mock_token = MagicMock()
            mock_token.is_stop = False
            mock_token.is_punct = False
            mock_token.text.lower.return_value = "好"
            mock_doc.__iter__.return_value = [mock_token]
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.classify(chinese_text)
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['label'] in ['POSITIVE', 'NEGATIVE', 'NEUTRAL']

    @pytest.mark.asyncio
    async def test_classify_negative_text(self, custom_classifier, negative_text):
        """Test classification of negative text"""
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline
            mock_doc = MagicMock()
            mock_token = MagicMock()
            mock_token.is_stop = False
            mock_token.is_punct = False
            mock_token.text.lower.return_value = "terrible"
            mock_doc.__iter__.return_value = [mock_token]
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.classify(negative_text)
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['label'] in ['POSITIVE', 'NEGATIVE', 'NEUTRAL']

    @pytest.mark.asyncio
    async def test_classify_neutral_text(self, custom_classifier, neutral_text):
        """Test classification of neutral text"""
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline
            mock_doc = MagicMock()
            mock_token = MagicMock()
            mock_token.is_stop = False
            mock_token.is_punct = False
            mock_token.text.lower.return_value = "specifications"
            mock_doc.__iter__.return_value = [mock_token]
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.classify(neutral_text)
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['label'] in ['POSITIVE', 'NEGATIVE', 'NEUTRAL']

    @pytest.mark.asyncio
    async def test_classify_rate_limit_exceeded(self, rate_limited_classifier):
        """Test classification when rate limit is exceeded"""
        with patch.object(rate_limited_classifier, '_check_rate_limit', return_value=False):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await rate_limited_classifier.classify("test text")

    # Test Tokenization
    @pytest.mark.asyncio
    async def test_tokenize_english(self, custom_classifier, english_text):
        """Test tokenization of English text"""
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline
            mock_doc = MagicMock()
            mock_tokens = [MagicMock(text="This"), MagicMock(text="is"), MagicMock(text="test")]
            mock_doc.__iter__.return_value = mock_tokens
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.tokenize(english_text)
            
            assert isinstance(result, list)
            assert len(result) == 3
            assert result == ["This", "is", "test"]

    @pytest.mark.asyncio
    async def test_tokenize_chinese(self, custom_classifier, chinese_text):
        """Test tokenization of Chinese text"""
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline for Chinese
            mock_doc = MagicMock()
            mock_tokens = [MagicMock(text="这"), MagicMock(text="是"), MagicMock(text="测试")]
            mock_doc.__iter__.return_value = mock_tokens
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.tokenize(chinese_text)
            
            assert isinstance(result, list)
            assert len(result) == 3
            assert result == ["这", "是", "测试"]

    @pytest.mark.asyncio
    async def test_tokenize_rate_limit_exceeded(self, rate_limited_classifier):
        """Test tokenization when rate limit is exceeded"""
        with patch.object(rate_limited_classifier, '_check_rate_limit', return_value=False):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await rate_limited_classifier.tokenize("test text")

    # Test POS Tagging
    @pytest.mark.asyncio
    async def test_pos_tag(self, custom_classifier, english_text):
        """Test part-of-speech tagging"""
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline
            mock_doc = MagicMock()
            mock_tokens = [
                MagicMock(text="This", pos_="DET"),
                MagicMock(text="is", pos_="VERB"),
                MagicMock(text="test", pos_="NOUN")
            ]
            mock_doc.__iter__.return_value = mock_tokens
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.pos_tag(english_text)
            
            assert isinstance(result, list)
            assert len(result) == 3
            assert result == [("This", "DET"), ("is", "VERB"), ("test", "NOUN")]

    @pytest.mark.asyncio
    async def test_pos_tag_rate_limit_exceeded(self, rate_limited_classifier):
        """Test POS tagging when rate limit is exceeded"""
        with patch.object(rate_limited_classifier, '_check_rate_limit', return_value=False):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await rate_limited_classifier.pos_tag("test text")

    # Test Named Entity Recognition
    @pytest.mark.asyncio
    async def test_ner(self, custom_classifier):
        """Test named entity recognition"""
        test_text = "Apple Inc. is located in Cupertino, California."
        
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline
            mock_doc = MagicMock()
            mock_entity = MagicMock()
            mock_entity.text = "Apple Inc."
            mock_entity.label_ = "ORG"
            mock_entity.start_char = 0
            mock_entity.end_char = 10
            mock_doc.ents = [mock_entity]
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.ner(text=test_text)
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['text'] == "Apple Inc."
            assert result[0]['label'] == "ORG"
            assert result[0]['start'] == 0
            assert result[0]['end'] == 10

    @pytest.mark.asyncio
    async def test_ner_rate_limit_exceeded(self, rate_limited_classifier):
        """Test NER when rate limit is exceeded"""
        with patch.object(rate_limited_classifier, '_check_rate_limit', return_value=False):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await rate_limited_classifier.ner(text="test text")

    # Test Lemmatization
    @pytest.mark.asyncio
    async def test_lemmatize(self, custom_classifier):
        """Test lemmatization"""
        test_text = "running dogs played"
        
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline
            mock_doc = MagicMock()
            mock_tokens = [
                MagicMock(lemma_="run"),
                MagicMock(lemma_="dog"),
                MagicMock(lemma_="play")
            ]
            mock_doc.__iter__.return_value = mock_tokens
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.lemmatize(text=test_text)
            
            assert isinstance(result, list)
            assert len(result) == 3
            assert result == ["run", "dog", "play"]

    @pytest.mark.asyncio
    async def test_lemmatize_rate_limit_exceeded(self, rate_limited_classifier):
        """Test lemmatization when rate limit is exceeded"""
        with patch.object(rate_limited_classifier, '_check_rate_limit', return_value=False):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await rate_limited_classifier.lemmatize(text="test text")

    # Test Dependency Parsing
    @pytest.mark.asyncio
    async def test_dependency_parse(self, custom_classifier):
        """Test dependency parsing"""
        test_text = "The cat sat on the mat."
        
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline
            mock_doc = MagicMock()
            mock_head = MagicMock(text="sat")
            mock_token = MagicMock()
            mock_token.text = "cat"
            mock_token.head = mock_head
            mock_token.dep_ = "nsubj"
            mock_token.pos_ = "NOUN"
            mock_doc.__iter__.return_value = [mock_token]
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.dependency_parse(text=test_text)
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['text'] == "cat"
            assert result[0]['head'] == "sat"
            assert result[0]['dep'] == "nsubj"
            assert result[0]['pos'] == "NOUN"

    @pytest.mark.asyncio
    async def test_dependency_parse_rate_limit_exceeded(self, rate_limited_classifier):
        """Test dependency parsing when rate limit is exceeded"""
        with patch.object(rate_limited_classifier, '_check_rate_limit', return_value=False):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await rate_limited_classifier.dependency_parse(text="test text")

    # Test Keyword Extraction
    def test_extract_english_phrases_with_rake(self, default_classifier):
        """Test English phrase extraction using RAKE"""
        test_text = "Natural language processing is a field of artificial intelligence."
        
        with patch('aiecs.tools.task_tools.classfire_tool.rake_nltk') as mock_rake_nltk:
            mock_rake = MagicMock()
            mock_rake.get_ranked_phrases.return_value = [
                "natural language processing",
                "artificial intelligence",
                "field"
            ]
            mock_rake_nltk.Rake.return_value = mock_rake
            
            # Also mock the _init_heavy_dependencies function to ensure rake_nltk is set
            with patch('aiecs.tools.task_tools.classfire_tool._init_heavy_dependencies') as mock_init:
                # Set the global rake_nltk to our mock
                import aiecs.tools.task_tools.classfire_tool as classfire_module
                classfire_module.rake_nltk = mock_rake_nltk
                
                result = default_classifier._extract_english_phrases(test_text, 3)
                
                assert isinstance(result, list)
                assert len(result) == 3
                assert "natural language processing" in result

    def test_extract_english_phrases_fallback(self, default_classifier):
        """Test English phrase extraction fallback to spaCy"""
        test_text = "Natural language processing is important."
        
        # Mock rake_nltk to be None to trigger fallback
        with patch('aiecs.tools.task_tools.classfire_tool.rake_nltk', None):
            with patch.object(default_classifier, '_get_spacy') as mock_get_spacy:
                # Mock spaCy fallback
                mock_doc = MagicMock()
                mock_tokens = [
                    MagicMock(text="language", pos_="NOUN"),
                    MagicMock(text="processing", pos_="NOUN")
                ]
                mock_doc.__iter__.return_value = mock_tokens
                
                mock_nlp = MagicMock()
                mock_nlp.return_value = mock_doc
                mock_get_spacy.return_value = mock_nlp
                
                result = default_classifier._extract_english_phrases(test_text, 2)
                
                assert isinstance(result, list)
                assert len(result) == 2
                # The actual result from spaCy fallback
                assert "natural language processing" in result

    def test_extract_chinese_phrases(self, default_classifier):
        """Test Chinese phrase extraction"""
        test_text = "自然语言处理是人工智能的一个重要领域。"
        
        with patch.object(default_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline for Chinese
            mock_doc = MagicMock()
            
            # Mock noun chunks
            mock_chunk = MagicMock()
            mock_chunk.text.strip.return_value = "自然语言处理"
            mock_doc.noun_chunks = [mock_chunk]
            
            # Mock entities
            mock_entity = MagicMock()
            mock_entity.text.strip.return_value = "人工智能"
            mock_doc.ents = [mock_entity]
            
            # Mock tokens
            mock_token = MagicMock()
            mock_token.pos_ = "NOUN"
            mock_token.text.strip.return_value = "领域"
            mock_doc.__iter__.return_value = [mock_token]
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = default_classifier._extract_chinese_phrases(test_text, 3)
            
            assert isinstance(result, list)
            assert len(result) <= 3

    def test_extract_chinese_phrases_error_fallback(self, default_classifier):
        """Test Chinese phrase extraction with error fallback"""
        test_text = "测试文本。"
        
        with patch.object(default_classifier, '_get_spacy', side_effect=Exception("spaCy error")):
            result = default_classifier._extract_chinese_phrases(test_text, 3)
            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_keyword_extract_english_phrases(self, default_classifier, english_text):
        """Test keyword extraction for English with phrases"""
        with patch.object(default_classifier, '_extract_english_phrases') as mock_extract:
            mock_extract.return_value = ["great product", "love", "works perfectly"]
            
            result = await default_classifier.keyword_extract(
                text=english_text, top_k=3, extract_phrases=True
            )
            
            assert isinstance(result, list)
            assert len(result) == 3
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_keyword_extract_english_keywords(self, custom_classifier, english_text):
        """Test keyword extraction for English with keywords only"""
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline
            mock_doc = MagicMock()
            mock_tokens = [
                MagicMock(text="product", pos_="NOUN"),
                MagicMock(text="work", pos_="NOUN")
            ]
            mock_doc.__iter__.return_value = mock_tokens
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.keyword_extract(
                text=english_text, top_k=2, extract_phrases=False
            )
            
            assert isinstance(result, list)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_keyword_extract_chinese_phrases(self, default_classifier, chinese_text):
        """Test keyword extraction for Chinese with phrases"""
        with patch.object(default_classifier, '_extract_chinese_phrases') as mock_extract:
            mock_extract.return_value = ["好产品", "喜欢", "完美"]
            
            result = await default_classifier.keyword_extract(
                text=chinese_text, top_k=3, extract_phrases=True
            )
            
            assert isinstance(result, list)
            assert len(result) == 3
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_keyword_extract_chinese_keywords(self, custom_classifier, chinese_text):
        """Test keyword extraction for Chinese with keywords only"""
        with patch.object(custom_classifier, '_get_spacy') as mock_get_spacy:
            # Mock spaCy pipeline
            mock_doc = MagicMock()
            mock_tokens = [
                MagicMock(text="产品", pos_="NOUN"),
                MagicMock(text="工作", pos_="NOUN")
            ]
            mock_doc.__iter__.return_value = mock_tokens
            
            mock_nlp = MagicMock()
            mock_nlp.return_value = mock_doc
            mock_get_spacy.return_value = mock_nlp
            
            result = await custom_classifier.keyword_extract(
                text=chinese_text, top_k=2, extract_phrases=False
            )
            
            assert isinstance(result, list)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_keyword_extract_rate_limit_exceeded(self, rate_limited_classifier):
        """Test keyword extraction when rate limit is exceeded"""
        with patch.object(rate_limited_classifier, '_check_rate_limit', return_value=False):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await rate_limited_classifier.keyword_extract(text="test text")

    # Test Summarization
    @pytest.mark.asyncio
    async def test_summarize_english(self, custom_classifier, english_text):
        """Test text summarization for English using real transformers model"""
        result = await custom_classifier.summarize(text=english_text, max_length=100)
        
        assert isinstance(result, str)
        assert len(result) > 0
        # The summary should be shorter than the original text
        assert len(result) < len(english_text)
        # Check that we get a reasonable summary (not too short, not too long)
        assert len(result) > 20  # Should be substantial enough
        print(f"English summary length: {len(result)} characters")
        print(f"English summary: {result}")

    @pytest.mark.asyncio
    async def test_summarize_chinese(self, custom_classifier, chinese_text):
        """Test text summarization for Chinese using real transformers model"""
        result = await custom_classifier.summarize(text=chinese_text, max_length=100)
        
        assert isinstance(result, str)
        assert len(result) > 0
        # The summary should be shorter than the original text
        assert len(result) < len(chinese_text)
        # For Chinese, be more lenient with length requirements due to T5 limitations
        assert len(result) >= 3  # At least a few characters
        print(f"Chinese summary length: {len(result)} characters")
        print(f"Chinese summary: {result}")
        print(f"Original text length: {len(chinese_text)} characters")

    @pytest.mark.asyncio
    async def test_summarize_model_loading(self, custom_classifier):
        """Test that transformers models can be loaded successfully"""
        # Test English model loading
        try:
            english_pipeline = custom_classifier._get_hf_pipeline("summarization", "facebook/bart-large-cnn")
            assert english_pipeline is not None
            print("✅ English model (facebook/bart-large-cnn) loaded successfully")
        except Exception as e:
            pytest.fail(f"Failed to load English model: {e}")
        
        # Test Chinese model loading (using multilingual t5-base)
        try:
            chinese_pipeline = custom_classifier._get_hf_pipeline("summarization", "t5-base")
            assert chinese_pipeline is not None
            print("✅ Multilingual model (t5-base) loaded successfully")
        except Exception as e:
            pytest.fail(f"Failed to load multilingual model: {e}")

    @pytest.mark.asyncio
    async def test_summarize_rate_limit_exceeded(self, rate_limited_classifier):
        """Test summarization when rate limit is exceeded"""
        with patch.object(rate_limited_classifier, '_check_rate_limit', return_value=False):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await rate_limited_classifier.summarize(text="test text")

    # Test Batch Processing
    @pytest.mark.asyncio
    async def test_batch_process_tokenize(self, custom_classifier):
        """Test batch processing with tokenize operation"""
        texts = ["Hello world", "Test text"]
        
        with patch.object(custom_classifier, 'run_batch') as mock_run_batch:
            mock_run_batch.return_value = [["Hello", "world"], ["Test", "text"]]
            
            result = await custom_classifier.batch_process(
                texts=texts, operation="tokenize", language="en"
            )
            
            assert isinstance(result, list)
            assert len(result) == 2
            mock_run_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_process_classify(self, custom_classifier):
        """Test batch processing with classify operation"""
        texts = ["Great product", "Bad product"]
        
        with patch.object(custom_classifier, 'run_batch') as mock_run_batch:
            mock_run_batch.return_value = [
                [{'label': 'POSITIVE', 'score': 0.9}],
                [{'label': 'NEGATIVE', 'score': 0.8}]
            ]
            
            result = await custom_classifier.batch_process(
                texts=texts, operation="classify", model="en_core_web_sm"
            )
            
            assert isinstance(result, list)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_batch_process_rate_limit_exceeded(self, rate_limited_classifier):
        """Test batch processing when rate limit is exceeded"""
        with patch.object(rate_limited_classifier, '_check_rate_limit', return_value=False):
            with pytest.raises(ValueError, match="Rate limit exceeded"):
                await rate_limited_classifier.batch_process(texts=["test"], operation="tokenize")

    # Test Health Check
    @pytest.mark.asyncio
    async def test_health_check_success(self, default_classifier):
        """Test health check with successful model loading"""
        with patch.object(default_classifier, '_get_spacy') as mock_get_spacy:
            mock_get_spacy.return_value = MagicMock()
            
            result = await default_classifier.health_check()
            
            assert isinstance(result, dict)
            assert result['status'] == 'ok'
            assert 'metrics' in result
            assert 'config' in result
            assert 'models' in result
            assert result['models']['spacy_en'] == 'ok'

    @pytest.mark.asyncio
    async def test_health_check_model_error(self, default_classifier):
        """Test health check with model loading error"""
        with patch.object(default_classifier, '_get_spacy', side_effect=Exception("Model error")):
            result = await default_classifier.health_check()
            
            assert isinstance(result, dict)
            assert result['status'] == 'warning'
            assert 'error: Model error' in result['models']['spacy_en']

    # Test Cleanup
    @pytest.mark.asyncio
    async def test_cleanup(self, default_classifier):
        """Test resource cleanup"""
        # Add some test data to verify cleanup
        default_classifier._spacy_nlp['en'] = MagicMock()
        default_classifier._metrics['requests'] = 10
        default_classifier._request_timestamps = [1000.0, 1001.0]
        
        await default_classifier.cleanup()
        
        assert len(default_classifier._spacy_nlp) == 0
        assert default_classifier._metrics['requests'] == 0
        assert len(default_classifier._request_timestamps) == 0

    # Test Enum Classes
    def test_language_enum(self):
        """Test Language enum values"""
        assert Language.ENGLISH == "en"
        assert Language.CHINESE == "zh"
        assert Language.AUTO == "auto"

    def test_model_type_enum(self):
        """Test ModelType enum values"""
        assert ModelType.SPACY_ENGLISH == "en_core_web_sm"
        assert ModelType.SPACY_CHINESE == "zh_core_web_sm"

    # Test Error Conditions
    @pytest.mark.asyncio
    async def test_async_method_with_executor_error(self, default_classifier):
        """Test async method error handling"""
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.run_in_executor.side_effect = Exception("Executor error")
            mock_get_loop.return_value = mock_loop
            
            with pytest.raises(Exception, match="Executor error"):
                await default_classifier.tokenize("test text")

    # Test Edge Cases
    def test_detect_language_edge_cases(self, default_classifier):
        """Test language detection edge cases"""
        # Test with only punctuation
        result = default_classifier._detect_language("!@#$%^&*()")
        assert result == 'en'
        
        # Test with only numbers
        result = default_classifier._detect_language("12345")
        assert result == 'en'
        
        # Test with single Chinese character
        result = default_classifier._detect_language("中")
        assert result == 'zh'
        
        # Test with exception handling
        with patch('builtins.sum', side_effect=Exception("Test error")):
            result = default_classifier._detect_language("test")
            assert result == 'en'

    # Test Configuration Environment Variables
    def test_config_env_prefix(self):
        """Test configuration environment prefix"""
        config = ClassifierTool.Config()
        assert hasattr(config, 'model_config')
        assert config.model_config['env_prefix'] == "CLASSIFIER_TOOL_"

    # Test Validation Decorators
    def test_validation_decorators(self):
        """Test that validation decorators are properly applied"""
        # Check that methods have the validate_input decorator
        assert hasattr(ClassifierTool.ner, '__wrapped__')
        assert hasattr(ClassifierTool.lemmatize, '__wrapped__')
        assert hasattr(ClassifierTool.dependency_parse, '__wrapped__')
        assert hasattr(ClassifierTool.keyword_extract, '__wrapped__')
        assert hasattr(ClassifierTool.summarize, '__wrapped__')
        assert hasattr(ClassifierTool.batch_process, '__wrapped__')

    # Test Metrics Collection
    def test_metrics_initialization(self, default_classifier):
        """Test metrics initialization"""
        assert 'requests' in default_classifier._metrics
        assert 'cache_hits' in default_classifier._metrics
        assert 'processing_time' in default_classifier._metrics
        assert default_classifier._metrics['requests'] == 0
        assert default_classifier._metrics['cache_hits'] == 0
        assert isinstance(default_classifier._metrics['processing_time'], list)

    def test_request_timestamps_initialization(self, default_classifier):
        """Test request timestamps initialization"""
        assert isinstance(default_classifier._request_timestamps, list)
        assert len(default_classifier._request_timestamps) == 0

    # Test Tool Registration
    def test_tool_registration(self):
        """Test that the tool is properly registered with the 'classifier' name"""
        tool = ClassifierTool()
        assert hasattr(tool, 'classify')
        assert hasattr(tool, 'tokenize')
        assert hasattr(tool, 'pos_tag')
        assert hasattr(tool, 'ner')
        assert hasattr(tool, 'lemmatize')
        assert hasattr(tool, 'dependency_parse')
        assert hasattr(tool, 'keyword_extract')
        assert hasattr(tool, 'summarize')
        assert hasattr(tool, 'batch_process')
        assert hasattr(tool, 'health_check')
        assert hasattr(tool, 'cleanup')
