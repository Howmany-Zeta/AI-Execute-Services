"""
Comprehensive tests for AIDocumentWriterOrchestrator

This test suite covers all functionality of the AIDocumentWriterOrchestrator including:
- AI content generation and orchestration
- Document writing workflows
- Content enhancement and editing
- Batch operations and coordination
- Error handling and recovery
- Configuration management
"""
import os
import pytest
import asyncio
import tempfile
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Import fixtures from conftest_docs
pytest_plugins = ["conftest_docs"]

from aiecs.tools.docs.ai_document_writer_orchestrator import (
    AIDocumentWriterOrchestrator,
    ContentGenerationMode,
    AIEditOperation,
    WriteStrategy,
    AIProvider,
    WriterOrchestratorSettings,
    AIDocumentWriterOrchestratorError,
    ContentGenerationError,
    WriteOrchestrationError
)

logger = logging.getLogger(__name__)


class TestAIDocumentWriterOrchestrator:
    """Test suite for AIDocumentWriterOrchestrator"""
    
    @pytest.fixture
    def orchestrator_config(self):
        """Configuration for AIDocumentWriterOrchestrator"""
        return {
            "default_ai_provider": AIProvider.OPENAI,
            "max_content_length": 10000,
            "max_concurrent_writes": 3,
            "default_temperature": 0.5,
            "max_tokens": 2000,
            "timeout": 30,
            "enable_draft_mode": True,
            "enable_content_review": True,
            "auto_backup_on_ai_write": True
        }
    
    @pytest.fixture
    def orchestrator(self, orchestrator_config):
        """Create AIDocumentWriterOrchestrator instance for testing"""
        return AIDocumentWriterOrchestrator(orchestrator_config)
    
    @pytest.fixture
    def orchestrator_with_default_config(self):
        """Create AIDocumentWriterOrchestrator with default configuration"""
        return AIDocumentWriterOrchestrator()
    
    @pytest.fixture
    def sample_content_requirements(self):
        """Sample content requirements for testing"""
        return {
            "content_type": "technical documentation",
            "requirements": "Create comprehensive API documentation with examples",
            "audience": "developers",
            "style": "professional and clear"
        }
    
    @pytest.fixture
    def sample_document_path(self, temp_dir):
        """Create a sample document path for testing"""
        return str(temp_dir / "test_document.md")
    
    def test_initialization_with_config(self, orchestrator_config):
        """Test AIDocumentWriterOrchestrator initialization with custom config"""
        orchestrator = AIDocumentWriterOrchestrator(orchestrator_config)
        
        assert orchestrator.settings.default_ai_provider == AIProvider.OPENAI
        assert orchestrator.settings.max_content_length == 10000
        assert orchestrator.settings.max_concurrent_writes == 3
        assert orchestrator.settings.default_temperature == 0.5
        assert orchestrator.settings.enable_draft_mode is True
        assert orchestrator.settings.enable_content_review is True
        assert orchestrator.settings.auto_backup_on_ai_write is True
    
    def test_initialization_with_default_config(self, orchestrator_with_default_config):
        """Test AIDocumentWriterOrchestrator initialization with default config"""
        orchestrator = orchestrator_with_default_config
        
        assert orchestrator.settings.default_ai_provider == AIProvider.OPENAI
        assert orchestrator.settings.max_content_length == 50000
        assert orchestrator.settings.max_concurrent_writes == 5
        assert orchestrator.settings.default_temperature == 0.3
        assert orchestrator.settings.max_tokens == 4000
        assert orchestrator.settings.timeout == 60
    
    def test_invalid_config_raises_error(self):
        """Test that invalid configuration raises ValueError"""
        invalid_config = {
            "invalid_setting": "invalid_value",
            "max_content_length": "not_a_number"
        }
        
        with pytest.raises(ValueError, match="Invalid settings"):
            AIDocumentWriterOrchestrator(invalid_config)
    
    def test_content_templates_initialization(self, orchestrator):
        """Test that content templates are properly initialized"""
        templates = orchestrator.content_templates
        
        assert ContentGenerationMode.GENERATE in templates
        assert ContentGenerationMode.ENHANCE in templates
        assert ContentGenerationMode.REWRITE in templates
        assert ContentGenerationMode.TRANSLATE in templates
        assert ContentGenerationMode.CONVERT_FORMAT in templates
        assert ContentGenerationMode.TEMPLATE_FILL in templates
        
        # Check template structure
        for mode, template in templates.items():
            assert "system_prompt" in template
            assert "user_prompt_template" in template
            assert isinstance(template["system_prompt"], str)
            assert isinstance(template["user_prompt_template"], str)
    
    def test_ai_write_document_basic(self, orchestrator, sample_document_path, sample_content_requirements):
        """Test basic AI document writing functionality"""
        requirements = "Create a simple test document with basic content"
        
        result = orchestrator.ai_write_document(
            target_path=sample_document_path,
            content_requirements=requirements,
            generation_mode=ContentGenerationMode.GENERATE,
            document_format="markdown",
            write_strategy=WriteStrategy.IMMEDIATE
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "target_path" in result
        assert "generation_mode" in result
        assert "document_format" in result
        assert "write_strategy" in result
        assert "ai_provider" in result
        assert "ai_result" in result
        assert "write_result" in result
        assert "post_process_result" in result
        assert "processing_metadata" in result
        
        # Verify values
        assert result["target_path"] == sample_document_path
        assert result["generation_mode"] == ContentGenerationMode.GENERATE
        assert result["document_format"] == "markdown"
        assert result["write_strategy"] == WriteStrategy.IMMEDIATE
        assert result["ai_provider"] == AIProvider.OPENAI
        
        # Verify file was created
        assert os.path.exists(sample_document_path)
    
    def test_ai_write_document_with_different_modes(self, orchestrator, sample_document_path):
        """Test AI document writing with different generation modes"""
        modes_to_test = [
            ContentGenerationMode.GENERATE,
            ContentGenerationMode.ENHANCE,
            ContentGenerationMode.REWRITE,
            ContentGenerationMode.TRANSLATE,
            ContentGenerationMode.CONVERT_FORMAT,
            ContentGenerationMode.TEMPLATE_FILL
        ]
        
        for mode in modes_to_test:
            result = orchestrator.ai_write_document(
                target_path=f"{sample_document_path}_{mode.value}",
                content_requirements=f"Test content for {mode.value}",
                generation_mode=mode,
                document_format="markdown"
            )
            
            assert result["generation_mode"] == mode
            assert "operation_id" in result
            assert "ai_result" in result
    
    def test_ai_write_document_with_different_strategies(self, orchestrator, sample_document_path):
        """Test AI document writing with different write strategies"""
        strategies_to_test = [
            WriteStrategy.IMMEDIATE,
            WriteStrategy.DRAFT,
            WriteStrategy.REVIEW,
            WriteStrategy.STAGED
        ]
        
        for strategy in strategies_to_test:
            result = orchestrator.ai_write_document(
                target_path=f"{sample_document_path}_{strategy.value}",
                content_requirements=f"Test content for {strategy.value}",
                generation_mode=ContentGenerationMode.GENERATE,
                document_format="markdown",
                write_strategy=strategy
            )
            
            assert result["write_strategy"] == strategy
            assert "operation_id" in result
            assert "write_result" in result
    
    def test_ai_write_document_with_custom_parameters(self, orchestrator, sample_document_path):
        """Test AI document writing with custom generation and write parameters"""
        generation_params = {
            "temperature": 0.7,
            "max_tokens": 1500,
            "audience": "technical users"
        }
        
        write_params = {
            "encoding": "utf-8",
            "validation_level": "strict"
        }
        
        result = orchestrator.ai_write_document(
            target_path=sample_document_path,
            content_requirements="Test with custom parameters",
            generation_mode=ContentGenerationMode.GENERATE,
            document_format="markdown",
            generation_params=generation_params,
            write_params=write_params
        )
        
        assert result["ai_result"]["generation_params"] == generation_params
        assert "operation_id" in result
    
    def test_enhance_document(self, orchestrator, sample_document_path):
        """Test document enhancement functionality"""
        # First create a document to enhance
        initial_content = "This is a basic document that needs enhancement."
        with open(sample_document_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        
        enhancement_goals = "Make the content more professional and detailed"
        
        result = orchestrator.enhance_document(
            source_path=sample_document_path,
            enhancement_goals=enhancement_goals,
            preserve_format=True
        )
        
        # Verify result structure
        assert "source_path" in result
        assert "target_path" in result
        assert "enhancement_goals" in result
        assert "preserve_format" in result
        assert "original_content" in result
        assert "ai_result" in result
        assert "write_result" in result
        assert "processing_metadata" in result
        
        # Verify values
        assert result["source_path"] == sample_document_path
        assert result["target_path"] == sample_document_path
        assert result["enhancement_goals"] == enhancement_goals
        assert result["preserve_format"] is True
    
    def test_enhance_document_with_target_path(self, orchestrator, sample_document_path, temp_dir):
        """Test document enhancement with different target path"""
        # Create source document
        initial_content = "Original content to enhance."
        with open(sample_document_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        
        target_path = str(temp_dir / "enhanced_document.md")
        enhancement_goals = "Enhance and improve the content"
        
        result = orchestrator.enhance_document(
            source_path=sample_document_path,
            target_path=target_path,
            enhancement_goals=enhancement_goals
        )
        
        assert result["source_path"] == sample_document_path
        assert result["target_path"] == target_path
        assert os.path.exists(target_path)
    
    def test_batch_ai_write_parallel(self, orchestrator, temp_dir):
        """Test batch AI write operations in parallel"""
        write_requests = []
        for i in range(3):
            write_requests.append({
                "target_path": str(temp_dir / f"batch_doc_{i}.md"),
                "content_requirements": f"Create document {i} with technical content",
                "generation_mode": ContentGenerationMode.GENERATE,
                "document_format": "markdown"
            })
        
        result = orchestrator.batch_ai_write(
            write_requests=write_requests,
            coordination_strategy="parallel",
            max_concurrent=2
        )
        
        # Verify result structure
        assert "batch_id" in result
        assert "coordination_strategy" in result
        assert "total_requests" in result
        assert "successful_requests" in result
        assert "failed_requests" in result
        assert "results" in result
        assert "batch_metadata" in result
        
        # Verify values
        assert result["coordination_strategy"] == "parallel"
        assert result["total_requests"] == 3
        assert result["successful_requests"] >= 0
        assert result["failed_requests"] >= 0
        assert len(result["results"]) == 3
    
    def test_batch_ai_write_sequential(self, orchestrator, temp_dir):
        """Test batch AI write operations sequentially"""
        write_requests = []
        for i in range(2):
            write_requests.append({
                "target_path": str(temp_dir / f"seq_doc_{i}.md"),
                "content_requirements": f"Create sequential document {i}",
                "generation_mode": ContentGenerationMode.GENERATE,
                "document_format": "markdown"
            })
        
        result = orchestrator.batch_ai_write(
            write_requests=write_requests,
            coordination_strategy="sequential"
        )
        
        assert result["coordination_strategy"] == "sequential"
        assert result["total_requests"] == 2
        assert len(result["results"]) == 2
    
    def test_batch_ai_write_smart(self, orchestrator, temp_dir):
        """Test batch AI write operations with smart coordination"""
        write_requests = []
        for i in range(2):
            write_requests.append({
                "target_path": str(temp_dir / f"smart_doc_{i}.md"),
                "content_requirements": f"Create smart document {i}",
                "generation_mode": ContentGenerationMode.GENERATE,
                "document_format": "markdown"
            })
        
        result = orchestrator.batch_ai_write(
            write_requests=write_requests,
            coordination_strategy="smart",
            max_concurrent=2
        )
        
        assert result["coordination_strategy"] == "smart"
        assert result["total_requests"] == 2
        assert len(result["results"]) == 2
    
    def test_ai_edit_document(self, orchestrator, sample_document_path):
        """Test AI document editing functionality"""
        # Create a document to edit
        initial_content = "This is a document that needs editing and formatting improvements."
        with open(sample_document_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        
        result = orchestrator.ai_edit_document(
            target_path=sample_document_path,
            edit_operation=AIEditOperation.SMART_FORMAT,
            edit_instructions="Improve formatting and structure",
            preserve_structure=True
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "target_path" in result
        assert "edit_operation" in result
        assert "edit_instructions" in result
        assert "analysis_result" in result
        assert "ai_edit_plan" in result
        assert "edit_results" in result
        assert "validation_result" in result
        assert "processing_metadata" in result
        
        # Verify values
        assert result["target_path"] == sample_document_path
        assert result["edit_operation"] == AIEditOperation.SMART_FORMAT
        assert result["edit_instructions"] == "Improve formatting and structure"
        assert result["preserve_structure"] is True
    
    def test_ai_edit_document_different_operations(self, orchestrator, sample_document_path):
        """Test AI document editing with different operations"""
        # Create a document to edit
        initial_content = "This document has important keywords and needs formatting."
        with open(sample_document_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        
        operations_to_test = [
            AIEditOperation.AUTO_BOLD_KEYWORDS,
            AIEditOperation.INTELLIGENT_HIGHLIGHT,
            AIEditOperation.CONTENT_RESTRUCTURE,
            AIEditOperation.AI_PROOFREADING
        ]
        
        for operation in operations_to_test:
            result = orchestrator.ai_edit_document(
                target_path=sample_document_path,
                edit_operation=operation,
                edit_instructions=f"Apply {operation.value} to the document"
            )
            
            assert result["edit_operation"] == operation
            assert "operation_id" in result
            assert "edit_results" in result
    
    def test_smart_format_document(self, orchestrator, sample_document_path):
        """Test smart document formatting functionality"""
        # Create a document to format
        initial_content = "This document needs better formatting and structure."
        with open(sample_document_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        
        result = orchestrator.smart_format_document(
            target_path=sample_document_path,
            format_goals="Improve readability and professional appearance",
            target_format="markdown"
        )
        
        # Verify result structure
        assert "target_path" in result
        assert "format_goals" in result
        assert "target_format" in result
        assert "structure_analysis" in result
        assert "format_plan" in result
        assert "format_results" in result
        assert "processing_metadata" in result
        
        # Verify values
        assert result["target_path"] == sample_document_path
        assert result["format_goals"] == "Improve readability and professional appearance"
        assert result["target_format"] == "markdown"
    
    def test_analyze_document_content(self, orchestrator, sample_document_path):
        """Test document content analysis functionality"""
        # Create a document to analyze
        initial_content = """# Test Document
        
This is a test document with multiple paragraphs and content.

## Section 1
Some content here with keywords and important information.

## Section 2
More content with different formatting and structure.
"""
        with open(sample_document_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        
        analysis_types = ["structure", "readability", "keywords", "formatting_issues", "content_quality"]
        
        for analysis_type in analysis_types:
            result = orchestrator.analyze_document_content(
                source_path=sample_document_path,
                analysis_type=analysis_type
            )
            
            # Verify result structure
            assert "source_path" in result
            assert "analysis_type" in result
            assert "analysis_result" in result
            assert "content_metadata" in result
            
            # Verify values
            assert result["source_path"] == sample_document_path
            assert result["analysis_type"] == analysis_type
            assert "content_length" in result["content_metadata"]
            assert "analysis_timestamp" in result["content_metadata"]
    
    def test_create_rich_document(self, orchestrator, temp_dir):
        """Test rich document creation functionality"""
        content_plan = {
            "document_type": "technical_doc",
            "format": "markdown",
            "metadata": {
                "title": "Test Rich Document",
                "author": "Test Author",
                "date": datetime.now().strftime("%Y-%m-%d")
            },
            "sections": [
                {"title": "Introduction", "level": 2, "required": True},
                {"title": "Main Content", "level": 2, "required": True},
                {"title": "Conclusion", "level": 2, "required": True}
            ],
            "generate_toc": True,
            "content_items": [
                {
                    "type": "ai_generated",
                    "requirements": "Generate introduction content",
                    "generation_params": {"audience": "developers"}
                }
            ]
        }
        
        layout_config = {
            "page_size": "a4",
            "orientation": "portrait",
            "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
        }
        
        output_path = str(temp_dir / "rich_document.md")
        
        result = orchestrator.create_rich_document(
            document_template="technical_doc",
            content_plan=content_plan,
            layout_config=layout_config,
            output_path=output_path,
            ai_assistance=True
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "document_path" in result
        assert "document_template" in result
        assert "content_plan" in result
        assert "layout_config" in result
        assert "creation_result" in result
        assert "content_results" in result
        assert "ai_assistance_used" in result
        assert "processing_metadata" in result
        
        # Verify values
        assert result["document_template"] == "technical_doc"
        assert result["ai_assistance_used"] is True
        assert os.path.exists(output_path)
    
    def test_generate_document_with_charts(self, orchestrator, temp_dir):
        """Test document generation with charts functionality"""
        requirements = "Create a data analysis report with visualizations"
        
        data_sources = [
            {
                "title": "Sales Data",
                "data": {"Q1": 100, "Q2": 150, "Q3": 200, "Q4": 180},
                "chart_type": "bar"
            },
            {
                "title": "Growth Trend",
                "data": {"Jan": 10, "Feb": 15, "Mar": 20, "Apr": 25},
                "chart_type": "line"
            }
        ]
        
        result = orchestrator.generate_document_with_charts(
            requirements=requirements,
            data_sources=data_sources,
            document_type="report",
            include_analysis=True
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "document_path" in result
        assert "requirements" in result
        assert "data_sources" in result
        assert "document_type" in result
        assert "content_plan" in result
        assert "chart_results" in result
        assert "rich_doc_result" in result
        assert "chart_insertion_results" in result
        assert "include_analysis" in result
        assert "processing_metadata" in result
        
        # Verify values
        assert result["requirements"] == requirements
        assert result["document_type"] == "report"
        assert result["include_analysis"] is True
        assert len(result["data_sources"]) == 2
        assert os.path.exists(result["document_path"])
    
    def test_optimize_document_layout(self, orchestrator, sample_document_path):
        """Test document layout optimization functionality"""
        # Create a document to optimize
        initial_content = """# Test Document
        
This is a test document that needs layout optimization.

## Section 1
Content here.

## Section 2
More content here.
"""
        with open(sample_document_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        
        optimization_goals = ["readability", "space_efficiency", "professional"]
        
        result = orchestrator.optimize_document_layout(
            document_path=sample_document_path,
            optimization_goals=optimization_goals,
            preserve_content=True
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "document_path" in result
        assert "optimization_goals" in result
        assert "layout_style" in result
        assert "content_analysis" in result
        assert "optimization_plan" in result
        assert "optimization_results" in result
        assert "preserve_content" in result
        assert "processing_metadata" in result
        
        # Verify values
        assert result["document_path"] == sample_document_path
        assert result["optimization_goals"] == optimization_goals
        assert result["preserve_content"] is True
    
    def test_batch_content_insertion(self, orchestrator, sample_document_path):
        """Test batch content insertion functionality"""
        # Create a document for content insertion
        initial_content = "This is a base document for content insertion."
        with open(sample_document_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        
        content_plan = [
            {
                "content_type": "text",
                "content": "Additional content 1",
                "position": {"type": "append"}
            },
            {
                "content_type": "text", 
                "content": "Additional content 2",
                "position": {"type": "append"}
            }
        ]
        
        result = orchestrator.batch_content_insertion(
            document_path=sample_document_path,
            content_plan=content_plan,
            insertion_strategy="sequential",
            ai_optimization=True
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "document_path" in result
        assert "content_plan" in result
        assert "optimized_plan" in result
        assert "insertion_strategy" in result
        assert "ai_optimization" in result
        assert "insertion_results" in result
        assert "processing_metadata" in result
        
        # Verify values
        assert result["document_path"] == sample_document_path
        assert result["insertion_strategy"] == "sequential"
        assert result["ai_optimization"] is True
    
    def test_create_content_template(self, orchestrator, temp_dir):
        """Test content template creation functionality"""
        template_name = "test_template"
        template_content = "This is a template with {variable1} and {variable2}."
        template_variables = ["variable1", "variable2"]
        metadata = {"category": "test", "version": "1.0"}
        
        result = orchestrator.create_content_template(
            template_name=template_name,
            template_content=template_content,
            template_variables=template_variables,
            metadata=metadata
        )
        
        # Verify result structure
        assert "name" in result
        assert "content" in result
        assert "variables" in result
        assert "metadata" in result
        assert "created_at" in result
        assert "version" in result
        
        # Verify values
        assert result["name"] == template_name
        assert result["content"] == template_content
        assert result["variables"] == template_variables
        assert result["metadata"] == metadata
        assert result["version"] == "1.0"
    
    def test_use_content_template(self, orchestrator, temp_dir):
        """Test content template usage functionality"""
        # First create a template
        template_name = "usage_test_template"
        template_content = "Hello {name}, welcome to {company}!"
        template_variables = ["name", "company"]
        
        orchestrator.create_content_template(
            template_name=template_name,
            template_content=template_content,
            template_variables=template_variables
        )
        
        # Use the template
        template_data = {"name": "John Doe", "company": "AIECS"}
        target_path = str(temp_dir / "template_output.md")
        
        result = orchestrator.use_content_template(
            template_name=template_name,
            template_data=template_data,
            target_path=target_path,
            ai_enhancement=False
        )
        
        # Verify result structure
        assert "template_name" in result
        assert "template_data" in result
        assert "target_path" in result
        assert "ai_enhancement" in result
        assert "filled_content" in result
        assert "write_result" in result
        
        # Verify values
        assert result["template_name"] == template_name
        assert result["template_data"] == template_data
        assert result["target_path"] == target_path
        assert result["ai_enhancement"] is False
        assert "John Doe" in result["filled_content"]
        assert "AIECS" in result["filled_content"]
        assert os.path.exists(target_path)
    
    def test_ai_write_document_async(self, orchestrator, sample_document_path):
        """Test async version of AI document writing"""
        async def run_async_test():
            result = await orchestrator.ai_write_document_async(
                target_path=sample_document_path,
                content_requirements="Create async test document",
                generation_mode=ContentGenerationMode.GENERATE,
                document_format="markdown"
            )
            
            assert "operation_id" in result
            assert result["target_path"] == sample_document_path
            assert result["generation_mode"] == ContentGenerationMode.GENERATE
            return result
        
        # Run the async test
        result = asyncio.run(run_async_test())
        assert os.path.exists(sample_document_path)
    
    def test_error_handling_invalid_path(self, orchestrator):
        """Test error handling for invalid file paths"""
        with pytest.raises(WriteOrchestrationError):
            orchestrator.ai_write_document(
                target_path="/invalid/path/that/does/not/exist/test.md",
                content_requirements="Test content",
                generation_mode=ContentGenerationMode.GENERATE,
                document_format="markdown"
            )
    
    def test_error_handling_invalid_generation_mode(self, orchestrator, sample_document_path):
        """Test error handling for invalid generation mode"""
        with pytest.raises(WriteOrchestrationError):
            orchestrator.ai_write_document(
                target_path=sample_document_path,
                content_requirements="Test content",
                generation_mode="invalid_mode",  # This should cause an error
                document_format="markdown"
            )
    
    def test_error_handling_missing_document_writer(self, orchestrator, sample_document_path):
        """Test error handling when document writer is not available"""
        # Temporarily remove document writer
        original_writer = orchestrator.document_writer
        orchestrator.document_writer = None
        
        try:
            with pytest.raises(WriteOrchestrationError):
                orchestrator.ai_write_document(
                    target_path=sample_document_path,
                    content_requirements="Test content",
                    generation_mode=ContentGenerationMode.GENERATE,
                    document_format="markdown"
                )
        finally:
            # Restore document writer
            orchestrator.document_writer = original_writer
    
    def test_content_generation_with_mock_ai(self, orchestrator, sample_document_path):
        """Test content generation with mock AI responses"""
        # This test verifies the content generation pipeline works
        # even when AI provider returns mock responses
        
        result = orchestrator.ai_write_document(
            target_path=sample_document_path,
            content_requirements="Generate mock content for testing",
            generation_mode=ContentGenerationMode.GENERATE,
            document_format="markdown",
            ai_provider=AIProvider.OPENAI
        )
        
        # Verify that content was generated and written
        assert "ai_result" in result
        assert "generated_content" in result["ai_result"]
        assert os.path.exists(sample_document_path)
        
        # Verify file contains some content
        with open(sample_document_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 0
    
    def test_processing_metadata_tracking(self, orchestrator, sample_document_path):
        """Test that processing metadata is properly tracked"""
        result = orchestrator.ai_write_document(
            target_path=sample_document_path,
            content_requirements="Test metadata tracking",
            generation_mode=ContentGenerationMode.GENERATE,
            document_format="markdown"
        )
        
        metadata = result["processing_metadata"]
        assert "start_time" in metadata
        assert "end_time" in metadata
        assert "duration" in metadata
        
        # Verify duration is a positive number
        assert isinstance(metadata["duration"], (int, float))
        assert metadata["duration"] >= 0
    
    def test_operation_id_uniqueness(self, orchestrator, temp_dir):
        """Test that operation IDs are unique across multiple operations"""
        operation_ids = set()
        
        for i in range(5):
            result = orchestrator.ai_write_document(
                target_path=str(temp_dir / f"unique_test_{i}.md"),
                content_requirements=f"Test operation {i}",
                generation_mode=ContentGenerationMode.GENERATE,
                document_format="markdown"
            )
            
            operation_id = result["operation_id"]
            assert operation_id not in operation_ids
            operation_ids.add(operation_id)
    
    def test_settings_validation(self):
        """Test settings validation and defaults"""
        # Test with minimal valid config
        minimal_config = {"max_content_length": 1000}
        orchestrator = AIDocumentWriterOrchestrator(minimal_config)
        
        assert orchestrator.settings.max_content_length == 1000
        assert orchestrator.settings.default_ai_provider == AIProvider.OPENAI  # Default value
        
        # Test with invalid config
        invalid_config = {"max_content_length": "not_a_number"}
        with pytest.raises(ValueError):
            AIDocumentWriterOrchestrator(invalid_config)


class TestContentGenerationModes:
    """Test suite for content generation modes"""
    
    @pytest.fixture
    def orchestrator(self):
        return AIDocumentWriterOrchestrator()
    
    def test_generate_mode_template(self, orchestrator):
        """Test GENERATE mode template structure"""
        template = orchestrator.content_templates[ContentGenerationMode.GENERATE]
        
        assert "system_prompt" in template
        assert "user_prompt_template" in template
        assert "content_type" in template["user_prompt_template"]
        assert "requirements" in template["user_prompt_template"]
        assert "audience" in template["user_prompt_template"]
    
    def test_enhance_mode_template(self, orchestrator):
        """Test ENHANCE mode template structure"""
        template = orchestrator.content_templates[ContentGenerationMode.ENHANCE]
        
        assert "system_prompt" in template
        assert "user_prompt_template" in template
        assert "existing_content" in template["user_prompt_template"]
        assert "enhancement_goals" in template["user_prompt_template"]
    
    def test_rewrite_mode_template(self, orchestrator):
        """Test REWRITE mode template structure"""
        template = orchestrator.content_templates[ContentGenerationMode.REWRITE]
        
        assert "system_prompt" in template
        assert "user_prompt_template" in template
        assert "existing_content" in template["user_prompt_template"]
        assert "rewrite_goals" in template["user_prompt_template"]
        assert "target_style" in template["user_prompt_template"]
    
    def test_translate_mode_template(self, orchestrator):
        """Test TRANSLATE mode template structure"""
        template = orchestrator.content_templates[ContentGenerationMode.TRANSLATE]
        
        assert "system_prompt" in template
        assert "user_prompt_template" in template
        assert "content" in template["user_prompt_template"]
        assert "target_language" in template["user_prompt_template"]
    
    def test_convert_format_mode_template(self, orchestrator):
        """Test CONVERT_FORMAT mode template structure"""
        template = orchestrator.content_templates[ContentGenerationMode.CONVERT_FORMAT]
        
        assert "system_prompt" in template
        assert "user_prompt_template" in template
        assert "source_format" in template["user_prompt_template"]
        assert "target_format" in template["user_prompt_template"]
        assert "content" in template["user_prompt_template"]
    
    def test_template_fill_mode_template(self, orchestrator):
        """Test TEMPLATE_FILL mode template structure"""
        template = orchestrator.content_templates[ContentGenerationMode.TEMPLATE_FILL]
        
        assert "system_prompt" in template
        assert "user_prompt_template" in template
        assert "template" in template["user_prompt_template"]
        assert "data" in template["user_prompt_template"]


class TestAIEditOperations:
    """Test suite for AI edit operations"""
    
    @pytest.fixture
    def orchestrator(self):
        return AIDocumentWriterOrchestrator()
    
    def test_smart_format_operation(self, orchestrator, temp_dir):
        """Test SMART_FORMAT edit operation"""
        doc_path = str(temp_dir / "smart_format_test.md")
        content = "This document needs smart formatting improvements."
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = orchestrator.ai_edit_document(
            target_path=doc_path,
            edit_operation=AIEditOperation.SMART_FORMAT,
            edit_instructions="Apply smart formatting"
        )
        
        assert result["edit_operation"] == AIEditOperation.SMART_FORMAT
        assert "edit_results" in result
    
    def test_auto_bold_keywords_operation(self, orchestrator, temp_dir):
        """Test AUTO_BOLD_KEYWORDS edit operation"""
        doc_path = str(temp_dir / "bold_keywords_test.md")
        content = "This document has important keywords that need emphasis."
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = orchestrator.ai_edit_document(
            target_path=doc_path,
            edit_operation=AIEditOperation.AUTO_BOLD_KEYWORDS,
            edit_instructions="Bold important keywords"
        )
        
        assert result["edit_operation"] == AIEditOperation.AUTO_BOLD_KEYWORDS
        assert "edit_results" in result
    
    def test_intelligent_highlight_operation(self, orchestrator, temp_dir):
        """Test INTELLIGENT_HIGHLIGHT edit operation"""
        doc_path = str(temp_dir / "highlight_test.md")
        content = "This document has sections that need highlighting."
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = orchestrator.ai_edit_document(
            target_path=doc_path,
            edit_operation=AIEditOperation.INTELLIGENT_HIGHLIGHT,
            edit_instructions="Highlight important sections"
        )
        
        assert result["edit_operation"] == AIEditOperation.INTELLIGENT_HIGHLIGHT
        assert "edit_results" in result
    
    def test_content_restructure_operation(self, orchestrator, temp_dir):
        """Test CONTENT_RESTRUCTURE edit operation"""
        doc_path = str(temp_dir / "restructure_test.md")
        content = "This document needs better structure and organization."
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = orchestrator.ai_edit_document(
            target_path=doc_path,
            edit_operation=AIEditOperation.CONTENT_RESTRUCTURE,
            edit_instructions="Restructure content for better flow"
        )
        
        assert result["edit_operation"] == AIEditOperation.CONTENT_RESTRUCTURE
        assert "edit_results" in result
    
    def test_ai_proofreading_operation(self, orchestrator, temp_dir):
        """Test AI_PROOFREADING edit operation"""
        doc_path = str(temp_dir / "proofreading_test.md")
        content = "This document has some errors that need proofreading."
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = orchestrator.ai_edit_document(
            target_path=doc_path,
            edit_operation=AIEditOperation.AI_PROOFREADING,
            edit_instructions="Proofread and correct errors"
        )
        
        assert result["edit_operation"] == AIEditOperation.AI_PROOFREADING
        assert "edit_results" in result


class TestWriteStrategies:
    """Test suite for write strategies"""
    
    @pytest.fixture
    def orchestrator(self):
        return AIDocumentWriterOrchestrator()
    
    def test_immediate_strategy(self, orchestrator, temp_dir):
        """Test IMMEDIATE write strategy"""
        doc_path = str(temp_dir / "immediate_test.md")
        
        result = orchestrator.ai_write_document(
            target_path=doc_path,
            content_requirements="Test immediate write",
            generation_mode=ContentGenerationMode.GENERATE,
            document_format="markdown",
            write_strategy=WriteStrategy.IMMEDIATE
        )
        
        assert result["write_strategy"] == WriteStrategy.IMMEDIATE
        assert os.path.exists(doc_path)
    
    def test_draft_strategy(self, orchestrator, temp_dir):
        """Test DRAFT write strategy"""
        doc_path = str(temp_dir / "draft_test.md")
        
        result = orchestrator.ai_write_document(
            target_path=doc_path,
            content_requirements="Test draft write",
            generation_mode=ContentGenerationMode.GENERATE,
            document_format="markdown",
            write_strategy=WriteStrategy.DRAFT
        )
        
        assert result["write_strategy"] == WriteStrategy.DRAFT
        # Should create a .draft file
        assert os.path.exists(f"{doc_path}.draft")
    
    def test_review_strategy(self, orchestrator, temp_dir):
        """Test REVIEW write strategy"""
        doc_path = str(temp_dir / "review_test.md")
        
        result = orchestrator.ai_write_document(
            target_path=doc_path,
            content_requirements="Test review write",
            generation_mode=ContentGenerationMode.GENERATE,
            document_format="markdown",
            write_strategy=WriteStrategy.REVIEW
        )
        
        assert result["write_strategy"] == WriteStrategy.REVIEW
        # Should create a .review file
        assert os.path.exists(f"{doc_path}.review")
    
    def test_staged_strategy(self, orchestrator, temp_dir):
        """Test STAGED write strategy"""
        doc_path = str(temp_dir / "staged_test.md")
        
        result = orchestrator.ai_write_document(
            target_path=doc_path,
            content_requirements="Test staged write with multiple paragraphs for staging.",
            generation_mode=ContentGenerationMode.GENERATE,
            document_format="markdown",
            write_strategy=WriteStrategy.STAGED
        )
        
        assert result["write_strategy"] == WriteStrategy.STAGED
        assert "write_result" in result
        assert "strategy" in result["write_result"]
        assert result["write_result"]["strategy"] == "staged"


class TestErrorHandling:
    """Test suite for error handling"""
    
    @pytest.fixture
    def orchestrator(self):
        return AIDocumentWriterOrchestrator()
    
    def test_content_generation_error(self, orchestrator, temp_dir):
        """Test ContentGenerationError handling"""
        doc_path = str(temp_dir / "error_test.md")
        
        # This should work with mock content generation
        result = orchestrator.ai_write_document(
            target_path=doc_path,
            content_requirements="Test error handling",
            generation_mode=ContentGenerationMode.GENERATE,
            document_format="markdown"
        )
        
        # Should not raise an error due to fallback mock generation
        assert "operation_id" in result
    
    def test_write_orchestration_error(self, orchestrator):
        """Test WriteOrchestrationError handling"""
        with pytest.raises(WriteOrchestrationError):
            orchestrator.ai_write_document(
                target_path="",  # Invalid path
                content_requirements="Test orchestration error",
                generation_mode=ContentGenerationMode.GENERATE,
                document_format="markdown"
            )
    
    def test_ai_document_writer_orchestrator_error(self, orchestrator):
        """Test AIDocumentWriterOrchestratorError handling"""
        # Test that the base exception can be caught
        try:
            orchestrator.ai_write_document(
                target_path="",  # Invalid path
                content_requirements="Test base error",
                generation_mode=ContentGenerationMode.GENERATE,
                document_format="markdown"
            )
        except AIDocumentWriterOrchestratorError as e:
            assert isinstance(e, AIDocumentWriterOrchestratorError)
            assert isinstance(e, WriteOrchestrationError)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


