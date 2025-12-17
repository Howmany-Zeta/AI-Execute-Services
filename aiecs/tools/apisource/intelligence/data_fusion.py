"""
Data Fusion Engine for Cross-Provider Results

Intelligently merges results from multiple API providers:
- Detect and handle duplicate data
- Resolve conflicts based on quality scores
- Support multiple fusion strategies
- Preserve provenance information
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, cast

logger = logging.getLogger(__name__)


class DataFusionEngine:
    """
    Fuses data from multiple providers intelligently.

    Handles duplicate detection, conflict resolution, and data quality
    optimization when combining results from different sources.
    """

    # Fusion strategies
    STRATEGY_BEST_QUALITY = "best_quality"
    STRATEGY_MERGE_ALL = "merge_all"
    STRATEGY_CONSENSUS = "consensus"
    STRATEGY_FIRST_SUCCESS = "first_success"

    def __init__(self):
        """Initialize data fusion engine"""

    def fuse_multi_provider_results(
        self,
        results: List[Dict[str, Any]],
        fusion_strategy: str = STRATEGY_BEST_QUALITY,
    ) -> Optional[Dict[str, Any]]:
        """
        Fuse results from multiple providers.

        Args:
            results: List of results from different providers
            fusion_strategy: Strategy to use for fusion:
                - 'best_quality': Select result with highest quality score
                - 'merge_all': Merge all results, preserving sources
                - 'consensus': Use data points agreed upon by multiple sources
                - 'first_success': Use first successful result

        Returns:
            Fused result dictionary or None if no valid results
        """
        if not results:
            return None

        # Filter out failed results
        valid_results = [r for r in results if r.get("data") is not None]

        if not valid_results:
            return None

        if fusion_strategy == self.STRATEGY_BEST_QUALITY:
            return self._fuse_best_quality(valid_results)

        elif fusion_strategy == self.STRATEGY_MERGE_ALL:
            return self._fuse_merge_all(valid_results)

        elif fusion_strategy == self.STRATEGY_CONSENSUS:
            return self._fuse_consensus(valid_results)

        elif fusion_strategy == self.STRATEGY_FIRST_SUCCESS:
            return valid_results[0]

        else:
            logger.warning(f"Unknown fusion strategy: {fusion_strategy}, using best_quality")
            return self._fuse_best_quality(valid_results)

    def _fuse_best_quality(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select result with highest quality score.

        Args:
            results: List of valid results

        Returns:
            Result with best quality
        """

        def get_quality_score(result: Dict[str, Any]) -> float:
            """Extract quality score from result"""
            metadata = result.get("metadata", {})
            quality = metadata.get("quality", {})
            return quality.get("score", 0.5)

        best_result = max(results, key=get_quality_score)

        # Add fusion metadata
        best_result["metadata"]["fusion_info"] = {
            "strategy": self.STRATEGY_BEST_QUALITY,
            "total_providers_queried": len(results),
            "selected_provider": best_result.get("provider"),
            "quality_score": get_quality_score(best_result),
            "alternative_providers": [r.get("provider") for r in results if r.get("provider") != best_result.get("provider")],
        }

        return best_result

    def _fuse_merge_all(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge all results, preserving source information.

        Args:
            results: List of valid results

        Returns:
            Merged result with all data
        """
        merged: Dict[str, Any] = {
            "operation": "multi_provider_search",
            "data": [],
            "metadata": {
                "fusion_info": {
                    "strategy": self.STRATEGY_MERGE_ALL,
                    "total_providers": len(results),
                    "sources": [],
                }
            },
        }

        # Collect all data with source tags
        for result in results:
            provider = result.get("provider", "unknown")
            data = result.get("data", [])
            metadata = result.get("metadata", {})

            # Handle different data structures
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # Add source information to each item
                        enriched_item = item.copy()
                        enriched_item["_source_provider"] = provider
                        enriched_item["_source_quality"] = metadata.get("quality", {})
                        enriched_item["_source_timestamp"] = metadata.get("timestamp")
                        merged["data"].append(enriched_item)
                    else:
                        # Handle non-dict items
                        merged["data"].append(
                            {
                                "value": item,
                                "_source_provider": provider,
                                "_source_quality": metadata.get("quality", {}),
                            }
                        )
            elif isinstance(data, dict):
                # Single dict result
                enriched_data = data.copy()
                enriched_data["_source_provider"] = provider
                enriched_data["_source_quality"] = metadata.get("quality", {})
                merged["data"].append(enriched_data)

            # Record source info
            fusion_info = cast(Dict[str, Any], merged["metadata"]["fusion_info"])
            sources = cast(List[Dict[str, Any]], fusion_info["sources"])
            sources.append(
                {
                    "provider": provider,
                    "operation": result.get("operation"),
                    "record_count": len(data) if isinstance(data, list) else 1,
                    "quality": metadata.get("quality", {}),
                }
            )

        return merged

    def _fuse_consensus(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use consensus-based fusion (data agreed upon by multiple sources).

        Implements sophisticated consensus logic:
        - Detects data point agreement across providers
        - Uses majority voting for conflicting values
        - Applies quality-weighted consensus calculation
        - Handles partial agreement scenarios
        - Calculates confidence scores

        Args:
            results: List of valid results

        Returns:
            Consensus result with confidence scores
        """
        if not results:
            return {}

        # Extract all data points with provider and quality information
        all_data_points: List[Dict[str, Any]] = []
        for result in results:
            provider = result.get("provider", "unknown")
            data = result.get("data", [])
            metadata = result.get("metadata", {})
            quality_score = metadata.get("quality", {}).get("score", 0.5)

            # Normalize data to list format
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        enriched_item = item.copy()
                        enriched_item["_provider"] = provider
                        enriched_item["_quality"] = quality_score
                        all_data_points.append(enriched_item)
                    else:
                        all_data_points.append({
                            "value": item,
                            "_provider": provider,
                            "_quality": quality_score
                        })
            elif isinstance(data, dict):
                enriched_data = data.copy()
                enriched_data["_provider"] = provider
                enriched_data["_quality"] = quality_score
                all_data_points.append(enriched_data)

        if not all_data_points:
            # Fallback to best quality if no data points
            return self._fuse_best_quality(results)

        # Group matching data points (agreement detection)
        data_groups = self._group_matching_data_points(all_data_points)

        # Build consensus result
        consensus_data = []
        total_confidence = 0.0
        agreement_stats = {
            "full_agreement": 0,
            "partial_agreement": 0,
            "conflicts": 0,
            "single_source": 0
        }

        for group in data_groups:
            if len(group) == 0:
                continue

            # Build consensus item from group
            consensus_item, confidence, agreement_type = self._build_consensus_item(group)
            consensus_data.append(consensus_item)
            total_confidence += confidence
            agreement_stats[agreement_type] += 1

        # Calculate average confidence
        avg_confidence = total_confidence / len(consensus_data) if consensus_data else 0.0

        # Build consensus result
        consensus_result: Dict[str, Any] = {
            "operation": "multi_provider_search",
            "data": consensus_data,
            "metadata": {
                "fusion_info": {
                    "strategy": self.STRATEGY_CONSENSUS,
                    "total_providers": len(results),
                    "providers": [r.get("provider", "unknown") for r in results],
                    "consensus_confidence": avg_confidence,
                    "agreement_stats": agreement_stats,
                    "data_points_analyzed": len(all_data_points),
                    "consensus_groups": len(data_groups),
                }
            }
        }

        return consensus_result

    def _group_matching_data_points(self, data_points: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group data points that represent the same entity/data point.

        Uses duplicate detection to identify matching data points across providers.

        Args:
            data_points: List of data points with provider info

        Returns:
            List of groups, where each group contains matching data points
        """
        groups: List[List[Dict[str, Any]]] = []
        processed = set()

        for i, data_point in enumerate(data_points):
            if i in processed:
                continue

            # Start a new group with this data point
            group = [data_point]
            processed.add(i)

            # Find matching data points
            for j, other_point in enumerate(data_points[i + 1:], start=i + 1):
                if j in processed:
                    continue

                is_duplicate, similarity = self.detect_duplicate_data(data_point, other_point)
                if is_duplicate:
                    group.append(other_point)
                    processed.add(j)

            groups.append(group)

        return groups

    def _build_consensus_item(
        self, group: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], float, str]:
        """
        Build a consensus item from a group of matching data points.

        Args:
            group: List of matching data points from different providers

        Returns:
            Tuple of (consensus_item, confidence_score, agreement_type)
        """
        if len(group) == 1:
            # Single source - use as-is with lower confidence
            item = group[0].copy()
            item.pop("_provider", None)
            item.pop("_quality", None)
            return item, 0.5, "single_source"

        # Multiple sources - build consensus
        consensus_item: Dict[str, Any] = {}
        field_agreements: Dict[str, List[Tuple[Any, float]]] = {}  # field -> [(value, quality), ...]

        # Collect all field values with their quality scores
        for data_point in group:
            quality = data_point.get("_quality", 0.5)
            for key, value in data_point.items():
                if key.startswith("_"):  # Skip metadata fields
                    continue
                if key not in field_agreements:
                    field_agreements[key] = []
                field_agreements[key].append((value, quality))

        # Build consensus for each field
        field_confidences: Dict[str, float] = {}
        full_agreement_count = 0
        partial_agreement_count = 0
        conflict_count = 0

        for field, value_quality_pairs in field_agreements.items():
            # Detect agreement
            unique_values = {}
            for value, quality in value_quality_pairs:
                value_key = str(value)  # Use string for comparison
                if value_key not in unique_values:
                    unique_values[value_key] = []
                unique_values[value_key].append((value, quality))

            if len(unique_values) == 1:
                # Full agreement - all providers have same value
                consensus_item[field] = value_quality_pairs[0][0]
                # Confidence based on number of agreeing sources and quality
                avg_quality = sum(q for _, q in value_quality_pairs) / len(value_quality_pairs)
                agreement_ratio = len(value_quality_pairs) / len(group)
                field_confidences[field] = avg_quality * agreement_ratio
                full_agreement_count += 1
            else:
                # Conflict - resolve using majority voting or quality weighting
                consensus_value, field_confidence = self._resolve_field_conflict(
                    unique_values, len(group)
                )
                consensus_item[field] = consensus_value
                field_confidences[field] = field_confidence
                
                # Check if majority agrees (>= 50%)
                max_agreement = max(len(vals) for vals in unique_values.values())
                if max_agreement >= len(group) * 0.5:
                    partial_agreement_count += 1
                else:
                    conflict_count += 1

        # Calculate overall confidence
        if field_confidences:
            overall_confidence = sum(field_confidences.values()) / len(field_confidences)
        else:
            overall_confidence = 0.5

        # Determine agreement type
        if conflict_count == 0 and partial_agreement_count == 0:
            agreement_type = "full_agreement"
        elif conflict_count == 0:
            agreement_type = "partial_agreement"
        else:
            agreement_type = "conflicts"

        # Add consensus metadata
        consensus_item["_consensus_metadata"] = {
            "sources_count": len(group),
            "providers": [dp.get("_provider", "unknown") for dp in group],
            "field_confidences": field_confidences,
            "overall_confidence": overall_confidence,
            "agreement_type": agreement_type,
        }

        return consensus_item, overall_confidence, agreement_type

    def _resolve_field_conflict(
        self, unique_values: Dict[str, List[Tuple[Any, float]]], total_sources: int
    ) -> Tuple[Any, float]:
        """
        Resolve conflict for a single field using majority voting and quality weighting.

        Args:
            unique_values: Dict mapping value strings to list of (value, quality) tuples
            total_sources: Total number of sources

        Returns:
            Tuple of (resolved_value, confidence_score)
        """
        # Calculate support (count) and quality-weighted scores for each value
        value_scores: List[Tuple[Any, float, int]] = []  # (value, quality_weighted_score, count)

        for value_str, value_quality_pairs in unique_values.items():
            count = len(value_quality_pairs)
            # Quality-weighted score: average quality * support ratio
            avg_quality = sum(q for _, q in value_quality_pairs) / count
            support_ratio = count / total_sources
            quality_weighted_score = avg_quality * support_ratio
            
            # Get original value (not string)
            original_value = value_quality_pairs[0][0]
            value_scores.append((original_value, quality_weighted_score, count))

        # Sort by quality-weighted score (descending), then by count (descending)
        value_scores.sort(key=lambda x: (x[1], x[2]), reverse=True)

        # Use majority voting: if majority agrees (>50%), use that value
        best_value, best_score, best_count = value_scores[0]
        
        # Check if majority agrees
        if best_count > total_sources / 2:
            # Majority vote wins
            confidence = best_score * (best_count / total_sources)
        else:
            # No clear majority - use quality-weighted consensus
            # Confidence is lower when no majority
            confidence = best_score * 0.7  # Penalty for no majority

        return best_value, confidence

    def detect_duplicate_data(
        self,
        data1: Dict[str, Any],
        data2: Dict[str, Any],
        key_fields: Optional[List[str]] = None,
    ) -> Tuple[bool, float]:
        """
        Detect if two data items are duplicates.

        Args:
            data1: First data item
            data2: Second data item
            key_fields: Fields to compare (auto-detected if None)

        Returns:
            Tuple of (is_duplicate, similarity_score)
        """
        if key_fields is None:
            # Auto-detect key fields
            key_fields = [
                "id",
                "series_id",
                "indicator_code",
                "indicator_id",
                "title",
                "name",
                "code",
            ]

        matches = 0
        total_fields = 0

        for field in key_fields:
            if field in data1 and field in data2:
                total_fields += 1
                if data1[field] == data2[field]:
                    matches += 1

        if total_fields == 0:
            # No common key fields, check title/name similarity
            return self._check_text_similarity(data1, data2)

        similarity = matches / total_fields if total_fields > 0 else 0.0
        is_duplicate = similarity > 0.8

        return is_duplicate, similarity

    def _check_text_similarity(self, data1: Dict[str, Any], data2: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Check text similarity for title/name fields.

        Args:
            data1: First data item
            data2: Second data item

        Returns:
            Tuple of (is_duplicate, similarity_score)
        """
        text_fields = ["title", "name", "description"]

        for field in text_fields:
            if field in data1 and field in data2:
                text1 = str(data1[field]).lower()
                text2 = str(data2[field]).lower()

                # Simple word-based similarity
                words1 = set(text1.split())
                words2 = set(text2.split())

                if not words1 or not words2:
                    continue

                intersection = len(words1 & words2)
                union = len(words1 | words2)

                similarity = intersection / union if union > 0 else 0.0

                if similarity > 0.7:
                    return True, similarity

        return False, 0.0

    def resolve_conflict(
        self,
        values: List[Dict[str, Any]],
        resolution_strategy: str = "quality",
    ) -> Any:
        """
        Resolve conflicts when multiple sources provide different values.

        Args:
            values: List of value dictionaries with {'value': ..., 'quality': ..., 'source': ...}
            resolution_strategy: Strategy for resolution ('quality', 'majority', 'average')

        Returns:
            Resolved value
        """
        if not values:
            return None

        if len(values) == 1:
            return values[0].get("value")

        if resolution_strategy == "quality":
            # Choose value from source with highest quality
            best = max(values, key=lambda v: v.get("quality", {}).get("score", 0))
            return best.get("value")

        elif resolution_strategy == "majority":
            # Use most common value
            from collections import Counter

            value_counts = Counter([str(v.get("value")) for v in values])
            most_common = value_counts.most_common(1)[0][0]
            # Return original type
            for v in values:
                if str(v.get("value")) == most_common:
                    return v.get("value")

        elif resolution_strategy == "average":
            # Average numeric values
            try:
                numeric_values = []
                for v in values:
                    value = v.get("value")
                    if value is not None:
                        try:
                            numeric_values.append(float(value))
                        except (ValueError, TypeError):
                            continue
                if numeric_values:
                    return sum(numeric_values) / len(numeric_values)
            except (ValueError, TypeError):
                # Fall back to quality-based
                return self.resolve_conflict(values, "quality")

        # Default: return first value
        return values[0].get("value")

    def deduplicate_results(
        self,
        data_list: List[Dict[str, Any]],
        key_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate entries from a data list.

        Args:
            data_list: List of data items
            key_fields: Fields to use for duplicate detection

        Returns:
            Deduplicated list
        """
        if not data_list:
            return []

        unique_data = []
        seen_signatures = set()

        for item in data_list:
            # Create a signature for this item
            if key_fields:
                signature = tuple(item.get(field) for field in key_fields if field in item)
            else:
                # Auto signature from common fields
                signature_fields = [
                    "id",
                    "series_id",
                    "indicator_code",
                    "title",
                    "name",
                ]
                signature = tuple(item.get(field) for field in signature_fields if field in item)

            if signature and signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_data.append(item)
            elif not signature:
                # No identifiable signature, include it
                unique_data.append(item)

        return unique_data
