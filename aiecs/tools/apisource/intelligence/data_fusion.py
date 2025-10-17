"""
Data Fusion Engine for Cross-Provider Results

Intelligently merges results from multiple API providers:
- Detect and handle duplicate data
- Resolve conflicts based on quality scores
- Support multiple fusion strategies
- Preserve provenance information
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DataFusionEngine:
    """
    Fuses data from multiple providers intelligently.
    
    Handles duplicate detection, conflict resolution, and data quality
    optimization when combining results from different sources.
    """
    
    # Fusion strategies
    STRATEGY_BEST_QUALITY = 'best_quality'
    STRATEGY_MERGE_ALL = 'merge_all'
    STRATEGY_CONSENSUS = 'consensus'
    STRATEGY_FIRST_SUCCESS = 'first_success'
    
    def __init__(self):
        """Initialize data fusion engine"""
        pass
    
    def fuse_multi_provider_results(
        self,
        results: List[Dict[str, Any]],
        fusion_strategy: str = STRATEGY_BEST_QUALITY
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
        valid_results = [
            r for r in results
            if r.get('data') is not None
        ]
        
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
            metadata = result.get('metadata', {})
            quality = metadata.get('quality', {})
            return quality.get('score', 0.5)
        
        best_result = max(results, key=get_quality_score)
        
        # Add fusion metadata
        best_result['metadata']['fusion_info'] = {
            'strategy': self.STRATEGY_BEST_QUALITY,
            'total_providers_queried': len(results),
            'selected_provider': best_result.get('provider'),
            'quality_score': get_quality_score(best_result),
            'alternative_providers': [
                r.get('provider') for r in results
                if r.get('provider') != best_result.get('provider')
            ]
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
        merged = {
            'operation': 'multi_provider_search',
            'data': [],
            'metadata': {
                'fusion_info': {
                    'strategy': self.STRATEGY_MERGE_ALL,
                    'total_providers': len(results),
                    'sources': []
                }
            }
        }
        
        # Collect all data with source tags
        for result in results:
            provider = result.get('provider', 'unknown')
            data = result.get('data', [])
            metadata = result.get('metadata', {})
            
            # Handle different data structures
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # Add source information to each item
                        enriched_item = item.copy()
                        enriched_item['_source_provider'] = provider
                        enriched_item['_source_quality'] = metadata.get('quality', {})
                        enriched_item['_source_timestamp'] = metadata.get('timestamp')
                        merged['data'].append(enriched_item)
                    else:
                        # Handle non-dict items
                        merged['data'].append({
                            'value': item,
                            '_source_provider': provider,
                            '_source_quality': metadata.get('quality', {})
                        })
            elif isinstance(data, dict):
                # Single dict result
                enriched_data = data.copy()
                enriched_data['_source_provider'] = provider
                enriched_data['_source_quality'] = metadata.get('quality', {})
                merged['data'].append(enriched_data)
            
            # Record source info
            merged['metadata']['fusion_info']['sources'].append({
                'provider': provider,
                'operation': result.get('operation'),
                'record_count': len(data) if isinstance(data, list) else 1,
                'quality': metadata.get('quality', {})
            })
        
        return merged
    
    def _fuse_consensus(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use consensus-based fusion (data agreed upon by multiple sources).
        
        Args:
            results: List of valid results
        
        Returns:
            Consensus result
        """
        # For now, implement a simple version
        # TODO: Implement more sophisticated consensus logic
        
        # Use best quality as baseline
        consensus = self._fuse_best_quality(results)
        
        # Update strategy in metadata
        consensus['metadata']['fusion_info']['strategy'] = self.STRATEGY_CONSENSUS
        consensus['metadata']['fusion_info']['note'] = (
            'Consensus strategy currently uses best quality baseline'
        )
        
        return consensus
    
    def detect_duplicate_data(
        self,
        data1: Dict[str, Any],
        data2: Dict[str, Any],
        key_fields: Optional[List[str]] = None
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
                'id', 'series_id', 'indicator_code', 'indicator_id',
                'title', 'name', 'code'
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
    
    def _check_text_similarity(
        self,
        data1: Dict[str, Any],
        data2: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        Check text similarity for title/name fields.
        
        Args:
            data1: First data item
            data2: Second data item
        
        Returns:
            Tuple of (is_duplicate, similarity_score)
        """
        text_fields = ['title', 'name', 'description']
        
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
        resolution_strategy: str = 'quality'
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
            return values[0].get('value')
        
        if resolution_strategy == 'quality':
            # Choose value from source with highest quality
            best = max(values, key=lambda v: v.get('quality', {}).get('score', 0))
            return best.get('value')
        
        elif resolution_strategy == 'majority':
            # Use most common value
            from collections import Counter
            value_counts = Counter([str(v.get('value')) for v in values])
            most_common = value_counts.most_common(1)[0][0]
            # Return original type
            for v in values:
                if str(v.get('value')) == most_common:
                    return v.get('value')
        
        elif resolution_strategy == 'average':
            # Average numeric values
            try:
                numeric_values = [
                    float(v.get('value'))
                    for v in values
                    if v.get('value') is not None
                ]
                if numeric_values:
                    return sum(numeric_values) / len(numeric_values)
            except (ValueError, TypeError):
                # Fall back to quality-based
                return self.resolve_conflict(values, 'quality')
        
        # Default: return first value
        return values[0].get('value')
    
    def deduplicate_results(
        self,
        data_list: List[Dict[str, Any]],
        key_fields: Optional[List[str]] = None
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
                signature = tuple(
                    item.get(field) for field in key_fields
                    if field in item
                )
            else:
                # Auto signature from common fields
                signature_fields = ['id', 'series_id', 'indicator_code', 'title', 'name']
                signature = tuple(
                    item.get(field) for field in signature_fields
                    if field in item
                )
            
            if signature and signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_data.append(item)
            elif not signature:
                # No identifiable signature, include it
                unique_data.append(item)
        
        return unique_data

