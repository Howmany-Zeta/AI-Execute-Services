"""
Comprehensive tests for DocumentLayoutTool

This test suite covers all functionality of the DocumentLayoutTool including:
- Page layout configuration
- Multi-column layouts
- Headers and footers setup
- Break insertion
- Typography configuration
- Layout optimization
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

from aiecs.tools.docs.document_layout_tool import (
    DocumentLayoutTool,
    PageSize,
    PageOrientation,
    LayoutType,
    AlignmentType,
    BreakType,
    HeaderFooterPosition,
    DocumentLayoutSettings,
    DocumentLayoutError,
    LayoutConfigurationError,
    PageSetupError
)

logger = logging.getLogger(__name__)


class TestDocumentLayoutTool:
    """Test suite for DocumentLayoutTool"""
    
    @pytest.fixture
    def layout_config(self):
        """Configuration for DocumentLayoutTool"""
        return {
            "temp_dir": "/tmp/test_layouts",
            "default_page_size": PageSize.A4,
            "default_orientation": PageOrientation.PORTRAIT,
            "default_margins": {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0},
            "auto_adjust_layout": True,
            "preserve_formatting": True
        }
    
    @pytest.fixture
    def layout_tool(self, layout_config):
        """Create DocumentLayoutTool instance for testing"""
        return DocumentLayoutTool(layout_config)
    
    @pytest.fixture
    def layout_tool_with_default_config(self):
        """Create DocumentLayoutTool with default configuration"""
        return DocumentLayoutTool()
    
    @pytest.fixture
    def sample_document_path(self, temp_dir):
        """Create a sample document path for testing"""
        doc_path = temp_dir / "test_document.md"
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\nThis is a test document for layout testing.\n")
        return str(doc_path)
    
    def test_initialization_with_config(self, layout_config):
        """Test DocumentLayoutTool initialization with custom config"""
        layout_tool = DocumentLayoutTool(layout_config)
        
        assert layout_tool.settings.default_page_size == PageSize.A4
        assert layout_tool.settings.default_orientation == PageOrientation.PORTRAIT
        assert layout_tool.settings.default_margins == {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0}
        assert layout_tool.settings.auto_adjust_layout is True
        assert layout_tool.settings.preserve_formatting is True
    
    def test_initialization_with_default_config(self, layout_tool_with_default_config):
        """Test DocumentLayoutTool initialization with default config"""
        layout_tool = layout_tool_with_default_config
        
        assert layout_tool.settings.default_page_size == PageSize.A4
        assert layout_tool.settings.default_orientation == PageOrientation.PORTRAIT
        assert layout_tool.settings.default_margins == {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
        assert layout_tool.settings.auto_adjust_layout is True
        assert layout_tool.settings.preserve_formatting is True
    
    def test_invalid_config_raises_error(self):
        """Test that invalid configuration raises ValueError"""
        invalid_config = {
            "invalid_setting": "invalid_value",
            "default_margins": "not_a_dict"
        }
        
        with pytest.raises(ValueError, match="Invalid settings"):
            DocumentLayoutTool(invalid_config)
    
    def test_layout_presets_initialization(self, layout_tool):
        """Test that layout presets are properly initialized"""
        presets = layout_tool.layout_presets
        
        expected_presets = [
            "default", "academic_paper", "business_report", "magazine",
            "newspaper", "presentation", "technical_doc", "letter",
            "invoice", "brochure"
        ]
        
        for preset_name in expected_presets:
            assert preset_name in presets
            preset = presets[preset_name]
            assert "description" in preset
            assert "page_size" in preset
            assert "orientation" in preset
            assert "margins" in preset
    
    def test_set_page_layout_basic(self, layout_tool, sample_document_path):
        """Test basic page layout setting functionality"""
        margins = {"top": 2.5, "bottom": 2.5, "left": 3.0, "right": 2.5}
        
        result = layout_tool.set_page_layout(
            document_path=sample_document_path,
            page_size=PageSize.A4,
            orientation=PageOrientation.PORTRAIT,
            margins=margins
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "operation_type" in result
        assert "document_path" in result
        assert "layout_config" in result
        assert "timestamp" in result
        assert "duration" in result
        
        # Verify values
        assert result["operation_type"] == "set_page_layout"
        assert result["document_path"] == sample_document_path
        assert result["layout_config"]["page_size"] == PageSize.A4
        assert result["layout_config"]["orientation"] == PageOrientation.PORTRAIT
        assert result["layout_config"]["margins"] == margins
    
    def test_set_page_layout_with_preset(self, layout_tool, sample_document_path):
        """Test page layout setting with preset"""
        margins = {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
        
        result = layout_tool.set_page_layout(
            document_path=sample_document_path,
            page_size=PageSize.A4,
            orientation=PageOrientation.PORTRAIT,
            margins=margins,
            layout_preset="academic_paper"
        )
        
        assert result["layout_config"]["layout_preset"] == "academic_paper"
        assert "dimensions" in result["layout_config"]
    
    def test_set_page_layout_different_sizes(self, layout_tool, sample_document_path):
        """Test page layout setting with different page sizes"""
        sizes_to_test = [PageSize.A4, PageSize.A3, PageSize.LETTER, PageSize.LEGAL]
        margins = {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0}
        
        for page_size in sizes_to_test:
            result = layout_tool.set_page_layout(
                document_path=f"{sample_document_path}_{page_size.value}",
                page_size=page_size,
                orientation=PageOrientation.PORTRAIT,
                margins=margins
            )
            
            assert result["layout_config"]["page_size"] == page_size
            assert "dimensions" in result["layout_config"]
    
    def test_set_page_layout_different_orientations(self, layout_tool, sample_document_path):
        """Test page layout setting with different orientations"""
        orientations_to_test = [PageOrientation.PORTRAIT, PageOrientation.LANDSCAPE]
        margins = {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0}
        
        for orientation in orientations_to_test:
            result = layout_tool.set_page_layout(
                document_path=f"{sample_document_path}_{orientation.value}",
                page_size=PageSize.A4,
                orientation=orientation,
                margins=margins
            )
            
            assert result["layout_config"]["orientation"] == orientation
            assert "dimensions" in result["layout_config"]
    
    def test_set_page_layout_invalid_margins(self, layout_tool, sample_document_path):
        """Test page layout setting with invalid margins"""
        invalid_margins = {"top": 2.0, "bottom": 2.0}  # Missing left and right
        
        with pytest.raises(LayoutConfigurationError, match="Missing margin"):
            layout_tool.set_page_layout(
                document_path=sample_document_path,
                page_size=PageSize.A4,
                orientation=PageOrientation.PORTRAIT,
                margins=invalid_margins
            )
    
    def test_create_multi_column_layout_basic(self, layout_tool, sample_document_path):
        """Test basic multi-column layout creation"""
        result = layout_tool.create_multi_column_layout(
            document_path=sample_document_path,
            num_columns=2,
            column_gap=1.0,
            balance_columns=True
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "operation_type" in result
        assert "document_path" in result
        assert "column_config" in result
        assert "timestamp" in result
        assert "duration" in result
        
        # Verify values
        assert result["operation_type"] == "create_multi_column_layout"
        assert result["document_path"] == sample_document_path
        assert result["column_config"]["num_columns"] == 2
        assert result["column_config"]["column_gap"] == 1.0
        assert result["column_config"]["balance_columns"] is True
    
    def test_create_multi_column_layout_with_custom_widths(self, layout_tool, sample_document_path):
        """Test multi-column layout with custom column widths"""
        column_widths = [3.0, 2.0, 1.0]
        
        result = layout_tool.create_multi_column_layout(
            document_path=sample_document_path,
            num_columns=3,
            column_gap=0.5,
            column_widths=column_widths,
            balance_columns=False
        )
        
        assert result["column_config"]["num_columns"] == 3
        assert result["column_config"]["column_widths"] == column_widths
        assert result["column_config"]["custom_widths"] is True
        assert result["column_config"]["balance_columns"] is False
    
    def test_create_multi_column_layout_invalid_columns(self, layout_tool, sample_document_path):
        """Test multi-column layout with invalid number of columns"""
        with pytest.raises(LayoutConfigurationError, match="Number of columns must be at least 1"):
            layout_tool.create_multi_column_layout(
                document_path=sample_document_path,
                num_columns=0,
                column_gap=1.0
            )
    
    def test_create_multi_column_layout_mismatched_widths(self, layout_tool, sample_document_path):
        """Test multi-column layout with mismatched column widths"""
        column_widths = [3.0, 2.0]  # Only 2 widths for 3 columns
        
        with pytest.raises(LayoutConfigurationError, match="Column widths count must match number of columns"):
            layout_tool.create_multi_column_layout(
                document_path=sample_document_path,
                num_columns=3,
                column_gap=1.0,
                column_widths=column_widths
            )
    
    def test_setup_headers_footers_basic(self, layout_tool, sample_document_path):
        """Test basic headers and footers setup"""
        header_config = {
            "left": "Document Title",
            "center": "Section",
            "right": "Date"
        }
        
        footer_config = {
            "left": "Company Name",
            "center": "Page {page}",
            "right": "Confidential"
        }
        
        result = layout_tool.setup_headers_footers(
            document_path=sample_document_path,
            header_config=header_config,
            footer_config=footer_config,
            page_numbering=True,
            numbering_style="numeric"
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "operation_type" in result
        assert "document_path" in result
        assert "header_config" in result
        assert "footer_config" in result
        assert "page_numbering" in result
        assert "numbering_style" in result
        assert "timestamp" in result
        assert "duration" in result
        
        # Verify values
        assert result["operation_type"] == "setup_headers_footers"
        assert result["document_path"] == sample_document_path
        assert result["page_numbering"] is True
        assert result["numbering_style"] == "numeric"
    
    def test_setup_headers_footers_different_styles(self, layout_tool, sample_document_path):
        """Test headers and footers setup with different numbering styles"""
        styles_to_test = ["numeric", "roman", "alpha", "with_total"]
        
        for style in styles_to_test:
            result = layout_tool.setup_headers_footers(
                document_path=f"{sample_document_path}_{style}",
                header_config={"right": "Header"},
                footer_config={"center": "Footer"},
                page_numbering=True,
                numbering_style=style
            )
            
            assert result["numbering_style"] == style
    
    def test_setup_headers_footers_no_numbering(self, layout_tool, sample_document_path):
        """Test headers and footers setup without page numbering"""
        result = layout_tool.setup_headers_footers(
            document_path=sample_document_path,
            header_config={"left": "Title"},
            footer_config={"right": "Footer"},
            page_numbering=False
        )
        
        assert result["page_numbering"] is False
    
    def test_insert_break_page_break(self, layout_tool, sample_document_path):
        """Test page break insertion"""
        position = {"line": 1}
        
        result = layout_tool.insert_break(
            document_path=sample_document_path,
            break_type=BreakType.PAGE_BREAK,
            position=position
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "operation_type" in result
        assert "document_path" in result
        assert "break_type" in result
        assert "position" in result
        assert "break_markup" in result
        assert "timestamp" in result
        assert "duration" in result
        
        # Verify values
        assert result["operation_type"] == "insert_break"
        assert result["document_path"] == sample_document_path
        assert result["break_type"] == BreakType.PAGE_BREAK
        assert result["position"] == position
    
    def test_insert_break_different_types(self, layout_tool, sample_document_path):
        """Test insertion of different break types"""
        break_types_to_test = [
            BreakType.PAGE_BREAK,
            BreakType.SECTION_BREAK,
            BreakType.COLUMN_BREAK,
            BreakType.LINE_BREAK
        ]
        
        for break_type in break_types_to_test:
            result = layout_tool.insert_break(
                document_path=f"{sample_document_path}_{break_type.value}",
                break_type=break_type,
                position={"line": 1}
            )
            
            assert result["break_type"] == break_type
            assert "break_markup" in result
    
    def test_insert_break_with_offset(self, layout_tool, sample_document_path):
        """Test break insertion with offset position"""
        position = {"offset": 50}
        
        result = layout_tool.insert_break(
            document_path=sample_document_path,
            break_type=BreakType.SECTION_BREAK,
            position=position
        )
        
        assert result["position"] == position
    
    def test_insert_break_without_position(self, layout_tool, sample_document_path):
        """Test break insertion without specific position (append at end)"""
        result = layout_tool.insert_break(
            document_path=sample_document_path,
            break_type=BreakType.PAGE_BREAK
        )
        
        assert result["position"] is None
        assert "break_markup" in result
    
    def test_configure_typography_basic(self, layout_tool, sample_document_path):
        """Test basic typography configuration"""
        font_config = {
            "family": "Arial",
            "size": 12,
            "weight": "normal"
        }
        
        spacing_config = {
            "line_height": 1.5,
            "paragraph_spacing": 6
        }
        
        result = layout_tool.configure_typography(
            document_path=sample_document_path,
            font_config=font_config,
            spacing_config=spacing_config,
            alignment=AlignmentType.JUSTIFY
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "operation_type" in result
        assert "document_path" in result
        assert "typography_config" in result
        assert "timestamp" in result
        assert "duration" in result
        
        # Verify values
        assert result["operation_type"] == "configure_typography"
        assert result["document_path"] == sample_document_path
        assert result["typography_config"]["font"] == font_config
        assert result["typography_config"]["spacing"] == spacing_config
        assert result["typography_config"]["alignment"] == AlignmentType.JUSTIFY
    
    def test_configure_typography_different_alignments(self, layout_tool, sample_document_path):
        """Test typography configuration with different alignments"""
        alignments_to_test = [
            AlignmentType.LEFT,
            AlignmentType.CENTER,
            AlignmentType.RIGHT,
            AlignmentType.JUSTIFY
        ]
        
        font_config = {"family": "Times New Roman", "size": 11}
        
        for alignment in alignments_to_test:
            result = layout_tool.configure_typography(
                document_path=f"{sample_document_path}_{alignment.value}",
                font_config=font_config,
                alignment=alignment
            )
            
            assert result["typography_config"]["alignment"] == alignment
    
    def test_configure_typography_missing_font_config(self, layout_tool, sample_document_path):
        """Test typography configuration with missing font configuration"""
        incomplete_font_config = {"family": "Arial"}  # Missing size
        
        with pytest.raises(LayoutConfigurationError, match="Missing font configuration"):
            layout_tool.configure_typography(
                document_path=sample_document_path,
                font_config=incomplete_font_config
            )
    
    def test_optimize_layout_for_content(self, layout_tool, sample_document_path):
        """Test layout optimization for content"""
        content_analysis = {
            "content_length": 1000,
            "line_count": 50,
            "word_count": 200,
            "has_headers": True,
            "has_columns": False
        }
        
        optimization_goals = ["readability", "space_efficiency", "professional"]
        
        result = layout_tool.optimize_layout_for_content(
            document_path=sample_document_path,
            content_analysis=content_analysis,
            optimization_goals=optimization_goals
        )
        
        # Verify result structure
        assert "operation_id" in result
        assert "operation_type" in result
        assert "document_path" in result
        assert "content_analysis" in result
        assert "optimization_goals" in result
        assert "optimization_plan" in result
        assert "optimization_results" in result
        assert "timestamp" in result
        assert "duration" in result
        
        # Verify values
        assert result["operation_type"] == "optimize_layout_for_content"
        assert result["document_path"] == sample_document_path
        assert result["content_analysis"] == content_analysis
        assert result["optimization_goals"] == optimization_goals
    
    def test_get_layout_presets(self, layout_tool):
        """Test getting available layout presets"""
        result = layout_tool.get_layout_presets()
        
        # Verify result structure
        assert "presets" in result
        assert "preset_details" in result
        assert "total_templates" in result
        
        # Verify preset list
        expected_presets = [
            "default", "academic_paper", "business_report", "magazine",
            "newspaper", "presentation", "technical_doc", "letter",
            "invoice", "brochure"
        ]
        
        for preset in expected_presets:
            assert preset in result["presets"]
            assert preset in result["preset_details"]
    
    def test_get_layout_operations(self, layout_tool, sample_document_path):
        """Test getting layout operations history"""
        # Perform some operations first
        layout_tool.set_page_layout(
            document_path=sample_document_path,
            page_size=PageSize.A4,
            orientation=PageOrientation.PORTRAIT,
            margins={"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
        )
        
        layout_tool.create_multi_column_layout(
            document_path=sample_document_path,
            num_columns=2,
            column_gap=1.0
        )
        
        operations = layout_tool.get_layout_operations()
        
        assert len(operations) == 2
        assert operations[0]["operation_type"] == "set_page_layout"
        assert operations[1]["operation_type"] == "create_multi_column_layout"
    
    def test_layout_operations_tracking(self, layout_tool, sample_document_path):
        """Test that layout operations are properly tracked"""
        initial_count = len(layout_tool.get_layout_operations())
        
        # Perform an operation
        layout_tool.set_page_layout(
            document_path=sample_document_path,
            page_size=PageSize.A4,
            orientation=PageOrientation.PORTRAIT,
            margins={"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0}
        )
        
        operations = layout_tool.get_layout_operations()
        assert len(operations) == initial_count + 1
        
        # Verify operation details
        operation = operations[-1]
        assert "operation_id" in operation
        assert "operation_type" in operation
        assert "document_path" in operation
        assert "timestamp" in operation
        assert "duration" in operation
    
    def test_error_handling_invalid_document_path(self, layout_tool):
        """Test error handling for invalid document path"""
        with pytest.raises(PageSetupError):
            layout_tool.set_page_layout(
                document_path="/invalid/path/that/does/not/exist.md",
                page_size=PageSize.A4,
                orientation=PageOrientation.PORTRAIT,
                margins={"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0}
            )
    
    def test_error_handling_layout_configuration_error(self, layout_tool, sample_document_path):
        """Test error handling for layout configuration errors"""
        with pytest.raises(LayoutConfigurationError):
            layout_tool.create_multi_column_layout(
                document_path=sample_document_path,
                num_columns=-1,  # Invalid number of columns
                column_gap=1.0
            )
    
    def test_document_format_detection(self, layout_tool, temp_dir):
        """Test document format detection"""
        # Test different file formats
        formats_to_test = [
            ("test.md", "markdown"),
            ("test.markdown", "markdown"),
            ("test.html", "html"),
            ("test.htm", "html"),
            ("test.tex", "latex"),
            ("test.latex", "latex"),
            ("test.txt", "text")
        ]
        
        for filename, expected_format in formats_to_test:
            file_path = temp_dir / filename
            with open(file_path, 'w') as f:
                f.write("Test content")
            
            detected_format = layout_tool._detect_document_format(str(file_path))
            assert detected_format == expected_format
    
    def test_page_dimensions_calculation(self, layout_tool):
        """Test page dimensions calculation"""
        margins = {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0}
        
        # Test A4 portrait
        dimensions = layout_tool._calculate_page_dimensions(
            PageSize.A4, PageOrientation.PORTRAIT, margins
        )
        
        assert "page_width" in dimensions
        assert "page_height" in dimensions
        assert "content_width" in dimensions
        assert "content_height" in dimensions
        assert "margins" in dimensions
        
        # Test A4 landscape
        dimensions_landscape = layout_tool._calculate_page_dimensions(
            PageSize.A4, PageOrientation.LANDSCAPE, margins
        )
        
        assert dimensions_landscape["page_width"] == dimensions["page_height"]
        assert dimensions_landscape["page_height"] == dimensions["page_width"]
    
    def test_column_configuration_calculation(self, layout_tool):
        """Test column configuration calculation"""
        # Test with equal widths
        config = layout_tool._calculate_column_configuration(
            num_columns=3,
            column_gap=1.0,
            column_widths=None,
            balance_columns=True
        )
        
        assert config["num_columns"] == 3
        assert config["column_gap"] == 1.0
        assert config["balance_columns"] is True
        assert config["custom_widths"] is False
        
        # Test with custom widths
        custom_widths = [3.0, 2.0, 1.0]
        config_custom = layout_tool._calculate_column_configuration(
            num_columns=3,
            column_gap=0.5,
            column_widths=custom_widths,
            balance_columns=False
        )
        
        assert config_custom["column_widths"] == custom_widths
        assert config_custom["custom_widths"] is True
        assert config_custom["balance_columns"] is False
    
    def test_operation_id_uniqueness(self, layout_tool, sample_document_path):
        """Test that operation IDs are unique across multiple operations"""
        operation_ids = set()
        
        for i in range(5):
            result = layout_tool.set_page_layout(
                document_path=f"{sample_document_path}_{i}",
                page_size=PageSize.A4,
                orientation=PageOrientation.PORTRAIT,
                margins={"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0}
            )
            
            operation_id = result["operation_id"]
            assert operation_id not in operation_ids
            operation_ids.add(operation_id)
    
    def test_processing_metadata_tracking(self, layout_tool, sample_document_path):
        """Test that processing metadata is properly tracked"""
        result = layout_tool.set_page_layout(
            document_path=sample_document_path,
            page_size=PageSize.A4,
            orientation=PageOrientation.PORTRAIT,
            margins={"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0}
        )
        
        assert "timestamp" in result
        assert "duration" in result
        
        # Verify duration is a positive number
        assert isinstance(result["duration"], (int, float))
        assert result["duration"] >= 0


class TestLayoutPresets:
    """Test suite for layout presets"""
    
    @pytest.fixture
    def layout_tool(self):
        return DocumentLayoutTool()
    
    def test_default_layout_preset(self, layout_tool):
        """Test default layout preset"""
        preset = layout_tool._get_default_layout()
        
        assert preset["description"] == "Standard single-column layout"
        assert preset["page_size"] == PageSize.A4
        assert preset["orientation"] == PageOrientation.PORTRAIT
        assert preset["columns"] == 1
        assert "font" in preset
        assert "spacing" in preset
    
    def test_academic_paper_layout_preset(self, layout_tool):
        """Test academic paper layout preset"""
        preset = layout_tool._get_academic_paper_layout()
        
        assert preset["description"] == "Academic paper with double spacing"
        assert preset["page_size"] == PageSize.A4
        assert preset["orientation"] == PageOrientation.PORTRAIT
        assert preset["columns"] == 1
        assert preset["font"]["family"] == "Times New Roman"
        assert preset["font"]["size"] == 12
        assert preset["spacing"]["line_height"] == 2.0
        assert "headers_footers" in preset
    
    def test_business_report_layout_preset(self, layout_tool):
        """Test business report layout preset"""
        preset = layout_tool._get_business_report_layout()
        
        assert preset["description"] == "Professional business report layout"
        assert preset["page_size"] == PageSize.A4
        assert preset["orientation"] == PageOrientation.PORTRAIT
        assert preset["columns"] == 1
        assert preset["font"]["family"] == "Calibri"
        assert preset["font"]["size"] == 11
        assert "headers_footers" in preset
    
    def test_magazine_layout_preset(self, layout_tool):
        """Test magazine layout preset"""
        preset = layout_tool._get_magazine_layout()
        
        assert preset["description"] == "Multi-column magazine layout"
        assert preset["page_size"] == PageSize.A4
        assert preset["orientation"] == PageOrientation.PORTRAIT
        assert preset["columns"] == 2
        assert preset["column_gap"] == 0.8
        assert preset["font"]["family"] == "Georgia"
        assert preset["font"]["size"] == 10
    
    def test_newspaper_layout_preset(self, layout_tool):
        """Test newspaper layout preset"""
        preset = layout_tool._get_newspaper_layout()
        
        assert preset["description"] == "Multi-column newspaper layout"
        assert preset["page_size"] == PageSize.TABLOID
        assert preset["orientation"] == PageOrientation.PORTRAIT
        assert preset["columns"] == 4
        assert preset["column_gap"] == 0.5
        assert preset["font"]["family"] == "Arial"
        assert preset["font"]["size"] == 9
    
    def test_presentation_layout_preset(self, layout_tool):
        """Test presentation layout preset"""
        preset = layout_tool._get_presentation_layout()
        
        assert preset["description"] == "Landscape presentation layout"
        assert preset["page_size"] == PageSize.A4
        assert preset["orientation"] == PageOrientation.LANDSCAPE
        assert preset["columns"] == 1
        assert preset["font"]["family"] == "Helvetica"
        assert preset["font"]["size"] == 14
    
    def test_technical_doc_layout_preset(self, layout_tool):
        """Test technical documentation layout preset"""
        preset = layout_tool._get_technical_doc_layout()
        
        assert preset["description"] == "Technical documentation with wide margins for notes"
        assert preset["page_size"] == PageSize.A4
        assert preset["orientation"] == PageOrientation.PORTRAIT
        assert preset["columns"] == 1
        assert preset["font"]["family"] == "Consolas"
        assert preset["font"]["size"] == 10
    
    def test_letter_layout_preset(self, layout_tool):
        """Test letter layout preset"""
        preset = layout_tool._get_letter_layout()
        
        assert preset["description"] == "Standard business letter layout"
        assert preset["page_size"] == PageSize.LETTER
        assert preset["orientation"] == PageOrientation.PORTRAIT
        assert preset["columns"] == 1
        assert preset["font"]["family"] == "Times New Roman"
        assert preset["font"]["size"] == 12
    
    def test_invoice_layout_preset(self, layout_tool):
        """Test invoice layout preset"""
        preset = layout_tool._get_invoice_layout()
        
        assert preset["description"] == "Invoice and billing document layout"
        assert preset["page_size"] == PageSize.A4
        assert preset["orientation"] == PageOrientation.PORTRAIT
        assert preset["columns"] == 1
        assert preset["font"]["family"] == "Arial"
        assert preset["font"]["size"] == 10
    
    def test_brochure_layout_preset(self, layout_tool):
        """Test brochure layout preset"""
        preset = layout_tool._get_brochure_layout()
        
        assert preset["description"] == "Tri-fold brochure layout"
        assert preset["page_size"] == PageSize.A4
        assert preset["orientation"] == PageOrientation.LANDSCAPE
        assert preset["columns"] == 3
        assert preset["column_gap"] == 0.5
        assert preset["font"]["family"] == "Verdana"
        assert preset["font"]["size"] == 9


class TestMarkupGeneration:
    """Test suite for markup generation"""
    
    @pytest.fixture
    def layout_tool(self):
        return DocumentLayoutTool()
    
    def test_markdown_layout_markup_generation(self, layout_tool):
        """Test Markdown layout markup generation"""
        layout_config = {
            "page_size": PageSize.A4,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
        }
        
        markup = layout_tool._generate_markdown_layout_markup(layout_config)
        
        assert isinstance(markup, str)
        assert "Layout:" in markup
        assert "a4" in markup.lower()
        assert "portrait" in markup.lower()
    
    def test_html_layout_markup_generation(self, layout_tool):
        """Test HTML layout markup generation"""
        layout_config = {
            "page_size": PageSize.A4,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
        }
        
        markup = layout_tool._generate_html_layout_markup(layout_config)
        
        assert isinstance(markup, str)
        assert "<style>" in markup
        assert "@page" in markup
        assert "size:" in markup
        assert "margin:" in markup
    
    def test_latex_layout_markup_generation(self, layout_tool):
        """Test LaTeX layout markup generation"""
        layout_config = {
            "page_size": PageSize.A4,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
        }
        
        markup = layout_tool._generate_latex_layout_markup(layout_config)
        
        assert isinstance(markup, str)
        assert "\\usepackage" in markup
        assert "geometry" in markup
    
    def test_generic_layout_markup_generation(self, layout_tool):
        """Test generic layout markup generation"""
        layout_config = {
            "page_size": PageSize.A4,
            "orientation": PageOrientation.PORTRAIT,
            "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
        }
        
        markup = layout_tool._generate_generic_layout_markup(layout_config)
        
        assert isinstance(markup, str)
        assert "Layout Configuration" in markup
        assert "a4" in markup.lower()
        assert "portrait" in markup.lower()
    
    def test_html_column_markup_generation(self, layout_tool):
        """Test HTML column markup generation"""
        column_config = {
            "num_columns": 3,
            "column_gap": 1.0,
            "balance_columns": True
        }
        
        markup = layout_tool._generate_html_column_markup(column_config)
        
        assert isinstance(markup, str)
        assert "<style>" in markup
        assert "multi-column" in markup
        assert "column-count: 3" in markup
        assert "column-gap: 1.0cm" in markup
    
    def test_latex_column_markup_generation(self, layout_tool):
        """Test LaTeX column markup generation"""
        column_config = {
            "num_columns": 2,
            "column_gap": 1.0,
            "balance_columns": True
        }
        
        markup = layout_tool._generate_latex_column_markup(column_config)
        
        assert isinstance(markup, str)
        assert "\\begin{multicols}{2}" in markup
    
    def test_generic_column_markup_generation(self, layout_tool):
        """Test generic column markup generation"""
        column_config = {
            "num_columns": 2,
            "column_gap": 1.0,
            "balance_columns": True
        }
        
        markup = layout_tool._generate_generic_column_markup(column_config)
        
        assert isinstance(markup, str)
        assert "2 columns" in markup
    
    def test_header_footer_markup_generation(self, layout_tool):
        """Test header/footer markup generation"""
        config = {"left": "Title", "center": "Section", "right": "Date"}
        
        # Test HTML format
        html_markup = layout_tool._generate_header_footer_markup(config, "header", "html")
        assert isinstance(html_markup, str)
        assert "HEADER:" in html_markup
        
        # Test LaTeX format
        latex_markup = layout_tool._generate_header_footer_markup(config, "footer", "latex")
        assert isinstance(latex_markup, str)
        assert "FOOTER:" in latex_markup
        
        # Test generic format
        generic_markup = layout_tool._generate_header_footer_markup(config, "header", "generic")
        assert isinstance(generic_markup, str)
        assert "HEADER:" in generic_markup
    
    def test_html_typography_markup_generation(self, layout_tool):
        """Test HTML typography markup generation"""
        typography_config = {
            "font": {"family": "Arial", "size": 12},
            "spacing": {"line_height": 1.5},
            "alignment": AlignmentType.JUSTIFY
        }
        
        markup = layout_tool._generate_html_typography_markup(typography_config)
        
        assert isinstance(markup, str)
        assert "<style>" in markup
        assert "font-family: 'Arial'" in markup
        assert "font-size: 12pt" in markup
    
    def test_latex_typography_markup_generation(self, layout_tool):
        """Test LaTeX typography markup generation"""
        typography_config = {
            "font": {"family": "Times New Roman", "size": 12},
            "spacing": {"line_height": 1.5},
            "alignment": AlignmentType.JUSTIFY
        }
        
        markup = layout_tool._generate_latex_typography_markup(typography_config)
        
        assert isinstance(markup, str)
        assert "\\usepackage{fontspec}" in markup
        assert "\\setmainfont{Times New Roman}" in markup
    
    def test_generic_typography_markup_generation(self, layout_tool):
        """Test generic typography markup generation"""
        typography_config = {
            "font": {"family": "Arial", "size": 12},
            "spacing": {"line_height": 1.5},
            "alignment": AlignmentType.JUSTIFY
        }
        
        markup = layout_tool._generate_generic_typography_markup(typography_config)
        
        assert isinstance(markup, str)
        assert "Typography:" in markup


class TestErrorHandling:
    """Test suite for error handling"""
    
    @pytest.fixture
    def layout_tool(self):
        return DocumentLayoutTool()
    
    def test_document_layout_error(self, layout_tool):
        """Test DocumentLayoutError handling"""
        with pytest.raises(DocumentLayoutError):
            raise DocumentLayoutError("Test layout error")
    
    def test_layout_configuration_error(self, layout_tool):
        """Test LayoutConfigurationError handling"""
        with pytest.raises(LayoutConfigurationError):
            raise LayoutConfigurationError("Test configuration error")
    
    def test_page_setup_error(self, layout_tool):
        """Test PageSetupError handling"""
        with pytest.raises(PageSetupError):
            raise PageSetupError("Test page setup error")
    
    def test_error_inheritance(self, layout_tool):
        """Test that specific errors inherit from base error"""
        assert issubclass(LayoutConfigurationError, DocumentLayoutError)
        assert issubclass(PageSetupError, DocumentLayoutError)
    
    def test_error_handling_in_operations(self, layout_tool, temp_dir):
        """Test error handling in layout operations"""
        # Test with non-existent file
        with pytest.raises(PageSetupError):
            layout_tool.set_page_layout(
                document_path=str(temp_dir / "non_existent.md"),
                page_size=PageSize.A4,
                orientation=PageOrientation.PORTRAIT,
                margins={"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0}
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


