"""
LLM-related fixtures for testing.

Provides fixtures for:
- Mock LLM clients (OpenAI, Google, Vertex, xAI)
- Mock LLM responses
- LLM configuration
"""

import pytest
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock


class MockLLMResponse:
    """Mock LLM response for testing."""
    
    def __init__(self, content: str, model: str = "gpt-3.5-turbo", 
                 usage: Optional[Dict[str, int]] = None):
        self.content = content
        self.model = model
        self.usage = usage or {
            'prompt_tokens': 10,
            'completion_tokens': 20,
            'total_tokens': 30
        }
    
    def __str__(self):
        return self.content


class MockLLMClient:
    """Mock LLM client for testing without real API calls."""
    
    def __init__(self, model: str = "gpt-3.5-turbo", 
                 responses: Optional[List[str]] = None):
        self.model = model
        self.responses = responses or ["Mock response from LLM"]
        self.call_count = 0
        self.call_history = []
    
    async def achat(self, messages: List[Dict[str, str]], **kwargs) -> MockLLMResponse:
        """Mock async chat completion."""
        self.call_count += 1
        self.call_history.append({
            'messages': messages,
            'kwargs': kwargs
        })
        
        # Cycle through responses
        response_idx = (self.call_count - 1) % len(self.responses)
        content = self.responses[response_idx]
        
        return MockLLMResponse(content=content, model=self.model)
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> MockLLMResponse:
        """Mock sync chat completion."""
        self.call_count += 1
        self.call_history.append({
            'messages': messages,
            'kwargs': kwargs
        })
        
        # Cycle through responses
        response_idx = (self.call_count - 1) % len(self.responses)
        content = self.responses[response_idx]
        
        return MockLLMResponse(content=content, model=self.model)
    
    async def agenerate(self, prompt: str, **kwargs) -> str:
        """Mock async generation."""
        self.call_count += 1
        self.call_history.append({
            'prompt': prompt,
            'kwargs': kwargs
        })
        
        response_idx = (self.call_count - 1) % len(self.responses)
        return self.responses[response_idx]
    
    def reset(self):
        """Reset call history."""
        self.call_count = 0
        self.call_history = []


@pytest.fixture
def mock_llm_client():
    """
    Create a mock LLM client for testing.
    
    Returns:
        MockLLMClient: Mock client that simulates LLM responses
    """
    return MockLLMClient()


@pytest.fixture
def mock_openai_client():
    """
    Create a mock OpenAI client.
    
    Returns:
        MockLLMClient: Mock OpenAI client
    """
    return MockLLMClient(
        model="gpt-3.5-turbo",
        responses=[
            "This is a response from OpenAI GPT-3.5",
            "Another response for testing"
        ]
    )


@pytest.fixture
def mock_google_client():
    """
    Create a mock Google AI client.
    
    Returns:
        MockLLMClient: Mock Google AI client
    """
    return MockLLMClient(
        model="gemini-pro",
        responses=[
            "This is a response from Google Gemini",
            "Another Gemini response"
        ]
    )


@pytest.fixture
def mock_vertex_client():
    """
    Create a mock Vertex AI client.
    
    Returns:
        MockLLMClient: Mock Vertex AI client
    """
    return MockLLMClient(
        model="gemini-pro",
        responses=[
            "This is a response from Vertex AI",
            "Another Vertex response"
        ]
    )


@pytest.fixture
def mock_xai_client():
    """
    Create a mock xAI client.
    
    Returns:
        MockLLMClient: Mock xAI client
    """
    return MockLLMClient(
        model="grok-1",
        responses=[
            "This is a response from xAI Grok",
            "Another Grok response"
        ]
    )


@pytest.fixture
def llm_config():
    """
    Sample LLM configuration for testing.
    
    Returns:
        dict: LLM configuration
    """
    return {
        'model': 'gpt-3.5-turbo',
        'temperature': 0.7,
        'max_tokens': 1000,
        'top_p': 1.0,
        'frequency_penalty': 0.0,
        'presence_penalty': 0.0
    }


@pytest.fixture
def multi_llm_config():
    """
    Configuration for multiple LLM providers.
    
    Returns:
        dict: Multi-provider LLM configuration
    """
    return {
        'openai': {
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-openai-key'
        },
        'google': {
            'model': 'gemini-pro',
            'api_key': 'test-google-key'
        },
        'vertex': {
            'model': 'gemini-pro',
            'project_id': 'test-project',
            'location': 'us-central1'
        },
        'xai': {
            'model': 'grok-1',
            'api_key': 'test-xai-key'
        }
    }


@pytest.fixture
def mock_llm_response():
    """
    Create a sample mock LLM response.
    
    Returns:
        MockLLMResponse: Sample response object
    """
    return MockLLMResponse(
        content="This is a test response from the LLM",
        model="gpt-3.5-turbo",
        usage={
            'prompt_tokens': 15,
            'completion_tokens': 25,
            'total_tokens': 40
        }
    )


@pytest.fixture
def sample_chat_messages():
    """
    Sample chat messages for testing.
    
    Returns:
        list: List of chat messages
    """
    return [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'What is the capital of France?'},
        {'role': 'assistant', 'content': 'The capital of France is Paris.'},
        {'role': 'user', 'content': 'What is its population?'}
    ]
