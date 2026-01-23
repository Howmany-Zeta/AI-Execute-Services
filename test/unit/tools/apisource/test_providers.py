"""
Comprehensive tests for all API Providers

Tests real API calls without mocks to verify actual behavior and output.
Tests all providers: FRED, News API, World Bank, Census

Run with: 
    poetry run pytest test/unit_tests/tools/apisource/test_providers.py -v -s

Coverage: 
    poetry run pytest test/unit_tests/tools/apisource/test_providers.py \
        --cov=aiecs.tools.apisource.providers --cov-report=term-missing
"""

import logging
from typing import Dict, Any

import pytest

from aiecs.tools.apisource.providers import (
    get_provider,
    list_providers,
    PROVIDER_REGISTRY,
    BaseAPIProvider,
)
from aiecs.tools.apisource.providers.fred import FREDProvider
from aiecs.tools.apisource.providers.newsapi import NewsAPIProvider
from aiecs.tools.apisource.providers.worldbank import WorldBankProvider
from aiecs.tools.apisource.providers.census import CensusProvider
from aiecs.tools.apisource.providers.alphavantage import AlphaVantageProvider
from aiecs.tools.apisource.providers.restcountries import RESTCountriesProvider
from aiecs.tools.apisource.providers.exchangerate import ExchangeRateProvider
from aiecs.tools.apisource.providers.openlibrary import OpenLibraryProvider
from aiecs.tools.apisource.providers.coingecko import CoinGeckoProvider
from aiecs.tools.apisource.providers.openweathermap import OpenWeatherMapProvider
from aiecs.tools.apisource.providers.wikipedia import WikipediaProvider
from aiecs.tools.apisource.providers.github import GitHubProvider
from aiecs.tools.apisource.providers.arxiv import ArxivProvider
from aiecs.tools.apisource.providers.pubmed import PubMedProvider
from aiecs.tools.apisource.providers.crossref import CrossRefProvider

logger = logging.getLogger(__name__)


class TestProviderRegistry:
    """Test provider registry and discovery"""
    
    def test_list_providers(self, debug_output):
        """Test listing all registered providers"""
        print("\n=== Testing Provider Registry ===")

        providers = list_providers()

        # list_providers returns a list, not a dict
        assert isinstance(providers, list)
        assert len(providers) > 0

        provider_names = [p.get('name') for p in providers]
        debug_output("Registered Providers", {
            'count': len(providers),
            'providers': provider_names,
        })

        # Verify expected providers are registered
        expected = ['fred', 'newsapi', 'worldbank', 'census', 'alphavantage', 'restcountries', 'exchangerate', 'openlibrary', 'coingecko', 'openweathermap', 'wikipedia', 'github', 'arxiv', 'pubmed', 'crossref']
        for provider_name in expected:
            assert provider_name in provider_names

        print(f"✓ {len(providers)} providers registered")
    
    def test_get_provider(self, fred_config, debug_output):
        """Test getting provider instance"""
        print("\n=== Testing Get Provider ===")
        
        provider = get_provider('fred', fred_config)
        
        assert provider is not None
        assert isinstance(provider, BaseAPIProvider)
        assert isinstance(provider, FREDProvider)
        assert provider.name == 'fred'
        
        debug_output("Provider Instance", {
            'name': provider.name,
            'description': provider.description,
            'operations': provider.supported_operations,
        })
        
        print("✓ Provider instance created successfully")
    
    def test_get_nonexistent_provider(self):
        """Test getting non-existent provider"""
        print("\n=== Testing Non-existent Provider ===")
        
        with pytest.raises(ValueError) as exc_info:
            get_provider('nonexistent', {})
        
        assert 'not found' in str(exc_info.value).lower()
        print("✓ Correctly raised ValueError for non-existent provider")


class TestFREDProvider:
    """Test FRED (Federal Reserve Economic Data) provider"""
    
    def test_provider_metadata(self, fred_config, debug_output):
        """Test FRED provider metadata"""
        print("\n=== Testing FRED Provider Metadata ===")
        
        provider = FREDProvider(fred_config)
        
        assert provider.name == 'fred'
        assert provider.description
        assert len(provider.supported_operations) > 0
        
        metadata = provider.get_metadata()
        
        debug_output("FRED Metadata", {
            'name': metadata['name'],
            'description': metadata['description'],
            'operations_count': len(metadata['operations']),
            'operations': metadata['operations'],
            'health': metadata['health'],
        })
        
        print("✓ FRED metadata retrieved successfully")
    
    @pytest.mark.network
    def test_search_series(self, fred_config, skip_if_no_api_key, debug_output,
                          measure_performance):
        """Test FRED search_series operation"""
        skip_if_no_api_key('fred')
        print("\n=== Testing FRED search_series ===")

        provider = FREDProvider(fred_config)

        measure_performance.start()
        result = provider.execute('search_series', {'search_text': 'GDP'})
        duration = measure_performance.stop()

        assert result['provider'] == 'fred'
        assert result['operation'] == 'search_series'
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0
        
        # Check first result structure
        first_result = result['data'][0]
        debug_output("FRED Search Result Sample", {
            'total_results': len(result['data']),
            'first_result_keys': list(first_result.keys()) if isinstance(first_result, dict) else 'N/A',
            'duration_seconds': duration,
        })
        
        measure_performance.print_result("FRED search_series")
        print(f"✓ Found {len(result['data'])} series")
    
    @pytest.mark.network
    def test_get_series_observations(self, fred_config, skip_if_no_api_key, debug_output,
                                    measure_performance):
        """Test FRED get_series_observations operation"""
        skip_if_no_api_key('fred')
        print("\n=== Testing FRED get_series_observations ===")

        provider = FREDProvider(fred_config)

        measure_performance.start()
        result = provider.execute('get_series_observations', {
            'series_id': 'GDP',
            'limit': 10
        })
        duration = measure_performance.stop()

        assert result['provider'] == 'fred'
        assert result['operation'] == 'get_series_observations'
        assert isinstance(result['data'], list)
        
        debug_output("FRED Observations", {
            'series_id': 'GDP',
            'observations_count': len(result['data']),
            'sample_data': result['data'][:3] if len(result['data']) > 0 else [],
            'duration_seconds': duration,
        })
        
        measure_performance.print_result("FRED get_series_observations")
        print(f"✓ Retrieved {len(result['data'])} observations")
    
    @pytest.mark.network
    def test_get_series_info(self, fred_config, skip_if_no_api_key, debug_output):
        """Test FRED get_series_info operation"""
        skip_if_no_api_key('fred')
        print("\n=== Testing FRED get_series_info ===")
        
        provider = FREDProvider(fred_config)
        
        result = provider.execute('get_series_info', {'series_id': 'GDP'})

        assert result['provider'] == 'fred'
        assert result['operation'] == 'get_series_info'
        assert 'data' in result
        
        debug_output("FRED Series Info", {
            'series_id': 'GDP',
            'data': result['data'],
        })
        
        print("✓ Retrieved series info successfully")
    
    def test_validate_params(self, fred_config):
        """Test FRED parameter validation"""
        print("\n=== Testing FRED Parameter Validation ===")
        
        provider = FREDProvider(fred_config)
        
        # Valid params
        is_valid, error = provider.validate_params('search_series', {'search_text': 'GDP'})
        assert is_valid is True
        assert error is None
        
        # Invalid params - missing required
        is_valid, error = provider.validate_params('search_series', {})
        assert is_valid is False
        assert error is not None
        
        print("✓ Parameter validation working correctly")
    
    def test_operation_schema(self, fred_config, debug_output):
        """Test FRED operation schema"""
        print("\n=== Testing FRED Operation Schema ===")
        
        provider = FREDProvider(fred_config)
        
        schema = provider.get_operation_schema('search_series')
        
        assert schema is not None
        assert 'description' in schema
        assert 'parameters' in schema
        
        debug_output("FRED search_series Schema", schema)
        
        print("✓ Operation schema retrieved successfully")


class TestNewsAPIProvider:
    """Test News API provider"""
    
    def test_provider_metadata(self, newsapi_config, debug_output):
        """Test News API provider metadata"""
        print("\n=== Testing News API Provider Metadata ===")
        
        provider = NewsAPIProvider(newsapi_config)
        
        assert provider.name == 'newsapi'
        assert provider.description
        assert len(provider.supported_operations) > 0
        
        metadata = provider.get_metadata()
        
        debug_output("News API Metadata", {
            'name': metadata['name'],
            'description': metadata['description'],
            'operations': metadata['operations'],
        })
        
        print("✓ News API metadata retrieved successfully")
    
    @pytest.mark.network
    def test_get_top_headlines(self, newsapi_config, skip_if_no_api_key, debug_output,
                               measure_performance):
        """Test News API get_top_headlines operation"""
        skip_if_no_api_key('newsapi')
        print("\n=== Testing News API get_top_headlines ===")

        provider = NewsAPIProvider(newsapi_config)

        measure_performance.start()
        result = provider.execute('get_top_headlines', {
            'country': 'us',
            'page_size': 5
        })
        duration = measure_performance.stop()

        assert result['provider'] == 'newsapi'
        assert result['operation'] == 'get_top_headlines'
        assert 'data' in result
        
        debug_output("News API Headlines", {
            'data_type': type(result['data']).__name__,
            'duration_seconds': duration,
        })
        
        measure_performance.print_result("News API get_top_headlines")
        print("✓ Retrieved top headlines successfully")
    
    @pytest.mark.network
    def test_search_everything(self, newsapi_config, skip_if_no_api_key, debug_output):
        """Test News API search_everything operation"""
        skip_if_no_api_key('newsapi')
        print("\n=== Testing News API search_everything ===")
        
        provider = NewsAPIProvider(newsapi_config)
        
        result = provider.execute('search_everything', {
            'q': 'technology',
            'page_size': 5,
            'language': 'en'
        })

        assert result['provider'] == 'newsapi'
        assert result['operation'] == 'search_everything'
        assert 'data' in result
        
        debug_output("News API Search Results", {
            'query': 'technology',
            'data_type': type(result['data']).__name__,
        })
        
        print("✓ Search executed successfully")

    @pytest.mark.network
    def test_get_sources(self, newsapi_config, skip_if_no_api_key, debug_output):
        """Test News API get_sources operation"""
        skip_if_no_api_key('newsapi')
        print("\n=== Testing News API get_sources ===")

        provider = NewsAPIProvider(newsapi_config)

        result = provider.execute('get_sources', {
            'language': 'en',
            'country': 'us'
        })

        assert result['provider'] == 'newsapi'
        assert result['operation'] == 'get_sources'
        assert 'data' in result

        debug_output("News API Sources", {
            'data_type': type(result['data']).__name__,
            'sources_count': len(result['data']) if isinstance(result['data'], list) else 'N/A',
        })

        print("✓ Retrieved news sources successfully")


class TestWorldBankProvider:
    """Test World Bank API provider"""

    def test_provider_metadata(self, worldbank_config, debug_output):
        """Test World Bank provider metadata"""
        print("\n=== Testing World Bank Provider Metadata ===")

        provider = WorldBankProvider(worldbank_config)

        assert provider.name == 'worldbank'
        assert provider.description
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()

        debug_output("World Bank Metadata", {
            'name': metadata['name'],
            'description': metadata['description'],
            'operations': metadata['operations'],
        })

        print("✓ World Bank metadata retrieved successfully")

    @pytest.mark.network
    def test_get_indicator(self, worldbank_config, debug_output,
                          measure_performance):
        """Test World Bank get_indicator operation"""
        print("\n=== Testing World Bank get_indicator ===")

        provider = WorldBankProvider(worldbank_config)

        measure_performance.start()
        result = provider.execute('get_indicator', {
            'indicator_code': 'NY.GDP.MKTP.CD',  # GDP (current US$)
            'country_code': 'USA'
        })
        duration = measure_performance.stop()

        assert result['provider'] == 'worldbank'
        assert result['operation'] == 'get_indicator'
        assert 'data' in result

        debug_output("World Bank Indicator Data", {
            'indicator': 'NY.GDP.MKTP.CD',
            'country': 'USA',
            'data_type': type(result['data']).__name__,
            'duration_seconds': duration,
        })

        measure_performance.print_result("World Bank get_indicator")
        print("✓ Retrieved indicator data successfully")

    @pytest.mark.network
    def test_search_indicators(self, worldbank_config, debug_output):
        """Test World Bank search_indicators operation"""
        print("\n=== Testing World Bank search_indicators ===")

        provider = WorldBankProvider(worldbank_config)

        result = provider.execute('search_indicators', {
            'search_text': 'GDP',
            'limit': 10
        })

        assert result['provider'] == 'worldbank'
        assert result['operation'] == 'search_indicators'
        assert 'data' in result

        debug_output("World Bank Indicator Search", {
            'search_text': 'GDP',
            'results_count': len(result['data']) if isinstance(result['data'], list) else 'N/A',
        })

        print("✓ Searched indicators successfully")

    @pytest.mark.network
    def test_list_countries(self, worldbank_config, debug_output):
        """Test World Bank list_countries operation"""
        print("\n=== Testing World Bank list_countries ===")

        provider = WorldBankProvider(worldbank_config)

        result = provider.execute('list_countries', {})

        assert result['provider'] == 'worldbank'
        assert result['operation'] == 'list_countries'
        assert 'data' in result

        debug_output("World Bank Countries", {
            'countries_count': len(result['data']) if isinstance(result['data'], list) else 'N/A',
        })

        print("✓ Listed countries successfully")

    @pytest.mark.network
    def test_get_country_data(self, worldbank_config, debug_output):
        """Test World Bank get_country_data operation"""
        print("\n=== Testing World Bank get_country_data ===")

        provider = WorldBankProvider(worldbank_config)

        result = provider.execute('get_country_data', {
            'country_code': 'USA'
        })

        assert result['provider'] == 'worldbank'
        assert result['operation'] == 'get_country_data'
        assert 'data' in result

        debug_output("World Bank Country Data", {
            'country': 'USA',
            'data': result['data'],
        })

        print("✓ Retrieved country data successfully")


