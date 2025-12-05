import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class ProcessingMode(str, Enum):
    """AI document processing modes"""

    SUMMARIZE = "summarize"
    EXTRACT_INFO = "extract_info"
    ANALYZE = "analyze"
    TRANSLATE = "translate"
    CLASSIFY = "classify"
    ANSWER_QUESTIONS = "answer_questions"
    CUSTOM = "custom"


class AIProvider(str, Enum):
    """Supported AI providers"""

    OPENAI = "openai"
    VERTEX_AI = "vertex_ai"
    XAI = "xai"
    LOCAL = "local"


class AIDocumentOrchestratorError(Exception):
    """Base exception for AI Document Orchestrator errors"""


class AIProviderError(AIDocumentOrchestratorError):
    """Raised when AI provider operations fail"""


class ProcessingError(AIDocumentOrchestratorError):
    """Raised when document processing fails"""


@register_tool("ai_document_orchestrator")
class AIDocumentOrchestrator(BaseTool):
    """
    AI-powered document processing orchestrator that:
    1. Coordinates document parsing with AI analysis
    2. Manages AI provider interactions
    3. Handles complex document processing workflows
    4. Provides intelligent content analysis and extraction

    Integrates with:
    - DocumentParserTool for document parsing
    - Various AI providers for content analysis
    - Existing AIECS infrastructure
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the AI document orchestrator tool
        
        Automatically reads from environment variables with AI_DOC_ORCHESTRATOR_ prefix.
        Example: AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER -> default_ai_provider
        """

        model_config = SettingsConfigDict(env_prefix="AI_DOC_ORCHESTRATOR_")

        default_ai_provider: str = Field(default="openai", description="Default AI provider to use")
        max_chunk_size: int = Field(default=4000, description="Maximum chunk size for AI processing")
        max_concurrent_requests: int = Field(default=5, description="Maximum concurrent AI requests")
        default_temperature: float = Field(default=0.1, description="Default temperature for AI model")
        max_tokens: int = Field(default=2000, description="Maximum tokens for AI response")
        timeout: int = Field(default=60, description="Timeout in seconds for AI operations")

    def __init__(self, config: Optional[Dict] = None, **kwargs):
        """Initialize AI Document Orchestrator with settings

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/ai_document_orchestrator.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)

        Args:
            config: Optional configuration overrides
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        self.logger = logging.getLogger(__name__)

        # Initialize document parser
        self._init_document_parser()

        # Initialize AI providers
        self._init_ai_providers()

        # Processing templates
        self._init_processing_templates()

    def _init_document_parser(self):
        """Initialize document parser tool"""
        try:
            from aiecs.tools.docs.document_parser_tool import (
                DocumentParserTool,
            )

            self.document_parser = DocumentParserTool()
        except ImportError:
            self.logger.error("DocumentParserTool not available")
            self.document_parser = None

    def _init_ai_providers(self):
        """Initialize AI providers"""
        self.ai_providers = {}

        try:
            # Initialize AIECS client for AI operations
            from aiecs import AIECS

            self.aiecs_client = AIECS()
            self.ai_providers["aiecs"] = self.aiecs_client
        except ImportError:
            self.logger.warning("AIECS client not available")
            self.aiecs_client = None

    def _init_processing_templates(self):
        """Initialize processing templates for different AI tasks"""
        self.processing_templates = {
            ProcessingMode.SUMMARIZE: {
                "system_prompt": "You are an expert document summarizer. Create concise, informative summaries.",
                "user_prompt_template": "Please summarize the following document content:\n\n{content}\n\nProvide a clear, structured summary highlighting the key points.",
            },
            ProcessingMode.EXTRACT_INFO: {
                "system_prompt": "You are an expert information extractor. Extract specific information from documents.",
                "user_prompt_template": (
                    "Extract the following information from the document:\n{extraction_criteria}\n\n" "Document content:\n{content}\n\nProvide the extracted information in a structured format."
                ),
            },
            ProcessingMode.ANALYZE: {
                "system_prompt": "You are an expert document analyzer. Provide thorough analysis of document content.",
                "user_prompt_template": (
                    "Analyze the following document content and provide insights:\n\n{content}\n\n"
                    "Include analysis of:\n- Main themes and topics\n- Key findings\n- Important details\n"
                    "- Overall structure and organization"
                ),
            },
            ProcessingMode.TRANSLATE: {
                "system_prompt": "You are an expert translator. Provide accurate translations while preserving meaning and context.",
                "user_prompt_template": "Translate the following document content to {target_language}:\n\n{content}\n\nMaintain the original structure and formatting where possible.",
            },
            ProcessingMode.CLASSIFY: {
                "system_prompt": "You are an expert document classifier. Classify documents accurately based on their content.",
                "user_prompt_template": (
                    "Classify the following document content into the appropriate categories:\n\n"
                    "Categories: {categories}\n\nDocument content:\n{content}\n\n"
                    "Provide the classification with confidence scores and reasoning."
                ),
            },
            ProcessingMode.ANSWER_QUESTIONS: {
                "system_prompt": "You are an expert document analyst. Answer questions based on document content accurately.",
                "user_prompt_template": (
                    "Based on the following document content, answer these questions:\n\nQuestions:\n{questions}\n\n"
                    "Document content:\n{content}\n\nProvide clear, accurate answers with references to the "
                    "relevant parts of the document."
                ),
            },
            ProcessingMode.CUSTOM: {
                "system_prompt": "You are an expert document analyst. Follow the custom instructions provided.",
                "user_prompt_template": "{custom_prompt}\n\nDocument content:\n{content}\n\nPlease provide your analysis based on the custom instructions above.",
            },
        }

    # Schema definitions
    class ProcessDocumentSchema(BaseModel):
        """Schema for process_document operation"""

        source: str = Field(description="URL or file path to the document")
        processing_mode: ProcessingMode = Field(description="AI processing mode to apply")
        ai_provider: Optional[AIProvider] = Field(default=None, description="AI provider to use")
        processing_params: Optional[Dict[str, Any]] = Field(default=None, description="Additional processing parameters")
        parse_params: Optional[Dict[str, Any]] = Field(default=None, description="Document parsing parameters")
        ai_params: Optional[Dict[str, Any]] = Field(default=None, description="AI provider parameters")

    class BatchProcessSchema(BaseModel):
        """Schema for batch_process_documents operation"""

        sources: List[str] = Field(description="List of URLs or file paths")
        processing_mode: ProcessingMode = Field(description="AI processing mode to apply")
        ai_provider: Optional[AIProvider] = Field(default=None, description="AI provider to use")
        processing_params: Optional[Dict[str, Any]] = Field(default=None, description="Additional processing parameters")
        max_concurrent: Optional[int] = Field(default=None, description="Maximum concurrent processing")

    class AnalyzeDocumentSchema(BaseModel):
        """Schema for analyze_document operation (AI-first approach)"""

        source: str = Field(description="URL or file path to the document")
        analysis_type: str = Field(description="Type of analysis to perform")
        custom_prompt: Optional[str] = Field(default=None, description="Custom AI prompt for analysis")
        ai_provider: Optional[AIProvider] = Field(default=None, description="AI provider to use")

    def process_document(
        self,
        source: str,
        processing_mode: ProcessingMode,
        ai_provider: Optional[AIProvider] = None,
        processing_params: Optional[Dict[str, Any]] = None,
        parse_params: Optional[Dict[str, Any]] = None,
        ai_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a document using AI with intelligent orchestration

        Args:
            source: URL or file path to document
            processing_mode: AI processing mode to apply
            ai_provider: AI provider to use (optional)
            processing_params: Additional processing parameters
            parse_params: Document parsing parameters
            ai_params: AI provider parameters

        Returns:
            Dict containing processed results and metadata
        """
        try:
            start_time = datetime.now()

            # Step 1: Parse the document
            self.logger.info(f"Starting document processing: {source}")
            parsed_result = self._parse_document(source, parse_params or {})

            # Step 2: Prepare content for AI processing
            content = self._prepare_content_for_ai(parsed_result, processing_mode)

            # Step 3: Process with AI
            provider = ai_provider or AIProvider(self.config.default_ai_provider)
            ai_result = self._process_with_ai(
                content,
                processing_mode,
                provider,
                processing_params or {},
                ai_params or {},
            )

            # Step 4: Combine results
            result = {
                "source": source,
                "processing_mode": processing_mode,
                "ai_provider": ai_provider or self.config.default_ai_provider,
                "document_info": {
                    "type": parsed_result.get("document_type"),
                    "detection_confidence": parsed_result.get("detection_confidence"),
                    "content_stats": parsed_result.get("content_stats"),
                },
                "ai_result": ai_result,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "processing_duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            # Step 5: Post-process if needed
            result = self._post_process_result(result, processing_mode, processing_params or {})

            return result

        except Exception as e:
            raise ProcessingError(f"Document processing failed: {str(e)}")

    async def process_document_async(
        self,
        source: str,
        processing_mode: ProcessingMode,
        ai_provider: Optional[AIProvider] = None,
        processing_params: Optional[Dict[str, Any]] = None,
        parse_params: Optional[Dict[str, Any]] = None,
        ai_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Async version of process_document"""
        return await asyncio.to_thread(
            self.process_document,
            source=source,
            processing_mode=processing_mode,
            ai_provider=ai_provider,
            processing_params=processing_params,
            parse_params=parse_params,
            ai_params=ai_params,
        )

    def batch_process_documents(
        self,
        sources: List[str],
        processing_mode: ProcessingMode,
        ai_provider: Optional[AIProvider] = None,
        processing_params: Optional[Dict[str, Any]] = None,
        max_concurrent: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process multiple documents in batch with intelligent orchestration

        Args:
            sources: List of URLs or file paths
            processing_mode: AI processing mode to apply
            ai_provider: AI provider to use
            processing_params: Additional processing parameters
            max_concurrent: Maximum concurrent processing

        Returns:
            Dict containing batch processing results
        """
        try:
            start_time = datetime.now()
            max_concurrent = max_concurrent or self.config.max_concurrent_requests

            # Process documents in batches
            results = asyncio.run(
                self._batch_process_async(
                    sources,
                    processing_mode,
                    ai_provider,
                    processing_params,
                    max_concurrent,
                )
            )

            # Aggregate results
            batch_result = {
                "sources": sources,
                "processing_mode": processing_mode,
                "ai_provider": ai_provider or self.config.default_ai_provider,
                "total_documents": len(sources),
                "successful_documents": len([r for r in results if r.get("status") == "success"]),
                "failed_documents": len([r for r in results if r.get("status") == "error"]),
                "results": results,
                "batch_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "total_duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            return batch_result

        except Exception as e:
            raise ProcessingError(f"Batch processing failed: {str(e)}")

    def analyze_document(
        self,
        source: str,
        analysis_type: str,
        custom_prompt: Optional[str] = None,
        ai_provider: Optional[AIProvider] = None,
    ) -> Dict[str, Any]:
        """
        Perform AI-first document analysis

        Args:
            source: URL or file path to document
            analysis_type: Type of analysis to perform
            custom_prompt: Custom AI prompt for analysis
            ai_provider: AI provider to use

        Returns:
            Dict containing analysis results
        """
        try:
            # Parse document first
            parsed_result = self._parse_document(source, {})
            content = parsed_result.get("content", "")

            # Prepare AI prompt
            if custom_prompt:
                prompt = custom_prompt.format(content=content, analysis_type=analysis_type)
            else:
                prompt = f"Perform {analysis_type} analysis on the following document:\n\n{content}"

            # Process with AI
            provider = ai_provider or AIProvider(self.config.default_ai_provider)
            ai_result = self._call_ai_provider(prompt, provider, {})

            return {
                "source": source,
                "analysis_type": analysis_type,
                "document_info": {
                    "type": parsed_result.get("document_type"),
                    "content_stats": parsed_result.get("content_stats"),
                },
                "analysis_result": ai_result,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            raise ProcessingError(f"Document analysis failed: {str(e)}")

    def _parse_document(self, source: str, parse_params: Dict[str, Any]) -> Dict[str, Any]:
        """Parse document using DocumentParserTool"""
        if not self.document_parser:
            raise ProcessingError("DocumentParserTool not available")

        try:
            return self.document_parser.parse_document(source, **parse_params)
        except Exception as e:
            raise ProcessingError(f"Document parsing failed: {str(e)}")

    def _prepare_content_for_ai(self, parsed_result: Dict[str, Any], processing_mode: ProcessingMode) -> str:
        """Prepare parsed content for AI processing"""
        content = parsed_result.get("content", "")

        if isinstance(content, dict):
            # Extract text from structured content
            text_content = content.get("text", str(content))
        else:
            text_content = str(content)

        # Chunk content if too large
        max_size = self.config.max_chunk_size
        if len(text_content) > max_size:
            # For now, truncate - could implement smart chunking
            text_content = text_content[:max_size] + "\n\n[Content truncated...]"

        return text_content

    def _process_with_ai(
        self,
        content: str,
        processing_mode: ProcessingMode,
        ai_provider: AIProvider,
        processing_params: Dict[str, Any],
        ai_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process content with AI based on processing mode"""
        try:
            # Get processing template
            template = self.processing_templates.get(processing_mode)
            if not template:
                raise ProcessingError(f"No template found for processing mode: {processing_mode}")

            # Format prompt
            prompt = self._format_prompt(template, content, processing_params)

            # Call AI provider
            ai_result = self._call_ai_provider(prompt, ai_provider, ai_params)

            return {
                "processing_mode": processing_mode,
                "prompt_used": prompt,
                "ai_response": ai_result,
                "ai_provider": ai_provider,
            }

        except Exception as e:
            raise AIProviderError(f"AI processing failed: {str(e)}")

    def _format_prompt(self, template: Dict[str, str], content: str, params: Dict[str, Any]) -> str:
        """Format AI prompt using template and parameters"""
        user_prompt = template["user_prompt_template"]

        # Replace content placeholder
        formatted_prompt = user_prompt.replace("{content}", content)

        # Replace other parameters
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if placeholder in formatted_prompt:
                formatted_prompt = formatted_prompt.replace(placeholder, str(value))

        return formatted_prompt

    def _call_ai_provider(self, prompt: str, ai_provider: AIProvider, ai_params: Dict[str, Any]) -> str:
        """Call AI provider with prompt"""
        try:
            if self.aiecs_client:
                # Use AIECS client for AI operations
                from aiecs.domain.task.task_context import TaskContext

                task_context = TaskContext(
                    data={
                        "task_id": f"doc_processing_{datetime.now().timestamp()}",
                        "task_type": "document_processing",
                        "input_data": {"prompt": prompt},
                        "metadata": ai_params,
                    },
                    task_dir="./tasks",
                )

                # This would need to be adapted based on actual AIECS API
                result = self.aiecs_client.process_task(task_context)
                return result.get("response", "")
            else:
                # Fallback to direct AI provider calls
                return self._direct_ai_call(prompt, ai_provider, ai_params)

        except Exception as e:
            raise AIProviderError(f"AI provider call failed: {str(e)}")

    def _direct_ai_call(self, prompt: str, ai_provider: AIProvider, ai_params: Dict[str, Any]) -> str:
        """Direct AI provider call (fallback)"""
        # This is a placeholder for direct AI provider integration
        # In a real implementation, you would integrate with specific AI APIs
        self.logger.warning("Using mock AI response - implement actual AI provider integration")
        return f"Mock AI response for prompt: {prompt[:100]}..."

    async def _batch_process_async(
        self,
        sources: List[str],
        processing_mode: ProcessingMode,
        ai_provider: Optional[AIProvider],
        processing_params: Optional[Dict[str, Any]],
        max_concurrent: int,
    ) -> List[Dict[str, Any]]:
        """Process documents in parallel with concurrency control"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single(source: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result = await self.process_document_async(
                        source=source,
                        processing_mode=processing_mode,
                        ai_provider=ai_provider,
                        processing_params=processing_params,
                    )
                    return {
                        "source": source,
                        "status": "success",
                        "result": result,
                    }
                except Exception as e:
                    return {
                        "source": source,
                        "status": "error",
                        "error": str(e),
                    }

        tasks = [process_single(source) for source in sources]
        return await asyncio.gather(*tasks)

    def _post_process_result(
        self,
        result: Dict[str, Any],
        processing_mode: ProcessingMode,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Post-process results based on processing mode"""
        # Add any post-processing logic here
        # For example, formatting, validation, additional analysis

        if processing_mode == ProcessingMode.EXTRACT_INFO:
            # Validate extracted information
            result["validation"] = self._validate_extracted_info(result, params)
        elif processing_mode == ProcessingMode.CLASSIFY:
            # Add confidence scoring
            result["confidence_analysis"] = self._analyze_classification_confidence(result)

        return result

    def _validate_extracted_info(self, result: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, str]:
        """Validate extracted information"""
        # Placeholder for validation logic
        return {"status": "validated", "notes": "Validation completed"}

    def _analyze_classification_confidence(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze classification confidence"""
        # Placeholder for confidence analysis
        return {
            "overall_confidence": 0.85,
            "factors": ["content_quality", "model_certainty"],
        }

    # Utility methods for custom processing
    def create_custom_processor(self, system_prompt: str, user_prompt_template: str) -> Callable:
        """Create a custom processing function"""

        def custom_processor(source: str, **kwargs) -> Dict[str, Any]:
            # Add custom template
            self.processing_templates[ProcessingMode.CUSTOM] = {
                "system_prompt": system_prompt,
                "user_prompt_template": user_prompt_template,
            }

            return self.process_document(
                source=source,
                processing_mode=ProcessingMode.CUSTOM,
                processing_params=kwargs,
            )

        return custom_processor

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        # Placeholder for statistics tracking
        return {
            "total_documents_processed": 0,
            "average_processing_time": 0,
            "success_rate": 1.0,
            "most_common_document_types": [],
            "ai_provider_usage": {},
        }
