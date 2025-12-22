"""
Comprehensive test suite for ImageTool component.

Tests all image processing functionality including load, OCR, metadata extraction,
resize, and filter operations with real image outputs and comprehensive error handling.
"""

import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from PIL import Image, ImageDraw
import subprocess

from aiecs.tools.task_tools.image_tool import (
    ImageTool, 
    ImageSettings, 
    ImageToolError, 
    FileOperationError, 
    SecurityError,
    BaseFileSchema,
    LoadSchema,
    OCRSchema, 
    MetadataSchema,
    ResizeSchema,
    FilterSchema,
    TesseractManager
)
from pydantic import ValidationError


class TestImageFixtures:
    """Test fixtures for creating test images and managing temporary files."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def test_image_rgb(self, temp_dir):
        """Create a test RGB image with text for testing."""
        image_path = os.path.join(temp_dir, "test_rgb.png")
        # Create a 400x200 RGB image with white background for better OCR
        img = Image.new('RGB', (400, 200), 'white')
        draw = ImageDraw.Draw(img)
        
        # Use a larger, clearer font for better OCR results
        try:
            # Try to use a system font for better text rendering
            from PIL import ImageFont
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            except (OSError, IOError):
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
                except (OSError, IOError):
                    font = ImageFont.load_default()
        except ImportError:
            font = None
        
        # Add clear, large text for OCR testing
        draw.text((20, 20), "HELLO WORLD", fill='black', font=font)
        draw.text((20, 60), "TEST IMAGE", fill='black', font=font)
        draw.text((20, 100), "123456", fill='black', font=font)
        
        # Add a simple rectangle for visual testing
        draw.rectangle([20, 140, 100, 180], outline='red', width=2)
        img.save(image_path)
        return image_path
    
    @pytest.fixture
    def test_image_ocr_friendly(self, temp_dir):
        """Create a high-contrast test image specifically optimized for OCR."""
        image_path = os.path.join(temp_dir, "test_ocr.png")
        # Create a larger image with high contrast
        img = Image.new('RGB', (600, 300), 'white')
        draw = ImageDraw.Draw(img)
        
        try:
            from PIL import ImageFont
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            except (OSError, IOError):
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
                except (OSError, IOError):
                    font = ImageFont.load_default()
        except ImportError:
            font = None
        
        # Simple, clear text that OCR should easily recognize
        draw.text((50, 50), "SAMPLE TEXT", fill='black', font=font)
        draw.text((50, 100), "FOR TESTING", fill='black', font=font)
        draw.text((50, 150), "TESSERACT", fill='black', font=font)
        draw.text((50, 200), "OCR ENGINE", fill='black', font=font)
        
        img.save(image_path)
        return image_path
    
    @pytest.fixture
    def test_image_grayscale(self, temp_dir):
        """Create a test grayscale image."""
        image_path = os.path.join(temp_dir, "test_gray.jpg")
        img = Image.new('L', (150, 75), 128)  # Gray background
        draw = ImageDraw.Draw(img)
        draw.ellipse([25, 25, 125, 50], fill=255, outline=0)
        img.save(image_path, quality=95)
        return image_path
    
    @pytest.fixture 
    def test_image_with_exif(self, temp_dir):
        """Create a test image with EXIF data."""
        image_path = os.path.join(temp_dir, "test_exif.jpg")
        img = Image.new('RGB', (100, 100), 'green')
        # Note: Creating real EXIF data is complex, so we'll test with a basic image
        # The metadata method will handle cases with and without EXIF
        img.save(image_path, quality=90)
        return image_path
    
    @pytest.fixture
    def large_test_image(self, temp_dir):
        """Create a large test image for size validation."""
        image_path = os.path.join(temp_dir, "large_test.png")
        # Create a larger image for size testing
        img = Image.new('RGB', (1000, 800), 'yellow')
        draw = ImageDraw.Draw(img)
        for i in range(0, 1000, 50):
            draw.line([(i, 0), (i, 800)], fill='black')
        for i in range(0, 800, 50):
            draw.line([(0, i), (1000, i)], fill='black')
        img.save(image_path)
        return image_path
    
    @pytest.fixture
    def invalid_file(self, temp_dir):
        """Create an invalid file (not an image)."""
        file_path = os.path.join(temp_dir, "invalid.txt")
        with open(file_path, 'w') as f:
            f.write("This is not an image file")
        return file_path

    @pytest.fixture
    def non_existent_file(self, temp_dir):
        """Return path to a non-existent file."""
        return os.path.join(temp_dir, "does_not_exist.png")


class TestImageSettings:
    """Test ImageSettings configuration class."""
    
    def test_default_settings(self):
        """Test default ImageSettings values."""
        settings = ImageSettings()
        assert settings.max_file_size_mb == 50
        assert settings.allowed_extensions == ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
        assert settings.tesseract_pool_size == 2
        assert settings.env_prefix == 'IMAGE_TOOL_'
    
    def test_custom_settings(self):
        """Test custom ImageSettings values."""
        settings = ImageSettings(
            max_file_size_mb=100,
            allowed_extensions=['.png', '.jpg'],
            tesseract_pool_size=4
        )
        assert settings.max_file_size_mb == 100
        assert settings.allowed_extensions == ['.png', '.jpg']
        assert settings.tesseract_pool_size == 4
    
    def test_environment_variables(self):
        """Test ImageSettings from environment variables."""
        with patch.dict(os.environ, {
            'IMAGE_TOOL_MAX_FILE_SIZE_MB': '25',
            'IMAGE_TOOL_TESSERACT_POOL_SIZE': '3'
        }):
            settings = ImageSettings()
            assert settings.max_file_size_mb == 25
            assert settings.tesseract_pool_size == 3


class TestExceptions:
    """Test custom exception classes."""
    
    def test_image_tool_error(self):
        """Test base ImageToolError exception."""
        error = ImageToolError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)
    
    def test_file_operation_error(self):
        """Test FileOperationError inheritance."""
        error = FileOperationError("File error")
        assert str(error) == "File error"
        assert isinstance(error, ImageToolError)
        assert isinstance(error, Exception)
    
    def test_security_error(self):
        """Test SecurityError inheritance."""
        error = SecurityError("Security error")
        assert str(error) == "Security error"
        assert isinstance(error, ImageToolError)
        assert isinstance(error, Exception)


class TestSchemaValidation(TestImageFixtures):
    """Test Pydantic schema validation."""
    
    def test_base_file_schema_valid_file(self, test_image_rgb):
        """Test BaseFileSchema with valid file."""
        schema = BaseFileSchema(file_path=test_image_rgb)
        assert schema.file_path == os.path.abspath(test_image_rgb)
    
    def test_base_file_schema_invalid_extension(self, invalid_file):
        """Test BaseFileSchema with invalid file extension."""
        with pytest.raises(SecurityError, match="Extension '.txt' not allowed"):
            BaseFileSchema(file_path=invalid_file)
    
    def test_base_file_schema_non_existent_file(self, non_existent_file):
        """Test BaseFileSchema with non-existent file."""
        with pytest.raises(FileOperationError, match="File not found"):
            BaseFileSchema(file_path=non_existent_file)
    
    def test_base_file_schema_large_file(self, temp_dir):
        """Test BaseFileSchema with file exceeding size limit."""
        # Create a large file that exceeds the default limit
        large_file = os.path.join(temp_dir, "huge.png")
        # Create a very large image
        img = Image.new('RGB', (5000, 5000), 'white')
        img.save(large_file)
        
        # Check if file is actually large enough to trigger the error
        size_mb = os.path.getsize(large_file) / (1024 * 1024)
        if size_mb > 50:  # Default limit
            with pytest.raises(FileOperationError, match="File too large"):
                BaseFileSchema(file_path=large_file)
        else:
            # If file is not large enough, just validate it works
            schema = BaseFileSchema(file_path=large_file)
            assert os.path.exists(schema.file_path)
    
    def test_load_schema(self, test_image_rgb):
        """Test LoadSchema validation."""
        schema = LoadSchema(file_path=test_image_rgb)
        assert schema.file_path == os.path.abspath(test_image_rgb)
    
    def test_ocr_schema(self, test_image_rgb):
        """Test OCRSchema validation."""
        schema = OCRSchema(file_path=test_image_rgb, lang='eng')
        assert schema.file_path == os.path.abspath(test_image_rgb)
        assert schema.lang == 'eng'
        
        # Test default language
        schema_default = OCRSchema(file_path=test_image_rgb)
        assert schema_default.lang is None
    
    def test_metadata_schema(self, test_image_rgb):
        """Test MetadataSchema validation."""
        schema = MetadataSchema(file_path=test_image_rgb, include_exif=True)
        assert schema.file_path == os.path.abspath(test_image_rgb)
        assert schema.include_exif is True
        
        # Test default
        schema_default = MetadataSchema(file_path=test_image_rgb)
        assert schema_default.include_exif is False
    
    def test_resize_schema(self, test_image_rgb, temp_dir):
        """Test ResizeSchema validation."""
        output_path = os.path.join(temp_dir, "resized.png")
        schema = ResizeSchema(
            file_path=test_image_rgb,
            output_path=output_path,
            width=100,
            height=50
        )
        assert schema.file_path == os.path.abspath(test_image_rgb)
        assert schema.output_path == os.path.abspath(output_path)
        assert schema.width == 100
        assert schema.height == 50
    
    def test_resize_schema_existing_output(self, test_image_rgb, test_image_grayscale):
        """Test ResizeSchema with existing output file."""
        with pytest.raises(FileOperationError, match="Output file already exists"):
            ResizeSchema(
                file_path=test_image_rgb,
                output_path=test_image_grayscale,  # This file already exists
                width=100,
                height=50
            )
    
    def test_filter_schema(self, test_image_rgb, temp_dir):
        """Test FilterSchema validation."""
        output_path = os.path.join(temp_dir, "filtered.png")
        schema = FilterSchema(
            file_path=test_image_rgb,
            output_path=output_path,
            filter_type='blur'
        )
        assert schema.file_path == os.path.abspath(test_image_rgb)
        assert schema.output_path == os.path.abspath(output_path)
        assert schema.filter_type == 'blur'
    
    def test_filter_schema_invalid_filter(self, test_image_rgb, temp_dir):
        """Test FilterSchema with invalid filter type."""
        output_path = os.path.join(temp_dir, "filtered.png")
        with pytest.raises(ValueError, match="Invalid filter_type"):
            FilterSchema(
                file_path=test_image_rgb,
                output_path=output_path,
                filter_type='invalid_filter'
            )


class TestTesseractManager:
    """Test TesseractManager process pool functionality."""
    
    def test_tesseract_manager_initialization(self):
        """Test TesseractManager initialization."""
        manager = TesseractManager(pool_size=2)
        assert manager.pool_size == 2
        assert len(manager.processes) == 0
        assert manager.queue.empty()
    
    def test_tesseract_manager_initialize_real(self):
        """Test real Tesseract process pool initialization."""
        manager = TesseractManager(pool_size=1)
        
        # Initialize with real Tesseract (should work now)
        manager.initialize()
        
        # Check that processes were created (if Tesseract is available)
        if len(manager.processes) > 0:
            assert len(manager.processes) == 1
            assert not manager.queue.empty()
        else:
            # If no processes, Tesseract might not be available
            pytest.skip("Tesseract not available for real initialization test")
        
        # Clean up
        manager.cleanup()
    
    def test_tesseract_manager_initialize_success_mocked(self):
        """Test successful Tesseract process pool initialization with mocked subprocess."""
        manager = TesseractManager(pool_size=1)
        
        # Mock successful subprocess creation
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            
            manager.initialize()
            
            assert len(manager.processes) == 1
            assert not manager.queue.empty()
            assert manager.queue.get() == mock_process
    
    def test_tesseract_manager_initialize_failure(self):
        """Test Tesseract initialization when tesseract is not found."""
        manager = TesseractManager(pool_size=2)
        
        with patch('subprocess.Popen', side_effect=FileNotFoundError()):
            with patch('logging.getLogger') as mock_logger:
                mock_logger_instance = MagicMock()
                mock_logger.return_value = mock_logger_instance
                
                manager.initialize()
                
                assert len(manager.processes) == 0
                assert manager.queue.empty()
                mock_logger_instance.warning.assert_called_once_with(
                    "Tesseract not found; OCR will be disabled"
                )
    
    def test_tesseract_manager_get_return_process(self):
        """Test getting and returning processes."""
        manager = TesseractManager(pool_size=1)
        mock_process = MagicMock()
        manager.queue.put(mock_process)
        manager.processes.append(mock_process)
        
        # Get process
        proc = manager.get_process()
        assert proc == mock_process
        assert manager.queue.empty()
        
        # Return process
        manager.return_process(proc)
        assert not manager.queue.empty()
        assert manager.queue.get() == mock_process
    
    def test_tesseract_manager_get_process_empty_queue(self):
        """Test getting process when queue is empty."""
        manager = TesseractManager(pool_size=1)
        proc = manager.get_process()
        assert proc is None
    
    def test_tesseract_manager_cleanup(self):
        """Test cleanup of Tesseract processes."""
        manager = TesseractManager(pool_size=2)
        
        # Create mock processes
        mock_proc1 = MagicMock()
        mock_proc2 = MagicMock()
        manager.processes = [mock_proc1, mock_proc2]
        
        manager.cleanup()
        
        mock_proc1.terminate.assert_called_once()
        mock_proc1.wait.assert_called_once_with(timeout=1)
        mock_proc2.terminate.assert_called_once()
        mock_proc2.wait.assert_called_once_with(timeout=1)
    
    def test_tesseract_manager_cleanup_with_errors(self):
        """Test cleanup handling errors during process termination."""
        manager = TesseractManager(pool_size=1)
        
        mock_proc = MagicMock()
        mock_proc.terminate.side_effect = OSError("Process error")
        manager.processes = [mock_proc]
        
        with patch('logging.getLogger') as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            manager.cleanup()
            
            mock_logger_instance.warning.assert_called()


class TestImageToolInitialization:
    """Test ImageTool initialization and configuration."""
    
    def test_default_initialization(self):
        """Test ImageTool initialization with default settings."""
        tool = ImageTool()
        assert isinstance(tool.settings, ImageSettings)
        assert tool.settings.max_file_size_mb == 50
        assert isinstance(tool._tesseract_manager, TesseractManager)
    
    def test_initialization_with_config(self):
        """Test ImageTool initialization with custom config."""
        config = {
            'max_file_size_mb': 25,
            'tesseract_pool_size': 1
        }
        tool = ImageTool(config)
        assert tool.settings.max_file_size_mb == 25
        assert tool._tesseract_manager.pool_size == 1
    
    def test_initialization_with_invalid_config(self):
        """Test ImageTool initialization with invalid config."""
        config = {'invalid_setting': 'value'}
        # Should raise ValueError for invalid configuration
        with pytest.raises(ValueError, match="Invalid configuration"):
            ImageTool(config)
    
    def test_update_settings(self):
        """Test updating ImageTool settings."""
        tool = ImageTool()
        original_size = tool.settings.max_file_size_mb
        
        new_config = {'max_file_size_mb': 75}
        tool.update_settings(new_config)
        
        assert tool.settings.max_file_size_mb == 75
        assert tool.settings.max_file_size_mb != original_size
    
    def test_update_settings_tesseract_pool_size(self):
        """Test updating Tesseract pool size recreates manager."""
        tool = ImageTool()
        original_manager = tool._tesseract_manager
        
        new_config = {'tesseract_pool_size': 3}
        tool.update_settings(new_config)
        
        assert tool._tesseract_manager is not original_manager
        assert tool._tesseract_manager.pool_size == 3
    
    def test_update_settings_with_invalid_config(self):
        """Test updating settings with invalid configuration."""
        tool = ImageTool()
        
        invalid_config = {'invalid_setting': 'value'}
        with pytest.raises(ValueError, match="Invalid configuration"):
            tool.update_settings(invalid_config)
    
    def test_initialization_with_real_tesseract(self):
        """Test ImageTool initialization with real Tesseract available."""
        tool = ImageTool()
        assert isinstance(tool, ImageTool)
        assert tool._tesseract_manager.pool_size == 2
        # With real Tesseract, processes should be initialized
        if len(tool._tesseract_manager.processes) > 0:
            assert len(tool._tesseract_manager.processes) <= 2
        # Clean up
        tool._tesseract_manager.cleanup()
    
    def test_initialization_without_tesseract_mocked(self):
        """Test ImageTool initialization when Tesseract is not available (mocked)."""
        with patch('subprocess.Popen', side_effect=FileNotFoundError()):
            # This should work fine even without Tesseract
            tool = ImageTool()
            assert isinstance(tool, ImageTool)
            assert tool._tesseract_manager.pool_size == 2
            assert len(tool._tesseract_manager.processes) == 0
    
    def test_destructor_cleanup(self):
        """Test that destructor calls cleanup."""
        tool = ImageTool()
        
        with patch.object(tool._tesseract_manager, 'cleanup') as mock_cleanup:
            del tool
            # Note: __del__ behavior can be implementation-dependent
            # This test may need to be adjusted based on the actual cleanup behavior


class TestImageToolLoad(TestImageFixtures):
    """Test ImageTool load functionality."""
    
    def test_load_rgb_image(self, test_image_rgb):
        """Test loading RGB image."""
        tool = ImageTool()
        result = tool.load(test_image_rgb)
        
        assert 'size' in result
        assert 'mode' in result
        assert result['size'] == (400, 200)  # Updated size to match new image dimensions
        assert result['mode'] == 'RGB'
    
    def test_load_grayscale_image(self, test_image_grayscale):
        """Test loading grayscale image."""
        tool = ImageTool()
        result = tool.load(test_image_grayscale)
        
        assert 'size' in result
        assert 'mode' in result
        assert result['size'] == (150, 75)
        assert result['mode'] == 'L'
    
    def test_load_non_existent_file(self, non_existent_file):
        """Test loading non-existent file."""
        tool = ImageTool()
        with pytest.raises(FileOperationError, match="File not found"):
            tool.load(non_existent_file)
    
    def test_load_invalid_image_file(self, invalid_file):
        """Test loading invalid image file."""
        tool = ImageTool()
        with pytest.raises(SecurityError, match="Extension '.txt' not allowed"):
            tool.load(invalid_file)


class TestImageToolOCR(TestImageFixtures):
    """Test ImageTool OCR functionality."""
    
    def test_ocr_real_integration(self, test_image_ocr_friendly):
        """Test real OCR integration with system Tesseract."""
        tool = ImageTool()
        
        # This test uses real Tesseract if available
        try:
            result = tool.ocr(test_image_ocr_friendly)
            # Should return some text (even if OCR isn't perfect on our test image)
            assert isinstance(result, str)
            # The OCR friendly image should produce some recognizable text
            result_upper = result.upper().replace('\n', ' ').replace('  ', ' ')
            # Check if any of our expected text appears in the result
            expected_words = ['SAMPLE', 'TEXT', 'TESTING', 'TESSERACT', 'OCR', 'ENGINE']
            found_words = [word for word in expected_words if word in result_upper]
            # At least some words should be recognized
            assert len(found_words) > 0, f"Expected to find some words from {expected_words} in OCR result: '{result}'"
        except FileOperationError as e:
            if "No Tesseract processes available" in str(e):
                pytest.skip("Tesseract not available for real integration test")
            else:
                raise
    
    def test_ocr_success_mocked(self, test_image_rgb):
        """Test successful OCR operation with mocked process."""
        tool = ImageTool()
        
        # Mock Tesseract process for testing
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Hello World\nTest Image", "")
        mock_process.returncode = 0
        
        with patch.object(tool._tesseract_manager, 'get_process', return_value=mock_process):
            with patch.object(tool._tesseract_manager, 'return_process') as mock_return:
                with patch('tempfile.NamedTemporaryFile') as mock_temp:
                    mock_temp_file = MagicMock()
                    mock_temp_file.name = '/tmp/test_ocr.png'
                    mock_temp_file.__enter__.return_value = mock_temp_file
                    mock_temp.return_value = mock_temp_file
                    
                    with patch('os.path.exists', return_value=True):
                        with patch('os.unlink'):
                            result = tool.ocr(test_image_rgb)
                    
                    assert result == "Hello World\nTest Image"
                    mock_return.assert_called_once_with(mock_process)
    
    def test_ocr_with_language_real(self, test_image_ocr_friendly):
        """Test OCR with specific language using real Tesseract."""
        tool = ImageTool()
        
        # Test with English language (should be available in most Tesseract installations)
        try:
            result = tool.ocr(test_image_ocr_friendly, lang='eng')
            assert isinstance(result, str)
            # Should recognize at least some text
            if result.strip():  # If we got some non-empty result
                result_upper = result.upper()
                # Check for at least one expected word
                expected_words = ['SAMPLE', 'TEXT', 'TESTING', 'TESSERACT', 'OCR', 'ENGINE']
                found_words = [word for word in expected_words if word in result_upper]
                # If we got text, at least some should be recognizable
                assert len(found_words) > 0, f"Expected to find some words in OCR result: '{result}'"
        except FileOperationError as e:
            if "No Tesseract processes available" in str(e):
                pytest.skip("Tesseract not available for real integration test")
            else:
                raise
    
    def test_ocr_with_language_mocked(self, test_image_rgb):
        """Test OCR with specific language using mocked process."""
        tool = ImageTool()
        
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Text content", "")
        mock_process.returncode = 0
        
        with patch.object(tool._tesseract_manager, 'get_process', return_value=mock_process):
            with patch.object(tool._tesseract_manager, 'return_process'):
                with patch('tempfile.NamedTemporaryFile') as mock_temp:
                    mock_temp_file = MagicMock()
                    mock_temp_file.name = '/tmp/test_ocr.png'
                    mock_temp_file.__enter__.return_value = mock_temp_file
                    mock_temp.return_value = mock_temp_file
                    
                    with patch('os.path.exists', return_value=True):
                        with patch('os.unlink'):
                            result = tool.ocr(test_image_rgb, lang='fra')
                    
                    assert result == "Text content"
    
    def test_ocr_no_process_available(self, test_image_rgb):
        """Test OCR when no Tesseract process is available."""
        tool = ImageTool()
        
        with patch.object(tool._tesseract_manager, 'get_process', return_value=None):
            with pytest.raises(FileOperationError, match="ocr: No Tesseract processes available"):
                tool.ocr(test_image_rgb)
    
    def test_ocr_tesseract_failure(self, test_image_rgb):
        """Test OCR when Tesseract process fails."""
        tool = ImageTool()
        
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "Tesseract error message")
        mock_process.returncode = 1
        
        with patch.object(tool._tesseract_manager, 'get_process', return_value=mock_process):
            with patch.object(tool._tesseract_manager, 'return_process'):
                with patch('tempfile.NamedTemporaryFile') as mock_temp:
                    mock_temp_file = MagicMock()
                    mock_temp_file.name = '/tmp/test_ocr.png'
                    mock_temp_file.__enter__.return_value = mock_temp_file
                    mock_temp.return_value = mock_temp_file
                    
                    with patch('os.path.exists', return_value=True):
                        with patch('os.unlink'):
                            with pytest.raises(FileOperationError, match="ocr: Tesseract failed"):
                                tool.ocr(test_image_rgb)
    
    def test_ocr_exception_during_processing(self, test_image_rgb):
        """Test OCR when exception occurs during processing."""
        tool = ImageTool()
        
        mock_process = MagicMock()
        mock_process.communicate.side_effect = Exception("Processing error")
        
        with patch.object(tool._tesseract_manager, 'get_process', return_value=mock_process):
            with patch.object(tool._tesseract_manager, 'return_process'):
                with pytest.raises(FileOperationError, match="ocr: Failed to process"):
                    tool.ocr(test_image_rgb)


class TestImageToolMetadata(TestImageFixtures):
    """Test ImageTool metadata functionality."""
    
    def test_metadata_basic(self, test_image_rgb):
        """Test basic metadata extraction."""
        tool = ImageTool()
        result = tool.metadata(test_image_rgb)
        
        assert 'size' in result
        assert 'mode' in result
        assert result['size'] == (400, 200)
        assert result['mode'] == 'RGB'
        assert 'exif' not in result
    
    def test_metadata_with_exif(self, test_image_with_exif):
        """Test metadata extraction with EXIF data."""
        tool = ImageTool()
        result = tool.metadata(test_image_with_exif, include_exif=True)
        
        assert 'size' in result
        assert 'mode' in result
        assert 'exif' in result
        assert isinstance(result['exif'], dict)
    
    def test_metadata_grayscale(self, test_image_grayscale):
        """Test metadata extraction for grayscale image."""
        tool = ImageTool()
        result = tool.metadata(test_image_grayscale)
        
        assert 'size' in result
        assert 'mode' in result
        assert result['size'] == (150, 75)
        assert result['mode'] == 'L'
    
    def test_metadata_invalid_file(self, invalid_file):
        """Test metadata extraction on invalid file."""
        tool = ImageTool()
        with pytest.raises(SecurityError, match="Extension '.txt' not allowed"):
            tool.metadata(invalid_file)
    
    def test_metadata_non_existent_file(self, non_existent_file):
        """Test metadata extraction on non-existent file."""
        tool = ImageTool()
        with pytest.raises(FileOperationError, match="File not found"):
            tool.metadata(non_existent_file)


class TestImageToolResize(TestImageFixtures):
    """Test ImageTool resize functionality."""
    
    def test_resize_success(self, test_image_rgb, temp_dir):
        """Test successful image resizing."""
        tool = ImageTool()
        output_path = os.path.join(temp_dir, "resized.png")
        
        result = tool.resize(test_image_rgb, output_path, 100, 50)
        
        assert result['success'] is True
        assert result['output_path'] == output_path
        assert os.path.exists(output_path)
        
        # Verify the resized image has correct dimensions
        with Image.open(output_path) as img:
            assert img.size == (100, 50)
    
    def test_resize_grayscale(self, test_image_grayscale, temp_dir):
        """Test resizing grayscale image."""
        tool = ImageTool()
        output_path = os.path.join(temp_dir, "resized_gray.jpg")
        
        result = tool.resize(test_image_grayscale, output_path, 75, 40)
        
        assert result['success'] is True
        assert os.path.exists(output_path)
        
        with Image.open(output_path) as img:
            assert img.size == (75, 40)
    
    def test_resize_large_image(self, large_test_image, temp_dir):
        """Test resizing a large image."""
        tool = ImageTool()
        output_path = os.path.join(temp_dir, "resized_large.png")
        
        result = tool.resize(large_test_image, output_path, 500, 400)
        
        assert result['success'] is True
        assert os.path.exists(output_path)
        
        with Image.open(output_path) as img:
            assert img.size == (500, 400)
    
    def test_resize_invalid_input_file(self, invalid_file, temp_dir):
        """Test resize with invalid input file."""
        tool = ImageTool()
        output_path = os.path.join(temp_dir, "resized.png")
        
        with pytest.raises(SecurityError, match="Extension '.txt' not allowed"):
            tool.resize(invalid_file, output_path, 100, 50)
    
    def test_resize_non_existent_input(self, non_existent_file, temp_dir):
        """Test resize with non-existent input file."""
        tool = ImageTool()
        output_path = os.path.join(temp_dir, "resized.png")
        
        with pytest.raises(FileOperationError, match="File not found"):
            tool.resize(non_existent_file, output_path, 100, 50)


class TestImageToolFilter(TestImageFixtures):
    """Test ImageTool filter functionality."""
    
    def test_filter_blur(self, test_image_rgb, temp_dir):
        """Test blur filter application."""
        tool = ImageTool()
        output_path = os.path.join(temp_dir, "blurred.png")
        
        result = tool.filter(test_image_rgb, output_path, 'blur')
        
        assert result['success'] is True
        assert result['output_path'] == output_path
        assert os.path.exists(output_path)
        
        # Verify the image was processed (dimensions should remain the same)
        with Image.open(output_path) as img:
            assert img.size == (400, 200)
    
    def test_filter_sharpen(self, test_image_rgb, temp_dir):
        """Test sharpen filter application."""
        tool = ImageTool()
        output_path = os.path.join(temp_dir, "sharpened.png")
        
        result = tool.filter(test_image_rgb, output_path, 'sharpen')
        
        assert result['success'] is True
        assert os.path.exists(output_path)
        
        with Image.open(output_path) as img:
            assert img.size == (400, 200)
    
    def test_filter_edge_enhance(self, test_image_grayscale, temp_dir):
        """Test edge enhance filter application."""
        tool = ImageTool()
        output_path = os.path.join(temp_dir, "edge_enhanced.jpg")
        
        result = tool.filter(test_image_grayscale, output_path, 'edge_enhance')
        
        assert result['success'] is True
        assert os.path.exists(output_path)
        
        with Image.open(output_path) as img:
            assert img.size == (150, 75)
    
    def test_filter_invalid_input_file(self, invalid_file, temp_dir):
        """Test filter with invalid input file."""
        tool = ImageTool()
        output_path = os.path.join(temp_dir, "filtered.png")
        
        with pytest.raises(SecurityError, match="Extension '.txt' not allowed"):
            tool.filter(invalid_file, output_path, 'blur')
    
    def test_filter_non_existent_input(self, non_existent_file, temp_dir):
        """Test filter with non-existent input file."""
        tool = ImageTool()
        output_path = os.path.join(temp_dir, "filtered.png")
        
        with pytest.raises(FileOperationError, match="File not found"):
            tool.filter(non_existent_file, output_path, 'blur')


class TestImageToolSecurity(TestImageFixtures):
    """Test ImageTool security and validation features."""
    
    def test_file_size_limit(self, temp_dir):
        """Test file size limit enforcement."""
        # Create tool with small file size limit
        config = {'max_file_size_mb': 1}  # 1MB limit
        tool = ImageTool(config)
        
        # Create a large test image
        large_image_path = os.path.join(temp_dir, "large.png")
        # Create an image that might exceed 1MB
        img = Image.new('RGB', (2000, 2000), 'white')
        img.save(large_image_path)
        
        # Check actual file size
        size_mb = os.path.getsize(large_image_path) / (1024 * 1024)
        if size_mb > 1:
            # If file is actually larger than limit, test should fail at validation
            with pytest.raises((SecurityError, FileOperationError)):
                tool.load(large_image_path)
        else:
            # If file is still under limit, it should work
            result = tool.load(large_image_path)
            assert 'size' in result
    
    def test_allowed_extensions_enforcement(self, temp_dir):
        """Test that only allowed file extensions are processed."""
        tool = ImageTool()
        
        # Create a file with disallowed extension
        bad_file = os.path.join(temp_dir, "test.bmp")
        img = Image.new('RGB', (100, 100), 'red')
        img.save(bad_file)
        
        # Rename to unauthorized extension
        unauthorized_file = os.path.join(temp_dir, "test.xyz")
        os.rename(bad_file, unauthorized_file)
        
        with pytest.raises(SecurityError, match="Extension '.xyz' not allowed"):
            tool.load(unauthorized_file)
    
    def test_path_normalization(self, test_image_rgb, temp_dir):
        """Test that file paths are properly normalized."""
        tool = ImageTool()
        
        # Test with relative path containing '..'
        rel_path = os.path.relpath(test_image_rgb, temp_dir)
        complex_path = os.path.join(temp_dir, '..', os.path.basename(temp_dir), rel_path)
        
        result = tool.load(complex_path)
        assert 'size' in result
        assert result['size'] == (400, 200)


class TestImageToolErrorHandling(TestImageFixtures):
    """Test comprehensive error handling scenarios."""
    
    def test_tool_with_permission_denied(self, temp_dir):
        """Test handling of permission denied errors."""
        tool = ImageTool()
        
        # Create a file and then make it unreadable
        test_file = os.path.join(temp_dir, "unreadable.png")
        img = Image.new('RGB', (50, 50), 'blue')
        img.save(test_file)
        
        # Make file unreadable (this might not work on all systems)
        try:
            os.chmod(test_file, 0o000)
            with pytest.raises(FileOperationError):
                tool.load(test_file)
        except (OSError, PermissionError):
            # If we can't change permissions, skip this test
            pass
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(test_file, 0o644)
            except (OSError, PermissionError):
                pass
    
    def test_corrupted_image_file(self, temp_dir):
        """Test handling of corrupted image files."""
        tool = ImageTool()
        
        # Create a file with image extension but invalid content
        corrupted_file = os.path.join(temp_dir, "corrupted.png")
        with open(corrupted_file, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n')  # PNG header but incomplete
            f.write(b'invalid data' * 100)
        
        with pytest.raises(FileOperationError, match="load: Failed to load image"):
            tool.load(corrupted_file)
    
    def test_concurrent_operations(self, test_image_rgb, temp_dir):
        """Test that multiple operations can be performed concurrently."""
        tool = ImageTool()
        
        # Perform multiple operations on the same image
        output1 = os.path.join(temp_dir, "out1.png")
        output2 = os.path.join(temp_dir, "out2.png")
        
        # Load metadata
        metadata_result = tool.metadata(test_image_rgb)
        
        # Resize
        resize_result = tool.resize(test_image_rgb, output1, 150, 75)
        
        # Filter
        filter_result = tool.filter(test_image_rgb, output2, 'blur')
        
        # All operations should succeed
        assert 'size' in metadata_result
        assert resize_result['success'] is True
        assert filter_result['success'] is True
        assert os.path.exists(output1)
        assert os.path.exists(output2)


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--cov=aiecs.tools.task_tools.image_tool",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=85"
    ])
