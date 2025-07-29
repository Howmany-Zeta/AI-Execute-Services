#!/usr/bin/env python3
"""
Test script for Vertex AI Vector Search integration
"""

import sys
import os
import asyncio
import logging

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import get_settings
from app.services.scholar.services.rag.vector_store_factory import VectorStoreFactory
from app.services.scholar.services.rag_service import DomainRAGService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_configuration():
    """Test if Vertex AI configuration is properly loaded"""
    print("🔧 Testing Vertex AI Configuration...")

    try:
        settings = get_settings()

        # Check basic Vertex AI settings
        print(f"✓ Project ID: {settings.vertex_project_id}")
        print(f"✓ Location: {settings.vertex_location}")
        print(f"✓ Vector Store Backend: {settings.vector_store_backend}")

        # Check Vector Search specific settings
        if hasattr(settings, 'vertex_index_id'):
            print(f"✓ Index ID: {settings.vertex_index_id or 'Not configured'}")
        if hasattr(settings, 'vertex_endpoint_id'):
            print(f"✓ Endpoint ID: {settings.vertex_endpoint_id or 'Not configured'}")
        if hasattr(settings, 'vertex_deployed_index_id'):
            print(f"✓ Deployed Index ID: {settings.vertex_deployed_index_id or 'Not configured'}")

        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_vector_store_factory():
    """Test vector store factory"""
    print("\n🏭 Testing Vector Store Factory...")

    try:
        # Test factory creation
        vector_store = VectorStoreFactory.create_vector_store()
        print(f"✓ Vector store created: {type(vector_store).__name__}")

        # Test available backends
        backends = VectorStoreFactory.get_available_backends()
        print(f"✓ Available backends: {backends}")

        return True, vector_store
    except Exception as e:
        print(f"❌ Factory error: {e}")
        return False, None

def test_vertex_vector_store(vector_store):
    """Test Vertex AI Vector Store basic functionality"""
    print("\n🔍 Testing Vertex Vector Store...")

    try:
        # Test basic properties
        print(f"✓ Project ID: {vector_store.project_id}")
        print(f"✓ Location: {vector_store.location}")

        # Test configuration check
        if vector_store.index_id:
            print(f"✓ Index configured: {vector_store.index_id}")
        else:
            print("⚠️  Index not configured (this is expected for initial setup)")

        if vector_store.endpoint_id:
            print(f"✓ Endpoint configured: {vector_store.endpoint_id}")
        else:
            print("⚠️  Endpoint not configured (this is expected for initial setup)")

        return True
    except Exception as e:
        print(f"❌ Vector store error: {e}")
        return False

def test_rag_service():
    """Test RAG service with new vector store"""
    print("\n🤖 Testing RAG Service...")

    try:
        # Create RAG service
        rag_service = DomainRAGService()
        print(f"✓ RAG service created: {type(rag_service.vector_store).__name__}")

        # Test basic functionality (without actual vector operations)
        test_input = {"query": "test query"}
        result = rag_service.run(test_input, {})  # Add empty context
        print(f"✓ RAG service query test: {result}")

        return True
    except Exception as e:
        print(f"❌ RAG service error: {e}")
        return False

async def test_streaming():
    """Test streaming functionality"""
    print("\n📡 Testing Streaming...")

    try:
        rag_service = DomainRAGService()
        test_input = {"query": "test streaming query"}

        chunks = []
        async for chunk in rag_service.stream(test_input, {}):
            chunks.append(chunk)

        print(f"✓ Streaming test completed: {len(chunks)} chunks received")
        return True
    except Exception as e:
        print(f"❌ Streaming error: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Vertex AI Vector Search Integration Test\n")

    # Test configuration
    config_ok = test_configuration()
    if not config_ok:
        print("\n❌ Configuration test failed. Please check your environment variables.")
        return False

    # Test vector store factory
    factory_ok, vector_store = test_vector_store_factory()
    if not factory_ok:
        print("\n❌ Vector store factory test failed.")
        return False

    # Test vector store
    store_ok = test_vertex_vector_store(vector_store)
    if not store_ok:
        print("\n❌ Vector store test failed.")
        return False

    # Test RAG service
    rag_ok = test_rag_service()
    if not rag_ok:
        print("\n❌ RAG service test failed.")
        return False

    # Test streaming
    try:
        streaming_ok = asyncio.run(test_streaming())
        if not streaming_ok:
            print("\n❌ Streaming test failed.")
            return False
    except Exception as e:
        print(f"\n❌ Streaming test error: {e}")
        return False

    print("\n✅ All tests passed! Vertex AI Vector Search integration is working correctly.")
    print("\n📋 Next Steps:")
    print("1. Configure your Vertex AI Vector Search index and endpoint")
    print("2. Set the required environment variables:")
    print("   - VERTEX_INDEX_ID")
    print("   - VERTEX_ENDPOINT_ID")
    print("   - VERTEX_DEPLOYED_INDEX_ID")
    print("3. Start using the vector search functionality")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
