import os
import re
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
from urllib.parse import urlparse
from pathlib import Path
import tempfile

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class DocumentType(str, Enum):
    """Supported document types for parsing"""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    TXT = "txt"
    HTML = "html"
    RTF = "rtf"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    MARKDOWN = "md"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ParsingStrategy(str, Enum):
    """Document parsing strategies"""

    TEXT_ONLY = "text_only"
    STRUCTURED = "structured"
    FULL_CONTENT = "full_content"
    METADATA_ONLY = "metadata_only"


class OutputFormat(str, Enum):
    """Output formats for parsed content"""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


class DocumentParserError(Exception):
    """Base exception for document parser errors"""


class UnsupportedDocumentError(DocumentParserError):
    """Raised when document type is not supported"""


class DownloadError(DocumentParserError):
    """Raised when document download fails"""


class ParseError(DocumentParserError):
    """Raised when document parsing fails"""


@register_tool("document_parser")
class DocumentParserTool(BaseTool):
    """
    Modern high-performance document parsing component that can:
    1. Auto-detect document types from URLs or files
    2. Download documents from URLs
    3. Parse various document formats using existing atomic tools
    4. Output structured content for AI consumption

    Leverages existing tools:
    - ScraperTool for URL downloading
    - OfficeTool for Office document parsing
    - ImageTool for image OCR

    Configuration:
    Configuration is automatically loaded by BaseTool from:
    1. Explicit config dict (highest priority) - passed to constructor
    2. YAML config files - config/tools/document_parser_tool.yaml or config/tools.yaml (see examples/config/tools/ for examples)
    3. Environment variables - from .env files via dotenv (DOC_PARSER_ prefix)
    4. Tool defaults - defined in Config class Field defaults (lowest priority)

    Example usage:
        # Basic usage (automatic configuration)
        tool = get_tool("document_parser")

        # With explicit config override
        tool = get_tool("document_parser", config={"timeout": 120})

        # Configuration files:
        # - Runtime config: config/tools/document_parser_tool.yaml (see examples/config/tools/ for examples)
        # - Sensitive config: .env file with DOC_PARSER_* variables

    See docs/developer/TOOLS/TOOL_CONFIGURATION_EXAMPLES.md for more examples.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the document parser tool

        Configuration is automatically loaded by BaseTool using ToolConfigLoader.
        Supports loading from:
        - YAML files: config/tools/document_parser_tool.yaml (see examples/config/tools/ for examples)
        - Environment variables: DOC_PARSER_* (from .env files via dotenv)
        - Explicit config dict: passed to constructor

        Environment variable prefix: DOC_PARSER_
        Example: DOC_PARSER_GCS_PROJECT_ID -> gcs_project_id
        Example: DOC_PARSER_TIMEOUT -> timeout
        """

        model_config = SettingsConfigDict(env_prefix="DOC_PARSER_")

        user_agent: str = Field(
            default="DocumentParser/1.0",
            description="User agent for HTTP requests",
        )
        max_file_size: int = Field(default=50 * 1024 * 1024, description="Maximum file size in bytes")
        temp_dir: str = Field(
            default=os.path.join(tempfile.gettempdir(), "document_parser"),
            description="Temporary directory for document processing",
        )
        default_encoding: str = Field(default="utf-8", description="Default encoding for text files")
        timeout: int = Field(default=30, description="Timeout for HTTP requests in seconds")
        max_pages: int = Field(
            default=1000,
            description="Maximum number of pages to process for large documents",
        )
        enable_cloud_storage: bool = Field(
            default=True,
            description="Whether to enable cloud storage integration",
        )
        gcs_bucket_name: str = Field(
            default="aiecs-documents",
            description="Google Cloud Storage bucket name",
        )
        gcs_project_id: Optional[str] = Field(default=None, description="Google Cloud Storage project ID")

    def __init__(self, config: Optional[Dict] = None, **kwargs):
        """Initialize DocumentParserTool with settings

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/document_parser_tool.yaml)
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
        os.makedirs(self.config.temp_dir, exist_ok=True)

        # Initialize dependent tools
        self._init_dependent_tools()

        # Initialize cloud storage
        self._init_cloud_storage()

    def _init_dependent_tools(self):
        """Initialize dependent tools for document processing"""
        try:
            from aiecs.tools.task_tools.scraper_tool import ScraperTool

            self.scraper_tool = ScraperTool()
        except ImportError:
            self.logger.warning("ScraperTool not available")
            self.scraper_tool = None

        try:
            from aiecs.tools.task_tools.office_tool import OfficeTool

            self.office_tool = OfficeTool()
        except ImportError:
            self.logger.warning("OfficeTool not available")
            self.office_tool = None

        try:
            from aiecs.tools.task_tools.image_tool import ImageTool

            self.image_tool = ImageTool()
        except ImportError:
            self.logger.warning("ImageTool not available")
            self.image_tool = None

    def _init_cloud_storage(self):
        """Initialize cloud storage for document retrieval"""
        self.file_storage = None

        if self.config.enable_cloud_storage:
            try:
                from aiecs.infrastructure.persistence.file_storage import (
                    FileStorage,
                )

                storage_config = {
                    "gcs_bucket_name": self.config.gcs_bucket_name,
                    "gcs_project_id": self.config.gcs_project_id,
                    "enable_local_fallback": True,
                    "local_storage_path": self.config.temp_dir,
                }

                self.file_storage = FileStorage(storage_config)
                asyncio.create_task(self._init_storage_async())

            except ImportError:
                self.logger.warning("FileStorage not available, cloud storage disabled")
            except Exception as e:
                self.logger.warning(f"Failed to initialize cloud storage: {e}")

    async def _init_storage_async(self):
        """Async initialization of file storage"""
        try:
            if self.file_storage:
                await self.file_storage.initialize()
                self.logger.info("Cloud storage initialized successfully")
        except Exception as e:
            self.logger.warning(f"Cloud storage initialization failed: {e}")
            self.file_storage = None

    # Schema definitions
    class ParseDocumentSchema(BaseModel):
        """Schema for parse_document operation"""

        source: str = Field(description="URL or file path to the document")
        strategy: ParsingStrategy = Field(
            default=ParsingStrategy.FULL_CONTENT,
            description="Parsing strategy",
        )
        output_format: OutputFormat = Field(default=OutputFormat.JSON, description="Output format")
        force_type: Optional[DocumentType] = Field(default=None, description="Force document type detection")
        extract_metadata: bool = Field(default=True, description="Whether to extract metadata")
        chunk_size: Optional[int] = Field(default=None, description="Chunk size for large documents")

    class DetectTypeSchema(BaseModel):
        """Schema for detect_document_type operation"""

        source: str = Field(description="URL or file path to analyze")
        download_sample: bool = Field(
            default=True,
            description="Download sample for content-based detection",
        )

    def detect_document_type(self, source: str, download_sample: bool = True) -> Dict[str, Any]:
        """
        Detect document type from URL or file path

        Args:
            source: URL or file path
            download_sample: Whether to download sample for content analysis

        Returns:
            Dict containing detected type and confidence
        """
        try:
            result: Dict[str, Any] = {
                "source": source,
                "is_url": self._is_url(source),
                "detected_type": DocumentType.UNKNOWN,
                "confidence": 0.0,
                "mime_type": None,
                "file_extension": None,
                "file_size": None,
                "detection_methods": [],
            }

            # Method 1: File extension analysis
            extension_type, ext_confidence = self._detect_by_extension(source)
            if extension_type != DocumentType.UNKNOWN:
                result["detected_type"] = extension_type
                result["confidence"] = ext_confidence
                result["file_extension"] = Path(source).suffix.lower()
                result["detection_methods"].append("file_extension")

            # Method 2: MIME type detection (for URLs)
            if self._is_url(source) and download_sample:
                mime_type, mime_confidence = self._detect_by_mime_type(source)
                confidence = result.get("confidence", 0.0)
                if isinstance(confidence, (int, float)) and mime_type != DocumentType.UNKNOWN and mime_confidence > confidence:
                    result["detected_type"] = mime_type
                    result["confidence"] = mime_confidence
                    result["detection_methods"].append("mime_type")

            # Method 3: Content-based detection
            if download_sample:
                content_type, content_confidence = self._detect_by_content(source)
                confidence = result.get("confidence", 0.0)
                if isinstance(confidence, (int, float)) and content_type != DocumentType.UNKNOWN and content_confidence > confidence:
                    result["detected_type"] = content_type
                    result["confidence"] = content_confidence
                    result["detection_methods"].append("content_analysis")

            return result

        except Exception as e:
            raise DocumentParserError(f"Document type detection failed: {str(e)}")

    def parse_document(
        self,
        source: str,
        strategy: ParsingStrategy = ParsingStrategy.FULL_CONTENT,
        output_format: OutputFormat = OutputFormat.JSON,
        force_type: Optional[DocumentType] = None,
        extract_metadata: bool = True,
        chunk_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Parse document from URL or file path

        Args:
            source: URL or file path to document
            strategy: Parsing strategy to use
            output_format: Format for output content
            force_type: Force specific document type
            extract_metadata: Whether to extract metadata
            chunk_size: Chunk size for large documents

        Returns:
            Dict containing parsed content and metadata
        """
        try:
            # Step 1: Detect document type
            if force_type:
                doc_type = force_type
                confidence = 1.0
            else:
                detection_result = self.detect_document_type(source)
                doc_type = detection_result["detected_type"]
                confidence = detection_result["confidence"]

                if confidence < 0.5:
                    raise UnsupportedDocumentError(f"Unable to reliably detect document type for: {source}")

            # Step 2: Download document if it's a URL
            local_path = self._ensure_local_file(source)

            # Step 3: Parse document based on type and strategy
            content = self._parse_by_type(local_path, doc_type, strategy)

            # Step 4: Extract metadata if requested
            metadata = {}
            if extract_metadata:
                metadata = self._extract_metadata(local_path, doc_type)

            # Step 5: Format output
            result = {
                "source": source,
                "document_type": doc_type,
                "detection_confidence": confidence,
                "parsing_strategy": strategy,
                "metadata": metadata,
                "content": content,
                "content_stats": self._calculate_content_stats(content),
                "chunks": [],
            }

            # Step 6: Create chunks if requested
            if chunk_size and isinstance(content, str):
                result["chunks"] = self._create_chunks(content, chunk_size)

            # Step 7: Format output according to requested format
            if output_format == OutputFormat.TEXT:
                return {"text": self._format_as_text(result)}
            elif output_format == OutputFormat.MARKDOWN:
                return {"markdown": self._format_as_markdown(result)}
            elif output_format == OutputFormat.HTML:
                return {"html": self._format_as_html(result)}
            else:
                return result

        except Exception as e:
            if isinstance(e, DocumentParserError):
                raise
            raise ParseError(f"Document parsing failed: {str(e)}")
        finally:
            # Cleanup temporary files
            self._cleanup_temp_files(source)

    async def parse_document_async(
        self,
        source: str,
        strategy: ParsingStrategy = ParsingStrategy.FULL_CONTENT,
        output_format: OutputFormat = OutputFormat.JSON,
        force_type: Optional[DocumentType] = None,
        extract_metadata: bool = True,
        chunk_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Async version of parse_document"""
        return await asyncio.to_thread(
            self.parse_document,
            source=source,
            strategy=strategy,
            output_format=output_format,
            force_type=force_type,
            extract_metadata=extract_metadata,
            chunk_size=chunk_size,
        )

    def _is_url(self, source: str) -> bool:
        """Check if source is a URL"""
        try:
            result = urlparse(source)
            return bool(result.scheme and result.netloc)
        except Exception:
            return False

    def _is_cloud_storage_path(self, source: str) -> bool:
        """Check if source is a cloud storage path"""
        # Support various cloud storage path formats:
        # - gs://bucket/path/file.pdf (Google Cloud Storage)
        # - s3://bucket/path/file.pdf (AWS S3)
        # - azure://container/path/file.pdf (Azure Blob Storage)
        # - cloud://path/file.pdf (Generic cloud storage)
        cloud_schemes = ["gs", "s3", "azure", "cloud"]
        try:
            parsed = urlparse(source)
            return parsed.scheme in cloud_schemes
        except Exception:
            return False

    def _is_storage_id(self, source: str) -> bool:
        """Check if source is a storage ID (UUID-like identifier)"""
        # Check for UUID patterns or other storage ID formats
        import re

        uuid_pattern = r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
        storage_id_pattern = r"^[a-zA-Z0-9_-]{10,}$"  # Generic storage ID

        return bool(re.match(uuid_pattern, source, re.IGNORECASE) or re.match(storage_id_pattern, source))

    def _detect_by_extension(self, source: str) -> Tuple[DocumentType, float]:
        """Detect document type by file extension"""
        try:
            path = Path(source)
            ext = path.suffix.lower()

            extension_map = {
                ".pdf": DocumentType.PDF,
                ".docx": DocumentType.DOCX,
                ".doc": DocumentType.DOCX,
                ".xlsx": DocumentType.XLSX,
                ".xls": DocumentType.XLSX,
                ".pptx": DocumentType.PPTX,
                ".ppt": DocumentType.PPTX,
                ".txt": DocumentType.TXT,
                ".html": DocumentType.HTML,
                ".htm": DocumentType.HTML,
                ".rtf": DocumentType.RTF,
                ".csv": DocumentType.CSV,
                ".json": DocumentType.JSON,
                ".xml": DocumentType.XML,
                ".md": DocumentType.MARKDOWN,
                ".markdown": DocumentType.MARKDOWN,
                ".jpg": DocumentType.IMAGE,
                ".jpeg": DocumentType.IMAGE,
                ".png": DocumentType.IMAGE,
                ".gif": DocumentType.IMAGE,
                ".bmp": DocumentType.IMAGE,
                ".tiff": DocumentType.IMAGE,
            }

            doc_type = extension_map.get(ext, DocumentType.UNKNOWN)
            confidence = 0.8 if doc_type != DocumentType.UNKNOWN else 0.0

            return doc_type, confidence

        except Exception:
            return DocumentType.UNKNOWN, 0.0

    def _detect_by_mime_type(self, url: str) -> Tuple[DocumentType, float]:
        """Detect document type by MIME type from URL"""
        try:
            if not self.scraper_tool:
                return DocumentType.UNKNOWN, 0.0

            # Get headers only
            response = asyncio.run(self.scraper_tool.get_httpx(url, method="HEAD", verify_ssl=False))

            content_type = response.get("headers", {}).get("content-type", "").lower()

            mime_map = {
                "application/pdf": DocumentType.PDF,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.XLSX,
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": DocumentType.PPTX,
                "text/plain": DocumentType.TXT,
                "text/html": DocumentType.HTML,
                "application/rtf": DocumentType.RTF,
                "text/csv": DocumentType.CSV,
                "application/json": DocumentType.JSON,
                "application/xml": DocumentType.XML,
                "text/xml": DocumentType.XML,
                "text/markdown": DocumentType.MARKDOWN,
                "image/jpeg": DocumentType.IMAGE,
                "image/png": DocumentType.IMAGE,
                "image/gif": DocumentType.IMAGE,
                "image/bmp": DocumentType.IMAGE,
                "image/tiff": DocumentType.IMAGE,
            }

            for mime_pattern, doc_type in mime_map.items():
                if mime_pattern in content_type:
                    return doc_type, 0.9

            return DocumentType.UNKNOWN, 0.0

        except Exception:
            return DocumentType.UNKNOWN, 0.0

    def _detect_by_content(self, source: str) -> Tuple[DocumentType, float]:
        """Detect document type by content analysis"""
        try:
            # Download a small sample for analysis
            if self._is_url(source):
                sample_path = self._download_sample(source, max_size=1024)  # 1KB sample
            else:
                sample_path = source

            with open(sample_path, "rb") as f:
                header = f.read(512)  # Read first 512 bytes

            # Magic number detection
            if header.startswith(b"%PDF"):
                return DocumentType.PDF, 0.95
            elif header.startswith(b"PK\x03\x04"):  # ZIP-based formats
                if b"word/" in header or b"document.xml" in header:
                    return DocumentType.DOCX, 0.9
                elif b"xl/" in header or b"workbook.xml" in header:
                    return DocumentType.XLSX, 0.9
                elif b"ppt/" in header or b"presentation.xml" in header:
                    return DocumentType.PPTX, 0.9
            elif header.startswith(b"{\rtf"):
                return DocumentType.RTF, 0.95
            elif header.startswith((b"\xff\xd8\xff", b"\x89PNG", b"GIF8")):
                return DocumentType.IMAGE, 0.95
            elif header.startswith(b"<?xml"):
                return DocumentType.XML, 0.9
            elif header.startswith((b"{", b"[")):
                # Try to parse as JSON
                try:
                    import json

                    json.loads(header.decode("utf-8", errors="ignore"))
                    return DocumentType.JSON, 0.85
                except Exception:
                    pass

            # Text-based detection
            try:
                text_content = header.decode("utf-8", errors="ignore")
                if re.match(r"^#\s+.*$", text_content, re.MULTILINE):
                    return DocumentType.MARKDOWN, 0.7
                elif "<html" in text_content.lower() or "<!doctype html" in text_content.lower():
                    return DocumentType.HTML, 0.85
                elif "," in text_content and "\n" in text_content:
                    # Simple CSV detection
                    lines = text_content.split("\n")[:5]
                    if all("," in line for line in lines if line.strip()):
                        return DocumentType.CSV, 0.6
            except Exception:
                pass

            return DocumentType.UNKNOWN, 0.0

        except Exception:
            return DocumentType.UNKNOWN, 0.0

    def _ensure_local_file(self, source: str) -> str:
        """Ensure we have a local file, download/retrieve if necessary"""
        # Check source type and handle accordingly
        if self._is_cloud_storage_path(source) or self._is_storage_id(source):
            # Download from cloud storage
            return asyncio.run(self._download_from_cloud_storage(source))
        elif self._is_url(source):
            # Download from URL
            return self._download_document(source)
        else:
            # Local file path
            if not os.path.exists(source):
                raise FileNotFoundError(f"File not found: {source}")
            return source

    def _download_document(self, url: str) -> str:
        """Download document from URL"""
        try:
            if not self.scraper_tool:
                raise DownloadError("ScraperTool not available for URL download")

            # Generate temp file path
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path) or "document"
            temp_path = os.path.join(self.config.temp_dir, f"download_{hash(url)}_{filename}")

            # Download using scraper tool
            result = asyncio.run(
                self.scraper_tool.get_httpx(
                    url,
                    content_type="binary",
                    output_path=temp_path,
                    verify_ssl=False,
                )
            )

            if isinstance(result, dict) and "saved_to" in result:
                return result["saved_to"]
            else:
                # Fallback: save content manually
                with open(temp_path, "wb") as f:
                    if isinstance(result, dict) and "content" in result:
                        f.write(result["content"])
                    else:
                        f.write(result)
                return temp_path

        except Exception as e:
            raise DownloadError(f"Failed to download document from {url}: {str(e)}")

    async def _download_from_cloud_storage(self, source: str) -> str:
        """Download document from cloud storage"""
        if not self.file_storage:
            raise DownloadError("Cloud storage not available")

        try:
            # Parse the cloud storage path
            storage_path = self._parse_cloud_storage_path(source)

            # Generate local temp file path
            temp_filename = f"cloud_download_{hash(source)}_{Path(storage_path).name}"
            temp_path = os.path.join(self.config.temp_dir, temp_filename)

            self.logger.info(f"Downloading from cloud storage: {source} -> {temp_path}")

            # Retrieve file from cloud storage
            file_data = await self.file_storage.retrieve(storage_path)

            # Save to local temp file
            if isinstance(file_data, bytes):
                with open(temp_path, "wb") as f:
                    f.write(file_data)
            elif isinstance(file_data, str):
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(file_data)
            else:
                # Handle other data types (e.g., dict, list)
                import json

                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(file_data, f)

            self.logger.info(f"Successfully downloaded file to: {temp_path}")
            return temp_path

        except Exception as e:
            raise DownloadError(f"Failed to download from cloud storage {source}: {str(e)}")

    def _parse_cloud_storage_path(self, source: str) -> str:
        """Parse cloud storage path to get the storage key"""
        try:
            if self._is_storage_id(source):
                # Direct storage ID
                return source
            elif self._is_cloud_storage_path(source):
                parsed = urlparse(source)
                if parsed.scheme == "gs":
                    # Google Cloud Storage: gs://bucket/path/file.pdf ->
                    # path/file.pdf
                    return parsed.path.lstrip("/")
                elif parsed.scheme == "s3":
                    # AWS S3: s3://bucket/path/file.pdf -> path/file.pdf
                    return parsed.path.lstrip("/")
                elif parsed.scheme == "azure":
                    # Azure Blob: azure://container/path/file.pdf ->
                    # path/file.pdf
                    return parsed.path.lstrip("/")
                elif parsed.scheme == "cloud":
                    # Generic cloud: cloud://path/file.pdf -> path/file.pdf
                    return parsed.path.lstrip("/")
                else:
                    return parsed.path.lstrip("/")
            else:
                # Assume it's already a storage path
                return source
        except Exception as e:
            self.logger.warning(f"Failed to parse cloud storage path {source}: {e}")
            return source

    def _download_sample(self, url: str, max_size: int = 1024) -> str:
        """Download a small sample of the document for analysis"""
        # This is a simplified version - in practice, you'd implement range
        # requests
        return self._download_document(url)

    def _parse_by_type(self, file_path: str, doc_type: DocumentType, strategy: ParsingStrategy) -> Union[str, Dict[str, Any]]:
        """Parse document based on its type and strategy"""
        try:
            if doc_type == DocumentType.PDF:
                return self._parse_pdf(file_path, strategy)
            elif doc_type in [
                DocumentType.DOCX,
                DocumentType.XLSX,
                DocumentType.PPTX,
            ]:
                return self._parse_office_document(file_path, doc_type, strategy)
            elif doc_type == DocumentType.IMAGE:
                return self._parse_image(file_path, strategy)
            elif doc_type in [
                DocumentType.TXT,
                DocumentType.HTML,
                DocumentType.CSV,
                DocumentType.JSON,
                DocumentType.XML,
                DocumentType.MARKDOWN,
            ]:
                return self._parse_text_document(file_path, doc_type, strategy)
            else:
                raise UnsupportedDocumentError(f"Unsupported document type: {doc_type}")

        except Exception as e:
            raise ParseError(f"Failed to parse {doc_type} document: {str(e)}")

    def _parse_pdf(self, file_path: str, strategy: ParsingStrategy) -> Union[str, Dict[str, Any]]:
        """Parse PDF document"""
        if self.office_tool:
            try:
                text_content = self.office_tool.extract_text(file_path)

                if strategy == ParsingStrategy.TEXT_ONLY:
                    return text_content
                elif strategy == ParsingStrategy.STRUCTURED:
                    # Try to extract structure from PDF
                    return {
                        "text": text_content,
                        "structure": self._extract_pdf_structure(text_content),
                    }
                else:
                    return {
                        "text": text_content,
                        "pages": self._split_into_pages(text_content),
                    }
            except Exception as e:
                self.logger.warning(f"OfficeTool PDF parsing failed: {e}")

        # Fallback to simple text extraction
        return self._extract_text_fallback(file_path)

    def _parse_office_document(self, file_path: str, doc_type: DocumentType, strategy: ParsingStrategy) -> Union[str, Dict[str, Any]]:
        """Parse Office documents (DOCX, XLSX, PPTX)"""
        if not self.office_tool:
            raise UnsupportedDocumentError("OfficeTool not available for Office document parsing")

        try:
            text_content = self.office_tool.extract_text(file_path)

            if strategy == ParsingStrategy.TEXT_ONLY:
                return text_content
            elif strategy == ParsingStrategy.STRUCTURED:
                return {
                    "text": text_content,
                    "structure": self._extract_office_structure(file_path, doc_type),
                }
            else:
                return {"text": text_content, "raw_content": text_content}

        except Exception as e:
            raise ParseError(f"Failed to parse Office document: {str(e)}")

    def _parse_image(self, file_path: str, strategy: ParsingStrategy) -> Union[str, Dict[str, Any]]:
        """Parse image document using OCR"""
        if not self.image_tool:
            raise UnsupportedDocumentError("ImageTool not available for image OCR")

        try:
            # Use image tool for OCR
            ocr_result = self.image_tool.ocr_image(file_path)

            if strategy == ParsingStrategy.TEXT_ONLY:
                return ocr_result.get("text", "")
            else:
                return ocr_result

        except Exception as e:
            raise ParseError(f"Failed to parse image document: {str(e)}")

    def _parse_text_document(self, file_path: str, doc_type: DocumentType, strategy: ParsingStrategy) -> Union[str, Dict[str, Any]]:
        """Parse text-based documents"""
        try:
            with open(
                file_path,
                "r",
                encoding=self.config.default_encoding,
                errors="ignore",
            ) as f:
                content = f.read()

            if strategy == ParsingStrategy.TEXT_ONLY:
                return content
            elif strategy == ParsingStrategy.STRUCTURED:
                return self._extract_text_structure(content, doc_type)
            else:
                return {
                    "text": content,
                    "lines": content.split("\n"),
                    "word_count": len(content.split()),
                }

        except Exception as e:
            raise ParseError(f"Failed to parse text document: {str(e)}")

    def _extract_metadata(self, file_path: str, doc_type: DocumentType) -> Dict[str, Any]:
        """Extract metadata from document"""
        metadata = {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "file_type": doc_type.value,
            "created_at": os.path.getctime(file_path),
            "modified_at": os.path.getmtime(file_path),
        }

        # Add type-specific metadata extraction here
        # This could leverage existing tools' metadata extraction capabilities

        return metadata

    def _calculate_content_stats(self, content: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics about the parsed content"""
        if isinstance(content, str):
            return {
                "character_count": len(content),
                "word_count": len(content.split()),
                "line_count": len(content.split("\n")),
                "paragraph_count": len([p for p in content.split("\n\n") if p.strip()]),
            }
        else:
            # For structured content, calculate stats on text portion
            text_content = content.get("text", "")
            return self._calculate_content_stats(text_content)

    def _create_chunks(self, content: str, chunk_size: int) -> List[Dict[str, Any]]:
        """Create chunks from content for better AI processing"""
        chunks: List[Dict[str, Any]] = []
        words = content.split()

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)

            chunks.append(
                {
                    "index": len(chunks),
                    "text": chunk_text,
                    "word_count": len(chunk_words),
                    "start_word": i,
                    "end_word": min(i + chunk_size, len(words)),
                }
            )

        return chunks

    def _format_as_text(self, result: Dict[str, Any]) -> str:
        """Format result as plain text"""
        content = result.get("content", "")
        if isinstance(content, dict):
            return content.get("text", str(content))
        return str(content)

    def _format_as_markdown(self, result: Dict[str, Any]) -> str:
        """Format result as Markdown"""
        content = result.get("content", "")
        result.get("metadata", {})

        md_content = f"# Document: {result.get('source', 'Unknown')}\n\n"
        md_content += f"**Type:** {result.get('document_type', 'Unknown')}\n"
        md_content += f"**Detection Confidence:** {result.get('detection_confidence', 0):.2f}\n\n"

        if isinstance(content, dict):
            md_content += content.get("text", str(content))
        else:
            md_content += str(content)

        return md_content

    def _format_as_html(self, result: Dict[str, Any]) -> str:
        """Format result as HTML"""
        content = result.get("content", "")

        html_content = f"""
        <html>
        <head><title>Parsed Document</title></head>
        <body>
        <h1>Document: {result.get('source', 'Unknown')}</h1>
        <p><strong>Type:</strong> {result.get('document_type', 'Unknown')}</p>
        <p><strong>Detection Confidence:</strong> {result.get('detection_confidence', 0):.2f}</p>
        <div class="content">
        """

        if isinstance(content, dict):
            html_content += f"<pre>{content.get('text', str(content))}</pre>"
        else:
            html_content += f"<pre>{str(content)}</pre>"

        html_content += "</div></body></html>"
        return html_content

    def _cleanup_temp_files(self, source: str):
        """Clean up temporary files"""
        import glob

        if self._is_url(source):
            # Clean up URL downloaded files
            temp_pattern = os.path.join(self.config.temp_dir, f"download_{hash(source)}_*")
            for temp_file in glob.glob(temp_pattern):
                try:
                    os.remove(temp_file)
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temp file {temp_file}: {e}")

        elif self._is_cloud_storage_path(source) or self._is_storage_id(source):
            # Clean up cloud storage downloaded files
            temp_pattern = os.path.join(self.config.temp_dir, f"cloud_download_{hash(source)}_*")
            for temp_file in glob.glob(temp_pattern):
                try:
                    os.remove(temp_file)
                    self.logger.debug(f"Cleaned up cloud temp file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up cloud temp file {temp_file}: {e}")

    # Helper methods for structure extraction
    def _extract_pdf_structure(self, text: str) -> Dict[str, Any]:
        """Extract structure from PDF text"""
        # Implement PDF structure extraction logic
        return {"sections": [], "headings": []}

    def _extract_office_structure(self, file_path: str, doc_type: DocumentType) -> Dict[str, Any]:
        """Extract structure from Office documents"""
        # Implement Office document structure extraction
        return {"sections": [], "tables": [], "images": []}

    def _extract_text_structure(self, content: str, doc_type: DocumentType) -> Dict[str, Any]:
        """Extract structure from text documents"""
        result: Dict[str, Any] = {"text": content}

        if doc_type == DocumentType.MARKDOWN:
            # Extract markdown structure
            headings = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)
            result["headings"] = [{"level": len(h[0]), "text": h[1]} for h in headings]
        elif doc_type == DocumentType.HTML:
            # Extract HTML structure (simplified)
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")
            result["title"] = soup.title.string if soup.title else ""
            result["headings"] = [{"tag": h.name, "text": h.get_text()} for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])]
        elif doc_type == DocumentType.JSON:
            import json

            try:
                result["json_data"] = json.loads(content)
            except Exception:
                pass

        return result

    def _split_into_pages(self, text: str) -> List[str]:
        """Split text into pages (simplified)"""
        # This is a simple implementation - could be enhanced
        # Form feed character often indicates page break
        pages = text.split("\f")
        return [page.strip() for page in pages if page.strip()]

    def _extract_text_fallback(self, file_path: str) -> str:
        """Fallback text extraction method"""
        try:
            with open(
                file_path,
                "r",
                encoding=self.config.default_encoding,
                errors="ignore",
            ) as f:
                return f.read()
        except Exception:
            with open(file_path, "rb") as f:
                return f.read().decode("utf-8", errors="ignore")
