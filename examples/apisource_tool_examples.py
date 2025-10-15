#!/usr/bin/env python3
"""
API Source Tool Usage Examples

Demonstrates how to use the API Source Tool to query various external data sources.

Note: Some examples require API keys. Set environment variables:
  - export FRED_API_KEY="your_key"
  - export NEWSAPI_API_KEY="your_key"
  - export CENSUS_API_KEY="your_key"  (optional)
"""

# Force load the tool module first
from aiecs.tools.task_tools import apisource_tool
from aiecs.tools import get_tool

# Initialize the tool
apisource = get_tool('apisource')

print("=" * 80)
print("API Source Tool Examples")
print("=" * 80)


# Example 1: List all available providers
print("\n📋 Example 1: List Available Providers\n")
print("-" * 80)

providers = apisource.list_providers()
print(f"Found {len(providers)} data providers:\n")

for provider in providers:
    print(f"✓ {provider['name']}: {provider['description']}")
    print(f"  Operations: {', '.join(provider['operations'])}")
    print()


# Example 2: Get detailed provider information
print("\n📋 Example 2: Get Provider Details\n")
print("-" * 80)

wb_info = apisource.get_provider_info('worldbank')
print(f"Provider: {wb_info['name']}")
print(f"Description: {wb_info['description']}")
print(f"Available Operations: {', '.join(wb_info['operations'])}")
print(f"Configuration: {wb_info['config']}")


# Example 3: Query World Bank for country list (no API key needed)
print("\n\n📊 Example 3: Query World Bank - List Countries\n")
print("-" * 80)

try:
    result = apisource.query(
        provider='worldbank',
        operation='list_countries',
        params={'per_page': 5}
    )
    
    print(f"Provider: {result['provider']}")
    print(f"Operation: {result['operation']}")
    print(f"Results: {len(result['data'])} countries")
    print(f"\nFirst 3 countries:")
    for country in result['data'][:3]:
        print(f"  - {country.get('name', 'N/A')} ({country.get('id', 'N/A')})")
    
except Exception as e:
    print(f"Error: {e}")


# Example 4: Search for GDP indicators (World Bank)
print("\n\n📊 Example 4: Search World Bank Indicators\n")
print("-" * 80)

try:
    result = apisource.query(
        provider='worldbank',
        operation='search_indicators',
        params={'search_text': 'GDP', 'limit': 3}
    )
    
    print(f"Found {len(result['data'])} indicators matching 'GDP':\n")
    for indicator in result['data'][:3]:
        print(f"  {indicator.get('id')}: {indicator.get('name')}")
    
except Exception as e:
    print(f"Error: {e}")


# Example 5: Query FRED for GDP data (requires API key)
print("\n\n📈 Example 5: Query FRED - US GDP Data\n")
print("-" * 80)

try:
    result = apisource.query(
        provider='fred',
        operation='get_series',
        params={
            'series_id': 'GDP',
            'limit': 5,
            'sort_order': 'desc'
        }
    )
    
    print(f"Provider: {result['provider']}")
    print(f"Latest GDP observations:")
    for obs in result['data'][:5]:
        print(f"  {obs.get('date')}: ${obs.get('value')} billion")
    
except ValueError as e:
    print(f"⚠️  API Key Required: {e}")
    print("   Set FRED_API_KEY environment variable to use this feature")
except Exception as e:
    print(f"Error: {e}")


# Example 6: Search FRED series (requires API key)
print("\n\n🔍 Example 6: Search FRED Series\n")
print("-" * 80)

try:
    result = apisource.query(
        provider='fred',
        operation='search_series',
        params={
            'search_text': 'unemployment rate',
            'limit': 3
        }
    )
    
    print(f"Found {len(result['data'])} series:")
    for series in result['data'][:3]:
        print(f"  {series.get('id')}: {series.get('title')}")
    
except ValueError as e:
    print(f"⚠️  API Key Required: {e}")
except Exception as e:
    print(f"Error: {e}")


# Example 7: Get news headlines (requires API key)
print("\n\n📰 Example 7: Get Top News Headlines\n")
print("-" * 80)

try:
    result = apisource.query(
        provider='newsapi',
        operation='get_top_headlines',
        params={
            'country': 'us',
            'category': 'technology',
            'page_size': 3
        }
    )
    
    articles = result['data']['articles']
    print(f"Found {result['data']['total_results']} articles, showing {len(articles)}:\n")
    
    for article in articles:
        print(f"  📄 {article.get('title')}")
        print(f"     Source: {article.get('source', {}).get('name')}")
        print(f"     Published: {article.get('publishedAt')}")
        print()
    
except ValueError as e:
    print(f"⚠️  API Key Required: {e}")
    print("   Set NEWSAPI_API_KEY environment variable to use this feature")
except Exception as e:
    print(f"Error: {e}")


# Example 8: Multi-provider search
print("\n\n🔎 Example 8: Search Across Multiple Providers\n")
print("-" * 80)

try:
    results = apisource.search(
        query='economic growth',
        providers=['worldbank'],  # Only World Bank doesn't need API key
        limit=3
    )
    
    print(f"Search Results from {len(results)} providers:\n")
    
    for result in results:
        print(f"Provider: {result['provider']}")
        print(f"Results: {len(result['data'])} items")
        if result['data']:
            print(f"Sample: {result['data'][0].get('name', 'N/A')[:80]}...")
        print()
    
except Exception as e:
    print(f"Error: {e}")


# Example 9: Census Bureau - Population data (API key optional)
print("\n\n👥 Example 9: Census Bureau - List Datasets\n")
print("-" * 80)

try:
    result = apisource.query(
        provider='census',
        operation='list_datasets',
        params={}
    )
    
    print(f"Available Census datasets: {len(result['data'])} found")
    print("\nSample datasets:")
    for dataset in result['data'][:3]:
        if isinstance(dataset, dict):
            print(f"  - {dataset.get('title', 'N/A')}")
    
except Exception as e:
    print(f"Error: {e}")


print("\n" + "=" * 80)
print("✅ Examples Complete!")
print("=" * 80)
print("\n💡 Tips:")
print("  - Set API keys as environment variables for full functionality")
print("  - Use list_providers() to see all available data sources")
print("  - Use get_provider_info() to see operations for each provider")
print("  - All queries are cached with 300s TTL by default")
print("  - Rate limiting is automatic and configurable per provider")
print("=" * 80)

