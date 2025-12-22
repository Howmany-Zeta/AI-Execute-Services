"""
Comprehensive tests for ContentInsertionTool

This test suite covers all functionality of the ContentInsertionTool including:
- Chart insertion and generation
- Table creation and formatting
- Image insertion and processing
- Media content handling
- Interactive element insertion
- Citation management
- Batch content operations
- Content validation and processing
"""
import os
import pytest
import tempfile
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Import fixtures from conftest_docs
pytest_plugins = ["conftest_docs"]

from aiecs.tools.docs.content_insertion_tool import (
    ContentInsertionTool,
    ContentType,
    ChartType,
    TableStyle,
    ImageAlignment,
    InsertionPosition,
    ContentInsertionSettings,
    ContentInsertionError,
    ChartError,
    TableError,
    ImageError,
    MediaError
)

logger = logging.getLogger(__name__)


class TestContentInsertionTool:
    """Test suite for ContentInsertionTool"""
    
    @pytest.fixture
    def insertion_config(self):
        """Configuration for ContentInsertionTool"""
        return {
            "output_dir": "/tmp/test_output",
            "default_chart_style": "default",
            "default_table_style": TableStyle.SIMPLE,
            "default_image_alignment": ImageAlignment.CENTER,
            "max_image_size": 1024 * 1024,  # 1MB
            "supported_image_formats": ["png", "jpg", "jpeg", "gif", "svg"],
            "auto_resize_images": True,
            "generate_thumbnails": True,
            "validate_content": True,
            "backup_original": True
        }
    
    @pytest.fixture
    def insertion_tool(self, insertion_config):
        """Create ContentInsertionTool instance for testing"""
        return ContentInsertionTool(insertion_config)
    
    @pytest.fixture
    def insertion_tool_with_default_config(self):
        """Create ContentInsertionTool with default configuration"""
        return ContentInsertionTool()
    
    @pytest.fixture
    def sample_chart_data(self):
        """Sample chart data for testing"""
        return {
            "labels": ["Jan", "Feb", "Mar", "Apr", "May"],
            "datasets": [
                {
                    "label": "Sales",
                    "data": [100, 120, 90, 150, 180],
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "borderColor": "rgba(54, 162, 235, 1)"
                }
            ]
        }
    
    @pytest.fixture
    def sample_table_data(self):
        """Sample table data for testing"""
        return {
            "headers": ["Name", "Age", "City", "Salary"],
            "rows": [
                ["John Doe", "30", "New York", "$50,000"],
                ["Jane Smith", "25", "Los Angeles", "$45,000"],
                ["Bob Johnson", "35", "Chicago", "$60,000"]
            ]
        }
    
    def test_initialization_with_config(self, insertion_config):
        """Test ContentInsertionTool initialization with custom config"""
        insertion_tool = ContentInsertionTool(insertion_config)
        
        assert insertion_tool.settings.default_chart_style == "default"
        assert insertion_tool.settings.default_table_style == TableStyle.SIMPLE
        assert insertion_tool.settings.default_image_alignment == ImageAlignment.CENTER
        assert insertion_tool.settings.max_image_size == 1024 * 1024
        assert insertion_tool.settings.auto_resize_images is True
        assert insertion_tool.settings.generate_thumbnails is True
        assert insertion_tool.settings.validate_content is True
        assert insertion_tool.settings.backup_original is True
    
    def test_initialization_with_default_config(self, insertion_tool_with_default_config):
        """Test ContentInsertionTool initialization with default config"""
        insertion_tool = insertion_tool_with_default_config
        
        assert insertion_tool.settings.default_chart_style == "default"
        assert insertion_tool.settings.default_table_style == TableStyle.SIMPLE
        assert insertion_tool.settings.default_image_alignment == ImageAlignment.CENTER
        assert insertion_tool.settings.max_image_size > 0
        assert insertion_tool.settings.auto_resize_images is True
        assert insertion_tool.settings.generate_thumbnails is True
        assert insertion_tool.settings.validate_content is True
        assert insertion_tool.settings.backup_original is True
    
    def test_invalid_config_raises_error(self):
        """Test that invalid configuration raises ValueError"""
        invalid_config = {
            "invalid_setting": "invalid_value",
            "max_image_size": "invalid_size"
        }
        
        with pytest.raises(ValueError, match="Invalid settings"):
            ContentInsertionTool(invalid_config)
    
    def test_insert_chart_basic(self, insertion_tool, sample_chart_data, temp_dir):
        """Test basic chart insertion functionality"""
        doc_path = str(temp_dir / "chart_test.md")
        
        # Create initial document
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\nContent here.\n")
        
        result = insertion_tool.insert_chart(
            document_path=doc_path,
            chart_type=ChartType.BAR,
            chart_data=sample_chart_data,
            chart_title="Sales Report",
            position=InsertionPosition.END,
            chart_style="default"
        )
        
        # Verify result structure
        assert "document_path" in result
        assert "chart_type" in result
        assert "chart_title" in result
        assert "chart_data" in result
        assert "position" in result
        assert "chart_style" in result
        assert "insertion_time" in result
        assert "chart_reference" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["chart_type"] == ChartType.BAR
        assert result["chart_title"] == "Sales Report"
        assert result["chart_data"] == sample_chart_data
        assert result["position"] == InsertionPosition.END
        assert result["chart_style"] == "default"
        
        # Verify chart was inserted into document
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Sales Report" in content
            assert "chart" in content.lower()
    
    def test_insert_chart_different_types(self, insertion_tool, sample_chart_data, temp_dir):
        """Test chart insertion with different chart types"""
        chart_types_to_test = [
            ChartType.BAR,
            ChartType.LINE,
            ChartType.PIE,
            ChartType.SCATTER,
            ChartType.AREA,
            ChartType.DOUGHNUT,
            ChartType.RADAR,
            ChartType.POLAR_AREA,
            ChartType.BUBBLE,
            ChartType.MIXED
        ]
        
        for chart_type in chart_types_to_test:
            doc_path = str(temp_dir / f"chart_{chart_type.value}.md")
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write("# Test Document\n")
            
            result = insertion_tool.insert_chart(
                document_path=doc_path,
                chart_type=chart_type,
                chart_data=sample_chart_data,
                chart_title=f"{chart_type.value.title()} Chart",
                position=InsertionPosition.END
            )
            
            assert result["chart_type"] == chart_type
            assert os.path.exists(doc_path)
    
    def test_insert_chart_different_positions(self, insertion_tool, sample_chart_data, temp_dir):
        """Test chart insertion at different positions"""
        positions_to_test = [
            InsertionPosition.BEGINNING,
            InsertionPosition.END,
            InsertionPosition.AFTER_HEADING,
            InsertionPosition.BEFORE_HEADING,
            InsertionPosition.REPLACE_SECTION
        ]
        
        for position in positions_to_test:
            doc_path = str(temp_dir / f"chart_{position.value}.md")
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write("# Test Document\n\n## Section 1\n\nContent here.\n\n## Section 2\n\nMore content.\n")
            
            result = insertion_tool.insert_chart(
                document_path=doc_path,
                chart_type=ChartType.BAR,
                chart_data=sample_chart_data,
                chart_title=f"Chart at {position.value}",
                position=position
            )
            
            assert result["position"] == position
            assert os.path.exists(doc_path)
    
    def test_insert_table_basic(self, insertion_tool, sample_table_data, temp_dir):
        """Test basic table insertion functionality"""
        doc_path = str(temp_dir / "table_test.md")
        
        # Create initial document
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\nContent here.\n")
        
        result = insertion_tool.insert_table(
            document_path=doc_path,
            table_data=sample_table_data,
            table_title="Employee Data",
            table_style=TableStyle.SIMPLE,
            position=InsertionPosition.END,
            include_header=True
        )
        
        # Verify result structure
        assert "document_path" in result
        assert "table_data" in result
        assert "table_title" in result
        assert "table_style" in result
        assert "position" in result
        assert "include_header" in result
        assert "insertion_time" in result
        assert "table_reference" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["table_data"] == sample_table_data
        assert result["table_title"] == "Employee Data"
        assert result["table_style"] == TableStyle.SIMPLE
        assert result["position"] == InsertionPosition.END
        assert result["include_header"] is True
        
        # Verify table was inserted into document
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Employee Data" in content
            assert "John Doe" in content
            assert "Jane Smith" in content
    
    def test_insert_table_different_styles(self, insertion_tool, sample_table_data, temp_dir):
        """Test table insertion with different styles"""
        styles_to_test = [
            TableStyle.SIMPLE,
            TableStyle.GRID,
            TableStyle.PIPE,
            TableStyle.MULTI_LINE,
            TableStyle.ALIGNED,
            TableStyle.CENTERED,
            TableStyle.LEFT_ALIGNED,
            TableStyle.RIGHT_ALIGNED
        ]
        
        for table_style in styles_to_test:
            doc_path = str(temp_dir / f"table_{table_style.value}.md")
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write("# Test Document\n")
            
            result = insertion_tool.insert_table(
                document_path=doc_path,
                table_data=sample_table_data,
                table_title=f"Table with {table_style.value} style",
                table_style=table_style,
                position=InsertionPosition.END
            )
            
            assert result["table_style"] == table_style
            assert os.path.exists(doc_path)
    
    def test_insert_table_without_header(self, insertion_tool, sample_table_data, temp_dir):
        """Test table insertion without header"""
        doc_path = str(temp_dir / "table_no_header.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        result = insertion_tool.insert_table(
            document_path=doc_path,
            table_data=sample_table_data,
            table_title="Table without header",
            table_style=TableStyle.SIMPLE,
            position=InsertionPosition.END,
            include_header=False
        )
        
        assert result["include_header"] is False
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Name" not in content  # Header should not be included
            assert "John Doe" in content  # Data should still be there
    
    def test_insert_image_basic(self, insertion_tool, temp_dir):
        """Test basic image insertion functionality"""
        doc_path = str(temp_dir / "image_test.md")
        
        # Create initial document
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\nContent here.\n")
        
        # Create a dummy image file
        image_path = str(temp_dir / "test_image.png")
        with open(image_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
        
        result = insertion_tool.insert_image(
            document_path=doc_path,
            image_path=image_path,
            image_title="Test Image",
            image_alt="A test image",
            alignment=ImageAlignment.CENTER,
            position=InsertionPosition.END,
            resize_image=True
        )
        
        # Verify result structure
        assert "document_path" in result
        assert "image_path" in result
        assert "image_title" in result
        assert "image_alt" in result
        assert "alignment" in result
        assert "position" in result
        assert "resize_image" in result
        assert "insertion_time" in result
        assert "image_reference" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["image_path"] == image_path
        assert result["image_title"] == "Test Image"
        assert result["image_alt"] == "A test image"
        assert result["alignment"] == ImageAlignment.CENTER
        assert result["position"] == InsertionPosition.END
        assert result["resize_image"] is True
        
        # Verify image was inserted into document
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test Image" in content
            assert "test_image.png" in content
    
    def test_insert_image_different_alignments(self, insertion_tool, temp_dir):
        """Test image insertion with different alignments"""
        alignments_to_test = [
            ImageAlignment.LEFT,
            ImageAlignment.CENTER,
            ImageAlignment.RIGHT,
            ImageAlignment.FLOAT_LEFT,
            ImageAlignment.FLOAT_RIGHT
        ]
        
        for alignment in alignments_to_test:
            doc_path = str(temp_dir / f"image_{alignment.value}.md")
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write("# Test Document\n")
            
            # Create a dummy image file
            image_path = str(temp_dir / f"test_image_{alignment.value}.png")
            with open(image_path, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
            
            result = insertion_tool.insert_image(
                document_path=doc_path,
                image_path=image_path,
                image_title=f"Image aligned {alignment.value}",
                image_alt="Test image",
                alignment=alignment,
                position=InsertionPosition.END
            )
            
            assert result["alignment"] == alignment
            assert os.path.exists(doc_path)
    
    def test_insert_image_nonexistent(self, insertion_tool, temp_dir):
        """Test image insertion with non-existent image file"""
        doc_path = str(temp_dir / "image_error_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        with pytest.raises(ImageError, match="Image file not found"):
            insertion_tool.insert_image(
                document_path=doc_path,
                image_path="nonexistent_image.png",
                image_title="Test Image",
                image_alt="Test image",
                alignment=ImageAlignment.CENTER,
                position=InsertionPosition.END
            )
    
    def test_insert_media_basic(self, insertion_tool, temp_dir):
        """Test basic media insertion functionality"""
        doc_path = str(temp_dir / "media_test.md")
        
        # Create initial document
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\nContent here.\n")
        
        # Create a dummy video file
        video_path = str(temp_dir / "test_video.mp4")
        with open(video_path, 'wb') as f:
            f.write(b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp41mp42isom')
        
        result = insertion_tool.insert_media(
            document_path=doc_path,
            media_path=video_path,
            media_type=ContentType.VIDEO,
            media_title="Test Video",
            media_description="A test video file",
            position=InsertionPosition.END,
            autoplay=False,
            controls=True
        )
        
        # Verify result structure
        assert "document_path" in result
        assert "media_path" in result
        assert "media_type" in result
        assert "media_title" in result
        assert "media_description" in result
        assert "position" in result
        assert "autoplay" in result
        assert "controls" in result
        assert "insertion_time" in result
        assert "media_reference" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["media_path"] == video_path
        assert result["media_type"] == ContentType.VIDEO
        assert result["media_title"] == "Test Video"
        assert result["media_description"] == "A test video file"
        assert result["position"] == InsertionPosition.END
        assert result["autoplay"] is False
        assert result["controls"] is True
        
        # Verify media was inserted into document
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test Video" in content
            assert "test_video.mp4" in content
    
    def test_insert_media_different_types(self, insertion_tool, temp_dir):
        """Test media insertion with different media types"""
        media_types_to_test = [
            ContentType.VIDEO,
            ContentType.AUDIO,
            ContentType.ANIMATION,
            ContentType.INTERACTIVE
        ]
        
        for media_type in media_types_to_test:
            doc_path = str(temp_dir / f"media_{media_type.value}.md")
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write("# Test Document\n")
            
            # Create appropriate dummy file
            if media_type == ContentType.VIDEO:
                media_path = str(temp_dir / f"test_{media_type.value}.mp4")
                with open(media_path, 'wb') as f:
                    f.write(b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp41mp42isom')
            elif media_type == ContentType.AUDIO:
                media_path = str(temp_dir / f"test_{media_type.value}.mp3")
                with open(media_path, 'wb') as f:
                    f.write(b'ID3\x03\x00\x00\x00\x00\x00\x00')
            else:
                media_path = str(temp_dir / f"test_{media_type.value}.html")
                with open(media_path, 'w') as f:
                    f.write(f"<div>Test {media_type.value}</div>")
            
            result = insertion_tool.insert_media(
                document_path=doc_path,
                media_path=media_path,
                media_type=media_type,
                media_title=f"Test {media_type.value}",
                media_description=f"A test {media_type.value} file",
                position=InsertionPosition.END
            )
            
            assert result["media_type"] == media_type
            assert os.path.exists(doc_path)
    
    def test_insert_interactive_element_basic(self, insertion_tool, temp_dir):
        """Test basic interactive element insertion functionality"""
        doc_path = str(temp_dir / "interactive_test.md")
        
        # Create initial document
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\nContent here.\n")
        
        interactive_config = {
            "type": "quiz",
            "questions": [
                {
                    "question": "What is 2 + 2?",
                    "options": ["3", "4", "5", "6"],
                    "correct": 1
                }
            ],
            "settings": {
                "show_results": True,
                "allow_retry": True
            }
        }
        
        result = insertion_tool.insert_interactive_element(
            document_path=doc_path,
            element_type=ContentType.INTERACTIVE,
            element_config=interactive_config,
            element_title="Math Quiz",
            position=InsertionPosition.END,
            embed_code=True
        )
        
        # Verify result structure
        assert "document_path" in result
        assert "element_type" in result
        assert "element_config" in result
        assert "element_title" in result
        assert "position" in result
        assert "embed_code" in result
        assert "insertion_time" in result
        assert "element_reference" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["element_type"] == ContentType.INTERACTIVE
        assert result["element_config"] == interactive_config
        assert result["element_title"] == "Math Quiz"
        assert result["position"] == InsertionPosition.END
        assert result["embed_code"] is True
        
        # Verify interactive element was inserted into document
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Math Quiz" in content
            assert "quiz" in content.lower()
    
    def test_insert_citation_basic(self, insertion_tool, temp_dir):
        """Test basic citation insertion functionality"""
        doc_path = str(temp_dir / "citation_test.md")
        
        # Create initial document
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\nContent here.\n")
        
        citation_data = {
            "author": "Smith, J.",
            "title": "Research Paper",
            "journal": "Science Journal",
            "year": "2024",
            "doi": "10.1000/example"
        }
        
        result = insertion_tool.insert_citation(
            document_path=doc_path,
            citation_data=citation_data,
            citation_style="apa",
            position=InsertionPosition.END,
            generate_bibliography=True
        )
        
        # Verify result structure
        assert "document_path" in result
        assert "citation_data" in result
        assert "citation_style" in result
        assert "position" in result
        assert "generate_bibliography" in result
        assert "insertion_time" in result
        assert "citation_reference" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["citation_data"] == citation_data
        assert result["citation_style"] == "apa"
        assert result["position"] == InsertionPosition.END
        assert result["generate_bibliography"] is True
        
        # Verify citation was inserted into document
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Smith, J." in content
            assert "Research Paper" in content
    
    def test_batch_insert_content(self, insertion_tool, sample_chart_data, sample_table_data, temp_dir):
        """Test batch content insertion functionality"""
        doc_path = str(temp_dir / "batch_test.md")
        
        # Create initial document
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\nContent here.\n")
        
        # Create a dummy image file
        image_path = str(temp_dir / "batch_image.png")
        with open(image_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
        
        content_items = [
            {
                "type": "chart",
                "chart_type": ChartType.BAR,
                "chart_data": sample_chart_data,
                "chart_title": "Sales Chart",
                "position": InsertionPosition.END
            },
            {
                "type": "table",
                "table_data": sample_table_data,
                "table_title": "Employee Table",
                "table_style": TableStyle.SIMPLE,
                "position": InsertionPosition.END
            },
            {
                "type": "image",
                "image_path": image_path,
                "image_title": "Batch Image",
                "image_alt": "A batch test image",
                "alignment": ImageAlignment.CENTER,
                "position": InsertionPosition.END
            }
        ]
        
        result = insertion_tool.batch_insert_content(
            document_path=doc_path,
            content_items=content_items,
            preserve_order=True,
            validate_content=True
        )
        
        # Verify result structure
        assert "document_path" in result
        assert "content_items" in result
        assert "items_processed" in result
        assert "items_successful" in result
        assert "items_failed" in result
        assert "preserve_order" in result
        assert "validate_content" in result
        assert "processing_time" in result
        assert "results" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["content_items"] == content_items
        assert result["items_processed"] == 3
        assert result["items_successful"] == 3
        assert result["items_failed"] == 0
        assert result["preserve_order"] is True
        assert result["validate_content"] is True
        
        # Verify all content was inserted
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Sales Chart" in content
            assert "Employee Table" in content
            assert "Batch Image" in content
    
    def test_batch_insert_content_with_failures(self, insertion_tool, sample_chart_data, temp_dir):
        """Test batch content insertion with some failures"""
        doc_path = str(temp_dir / "batch_failure_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        content_items = [
            {
                "type": "chart",
                "chart_type": ChartType.BAR,
                "chart_data": sample_chart_data,
                "chart_title": "Valid Chart",
                "position": InsertionPosition.END
            },
            {
                "type": "image",
                "image_path": "nonexistent_image.png",  # This will fail
                "image_title": "Invalid Image",
                "image_alt": "A non-existent image",
                "alignment": ImageAlignment.CENTER,
                "position": InsertionPosition.END
            }
        ]
        
        result = insertion_tool.batch_insert_content(
            document_path=doc_path,
            content_items=content_items,
            preserve_order=True,
            validate_content=True
        )
        
        assert result["items_processed"] == 2
        assert result["items_successful"] == 1
        assert result["items_failed"] == 1
        assert len(result["results"]) == 2
        
        # Verify successful item
        assert result["results"][0]["success"] is True
        assert result["results"][0]["item"]["chart_title"] == "Valid Chart"
        
        # Verify failed item
        assert result["results"][1]["success"] is False
        assert result["results"][1]["item"]["image_title"] == "Invalid Image"
        assert "error" in result["results"][1]
    
    def test_get_content_references(self, insertion_tool, sample_chart_data, temp_dir):
        """Test getting content references from document"""
        doc_path = str(temp_dir / "references_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        # Insert some content
        insertion_tool.insert_chart(
            document_path=doc_path,
            chart_type=ChartType.BAR,
            chart_data=sample_chart_data,
            chart_title="Test Chart",
            position=InsertionPosition.END
        )
        
        result = insertion_tool.get_content_references(doc_path)
        
        # Verify result structure
        assert "document_path" in result
        assert "total_references" in result
        assert "references_by_type" in result
        assert "references" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["total_references"] > 0
        assert "chart" in result["references_by_type"]
        assert len(result["references"]) > 0
    
    def test_validate_content_basic(self, insertion_tool, sample_chart_data, temp_dir):
        """Test basic content validation functionality"""
        doc_path = str(temp_dir / "validation_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        # Insert content
        insertion_tool.insert_chart(
            document_path=doc_path,
            chart_type=ChartType.BAR,
            chart_data=sample_chart_data,
            chart_title="Test Chart",
            position=InsertionPosition.END
        )
        
        result = insertion_tool.validate_content(doc_path)
        
        # Verify result structure
        assert "document_path" in result
        assert "is_valid" in result
        assert "validation_errors" in result
        assert "validation_warnings" in result
        assert "content_types_found" in result
        assert "validation_time" in result
        
        # Verify values
        assert result["document_path"] == doc_path
        assert result["is_valid"] is True
        assert len(result["validation_errors"]) == 0
        assert "chart" in result["content_types_found"]
    
    def test_error_handling_invalid_chart_data(self, insertion_tool, temp_dir):
        """Test error handling for invalid chart data"""
        doc_path = str(temp_dir / "chart_error_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        invalid_chart_data = {
            "invalid": "data"
        }
        
        with pytest.raises(ChartError, match="Invalid chart data"):
            insertion_tool.insert_chart(
                document_path=doc_path,
                chart_type=ChartType.BAR,
                chart_data=invalid_chart_data,
                chart_title="Invalid Chart",
                position=InsertionPosition.END
            )
    
    def test_error_handling_invalid_table_data(self, insertion_tool, temp_dir):
        """Test error handling for invalid table data"""
        doc_path = str(temp_dir / "table_error_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        invalid_table_data = {
            "invalid": "data"
        }
        
        with pytest.raises(TableError, match="Invalid table data"):
            insertion_tool.insert_table(
                document_path=doc_path,
                table_data=invalid_table_data,
                table_title="Invalid Table",
                table_style=TableStyle.SIMPLE,
                position=InsertionPosition.END
            )
    
    def test_error_handling_invalid_media_type(self, insertion_tool, temp_dir):
        """Test error handling for invalid media type"""
        doc_path = str(temp_dir / "media_error_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        with pytest.raises(MediaError, match="Invalid media type"):
            insertion_tool.insert_media(
                document_path=doc_path,
                media_path="test.txt",
                media_type="invalid_type",
                media_title="Invalid Media",
                media_description="Invalid media type",
                position=InsertionPosition.END
            )


class TestHelperMethods:
    """Test suite for helper methods"""
    
    @pytest.fixture
    def insertion_tool(self):
        return ContentInsertionTool()
    
    def test_validate_chart_data(self, insertion_tool, sample_chart_data):
        """Test chart data validation"""
        # Test valid data
        assert insertion_tool._validate_chart_data(sample_chart_data) is True
        
        # Test invalid data
        invalid_data = {"invalid": "data"}
        with pytest.raises(ChartError, match="Invalid chart data"):
            insertion_tool._validate_chart_data(invalid_data)
    
    def test_validate_table_data(self, insertion_tool, sample_table_data):
        """Test table data validation"""
        # Test valid data
        assert insertion_tool._validate_table_data(sample_table_data) is True
        
        # Test invalid data
        invalid_data = {"invalid": "data"}
        with pytest.raises(TableError, match="Invalid table data"):
            insertion_tool._validate_table_data(invalid_data)
    
    def test_validate_image_file(self, insertion_tool, temp_dir):
        """Test image file validation"""
        # Create a valid image file
        image_path = str(temp_dir / "valid_image.png")
        with open(image_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
        
        assert insertion_tool._validate_image_file(image_path) is True
        
        # Test non-existent file
        with pytest.raises(ImageError, match="Image file not found"):
            insertion_tool._validate_image_file("nonexistent.png")
        
        # Test invalid file format
        invalid_path = str(temp_dir / "invalid.txt")
        with open(invalid_path, 'w') as f:
            f.write("Not an image")
        
        with pytest.raises(ImageError, match="Invalid image format"):
            insertion_tool._validate_image_file(invalid_path)
    
    def test_generate_chart_markup(self, insertion_tool, sample_chart_data):
        """Test chart markup generation"""
        markup = insertion_tool._generate_chart_markup(
            ChartType.BAR, sample_chart_data, "Test Chart", "default"
        )
        
        assert isinstance(markup, str)
        assert "Test Chart" in markup
        assert "chart" in markup.lower()
        assert "bar" in markup.lower()
    
    def test_generate_table_markup(self, insertion_tool, sample_table_data):
        """Test table markup generation"""
        markup = insertion_tool._generate_table_markup(
            sample_table_data, "Test Table", TableStyle.SIMPLE, True
        )
        
        assert isinstance(markup, str)
        assert "Test Table" in markup
        assert "John Doe" in markup
        assert "Jane Smith" in markup
    
    def test_generate_image_markup(self, insertion_tool):
        """Test image markup generation"""
        markup = insertion_tool._generate_image_markup(
            "test_image.png", "Test Image", "Test alt", ImageAlignment.CENTER
        )
        
        assert isinstance(markup, str)
        assert "Test Image" in markup
        assert "test_image.png" in markup
        assert "Test alt" in markup
    
    def test_generate_media_markup(self, insertion_tool):
        """Test media markup generation"""
        markup = insertion_tool._generate_media_markup(
            "test_video.mp4", ContentType.VIDEO, "Test Video", "Test description"
        )
        
        assert isinstance(markup, str)
        assert "Test Video" in markup
        assert "test_video.mp4" in markup
        assert "Test description" in markup
    
    def test_generate_citation_markup(self, insertion_tool):
        """Test citation markup generation"""
        citation_data = {
            "author": "Smith, J.",
            "title": "Research Paper",
            "year": "2024"
        }
        
        markup = insertion_tool._generate_citation_markup(citation_data, "apa")
        
        assert isinstance(markup, str)
        assert "Smith, J." in markup
        assert "Research Paper" in markup
        assert "2024" in markup
    
    def test_process_content_for_insertion(self, insertion_tool, temp_dir):
        """Test content processing for insertion"""
        doc_path = str(temp_dir / "process_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\n## Section 1\n\nContent here.\n\n## Section 2\n\nMore content.\n")
        
        content = "New content to insert"
        position = InsertionPosition.AFTER_HEADING
        heading_text = "Section 1"
        
        result = insertion_tool._process_content_for_insertion(
            doc_path, content, position, heading_text
        )
        
        assert isinstance(result, str)
        assert "New content to insert" in result
        assert "Section 1" in result
    
    def test_detect_document_format(self, insertion_tool, temp_dir):
        """Test document format detection"""
        # Test different file extensions
        formats_to_test = [
            ("test.md", "markdown"),
            ("test.html", "html"),
            ("test.txt", "plain_text"),
            ("test.json", "json"),
            ("test.xml", "xml")
        ]
        
        for filename, expected_format in formats_to_test:
            file_path = temp_dir / filename
            with open(file_path, 'w') as f:
                f.write("Test content")
            
            detected_format = insertion_tool._detect_document_format(str(file_path))
            assert detected_format == expected_format
    
    def test_generate_content_reference(self, insertion_tool):
        """Test content reference generation"""
        reference = insertion_tool._generate_content_reference(
            "chart", "Test Chart", "chart_001"
        )
        
        assert isinstance(reference, dict)
        assert reference["type"] == "chart"
        assert reference["title"] == "Test Chart"
        assert reference["id"] == "chart_001"
        assert "created_at" in reference
    
    def test_resize_image_if_needed(self, insertion_tool, temp_dir):
        """Test image resizing functionality"""
        # Create a dummy image file
        image_path = str(temp_dir / "resize_test.png")
        with open(image_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
        
        result_path = insertion_tool._resize_image_if_needed(
            image_path, max_size=(800, 600)
        )
        
        assert os.path.exists(result_path)
        assert result_path != image_path  # Should create a new file if resized
    
    def test_generate_thumbnail(self, insertion_tool, temp_dir):
        """Test thumbnail generation functionality"""
        # Create a dummy image file
        image_path = str(temp_dir / "thumbnail_test.png")
        with open(image_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
        
        thumbnail_path = insertion_tool._generate_thumbnail(image_path, size=(150, 150))
        
        assert os.path.exists(thumbnail_path)
        assert thumbnail_path != image_path
        assert "thumbnail" in thumbnail_path


class TestErrorHandling:
    """Test suite for error handling"""
    
    @pytest.fixture
    def insertion_tool(self):
        return ContentInsertionTool()
    
    def test_content_insertion_error(self, insertion_tool):
        """Test ContentInsertionError handling"""
        with pytest.raises(ContentInsertionError):
            raise ContentInsertionError("Test insertion error")
    
    def test_chart_error(self, insertion_tool):
        """Test ChartError handling"""
        with pytest.raises(ChartError):
            raise ChartError("Test chart error")
    
    def test_table_error(self, insertion_tool):
        """Test TableError handling"""
        with pytest.raises(TableError):
            raise TableError("Test table error")
    
    def test_image_error(self, insertion_tool):
        """Test ImageError handling"""
        with pytest.raises(ImageError):
            raise ImageError("Test image error")
    
    def test_media_error(self, insertion_tool):
        """Test MediaError handling"""
        with pytest.raises(MediaError):
            raise MediaError("Test media error")
    
    def test_error_inheritance(self, insertion_tool):
        """Test that specific errors inherit from base error"""
        assert issubclass(ChartError, ContentInsertionError)
        assert issubclass(TableError, ContentInsertionError)
        assert issubclass(ImageError, ContentInsertionError)
        assert issubclass(MediaError, ContentInsertionError)
    
    def test_error_handling_in_operations(self, insertion_tool, temp_dir):
        """Test error handling in content insertion operations"""
        doc_path = str(temp_dir / "error_test.md")
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n")
        
        # Test with invalid chart data
        with pytest.raises(ChartError):
            insertion_tool.insert_chart(
                document_path=doc_path,
                chart_type=ChartType.BAR,
                chart_data={"invalid": "data"},
                chart_title="Invalid Chart",
                position=InsertionPosition.END
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])



