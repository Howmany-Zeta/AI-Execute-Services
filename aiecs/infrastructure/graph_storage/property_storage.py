"""
Optimized Property Storage for Knowledge Graph Entities

Provides optimized storage for entities with large property sets (200+ properties):
- Sparse property storage for optional properties
- Property compression for large property sets
- Property indexing for frequently queried properties

This module helps reduce memory footprint and improve query performance
when dealing with entities that have many properties.
"""

import json
import zlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


# Threshold for property compression (number of properties)
COMPRESSION_THRESHOLD = 200

# Threshold for property count to consider a set as large
LARGE_PROPERTY_SET_THRESHOLD = 50


@dataclass
class PropertyStorageConfig:
    """Configuration for property storage optimization"""
    
    # Enable sparse storage (only store non-null values)
    enable_sparse_storage: bool = True
    
    # Enable compression for large property sets
    enable_compression: bool = True
    
    # Minimum properties before compression is applied
    compression_threshold: int = COMPRESSION_THRESHOLD
    
    # Compression level (1-9, higher = better compression but slower)
    compression_level: int = 6
    
    # Properties to always index for fast lookup
    indexed_properties: Set[str] = field(default_factory=set)
    
    # Track query frequency for auto-indexing
    auto_index_threshold: int = 100  # Queries before auto-indexing


@dataclass
class CompressedProperties:
    """Represents compressed property storage"""
    
    # Compressed property data
    data: bytes
    
    # Number of properties
    property_count: int
    
    # Original size in bytes
    original_size: int
    
    # Compressed size in bytes
    compressed_size: int
    
    @property
    def compression_ratio(self) -> float:
        """Get compression ratio (0-1, lower is better)"""
        if self.original_size == 0:
            return 1.0
        return self.compressed_size / self.original_size
    
    def decompress(self) -> Dict[str, Any]:
        """Decompress and return properties dict"""
        decompressed = zlib.decompress(self.data)
        return json.loads(decompressed.decode('utf-8'))


class PropertyIndex:
    """
    Index for fast property-based lookups
    
    Maintains reverse index from property values to entity IDs.
    """
    
    def __init__(self):
        # property_name -> value -> set of entity_ids
        self._index: Dict[str, Dict[Any, Set[str]]] = defaultdict(lambda: defaultdict(set))
        
        # Track indexed properties
        self._indexed_properties: Set[str] = set()
        
        # Query frequency tracking for auto-indexing
        self._query_counts: Dict[str, int] = defaultdict(int)
        
    def add_to_index(self, entity_id: str, property_name: str, value: Any) -> None:
        """Add a property value to the index"""
        if property_name not in self._indexed_properties:
            return
        
        # Convert value to hashable type if needed
        hashable_value = self._make_hashable(value)
        if hashable_value is not None:
            self._index[property_name][hashable_value].add(entity_id)
    
    def remove_from_index(self, entity_id: str, property_name: str, value: Any) -> None:
        """Remove a property value from the index"""
        if property_name not in self._indexed_properties:
            return
        
        hashable_value = self._make_hashable(value)
        if hashable_value is not None and hashable_value in self._index[property_name]:
            self._index[property_name][hashable_value].discard(entity_id)
    
    def lookup(self, property_name: str, value: Any) -> Set[str]:
        """Look up entity IDs by property value"""
        # Track query frequency
        self._query_counts[property_name] += 1
        
        if property_name not in self._indexed_properties:
            return set()
        
        hashable_value = self._make_hashable(value)
        if hashable_value is None:
            return set()
        
        return self._index[property_name].get(hashable_value, set()).copy()
    
    def add_indexed_property(self, property_name: str) -> None:
        """Mark a property as indexed"""
        self._indexed_properties.add(property_name)
        
    def remove_indexed_property(self, property_name: str) -> None:
        """Remove a property from indexing"""
        self._indexed_properties.discard(property_name)
        if property_name in self._index:
            del self._index[property_name]
    
    def get_query_counts(self) -> Dict[str, int]:
        """Get query counts for all properties"""
        return dict(self._query_counts)
    
    def _make_hashable(self, value: Any) -> Optional[Any]:
        """Convert value to hashable type, or None if not possible"""
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (list, tuple)):
            return tuple(value) if all(isinstance(v, (str, int, float, bool, type(None))) for v in value) else None
        return None

    def clear(self) -> None:
        """Clear all indexes"""
        self._index.clear()
        self._query_counts.clear()
        # Keep indexed properties


