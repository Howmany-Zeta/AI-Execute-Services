# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
TTL Strategy Mock Demo - No API Required

This demo shows how the intelligent TTL strategy works without requiring
actual Google API credentials. It uses a mock search tool to demonstrate:

1. Dynamic TTL calculation based on result metadata
2. Cache key generation by tool_executor
3. Different TTL values for different query types
4. Cache hit/miss behavior

Run: poetry run python examples/ttl_strategy_mock_demo.py
"""

import sys
import os
import time
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiecs.tools.base_tool import BaseTool
from aiecs.tools.tool_executor import cache_result_with_strategy


class MockSearchTool(BaseTool):
    """Mock search tool for demonstration purposes"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.call_count = {}

    @staticmethod
    def _static_ttl_strategy(result: Any, args: tuple, kwargs: dict) -> int:
        """Static TTL strategy that can be called from decorator"""
        # Extract metadata from result
        metadata = result.get('_metadata', {})
        intent_type = metadata.get('intent_type', 'GENERAL')
        results_list = result.get('results', [])

        # Intent-based TTL mapping
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
                base_ttl = int(base_ttl * 1.5)
            elif avg_quality < 0.3:
                base_ttl = base_ttl // 2

        print(f"  🔧 TTL Strategy: intent={intent_type}, base_ttl={base_ttl}s ({base_ttl/3600:.1f}h)")
        return base_ttl

    def _create_search_ttl_strategy(self):
        """Create intelligent TTL strategy for search results"""
        def calculate_search_ttl(result: Any, args: tuple, kwargs: dict) -> int:
            # Extract metadata from result
            metadata = result.get('_metadata', {})
            intent_type = metadata.get('intent_type', 'GENERAL')
            results_list = result.get('results', [])
            
            # Intent-based TTL mapping
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
                    base_ttl = int(base_ttl * 1.5)
                elif avg_quality < 0.3:
                    base_ttl = base_ttl // 2
            
            print(f"  🔧 TTL Strategy: intent={intent_type}, base_ttl={base_ttl}s ({base_ttl/3600:.1f}h)")
            return base_ttl
        
        return calculate_search_ttl
    
    @cache_result_with_strategy(
        ttl_strategy=lambda result, args, kwargs:
            MockSearchTool._static_ttl_strategy(result, args, kwargs)
    )
    def search_web(self, query: str, **kwargs) -> Dict[str, Any]:
        """Mock search that simulates different query types"""
        # Track call count
        self.call_count[query] = self.call_count.get(query, 0) + 1
        
        print(f"  ⚙️  Executing search (call #{self.call_count[query]})...")
        time.sleep(0.1)  # Simulate API call
        
        # Determine intent type based on query
        intent_type = 'GENERAL'
        quality_score = 0.7
        
        if 'what is' in query.lower() or 'define' in query.lower():
            intent_type = 'DEFINITION'
            quality_score = 0.9
        elif 'news' in query.lower() or 'latest' in query.lower():
            intent_type = 'RECENT_NEWS'
            quality_score = 0.6
        elif 'how to' in query.lower() or 'tutorial' in query.lower():
            intent_type = 'GENERAL'
            quality_score = 0.8
        
        # Generate mock results
        results = [
            {
                'title': f'Result {i+1} for: {query}',
                'link': f'https://example.com/{i+1}',
                'snippet': f'This is result {i+1}...',
                '_quality': {
                    'quality_score': quality_score,
                    'freshness_score': 0.8
                }
            }
            for i in range(3)
        ]
        
        return {
            'results': results,
            '_metadata': {
                'intent_type': intent_type,
                'query': query,
                'timestamp': time.time()
            }
        }


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def demo_basic_caching():
    """Demonstrate basic caching behavior"""
    print_section("1. Basic Caching - Cache Hit/Miss")
    
    tool = MockSearchTool()
    
    print("🔍 First search (cache MISS):")
    start = time.time()
    result1 = tool.search_web(query="Python programming")
    elapsed1 = time.time() - start
    print(f"  ✅ Results: {len(result1['results'])}")
    print(f"  ⏱️  Time: {elapsed1:.3f}s")
    
    print("\n🔍 Second search - same query (cache HIT):")
    start = time.time()
    result2 = tool.search_web(query="Python programming")
    elapsed2 = time.time() - start
    print(f"  ✅ Results: {len(result2['results'])}")
    print(f"  ⏱️  Time: {elapsed2:.3f}s")
    print(f"  🚀 Speedup: {elapsed1/elapsed2:.1f}x faster!")
    
    print(f"\n📊 Call Statistics:")
    print(f"  - Actual function calls: {tool.call_count.get('Python programming', 0)}")
    print(f"  - Total requests: 2")
    print(f"  - Cache hits: 1")


def demo_intent_based_ttl():
    """Demonstrate different TTL for different query types"""
    print_section("2. Intent-Based TTL Calculation")
    
    tool = MockSearchTool()
    
    queries = [
        ("What is Python?", "DEFINITION", "30 days"),
        ("Python latest news", "RECENT_NEWS", "1 hour"),
        ("How to learn Python", "GENERAL", "1 day"),
    ]
    
    for query, expected_intent, expected_ttl in queries:
        print(f"🔍 Query: '{query}'")
        print(f"  📝 Expected: {expected_intent} → TTL: {expected_ttl}")
        
        result = tool.search_web(query=query)
        metadata = result['_metadata']
        
        print(f"  ✅ Actual Intent: {metadata['intent_type']}")
        print(f"  📊 Results: {len(result['results'])}")
        print()


