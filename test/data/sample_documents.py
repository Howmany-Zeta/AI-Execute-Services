"""
Sample documents for testing document processing tools

This module provides various sample documents for testing:
- Text documents
- Markdown documents
- JSON documents
- CSV documents
- HTML documents
"""
import json
from pathlib import Path
from typing import Dict, Any

def create_sample_txt_content() -> str:
    """Create sample text content"""
    return """AI Document Processing System

This is a comprehensive document processing system that can handle various document types including PDF, DOCX, XLSX, PPTX, TXT, HTML, RTF, CSV, JSON, XML, and Markdown files.

Key Features:
- Automatic document type detection
- Content extraction and parsing
- AI-powered analysis and processing
- Support for multiple output formats
- Cloud storage integration
- Concurrent processing capabilities

The system is designed to be scalable, reliable, and easy to use. It provides a unified interface for document processing operations and integrates seamlessly with AI services for advanced content analysis.

Technical Specifications:
- Built with Python 3.10+
- Uses FastAPI for web services
- Supports async/await patterns
- Implements proper error handling
- Provides comprehensive logging
- Includes extensive test coverage

This document serves as a test case for the document processing system and should be parsed correctly by all supported parsers.
"""

def create_sample_markdown_content() -> str:
    """Create sample markdown content"""
    return """# AI Document Processing System

## Overview

This is a **comprehensive** document processing system that can handle various document types including:

- PDF documents
- Microsoft Office files (DOCX, XLSX, PPTX)
- Plain text files
- Web content (HTML)
- Rich text format (RTF)
- Data files (CSV, JSON, XML)
- Markdown documents

## Key Features

### Core Functionality
- **Automatic document type detection**
- Content extraction and parsing
- AI-powered analysis and processing
- Support for multiple output formats

### Advanced Features
- Cloud storage integration
- Concurrent processing capabilities
- Real-time processing
- Batch processing support

## Technical Architecture

The system is built with modern Python technologies:

```python
class DocumentProcessor:
    def __init__(self):
        self.parsers = {}
        self.ai_services = {}
    
    async def process_document(self, file_path: str):
        # Process document
        pass
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/parse` | POST | Parse a document |
| `/analyze` | POST | Analyze document content |
| `/summarize` | POST | Generate document summary |

## Configuration

The system can be configured using environment variables:

```bash
export DOC_PARSER_MAX_FILE_SIZE=52428800
export DOC_PARSER_TIMEOUT=30
export AI_DOC_ORCHESTRATOR_MAX_CHUNKS=10
```

## Testing

This document serves as a test case for the document processing system and should be parsed correctly by all supported parsers.

> **Note**: This is a sample document for testing purposes.
"""

def create_sample_json_content() -> Dict[str, Any]:
    """Create sample JSON content"""
    return {
        "title": "AI Document Processing System",
        "version": "1.0.0",
        "description": "A comprehensive document processing system with AI capabilities",
        "features": [
            "Automatic document type detection",
            "Content extraction and parsing",
            "AI-powered analysis",
            "Multiple output formats",
            "Cloud storage integration",
            "Concurrent processing"
        ],
        "supported_formats": {
            "documents": ["pdf", "docx", "xlsx", "pptx", "txt", "html", "rtf"],
            "data": ["csv", "json", "xml"],
            "markup": ["markdown", "html"]
        },
        "technical_specs": {
            "language": "Python 3.10+",
            "framework": "FastAPI",
            "async_support": True,
            "error_handling": True,
            "logging": True,
            "test_coverage": "85%+"
        },
        "api_endpoints": [
            {
                "path": "/parse",
                "method": "POST",
                "description": "Parse a document"
            },
            {
                "path": "/analyze",
                "method": "POST", 
                "description": "Analyze document content"
            },
            {
                "path": "/summarize",
                "method": "POST",
                "description": "Generate document summary"
            }
        ],
        "configuration": {
            "max_file_size": "50MB",
            "timeout": "30 seconds",
            "max_chunks": 10,
            "concurrent_requests": 5
        },
        "metadata": {
            "created": "2024-01-01",
            "author": "AIECS Team",
            "license": "MIT",
            "repository": "https://github.com/aiecs/document-processor"
        }
    }