class PropertyOptimizer:
    """
    Optimizes property storage for entities

    Provides:
    - Sparse storage (only non-null values)
    - Compression for large property sets
    - Indexing for fast property lookups

    Example:
        ```python
        optimizer = PropertyOptimizer()

        # Compress large property set
        properties = {"col1": 1, "col2": 2, ..., "col250": 250}
        compressed = optimizer.compress_properties(properties)

        # Decompress when needed
        original = optimizer.decompress_properties(compressed)
        ```
    """

    def __init__(self, config: Optional[PropertyStorageConfig] = None):
        """
        Initialize property optimizer

        Args:
            config: Configuration for optimization behavior
        """
        self.config = config or PropertyStorageConfig()
        self._property_index = PropertyIndex()

        # Add configured indexed properties
        for prop in self.config.indexed_properties:
            self._property_index.add_indexed_property(prop)

    def compress_properties(self, properties: Dict[str, Any]) -> CompressedProperties:
        """
        Compress a property dictionary

        Args:
            properties: Property dictionary to compress

        Returns:
            CompressedProperties object
        """
        # Apply sparse storage first (filter out None values)
        if self.config.enable_sparse_storage:
            properties = {k: v for k, v in properties.items() if v is not None}

        # Serialize to JSON
        json_str = json.dumps(properties, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        original_size = len(json_bytes)

        # Compress
        compressed = zlib.compress(json_bytes, level=self.config.compression_level)

        return CompressedProperties(
            data=compressed,
            property_count=len(properties),
            original_size=original_size,
            compressed_size=len(compressed)
        )

    def decompress_properties(self, compressed: CompressedProperties) -> Dict[str, Any]:
        """
        Decompress a CompressedProperties object

        Args:
            compressed: CompressedProperties to decompress

        Returns:
            Original property dictionary
        """
        return compressed.decompress()

    def should_compress(self, properties: Dict[str, Any]) -> bool:
        """
        Determine if properties should be compressed

        Args:
            properties: Property dictionary

        Returns:
            True if compression would be beneficial
        """
        if not self.config.enable_compression:
            return False

        return len(properties) >= self.config.compression_threshold

    def optimize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply sparse storage optimization

        Removes None values from properties dict.

        Args:
            properties: Property dictionary

        Returns:
            Optimized property dictionary
        """
        if not self.config.enable_sparse_storage:
            return properties

        return {k: v for k, v in properties.items() if v is not None}

    def estimate_memory_savings(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate memory savings from optimization

        Args:
            properties: Property dictionary

        Returns:
            Dictionary with memory statistics
        """
        import sys

        # Original size
        original_json = json.dumps(properties)
        original_size = sys.getsizeof(properties) + sys.getsizeof(original_json)

        # Sparse storage
        sparse_props = self.optimize_properties(properties)
        sparse_json = json.dumps(sparse_props)
        sparse_size = sys.getsizeof(sparse_props) + sys.getsizeof(sparse_json)

        # Compressed
        compressed = self.compress_properties(properties)
        compressed_size = sys.getsizeof(compressed.data)

        return {
            "original_size_bytes": original_size,
            "sparse_size_bytes": sparse_size,
            "compressed_size_bytes": compressed_size,
            "property_count": len(properties),
            "non_null_count": len(sparse_props),
            "null_count": len(properties) - len(sparse_props),
            "sparse_reduction_pct": (1 - sparse_size / original_size) * 100 if original_size > 0 else 0,
            "compression_ratio": compressed.compression_ratio,
            "compression_reduction_pct": (1 - compressed.compression_ratio) * 100
        }

    # Index operations
    @property
    def property_index(self) -> PropertyIndex:
        """Get the property index"""
        return self._property_index

    def index_entity(self, entity_id: str, properties: Dict[str, Any]) -> None:
        """
        Index all properties for an entity

        Args:
            entity_id: Entity ID
            properties: Entity properties
        """
        for prop_name, value in properties.items():
            self._property_index.add_to_index(entity_id, prop_name, value)

    def unindex_entity(self, entity_id: str, properties: Dict[str, Any]) -> None:
        """
        Remove entity from all property indexes

        Args:
            entity_id: Entity ID
            properties: Entity properties
        """
        for prop_name, value in properties.items():
            self._property_index.remove_from_index(entity_id, prop_name, value)

    def lookup_by_property(self, property_name: str, value: Any) -> Set[str]:
        """
        Look up entity IDs by property value

        Args:
            property_name: Property name to search
            value: Property value to match

        Returns:
            Set of matching entity IDs
        """
        return self._property_index.lookup(property_name, value)

    def add_indexed_property(self, property_name: str) -> None:
        """Add a property to the index"""
        self._property_index.add_indexed_property(property_name)

