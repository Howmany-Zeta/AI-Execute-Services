"""Intelligent caching for web scraper with LRU and optional Redis backend."""

import hashlib
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Tracking params to remove for URL normalization
TRACKING_PARAMS = frozenset([
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'fbclid', 'gclid', 'msclkid', 'ref', 'source', 'mc_eid', 'mc_cid',
])

# TTL strategies by content type (seconds)
TTL_STRATEGIES = {
    'static': 86400,    # 24 hours
    'api': 3600,        # 1 hour
    'news': 1800,       # 30 minutes
    'default': 3600,    # 1 hour
}


class ScraperCache:
    """LRU cache with optional Redis backend for scraped content."""

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,
        redis_url: Optional[str] = None,
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.redis_url = redis_url
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._redis: Optional[Any] = None

    async def _get_redis(self) -> Optional[Any]:
        """Lazy connect to Redis."""
        if self.redis_url and self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url)
            except (ImportError, Exception):
                self._redis = None
        return self._redis

    def _generate_key(self, url: str) -> str:
        """Normalize URL and generate cache key."""
        parsed = urlparse(url.lower().strip())
        params = parse_qs(parsed.query)
        filtered_params = {k: v for k, v in params.items() if k not in TRACKING_PARAMS}
        normalized_query = urlencode(sorted(filtered_params.items()), doseq=True)
        normalized = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path.rstrip('/'),
            parsed.params, normalized_query, ''
        ))
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry has expired."""
        return time.time() > entry.get('expires_at', 0)

    def _get_ttl(self, content_type: Optional[str] = None) -> int:
        """Get TTL based on content type."""
        if content_type and content_type in TTL_STRATEGIES:
            return TTL_STRATEGIES[content_type]
        return self.default_ttl

    async def get(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached content for URL."""
        key = self._generate_key(url)

        # Check in-memory cache first
        if key in self._cache:
            entry = self._cache[key]
            if not self._is_expired(entry):
                self._cache.move_to_end(key)
                return entry.get('content')
            del self._cache[key]

        # Check Redis
        redis_client = await self._get_redis()
        if redis_client:
            try:
                import json
                data = await redis_client.get(f'scraper:{key}')
                if data:
                    entry = json.loads(data)
                    self._cache[key] = entry
                    self._cache.move_to_end(key)
                    return entry.get('content')
            except Exception:
                pass
        return None

    async def set(
        self, url: str, content: Dict[str, Any], ttl: Optional[int] = None,
        content_type: Optional[str] = None,
    ) -> None:
        """Cache content for URL."""
        key = self._generate_key(url)
        actual_ttl = ttl if ttl is not None else self._get_ttl(content_type)
        entry = {'content': content, 'expires_at': time.time() + actual_ttl, 'url': url}

        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = entry
        self._cache.move_to_end(key)

        # Store in Redis
        redis_client = await self._get_redis()
        if redis_client:
            try:
                import json
                await redis_client.setex(f'scraper:{key}', actual_ttl, json.dumps(entry))
            except Exception:
                pass

    async def invalidate(self, url: str) -> None:
        """Remove URL from cache."""
        key = self._generate_key(url)
        self._cache.pop(key, None)
        redis_client = await self._get_redis()
        if redis_client:
            try:
                await redis_client.delete(f'scraper:{key}')
            except Exception:
                pass


class ContentDeduplicator:
    """Detect duplicate and near-duplicate content using shingle-based similarity."""

    def __init__(self, shingle_size: int = 5):
        self._index: Dict[str, set] = {}  # url -> shingles
        self._hashes: Dict[str, str] = {}  # hash -> url
        self.shingle_size = shingle_size

    def get_hash(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8', errors='ignore')).hexdigest()

    def _get_shingles(self, content: str) -> set:
        """Generate shingles (n-grams) from content."""
        tokens = content.lower().split()
        if len(tokens) < self.shingle_size:
            return {' '.join(tokens)} if tokens else set()
        return {' '.join(tokens[i:i + self.shingle_size])
                for i in range(len(tokens) - self.shingle_size + 1)}

    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        """Compute Jaccard similarity between two sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union else 0.0

    def is_duplicate(
        self, content: str, threshold: float = 0.85,
    ) -> Tuple[bool, Optional[str]]:
        """Check if content is duplicate. Returns (is_dup, matching_url)."""
        content_hash = self.get_hash(content)
        if content_hash in self._hashes:
            return True, self._hashes[content_hash]

        shingles = self._get_shingles(content)
        for url, existing_shingles in self._index.items():
            similarity = self._jaccard_similarity(shingles, existing_shingles)
            if similarity >= threshold:
                return True, url
        return False, None

    def add_content(self, url: str, content: str) -> None:
        """Add content to deduplication index."""
        content_hash = self.get_hash(content)
        self._hashes[content_hash] = url
        self._index[url] = self._get_shingles(content)

