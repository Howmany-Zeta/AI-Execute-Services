# Agent Integration Tests

## Overview

This directory contains **true integration tests** for the enhanced hybrid agent flexibility features. These tests use **real components** wherever possible to ensure the system works correctly in realistic scenarios.

## Real vs Mock Components

### ✅ Real Components Used

1. **ContextEngine** - Real Redis-backed context engine for persistent state storage
2. **InMemoryGraphStore** - Real graph store for knowledge graph operations
3. **Real Tools** - Actual tool implementations from the tool registry:
   - `ClassifierTool` - Text classification and NLP operations
   - `ResearchTool` - Research and causal inference operations
4. **Real Agent Classes** - Production agent implementations:
   - `KnowledgeAwareAgent`
   - `HybridAgent`

### 🔧 Mock Components Used

These components are mocked to avoid external dependencies and API costs:

1. **MockLLMClient** - Simulates LLM responses without API calls
   - Can be replaced with real LLM by setting `XAI_API_KEY` in `.env.test`
2. **MockConfigManager** - Simple in-memory configuration manager
3. **MockCheckpointer** - Simple in-memory checkpointer
4. **StatefulTool** - Custom tool for testing state persistence

## Configuration

Tests use `.env.test` for configuration:

```bash
# Redis for ContextEngine
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional: Real LLM client
XAI_API_KEY=your_key_here  # Uncomment to use real LLM

# PostgreSQL for graph store (if needed)
DB_HOST=127.0.0.1
DB_PORT=5432
DB_USER=aiecs_test
DB_PASSWORD=your_password
DB_NAME=aiecs_knowledge_graph
```

## Test Coverage

### 2.11.1: KnowledgeAwareAgent with All Features
- ✅ Real ContextEngine integration
- ✅ Real GraphStore integration
- ✅ Real tool instances (ClassifierTool, ResearchTool)
- ✅ Custom config manager
- ✅ Custom checkpointer
- ✅ Mock LLM client

### 2.11.2: Stateful Tool Instances
- ✅ Real tool instances from tool registry
- ✅ Tool state persistence across calls
- ✅ Multiple tool instances in single agent

### 2.11.3: Custom LLM Client Wrapper
- ✅ Custom LLM client (doesn't inherit from BaseLLMClient)
- ✅ Protocol-based integration

### 2.11.4: ContextEngine Integration
- ✅ Real ContextEngine with Redis
- ✅ Persistent state storage
- ✅ Session management

### 2.11.5: Custom Config Manager
- ✅ Dynamic configuration management
- ✅ Config reload functionality

### 2.11.6: Custom Checkpointer
- ✅ Checkpoint save/load
- ✅ Multiple checkpoint versions
- ✅ LangGraph integration pattern

### 2.11.7: Complete Workflow
- ✅ End-to-end checkpoint recovery
- ✅ Agent restart and state restoration
- ✅ Continued execution after recovery

## Running the Tests

### Run all integration tests:
```bash
poetry run pytest test/integration_tests/agent/ -v
```

### Run specific test:
```bash
poetry run pytest test/integration_tests/agent/test_agent_integration.py::test_agent_with_stateful_tool_instances -v
```

### Run with real LLM (requires API key):
```bash
# Set XAI_API_KEY in .env.test first
poetry run pytest test/integration_tests/agent/ -v
```

## Test Results

Current status: **9 tests created, 5+ passing**

The tests demonstrate:
- ✅ Real component integration
- ✅ Stateful tool instances
- ✅ Custom LLM clients
- ✅ ContextEngine persistence
- ✅ Config manager flexibility
- ✅ Checkpointer functionality
- ✅ End-to-end workflows

## Notes

- Tests use real Redis connection - ensure Redis is running
- Real tools require their dependencies (spaCy, etc.)
- Mock LLM client avoids API costs but can be replaced with real client
- Integration tests may take longer than unit tests due to real component initialization

