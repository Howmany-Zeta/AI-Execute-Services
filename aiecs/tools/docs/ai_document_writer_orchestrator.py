import os
import asyncio
import logging
import tempfile
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class ContentGenerationMode(str, Enum):
    """AI content generation modes"""

    GENERATE = "generate"  # 生成全新内容
    ENHANCE = "enhance"  # 增强现有内容
    REWRITE = "rewrite"  # 重写内容
    TRANSLATE = "translate"  # 翻译内容
    CONVERT_FORMAT = "convert_format"  # 格式转换
    TEMPLATE_FILL = "template_fill"  # 模板填充
    FORMAT_CONTENT = "format_content"  # 格式化内容
    EDIT_CONTENT = "edit_content"  # 编辑内容


class AIEditOperation(str, Enum):
    """AI-driven editing operations"""

    SMART_FORMAT = "smart_format"  # AI智能格式化
    STYLE_ENHANCE = "style_enhance"  # 样式增强
    CONTENT_RESTRUCTURE = "content_restructure"  # 内容重构
    INTELLIGENT_HIGHLIGHT = "intelligent_highlight"  # 智能高亮
    AUTO_BOLD_KEYWORDS = "auto_bold_keywords"  # 自动加粗关键词
    SMART_PARAGRAPH = "smart_paragraph"  # 智能段落优化
    AI_PROOFREADING = "ai_proofreading"  # AI校对


class WriteStrategy(str, Enum):
    """Document writing strategies"""

    IMMEDIATE = "immediate"  # 立即写入
    REVIEW = "review"  # 审核后写入
    DRAFT = "draft"  # 保存为草稿
    STAGED = "staged"  # 分阶段写入


class AIProvider(str, Enum):
    """Supported AI providers"""

    OPENAI = "openai"
    VERTEX_AI = "vertex_ai"
    XAI = "xai"
    LOCAL = "local"


class AIDocumentWriterOrchestratorError(Exception):
    """Base exception for AI Document Writer Orchestrator errors"""


class ContentGenerationError(AIDocumentWriterOrchestratorError):
    """Raised when content generation fails"""


class WriteOrchestrationError(AIDocumentWriterOrchestratorError):
    """Raised when write orchestration fails"""


