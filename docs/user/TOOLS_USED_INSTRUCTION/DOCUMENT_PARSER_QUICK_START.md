# Document Parser Tool - Quick Start Guide

## 🚀 Ready to Use

The document parsing component is now fully ready to use out of the box! Developers can directly use these tools in their projects.

## 📁 New Directory Structure

```
aiecs/tools/
├── docs/                          # Document processing tools directory 
│   ├── __init__.py                # Document tools module initialization
│   ├── document_parser_tool.py    # Core document parser tool
│   └── ai_document_orchestrator.py # AI intelligent orchestrator
├── task_tools/                    # Other task tools
│   ├── chart_tool.py
│   ├── scraper_tool.py
│   └── ...
└── __init__.py                    # Main tool registration
```

## 🔧 Installation and Configuration

### 1. Basic Installation
```bash
# Project already includes all necessary dependencies
pip install -e .

# Or install from PyPI
pip install aiecs
```

### 2. Environment Variable Configuration (Optional)
```bash
# Document parser configuration
export DOC_PARSER_enable_cloud_storage=true
export DOC_PARSER_gcs_bucket_name=your-bucket-name
export DOC_PARSER_gcs_project_id=your-project-id

# AI orchestrator configuration
export AI_DOC_ORCHESTRATOR_default_ai_provider=openai
export AI_DOC_ORCHESTRATOR_max_chunk_size=4000
```

## 💻 Basic Usage

### 1. Import Tools (New Path)
```python
# Import document processing tools from docs directory
from aiecs.tools.docs.document_parser_tool import DocumentParserTool
from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator

# Or use lazy loading
from aiecs.tools.docs import document_parser_tool, ai_document_orchestrator
```

### 2. Quick Start Example
```python
#!/usr/bin/env python3
"""
Document processing quick start example
"""

def quick_start_example():
    # 1. Initialize tools
    from aiecs.tools.docs.document_parser_tool import DocumentParserTool
    from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator
    
    parser = DocumentParserTool()
    orchestrator = AIDocumentOrchestrator()
    
    # 2. Process local document
    result = orchestrator.process_document(
        source="test_document.txt",
        processing_mode="summarize"
    )
    
    print("AI Summary:", result['ai_result']['ai_response'])

if __name__ == "__main__":
    quick_start_example()
```

### 3. Supported Document Sources
```python
# Support multiple document sources
sources = [
    "/path/to/local/file.pdf",                    # Local file
    "https://example.com/document.pdf",           # URL link
    "gs://bucket/document.pdf",                   # Google Cloud Storage
    "s3://bucket/document.pdf",                   # AWS S3
    "azure://container/document.pdf",             # Azure Blob
    "doc_123456789",                              # Storage ID
]

for source in sources:
    try:
        result = parser.parse_document(source=source)
        print(f"✓ Successfully parsed: {source}")
    except Exception as e:
        print(f"✗ Parsing failed: {source} - {e}")
```

## 🌐 Cloud Storage Configuration

### Google Cloud Storage
```python
config = {
    "enable_cloud_storage": True,
    "gcs_bucket_name": "my-documents",
    "gcs_project_id": "my-project-id"
}

parser = DocumentParserTool(config)
```

### Process Cloud Storage Documents
```python
# Directly process documents in cloud storage
cloud_doc = "gs://my-bucket/reports/annual_report.pdf"

result = orchestrator.process_document(
    source=cloud_doc,
    processing_mode="extract_info",
    processing_params={
        "extraction_criteria": "Financial data, key metrics, conclusions"
    }
)
```

## 🎯 Real-World Application Examples

### 1. Batch Process Documents
```python
def batch_process_documents():
    orchestrator = AIDocumentOrchestrator()
    
    documents = [
        "gs://docs/report1.pdf",
        "gs://docs/report2.pdf", 
        "s3://legal/contract.docx"
    ]
    
    result = orchestrator.batch_process_documents(
        sources=documents,
        processing_mode="analyze",
        max_concurrent=3
    )
    
    print(f"Successfully processed: {result['successful_documents']}")
    return result

# Run batch processing
batch_result = batch_process_documents()
```

### 2. Custom AI Analysis
```python
def custom_document_analysis():
    orchestrator = AIDocumentOrchestrator()
    
    # Create custom analyzer
    legal_analyzer = orchestrator.create_custom_processor(
        system_prompt="You are a professional legal document analyst",
        user_prompt_template="Analyze the following legal document and extract key clauses: {content}"
    )
    
    # Use custom analyzer
    result = legal_analyzer("contract.pdf")
    return result

# Run custom analysis
analysis_result = custom_document_analysis()
```

