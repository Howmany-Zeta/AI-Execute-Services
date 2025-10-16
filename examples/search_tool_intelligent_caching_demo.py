"""
SearchTool Intelligent Caching with tool_executor Demo

This example demonstrates how SearchTool now uses tool_executor's intelligent caching
with dynamic TTL calculation based on query intent, result quality, and freshness.

Key Features:
1. Automatic cache key generation by tool_executor
2. Dynamic TTL calculation based on search context
3. Support for dual-layer caching (L1: LRU + L2: Redis)
4. Intent-aware TTL strategies

Setup:
1. Set GOOGLE_API_KEY and GOOGLE_CSE_ID in your .env file
2. Optional: Configure Redis for dual-layer caching
3. Run: python examples/search_tool_intelligent_caching_demo.py
"""

import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiecs.tools.search_tool import SearchTool
from aiecs.tools.tool_executor import cache_result_with_strategy


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def demo_basic_caching():
    """Demonstrate basic intelligent caching"""
    print_section("1. Basic Intelligent Caching")

    try:
        search_tool = SearchTool()
        
        # First search - will be cached
        print("🔍 First search (will be cached)...")
        start = time.time()
        result1 = search_tool.search_web(
            query="Python programming tutorial",
            num_results=5
        )
        elapsed1 = time.time() - start
        
        print(f"✅ Found {len(result1.get('results', []))} results")
        print(f"⏱️  Time: {elapsed1:.2f}s")
        print(f"📊 Intent Type: {result1.get('_metadata', {}).get('intent_type')}")
        
        # Second search - should hit cache
        print("\n🔍 Second search (should hit cache)...")
        start = time.time()
        result2 = search_tool.search_web(
            query="Python programming tutorial",
            num_results=5
        )
        elapsed2 = time.time() - start
        
        print(f"✅ Found {len(result2.get('results', []))} results")
        print(f"⏱️  Time: {elapsed2:.2f}s (should be much faster!)")
        print(f"🚀 Speedup: {elapsed1/elapsed2:.1f}x")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_intent_based_ttl():
    """Demonstrate intent-based TTL calculation"""
    print_section("2. Intent-Based TTL Calculation")

    try:
        search_tool = SearchTool()
        
        # Different query types with different TTLs
        queries = [
            ("What is Python?", "DEFINITION - Long TTL (30 days)"),
            ("Python latest news", "RECENT_NEWS - Short TTL (1 hour)"),
            ("Python tutorial", "GENERAL - Medium TTL (1 day)"),
        ]
        
        for query, description in queries:
            print(f"\n🔍 Query: '{query}'")
            print(f"📝 Expected: {description}")
            
            result = search_tool.search_web(query=query, num_results=3)
            metadata = result.get('_metadata', {})
            
            print(f"✅ Intent Type: {metadata.get('intent_type')}")
            print(f"📊 Results: {len(result.get('results', []))}")
            
            # The TTL is calculated internally by the decorator
            # based on intent_type in _metadata
            
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_custom_ttl_strategy():
    """Demonstrate custom TTL strategy"""
    print_section("3. Custom TTL Strategy Example")
    
    print("""
Custom TTL Strategy Function:

def calculate_search_ttl(result, args, kwargs):
    # Extract metadata
    metadata = result.get('_metadata', {})
    intent_type = metadata.get('intent_type', 'GENERAL')
    results_list = result.get('results', [])
    
    # Intent-based base TTL
    ttl_map = {
        'DEFINITION': 86400 * 30,  # 30 days
        'FACTUAL': 86400 * 7,      # 7 days
        'GENERAL': 86400,          # 1 day
        'RECENT_NEWS': 3600,       # 1 hour
        'REAL_TIME': 300           # 5 minutes
    }
    base_ttl = ttl_map.get(intent_type, 3600)
    
    # Adjust based on result quality
    if results_list:
        avg_quality = sum(
            r.get('_quality', {}).get('quality_score', 0.5)
            for r in results_list
        ) / len(results_list)
        
        if avg_quality > 0.8:
            base_ttl = int(base_ttl * 1.5)  # High quality -> longer cache
    
    return base_ttl

# Usage with decorator:
@cache_result_with_strategy(ttl_strategy=calculate_search_ttl)
def search_web(self, query, **kwargs):
    # ... search logic
    return {
        'results': [...],
        '_metadata': {'intent_type': 'DEFINITION', ...}
    }
""")


