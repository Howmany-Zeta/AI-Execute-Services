#!/usr/bin/env python3
"""
Document Layout Tool

This tool is responsible for document layout, page formatting, and
visual presentation of documents across different formats.

Key Features:
1. Page layout management (margins, orientation, size)
2. Multi-column layouts and text flow
3. Headers, footers, and page numbering
4. Section breaks and page breaks
5. Typography and spacing control
6. Format-specific layout optimization
"""

import os
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


class PageSize(str, Enum):
    """Standard page sizes"""

    A4 = "a4"
    A3 = "a3"
    A5 = "a5"
    LETTER = "letter"
    LEGAL = "legal"
    TABLOID = "tabloid"
    CUSTOM = "custom"


class PageOrientation(str, Enum):
    """Page orientations"""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class LayoutType(str, Enum):
    """Document layout types"""

    SINGLE_COLUMN = "single_column"
    TWO_COLUMN = "two_column"
    THREE_COLUMN = "three_column"
    MULTI_COLUMN = "multi_column"
    MAGAZINE = "magazine"
    NEWSPAPER = "newspaper"
    ACADEMIC = "academic"
    CUSTOM = "custom"


class AlignmentType(str, Enum):
    """Text alignment types"""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class BreakType(str, Enum):
    """Break types"""

    PAGE_BREAK = "page_break"
    SECTION_BREAK = "section_break"
    COLUMN_BREAK = "column_break"
    LINE_BREAK = "line_break"


class HeaderFooterPosition(str, Enum):
    """Header/footer positions"""

    HEADER_LEFT = "header_left"
    HEADER_CENTER = "header_center"
    HEADER_RIGHT = "header_right"
    FOOTER_LEFT = "footer_left"
    FOOTER_CENTER = "footer_center"
    FOOTER_RIGHT = "footer_right"


class DocumentLayoutError(Exception):
    """Base exception for Document Layout errors"""


class LayoutConfigurationError(DocumentLayoutError):
    """Raised when layout configuration fails"""


class PageSetupError(DocumentLayoutError):
    """Raised when page setup fails"""


