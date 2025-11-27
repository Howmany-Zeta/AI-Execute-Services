"""
File Storage Implementation with Google Cloud Storage

Provides file storage capabilities using Google Cloud Storage as the backend,
with support for local fallback and caching.
"""

import os
import json
import logging
import aiofiles
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import gzip
import pickle

try:
    from google.cloud import storage  # type: ignore[attr-defined]
    from google.cloud.exceptions import NotFound, GoogleCloudError
    from google.auth.exceptions import DefaultCredentialsError

    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    from typing import Any, TYPE_CHECKING
    if TYPE_CHECKING:
        storage: Any  # type: ignore[assignment,no-redef]
        NotFound: Any  # type: ignore[assignment,no-redef]
        GoogleCloudError: Any  # type: ignore[assignment,no-redef]
        DefaultCredentialsError: Any  # type: ignore[assignment,no-redef]
    else:
        storage = None  # type: ignore[assignment]
        NotFound = Exception  # type: ignore[assignment]
        GoogleCloudError = Exception  # type: ignore[assignment]
        DefaultCredentialsError = Exception  # type: ignore[assignment]

from ..monitoring.global_metrics_manager import get_global_metrics

logger = logging.getLogger(__name__)


class FileStorageError(Exception):
    """Base exception for file storage operations."""


class FileStorageConfig:
    """Configuration for file storage."""

    def __init__(self, config: Dict[str, Any]):
        # Google Cloud Storage settings
        self.gcs_bucket_name = config.get("gcs_bucket_name", "multi-task-storage")
        self.gcs_project_id = config.get("gcs_project_id")
        self.gcs_credentials_path = config.get("gcs_credentials_path")
        self.gcs_location = config.get("gcs_location", "US")

        # Local storage fallback
        self.local_storage_path = config.get("local_storage_path", "./storage")
        self.enable_local_fallback = config.get("enable_local_fallback", True)

        # Cache settings
        self.enable_cache = config.get("enable_cache", True)
        self.cache_ttl_seconds = config.get("cache_ttl_seconds", 3600)
        self.max_cache_size_mb = config.get("max_cache_size_mb", 100)

        # Performance settings
        self.chunk_size = config.get("chunk_size", 8192)
        self.max_retries = config.get("max_retries", 3)
        self.timeout_seconds = config.get("timeout_seconds", 30)

        # Compression settings
        self.enable_compression = config.get("enable_compression", True)
        self.compression_threshold_bytes = config.get("compression_threshold_bytes", 1024)

        # Security settings
        self.enable_encryption = config.get("enable_encryption", False)
        self.encryption_key = config.get("encryption_key")


