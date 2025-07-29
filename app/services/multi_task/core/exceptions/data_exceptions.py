"""
Data Layer Exceptions

Exception classes for data layer operations in the multi-task service.
"""

from typing import Optional, Dict, Any


class DataException(Exception):
    """Base exception for all data layer operations."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "DATA_ERROR"
        self.details = details or {}


class DataRepositoryError(DataException):
    """Exception raised when repository operations fail."""

    def __init__(self, message: str, repository_type: Optional[str] = None, operation: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="REPOSITORY_ERROR", **kwargs)
        self.repository_type = repository_type
        self.operation = operation


class DataValidationError(DataException):
    """Exception raised when data validation fails."""

    def __init__(self, message: str, field_name: Optional[str] = None, validation_rule: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_VALIDATION_ERROR", **kwargs)
        self.field_name = field_name
        self.validation_rule = validation_rule


class DataSerializationError(DataException):
    """Exception raised when data serialization/deserialization fails."""

    def __init__(self, message: str, data_type: Optional[str] = None, serializer: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="SERIALIZATION_ERROR", **kwargs)
        self.data_type = data_type
        self.serializer = serializer


class StorageError(DataException):
    """Exception raised when storage operations fail."""

    def __init__(self, message: str, storage_type: Optional[str] = None, operation: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="STORAGE_ERROR", **kwargs)
        self.storage_type = storage_type
        self.operation = operation


class StorageConnectionError(StorageError):
    """Exception raised when storage connection fails."""

    def __init__(self, message: str, storage_type: Optional[str] = None, **kwargs):
        super().__init__(message, storage_type=storage_type, operation="connect", error_code="STORAGE_CONNECTION_ERROR", **kwargs)


class StorageTimeoutError(StorageError):
    """Exception raised when storage operations timeout."""

    def __init__(self, message: str, timeout_seconds: Optional[float] = None, **kwargs):
        super().__init__(message, error_code="STORAGE_TIMEOUT_ERROR", **kwargs)
        self.timeout_seconds = timeout_seconds


class StorageQuotaExceededError(StorageError):
    """Exception raised when storage quota is exceeded."""

    def __init__(self, message: str, quota_limit: Optional[str] = None, current_usage: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="STORAGE_QUOTA_EXCEEDED", **kwargs)
        self.quota_limit = quota_limit
        self.current_usage = current_usage


class DataNotFoundError(DataException):
    """Exception raised when requested data is not found."""

    def __init__(self, message: str, entity_id: Optional[str] = None, entity_type: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_NOT_FOUND", **kwargs)
        self.entity_id = entity_id
        self.entity_type = entity_type


class DataConflictError(DataException):
    """Exception raised when data conflicts occur (e.g., duplicate keys)."""

    def __init__(self, message: str, conflicting_field: Optional[str] = None, conflicting_value: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_CONFLICT", **kwargs)
        self.conflicting_field = conflicting_field
        self.conflicting_value = conflicting_value


class DataIntegrityError(DataException):
    """Exception raised when data integrity constraints are violated."""

    def __init__(self, message: str, constraint_type: Optional[str] = None, constraint_name: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_INTEGRITY_ERROR", **kwargs)
        self.constraint_type = constraint_type
        self.constraint_name = constraint_name


class CacheError(DataException):
    """Exception raised when cache operations fail."""

    def __init__(self, message: str, cache_type: Optional[str] = None, operation: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="CACHE_ERROR", **kwargs)
        self.cache_type = cache_type
        self.operation = operation


class CacheConnectionError(CacheError):
    """Exception raised when cache connection fails."""

    def __init__(self, message: str, cache_type: Optional[str] = None, **kwargs):
        super().__init__(message, cache_type=cache_type, operation="connect", error_code="CACHE_CONNECTION_ERROR", **kwargs)


class DataMigrationError(DataException):
    """Exception raised when data migration operations fail."""

    def __init__(self, message: str, migration_version: Optional[str] = None, migration_step: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_MIGRATION_ERROR", **kwargs)
        self.migration_version = migration_version
        self.migration_step = migration_step


class DataBackupError(DataException):
    """Exception raised when data backup operations fail."""

    def __init__(self, message: str, backup_type: Optional[str] = None, backup_location: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_BACKUP_ERROR", **kwargs)
        self.backup_type = backup_type
        self.backup_location = backup_location


class DataRestoreError(DataException):
    """Exception raised when data restore operations fail."""

    def __init__(self, message: str, restore_source: Optional[str] = None, restore_point: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_RESTORE_ERROR", **kwargs)
        self.restore_source = restore_source
        self.restore_point = restore_point


class DataCompressionError(DataException):
    """Exception raised when data compression/decompression fails."""

    def __init__(self, message: str, compression_type: Optional[str] = None, operation: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_COMPRESSION_ERROR", **kwargs)
        self.compression_type = compression_type
        self.operation = operation


class DataEncryptionError(DataException):
    """Exception raised when data encryption/decryption fails."""

    def __init__(self, message: str, encryption_type: Optional[str] = None, operation: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_ENCRYPTION_ERROR", **kwargs)
        self.encryption_type = encryption_type
        self.operation = operation


class SerializationError(DataSerializationError):
    """Exception raised when serialization fails."""
    pass


class DeserializationError(DataSerializationError):
    """Exception raised when deserialization fails."""
    pass


class DataLayerError(DataException):
    """Exception raised for general data layer errors."""

    def __init__(self, message: str, layer: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="DATA_LAYER_ERROR", **kwargs)
        self.layer = layer
