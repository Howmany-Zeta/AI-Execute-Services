"""
Result Deduplication

This module handles detection and removal of duplicate and highly similar
search results.
"""

import hashlib
from typing import Any, Dict, List
from urllib.parse import urlparse, urlunparse


class ResultDeduplicator:
    """Removes duplicate and similar search results"""

    def deduplicate_results(self, results: List[Dict[str, Any]], similarity_threshold: float = 0.85) -> List[Dict[str, Any]]:
        """
        Remove duplicate and highly similar results.

        Args:
            results: List of search results
            similarity_threshold: Similarity threshold (0-1) for considering results as duplicates

        Returns:
            Deduplicated list of results
        """
        if not results:
            return []

        unique_results = []
        seen_urls = set()
        seen_content_hashes: set[str] = set()

        for result in results:
            url = result.get("link", "")

            # 1. URL deduplication (normalized)
            normalized_url = self._normalize_url(url)
            if normalized_url in seen_urls:
                continue

            # 2. Content similarity deduplication
            content_hash = self._calculate_content_hash(result.get("title", ""), result.get("snippet", ""))

            # Check for high similarity with existing results
            is_duplicate = False
            for seen_hash in seen_content_hashes:
                similarity = self._calculate_similarity(content_hash, seen_hash)
                if similarity > similarity_threshold:
                    is_duplicate = True
                    break

            if is_duplicate:
                continue

            # Add to unique results
            unique_results.append(result)
            seen_urls.add(normalized_url)
            seen_content_hashes.add(content_hash)

        return unique_results

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing query parameters and fragments.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL
        """
        try:
            parsed = urlparse(url)
            # Keep only scheme, netloc, and path
            normalized = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc.lower(),
                    parsed.path.rstrip("/"),
                    "",
                    "",
                    "",  # Remove params, query, fragment
                )
            )
            return normalized
        except Exception:
            return url.lower()

    def _calculate_content_hash(self, title: str, snippet: str) -> str:
        """
        Calculate content hash for similarity detection.

        Args:
            title: Result title
            snippet: Result snippet

        Returns:
            Content hash string
        """
        content = f"{title.lower()} {snippet.lower()}"
        # Remove punctuation and normalize whitespace
        content = "".join(c for c in content if c.isalnum() or c.isspace())
        content = " ".join(content.split())
        return hashlib.md5(content.encode()).hexdigest()

    def _calculate_similarity(self, hash1: str, hash2: str) -> float:
        """
        Calculate similarity between two content hashes.

        Args:
            hash1: First content hash
            hash2: Second content hash

        Returns:
            Similarity score (0-1)
        """
        # Exact hash match
        return 1.0 if hash1 == hash2 else 0.0
