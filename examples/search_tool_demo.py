"""
Search Tool Demonstration

This example demonstrates the comprehensive features of the AIECS Search Tool,
including web search, image search, news search, batch operations, and monitoring.

Setup:
1. Set GOOGLE_API_KEY and GOOGLE_CSE_ID in your .env file
2. Run: python examples/search_tool_demo.py
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiecs.tools import discover_tools, get_tool
from aiecs.tools.task_tools.search_tool import (
    RateLimitError,
    QuotaExceededError,
    AuthenticationError,
    SearchAPIError
)


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def demo_basic_web_search():
    """Demonstrate basic web search"""
    print_section("1. Basic Web Search")
    
    try:
        search_tool = get_tool('search')
        
        results = search_tool.search_web(
            query="artificial intelligence",
            num_results=5,
            language="en"
        )
        
        print(f"Found {len(results)} results for 'artificial intelligence':\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['link']}")
            print(f"   Snippet: {result['snippet'][:100]}...")
            print()
    
    except AuthenticationError as e:
        print(f"❌ Authentication Error: {e}")
        print("   Make sure GOOGLE_API_KEY and GOOGLE_CSE_ID are set in .env")
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_advanced_web_search():
    """Demonstrate advanced web search with filters"""
    print_section("2. Advanced Web Search with Filters")
    
    try:
        search_tool = get_tool('search')
        
        results = search_tool.search_web(
            query="machine learning research",
            num_results=5,
            language="en",
            country="us",
            safe_search="medium",
            date_restrict="m6",  # Last 6 months
            file_type="pdf",     # Only PDFs
        )
        
        print(f"Found {len(results)} PDF results from last 6 months:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['link']}")
            print()
    
    except QuotaExceededError as e:
        print(f"❌ Quota Exceeded: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_image_search():
    """Demonstrate image search"""
    print_section("3. Image Search")
    
    try:
        search_tool = get_tool('search')
        
        results = search_tool.search_images(
            query="sunset beach",
            num_results=5,
            image_size="large",
            image_type="photo",
            safe_search="high"
        )
        
        print(f"Found {len(results)} images:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   Image URL: {result['link']}")
            if 'image' in result:
                print(f"   Thumbnail: {result['image'].get('thumbnailLink', 'N/A')}")
                print(f"   Size: {result['image'].get('width', '?')}x{result['image'].get('height', '?')}")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_news_search():
    """Demonstrate news search"""
    print_section("4. News Search")
    
    try:
        search_tool = get_tool('search')
        
        results = search_tool.search_news(
            query="technology innovation",
            num_results=5,
            language="en",
            date_restrict="d7",  # Last 7 days
            sort_by="date"
        )
        
        print(f"Found {len(results)} news articles from last 7 days:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   Source: {result['displayLink']}")
            print(f"   URL: {result['link']}")
            print(f"   Snippet: {result['snippet'][:100]}...")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_video_search():
    """Demonstrate video search"""
    print_section("5. Video Search")
    
    try:
        search_tool = get_tool('search')
        
        results = search_tool.search_videos(
            query="python tutorial",
            num_results=5,
            language="en"
        )
        
        print(f"Found {len(results)} video results:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['link']}")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_paginated_search():
    """Demonstrate paginated search"""
    print_section("6. Paginated Search (Multiple Pages)")
    
    try:
        search_tool = get_tool('search')
        
        print("Fetching 25 results across multiple pages...")
        results = search_tool.search_paginated(
            query="deep learning",
            total_results=25,
            search_type="web",
            language="en"
        )
        
        print(f"\nRetrieved {len(results)} results total\n")
        print("First 5 results:")
        for i, result in enumerate(results[:5], 1):
            print(f"{i}. {result['title']}")
        
        print("\nLast 5 results:")
        for i, result in enumerate(results[-5:], len(results)-4):
            print(f"{i}. {result['title']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def demo_batch_search():
    """Demonstrate batch search with multiple queries"""
    print_section("7. Batch Search (Parallel Queries)")
    
    try:
        search_tool = get_tool('search')
        
        queries = [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural networks",
            "natural language processing"
        ]
        
        print(f"Searching {len(queries)} queries in parallel...\n")
        
        results = await search_tool.search_batch(
            queries=queries,
            search_type="web",
            num_results=3
        )
        
        for query, query_results in results.items():
            print(f"\n'{query}' ({len(query_results)} results):")
            for i, result in enumerate(query_results, 1):
                print(f"  {i}. {result['title'][:60]}...")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_quota_monitoring():
    """Demonstrate quota and metrics monitoring"""
    print_section("8. Quota & Metrics Monitoring")
    
    try:
        search_tool = get_tool('search')
        
        # Check quota status
        quota = search_tool.get_quota_status()
        print("Quota Status:")
        print(f"  Remaining Quota: {quota['remaining_quota']} requests")
        print(f"  Max Requests: {quota['max_requests']} per {quota['time_window_seconds']}s")
        print(f"  Circuit Breaker: {quota['circuit_breaker_state']}")
        
        # Get metrics
        print("\nUsage Metrics:")
        metrics = search_tool.get_metrics()
        print(f"  Total Requests: {metrics['total_requests']}")
        print(f"  Successful: {metrics['successful_requests']}")
        print(f"  Failed: {metrics['failed_requests']}")
        print(f"  Cache Hits: {metrics['cache_hits']}")
        
        if metrics['total_requests'] > 0:
            success_rate = metrics['success_rate'] * 100
            print(f"  Success Rate: {success_rate:.1f}%")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_credential_validation():
    """Demonstrate credential validation"""
    print_section("9. Credential Validation")
    
    try:
        search_tool = get_tool('search')
        
        status = search_tool.validate_credentials()
        
        if status['valid']:
            print(f"✓ Credentials are valid!")
            print(f"  Authentication Method: {status.get('method', 'unknown')}")
            print(f"  CSE ID: {status.get('cse_id', 'N/A')}")
            print(f"  Message: {status['message']}")
        else:
            print(f"✗ Credential validation failed")
            print(f"  Error: {status.get('error', 'Unknown error')}")
            print(f"  Message: {status['message']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_error_handling():
    """Demonstrate error handling"""
    print_section("10. Error Handling")
    
    try:
        search_tool = get_tool('search')
        
        # Test with empty query (should raise ValidationError)
        print("Testing with empty query...")
        try:
            search_tool.search_web("")
        except Exception as e:
            print(f"✓ Caught expected error: {e.__class__.__name__}: {e}")
        
        # Test with invalid num_results
        print("\nTesting with invalid num_results...")
        try:
            search_tool.search_web("test", num_results=1000)
        except Exception as e:
            print(f"✓ Caught expected error: {e.__class__.__name__}: {e}")
        
        print("\n✓ Error handling is working correctly")
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Run all demonstrations"""
    print("\n" + "="*80)
    print("  AIECS Search Tool - Comprehensive Demo")
    print("="*80)
    print("\nThis demo showcases all features of the Search Tool.")
    print("Note: Some demos may fail if API credentials are not configured.\n")
    
    # Discover tools
    discover_tools()
    
    # Run demonstrations
    demo_credential_validation()
    demo_quota_monitoring()
    demo_basic_web_search()
    demo_advanced_web_search()
    demo_image_search()
    demo_news_search()
    demo_video_search()
    demo_paginated_search()
    
    # Run async demo
    print("\nRunning batch search demo (async)...")
    asyncio.run(demo_batch_search())
    
    demo_error_handling()
    
    # Final metrics
    demo_quota_monitoring()
    
    print("\n" + "="*80)
    print("  Demo Complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

