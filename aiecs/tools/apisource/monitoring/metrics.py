"""
Detailed Metrics and Health Monitoring for API Providers

This module provides comprehensive performance tracking including:
- Response time percentiles
- Data volume statistics
- Error type distribution
- Rate limiting events
- Cache hit rates
- Overall health scoring
"""

import logging
import time
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DetailedMetrics:
    """
    Tracks detailed performance metrics for API providers.
    
    Provides comprehensive monitoring including response times, data volumes,
    error patterns, and overall health scoring.
    """
    
    def __init__(self, max_response_times: int = 100):
        """
        Initialize metrics tracker.
        
        Args:
            max_response_times: Maximum number of response times to keep in memory
        """
        self.max_response_times = max_response_times
        self.lock = Lock()
        
        # Request metrics
        self.metrics = {
            'requests': {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'cached': 0
            },
            'performance': {
                'response_times': [],  # Last N response times
                'avg_response_time_ms': 0.0,
                'p50_response_time_ms': 0.0,
                'p95_response_time_ms': 0.0,
                'p99_response_time_ms': 0.0,
                'min_response_time_ms': 0.0,
                'max_response_time_ms': 0.0
            },
            'data_volume': {
                'total_records_fetched': 0,
                'total_bytes_transferred': 0,
                'avg_records_per_request': 0.0,
                'avg_bytes_per_request': 0.0
            },
            'errors': {
                'by_type': defaultdict(int),  # {error_type: count}
                'recent_errors': []  # Last 10 errors with details
            },
            'rate_limiting': {
                'throttled_requests': 0,
                'total_wait_time_ms': 0.0,
                'avg_wait_time_ms': 0.0
            },
            'timestamps': {
                'first_request': None,
                'last_request': None,
                'last_success': None,
                'last_failure': None
            }
        }
    
    def record_request(
        self,
        success: bool,
        response_time_ms: float,
        record_count: int = 0,
        bytes_transferred: int = 0,
        cached: bool = False,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Record a request with its metrics.
        
        Args:
            success: Whether the request was successful
            response_time_ms: Response time in milliseconds
            record_count: Number of records returned
            bytes_transferred: Bytes transferred in the response
            cached: Whether the response was cached
            error_type: Type of error if failed (e.g., 'timeout', 'auth', 'rate_limit')
            error_message: Error message if failed
        """
        with self.lock:
            now = datetime.utcnow().isoformat()
            
            # Update request counts
            self.metrics['requests']['total'] += 1
            if success:
                self.metrics['requests']['successful'] += 1
                self.metrics['timestamps']['last_success'] = now
            else:
                self.metrics['requests']['failed'] += 1
                self.metrics['timestamps']['last_failure'] = now
            
            if cached:
                self.metrics['requests']['cached'] += 1
            
            # Update timestamps
            if self.metrics['timestamps']['first_request'] is None:
                self.metrics['timestamps']['first_request'] = now
            self.metrics['timestamps']['last_request'] = now
            
            # Update performance metrics
            self.metrics['performance']['response_times'].append(response_time_ms)
            if len(self.metrics['performance']['response_times']) > self.max_response_times:
                self.metrics['performance']['response_times'].pop(0)
            
            # Calculate percentiles
            self._calculate_percentiles()
            
            # Update data volume metrics
            self.metrics['data_volume']['total_records_fetched'] += record_count
            self.metrics['data_volume']['total_bytes_transferred'] += bytes_transferred
            
            total_requests = self.metrics['requests']['total']
            if total_requests > 0:
                self.metrics['data_volume']['avg_records_per_request'] = (
                    self.metrics['data_volume']['total_records_fetched'] / total_requests
                )
                self.metrics['data_volume']['avg_bytes_per_request'] = (
                    self.metrics['data_volume']['total_bytes_transferred'] / total_requests
                )
            
            # Record errors
            if not success and error_type:
                self.metrics['errors']['by_type'][error_type] += 1
                
                error_entry = {
                    'type': error_type,
                    'message': error_message or 'Unknown error',
                    'timestamp': now,
                    'response_time_ms': response_time_ms
                }
                
                self.metrics['errors']['recent_errors'].append(error_entry)
                if len(self.metrics['errors']['recent_errors']) > 10:
                    self.metrics['errors']['recent_errors'].pop(0)
    
    def record_rate_limit_wait(self, wait_time_ms: float):
        """
        Record a rate limit wait event.
        
        Args:
            wait_time_ms: Time waited in milliseconds
        """
        with self.lock:
            self.metrics['rate_limiting']['throttled_requests'] += 1
            self.metrics['rate_limiting']['total_wait_time_ms'] += wait_time_ms
            
            throttled = self.metrics['rate_limiting']['throttled_requests']
            if throttled > 0:
                self.metrics['rate_limiting']['avg_wait_time_ms'] = (
                    self.metrics['rate_limiting']['total_wait_time_ms'] / throttled
                )
    
    def _calculate_percentiles(self):
        """Calculate response time percentiles"""
        times = sorted(self.metrics['performance']['response_times'])
        if not times:
            return
        
        n = len(times)
        self.metrics['performance']['avg_response_time_ms'] = sum(times) / n
        self.metrics['performance']['min_response_time_ms'] = times[0]
        self.metrics['performance']['max_response_time_ms'] = times[-1]
        self.metrics['performance']['p50_response_time_ms'] = times[n // 2]
        self.metrics['performance']['p95_response_time_ms'] = times[int(n * 0.95)]
        self.metrics['performance']['p99_response_time_ms'] = times[min(int(n * 0.99), n - 1)]
    
    def _calculate_health_score_unlocked(self) -> float:
        """
        Calculate health score without acquiring lock (internal use only).
        Must be called while holding self.lock.
        """
        total = self.metrics['requests']['total']
        if total == 0:
            return 1.0

        # Success rate score (40%)
        success_rate = self.metrics['requests']['successful'] / total
        success_score = success_rate * 0.4

        # Performance score (30%)
        avg_time = self.metrics['performance']['avg_response_time_ms']
        # Assume < 200ms is excellent, > 2000ms is poor
        if avg_time < 200:
            performance_score = 0.3
        elif avg_time > 2000:
            performance_score = 0.0
        else:
            performance_score = max(0, min(1, (2000 - avg_time) / 1800)) * 0.3

        # Cache hit rate score (20%)
        cache_rate = self.metrics['requests']['cached'] / total
        cache_score = cache_rate * 0.2

        # Error diversity score (10%) - fewer error types is better
        error_types = len(self.metrics['errors']['by_type'])
        error_score = max(0, (5 - error_types) / 5) * 0.1

        return success_score + performance_score + cache_score + error_score

    def get_health_score(self) -> float:
        """
        Calculate overall health score (0-1).

        The health score considers:
        - Success rate (40%)
        - Performance (30%)
        - Cache hit rate (20%)
        - Error diversity (10%)

        Returns:
            Health score between 0 and 1
        """
        with self.lock:
            return self._calculate_health_score_unlocked()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get all metrics as a dictionary.
        
        Returns:
            Complete metrics dictionary
        """
        with self.lock:
            # Convert defaultdict to regular dict for JSON serialization
            stats = {
                'requests': dict(self.metrics['requests']),
                'performance': dict(self.metrics['performance']),
                'data_volume': dict(self.metrics['data_volume']),
                'errors': {
                    'by_type': dict(self.metrics['errors']['by_type']),
                    'recent_errors': list(self.metrics['errors']['recent_errors'])
                },
                'rate_limiting': dict(self.metrics['rate_limiting']),
                'timestamps': dict(self.metrics['timestamps']),
                'health_score': self.get_health_score()
            }
            
            # Remove response_times array to keep output clean
            stats['performance'] = {
                k: v for k, v in stats['performance'].items()
                if k != 'response_times'
            }
            
            return stats
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a concise summary of key metrics.

        Returns:
            Summary dictionary with key metrics
        """
        with self.lock:
            total = self.metrics['requests']['total']
            if total == 0:
                return {
                    'status': 'no_activity',
                    'health_score': 1.0
                }

            success_rate = self.metrics['requests']['successful'] / total
            cache_hit_rate = self.metrics['requests']['cached'] / total
            health_score = self._calculate_health_score_unlocked()  # Use unlocked version to avoid deadlock

            return {
                'status': 'healthy' if health_score > 0.7 else 'degraded',
                'health_score': round(health_score, 3),
                'total_requests': total,
                'success_rate': round(success_rate, 3),
                'cache_hit_rate': round(cache_hit_rate, 3),
                'avg_response_time_ms': round(
                    self.metrics['performance']['avg_response_time_ms'], 2
                ),
                'p95_response_time_ms': round(
                    self.metrics['performance']['p95_response_time_ms'], 2
                ),
                'total_errors': self.metrics['requests']['failed'],
                'error_types': len(self.metrics['errors']['by_type'])
            }
    
    def reset(self):
        """Reset all metrics"""
        with self.lock:
            self.__init__(self.max_response_times)

