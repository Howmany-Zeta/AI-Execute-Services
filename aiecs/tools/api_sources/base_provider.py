"""
Base API Provider Interface

Abstract base class for all API data source providers in the API Source Tool.
Provides common functionality for rate limiting, caching, error handling, and metadata.
"""

import logging
import time
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API requests"""
    
    def __init__(self, tokens_per_second: float = 1.0, max_tokens: int = 10):
        """
        Initialize rate limiter with token bucket algorithm.
        
        Args:
            tokens_per_second: Rate at which tokens are added to the bucket
            max_tokens: Maximum number of tokens the bucket can hold
        """
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_update = time.time()
        self.lock = Lock()
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add new tokens based on elapsed time
            self.tokens = min(
                self.max_tokens,
                self.tokens + elapsed * self.tokens_per_second
            )
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """
        Wait until tokens are available.
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if tokens were acquired, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.acquire(tokens):
                return True
            time.sleep(0.1)
        return False


class BaseAPIProvider(ABC):
    """
    Abstract base class for all API data source providers.
    
    Provides:
    - Rate limiting with token bucket algorithm
    - Standardized error handling
    - Metadata about provider capabilities
    - Parameter validation
    - Response formatting
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the API provider.
        
        Args:
            config: Configuration dictionary with API keys, rate limits, etc.
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize rate limiter
        rate_limit = self.config.get('rate_limit', 10)  # requests per second
        max_burst = self.config.get('max_burst', 20)
        self.rate_limiter = RateLimiter(
            tokens_per_second=rate_limit,
            max_tokens=max_burst
        )
        
        # Request statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'last_request_time': None
        }
        self.stats_lock = Lock()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'fred', 'worldbank')"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the provider"""
        pass
    
    @property
    @abstractmethod
    def supported_operations(self) -> List[str]:
        """List of supported operation names"""
        pass
    
    @abstractmethod
    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate parameters for a specific operation.
        
        Args:
            operation: Operation name
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch data from the API.
        
        Args:
            operation: Operation to perform
            params: Operation parameters
            
        Returns:
            Response data in standardized format
            
        Raises:
            ValueError: If operation is not supported
            Exception: If API request fails
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get provider metadata.
        
        Returns:
            Dictionary with provider information
        """
        return {
            'name': self.name,
            'description': self.description,
            'operations': self.supported_operations,
            'stats': dict(self.stats),
            'config': {
                'rate_limit': self.config.get('rate_limit', 10),
                'timeout': self.config.get('timeout', 30)
            }
        }
    
    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """
        Get schema for a specific operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Schema dictionary or None if not available
        """
        # Override in subclass to provide operation-specific schemas
        return None
    
    def _update_stats(self, success: bool):
        """Update request statistics"""
        with self.stats_lock:
            self.stats['total_requests'] += 1
            if success:
                self.stats['successful_requests'] += 1
            else:
                self.stats['failed_requests'] += 1
            self.stats['last_request_time'] = datetime.utcnow().isoformat()
    
    def _format_response(
        self, 
        operation: str, 
        data: Any, 
        source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format response in standardized format.
        
        Args:
            operation: Operation that was performed
            data: Response data
            source: Data source URL or identifier
            
        Returns:
            Standardized response dictionary
        """
        return {
            'provider': self.name,
            'operation': operation,
            'data': data,
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'source': source or f'{self.name} API',
                'cached': False
            }
        }
    
    def _get_api_key(self, key_name: Optional[str] = None) -> Optional[str]:
        """
        Get API key from config or environment.
        
        Args:
            key_name: Specific key name to retrieve
            
        Returns:
            API key or None if not found
        """
        import os
        
        # Try config first
        if 'api_key' in self.config:
            return self.config['api_key']
        
        # Try environment variable
        env_var = key_name or f'{self.name.upper()}_API_KEY'
        return os.getenv(env_var)
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an operation with rate limiting and error handling.
        
        Args:
            operation: Operation to perform
            params: Operation parameters
            
        Returns:
            Response data
            
        Raises:
            ValueError: If operation is invalid
            Exception: If API request fails
        """
        # Validate operation
        if operation not in self.supported_operations:
            raise ValueError(
                f"Operation '{operation}' not supported. "
                f"Supported operations: {', '.join(self.supported_operations)}"
            )
        
        # Validate parameters
        is_valid, error_msg = self.validate_params(operation, params)
        if not is_valid:
            raise ValueError(f"Invalid parameters: {error_msg}")
        
        # Apply rate limiting
        if not self.rate_limiter.wait(tokens=1, timeout=30):
            raise Exception("Rate limit exceeded, please try again later")
        
        # Execute request
        try:
            self.logger.info(f"Executing {self.name}.{operation} with params: {params}")
            result = self.fetch(operation, params)
            self._update_stats(success=True)
            return result
        except Exception as e:
            self._update_stats(success=False)
            self.logger.error(f"Error executing {self.name}.{operation}: {e}")
            raise

