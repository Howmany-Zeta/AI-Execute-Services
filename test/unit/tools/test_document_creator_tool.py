"""
Comprehensive tests for DocumentCreatorTool

This test suite covers all functionality of the DocumentCreatorTool including:
- Document creation from templates
- Template management and selection
- Document structure initialization
- Metadata configuration
- Style and format setup
- Multi-format document creation
- Error handling and recovery
"""
import os
import pytest
import tempfile
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Import fixtures from conftest_docs
pytest_plugins = ["conftest_docs"]

from aiecs.tools.docs.document_creator_tool import (
    DocumentCreatorTool,
    DocumentType,
    DocumentFormat,
    TemplateType,
    StylePreset,
    DocumentCreatorSettings,
    DocumentCreatorError,
    TemplateError,
    DocumentCreationError
)

logger = logging.getLogger(__name__)


class TestDocumentCreatorTool:
    """Test suite for DocumentCreatorTool"""
    
    @pytest.fixture
    def creator_config(self):
        """Configuration for DocumentCreatorTool"""
        return {
            "templates_dir": "/tmp/test_templates",
            "output_dir": "/tmp/test_output",
            "default_format": DocumentFormat.MARKDOWN,
            "default_style": StylePreset.DEFAULT,
            "auto_backup": True,
            "include_metadata": True,
            "generate_toc": True
        }
    
    @pytest.fixture
    def creator_tool(self, creator_config):
        """Create DocumentCreatorTool instance for testing"""
        return DocumentCreatorTool(creator_config)
    
    @pytest.fixture
    def creator_tool_with_default_config(self):
        """Create DocumentCreatorTool with default configuration"""
        return DocumentCreatorTool()
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing"""
        return {
            "title": "Test Document",
            "author": "Test Author",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "department": "Testing",
            "version": "1.0"
        }
    
    def test_initialization_with_config(self, creator_config):
        """Test DocumentCreatorTool initialization with custom config"""
        creator_tool = DocumentCreatorTool(creator_config)
        
        assert creator_tool.settings.default_format == DocumentFormat.MARKDOWN
        assert creator_tool.settings.default_style == StylePreset.DEFAULT
        assert creator_tool.settings.auto_backup is True
        assert creator_tool.settings.include_metadata is True
        assert creator_tool.settings.generate_toc is True
    
    def test_initialization_with_default_config(self, creator_tool_with_default_config):
        """Test DocumentCreatorTool initialization with default config"""
        creator_tool = creator_tool_with_default_config
        
        assert creator_tool.settings.default_format == DocumentFormat.MARKDOWN
        assert creator_tool.settings.default_style == StylePreset.DEFAULT
        assert creator_tool.settings.auto_backup is True
        assert creator_tool.settings.include_metadata is True
        assert creator_tool.settings.generate_toc is True
    
    def test_invalid_config_raises_error(self):
        """Test that invalid configuration raises ValueError"""
        invalid_config = {
            "invalid_setting": "invalid_value",
            "default_format": "invalid_format"
        }
        
        with pytest.raises(ValueError, match="Invalid settings"):
            DocumentCreatorTool(invalid_config)
    
    def test_templates_initialization(self, creator_tool):
        """Test that templates are properly initialized"""
        templates = creator_tool.templates
        
        expected_templates = [
            TemplateType.BLANK,
            TemplateType.BUSINESS_REPORT,
            TemplateType.TECHNICAL_DOC,
            TemplateType.ACADEMIC_PAPER,
            TemplateType.PROJECT_PROPOSAL,
            TemplateType.USER_MANUAL,
            TemplateType.PRESENTATION,
            TemplateType.NEWSLETTER,
            TemplateType.INVOICE
        ]
        
        for template_type in expected_templates:
            assert template_type in templates
            template = templates[template_type]
            assert "name" in template
            assert "description" in template
            assert "content" in template
            assert "sections" in template
            assert "variables" in template
            assert "supported_formats" in template
    
    def test_create_document_basic(self, creator_tool, sample_metadata, temp_dir):
        """Test basic document creation functionality"""
        output_path = str(temp_dir / "test_document.md")
        
        result = creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata=sample_metadata,
            output_path=output_path
        )
        
        # Verify result structure
        assert "document_id" in result
        assert "document_type" in result
        assert "template_type" in result
        assert "output_format" in result
        assert "output_path" in result
        assert "metadata" in result
        assert "style_preset" in result
        assert "creation_metadata" in result
        
        # Verify values
        assert result["document_type"] == DocumentType.REPORT
        assert result["template_type"] == TemplateType.BLANK
        assert result["output_format"] == DocumentFormat.MARKDOWN
        assert result["output_path"] == output_path
        assert result["metadata"] == sample_metadata
        
        # Verify file was created
        assert os.path.exists(output_path)
    
    def test_create_document_with_different_types(self, creator_tool, sample_metadata, temp_dir):
        """Test document creation with different document types"""
        types_to_test = [
            DocumentType.REPORT,
            DocumentType.ARTICLE,
            DocumentType.PRESENTATION,
            DocumentType.MANUAL,
            DocumentType.LETTER,
            DocumentType.PROPOSAL,
            DocumentType.ACADEMIC,
            DocumentType.TECHNICAL,
            DocumentType.CREATIVE,
            DocumentType.CUSTOM
        ]
        
        for doc_type in types_to_test:
            output_path = str(temp_dir / f"test_{doc_type.value}.md")
            
            result = creator_tool.create_document(
                document_type=doc_type,
                template_type=TemplateType.BLANK,
                output_format=DocumentFormat.MARKDOWN,
                metadata=sample_metadata,
                output_path=output_path
            )
            
            assert result["document_type"] == doc_type
            assert os.path.exists(output_path)
    
    def test_create_document_with_different_templates(self, creator_tool, sample_metadata, temp_dir):
        """Test document creation with different templates"""
        templates_to_test = [
            TemplateType.BLANK,
            TemplateType.BUSINESS_REPORT,
            TemplateType.TECHNICAL_DOC,
            TemplateType.ACADEMIC_PAPER,
            TemplateType.PROJECT_PROPOSAL,
            TemplateType.USER_MANUAL,
            TemplateType.PRESENTATION,
            TemplateType.NEWSLETTER,
            TemplateType.INVOICE
        ]
        
        for template_type in templates_to_test:
            output_path = str(temp_dir / f"test_{template_type.value}.md")
            
            result = creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=template_type,
                output_format=DocumentFormat.MARKDOWN,
                metadata=sample_metadata,
                output_path=output_path
            )
            
            assert result["template_type"] == template_type
            assert os.path.exists(output_path)
    
    def test_create_document_with_different_formats(self, creator_tool, sample_metadata, temp_dir):
        """Test document creation with different output formats"""
        formats_to_test = [
            DocumentFormat.MARKDOWN,
            DocumentFormat.HTML,
            DocumentFormat.PLAIN_TEXT,
            DocumentFormat.JSON,
            DocumentFormat.XML
        ]
        
        for output_format in formats_to_test:
            output_path = str(temp_dir / f"test.{output_format.value}")
            
            result = creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=TemplateType.BLANK,
                output_format=output_format,
                metadata=sample_metadata,
                output_path=output_path
            )
            
            assert result["output_format"] == output_format
            assert os.path.exists(output_path)
    
    def test_create_document_with_style_presets(self, creator_tool, sample_metadata, temp_dir):
        """Test document creation with different style presets"""
        presets_to_test = [
            StylePreset.DEFAULT,
            StylePreset.CORPORATE,
            StylePreset.ACADEMIC,
            StylePreset.MODERN,
            StylePreset.CLASSIC,
            StylePreset.MINIMAL,
            StylePreset.COLORFUL,
            StylePreset.PROFESSIONAL
        ]
        
        for style_preset in presets_to_test:
            output_path = str(temp_dir / f"test_{style_preset.value}.md")
            
            result = creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=TemplateType.BLANK,
                output_format=DocumentFormat.MARKDOWN,
                metadata=sample_metadata,
                style_preset=style_preset,
                output_path=output_path
            )
            
            assert result["style_preset"] == style_preset
            assert os.path.exists(output_path)
    
    def test_create_document_without_output_path(self, creator_tool, sample_metadata):
        """Test document creation without specifying output path"""
        result = creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata=sample_metadata
        )
        
        assert "output_path" in result
        assert os.path.exists(result["output_path"])
    
    def test_create_from_template_basic(self, creator_tool, temp_dir):
        """Test basic document creation from custom template"""
        # Create a custom template
        template_name = "test_template.md"
        template_content = """# {title}