def create_sample_csv_content() -> str:
    """Create sample CSV content"""
    return """Name,Age,Department,Role,Experience,Skills
John Smith,32,Engineering,Senior Developer,8,Python,JavaScript,React
Sarah Johnson,28,Design,UX Designer,5,UI/UX,Sketch,Figma
Michael Brown,35,Engineering,Tech Lead,10,Python,Java,Architecture
Emily Davis,26,Marketing,Marketing Specialist,3,Digital Marketing,SEO,Analytics
David Wilson,30,Engineering,DevOps Engineer,6,Docker,Kubernetes,AWS
Lisa Anderson,29,Design,Graphic Designer,4,Photoshop,Illustrator,Branding
Robert Taylor,33,Engineering,Backend Developer,7,Python,Django,PostgreSQL
Jennifer Martinez,27,Marketing,Content Manager,4,Content Strategy,SEO,Social Media
Christopher Lee,31,Engineering,Frontend Developer,6,React,Vue.js,TypeScript
Amanda White,25,Design,Product Designer,3,Product Design,User Research,Prototyping
"""

def create_sample_html_content() -> str:
    """Create sample HTML content"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Document Processing System</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        h2 { color: #666; }
        .feature { background-color: #f5f5f5; padding: 10px; margin: 10px 0; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>AI Document Processing System</h1>
    
    <h2>Overview</h2>
    <p>This is a <strong>comprehensive</strong> document processing system that can handle various document types including PDF, DOCX, XLSX, PPTX, TXT, HTML, RTF, CSV, JSON, XML, and Markdown files.</p>
    
    <h2>Key Features</h2>
    <div class="feature">
        <h3>Automatic Document Type Detection</h3>
        <p>The system automatically detects document types from file extensions and content analysis.</p>
    </div>
    
    <div class="feature">
        <h3>Content Extraction and Parsing</h3>
        <p>Extract text, metadata, and structured data from various document formats.</p>
    </div>
    
    <div class="feature">
        <h3>AI-Powered Analysis</h3>
        <p>Leverage AI services for document summarization, classification, and analysis.</p>
    </div>
    
    <h2>Supported Formats</h2>
    <table>
        <tr>
            <th>Category</th>
            <th>Formats</th>
            <th>Description</th>
        </tr>
        <tr>
            <td>Documents</td>
            <td>PDF, DOCX, XLSX, PPTX, TXT, HTML, RTF</td>
            <td>Standard document formats</td>
        </tr>
        <tr>
            <td>Data</td>
            <td>CSV, JSON, XML</td>
            <td>Structured data formats</td>
        </tr>
        <tr>
            <td>Markup</td>
            <td>Markdown, HTML</td>
            <td>Markup languages</td>
        </tr>
    </table>
    
    <h2>Technical Specifications</h2>
    <ul>
        <li><strong>Language:</strong> Python 3.10+</li>
        <li><strong>Framework:</strong> FastAPI</li>
        <li><strong>Async Support:</strong> Yes</li>
        <li><strong>Error Handling:</strong> Comprehensive</li>
        <li><strong>Logging:</strong> Structured logging</li>
        <li><strong>Test Coverage:</strong> 85%+</li>
    </ul>
    
    <h2>API Endpoints</h2>
    <p>The system provides RESTful API endpoints for document processing operations.</p>
    
    <h2>Configuration</h2>
    <p>System behavior can be configured using environment variables and configuration files.</p>
    
    <footer>
        <p><em>This document serves as a test case for the document processing system.</em></p>
    </footer>
</body>
</html>"""

