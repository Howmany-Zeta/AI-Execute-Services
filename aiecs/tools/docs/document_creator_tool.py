#!/usr/bin/env python3
"""
Document Creator Tool

This tool is responsible for creating new documents from templates,
initializing document structure, and managing document metadata.

Key Features:
1. Template-based document creation
2. Document structure initialization
3. Metadata management (title, author, date, etc.)
4. Style configuration and presets
5. Multi-format support (MD, HTML, DOCX, PDF, etc.)
"""

import os
import json
import uuid
import tempfile
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class DocumentType(str, Enum):
    """Supported document types"""

    REPORT = "report"
    ARTICLE = "article"
    PRESENTATION = "presentation"
    MANUAL = "manual"
    LETTER = "letter"
    PROPOSAL = "proposal"
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    CUSTOM = "custom"


class DocumentFormat(str, Enum):
    """Supported output formats"""

    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    PDF = "pdf"
    LATEX = "latex"
    PLAIN_TEXT = "txt"
    JSON = "json"
    XML = "xml"


class TemplateType(str, Enum):
    """Document template types"""

    BLANK = "blank"
    BUSINESS_REPORT = "business_report"
    TECHNICAL_DOC = "technical_doc"
    ACADEMIC_PAPER = "academic_paper"
    PROJECT_PROPOSAL = "project_proposal"
    USER_MANUAL = "user_manual"
    PRESENTATION = "presentation"
    NEWSLETTER = "newsletter"
    INVOICE = "invoice"
    CUSTOM = "custom"


class StylePreset(str, Enum):
    """Style presets for documents"""

    DEFAULT = "default"
    CORPORATE = "corporate"
    ACADEMIC = "academic"
    MODERN = "modern"
    CLASSIC = "classic"
    MINIMAL = "minimal"
    COLORFUL = "colorful"
    PROFESSIONAL = "professional"


class DocumentCreatorError(Exception):
    """Base exception for Document Creator errors"""


class TemplateError(DocumentCreatorError):
    """Raised when template operations fail"""


class DocumentCreationError(DocumentCreatorError):
    """Raised when document creation fails"""


