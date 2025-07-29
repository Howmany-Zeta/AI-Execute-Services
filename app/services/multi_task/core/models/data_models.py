"""
Data Models

Data models for storage and persistence operations in the multi-task service.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum


class StorageType(Enum):
    """Storage type enumeration."""
    FILE_SYSTEM = "file_system"
    CLOUD_STORAGE = "cloud_storage"
    DATABASE = "database"
    CACHE = "cache"
    MEMORY = "memory"


class CompressionType(Enum):
    """Compression type enumeration."""
    NONE = "none"
    GZIP = "gzip"
    BZIP2 = "bzip2"
    LZ4 = "lz4"
    ZSTD = "zstd"


class EncryptionType(Enum):
    """Encryption type enumeration."""
    NONE = "none"
    AES_256 = "aes_256"
    RSA = "rsa"
    CHACHA20 = "chacha20"


class DataFormat(Enum):
    """Data format enumeration."""
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    CSV = "csv"
    PARQUET = "parquet"
    PICKLE = "pickle"
    BINARY = "binary"
    TEXT = "text"


class StorageMetadata(BaseModel):
    """
    Metadata for stored data.
    """
    # Basic information
    key: str = Field(..., description="Storage key")
    storage_type: StorageType = Field(default=StorageType.FILE_SYSTEM, description="Storage type for strategy selection")
    size_bytes: Optional[int] = Field(None, description="Data size in bytes")
    content_type: Optional[str] = Field(None, description="MIME content type")
    data_format: DataFormat = Field(default=DataFormat.JSON, description="Data format")
    cache_ttl: Optional[int] = Field(None, description="Cache time-to-live in seconds")

    # Compression and encryption
    compression_type: CompressionType = Field(default=CompressionType.NONE, description="Compression type")
    encryption_type: EncryptionType = Field(default=EncryptionType.NONE, description="Encryption type")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    accessed_at: Optional[datetime] = Field(None, description="Last access timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")

    # Versioning
    version: str = Field(default="1.0.0", description="Data version")
    checksum: Optional[str] = Field(None, description="Data checksum")

    # Tags and labels
    tags: List[str] = Field(default_factory=list, description="Data tags")
    labels: Dict[str, str] = Field(default_factory=dict, description="Data labels")

    # Custom metadata
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StorageConfig(BaseModel):
    """
    Configuration for storage operations.
    """
    # Storage settings
    storage_type: StorageType = Field(..., description="Type of storage")
    base_path: Optional[str] = Field(None, description="Base storage path")
    bucket_name: Optional[str] = Field(None, description="Cloud storage bucket name")

    # Connection settings
    connection_string: Optional[str] = Field(None, description="Storage connection string")
    credentials: Optional[Dict[str, Any]] = Field(None, description="Storage credentials")

    # Performance settings
    max_connections: int = Field(default=10, description="Maximum concurrent connections")
    timeout_seconds: int = Field(default=30, description="Operation timeout")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")

    # Compression and encryption
    default_compression: CompressionType = Field(default=CompressionType.NONE, description="Default compression")
    default_encryption: EncryptionType = Field(default=EncryptionType.NONE, description="Default encryption")

    # Caching
    enable_cache: bool = Field(default=True, description="Enable caching")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")

    # Backup and retention
    enable_backup: bool = Field(default=False, description="Enable automatic backup")
    backup_interval_hours: int = Field(default=24, description="Backup interval in hours")
    retention_days: int = Field(default=30, description="Data retention in days")

    class Config:
        use_enum_values = True


class DataRecord(BaseModel):
    """
    A record representing stored data.
    """
    # Identification
    record_id: str = Field(..., description="Unique record identifier")
    key: str = Field(..., description="Storage key")

    # Data
    data: Union[str, bytes, Dict[str, Any]] = Field(..., description="Stored data")
    metadata: StorageMetadata = Field(..., description="Storage metadata")

    # Status
    is_active: bool = Field(default=True, description="Whether record is active")
    is_compressed: bool = Field(default=False, description="Whether data is compressed")
    is_encrypted: bool = Field(default=False, description="Whether data is encrypted")

    # Relationships
    parent_record_id: Optional[str] = Field(None, description="Parent record ID")
    child_record_ids: List[str] = Field(default_factory=list, description="Child record IDs")

    # Audit trail
    created_by: Optional[str] = Field(None, description="Creator user ID")
    updated_by: Optional[str] = Field(None, description="Last updater user ID")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StorageOperation(BaseModel):
    """
    A storage operation record.
    """
    # Identification
    operation_id: str = Field(..., description="Unique operation identifier")
    operation_type: str = Field(..., description="Type of operation (store, retrieve, delete, etc.)")

    # Target
    storage_key: str = Field(..., description="Target storage key")
    storage_type: StorageType = Field(..., description="Storage type")

    # Status
    status: str = Field(..., description="Operation status")
    success: bool = Field(..., description="Whether operation was successful")

    # Performance metrics
    duration_ms: Optional[float] = Field(None, description="Operation duration in milliseconds")
    data_size_bytes: Optional[int] = Field(None, description="Data size in bytes")

    # Error information
    error_code: Optional[str] = Field(None, description="Error code if operation failed")
    error_message: Optional[str] = Field(None, description="Error message if operation failed")

    # Context
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    execution_id: Optional[str] = Field(None, description="Execution ID")

    # Timestamps
    started_at: datetime = Field(..., description="Operation start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Operation completion timestamp")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BackupRecord(BaseModel):
    """
    A backup record.
    """
    # Identification
    backup_id: str = Field(..., description="Unique backup identifier")
    backup_name: str = Field(..., description="Human-readable backup name")

    # Source information
    source_keys: List[str] = Field(..., description="Source storage keys")
    source_storage_type: StorageType = Field(..., description="Source storage type")

    # Backup information
    backup_location: str = Field(..., description="Backup storage location")
    backup_size_bytes: Optional[int] = Field(None, description="Backup size in bytes")

    # Compression and encryption
    compression_type: CompressionType = Field(default=CompressionType.GZIP, description="Backup compression")
    encryption_type: EncryptionType = Field(default=EncryptionType.NONE, description="Backup encryption")

    # Status
    status: str = Field(..., description="Backup status")
    success: bool = Field(..., description="Whether backup was successful")

    # Verification
    checksum: Optional[str] = Field(None, description="Backup checksum")
    verified: bool = Field(default=False, description="Whether backup was verified")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Backup creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Backup expiration timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional backup metadata")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CacheEntry(BaseModel):
    """
    A cache entry record.
    """
    # Identification
    cache_key: str = Field(..., description="Cache key")
    namespace: Optional[str] = Field(None, description="Cache namespace")

    # Data
    data: Union[str, bytes, Dict[str, Any]] = Field(..., description="Cached data")
    data_type: str = Field(..., description="Type of cached data")

    # Cache settings
    ttl_seconds: Optional[int] = Field(None, description="Time to live in seconds")
    priority: int = Field(default=1, description="Cache priority (1=low, 5=high)")

    # Status
    is_compressed: bool = Field(default=False, description="Whether data is compressed")
    hit_count: int = Field(default=0, description="Number of cache hits")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Cache entry creation timestamp")
    accessed_at: datetime = Field(default_factory=datetime.utcnow, description="Last access timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Cache tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DataIndex(BaseModel):
    """
    A data index for efficient querying.
    """
    # Identification
    index_id: str = Field(..., description="Unique index identifier")
    index_name: str = Field(..., description="Human-readable index name")

    # Index configuration
    indexed_fields: List[str] = Field(..., description="Fields included in the index")
    index_type: str = Field(..., description="Type of index (btree, hash, etc.)")

    # Storage information
    storage_keys: List[str] = Field(..., description="Storage keys covered by this index")
    index_size_bytes: Optional[int] = Field(None, description="Index size in bytes")

    # Performance metrics
    query_count: int = Field(default=0, description="Number of queries using this index")
    avg_query_time_ms: Optional[float] = Field(None, description="Average query time in milliseconds")

    # Status
    is_active: bool = Field(default=True, description="Whether index is active")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional index metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
