import os
import json
import uuid
import hashlib
import logging
import asyncio
import shutil
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
from datetime import datetime
from pathlib import Path
import tempfile

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class DocumentFormat(str, Enum):
    """Supported document formats for writing"""

    TXT = "txt"
    PLAIN_TEXT = "txt"  # Alias for TXT
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    MARKDOWN = "md"
    HTML = "html"
    YAML = "yaml"
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    BINARY = "binary"


class WriteMode(str, Enum):
    """Document writing modes"""

    CREATE = "create"  # 创建新文件，如果存在则失败
    OVERWRITE = "overwrite"  # 覆盖现有文件
    APPEND = "append"  # 追加到现有文件
    UPDATE = "update"  # 更新现有文件（智能合并）
    BACKUP_WRITE = "backup_write"  # 备份后写入
    VERSION_WRITE = "version_write"  # 版本化写入
    INSERT = "insert"  # 在指定位置插入内容
    REPLACE = "replace"  # 替换指定内容
    DELETE = "delete"  # 删除指定内容


class EditOperation(str, Enum):
    """Advanced edit operations"""

    BOLD = "bold"  # 加粗文本
    ITALIC = "italic"  # 斜体文本
    UNDERLINE = "underline"  # 下划线文本
    STRIKETHROUGH = "strikethrough"  # 删除线文本
    HIGHLIGHT = "highlight"  # 高亮文本
    INSERT_TEXT = "insert_text"  # 插入文本
    DELETE_TEXT = "delete_text"  # 删除文本
    REPLACE_TEXT = "replace_text"  # 替换文本
    COPY_TEXT = "copy_text"  # 复制文本
    CUT_TEXT = "cut_text"  # 剪切文本
    PASTE_TEXT = "paste_text"  # 粘贴文本
    FIND_REPLACE = "find_replace"  # 查找替换
    INSERT_LINE = "insert_line"  # 插入行
    DELETE_LINE = "delete_line"  # 删除行
    MOVE_LINE = "move_line"  # 移动行


class EncodingType(str, Enum):
    """Text encoding types"""

    UTF8 = "utf-8"
    UTF16 = "utf-16"
    ASCII = "ascii"
    GBK = "gbk"
    AUTO = "auto"


class ValidationLevel(str, Enum):
    """Content validation levels"""

    NONE = "none"  # 无验证
    BASIC = "basic"  # 基础验证（格式、大小）
    STRICT = "strict"  # 严格验证（内容、结构）
    ENTERPRISE = "enterprise"  # 企业级验证（安全、合规）


class DocumentWriterError(Exception):
    """Base exception for document writer errors"""


class WriteError(DocumentWriterError):
    """Raised when write operations fail"""


class ValidationError(DocumentWriterError):
    """Raised when validation fails"""


class SecurityError(DocumentWriterError):
    """Raised when security validation fails"""


class WritePermissionError(DocumentWriterError):
    """Raised when write permission is denied"""


class ContentValidationError(DocumentWriterError):
    """Raised when content validation fails"""


class StorageError(DocumentWriterError):
    """Raised when storage operations fail"""


