import os
import logging
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from dataclasses import field

from pydantic import (
    BaseModel,
    ValidationError,
    field_validator,
    Field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from PIL import Image, ExifTags, ImageFilter
from queue import Queue

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool

# Module-level default configuration for validators
_DEFAULT_MAX_FILE_SIZE_MB = 50
_DEFAULT_ALLOWED_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tiff",
    ".gif",
]

# Exceptions


class ImageToolError(Exception):
    """Base exception for ImageTool errors."""


class FileOperationError(ImageToolError):
    """Raised when file operations fail."""


class SecurityError(ImageToolError):
    """Raised for security-related issues."""


# Base schema for common fields


class BaseFileSchema(BaseModel):
    file_path: str
    _mtime: Optional[float] = None  # Internal use for cache

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file path for existence, size, and extension."""
        abs_path = os.path.abspath(os.path.normpath(v))
        ext = os.path.splitext(abs_path)[1].lower()
        if ext not in _DEFAULT_ALLOWED_EXTENSIONS:
            raise SecurityError(f"Extension '{ext}' not allowed, expected {_DEFAULT_ALLOWED_EXTENSIONS}")
        if not os.path.isfile(abs_path):
            raise FileOperationError(f"File not found: {abs_path}")
        size_mb = os.path.getsize(abs_path) / (1024 * 1024)
        if size_mb > _DEFAULT_MAX_FILE_SIZE_MB:
            raise FileOperationError(f"File too large: {size_mb:.1f}MB, max {_DEFAULT_MAX_FILE_SIZE_MB}MB")
        return abs_path


# Schemas for operations


class LoadSchema(BaseFileSchema):
    """Schema for load operation."""


class OCRSchema(BaseFileSchema):
    """Schema for OCR operation."""

    lang: Optional[str] = None


class MetadataSchema(BaseFileSchema):
    """Schema for metadata extraction operation."""

    include_exif: bool = False


class ResizeSchema(BaseFileSchema):
    """Schema for resize operation."""

    output_path: str
    width: int
    height: int

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, v: str) -> str:
        """Validate output path for existence and extension."""
        abs_path = os.path.abspath(os.path.normpath(v))
        ext = os.path.splitext(abs_path)[1].lower()
        if ext not in _DEFAULT_ALLOWED_EXTENSIONS:
            raise SecurityError(f"Output extension '{ext}' not allowed, expected {_DEFAULT_ALLOWED_EXTENSIONS}")
        if os.path.exists(abs_path):
            raise FileOperationError(f"Output file already exists: {abs_path}")
        return abs_path


class FilterSchema(BaseFileSchema):
    """Schema for filter operation."""

    output_path: str
    filter_type: str = "blur"

    @field_validator("filter_type")
    @classmethod
    def validate_filter_type(cls, v: str) -> str:
        """Validate filter type."""
        valid_filters = ["blur", "sharpen", "edge_enhance"]
        if v not in valid_filters:
            raise ValueError(f"Invalid filter_type '{v}', expected {valid_filters}")
        return v

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, v: str) -> str:
        """Validate output path for existence and extension."""
        abs_path = os.path.abspath(os.path.normpath(v))
        ext = os.path.splitext(abs_path)[1].lower()
        if ext not in _DEFAULT_ALLOWED_EXTENSIONS:
            raise SecurityError(f"Output extension '{ext}' not allowed, expected {_DEFAULT_ALLOWED_EXTENSIONS}")
        if os.path.exists(abs_path):
            raise FileOperationError(f"Output file already exists: {abs_path}")
        return abs_path


# Tesseract process manager


@dataclass
class TesseractManager:
    """Manages a pool of Tesseract processes for OCR."""

    pool_size: int
    processes: List[subprocess.Popen] = field(default_factory=list)
    queue: Queue = field(default_factory=lambda: Queue())

    def initialize(self):
        """Initialize Tesseract process pool."""
        for _ in range(self.pool_size):
            try:
                proc = subprocess.Popen(
                    ["tesseract", "--oem", "1", "-", "stdout", "-l", "eng"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self.queue.put(proc)
                self.processes.append(proc)
            except FileNotFoundError:
                logging.getLogger(__name__).warning("Tesseract not found; OCR will be disabled")
                break

    def get_process(self) -> Optional[subprocess.Popen]:
        """Get an available Tesseract process."""
        if self.queue.empty():
            return None
        return self.queue.get()

    def return_process(self, proc: subprocess.Popen):
        """Return a Tesseract process to the pool."""
        self.queue.put(proc)

    def cleanup(self):
        """Clean up all Tesseract processes."""
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except (subprocess.TimeoutExpired, OSError) as e:
                logging.getLogger(__name__).warning(f"Error terminating Tesseract process: {e}")


@register_tool("image")
class ImageTool(BaseTool):
    """
    Image processing tool supporting:
      - load: Load image and return size and mode.
      - ocr: Extract text using a pooled Tesseract process.
      - metadata: Retrieve EXIF and basic image info.
      - resize: Resize image to specified dimensions.
      - filter: Apply filters (blur, sharpen, edge_enhance).

    Inherits from BaseTool to leverage ToolExecutor for caching, concurrency, and error handling.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the image tool
        
        Automatically reads from environment variables with IMAGE_TOOL_ prefix.
        Example: IMAGE_TOOL_MAX_FILE_SIZE_MB -> max_file_size_mb
        """

        model_config = SettingsConfigDict(env_prefix="IMAGE_TOOL_")

        max_file_size_mb: int = Field(default=50, description="Maximum file size in megabytes")
        allowed_extensions: List[str] = Field(
            default=[".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"],
            description="Allowed image file extensions",
        )
        tesseract_pool_size: int = Field(default=2, description="Number of Tesseract processes for OCR")

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize ImageTool with configuration and resources.

        Args:
            config (Dict, optional): Configuration overrides for ImageTool.
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Raises:
            ValueError: If config contains invalid settings.

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/image.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Initialize Tesseract manager
        self._tesseract_manager = TesseractManager(self.config.tesseract_pool_size)
        self._tesseract_manager.initialize()

    def __del__(self):
        """Clean up Tesseract processes on destruction."""
        self._tesseract_manager.cleanup()

    def update_config(self, config: Dict) -> None:
        """
        Update configuration settings dynamically.

        Args:
            config (Dict): New settings to apply.

        Raises:
            ValueError: If config contains invalid settings.
        """
        try:
            self.config = self.Config(**{**self.config.model_dump(), **config})
            # Reinitialize Tesseract if pool size changes
            if "tesseract_pool_size" in config:
                self._tesseract_manager.cleanup()
                self._tesseract_manager = TesseractManager(self.config.tesseract_pool_size)
                self._tesseract_manager.initialize()
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {e}")

    def load(self, file_path: str) -> Dict[str, Any]:
        """
        Load an image and return its size and mode.

        Args:
            file_path (str): Path to the image file.

        Returns:
            Dict[str, Any]: Image info {'size': (width, height), 'mode': str}.

        Raises:
            FileOperationError: If file is invalid or inaccessible.
        """
        # Validate input using schema
        validated_input = LoadSchema(file_path=file_path)

        try:
            with Image.open(validated_input.file_path) as img:
                img.load()
                return {"size": img.size, "mode": img.mode}
        except Exception as e:
            raise FileOperationError(f"load: Failed to load image '{file_path}': {e}")

    def ocr(self, file_path: str, lang: Optional[str] = None) -> str:
        """
        Extract text from an image using a pooled Tesseract process.

        Args:
            file_path (str): Path to the image file.
            lang (Optional[str]): Language code for OCR (e.g., 'eng').

        Returns:
            str: Extracted text.

        Raises:
            FileOperationError: If OCR fails or Tesseract is unavailable.
        """
        # Validate input using schema
        validated_input = OCRSchema(file_path=file_path, lang=lang)

        proc = self._tesseract_manager.get_process()
        if not proc:
            raise FileOperationError(f"ocr: No Tesseract processes available (lang: {lang or 'eng'})")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = temp_file.name
        try:
            img = Image.open(validated_input.file_path).convert("L").filter(ImageFilter.SHARPEN)
            img.save(temp_path)
            stdout, stderr = proc.communicate(input=temp_path, timeout=30)
            if proc.returncode != 0:
                raise FileOperationError(f"ocr: Tesseract failed for '{file_path}' (lang: {lang or 'eng'}): {stderr}")
            return stdout.strip()
        except Exception as e:
            raise FileOperationError(f"ocr: Failed to process '{file_path}' (lang: {lang or 'eng'}): {e}")
        finally:
            self._tesseract_manager.return_process(proc)
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    self.logger.warning(f"Failed to remove temporary file {temp_path}: {e}")

    def metadata(self, file_path: str, include_exif: bool = False) -> Dict[str, Any]:
        """
        Retrieve metadata (size, mode, EXIF) from an image.

        Args:
            file_path (str): Path to the image file.
            include_exif (bool): Whether to include EXIF data.

        Returns:
            Dict[str, Any]: Image metadata {'size': tuple, 'mode': str, 'exif': Dict}.

        Raises:
            FileOperationError: If metadata extraction fails.
        """
        # Validate input using schema
        validated_input = MetadataSchema(file_path=file_path, include_exif=include_exif)

        try:
            with Image.open(validated_input.file_path) as img:
                img.load()
                info = {"size": img.size, "mode": img.mode}
                if include_exif:
                    exif = {}
                    raw = img._getexif() or {}
                    for tag, val in raw.items():
                        decoded = ExifTags.TAGS.get(tag, tag)
                        exif[decoded] = val
                    info["exif"] = exif
                return info
        except Exception as e:
            raise FileOperationError(f"metadata: Failed to process '{file_path}': {e}")

    def resize(self, file_path: str, output_path: str, width: int, height: int) -> Dict[str, Any]:
        """
        Resize an image to specified dimensions and save to output path.

        Args:
            file_path (str): Path to the image file.
            output_path (str): Path to save the resized image.
            width (int): Target width.
            height (int): Target height.

        Returns:
            Dict[str, Any]: Status with output path {'success': bool, 'output_path': str}.

        Raises:
            FileOperationError: If resizing fails.
        """
        # Validate input using schema
        validated_input = ResizeSchema(
            file_path=file_path,
            output_path=output_path,
            width=width,
            height=height,
        )

        try:
            with Image.open(validated_input.file_path) as img:
                img = img.resize((width, height), Image.Resampling.LANCZOS)
                img.save(validated_input.output_path)
            return {
                "success": True,
                "output_path": validated_input.output_path,
            }
        except Exception as e:
            raise FileOperationError(f"resize: Failed to process '{file_path}' (output_path: {output_path}): {e}")

    def filter(self, file_path: str, output_path: str, filter_type: str) -> Dict[str, Any]:
        """
        Apply a filter (blur, sharpen, edge_enhance) to an image and save to output path.

        Args:
            file_path (str): Path to the image file.
            output_path (str): Path to save the filtered image.
            filter_type (str): Filter type ('blur', 'sharpen', 'edge_enhance').

        Returns:
            Dict[str, Any]: Status with output path {'success': bool, 'output_path': str}.

        Raises:
            FileOperationError: If filtering fails.
        """
        # Validate input using schema
        validated_input = FilterSchema(
            file_path=file_path,
            output_path=output_path,
            filter_type=filter_type,
        )

        try:
            filter_map = {
                "blur": ImageFilter.BLUR,
                "sharpen": ImageFilter.SHARPEN,
                "edge_enhance": ImageFilter.EDGE_ENHANCE,
            }
            with Image.open(validated_input.file_path) as img:
                img = img.filter(filter_map[filter_type])
                img.save(validated_input.output_path)
            return {
                "success": True,
                "output_path": validated_input.output_path,
            }
        except Exception as e:
            raise FileOperationError(f"filter: Failed to process '{file_path}' (output_path: {output_path}, filter_type: {filter_type}): {e}")