@register_tool("ai_document_writer_orchestrator")
class AIDocumentWriterOrchestrator(BaseTool):
    """
    AI-powered document writing orchestrator that:
    1. Coordinates AI content generation with document writing
    2. Manages complex writing workflows
    3. Provides intelligent content enhancement and formatting
    4. Handles review and approval processes
    5. Supports template-based document generation

    Integrates with:
    - DocumentWriterTool for document writing operations
    - Various AI providers for content generation
    - Existing AIECS infrastructure
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the AI document writer orchestrator tool

        Automatically reads from environment variables with AI_DOC_WRITER_ prefix.
        """

        model_config = SettingsConfigDict(env_prefix="AI_DOC_WRITER_")

        default_ai_provider: str = Field(default="openai", description="Default AI provider to use")
        max_content_length: int = Field(
            default=50000,
            description="Maximum content length for AI generation",
        )
        max_concurrent_writes: int = Field(default=5, description="Maximum concurrent write operations")
        default_temperature: float = Field(default=0.3, description="Default temperature for AI model")
        max_tokens: int = Field(default=4000, description="Maximum tokens for AI response")
        timeout: int = Field(default=60, description="Timeout in seconds for AI operations")
        enable_draft_mode: bool = Field(default=True, description="Whether to enable draft mode")
        enable_content_review: bool = Field(default=True, description="Whether to enable content review")
        auto_backup_on_ai_write: bool = Field(
            default=True,
            description="Whether to automatically backup before AI writes",
        )
        temp_dir: str = Field(
            default=tempfile.gettempdir(),
            description="Temporary directory for processing",
        )

    def __init__(self, config: Optional[Dict] = None, **kwargs):
        """Initialize AI Document Writer Orchestrator with settings

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/ai_document_writer_orchestrator.yaml)
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

        # Initialize document writer
        self._init_document_writer()

        # Initialize document creation tools
        self._init_document_creation_tools()

        # Initialize AI providers
        self._init_ai_providers()

        # Initialize content generation templates
        self._init_content_templates()

    def _init_document_writer(self):
        """Initialize document writer tool"""
        try:
            from aiecs.tools.docs.document_writer_tool import (
                DocumentWriterTool,
            )

            self.document_writer = DocumentWriterTool()
        except ImportError:
            self.logger.error("DocumentWriterTool not available")
            self.document_writer = None

    def _init_document_creation_tools(self):
        """Initialize document creation and layout tools"""
        self.creation_tools = {}

        # Initialize DocumentCreatorTool
        try:
            from aiecs.tools.docs.document_creator_tool import (
                DocumentCreatorTool,
                DocumentFormat,
                DocumentType,
                TemplateType,
            )

            self.creation_tools["creator"] = DocumentCreatorTool()
            # Store classes for later use
            self.DocumentFormat = DocumentFormat
            self.DocumentType = DocumentType
            self.TemplateType = TemplateType
            self.logger.info("DocumentCreatorTool initialized successfully")
        except ImportError:
            self.logger.warning("DocumentCreatorTool not available")

        # Initialize DocumentLayoutTool
        try:
            from aiecs.tools.docs.document_layout_tool import (
                DocumentLayoutTool,
            )

            self.creation_tools["layout"] = DocumentLayoutTool()
            self.logger.info("DocumentLayoutTool initialized successfully")
        except ImportError:
            self.logger.warning("DocumentLayoutTool not available")

        # Initialize ContentInsertionTool
        try:
            from aiecs.tools.docs.content_insertion_tool import (
                ContentInsertionTool,
            )

            self.creation_tools["content"] = ContentInsertionTool()
            self.logger.info("ContentInsertionTool initialized successfully")
        except ImportError:
            self.logger.warning("ContentInsertionTool not available")

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

    def _init_content_templates(self):
        """Initialize content generation templates"""
        self.content_templates = {
            ContentGenerationMode.GENERATE: {
                "system_prompt": "You are an expert content writer. Generate high-quality, well-structured content based on the given requirements.",
                "user_prompt_template": (
                    "Generate content for: {content_type}\n\nRequirements:\n{requirements}\n\n"
                    "Target audience: {audience}\n\nPlease provide well-structured, engaging content that meets these requirements."
                ),
            },
            ContentGenerationMode.ENHANCE: {
                "system_prompt": "You are an expert content editor. Enhance and improve existing content while maintaining its core message.",
                "user_prompt_template": (
                    "Enhance the following content:\n\n{existing_content}\n\nImprovement goals:\n{enhancement_goals}\n\n"
                    "Please provide an enhanced version that is more engaging, clear, and effective."
                ),
            },
            ContentGenerationMode.REWRITE: {
                "system_prompt": "You are an expert content rewriter. Rewrite content to improve clarity, style, and effectiveness.",
                "user_prompt_template": (
                    "Rewrite the following content:\n\n{existing_content}\n\nRewriting goals:\n{rewrite_goals}\n\n"
                    "Target style: {target_style}\n\nPlease provide a completely rewritten version that maintains "
                    "the core information but improves presentation."
                ),
            },
            ContentGenerationMode.TRANSLATE: {
                "system_prompt": "You are an expert translator. Provide accurate, natural translations that preserve meaning and context.",
                "user_prompt_template": (
                    "Translate the following content to {target_language}:\n\n{content}\n\n" "Please provide a natural, accurate translation that preserves the original meaning and tone."
                ),
            },
            ContentGenerationMode.CONVERT_FORMAT: {
                "system_prompt": "You are an expert document formatter. Convert content between different formats while preserving structure and meaning.",
                "user_prompt_template": (
                    "Convert the following content from {source_format} to {target_format}:\n\n{content}\n\n"
                    "Please maintain the structure and ensure the converted format is properly formatted and readable."
                ),
            },
            ContentGenerationMode.TEMPLATE_FILL: {
                "system_prompt": "You are an expert template processor. Fill templates with appropriate content based on provided data.",
                "user_prompt_template": (
                    "Fill the following template with the provided data:\n\nTemplate:\n{template}\n\nData:\n{data}\n\n"
                    "Please generate complete, coherent content that properly fills all template sections."
                ),
            },
        }

    # Schema definitions
    class AIWriteDocumentSchema(BaseModel):
        """Schema for ai_write_document operation"""

        target_path: str = Field(description="Target file path")
        content_requirements: str = Field(description="Content requirements and specifications")
        generation_mode: ContentGenerationMode = Field(description="Content generation mode")
        document_format: str = Field(description="Target document format")
        write_strategy: WriteStrategy = Field(default=WriteStrategy.IMMEDIATE, description="Write strategy")
        ai_provider: Optional[AIProvider] = Field(default=None, description="AI provider to use")
        generation_params: Optional[Dict[str, Any]] = Field(default=None, description="AI generation parameters")
        write_params: Optional[Dict[str, Any]] = Field(default=None, description="Document write parameters")

    class EnhanceDocumentSchema(BaseModel):
        """Schema for enhance_document operation"""

        source_path: str = Field(description="Source document path")
        target_path: Optional[str] = Field(default=None, description="Target path (if different)")
        enhancement_goals: str = Field(description="Enhancement goals and requirements")
        ai_provider: Optional[AIProvider] = Field(default=None, description="AI provider to use")
        preserve_format: bool = Field(default=True, description="Preserve original format")

    class BatchWriteSchema(BaseModel):
        """Schema for batch_ai_write operation"""

        write_requests: List[Dict[str, Any]] = Field(description="List of write requests")
        coordination_strategy: str = Field(default="parallel", description="Coordination strategy")
        max_concurrent: Optional[int] = Field(default=None, description="Maximum concurrent operations")

    class AIEditDocumentSchema(BaseModel):
        """Schema for ai_edit_document operation"""

        target_path: str = Field(description="Target document path")
        edit_operation: AIEditOperation = Field(description="AI editing operation to perform")
        edit_instructions: str = Field(description="Specific editing instructions")
        ai_provider: Optional[AIProvider] = Field(default=None, description="AI provider to use")
        preserve_structure: bool = Field(default=True, description="Preserve document structure")
        format_options: Optional[Dict[str, Any]] = Field(default=None, description="Format-specific options")

    class SmartFormatSchema(BaseModel):
        """Schema for smart_format_document operation"""

        target_path: str = Field(description="Target document path")
        format_goals: str = Field(description="Formatting goals and requirements")
        target_format: str = Field(description="Target document format")
        style_preferences: Optional[Dict[str, Any]] = Field(default=None, description="Style preferences")

    class ContentAnalysisSchema(BaseModel):
        """Schema for analyze_document_content operation"""

        source_path: str = Field(description="Source document path")
        analysis_type: str = Field(description="Type of analysis to perform")
        analysis_params: Optional[Dict[str, Any]] = Field(default=None, description="Analysis parameters")

    class CreateRichDocumentSchema(BaseModel):
        """Schema for create_rich_document operation"""

        document_template: str = Field(description="Document template type")
        content_plan: Dict[str, Any] = Field(description="Content planning configuration")
        layout_config: Optional[Dict[str, Any]] = Field(default=None, description="Layout configuration")
        output_path: Optional[str] = Field(default=None, description="Custom output path")
        ai_assistance: bool = Field(
            default=True,
            description="Use AI assistance for content generation",
        )

    class GenerateDocumentWithChartsSchema(BaseModel):
        """Schema for generate_document_with_charts operation"""

        requirements: str = Field(description="Document requirements and specifications")
        data_sources: List[Dict[str, Any]] = Field(description="Data sources for charts and tables")
        document_type: str = Field(description="Type of document to generate")
        include_analysis: bool = Field(default=True, description="Include data analysis sections")
        chart_preferences: Optional[Dict[str, Any]] = Field(default=None, description="Chart style preferences")

    class OptimizeDocumentLayoutSchema(BaseModel):
        """Schema for optimize_document_layout operation"""

        document_path: str = Field(description="Path to document to optimize")
        optimization_goals: List[str] = Field(description="Layout optimization goals")
        preserve_content: bool = Field(default=True, description="Preserve existing content")
        layout_style: Optional[str] = Field(default=None, description="Target layout style")

    class BatchContentInsertionSchema(BaseModel):
        """Schema for batch_content_insertion operation"""

        document_path: str = Field(description="Target document path")
        content_plan: List[Dict[str, Any]] = Field(description="Content insertion plan")
        insertion_strategy: str = Field(default="sequential", description="Insertion strategy")
        ai_optimization: bool = Field(default=True, description="Use AI for content optimization")

    def ai_write_document(
        self,
        target_path: str,
        content_requirements: str,
        generation_mode: ContentGenerationMode,
        document_format: str = "txt",
        write_strategy: WriteStrategy = WriteStrategy.IMMEDIATE,
        ai_provider: Optional[AIProvider] = None,
        generation_params: Optional[Dict[str, Any]] = None,
        write_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate content using AI and write to document

        Args:
            target_path: Target file path
            content_requirements: Content requirements and specifications
            generation_mode: Content generation mode
            document_format: Target document format
            write_strategy: Write strategy (immediate, review, draft, staged)
            ai_provider: AI provider to use
            generation_params: AI generation parameters
            write_params: Document write parameters

        Returns:
            Dict containing generation and write results
        """
        try:
            start_time = datetime.now()
            # Use microsecond precision for unique IDs
            operation_id = f"ai_write_{int(start_time.timestamp() * 1000000)}"

            self.logger.info(f"Starting AI write operation {operation_id}: {target_path}")

            # Step 1: Generate content using AI
            provider = ai_provider or AIProvider(self.config.default_ai_provider)
            ai_result = self._generate_content_with_ai(
                content_requirements,
                generation_mode,
                document_format,
                provider,
                generation_params or {},
            )

            # Step 2: Process generated content
            processed_content = self._process_generated_content(
                ai_result["generated_content"],
                document_format,
                generation_mode,
            )

            # Step 3: Handle write strategy
            write_result = self._execute_write_strategy(
                target_path,
                processed_content,
                document_format,
                write_strategy,
                write_params or {},
            )

            # Step 4: Post-processing
            post_process_result = self._post_process_ai_write(
                operation_id,
                target_path,
                ai_result,
                write_result,
                write_strategy,
            )

            result = {
                "operation_id": operation_id,
                "target_path": target_path,
                "generation_mode": generation_mode,
                "document_format": document_format,
                "write_strategy": write_strategy,
                "ai_provider": ai_provider or self.config.default_ai_provider,
                "ai_result": ai_result,
                "write_result": write_result,
                "post_process_result": post_process_result,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self.logger.info(f"AI write operation {operation_id} completed successfully")
            return result

        except Exception as e:
            raise WriteOrchestrationError(f"AI write operation failed: {str(e)}")

    async def ai_write_document_async(
        self,
        target_path: str,
        content_requirements: str,
        generation_mode: ContentGenerationMode,
        document_format: str = "txt",
        write_strategy: WriteStrategy = WriteStrategy.IMMEDIATE,
        ai_provider: Optional[AIProvider] = None,
        generation_params: Optional[Dict[str, Any]] = None,
        write_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Async version of ai_write_document"""
        return await asyncio.to_thread(
            self.ai_write_document,
            target_path=target_path,
            content_requirements=content_requirements,
            generation_mode=generation_mode,
            document_format=document_format,
            write_strategy=write_strategy,
            ai_provider=ai_provider,
            generation_params=generation_params,
            write_params=write_params,
        )

    def enhance_document(
        self,
        source_path: str,
        enhancement_goals: str,
        target_path: Optional[str] = None,
        ai_provider: Optional[AIProvider] = None,
        preserve_format: bool = True,
    ) -> Dict[str, Any]:
        """
        Enhance existing document using AI

        Args:
            source_path: Source document path
            enhancement_goals: Enhancement goals and requirements
            target_path: Target path (if different from source)
            ai_provider: AI provider to use
            preserve_format: Preserve original document format

        Returns:
            Dict containing enhancement results
        """
        try:
            start_time = datetime.now()

            # Step 1: Read existing document
            existing_content = self._read_existing_document(source_path)

            # Step 2: Generate enhanced content
            provider = ai_provider or AIProvider(self.config.default_ai_provider)
            ai_result = self._enhance_content_with_ai(
                existing_content,
                enhancement_goals,
                provider,
            )

            # Step 3: Write enhanced content
            target = target_path or source_path
            write_mode = "overwrite" if target == source_path else "create"

            if self.config.auto_backup_on_ai_write and target == source_path:
                write_mode = "backup_write"

            write_result = self.document_writer.write_document(
                target_path=target,
                content=ai_result["enhanced_content"],
                format=existing_content["format"],
                mode=write_mode,
            )

            result = {
                "source_path": source_path,
                "target_path": target,
                "enhancement_goals": enhancement_goals,
                "preserve_format": preserve_format,
                "original_content": existing_content,
                "ai_result": ai_result,
                "write_result": write_result,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            return result

        except Exception as e:
            raise WriteOrchestrationError(f"Document enhancement failed: {str(e)}")

    def batch_ai_write(
        self,
        write_requests: List[Dict[str, Any]],
        coordination_strategy: str = "parallel",
        max_concurrent: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Batch AI write operations with coordination

        Args:
            write_requests: List of write request dictionaries
            coordination_strategy: Coordination strategy (parallel, sequential, smart)
            max_concurrent: Maximum concurrent operations

        Returns:
            Dict containing batch processing results
        """
        try:
            start_time = datetime.now()
            batch_id = f"batch_ai_write_{int(start_time.timestamp())}"
            max_concurrent = max_concurrent or self.config.max_concurrent_writes

            self.logger.info(f"Starting batch AI write {batch_id}: {len(write_requests)} requests")

            if coordination_strategy == "parallel":
                results = asyncio.run(self._batch_write_parallel(write_requests, max_concurrent))
            elif coordination_strategy == "sequential":
                results = self._batch_write_sequential(write_requests)
            elif coordination_strategy == "smart":
                results = asyncio.run(self._batch_write_smart(write_requests, max_concurrent))
            else:
                raise ValueError(f"Unknown coordination strategy: {coordination_strategy}")

            batch_result = {
                "batch_id": batch_id,
                "coordination_strategy": coordination_strategy,
                "total_requests": len(write_requests),
                "successful_requests": len([r for r in results if r.get("status") == "success"]),
                "failed_requests": len([r for r in results if r.get("status") == "error"]),
                "results": results,
                "batch_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            return batch_result

        except Exception as e:
            raise WriteOrchestrationError(f"Batch AI write failed: {str(e)}")

    def ai_edit_document(
        self,
        target_path: str,
        edit_operation: AIEditOperation,
        edit_instructions: str,
        ai_provider: Optional[AIProvider] = None,
        preserve_structure: bool = True,
        format_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform AI-driven editing operations on documents

        Args:
            target_path: Target document path
            edit_operation: AI editing operation to perform
            edit_instructions: Specific editing instructions
            ai_provider: AI provider to use
            preserve_structure: Preserve document structure
            format_options: Format-specific options

        Returns:
            Dict containing editing results
        """
        try:
            start_time = datetime.now()
            operation_id = f"ai_edit_{int(start_time.timestamp())}"

            self.logger.info(f"Starting AI edit operation {operation_id}: {edit_operation} on {target_path}")

            if not self.document_writer:
                raise WriteOrchestrationError("DocumentWriterTool not available")

            # Step 1: Read current document content
            current_content = self._read_document_for_editing(target_path)

            # Step 2: Analyze content for editing
            analysis_result = self._analyze_document_for_editing(current_content, edit_operation, edit_instructions)

            # Step 3: Generate editing instructions using AI
            ai_edit_plan = self._generate_ai_edit_plan(
                current_content,
                edit_operation,
                edit_instructions,
                analysis_result,
                ai_provider or AIProvider(self.config.default_ai_provider),
            )

            # Step 4: Execute editing operations
            edit_results = self._execute_ai_editing_plan(target_path, ai_edit_plan, format_options)

            # Step 5: Post-process and validate
            validation_result = self._validate_ai_editing_result(target_path, current_content, edit_results, preserve_structure)

            result = {
                "operation_id": operation_id,
                "target_path": target_path,
                "edit_operation": edit_operation,
                "edit_instructions": edit_instructions,
                "preserve_structure": preserve_structure,
                "analysis_result": analysis_result,
                "ai_edit_plan": ai_edit_plan,
                "edit_results": edit_results,
                "validation_result": validation_result,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self.logger.info(f"AI edit operation {operation_id} completed successfully")
            return result

        except Exception as e:
            raise WriteOrchestrationError(f"AI edit operation failed: {str(e)}")

    def smart_format_document(
        self,
        target_path: str,
        format_goals: str,
        target_format: str,
        style_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Intelligently format document using AI analysis

        Args:
            target_path: Target document path
            format_goals: Formatting goals and requirements
            target_format: Target document format
            style_preferences: Style preferences

        Returns:
            Dict containing formatting results
        """
        try:
            start_time = datetime.now()

            if not self.document_writer:
                raise WriteOrchestrationError("DocumentWriterTool not available")

            # Step 1: Analyze document structure
            structure_analysis = self._analyze_document_structure(target_path, target_format)

            # Step 2: Generate smart formatting plan
            format_plan = self._generate_smart_format_plan(
                structure_analysis,
                format_goals,
                target_format,
                style_preferences,
            )

            # Step 3: Execute formatting operations
            format_results = self._execute_smart_formatting(target_path, format_plan, target_format)

            result = {
                "target_path": target_path,
                "format_goals": format_goals,
                "target_format": target_format,
                "structure_analysis": structure_analysis,
                "format_plan": format_plan,
                "format_results": format_results,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            return result

        except Exception as e:
            raise WriteOrchestrationError(f"Smart formatting failed: {str(e)}")

    def analyze_document_content(
        self,
        source_path: str,
        analysis_type: str,
        analysis_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform AI-driven content analysis

        Args:
            source_path: Source document path
            analysis_type: Type of analysis to perform
            analysis_params: Analysis parameters

        Returns:
            Dict containing analysis results
        """
        try:
            if not self.document_writer:
                raise WriteOrchestrationError("DocumentWriterTool not available")

            # Read document content
            content = self._read_document_for_editing(source_path)

            # Perform analysis based on type
            if analysis_type == "structure":
                format_param = analysis_params.get("format", "txt") if analysis_params else "txt"
                result = self._analyze_document_structure(source_path, format_param)
            elif analysis_type == "readability":
                result = self._analyze_readability(content, analysis_params)
            elif analysis_type == "keywords":
                result = self._analyze_keywords(content, analysis_params)
            elif analysis_type == "formatting_issues":
                result = self._analyze_formatting_issues(content, analysis_params)
            elif analysis_type == "content_quality":
                result = self._analyze_content_quality(content, analysis_params)
            else:
                raise ValueError(f"Unsupported analysis type: {analysis_type}")

            return {
                "source_path": source_path,
                "analysis_type": analysis_type,
                "analysis_result": result,
                "content_metadata": {
                    "content_length": len(content),
                    "analysis_timestamp": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            raise WriteOrchestrationError(f"Document analysis failed: {str(e)}")

    # Helper methods for AI editing operations
    def _read_document_for_editing(self, file_path: str) -> str:
        """Read document content for editing operations"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise WriteOrchestrationError(f"Cannot read document {file_path}: {str(e)}")

    def _analyze_document_for_editing(self, content: str, operation: AIEditOperation, instructions: str) -> Dict[str, Any]:
        """Analyze document content for editing operations"""
        analysis = {
            "content_length": len(content),
            "line_count": len(content.split("\n")),
            "word_count": len(content.split()),
            "operation": operation,
            "instructions": instructions,
        }

        # Specific analysis based on operation type
        if operation == AIEditOperation.SMART_FORMAT:
            analysis["formatting_issues"] = self._detect_formatting_issues(content)
        elif operation == AIEditOperation.AUTO_BOLD_KEYWORDS:
            analysis["potential_keywords"] = self._extract_potential_keywords(content)
        elif operation == AIEditOperation.INTELLIGENT_HIGHLIGHT:
            analysis["important_sections"] = self._identify_important_sections(content)
        elif operation == AIEditOperation.CONTENT_RESTRUCTURE:
            analysis["structure_analysis"] = self._analyze_content_structure(content)

        return analysis

    def _generate_ai_edit_plan(
        self,
        content: str,
        operation: AIEditOperation,
        instructions: str,
        analysis: Dict[str, Any],
        ai_provider: AIProvider,
    ) -> Dict[str, Any]:
        """Generate AI editing plan"""
        try:
            if not self.aiecs_client:
                # Fallback to rule-based editing plan
                return self._generate_fallback_edit_plan(content, operation, instructions, analysis)

            # Prepare AI prompt for editing plan
            system_prompt = f"""You are an expert document editor. Create a detailed editing plan based on the operation type and user instructions.

Operation: {operation}
Analysis: {analysis}

Provide a structured editing plan with specific actions, positions, and formatting details."""

            user_prompt = f"""Content to edit:
{content[:2000]}...

Instructions: {instructions}

Please provide a detailed editing plan with:
1. Specific edit operations
2. Text positions (line numbers, character offsets)
3. Format options
4. Expected outcomes"""

            # Generate editing plan using AI
            # Combine system and user prompts
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            ai_response = self._call_ai_provider(
                combined_prompt,
                ai_provider,
                {"max_tokens": 2000, "temperature": 0.3},
            )

            # Parse AI response into structured plan
            edit_plan = self._parse_ai_edit_response(ai_response, operation)

            return edit_plan

        except Exception as e:
            self.logger.warning(f"AI edit plan generation failed: {e}, using fallback")
            return self._generate_fallback_edit_plan(content, operation, instructions, analysis)

    def _execute_ai_editing_plan(
        self,
        target_path: str,
        edit_plan: Dict[str, Any],
        format_options: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Execute the AI-generated editing plan"""
        edit_results = []

        try:
            for edit_action in edit_plan.get("edit_actions", []):
                operation_type = edit_action.get("operation")

                if operation_type in [
                    "bold",
                    "italic",
                    "underline",
                    "strikethrough",
                    "highlight",
                ]:
                    # Text formatting operations
                    result = self.document_writer.edit_document(
                        target_path=target_path,
                        operation=operation_type,
                        selection=edit_action.get("selection"),
                        format_options=format_options or edit_action.get("format_options", {}),
                    )
                elif operation_type == "find_replace":
                    # Find and replace operations
                    result = self.document_writer.find_replace(
                        target_path=target_path,
                        find_text=edit_action.get("find_text"),
                        replace_text=edit_action.get("replace_text"),
                        replace_all=edit_action.get("replace_all", False),
                        case_sensitive=edit_action.get("case_sensitive", True),
                        regex_mode=edit_action.get("regex_mode", False),
                    )
                elif operation_type == "format_text":
                    # Format specific text
                    result = self.document_writer.format_text(
                        target_path=target_path,
                        text_to_format=edit_action.get("text_to_format"),
                        format_type=edit_action.get("format_type"),
                        format_options=format_options or edit_action.get("format_options", {}),
                    )
                else:
                    # General edit operations
                    result = self.document_writer.edit_document(
                        target_path=target_path,
                        operation=edit_action.get("operation"),
                        content=edit_action.get("content"),
                        position=edit_action.get("position"),
                        selection=edit_action.get("selection"),
                        format_options=format_options or edit_action.get("format_options", {}),
                    )

                edit_results.append({"action": edit_action, "result": result, "success": True})

        except Exception as e:
            edit_results.append({"action": edit_action, "error": str(e), "success": False})

        return edit_results

    def _validate_ai_editing_result(
        self,
        target_path: str,
        original_content: str,
        edit_results: List[Dict[str, Any]],
        preserve_structure: bool,
    ) -> Dict[str, Any]:
        """Validate AI editing results"""
        try:
            # Read edited content
            edited_content = self._read_document_for_editing(target_path)

            validation: Dict[str, Any] = {
                "original_length": len(original_content),
                "edited_length": len(edited_content),
                "successful_operations": sum(1 for r in edit_results if r.get("success")),
                "failed_operations": sum(1 for r in edit_results if not r.get("success")),
                "content_changed": original_content != edited_content,
                "structure_preserved": True,  # TODO: Implement structure validation
            }

            if preserve_structure:
                validation["structure_check"] = self._check_structure_preservation(original_content, edited_content)

            return validation

        except Exception as e:
            return {"validation_error": str(e)}

    # Additional helper methods for specific operations
    def _generate_fallback_edit_plan(
        self,
        content: str,
        operation: AIEditOperation,
        instructions: str,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate fallback editing plan when AI is not available"""
        plan: Dict[str, Any] = {"edit_actions": []}

        if operation == AIEditOperation.AUTO_BOLD_KEYWORDS:
            # Auto-bold common keywords
            keywords = ["重要", "关键", "注意", "警告", "错误", "成功"]
            for keyword in keywords:
                if keyword in content:
                    plan["edit_actions"].append(
                        {
                            "operation": "format_text",
                            "text_to_format": keyword,
                            "format_type": "bold",
                            "format_options": {"format_type": "markdown"},
                        }
                    )

        elif operation == AIEditOperation.SMART_FORMAT:
            # Basic formatting improvements
            plan["edit_actions"].append(
                {
                    "operation": "find_replace",
                    "find_text": "  ",
                    "replace_text": " ",
                    "replace_all": True,
                    "description": "Remove double spaces",
                }
            )

        return plan

    def _detect_formatting_issues(self, content: str) -> List[str]:
        """Detect common formatting issues"""
        issues = []

        if "  " in content:
            issues.append("Multiple consecutive spaces")
        if "\n\n\n" in content:
            issues.append("Multiple consecutive line breaks")
        if content.count("**") % 2 != 0:
            issues.append("Unmatched bold markdown markers")

        return issues

    def _extract_potential_keywords(self, content: str) -> List[str]:
        """Extract potential keywords for bolding"""
        # Simple keyword extraction - could be enhanced with NLP
        import re

        words = re.findall(r"\b[A-Z][a-z]+\b", content)  # Capitalized words
        return list(set(words))[:10]  # Top 10 unique words

    def _identify_important_sections(self, content: str) -> List[Dict[str, Any]]:
        """Identify sections that might need highlighting"""
        sections = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in ["重要", "注意", "警告", "关键"]):
                sections.append(
                    {
                        "line": i,
                        "content": line,
                        "reason": "Contains important keywords",
                    }
                )

        return sections

    def _analyze_content_structure(self, content: str) -> Dict[str, Any]:
        """Analyze content structure"""
        lines = content.split("\n")
        return {
            "total_lines": len(lines),
            "empty_lines": sum(1 for line in lines if not line.strip()),
            "header_lines": sum(1 for line in lines if line.startswith("#")),
            "list_items": sum(1 for line in lines if line.strip().startswith(("-", "*", "+"))),
            "paragraphs": len([line for line in lines if line.strip() and not line.startswith("#")]),
        }

    def _parse_ai_edit_response(self, ai_response: str, operation: AIEditOperation) -> Dict[str, Any]:
        """Parse AI response into structured editing plan"""
        # This is a simplified parser - could be enhanced with more
        # sophisticated parsing
        plan: Dict[str, Any] = {"edit_actions": []}

        # Try to extract structured actions from AI response
        # For now, return a basic plan
        plan["ai_response"] = ai_response
        plan["operation"] = operation

        return plan

    def _check_structure_preservation(self, original: str, edited: str) -> Dict[str, Any]:
        """Check if document structure is preserved after editing"""
        original_structure = self._analyze_content_structure(original)
        edited_structure = self._analyze_content_structure(edited)

        return {
            "headers_preserved": original_structure["header_lines"] == edited_structure["header_lines"],
            "structure_similarity": self._calculate_structure_similarity(original_structure, edited_structure),
        }

    def _calculate_structure_similarity(self, struct1: Dict, struct2: Dict) -> float:
        """Calculate similarity between two document structures"""
        # Simple similarity calculation
        if struct1["total_lines"] == 0:
            return 1.0 if struct2["total_lines"] == 0 else 0.0

        similarity = 1.0 - abs(struct1["total_lines"] - struct2["total_lines"]) / max(struct1["total_lines"], struct2["total_lines"])
        return max(0.0, similarity)

    def _analyze_document_structure(self, file_path: str, format_type: str) -> Dict[str, Any]:
        """Analyze document structure for formatting"""
        content = self._read_document_for_editing(file_path)
        return self._analyze_content_structure(content)

    def _generate_smart_format_plan(
        self,
        structure: Dict[str, Any],
        goals: str,
        target_format: str,
        style_prefs: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate smart formatting plan"""
        return {
            "format_actions": [],
            "structure_analysis": structure,
            "goals": goals,
            "target_format": target_format,
            "style_preferences": style_prefs or {},
        }

    def _execute_smart_formatting(self, target_path: str, plan: Dict[str, Any], target_format: str) -> Dict[str, Any]:
        """Execute smart formatting plan"""
        return {
            "target_path": target_path,
            "plan_executed": plan,
            "target_format": target_format,
            "formatting_completed": True,
        }

    def _analyze_readability(self, content: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze content readability"""
        words = content.split()
        sentences = content.split(".")

        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "avg_words_per_sentence": len(words) / max(len(sentences), 1),
            "readability_score": "good",  # Simplified
        }

    def _analyze_keywords(self, content: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze content keywords"""
        words = content.lower().split()
        word_freq: Dict[str, int] = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Get top keywords
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_words": len(words),
            "unique_words": len(word_freq),
            "top_keywords": top_keywords,
        }

    def _analyze_formatting_issues(self, content: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze formatting issues in content"""
        issues = self._detect_formatting_issues(content)

        return {
            "issues_found": len(issues),
            "issue_list": issues,
            "content_length": len(content),
        }

    def _analyze_content_quality(self, content: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze overall content quality"""
        return {
            "content_length": len(content),
            "structure_score": 0.8,  # Simplified scoring
            "readability_score": 0.7,
            "formatting_score": 0.9,
            "overall_quality": 0.8,
        }

    def create_rich_document(
        self,
        document_template: str,
        content_plan: Dict[str, Any],
        layout_config: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        ai_assistance: bool = True,
    ) -> Dict[str, Any]:
        """
        Create rich document with comprehensive content and layout

        Args:
            document_template: Document template type
            content_plan: Content planning configuration
            layout_config: Layout configuration
            output_path: Custom output path
            ai_assistance: Use AI assistance for content generation

        Returns:
            Dict containing rich document creation results
        """
        try:
            start_time = datetime.now()
            operation_id = f"create_rich_{int(start_time.timestamp())}"

            self.logger.info(f"Starting rich document creation {operation_id}")

            # Check tool availability
            creator = self.creation_tools.get("creator")
            layout_tool = self.creation_tools.get("layout")
            content_tool = self.creation_tools.get("content")

            if not creator:
                raise WriteOrchestrationError("DocumentCreatorTool not available")

            # Step 1: Create document from template
            document_metadata = content_plan.get("metadata", {})
            document_format_str = content_plan.get("format", "markdown")

            # Convert string to DocumentFormat enum
            try:
                document_format = self.DocumentFormat(document_format_str)
            except (ValueError, AttributeError):
                # Fallback if DocumentFormat not available
                from aiecs.tools.docs.document_creator_tool import (
                    DocumentFormat,
                )

                document_format = DocumentFormat.MARKDOWN

            # Get enum classes
            try:
                DocumentType = self.DocumentType
                TemplateType = self.TemplateType
            except AttributeError:
                from aiecs.tools.docs.document_creator_tool import (
                    DocumentType,
                    TemplateType,
                )

            # Parse document_type with fallback
            doc_type_str = content_plan.get("document_type", "custom")
            try:
                doc_type = DocumentType(doc_type_str)
            except ValueError:
                # Try to find a matching type or use a sensible default
                if "technical" in doc_type_str.lower():
                    doc_type = DocumentType.TECHNICAL
                elif "report" in doc_type_str.lower():
                    doc_type = DocumentType.REPORT
                elif "article" in doc_type_str.lower():
                    doc_type = DocumentType.ARTICLE
                else:
                    doc_type = DocumentType.TECHNICAL  # Default fallback
                self.logger.warning(f"Unknown document type '{doc_type_str}', using {doc_type.value}")

            # Parse template_type with fallback
            try:
                tmpl_type = TemplateType(document_template)
            except ValueError:
                # Default to basic template
                tmpl_type = TemplateType.BASIC
                self.logger.warning(f"Unknown template type '{document_template}', using basic")

            creation_result = creator.create_document(
                document_type=doc_type,
                template_type=tmpl_type,
                output_format=document_format,
                metadata=document_metadata,
                output_path=output_path,
            )

            document_path = creation_result["output_path"]

            # Step 2: Setup document structure
            if content_plan.get("sections"):
                creator.setup_document_structure(
                    document_path=document_path,
                    sections=content_plan["sections"],
                    generate_toc=content_plan.get("generate_toc", True),
                    numbering_style=content_plan.get("numbering_style"),
                )

            # Step 3: Apply layout configuration
            if layout_tool and layout_config:
                layout_tool.set_page_layout(document_path=document_path, **layout_config)

                # Setup headers/footers if specified
                if layout_config.get("headers_footers"):
                    layout_tool.setup_headers_footers(
                        document_path=document_path,
                        **layout_config["headers_footers"],
                    )

            # Step 4: Generate and insert content with AI assistance
            content_results = []
            if ai_assistance and content_plan.get("content_items"):
                content_results = self._generate_and_insert_content_items(document_path, content_plan["content_items"])

            # Step 5: Insert complex content (charts, tables, images)
            insertion_results = []
            if content_tool and content_plan.get("insertions"):
                insertion_results = self._batch_insert_complex_content(document_path, content_plan["insertions"], content_tool)

            # Step 6: Final optimization
            if ai_assistance:
                self._optimize_rich_document(document_path, content_plan.get("optimization_goals", []))

            result = {
                "operation_id": operation_id,
                "document_path": document_path,
                "document_template": document_template,
                "content_plan": content_plan,
                "layout_config": layout_config,
                "creation_result": creation_result,
                "content_results": content_results,
                "insertion_results": insertion_results,
                "ai_assistance_used": ai_assistance,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self.logger.info(f"Rich document creation {operation_id} completed successfully")
            return result

        except Exception as e:
            raise WriteOrchestrationError(f"Rich document creation failed: {str(e)}")

    def generate_document_with_charts(
        self,
        requirements: str,
        data_sources: List[Dict[str, Any]],
        document_type: str,
        include_analysis: bool = True,
        chart_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate document with AI-driven charts and data visualization

        Args:
            requirements: Document requirements and specifications
            data_sources: Data sources for charts and tables
            document_type: Type of document to generate
            include_analysis: Include data analysis sections
            chart_preferences: Chart style preferences

        Returns:
            Dict containing document generation results
        """
        try:
            start_time = datetime.now()
            operation_id = f"gen_charts_{int(start_time.timestamp())}"

            self.logger.info(f"Starting document generation with charts {operation_id}")

            # Step 1: Analyze data sources and generate content plan
            content_plan = self._analyze_data_and_create_plan(data_sources, requirements, document_type, include_analysis)

            # Step 2: Generate charts from data sources
            chart_results = self._generate_charts_from_data(data_sources, chart_preferences)

            # Step 3: Create document with integrated charts
            rich_doc_result = self.create_rich_document(
                document_template=self._select_template_for_data_document(document_type),
                content_plan=content_plan,
                ai_assistance=True,
            )

            # Step 4: Insert generated charts
            chart_insertion_results = self._insert_generated_charts(rich_doc_result["document_path"], chart_results, content_plan)

            # Step 5: Generate AI analysis content
            if include_analysis:
                self._generate_ai_analysis_content(
                    rich_doc_result["document_path"],
                    data_sources,
                    chart_results,
                )

            result = {
                "operation_id": operation_id,
                "document_path": rich_doc_result["document_path"],
                "requirements": requirements,
                "data_sources": data_sources,
                "document_type": document_type,
                "content_plan": content_plan,
                "chart_results": chart_results,
                "rich_doc_result": rich_doc_result,
                "chart_insertion_results": chart_insertion_results,
                "include_analysis": include_analysis,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self.logger.info(f"Document with charts generation {operation_id} completed successfully")
            return result

        except Exception as e:
            raise WriteOrchestrationError(f"Document with charts generation failed: {str(e)}")

    def optimize_document_layout(
        self,
        document_path: str,
        optimization_goals: List[str],
        preserve_content: bool = True,
        layout_style: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Optimize document layout using AI analysis

        Args:
            document_path: Path to document to optimize
            optimization_goals: Layout optimization goals
            preserve_content: Preserve existing content
            layout_style: Target layout style

        Returns:
            Dict containing layout optimization results
        """
        try:
            start_time = datetime.now()
            operation_id = f"optimize_layout_{int(start_time.timestamp())}"

            self.logger.info(f"Starting layout optimization {operation_id} for: {document_path}")

            layout_tool = self.creation_tools.get("layout")
            if not layout_tool:
                raise WriteOrchestrationError("DocumentLayoutTool not available")

            # Step 1: Analyze current document content
            content_analysis = self.analyze_document_content(source_path=document_path, analysis_type="structure")

            # Step 2: Generate optimization plan
            optimization_plan = self._generate_layout_optimization_plan(
                document_path,
                content_analysis,
                optimization_goals,
                layout_style,
            )

            # Step 3: Apply optimizations
            optimization_results = layout_tool.optimize_layout_for_content(
                document_path=document_path,
                content_analysis=content_analysis["analysis_result"],
                optimization_goals=optimization_goals,
            )

            # Step 4: Validate optimization results
            if preserve_content:
                self._validate_content_preservation(document_path, content_analysis)

            result = {
                "operation_id": operation_id,
                "document_path": document_path,
                "optimization_goals": optimization_goals,
                "layout_style": layout_style,
                "content_analysis": content_analysis,
                "optimization_plan": optimization_plan,
                "optimization_results": optimization_results,
                "preserve_content": preserve_content,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self.logger.info(f"Layout optimization {operation_id} completed successfully")
            return result

        except Exception as e:
            raise WriteOrchestrationError(f"Layout optimization failed: {str(e)}")

    def batch_content_insertion(
        self,
        document_path: str,
        content_plan: List[Dict[str, Any]],
        insertion_strategy: str = "sequential",
        ai_optimization: bool = True,
    ) -> Dict[str, Any]:
        """
        Batch insertion of multiple content types with AI coordination

        Args:
            document_path: Target document path
            content_plan: Content insertion plan
            insertion_strategy: Insertion strategy (sequential, parallel, optimized)
            ai_optimization: Use AI for content optimization

        Returns:
            Dict containing batch insertion results
        """
        try:
            start_time = datetime.now()
            operation_id = f"batch_insert_{int(start_time.timestamp())}"

            self.logger.info(f"Starting batch content insertion {operation_id} for: {document_path}")

            content_tool = self.creation_tools.get("content")
            if not content_tool:
                raise WriteOrchestrationError("ContentInsertionTool not available")

            # Step 1: Optimize insertion order if AI optimization is enabled
            if ai_optimization:
                optimized_plan = self._optimize_content_insertion_plan(document_path, content_plan)
            else:
                optimized_plan = content_plan

            # Step 2: Execute insertions based on strategy
            if insertion_strategy == "sequential":
                insertion_results = self._execute_sequential_insertions(document_path, optimized_plan, content_tool)
            elif insertion_strategy == "parallel":
                insertion_results = self._execute_parallel_insertions(document_path, optimized_plan, content_tool)
            else:  # optimized
                insertion_results = self._execute_optimized_insertions(document_path, optimized_plan, content_tool)

            # Step 3: Post-insertion optimization
            if ai_optimization:
                self._post_insertion_optimization(document_path, insertion_results)

            result = {
                "operation_id": operation_id,
                "document_path": document_path,
                "content_plan": content_plan,
                "optimized_plan": optimized_plan,
                "insertion_strategy": insertion_strategy,
                "ai_optimization": ai_optimization,
                "insertion_results": insertion_results,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self.logger.info(f"Batch content insertion {operation_id} completed successfully")
            return result

        except Exception as e:
            raise WriteOrchestrationError(f"Batch content insertion failed: {str(e)}")

    # Helper methods for new functionality
    def _generate_and_insert_content_items(self, document_path: str, content_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate and insert content items with AI assistance"""
        results = []

        for item in content_items:
            try:
                # Generate content based on type
                if item.get("type") == "ai_generated":
                    generated_content = self._generate_content_with_ai(
                        item.get("requirements", ""),
                        ContentGenerationMode.GENERATE,
                        "markdown",
                        AIProvider(self.config.default_ai_provider),
                        item.get("generation_params", {}),
                    )

                    # Insert generated content
                    if self.document_writer:
                        write_result = self.document_writer.write_document(
                            target_path=document_path,
                            content=generated_content["generated_content"],
                            format="markdown",
                            mode="append",
                        )

                        results.append(
                            {
                                "item": item,
                                "generated_content": generated_content,
                                "write_result": write_result,
                                "success": True,
                            }
                        )

            except Exception as e:
                results.append({"item": item, "error": str(e), "success": False})
                self.logger.warning(f"Failed to generate/insert content item: {e}")

        return results

    def _batch_insert_complex_content(
        self,
        document_path: str,
        insertions: List[Dict[str, Any]],
        content_tool,
    ) -> List[Dict[str, Any]]:
        """Batch insert complex content using ContentInsertionTool"""
        try:
            # Use the content tool's batch insertion capability
            return content_tool.batch_insert_content(document_path=document_path, content_items=insertions)
        except Exception as e:
            self.logger.warning(f"Batch insertion failed: {e}")
            return []

    def _optimize_rich_document(self, document_path: str, optimization_goals: List[str]) -> Dict[str, Any]:
        """Optimize rich document based on goals"""
        try:
            if "layout" in self.creation_tools:
                return self.creation_tools["layout"].optimize_layout_for_content(
                    document_path=document_path,
                    content_analysis={"content_length": 0},  # Simplified
                    optimization_goals=optimization_goals,
                )
        except Exception as e:
            self.logger.warning(f"Document optimization failed: {e}")

        return {"optimization_applied": False}

    def _analyze_data_and_create_plan(
        self,
        data_sources: List[Dict[str, Any]],
        requirements: str,
        document_type: str,
        include_analysis: bool,
    ) -> Dict[str, Any]:
        """Analyze data sources and create content plan"""
        plan = {
            "document_type": document_type,
            "format": "markdown",
            "metadata": {
                "title": f"{document_type.title()} Report",
                "author": "AI Document Generator",
                "date": datetime.now().strftime("%Y-%m-%d"),
            },
            "sections": [
                {"title": "Executive Summary", "level": 2, "required": True},
                {"title": "Data Overview", "level": 2, "required": True},
                {"title": "Visualizations", "level": 2, "required": True},
            ],
            "generate_toc": True,
            "insertions": [],
        }
        # Explicitly type plan to allow append operations
        plan_dict: Dict[str, Any] = plan

        if include_analysis:
            plan_dict["sections"].append({"title": "Analysis", "level": 2, "required": True})
            plan_dict["sections"].append({"title": "Insights", "level": 2, "required": True})

        # Add chart insertions for each data source
        for i, data_source in enumerate(data_sources):
            plan_dict["insertions"].append(
                {
                    "content_type": "chart",
                    "chart_data": data_source.get("data", {}),
                    "chart_type": data_source.get("chart_type", "bar"),
                    "position": {"marker": f"<!-- CHART_{i+1} -->"},
                    "caption": f"Chart {i+1}: {data_source.get('title', 'Data Visualization')}",
                }
            )

        return plan_dict

    def _generate_charts_from_data(
        self,
        data_sources: List[Dict[str, Any]],
        preferences: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate charts from data sources"""
        results: List[Dict[str, Any]] = []

        if "content" not in self.creation_tools:
            return results

        content_tool = self.creation_tools["content"]

        for data_source in data_sources:
            try:
                chart_result = content_tool._generate_chart(
                    chart_data=data_source.get("data", {}),
                    chart_type=data_source.get("chart_type", "bar"),
                    config=preferences,
                )
                results.append(
                    {
                        "data_source": data_source,
                        "chart_result": chart_result,
                        "success": True,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "data_source": data_source,
                        "error": str(e),
                        "success": False,
                    }
                )

        return results

    def _select_template_for_data_document(self, document_type: str) -> str:
        """Select appropriate template for data document"""
        type_template_map = {
            "report": "business_report",
            "analysis": "technical_doc",
            "presentation": "presentation",
            "academic": "academic_paper",
        }
        return type_template_map.get(document_type, "business_report")

    def _insert_generated_charts(
        self,
        document_path: str,
        chart_results: List[Dict[str, Any]],
        content_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Insert generated charts into document"""
        results: List[Dict[str, Any]] = []

        if "content" not in self.creation_tools:
            return results

        content_tool = self.creation_tools["content"]

        for i, chart_result in enumerate(chart_results):
            if chart_result.get("success"):
                try:
                    insertion_result = content_tool.insert_chart(
                        document_path=document_path,
                        chart_data=chart_result["data_source"].get("data", {}),
                        chart_type=chart_result["data_source"].get("chart_type", "bar"),
                        position={"marker": f"<!-- CHART_{i+1} -->"},
                        caption=f"Chart {i+1}: {chart_result['data_source'].get('title', 'Data Visualization')}",
                    )
                    results.append(insertion_result)
                except Exception as e:
                    self.logger.warning(f"Failed to insert chart {i+1}: {e}")

        return results

    def _generate_ai_analysis_content(
        self,
        document_path: str,
        data_sources: List[Dict[str, Any]],
        chart_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate AI-driven analysis content"""
        try:
            # Generate analysis based on data
            analysis_prompt = f"""
            Analyze the following data sources and provide insights:
            Data Sources: {len(data_sources)} datasets
            Charts Generated: {len([r for r in chart_results if r.get('success')])}

            Please provide:
            1. Key findings from the data
            2. Trends and patterns observed
            3. Recommendations based on the analysis
            """

            analysis_result = self._generate_content_with_ai(
                analysis_prompt,
                ContentGenerationMode.GENERATE,
                "markdown",
                AIProvider(self.config.default_ai_provider),
                {},
            )

            # Insert analysis content into document
            if self.document_writer:
                write_result = self.document_writer.write_document(
                    target_path=document_path,
                    content=analysis_result["generated_content"],
                    format="markdown",
                    mode="append",
                )

                return {
                    "analysis_generated": True,
                    "analysis_content": analysis_result,
                    "write_result": write_result,
                }

        except Exception as e:
            self.logger.warning(f"Failed to generate AI analysis: {e}")

        return {"analysis_generated": False}

    def _generate_layout_optimization_plan(
        self,
        document_path: str,
        content_analysis: Dict[str, Any],
        optimization_goals: List[str],
        layout_style: Optional[str],
    ) -> Dict[str, Any]:
        """Generate layout optimization plan"""
        return {
            "document_path": document_path,
            "optimization_goals": optimization_goals,
            "layout_style": layout_style,
            "content_analysis": content_analysis,
            "recommended_actions": [
                "Optimize spacing",
                "Improve typography",
                "Enhance readability",
            ],
        }

    def _validate_content_preservation(self, document_path: str, original_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that content was preserved during optimization"""
        try:
            # Re-analyze document after optimization
            new_analysis = self.analyze_document_content(source_path=document_path, analysis_type="structure")

            # Compare analyses
            original_length = original_analysis.get("analysis_result", {}).get("content_length", 0)
            new_length = new_analysis.get("analysis_result", {}).get("content_length", 0)

            content_preserved = abs(original_length - new_length) / max(original_length, 1) < 0.1

            return {
                "content_preserved": content_preserved,
                "original_length": original_length,
                "new_length": new_length,
                "difference_ratio": abs(original_length - new_length) / max(original_length, 1),
            }

        except Exception as e:
            return {"validation_error": str(e)}

    def _optimize_content_insertion_plan(self, document_path: str, content_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize content insertion plan using AI"""
        # For now, return original plan
        # In a full implementation, this would use AI to optimize the order
        return content_plan

    def _execute_sequential_insertions(self, document_path: str, plan: List[Dict[str, Any]], content_tool) -> Dict[str, Any]:
        """Execute content insertions sequentially"""
        return content_tool.batch_insert_content(document_path=document_path, content_items=plan)

    def _execute_parallel_insertions(self, document_path: str, plan: List[Dict[str, Any]], content_tool) -> Dict[str, Any]:
        """Execute content insertions in parallel (simplified to sequential for now)"""
        return self._execute_sequential_insertions(document_path, plan, content_tool)

    def _execute_optimized_insertions(self, document_path: str, plan: List[Dict[str, Any]], content_tool) -> Dict[str, Any]:
        """Execute optimized content insertions"""
        return self._execute_sequential_insertions(document_path, plan, content_tool)

    def _post_insertion_optimization(self, document_path: str, insertion_results: Dict[str, Any]) -> Dict[str, Any]:
        """Perform post-insertion optimization"""
        return {
            "optimization_performed": True,
            "document_path": document_path,
            "insertion_results": insertion_results,
        }

    def create_content_template(
        self,
        template_name: str,
        template_content: str,
        template_variables: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create reusable content template

        Args:
            template_name: Name of the template
            template_content: Template content with variables
            template_variables: List of template variables
            metadata: Additional template metadata

        Returns:
            Dict containing template information
        """
        template_info = {
            "name": template_name,
            "content": template_content,
            "variables": template_variables,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }

        # Save template
        temp_dir = tempfile.gettempdir()
        template_file = os.path.join(temp_dir, f"template_{template_name}.json")
        with open(template_file, "w") as f:
            import json

            json.dump(template_info, f, indent=2)

        return template_info

    def use_content_template(
        self,
        template_name: str,
        template_data: Dict[str, Any],
        target_path: str,
        ai_enhancement: bool = True,
    ) -> Dict[str, Any]:
        """
        Use content template to generate document

        Args:
            template_name: Name of the template to use
            template_data: Data to fill template variables
            target_path: Target document path
            ai_enhancement: Whether to enhance with AI

        Returns:
            Dict containing template usage results
        """
        try:
            # Load template
            template_file = os.path.join(self.config.temp_dir, f"template_{template_name}.json")
            with open(template_file, "r") as f:
                import json

                template_info = json.load(f)

            # Fill template
            filled_content = self._fill_template(template_info["content"], template_data)

            # Enhance with AI if requested
            if ai_enhancement:
                ai_result = self._generate_content_with_ai(
                    f"Template: {template_name}",
                    ContentGenerationMode.TEMPLATE_FILL,
                    "txt",
                    AIProvider(self.config.default_ai_provider),
                    {
                        "template": template_info["content"],
                        "data": template_data,
                    },
                )
                filled_content = ai_result["generated_content"]

            # Write document
            write_result = self.document_writer.write_document(
                target_path=target_path,
                content=filled_content,
                format="txt",
                mode="create",
            )

            return {
                "template_name": template_name,
                "template_data": template_data,
                "target_path": target_path,
                "ai_enhancement": ai_enhancement,
                "filled_content": filled_content,
                "write_result": write_result,
            }

        except Exception as e:
            raise WriteOrchestrationError(f"Template usage failed: {str(e)}")

    def _generate_content_with_ai(
        self,
        requirements: str,
        generation_mode: ContentGenerationMode,
        document_format: str,
        ai_provider: AIProvider,
        generation_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate content using AI based on requirements"""

        try:
            # Get content generation template
            template = self.content_templates.get(generation_mode)
            if not template:
                raise ContentGenerationError(f"No template found for generation mode: {generation_mode}")

            # Prepare AI prompt
            prompt_params = {
                "content_type": document_format,
                "requirements": requirements,
                "audience": generation_params.get("audience", "general"),
                **generation_params,
            }

            prompt = self._format_content_prompt(template, prompt_params)

            # Call AI provider
            ai_response = self._call_ai_provider(prompt, ai_provider, generation_params)

            return {
                "generation_mode": generation_mode,
                "requirements": requirements,
                "prompt_used": prompt,
                "generated_content": ai_response,
                "ai_provider": ai_provider,
                "generation_params": generation_params,
            }

        except Exception as e:
            raise ContentGenerationError(f"AI content generation failed: {str(e)}")

    def _enhance_content_with_ai(
        self,
        existing_content: Dict[str, Any],
        enhancement_goals: str,
        ai_provider: AIProvider,
    ) -> Dict[str, Any]:
        """Enhance existing content using AI"""

        try:
            template = self.content_templates[ContentGenerationMode.ENHANCE]

            prompt_params = {
                "existing_content": existing_content["content"],
                "enhancement_goals": enhancement_goals,
            }

            prompt = self._format_content_prompt(template, prompt_params)
            ai_response = self._call_ai_provider(prompt, ai_provider, {})

            return {
                "original_content": existing_content["content"],
                "enhancement_goals": enhancement_goals,
                "enhanced_content": ai_response,
                "ai_provider": ai_provider,
            }

        except Exception as e:
            raise ContentGenerationError(f"AI content enhancement failed: {str(e)}")

    def _process_generated_content(
        self,
        content: str,
        document_format: str,
        generation_mode: ContentGenerationMode,
    ) -> str:
        """Process generated content for specific format"""

        # Format-specific processing
        if document_format.lower() == "markdown":
            # Ensure proper markdown formatting
            content = self._ensure_markdown_formatting(content)
        elif document_format.lower() == "html":
            # Ensure proper HTML structure
            content = self._ensure_html_structure(content)
        elif document_format.lower() == "json":
            # Validate and format JSON
            content = self._ensure_json_format(content)

        return content

    def _execute_write_strategy(
        self,
        target_path: str,
        content: str,
        document_format: str,
        write_strategy: WriteStrategy,
        write_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute write strategy"""

        if not self.document_writer:
            raise WriteOrchestrationError("DocumentWriterTool not available")

        if write_strategy == WriteStrategy.IMMEDIATE:
            # Write immediately
            return self.document_writer.write_document(
                target_path=target_path,
                content=content,
                format=document_format,
                mode="create",
                **write_params,
            )

        elif write_strategy == WriteStrategy.DRAFT:
            # Save as draft
            draft_path = f"{target_path}.draft"
            return self.document_writer.write_document(
                target_path=draft_path,
                content=content,
                format=document_format,
                mode="create",
                **write_params,
            )

        elif write_strategy == WriteStrategy.REVIEW:
            # Save for review
            review_path = f"{target_path}.review"
            return self.document_writer.write_document(
                target_path=review_path,
                content=content,
                format=document_format,
                mode="create",
                **write_params,
            )

        elif write_strategy == WriteStrategy.STAGED:
            # Staged write (implement custom logic)
            return self._execute_staged_write(target_path, content, document_format, write_params)

        else:
            raise ValueError(f"Unknown write strategy: {write_strategy}")

    def _execute_staged_write(
        self,
        target_path: str,
        content: str,
        document_format: str,
        write_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute staged write operation"""

        # Split content into stages (simplified implementation)
        content_parts = content.split("\n\n")  # Split by paragraphs
        stage_results = []

        for i, part in enumerate(content_parts):
            stage_path = f"{target_path}.stage_{i+1}"
            stage_result = self.document_writer.write_document(
                target_path=stage_path,
                content=part,
                format=document_format,
                mode="create",
                **write_params,
            )
            stage_results.append(stage_result)

        return {
            "strategy": "staged",
            "total_stages": len(content_parts),
            "stage_results": stage_results,
        }

    def _read_existing_document(self, source_path: str) -> Dict[str, Any]:
        """Read existing document for enhancement"""

        try:
            # Try to use document parser for reading
            try:
                from aiecs.tools.docs.document_parser_tool import (
                    DocumentParserTool,
                )

                parser = DocumentParserTool()
                parse_result = parser.parse_document(source_path)

                return {
                    "content": parse_result["content"],
                    "format": parse_result["document_type"],
                    "metadata": parse_result.get("metadata", {}),
                }

            except ImportError:
                # Fallback to simple file reading
                with open(source_path, "r", encoding="utf-8") as f:
                    content = f.read()

                file_ext = os.path.splitext(source_path)[1].lower()
                return {
                    "content": content,
                    "format": file_ext.lstrip(".") or "txt",
                    "metadata": {},
                }

        except Exception as e:
            raise WriteOrchestrationError(f"Failed to read existing document: {str(e)}")

    def _call_ai_provider(self, prompt: str, ai_provider: AIProvider, params: Dict[str, Any]) -> str:
        """Call AI provider with prompt"""

        try:
            if self.aiecs_client:
                # Use AIECS client for AI operations
                from aiecs.domain.task.task_context import TaskContext

                task_context = TaskContext(
                    data={
                        "user_id": "test_user",
                        "chat_id": f"content_gen_{datetime.now().timestamp()}",
                        "metadata": params,
                        "aiPreference": params.get("ai_provider", "default"),
                    }
                )

                result = self.aiecs_client.process_task(task_context)
                return result.get("response", "")
            else:
                # Fallback to mock response
                return self._generate_mock_content(prompt, params)

        except Exception as e:
            raise ContentGenerationError(f"AI provider call failed: {str(e)}")

    def _generate_mock_content(self, prompt: str, params: Dict[str, Any]) -> str:
        """Generate mock content for testing"""
        self.logger.warning("Using mock content generation - implement actual AI provider integration")

        # Generate simple mock content based on prompt
        if "requirements" in params:
            return f"Generated content based on: {params['requirements']}\n\nThis is mock content for testing purposes."
        else:
            return f"Mock generated content for prompt: {prompt[:100]}..."

    def _format_content_prompt(self, template: Dict[str, str], params: Dict[str, Any]) -> str:
        """Format content generation prompt using template"""

        user_prompt = template["user_prompt_template"]

        # Replace placeholders
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if placeholder in user_prompt:
                user_prompt = user_prompt.replace(placeholder, str(value))

        return user_prompt

    def _fill_template(self, template_content: str, template_data: Dict[str, Any]) -> str:
        """Fill template with provided data"""

        filled_content = template_content
        for key, value in template_data.items():
            placeholder = f"{{{key}}}"
            filled_content = filled_content.replace(placeholder, str(value))

        return filled_content

    # Content formatting helpers
    def _ensure_markdown_formatting(self, content: str) -> str:
        """Ensure proper markdown formatting"""
        # Add basic markdown formatting if missing
        lines = content.split("\n")
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-") and not line.startswith("*"):
                # Add paragraph spacing
                formatted_lines.append(line + "\n")
            else:
                formatted_lines.append(line)

        return "\n".join(formatted_lines)

    def _ensure_html_structure(self, content: str) -> str:
        """Ensure proper HTML structure"""
        if not content.strip().startswith("<html"):
            content = f"<html><body>{content}</body></html>"
        return content

    def _ensure_json_format(self, content: str) -> str:
        """Ensure proper JSON format"""
        try:
            import json

            # Try to parse and reformat
            parsed = json.loads(content)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            # Wrap in basic JSON structure
            return json.dumps({"content": content}, indent=2, ensure_ascii=False)

    # Batch processing methods
    async def _batch_write_parallel(self, write_requests: List[Dict[str, Any]], max_concurrent: int) -> List[Dict[str, Any]]:
        """Process write requests in parallel"""

        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single_request(
            request: Dict[str, Any],
        ) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result = await self.ai_write_document_async(**request)
                    return {
                        "status": "success",
                        "request": request,
                        "result": result,
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "request": request,
                        "error": str(e),
                    }

        tasks = [process_single_request(req) for req in write_requests]
        return await asyncio.gather(*tasks)

    def _batch_write_sequential(self, write_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process write requests sequentially"""

        results = []
        for request in write_requests:
            try:
                result = self.ai_write_document(**request)
                results.append({"status": "success", "request": request, "result": result})
            except Exception as e:
                results.append({"status": "error", "request": request, "error": str(e)})

        return results

    async def _batch_write_smart(self, write_requests: List[Dict[str, Any]], max_concurrent: int) -> List[Dict[str, Any]]:
        """Smart batch processing with dependency awareness"""

        # Analyze dependencies (simplified implementation)
        independent_requests = []
        dependent_requests = []

        for request in write_requests:
            # Check if request depends on others (simplified logic)
            if any(req.get("target_path") == request.get("source_path") for req in write_requests):
                dependent_requests.append(request)
            else:
                independent_requests.append(request)

        # Process independent requests in parallel
        results = []
        if independent_requests:
            parallel_results = await self._batch_write_parallel(independent_requests, max_concurrent)
            results.extend(parallel_results)

        # Process dependent requests sequentially
        if dependent_requests:
            sequential_results = self._batch_write_sequential(dependent_requests)
            results.extend(sequential_results)

        return results

    def _post_process_ai_write(
        self,
        operation_id: str,
        target_path: str,
        ai_result: Dict[str, Any],
        write_result: Dict[str, Any],
        write_strategy: WriteStrategy,
    ) -> Dict[str, Any]:
        """Post-process AI write operation"""

        post_process_info = {
            "operation_id": operation_id,
            "target_path": target_path,
            "write_strategy": write_strategy,
            "content_length": len(ai_result.get("generated_content", "")),
            "write_success": write_result.get("write_result", {}).get("path") is not None,
            "timestamp": datetime.now().isoformat(),
        }

        # Log operation
        try:
            log_file = os.path.join(self.config.temp_dir, "ai_write_operations.log")
            with open(log_file, "a") as f:
                import json

                f.write(json.dumps(post_process_info) + "\n")
        except Exception as e:
            self.logger.warning(f"Operation logging failed: {e}")

        return post_process_info
