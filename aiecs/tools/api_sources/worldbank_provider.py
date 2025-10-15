"""
World Bank API Provider

Provides access to World Bank development indicators and data.
Supports country data, indicators, and time series queries.

API Documentation: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from aiecs.tools.api_sources import register_provider
from aiecs.tools.api_sources.base_provider import BaseAPIProvider

logger = logging.getLogger(__name__)

# Optional HTTP client
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class WorldBankProvider(BaseAPIProvider):
    """
    World Bank API provider for development indicators and country data.
    
    Provides access to:
    - Economic indicators (GDP, inflation, trade, etc.)
    - Social indicators (education, health, population)
    - Environmental data
    - Country-specific statistics
    """
    
    BASE_URL = "https://api.worldbank.org/v2"
    
    @property
    def name(self) -> str:
        return "worldbank"
    
    @property
    def description(self) -> str:
        return "World Bank API for global development indicators and country statistics"
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            'get_indicator',
            'search_indicators',
            'get_country_data',
            'list_countries',
            'list_indicators'
        ]
    
    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for World Bank operations"""
        
        if operation == 'get_indicator':
            if 'indicator_code' not in params:
                return False, "Missing required parameter: indicator_code"
            if 'country_code' not in params:
                return False, "Missing required parameter: country_code"
        
        elif operation == 'get_country_data':
            if 'country_code' not in params:
                return False, "Missing required parameter: country_code"
        
        elif operation == 'search_indicators':
            if 'search_text' not in params:
                return False, "Missing required parameter: search_text"
        
        return True, None
    
    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from World Bank API"""
        
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for World Bank provider")
        
        # World Bank API doesn't require API key for most operations
        timeout = self.config.get('timeout', 30)
        
        # Build endpoint based on operation
        if operation == 'get_indicator':
            country = params['country_code']
            indicator = params['indicator_code']
            endpoint = f"{self.BASE_URL}/country/{country}/indicator/{indicator}"
            query_params = {'format': 'json'}
            
            # Optional parameters
            if 'date' in params:
                query_params['date'] = params['date']
            if 'per_page' in params:
                query_params['per_page'] = params['per_page']
        
        elif operation == 'get_country_data':
            country = params['country_code']
            endpoint = f"{self.BASE_URL}/country/{country}"
            query_params = {'format': 'json'}
        
        elif operation == 'list_countries':
            endpoint = f"{self.BASE_URL}/country"
            query_params = {'format': 'json', 'per_page': params.get('per_page', 100)}
        
        elif operation == 'list_indicators':
            endpoint = f"{self.BASE_URL}/indicator"
            query_params = {'format': 'json', 'per_page': params.get('per_page', 100)}
        
        elif operation == 'search_indicators':
            # World Bank doesn't have direct search, so we list and filter
            endpoint = f"{self.BASE_URL}/indicator"
            query_params = {'format': 'json', 'per_page': 1000}
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Make API request
        try:
            response = requests.get(
                endpoint,
                params=query_params,
                timeout=timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # World Bank API returns [metadata, data]
            if isinstance(data, list) and len(data) > 1:
                result_data = data[1]
            else:
                result_data = data
            
            # Filter for search operation
            if operation == 'search_indicators' and result_data:
                search_text = params['search_text'].lower()
                filtered = [
                    item for item in result_data
                    if search_text in str(item.get('name', '')).lower() or
                       search_text in str(item.get('sourceNote', '')).lower()
                ]
                result_data = filtered[:params.get('limit', 20)]
            
            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"World Bank API - {endpoint}"
            )
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"World Bank API request failed: {e}")
            raise Exception(f"World Bank API request failed: {str(e)}")


# Register the provider
register_provider(WorldBankProvider)

