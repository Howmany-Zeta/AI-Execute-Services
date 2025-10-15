"""
US Census Bureau API Provider

Provides access to US Census Bureau data including demographic,
economic, and geographic information.

API Documentation: https://www.census.gov/data/developers/guidance/api-user-guide.html
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


class CensusProvider(BaseAPIProvider):
    """
    US Census Bureau API provider for demographic and economic data.
    
    Provides access to:
    - American Community Survey (ACS) data
    - Decennial Census
    - Economic indicators
    - Population estimates
    - Geographic data
    """
    
    BASE_URL = "https://api.census.gov/data"
    
    @property
    def name(self) -> str:
        return "census"
    
    @property
    def description(self) -> str:
        return "US Census Bureau API for demographic, economic, and geographic data"
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            'get_acs_data',
            'get_population',
            'get_economic_data',
            'list_datasets',
            'list_variables'
        ]
    
    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Census API operations"""
        
        if operation == 'get_acs_data':
            if 'variables' not in params:
                return False, "Missing required parameter: variables"
            if 'geography' not in params:
                return False, "Missing required parameter: geography"
        
        elif operation == 'get_population':
            if 'geography' not in params:
                return False, "Missing required parameter: geography"
        
        elif operation == 'get_economic_data':
            if 'variables' not in params:
                return False, "Missing required parameter: variables"
        
        return True, None
    
    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Census API"""
        
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Census provider")
        
        # Census API may require a key for some datasets
        api_key = self._get_api_key('CENSUS_API_KEY')
        timeout = self.config.get('timeout', 30)
        
        # Build endpoint based on operation
        if operation == 'get_acs_data':
            # American Community Survey 5-Year Data
            year = params.get('year', '2021')
            endpoint = f"{self.BASE_URL}/{year}/acs/acs5"
            
            # Build query parameters
            variables = params['variables']
            if isinstance(variables, list):
                variables = ','.join(variables)
            
            geography = params['geography']
            
            query_params = {
                'get': variables,
                'for': geography
            }
            
            if api_key:
                query_params['key'] = api_key
        
        elif operation == 'get_population':
            # Population Estimates
            year = params.get('year', '2021')
            endpoint = f"{self.BASE_URL}/{year}/pep/population"
            
            geography = params['geography']
            variables = params.get('variables', 'POP')
            
            query_params = {
                'get': variables,
                'for': geography
            }
            
            if api_key:
                query_params['key'] = api_key
        
        elif operation == 'get_economic_data':
            # Economic Census or other economic data
            year = params.get('year', '2017')
            dataset = params.get('dataset', 'ecnbasic')
            endpoint = f"{self.BASE_URL}/{year}/ecnbasic"
            
            variables = params['variables']
            if isinstance(variables, list):
                variables = ','.join(variables)
            
            geography = params.get('geography', 'state:*')
            
            query_params = {
                'get': variables,
                'for': geography
            }
            
            if api_key:
                query_params['key'] = api_key
        
        elif operation == 'list_datasets':
            # List available datasets
            endpoint = f"{self.BASE_URL}.json"
            query_params = {}
        
        elif operation == 'list_variables':
            # List variables for a dataset
            year = params.get('year', '2021')
            dataset = params.get('dataset', 'acs/acs5')
            endpoint = f"{self.BASE_URL}/{year}/{dataset}/variables.json"
            query_params = {}
        
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
            
            # Census API typically returns array of arrays
            # First row is headers, subsequent rows are data
            if operation in ['get_acs_data', 'get_population', 'get_economic_data']:
                if isinstance(data, list) and len(data) > 1:
                    headers = data[0]
                    rows = data[1:]
                    
                    # Convert to list of dictionaries
                    result_data = [
                        dict(zip(headers, row)) for row in rows
                    ]
                else:
                    result_data = data
            else:
                result_data = data
            
            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"US Census Bureau - {endpoint}"
            )
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Census API request failed: {e}")
            raise Exception(f"Census API request failed: {str(e)}")


# Register the provider
register_provider(CensusProvider)