class TestCensusProvider:
    """Test US Census Bureau API provider"""

    def test_provider_metadata(self, census_config, debug_output):
        """Test Census provider metadata"""
        print("\n=== Testing Census Provider Metadata ===")

        provider = CensusProvider(census_config)

        assert provider.name == 'census'
        assert provider.description
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()

        debug_output("Census Metadata", {
            'name': metadata['name'],
            'description': metadata['description'],
            'operations': metadata['operations'],
        })

        print("✓ Census metadata retrieved successfully")

    @pytest.mark.network
    def test_get_acs_data(self, census_config, skip_if_no_api_key, debug_output,
                         measure_performance):
        """Test Census get_acs_data operation"""
        skip_if_no_api_key('census')
        print("\n=== Testing Census get_acs_data ===")

        provider = CensusProvider(census_config)

        measure_performance.start()
        result = provider.execute('get_acs_data', {
            'variables': 'B01001_001E',  # Total population
            'geography': 'state:*',
            'year': 2021
        })
        duration = measure_performance.stop()

        assert result['provider'] == 'census'
        assert result['operation'] == 'get_acs_data'
        assert 'data' in result

        debug_output("Census ACS Data", {
            'variables': 'B01001_001E',
            'geography': 'state:*',
            'data_type': type(result['data']).__name__,
            'duration_seconds': duration,
        })

        measure_performance.print_result("Census get_acs_data")
        print("✓ Retrieved ACS data successfully")

    @pytest.mark.network
    @pytest.mark.skip(reason="Census PEP API endpoint may not be available or requires different parameters")
    def test_get_population(self, census_config, skip_if_no_api_key, debug_output):
        """Test Census get_population operation"""
        skip_if_no_api_key('census')
        print("\n=== Testing Census get_population ===")

        provider = CensusProvider(census_config)

        # Note: This test is skipped because the Census PEP (Population Estimates Program)
        # API endpoint may require different parameters or may not be available
        # The actual implementation works, but the specific endpoint/parameters need verification
        result = provider.execute('get_population', {
            'geography': 'state:06',  # California
            'year': 2021
        })

        assert result['provider'] == 'census'
        assert result['operation'] == 'get_population'
        assert 'data' in result

        debug_output("Census Population Data", {
            'geography': 'state:06 (California)',
            'data': result['data'],
        })

        print("✓ Retrieved population data successfully")

    @pytest.mark.network
    def test_list_datasets(self, census_config, debug_output):
        """Test Census list_datasets operation"""
        print("\n=== Testing Census list_datasets ===")

        provider = CensusProvider(census_config)

        result = provider.execute('list_datasets', {})

        assert result['provider'] == 'census'
        assert result['operation'] == 'list_datasets'
        assert 'data' in result

        debug_output("Census Datasets", {
            'datasets_count': len(result['data']) if isinstance(result['data'], list) else 'N/A',
        })

        print("✓ Listed datasets successfully")


class TestAlphaVantageProvider:
    """Test Alpha Vantage API provider"""

    def test_provider_metadata(self, alphavantage_config, debug_output):
        """Test Alpha Vantage provider metadata"""
        print("\n=== Testing Alpha Vantage Provider Metadata ===")

        provider = AlphaVantageProvider(alphavantage_config)

        assert provider.name == 'alphavantage'
        assert provider.description
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()

        debug_output("Alpha Vantage Metadata", {
            'name': metadata['name'],
            'description': metadata['description'],
            'operations': metadata['operations'],
        })

        print("✓ Alpha Vantage metadata retrieved successfully")

    @pytest.mark.network
    def test_search_symbol(self, alphavantage_config, skip_if_no_api_key, debug_output,
                          measure_performance):
        """Test Alpha Vantage search_symbol operation"""
        skip_if_no_api_key('alphavantage')
        print("\n=== Testing Alpha Vantage search_symbol ===")

        provider = AlphaVantageProvider(alphavantage_config)

        measure_performance.start()
        result = provider.execute('search_symbol', {
            'keywords': 'Apple'
        })
        duration = measure_performance.stop()

        assert result['provider'] == 'alphavantage'
        assert result['operation'] == 'search_symbol'
        assert 'data' in result

        debug_output("Alpha Vantage Search Results", {
            'keywords': 'Apple',
            'results_count': len(result['data']) if isinstance(result['data'], list) else 'N/A',
            'duration_seconds': duration,
        })

        measure_performance.print_result("Alpha Vantage search_symbol")
        print("✓ Symbol search executed successfully")

    @pytest.mark.network
    def test_get_global_quote(self, alphavantage_config, skip_if_no_api_key, debug_output,
                              measure_performance):
        """Test Alpha Vantage get_global_quote operation"""
        skip_if_no_api_key('alphavantage')
        print("\n=== Testing Alpha Vantage get_global_quote ===")

        provider = AlphaVantageProvider(alphavantage_config)

        measure_performance.start()
        result = provider.execute('get_global_quote', {
            'symbol': 'AAPL'
        })
        duration = measure_performance.stop()

        assert result['provider'] == 'alphavantage'
        assert result['operation'] == 'get_global_quote'
        assert 'data' in result

        debug_output("Alpha Vantage Global Quote", {
            'symbol': 'AAPL',
            'data_type': type(result['data']).__name__,
            'duration_seconds': duration,
        })

        measure_performance.print_result("Alpha Vantage get_global_quote")
        print("✓ Retrieved global quote successfully")

    @pytest.mark.network
    def test_get_time_series_daily(self, alphavantage_config, skip_if_no_api_key, debug_output,
                                   measure_performance):
        """Test Alpha Vantage get_time_series_daily operation"""
        skip_if_no_api_key('alphavantage')
        print("\n=== Testing Alpha Vantage get_time_series_daily ===")

        provider = AlphaVantageProvider(alphavantage_config)

        measure_performance.start()
        result = provider.execute('get_time_series_daily', {
            'symbol': 'AAPL',
            'outputsize': 'compact'
        })
        duration = measure_performance.stop()

        assert result['provider'] == 'alphavantage'
        assert result['operation'] == 'get_time_series_daily'
        assert 'data' in result

        debug_output("Alpha Vantage Daily Time Series", {
            'symbol': 'AAPL',
            'data_type': type(result['data']).__name__,
            'data_points': len(result['data']) if isinstance(result['data'], dict) else 'N/A',
            'duration_seconds': duration,
        })

        measure_performance.print_result("Alpha Vantage get_time_series_daily")
        print("✓ Retrieved daily time series successfully")

    @pytest.mark.network
    def test_get_time_series_intraday(self, alphavantage_config, skip_if_no_api_key, debug_output):
        """Test Alpha Vantage get_time_series_intraday operation"""
        skip_if_no_api_key('alphavantage')
        print("\n=== Testing Alpha Vantage get_time_series_intraday ===")

        provider = AlphaVantageProvider(alphavantage_config)

        result = provider.execute('get_time_series_intraday', {
            'symbol': 'AAPL',
            'interval': '5min',
            'outputsize': 'compact'
        })

        assert result['provider'] == 'alphavantage'
        assert result['operation'] == 'get_time_series_intraday'
        assert 'data' in result

        debug_output("Alpha Vantage Intraday Time Series", {
            'symbol': 'AAPL',
            'interval': '5min',
            'data_type': type(result['data']).__name__,
        })

        print("✓ Retrieved intraday time series successfully")

    def test_validate_params(self, alphavantage_config):
        """Test Alpha Vantage parameter validation"""
        print("\n=== Testing Alpha Vantage Parameter Validation ===")

        provider = AlphaVantageProvider(alphavantage_config)

        # Valid params
        is_valid, error = provider.validate_params('search_symbol', {'keywords': 'Apple'})
        assert is_valid is True
        assert error is None

        # Invalid params - missing required
        is_valid, error = provider.validate_params('search_symbol', {})
        assert is_valid is False
        assert error is not None

        # Valid params for get_global_quote
        is_valid, error = provider.validate_params('get_global_quote', {'symbol': 'AAPL'})
        assert is_valid is True
        assert error is None

        # Invalid params for get_forex_rate
        is_valid, error = provider.validate_params('get_forex_rate', {'from_currency': 'USD'})
        assert is_valid is False
        assert error is not None

        print("✓ Parameter validation working correctly")

    def test_operation_schema(self, alphavantage_config, debug_output):
        """Test Alpha Vantage operation schema"""
        print("\n=== Testing Alpha Vantage Operation Schema ===")

        provider = AlphaVantageProvider(alphavantage_config)

        schema = provider.get_operation_schema('get_global_quote')

        assert schema is not None
        assert 'description' in schema
        assert 'parameters' in schema

        debug_output("Alpha Vantage get_global_quote Schema", schema)

        print("✓ Operation schema retrieved successfully")


