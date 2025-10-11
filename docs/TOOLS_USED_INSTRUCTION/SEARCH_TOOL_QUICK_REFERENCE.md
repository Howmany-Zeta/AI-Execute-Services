# Search Tool Quick Reference

## Setup (2 minutes)

```bash
# 1. Add to .env
GOOGLE_API_KEY=your_api_key
GOOGLE_CSE_ID=your_cse_id

# 2. Use in code
from aiecs.tools import get_tool
tool = get_tool('search')
```

## Common Operations

### Web Search
```python
# Basic
results = tool.search_web("AI research", num_results=5)

# Advanced
results = tool.search_web(
    query="machine learning",
    num_results=10,
    language="en",
    date_restrict="m6",  # Last 6 months
    file_type="pdf"
)
```

### Image Search
```python
images = tool.search_images(
    query="sunset",
    num_results=10,
    image_size="large",
    image_type="photo"
)
```

### News Search
```python
news = tool.search_news(
    query="technology",
    date_restrict="d7",  # Last 7 days
    sort_by="date"
)
```

### Paginated (25+ results)
```python
results = tool.search_paginated(
    query="deep learning",
    total_results=50,
    search_type="web"
)
```

### Batch (Multiple queries)
```python
import asyncio
results = asyncio.run(tool.search_batch(
    queries=["AI", "ML", "DL"],
    num_results=5
))
```

## Monitoring

```python
# Check quota
quota = tool.get_quota_status()
print(f"Remaining: {quota['remaining_quota']}")

# Get metrics
metrics = tool.get_metrics()
print(f"Success rate: {metrics['success_rate']:.1%}")
```

## Error Handling

```python
from aiecs.tools.task_tools.search_tool import (
    RateLimitError, QuotaExceededError, AuthenticationError
)

try:
    results = tool.search_web("query")
except RateLimitError:
    print("Rate limit exceeded, wait and retry")
except QuotaExceededError:
    print("Daily quota exceeded")
except AuthenticationError:
    print("Check API credentials")
```

## Parameters Cheat Sheet

### Date Restrictions
- `d[1-365]`: Days (e.g., "d7" = last 7 days)
- `w[1-52]`: Weeks (e.g., "w2" = last 2 weeks)
- `m[1-12]`: Months (e.g., "m6" = last 6 months)
- `y[1-50]`: Years (e.g., "y1" = last year)

### Image Sizes
- `icon`, `small`, `medium`, `large`, `xlarge`, `xxlarge`, `huge`

### Image Types
- `clipart`, `face`, `lineart`, `stock`, `photo`, `animated`

### Safe Search
- `off`, `medium`, `high`

### File Types
- `pdf`, `doc`, `docx`, `xls`, `xlsx`, `ppt`, `pptx`, `txt`, etc.

## LangChain Usage

```python
from aiecs.tools.langchain_adapter import get_langchain_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI

tools = get_langchain_tools(['search'])
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)

result = executor.invoke({
    "input": "Find recent AI news"
})
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Authentication failed" | Set `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` |
| "Quota exceeded" | Wait 24h or upgrade plan |
| "Circuit breaker OPEN" | Wait 60s, automatic recovery |
| "Rate limit exceeded" | Automatic backoff, or increase limits |

## Configuration

```bash
# Optional: Customize limits
SEARCH_TOOL_RATE_LIMIT_REQUESTS=1000
SEARCH_TOOL_RATE_LIMIT_WINDOW=86400
SEARCH_TOOL_CACHE_TTL=3600
```

## Documentation

- Full Docs: `docs/TOOLS/TOOLS_SEARCH_TOOL.md`
- Examples: `examples/search_tool_demo.py`
- Setup Guide: `examples/README_SEARCH_TOOL.md`