**Author:** {author}
**Date:** {date}

## Introduction

{introduction}

## Main Content

{main_content}

## Conclusion

{conclusion}
"""
        
        template_path = Path(creator_tool.settings.templates_dir) / template_name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        # Use the template
        template_variables = {
            "title": "Test Document",
            "author": "Test Author",
            "date": "2024-01-01",
            "introduction": "This is the introduction.",
            "main_content": "This is the main content.",
            "conclusion": "This is the conclusion."
        }
        
        output_path = str(temp_dir / "template_output.md")
        
        result = creator_tool.create_from_template(
            template_name=template_name,
            template_variables=template_variables,
            output_format=DocumentFormat.MARKDOWN,
            output_path=output_path
        )
        
        # Verify result structure
        assert "template_name" in result
        assert "output_path" in result
        assert "output_format" in result
        assert "variables_used" in result
        assert "creation_time" in result
        
        # Verify values
        assert result["template_name"] == template_name
        assert result["output_path"] == output_path
        assert result["output_format"] == DocumentFormat.MARKDOWN
        assert result["variables_used"] == template_variables
        
        # Verify file was created and contains processed content
        assert os.path.exists(output_path)
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test Document" in content
            assert "Test Author" in content
            assert "This is the introduction." in content
    
    def test_create_from_template_nonexistent(self, creator_tool, temp_dir):
        """Test document creation from non-existent template"""
        with pytest.raises(TemplateError, match="Template not found"):
            creator_tool.create_from_template(
                template_name="nonexistent_template.md",
                template_variables={"title": "Test"},
                output_format=DocumentFormat.MARKDOWN,
                output_path=str(temp_dir / "test.md")
            )
    
    def test_setup_document_structure_basic(self, creator_tool, temp_dir):
        """Test basic document structure setup"""
        doc_path = str(temp_dir / "structure_test.md")
        
        # Create initial document
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Initial Document\n\nSome initial content.\n")
        
        sections = [
            {"title": "Introduction", "level": 2, "required": True},
            {"title": "Main Content", "level": 2, "required": True},
            {"title": "Conclusion", "level": 2, "required": True}
        ]
        
        result = creator_tool.setup_document_structure(
            document_path=doc_path,
            sections=sections,
            generate_toc=True,
            numbering_style="numeric"
        )
        
        # Verify result structure
        assert "document_path" in result
        assert "sections_created" in result
        assert "toc_generated" in result
        assert "numbering_style" in result
        assert "structure_setup_time" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["sections_created"] == 3
        assert result["toc_generated"] is True
        assert result["numbering_style"] == "numeric"
        
        # Verify file was updated with structure
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "# Table of Contents" in content
            assert "## 1. Introduction" in content
            assert "## 2. Main Content" in content
            assert "## 3. Conclusion" in content
    
    def test_setup_document_structure_different_numbering(self, creator_tool, temp_dir):
        """Test document structure setup with different numbering styles"""
        doc_path = str(temp_dir / "numbering_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        sections = [
            {"title": "Section A", "level": 2, "required": True},
            {"title": "Section B", "level": 2, "required": True}
        ]
        
        # Test alpha numbering
        result = creator_tool.setup_document_structure(
            document_path=doc_path,
            sections=sections,
            generate_toc=True,
            numbering_style="alpha"
        )
        
        assert result["numbering_style"] == "alpha"
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "## A. Section A" in content
            assert "## B. Section B" in content
    
    def test_setup_document_structure_without_toc(self, creator_tool, temp_dir):
        """Test document structure setup without table of contents"""
        doc_path = str(temp_dir / "no_toc_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        sections = [
            {"title": "Section 1", "level": 2, "required": True}
        ]
        
        result = creator_tool.setup_document_structure(
            document_path=doc_path,
            sections=sections,
            generate_toc=False
        )
        
        assert result["toc_generated"] is False
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "# Table of Contents" not in content
            assert "## Section 1" in content
    
    def test_configure_metadata_basic(self, creator_tool, temp_dir):
        """Test basic metadata configuration"""
        doc_path = str(temp_dir / "metadata_test.md")
        
        # Create initial document
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\nContent here.\n")
        
        metadata = {
            "title": "Configured Document",
            "author": "Metadata Author",
            "date": "2024-01-01",
            "version": "2.0",
            "tags": ["test", "metadata"]
        }
        
        result = creator_tool.configure_metadata(
            document_path=doc_path,
            metadata=metadata,
            format_specific=True
        )
        
        # Verify result structure
        assert "document_path" in result
        assert "metadata_configured" in result
        assert "format" in result
        assert "format_specific" in result
        assert "configuration_time" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["metadata_configured"] == metadata
        assert result["format_specific"] is True
        
        # Verify metadata was added to document
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "title: Configured Document" in content
            assert "author: Metadata Author" in content
    
    def test_configure_metadata_format_specific(self, creator_tool, temp_dir):
        """Test metadata configuration with format-specific syntax"""
        # Test Markdown format
        md_path = str(temp_dir / "md_metadata.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Test\n")
        
        metadata = {"title": "MD Document", "author": "MD Author"}
        
        result = creator_tool.configure_metadata(
            document_path=md_path,
            metadata=metadata,
            format_specific=True
        )
        
        assert result["format"] == "markdown"
        
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "---" in content  # YAML front matter
        
        # Test HTML format
        html_path = str(temp_dir / "html_metadata.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write("<html><body><h1>Test</h1></body></html>")
        
        result = creator_tool.configure_metadata(
            document_path=html_path,
            metadata=metadata,
            format_specific=True
        )
        
        assert result["format"] == "html"
        
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "<meta name=" in content
    
    def test_configure_metadata_generic(self, creator_tool, temp_dir):
        """Test metadata configuration with generic syntax"""
        doc_path = str(temp_dir / "generic_metadata.txt")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("Test Document\n")
        
        metadata = {"title": "Generic Document", "author": "Generic Author"}
        
        result = creator_tool.configure_metadata(
            document_path=doc_path,
            metadata=metadata,
            format_specific=False
        )
        
        assert result["format_specific"] is False
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "% title: Generic Document" in content
            assert "% author: Generic Author" in content
    
    def test_list_templates(self, creator_tool, temp_dir):
        """Test listing available templates"""
        # Create a custom template
        custom_template_path = Path(creator_tool.settings.templates_dir) / "custom_template.md"
        custom_template_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(custom_template_path, 'w', encoding='utf-8') as f:
            f.write("# Custom Template\n")
        
        result = creator_tool.list_templates()
        
        # Verify result structure
        assert "built_in_templates" in result
        assert "custom_templates" in result
        assert "templates_directory" in result
        assert "total_templates" in result
        
        # Verify built-in templates
        expected_built_in = [
            "blank", "business_report", "technical_doc", "academic_paper",
            "project_proposal", "user_manual", "presentation", "newsletter", "invoice"
        ]
        
        for template in expected_built_in:
            assert template in result["built_in_templates"]
        
        # Verify custom template
        assert "custom_template.md" in result["custom_templates"]
        assert result["templates_directory"] == creator_tool.settings.templates_dir
        assert result["total_templates"] == len(expected_built_in) + 1
    
    def test_get_template_info(self, creator_tool):
        """Test getting template information"""
        result = creator_tool.get_template_info(TemplateType.BUSINESS_REPORT)
        
        # Verify result structure
        assert "template_type" in result
        assert "name" in result
        assert "description" in result
        assert "sections" in result
        assert "variables" in result
        assert "supported_formats" in result
        assert "style_presets" in result
        
        # Verify values
        assert result["template_type"] == "business_report"
        assert result["name"] == "Business Report"
        assert "description" in result["description"]
        assert len(result["sections"]) > 0
        assert len(result["variables"]) > 0
        assert len(result["supported_formats"]) > 0
    
    def test_get_template_info_nonexistent(self, creator_tool):
        """Test getting information for non-existent template"""
        with pytest.raises(TemplateError, match="Template not found"):
            creator_tool.get_template_info("nonexistent_template")
    
    def test_get_created_documents(self, creator_tool, sample_metadata, temp_dir):
        """Test getting list of created documents"""
        initial_count = len(creator_tool.get_created_documents())
        
        # Create a document
        output_path = str(temp_dir / "tracking_test.md")
        creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata=sample_metadata,
            output_path=output_path
        )
        
        created_docs = creator_tool.get_created_documents()
        assert len(created_docs) == initial_count + 1
        
        # Verify document info
        doc_info = created_docs[-1]
        assert "document_id" in doc_info
        assert "document_type" in doc_info
        assert "template_type" in doc_info
        assert "output_path" in doc_info
        assert "creation_metadata" in doc_info
    
    def test_error_handling_invalid_document_type(self, creator_tool, sample_metadata, temp_dir):
        """Test error handling for invalid document type"""
        with pytest.raises(DocumentCreationError):
            creator_tool.create_document(
                document_type="invalid_type",  # This should cause an error
                template_type=TemplateType.BLANK,
                output_format=DocumentFormat.MARKDOWN,
                metadata=sample_metadata,
                output_path=str(temp_dir / "test.md")
            )
    
    def test_error_handling_invalid_template_type(self, creator_tool, sample_metadata, temp_dir):
        """Test error handling for invalid template type"""
        with pytest.raises(DocumentCreationError):
            creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type="invalid_template",  # This should cause an error
                output_format=DocumentFormat.MARKDOWN,
                metadata=sample_metadata,
                output_path=str(temp_dir / "test.md")
            )
    
    def test_error_handling_invalid_output_format(self, creator_tool, sample_metadata, temp_dir):
        """Test error handling for invalid output format"""
        with pytest.raises(DocumentCreationError):
            creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=TemplateType.BLANK,
                output_format="invalid_format",  # This should cause an error
                metadata=sample_metadata,
                output_path=str(temp_dir / "test.md")
            )
    
    def test_document_id_uniqueness(self, creator_tool, sample_metadata, temp_dir):
        """Test that document IDs are unique across multiple creations"""
        document_ids = set()
        
        for i in range(5):
            output_path = str(temp_dir / f"unique_test_{i}.md")
            result = creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=TemplateType.BLANK,
                output_format=DocumentFormat.MARKDOWN,
                metadata=sample_metadata,
                output_path=output_path
            )
            
            document_id = result["document_id"]
            assert document_id not in document_ids
            document_ids.add(document_id)
    
    def test_creation_metadata_tracking(self, creator_tool, sample_metadata, temp_dir):
        """Test that creation metadata is properly tracked"""
        output_path = str(temp_dir / "metadata_tracking_test.md")
        
        result = creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata=sample_metadata,
            output_path=output_path
        )
        
        metadata = result["creation_metadata"]
        assert "created_at" in metadata
        assert "file_size" in metadata
        assert "duration" in metadata
        
        # Verify duration is a positive number
        assert isinstance(metadata["duration"], (int, float))
        assert metadata["duration"] >= 0
        
        # Verify file size
        assert metadata["file_size"] > 0


class TestTemplateDefinitions:
    """Test suite for template definitions"""
    
    @pytest.fixture
    def creator_tool(self):
        return DocumentCreatorTool()
    
    def test_blank_template(self, creator_tool):
        """Test blank template structure"""
        template = creator_tool._get_blank_template()
        
        assert template["name"] == "Blank Document"
        assert template["description"] == "Empty document with basic structure"
        assert template["content"] == ""
        assert template["sections"] == []
        assert template["variables"] == []
        assert "markdown" in template["supported_formats"]
        assert "metadata_template" in template
    
    def test_business_report_template(self, creator_tool):
        """Test business report template structure"""
        template = creator_tool._get_business_report_template()
        
        assert template["name"] == "Business Report"
        assert template["description"] == "Professional business report template"
        assert "{title}" in template["content"]
        assert "{author}" in template["content"]
        assert "{date}" in template["content"]
        assert len(template["sections"]) > 0
        assert "title" in template["variables"]
        assert "author" in template["variables"]
        assert "markdown" in template["supported_formats"]
        assert "corporate" in template["style_presets"]
    
    def test_technical_doc_template(self, creator_tool):
        """Test technical documentation template structure"""
        template = creator_tool._get_technical_doc_template()
        
        assert template["name"] == "Technical Documentation"
        assert template["description"] == "Technical documentation with code examples"
        assert "{title}" in template["content"]
        assert "{version}" in template["content"]
        assert len(template["sections"]) > 0
        assert "title" in template["variables"]
        assert "version" in template["variables"]
        assert "markdown" in template["supported_formats"]
        assert "technical" in template["style_presets"]
    
    def test_academic_paper_template(self, creator_tool):
        """Test academic paper template structure"""
        template = creator_tool._get_academic_paper_template()
        
        assert template["name"] == "Academic Paper"
        assert template["description"] == "Academic research paper template"
        assert "{title}" in template["content"]
        assert "{author}" in template["content"]
        assert "{institution}" in template["content"]
        assert len(template["sections"]) > 0
        assert "title" in template["variables"]
        assert "author" in template["variables"]
        assert "institution" in template["variables"]
        assert "markdown" in template["supported_formats"]
        assert "academic" in template["style_presets"]
    
    def test_project_proposal_template(self, creator_tool):
        """Test project proposal template structure"""
        template = creator_tool._get_project_proposal_template()
        
        assert template["name"] == "Project Proposal"
        assert template["description"] == "Project proposal and planning template"
        assert "{project_name}" in template["content"]
        assert "{project_manager}" in template["content"]
        assert "{budget}" in template["content"]
        assert len(template["sections"]) > 0
        assert "project_name" in template["variables"]
        assert "project_manager" in template["variables"]
        assert "budget" in template["variables"]
        assert "markdown" in template["supported_formats"]
        assert "professional" in template["style_presets"]
    
    def test_user_manual_template(self, creator_tool):
        """Test user manual template structure"""
        template = creator_tool._get_user_manual_template()
        
        assert template["name"] == "User Manual"
        assert template["description"] == "User manual and guide template"
        assert "{product_name}" in template["content"]
        assert "{version}" in template["content"]
        assert len(template["sections"]) > 0
        assert "product_name" in template["variables"]
        assert "version" in template["variables"]
        assert "markdown" in template["supported_formats"]
        assert "user-friendly" in template["style_presets"]
    
    def test_presentation_template(self, creator_tool):
        """Test presentation template structure"""
        template = creator_tool._get_presentation_template()
        
        assert template["name"] == "Presentation"
        assert template["description"] == "Slide presentation template"
        assert "{title}" in template["content"]
        assert "{presenter}" in template["content"]
        assert "---" in template["content"]  # Slide separators
        assert len(template["sections"]) > 0
        assert "title" in template["variables"]
        assert "presenter" in template["variables"]
        assert "markdown" in template["supported_formats"]
        assert "presentation" in template["style_presets"]
    
    def test_newsletter_template(self, creator_tool):
        """Test newsletter template structure"""
        template = creator_tool._get_newsletter_template()
        
        assert template["name"] == "Newsletter"
        assert template["description"] == "Newsletter and bulletin template"
        assert "{newsletter_name}" in template["content"]
        assert "{issue_number}" in template["content"]
        assert len(template["sections"]) > 0
        assert "newsletter_name" in template["variables"]
        assert "issue_number" in template["variables"]
        assert "markdown" in template["supported_formats"]
        assert "newsletter" in template["style_presets"]
    
    def test_invoice_template(self, creator_tool):
        """Test invoice template structure"""
        template = creator_tool._get_invoice_template()
        
        assert template["name"] == "Invoice"
        assert template["description"] == "Business invoice template"
        assert "{invoice_number}" in template["content"]
        assert "{date}" in template["content"]
        assert "{due_date}" in template["content"]
        assert len(template["sections"]) > 0
        assert "invoice_number" in template["variables"]
        assert "date" in template["variables"]
        assert "due_date" in template["variables"]
        assert "markdown" in template["supported_formats"]
        assert "professional" in template["style_presets"]


class TestHelperMethods:
    """Test suite for helper methods"""
    
    @pytest.fixture
    def creator_tool(self):
        return DocumentCreatorTool()
    
    def test_get_template(self, creator_tool):
        """Test getting template by type"""
        template = creator_tool._get_template(TemplateType.BUSINESS_REPORT)
        
        assert template["name"] == "Business Report"
        assert "content" in template
        assert "variables" in template
    
    def test_get_template_nonexistent(self, creator_tool):
        """Test getting non-existent template"""
        with pytest.raises(TemplateError, match="Template not found"):
            creator_tool._get_template("nonexistent_template")
    
    def test_generate_output_path(self, creator_tool):
        """Test output path generation"""
        output_path = creator_tool._generate_output_path(
            "report", DocumentFormat.MARKDOWN, "test_id"
        )
        
        assert output_path.endswith(".markdown")
        assert "report" in output_path
        assert "test_id" in output_path
        assert creator_tool.settings.output_dir in output_path
    
    def test_process_metadata(self, creator_tool):
        """Test metadata processing"""
        input_metadata = {
            "title": "Test Document",
            "author": "Test Author"
        }
        
        processed = creator_tool._process_metadata(input_metadata, DocumentFormat.MARKDOWN)
        
        assert processed["title"] == "Test Document"
        assert processed["author"] == "Test Author"
        assert "date" in processed  # Should be added
        assert "created_by" in processed  # Should be added
        assert processed["format"] == "markdown"
    
    def test_get_style_config(self, creator_tool):
        """Test style configuration retrieval"""
        # Test default style
        config = creator_tool._get_style_config(StylePreset.DEFAULT)
        assert "font_family" in config
        assert "font_size" in config
        assert "colors" in config
        
        # Test corporate style
        config = creator_tool._get_style_config(StylePreset.CORPORATE)
        assert config["font_family"] == "Calibri"
        assert config["font_size"] == 11
        
        # Test academic style
        config = creator_tool._get_style_config(StylePreset.ACADEMIC)
        assert config["font_family"] == "Times New Roman"
        assert config["font_size"] == 12
    
    def test_create_document_from_template(self, creator_tool):
        """Test document creation from template"""
        template = creator_tool._get_blank_template()
        metadata = {"title": "Test", "author": "Author"}
        style_config = {"font_family": "Arial", "font_size": 12}
        
        content = creator_tool._create_document_from_template(
            template, metadata, style_config, DocumentFormat.MARKDOWN
        )
        
        assert isinstance(content, str)
        # Should include metadata header if include_metadata is True
        if creator_tool.settings.include_metadata:
            assert "title: Test" in content
    
    def test_generate_metadata_header(self, creator_tool):
        """Test metadata header generation"""
        metadata = {"title": "Test", "author": "Author", "date": "2024-01-01"}
        
        # Test Markdown format
        md_header = creator_tool._generate_metadata_header(metadata, DocumentFormat.MARKDOWN)
        assert "---" in md_header
        assert "title: Test" in md_header
        assert "author: Author" in md_header
        
        # Test HTML format
        html_header = creator_tool._generate_metadata_header(metadata, DocumentFormat.HTML)
        assert "<meta name=" in html_header
        assert 'content="Test"' in html_header
        
        # Test other formats
        other_header = creator_tool._generate_metadata_header(metadata, DocumentFormat.PLAIN_TEXT)
        assert "Document Metadata" in other_header
        assert "title: Test" in other_header
    
    def test_write_document_file(self, creator_tool, temp_dir):
        """Test document file writing"""
        content = "Test document content"
        output_path = str(temp_dir / "write_test.md")
        
        creator_tool._write_document_file(output_path, content, DocumentFormat.MARKDOWN)
        
        assert os.path.exists(output_path)
        with open(output_path, 'r', encoding='utf-8') as f:
            written_content = f.read()
            assert written_content == content
    
    def test_write_document_file_json(self, creator_tool, temp_dir):
        """Test document file writing in JSON format"""
        content = {"title": "Test", "content": "Test content"}
        output_path = str(temp_dir / "write_test.json")
        
        creator_tool._write_document_file(output_path, content, DocumentFormat.JSON)
        
        assert os.path.exists(output_path)
        with open(output_path, 'r', encoding='utf-8') as f:
            written_content = json.load(f)
            assert written_content["content"] == content
    
    def test_process_template_variables(self, creator_tool):
        """Test template variable processing"""
        template_content = "Hello {name}, welcome to {company}!"
        variables = {"name": "John", "company": "AIECS"}
        
        result = creator_tool._process_template_variables(template_content, variables)
        
        assert result == "Hello John, welcome to AIECS!"
    
    def test_generate_document_structure(self, creator_tool):
        """Test document structure generation"""
        sections = [
            {"title": "Introduction", "level": 2, "required": True},
            {"title": "Main Content", "level": 2, "required": True}
        ]
        
        structure = creator_tool._generate_document_structure(
            sections, generate_toc=True, numbering_style="numeric"
        )
        
        assert "# Table of Contents" in structure
        assert "## 1. Introduction" in structure
        assert "## 2. Main Content" in structure
    
    def test_generate_table_of_contents(self, creator_tool):
        """Test table of contents generation"""
        sections = [
            {"title": "Section A", "level": 2, "required": True},
            {"title": "Section B", "level": 2, "required": True}
        ]
        
        toc = creator_tool._generate_table_of_contents(sections, "numeric")
        
        assert "# Table of Contents" in toc
        assert "- 1. Section A" in toc
        assert "- 2. Section B" in toc
    
    def test_detect_document_format(self, creator_tool, temp_dir):
        """Test document format detection"""
        # Test different file extensions
        formats_to_test = [
            ("test.md", DocumentFormat.MARKDOWN),
            ("test.markdown", DocumentFormat.MARKDOWN),
            ("test.html", DocumentFormat.HTML),
            ("test.htm", DocumentFormat.HTML),
            ("test.txt", DocumentFormat.PLAIN_TEXT),
            ("test.json", DocumentFormat.JSON),
            ("test.xml", DocumentFormat.XML),
            ("test.tex", DocumentFormat.LATEX),
            ("test.docx", DocumentFormat.DOCX),
            ("test.pdf", DocumentFormat.PDF)
        ]
        
        for filename, expected_format in formats_to_test:
            file_path = temp_dir / filename
            with open(file_path, 'w') as f:
                f.write("Test content")
            
            detected_format = creator_tool._detect_document_format(str(file_path))
            assert detected_format == expected_format
    
    def test_generate_format_specific_metadata(self, creator_tool):
        """Test format-specific metadata generation"""
        metadata = {"title": "Test", "author": "Author"}
        
        # Test Markdown
        md_metadata = creator_tool._generate_format_specific_metadata(metadata, DocumentFormat.MARKDOWN)
        assert "---" in md_metadata
        assert "title: Test" in md_metadata
        
        # Test HTML
        html_metadata = creator_tool._generate_format_specific_metadata(metadata, DocumentFormat.HTML)
        assert "<head>" in html_metadata
        assert "<meta name=" in html_metadata
        
        # Test LaTeX
        latex_metadata = creator_tool._generate_format_specific_metadata(metadata, DocumentFormat.LATEX)
        assert "\\title{Test}" in latex_metadata
        assert "\\author{Author}" in latex_metadata
    
    def test_generate_generic_metadata(self, creator_tool):
        """Test generic metadata generation"""
        metadata = {"title": "Test", "author": "Author"}
        
        generic_metadata = creator_tool._generate_generic_metadata(metadata)
        
        assert "% title: Test" in generic_metadata
        assert "% author: Author" in generic_metadata


class TestErrorHandling:
    """Test suite for error handling"""
    
    @pytest.fixture
    def creator_tool(self):
        return DocumentCreatorTool()
    
    def test_document_creator_error(self, creator_tool):
        """Test DocumentCreatorError handling"""
        with pytest.raises(DocumentCreatorError):
            raise DocumentCreatorError("Test creator error")
    
    def test_template_error(self, creator_tool):
        """Test TemplateError handling"""
        with pytest.raises(TemplateError):
            raise TemplateError("Test template error")
    
    def test_document_creation_error(self, creator_tool):
        """Test DocumentCreationError handling"""
        with pytest.raises(DocumentCreationError):
            raise DocumentCreationError("Test creation error")
    
    def test_error_inheritance(self, creator_tool):
        """Test that specific errors inherit from base error"""
        assert issubclass(TemplateError, DocumentCreatorError)
        assert issubclass(DocumentCreationError, DocumentCreatorError)
    
    def test_error_handling_in_operations(self, creator_tool, temp_dir):
        """Test error handling in document creation operations"""
        # Test with invalid document type
        with pytest.raises(DocumentCreationError):
            creator_tool.create_document(
                document_type="invalid_type",
                template_type=TemplateType.BLANK,
                output_format=DocumentFormat.MARKDOWN,
                metadata={"title": "Test"},
                output_path=str(temp_dir / "test.md")
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])



