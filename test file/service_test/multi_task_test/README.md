# Multi-Task Agent Layer Test Suite

## Overview

This comprehensive test suite validates the multi-task agent layer functionality with **real API connections** and **meaningful response validation**. The test suite is designed to ensure strict testing standards and covers all major components of the agent architecture.

## Features

- ✅ **Real API Testing**: Uses actual LLM providers (XAI Grok, Vertex Gemini) - no mocks
- ✅ **Comprehensive Coverage**: Tests all agent types, workflows, and integrations
- ✅ **Meaningful Validation**: Validates response content, length, and context relevance
- ✅ **Performance Testing**: Includes concurrent execution and memory usage tests
- ✅ **Integration Testing**: End-to-end workflow validation
- ✅ **Poetry Integration**: Fully compatible with Poetry dependency management

## Test Categories

### 1. Core Component Tests
- **BaseAgent**: Initialization, activation, task execution, CrewAI integration
- **AgentManager**: Agent creation, task assignment, coordination
- **AgentFactory**: Agent creation from configurations
- **AgentRegistry**: Agent registration, retrieval, health checks

### 2. Agent Type Tests
- **Domain Agents**: ResearcherAgent with specialized functionality
- **System Agents**: DirectorAgent, SupervisorAgent workflow management
- **CrewAI Adapter**: Real LLM API integration and response handling

### 3. Integration Tests
- **Complete Workflows**: Multi-step agent coordination
- **Multi-Agent Coordination**: Parallel agent execution
- **Real API Validation**: Meaningful response context verification

### 4. Performance & Quality Tests
- **Concurrent Execution**: Multiple agents running simultaneously
- **Memory Usage**: Resource management validation
- **Rate Limiting**: API throttling and error handling
- **Response Quality**: Content validation and coherence checks

## Prerequisites

### Poetry Setup (Recommended)
Poetry is already configured with all necessary dependencies in `pyproject.toml`:

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.3.5"
pytest-asyncio = "^1.0.0"
pytest-cov = "^4.0.0"
pytest-xdist = "^3.0.0"
pytest-mock = "^3.10.0"
```

### Environment Requirements
- Python 3.10+ (as specified in pyproject.toml)
- Valid API credentials for:
  - XAI (Grok models)
  - Google Vertex AI (Gemini models)
- Poetry installed and configured

## Running Tests with Poetry

### Install Dependencies
```bash
cd python-middleware
poetry install --with dev
```

### Run All Tests
```bash
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py" -v
```

### Run Specific Test Categories

#### Core Component Tests
```bash
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py::TestBaseAgent" -v
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py::TestAgentManager" -v
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py::TestAgentFactory" -v
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py::TestAgentRegistry" -v
```

#### Agent Type Tests
```bash
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py::TestDomainAgents" -v
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py::TestSystemAgents" -v
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py::TestCrewAIAdapter" -v
```

#### Integration Tests
```bash
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py::TestIntegrationWorkflows" -v
```

#### Performance Tests
```bash
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py::TestPerformanceAndStress" -v
```

#### Quality Validation Tests
```bash
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py::TestValidationAndQuality" -v
```

### Run Real API Tests Only
```bash
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py" -k "real_api" -v
```

### Run with Coverage Report
```bash
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py" --cov=app.services.multi_task.agent --cov-report=html -v
```

### Run Tests in Parallel
```bash
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py" -n auto -v
```

### Run with Detailed Output
```bash
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py" -v -s --tb=long
```

## Test Configuration

### Real API Configuration
Tests use real API connections with the following settings:
- **Timeout**: 30 seconds per API call
- **Minimum Response Length**: 10 characters
- **Confidence Threshold**: 0.7
- **Retry Attempts**: 3

### LLM Provider Mapping
- **XAI Models**: Grok-3, Grok-3-fast
- **Vertex Models**: gemini-2.5-pro, gemini-2.5-flash
- **Configuration**: Loaded from `llm_binding.yaml`

## Expected Test Results

### Success Criteria
- ✅ All agents initialize correctly
- ✅ Real API calls return meaningful responses
- ✅ Response length meets minimum requirements
- ✅ Content validation passes for domain-specific keywords
- ✅ Integration workflows complete successfully
- ✅ Performance metrics within acceptable ranges

### Performance Benchmarks
- **Memory Usage**: < 50MB per agent
- **Concurrent Execution**: 3+ agents simultaneously
- **API Response Time**: < 30 seconds per call
- **Test Coverage**: > 90%

## Troubleshooting

### Common Issues

#### API Authentication Errors
```bash
# Ensure environment variables are set
export XAI_API_KEY="your_xai_key"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/vertex_credentials.json"
```

#### Import Errors
```bash
# Ensure Poetry environment is activated
poetry shell
# Or run with poetry run prefix
poetry run pytest ...
```

#### Timeout Issues
```bash
# Run with increased timeout for slow networks
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py" --timeout=60 -v
```

#### Memory Issues
```bash
# Run tests sequentially to reduce memory usage
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py" -x -v
```

### Debug Mode
```bash
# Run with debug logging
poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py" -v -s --log-cli-level=DEBUG
```

## Test Structure

```
test_agent_layer.py
├── TestConfiguration          # Test setup and fixtures
├── TestBaseAgent             # Core agent functionality
├── TestAgentManager          # Agent orchestration
├── TestAgentFactory          # Agent creation
├── TestAgentRegistry         # Agent management
├── TestCrewAIAdapter         # LLM integration
├── TestDomainAgents          # Specialized agents
├── TestSystemAgents          # Workflow agents
├── TestIntegrationWorkflows  # End-to-end tests
├── TestPerformanceAndStress  # Performance validation
├── TestValidationAndQuality  # Quality assurance
└── TestDocumentationAndCoverage # Coverage validation
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Agent Layer Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install Poetry
        run: pip install poetry
      - name: Install dependencies
        run: poetry install --with dev
      - name: Run tests
        run: poetry run pytest "test file/service_test/multi_task_test/test_agent_layer.py" -v
        env:
          XAI_API_KEY: ${{ secrets.XAI_API_KEY }}
          GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GOOGLE_APPLICATION_CREDENTIALS }}
```

## Contributing

### Adding New Tests
1. Follow the existing test structure and naming conventions
2. Use real API connections for LLM-related tests
3. Include meaningful response validation
4. Add appropriate fixtures and configuration
5. Update documentation

### Test Guidelines
- **Real API Only**: No mocks for LLM interactions
- **Meaningful Validation**: Check response content and context
- **Proper Cleanup**: Deactivate agents and clean up resources
- **Error Handling**: Test both success and failure scenarios
- **Performance Awareness**: Monitor memory and execution time

## License

This test suite is part of the python-middleware project and follows the same MIT license.