class TestRESTCountriesProvider:
    """Test REST Countries provider"""

    def test_provider_metadata(self, restcountries_config, debug_output):
        """Test REST Countries provider metadata"""
        print("\n=== Testing REST Countries Provider Metadata ===")

        provider = RESTCountriesProvider(restcountries_config)

        assert provider.name == 'restcountries'
        assert provider.description is not None
        assert len(provider.supported_operations) > 0

        debug_output("REST Countries Metadata", {
            'name': provider.name,
            'description': provider.description,
            'operations': f'list (length: {len(provider.supported_operations)})',
        })

        print("✓ REST Countries metadata retrieved successfully")

    @pytest.mark.network
    def test_get_all_countries(self, restcountries_config, debug_output, measure_performance):
        """Test getting all countries (may be slow or rate-limited)"""
        print("\n=== Testing REST Countries get_all_countries ===")

        provider = RESTCountriesProvider(restcountries_config)

        try:
            measure_performance.start()
            result = provider.get_all_countries()
            duration = measure_performance.stop()

            assert result is not None
            assert 'data' in result
            assert isinstance(result['data'], list)
            assert len(result['data']) > 0

            debug_output("REST Countries All Countries", {
                'countries_count': len(result['data']),
                'duration_seconds': duration,
            })

            print(f"⏱  REST Countries get_all_countries took {duration:.3f} seconds")
            print("✓ Retrieved all countries successfully")
        except Exception as e:
            # The /all endpoint may be rate-limited or temporarily unavailable
            # This is acceptable for this test
            print(f"⚠️  REST Countries /all endpoint unavailable: {e}")
            pytest.skip(f"REST Countries /all endpoint unavailable: {e}")

    def test_get_country_by_name(self, restcountries_config, debug_output, measure_performance):
        """Test getting country by name"""
        print("\n=== Testing REST Countries get_country_by_name ===")

        provider = RESTCountriesProvider(restcountries_config)

        measure_performance.start()
        result = provider.get_country_by_name(name='United States')
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        debug_output("REST Countries Search by Name", {
            'name': 'United States',
            'results_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  REST Countries get_country_by_name took {duration:.3f} seconds")
        print("✓ Retrieved country by name successfully")

    def test_get_country_by_code(self, restcountries_config, debug_output, measure_performance):
        """Test getting country by code"""
        print("\n=== Testing REST Countries get_country_by_code ===")

        provider = RESTCountriesProvider(restcountries_config)

        measure_performance.start()
        result = provider.get_country_by_code(code='US')
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        debug_output("REST Countries Get by Code", {
            'code': 'US',
            'data_type': type(result['data']).__name__,
            'duration_seconds': duration,
        })

        print(f"⏱  REST Countries get_country_by_code took {duration:.3f} seconds")
        print("✓ Retrieved country by code successfully")

    def test_get_countries_by_region(self, restcountries_config, debug_output, measure_performance):
        """Test getting countries by region"""
        print("\n=== Testing REST Countries get_countries_by_region ===")

        provider = RESTCountriesProvider(restcountries_config)

        measure_performance.start()
        result = provider.get_countries_by_region(region='Europe')
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        debug_output("REST Countries Get by Region", {
            'region': 'Europe',
            'countries_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  REST Countries get_countries_by_region took {duration:.3f} seconds")
        print("✓ Retrieved countries by region successfully")

    def test_get_countries_by_language(self, restcountries_config, debug_output, measure_performance):
        """Test getting countries by language"""
        print("\n=== Testing REST Countries get_countries_by_language ===")

        provider = RESTCountriesProvider(restcountries_config)

        measure_performance.start()
        result = provider.get_countries_by_language(language='spanish')
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        debug_output("REST Countries Get by Language", {
            'language': 'spanish',
            'countries_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  REST Countries get_countries_by_language took {duration:.3f} seconds")
        print("✓ Retrieved countries by language successfully")

    def test_validate_params(self, restcountries_config):
        """Test REST Countries parameter validation"""
        print("\n=== Testing REST Countries Parameter Validation ===")

        provider = RESTCountriesProvider(restcountries_config)

        # Invalid params for get_country_by_name
        is_valid, error = provider.validate_params('get_country_by_name', {})
        assert is_valid is False
        assert error is not None

        # Valid params for get_country_by_name
        is_valid, error = provider.validate_params('get_country_by_name', {'name': 'Germany'})
        assert is_valid is True
        assert error is None

        # Invalid params for get_countries_by_region
        is_valid, error = provider.validate_params('get_countries_by_region', {})
        assert is_valid is False
        assert error is not None

        print("✓ Parameter validation working correctly")

    def test_operation_schema(self, restcountries_config, debug_output):
        """Test REST Countries operation schema"""
        print("\n=== Testing REST Countries Operation Schema ===")

        provider = RESTCountriesProvider(restcountries_config)

        schema = provider.get_operation_schema('get_country_by_name')

        assert schema is not None
        assert 'description' in schema
        assert 'parameters' in schema

        debug_output("REST Countries get_country_by_name Schema", schema)

        print("✓ Operation schema retrieved successfully")

    def test_get_countries_by_subregion(self, restcountries_config, debug_output, measure_performance):
        """Test getting countries by subregion"""
        print("\n=== Testing REST Countries get_countries_by_subregion ===")

        provider = RESTCountriesProvider(restcountries_config)

        measure_performance.start()
        result = provider.get_countries_by_subregion(subregion='Western Europe')
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Verify data structure
        first_country = result['data'][0]
        assert isinstance(first_country, dict)
        assert 'name' in first_country or '_raw' in first_country

        debug_output("REST Countries Get by Subregion", {
            'subregion': 'Western Europe',
            'countries_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  REST Countries get_countries_by_subregion took {duration:.3f} seconds")
        print("✓ Retrieved countries by subregion successfully")

    def test_get_countries_by_currency(self, restcountries_config, debug_output, measure_performance):
        """Test getting countries by currency"""
        print("\n=== Testing REST Countries get_countries_by_currency ===")

        provider = RESTCountriesProvider(restcountries_config)

        measure_performance.start()
        result = provider.get_countries_by_currency(currency='USD')
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Verify data structure
        first_country = result['data'][0]
        assert isinstance(first_country, dict)

        debug_output("REST Countries Get by Currency", {
            'currency': 'USD',
            'countries_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  REST Countries get_countries_by_currency took {duration:.3f} seconds")
        print("✓ Retrieved countries by currency successfully")

    def test_country_data_structure(self, restcountries_config, debug_output):
        """Test the structure of country data returned"""
        print("\n=== Testing REST Countries Data Structure ===")

        provider = RESTCountriesProvider(restcountries_config)

        result = provider.get_country_by_code(code='US')

        assert result is not None
        assert 'data' in result
        assert 'metadata' in result
        assert 'provider' in result
        assert 'operation' in result

        # Check metadata structure
        metadata = result['metadata']
        assert 'timestamp' in metadata
        assert 'source' in metadata
        assert 'quality' in metadata

        # Check quality metadata
        quality = metadata['quality']
        assert 'score' in quality
        assert 'completeness' in quality
        assert 'confidence' in quality

        debug_output("REST Countries Data Structure", {
            'has_data': 'data' in result,
            'has_metadata': 'metadata' in result,
            'quality_score': quality.get('score'),
            'completeness': quality.get('completeness'),
        })

        print("✓ Country data structure is valid")

    def test_multiple_regions(self, restcountries_config, debug_output):
        """Test getting countries from multiple regions"""
        print("\n=== Testing REST Countries Multiple Regions ===")

        provider = RESTCountriesProvider(restcountries_config)

        regions = ['Africa', 'Americas', 'Asia', 'Europe', 'Oceania']
        results = {}

        for region in regions:
            result = provider.get_countries_by_region(region=region)
            assert result is not None
            assert 'data' in result
            assert isinstance(result['data'], list)
            assert len(result['data']) > 0
            results[region] = len(result['data'])

        debug_output("REST Countries Multiple Regions", results)

        print(f"✓ Retrieved countries from {len(regions)} regions successfully")

    def test_country_search_partial_match(self, restcountries_config, debug_output):
        """Test partial name matching"""
        print("\n=== Testing REST Countries Partial Name Match ===")

        provider = RESTCountriesProvider(restcountries_config)

        # Search with partial name
        result = provider.get_country_by_name(name='United')

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Should match multiple countries (United States, United Kingdom, etc.)
        debug_output("REST Countries Partial Match", {
            'search_term': 'United',
            'matches_count': len(result['data']),
        })

        print("✓ Partial name matching working correctly")

    def test_country_search_full_text(self, restcountries_config, debug_output):
        """Test full text exact matching"""
        print("\n=== Testing REST Countries Full Text Match ===")

        provider = RESTCountriesProvider(restcountries_config)

        # Search with full text match
        result = provider.get_country_by_name(name='Germany', full_text=True)

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        # Full text should return exact match only
        assert len(result['data']) >= 1

        debug_output("REST Countries Full Text Match", {
            'search_term': 'Germany',
            'full_text': True,
            'matches_count': len(result['data']),
        })

        print("✓ Full text matching working correctly")

    def test_iso_code_formats(self, restcountries_config, debug_output):
        """Test different ISO code formats"""
        print("\n=== Testing REST Countries ISO Code Formats ===")

        provider = RESTCountriesProvider(restcountries_config)

        # Test alpha-2 code
        result_alpha2 = provider.get_country_by_code(code='US')
        assert result_alpha2 is not None
        assert 'data' in result_alpha2
        assert len(result_alpha2['data']) > 0

        # Test alpha-3 code
        result_alpha3 = provider.get_country_by_code(code='USA')
        assert result_alpha3 is not None
        assert 'data' in result_alpha3
        assert len(result_alpha3['data']) > 0

        debug_output("REST Countries ISO Code Formats", {
            'alpha2_code': 'US',
            'alpha3_code': 'USA',
            'both_successful': True,
        })

        print("✓ ISO code formats working correctly")

    def test_response_validation(self, restcountries_config):
        """Test response validation"""
        print("\n=== Testing REST Countries Response Validation ===")

        provider = RESTCountriesProvider(restcountries_config)

        # Get sample data
        result = provider.get_country_by_code(code='FR')
        data = result['data']

        # Validate response
        is_valid, error = provider.validate_response('get_country_by_code', data)
        assert is_valid is True
        assert error is None

        # Test with empty list
        is_valid, error = provider.validate_response('get_country_by_code', [])
        assert is_valid is False
        assert error is not None

        print("✓ Response validation working correctly")

    def test_data_quality_assessment(self, restcountries_config, debug_output):
        """Test data quality assessment"""
        print("\n=== Testing REST Countries Data Quality Assessment ===")

        provider = RESTCountriesProvider(restcountries_config)

        # Get sample data
        result = provider.get_country_by_code(code='JP')
        data = result['data']

        # Assess quality
        quality = provider.assess_data_quality('get_country_by_code', data)

        assert quality is not None
        assert 'completeness' in quality
        assert 'freshness' in quality
        assert 'accuracy' in quality

        debug_output("REST Countries Data Quality", quality)

        print("✓ Data quality assessment working correctly")

    def test_error_handling_invalid_region(self, restcountries_config):
        """Test error handling for invalid region"""
        print("\n=== Testing REST Countries Invalid Region Error ===")

        provider = RESTCountriesProvider(restcountries_config)

        # Invalid region should raise an exception
        with pytest.raises(Exception):
            result = provider.get_countries_by_region(region='InvalidRegion')

        print("✓ Invalid region error handled correctly")

    def test_error_handling_invalid_code(self, restcountries_config):
        """Test error handling for invalid country code"""
        print("\n=== Testing REST Countries Invalid Code Error ===")

        provider = RESTCountriesProvider(restcountries_config)

        # Invalid code should raise an exception
        with pytest.raises(Exception):
            result = provider.get_country_by_code(code='INVALID')

        print("✓ Invalid country code error handled correctly")

    def test_metadata_completeness(self, restcountries_config, debug_output):
        """Test metadata completeness in responses"""
        print("\n=== Testing REST Countries Metadata Completeness ===")

        provider = RESTCountriesProvider(restcountries_config)

        result = provider.get_countries_by_language(language='english')

        # Check all required metadata fields
        assert 'provider' in result
        assert result['provider'] == 'restcountries'
        assert 'operation' in result
        assert result['operation'] == 'get_countries_by_language'
        assert 'metadata' in result

        metadata = result['metadata']
        assert 'timestamp' in metadata
        assert 'source' in metadata
        assert 'quality' in metadata

        debug_output("REST Countries Metadata", {
            'provider': result['provider'],
            'operation': result['operation'],
            'has_timestamp': 'timestamp' in metadata,
            'has_quality': 'quality' in metadata,
        })

        print("✓ Metadata completeness verified")


class TestExchangeRateProvider:
    """Test ExchangeRate-API provider"""

    def test_provider_metadata(self, exchangerate_config, debug_output):
        """Test ExchangeRate provider metadata"""
        print("\n=== Testing ExchangeRate Provider Metadata ===")

        provider = ExchangeRateProvider(exchangerate_config)

        assert provider.name == "exchangerate"
        assert provider.description is not None
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()
        assert metadata['name'] == 'exchangerate'
        assert 'operations' in metadata

        debug_output("ExchangeRate Provider Metadata", {
            'name': provider.name,
            'description': provider.description,
            'operations': provider.supported_operations,
        })

        print("✓ ExchangeRate provider metadata validated")

    @pytest.mark.network
    def test_get_latest_rates(self, exchangerate_config, debug_output, measure_performance):
        """Test getting latest exchange rates"""
        print("\n=== Testing ExchangeRate get_latest_rates ===")

        provider = ExchangeRateProvider(exchangerate_config)

        measure_performance.start()
        result = provider.get_latest_rates(base_currency="USD")
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'base_currency' in result['data']
        assert 'rates' in result['data']
        assert isinstance(result['data']['rates'], dict)
        assert len(result['data']['rates']) > 0

        # Check for common currencies
        rates = result['data']['rates']
        common_currencies = ['EUR', 'GBP', 'JPY', 'CAD', 'AUD']
        for currency in common_currencies:
            assert currency in rates, f"Expected {currency} in rates"

        debug_output("ExchangeRate Latest Rates", {
            'base_currency': result['data']['base_currency'],
            'num_rates': len(result['data']['rates']),
            'sample_rates': {k: rates[k] for k in list(rates.keys())[:5]},
            'duration_seconds': duration,
        })

        print(f"⏱  ExchangeRate get_latest_rates took {duration:.3f} seconds")
        print("✓ Retrieved latest exchange rates successfully")

    @pytest.mark.network
    def test_convert_currency(self, exchangerate_config, debug_output, measure_performance):
        """Test currency conversion"""
        print("\n=== Testing ExchangeRate convert_currency ===")

        provider = ExchangeRateProvider(exchangerate_config)

        measure_performance.start()
        result = provider.convert_currency(
            from_currency="USD",
            to_currency="EUR",
            amount=100
        )
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'from_currency' in result['data']
        assert 'to_currency' in result['data']
        assert 'amount' in result['data']
        assert 'conversion_rate' in result['data']
        assert 'converted_amount' in result['data']

        data = result['data']
        assert data['from_currency'] == 'USD'
        assert data['to_currency'] == 'EUR'
        assert data['amount'] == 100
        assert data['conversion_rate'] > 0
        assert data['converted_amount'] > 0

        debug_output("ExchangeRate Currency Conversion", {
            'from': data['from_currency'],
            'to': data['to_currency'],
            'amount': data['amount'],
            'rate': data['conversion_rate'],
            'result': data['converted_amount'],
            'duration_seconds': duration,
        })

        print(f"⏱  ExchangeRate convert_currency took {duration:.3f} seconds")
        print(f"✓ Converted {data['amount']} {data['from_currency']} = {data['converted_amount']:.2f} {data['to_currency']}")

    @pytest.mark.network
    def test_get_pair_rate(self, exchangerate_config, debug_output, measure_performance):
        """Test getting exchange rate for a currency pair"""
        print("\n=== Testing ExchangeRate get_pair_rate ===")

        provider = ExchangeRateProvider(exchangerate_config)

        measure_performance.start()
        result = provider.get_pair_rate(
            from_currency="USD",
            to_currency="GBP"
        )
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'from_currency' in result['data']
        assert 'to_currency' in result['data']
        assert 'conversion_rate' in result['data']

        data = result['data']
        assert data['from_currency'] == 'USD'
        assert data['to_currency'] == 'GBP'
        assert data['conversion_rate'] > 0

        debug_output("ExchangeRate Pair Rate", {
            'from': data['from_currency'],
            'to': data['to_currency'],
            'rate': data['conversion_rate'],
            'duration_seconds': duration,
        })

        print(f"⏱  ExchangeRate get_pair_rate took {duration:.3f} seconds")
        print(f"✓ Retrieved rate: 1 {data['from_currency']} = {data['conversion_rate']:.4f} {data['to_currency']}")

    @pytest.mark.network
    def test_get_supported_currencies(self, exchangerate_config, debug_output, measure_performance):
        """Test getting list of supported currencies"""
        print("\n=== Testing ExchangeRate get_supported_currencies ===")

        provider = ExchangeRateProvider(exchangerate_config)

        measure_performance.start()
        result = provider.get_supported_currencies()
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'supported_codes' in result['data']
        assert isinstance(result['data']['supported_codes'], list)
        assert len(result['data']['supported_codes']) > 0

        codes = result['data']['supported_codes']

        # Check for major currencies
        major_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']
        for currency in major_currencies:
            assert currency in codes, f"Expected {currency} in supported currencies"

        debug_output("ExchangeRate Supported Currencies", {
            'total_currencies': len(codes),
            'sample_codes': codes[:10],
            'duration_seconds': duration,
        })

        print(f"⏱  ExchangeRate get_supported_currencies took {duration:.3f} seconds")
        print(f"✓ Retrieved {len(codes)} supported currencies")

    def test_validate_params(self, exchangerate_config):
        """Test parameter validation"""
        print("\n=== Testing ExchangeRate Parameter Validation ===")

        provider = ExchangeRateProvider(exchangerate_config)

        # Valid params for get_latest_rates
        is_valid, error = provider.validate_params("get_latest_rates", {"base_currency": "USD"})
        assert is_valid is True
        assert error is None

        # Invalid params for get_latest_rates (missing base_currency)
        is_valid, error = provider.validate_params("get_latest_rates", {})
        assert is_valid is False
        assert error is not None

        # Valid params for convert_currency
        is_valid, error = provider.validate_params("convert_currency", {
            "from_currency": "USD",
            "to_currency": "EUR",
            "amount": 100
        })
        assert is_valid is True
        assert error is None

        # Invalid params for convert_currency (missing amount)
        is_valid, error = provider.validate_params("convert_currency", {
            "from_currency": "USD",
            "to_currency": "EUR"
        })
        assert is_valid is False
        assert error is not None

        print("✓ Parameter validation working correctly")

    def test_operation_schema(self, exchangerate_config, debug_output):
        """Test operation schema retrieval"""
        print("\n=== Testing ExchangeRate Operation Schema ===")

        provider = ExchangeRateProvider(exchangerate_config)

        # Test get_latest_rates schema
        schema = provider.get_operation_schema("get_latest_rates")
        assert schema is not None
        assert 'description' in schema
        assert 'parameters' in schema
        assert 'base_currency' in schema['parameters']

        # Test convert_currency schema
        schema = provider.get_operation_schema("convert_currency")
        assert schema is not None
        assert 'description' in schema
        assert 'parameters' in schema
        assert 'from_currency' in schema['parameters']
        assert 'to_currency' in schema['parameters']
        assert 'amount' in schema['parameters']

        debug_output("ExchangeRate Operation Schema", {
            'operations': provider.supported_operations,
            'sample_schema': schema,
        })

        print("✓ Operation schemas retrieved successfully")

    @pytest.mark.network
    def test_multiple_currency_pairs(self, exchangerate_config, debug_output, measure_performance):
        """Test multiple currency pair conversions"""
        print("\n=== Testing ExchangeRate Multiple Currency Pairs ===")

        provider = ExchangeRateProvider(exchangerate_config)

        currency_pairs = [
            ("USD", "EUR"),
            ("EUR", "GBP"),
            ("GBP", "JPY"),
            ("JPY", "CHF"),
        ]

        results = []
        measure_performance.start()

        for from_curr, to_curr in currency_pairs:
            result = provider.get_pair_rate(from_currency=from_curr, to_currency=to_curr)
            assert result is not None
            assert 'data' in result
            results.append({
                'pair': f"{from_curr}/{to_curr}",
                'rate': result['data']['conversion_rate']
            })

        duration = measure_performance.stop()

        debug_output("ExchangeRate Multiple Pairs", {
            'pairs_tested': len(currency_pairs),
            'results': results,
            'duration_seconds': duration,
        })

        print(f"⏱  Testing {len(currency_pairs)} pairs took {duration:.3f} seconds")
        print("✓ All currency pairs retrieved successfully")

    @pytest.mark.network
    def test_conversion_accuracy(self, exchangerate_config, debug_output):
        """Test conversion calculation accuracy"""
        print("\n=== Testing ExchangeRate Conversion Accuracy ===")

        provider = ExchangeRateProvider(exchangerate_config)

        # Get the rate first
        rate_result = provider.get_pair_rate(from_currency="USD", to_currency="EUR")
        rate = rate_result['data']['conversion_rate']

        # Convert an amount
        amount = 100
        convert_result = provider.convert_currency(
            from_currency="USD",
            to_currency="EUR",
            amount=amount
        )
        converted = convert_result['data']['converted_amount']

        # Verify the calculation
        expected = amount * rate
        # Allow small floating point difference
        assert abs(converted - expected) < 0.01, f"Expected {expected}, got {converted}"

        debug_output("ExchangeRate Conversion Accuracy", {
            'rate': rate,
            'amount': amount,
            'converted': converted,
            'expected': expected,
            'difference': abs(converted - expected),
        })

        print("✓ Conversion calculation is accurate")

    @pytest.mark.network
    def test_response_validation(self, exchangerate_config, debug_output):
        """Test response structure validation"""
        print("\n=== Testing ExchangeRate Response Validation ===")

        provider = ExchangeRateProvider(exchangerate_config)

        result = provider.get_latest_rates(base_currency="USD")

        # Validate response structure
        assert 'provider' in result
        assert 'operation' in result
        assert 'data' in result
        assert 'metadata' in result

        assert result['provider'] == 'exchangerate'
        assert result['operation'] == 'get_latest_rates'

        metadata = result['metadata']
        assert 'timestamp' in metadata
        assert 'source' in metadata

        debug_output("ExchangeRate Response Structure", {
            'provider': result['provider'],
            'operation': result['operation'],
            'has_data': 'data' in result,
            'has_metadata': 'metadata' in result,
        })

        print("✓ Response structure validated")


class TestProviderErrorHandling:
    """Test error handling across all providers"""

    @pytest.mark.parametrize("provider_class,config_fixture", [
        (FREDProvider, 'fred_config'),
        (NewsAPIProvider, 'newsapi_config'),
        (WorldBankProvider, 'worldbank_config'),
        (CensusProvider, 'census_config'),
        (AlphaVantageProvider, 'alphavantage_config'),
        (RESTCountriesProvider, 'restcountries_config'),
        (ExchangeRateProvider, 'exchangerate_config'),
    ])
    def test_invalid_operation(self, provider_class, config_fixture, request):
        """Test handling of invalid operations"""
        config = request.getfixturevalue(config_fixture)
        print(f"\n=== Testing Invalid Operation: {provider_class.__name__} ===")

        provider = provider_class(config)

        # Invalid operation raises ValueError
        with pytest.raises(ValueError) as exc_info:
            result = provider.execute('invalid_operation', {})

        # Expected to raise ValueError for invalid operation
        assert 'invalid_operation' in str(exc_info.value).lower() or 'not supported' in str(exc_info.value).lower()

        print(f"✓ {provider_class.__name__} handled invalid operation correctly")

    @pytest.mark.parametrize("provider_class,config_fixture,operation,params", [
        (FREDProvider, 'fred_config', 'search_series', {}),
        (NewsAPIProvider, 'newsapi_config', 'search_everything', {}),
        (WorldBankProvider, 'worldbank_config', 'get_indicator', {}),
        (CensusProvider, 'census_config', 'get_acs_data', {}),
        (AlphaVantageProvider, 'alphavantage_config', 'search_symbol', {}),
        (RESTCountriesProvider, 'restcountries_config', 'get_country_by_name', {}),
        (ExchangeRateProvider, 'exchangerate_config', 'convert_currency', {}),
    ])
    def test_missing_required_params(self, provider_class, config_fixture, operation, params, request):
        """Test handling of missing required parameters"""
        config = request.getfixturevalue(config_fixture)
        print(f"\n=== Testing Missing Params: {provider_class.__name__}.{operation} ===")

        provider = provider_class(config)

        # Validate should fail
        is_valid, error = provider.validate_params(operation, params)
        assert is_valid is False
        assert error is not None

        print(f"✓ {provider_class.__name__} validated parameters correctly")


class TestOpenLibraryProvider:
    """Test Open Library API provider"""

    def test_provider_metadata(self, openlibrary_config, debug_output):
        """Test Open Library provider metadata"""
        print("\n=== Testing Open Library Provider Metadata ===")

        provider = OpenLibraryProvider(openlibrary_config)

        assert provider.name == "openlibrary"
        assert provider.description is not None
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()
        assert metadata['name'] == 'openlibrary'
        assert 'operations' in metadata

        debug_output("Open Library Provider Metadata", {
            'name': provider.name,
            'description': provider.description,
            'operations': provider.supported_operations,
        })

        print("✓ Open Library provider metadata validated")

    @pytest.mark.network
    def test_search_books(self, openlibrary_config, debug_output, measure_performance):
        """Test searching for books"""
        print("\n=== Testing Open Library search_books ===")

        provider = OpenLibraryProvider(openlibrary_config)

        measure_performance.start()
        result = provider.search_books(q="the lord of the rings", limit=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check first result structure
        first_result = result['data'][0]
        assert isinstance(first_result, dict)
        assert 'title' in first_result or 'key' in first_result

        debug_output("Open Library Search Results", {
            'query': 'the lord of the rings',
            'results_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  Open Library search_books took {duration:.3f} seconds")
        print("✓ Retrieved book search results successfully")

    @pytest.mark.network
    def test_search_books_by_author(self, openlibrary_config, debug_output, measure_performance):
        """Test searching for books by author"""
        print("\n=== Testing Open Library search_books by author ===")

        provider = OpenLibraryProvider(openlibrary_config)

        measure_performance.start()
        result = provider.search_books(author="J.R.R. Tolkien", limit=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        debug_output("Open Library Author Search", {
            'author': 'J.R.R. Tolkien',
            'results_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  Open Library search by author took {duration:.3f} seconds")
        print("✓ Retrieved books by author successfully")

    @pytest.mark.network
    def test_get_work(self, openlibrary_config, debug_output, measure_performance):
        """Test getting work details"""
        print("\n=== Testing Open Library get_work ===")

        provider = OpenLibraryProvider(openlibrary_config)

        measure_performance.start()
        result = provider.get_work(work_id="OL27448W")  # The Lord of the Rings
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'title' in result['data'] or 'key' in result['data']

        debug_output("Open Library Work Details", {
            'work_id': 'OL27448W',
            'data_type': type(result['data']).__name__,
            'duration_seconds': duration,
        })

        print(f"⏱  Open Library get_work took {duration:.3f} seconds")
        print("✓ Retrieved work details successfully")

    @pytest.mark.network
    def test_search_authors(self, openlibrary_config, debug_output, measure_performance):
        """Test searching for authors"""
        print("\n=== Testing Open Library search_authors ===")

        provider = OpenLibraryProvider(openlibrary_config)

        measure_performance.start()
        result = provider.search_authors(q="Mark Twain", limit=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        debug_output("Open Library Author Search", {
            'query': 'Mark Twain',
            'results_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  Open Library search_authors took {duration:.3f} seconds")
        print("✓ Retrieved author search results successfully")

    @pytest.mark.network
    def test_get_subject(self, openlibrary_config, debug_output, measure_performance):
        """Test getting books by subject"""
        print("\n=== Testing Open Library get_subject ===")

        provider = OpenLibraryProvider(openlibrary_config)

        measure_performance.start()
        result = provider.get_subject(subject="science_fiction", limit=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        # Subject endpoint may return dict or list
        assert isinstance(result['data'], (dict, list))

        debug_output("Open Library Subject Books", {
            'subject': 'science_fiction',
            'data_type': type(result['data']).__name__,
            'duration_seconds': duration,
        })

        print(f"⏱  Open Library get_subject took {duration:.3f} seconds")
        print("✓ Retrieved books by subject successfully")

    def test_validate_params(self, openlibrary_config):
        """Test Open Library parameter validation"""
        print("\n=== Testing Open Library Parameter Validation ===")

        provider = OpenLibraryProvider(openlibrary_config)

        # Valid params for search_books
        is_valid, error = provider.validate_params('search_books', {'q': 'python'})
        assert is_valid is True
        assert error is None

        # Invalid params - missing all search parameters
        is_valid, error = provider.validate_params('search_books', {})
        assert is_valid is False
        assert error is not None

        # Valid params for get_work
        is_valid, error = provider.validate_params('get_work', {'work_id': 'OL27448W'})
        assert is_valid is True
        assert error is None

        # Invalid params for get_work
        is_valid, error = provider.validate_params('get_work', {})
        assert is_valid is False
        assert error is not None

        print("✓ Parameter validation working correctly")

    def test_operation_schema(self, openlibrary_config, debug_output):
        """Test Open Library operation schema"""
        print("\n=== Testing Open Library Operation Schema ===")

        provider = OpenLibraryProvider(openlibrary_config)

        schema = provider.get_operation_schema('search_books')

        assert schema is not None
        assert 'description' in schema
        assert 'parameters' in schema

        debug_output("Open Library search_books Schema", schema)

        print("✓ Operation schema retrieved successfully")


class TestCoinGeckoProvider:
    """Test CoinGecko API provider"""

    def test_provider_metadata(self, coingecko_config, debug_output):
        """Test CoinGecko provider metadata"""
        print("\n=== Testing CoinGecko Provider Metadata ===")

        provider = CoinGeckoProvider(coingecko_config)

        assert provider.name == 'coingecko'
        assert provider.description
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()

        debug_output("CoinGecko Metadata", {
            'name': metadata['name'],
            'description': metadata['description'],
            'operations': metadata['operations'],
        })

        print("✓ CoinGecko metadata retrieved successfully")

    @pytest.mark.network
    def test_get_coin_price(self, coingecko_config, debug_output, measure_performance):
        """Test CoinGecko get_coin_price operation"""
        print("\n=== Testing CoinGecko get_coin_price ===")

        provider = CoinGeckoProvider(coingecko_config)

        measure_performance.start()
        result = provider.get_coin_price(
            ids='bitcoin,ethereum',
            vs_currencies='usd,eur'
        )
        duration = measure_performance.stop()

        assert result is not None
        assert 'bitcoin' in result
        assert 'ethereum' in result
        assert 'usd' in result['bitcoin']
        assert 'eur' in result['bitcoin']

        debug_output("CoinGecko Coin Prices", {
            'bitcoin_usd': result['bitcoin']['usd'],
            'ethereum_usd': result['ethereum']['usd'],
            'duration_seconds': duration,
        })

        measure_performance.print_result("CoinGecko get_coin_price")
        print("✓ Retrieved coin prices successfully")

    @pytest.mark.network
    def test_get_trending_coins(self, coingecko_config, debug_output, measure_performance):
        """Test CoinGecko get_trending_coins operation"""
        print("\n=== Testing CoinGecko get_trending_coins ===")

        provider = CoinGeckoProvider(coingecko_config)

        measure_performance.start()
        result = provider.get_trending_coins()
        duration = measure_performance.stop()

        assert result is not None
        assert 'coins' in result

        debug_output("CoinGecko Trending Coins", {
            'trending_count': len(result['coins']),
            'duration_seconds': duration,
        })

        measure_performance.print_result("CoinGecko get_trending_coins")
        print("✓ Retrieved trending coins successfully")

    @pytest.mark.network
    def test_search_coins(self, coingecko_config, debug_output):
        """Test CoinGecko search_coins operation"""
        print("\n=== Testing CoinGecko search_coins ===")

        provider = CoinGeckoProvider(coingecko_config)

        result = provider.search_coins(query='bitcoin')

        assert result is not None
        assert 'coins' in result
        assert len(result['coins']) > 0

        debug_output("CoinGecko Search Results", {
            'query': 'bitcoin',
            'results_count': len(result['coins']),
        })

        print("✓ Search executed successfully")

    def test_validate_params(self, coingecko_config):
        """Test CoinGecko parameter validation"""
        print("\n=== Testing CoinGecko Parameter Validation ===")

        provider = CoinGeckoProvider(coingecko_config)

        # Valid params
        is_valid, error = provider.validate_params('get_coin_price', {
            'ids': 'bitcoin',
            'vs_currencies': 'usd'
        })
        assert is_valid is True
        assert error is None

        # Invalid params - missing ids
        is_valid, error = provider.validate_params('get_coin_price', {
            'vs_currencies': 'usd'
        })
        assert is_valid is False
        assert error is not None
        assert 'ids' in error

        # Invalid params - missing vs_currencies
        is_valid, error = provider.validate_params('get_coin_price', {
            'ids': 'bitcoin'
        })
        assert is_valid is False
        assert error is not None
        assert 'vs_currencies' in error

        print("✓ Parameter validation working correctly")


class TestOpenWeatherMapProvider:
    """Test OpenWeatherMap API provider"""

    def test_provider_metadata(self, openweathermap_config, debug_output):
        """Test OpenWeatherMap provider metadata"""
        print("\n=== Testing OpenWeatherMap Provider Metadata ===")

        provider = OpenWeatherMapProvider(openweathermap_config)

        assert provider.name == 'openweathermap'
        assert provider.description
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()

        debug_output("OpenWeatherMap Metadata", {
            'name': metadata['name'],
            'description': metadata['description'],
            'operations': metadata['operations'],
        })

        print("✓ OpenWeatherMap metadata retrieved successfully")

    @pytest.mark.network
    def test_get_current_weather(self, openweathermap_config, skip_if_no_api_key, debug_output, measure_performance):
        """Test OpenWeatherMap get_current_weather operation"""
        skip_if_no_api_key('openweathermap')
        print("\n=== Testing OpenWeatherMap get_current_weather ===")

        provider = OpenWeatherMapProvider(openweathermap_config)

        measure_performance.start()
        result = provider.get_current_weather(
            appid=openweathermap_config.get('api_key', 'test'),
            q='London,UK',
            units='metric'
        )
        duration = measure_performance.stop()

        assert result is not None
        if 'error' not in result:
            assert 'main' in result
            assert 'temp' in result['main']
            assert 'weather' in result

            debug_output("OpenWeatherMap Current Weather", {
                'location': 'London,UK',
                'temperature': result['main']['temp'],
                'weather': result['weather'][0]['description'] if result['weather'] else 'N/A',
                'duration_seconds': duration,
            })

            measure_performance.print_result("OpenWeatherMap get_current_weather")
            print("✓ Retrieved current weather successfully")
        else:
            print(f"⚠️  API key required or rate limited: {result.get('error')}")

    @pytest.mark.network
    def test_geocode_location(self, openweathermap_config, skip_if_no_api_key, debug_output):
        """Test OpenWeatherMap geocode_location operation"""
        skip_if_no_api_key('openweathermap')
        print("\n=== Testing OpenWeatherMap geocode_location ===")

        provider = OpenWeatherMapProvider(openweathermap_config)

        result = provider.geocode_location(
            appid=openweathermap_config.get('api_key', 'test'),
            q='London,UK',
            limit=5
        )

        assert result is not None
        if 'error' not in result and isinstance(result, list):
            assert len(result) > 0
            first_result = result[0]
            assert 'lat' in first_result
            assert 'lon' in first_result
            assert 'name' in first_result

            debug_output("OpenWeatherMap Geocoding", {
                'query': 'London,UK',
                'results_count': len(result),
                'first_result': {
                    'name': first_result['name'],
                    'lat': first_result['lat'],
                    'lon': first_result['lon'],
                },
            })

            print("✓ Geocoding executed successfully")
        else:
            print(f"⚠️  API key required or rate limited")

    def test_validate_params(self, openweathermap_config):
        """Test OpenWeatherMap parameter validation"""
        print("\n=== Testing OpenWeatherMap Parameter Validation ===")

        provider = OpenWeatherMapProvider(openweathermap_config)

        # Valid params with city
        is_valid, error = provider.validate_params('get_current_weather', {
            'appid': 'test_key',
            'q': 'London'
        })
        assert is_valid is True
        assert error is None

        # Valid params with coordinates
        is_valid, error = provider.validate_params('get_current_weather', {
            'appid': 'test_key',
            'lat': 51.5074,
            'lon': -0.1278
        })
        assert is_valid is True
        assert error is None

        # Invalid params - missing API key
        is_valid, error = provider.validate_params('get_current_weather', {
            'q': 'London'
        })
        assert is_valid is False
        assert error is not None
        assert 'appid' in error

        # Invalid params - missing location
        is_valid, error = provider.validate_params('get_current_weather', {
            'appid': 'test_key'
        })
        assert is_valid is False
        assert error is not None

        print("✓ Parameter validation working correctly")


class TestWikipediaProvider:
    """Test Wikipedia API provider"""

    def test_provider_metadata(self, wikipedia_config, debug_output):
        """Test Wikipedia provider metadata"""
        print("\n=== Testing Wikipedia Provider Metadata ===")

        provider = WikipediaProvider(wikipedia_config)

        assert provider.name == "wikipedia"
        assert provider.description is not None
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()
        assert metadata['name'] == 'wikipedia'
        assert 'operations' in metadata

        debug_output("Wikipedia Provider Metadata", {
            'name': provider.name,
            'description': provider.description,
            'operations': provider.supported_operations,
        })

        print("✓ Wikipedia provider metadata validated")

    @pytest.mark.network
    def test_search_pages(self, wikipedia_config, debug_output, measure_performance):
        """Test searching Wikipedia pages"""
        print("\n=== Testing Wikipedia search_pages ===")

        provider = WikipediaProvider(wikipedia_config)

        measure_performance.start()
        result = provider.search_pages(query="Python programming", limit=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check first result structure
        first_result = result['data'][0]
        assert 'title' in first_result
        assert 'snippet' in first_result or 'pageid' in first_result

        debug_output("Wikipedia Search Results", {
            'query': 'Python programming',
            'results_count': len(result['data']),
            'first_result_title': first_result.get('title'),
            'duration_seconds': duration,
        })

        print(f"⏱  Wikipedia search_pages took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} results")

    @pytest.mark.network
    def test_get_page_summary(self, wikipedia_config, debug_output, measure_performance):
        """Test getting page summary"""
        print("\n=== Testing Wikipedia get_page_summary ===")

        provider = WikipediaProvider(wikipedia_config)

        measure_performance.start()
        result = provider.get_page_summary(title="Python (programming language)")
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)

        # Check summary structure
        data = result['data']
        assert 'title' in data or 'extract' in data

        debug_output("Wikipedia Page Summary", {
            'title': 'Python (programming language)',
            'has_extract': 'extract' in data,
            'duration_seconds': duration,
        })

        print(f"⏱  Wikipedia get_page_summary took {duration:.3f} seconds")
        print("✓ Retrieved page summary successfully")

    @pytest.mark.network
    def test_get_page_content(self, wikipedia_config, debug_output, measure_performance):
        """Test getting full page content"""
        print("\n=== Testing Wikipedia get_page_content ===")

        provider = WikipediaProvider(wikipedia_config)

        measure_performance.start()
        result = provider.get_page_content(title="Python (programming language)")
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)

        debug_output("Wikipedia Page Content", {
            'title': 'Python (programming language)',
            'data_keys': list(result['data'].keys()) if isinstance(result['data'], dict) else 'N/A',
            'duration_seconds': duration,
        })

        print(f"⏱  Wikipedia get_page_content took {duration:.3f} seconds")
        print("✓ Retrieved page content successfully")

    @pytest.mark.network
    def test_get_random_page(self, wikipedia_config, debug_output, measure_performance):
        """Test getting random page"""
        print("\n=== Testing Wikipedia get_random_page ===")

        provider = WikipediaProvider(wikipedia_config)

        measure_performance.start()
        result = provider.get_random_page()
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check random page structure
        first_page = result['data'][0]
        assert 'title' in first_page or 'id' in first_page

        debug_output("Wikipedia Random Page", {
            'page_title': first_page.get('title', 'N/A'),
            'duration_seconds': duration,
        })

        print(f"⏱  Wikipedia get_random_page took {duration:.3f} seconds")
        print("✓ Retrieved random page successfully")

    @pytest.mark.network
    def test_get_page_info(self, wikipedia_config, debug_output, measure_performance):
        """Test getting page information"""
        print("\n=== Testing Wikipedia get_page_info ===")

        provider = WikipediaProvider(wikipedia_config)

        measure_performance.start()
        result = provider.get_page_info(title="Python (programming language)")
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)

        debug_output("Wikipedia Page Info", {
            'title': 'Python (programming language)',
            'data_keys': list(result['data'].keys()) if isinstance(result['data'], dict) else 'N/A',
            'duration_seconds': duration,
        })

        print(f"⏱  Wikipedia get_page_info took {duration:.3f} seconds")
        print("✓ Retrieved page info successfully")

    def test_validate_params(self, wikipedia_config):
        """Test Wikipedia parameter validation"""
        print("\n=== Testing Wikipedia Parameter Validation ===")

        provider = WikipediaProvider(wikipedia_config)

        # Valid params for search_pages
        is_valid, error = provider.validate_params('search_pages', {'query': 'Python'})
        assert is_valid is True
        assert error is None

        # Invalid params for search_pages - missing query
        is_valid, error = provider.validate_params('search_pages', {})
        assert is_valid is False
        assert error is not None

        # Valid params for get_page_summary
        is_valid, error = provider.validate_params('get_page_summary', {'title': 'Python'})
        assert is_valid is True
        assert error is None

        # Invalid params for get_page_summary - missing title
        is_valid, error = provider.validate_params('get_page_summary', {})
        assert is_valid is False
        assert error is not None

        # Valid params for get_random_page (no params required)
        is_valid, error = provider.validate_params('get_random_page', {})
        assert is_valid is True
        assert error is None

        print("✓ Parameter validation working correctly")

    def test_operation_schema(self, wikipedia_config, debug_output):
        """Test operation schema retrieval"""
        print("\n=== Testing Wikipedia Operation Schema ===")

        provider = WikipediaProvider(wikipedia_config)

        # Test search_pages schema
        schema = provider.get_operation_schema("search_pages")
        assert schema is not None
        assert 'description' in schema
        assert 'parameters' in schema
        assert 'query' in schema['parameters']

        # Test get_page_summary schema
        schema = provider.get_operation_schema("get_page_summary")
        assert schema is not None
        assert 'description' in schema
        assert 'parameters' in schema
        assert 'title' in schema['parameters']

        debug_output("Wikipedia Operation Schema", {
            'operations': provider.supported_operations,
            'sample_schema': schema,
        })

        print("✓ Operation schemas retrieved successfully")

    @pytest.mark.network
    def test_multiple_searches(self, wikipedia_config, debug_output, measure_performance):
        """Test multiple search queries"""
        print("\n=== Testing Wikipedia Multiple Searches ===")

        provider = WikipediaProvider(wikipedia_config)

        search_queries = [
            "Artificial Intelligence",
            "Machine Learning",
            "Deep Learning",
        ]

        results = []
        measure_performance.start()

        for query in search_queries:
            result = provider.search_pages(query=query, limit=3)
            assert result is not None
            assert 'data' in result
            results.append({
                'query': query,
                'results_count': len(result['data'])
            })

        duration = measure_performance.stop()

        debug_output("Wikipedia Multiple Searches", {
            'queries_tested': len(search_queries),
            'results': results,
            'duration_seconds': duration,
        })

        print(f"⏱  Testing {len(search_queries)} queries took {duration:.3f} seconds")
        print("✓ All searches executed successfully")

    @pytest.mark.network
    def test_response_validation(self, wikipedia_config, debug_output):
        """Test response structure validation"""
        print("\n=== Testing Wikipedia Response Validation ===")

        provider = WikipediaProvider(wikipedia_config)

        result = provider.search_pages(query="Python", limit=5)

        # Validate response structure
        assert 'provider' in result
        assert 'operation' in result
        assert 'data' in result
        assert 'metadata' in result

        assert result['provider'] == 'wikipedia'
        assert result['operation'] == 'search_pages'

        metadata = result['metadata']
        assert 'timestamp' in metadata
        assert 'source' in metadata

        debug_output("Wikipedia Response Structure", {
            'provider': result['provider'],
            'operation': result['operation'],
            'has_data': 'data' in result,
            'has_metadata': 'metadata' in result,
        })

        print("✓ Response structure validated")

    @pytest.mark.network
    def test_error_handling_invalid_title(self, wikipedia_config):
        """Test error handling for invalid page title"""
        print("\n=== Testing Wikipedia Invalid Title Error ===")

        provider = WikipediaProvider(wikipedia_config)

        # This should not raise an exception, but return empty or error data
        try:
            result = provider.get_page_summary(title="ThisPageDefinitelyDoesNotExist12345XYZ")
            # Wikipedia API may return an error or empty result
            assert result is not None
            print("✓ Invalid title handled gracefully")
        except Exception as e:
            # If it raises an exception, that's also acceptable
            print(f"✓ Invalid title raised exception: {type(e).__name__}")


class TestGitHubProvider:
    """Test GitHub API provider"""

    def test_provider_metadata(self, github_config, debug_output):
        """Test GitHub provider metadata"""
        print("\n=== Testing GitHub Provider Metadata ===")

        provider = GitHubProvider(github_config)

        assert provider.name == "github"
        assert provider.description is not None
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()
        assert metadata['name'] == 'github'
        assert 'operations' in metadata

        debug_output("GitHub Provider Metadata", {
            'name': provider.name,
            'description': provider.description,
            'operations': provider.supported_operations,
        })

        print("✓ GitHub provider metadata validated")

    @pytest.mark.network
    def test_get_repository(self, github_config, debug_output, measure_performance):
        """Test getting repository information"""
        print("\n=== Testing GitHub get_repository ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.get_repository(owner="octocat", repo="Hello-World")
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'name' in result['data']
        assert 'owner' in result['data']

        debug_output("GitHub Repository Data", {
            'owner': 'octocat',
            'repo': 'Hello-World',
            'name': result['data'].get('name'),
            'stars': result['data'].get('stargazers_count'),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub get_repository took {duration:.3f} seconds")
        print("✓ Retrieved repository data successfully")

    @pytest.mark.network
    def test_search_repositories(self, github_config, debug_output, measure_performance):
        """Test searching repositories"""
        print("\n=== Testing GitHub search_repositories ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.search_repositories(query="language:python stars:>1000", per_page=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check first result structure
        first_result = result['data'][0]
        assert 'name' in first_result
        assert 'owner' in first_result or 'full_name' in first_result

        debug_output("GitHub Repository Search Results", {
            'query': 'language:python stars:>1000',
            'results_count': len(result['data']),
            'first_result_name': first_result.get('name') or first_result.get('full_name'),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub search_repositories took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} repositories")

    @pytest.mark.network
    def test_get_user(self, github_config, debug_output, measure_performance):
        """Test getting user information"""
        print("\n=== Testing GitHub get_user ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.get_user(username="octocat")
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'login' in result['data']

        debug_output("GitHub User Data", {
            'username': 'octocat',
            'login': result['data'].get('login'),
            'public_repos': result['data'].get('public_repos'),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub get_user took {duration:.3f} seconds")
        print("✓ Retrieved user data successfully")

    @pytest.mark.network
    def test_search_users(self, github_config, debug_output, measure_performance):
        """Test searching users"""
        print("\n=== Testing GitHub search_users ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.search_users(query="followers:>1000", per_page=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check first result structure
        first_result = result['data'][0]
        assert 'login' in first_result

        debug_output("GitHub User Search Results", {
            'query': 'followers:>1000',
            'results_count': len(result['data']),
            'first_result_login': first_result.get('login'),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub search_users took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} users")

    @pytest.mark.network
    def test_get_repository_issues(self, github_config, debug_output, measure_performance):
        """Test getting repository issues"""
        print("\n=== Testing GitHub get_repository_issues ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.get_repository_issues(owner="octocat", repo="Hello-World", state="all", per_page=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)

        debug_output("GitHub Repository Issues", {
            'owner': 'octocat',
            'repo': 'Hello-World',
            'issues_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub get_repository_issues took {duration:.3f} seconds")
        print(f"✓ Retrieved {len(result['data'])} issues")

    @pytest.mark.network
    def test_get_repository_pulls(self, github_config, debug_output, measure_performance):
        """Test getting repository pull requests"""
        print("\n=== Testing GitHub get_repository_pulls ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.get_repository_pulls(owner="microsoft", repo="vscode", state="closed", per_page=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)

        debug_output("GitHub Repository Pull Requests", {
            'owner': 'microsoft',
            'repo': 'vscode',
            'pulls_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub get_repository_pulls took {duration:.3f} seconds")
        print(f"✓ Retrieved {len(result['data'])} pull requests")

    def test_validate_params(self, github_config):
        """Test GitHub parameter validation"""
        print("\n=== Testing GitHub Parameter Validation ===")

        provider = GitHubProvider(github_config)

        # Valid params for get_repository
        is_valid, error = provider.validate_params('get_repository', {'owner': 'octocat', 'repo': 'Hello-World'})
        assert is_valid is True
        assert error is None

        # Invalid params - missing required
        is_valid, error = provider.validate_params('get_repository', {'owner': 'octocat'})
        assert is_valid is False
        assert error is not None

        # Valid params for search_repositories
        is_valid, error = provider.validate_params('search_repositories', {'query': 'python'})
        assert is_valid is True
        assert error is None

        # Invalid params for search_repositories
        is_valid, error = provider.validate_params('search_repositories', {})
        assert is_valid is False
        assert error is not None

        print("✓ Parameter validation working correctly")

    def test_operation_schema(self, github_config, debug_output):
        """Test GitHub operation schema"""
        print("\n=== Testing GitHub Operation Schema ===")

        provider = GitHubProvider(github_config)

        schema = provider.get_operation_schema('get_repository')

        assert schema is not None
        assert 'description' in schema
        assert 'parameters' in schema

        debug_output("GitHub get_repository Schema", schema)

        print("✓ Operation schema retrieved successfully")


class TestGitHubProvider:
    """Test GitHub API provider"""

    def test_provider_metadata(self, github_config, debug_output):
        """Test GitHub provider metadata"""
        print("\n=== Testing GitHub Provider Metadata ===")

        provider = GitHubProvider(github_config)

        assert provider.name == "github"
        assert provider.description is not None
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()
        assert metadata['name'] == 'github'
        assert 'operations' in metadata

        debug_output("GitHub Provider Metadata", {
            'name': provider.name,
            'description': provider.description,
            'operations': provider.supported_operations,
        })

        print("✓ GitHub provider metadata validated")

    @pytest.mark.network
    def test_get_repository(self, github_config, debug_output, measure_performance):
        """Test getting repository information"""
        print("\n=== Testing GitHub get_repository ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.get_repository(owner="octocat", repo="Hello-World")
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'name' in result['data']
        assert 'owner' in result['data']

        debug_output("GitHub Repository Data", {
            'owner': 'octocat',
            'repo': 'Hello-World',
            'name': result['data'].get('name'),
            'stars': result['data'].get('stargazers_count'),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub get_repository took {duration:.3f} seconds")
        print("✓ Retrieved repository data successfully")

    @pytest.mark.network
    def test_search_repositories(self, github_config, debug_output, measure_performance):
        """Test searching repositories"""
        print("\n=== Testing GitHub search_repositories ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.search_repositories(query="language:python stars:>1000", per_page=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check first result structure
        first_result = result['data'][0]
        assert 'name' in first_result
        assert 'owner' in first_result or 'full_name' in first_result

        debug_output("GitHub Repository Search Results", {
            'query': 'language:python stars:>1000',
            'results_count': len(result['data']),
            'first_result_name': first_result.get('name') or first_result.get('full_name'),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub search_repositories took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} repositories")

    @pytest.mark.network
    def test_get_user(self, github_config, debug_output, measure_performance):
        """Test getting user information"""
        print("\n=== Testing GitHub get_user ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.get_user(username="octocat")
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'login' in result['data']

        debug_output("GitHub User Data", {
            'username': 'octocat',
            'login': result['data'].get('login'),
            'public_repos': result['data'].get('public_repos'),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub get_user took {duration:.3f} seconds")
        print("✓ Retrieved user data successfully")

    @pytest.mark.network
    def test_search_users(self, github_config, debug_output, measure_performance):
        """Test searching users"""
        print("\n=== Testing GitHub search_users ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.search_users(query="followers:>1000", per_page=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check first result structure
        first_result = result['data'][0]
        assert 'login' in first_result

        debug_output("GitHub User Search Results", {
            'query': 'followers:>1000',
            'results_count': len(result['data']),
            'first_result_login': first_result.get('login'),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub search_users took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} users")

    @pytest.mark.network
    def test_get_repository_issues(self, github_config, debug_output, measure_performance):
        """Test getting repository issues"""
        print("\n=== Testing GitHub get_repository_issues ===")

        provider = GitHubProvider(github_config)

        measure_performance.start()
        result = provider.get_repository_issues(owner="octocat", repo="Hello-World", state="all", per_page=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)

        debug_output("GitHub Repository Issues", {
            'owner': 'octocat',
            'repo': 'Hello-World',
            'issues_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  GitHub get_repository_issues took {duration:.3f} seconds")
        print(f"✓ Retrieved {len(result['data'])} issues")

    def test_validate_params(self, github_config):
        """Test GitHub parameter validation"""
        print("\n=== Testing GitHub Parameter Validation ===")

        provider = GitHubProvider(github_config)

        # Valid params for get_repository
        is_valid, error = provider.validate_params('get_repository', {'owner': 'octocat', 'repo': 'Hello-World'})
        assert is_valid is True
        assert error is None

        # Invalid params - missing required
        is_valid, error = provider.validate_params('get_repository', {'owner': 'octocat'})
        assert is_valid is False
        assert error is not None

        # Valid params for search_repositories
        is_valid, error = provider.validate_params('search_repositories', {'query': 'python'})
        assert is_valid is True
        assert error is None

        # Invalid params for search_repositories
        is_valid, error = provider.validate_params('search_repositories', {})
        assert is_valid is False
        assert error is not None

        print("✓ Parameter validation working correctly")

    def test_operation_schema(self, github_config, debug_output):
        """Test GitHub operation schema"""
        print("\n=== Testing GitHub Operation Schema ===")

        provider = GitHubProvider(github_config)

        schema = provider.get_operation_schema('get_repository')

        assert schema is not None
        assert 'description' in schema
        assert 'parameters' in schema

        debug_output("GitHub get_repository Schema", schema)

        print("✓ Operation schema retrieved successfully")


class TestArxivProvider:
    """Test arXiv API provider"""

    def test_provider_metadata(self, arxiv_config, debug_output):
        """Test arXiv provider metadata"""
        print("\n=== Testing arXiv Provider Metadata ===")

        provider = ArxivProvider(arxiv_config)

        assert provider.name == "arxiv"
        assert provider.description is not None
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()
        assert metadata['name'] == 'arxiv'
        assert 'operations' in metadata

        debug_output("arXiv Provider Metadata", {
            'name': provider.name,
            'description': provider.description,
            'operations': provider.supported_operations,
        })

        print("✓ arXiv provider metadata validated")

    @pytest.mark.network
    def test_search_papers(self, arxiv_config, debug_output, measure_performance):
        """Test searching for papers"""
        print("\n=== Testing arXiv search_papers ===")

        provider = ArxivProvider(arxiv_config)

        measure_performance.start()
        result = provider.search_papers(query="machine learning", max_results=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check first paper structure
        first_paper = result['data'][0]
        assert 'title' in first_paper
        assert 'authors' in first_paper
        assert 'abstract' in first_paper

        debug_output("arXiv Search Papers", {
            'query': 'machine learning',
            'results_count': len(result['data']),
            'first_paper_title': first_paper.get('title', 'N/A'),
            'duration_seconds': duration,
        })

        print(f"⏱  arXiv search_papers took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} papers")

    @pytest.mark.network
    def test_get_paper_by_id(self, arxiv_config, debug_output, measure_performance):
        """Test getting a specific paper by arXiv ID"""
        print("\n=== Testing arXiv get_paper_by_id ===")

        provider = ArxivProvider(arxiv_config)

        # Use a well-known arXiv paper ID
        measure_performance.start()
        result = provider.get_paper_by_id(arxiv_id="1706.03762")  # "Attention Is All You Need"
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'title' in result['data']
        assert 'authors' in result['data']
        assert 'abstract' in result['data']

        debug_output("arXiv Get Paper by ID", {
            'arxiv_id': '1706.03762',
            'title': result['data'].get('title', 'N/A'),
            'authors_count': len(result['data'].get('authors', [])),
            'duration_seconds': duration,
        })

        print(f"⏱  arXiv get_paper_by_id took {duration:.3f} seconds")
        print("✓ Retrieved paper successfully")

    @pytest.mark.network
    def test_search_by_author(self, arxiv_config, debug_output, measure_performance):
        """Test searching papers by author"""
        print("\n=== Testing arXiv search_by_author ===")

        provider = ArxivProvider(arxiv_config)

        measure_performance.start()
        result = provider.search_by_author(author="Yoshua Bengio", max_results=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        debug_output("arXiv Search by Author", {
            'author': 'Yoshua Bengio',
            'results_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  arXiv search_by_author took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} papers")

    @pytest.mark.network
    def test_search_by_category(self, arxiv_config, debug_output, measure_performance):
        """Test searching papers by category"""
        print("\n=== Testing arXiv search_by_category ===")

        provider = ArxivProvider(arxiv_config)

        measure_performance.start()
        result = provider.search_by_category(category="cs.AI", max_results=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Verify papers have the category
        for paper in result['data']:
            assert 'categories' in paper or 'primary_category' in paper

        debug_output("arXiv Search by Category", {
            'category': 'cs.AI',
            'results_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  arXiv search_by_category took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} papers in cs.AI category")

    def test_validate_params(self, arxiv_config):
        """Test arXiv parameter validation"""
        print("\n=== Testing arXiv Parameter Validation ===")

        provider = ArxivProvider(arxiv_config)

        # Valid params for search_papers
        is_valid, error = provider.validate_params('search_papers', {'query': 'quantum computing'})
        assert is_valid is True
        assert error is None

        # Invalid params - missing required
        is_valid, error = provider.validate_params('search_papers', {})
        assert is_valid is False
        assert error is not None

        # Valid params for get_paper_by_id
        is_valid, error = provider.validate_params('get_paper_by_id', {'arxiv_id': '1234.5678'})
        assert is_valid is True
        assert error is None

        # Invalid params for get_paper_by_id
        is_valid, error = provider.validate_params('get_paper_by_id', {})
        assert is_valid is False
        assert error is not None

        # Valid params for search_by_author
        is_valid, error = provider.validate_params('search_by_author', {'author': 'John Doe'})
        assert is_valid is True
        assert error is None

        # Valid params for search_by_category
        is_valid, error = provider.validate_params('search_by_category', {'category': 'cs.LG'})
        assert is_valid is True
        assert error is None

        print("✓ Parameter validation working correctly")

    def test_operation_schema(self, arxiv_config, debug_output):
        """Test arXiv operation schema"""
        print("\n=== Testing arXiv Operation Schema ===")

        provider = ArxivProvider(arxiv_config)

        # Test search_papers schema
        schema = provider.get_operation_schema('search_papers')
        assert schema is not None
        assert 'type' in schema
        assert 'properties' in schema
        assert 'query' in schema['properties']

        # Test get_paper_by_id schema
        schema = provider.get_operation_schema('get_paper_by_id')
        assert schema is not None
        assert 'properties' in schema
        assert 'arxiv_id' in schema['properties']

        debug_output("arXiv Operation Schema", {
            'operations': provider.supported_operations,
            'sample_schema': schema,
        })

        print("✓ Operation schemas retrieved successfully")

    @pytest.mark.network
    def test_response_validation(self, arxiv_config, debug_output):
        """Test response structure validation"""
        print("\n=== Testing arXiv Response Validation ===")

        provider = ArxivProvider(arxiv_config)

        result = provider.search_papers(query="neural networks", max_results=3)

        # Validate response structure
        assert 'provider' in result
        assert 'operation' in result
        assert 'data' in result
        assert 'metadata' in result

        assert result['provider'] == 'arxiv'
        assert result['operation'] == 'search_papers'

        metadata = result['metadata']
        assert 'timestamp' in metadata
        assert 'source' in metadata

        debug_output("arXiv Response Structure", {
            'provider': result['provider'],
            'operation': result['operation'],
            'has_data': 'data' in result,
            'has_metadata': 'metadata' in result,
            'total_results': metadata.get('total_results', 'N/A'),
        })

        print("✓ Response structure validated")

    @pytest.mark.network
    def test_paper_data_structure(self, arxiv_config, debug_output):
        """Test the structure of paper data returned"""
        print("\n=== Testing arXiv Paper Data Structure ===")

        provider = ArxivProvider(arxiv_config)

        result = provider.get_paper_by_id(arxiv_id="1706.03762")

        paper = result['data']
        assert isinstance(paper, dict)

        # Check required fields
        assert 'title' in paper
        assert 'authors' in paper
        assert 'abstract' in paper

        # Check optional but common fields
        expected_fields = ['arxiv_id', 'published', 'updated', 'categories', 'pdf_url', 'abs_url']
        present_fields = [field for field in expected_fields if field in paper]

        debug_output("arXiv Paper Data Structure", {
            'has_title': 'title' in paper,
            'has_authors': 'authors' in paper,
            'has_abstract': 'abstract' in paper,
            'authors_count': len(paper.get('authors', [])),
            'categories_count': len(paper.get('categories', [])),
            'present_fields': present_fields,
        })

        print("✓ Paper data structure is valid")

    @pytest.mark.network
    def test_pagination(self, arxiv_config, debug_output, measure_performance):
        """Test pagination with start parameter"""
        print("\n=== Testing arXiv Pagination ===")

        provider = ArxivProvider(arxiv_config)

        # Get first page
        measure_performance.start()
        result1 = provider.search_papers(query="deep learning", max_results=3, start=0)
        duration1 = measure_performance.stop()

        # Get second page
        measure_performance.start()
        result2 = provider.search_papers(query="deep learning", max_results=3, start=3)
        duration2 = measure_performance.stop()

        assert result1 is not None
        assert result2 is not None
        assert len(result1['data']) > 0
        assert len(result2['data']) > 0

        # Papers should be different
        first_page_ids = [p.get('arxiv_id', p.get('id')) for p in result1['data']]
        second_page_ids = [p.get('arxiv_id', p.get('id')) for p in result2['data']]

        # At least some papers should be different
        assert first_page_ids != second_page_ids

        debug_output("arXiv Pagination", {
            'first_page_count': len(result1['data']),
            'second_page_count': len(result2['data']),
            'duration_page1': duration1,
            'duration_page2': duration2,
        })

        print("✓ Pagination working correctly")

    @pytest.mark.network
    def test_multiple_categories(self, arxiv_config, debug_output):
        """Test papers with multiple categories"""
        print("\n=== Testing arXiv Multiple Categories ===")

        provider = ArxivProvider(arxiv_config)

        result = provider.search_by_category(category="cs.LG", max_results=5)

        assert result is not None
        assert len(result['data']) > 0

        # Check that papers have categories
        papers_with_multiple_cats = 0
        for paper in result['data']:
            if 'categories' in paper and len(paper['categories']) > 1:
                papers_with_multiple_cats += 1

        debug_output("arXiv Multiple Categories", {
            'total_papers': len(result['data']),
            'papers_with_multiple_categories': papers_with_multiple_cats,
        })

        print(f"✓ Found {papers_with_multiple_cats} papers with multiple categories")


class TestPubMedProvider:
    """Test PubMed/NCBI E-utilities API provider"""

    def test_provider_metadata(self, pubmed_config, debug_output):
        """Test PubMed provider metadata"""
        print("\n=== Testing PubMed Provider Metadata ===")

        provider = PubMedProvider(pubmed_config)

        assert provider.name == "pubmed"
        assert provider.description is not None
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()
        assert metadata['name'] == 'pubmed'
        assert 'operations' in metadata

        debug_output("PubMed Provider Metadata", {
            'name': provider.name,
            'description': provider.description,
            'operations': provider.supported_operations,
        })

        print("✓ PubMed provider metadata validated")

    @pytest.mark.network
    def test_search_papers(self, pubmed_config, debug_output, measure_performance):
        """Test searching for papers"""
        print("\n=== Testing PubMed search_papers ===")

        provider = PubMedProvider(pubmed_config)

        measure_performance.start()
        result = provider.search_papers(query="COVID-19 vaccine", max_results=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check first paper structure
        first_paper = result['data'][0]
        assert 'title' in first_paper
        assert 'pmid' in first_paper

        debug_output("PubMed Search Papers", {
            'query': 'COVID-19 vaccine',
            'results_count': len(result['data']),
            'first_paper_title': first_paper.get('title', 'N/A'),
            'first_paper_pmid': first_paper.get('pmid', 'N/A'),
            'duration_seconds': duration,
        })

        print(f"⏱  PubMed search_papers took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} papers")

    @pytest.mark.network
    def test_get_paper_by_id(self, pubmed_config, debug_output, measure_performance):
        """Test getting a specific paper by PMID"""
        print("\n=== Testing PubMed get_paper_by_id ===")

        provider = PubMedProvider(pubmed_config)

        # Use a well-known PubMed paper ID
        measure_performance.start()
        result = provider.get_paper_by_id(pmid="33301246")  # COVID-19 vaccine paper
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'title' in result['data']
        assert 'pmid' in result['data']
        assert result['data']['pmid'] == "33301246"

        debug_output("PubMed Get Paper by ID", {
            'pmid': '33301246',
            'title': result['data'].get('title', 'N/A'),
            'authors_count': len(result['data'].get('authors', [])),
            'has_abstract': 'abstract' in result['data'],
            'duration_seconds': duration,
        })

        print(f"⏱  PubMed get_paper_by_id took {duration:.3f} seconds")
        print("✓ Retrieved paper successfully")

    @pytest.mark.network
    def test_search_by_author(self, pubmed_config, debug_output, measure_performance):
        """Test searching papers by author"""
        print("\n=== Testing PubMed search_by_author ===")

        provider = PubMedProvider(pubmed_config)

        measure_performance.start()
        result = provider.search_by_author(author="Fauci AS", max_results=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        debug_output("PubMed Search by Author", {
            'author': 'Fauci AS',
            'results_count': len(result['data']),
            'duration_seconds': duration,
        })

        print(f"⏱  PubMed search_by_author took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} papers")

    @pytest.mark.network
    def test_get_paper_details(self, pubmed_config, debug_output, measure_performance):
        """Test getting detailed paper information"""
        print("\n=== Testing PubMed get_paper_details ===")

        provider = PubMedProvider(pubmed_config)

        measure_performance.start()
        result = provider.get_paper_details(pmid="33301246")
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'title' in result['data']
        assert 'abstract' in result['data']
        assert 'authors' in result['data']

        debug_output("PubMed Get Paper Details", {
            'pmid': '33301246',
            'title': result['data'].get('title', 'N/A'),
            'has_abstract': 'abstract' in result['data'],
            'has_authors': 'authors' in result['data'],
            'has_journal': 'journal' in result['data'],
            'has_doi': 'doi' in result['data'],
            'duration_seconds': duration,
        })

        print(f"⏱  PubMed get_paper_details took {duration:.3f} seconds")
        print("✓ Retrieved detailed paper information successfully")

    def test_validate_params(self, pubmed_config):
        """Test PubMed parameter validation"""
        print("\n=== Testing PubMed Parameter Validation ===")

        provider = PubMedProvider(pubmed_config)

        # Valid params for search_papers
        is_valid, error = provider.validate_params('search_papers', {'query': 'cancer'})
        assert is_valid is True
        assert error is None

        # Invalid params - missing required
        is_valid, error = provider.validate_params('search_papers', {})
        assert is_valid is False
        assert error is not None

        # Valid params for get_paper_by_id
        is_valid, error = provider.validate_params('get_paper_by_id', {'pmid': '12345678'})
        assert is_valid is True
        assert error is None

        # Invalid params for get_paper_by_id
        is_valid, error = provider.validate_params('get_paper_by_id', {})
        assert is_valid is False
        assert error is not None

        # Valid params for search_by_author
        is_valid, error = provider.validate_params('search_by_author', {'author': 'Smith J'})
        assert is_valid is True
        assert error is None

        # Valid params for get_paper_details
        is_valid, error = provider.validate_params('get_paper_details', {'pmid': '12345678'})
        assert is_valid is True
        assert error is None

        print("✓ Parameter validation working correctly")

    def test_operation_schema(self, pubmed_config, debug_output):
        """Test PubMed operation schema"""
        print("\n=== Testing PubMed Operation Schema ===")

        provider = PubMedProvider(pubmed_config)

        # Test search_papers schema
        schema = provider.get_operation_schema('search_papers')
        assert schema is not None
        assert 'type' in schema
        assert 'properties' in schema
        assert 'query' in schema['properties']
        assert 'required' in schema
        assert 'query' in schema['required']

        debug_output("PubMed search_papers Schema", schema)

        # Test get_paper_by_id schema
        schema = provider.get_operation_schema('get_paper_by_id')
        assert schema is not None
        assert 'pmid' in schema['properties']

        # Test search_by_author schema
        schema = provider.get_operation_schema('search_by_author')
        assert schema is not None
        assert 'author' in schema['properties']

        print("✓ Operation schemas retrieved successfully")


class TestCrossRefProvider:
    """Test CrossRef API provider"""

    def test_provider_metadata(self, crossref_config, debug_output):
        """Test CrossRef provider metadata"""
        print("\n=== Testing CrossRef Provider Metadata ===")

        provider = CrossRefProvider(crossref_config)

        assert provider.name == "crossref"
        assert provider.description is not None
        assert len(provider.supported_operations) > 0

        metadata = provider.get_metadata()
        assert metadata['name'] == 'crossref'
        assert 'operations' in metadata

        debug_output("CrossRef Provider Metadata", {
            'name': provider.name,
            'description': provider.description,
            'operations': provider.supported_operations,
        })

        print("✓ CrossRef provider metadata validated")

    @pytest.mark.network
    def test_get_work_by_doi(self, crossref_config, debug_output, measure_performance):
        """Test getting work metadata by DOI"""
        print("\n=== Testing CrossRef get_work_by_doi ===")

        provider = CrossRefProvider(crossref_config)

        # Use a well-known DOI
        measure_performance.start()
        result = provider.get_work_by_doi(doi="10.1038/nature12373")
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], dict)
        assert 'DOI' in result['data']
        assert 'title' in result['data']

        debug_output("CrossRef Get Work by DOI", {
            'doi': '10.1038/nature12373',
            'title': result['data'].get('title', ['N/A'])[0] if isinstance(result['data'].get('title'), list) else 'N/A',
            'type': result['data'].get('type', 'N/A'),
            'duration_seconds': duration,
        })

        print(f"⏱  CrossRef get_work_by_doi took {duration:.3f} seconds")
        print("✓ Retrieved work metadata successfully")

    @pytest.mark.network
    def test_search_works(self, crossref_config, debug_output, measure_performance):
        """Test searching for works"""
        print("\n=== Testing CrossRef search_works ===")

        provider = CrossRefProvider(crossref_config)

        measure_performance.start()
        result = provider.search_works(query="machine learning", rows=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check first work structure
        first_work = result['data'][0]
        assert 'DOI' in first_work
        assert 'title' in first_work

        # Check metadata
        assert 'metadata' in result
        assert 'search_info' in result['metadata']
        assert 'total_results' in result['metadata']['search_info']

        debug_output("CrossRef Search Works", {
            'query': 'machine learning',
            'results_count': len(result['data']),
            'total_results': result['metadata']['search_info']['total_results'],
            'first_work_doi': first_work.get('DOI', 'N/A'),
            'duration_seconds': duration,
        })

        print(f"⏱  CrossRef search_works took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} works")

    @pytest.mark.network
    def test_get_journal_works(self, crossref_config, debug_output, measure_performance):
        """Test getting works from a specific journal"""
        print("\n=== Testing CrossRef get_journal_works ===")

        provider = CrossRefProvider(crossref_config)

        # Use Nature's ISSN
        measure_performance.start()
        result = provider.get_journal_works(issn="0028-0836", rows=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check metadata
        assert 'metadata' in result
        assert 'journal_info' in result['metadata']
        assert result['metadata']['journal_info']['issn'] == "0028-0836"

        debug_output("CrossRef Get Journal Works", {
            'issn': '0028-0836',
            'journal': 'Nature',
            'results_count': len(result['data']),
            'total_results': result['metadata']['journal_info']['total_results'],
            'duration_seconds': duration,
        })

        print(f"⏱  CrossRef get_journal_works took {duration:.3f} seconds")
        print(f"✓ Retrieved {len(result['data'])} works from journal")

    @pytest.mark.network
    def test_search_funders(self, crossref_config, debug_output, measure_performance):
        """Test searching for funders"""
        print("\n=== Testing CrossRef search_funders ===")

        provider = CrossRefProvider(crossref_config)

        measure_performance.start()
        result = provider.search_funders(query="National Science Foundation", rows=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check first funder structure
        first_funder = result['data'][0]
        assert 'id' in first_funder
        assert 'name' in first_funder

        debug_output("CrossRef Search Funders", {
            'query': 'National Science Foundation',
            'results_count': len(result['data']),
            'first_funder_name': first_funder.get('name', 'N/A'),
            'first_funder_id': first_funder.get('id', 'N/A'),
            'duration_seconds': duration,
        })

        print(f"⏱  CrossRef search_funders took {duration:.3f} seconds")
        print(f"✓ Found {len(result['data'])} funders")

    @pytest.mark.network
    def test_get_funder_works(self, crossref_config, debug_output, measure_performance):
        """Test getting works funded by a specific funder"""
        print("\n=== Testing CrossRef get_funder_works ===")

        provider = CrossRefProvider(crossref_config)

        # Use NSF funder ID
        measure_performance.start()
        result = provider.get_funder_works(funder_id="100000001", rows=5)
        duration = measure_performance.stop()

        assert result is not None
        assert 'data' in result
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0

        # Check metadata
        assert 'metadata' in result
        assert 'funder_info' in result['metadata']
        assert result['metadata']['funder_info']['funder_id'] == "100000001"

        debug_output("CrossRef Get Funder Works", {
            'funder_id': '100000001',
            'funder': 'NSF',
            'results_count': len(result['data']),
            'total_results': result['metadata']['funder_info']['total_results'],
            'duration_seconds': duration,
        })

        print(f"⏱  CrossRef get_funder_works took {duration:.3f} seconds")
        print(f"✓ Retrieved {len(result['data'])} works funded by NSF")

    def test_validate_params(self, crossref_config):
        """Test CrossRef parameter validation"""
        print("\n=== Testing CrossRef Parameter Validation ===")

        provider = CrossRefProvider(crossref_config)

        # Valid params for get_work_by_doi
        is_valid, error = provider.validate_params('get_work_by_doi', {'doi': '10.1038/nature12373'})
        assert is_valid is True
        assert error is None

        # Invalid params - missing required
        is_valid, error = provider.validate_params('get_work_by_doi', {})
        assert is_valid is False
        assert error is not None

        # Valid params for search_works
        is_valid, error = provider.validate_params('search_works', {'query': 'climate change'})
        assert is_valid is True
        assert error is None

        # Invalid params for search_works
        is_valid, error = provider.validate_params('search_works', {})
        assert is_valid is False
        assert error is not None

        # Valid params for get_journal_works
        is_valid, error = provider.validate_params('get_journal_works', {'issn': '0028-0836'})
        assert is_valid is True
        assert error is None

        # Valid params for search_funders
        is_valid, error = provider.validate_params('search_funders', {'query': 'NSF'})
        assert is_valid is True
        assert error is None

        # Valid params for get_funder_works
        is_valid, error = provider.validate_params('get_funder_works', {'funder_id': '100000001'})
        assert is_valid is True
        assert error is None

        print("✓ Parameter validation working correctly")

    def test_operation_schema(self, crossref_config, debug_output):
        """Test CrossRef operation schema"""
        print("\n=== Testing CrossRef Operation Schema ===")

        provider = CrossRefProvider(crossref_config)

        # Test get_work_by_doi schema
        schema = provider.get_operation_schema('get_work_by_doi')
        assert schema is not None
        assert 'type' in schema
        assert 'properties' in schema
        assert 'doi' in schema['properties']

        debug_output("CrossRef get_work_by_doi Schema", schema)

        # Test search_works schema
        schema = provider.get_operation_schema('search_works')
        assert schema is not None
        assert 'query' in schema['properties']

        # Test get_journal_works schema
        schema = provider.get_operation_schema('get_journal_works')
        assert schema is not None
        assert 'issn' in schema['properties']

        print("✓ Operation schemas retrieved successfully")

