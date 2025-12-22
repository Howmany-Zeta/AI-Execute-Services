# Document Processing Tools Testing

This directory contains comprehensive tests for the document processing tools in the AIECS system.

## Test Structure

```
test/
├── conftest_docs.py                    # Test configuration and fixtures
├── test_document_parser_tool.py        # DocumentParserTool tests
├── test_ai_document_orchestrator.py    # AIDocumentOrchestrator tests
├── pytest.ini                         # Pytest configuration
├── run_docs_tests.py                   # Test runner script
├── data/                              # Test data directory
│   ├── sample_documents.py            # Sample document generator
│   ├── sample.txt                     # Sample text document
│   ├── sample.md                      # Sample markdown document
│   ├── sample.json                    # Sample JSON document
│   ├── sample.csv                     # Sample CSV document
│   ├── sample.html                    # Sample HTML document
│   ├── sample.xml                     # Sample XML document
│   ├── sample.rtf                     # Sample RTF document
│   └── sample.large                   # Large document for testing
└── README_DOCS_TESTING.md             # This file
```

## Running Tests

### Basic Test Execution

```bash
# Run all document processing tests
poetry run python test/run_docs_tests.py

# Run specific test file
poetry run python test/run_docs_tests.py --file test_document_parser_tool.py

# Run with coverage report
poetry run python test/run_docs_tests.py

# Run without coverage (faster)
poetry run python test/run_docs_tests.py --no-coverage
```

### Advanced Test Options

```bash
# Skip slow tests
poetry run python test/run_docs_tests.py --fast

# Run only AI-related tests
poetry run python test/run_docs_tests.py --ai-tests

# Run with specific markers
poetry run python test/run_docs_tests.py --markers "not slow and not ai_required"

# Quiet mode (less verbose output)
poetry run python test/run_docs_tests.py --quiet
```

### Direct Pytest Usage

```bash
# Run all tests with coverage
poetry run pytest test/test_document_parser_tool.py test/test_ai_document_orchestrator.py -v --cov=aiecs.tools.docs --cov-report=html

# Run specific test class
poetry run pytest test/test_document_parser_tool.py::TestDocumentParserTool -v

# Run specific test method
poetry run pytest test/test_document_parser_tool.py::TestDocumentParserTool::test_parse_txt_file -v

# Run with markers
poetry run pytest -m "not slow" -v
```

## Test Coverage

The tests are designed to achieve **85%+ coverage** for both components:

- **DocumentParserTool**: Tests all parsing strategies, output formats, error handling, and edge cases
- **AIDocumentOrchestrator**: Tests all processing modes, AI provider integration, and workflow orchestration

### Coverage Reports

After running tests, coverage reports are generated in:
- **Terminal**: Shows missing lines
- **HTML**: `htmlcov/index.html` - Interactive coverage report
- **XML**: `coverage.xml` - For CI/CD integration

## Test Categories

### DocumentParserTool Tests

1. **Initialization Tests**
   - Configuration validation
   - Default settings
   - Custom settings

2. **Document Type Detection**
   - File extension detection
   - Content-based detection
   - MIME type detection

3. **Parsing Tests**
   - Text files (TXT)
   - Markdown files (MD)
   - JSON files
   - CSV files
   - HTML files
   - XML files
   - RTF files

4. **Strategy Tests**
   - Text-only parsing
   - Structured parsing
   - Full content parsing
   - Metadata-only parsing

5. **Output Format Tests**
   - Text output
   - JSON output
   - Markdown output
   - HTML output

6. **Error Handling**
   - Non-existent files
   - Unsupported formats
   - Corrupted files
   - Network errors

7. **Performance Tests**
   - Large file handling
   - Concurrent parsing
   - Memory usage

### AIDocumentOrchestrator Tests

1. **Initialization Tests**
   - Configuration validation
   - AI provider setup
   - Document parser integration

2. **Processing Mode Tests**
   - Summarization
   - Information extraction
   - Analysis
   - Translation
   - Classification
   - Question answering
   - Custom processing

3. **AI Provider Tests**
   - OpenAI integration
   - Vertex AI integration
   - XAI integration
   - Local provider

4. **Workflow Tests**
   - Document chunking
   - Concurrent processing
   - Result aggregation
   - Error recovery

5. **Integration Tests**
   - End-to-end workflows
   - Tool integration
   - API compatibility

## Test Data

The test suite includes comprehensive sample documents:

- **sample.txt**: Multi-paragraph text document
- **sample.md**: Markdown with headers, lists, tables, code blocks
- **sample.json**: Structured JSON with nested objects and arrays
- **sample.csv**: CSV with headers and multiple rows
- **sample.html**: HTML with styling, tables, and structure
- **sample.xml**: XML with nested elements and attributes
- **sample.rtf**: Rich text format document
- **sample.large**: Large document for performance testing

## Test Markers

Tests are categorized with markers for selective execution:

- `@pytest.mark.slow`: Tests that take longer to run
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.ai_required`: Tests requiring AI services
- `@pytest.mark.network`: Tests requiring network access
- `@pytest.mark.cloud`: Tests requiring cloud services

## Debugging Tests

### Enable Debug Logging

```bash
# Run with debug logging
poetry run pytest -v -s --log-cli-level=DEBUG

# Run specific test with debug output
poetry run pytest test/test_document_parser_tool.py::TestDocumentParserTool::test_parse_txt_file -v -s --log-cli-level=DEBUG
```

### Test Output Analysis

The tests include comprehensive logging to help debug issues:

- **INFO**: Test progress and results
- **DEBUG**: Detailed execution information
- **WARNING**: Non-critical issues
- **ERROR**: Test failures and errors

## Continuous Integration

The test suite is designed for CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run Document Processing Tests
  run: |
    poetry install
    poetry run python test/run_docs_tests.py
    poetry run pytest --cov=aiecs.tools.docs --cov-report=xml --junitxml=test-results.xml
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the project is properly installed with `poetry install`
2. **Permission Errors**: Check file permissions for test data
3. **Network Errors**: Some tests require network access for URL downloading
4. **AI Service Errors**: AI-related tests may fail without proper API keys

### Test Environment Setup

```bash
# Install dependencies
poetry install

# Set up test environment
export DOC_PARSER_TEMP_DIR=/tmp/test_doc_parser
export AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=2

# Run tests
poetry run python test/run_docs_tests.py
```

## Performance Benchmarks

The test suite includes performance benchmarks:

- **Document Parsing**: < 1 second for typical documents
- **Large File Processing**: < 10 seconds for 1MB documents
- **Concurrent Processing**: 5x speedup with 5 concurrent requests
- **Memory Usage**: < 100MB for typical test runs

## Contributing

When adding new tests:

1. Follow the existing test structure
2. Add appropriate markers for test categorization
3. Include comprehensive error handling tests
4. Update this README with new test descriptions
5. Ensure 85%+ coverage is maintained

## Test Results

Expected test results:
- **DocumentParserTool**: 25+ test methods
- **AIDocumentOrchestrator**: 20+ test methods
- **Total Coverage**: 85%+ for both components
- **Test Duration**: < 5 minutes for full suite
- **Success Rate**: 100% with proper environment setup



