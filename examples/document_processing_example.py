#!/usr/bin/env python3
"""
Document Processing Example - Modern AI-Powered Document Parser

This example demonstrates how to use the modern document parsing component
to parse various document types and process them with AI.

Features demonstrated:
1. Document type auto-detection
2. URL and local file parsing
3. AI-powered content analysis
4. Batch processing
5. Custom processing workflows
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_document_parser():
    """Initialize the document parser tool"""
    try:
        from aiecs.tools.docs.document_parser_tool import DocumentParserTool
        return DocumentParserTool()
    except ImportError:
        logger.error("DocumentParserTool not available. Please ensure it's properly installed.")
        return None

def setup_ai_orchestrator():
    """Initialize the AI document orchestrator"""
    try:
        from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator
        return AIDocumentOrchestrator()
    except ImportError:
        logger.error("AIDocumentOrchestrator not available. Please ensure it's properly installed.")
        return None

def example_1_document_type_detection():
    """Example 1: Document type detection"""
    print("\n=== Example 1: Document Type Detection ===")
    
    parser = setup_document_parser()
    if not parser:
        return
    
    # Test URLs and files
    test_sources = [
        "https://www.example.com/sample.pdf",
        "https://docs.google.com/document/sample",
        "/path/to/local/document.docx",
        "sample.xlsx",
        "README.md"
    ]
    
    for source in test_sources:
        try:
            result = parser.detect_document_type(source, download_sample=False)
            print(f"Source: {source}")
            print(f"  Detected Type: {result['detected_type']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Detection Methods: {result['detection_methods']}")
            print(f"  Is URL: {result['is_url']}")
            print()
        except Exception as e:
            print(f"Error detecting type for {source}: {e}")

def example_2_basic_document_parsing():
    """Example 2: Basic document parsing"""
    print("\n=== Example 2: Basic Document Parsing ===")
    
    parser = setup_document_parser()
    if not parser:
        return
    
    # Example with a hypothetical PDF URL
    test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    
    try:
        # Parse with different strategies
        strategies = ["text_only", "structured", "full_content"]
        
        for strategy in strategies:
            print(f"\nParsing with strategy: {strategy}")
            result = parser.parse_document(
                source=test_url,
                strategy=strategy,
                output_format="json",
                extract_metadata=True
            )
            
            print(f"Document Type: {result.get('document_type')}")
            print(f"Content Stats: {result.get('content_stats')}")
            print(f"Metadata Keys: {list(result.get('metadata', {}).keys())}")
            
            # Show content preview
            content = result.get('content', '')
            if isinstance(content, str):
                preview = content[:200] + "..." if len(content) > 200 else content
            else:
                preview = str(content)[:200] + "..."
            print(f"Content Preview: {preview}")
            
    except Exception as e:
        print(f"Error parsing document: {e}")

def example_3_ai_powered_analysis():
    """Example 3: AI-powered document analysis"""
    print("\n=== Example 3: AI-Powered Document Analysis ===")
    
    orchestrator = setup_ai_orchestrator()
    if not orchestrator:
        return
    
    # Example document (you can replace with actual URL or file path)
    test_document = "sample_document.txt"
    
    # Create a sample document for testing
    sample_content = """
    Artificial Intelligence in Document Processing
    
    Introduction:
    Artificial Intelligence (AI) has revolutionized how we process and analyze documents. 
    Modern AI systems can automatically extract information, summarize content, and 
    provide intelligent insights from various document formats.
    
    Key Benefits:
    1. Automated information extraction
    2. Intelligent content summarization
    3. Multi-language support
    4. High accuracy and speed
    
    Applications:
    - Legal document review
    - Medical record analysis
    - Financial report processing
    - Academic research assistance
    
    Conclusion:
    AI-powered document processing represents a significant advancement in information 
    management and analysis capabilities.
    """
    
    # Create sample file
    with open(test_document, 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    try:
        # Test different processing modes
        processing_modes = [
            ("summarize", {}),
            ("analyze", {}),
            ("extract_info", {"extraction_criteria": "key benefits and applications"}),
            ("classify", {"categories": "Technology, Business, Education, Medical"})
        ]
        
        for mode, params in processing_modes:
            print(f"\n--- Processing Mode: {mode} ---")
            
            result = orchestrator.process_document(
                source=test_document,
                processing_mode=mode,
                processing_params=params
            )
            
            print(f"Processing Mode: {result.get('processing_mode')}")
            print(f"AI Provider: {result.get('ai_provider')}")
            print(f"Document Type: {result.get('document_info', {}).get('type')}")
            
            ai_result = result.get('ai_result', {})
            ai_response = ai_result.get('ai_response', 'No response')
            preview = ai_response[:300] + "..." if len(ai_response) > 300 else ai_response
            print(f"AI Response Preview: {preview}")
            
            duration = result.get('processing_metadata', {}).get('processing_duration', 0)
            print(f"Processing Duration: {duration:.2f} seconds")
            
    except Exception as e:
        print(f"Error in AI processing: {e}")
    
    finally:
        # Cleanup
        try:
            Path(test_document).unlink()
        except:
            pass

def example_4_batch_processing():
    """Example 4: Batch document processing"""
    print("\n=== Example 4: Batch Document Processing ===")
    
    orchestrator = setup_ai_orchestrator()
    if not orchestrator:
        return
    
    # Create multiple sample documents
    sample_documents = []
    sample_contents = [
        "Technical Report: AI advances in 2024 have been remarkable...",
        "Business Analysis: Market trends show significant growth...",
        "Research Paper: Our study on machine learning reveals...",
        "User Manual: This guide explains how to use the new system..."
    ]
    
    for i, content in enumerate(sample_contents):
        filename = f"sample_doc_{i+1}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        sample_documents.append(filename)
    
    try:
        print(f"Processing {len(sample_documents)} documents...")
        
        result = orchestrator.batch_process_documents(
            sources=sample_documents,
            processing_mode="summarize",
            max_concurrent=2
        )
        
        print(f"Total Documents: {result.get('total_documents')}")
        print(f"Successful: {result.get('successful_documents')}")
        print(f"Failed: {result.get('failed_documents')}")
        print(f"Total Duration: {result.get('batch_metadata', {}).get('total_duration', 0):.2f} seconds")
        
        # Show results for each document
        for doc_result in result.get('results', []):
            source = doc_result.get('source')
            status = doc_result.get('status')
            print(f"\nDocument: {source} - Status: {status}")
            
            if status == "success":
                ai_response = doc_result.get('result', {}).get('ai_result', {}).get('ai_response', '')
                preview = ai_response[:150] + "..." if len(ai_response) > 150 else ai_response
                print(f"  Summary Preview: {preview}")
            else:
                error = doc_result.get('error', 'Unknown error')
                print(f"  Error: {error}")
                
    except Exception as e:
        print(f"Error in batch processing: {e}")
    
    finally:
        # Cleanup
        for doc in sample_documents:
            try:
                Path(doc).unlink()
            except:
                pass

def example_5_custom_analysis():
    """Example 5: Custom document analysis"""
    print("\n=== Example 5: Custom Document Analysis ===")
    
    orchestrator = setup_ai_orchestrator()
    if not orchestrator:
        return
    
    # Create a sample document
    test_document = "custom_analysis_sample.txt"
    sample_content = """
    Project Status Report - Q4 2024
    
    Executive Summary:
    The AI implementation project has made significant progress in Q4. 
    We have successfully deployed 3 major features and are on track 
    to meet our year-end objectives.
    
    Key Achievements:
    - Document processing system deployed (95% accuracy)
    - User interface redesigned (30% improvement in user satisfaction)
    - API integration completed (99.9% uptime)
    
    Challenges:
    - Budget constraints affected timeline
    - Staff training required more resources than expected
    
    Next Quarter Goals:
    - Launch beta testing program
    - Optimize performance metrics
    - Expand to international markets
    
    Budget Status: $150,000 spent of $200,000 allocated
    Timeline: 2 weeks ahead of schedule
    """
    
    with open(test_document, 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    try:
        # Custom analysis with specific prompt
        custom_prompt = """
        Analyze this project report and extract the following information:
        1. Project health status (Green/Yellow/Red)
        2. Key metrics and their values
        3. Risk factors identified
        4. Success indicators
        5. Budget utilization percentage
        
        Document content: {content}
        
        Provide a structured analysis with clear recommendations.
        """
        
        result = orchestrator.analyze_document(
            source=test_document,
            analysis_type="project_health_assessment",
            custom_prompt=custom_prompt
        )
        
        print(f"Analysis Type: {result.get('analysis_type')}")
        print(f"Document Type: {result.get('document_info', {}).get('type')}")
        
        analysis_result = result.get('analysis_result', 'No analysis available')
        print(f"\nCustom Analysis Result:")
        print(analysis_result)
        
        # Create a custom processor for reuse
        project_analyzer = orchestrator.create_custom_processor(
            system_prompt="You are a project management expert. Analyze project reports thoroughly.",
            user_prompt_template="Analyze this project report and provide insights: {content}"
        )
        
        print("\n--- Using Custom Processor ---")
        custom_result = project_analyzer(test_document)
        
        ai_response = custom_result.get('ai_result', {}).get('ai_response', 'No response')
        preview = ai_response[:300] + "..." if len(ai_response) > 300 else ai_response
        print(f"Custom Processor Result: {preview}")
        
    except Exception as e:
        print(f"Error in custom analysis: {e}")
    
    finally:
        # Cleanup
        try:
            Path(test_document).unlink()
        except:
            pass

async def example_6_async_processing():
    """Example 6: Asynchronous document processing"""
    print("\n=== Example 6: Asynchronous Document Processing ===")
    
    orchestrator = setup_ai_orchestrator()
    if not orchestrator:
        return
    
    # Create sample documents
    documents = []
    for i in range(3):
        filename = f"async_doc_{i+1}.txt"
        content = f"Document {i+1}: This is a sample document for async processing testing. " * 10
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        documents.append(filename)
    
    try:
        print("Starting async processing...")
        
        # Process multiple documents concurrently
        tasks = [
            orchestrator.process_document_async(
                source=doc,
                processing_mode="summarize"
            )
            for doc in documents
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            print(f"\nAsync Result {i+1}:")
            if isinstance(result, Exception):
                print(f"  Error: {result}")
            else:
                duration = result.get('processing_metadata', {}).get('processing_duration', 0)
                print(f"  Duration: {duration:.2f} seconds")
                print(f"  Status: Success")
                
                ai_response = result.get('ai_result', {}).get('ai_response', '')
                preview = ai_response[:150] + "..." if len(ai_response) > 150 else ai_response
                print(f"  Summary: {preview}")
                
    except Exception as e:
        print(f"Error in async processing: {e}")
    
    finally:
        # Cleanup
        for doc in documents:
            try:
                Path(doc).unlink()
            except:
                pass

def main():
    """Main function to run all examples"""
    print("Modern AI-Powered Document Processing Examples")
    print("=" * 50)
    
    try:
        # Run synchronous examples
        example_1_document_type_detection()
        example_2_basic_document_parsing()
        example_3_ai_powered_analysis()
        example_4_batch_processing()
        example_5_custom_analysis()
        
        # Run async example
        print("\nRunning async example...")
        asyncio.run(example_6_async_processing())
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user.")
    except Exception as e:
        print(f"\nError running examples: {e}")
        logger.exception("Exception in main:")

if __name__ == "__main__":
    main()