@register_tool("document_creator")
class DocumentCreatorTool(BaseTool):
    """
    Document Creator Tool for creating new documents from templates

    This tool provides:
    1. Template management and selection
    2. Document structure initialization
    3. Metadata configuration
    4. Style and format setup
    5. Multi-format document creation

    Integrates with:
    - DocumentWriterTool for content writing
    - DocumentLayoutTool for layout configuration
    - ContentInsertionTool for complex content
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the document creator tool
        
        Automatically reads from environment variables with DOC_CREATOR_ prefix.
        Example: DOC_CREATOR_TEMPLATES_DIR -> templates_dir
        """

        model_config = SettingsConfigDict(env_prefix="DOC_CREATOR_")

        templates_dir: str = Field(
            default=os.path.join(tempfile.gettempdir(), "document_templates"),
            description="Directory for document templates",
        )
        output_dir: str = Field(
            default=os.path.join(tempfile.gettempdir(), "created_documents"),
            description="Directory for created documents",
        )
        default_format: str = Field(default="markdown", description="Default output format")
        default_style: str = Field(default="default", description="Default style preset")
        auto_backup: bool = Field(
            default=True,
            description="Whether to automatically backup created documents",
        )
        include_metadata: bool = Field(
            default=True,
            description="Whether to include metadata in created documents",
        )
        generate_toc: bool = Field(
            default=True,
            description="Whether to generate table of contents automatically",
        )

    def __init__(self, config: Optional[Dict] = None, **kwargs):
        """Initialize Document Creator Tool with settings

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/document_creator.yaml)
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

        # Initialize directories
        self._init_directories()

        # Initialize templates
        self._init_templates()

        # Initialize document tracking
        self._documents_created: List[Any] = []

    def _init_directories(self):
        """Initialize required directories"""
        os.makedirs(self.config.templates_dir, exist_ok=True)
        os.makedirs(self.config.output_dir, exist_ok=True)

    def _init_templates(self):
        """Initialize built-in templates"""
        self.templates = {
            TemplateType.BLANK: self._get_blank_template(),
            TemplateType.BUSINESS_REPORT: self._get_business_report_template(),
            TemplateType.TECHNICAL_DOC: self._get_technical_doc_template(),
            TemplateType.ACADEMIC_PAPER: self._get_academic_paper_template(),
            TemplateType.PROJECT_PROPOSAL: self._get_project_proposal_template(),
            TemplateType.USER_MANUAL: self._get_user_manual_template(),
            TemplateType.PRESENTATION: self._get_presentation_template(),
            TemplateType.NEWSLETTER: self._get_newsletter_template(),
            TemplateType.INVOICE: self._get_invoice_template(),
        }

    # Schema definitions
    class CreateDocumentSchema(BaseModel):
        """Schema for create_document operation"""

        document_type: DocumentType = Field(description="Type of document to create")
        template_type: TemplateType = Field(description="Template to use")
        output_format: DocumentFormat = Field(description="Output format")
        metadata: Dict[str, Any] = Field(description="Document metadata")
        style_preset: Optional[StylePreset] = Field(default=None, description="Style preset")
        output_path: Optional[str] = Field(default=None, description="Custom output path")

    class CreateFromTemplateSchema(BaseModel):
        """Schema for create_from_template operation"""

        template_name: str = Field(description="Name of template to use")
        template_variables: Dict[str, Any] = Field(description="Variables to fill in template")
        output_format: DocumentFormat = Field(description="Output format")
        output_path: Optional[str] = Field(default=None, description="Custom output path")

    class SetupStructureSchema(BaseModel):
        """Schema for setup_document_structure operation"""

        document_path: str = Field(description="Path to document")
        sections: List[Dict[str, Any]] = Field(description="Document sections configuration")
        generate_toc: bool = Field(default=True, description="Generate table of contents")
        numbering_style: Optional[str] = Field(default=None, description="Section numbering style")

    class ConfigureMetadataSchema(BaseModel):
        """Schema for configure_metadata operation"""

        document_path: str = Field(description="Path to document")
        metadata: Dict[str, Any] = Field(description="Metadata to configure")
        format_specific: bool = Field(default=True, description="Use format-specific metadata")

    def create_document(
        self,
        document_type: DocumentType,
        template_type: TemplateType,
        output_format: DocumentFormat,
        metadata: Dict[str, Any],
        style_preset: Optional[StylePreset] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new document from template

        Args:
            document_type: Type of document to create
            template_type: Template to use
            output_format: Output format for the document
            metadata: Document metadata (title, author, etc.)
            style_preset: Style preset to apply
            output_path: Custom output path

        Returns:
            Dict containing document creation results
        """
        try:
            start_time = datetime.now()
            document_id = str(uuid.uuid4())

            self.logger.info(f"Creating document {document_id}: {document_type} using {template_type}")

            # Step 1: Validate and prepare template
            template = self._get_template(template_type)

            # Step 2: Generate output path
            if not output_path:
                output_path = self._generate_output_path(document_type, output_format, document_id)

            # Step 3: Process metadata
            processed_metadata = self._process_metadata(metadata, output_format)

            # Step 4: Apply style preset
            preset_value = style_preset or self.config.default_style
            style_preset_enum = StylePreset(preset_value) if isinstance(preset_value, str) else preset_value
            style_config = self._get_style_config(style_preset_enum)

            # Step 5: Create document from template
            document_content = self._create_document_from_template(template, processed_metadata, style_config, output_format)

            # Step 6: Write document to file
            self._write_document_file(output_path, document_content, output_format)

            # Step 7: Track created document
            document_info = {
                "document_id": document_id,
                "document_type": document_type,
                "template_type": template_type,
                "output_format": output_format,
                "output_path": output_path,
                "metadata": processed_metadata,
                "style_preset": style_preset,
                "creation_metadata": {
                    "created_at": start_time.isoformat(),
                    "file_size": (os.path.getsize(output_path) if os.path.exists(output_path) else 0),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self._documents_created.append(document_info)

            self.logger.info(f"Document {document_id} created successfully at {output_path}")
            return document_info

        except Exception as e:
            raise DocumentCreationError(f"Failed to create document: {str(e)}")

    def create_from_template(
        self,
        template_name: str,
        template_variables: Dict[str, Any],
        output_format: DocumentFormat,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create document from custom template with variables

        Args:
            template_name: Name of template file
            template_variables: Variables to substitute in template
            output_format: Output format
            output_path: Custom output path

        Returns:
            Dict containing creation results
        """
        try:
            # Load custom template
            template_path = os.path.join(self.config.templates_dir, template_name)
            if not os.path.exists(template_path):
                raise TemplateError(f"Template not found: {template_name}")

            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # Process template variables
            processed_content = self._process_template_variables(template_content, template_variables)

            # Generate output path if not provided
            if not output_path:
                output_path = self._generate_output_path("custom", output_format, str(uuid.uuid4()))

            # Write processed content
            self._write_document_file(output_path, processed_content, output_format)

            return {
                "template_name": template_name,
                "output_path": output_path,
                "output_format": output_format,
                "variables_used": template_variables,
                "creation_time": datetime.now().isoformat(),
            }

        except Exception as e:
            raise DocumentCreationError(f"Failed to create from template: {str(e)}")

    def setup_document_structure(
        self,
        document_path: str,
        sections: List[Dict[str, Any]],
        generate_toc: bool = True,
        numbering_style: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Setup document structure with sections and headers

        Args:
            document_path: Path to document
            sections: List of section configurations
            generate_toc: Whether to generate table of contents
            numbering_style: Section numbering style

        Returns:
            Dict containing structure setup results
        """
        try:
            self.logger.info(f"Setting up structure for document: {document_path}")

            # Read existing document
            if os.path.exists(document_path):
                with open(document_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = ""

            # Generate structure
            structure_content = self._generate_document_structure(sections, generate_toc, numbering_style)

            # Combine with existing content
            final_content = self._combine_structure_with_content(structure_content, content)

            # Write back to file
            with open(document_path, "w", encoding="utf-8") as f:
                f.write(final_content)

            return {
                "document_path": document_path,
                "sections_created": len(sections),
                "toc_generated": generate_toc,
                "numbering_style": numbering_style,
                "structure_setup_time": datetime.now().isoformat(),
            }

        except Exception as e:
            raise DocumentCreationError(f"Failed to setup document structure: {str(e)}")

    def configure_metadata(
        self,
        document_path: str,
        metadata: Dict[str, Any],
        format_specific: bool = True,
    ) -> Dict[str, Any]:
        """
        Configure document metadata

        Args:
            document_path: Path to document
            metadata: Metadata to configure
            format_specific: Use format-specific metadata syntax

        Returns:
            Dict containing metadata configuration results
        """
        try:
            # Detect document format
            file_format = self._detect_document_format(document_path)

            # Generate metadata content
            if format_specific:
                metadata_content = self._generate_format_specific_metadata(metadata, file_format)
            else:
                metadata_content = self._generate_generic_metadata(metadata)

            # Insert metadata into document
            self._insert_metadata_into_document(document_path, metadata_content, file_format)

            return {
                "document_path": document_path,
                "metadata_configured": metadata,
                "format": file_format,
                "format_specific": format_specific,
                "configuration_time": datetime.now().isoformat(),
            }

        except Exception as e:
            raise DocumentCreationError(f"Failed to configure metadata: {str(e)}")

    def list_templates(self) -> Dict[str, Any]:
        """
        List available document templates

        Returns:
            Dict containing available templates
        """
        built_in_templates = list(self.templates.keys())

        # Scan for custom templates
        custom_templates = []
        if os.path.exists(self.config.templates_dir):
            for file in os.listdir(self.config.templates_dir):
                if file.endswith((".md", ".html", ".txt", ".json")):
                    custom_templates.append(file)

        return {
            "built_in_templates": [t.value for t in built_in_templates],
            "custom_templates": custom_templates,
            "templates_directory": self.config.templates_dir,
            "total_templates": len(built_in_templates) + len(custom_templates),
        }

    def get_template_info(self, template_type: TemplateType) -> Dict[str, Any]:
        """
        Get information about a specific template

        Args:
            template_type: Type of template

        Returns:
            Dict containing template information
        """
        if template_type not in self.templates:
            raise TemplateError(f"Template not found: {template_type}")

        template = self.templates[template_type]

        return {
            "template_type": template_type.value,
            "name": template.get("name", ""),
            "description": template.get("description", ""),
            "sections": template.get("sections", []),
            "variables": template.get("variables", []),
            "supported_formats": template.get("supported_formats", []),
            "style_presets": template.get("style_presets", []),
        }

    def get_created_documents(self) -> List[Dict[str, Any]]:
        """
        Get list of documents created in this session

        Returns:
            List of created document information
        """
        return self._documents_created.copy()

    # Template definitions
    def _get_blank_template(self) -> Dict[str, Any]:
        """Get blank document template"""
        return {
            "name": "Blank Document",
            "description": "Empty document with basic structure",
            "content": "",
            "sections": [],
            "variables": [],
            "supported_formats": ["markdown", "html", "txt", "docx"],
            "metadata_template": {
                "title": "New Document",
                "author": "Author",
                "date": datetime.now().strftime("%Y-%m-%d"),
            },
        }

    def _get_business_report_template(self) -> Dict[str, Any]:
        """Get business report template"""
        return {
            "name": "Business Report",
            "description": "Professional business report template",
            "content": """# {title}

**Date:** {date}
**Author:** {author}
**Department:** {department}

## Executive Summary

{executive_summary}

## Introduction

{introduction}

## Analysis

### Key Findings

{key_findings}

### Data Analysis

{data_analysis}

## Recommendations

{recommendations}

## Conclusion

{conclusion}

## Appendices

{appendices}
""",
            "sections": [
                {"name": "Executive Summary", "level": 2, "required": True},
                {"name": "Introduction", "level": 2, "required": True},
                {"name": "Analysis", "level": 2, "required": True},
                {"name": "Recommendations", "level": 2, "required": True},
                {"name": "Conclusion", "level": 2, "required": True},
            ],
            "variables": [
                "title",
                "date",
                "author",
                "department",
                "executive_summary",
                "introduction",
                "key_findings",
                "data_analysis",
                "recommendations",
                "conclusion",
                "appendices",
            ],
            "supported_formats": ["markdown", "html", "docx", "pdf"],
            "style_presets": ["corporate", "professional", "modern"],
        }

    def _get_technical_doc_template(self) -> Dict[str, Any]:
        """Get technical documentation template"""
        return {
            "name": "Technical Documentation",
            "description": "Technical documentation with code examples",
            "content": """# {title}

**Version:** {version}
**Last Updated:** {date}
**Author:** {author}

## Overview

{overview}

## Prerequisites

{prerequisites}

## Installation

{installation}

## Configuration

{configuration}

## Usage

{usage}

## API Reference

{api_reference}

## Examples

{examples}

## Troubleshooting

{troubleshooting}

## Changelog

{changelog}
""",
            "sections": [
                {"name": "Overview", "level": 2, "required": True},
                {"name": "Prerequisites", "level": 2, "required": False},
                {"name": "Installation", "level": 2, "required": True},
                {"name": "Configuration", "level": 2, "required": False},
                {"name": "Usage", "level": 2, "required": True},
                {"name": "API Reference", "level": 2, "required": False},
                {"name": "Examples", "level": 2, "required": True},
                {"name": "Troubleshooting", "level": 2, "required": False},
            ],
            "variables": [
                "title",
                "version",
                "date",
                "author",
                "overview",
                "prerequisites",
                "installation",
                "configuration",
                "usage",
                "api_reference",
                "examples",
                "troubleshooting",
                "changelog",
            ],
            "supported_formats": ["markdown", "html", "pdf"],
            "style_presets": ["technical", "modern", "minimal"],
        }

    def _get_academic_paper_template(self) -> Dict[str, Any]:
        """Get academic paper template"""
        return {
            "name": "Academic Paper",
            "description": "Academic research paper template",
            "content": """# {title}

**Author:** {author}
**Institution:** {institution}
**Email:** {email}
**Date:** {date}

## Abstract

{abstract}

**Keywords:** {keywords}

## 1. Introduction

{introduction}

## 2. Literature Review

{literature_review}

## 3. Methodology

{methodology}

## 4. Results

{results}

## 5. Discussion

{discussion}

## 6. Conclusion

{conclusion}

## References

{references}

## Appendices

{appendices}
""",
            "sections": [
                {"name": "Abstract", "level": 2, "required": True},
                {"name": "Introduction", "level": 2, "required": True},
                {"name": "Literature Review", "level": 2, "required": True},
                {"name": "Methodology", "level": 2, "required": True},
                {"name": "Results", "level": 2, "required": True},
                {"name": "Discussion", "level": 2, "required": True},
                {"name": "Conclusion", "level": 2, "required": True},
                {"name": "References", "level": 2, "required": True},
            ],
            "variables": [
                "title",
                "author",
                "institution",
                "email",
                "date",
                "abstract",
                "keywords",
                "introduction",
                "literature_review",
                "methodology",
                "results",
                "discussion",
                "conclusion",
                "references",
                "appendices",
            ],
            "supported_formats": ["markdown", "latex", "pdf"],
            "style_presets": ["academic", "classic", "formal"],
        }

    def _get_project_proposal_template(self) -> Dict[str, Any]:
        """Get project proposal template"""
        return {
            "name": "Project Proposal",
            "description": "Project proposal and planning template",
            "content": """# {project_name}

**Proposal Date:** {date}
**Project Manager:** {project_manager}
**Department:** {department}
**Budget:** {budget}

## Project Overview

{project_overview}

## Objectives

{objectives}

## Scope

### In Scope
{in_scope}

### Out of Scope
{out_scope}

## Timeline

{timeline}

## Resources Required

{resources}

## Budget Breakdown

{budget_breakdown}

## Risk Assessment

{risk_assessment}

## Success Criteria

{success_criteria}

## Next Steps

{next_steps}
""",
            "variables": [
                "project_name",
                "date",
                "project_manager",
                "department",
                "budget",
                "project_overview",
                "objectives",
                "in_scope",
                "out_scope",
                "timeline",
                "resources",
                "budget_breakdown",
                "risk_assessment",
                "success_criteria",
                "next_steps",
            ],
            "supported_formats": ["markdown", "html", "docx", "pdf"],
            "style_presets": ["professional", "corporate", "modern"],
        }

    def _get_user_manual_template(self) -> Dict[str, Any]:
        """Get user manual template"""
        return {
            "name": "User Manual",
            "description": "User manual and guide template",
            "content": """# {product_name} User Manual

**Version:** {version}
**Date:** {date}
**Support:** {support_contact}

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Features](#basic-features)
3. [Advanced Features](#advanced-features)
4. [Troubleshooting](#troubleshooting)
5. [FAQ](#faq)

## Getting Started

{getting_started}

## Basic Features

{basic_features}

## Advanced Features

{advanced_features}

## Troubleshooting

{troubleshooting}

## FAQ

{faq}

## Contact Support

{support_info}
""",
            "variables": [
                "product_name",
                "version",
                "date",
                "support_contact",
                "getting_started",
                "basic_features",
                "advanced_features",
                "troubleshooting",
                "faq",
                "support_info",
            ],
            "supported_formats": ["markdown", "html", "pdf"],
            "style_presets": ["user-friendly", "modern", "minimal"],
        }

    def _get_presentation_template(self) -> Dict[str, Any]:
        """Get presentation template"""
        return {
            "name": "Presentation",
            "description": "Slide presentation template",
            "content": """# {title}

---

## Slide 1: Title Slide

### {title}
**Presenter:** {presenter}
**Date:** {date}
**Organization:** {organization}

---

## Slide 2: Agenda

{agenda}

---

## Slide 3: Introduction

{introduction}

---

## Slide 4: Main Content

{main_content}

---

## Slide 5: Conclusion

{conclusion}

---

## Slide 6: Questions

{questions}

---

## Slide 7: Thank You

**Contact Information:**
{contact_info}
""",
            "variables": [
                "title",
                "presenter",
                "date",
                "organization",
                "agenda",
                "introduction",
                "main_content",
                "conclusion",
                "questions",
                "contact_info",
            ],
            "supported_formats": ["markdown", "html"],
            "style_presets": ["presentation", "modern", "colorful"],
        }

    def _get_newsletter_template(self) -> Dict[str, Any]:
        """Get newsletter template"""
        return {
            "name": "Newsletter",
            "description": "Newsletter and bulletin template",
            "content": """# {newsletter_name}

**Issue #{issue_number}** | {date}

## Headlines

{headlines}

## Feature Article

{feature_article}

## News Briefs

{news_briefs}

## Upcoming Events

{upcoming_events}

## Community Spotlight

{community_spotlight}

## Contact Us

{contact_info}
""",
            "variables": [
                "newsletter_name",
                "issue_number",
                "date",
                "headlines",
                "feature_article",
                "news_briefs",
                "upcoming_events",
                "community_spotlight",
                "contact_info",
            ],
            "supported_formats": ["markdown", "html"],
            "style_presets": ["newsletter", "colorful", "modern"],
        }

    def _get_invoice_template(self) -> Dict[str, Any]:
        """Get invoice template"""
        return {
            "name": "Invoice",
            "description": "Business invoice template",
            "content": """# INVOICE

**Invoice #:** {invoice_number}
**Date:** {date}
**Due Date:** {due_date}

## Bill To:
{client_info}

## Bill From:
{company_info}

## Items

{items_table}

## Summary

**Subtotal:** {subtotal}
**Tax:** {tax}
**Total:** {total}

## Payment Terms

{payment_terms}

## Notes

{notes}
""",
            "variables": [
                "invoice_number",
                "date",
                "due_date",
                "client_info",
                "company_info",
                "items_table",
                "subtotal",
                "tax",
                "total",
                "payment_terms",
                "notes",
            ],
            "supported_formats": ["markdown", "html", "pdf"],
            "style_presets": ["professional", "corporate", "minimal"],
        }

    # Helper methods
    def _get_template(self, template_type: TemplateType) -> Dict[str, Any]:
        """Get template by type"""
        if template_type not in self.templates:
            raise TemplateError(f"Template not found: {template_type}")
        return self.templates[template_type]

    def _generate_output_path(
        self,
        document_type: str,
        output_format: DocumentFormat,
        document_id: str,
    ) -> str:
        """Generate output path for document"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{document_type}_{timestamp}_{document_id[:8]}.{output_format.value}"
        return os.path.join(self.config.output_dir, filename)

    def _process_metadata(self, metadata: Dict[str, Any], output_format: DocumentFormat) -> Dict[str, Any]:
        """Process and validate metadata"""
        processed = metadata.copy()

        # Add default metadata if missing
        if "date" not in processed:
            processed["date"] = datetime.now().strftime("%Y-%m-%d")
        if "created_by" not in processed:
            processed["created_by"] = "AIECS Document Creator"
        if "format" not in processed:
            processed["format"] = output_format.value

        return processed

    def _get_style_config(self, style_preset: StylePreset) -> Dict[str, Any]:
        """Get style configuration for preset"""
        style_configs = {
            StylePreset.DEFAULT: {
                "font_family": "Arial",
                "font_size": 12,
                "colors": {"primary": "#000000"},
            },
            StylePreset.CORPORATE: {
                "font_family": "Calibri",
                "font_size": 11,
                "colors": {"primary": "#2E5D92"},
            },
            StylePreset.ACADEMIC: {
                "font_family": "Times New Roman",
                "font_size": 12,
                "colors": {"primary": "#000000"},
            },
            StylePreset.MODERN: {
                "font_family": "Helvetica",
                "font_size": 11,
                "colors": {"primary": "#333333"},
            },
            StylePreset.CLASSIC: {
                "font_family": "Georgia",
                "font_size": 12,
                "colors": {"primary": "#1a1a1a"},
            },
            StylePreset.MINIMAL: {
                "font_family": "Arial",
                "font_size": 10,
                "colors": {"primary": "#444444"},
            },
            StylePreset.COLORFUL: {
                "font_family": "Verdana",
                "font_size": 11,
                "colors": {"primary": "#2E8B57"},
            },
            StylePreset.PROFESSIONAL: {
                "font_family": "Segoe UI",
                "font_size": 11,
                "colors": {"primary": "#2F4F4F"},
            },
        }
        return style_configs.get(style_preset, style_configs[StylePreset.DEFAULT])

    def _create_document_from_template(
        self,
        template: Dict[str, Any],
        metadata: Dict[str, Any],
        style_config: Dict[str, Any],
        output_format: DocumentFormat,
    ) -> str:
        """Create document content from template"""
        content = template.get("content", "")

        # Apply metadata to template
        if content and template.get("variables"):
            # Replace template variables with metadata values
            for var in template["variables"]:
                placeholder = f"{{{var}}}"
                value = metadata.get(var, f"[{var}]")
                content = content.replace(placeholder, str(value))

        # Add metadata header if required
        if self.config.include_metadata:
            metadata_header = self._generate_metadata_header(metadata, output_format)
            content = metadata_header + "\n\n" + content

        return content

    def _generate_metadata_header(self, metadata: Dict[str, Any], output_format: DocumentFormat) -> str:
        """Generate metadata header for document"""
        if output_format == DocumentFormat.MARKDOWN:
            return "---\n" + "\n".join([f"{k}: {v}" for k, v in metadata.items()]) + "\n---"
        elif output_format == DocumentFormat.HTML:
            meta_tags = "\n".join([f'<meta name="{k}" content="{v}">' for k, v in metadata.items()])
            return f"<!-- Document Metadata -->\n{meta_tags}\n<!-- End Metadata -->"
        else:
            return "# Document Metadata\n" + "\n".join([f"{k}: {v}" for k, v in metadata.items()])

    def _write_document_file(self, output_path: str, content: str, output_format: DocumentFormat):
        """Write document content to file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if output_format in [
            DocumentFormat.MARKDOWN,
            DocumentFormat.HTML,
            DocumentFormat.PLAIN_TEXT,
            DocumentFormat.LATEX,
        ]:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        elif output_format == DocumentFormat.JSON:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"content": content}, f, indent=2, ensure_ascii=False)
        else:
            # For other formats, write as text for now
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

    def _process_template_variables(self, template_content: str, variables: Dict[str, Any]) -> str:
        """Process template variables in content"""
        result = template_content
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        return result

    def _generate_document_structure(
        self,
        sections: List[Dict[str, Any]],
        generate_toc: bool,
        numbering_style: Optional[str],
    ) -> str:
        """Generate document structure from sections"""
        structure_parts = []

        # Generate table of contents
        if generate_toc:
            toc = self._generate_table_of_contents(sections, numbering_style)
            structure_parts.append(toc)

        # Generate section headers
        for i, section in enumerate(sections, 1):
            level = section.get("level", 2)
            title = section.get("title", f"Section {i}")

            if numbering_style == "numeric":
                header = f"{'#' * level} {i}. {title}"
            elif numbering_style == "alpha":
                alpha = chr(ord("A") + i - 1) if i <= 26 else f"Section{i}"
                header = f"{'#' * level} {alpha}. {title}"
            else:
                header = f"{'#' * level} {title}"

            structure_parts.append(header)
            structure_parts.append("")  # Empty line

            # Add placeholder content
            placeholder = section.get("placeholder", f"Content for {title} goes here...")
            structure_parts.append(placeholder)
            structure_parts.append("")  # Empty line

        return "\n".join(structure_parts)

    def _generate_table_of_contents(self, sections: List[Dict[str, Any]], numbering_style: Optional[str]) -> str:
        """Generate table of contents"""
        toc_parts = ["# Table of Contents", ""]

        for i, section in enumerate(sections, 1):
            title = section.get("title", f"Section {i}")
            level = section.get("level", 2)
            indent = "  " * (level - 1)

            if numbering_style == "numeric":
                toc_line = f"{indent}- {i}. {title}"
            elif numbering_style == "alpha":
                alpha = chr(ord("A") + i - 1) if i <= 26 else f"Section{i}"
                toc_line = f"{indent}- {alpha}. {title}"
            else:
                toc_line = f"{indent}- {title}"

            toc_parts.append(toc_line)

        toc_parts.extend(["", "---", ""])
        return "\n".join(toc_parts)

    def _combine_structure_with_content(self, structure: str, existing_content: str) -> str:
        """Combine generated structure with existing content"""
        if not existing_content.strip():
            return structure

        # If existing content has structure markers, replace them
        if "# Table of Contents" in existing_content:
            # Replace existing structure
            lines = existing_content.split("\n")
            content_start = -1
            for i, line in enumerate(lines):
                if line.startswith("---") and i > 0:
                    content_start = i + 1
                    break

            if content_start > 0:
                existing_body = "\n".join(lines[content_start:])
                return structure + "\n" + existing_body

        return structure + "\n\n" + existing_content

    def _detect_document_format(self, document_path: str) -> DocumentFormat:
        """Detect document format from file extension"""
        ext = os.path.splitext(document_path)[1].lower()
        format_map = {
            ".md": DocumentFormat.MARKDOWN,
            ".markdown": DocumentFormat.MARKDOWN,
            ".html": DocumentFormat.HTML,
            ".htm": DocumentFormat.HTML,
            ".txt": DocumentFormat.PLAIN_TEXT,
            ".json": DocumentFormat.JSON,
            ".xml": DocumentFormat.XML,
            ".tex": DocumentFormat.LATEX,
            ".docx": DocumentFormat.DOCX,
            ".pdf": DocumentFormat.PDF,
        }
        return format_map.get(ext, DocumentFormat.PLAIN_TEXT)

    def _generate_format_specific_metadata(self, metadata: Dict[str, Any], file_format: DocumentFormat) -> str:
        """Generate format-specific metadata"""
        if file_format == DocumentFormat.MARKDOWN:
            return "---\n" + "\n".join([f"{k}: {v}" for k, v in metadata.items()]) + "\n---"
        elif file_format == DocumentFormat.HTML:
            meta_tags = "\n".join([f'<meta name="{k}" content="{v}">' for k, v in metadata.items()])
            return f"<head>\n{meta_tags}\n</head>"
        elif file_format == DocumentFormat.LATEX:
            return "\n".join([f"\\{k}{{{v}}}" for k, v in metadata.items()])
        else:
            return self._generate_generic_metadata(metadata)

    def _generate_generic_metadata(self, metadata: Dict[str, Any]) -> str:
        """Generate generic metadata"""
        return "% " + "\n% ".join([f"{k}: {v}" for k, v in metadata.items()])

    def _insert_metadata_into_document(
        self,
        document_path: str,
        metadata_content: str,
        file_format: DocumentFormat,
    ):
        """Insert metadata into document"""
        with open(document_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Insert metadata at the beginning
        if file_format == DocumentFormat.HTML and "<head>" in content:
            # Insert into existing head section
            content = content.replace("<head>", f"<head>\n{metadata_content}")
        else:
            # Insert at the beginning
            content = metadata_content + "\n\n" + content

        with open(document_path, "w", encoding="utf-8") as f:
            f.write(content)
