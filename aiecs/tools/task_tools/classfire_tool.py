from aiecs.tools import register_tool
from aiecs.tools.tool_executor import (
    validate_input,
)
from aiecs.tools.base_tool import BaseTool
import os
import re
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Lazy imports for heavy dependencies
rake_nltk = None
spacy = None


def _init_heavy_dependencies():
    """Initialize heavy dependencies when actually needed"""
    global rake_nltk, spacy

    if rake_nltk is None:
        try:
            import rake_nltk as _rake_nltk  # type: ignore[import-untyped]

            rake_nltk = _rake_nltk
        except ImportError:
            import logging

            logging.getLogger(__name__).error("rake_nltk not available")

    if spacy is None:
        try:
            import spacy as _spacy

            spacy = _spacy
        except ImportError:
            import logging

            logging.getLogger(__name__).warning("spacy not available (optional)")


# Enums for configuration options


class Language(str, Enum):
    ENGLISH = "en"
    CHINESE = "zh"
    AUTO = "auto"


class ModelType(str, Enum):
    SPACY_ENGLISH = "en_core_web_sm"
    SPACY_CHINESE = "zh_core_web_sm"


@register_tool("classifier")
class ClassifierTool(BaseTool):
    """
    Text classification, tokenization, POS tagging, NER, lemmatization, dependency parsing,
    keyword extraction, and summarization tool.

    Operations:
      - classify: Sentiment or topic classification.
      - tokenize: Tokenize text.
      - pos_tag: Part-of-speech tagging.
      - ner: Named entity recognition.
      - lemmatize: Lemmatize tokens.
      - dependency_parse: Dependency parsing.
      - keyword_extract: Extract key phrases.
      - summarize: Summarize text.
      - batch_process: Process multiple texts with any operation.

    Supports English (spaCy) and Chinese (Jieba, spaCy).
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the classifier tool
        
        Automatically reads from environment variables with CLASSIFIER_TOOL_ prefix.
        Example: CLASSIFIER_TOOL_MAX_WORKERS -> max_workers
        """

        model_config = SettingsConfigDict(env_prefix="CLASSIFIER_TOOL_")

        max_workers: int = Field(
            default=min(32, (os.cpu_count() or 4) * 2),
            description="Maximum number of worker threads",
        )
        pipeline_cache_ttl: int = Field(
            default=3600,
            description="Time-to-live for pipeline cache in seconds",
        )
        pipeline_cache_size: int = Field(default=10, description="Maximum number of pipeline cache entries")
        max_text_length: int = Field(default=10_000, description="Maximum text length in characters")
        spacy_model_en: str = Field(default="en_core_web_sm", description="spaCy model for English")
        spacy_model_zh: str = Field(default="zh_core_web_sm", description="spaCy model for Chinese")
        allowed_models: List[str] = Field(
            default=["en_core_web_sm", "zh_core_web_sm"],
            description="List of allowed spaCy models",
        )
        rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
        rate_limit_requests: int = Field(default=100, description="Maximum requests per window")
        rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
        use_rake_for_english: bool = Field(default=True, description="Use RAKE for English phrase extraction")

    # Base schema for text operations
    class BaseTextSchema(BaseModel):
        """Base schema for text operations"""

        text: str = Field(description="Text to process")

        @field_validator("text")
        @classmethod
        def check_length_and_content(cls, v: str) -> str:
            if len(v) > 10_000:  # Using a constant here for validation
                raise ValueError("Text length exceeds 10,000 characters")
            # Check for malicious patterns (e.g., SQL injection)
            if re.search(
                r"(\bSELECT\b|\bINSERT\b|\bDELETE\b|--|;|/\*)",
                v,
                re.IGNORECASE,
            ):
                raise ValueError("Text contains potentially malicious content")
            return v

    # Input schemas for operations
    class ClassifySchema(BaseTextSchema):
        """Schema for text classification"""

        model: Optional[str] = Field(default=None, description="Model to use for classification")
        language: Optional[Language] = Field(default=None, description="Language of the text")

        @field_validator("model")
        @classmethod
        def check_model(cls, v: Optional[str]) -> Optional[str]:
            allowed_models = ["en_core_web_sm", "zh_core_web_sm"]
            if v and v not in allowed_models:
                raise ValueError(f"Model '{v}' not in allowed spaCy models: {allowed_models}")
            return v

    class TokenizeSchema(BaseTextSchema):
        """Schema for text tokenization"""

        language: Optional[Language] = Field(default=None, description="Language of the text")

    class PosTagSchema(BaseTextSchema):
        """Schema for part-of-speech tagging"""

        language: Optional[Language] = Field(default=None, description="Language of the text")

    class NERSchema(BaseTextSchema):
        """Schema for named entity recognition"""

        language: Optional[Language] = Field(default=None, description="Language of the text")

    class LemmatizeSchema(BaseTextSchema):
        """Schema for lemmatization"""

        language: Optional[Language] = Field(default=None, description="Language of the text")

    class DependencyParseSchema(BaseTextSchema):
        """Schema for dependency parsing"""

        language: Optional[Language] = Field(default=None, description="Language of the text")

    class KeywordExtractSchema(BaseTextSchema):
        """Schema for keyword extraction"""

        top_k: int = Field(default=10, description="Number of keywords to extract")
        language: Optional[Language] = Field(default=None, description="Language of the text")
        extract_phrases: bool = Field(
            default=True,
            description="Whether to extract phrases or just keywords",
        )

    class SummarizeSchema(BaseTextSchema):
        """Schema for text summarization"""

        max_length: int = Field(default=150, description="Maximum length of the summary")
        language: Optional[Language] = Field(default=None, description="Language of the text")

    class BatchProcessSchema(BaseModel):
        """Schema for batch processing"""

        texts: List[str] = Field(description="List of texts to process")
        operation: str = Field(description="Operation to perform on each text")
        language: Optional[Language] = Field(default=None, description="Language of the texts")
        model: Optional[str] = Field(default=None, description="Model to use for processing")
        top_k: Optional[int] = Field(
            default=None,
            description="Number of keywords to extract (for keyword_extract)",
        )
        max_length: Optional[int] = Field(
            default=None,
            description="Maximum length of the summary (for summarize)",
        )

        @field_validator("texts")
        @classmethod
        def check_texts(cls, v: List[str]) -> List[str]:
            for text in v:
                if len(text) > 10_000:  # Using a constant here for validation
                    raise ValueError("Text length exceeds 10,000 characters")
                if re.search(
                    r"(\bSELECT\b|\bINSERT\b|\bDELETE\b|--|;|/\*)",
                    text,
                    re.IGNORECASE,
                ):
                    raise ValueError("Text contains potentially malicious content")
            return v

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ClassifierTool with settings and resources.

        Args:
            config (Dict, optional): Configuration overrides for ClassifierSettings.

        Raises:
            ValueError: If config contains invalid settings.
        
        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/classifier.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)
        """
        super().__init__(config)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        # Set up logger
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Initialize resources
        self._spacy_nlp: Dict[str, Any] = {}  # Language -> spaCy pipeline
        self._metrics = {"requests": 0, "cache_hits": 0, "processing_time": []}
        self._request_timestamps: List[float] = []

    def _get_sentiment_lexicon(self, language: str) -> Dict[str, float]:
        """
        Get sentiment lexicon for the specified language.

        Args:
            language (str): Language code ('en', 'zh').

        Returns:
            Dict[str, float]: Sentiment lexicon with word -> score mapping.
        """
        if language == "en":
            # Simple English sentiment lexicon
            return {
                "good": 1.0,
                "great": 1.5,
                "excellent": 2.0,
                "amazing": 2.0,
                "wonderful": 1.5,
                "fantastic": 2.0,
                "awesome": 1.5,
                "perfect": 2.0,
                "love": 1.5,
                "like": 1.0,
                "happy": 1.5,
                "pleased": 1.0,
                "satisfied": 1.0,
                "positive": 1.0,
                "best": 2.0,
                "bad": -1.0,
                "terrible": -2.0,
                "awful": -2.0,
                "horrible": -2.0,
                "hate": -2.0,
                "dislike": -1.0,
                "sad": -1.5,
                "angry": -1.5,
                "disappointed": -1.5,
                "negative": -1.0,
                "worst": -2.0,
                "poor": -1.0,
                "fail": -1.5,
                "wrong": -1.0,
                "problem": -1.0,
            }
        else:  # Chinese
            return {
                "好": 1.0,
                "很好": 1.5,
                "非常好": 2.0,
                "棒": 1.5,
                "优秀": 2.0,
                "完美": 2.0,
                "喜欢": 1.5,
                "爱": 2.0,
                "满意": 1.0,
                "开心": 1.5,
                "高兴": 1.5,
                "积极": 1.0,
                "坏": -1.0,
                "很坏": -1.5,
                "糟糕": -2.0,
                "讨厌": -2.0,
                "恨": -2.0,
                "失望": -1.5,
                "生气": -1.5,
                "愤怒": -2.0,
                "消极": -1.0,
                "问题": -1.0,
                "错误": -1.0,
                "失败": -1.5,
            }

    def _get_spacy(self, language: str) -> Any:
        """
        Get a spaCy pipeline for the specified language.

        Args:
            language (str): Language code ('en', 'zh').

        Returns:
            Any: spaCy NLP object.
        """
        global spacy
        if spacy is None:
            try:
                import spacy as spacy_module

                spacy = spacy_module
            except ImportError:
                raise ImportError("spaCy is required but not installed. Please install it with: pip install spacy")

        model = self.config.spacy_model_zh if language == "zh" else self.config.spacy_model_en
        return spacy.load(model, disable=["textcat"])

    def _detect_language(self, text: str) -> str:
        """
        Detect the language of the input text using character analysis.

        Args:
            text (str): Input text.

        Returns:
            str: Language code ('en', 'zh', or 'en' for unknown).
        """
        try:
            # Count Chinese characters (CJK Unified Ideographs)
            chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
            total_chars = len([char for char in text if char.isalpha()])

            if total_chars == 0:
                return "en"

            # If more than 30% are Chinese characters, consider it Chinese
            chinese_ratio = chinese_chars / total_chars
            return "zh" if chinese_ratio > 0.3 else "en"
        except Exception:
            return "en"

    def _check_rate_limit(self) -> bool:
        """
        Check if the request is within rate limits.

        Returns:
            bool: True if within limits, False otherwise.
        """
        if not self.config.rate_limit_enabled:
            return True

        current_time = time.time()

        # Get lock from executor
        with self._executor.get_lock("rate_limit"):
            # Remove timestamps outside the window
            self._request_timestamps = [ts for ts in self._request_timestamps if current_time - ts <= self.config.rate_limit_window]

            # Check if we're at the limit
            if len(self._request_timestamps) >= self.config.rate_limit_requests:
                return False

            # Add current timestamp
            self._request_timestamps.append(current_time)
            return True

    def _extract_english_phrases(self, text: str, top_k: int) -> List[str]:
        """
        Extract key phrases from English text using RAKE.

        Args:
            text (str): Input text.
            top_k (int): Number of phrases to extract.

        Returns:
            List[str]: Extracted phrases.
        """
        try:
            # Initialize heavy dependencies if needed
            _init_heavy_dependencies()

            if rake_nltk is None:
                raise ImportError("rake_nltk not available")

            rake = rake_nltk.Rake()
            rake.extract_keywords_from_text(text)
            phrases = rake.get_ranked_phrases()[:top_k]
            return phrases
        except Exception as e:
            self.logger.error(f"Error extracting English phrases: {e}")
            # Fallback to simple keyword extraction
            nlp = self._get_spacy("en")
            doc = nlp(text)
            keywords = [token.text for token in doc if token.pos_ in ("NOUN", "PROPN")][:top_k]
            return keywords

    def _extract_chinese_phrases(self, text: str, top_k: int) -> List[str]:
        """
        Extract key phrases from Chinese text using spaCy.

        Args:
            text (str): Input text.
            top_k (int): Number of phrases to extract.

        Returns:
            List[str]: Extracted phrases.
        """
        try:
            nlp = self._get_spacy("zh")
            doc = nlp(text)

            # Extract noun phrases and named entities
            phrases = []

            # Add noun chunks
            for chunk in doc.noun_chunks:
                if len(chunk.text.strip()) > 1:
                    phrases.append(chunk.text.strip())

            # Add named entities
            for ent in doc.ents:
                if len(ent.text.strip()) > 1:
                    phrases.append(ent.text.strip())

            # Add important nouns and proper nouns
            for token in doc:
                if token.pos_ in ("NOUN", "PROPN") and len(token.text.strip()) > 1:
                    phrases.append(token.text.strip())

            # Remove duplicates and return top_k
            unique_phrases = list(dict.fromkeys(phrases))  # Preserve order
            return unique_phrases[:top_k]

        except Exception as e:
            self.logger.error(f"Error extracting Chinese phrases with spaCy: {e}")
            # Fallback to simple noun extraction
            try:
                nlp = self._get_spacy("zh")
                doc = nlp(text)
                nouns = [token.text for token in doc if token.pos_ in ("NOUN", "PROPN")]
                return nouns[:top_k]
            except Exception:
                return []

    def _get_hf_pipeline(self, task: str, model: str):
        """
        Get a Hugging Face transformers pipeline for the specified task and model.

        Args:
            task (str): The task type (e.g., "summarization").
            model (str): The model name.

        Returns:
            Any: Hugging Face pipeline object.

        Raises:
            ImportError: If transformers library is not available.
            ValueError: If the pipeline creation fails.
        """
        try:
            from transformers import pipeline  # type: ignore[import-not-found]

            return pipeline(task, model=model)
        except ImportError:
            raise ImportError("transformers library is required for summarization but not installed. Please install it with: pip install transformers")
        except Exception as e:
            raise ValueError(f"Error creating pipeline for task '{task}' with model '{model}': {e}")

    async def classify(
        self,
        text: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform sentiment classification on text using spaCy and lexicon-based approach.

        Args:
            text (str): Text to classify.
            model (Optional[str]): spaCy model to use (optional, auto-detected).
            language (Optional[str]): Language of the text.

        Returns:
            List[Dict[str, Any]]: Classification results [{'label': str, 'score': float}].
        """
        if not self._check_rate_limit():
            raise ValueError("Rate limit exceeded. Please try again later.")

        language = language or self._detect_language(text)

        # Get spaCy pipeline and sentiment lexicon
        nlp = await asyncio.get_event_loop().run_in_executor(None, self._get_spacy, language)

        sentiment_lexicon = self._get_sentiment_lexicon(language)

        # Process text with spaCy
        doc = await asyncio.get_event_loop().run_in_executor(None, nlp, text)

        # Calculate sentiment score
        sentiment_score = 0.0
        word_count = 0

        for token in doc:
            if not token.is_stop and not token.is_punct and token.text.lower() in sentiment_lexicon:
                sentiment_score += sentiment_lexicon[token.text.lower()]
                word_count += 1

        # Normalize score
        if word_count > 0:
            sentiment_score = sentiment_score / word_count

        # Determine label and confidence
        if sentiment_score > 0.1:
            label = "POSITIVE"
            confidence = min(0.9, 0.5 + abs(sentiment_score) * 0.4)
        elif sentiment_score < -0.1:
            label = "NEGATIVE"
            confidence = min(0.9, 0.5 + abs(sentiment_score) * 0.4)
        else:
            label = "NEUTRAL"
            confidence = 0.6

        return [{"label": label, "score": confidence}]

    async def tokenize(self, text: str, language: Optional[str] = None) -> List[str]:
        """
        Tokenize text into words or tokens using spaCy.

        Args:
            text (str): Text to tokenize.
            language (Optional[str]): Language of the text.

        Returns:
            List[str]: List of tokens.
        """
        if not self._check_rate_limit():
            raise ValueError("Rate limit exceeded. Please try again later.")

        language = language or self._detect_language(text)

        nlp = await asyncio.get_event_loop().run_in_executor(None, self._get_spacy, language)

        doc = await asyncio.get_event_loop().run_in_executor(None, nlp, text)

        return [token.text for token in doc]

    async def pos_tag(self, text: str, language: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Perform part-of-speech tagging using spaCy, returning (token, pos) pairs.

        Args:
            text (str): Text to tag.
            language (Optional[str]): Language of the text.

        Returns:
            List[Tuple[str, str]]: List of (token, POS tag) tuples.
        """
        if not self._check_rate_limit():
            raise ValueError("Rate limit exceeded. Please try again later.")

        language = language or self._detect_language(text)

        nlp = await asyncio.get_event_loop().run_in_executor(None, self._get_spacy, language)

        doc = await asyncio.get_event_loop().run_in_executor(None, nlp, text)

        return [(token.text, token.pos_) for token in doc]

    @validate_input(NERSchema)
    async def ner(self, text: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform named entity recognition.

        Args:
            text (str): Text to analyze.
            language (Optional[str]): Language of the text.

        Returns:
            List[Dict[str, Any]]: List of named entities with text, label, start, and end.
        """
        if not self._check_rate_limit():
            raise ValueError("Rate limit exceeded. Please try again later.")

        language = language or self._detect_language(text)

        nlp = await asyncio.get_event_loop().run_in_executor(None, self._get_spacy, language)

        doc = await asyncio.get_event_loop().run_in_executor(None, nlp, text)

        return [
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            }
            for ent in doc.ents
        ]

    @validate_input(LemmatizeSchema)
    async def lemmatize(self, text: str, language: Optional[str] = None) -> List[str]:
        """
        Lemmatize tokens in text using spaCy.

        Args:
            text (str): Text to lemmatize.
            language (Optional[str]): Language of the text.

        Returns:
            List[str]: List of lemmatized tokens.
        """
        if not self._check_rate_limit():
            raise ValueError("Rate limit exceeded. Please try again later.")

        language = language or self._detect_language(text)

        nlp = await asyncio.get_event_loop().run_in_executor(None, self._get_spacy, language)

        doc = await asyncio.get_event_loop().run_in_executor(None, nlp, text)

        # For Chinese, lemma might be the same as text, but spaCy handles it
        # consistently
        return [token.lemma_ for token in doc]

    @validate_input(DependencyParseSchema)
    async def dependency_parse(self, text: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform dependency parsing using spaCy (supports both English and Chinese).

        Args:
            text (str): Text to parse.
            language (Optional[str]): Language of the text.

        Returns:
            List[Dict[str, Any]]: List of tokens with dependency information.
        """
        if not self._check_rate_limit():
            raise ValueError("Rate limit exceeded. Please try again later.")

        language = language or self._detect_language(text)

        nlp = await asyncio.get_event_loop().run_in_executor(None, self._get_spacy, language)

        doc = await asyncio.get_event_loop().run_in_executor(None, nlp, text)

        return [
            {
                "text": token.text,
                "head": token.head.text,
                "dep": token.dep_,
                "pos": token.pos_,
            }
            for token in doc
        ]

    @validate_input(KeywordExtractSchema)
    async def keyword_extract(
        self,
        text: str,
        top_k: int = 10,
        language: Optional[str] = None,
        extract_phrases: bool = True,
    ) -> List[str]:
        """
        Extract keywords or key phrases from text using spaCy.

        Args:
            text (str): Text to analyze.
            top_k (int): Number of keywords to extract.
            language (Optional[str]): Language of the text.
            extract_phrases (bool): Whether to extract phrases or just keywords.

        Returns:
            List[str]: List of extracted keywords or phrases.
        """
        if not self._check_rate_limit():
            raise ValueError("Rate limit exceeded. Please try again later.")

        language = language or self._detect_language(text)

        if language == "zh":
            if extract_phrases:
                return await asyncio.get_event_loop().run_in_executor(None, self._extract_chinese_phrases, text, top_k)
            else:
                # Extract simple keywords using spaCy
                nlp = await asyncio.get_event_loop().run_in_executor(None, self._get_spacy, language)

                doc = await asyncio.get_event_loop().run_in_executor(None, nlp, text)

                keywords = [token.text for token in doc if token.pos_ in ("NOUN", "PROPN")][:top_k]
                return keywords
        else:  # English or other languages
            if extract_phrases and self.config.use_rake_for_english:
                return await asyncio.get_event_loop().run_in_executor(None, self._extract_english_phrases, text, top_k)
            else:
                nlp = await asyncio.get_event_loop().run_in_executor(None, self._get_spacy, language)

                doc = await asyncio.get_event_loop().run_in_executor(None, nlp, text)

                keywords = [token.text for token in doc if token.pos_ in ("NOUN", "PROPN")][:top_k]
                return keywords

    @validate_input(SummarizeSchema)
    async def summarize(self, text: str, max_length: int = 150, language: Optional[str] = None) -> str:
        """
        Summarize text.

        Args:
            text (str): Text to summarize.
            max_length (int): Maximum length of the summary.
            language (Optional[str]): Language of the text.

        Returns:
            str: Summarized text.
        """
        if not self._check_rate_limit():
            raise ValueError("Rate limit exceeded. Please try again later.")

        language = language or self._detect_language(text)
        # Use appropriate models for summarization
        if language == "en":
            model = "facebook/bart-large-cnn"
        else:
            # For Chinese and other languages, use a multilingual model
            # For now, use t5-base, but consider using a Chinese-specific model
            # in the future
            model = "t5-base"

        pipe = await asyncio.get_event_loop().run_in_executor(None, self._get_hf_pipeline, "summarization", model)

        # Different models use different parameter names for length control
        if model.startswith("t5"):
            # T5 models use max_new_tokens instead of max_length
            # For Chinese text, use a more conservative approach
            if language == "zh":
                # Chinese text: use character count and be more conservative
                input_chars = len(text)
                max_new_tokens = min(max_length, max(input_chars // 4, 5))
                min_new_tokens = 2
            else:
                # English text: use word count
                input_words = len(text.split())
                max_new_tokens = min(max_length, max(input_words // 2, 10))
                min_new_tokens = 5

            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: pipe(
                    text,
                    max_new_tokens=max_new_tokens,
                    min_new_tokens=min_new_tokens,
                    do_sample=False,
                )[
                    0
                ]["summary_text"],
            )
        else:
            # BART and other models use max_length
            if language == "zh":
                # Chinese text: use character count
                input_chars = len(text)
                max_len = min(max_length, max(input_chars // 4, 10))
                min_len = 5
            else:
                # English text: use word count
                input_words = len(text.split())
                max_len = min(max_length, max(input_words // 2, 20))
                min_len = 10

            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: pipe(
                    text,
                    max_length=max_len,
                    min_length=min_len,
                    do_sample=False,
                )[
                    0
                ]["summary_text"],
            )

        return result

    @validate_input(BatchProcessSchema)
    async def batch_process(
        self,
        texts: List[str],
        operation: str,
        language: Optional[str] = None,
        model: Optional[str] = None,
        top_k: Optional[int] = None,
        max_length: Optional[int] = None,
    ) -> List[Any]:
        """
        Process multiple texts with the specified operation.

        Args:
            texts (List[str]): List of texts to process.
            operation (str): Operation to perform on each text.
            language (Optional[str]): Language of the texts.
            model (Optional[str]): Model to use for processing.
            top_k (Optional[int]): Number of keywords to extract (for keyword_extract).
            max_length (Optional[int]): Maximum length of the summary (for summarize).

        Returns:
            List[Any]: List of operation results.
        """
        if not self._check_rate_limit():
            raise ValueError("Rate limit exceeded. Please try again later.")

        # Prepare operations to execute in batch
        operations = []
        for text in texts:
            kwargs: Dict[str, Any] = {"text": text}
            if language:
                kwargs["language"] = language
            if model and operation == "classify":
                kwargs["model"] = model
            if top_k and operation == "keyword_extract":
                kwargs["top_k"] = top_k
            if max_length and operation == "summarize":
                kwargs["max_length"] = max_length

            operations.append({"op": operation, "kwargs": kwargs})

        # Execute batch operations
        return await self.run_batch(operations)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the tool.

        Returns:
            Dict[str, Any]: Health check results.
        """
        result = {
            "status": "ok",
            "metrics": {
                "requests": self._metrics["requests"],
                "cache_hits": self._metrics["cache_hits"],
                "avg_processing_time": (
                    sum(float(t) for t in processing_times) / len(processing_times)
                    if (processing_times := self._metrics.get("processing_time")) and isinstance(processing_times, list) and len(processing_times) > 0
                    else 0.0
                ),
            },
            "config": {
                "max_workers": self.config.max_workers,
                "pipeline_cache_size": self.config.pipeline_cache_size,
                "rate_limit_enabled": self.config.rate_limit_enabled,
                "rate_limit_requests": self.config.rate_limit_requests,
                "rate_limit_window": self.config.rate_limit_window,
            },
        }

        # Check if models can be loaded
        try:
            await asyncio.get_event_loop().run_in_executor(None, self._get_spacy, "en")
            result["models"] = {"spacy_en": "ok"}
        except Exception as e:
            result["status"] = "warning"
            result["models"] = {"spacy_en": f"error: {str(e)}"}

        return result

    async def cleanup(self) -> None:
        """
        Clean up resources used by the tool.
        """
        # Clear spaCy models
        self._spacy_nlp.clear()

        # Clear metrics
        self._metrics = {"requests": 0, "cache_hits": 0, "processing_time": []}

        # Clear rate limiting data
        self._request_timestamps = []

        self.logger.info("ClassifierTool resources cleaned up")
