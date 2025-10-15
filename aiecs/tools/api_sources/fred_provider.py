"""
Federal Reserve Economic Data (FRED) API Provider

Provides access to Federal Reserve Economic Data through the FRED API.
Supports time series data retrieval, search, and metadata operations.

API Documentation: https://fred.stlouisfed.org/docs/api/fred/
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from aiecs.tools.api_sources import register_provider
from aiecs.tools.api_sources.base_provider import BaseAPIProvider

logger = logging.getLogger(__name__)

# Optional HTTP client - graceful degradation
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class FREDProvider(BaseAPIProvider):
    """
    Federal Reserve Economic Data (FRED) API provider.
    
    Provides access to economic indicators including:
    - GDP, unemployment, inflation data
    - Interest rates and monetary indicators
    - Regional economic data
    - International statistics
    """
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    @property
    def name(self) -> str:
        return "fred"
    
    @property
    def description(self) -> str:
        return "Federal Reserve Economic Data API for US economic indicators and time series"
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            'get_series',
            'search_series',
            'get_series_observations',
            'get_series_info',
            'get_categories',
            'get_releases'
        ]
    
    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for FRED operations"""
        
        if operation == 'get_series' or operation == 'get_series_info':
            if 'series_id' not in params:
                return False, "Missing required parameter: series_id"
        
        elif operation == 'get_series_observations':
            if 'series_id' not in params:
                return False, "Missing required parameter: series_id"
        
        elif operation == 'search_series':
            if 'search_text' not in params:
                return False, "Missing required parameter: search_text"
        
        return True, None
    
    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from FRED API"""
        
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for FRED provider. Install with: pip install requests")
        
        # Get API key
        api_key = self._get_api_key('FRED_API_KEY')
        if not api_key:
            raise ValueError(
                "FRED API key not found. Set FRED_API_KEY environment variable or "
                "provide 'api_key' in config"
            )
        
        # Build endpoint based on operation
        if operation == 'get_series' or operation == 'get_series_observations':
            endpoint = f"{self.BASE_URL}/series/observations"
            query_params = {
                'series_id': params['series_id'],
                'api_key': api_key,
                'file_type': 'json'
            }
            
            # Optional parameters
            if 'limit' in params:
                query_params['limit'] = params['limit']
            if 'offset' in params:
                query_params['offset'] = params['offset']
            if 'sort_order' in params:
                query_params['sort_order'] = params['sort_order']
            if 'observation_start' in params:
                query_params['observation_start'] = params['observation_start']
            if 'observation_end' in params:
                query_params['observation_end'] = params['observation_end']
        
        elif operation == 'get_series_info':
            endpoint = f"{self.BASE_URL}/series"
            query_params = {
                'series_id': params['series_id'],
                'api_key': api_key,
                'file_type': 'json'
            }
        
        elif operation == 'search_series':
            endpoint = f"{self.BASE_URL}/series/search"
            query_params = {
                'search_text': params['search_text'],
                'api_key': api_key,
                'file_type': 'json'
            }
            
            if 'limit' in params:
                query_params['limit'] = params['limit']
            if 'offset' in params:
                query_params['offset'] = params['offset']
        
        elif operation == 'get_categories':
            endpoint = f"{self.BASE_URL}/category"
            query_params = {
                'api_key': api_key,
                'file_type': 'json'
            }
            
            if 'category_id' in params:
                query_params['category_id'] = params['category_id']
        
        elif operation == 'get_releases':
            endpoint = f"{self.BASE_URL}/releases"
            query_params = {
                'api_key': api_key,
                'file_type': 'json'
            }
            
            if 'limit' in params:
                query_params['limit'] = params['limit']
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Make API request
        timeout = self.config.get('timeout', 30)
        try:
            response = requests.get(
                endpoint,
                params=query_params,
                timeout=timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract relevant data based on operation
            if operation in ['get_series', 'get_series_observations']:
                result_data = data.get('observations', [])
            elif operation == 'search_series':
                result_data = data.get('seriess', [])
            elif operation == 'get_series_info':
                result_data = data.get('seriess', [])
            elif operation == 'get_categories':
                result_data = data.get('categories', [])
            elif operation == 'get_releases':
                result_data = data.get('releases', [])
            else:
                result_data = data
            
            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"FRED API - {endpoint}"
            )
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"FRED API request failed: {e}")
            raise Exception(f"FRED API request failed: {str(e)}")


# Register the provider
register_provider(FREDProvider)