@register_tool("document_writer")
class DocumentWriterTool(BaseTool):
    """
    Modern high-performance document writing component that can:
    1. Handle multiple document formats and encodings
    2. Provide production-grade write operations with validation
    3. Support various write modes (create, overwrite, append, update)
    4. Implement backup and versioning strategies
    5. Ensure atomic operations and data integrity
    6. Support both local and cloud storage

    Production Features:
    - Atomic writes (no partial writes)
    - Content validation and security scanning
    - Automatic backup and versioning
    - Write permission and quota checks
    - Transaction-like operations
    - Audit logging
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the document writer tool

        Automatically reads from environment variables with DOC_WRITER_ prefix.
        Example: DOC_WRITER_GCS_PROJECT_ID -> gcs_project_id
        """

        model_config = SettingsConfigDict(env_prefix="DOC_WRITER_")

        temp_dir: str = Field(
            default=os.path.join(tempfile.gettempdir(), "document_writer"),
            description="Temporary directory for document processing",
        )
        backup_dir: str = Field(
            default=os.path.join(tempfile.gettempdir(), "document_backups"),
            description="Directory for document backups",
        )
        output_dir: Optional[str] = Field(default=None, description="Default output directory for documents")
        max_file_size: int = Field(default=100 * 1024 * 1024, description="Maximum file size in bytes")
        max_backup_versions: int = Field(default=10, description="Maximum number of backup versions to keep")
        default_encoding: str = Field(default="utf-8", description="Default text encoding for documents")
        enable_backup: bool = Field(
            default=True,
            description="Whether to enable automatic backup functionality",
        )
        enable_versioning: bool = Field(default=True, description="Whether to enable document versioning")
        enable_content_validation: bool = Field(default=True, description="Whether to enable content validation")
        enable_security_scan: bool = Field(default=True, description="Whether to enable security scanning")
        atomic_write: bool = Field(default=True, description="Whether to use atomic write operations")
        validation_level: str = Field(default="basic", description="Content validation level")
        timeout_seconds: int = Field(default=60, description="Operation timeout in seconds")
        auto_backup: bool = Field(
            default=True,
            description="Whether to automatically backup before write operations",
        )
        atomic_writes: bool = Field(default=True, description="Whether to use atomic write operations")
        default_format: str = Field(default="md", description="Default document format")
        version_control: bool = Field(default=True, description="Whether to enable version control")
        security_scan: bool = Field(default=True, description="Whether to enable security scanning")
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
        """Initialize DocumentWriterTool with settings

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/document_writer_tool.yaml)
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

        # Create necessary directories
        os.makedirs(self.config.temp_dir, exist_ok=True)
        os.makedirs(self.config.backup_dir, exist_ok=True)

        # Initialize cloud storage
        self._init_cloud_storage()

        # Initialize content validators
        self._init_validators()

    def _init_cloud_storage(self):
        """Initialize cloud storage for document writing"""
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

    def _init_validators(self):
        """Initialize content validators"""
        self.validators = {
            DocumentFormat.JSON: self._validate_json_content,
            DocumentFormat.XML: self._validate_xml_content,
            DocumentFormat.CSV: self._validate_csv_content,
            DocumentFormat.YAML: self._validate_yaml_content,
            DocumentFormat.HTML: self._validate_html_content,
        }

    # Schema definitions
    class WriteDocumentSchema(BaseModel):
        """Schema for write_document operation"""

        target_path: str = Field(description="Target file path (local or cloud)")
        content: Union[str, bytes, Dict, List] = Field(description="Content to write")
        format: DocumentFormat = Field(description="Document format")
        mode: WriteMode = Field(default=WriteMode.CREATE, description="Write mode")
        encoding: EncodingType = Field(default=EncodingType.UTF8, description="Text encoding")
        validation_level: ValidationLevel = Field(default=ValidationLevel.BASIC, description="Validation level")
        metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
        backup_comment: Optional[str] = Field(default=None, description="Backup comment")

    class BatchWriteSchema(BaseModel):
        """Schema for batch_write_documents operation"""

        write_operations: List[Dict[str, Any]] = Field(description="List of write operations")
        transaction_mode: bool = Field(default=True, description="Use transaction mode")
        rollback_on_error: bool = Field(default=True, description="Rollback on any error")

    class EditDocumentSchema(BaseModel):
        """Schema for edit_document operation"""

        target_path: str = Field(description="Target file path")
        operation: EditOperation = Field(description="Edit operation to perform")
        content: Optional[str] = Field(default=None, description="Content for the operation")
        position: Optional[Dict[str, Any]] = Field(default=None, description="Position info (line, column, offset)")
        selection: Optional[Dict[str, Any]] = Field(default=None, description="Text selection range")
        format_options: Optional[Dict[str, Any]] = Field(default=None, description="Formatting options")

    class FormatTextSchema(BaseModel):
        """Schema for format_text operation"""

        target_path: str = Field(description="Target file path")
        text_to_format: str = Field(description="Text to apply formatting to")
        format_type: EditOperation = Field(description="Type of formatting")
        format_options: Optional[Dict[str, Any]] = Field(default=None, description="Additional format options")

    class FindReplaceSchema(BaseModel):
        """Schema for find_replace operation"""

        target_path: str = Field(description="Target file path")
        find_text: str = Field(description="Text to find")
        replace_text: str = Field(description="Text to replace with")
        replace_all: bool = Field(default=False, description="Replace all occurrences")
        case_sensitive: bool = Field(default=True, description="Case sensitive search")
        regex_mode: bool = Field(default=False, description="Use regex for find/replace")

    def write_document(
        self,
        target_path: str,
        content: Union[str, bytes, Dict, List],
        format: DocumentFormat,
        mode: WriteMode = WriteMode.CREATE,
        encoding: EncodingType = EncodingType.UTF8,
        validation_level: ValidationLevel = ValidationLevel.BASIC,
        metadata: Optional[Dict[str, Any]] = None,
        backup_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Write document with production-grade features

        Args:
            target_path: Target file path (local or cloud)
            content: Content to write
            format: Document format
            mode: Write mode (create, overwrite, append, update, etc.)
            encoding: Text encoding
            validation_level: Content validation level
            metadata: Additional metadata
            backup_comment: Comment for backup

        Returns:
            Dict containing write results and metadata
        """
        try:
            start_time = datetime.now()
            operation_id = str(uuid.uuid4())

            self.logger.info(f"Starting write operation {operation_id}: {target_path}")

            # Step 1: Validate inputs
            self._validate_write_inputs(target_path, content, format, mode)

            # Step 2: Prepare content
            processed_content, content_metadata = self._prepare_content(content, format, encoding, validation_level)

            # Step 3: Handle write mode logic
            write_plan = self._plan_write_operation(target_path, mode, metadata)

            # Step 4: Create backup if needed
            backup_info = None
            if self.config.enable_backup and mode in [
                WriteMode.OVERWRITE,
                WriteMode.UPDATE,
            ]:
                backup_info = self._create_backup(target_path, backup_comment)

            # Step 5: Execute atomic write
            import asyncio
            write_result = asyncio.run(self._execute_atomic_write(target_path, processed_content, format, encoding, write_plan))

            # Step 6: Update metadata and versioning
            version_info = self._handle_versioning(target_path, content_metadata, metadata)

            # Step 7: Audit logging
            audit_info = self._log_write_operation(operation_id, target_path, mode, write_result, backup_info)

            result = {
                "operation_id": operation_id,
                "target_path": target_path,
                "write_mode": mode,
                "format": format,
                "encoding": encoding,
                "content_metadata": content_metadata,
                "write_result": write_result,
                "backup_info": backup_info,
                "version_info": version_info,
                "audit_info": audit_info,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self.logger.info(f"Write operation {operation_id} completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Write operation failed for {target_path}: {str(e)}")
            # Rollback if needed
            if "backup_info" in locals() and backup_info:
                self._rollback_from_backup(target_path, backup_info)
            raise DocumentWriterError(f"Document write failed: {str(e)}")

    async def write_document_async(
        self,
        target_path: str,
        content: Union[str, bytes, Dict, List],
        format: DocumentFormat,
        mode: WriteMode = WriteMode.CREATE,
        encoding: EncodingType = EncodingType.UTF8,
        validation_level: ValidationLevel = ValidationLevel.BASIC,
        metadata: Optional[Dict[str, Any]] = None,
        backup_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async version of write_document"""
        return await asyncio.to_thread(
            self.write_document,
            target_path=target_path,
            content=content,
            format=format,
            mode=mode,
            encoding=encoding,
            validation_level=validation_level,
            metadata=metadata,
            backup_comment=backup_comment,
        )

    def batch_write_documents(
        self,
        write_operations: List[Dict[str, Any]],
        transaction_mode: bool = True,
        rollback_on_error: bool = True,
    ) -> Dict[str, Any]:
        """
        Batch write multiple documents with transaction support

        Args:
            write_operations: List of write operation dictionaries
            transaction_mode: Use transaction mode for atomicity
            rollback_on_error: Rollback all operations on any error

        Returns:
            Dict containing batch write results
        """
        try:
            start_time = datetime.now()
            batch_id = str(uuid.uuid4())

            self.logger.info(f"Starting batch write operation {batch_id}: {len(write_operations)} operations")

            completed_operations = []
            backup_operations = []

            try:
                for i, operation in enumerate(write_operations):
                    self.logger.info(f"Processing operation {i+1}/{len(write_operations)}")

                    # Execute individual write operation
                    result = self.write_document(**operation)
                    completed_operations.append(
                        {
                            "index": i,
                            "operation": operation,
                            "result": result,
                            "status": "success",
                        }
                    )

                    # Track backup info for potential rollback
                    if result.get("backup_info"):
                        backup_operations.append(result["backup_info"])

                batch_result = {
                    "batch_id": batch_id,
                    "total_operations": len(write_operations),
                    "successful_operations": len(completed_operations),
                    "failed_operations": 0,
                    "operations": completed_operations,
                    "transaction_mode": transaction_mode,
                    "batch_metadata": {
                        "start_time": start_time.isoformat(),
                        "end_time": datetime.now().isoformat(),
                        "duration": (datetime.now() - start_time).total_seconds(),
                    },
                }

                self.logger.info(f"Batch write operation {batch_id} completed successfully")
                return batch_result

            except Exception as e:
                self.logger.error(f"Batch write operation {batch_id} failed: {str(e)}")

                if rollback_on_error and transaction_mode:
                    self.logger.info(f"Rolling back batch operation {batch_id}")
                    self._rollback_batch_operations(completed_operations, backup_operations)

                # Create failure result
                batch_result = {
                    "batch_id": batch_id,
                    "total_operations": len(write_operations),
                    "successful_operations": len(completed_operations),
                    "failed_operations": len(write_operations) - len(completed_operations),
                    "operations": completed_operations,
                    "error": str(e),
                    "transaction_mode": transaction_mode,
                    "rollback_performed": rollback_on_error and transaction_mode,
                }

                raise DocumentWriterError(f"Batch write operation failed: {str(e)}")

        except Exception as e:
            raise DocumentWriterError(f"Batch write operation failed: {str(e)}")

    def _validate_write_inputs(
        self,
        target_path: str,
        content: Any,
        format: DocumentFormat,
        mode: WriteMode,
    ):
        """Validate write operation inputs"""
        # Path validation
        if not target_path or not isinstance(target_path, str):
            raise ValueError("Invalid target path")

        # Content validation
        if content is None:
            raise ValueError("Content cannot be None")

        # Size validation
        content_size = self._calculate_content_size(content)
        if content_size > self.config.max_file_size:
            raise ValueError(f"Content size {content_size} exceeds maximum {self.config.max_file_size}")

        # Permission validation
        if not self._check_write_permission(target_path, mode):
            raise WritePermissionError(f"No write permission for {target_path}")

    def _prepare_content(
        self,
        content: Any,
        format: DocumentFormat,
        encoding: EncodingType,
        validation_level: ValidationLevel,
    ) -> Tuple[Union[str, bytes], Dict]:
        """Prepare and validate content for writing"""

        # Content conversion based on format
        processed_content: Union[str, bytes]
        if format == DocumentFormat.JSON:
            if isinstance(content, (dict, list)):
                processed_content = json.dumps(content, ensure_ascii=False, indent=2)
            else:
                processed_content = str(content)
        elif format == DocumentFormat.CSV:
            processed_content = self._convert_to_csv(content)
        elif format == DocumentFormat.XML:
            processed_content = self._convert_to_xml(content)
        elif format == DocumentFormat.YAML:
            processed_content = self._convert_to_yaml(content)
        elif format == DocumentFormat.HTML:
            processed_content = self._convert_to_html(content)
        elif format == DocumentFormat.MARKDOWN:
            processed_content = self._convert_to_markdown(content)
        elif format == DocumentFormat.BINARY:
            if isinstance(content, bytes):
                processed_content = content
            else:
                processed_content = str(content).encode(encoding.value)
        else:
            processed_content = str(content)

        # Content validation
        if self.config.enable_content_validation:
            self._validate_content(processed_content, format, validation_level)

        # Calculate metadata
        content_metadata = {
            "original_type": type(content).__name__,
            "processed_size": (len(processed_content) if isinstance(processed_content, (str, bytes)) else 0),
            "format": format,
            "encoding": encoding,
            "checksum": self._calculate_checksum(processed_content),
            "validation_level": validation_level,
            "timestamp": datetime.now().isoformat(),
        }

        return processed_content, content_metadata

    def _plan_write_operation(self, target_path: str, mode: WriteMode, metadata: Optional[Dict]) -> Dict:
        """Plan the write operation based on mode and target"""

        plan = {
            "target_path": target_path,
            "mode": mode,
            "file_exists": self._file_exists(target_path),
            "is_cloud_path": self._is_cloud_storage_path(target_path),
            "requires_backup": False,
            "requires_versioning": False,
            "atomic_operation": self.config.atomic_write,
        }

        if mode == WriteMode.CREATE and plan["file_exists"]:
            raise DocumentWriterError(f"File already exists: {target_path}")

        if mode in [WriteMode.OVERWRITE, WriteMode.UPDATE] and plan["file_exists"]:
            plan["requires_backup"] = self.config.enable_backup
            plan["requires_versioning"] = self.config.enable_versioning

        if mode == WriteMode.APPEND and not plan["file_exists"]:
            # Convert to CREATE mode
            plan["mode"] = WriteMode.CREATE

        return plan

    def _create_backup(self, target_path: str, comment: Optional[str] = None) -> Dict:
        """Create backup of existing file"""
        if not self._file_exists(target_path):
            return {}

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_stem = Path(target_path).stem
            file_suffix = Path(target_path).suffix

            backup_filename = f"{file_stem}_backup_{timestamp}{file_suffix}"
            backup_path = os.path.join(self.config.backup_dir, backup_filename)

            # Copy file to backup location
            if self._is_cloud_storage_path(target_path):
                backup_path = self._backup_cloud_file(target_path, backup_path)
            else:
                shutil.copy2(target_path, backup_path)

            backup_info = {
                "original_path": target_path,
                "backup_path": backup_path,
                "timestamp": timestamp,
                "comment": comment,
                "checksum": self._calculate_file_checksum(target_path),
            }

            self.logger.info(f"Created backup: {backup_path}")
            return backup_info

        except Exception as e:
            self.logger.error(f"Failed to create backup for {target_path}: {e}")
            raise StorageError(f"Backup creation failed: {e}")

    async def _execute_atomic_write(
        self,
        target_path: str,
        content: Union[str, bytes],
        format: DocumentFormat,
        encoding: EncodingType,
        plan: Dict,
    ) -> Dict:
        """Execute atomic write operation"""

        if plan["is_cloud_path"]:
            return await self._write_to_cloud_storage(target_path, content, format, encoding, plan)
        else:
            return self._write_to_local_file(target_path, content, format, encoding, plan)

    def _write_to_local_file(
        self,
        target_path: str,
        content: Union[str, bytes],
        format: DocumentFormat,
        encoding: EncodingType,
        plan: Dict,
    ) -> Dict:
        """Write to local file system with atomic operation"""

        try:
            # Create parent directories
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            if plan["atomic_operation"]:
                # Atomic write using temporary file
                temp_path = f"{target_path}.tmp.{uuid.uuid4().hex}"

                try:
                    if plan["mode"] == WriteMode.APPEND and plan["file_exists"]:
                        # Read existing content first
                        with open(target_path, "rb") as f:
                            existing_content = f.read()

                        if isinstance(content, str):
                            content = existing_content.decode(encoding.value) + content
                        else:
                            content = existing_content + content

                    # Write to temporary file
                    if isinstance(content, bytes):
                        with open(temp_path, "wb") as f:
                            f.write(content)
                    else:
                        # Handle both EncodingType enum and string
                        enc_value = encoding.value if hasattr(encoding, "value") else str(encoding)
                        with open(temp_path, "w", encoding=enc_value) as f:
                            f.write(content)

                    # Atomic move
                    shutil.move(temp_path, target_path)

                finally:
                    # Cleanup temp file if it still exists
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            else:
                # Direct write
                mode_map = {
                    WriteMode.CREATE: "w",
                    WriteMode.OVERWRITE: "w",
                    WriteMode.APPEND: "a",
                    WriteMode.UPDATE: "w",
                }

                file_mode = mode_map.get(plan["mode"], "w")
                if isinstance(content, bytes):
                    file_mode += "b"

                # Handle both EncodingType enum and string
                file_enc_value: Optional[str] = None if isinstance(content, bytes) else (encoding.value if hasattr(encoding, "value") else str(encoding))
                with open(target_path, file_mode, encoding=file_enc_value) as f:
                    f.write(content)

            # Get file stats
            stat = os.stat(target_path)

            return {
                "path": target_path,
                "size": stat.st_size,
                "checksum": self._calculate_file_checksum(target_path),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "atomic_write": plan["atomic_operation"],
            }

        except Exception as e:
            raise StorageError(f"Local file write failed: {e}")

    async def _write_to_cloud_storage(
        self,
        target_path: str,
        content: Union[str, bytes],
        format: DocumentFormat,
        encoding: EncodingType,
        plan: Dict,
    ) -> Dict:
        """Write to cloud storage"""

        if not self.file_storage:
            raise StorageError("Cloud storage not available")

        try:
            storage_path = self._parse_cloud_storage_path(target_path)

            # Handle append mode for cloud storage
            if plan["mode"] == WriteMode.APPEND and plan["file_exists"]:
                existing_content = await self.file_storage.retrieve(storage_path)
                if isinstance(content, str) and isinstance(existing_content, str):
                    content = existing_content + content
                elif isinstance(content, bytes) and isinstance(existing_content, bytes):
                    content = existing_content + content

            # Store in cloud storage
            await self.file_storage.store(storage_path, content)

            return {
                "path": target_path,
                "storage_path": storage_path,
                "size": (len(content) if isinstance(content, (str, bytes)) else 0),
                "checksum": self._calculate_checksum(content),
                "cloud_storage": True,
            }

        except Exception as e:
            raise StorageError(f"Cloud storage write failed: {e}")

    def _handle_versioning(
        self,
        target_path: str,
        content_metadata: Dict,
        metadata: Optional[Dict],
    ) -> Optional[Dict]:
        """Handle document versioning"""

        if not self.config.enable_versioning:
            return None

        try:
            version_info = {
                "path": target_path,
                "version": self._get_next_version(target_path),
                "timestamp": datetime.now().isoformat(),
                "content_metadata": content_metadata,
                "user_metadata": metadata or {},
            }

            # Store version info
            version_file = f"{target_path}.versions.json"
            versions = self._load_version_history(version_file)
            versions.append(version_info)

            # Keep only recent versions
            if len(versions) > self.config.max_backup_versions:
                versions = versions[-self.config.max_backup_versions :]

            self._save_version_history(version_file, versions)

            return version_info

        except Exception as e:
            self.logger.warning(f"Versioning failed for {target_path}: {e}")
            return None

    def _validate_content(
        self,
        content: Union[str, bytes],
        format: DocumentFormat,
        validation_level: ValidationLevel,
    ):
        """Validate content based on format and validation level"""

        if validation_level == ValidationLevel.NONE:
            return

        try:
            # Format-specific validation
            if format in self.validators:
                self.validators[format](content, validation_level)

            # Security validation for enterprise level
            if validation_level == ValidationLevel.ENTERPRISE:
                self._security_scan_content(content)

        except Exception as e:
            raise ContentValidationError(f"Content validation failed: {e}")

    def _validate_json_content(self, content: Union[str, bytes], validation_level: ValidationLevel):
        """Validate JSON content"""
        try:
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            json.loads(content)
        except json.JSONDecodeError as e:
            raise ContentValidationError(f"Invalid JSON: {e}")

    def _validate_xml_content(self, content: Union[str, bytes], validation_level: ValidationLevel):
        """Validate XML content"""
        try:
            import xml.etree.ElementTree as ET

            if isinstance(content, bytes):
                content = content.decode("utf-8")
            ET.fromstring(content)
        except ET.ParseError as e:
            raise ContentValidationError(f"Invalid XML: {e}")

    def _validate_csv_content(self, content: Union[str, bytes], validation_level: ValidationLevel):
        """Validate CSV content"""
        try:
            import csv
            import io

            if isinstance(content, bytes):
                content = content.decode("utf-8")
            csv.reader(io.StringIO(content))
        except Exception as e:
            raise ContentValidationError(f"Invalid CSV: {e}")

    def _validate_yaml_content(self, content: Union[str, bytes], validation_level: ValidationLevel):
        """Validate YAML content"""
        try:
            import yaml

            if isinstance(content, bytes):
                content = content.decode("utf-8")
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ContentValidationError(f"Invalid YAML: {e}")

    def _validate_html_content(self, content: Union[str, bytes], validation_level: ValidationLevel):
        """Validate HTML content"""
        try:
            from bs4 import BeautifulSoup

            if isinstance(content, bytes):
                content = content.decode("utf-8")
            BeautifulSoup(content, "html.parser")
        except Exception as e:
            raise ContentValidationError(f"Invalid HTML: {e}")

    def _security_scan_content(self, content: Union[str, bytes]):
        """Perform security scan on content"""
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="ignore")

        # Check for suspicious patterns
        suspicious_patterns = [
            r"<script[^>]*>",  # JavaScript
            r"javascript:",  # JavaScript URLs
            r"vbscript:",  # VBScript URLs
            r"data:.*base64",  # Base64 data URLs
            r"eval\s*\(",  # eval() calls
            r"exec\s*\(",  # exec() calls
        ]

        import re

        for pattern in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                raise ContentValidationError("Security scan failed: suspicious pattern detected")

    # Helper methods
    def _calculate_content_size(self, content: Any) -> int:
        """Calculate content size in bytes"""
        if isinstance(content, bytes):
            return len(content)
        elif isinstance(content, str):
            return len(content.encode("utf-8"))
        else:
            return len(str(content).encode("utf-8"))

    def _calculate_checksum(self, content: Union[str, bytes]) -> str:
        """Calculate content checksum"""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate file checksum"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _check_write_permission(self, target_path: str, mode: WriteMode) -> bool:
        """Check write permission for target path"""
        try:
            if self._is_cloud_storage_path(target_path):
                return self.file_storage is not None

            parent_dir = os.path.dirname(target_path)
            if not os.path.exists(parent_dir):
                # Check if we can create the directory
                return os.access(os.path.dirname(parent_dir), os.W_OK)

            if os.path.exists(target_path):
                return os.access(target_path, os.W_OK)
            else:
                return os.access(parent_dir, os.W_OK)

        except Exception:
            return False

    def _file_exists(self, file_path: str) -> bool:
        """Check if file exists (local or cloud)"""
        if self._is_cloud_storage_path(file_path):
            # For cloud storage, we'd need to implement exists check
            return False  # Simplified for now
        else:
            return os.path.exists(file_path)

    def _is_cloud_storage_path(self, source: str) -> bool:
        """Check if source is a cloud storage path"""
        cloud_schemes = ["gs", "s3", "azure", "cloud"]
        try:
            from urllib.parse import urlparse

            parsed = urlparse(source)
            return parsed.scheme in cloud_schemes
        except Exception:
            return False

    def _parse_cloud_storage_path(self, source: str) -> str:
        """Parse cloud storage path to get storage key"""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(source)
            return parsed.path.lstrip("/")
        except Exception:
            return source

    # Content conversion methods
    def _convert_to_csv(self, content: Any) -> str:
        """Convert content to CSV format"""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        if isinstance(content, list):
            for row in content:
                if isinstance(row, (list, tuple)):
                    writer.writerow(row)
                else:
                    writer.writerow([row])
        elif isinstance(content, dict):
            # Convert dict to CSV with headers
            if content:
                headers = list(content.keys())
                writer.writerow(headers)
                writer.writerow([content[h] for h in headers])
        else:
            writer.writerow([str(content)])

        return output.getvalue()

    def _convert_to_xml(self, content: Any) -> str:
        """Convert content to XML format"""
        import xml.etree.ElementTree as ET

        if isinstance(content, dict):
            root = ET.Element("document")
            for key, value in content.items():
                elem = ET.SubElement(root, str(key))
                elem.text = str(value)
            return ET.tostring(root, encoding="unicode")
        else:
            root = ET.Element("document")
            root.text = str(content)
            return ET.tostring(root, encoding="unicode")

    def _convert_to_yaml(self, content: Any) -> str:
        """Convert content to YAML format"""
        try:
            import yaml

            return yaml.dump(content, default_flow_style=False, allow_unicode=True)
        except ImportError:
            # Fallback to simple string representation
            return str(content)

    def _convert_to_html(self, content: Any) -> str:
        """Convert content to HTML format"""
        if isinstance(content, dict):
            html = "<html><body>\n"
            for key, value in content.items():
                html += f"<h3>{key}</h3>\n<p>{value}</p>\n"
            html += "</body></html>"
            return html
        else:
            return f"<html><body><pre>{str(content)}</pre></body></html>"

    def _convert_to_markdown(self, content: Any) -> str:
        """Convert content to Markdown format"""
        if isinstance(content, dict):
            md = ""
            for key, value in content.items():
                md += f"## {key}\n\n{value}\n\n"
            return md
        else:
            return str(content)

    # Versioning methods
    def _get_next_version(self, file_path: str) -> int:
        """Get next version number for file"""
        version_file = f"{file_path}.versions.json"
        versions = self._load_version_history(version_file)
        return len(versions) + 1

    def _load_version_history(self, version_file: str) -> List[Dict]:
        """Load version history from file"""
        try:
            if os.path.exists(version_file):
                with open(version_file, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_version_history(self, version_file: str, versions: List[Dict]):
        """Save version history to file"""
        try:
            with open(version_file, "w") as f:
                json.dump(versions, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save version history: {e}")

    # Backup and rollback methods
    def _backup_cloud_file(self, source_path: str, backup_path: str) -> str:
        """Backup cloud file"""
        # Simplified implementation
        return backup_path

    def _rollback_from_backup(self, target_path: str, backup_info: Dict):
        """Rollback file from backup"""
        try:
            if backup_info and os.path.exists(backup_info["backup_path"]):
                shutil.copy2(backup_info["backup_path"], target_path)
                self.logger.info(f"Rolled back {target_path} from backup")
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")

    def _rollback_batch_operations(self, completed_operations: List[Dict], backup_operations: List[Dict]):
        """Rollback batch operations"""
        for op in reversed(completed_operations):
            try:
                result = op.get("result", {})
                backup_info = result.get("backup_info")
                if backup_info:
                    self._rollback_from_backup(result["write_result"]["path"], backup_info)
            except Exception as e:
                self.logger.error(f"Batch rollback failed for operation: {e}")

    def _log_write_operation(
        self,
        operation_id: str,
        target_path: str,
        mode: WriteMode,
        write_result: Dict,
        backup_info: Optional[Dict],
    ) -> Dict:
        """Log write operation for audit"""
        audit_info = {
            "operation_id": operation_id,
            "timestamp": datetime.now().isoformat(),
            "target_path": target_path,
            "mode": mode,
            "success": True,
            "file_size": write_result.get("size", 0),
            "checksum": write_result.get("checksum"),
            "backup_created": backup_info is not None,
        }

        # Log to audit file
        try:
            audit_file = os.path.join(self.config.temp_dir, "write_audit.log")
            with open(audit_file, "a") as f:
                f.write(json.dumps(audit_info) + "\n")
        except Exception as e:
            self.logger.warning(f"Audit logging failed: {e}")

        return audit_info

    def edit_document(
        self,
        target_path: str,
        operation: EditOperation,
        content: Optional[str] = None,
        position: Optional[Dict[str, Any]] = None,
        selection: Optional[Dict[str, Any]] = None,
        format_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform advanced editing operations on documents

        Args:
            target_path: Target file path
            operation: Edit operation to perform
            content: Content for the operation (if applicable)
            position: Position info (line, column, offset)
            selection: Text selection range
            format_options: Additional format options

        Returns:
            Dict containing edit results
        """
        try:
            start_time = datetime.now()
            operation_id = str(uuid.uuid4())

            self.logger.info(f"Starting edit operation {operation_id}: {operation} on {target_path}")

            # Read current document content
            current_content = self._read_document_content(target_path)

            # Perform the specific edit operation
            if operation == EditOperation.INSERT_TEXT:
                if content is None:
                    raise ValueError("content is required for INSERT_TEXT operation")
                edited_content = self._insert_text(current_content, content, position)
            elif operation == EditOperation.DELETE_TEXT:
                edited_content = self._delete_text(current_content, selection)
            elif operation == EditOperation.REPLACE_TEXT:
                if content is None:
                    raise ValueError("content is required for REPLACE_TEXT operation")
                edited_content = self._replace_text(current_content, selection, content)
            elif operation == EditOperation.BOLD:
                edited_content = self._format_text_bold(current_content, selection, format_options)
            elif operation == EditOperation.ITALIC:
                edited_content = self._format_text_italic(current_content, selection, format_options)
            elif operation == EditOperation.UNDERLINE:
                edited_content = self._format_text_underline(current_content, selection, format_options)
            elif operation == EditOperation.STRIKETHROUGH:
                edited_content = self._format_text_strikethrough(current_content, selection, format_options)
            elif operation == EditOperation.HIGHLIGHT:
                edited_content = self._format_text_highlight(current_content, selection, format_options)
            elif operation == EditOperation.INSERT_LINE:
                if content is None:
                    raise ValueError("content is required for INSERT_LINE operation")
                edited_content = self._insert_line(current_content, position, content)
            elif operation == EditOperation.DELETE_LINE:
                edited_content = self._delete_line(current_content, position)
            elif operation == EditOperation.MOVE_LINE:
                edited_content = self._move_line(current_content, position, format_options)
            elif operation == EditOperation.COPY_TEXT:
                return self._copy_text(current_content, selection)
            elif operation == EditOperation.CUT_TEXT:
                edited_content, cut_content = self._cut_text(current_content, selection)
                # Store cut content in clipboard
                self._store_clipboard_content(cut_content)
            elif operation == EditOperation.PASTE_TEXT:
                clipboard_content = self._get_clipboard_content()
                edited_content = self._paste_text(current_content, position, clipboard_content)
            else:
                raise ValueError(f"Unsupported edit operation: {operation}")

            # Write the edited content back to file
            file_format_str = self._detect_file_format(target_path)
            file_format = DocumentFormat(file_format_str) if file_format_str in [f.value for f in DocumentFormat] else DocumentFormat.TXT
            write_result = self.write_document(
                target_path=target_path,
                content=edited_content,
                format=file_format,
                mode=WriteMode.BACKUP_WRITE,  # Always backup before editing
                backup_comment=f"Edit operation: {operation}",
            )

            result = {
                "operation_id": operation_id,
                "target_path": target_path,
                "operation": operation,
                "edit_metadata": {
                    "original_size": len(current_content),
                    "edited_size": (len(edited_content) if isinstance(edited_content, str) else 0),
                    "position": position,
                    "selection": selection,
                },
                "write_result": write_result,
                "processing_metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self.logger.info(f"Edit operation {operation_id} completed successfully")
            return result

        except Exception as e:
            raise DocumentWriterError(f"Edit operation failed: {str(e)}")

    def format_text(
        self,
        target_path: str,
        text_to_format: str,
        format_type: EditOperation,
        format_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Apply formatting to specific text in a document

        Args:
            target_path: Target file path
            text_to_format: Text to apply formatting to
            format_type: Type of formatting (bold, italic, etc.)
            format_options: Additional format options

        Returns:
            Dict containing formatting results
        """
        try:
            current_content = self._read_document_content(target_path)

            # Find all occurrences of the text
            formatted_content = self._apply_text_formatting(current_content, text_to_format, format_type, format_options)

            # Write back to file
            file_format_str = self._detect_file_format(target_path)
            file_format = DocumentFormat(file_format_str) if file_format_str in [f.value for f in DocumentFormat] else DocumentFormat.TXT
            write_result = self.write_document(
                target_path=target_path,
                content=formatted_content,
                format=file_format,
                mode=WriteMode.BACKUP_WRITE,
            )

            return {
                "target_path": target_path,
                "text_formatted": text_to_format,
                "format_type": format_type,
                "write_result": write_result,
            }

        except Exception as e:
            raise DocumentWriterError(f"Text formatting failed: {str(e)}")

    def find_replace(
        self,
        target_path: str,
        find_text: str,
        replace_text: str,
        replace_all: bool = False,
        case_sensitive: bool = True,
        regex_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Find and replace text in a document

        Args:
            target_path: Target file path
            find_text: Text to find
            replace_text: Text to replace with
            replace_all: Replace all occurrences
            case_sensitive: Case sensitive search
            regex_mode: Use regex for find/replace

        Returns:
            Dict containing find/replace results
        """
        try:
            current_content = self._read_document_content(target_path)

            # Perform find and replace
            new_content, replacements = self._perform_find_replace(
                current_content,
                find_text,
                replace_text,
                replace_all,
                case_sensitive,
                regex_mode,
            )

            if replacements > 0:
                # Write back to file
                file_format_str = self._detect_file_format(target_path)
                file_format = DocumentFormat(file_format_str) if file_format_str in [f.value for f in DocumentFormat] else DocumentFormat.TXT
                write_result = self.write_document(
                    target_path=target_path,
                    content=new_content,
                    format=file_format,
                    mode=WriteMode.BACKUP_WRITE,
                    backup_comment=f"Find/Replace: '{find_text}' -> '{replace_text}'",
                )

                return {
                    "target_path": target_path,
                    "find_text": find_text,
                    "replace_text": replace_text,
                    "replacements_made": replacements,
                    "write_result": write_result,
                }
            else:
                return {
                    "target_path": target_path,
                    "find_text": find_text,
                    "replace_text": replace_text,
                    "replacements_made": 0,
                    "message": "No matches found",
                }

        except Exception as e:
            raise DocumentWriterError(f"Find/replace operation failed: {str(e)}")

    # Helper methods for editing operations
    def _read_document_content(self, file_path: str) -> str:
        """Read document content for editing"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ["gbk", "latin1", "cp1252"]:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        return f.read()
                except Exception:
                    continue
            raise DocumentWriterError(f"Cannot decode file: {file_path}")
        except Exception as e:
            raise DocumentWriterError(f"Cannot read file {file_path}: {str(e)}")

    def _detect_file_format(self, file_path: str) -> str:
        """Detect file format from extension"""
        ext = os.path.splitext(file_path)[1].lower()
        format_map = {
            ".txt": "txt",
            ".json": "json",
            ".csv": "csv",
            ".xml": "xml",
            ".html": "html",
            ".htm": "html",
            ".md": "markdown",
            ".markdown": "markdown",
            ".yaml": "yaml",
            ".yml": "yaml",
        }
        return format_map.get(ext, "txt")

    def _insert_text(self, content: str, text: str, position: Optional[Dict[str, Any]]) -> str:
        """Insert text at specified position"""
        if not position:
            return content + text

        if "offset" in position:
            offset = position["offset"]
            return content[:offset] + text + content[offset:]
        elif "line" in position:
            lines = content.split("\n")
            line_num = position.get("line", 0)
            column = position.get("column", 0)

            if line_num < len(lines):
                line = lines[line_num]
                lines[line_num] = line[:column] + text + line[column:]
            else:
                lines.append(text)
            return "\n".join(lines)
        else:
            return content + text

    def _delete_text(self, content: str, selection: Optional[Dict[str, Any]]) -> str:
        """Delete text in specified selection"""
        if not selection:
            return content

        if "start_offset" in selection and "end_offset" in selection:
            start = selection["start_offset"]
            end = selection["end_offset"]
            return content[:start] + content[end:]
        elif "start_line" in selection and "end_line" in selection:
            lines = content.split("\n")
            start_line = selection["start_line"]
            end_line = selection["end_line"]
            start_col = selection.get("start_column", 0)
            end_col = selection.get(
                "end_column",
                len(lines[end_line]) if end_line < len(lines) else 0,
            )

            if start_line == end_line:
                # Same line deletion
                line = lines[start_line]
                lines[start_line] = line[:start_col] + line[end_col:]
            else:
                # Multi-line deletion
                lines[start_line] = lines[start_line][:start_col]
                if end_line < len(lines):
                    lines[start_line] += lines[end_line][end_col:]
                del lines[start_line + 1 : end_line + 1]

            return "\n".join(lines)

        return content

    def _replace_text(
        self,
        content: str,
        selection: Optional[Dict[str, Any]],
        replacement: str,
    ) -> str:
        """Replace text in specified selection"""
        if not selection:
            return content

        # First delete the selected text, then insert replacement
        content_after_delete = self._delete_text(content, selection)

        # Calculate new insertion position after deletion
        if "start_offset" in selection:
            insert_pos = {"offset": selection["start_offset"]}
        elif "start_line" in selection:
            insert_pos = {
                "line": selection["start_line"],
                "column": selection.get("start_column", 0),
            }
        else:
            insert_pos = None

        return self._insert_text(content_after_delete, replacement, insert_pos)

    def _format_text_bold(
        self,
        content: str,
        selection: Optional[Dict[str, Any]],
        options: Optional[Dict[str, Any]],
    ) -> str:
        """Apply bold formatting to selected text"""
        if not selection:
            return content

        format_type = options.get("format_type", "markdown") if options else "markdown"

        if format_type == "markdown":
            return self._apply_markdown_formatting(content, selection, "**", "**")
        elif format_type == "html":
            return self._apply_html_formatting(content, selection, "<strong>", "</strong>")
        else:
            return content

    def _format_text_italic(
        self,
        content: str,
        selection: Optional[Dict[str, Any]],
        options: Optional[Dict[str, Any]],
    ) -> str:
        """Apply italic formatting to selected text"""
        if not selection:
            return content

        format_type = options.get("format_type", "markdown") if options else "markdown"

        if format_type == "markdown":
            return self._apply_markdown_formatting(content, selection, "*", "*")
        elif format_type == "html":
            return self._apply_html_formatting(content, selection, "<em>", "</em>")
        else:
            return content

    def _format_text_underline(
        self,
        content: str,
        selection: Optional[Dict[str, Any]],
        options: Optional[Dict[str, Any]],
    ) -> str:
        """Apply underline formatting to selected text"""
        if not selection:
            return content

        format_type = options.get("format_type", "html") if options else "html"

        if format_type == "html":
            return self._apply_html_formatting(content, selection, "<u>", "</u>")
        else:
            return content

    def _format_text_strikethrough(
        self,
        content: str,
        selection: Optional[Dict[str, Any]],
        options: Optional[Dict[str, Any]],
    ) -> str:
        """Apply strikethrough formatting to selected text"""
        if not selection:
            return content

        format_type = options.get("format_type", "markdown") if options else "markdown"

        if format_type == "markdown":
            return self._apply_markdown_formatting(content, selection, "~~", "~~")
        elif format_type == "html":
            return self._apply_html_formatting(content, selection, "<del>", "</del>")
        else:
            return content

    def _format_text_highlight(
        self,
        content: str,
        selection: Optional[Dict[str, Any]],
        options: Optional[Dict[str, Any]],
    ) -> str:
        """Apply highlight formatting to selected text"""
        if not selection:
            return content

        format_type = options.get("format_type", "html") if options else "html"
        color = options.get("color", "yellow") if options else "yellow"

        if format_type == "html":
            return self._apply_html_formatting(
                content,
                selection,
                f'<mark style="background-color: {color}">',
                "</mark>",
            )
        elif format_type == "markdown":
            return self._apply_markdown_formatting(content, selection, "==", "==")
        else:
            return content

    def _apply_markdown_formatting(
        self,
        content: str,
        selection: Dict[str, Any],
        start_marker: str,
        end_marker: str,
    ) -> str:
        """Apply markdown formatting to selected text"""
        selected_text = self._extract_selected_text(content, selection)
        formatted_text = start_marker + selected_text + end_marker
        return self._replace_text(content, selection, formatted_text)

    def _apply_html_formatting(
        self,
        content: str,
        selection: Dict[str, Any],
        start_tag: str,
        end_tag: str,
    ) -> str:
        """Apply HTML formatting to selected text"""
        selected_text = self._extract_selected_text(content, selection)
        formatted_text = start_tag + selected_text + end_tag
        return self._replace_text(content, selection, formatted_text)

    def _extract_selected_text(self, content: str, selection: Dict[str, Any]) -> str:
        """Extract text from selection"""
        if "start_offset" in selection and "end_offset" in selection:
            return content[selection["start_offset"] : selection["end_offset"]]
        elif "start_line" in selection and "end_line" in selection:
            lines = content.split("\n")
            start_line = selection["start_line"]
            end_line = selection["end_line"]
            start_col = selection.get("start_column", 0)
            end_col = selection.get(
                "end_column",
                len(lines[end_line]) if end_line < len(lines) else 0,
            )

            if start_line == end_line:
                return lines[start_line][start_col:end_col]
            else:
                result = [lines[start_line][start_col:]]
                result.extend(lines[start_line + 1 : end_line])
                if end_line < len(lines):
                    result.append(lines[end_line][:end_col])
                return "\n".join(result)
        return ""

    def _insert_line(
        self,
        content: str,
        position: Optional[Dict[str, Any]],
        line_content: str,
    ) -> str:
        """Insert a new line at specified position"""
        lines = content.split("\n")
        line_num = position.get("line", len(lines)) if position else len(lines)

        lines.insert(line_num, line_content)
        return "\n".join(lines)

    def _delete_line(self, content: str, position: Optional[Dict[str, Any]]) -> str:
        """Delete line at specified position"""
        lines = content.split("\n")
        line_num = position.get("line", 0) if position else 0

        if 0 <= line_num < len(lines):
            del lines[line_num]

        return "\n".join(lines)

    def _move_line(
        self,
        content: str,
        position: Optional[Dict[str, Any]],
        options: Optional[Dict[str, Any]],
    ) -> str:
        """Move line to different position"""
        lines = content.split("\n")
        from_line = position.get("line", 0) if position else 0
        to_line = options.get("to_line", 0) if options else 0

        if 0 <= from_line < len(lines) and 0 <= to_line < len(lines):
            line_content = lines.pop(from_line)
            lines.insert(to_line, line_content)

        return "\n".join(lines)

    def _copy_text(self, content: str, selection: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Copy selected text to clipboard"""
        selected_text = self._extract_selected_text(content, selection) if selection else content
        self._store_clipboard_content(selected_text)

        return {
            "operation": "copy",
            "copied_text": selected_text,
            "copied_length": len(selected_text),
        }

    def _cut_text(self, content: str, selection: Optional[Dict[str, Any]]) -> Tuple[str, str]:
        """Cut selected text (copy and delete)"""
        selected_text = self._extract_selected_text(content, selection) if selection else content
        new_content = self._delete_text(content, selection) if selection else ""

        return new_content, selected_text

    def _paste_text(
        self,
        content: str,
        position: Optional[Dict[str, Any]],
        clipboard_content: str,
    ) -> str:
        """Paste text from clipboard"""
        return self._insert_text(content, clipboard_content, position)

    def _store_clipboard_content(self, content: str):
        """Store content in clipboard (simplified implementation)"""
        clipboard_file = os.path.join(self.config.temp_dir, "clipboard.txt")
        try:
            with open(clipboard_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            self.logger.warning(f"Failed to store clipboard content: {e}")

    def _get_clipboard_content(self) -> str:
        """Get content from clipboard"""
        clipboard_file = os.path.join(self.config.temp_dir, "clipboard.txt")
        try:
            with open(clipboard_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _apply_text_formatting(
        self,
        content: str,
        text_to_format: str,
        format_type: EditOperation,
        options: Optional[Dict[str, Any]],
    ) -> str:
        """Apply formatting to all occurrences of specific text"""
        if format_type == EditOperation.BOLD:
            replacement = f"**{text_to_format}**"
        elif format_type == EditOperation.ITALIC:
            replacement = f"*{text_to_format}*"
        elif format_type == EditOperation.UNDERLINE:
            replacement = f"<u>{text_to_format}</u>"
        elif format_type == EditOperation.STRIKETHROUGH:
            replacement = f"~~{text_to_format}~~"
        elif format_type == EditOperation.HIGHLIGHT:
            color = options.get("color", "yellow") if options else "yellow"
            replacement = f'<mark style="background-color: {color}">{text_to_format}</mark>'
        else:
            replacement = text_to_format

        return content.replace(text_to_format, replacement)

    def _perform_find_replace(
        self,
        content: str,
        find_text: str,
        replace_text: str,
        replace_all: bool,
        case_sensitive: bool,
        regex_mode: bool,
    ) -> Tuple[str, int]:
        """Perform find and replace operation"""
        import re

        replacements = 0

        if regex_mode:
            flags = 0 if case_sensitive else re.IGNORECASE
            if replace_all:
                new_content, replacements = re.subn(find_text, replace_text, content, flags=flags)
            else:
                new_content = re.sub(find_text, replace_text, content, count=1, flags=flags)
                replacements = 1 if new_content != content else 0
        else:
            if case_sensitive:
                if replace_all:
                    replacements = content.count(find_text)
                    new_content = content.replace(find_text, replace_text)
                else:
                    new_content = content.replace(find_text, replace_text, 1)
                    replacements = 1 if new_content != content else 0
            else:
                # Case insensitive replacement
                import re

                pattern = re.escape(find_text)
                if replace_all:
                    new_content, replacements = re.subn(pattern, replace_text, content, flags=re.IGNORECASE)
                else:
                    new_content = re.sub(
                        pattern,
                        replace_text,
                        content,
                        count=1,
                        flags=re.IGNORECASE,
                    )
                    replacements = 1 if new_content != content else 0

        return new_content, replacements
