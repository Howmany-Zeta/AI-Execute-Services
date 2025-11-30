# Search Tool - Developer's Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Installation & Setup](#installation--setup)
3. [Basic Usage](#basic-usage)
4. [Advanced Usage](#advanced-usage)
5. [LangChain Integration](#langchain-integration)
6. [Best Practices](#best-practices)
7. [Common Patterns](#common-patterns)
8. [Troubleshooting](#troubleshooting)
9. [Examples](#examples)

---

## 1. Quick Start

### 1.1 5-Minute Setup

**Step 1: Install Dependencies**
```bash
# Dependencies are included in AIECS
pip install aiecs
```

**Step 2: Get Google Credentials**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select a project
3. Enable "Custom Search API"
4. Create API key
5. Go to [Google Custom Search](https://cse.google.com/)
6. Create a search engine
7. Copy the CSE ID

**Step 3: Configure Environment**
```bash
# Create .env file
cat > .env << EOF
GOOGLE_API_KEY=your_api_key_here
GOOGLE_CSE_ID=your_cse_id_here
EOF
```

**Step 4: Use the Tool**
```python
from dotenv import load_dotenv
load_dotenv()

from aiecs.tools import get_tool

# Initialize
tool = get_tool('search')

# Search
results = tool.search_web("artificial intelligence", num_results=5)

# Display
for result in results:
    print(f"{result['title']}: {result['link']}")
```

### 1.2 First Search in 3 Lines

```python
from aiecs.tools import get_tool
tool = get_tool('search')
results = tool.search_web("python tutorial", num_results=5)
```

---

## 2. Installation & Setup

### 2.1 Prerequisites

- Python 3.8+
- Google Cloud account
- Google Custom Search Engine

### 2.2 Google Custom Search Setup

**Create Custom Search Engine**:
1. Visit https://programmablesearchengine.google.com/
2. Click "Add" to create new search engine
3. Configure:
   - **Sites to search**: Leave blank for web-wide search
   - **Language**: Select your preferred language
   - **Name**: Give it a descriptive name
4. Click "Create"
5. Copy your **Search Engine ID (CSE ID)**

**Get API Key**:
1. Visit https://console.cloud.google.com/apis/credentials
2. Create or select a project
3. Click "Create Credentials" → "API Key"
4. Copy the API key
5. (Recommended) Click on the key to restrict it:
   - API restrictions: Select "Custom Search API"
   - Application restrictions: Add IP restrictions if needed

**Enable Custom Search API**:
1. Go to https://console.cloud.google.com/apis/library
2. Search for "Custom Search API"
3. Click "Enable"

### 2.3 Environment Configuration

**Option 1: Using .env File (Recommended)**

```bash
# .env file in your project root
GOOGLE_API_KEY=AIzaSyBvOkBwv7wjHjf7hK8l9m0n1o2p3q4r5s6t7u8v9w0
GOOGLE_CSE_ID=012345678901234567890:abcdefghijk

# Optional: Advanced configuration
SEARCH_TOOL_MAX_RESULTS_PER_QUERY=10
SEARCH_TOOL_CACHE_TTL=3600
SEARCH_TOOL_RATE_LIMIT_REQUESTS=100
SEARCH_TOOL_ENABLE_QUALITY_ANALYSIS=true
SEARCH_TOOL_ENABLE_INTENT_ANALYSIS=true
```

Load in your application:
```python
from dotenv import load_dotenv
load_dotenv()  # Must be called before importing tools

from aiecs.tools import get_tool
tool = get_tool('search')
```

**Option 2: Environment Variables**

```bash
export GOOGLE_API_KEY="your_api_key"
export GOOGLE_CSE_ID="your_cse_id"
python your_app.py
```

**Option 3: Programmatic Configuration**

```python
from aiecs.tools.search_tool import SearchTool

tool = SearchTool(config={
    'google_api_key': 'your_api_key',
    'google_cse_id': 'your_cse_id',
    'max_results_per_query': 10,
    'enable_quality_analysis': True
})
```

### 2.4 Verify Setup

```python
from aiecs.tools import get_tool

tool = get_tool('search')

# Validate credentials
status = tool.validate_credentials()
if status['valid']:
    print(f"✓ Credentials valid ({status['method']})")
else:
    print(f"✗ Validation failed: {status['error']}")

# Check quota
quota = tool.get_quota_status()
print(f"Remaining quota: {quota['remaining_quota']}/{quota['quota_limit']}")
```

---

## 3. Basic Usage

### 3.1 Web Search

**Simple Search**:
```python
from aiecs.tools import get_tool

tool = get_tool('search')
results = tool.search_web("machine learning", num_results=10)

for result in results:
    print(f"Title: {result['title']}")
    print(f"URL: {result['link']}")
    print(f"Snippet: {result['snippet']}")
    print("---")
```

**Search with Filters**:
```python
results = tool.search_web(
    query="climate change research",
    num_results=10,
    language="en",           # Language
    country="us",            # Country
    safe_search="medium",    # Safe search level
    date_restrict="m6",      # Last 6 months
    file_type="pdf"          # Only PDFs
)
```

**Date Restrictions**:
- `d[number]`: Days (e.g., `d7` = last 7 days)
- `w[number]`: Weeks (e.g., `w2` = last 2 weeks)
- `m[number]`: Months (e.g., `m6` = last 6 months)
- `y[number]`: Years (e.g., `y1` = last year)

**File Types**:
- `pdf`, `doc`, `docx`, `xls`, `xlsx`, `ppt`, `pptx`

### 3.2 Image Search

```python
images = tool.search_images(
    query="sunset beach",
    num_results=10,
    image_size="large",        # icon, small, medium, large, xlarge, xxlarge, huge
    image_type="photo",        # clipart, face, lineart, stock, photo, animated
    image_color_type="color",  # color, gray, mono, trans
    safe_search="high"
)

for img in images:
    print(f"Image URL: {img['link']}")
    print(f"Thumbnail: {img['image']['thumbnailLink']}")
    print(f"Size: {img['image']['width']}x{img['image']['height']}")
```

### 3.3 News Search

```python
news = tool.search_news(
    query="technology innovation",
    num_results=10,
    language="en",
    date_restrict="d7",  # Last 7 days
    sort_by="date"       # or "relevance"
)

for article in news:
    print(f"Headline: {article['title']}")
    print(f"Source: {article['displayLink']}")
    print(f"URL: {article['link']}")
```

### 3.4 Video Search

```python
videos = tool.search_videos(
    query="python tutorial",
    num_results=10,
    safe_search="medium",
    language="en"
)
```

### 3.5 Pagination

**Get More Results** (up to 100):
```python
# Automatic pagination
results = tool.search_paginated(
    query="artificial intelligence",
    total_results=50,      # Up to 100
    search_type="web",
    language="en"
)

print(f"Retrieved {len(results)} results")
```

**Manual Pagination**:
```python
# Page 1 (results 1-10)
page1 = tool.search_web("query", num_results=10, start_index=1)

# Page 2 (results 11-20)
page2 = tool.search_web("query", num_results=10, start_index=11)

# Page 3 (results 21-30)
page3 = tool.search_web("query", num_results=10, start_index=21)
```

### 3.6 Batch Search

**Search Multiple Queries in Parallel**:
```python
import asyncio

queries = [
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "neural networks"
]

results = asyncio.run(tool.search_batch(
    queries=queries,
    search_type="web",
    num_results=5
))

for query, query_results in results.items():
    print(f"\nResults for '{query}':")
    for result in query_results:
        print(f"  - {result['title']}")
```

---

## 4. Advanced Usage

### 4.1 Quality Analysis

**Enable Quality Scoring**:
```python
# Quality analysis is enabled by default
results = tool.search_web("machine learning", num_results=10)

for result in results:
    quality = result['_quality_summary']
    print(f"Title: {result['title']}")
    print(f"Quality Score: {quality['score']:.2f}")
    print(f"Credibility: {quality['level']}")
    print(f"Authoritative: {quality['is_authoritative']}")
    print(f"Authority Score: {quality['authority_score']:.2f}")
    print(f"Relevance Score: {quality['relevance_score']:.2f}")
```

**Filter by Quality**:
```python
results = tool.search_web("research topic", num_results=20)

# Get only high-quality results
high_quality = [
    r for r in results 
    if r['_quality_summary']['level'] == 'high'
]

# Get only authoritative sources
authoritative = [
    r for r in results 
    if r['_quality_summary']['is_authoritative']
]
```

### 4.2 Intent Analysis

**Automatic Query Enhancement**:
```python
# Intent analysis automatically enhances queries
results = tool.search_web(
    query="how to build REST API",
    auto_enhance=True  # Default
)

# Check what happened
for result in results:
    metadata = result.get('_search_metadata', {})
    print(f"Original: {metadata.get('original_query')}")
    print(f"Enhanced: {metadata.get('enhanced_query')}")
    print(f"Intent: {metadata.get('intent_type')}")
    print(f"Confidence: {metadata.get('intent_confidence'):.2f}")
```

**Intent Types Detected**:
- `definition`: "what is X", "define X"
- `how_to`: "how to X", "steps to X"
- `comparison`: "X vs Y", "difference between X and Y"
- `factual`: "when/where/who X"
- `recent_news`: "latest X", "recent X"
- `academic`: "research on X", "study about X"
- `product`: "buy X", "X review"
- `general`: General queries

### 4.3 Result Summaries

**Get Structured Summary**:
```python
response = tool.search_web(
    query="artificial intelligence",
    num_results=20,
    return_summary=True  # Enable summary
)

results = response['results']
summary = response['summary']

print(f"Total Results: {summary['total_results']}")
print(f"Average Quality: {summary['avg_quality_score']:.2f}")
print(f"\nQuality Distribution:")
for level, count in summary['quality_distribution'].items():
    print(f"  {level}: {count}")

print(f"\nTop Domains:")
for domain, count in summary['top_domains'].items():
    print(f"  {domain}: {count}")

print(f"\nRecommended Results:")
for result in summary['recommended_results']:
    print(f"  - {result['title']}")

if summary['warnings']:
    print(f"\nWarnings: {summary['warnings']}")

if summary['suggestions']:
    print(f"\nSuggestions: {summary['suggestions']}")
```

### 4.4 Search Context

**Track Search History**:
```python
# First search
tool.search_web("python basics")

# Second search
tool.search_web("python advanced")

# Get context
context = tool.get_search_context()
print(f"Search History: {len(context['history'])} searches")
print(f"Preferred Domains: {context['preferences']['preferred_domains']}")
print(f"Current Topic: {context['topic_context']['current_topic']}")
```

**Provide Feedback**:
```python
# Search
results = tool.search_web("machine learning")

# User liked a result
tool.search_context.add_feedback(
    query="machine learning",
    result_url="https://example.com",
    feedback_type="positive"
)

# User disliked a result
tool.search_context.add_feedback(
    query="machine learning",
    result_url="https://spam-site.com",
    feedback_type="negative"
)
```

### 4.5 Monitoring & Metrics

**Get Performance Metrics**:
```python
metrics = tool.get_metrics()

print(f"Total Requests: {metrics['requests']['total']}")
print(f"Success Rate: {metrics['requests']['successful'] / metrics['requests']['total']:.2%}")
print(f"Cache Hit Rate: {metrics['cache']['hit_rate']:.2%}")
print(f"Avg Response Time: {metrics['performance']['avg_response_time']:.0f}ms")
print(f"Avg Quality Score: {metrics['quality']['avg_quality_score']:.2f}")
```

**Get Health Score**:
```python
health = tool.get_health_score()
print(f"System Health: {health:.2%}")

if health < 0.8:
    print("⚠️ Warning: System health is below optimal")
```

**Get Human-Readable Report**:
```python
print(tool.get_metrics_report())
```

**Check Quota Status**:
```python
quota = tool.get_quota_status()
print(f"Quota: {quota['remaining_quota']}/{quota['quota_limit']}")
print(f"Circuit Breaker: {quota['circuit_breaker_state']}")

if quota['remaining_quota'] < 10:
    print("⚠️ Warning: Low quota remaining")
```

---

## 5. LangChain Integration

### 5.1 Basic LangChain Usage

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from aiecs.tools.langchain_adapter import get_langchain_tools

# Get search tools for LangChain
tools = get_langchain_tools(['search'])

# Create agent
llm = ChatOpenAI(model="gpt-4", temperature=0)

prompt = PromptTemplate.from_template("""
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
{agent_scratchpad}
""")

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Use the agent
result = agent_executor.invoke({
    "input": "Find recent news about artificial intelligence breakthroughs"
})

print(result['output'])
```

### 5.2 Available LangChain Tools

When you call `get_langchain_tools(['search'])`, you get 9 individual tools:

1. `search_search_web` - Web search
2. `search_search_images` - Image search
3. `search_search_news` - News search
4. `search_search_videos` - Video search
5. `search_search_paginated` - Paginated search
6. `search_search_batch` - Batch search
7. `search_validate_credentials` - Credential validation
8. `search_get_quota_status` - Quota status
9. `search_get_metrics` - Usage metrics

### 5.3 Custom LangChain Tool Selection

```python
from aiecs.tools.langchain_adapter import get_langchain_tools

# Get only specific operations
tools = get_langchain_tools(
    ['search'],
    operations=['search_web', 'search_news']
)

# Now agent only has access to web and news search
```

---

## 6. Best Practices

### 6.1 Performance Optimization

**1. Enable Caching**:
```python
# Caching is enabled by default
# Adjust TTL based on your needs
tool = SearchTool(config={
    'enable_intelligent_cache': True,
    'cache_ttl': 3600  # 1 hour default
})
```

**2. Use Appropriate Result Counts**:
```python
# Don't request more than you need
results = tool.search_web("query", num_results=5)  # Not 100
```

**3. Batch Similar Queries**:
```python
# Instead of multiple individual calls
queries = ["AI", "ML", "DL"]
results = asyncio.run(tool.search_batch(queries=queries))
```

**4. Leverage Pagination Wisely**:
```python
# Only paginate when necessary
results = tool.search_paginated("query", total_results=20)  # Not 100
```

### 6.2 Quota Management

**1. Monitor Quota**:
```python
quota = tool.get_quota_status()
if quota['remaining_quota'] < 10:
    # Send alert or throttle requests
    logger.warning("Low quota remaining")
```

**2. Configure Rate Limits**:
```python
tool = SearchTool(config={
    'rate_limit_requests': 100,  # Match your API quota
    'rate_limit_window': 86400   # 24 hours
})
```

**3. Handle Rate Limit Errors**:
```python
from aiecs.tools.search_tool import RateLimitError
import time

try:
    results = tool.search_web("query")
except RateLimitError as e:
    # Wait and retry
    time.sleep(60)
    results = tool.search_web("query")
```

### 6.3 Error Handling

**1. Comprehensive Error Handling**:
```python
from aiecs.tools.search_tool import (
    RateLimitError,
    QuotaExceededError,
    CircuitBreakerOpenError,
    AuthenticationError,
    SearchAPIError
)

try:
    results = tool.search_web("query")
    
except AuthenticationError as e:
    # Fix credentials
    logger.error(f"Auth error: {e}")
    
except QuotaExceededError as e:
    # Use fallback or wait
    logger.error(f"Quota exceeded: {e}")
    
except RateLimitError as e:
    # Wait and retry
    time.sleep(60)
    
except CircuitBreakerOpenError as e:
    # API is down, use fallback
    logger.error(f"Circuit breaker open: {e}")
    
except SearchAPIError as e:
    # API error, retry or fallback
    logger.error(f"API error: {e}")
```

**2. Use Agent-Friendly Errors**:
```python
try:
    results = tool.search_web("query")
except Exception as e:
    error_info = tool.error_handler.format_error(e)
    print(f"Error: {error_info['message']}")
    print(f"Suggested actions: {error_info['suggested_actions']}")
    print(f"Is retryable: {error_info['is_retryable']}")
```

### 6.4 Quality Assurance

**1. Filter by Quality**:
```python
results = tool.search_web("query", num_results=20)
high_quality = [
    r for r in results 
    if r['_quality_summary']['score'] > 0.8
]
```

**2. Prefer Authoritative Sources**:
```python
authoritative = [
    r for r in results 
    if r['_quality_summary']['is_authoritative']
]
```

**3. Monitor Quality Metrics**:
```python
metrics = tool.get_metrics()
if metrics['quality']['avg_quality_score'] < 0.7:
    logger.warning("Average quality score is low")
```

---

## 7. Common Patterns

### 7.1 Research Assistant Pattern

```python
def research_topic(topic: str, depth: str = "basic"):
    """Research a topic with varying depth"""
    tool = get_tool('search')
    
    if depth == "basic":
        # Quick overview
        results = tool.search_web(topic, num_results=5)
        
    elif depth == "comprehensive":
        # Detailed research
        results = tool.search_paginated(topic, total_results=50)
        
        # Get academic papers
        papers = tool.search_web(
            topic,
            file_type="pdf",
            num_results=10
        )
        
        # Get recent news
        news = tool.search_news(
            topic,
            date_restrict="m1",
            num_results=10
        )
        
        return {
            'overview': results,
            'papers': papers,
            'news': news
        }
    
    return results
```

### 7.2 Content Aggregator Pattern

```python
async def aggregate_content(topics: List[str]):
    """Aggregate content from multiple topics"""
    tool = get_tool('search')
    
    # Batch search all topics
    results = await tool.search_batch(
        queries=topics,
        search_type="web",
        num_results=10
    )
    
    # Filter for high quality
    aggregated = {}
    for topic, topic_results in results.items():
        high_quality = [
            r for r in topic_results
            if r['_quality_summary']['score'] > 0.8
        ]
        aggregated[topic] = high_quality
    
    return aggregated
```

### 7.3 News Monitor Pattern

```python
def monitor_news(keywords: List[str], hours: int = 24):
    """Monitor news for specific keywords"""
    tool = get_tool('search')
    
    date_restrict = f"h{hours}"  # Last N hours
    
    all_news = []
    for keyword in keywords:
        news = tool.search_news(
            query=keyword,
            date_restrict=date_restrict,
            sort_by="date",
            num_results=10
        )
        all_news.extend(news)
    
    # Remove duplicates
    seen_urls = set()
    unique_news = []
    for article in all_news:
        if article['link'] not in seen_urls:
            seen_urls.add(article['link'])
            unique_news.append(article)
    
    return sorted(unique_news, key=lambda x: x.get('date', ''), reverse=True)
```

### 7.4 Smart Search Pattern

```python
def smart_search(query: str):
    """Search with automatic optimization"""
    tool = get_tool('search')
    
    # Get results with summary
    response = tool.search_web(
        query=query,
        num_results=20,
        auto_enhance=True,
        return_summary=True
    )
    
    results = response['results']
    summary = response['summary']
    
    # If quality is low, try enhanced query
    if summary['avg_quality_score'] < 0.6:
        # Try with academic sources
        results = tool.search_web(
            query=f"{query} research paper",
            file_type="pdf",
            num_results=10
        )
    
    # Return only high-quality results
    return [
        r for r in results
        if r['_quality_summary']['score'] > 0.7
    ]
```

---

## 8. Troubleshooting

### 8.1 Common Issues

**Issue: AuthenticationError**
```
Error: Google API key not provided
```
**Solution**:
```python
# Check environment variables
import os
print(f"API Key: {os.getenv('GOOGLE_API_KEY')}")
print(f"CSE ID: {os.getenv('GOOGLE_CSE_ID')}")

# Or set programmatically
tool = SearchTool(config={
    'google_api_key': 'your_key',
    'google_cse_id': 'your_cse_id'
})
```

**Issue: QuotaExceededError**
```
Error: API quota exceeded
```
**Solution**:
```python
# Check quota
quota = tool.get_quota_status()
print(f"Quota: {quota['remaining_quota']}/{quota['quota_limit']}")

# Increase cache TTL to reduce API calls
tool = SearchTool(config={'cache_ttl': 7200})  # 2 hours

# Or wait for quota reset (24 hours)
```

**Issue: Low Quality Results**
```
Average quality score is low
```
**Solution**:
```python
# Enable query enhancement
results = tool.search_web(query, auto_enhance=True)

# Add specific terms
results = tool.search_web(f"{query} research paper")

# Filter by file type
results = tool.search_web(query, file_type="pdf")

# Check intent suggestions
response = tool.search_web(query, return_summary=True)
print(response['summary']['suggestions'])
```

**Issue: Circuit Breaker Open**
```
Error: Circuit breaker is open
```
**Solution**:
```python
# Check circuit breaker status
quota = tool.get_quota_status()
print(f"Circuit Breaker: {quota['circuit_breaker_state']}")

# Wait for recovery (default: 60 seconds)
time.sleep(60)

# Or adjust threshold
tool = SearchTool(config={
    'circuit_breaker_threshold': 10,  # More tolerant
    'circuit_breaker_timeout': 120    # Longer recovery
})
```

### 8.2 Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Now all operations are logged
tool = get_tool('search')
results = tool.search_web("query")
```

### 8.3 Validation

```python
# Validate credentials
status = tool.validate_credentials()
if not status['valid']:
    print(f"Validation failed: {status['error']}")
    print(f"API Key present: {status.get('api_key_present')}")
    print(f"CSE ID present: {status.get('cse_id_present')}")

# Test search
try:
    results = tool.search_web("test", num_results=1)
    print("✓ Search working")
except Exception as e:
    print(f"✗ Search failed: {e}")
```

---

## 9. Examples

### 9.1 Complete Example: Research Assistant

```python
from dotenv import load_dotenv
load_dotenv()

from aiecs.tools import get_tool
import asyncio

class ResearchAssistant:
    def __init__(self):
        self.tool = get_tool('search')
    
    def research(self, topic: str):
        """Comprehensive research on a topic"""
        print(f"Researching: {topic}\n")
        
        # 1. Get overview
        print("1. Getting overview...")
        overview = self.tool.search_web(
            topic,
            num_results=10,
            auto_enhance=True,
            return_summary=True
        )
        
        print(f"   Found {len(overview['results'])} results")
        print(f"   Avg quality: {overview['summary']['avg_quality_score']:.2f}")
        
        # 2. Get academic papers
        print("\n2. Finding academic papers...")
        papers = self.tool.search_web(
            f"{topic} research",
            file_type="pdf",
            num_results=10
        )
        
        authoritative_papers = [
            p for p in papers
            if p['_quality_summary']['is_authoritative']
        ]
        print(f"   Found {len(authoritative_papers)} authoritative papers")
        
        # 3. Get recent news
        print("\n3. Checking recent news...")
        news = self.tool.search_news(
            topic,
            date_restrict="m1",
            num_results=10
        )
        print(f"   Found {len(news)} recent articles")
        
        # 4. Compile report
        return {
            'topic': topic,
            'overview': overview['results'][:5],
            'papers': authoritative_papers[:5],
            'news': news[:5],
            'summary': overview['summary']
        }

# Use the assistant
assistant = ResearchAssistant()
report = assistant.research("quantum computing")

print("\n" + "="*80)
print("RESEARCH REPORT")
print("="*80)

print(f"\nTopic: {report['topic']}")
print(f"\nTop Results:")
for i, result in enumerate(report['overview'], 1):
    print(f"{i}. {result['title']}")
    print(f"   Quality: {result['_quality_summary']['score']:.2f}")

print(f"\nAcademic Papers:")
for paper in report['papers']:
    print(f"- {paper['title']}")

print(f"\nRecent News:")
for article in report['news']:
    print(f"- {article['title']}")
```

### 9.2 Complete Example: News Aggregator

```python
import asyncio
from aiecs.tools import get_tool
from datetime import datetime

async def aggregate_tech_news():
    """Aggregate technology news from multiple topics"""
    tool = get_tool('search')
    
    topics = [
        "artificial intelligence",
        "quantum computing",
        "blockchain",
        "cybersecurity",
        "5G technology"
    ]
    
    print("Aggregating tech news...\n")
    
    # Batch search all topics
    results = await tool.search_batch(
        queries=topics,
        search_type="news",
        num_results=5,
        date_restrict="d7"  # Last 7 days
    )
    
    # Organize by topic
    for topic, articles in results.items():
        print(f"\n{topic.upper()}")
        print("-" * 80)
        
        for article in articles:
            print(f"• {article['title']}")
            print(f"  {article['displayLink']}")
            print(f"  {article['link']}")
            print()

# Run the aggregator
asyncio.run(aggregate_tech_news())
```

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-18  
**Maintainer**: AIECS Tools Team