@register_tool("document_layout")
class DocumentLayoutTool(BaseTool):
    """
    Document Layout Tool for managing document presentation and formatting

    This tool provides:
    1. Page setup and formatting
    2. Multi-column layouts
    3. Headers, footers, and page numbering
    4. Typography and spacing control
    5. Break management (page, section, column)
    6. Format-specific layout optimization

    Integrates with:
    - DocumentCreatorTool for initial document setup
    - DocumentWriterTool for content placement
    - ContentInsertionTool for complex content positioning
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the document layout tool
        
        Automatically reads from environment variables with DOC_LAYOUT_ prefix.
        Example: DOC_LAYOUT_TEMP_DIR -> temp_dir
        """

        model_config = SettingsConfigDict(env_prefix="DOC_LAYOUT_")

        temp_dir: str = Field(
            default=os.path.join(tempfile.gettempdir(), "document_layouts"),
            description="Temporary directory for layout processing",
        )
        default_page_size: str = Field(default="a4", description="Default page size")
        default_orientation: str = Field(default="portrait", description="Default page orientation")
        default_margins: Dict[str, float] = Field(
            default={"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
            description="Default page margins in centimeters (top, bottom, left, right)",
        )
        auto_adjust_layout: bool = Field(
            default=True,
            description="Whether to automatically adjust layout for optimal presentation",
        )
        preserve_formatting: bool = Field(
            default=True,
            description="Whether to preserve existing formatting when applying layouts",
        )

    def __init__(self, config: Optional[Dict] = None, **kwargs):
        """Initialize Document Layout Tool with settings

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/document_layout.yaml)
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

        # Initialize layout presets
        self._init_layout_presets()

        # Track layout operations
        self._layout_operations: List[Any] = []

    def _init_directories(self):
        """Initialize required directories"""
        os.makedirs(self.config.temp_dir, exist_ok=True)

    def _init_layout_presets(self):
        """Initialize built-in layout presets"""
        self.layout_presets = {
            "default": self._get_default_layout(),
            "academic_paper": self._get_academic_paper_layout(),
            "business_report": self._get_business_report_layout(),
            "magazine": self._get_magazine_layout(),
            "newspaper": self._get_newspaper_layout(),
            "presentation": self._get_presentation_layout(),
            "technical_doc": self._get_technical_doc_layout(),
            "letter": self._get_letter_layout(),
            "invoice": self._get_invoice_layout(),
            "brochure": self._get_brochure_layout(),
        }

    # Schema definitions
    class SetPageLayoutSchema(BaseModel):
        """Schema for set_page_layout operation"""

        document_path: str = Field(description="Path to document")
        page_size: PageSize = Field(description="Page size")
        orientation: PageOrientation = Field(description="Page orientation")
        margins: Dict[str, float] = Field(description="Page margins (top, bottom, left, right)")
        layout_preset: Optional[str] = Field(default=None, description="Layout preset name")

    class CreateMultiColumnSchema(BaseModel):
        """Schema for create_multi_column_layout operation"""

        document_path: str = Field(description="Path to document")
        num_columns: int = Field(description="Number of columns")
        column_gap: float = Field(default=1.0, description="Gap between columns (cm)")
        column_widths: Optional[List[float]] = Field(default=None, description="Custom column widths")
        balance_columns: bool = Field(default=True, description="Balance column heights")

    class SetupHeadersFootersSchema(BaseModel):
        """Schema for setup_headers_footers operation"""

        document_path: str = Field(description="Path to document")
        header_config: Optional[Dict[str, Any]] = Field(default=None, description="Header configuration")
        footer_config: Optional[Dict[str, Any]] = Field(default=None, description="Footer configuration")
        page_numbering: bool = Field(default=True, description="Include page numbering")
        numbering_style: str = Field(default="numeric", description="Page numbering style")

    class InsertBreakSchema(BaseModel):
        """Schema for insert_break operation"""

        document_path: str = Field(description="Path to document")
        break_type: BreakType = Field(description="Type of break to insert")
        position: Optional[Dict[str, Any]] = Field(default=None, description="Position to insert break")
        break_options: Optional[Dict[str, Any]] = Field(default=None, description="Break-specific options")

    class ConfigureTypographySchema(BaseModel):
        """Schema for configure_typography operation"""

        document_path: str = Field(description="Path to document")
        font_config: Dict[str, Any] = Field(description="Font configuration")
        spacing_config: Optional[Dict[str, Any]] = Field(default=None, description="Spacing configuration")
        alignment: Optional[AlignmentType] = Field(default=None, description="Text alignment")

    def set_page_layout(
        self,
        document_path: str,
        page_size: PageSize,
        orientation: PageOrientation,
        margins: Dict[str, float],
        layout_preset: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Set page layout configuration for document

        Args:
            document_path: Path to document
            page_size: Page size (A4, Letter, etc.)
            orientation: Page orientation (portrait/landscape)
            margins: Page margins in cm (top, bottom, left, right)
            layout_preset: Optional layout preset to apply

        Returns:
            Dict containing layout configuration results
        """
        try:
            start_time = datetime.now()
            operation_id = str(uuid.uuid4())

            self.logger.info(f"Setting page layout {operation_id} for: {document_path}")

            # Validate margins
            required_margins = ["top", "bottom", "left", "right"]
            for margin in required_margins:
                if margin not in margins:
                    raise LayoutConfigurationError(f"Missing margin: {margin}")

            # Apply layout preset if specified
            if layout_preset:
                preset_config = self._get_layout_preset(layout_preset)
                if preset_config:
                    page_size = preset_config.get("page_size", page_size)
                    orientation = preset_config.get("orientation", orientation)
                    margins.update(preset_config.get("margins", {}))

            # Create layout configuration
            layout_config = {
                "page_size": page_size,
                "orientation": orientation,
                "margins": margins,
                "layout_preset": layout_preset,
                "dimensions": self._calculate_page_dimensions(page_size, orientation, margins),
            }

            # Apply layout to document
            self._apply_page_layout_to_document(document_path, layout_config)

            # Track operation
            operation_info = {
                "operation_id": operation_id,
                "operation_type": "set_page_layout",
                "document_path": document_path,
                "layout_config": layout_config,
                "timestamp": start_time.isoformat(),
                "duration": (datetime.now() - start_time).total_seconds(),
            }

            self._layout_operations.append(operation_info)

            self.logger.info(f"Page layout {operation_id} applied successfully")
            return operation_info

        except Exception as e:
            raise PageSetupError(f"Failed to set page layout: {str(e)}")

    def create_multi_column_layout(
        self,
        document_path: str,
        num_columns: int,
        column_gap: float = 1.0,
        column_widths: Optional[List[float]] = None,
        balance_columns: bool = True,
    ) -> Dict[str, Any]:
        """
        Create multi-column layout for document

        Args:
            document_path: Path to document
            num_columns: Number of columns
            column_gap: Gap between columns in cm
            column_widths: Custom column widths (if None, equal widths)
            balance_columns: Whether to balance column heights

        Returns:
            Dict containing multi-column layout results
        """
        try:
            start_time = datetime.now()
            operation_id = str(uuid.uuid4())

            self.logger.info(f"Creating {num_columns}-column layout {operation_id} for: {document_path}")

            # Validate parameters
            if num_columns < 1:
                raise LayoutConfigurationError("Number of columns must be at least 1")
            if column_widths and len(column_widths) != num_columns:
                raise LayoutConfigurationError("Column widths count must match number of columns")

            # Calculate column configuration
            column_config = self._calculate_column_configuration(num_columns, column_gap, column_widths, balance_columns)

            # Apply multi-column layout
            self._apply_multi_column_layout(document_path, column_config)

            operation_info = {
                "operation_id": operation_id,
                "operation_type": "create_multi_column_layout",
                "document_path": document_path,
                "column_config": column_config,
                "timestamp": start_time.isoformat(),
                "duration": (datetime.now() - start_time).total_seconds(),
            }

            self._layout_operations.append(operation_info)

            self.logger.info(f"Multi-column layout {operation_id} created successfully")
            return operation_info

        except Exception as e:
            raise LayoutConfigurationError(f"Failed to create multi-column layout: {str(e)}")

    def setup_headers_footers(
        self,
        document_path: str,
        header_config: Optional[Dict[str, Any]] = None,
        footer_config: Optional[Dict[str, Any]] = None,
        page_numbering: bool = True,
        numbering_style: str = "numeric",
    ) -> Dict[str, Any]:
        """
        Setup headers and footers for document

        Args:
            document_path: Path to document
            header_config: Header configuration
            footer_config: Footer configuration
            page_numbering: Include page numbering
            numbering_style: Page numbering style (numeric, roman, alpha)

        Returns:
            Dict containing header/footer setup results
        """
        try:
            start_time = datetime.now()
            operation_id = str(uuid.uuid4())

            self.logger.info(f"Setting up headers/footers {operation_id} for: {document_path}")

            # Process header configuration
            processed_header = self._process_header_footer_config(header_config, "header", page_numbering, numbering_style)

            # Process footer configuration
            processed_footer = self._process_header_footer_config(footer_config, "footer", page_numbering, numbering_style)

            # Apply headers and footers
            self._apply_headers_footers(document_path, processed_header, processed_footer)

            operation_info = {
                "operation_id": operation_id,
                "operation_type": "setup_headers_footers",
                "document_path": document_path,
                "header_config": processed_header,
                "footer_config": processed_footer,
                "page_numbering": page_numbering,
                "numbering_style": numbering_style,
                "timestamp": start_time.isoformat(),
                "duration": (datetime.now() - start_time).total_seconds(),
            }

            self._layout_operations.append(operation_info)

            self.logger.info(f"Headers/footers {operation_id} setup successfully")
            return operation_info

        except Exception as e:
            raise LayoutConfigurationError(f"Failed to setup headers/footers: {str(e)}")

    def insert_break(
        self,
        document_path: str,
        break_type: BreakType,
        position: Optional[Dict[str, Any]] = None,
        break_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Insert page, section, or column break

        Args:
            document_path: Path to document
            break_type: Type of break to insert
            position: Position to insert break (line, offset, etc.)
            break_options: Break-specific options

        Returns:
            Dict containing break insertion results
        """
        try:
            start_time = datetime.now()
            operation_id = str(uuid.uuid4())

            self.logger.info(f"Inserting {break_type} break {operation_id} in: {document_path}")

            # Determine break markup based on type and format
            break_markup = self._generate_break_markup(break_type, break_options)

            # Insert break at specified position
            self._insert_break_at_position(document_path, break_markup, position)

            operation_info = {
                "operation_id": operation_id,
                "operation_type": "insert_break",
                "document_path": document_path,
                "break_type": break_type,
                "position": position,
                "break_options": break_options,
                "break_markup": break_markup,
                "timestamp": start_time.isoformat(),
                "duration": (datetime.now() - start_time).total_seconds(),
            }

            self._layout_operations.append(operation_info)

            self.logger.info(f"Break {operation_id} inserted successfully")
            return operation_info

        except Exception as e:
            raise LayoutConfigurationError(f"Failed to insert break: {str(e)}")

    def configure_typography(
        self,
        document_path: str,
        font_config: Dict[str, Any],
        spacing_config: Optional[Dict[str, Any]] = None,
        alignment: Optional[AlignmentType] = None,
    ) -> Dict[str, Any]:
        """
        Configure typography and text formatting

        Args:
            document_path: Path to document
            font_config: Font configuration (family, size, weight, etc.)
            spacing_config: Spacing configuration (line height, paragraph spacing)
            alignment: Text alignment

        Returns:
            Dict containing typography configuration results
        """
        try:
            start_time = datetime.now()
            operation_id = str(uuid.uuid4())

            self.logger.info(f"Configuring typography {operation_id} for: {document_path}")

            # Process typography configuration
            typography_config = self._process_typography_config(font_config, spacing_config, alignment)

            # Apply typography settings
            self._apply_typography_settings(document_path, typography_config)

            operation_info = {
                "operation_id": operation_id,
                "operation_type": "configure_typography",
                "document_path": document_path,
                "typography_config": typography_config,
                "timestamp": start_time.isoformat(),
                "duration": (datetime.now() - start_time).total_seconds(),
            }

            self._layout_operations.append(operation_info)

            self.logger.info(f"Typography {operation_id} configured successfully")
            return operation_info

        except Exception as e:
            raise LayoutConfigurationError(f"Failed to configure typography: {str(e)}")

    def optimize_layout_for_content(
        self,
        document_path: str,
        content_analysis: Dict[str, Any],
        optimization_goals: List[str],
    ) -> Dict[str, Any]:
        """
        Optimize document layout based on content analysis

        Args:
            document_path: Path to document
            content_analysis: Analysis of document content
            optimization_goals: List of optimization goals

        Returns:
            Dict containing layout optimization results
        """
        try:
            start_time = datetime.now()
            operation_id = str(uuid.uuid4())

            self.logger.info(f"Optimizing layout {operation_id} for: {document_path}")

            # Analyze current layout
            current_layout = self._analyze_current_layout(document_path)

            # Generate optimization recommendations
            optimization_plan = self._generate_optimization_plan(current_layout, content_analysis, optimization_goals)

            # Apply optimizations
            optimization_results = self._apply_layout_optimizations(document_path, optimization_plan)

            operation_info = {
                "operation_id": operation_id,
                "operation_type": "optimize_layout_for_content",
                "document_path": document_path,
                "content_analysis": content_analysis,
                "optimization_goals": optimization_goals,
                "optimization_plan": optimization_plan,
                "optimization_results": optimization_results,
                "timestamp": start_time.isoformat(),
                "duration": (datetime.now() - start_time).total_seconds(),
            }

            self._layout_operations.append(operation_info)

            self.logger.info(f"Layout optimization {operation_id} completed successfully")
            return operation_info

        except Exception as e:
            raise LayoutConfigurationError(f"Failed to optimize layout: {str(e)}")

    def get_layout_presets(self) -> Dict[str, Any]:
        """
        Get available layout presets

        Returns:
            Dict containing available layout presets
        """
        return {
            "presets": list(self.layout_presets.keys()),
            "preset_details": {name: preset.get("description", "") for name, preset in self.layout_presets.items()},
        }

    def get_layout_operations(self) -> List[Dict[str, Any]]:
        """
        Get list of layout operations performed

        Returns:
            List of layout operation information
        """
        return self._layout_operations.copy()

    # Layout preset definitions
    def _get_default_layout(self) -> Dict[str, Any]:
        """Get default layout configuration"""
        return {
            "description": "Standard single-column layout",
            "page_size": PageSize.A4,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
            "columns": 1,
            "font": {"family": "Arial", "size": 12},
            "spacing": {"line_height": 1.5, "paragraph_spacing": 6},
        }

    def _get_academic_paper_layout(self) -> Dict[str, Any]:
        """Get academic paper layout configuration"""
        return {
            "description": "Academic paper with double spacing",
            "page_size": PageSize.A4,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 2.5, "bottom": 2.5, "left": 3.0, "right": 2.5},
            "columns": 1,
            "font": {"family": "Times New Roman", "size": 12},
            "spacing": {"line_height": 2.0, "paragraph_spacing": 0},
            "headers_footers": {
                "header_right": "{author_name}",
                "footer_center": "{page_number}",
            },
        }

    def _get_business_report_layout(self) -> Dict[str, Any]:
        """Get business report layout configuration"""
        return {
            "description": "Professional business report layout",
            "page_size": PageSize.A4,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 2.0, "bottom": 2.0, "left": 2.5, "right": 2.5},
            "columns": 1,
            "font": {"family": "Calibri", "size": 11},
            "spacing": {"line_height": 1.15, "paragraph_spacing": 6},
            "headers_footers": {
                "header_left": "{document_title}",
                "header_right": "{date}",
                "footer_center": "Page {page_number} of {total_pages}",
                "footer_right": "{company_name}",
            },
        }

    def _get_magazine_layout(self) -> Dict[str, Any]:
        """Get magazine layout configuration"""
        return {
            "description": "Multi-column magazine layout",
            "page_size": PageSize.A4,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 1.5, "bottom": 1.5, "left": 1.5, "right": 1.5},
            "columns": 2,
            "column_gap": 0.8,
            "font": {"family": "Georgia", "size": 10},
            "spacing": {"line_height": 1.3, "paragraph_spacing": 4},
        }

    def _get_newspaper_layout(self) -> Dict[str, Any]:
        """Get newspaper layout configuration"""
        return {
            "description": "Multi-column newspaper layout",
            "page_size": PageSize.TABLOID,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0},
            "columns": 4,
            "column_gap": 0.5,
            "font": {"family": "Arial", "size": 9},
            "spacing": {"line_height": 1.2, "paragraph_spacing": 3},
        }

    def _get_presentation_layout(self) -> Dict[str, Any]:
        """Get presentation layout configuration"""
        return {
            "description": "Landscape presentation layout",
            "page_size": PageSize.A4,
            "orientation": PageOrientation.LANDSCAPE,
            "margins": {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0},
            "columns": 1,
            "font": {"family": "Helvetica", "size": 14},
            "spacing": {"line_height": 1.4, "paragraph_spacing": 12},
        }

    def _get_technical_doc_layout(self) -> Dict[str, Any]:
        """Get technical documentation layout configuration"""
        return {
            "description": "Technical documentation with wide margins for notes",
            "page_size": PageSize.A4,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 2.0, "bottom": 2.0, "left": 3.5, "right": 2.0},
            "columns": 1,
            "font": {"family": "Consolas", "size": 10},
            "spacing": {"line_height": 1.4, "paragraph_spacing": 8},
        }

    def _get_letter_layout(self) -> Dict[str, Any]:
        """Get letter layout configuration"""
        return {
            "description": "Standard business letter layout",
            "page_size": PageSize.LETTER,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
            "columns": 1,
            "font": {"family": "Times New Roman", "size": 12},
            "spacing": {"line_height": 1.0, "paragraph_spacing": 12},
        }

    def _get_invoice_layout(self) -> Dict[str, Any]:
        """Get invoice layout configuration"""
        return {
            "description": "Invoice and billing document layout",
            "page_size": PageSize.A4,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 1.5, "bottom": 1.5, "left": 2.0, "right": 2.0},
            "columns": 1,
            "font": {"family": "Arial", "size": 10},
            "spacing": {"line_height": 1.2, "paragraph_spacing": 4},
        }

    def _get_brochure_layout(self) -> Dict[str, Any]:
        """Get brochure layout configuration"""
        return {
            "description": "Tri-fold brochure layout",
            "page_size": PageSize.A4,
            "orientation": PageOrientation.LANDSCAPE,
            "margins": {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0},
            "columns": 3,
            "column_gap": 0.5,
            "font": {"family": "Verdana", "size": 9},
            "spacing": {"line_height": 1.3, "paragraph_spacing": 6},
        }

    # Helper methods
    def _get_layout_preset(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """Get layout preset by name"""
        return self.layout_presets.get(preset_name)

    def _calculate_page_dimensions(
        self,
        page_size: PageSize,
        orientation: PageOrientation,
        margins: Dict[str, float],
    ) -> Dict[str, Any]:
        """Calculate page dimensions including margins"""
        # Standard page sizes in cm
        page_sizes = {
            PageSize.A4: (21.0, 29.7),
            PageSize.A3: (29.7, 42.0),
            PageSize.A5: (14.8, 21.0),
            PageSize.LETTER: (21.59, 27.94),
            PageSize.LEGAL: (21.59, 35.56),
            PageSize.TABLOID: (27.94, 43.18),
        }

        width, height = page_sizes.get(page_size, (21.0, 29.7))

        if orientation == PageOrientation.LANDSCAPE:
            width, height = height, width

        content_width = width - margins["left"] - margins["right"]
        content_height = height - margins["top"] - margins["bottom"]

        return {
            "page_width": width,
            "page_height": height,
            "content_width": content_width,
            "content_height": content_height,
            "margins": margins,
        }

    def _calculate_column_configuration(
        self,
        num_columns: int,
        column_gap: float,
        column_widths: Optional[List[float]],
        balance_columns: bool,
    ) -> Dict[str, Any]:
        """Calculate column configuration"""
        config: Dict[str, Any] = {
            "num_columns": num_columns,
            "column_gap": column_gap,
            "balance_columns": balance_columns,
        }

        if column_widths:
            config["column_widths"] = column_widths
            config["custom_widths"] = True
        else:
            # Equal column widths
            config["custom_widths"] = False

        return config

    def _apply_page_layout_to_document(self, document_path: str, layout_config: Dict[str, Any]):
        """Apply page layout configuration to document"""
        # Detect document format
        file_format = self._detect_document_format(document_path)

        # Generate layout markup based on format
        if file_format == "markdown":
            layout_markup = self._generate_markdown_layout_markup(layout_config)
        elif file_format == "html":
            layout_markup = self._generate_html_layout_markup(layout_config)
        elif file_format == "latex":
            layout_markup = self._generate_latex_layout_markup(layout_config)
        else:
            layout_markup = self._generate_generic_layout_markup(layout_config)

        # Insert layout markup into document
        self._insert_layout_markup(document_path, layout_markup, "page_layout")

    def _apply_multi_column_layout(self, document_path: str, column_config: Dict[str, Any]):
        """Apply multi-column layout to document"""
        file_format = self._detect_document_format(document_path)

        if file_format == "html":
            column_markup = self._generate_html_column_markup(column_config)
        elif file_format == "latex":
            column_markup = self._generate_latex_column_markup(column_config)
        else:
            column_markup = self._generate_generic_column_markup(column_config)

        self._insert_layout_markup(document_path, column_markup, "multi_column")

    def _apply_headers_footers(
        self,
        document_path: str,
        header_config: Dict[str, Any],
        footer_config: Dict[str, Any],
    ):
        """Apply headers and footers to document"""
        file_format = self._detect_document_format(document_path)

        header_markup = self._generate_header_footer_markup(header_config, "header", file_format)
        footer_markup = self._generate_header_footer_markup(footer_config, "footer", file_format)

        self._insert_layout_markup(document_path, header_markup, "headers")
        self._insert_layout_markup(document_path, footer_markup, "footers")

    def _process_header_footer_config(
        self,
        config: Optional[Dict[str, Any]],
        hf_type: str,
        page_numbering: bool,
        numbering_style: str,
    ) -> Dict[str, Any]:
        """Process header or footer configuration"""
        processed = config.copy() if config else {}

        # Add page numbering if requested
        if page_numbering:
            numbering_text = self._generate_page_numbering_text(numbering_style)
            if hf_type == "footer" and "center" not in processed:
                processed["center"] = numbering_text
            elif hf_type == "header" and "right" not in processed:
                processed["right"] = numbering_text

        return processed

    def _generate_page_numbering_text(self, style: str) -> str:
        """Generate page numbering text based on style"""
        if style == "roman":
            return "{page_roman}"
        elif style == "alpha":
            return "{page_alpha}"
        elif style == "with_total":
            return "Page {page} of {total_pages}"
        else:  # numeric
            return "{page}"

    def _generate_break_markup(self, break_type: BreakType, options: Optional[Dict[str, Any]]) -> str:
        """Generate break markup based on type"""
        if break_type == BreakType.PAGE_BREAK:
            return "\n<!-- PAGE BREAK -->\n\\newpage\n"
        elif break_type == BreakType.SECTION_BREAK:
            return "\n<!-- SECTION BREAK -->\n\\clearpage\n"
        elif break_type == BreakType.COLUMN_BREAK:
            return "\n<!-- COLUMN BREAK -->\n\\columnbreak\n"
        elif break_type == BreakType.LINE_BREAK:
            return "\n<!-- LINE BREAK -->\n\\linebreak\n"
        else:
            return "\n"

    def _insert_break_at_position(
        self,
        document_path: str,
        break_markup: str,
        position: Optional[Dict[str, Any]],
    ):
        """Insert break markup at specified position"""
        try:
            with open(document_path, "r", encoding="utf-8") as f:
                content = f.read()

            if position:
                if "line" in position:
                    lines = content.split("\n")
                    line_num = position["line"]
                    if 0 <= line_num <= len(lines):
                        lines.insert(line_num, break_markup.strip())
                        content = "\n".join(lines)
                elif "offset" in position:
                    offset = position["offset"]
                    content = content[:offset] + break_markup + content[offset:]
            else:
                # Append at end
                content += break_markup

            with open(document_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            raise LayoutConfigurationError(f"Failed to insert break: {str(e)}")

    def _process_typography_config(
        self,
        font_config: Dict[str, Any],
        spacing_config: Optional[Dict[str, Any]],
        alignment: Optional[AlignmentType],
    ) -> Dict[str, Any]:
        """Process typography configuration"""
        config = {
            "font": font_config,
            "spacing": spacing_config or {},
            "alignment": alignment,
        }

        # Validate font configuration
        required_font_keys = ["family", "size"]
        for key in required_font_keys:
            if key not in font_config:
                raise LayoutConfigurationError(f"Missing font configuration: {key}")

        return config

    def _apply_typography_settings(self, document_path: str, typography_config: Dict[str, Any]):
        """Apply typography settings to document"""
        file_format = self._detect_document_format(document_path)

        if file_format == "html":
            typography_markup = self._generate_html_typography_markup(typography_config)
        elif file_format == "latex":
            typography_markup = self._generate_latex_typography_markup(typography_config)
        else:
            typography_markup = self._generate_generic_typography_markup(typography_config)

        self._insert_layout_markup(document_path, typography_markup, "typography")

    def _analyze_current_layout(self, document_path: str) -> Dict[str, Any]:
        """Analyze current document layout"""
        try:
            with open(document_path, "r", encoding="utf-8") as f:
                content = f.read()

            return {
                "content_length": len(content),
                "line_count": len(content.split("\n")),
                "word_count": len(content.split()),
                "has_headers": "header" in content.lower(),
                "has_columns": "column" in content.lower(),
                "file_format": self._detect_document_format(document_path),
            }
        except Exception:
            return {"error": "Failed to analyze layout"}

    def _generate_optimization_plan(
        self,
        current_layout: Dict[str, Any],
        content_analysis: Dict[str, Any],
        optimization_goals: List[str],
    ) -> Dict[str, Any]:
        """Generate layout optimization plan"""
        plan: Dict[str, Any] = {
            "optimizations": [],
            "goals": optimization_goals,
            "current_layout": current_layout,
            "content_analysis": content_analysis,
        }

        # Add optimizations based on goals
        for goal in optimization_goals:
            if goal == "readability":
                plan["optimizations"].append(
                    {
                        "type": "typography",
                        "action": "improve_readability",
                        "details": "Increase line height and adjust font size",
                    }
                )
            elif goal == "space_efficiency":
                plan["optimizations"].append(
                    {
                        "type": "layout",
                        "action": "optimize_spacing",
                        "details": "Reduce margins and adjust paragraph spacing",
                    }
                )
            elif goal == "professional":
                plan["optimizations"].append(
                    {
                        "type": "styling",
                        "action": "apply_professional_style",
                        "details": "Use professional fonts and consistent formatting",
                    }
                )

        return plan

    def _apply_layout_optimizations(self, document_path: str, optimization_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Apply layout optimizations based on plan"""
        results: Dict[str, Any] = {
            "optimizations_applied": [],
            "success_count": 0,
            "error_count": 0,
        }

        for optimization in optimization_plan.get("optimizations", []):
            try:
                # Apply optimization based on type
                if optimization["type"] == "typography":
                    self._apply_typography_optimization(document_path, optimization)
                elif optimization["type"] == "layout":
                    self._apply_layout_optimization(document_path, optimization)
                elif optimization["type"] == "styling":
                    self._apply_styling_optimization(document_path, optimization)

                results["optimizations_applied"].append(optimization)
                success_count = results.get("success_count", 0)
                if isinstance(success_count, (int, float)):
                    results["success_count"] = success_count + 1

            except Exception as e:
                error_count = results.get("error_count", 0)
                if isinstance(error_count, (int, float)):
                    results["error_count"] = error_count + 1
                self.logger.warning(f"Failed to apply optimization {optimization['type']}: {e}")

        return results

    def _apply_typography_optimization(self, document_path: str, optimization: Dict[str, Any]):
        """Apply typography optimization"""
        # Simplified implementation

    def _apply_layout_optimization(self, document_path: str, optimization: Dict[str, Any]):
        """Apply layout optimization"""
        # Simplified implementation

    def _apply_styling_optimization(self, document_path: str, optimization: Dict[str, Any]):
        """Apply styling optimization"""
        # Simplified implementation

    def _detect_document_format(self, document_path: str) -> str:
        """Detect document format from file extension"""
        ext = os.path.splitext(document_path)[1].lower()
        format_map = {
            ".md": "markdown",
            ".markdown": "markdown",
            ".html": "html",
            ".htm": "html",
            ".tex": "latex",
            ".latex": "latex",
            ".txt": "text",
        }
        return format_map.get(ext, "text")

    def _generate_markdown_layout_markup(self, layout_config: Dict[str, Any]) -> str:
        """Generate Markdown layout markup"""
        return f"<!-- Layout: {layout_config['page_size']} {layout_config['orientation']} -->\n"

    def _generate_html_layout_markup(self, layout_config: Dict[str, Any]) -> str:
        """Generate HTML layout markup"""
        margins = layout_config["margins"]
        return f"""<style>
@page {{
    size: {layout_config['page_size']};
    margin: {margins['top']}cm {margins['right']}cm {margins['bottom']}cm {margins['left']}cm;
}}
</style>"""

    def _generate_latex_layout_markup(self, layout_config: Dict[str, Any]) -> str:
        """Generate LaTeX layout markup"""
        margins = layout_config["margins"]
        return f"""\\usepackage[top={margins['top']}cm,bottom={margins['bottom']}cm,left={margins['left']}cm,right={margins['right']}cm]{{geometry}}
\\usepackage[{layout_config['orientation']}]{{geometry}}"""

    def _generate_generic_layout_markup(self, layout_config: Dict[str, Any]) -> str:
        """Generate generic layout markup"""
        return f"# Layout Configuration\nPage: {layout_config['page_size']} {layout_config['orientation']}\n"

    def _generate_html_column_markup(self, column_config: Dict[str, Any]) -> str:
        """Generate HTML column markup"""
        num_cols = column_config["num_columns"]
        gap = column_config["column_gap"]
        return f"""<style>
.multi-column {{
    column-count: {num_cols};
    column-gap: {gap}cm;
}}
</style>
<div class="multi-column">"""

    def _generate_latex_column_markup(self, column_config: Dict[str, Any]) -> str:
        """Generate LaTeX column markup"""
        return f"\\begin{{multicols}}{{{column_config['num_columns']}}}"

    def _generate_generic_column_markup(self, column_config: Dict[str, Any]) -> str:
        """Generate generic column markup"""
        return f"<!-- {column_config['num_columns']} columns -->\n"

    def _generate_header_footer_markup(self, config: Dict[str, Any], hf_type: str, file_format: str) -> str:
        """Generate header/footer markup"""
        if file_format == "html":
            return f"<!-- {hf_type.upper()}: {config} -->\n"
        elif file_format == "latex":
            return f"% {hf_type.upper()}: {config}\n"
        else:
            return f"# {hf_type.upper()}: {config}\n"

    def _generate_html_typography_markup(self, typography_config: Dict[str, Any]) -> str:
        """Generate HTML typography markup"""
        font = typography_config["font"]
        return f"""<style>
body {{
    font-family: '{font['family']}';
    font-size: {font['size']}pt;
}}
</style>"""

    def _generate_latex_typography_markup(self, typography_config: Dict[str, Any]) -> str:
        """Generate LaTeX typography markup"""
        font = typography_config["font"]
        return f"\\usepackage{{fontspec}}\n\\setmainfont{{{font['family']}}}\n"

    def _generate_generic_typography_markup(self, typography_config: Dict[str, Any]) -> str:
        """Generate generic typography markup"""
        return f"# Typography: {typography_config['font']}\n"

    def _insert_layout_markup(self, document_path: str, markup: str, markup_type: str):
        """Insert layout markup into document"""
        try:
            with open(document_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Insert at the beginning of document
            content = markup + "\n" + content

            with open(document_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            raise LayoutConfigurationError(f"Failed to insert {markup_type} markup: {str(e)}")
