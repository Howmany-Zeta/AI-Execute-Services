"""
Query Profiler for Knowledge Graph

Provides detailed profiling and timing metrics for graph queries.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QueryProfile:
    """
    Profile data for a single query execution

    Attributes:
        query_id: Unique identifier for the query
        query_type: Type of query (search, traverse, etc.)
        start_time: When the query started
        end_time: When the query completed
        duration_ms: Total duration in milliseconds
        steps: List of execution steps with timing
        metadata: Additional query metadata
    """

    query_id: str
    query_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self) -> None:
        """Mark query as complete and calculate duration"""
        self.end_time = datetime.utcnow()
        if self.start_time:
            delta = self.end_time - self.start_time
            self.duration_ms = delta.total_seconds() * 1000

    def add_step(
        self,
        name: str,
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an execution step"""
        self.steps.append(
            {
                "name": name,
                "duration_ms": duration_ms,
                "metadata": metadata or {},
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query_id": self.query_id,
            "query_type": self.query_type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "steps": self.steps,
            "metadata": self.metadata,
        }


class QueryProfiler:
    """
    Query profiler for detailed performance analysis

    Tracks query execution with step-by-step timing and metadata.

    Example:
        ```python
        profiler = QueryProfiler()

        # Profile a query
        async with profiler.profile("search_query", "vector_search") as profile:
            # Step 1
            async with profiler.step(profile, "embedding_lookup"):
                embedding = await get_embedding(query)

            # Step 2
            async with profiler.step(profile, "vector_search"):
                results = await search(embedding)

        # Get profile
        profile_data = profiler.get_profile("search_query")
        print(f"Total: {profile_data.duration_ms}ms")
        for step in profile_data.steps:
            print(f"  {step['name']}: {step['duration_ms']}ms")
        ```
    """

    def __init__(self, max_profiles: int = 1000):
        """
        Initialize query profiler

        Args:
            max_profiles: Maximum number of profiles to keep in memory
        """
        self.max_profiles = max_profiles
        self.profiles: Dict[str, QueryProfile] = {}
        self._profile_order: List[str] = []

    @asynccontextmanager
    async def profile(
        self,
        query_id: str,
        query_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for profiling a query

        Args:
            query_id: Unique identifier for the query
            query_type: Type of query
            metadata: Additional metadata

        Yields:
            QueryProfile object
        """
        # Create profile
        profile = QueryProfile(
            query_id=query_id,
            query_type=query_type,
            start_time=datetime.utcnow(),
            metadata=metadata or {},
        )

        try:
            yield profile
        finally:
            # Complete profile
            profile.complete()

            # Store profile
            self._store_profile(profile)

    @asynccontextmanager
    async def step(
        self,
        profile: QueryProfile,
        step_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for profiling a query step

        Args:
            profile: Parent query profile
            step_name: Name of the step
            metadata: Additional metadata
        """
        start_time = time.perf_counter()

        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            profile.add_step(step_name, duration_ms, metadata)

    def _store_profile(self, profile: QueryProfile) -> None:
        """Store profile with LRU eviction"""
        # Add to storage
        self.profiles[profile.query_id] = profile
        self._profile_order.append(profile.query_id)

        # Evict oldest if over limit
        while len(self._profile_order) > self.max_profiles:
            oldest_id = self._profile_order.pop(0)
            if oldest_id in self.profiles:
                del self.profiles[oldest_id]

    def get_profile(self, query_id: str) -> Optional[QueryProfile]:
        """Get profile by query ID"""
        return self.profiles.get(query_id)

    def get_all_profiles(self) -> List[QueryProfile]:
        """Get all stored profiles"""
        return list(self.profiles.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get profiling statistics"""
        if not self.profiles:
            return {
                "total_queries": 0,
                "avg_duration_ms": 0,
                "min_duration_ms": 0,
                "max_duration_ms": 0,
            }

        durations = [p.duration_ms for p in self.profiles.values() if p.duration_ms]

        return {
            "total_queries": len(self.profiles),
            "avg_duration_ms": (sum(durations) / len(durations) if durations else 0),
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "query_types": self._get_query_type_stats(),
        }

    def _get_query_type_stats(self) -> Dict[str, int]:
        """Get statistics by query type"""
        stats: Dict[str, int] = {}
        for profile in self.profiles.values():
            stats[profile.query_type] = stats.get(profile.query_type, 0) + 1
        return stats

    def clear(self) -> None:
        """Clear all profiles"""
        self.profiles.clear()
        self._profile_order.clear()
