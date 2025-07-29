"""
Data Serializer Implementation

Provides serialization and deserialization for different data formats.
"""

import json
import pickle
import yaml
import gzip
import base64
import logging
from typing import Any, Dict, Optional, Union, Set
from datetime import datetime
from enum import Enum

from ...core.models.data_models import DataFormat, CompressionType
from ...core.exceptions.data_exceptions import SerializationError, DeserializationError

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    YAML = "yaml"
    PICKLE = "pickle"
    BINARY = "binary"


class DataSerializer:
    """
    Data serializer with support for multiple formats and compression.

    Features:
    - Multiple serialization formats (JSON, YAML, Pickle)
    - Compression support (gzip)
    - Type preservation
    - Error handling
    - Performance optimization
    """

    def __init__(self, default_format: DataFormat = DataFormat.JSON,
                 compression: CompressionType = CompressionType.NONE):
        self.default_format = default_format
        self.compression = compression
        self._serializers = {
            DataFormat.JSON: self._serialize_json,
            DataFormat.YAML: self._serialize_yaml,
            DataFormat.PICKLE: self._serialize_pickle,
            DataFormat.BINARY: self._serialize_binary
        }
        self._deserializers = {
            DataFormat.JSON: self._deserialize_json,
            DataFormat.YAML: self._deserialize_yaml,
            DataFormat.PICKLE: self._deserialize_pickle,
            DataFormat.BINARY: self._deserialize_binary
        }

    def serialize(self, data: Any, format_type: Optional[DataFormat] = None,
                 compress: Optional[CompressionType] = None) -> bytes:
        """
        Serialize data to bytes.

        Args:
            data: Data to serialize
            format_type: Serialization format (defaults to instance default)
            compress: Compression type (defaults to instance default)

        Returns:
            Serialized data as bytes

        Raises:
            SerializationError: If serialization fails
        """
        try:
            format_type = format_type or self.default_format
            compress = compress or self.compression

            # Get serializer
            serializer = self._serializers.get(format_type)
            if not serializer:
                raise SerializationError(f"Unsupported format: {format_type}")

            # Serialize data
            serialized_data = serializer(data)

            # Apply compression if requested
            if compress == CompressionType.GZIP:
                serialized_data = self._compress_gzip(serialized_data)
            elif compress == CompressionType.LZ4:
                serialized_data = self._compress_lz4(serialized_data)

            return serialized_data

        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            raise SerializationError(f"Failed to serialize data: {e}")

    def deserialize(self, data: bytes, format_type: Optional[DataFormat] = None,
                   compress: Optional[CompressionType] = None) -> Any:
        """
        Deserialize data from bytes.

        Args:
            data: Serialized data as bytes
            format_type: Serialization format (defaults to instance default)
            compress: Compression type (defaults to instance default)

        Returns:
            Deserialized data

        Raises:
            DeserializationError: If deserialization fails
        """
        try:
            format_type = format_type or self.default_format
            compress = compress or self.compression

            # Apply decompression if needed
            if compress == CompressionType.GZIP:
                data = self._decompress_gzip(data)
            elif compress == CompressionType.LZ4:
                data = self._decompress_lz4(data)

            # Get deserializer
            deserializer = self._deserializers.get(format_type)
            if not deserializer:
                raise DeserializationError(f"Unsupported format: {format_type}")

            # Deserialize data
            return deserializer(data)

        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            raise DeserializationError(f"Failed to deserialize data: {e}")

    def serialize_with_metadata(self, data: Any, metadata: Optional[Dict[str, Any]] = None,
                              format_type: Optional[DataFormat] = None,
                              compress: Optional[CompressionType] = None) -> bytes:
        """
        Serialize data with metadata.

        Args:
            data: Data to serialize
            metadata: Additional metadata
            format_type: Serialization format
            compress: Compression type

        Returns:
            Serialized data with metadata as bytes
        """
        try:
            # Create wrapper with metadata
            wrapper = {
                'data': data,
                'metadata': metadata or {},
                'format': (format_type or self.default_format).value,
                'compression': (compress or self.compression).value,
                'serialized_at': datetime.utcnow().isoformat(),
                'version': '1.0'
            }

            return self.serialize(wrapper, format_type, compress)

        except Exception as e:
            logger.error(f"Serialization with metadata failed: {e}")
            raise SerializationError(f"Failed to serialize data with metadata: {e}")

    def deserialize_with_metadata(self, data: bytes, format_type: Optional[DataFormat] = None,
                                compress: Optional[CompressionType] = None) -> tuple[Any, Dict[str, Any]]:
        """
        Deserialize data with metadata.

        Args:
            data: Serialized data as bytes
            format_type: Serialization format
            compress: Compression type

        Returns:
            Tuple of (deserialized_data, metadata)
        """
        try:
            wrapper = self.deserialize(data, format_type, compress)

            if isinstance(wrapper, dict) and 'data' in wrapper:
                return wrapper['data'], wrapper.get('metadata', {})
            else:
                # Fallback for data without metadata wrapper
                return wrapper, {}

        except Exception as e:
            logger.error(f"Deserialization with metadata failed: {e}")
            raise DeserializationError(f"Failed to deserialize data with metadata: {e}")

    # JSON serialization

    def _serialize_json(self, data: Any) -> bytes:
        """Serialize data to JSON."""
        try:
            # Convert data to a JSON-serializable format with cycle detection
            visited = set()
            data_dict = self._convert_to_serializable(data, visited)
            json_str = json.dumps(data_dict, default=lambda obj: self._json_serializer(obj, visited), ensure_ascii=False, separators=(',', ':'))
            return json_str.encode('utf-8')
        except Exception as e:
            raise SerializationError(f"JSON serialization failed: {e}")

    def _deserialize_json(self, data: bytes) -> Any:
        """Deserialize data from JSON."""
        try:
            json_str = data.decode('utf-8')
            return json.loads(json_str, object_hook=self._json_deserializer)
        except Exception as e:
            raise DeserializationError(f"JSON deserialization failed: {e}")

    def _convert_to_serializable(self, data: Any, visited: Optional[set] = None) -> Any:
        """Convert data to a JSON-serializable format, handling mappingproxy and other types with cycle detection."""
        import types

        if visited is None:
            visited = set()

        # Check for circular references using object id
        obj_id = id(data)
        if obj_id in visited:
            # Return a placeholder for circular reference
            return f"<Circular reference to {type(data).__name__} object>"

        if data is None:
            return None
        elif isinstance(data, (str, int, float, bool)):
            return data
        elif isinstance(data, (list, tuple)):
            # Add to visited set for complex objects
            visited.add(obj_id)
            try:
                result = [self._convert_to_serializable(item, visited) for item in data]
            finally:
                visited.remove(obj_id)
            return result
        elif isinstance(data, dict):
            # Add to visited set for complex objects
            visited.add(obj_id)
            try:
                result = {str(k): self._convert_to_serializable(v, visited) for k, v in data.items()}
            finally:
                visited.remove(obj_id)
            return result
        elif isinstance(data, types.MappingProxyType):
            # Convert mappingproxy to regular dict
            visited.add(obj_id)
            try:
                result = {str(k): self._convert_to_serializable(v, visited) for k, v in data.items()}
            finally:
                visited.remove(obj_id)
            return result
        elif hasattr(data, 'dict') and callable(getattr(data, 'dict')):
            # Pydantic model - convert to dict and recursively process
            visited.add(obj_id)
            try:
                result = self._convert_to_serializable(data.dict(), visited)
            finally:
                visited.remove(obj_id)
            return result
        elif hasattr(data, '__dict__'):
            # Regular object with __dict__
            visited.add(obj_id)
            try:
                result = self._convert_to_serializable(data.__dict__, visited)
            finally:
                visited.remove(obj_id)
            return result
        elif isinstance(data, set):
            visited.add(obj_id)
            try:
                result = [self._convert_to_serializable(item, visited) for item in data]
            finally:
                visited.remove(obj_id)
            return result
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, bytes):
            return base64.b64encode(data).decode('ascii')
        else:
            # Try to convert to string as fallback
            try:
                return str(data)
            except Exception:
                return f"<{type(data).__name__} object>"

    def _json_serializer(self, obj: Any, visited: Optional[set] = None) -> Any:
        """Custom JSON serializer for special types with cycle detection."""
        if visited is None:
            visited = set()

        # Check for circular references using object id
        obj_id = id(obj)
        if obj_id in visited:
            # Return a placeholder for circular reference
            return f"<Circular reference to {type(obj).__name__} object>"

        if isinstance(obj, datetime):
            return {'__datetime__': obj.isoformat()}
        elif isinstance(obj, set):
            visited.add(obj_id)
            try:
                result = {'__set__': [self._convert_to_serializable(item, visited) for item in obj]}
            finally:
                visited.remove(obj_id)
            return result
        elif isinstance(obj, bytes):
            return {'__bytes__': base64.b64encode(obj).decode('ascii')}
        elif hasattr(obj, '__dict__'):
            visited.add(obj_id)
            try:
                result = {'__object__': obj.__class__.__name__, '__data__': self._convert_to_serializable(obj.__dict__, visited)}
            finally:
                visited.remove(obj_id)
            return result
        else:
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _json_deserializer(self, obj: Dict[str, Any]) -> Any:
        """Custom JSON deserializer for special types."""
        if '__datetime__' in obj:
            return datetime.fromisoformat(obj['__datetime__'])
        elif '__set__' in obj:
            return set(obj['__set__'])
        elif '__bytes__' in obj:
            return base64.b64decode(obj['__bytes__'])
        elif '__object__' in obj:
            # Note: This is a simplified object reconstruction
            # In production, you might want more sophisticated object reconstruction
            return obj['__data__']
        return obj

    # YAML serialization

    def _serialize_yaml(self, data: Any) -> bytes:
        """Serialize data to YAML."""
        try:
            yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True)
            return yaml_str.encode('utf-8')
        except Exception as e:
            raise SerializationError(f"YAML serialization failed: {e}")

    def _deserialize_yaml(self, data: bytes) -> Any:
        """Deserialize data from YAML."""
        try:
            yaml_str = data.decode('utf-8')
            return yaml.safe_load(yaml_str)
        except Exception as e:
            raise DeserializationError(f"YAML deserialization failed: {e}")

    # Pickle serialization

    def _serialize_pickle(self, data: Any) -> bytes:
        """Serialize data to Pickle."""
        try:
            return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            raise SerializationError(f"Pickle serialization failed: {e}")

    def _deserialize_pickle(self, data: bytes) -> Any:
        """Deserialize data from Pickle."""
        try:
            return pickle.loads(data)
        except Exception as e:
            raise DeserializationError(f"Pickle deserialization failed: {e}")

    # Binary serialization

    def _serialize_binary(self, data: Any) -> bytes:
        """Serialize binary data."""
        try:
            if isinstance(data, bytes):
                return data
            elif isinstance(data, str):
                return data.encode('utf-8')
            else:
                # Fallback to pickle for complex objects
                return self._serialize_pickle(data)
        except Exception as e:
            raise SerializationError(f"Binary serialization failed: {e}")

    def _deserialize_binary(self, data: bytes) -> Any:
        """Deserialize binary data."""
        try:
            # Try to decode as UTF-8 string first
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                # If that fails, try pickle
                try:
                    return self._deserialize_pickle(data)
                except:
                    # If all else fails, return raw bytes
                    return data
        except Exception as e:
            raise DeserializationError(f"Binary deserialization failed: {e}")

    # Compression methods

    def _compress_gzip(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        try:
            return gzip.compress(data)
        except Exception as e:
            raise SerializationError(f"Gzip compression failed: {e}")

    def _decompress_gzip(self, data: bytes) -> bytes:
        """Decompress data using gzip."""
        try:
            return gzip.decompress(data)
        except Exception as e:
            raise DeserializationError(f"Gzip decompression failed: {e}")

    def _compress_lz4(self, data: bytes) -> bytes:
        """Compress data using LZ4."""
        try:
            # Note: This requires the lz4 package
            # pip install lz4
            import lz4.frame
            return lz4.frame.compress(data)
        except ImportError:
            logger.warning("LZ4 compression not available, falling back to gzip")
            return self._compress_gzip(data)
        except Exception as e:
            raise SerializationError(f"LZ4 compression failed: {e}")

    def _decompress_lz4(self, data: bytes) -> bytes:
        """Decompress data using LZ4."""
        try:
            import lz4.frame
            return lz4.frame.decompress(data)
        except ImportError:
            logger.warning("LZ4 decompression not available, falling back to gzip")
            return self._decompress_gzip(data)
        except Exception as e:
            raise DeserializationError(f"LZ4 decompression failed: {e}")

    # Utility methods

    def get_serialized_size(self, data: Any, format_type: Optional[DataFormat] = None,
                          compress: Optional[CompressionType] = None) -> int:
        """Get the size of serialized data without actually storing it."""
        try:
            serialized = self.serialize(data, format_type, compress)
            return len(serialized)
        except Exception as e:
            logger.error(f"Failed to get serialized size: {e}")
            return 0

    def validate_data(self, data: Any, format_type: Optional[DataFormat] = None) -> bool:
        """Validate that data can be serialized and deserialized."""
        try:
            serialized = self.serialize(data, format_type)
            deserialized = self.deserialize(serialized, format_type)
            return True
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return False


# Factory function for creating serializers
def create_serializer(format_type: DataFormat = DataFormat.JSON,
                     compression: CompressionType = CompressionType.NONE) -> DataSerializer:
    """Create a data serializer with specified format and compression."""
    return DataSerializer(format_type, compression)


# Convenience functions
def serialize_json(data: Any, compress: bool = False) -> bytes:
    """Serialize data to JSON."""
    compression = CompressionType.GZIP if compress else CompressionType.NONE
    serializer = create_serializer(DataFormat.JSON, compression)
    return serializer.serialize(data)


def deserialize_json(data: bytes, decompress: bool = False) -> Any:
    """Deserialize data from JSON."""
    compression = CompressionType.GZIP if decompress else CompressionType.NONE
    serializer = create_serializer(DataFormat.JSON, compression)
    return serializer.deserialize(data)


def serialize_yaml(data: Any, compress: bool = False) -> bytes:
    """Serialize data to YAML."""
    compression = CompressionType.GZIP if compress else CompressionType.NONE
    serializer = create_serializer(DataFormat.YAML, compression)
    return serializer.serialize(data)


def deserialize_yaml(data: bytes, decompress: bool = False) -> Any:
    """Deserialize data from YAML."""
    compression = CompressionType.GZIP if decompress else CompressionType.NONE
    serializer = create_serializer(DataFormat.YAML, compression)
    return serializer.deserialize(data)


def serialize_pickle(data: Any, compress: bool = False) -> bytes:
    """Serialize data to Pickle."""
    compression = CompressionType.GZIP if compress else CompressionType.NONE
    serializer = create_serializer(DataFormat.PICKLE, compression)
    return serializer.serialize(data)


def deserialize_pickle(data: bytes, decompress: bool = False) -> Any:
    """Deserialize data from Pickle."""
    compression = CompressionType.GZIP if decompress else CompressionType.NONE
    serializer = create_serializer(DataFormat.PICKLE, compression)
    return serializer.deserialize(data)