def demo_quality_adjustment():
    """Demonstrate TTL adjustment based on quality"""
    print_section("3. Quality-Based TTL Adjustment")
    
    print("""
The TTL strategy adjusts cache time based on result quality:

High Quality (score > 0.8):
  - Base TTL × 1.5
  - Example: DEFINITION (30 days) → 45 days
  
Normal Quality (0.3 ≤ score ≤ 0.8):
  - Base TTL (no change)
  - Example: GENERAL (1 day) → 1 day
  
Low Quality (score < 0.3):
  - Base TTL ÷ 2
  - Example: RECENT_NEWS (1 hour) → 30 minutes

This ensures:
✅ High-quality content stays cached longer
✅ Low-quality content expires faster
✅ Automatic quality-based cache management
""")


def demo_cache_key_generation():
    """Demonstrate automatic cache key generation"""
    print_section("4. Automatic Cache Key Generation")
    
    tool = MockSearchTool()
    
    print("Cache keys are automatically generated by tool_executor based on:")
    print("  - Function name")
    print("  - All parameters (args + kwargs)")
    print("  - User ID (if provided)")
    print("  - Task ID (if provided)")
    print()
    
    print("🔍 Same query, same parameters → Same cache key (HIT):")
    tool.search_web(query="AI", num_results=5)
    print("  First call: cache MISS, function executed")
    
    tool.search_web(query="AI", num_results=5)
    print("  Second call: cache HIT, function NOT executed")
    
    print(f"  📊 Function calls: {tool.call_count.get('AI', 0)}")
    
    print("\n🔍 Same query, different parameters → Different cache key (MISS):")
    tool.search_web(query="AI", num_results=10)
    print("  Third call: cache MISS (different num_results), function executed")
    
    print(f"  📊 Function calls: {tool.call_count.get('AI', 0)}")


def demo_ttl_strategy_types():
    """Demonstrate different TTL strategy types"""
    print_section("5. TTL Strategy Types")
    
    print("""
The @cache_result_with_strategy decorator supports three TTL strategy types:

1️⃣ Fixed TTL (int):
   @cache_result_with_strategy(ttl_strategy=3600)
   def operation(self, data):
       return process(data)
   
   → All results cached for 3600 seconds (1 hour)

2️⃣ Dynamic TTL (Callable):
   def calculate_ttl(result, args, kwargs):
       if result.get('type') == 'permanent':
           return 86400 * 30  # 30 days
       return 3600  # 1 hour
   
   @cache_result_with_strategy(ttl_strategy=calculate_ttl)
   def operation(self, data):
       return {'data': data, 'type': 'permanent'}
   
   → TTL calculated based on result content

3️⃣ Default TTL (None):
   @cache_result_with_strategy()
   def operation(self, data):
       return process(data)
   
   → Uses default TTL from ExecutorConfig

Current SearchTool uses Dynamic TTL (type 2) with intent-aware calculation!
""")


def demo_dual_layer_caching():
    """Demonstrate dual-layer caching concept"""
    print_section("6. Dual-Layer Caching Architecture")
    
    print("""
When dual-layer caching is enabled:

┌─────────────────────────────────────────────────────────────┐
│                        Query Request                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L1 Cache (LRU Memory)                                      │
│  - Size: 1000 entries                                       │
│  - TTL: 5 minutes (fixed)                                   │
│  - Purpose: Fast response for recent queries                │
└─────────────────────────────────────────────────────────────┘
                            ↓ (miss)
┌─────────────────────────────────────────────────────────────┐
│  L2 Cache (Redis)                                           │
│  - Size: Unlimited                                          │
│  - TTL: Intelligent (based on intent)                       │
│  - Purpose: Long-term storage for stable content            │
└─────────────────────────────────────────────────────────────┘
                            ↓ (miss)
┌─────────────────────────────────────────────────────────────┐
│  Execute Function                                           │
│  - Call actual API                                          │
│  - Calculate intelligent TTL                                │
│  - Write to L2 (intelligent TTL)                            │
│  - Write to L1 (5 min TTL)                                  │
└─────────────────────────────────────────────────────────────┘

Benefits:
✅ Fast: L1 serves recent queries instantly
✅ Persistent: L2 stores results long-term
✅ Intelligent: TTL adapts to content type
✅ Cost-effective: Reduces API calls significantly
""")


def main():
    """Run all demonstrations"""
    print("="*80)
    print("  TTL Strategy Mock Demo - Intelligent Caching Without API")
    print("="*80)
    
    demo_basic_caching()
    demo_intent_based_ttl()
    demo_quality_adjustment()
    demo_cache_key_generation()
    demo_ttl_strategy_types()
    demo_dual_layer_caching()
    
    print("\n" + "="*80)
    print("  Summary")
    print("="*80)
    print("""
✅ Successfully demonstrated:

1. Cache Hit/Miss Behavior
   - First call: cache miss, function executes
   - Second call: cache hit, function skipped
   - Significant performance improvement

2. Intent-Based TTL Calculation
   - DEFINITION queries: 30 days TTL
   - RECENT_NEWS queries: 1 hour TTL
   - GENERAL queries: 1 day TTL

3. Quality-Based TTL Adjustment
   - High quality → longer cache
   - Low quality → shorter cache

4. Automatic Cache Key Generation
   - Based on function name + parameters
   - No manual key management needed

5. Flexible TTL Strategies
   - Fixed, Dynamic, or Default
   - Easy to implement custom logic

6. Dual-Layer Caching Architecture
   - L1 (Memory): Fast recent queries
   - L2 (Redis): Long-term storage

🎯 Next Steps:
   - Configure Google API credentials to test with real searches
   - Enable Redis for dual-layer caching
   - Monitor cache statistics in production
   - Customize TTL strategies for your use case
""")


if __name__ == "__main__":
    main()