class FileStorage:
    """
    File storage implementation with Google Cloud Storage backend.

    Features:
    - Google Cloud Storage as primary backend
    - Local filesystem fallback
    - In-memory caching with TTL
    - Automatic compression for large files
    - Retry logic with exponential backoff
    - Metrics collection
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = FileStorageConfig(config)
        self._gcs_client = None
        self._gcs_bucket = None
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._initialized = False

        # Metrics - use global metrics manager
        self.metrics = get_global_metrics()

        # Ensure local storage directory exists
        if self.config.enable_local_fallback:
            Path(self.config.local_storage_path).mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """
        Initialize the file storage system.

        Returns:
            True if initialization was successful
        """
        try:
            if GCS_AVAILABLE:
                await self._init_gcs()
            else:
                logger.warning("Google Cloud Storage not available, using local storage only")

            self._initialized = True
            logger.info("File storage initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize file storage: {e}")
            if not self.config.enable_local_fallback:
                raise FileStorageError(f"Storage initialization failed: {e}")

            logger.info("Falling back to local storage only")
            self._initialized = True
            return True

    async def _init_gcs(self):
        """Initialize Google Cloud Storage client."""
        try:
            # Set credentials if provided
            if self.config.gcs_credentials_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.config.gcs_credentials_path

            # Create client - project is required for bucket creation
            # If project_id is None, client will use default project from credentials
            # but we need it for bucket creation API calls
            if not self.config.gcs_project_id:
                logger.warning("GCS project ID not provided. Bucket creation will be disabled.")
                logger.warning("Bucket must exist and be accessible. Falling back to local storage if bucket not found.")

            # Create client with project ID (can be None, but bucket creation
            # will fail)
            self._gcs_client = storage.Client(project=self.config.gcs_project_id)

            # Get or create bucket
            try:
                self._gcs_bucket = self._gcs_client.bucket(self.config.gcs_bucket_name)
                # Test bucket access
                self._gcs_bucket.reload()
                logger.info(f"Connected to GCS bucket: {self.config.gcs_bucket_name}")

            except NotFound:
                # Only create bucket if project_id is provided
                # Bucket creation requires project parameter in API call
                if self.config.gcs_project_id:
                    try:
                        self._gcs_bucket = self._gcs_client.create_bucket(
                            self.config.gcs_bucket_name,
                            project=self.config.gcs_project_id,  # Explicitly pass project parameter
                            location=self.config.gcs_location,
                        )
                        logger.info(f"Created GCS bucket: {self.config.gcs_bucket_name} in project {self.config.gcs_project_id}")
                    except Exception as create_error:
                        logger.error(f"Failed to create GCS bucket {self.config.gcs_bucket_name}: {create_error}")
                        logger.warning("Bucket creation failed. Will use local storage fallback.")
                        self._gcs_bucket = None
                else:
                    logger.error(f"GCS bucket '{self.config.gcs_bucket_name}' not found and " "project ID is not provided. Cannot create bucket without project parameter.")
                    logger.warning("Please ensure the bucket exists or provide DOC_PARSER_GCS_PROJECT_ID in configuration.")
                    logger.warning("Falling back to local storage only.")
                    self._gcs_bucket = None

        except DefaultCredentialsError:
            logger.warning("GCS credentials not found, using local storage only")
            self._gcs_client = None
            self._gcs_bucket = None

        except Exception as e:
            logger.error(f"Failed to initialize GCS: {e}")
            self._gcs_client = None
            self._gcs_bucket = None

    async def store(
        self,
        key: str,
        data: Union[str, bytes, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store data with the given key.

        Args:
            key: Storage key
            data: Data to store
            metadata: Optional metadata

        Returns:
            True if storage was successful
        """
        if not self._initialized:
            await self.initialize()

        start_time = datetime.utcnow()

        try:
            # Serialize data
            serialized_data = await self._serialize_data(data)

            # Compress if enabled and data is large enough
            if self.config.enable_compression and len(serialized_data) > self.config.compression_threshold_bytes:
                serialized_data = gzip.compress(serialized_data)
                compressed = True
            else:
                compressed = False

            # Store in cache
            if self.config.enable_cache:
                self._cache[key] = {
                    "data": data,
                    "metadata": metadata,
                    "compressed": compressed,
                }
                self._cache_timestamps[key] = datetime.utcnow()
                await self._cleanup_cache()

            # Store in GCS if available
            if self._gcs_bucket:
                success = await self._store_gcs(key, serialized_data, metadata, compressed)
                if success:
                    if self.metrics:
                        self.metrics.record_operation("gcs_store_success", True)
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        self.metrics.record_duration("gcs_store_duration", duration)
                    return True

            # Fallback to local storage
            if self.config.enable_local_fallback:
                success = await self._store_local(key, serialized_data, metadata, compressed)
                if success:
                    if self.metrics:
                        self.metrics.record_operation("local_store_success", True)
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        self.metrics.record_duration("local_store_duration", duration)
                    return True

            if self.metrics:
                self.metrics.record_operation("store_failure", False)
            return False

        except Exception as e:
            logger.error(f"Failed to store data for key {key}: {e}")
            if self.metrics:
                self.metrics.record_operation("store_error", False)
            raise FileStorageError(f"Storage failed: {e}")

    async def retrieve(self, key: str) -> Optional[Union[str, bytes, Dict[str, Any]]]:
        """
        Retrieve data by key.

        Args:
            key: Storage key

        Returns:
            The stored data if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()

        start_time = datetime.utcnow()

        try:
            # Check cache first
            if self.config.enable_cache and key in self._cache:
                cache_time = self._cache_timestamps.get(key)
                if cache_time and (datetime.utcnow() - cache_time).total_seconds() < float(self.config.cache_ttl_seconds):
                    if self.metrics:
                        self.metrics.record_operation("cache_hit", True)
                    return self._cache[key]["data"]
                else:
                    # Remove expired cache entry
                    self._cache.pop(key, None)
                    self._cache_timestamps.pop(key, None)

            # Try GCS first
            if self._gcs_bucket:
                data = await self._retrieve_gcs(key)
                if data is not None:
                    if self.metrics:
                        self.metrics.record_operation("gcs_retrieve_success", True)
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        self.metrics.record_duration("gcs_retrieve_duration", duration)

                    # Update cache
                    if self.config.enable_cache:
                        self._cache[key] = {"data": data, "metadata": {}}
                        self._cache_timestamps[key] = datetime.utcnow()

                    return data

            # Fallback to local storage
            if self.config.enable_local_fallback:
                data = await self._retrieve_local(key)
                if data is not None:
                    if self.metrics:
                        self.metrics.record_operation("local_retrieve_success", True)
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        self.metrics.record_duration("local_retrieve_duration", duration)

                    # Update cache
                    if self.config.enable_cache:
                        self._cache[key] = {"data": data, "metadata": {}}
                        self._cache_timestamps[key] = datetime.utcnow()

                    return data

            if self.metrics:
                self.metrics.record_operation("retrieve_not_found", False)
            return None

        except Exception as e:
            logger.error(f"Failed to retrieve data for key {key}: {e}")
            if self.metrics:
                self.metrics.record_operation("retrieve_error", False)
            raise FileStorageError(f"Retrieval failed: {e}")

    async def delete(self, key: str) -> bool:
        """
        Delete data by key.

        Args:
            key: Storage key

        Returns:
            True if deletion was successful
        """
        if not self._initialized:
            await self.initialize()

        try:
            success = True

            # Remove from cache
            if self.config.enable_cache:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)

            # Delete from GCS
            if self._gcs_bucket:
                gcs_success = await self._delete_gcs(key)
                if gcs_success:
                    if self.metrics:
                        self.metrics.record_operation("gcs_delete_success", True)
                else:
                    success = False

            # Delete from local storage
            if self.config.enable_local_fallback:
                local_success = await self._delete_local(key)
                if local_success:
                    if self.metrics:
                        self.metrics.record_operation("local_delete_success", True)
                else:
                    success = False

            if self.metrics:
                if success:
                    self.metrics.record_operation("delete_success", True)
                else:
                    self.metrics.record_operation("delete_failure", False)

            return success

        except Exception as e:
            logger.error(f"Failed to delete data for key {key}: {e}")
            if self.metrics:
                self.metrics.record_operation("delete_error", False)
            raise FileStorageError(f"Deletion failed: {e}")

    async def exists(self, key: str) -> bool:
        """
        Check if data exists for the given key.

        Args:
            key: Storage key

        Returns:
            True if data exists
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Check cache first
            if self.config.enable_cache and key in self._cache:
                cache_time = self._cache_timestamps.get(key)
                if cache_time and (datetime.utcnow() - cache_time).total_seconds() < float(self.config.cache_ttl_seconds):
                    return True

            # Check GCS
            if self._gcs_bucket:
                if await self._exists_gcs(key):
                    return True

            # Check local storage
            if self.config.enable_local_fallback:
                return await self._exists_local(key)

            return False

        except Exception as e:
            logger.error(f"Failed to check existence for key {key}: {e}")
            raise FileStorageError(f"Existence check failed: {e}")

    async def list_keys(self, prefix: Optional[str] = None, limit: Optional[int] = None) -> List[str]:
        """
        List storage keys with optional prefix filtering.

        Args:
            prefix: Optional key prefix filter
            limit: Maximum number of keys to return

        Returns:
            List of storage keys
        """
        if not self._initialized:
            await self.initialize()

        try:
            keys = set()

            # Get keys from GCS
            if self._gcs_bucket:
                gcs_keys = await self._list_keys_gcs(prefix, limit)
                keys.update(gcs_keys)

            # Get keys from local storage
            if self.config.enable_local_fallback:
                local_keys = await self._list_keys_local(prefix, limit)
                keys.update(local_keys)

            # Apply limit if specified
            keys_list = list(keys)
            if limit:
                keys_list = keys_list[:limit]

            return keys_list

        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            raise FileStorageError(f"Key listing failed: {e}")

    # GCS implementation methods

    async def _store_gcs(
        self,
        key: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]],
        compressed: bool,
    ) -> bool:
        """Store data in Google Cloud Storage."""
        if self._gcs_bucket is None:
            logger.error("GCS bucket not initialized")
            return False
        try:
            blob = self._gcs_bucket.blob(key)

            # Set metadata
            if metadata:
                blob.metadata = metadata
            if compressed:
                blob.content_encoding = "gzip"

            # Upload data
            blob.upload_from_string(data)
            return True

        except Exception as e:
            logger.error(f"GCS store failed for key {key}: {e}")
            return False

    async def _retrieve_gcs(self, key: str) -> Optional[Any]:
        """Retrieve data from Google Cloud Storage."""
        if self._gcs_bucket is None:
            logger.error("GCS bucket not initialized")
            return None
        try:
            blob = self._gcs_bucket.blob(key)

            if not blob.exists():
                return None

            # Download data
            data = blob.download_as_bytes()

            # Decompress if needed
            if blob.content_encoding == "gzip":
                data = gzip.decompress(data)

            # Deserialize data
            return await self._deserialize_data(data)

        except NotFound:
            return None
        except Exception as e:
            logger.error(f"GCS retrieve failed for key {key}: {e}")
            return None

    async def _delete_gcs(self, key: str) -> bool:
        """Delete data from Google Cloud Storage."""
        if self._gcs_bucket is None:
            logger.error("GCS bucket not initialized")
            return False
        try:
            blob = self._gcs_bucket.blob(key)
            blob.delete()
            return True

        except NotFound:
            return True  # Already deleted
        except Exception as e:
            logger.error(f"GCS delete failed for key {key}: {e}")
            return False

    async def _exists_gcs(self, key: str) -> bool:
        """Check if data exists in Google Cloud Storage."""
        if self._gcs_bucket is None:
            logger.error("GCS bucket not initialized")
            return False
        try:
            blob = self._gcs_bucket.blob(key)
            return blob.exists()

        except Exception as e:
            logger.error(f"GCS exists check failed for key {key}: {e}")
            return False

    async def _list_keys_gcs(self, prefix: Optional[str], limit: Optional[int]) -> List[str]:
        """List keys from Google Cloud Storage."""
        if self._gcs_bucket is None:
            logger.error("GCS bucket not initialized")
            return []
        try:
            blobs = self._gcs_bucket.list_blobs(prefix=prefix, max_results=limit)
            return [blob.name for blob in blobs]

        except Exception as e:
            logger.error(f"GCS list keys failed: {e}")
            return []

    # Local storage implementation methods

    async def _store_local(
        self,
        key: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]],
        compressed: bool,
    ) -> bool:
        """Store data in local filesystem."""
        try:
            file_path = Path(self.config.local_storage_path) / key
            file_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(file_path, "wb") as f:
                await f.write(data)

            # Store metadata separately
            if metadata:
                metadata_path = file_path.with_suffix(".metadata")
                metadata_with_compression = {
                    **metadata,
                    "compressed": compressed,
                }
                async with aiofiles.open(metadata_path, "w") as f:
                    await f.write(json.dumps(metadata_with_compression))

            return True

        except Exception as e:
            logger.error(f"Local store failed for key {key}: {e}")
            return False

    async def _retrieve_local(self, key: str) -> Optional[Any]:
        """Retrieve data from local filesystem."""
        try:
            file_path = Path(self.config.local_storage_path) / key

            if not file_path.exists():
                return None

            async with aiofiles.open(file_path, "rb") as f:
                data = await f.read()

            # Check for compression metadata
            metadata_path = file_path.with_suffix(".metadata")
            compressed = False
            if metadata_path.exists():
                async with aiofiles.open(metadata_path, "r") as f:
                    metadata = json.loads(await f.read())
                    compressed = metadata.get("compressed", False)

            # Decompress if needed
            if compressed:
                data = gzip.decompress(data)

            # Deserialize data
            return await self._deserialize_data(data)

        except Exception as e:
            logger.error(f"Local retrieve failed for key {key}: {e}")
            return None

    async def _delete_local(self, key: str) -> bool:
        """Delete data from local filesystem."""
        try:
            file_path = Path(self.config.local_storage_path) / key
            metadata_path = file_path.with_suffix(".metadata")

            success = True
            if file_path.exists():
                file_path.unlink()

            if metadata_path.exists():
                metadata_path.unlink()

            return success

        except Exception as e:
            logger.error(f"Local delete failed for key {key}: {e}")
            return False

    async def _exists_local(self, key: str) -> bool:
        """Check if data exists in local filesystem."""
        try:
            file_path = Path(self.config.local_storage_path) / key
            return file_path.exists()

        except Exception as e:
            logger.error(f"Local exists check failed for key {key}: {e}")
            return False

    async def _list_keys_local(self, prefix: Optional[str], limit: Optional[int]) -> List[str]:
        """List keys from local filesystem."""
        try:
            storage_path = Path(self.config.local_storage_path)
            if not storage_path.exists():
                return []

            keys = []
            for file_path in storage_path.rglob("*"):
                if file_path.is_file() and not file_path.name.endswith(".metadata"):
                    key = str(file_path.relative_to(storage_path))
                    if not prefix or key.startswith(prefix):
                        keys.append(key)
                        if limit and len(keys) >= limit:
                            break

            return keys

        except Exception as e:
            logger.error(f"Local list keys failed: {e}")
            return []

    # Utility methods

    async def _serialize_data(self, data: Union[str, bytes, Dict[str, Any]]) -> bytes:
        """Serialize data for storage."""
        if isinstance(data, bytes):
            return data
        elif isinstance(data, str):
            return data.encode("utf-8")
        else:
            # Use pickle for complex objects
            return pickle.dumps(data)

    async def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from storage."""
        try:
            # Try to deserialize as pickle first
            return pickle.loads(data)
        except Exception:
            try:
                # Try as JSON
                return json.loads(data.decode("utf-8"))
            except Exception:
                # Return as string
                return data.decode("utf-8")

    async def _cleanup_cache(self):
        """Clean up expired cache entries."""
        if not self.config.enable_cache:
            return

        current_time = datetime.utcnow()
        expired_keys = []

        for key, timestamp in self._cache_timestamps.items():
            if (current_time - timestamp).total_seconds() > self.config.cache_ttl_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            "initialized": self._initialized,
            "gcs_available": self._gcs_bucket is not None,
            "local_fallback_enabled": self.config.enable_local_fallback,
            "cache_enabled": self.config.enable_cache,
            "cache_size": len(self._cache),
            "metrics": (self.metrics.get_metrics_summary() if self.metrics and hasattr(self.metrics, "get_metrics_summary") else {}),
        }


# Global instance
_file_storage_instance = None


def get_file_storage(config: Optional[Dict[str, Any]] = None) -> FileStorage:
    """Get the global file storage instance."""
    global _file_storage_instance
    if _file_storage_instance is None:
        if config is None:
            from aiecs.config.config import get_settings

            settings = get_settings()
            config = settings.file_storage_config
        _file_storage_instance = FileStorage(config)
    return _file_storage_instance


async def initialize_file_storage(
    config: Optional[Dict[str, Any]] = None,
) -> FileStorage:
    """Initialize and return the file storage instance."""
    storage = get_file_storage(config)
    await storage.initialize()
    return storage
