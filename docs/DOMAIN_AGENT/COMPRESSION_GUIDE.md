# ContextEngine Compression Strategies

This comprehensive guide covers all compression strategies available in ContextEngine, including when to use each strategy, configuration options, and best practices.

## Table of Contents

1. [Overview](#overview)
2. [Compression Strategies](#compression-strategies)
3. [Configuration Options](#configuration-options)
4. [Use Cases](#use-cases)
5. [Custom Compression Prompts](#custom-compression-prompts)
6. [Auto-Compression](#auto-compression)
7. [Best Practices](#best-practices)

## Overview

ContextEngine compression helps manage conversation history size and reduce token usage by:

- **Reducing Token Count**: Compress long conversations to stay within token limits
- **Preserving Context**: Keep important recent messages while compressing older ones
- **Multiple Strategies**: Choose the best strategy for your use case
- **Automatic Compression**: Trigger compression automatically when thresholds are exceeded

### Compression Strategies

1. **truncate**: Fast truncation, keeps most recent N messages (no LLM required)
2. **summarize**: LLM-based summarization of older messages
3. **semantic**: Embedding-based deduplication of similar messages
4. **hybrid**: Combination of multiple strategies applied sequentially

## Compression Strategies

### Strategy 1: Truncate

Fast truncation strategy that keeps the most recent N messages.

**Use When**:
- You need fast compression (no LLM calls)
- Recent messages are most important
- Older context can be discarded
- Cost is a concern (no LLM usage)

**Configuration**:
```python
from aiecs.domain.context import CompressionConfig

config = CompressionConfig(
    strategy="truncate",
    max_messages=50,  # Keep 50 most recent messages
    keep_recent=10   # Always keep 10 most recent
)
```

**Example**:
```python
from aiecs.domain.context import ContextEngine, CompressionConfig

# Configure truncation
compression_config = CompressionConfig(
    strategy="truncate",
    max_messages=50,
    keep_recent=10
)

context_engine = ContextEngine(compression_config=compression_config)
await context_engine.initialize()

# Compression happens automatically
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

# Long conversation automatically truncated
for i in range(100):
    await agent.execute_task(
        {"description": f"Message {i}"},
        {"session_id": "user-123"}
    )
# Only 50 most recent messages kept
```

### Strategy 2: Summarize

LLM-based summarization of older messages while keeping recent ones.

**Use When**:
- You need to preserve older context
- Recent messages are critical
- You can afford LLM costs
- Quality summarization is important

**Configuration**:
```python
config = CompressionConfig(
    strategy="summarize",
    keep_recent=10,  # Keep 10 most recent messages
    summary_max_tokens=500,  # Maximum tokens for summary
    include_summary_in_history=True,  # Add summary as system message
    summary_prompt_template=None  # Use default prompt
)
```

**Example**:
```python
compression_config = CompressionConfig(
    strategy="summarize",
    keep_recent=10,
    summary_max_tokens=500,
    include_summary_in_history=True
)

context_engine = ContextEngine(compression_config=compression_config)
await context_engine.initialize()

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

# Older messages summarized, recent ones preserved
for i in range(100):
    await agent.execute_task(
        {"description": f"Message {i}"},
        {"session_id": "user-123"}
    )
# 10 most recent messages + summary of older messages
```

### Strategy 3: Semantic

Embedding-based deduplication of similar messages.

**Use When**:
- You have many similar/redundant messages
- You want to preserve unique information
- You have embedding model access
- Quality preservation is important

**Configuration**:
```python
config = CompressionConfig(
    strategy="semantic",
    keep_recent=10,  # Always keep 10 most recent
    similarity_threshold=0.95,  # Remove messages with >95% similarity
    embedding_model="text-embedding-ada-002"  # Embedding model
)
```

**Example**:
```python
compression_config = CompressionConfig(
    strategy="semantic",
    keep_recent=10,
    similarity_threshold=0.95,
    embedding_model="text-embedding-ada-002"
)

context_engine = ContextEngine(compression_config=compression_config)
await context_engine.initialize()

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

# Similar messages deduplicated
for i in range(100):
    await agent.execute_task(
        {"description": "What's the weather?"},  # Similar messages
        {"session_id": "user-123"}
    )
# Duplicate messages removed, unique ones preserved
```

### Strategy 4: Hybrid

Combination of multiple strategies applied sequentially.

**Use When**:
- You need the best of multiple strategies
- You want both speed and quality
- You have complex compression requirements
- You want maximum compression efficiency

**Configuration**:
```python
config = CompressionConfig(
    strategy="hybrid",
    hybrid_strategies=["truncate", "summarize"],  # Apply truncate then summarize
    keep_recent=10,
    summary_max_tokens=500
)
```

**Example**:
```python
compression_config = CompressionConfig(
    strategy="hybrid",
    hybrid_strategies=["truncate", "summarize"],
    keep_recent=10,
    summary_max_tokens=500
)

context_engine = ContextEngine(compression_config=compression_config)
await context_engine.initialize()

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

# Hybrid compression: truncate then summarize
for i in range(200):
    await agent.execute_task(
        {"description": f"Message {i}"},
        {"session_id": "user-123"}
    )
# First truncate to 100 messages, then summarize older ones
```

## Configuration Options

### Basic Configuration

```python
compression_config = CompressionConfig(
    strategy="summarize",  # Compression strategy
    max_messages=50,  # Max messages (for truncate)
    keep_recent=10,  # Always keep N recent messages
    summary_max_tokens=500,  # Max tokens for summary
    include_summary_in_history=True  # Add summary to history
)
```

### Advanced Configuration

```python
compression_config = CompressionConfig(
    strategy="hybrid",
    hybrid_strategies=["truncate", "summarize"],
    keep_recent=20,
    summary_max_tokens=1000,
    summary_prompt_template=(
        "Summarize the following conversation focusing on "
        "key decisions and action items:\n\n{messages}"
    ),
    similarity_threshold=0.95,
    embedding_model="text-embedding-ada-002",
    auto_compress_enabled=True,
    auto_compress_threshold=100,
    auto_compress_target=50,
    compression_timeout=30
)
```

## Use Cases

### Use Case 1: Long Conversations

For conversations that grow very long over time.

```python
# Use summarize strategy to preserve context
compression_config = CompressionConfig(
    strategy="summarize",
    keep_recent=20,
    auto_compress_enabled=True,
    auto_compress_threshold=100,
    auto_compress_target=50
)
```

### Use Case 2: Cost Optimization

Minimize LLM costs while maintaining functionality.

```python
# Use truncate strategy (no LLM calls)
compression_config = CompressionConfig(
    strategy="truncate",
    max_messages=50,
    keep_recent=10
)
```

### Use Case 3: Quality Preservation

Preserve important context while reducing size.

```python
# Use semantic strategy to remove duplicates
compression_config = CompressionConfig(
    strategy="semantic",
    keep_recent=10,
    similarity_threshold=0.95
)
```

### Use Case 4: Maximum Compression

Get maximum compression with hybrid strategy.

```python
# Use hybrid strategy for best compression
compression_config = CompressionConfig(
    strategy="hybrid",
    hybrid_strategies=["truncate", "summarize"],
    keep_recent=10,
    summary_max_tokens=500
)
```

## Custom Compression Prompts

### Pattern 1: Custom Summarization Prompt

Use custom prompt for summarization.

```python
compression_config = CompressionConfig(
    strategy="summarize",
    keep_recent=10,
    summary_prompt_template=(
        "Summarize the following conversation focusing on:\n"
        "1. Key decisions made\n"
        "2. Action items\n"
        "3. Important context\n\n"
        "Conversation:\n{messages}\n\n"
        "Summary:"
    ),
    summary_max_tokens=500
)
```

### Pattern 2: Domain-Specific Prompt

Use domain-specific prompt for your use case.

```python
# Customer support prompt
compression_config = CompressionConfig(
    strategy="summarize",
    summary_prompt_template=(
        "Summarize this customer support conversation:\n"
        "- Customer issue\n"
        "- Resolution steps\n"
        "- Current status\n\n"
        "{messages}\n\n"
        "Summary:"
    )
)

# Technical support prompt
compression_config = CompressionConfig(
    strategy="summarize",
    summary_prompt_template=(
        "Summarize this technical conversation:\n"
        "- Problem description\n"
        "- Troubleshooting steps\n"
        "- Solution\n\n"
        "{messages}\n\n"
        "Summary:"
    )
)
```

### Pattern 3: Multi-Language Prompt

Use prompts in different languages.

```python
# Spanish prompt
compression_config = CompressionConfig(
    strategy="summarize",
    summary_prompt_template=(
        "Resume la siguiente conversación enfocándote en "
        "decisiones clave y elementos de acción:\n\n{messages}"
    )
)
```

## Auto-Compression

### Pattern 1: Message Count Trigger

Trigger compression when message count exceeds threshold.

```python
compression_config = CompressionConfig(
    strategy="summarize",
    auto_compress_enabled=True,
    auto_compress_threshold=100,  # Compress when 100+ messages
    auto_compress_target=50  # Target 50 messages after compression
)

context_engine = ContextEngine(compression_config=compression_config)
await context_engine.initialize()

# Compression happens automatically at 100 messages
for i in range(150):
    await agent.execute_task(
        {"description": f"Message {i}"},
        {"session_id": "user-123"}
    )
# Compression triggered at 100 messages, reduced to ~50
```

### Pattern 2: Token Count Trigger

Trigger compression based on token count (if supported).

```python
# Note: Token-based triggers may require custom implementation
compression_config = CompressionConfig(
    strategy="summarize",
    auto_compress_enabled=True,
    auto_compress_threshold=100,  # Message count threshold
    auto_compress_target=50
)
```

### Pattern 3: Time-Based Compression

Compress old messages periodically.

```python
import asyncio

async def compress_old_messages():
    """Compress messages older than 1 hour"""
    while True:
        # Get sessions with old messages
        sessions = await context_engine.list_sessions()
        
        for session in sessions:
            # Compress if messages older than 1 hour
            await context_engine.compress_conversation(
                session_id=session.session_id,
                older_than_hours=1
            )
        
        await asyncio.sleep(3600)  # Check every hour

# Start compression task
asyncio.create_task(compress_old_messages())
```

## Best Practices

### 1. Choose Appropriate Strategy

Select strategy based on your needs:

```python
# Fast and cheap: truncate
# Quality preservation: summarize
# Duplicate removal: semantic
# Maximum compression: hybrid
```

### 2. Set Appropriate Thresholds

Set thresholds based on your token limits:

```python
# For 4K token limit
compression_config = CompressionConfig(
    auto_compress_threshold=50,  # Compress at 50 messages
    auto_compress_target=30  # Target 30 messages
)

# For 8K token limit
compression_config = CompressionConfig(
    auto_compress_threshold=100,
    auto_compress_target=60
)
```

### 3. Always Keep Recent Messages

Always keep recent messages for context:

```python
compression_config = CompressionConfig(
    keep_recent=10  # Always keep 10 most recent
)
```

### 4. Use Custom Prompts

Use custom prompts for better summaries:

```python
compression_config = CompressionConfig(
    summary_prompt_template=(
        "Your custom prompt here:\n\n{messages}"
    )
)
```

### 5. Monitor Compression Performance

Monitor compression performance:

```python
# Check compression stats
stats = await context_engine.get_compression_stats("session-123")
print(f"Compressions: {stats['count']}")
print(f"Average reduction: {stats['avg_reduction']}%")
```

### 6. Test Compression Quality

Test compression quality for your use case:

```python
# Test compression
original_messages = await context_engine.get_conversation_history("session-123")
compressed = await context_engine.compress_conversation("session-123")
compressed_messages = await context_engine.get_conversation_history("session-123")

print(f"Original: {len(original_messages)} messages")
print(f"Compressed: {len(compressed_messages)} messages")
print(f"Reduction: {(1 - len(compressed_messages)/len(original_messages))*100}%")
```

## Summary

Compression strategies provide:
- ✅ Multiple strategies (truncate, summarize, semantic, hybrid)
- ✅ Automatic compression triggers
- ✅ Custom compression prompts
- ✅ Configurable thresholds
- ✅ Quality preservation options

**Strategy Selection Guide**:
- **truncate**: Fast, cheap, recent messages only
- **summarize**: Quality preservation, LLM-based
- **semantic**: Duplicate removal, embedding-based
- **hybrid**: Maximum compression, multiple strategies

For more details, see:
- [ContextEngine Integration](./CONTEXTENGINE_INTEGRATION.md)
- [Agent Integration Guide](./AGENT_INTEGRATION.md)