### 3. Real-time Document Processing
```python
async def realtime_document_processing():
    orchestrator = AIDocumentOrchestrator()
    
    # Asynchronously process multiple documents
    tasks = [
        orchestrator.process_document_async(
            source=doc,
            processing_mode="summarize"
        )
        for doc in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    ]
    
    results = await asyncio.gather(*tasks)
    return results

# Run async processing
import asyncio
async_results = asyncio.run(realtime_document_processing())
```

## 🔍 Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors
```python
# Wrong old path
# from aiecs.tools.task_tools.document_parser_tool import DocumentParserTool

# Correct new path
from aiecs.tools.docs.document_parser_tool import DocumentParserTool
```

#### 2. Permission Issues
```bash
# If encountering temporary file permission issues
export TMPDIR=/tmp/aiecs_temp
mkdir -p $TMPDIR
chmod 755 $TMPDIR
```

#### 3. Cloud Storage Configuration
```python
# Ensure cloud storage configuration is correct
config = {
    "enable_cloud_storage": True,
    "gcs_bucket_name": "your-bucket",
    "gcs_project_id": "your-project"
}

# Test configuration
parser = DocumentParserTool(config)
print("Cloud storage configuration:", parser.settings.enable_cloud_storage)
```

## 📊 Feature Checklist

Run the following code to check if all features are working:

```python
def system_check():
    """System feature check"""
    
    print("🔍 AIECS Document Processing System Check")
    print("=" * 40)
    
    # 1. Import test
    try:
        from aiecs.tools.docs.document_parser_tool import DocumentParserTool
        from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator
        print("✓ Module import successful")
    except ImportError as e:
        print(f"✗ Module import failed: {e}")
        return
    
    # 2. Initialization test
    try:
        parser = DocumentParserTool()
        orchestrator = AIDocumentOrchestrator()
        print("✓ Tool initialization successful")
    except Exception as e:
        print(f"✗ Tool initialization failed: {e}")
        return
    
    # 3. Configuration test
    print(f"✓ Cloud storage support: {parser.settings.enable_cloud_storage}")
    print(f"✓ Temporary directory: {parser.settings.temp_dir}")
    print(f"✓ AI provider: {orchestrator.settings.default_ai_provider}")
    
    # 4. Feature test
    test_sources = [
        ("Local path", "/tmp/test.txt"),
        ("HTTP URL", "https://example.com/file.pdf"),
        ("Cloud storage", "gs://bucket/file.pdf"),
        ("Storage ID", "doc_123456")
    ]
    
    for name, source in test_sources:
        is_supported = (
            not parser._is_url(source) or
            parser._is_cloud_storage_path(source) or
            parser._is_storage_id(source)
        )
        status = "✓" if is_supported else "✗"
        print(f"{status} {name} support: {source}")
    
    print("\n🎉 System check completed!")

# Run system check
system_check()
```

## 🚀 Production Deployment Recommendations

### 1. Performance Configuration
```python
# Recommended production environment configuration
production_config = {
    "max_file_size": 100 * 1024 * 1024,  # 100MB
    "timeout": 120,                       # 2 minute timeout
    "max_concurrent_requests": 10,        # Concurrent request limit
    "enable_cloud_storage": True,         # Enable cloud storage
    "max_chunk_size": 8000               # AI processing chunk size
}
```

### 2. Error Handling
```python
def robust_document_processing(source):
    """Robust document processing"""
    try:
        orchestrator = AIDocumentOrchestrator()
        result = orchestrator.process_document(
            source=source,
            processing_mode="summarize"
        )
        return {"status": "success", "result": result}
    
    except Exception as e:
        logger.error(f"Document processing failed: {source} - {e}")
        return {"status": "error", "error": str(e)}
```

### 3. Monitoring and Logging
```python
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable debug logging for specific modules
logging.getLogger('aiecs.tools.docs').setLevel(logging.DEBUG)
```

## 📚 More Resources

- Complete API Documentation: `docs/TOOLS_USED_INSTRUCTION/DOCUMENT_PARSER_TOOL.md`
- Example Code: `examples/document_processing_example.py`
- Cloud Storage Examples: `examples/cloud_storage_document_example.py`
- Tool Architecture Guide: `docs/TOOLS_USED_INSTRUCTION/TOOL_SPECIAL_SPECIAL_INSTRUCTIONS.md`

## 🎯 Summary

The document parsing component now:

✅ **Ready to Use** - Can be directly used in projects  
✅ **Clear Structure** - Document tools independently in `docs` directory  
✅ **Complete Features** - Supports multiple document sources and AI processing modes  
✅ **High Performance** - Async processing, intelligent caching, concurrency control  
✅ **Easy to Extend** - Supports custom processing workflows and AI providers  

Developers can now directly use this modern document parsing component to build their own AI document processing applications!