def demo_cache_statistics():
    """Demonstrate cache statistics"""
    print_section("4. Cache Statistics")

    try:
        search_tool = SearchTool()
        
        # Get executor stats
        if hasattr(search_tool, '_executor'):
            stats = search_tool._executor.get_stats()
            print("📊 Tool Executor Statistics:")
            print(f"  - Total Requests: {stats.get('total_requests', 0)}")
            print(f"  - Cache Hits: {stats.get('cache_hits', 0)}")
            print(f"  - Cache Misses: {stats.get('cache_misses', 0)}")
            print(f"  - Hit Rate: {stats.get('hit_rate', 0):.1%}")
            print(f"  - Failures: {stats.get('failures', 0)}")
            print(f"  - Avg Response Time: {stats.get('avg_response_time', 0):.3f}s")
        
        # Get cache provider stats
        if hasattr(search_tool._executor, 'cache_provider'):
            cache_stats = search_tool._executor.cache_provider.get_stats()
            print("\n💾 Cache Provider Statistics:")
            for key, value in cache_stats.items():
                print(f"  - {key}: {value}")
                
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_dual_layer_caching():
    """Demonstrate dual-layer caching configuration"""
    print_section("5. Dual-Layer Caching Configuration")
    
    print("""
To enable dual-layer caching (L1: LRU + L2: Redis):

1. Configure tool_executor with dual cache:

from aiecs.tools.tool_executor import ToolExecutor, ExecutorConfig

config = ExecutorConfig(
    enable_cache=True,
    enable_dual_cache=True,      # Enable dual-layer cache
    enable_redis_cache=True,     # Enable Redis as L2
    cache_size=1000,             # L1 cache size
    cache_ttl=3600               # Default TTL
)

executor = ToolExecutor(config)

2. SearchTool will automatically use this configuration:
   - L1 (LRU): Fast in-memory cache with short TTL (5 minutes)
   - L2 (Redis): Persistent cache with intelligent TTL (based on intent)

3. Cache flow:
   Query → Check L1 → Check L2 → Execute Search
   Result → Write to L2 (intelligent TTL) → Write to L1 (short TTL)

4. Benefits:
   - Fast response for recent queries (L1)
   - Long-term caching for stable content (L2)
   - Automatic TTL calculation based on search context
   - Reduced API calls and costs
""")


def main():
    """Main demonstration function"""
    print("="*80)
    print("  SearchTool Intelligent Caching with tool_executor Demo")
    print("="*80)
    
    # Run demonstrations
    demo_basic_caching()
    demo_intent_based_ttl()
    demo_custom_ttl_strategy()
    demo_cache_statistics()
    demo_dual_layer_caching()
    
    print("\n" + "="*80)
    print("  Summary")
    print("="*80)
    print("""
✅ Key Improvements:

1. Unified Caching Architecture:
   - SearchTool now uses tool_executor's caching infrastructure
   - Consistent cache key generation across all tools
   - Support for pluggable cache providers

2. Intelligent TTL Calculation:
   - Dynamic TTL based on query intent type
   - Adjustments based on result quality and freshness
   - Extensible strategy pattern for custom TTL logic

3. Dual-Layer Caching:
   - L1 (LRU): Fast in-memory cache for recent queries
   - L2 (Redis): Persistent cache with intelligent TTL
   - Automatic cache promotion and demotion

4. Easy Integration:
   - Simple decorator: @cache_result_with_strategy(ttl_strategy=...)
   - Flexible TTL strategies: int, Callable, or None
   - Compatible with existing tool_executor features

5. Developer Experience:
   - No manual cache key generation required
   - Automatic cache invalidation based on TTL
   - Built-in cache statistics and monitoring
""")


if __name__ == "__main__":
    main()

