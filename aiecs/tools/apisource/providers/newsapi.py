"""
News API Provider

Provides access to news articles from various sources worldwide.
Supports headline retrieval, article search, and source listing.

API Documentation: https://newsapi.org/docs
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from aiecs.tools.apisource.providers.base import BaseAPIProvider

logger = logging.getLogger(__name__)

# Optional HTTP client
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class NewsAPIProvider(BaseAPIProvider):
    """
    News API provider for accessing news articles and headlines.
    
    Provides access to:
    - Top headlines from various sources
    - Article search by keywords
    - News sources listing
    - Filtering by country, language, category
    """
    
    BASE_URL = "https://newsapi.org/v2"
    
    @property
    def name(self) -> str:
        return "newsapi"
    
    @property
    def description(self) -> str:
        return "News API for accessing news articles, headlines, and sources worldwide"
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            'get_top_headlines',
            'search_everything',
            'get_sources'
        ]
    
    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for News API operations"""
        
        if operation == 'get_top_headlines':
            # At least one of these is required
            if not any(k in params for k in ['q', 'country', 'category', 'sources']):
                return False, "At least one of q, country, category, or sources is required"
        
        elif operation == 'search_everything':
            if 'q' not in params:
                return False, "Missing required parameter: q (search query)"
        
        return True, None
    
    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from News API"""
        
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for News API provider")
        
        # Get API key
        api_key = self._get_api_key('NEWSAPI_API_KEY')
        if not api_key:
            raise ValueError(
                "News API key not found. Set NEWSAPI_API_KEY environment variable or "
                "provide 'api_key' in config. Get your key at https://newsapi.org"
            )
        
        headers = {'X-Api-Key': api_key}
        timeout = self.config.get('timeout', 30)
        
        # Build endpoint based on operation
        if operation == 'get_top_headlines':
            endpoint = f"{self.BASE_URL}/top-headlines"
            query_params = {}
            
            # Optional parameters
            if 'q' in params:
                query_params['q'] = params['q']
            if 'country' in params:
                query_params['country'] = params['country']
            if 'category' in params:
                query_params['category'] = params['category']
            if 'sources' in params:
                query_params['sources'] = params['sources']
            if 'page_size' in params:
                query_params['pageSize'] = params['page_size']
            if 'page' in params:
                query_params['page'] = params['page']
        
        elif operation == 'search_everything':
            endpoint = f"{self.BASE_URL}/everything"
            query_params = {
                'q': params['q']
            }
            
            # Optional parameters
            if 'from_date' in params:
                query_params['from'] = params['from_date']
            elif 'days_back' in params:
                # Convenience parameter: go back N days
                from_date = datetime.now() - timedelta(days=params['days_back'])
                query_params['from'] = from_date.strftime('%Y-%m-%d')
            
            if 'to_date' in params:
                query_params['to'] = params['to_date']
            if 'language' in params:
                query_params['language'] = params['language']
            if 'sort_by' in params:
                query_params['sortBy'] = params['sort_by']
            if 'page_size' in params:
                query_params['pageSize'] = params['page_size']
            if 'page' in params:
                query_params['page'] = params['page']
        
        elif operation == 'get_sources':
            endpoint = f"{self.BASE_URL}/top-headlines/sources"
            query_params = {}
            
            # Optional parameters
            if 'country' in params:
                query_params['country'] = params['country']
            if 'language' in params:
                query_params['language'] = params['language']
            if 'category' in params:
                query_params['category'] = params['category']
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Make API request
        try:
            response = requests.get(
                endpoint,
                params=query_params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check API response status
            if data.get('status') != 'ok':
                raise Exception(f"News API error: {data.get('message', 'Unknown error')}")
            
            # Extract relevant data
            if operation == 'get_sources':
                result_data = data.get('sources', [])
            else:
                result_data = {
                    'articles': data.get('articles', []),
                    'total_results': data.get('totalResults', 0)
                }
            
            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"News API - {endpoint}"
            )
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"News API request failed: {e}")
            raise Exception(f"News API request failed: {str(e)}")

