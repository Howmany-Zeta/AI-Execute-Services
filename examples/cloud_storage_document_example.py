#!/usr/bin/env python3
"""
Cloud Storage Document Processing Example

This example demonstrates how to process documents stored in cloud storage
(Google Cloud Storage, AWS S3, Azure Blob, etc.) using the modern document
parsing component.

Workflow:
1. User uploads document to cloud storage
2. System receives storage path/ID
3. Document parser retrieves from cloud storage
4. AI processes the document content
5. Results are returned to user

Supported cloud storage formats:
- gs://bucket/path/file.pdf (Google Cloud Storage)
- s3://bucket/path/file.pdf (AWS S3)
- azure://container/path/file.pdf (Azure Blob Storage)
- cloud://path/file.pdf (Generic cloud storage)
- storage_id_12345 (Direct storage ID)
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_document_parser_with_cloud():
    """Initialize document parser with cloud storage support"""
    try:
        from aiecs.tools.docs.document_parser_tool import DocumentParserTool
        
        # Configure with cloud storage settings
        config = {
            "enable_cloud_storage": True,
            "gcs_bucket_name": "aiecs-documents",
            "gcs_project_id": "my-ai-project",
            "max_file_size": 100 * 1024 * 1024,  # 100MB
            "timeout": 60
        }
        
        return DocumentParserTool(config)
    except ImportError:
        logger.error("DocumentParserTool not available")
        return None

def setup_ai_orchestrator():
    """Initialize AI orchestrator"""
    try:
        from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator
        return AIDocumentOrchestrator()
    except ImportError:
        logger.error("AIDocumentOrchestrator not available")
        return None

def example_1_cloud_storage_path_detection():
    """Example 1: Detect different cloud storage path formats"""
    print("\n=== Example 1: Cloud Storage Path Detection ===")
    
    parser = setup_document_parser_with_cloud()
    if not parser:
        return
    
    # Test various cloud storage path formats
    test_sources = [
        "gs://my-bucket/documents/report.pdf",  # Google Cloud Storage
        "s3://my-bucket/files/presentation.pptx",  # AWS S3
        "azure://my-container/data/spreadsheet.xlsx",  # Azure Blob
        "cloud://shared/documents/contract.docx",  # Generic cloud
        "doc_123456789abcdef",  # Storage ID
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  # UUID storage ID
        "https://example.com/file.pdf",  # Regular URL
        "/local/path/file.txt"  # Local file
    ]
    
    for source in test_sources:
        is_cloud = parser._is_cloud_storage_path(source)
        is_storage_id = parser._is_storage_id(source)
        is_url = parser._is_url(source)
        
        print(f"Source: {source}")
        print(f"  Cloud Storage Path: {is_cloud}")
        print(f"  Storage ID: {is_storage_id}")
        print(f"  URL: {is_url}")
        
        if is_cloud or is_storage_id:
            storage_path = parser._parse_cloud_storage_path(source)
            print(f"  Parsed Storage Path: {storage_path}")
        print()

def example_2_mock_cloud_document_processing():
    """Example 2: Mock cloud document processing workflow"""
    print("\n=== Example 2: Mock Cloud Document Processing ===")
    
    parser = setup_document_parser_with_cloud()
    orchestrator = setup_ai_orchestrator()
    
    if not parser or not orchestrator:
        return
    
    # Mock cloud storage paths
    cloud_documents = [
        {
            "path": "gs://aiecs-docs/reports/quarterly_report_q4_2024.pdf",
            "description": "Q4 2024 Financial Report"
        },
        {
            "path": "s3://company-docs/contracts/vendor_agreement_2024.docx", 
            "description": "Vendor Agreement Contract"
        },
        {
            "path": "azure://legal-docs/policies/privacy_policy_v2.pdf",
            "description": "Privacy Policy Document"
        },
        {
            "path": "doc_abc123def456",
            "description": "Technical Specification (Storage ID)"
        }
    ]
    
    for doc_info in cloud_documents:
        cloud_path = doc_info["path"]
        description = doc_info["description"]
        
        print(f"\n--- Processing: {description} ---")
        print(f"Cloud Path: {cloud_path}")
        
        try:
            # In a real scenario, this would actually download from cloud storage
            # For demo purposes, we'll simulate the detection and parsing workflow
            
            # Step 1: Detect document type (without downloading)
            print("Step 1: Document Type Detection")
            detection_result = parser.detect_document_type(cloud_path, download_sample=False)
            print(f"  Detected Type: {detection_result['detected_type']}")
            print(f"  Confidence: {detection_result['confidence']:.2f}")
            print(f"  Is Cloud Storage: {parser._is_cloud_storage_path(cloud_path)}")
            
            # Step 2: Parse storage path
            print("Step 2: Storage Path Parsing")
            storage_key = parser._parse_cloud_storage_path(cloud_path)
            print(f"  Storage Key: {storage_key}")
            
            # Step 3: Simulate document processing workflow
            print("Step 3: Document Processing Simulation")
            print(f"  Would download from: {cloud_path}")
            print(f"  Would parse as: {detection_result['detected_type']}")
            print(f"  Would process with AI: summarize mode")
            
            # In real implementation, you would call:
            # result = orchestrator.process_document(
            #     source=cloud_path,
            #     processing_mode="summarize"
            # )
            
        except Exception as e:
            print(f"Error processing {cloud_path}: {e}")

def example_3_cloud_storage_metadata_extraction():
    """Example 3: Extract metadata from cloud storage paths"""
    print("\n=== Example 3: Cloud Storage Metadata Extraction ===")
    
    parser = setup_document_parser_with_cloud()
    if not parser:
        return
    
    cloud_paths = [
        "gs://docs/2024/reports/annual_report_2024.pdf",
        "s3://legal/contracts/service_agreement_v3.docx",
        "azure://media/presentations/product_launch_deck.pptx"
    ]
    
    for cloud_path in cloud_paths:
        print(f"\nCloud Path: {cloud_path}")
        
        # Extract metadata from path
        metadata = extract_metadata_from_cloud_path(cloud_path)
        
        for key, value in metadata.items():
            print(f"  {key}: {value}")

def extract_metadata_from_cloud_path(cloud_path: str) -> Dict[str, Any]:
    """Extract metadata from cloud storage path"""
    from urllib.parse import urlparse
    from pathlib import Path
    
    try:
        parsed = urlparse(cloud_path)
        file_path = Path(parsed.path)
        
        metadata = {
            "storage_provider": parsed.scheme.upper() if parsed.scheme else "Unknown",
            "bucket_or_container": parsed.netloc,
            "file_name": file_path.name,
            "file_extension": file_path.suffix,
            "directory_structure": str(file_path.parent),
            "full_storage_path": cloud_path
        }
        
        # Extract additional info from path structure
        path_parts = file_path.parts
        if len(path_parts) > 1:
            metadata["category"] = path_parts[1] if len(path_parts) > 1 else "root"
            metadata["subcategory"] = path_parts[2] if len(path_parts) > 2 else "none"
        
        # Infer document type from extension
        doc_type_map = {
            '.pdf': 'PDF Document',
            '.docx': 'Word Document',
            '.xlsx': 'Excel Spreadsheet',
            '.pptx': 'PowerPoint Presentation',
            '.txt': 'Text File',
            '.json': 'JSON Data',
            '.csv': 'CSV Data'
        }
        
        metadata["inferred_type"] = doc_type_map.get(file_path.suffix.lower(), "Unknown")
        
        return metadata
        
    except Exception as e:
        return {"error": f"Failed to extract metadata: {e}"}

def example_4_batch_cloud_processing():
    """Example 4: Batch processing of cloud documents"""
    print("\n=== Example 4: Batch Cloud Document Processing ===")
    
    orchestrator = setup_ai_orchestrator()
    if not orchestrator:
        return
    
    # Simulate a batch of cloud documents
    cloud_document_batch = [
        "gs://company-docs/reports/sales_report_jan.pdf",
        "gs://company-docs/reports/sales_report_feb.pdf", 
        "gs://company-docs/reports/sales_report_mar.pdf",
        "s3://analytics/data/customer_analysis.xlsx",
        "azure://research/papers/market_research_2024.docx"
    ]
    
    print(f"Processing batch of {len(cloud_document_batch)} cloud documents...")
    
    # Simulate batch processing workflow
    for i, cloud_path in enumerate(cloud_document_batch, 1):
        print(f"\n{i}. Processing: {Path(cloud_path).name}")
        print(f"   Source: {cloud_path}")
        print(f"   Status: Queued for processing")
        
        # Extract metadata
        metadata = extract_metadata_from_cloud_path(cloud_path)
        print(f"   Provider: {metadata.get('storage_provider')}")
        print(f"   Type: {metadata.get('inferred_type')}")
        
        # In real implementation:
        # result = await orchestrator.process_document_async(
        #     source=cloud_path,
        #     processing_mode="analyze"
        # )
    
    print(f"\nBatch processing simulation completed!")

def example_5_cloud_storage_configuration():
    """Example 5: Different cloud storage configurations"""
    print("\n=== Example 5: Cloud Storage Configuration ===")
    
    # Configuration for different cloud providers
    configs = [
        {
            "name": "Google Cloud Storage",
            "config": {
                "enable_cloud_storage": True,
                "gcs_bucket_name": "my-gcs-bucket",
                "gcs_project_id": "my-gcp-project",
                "gcs_location": "US"
            }
        },
        {
            "name": "AWS S3 (via compatible interface)",
            "config": {
                "enable_cloud_storage": True,
                "gcs_bucket_name": "my-s3-bucket",  # Using GCS interface
                "gcs_project_id": "aws-compat-project"
            }
        },
        {
            "name": "Local Storage Fallback",
            "config": {
                "enable_cloud_storage": False,
                "temp_dir": "./local_documents"
            }
        }
    ]
    
    for config_info in configs:
        print(f"\n--- {config_info['name']} Configuration ---")
        config = config_info['config']
        
        try:
            from aiecs.tools.docs.document_parser_tool import DocumentParserTool
            parser = DocumentParserTool(config)
            
            print("✓ Parser initialized successfully")
            print(f"  Cloud Storage Enabled: {config.get('enable_cloud_storage', False)}")
            print(f"  Bucket/Container: {config.get('gcs_bucket_name', 'N/A')}")
            print(f"  Project ID: {config.get('gcs_project_id', 'N/A')}")
            print(f"  Local Fallback: {parser.settings.temp_dir}")
            
        except Exception as e:
            print(f"✗ Configuration failed: {e}")

def example_6_storage_security_considerations():
    """Example 6: Security considerations for cloud storage"""
    print("\n=== Example 6: Storage Security Considerations ===")
    
    security_guidelines = [
        {
            "aspect": "Authentication",
            "description": "Use service accounts and IAM roles",
            "implementation": "Configure GCS credentials via service account JSON or IAM"
        },
        {
            "aspect": "Access Control",
            "description": "Implement least-privilege access",
            "implementation": "Grant only necessary bucket/object permissions"
        },
        {
            "aspect": "Encryption",
            "description": "Enable encryption at rest and in transit",
            "implementation": "Use Cloud KMS or customer-managed encryption keys"
        },
        {
            "aspect": "Audit Logging",
            "description": "Monitor all storage access",
            "implementation": "Enable Cloud Audit Logs for storage operations"
        },
        {
            "aspect": "Network Security",
            "description": "Use private networks when possible", 
            "implementation": "Configure VPC Service Controls or private endpoints"
        },
        {
            "aspect": "Data Validation",
            "description": "Validate file types and content",
            "implementation": "Check file signatures and scan for malware"
        }
    ]
    
    for guideline in security_guidelines:
        print(f"\n{guideline['aspect']}:")
        print(f"  Description: {guideline['description']}")
        print(f"  Implementation: {guideline['implementation']}")

async def example_7_async_cloud_processing():
    """Example 7: Asynchronous cloud document processing"""
    print("\n=== Example 7: Async Cloud Document Processing ===")
    
    orchestrator = setup_ai_orchestrator()
    if not orchestrator:
        return
    
    # Cloud documents for async processing
    cloud_docs = [
        "gs://legal/contracts/contract_001.pdf",
        "gs://legal/contracts/contract_002.pdf",
        "gs://legal/contracts/contract_003.pdf"
    ]
    
    print("Starting async cloud document processing...")
    
    # Simulate async processing
    async def process_cloud_document(doc_path: str):
        print(f"Processing: {Path(doc_path).name}")
        # Simulate processing time
        await asyncio.sleep(1)
        return {
            "source": doc_path,
            "status": "completed", 
            "summary": f"Mock summary for {Path(doc_path).name}"
        }
    
    # Process documents concurrently
    tasks = [process_cloud_document(doc) for doc in cloud_docs]
    results = await asyncio.gather(*tasks)
    
    print("\nProcessing Results:")
    for result in results:
        print(f"  {Path(result['source']).name}: {result['status']}")
        print(f"    Summary: {result['summary']}")

def main():
    """Main function to run all cloud storage examples"""
    print("Cloud Storage Document Processing Examples")
    print("=" * 55)
    
    try:
        # Run synchronous examples
        example_1_cloud_storage_path_detection()
        example_2_mock_cloud_document_processing()
        example_3_cloud_storage_metadata_extraction()
        example_4_batch_cloud_processing()
        example_5_cloud_storage_configuration()
        example_6_storage_security_considerations()
        
        # Run async example
        print("\nRunning async cloud processing example...")
        asyncio.run(example_7_async_cloud_processing())
        
        print("\n" + "=" * 55)
        print("All cloud storage examples completed!")
        
        # Implementation notes
        print("\n📝 Implementation Notes:")
        print("1. This demo uses mock cloud storage operations")
        print("2. In production, configure actual cloud credentials")
        print("3. Ensure proper IAM permissions for storage access")
        print("4. Consider implementing retry logic for network failures")
        print("5. Monitor storage costs and access patterns")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user.")
    except Exception as e:
        print(f"\nError running examples: {e}")
        logger.exception("Exception in main:")

if __name__ == "__main__":
    main()