def create_sample_xml_content() -> str:
    """Create sample XML content"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<document>
    <metadata>
        <title>AI Document Processing System</title>
        <version>1.0.0</version>
        <author>AIECS Team</author>
        <created>2024-01-01</created>
        <description>A comprehensive document processing system with AI capabilities</description>
    </metadata>
    
    <features>
        <feature>
            <name>Automatic Document Type Detection</name>
            <description>Automatically detect document types from file extensions and content</description>
            <priority>high</priority>
        </feature>
        <feature>
            <name>Content Extraction and Parsing</name>
            <description>Extract text, metadata, and structured data from various formats</description>
            <priority>high</priority>
        </feature>
        <feature>
            <name>AI-Powered Analysis</name>
            <description>Leverage AI services for document analysis and processing</description>
            <priority>medium</priority>
        </feature>
        <feature>
            <name>Multiple Output Formats</name>
            <description>Support for various output formats including JSON, XML, and text</description>
            <priority>medium</priority>
        </feature>
    </features>
    
    <supported_formats>
        <category name="documents">
            <format>PDF</format>
            <format>DOCX</format>
            <format>XLSX</format>
            <format>PPTX</format>
            <format>TXT</format>
            <format>HTML</format>
            <format>RTF</format>
        </category>
        <category name="data">
            <format>CSV</format>
            <format>JSON</format>
            <format>XML</format>
        </category>
        <category name="markup">
            <format>Markdown</format>
            <format>HTML</format>
        </category>
    </supported_formats>
    
    <technical_specs>
        <spec name="language">Python 3.10+</spec>
        <spec name="framework">FastAPI</spec>
        <spec name="async_support">true</spec>
        <spec name="error_handling">true</spec>
        <spec name="logging">true</spec>
        <spec name="test_coverage">85%+</spec>
    </technical_specs>
    
    <api_endpoints>
        <endpoint>
            <path>/parse</path>
            <method>POST</method>
            <description>Parse a document</description>
        </endpoint>
        <endpoint>
            <path>/analyze</path>
            <method>POST</method>
            <description>Analyze document content</description>
        </endpoint>
        <endpoint>
            <path>/summarize</path>
            <method>POST</method>
            <description>Generate document summary</description>
        </endpoint>
    </api_endpoints>
</document>"""

def create_sample_rtf_content() -> str:
    """Create sample RTF content"""
    return r"""{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}}
\f0\fs24 AI Document Processing System\par
\par
This is a \b comprehensive \b0 document processing system that can handle various document types including:\par
\par
\bullet PDF documents\par
\bullet Microsoft Office files (DOCX, XLSX, PPTX)\par
\bullet Plain text files\par
\bullet Web content (HTML)\par
\bullet Rich text format (RTF)\par
\bullet Data files (CSV, JSON, XML)\par
\bullet Markdown documents\par
\par
\b Key Features:\b0\par
\par
\bullet \b Automatic document type detection\b0\par
\bullet Content extraction and parsing\par
\bullet AI-powered analysis and processing\par
\bullet Support for multiple output formats\par
\bullet Cloud storage integration\par
\bullet Concurrent processing capabilities\par
\par
\b Technical Architecture:\b0\par
\par
The system is built with modern Python technologies and provides a unified interface for document processing operations.\par
\par
\b Configuration:\b0\par
\par
The system can be configured using environment variables and configuration files.\par
\par
\b Testing:\b0\par
\par
This document serves as a test case for the document processing system and should be parsed correctly by all supported parsers.\par
}"""

def create_large_document_content() -> str:
    """Create large document content for testing"""
    base_content = """This is a test paragraph for large document testing. It contains various elements including text, numbers, and special characters. The purpose is to test the system's ability to handle large documents efficiently.

Key points to consider:
- Document size handling
- Memory usage optimization
- Processing time efficiency
- Error handling for large files
- Chunking and streaming capabilities

Technical specifications:
- Maximum file size: 50MB
- Chunk size: 4000 characters
- Timeout: 30 seconds
- Concurrent processing: 5 requests

This content will be repeated multiple times to create a large document for testing purposes.
"""
    
    # Repeat content to create a large document
    return base_content * 1000  # Creates approximately 1MB of content

def get_sample_documents() -> Dict[str, str]:
    """Get all sample documents as a dictionary"""
    return {
        "txt": create_sample_txt_content(),
        "md": create_sample_markdown_content(),
        "json": json.dumps(create_sample_json_content(), indent=2),
        "csv": create_sample_csv_content(),
        "html": create_sample_html_content(),
        "xml": create_sample_xml_content(),
        "rtf": create_sample_rtf_content(),
        "large": create_large_document_content()
    }

if __name__ == "__main__":
    # Create sample files for testing
    data_dir = Path(__file__).parent
    documents = get_sample_documents()
    
    for ext, content in documents.items():
        file_path = data_dir / f"sample.{ext}"
        file_path.write_text(content, encoding="utf-8")
        print(f"Created {file_path}")
    
    print(f"\nCreated {len(documents)} sample documents in {data_dir}")
