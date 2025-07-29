"""
Test Configuration for SummarizerService Real API Tests

This module provides configuration settings and utilities for testing
the SummarizerService with real API connections.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TestConfig:
    """Configuration for SummarizerService tests"""

    # API Configuration
    xai_api_key: Optional[str] = None
    vertex_project_id: Optional[str] = None
    vertex_location: str = "us-central1"
    google_credentials_path: Optional[str] = None

    # Test Configuration
    test_timeout: int = 300  # 5 minutes
    max_retries: int = 3
    retry_delay: float = 1.0

    # Rate Limiting
    requests_per_minute: int = 10
    concurrent_requests: int = 3

    # Content Validation
    min_response_length: int = 20
    max_response_length: int = 10000

    # Test Data
    sample_texts: Dict[str, str] = None

    def __post_init__(self):
        """Initialize configuration from environment variables"""
        # Load API keys from environment
        self.xai_api_key = os.getenv('XAI_API_KEY') or os.getenv('GROK_API_KEY')
        self.vertex_project_id = os.getenv('VERTEX_PROJECT_ID')
        self.vertex_location = os.getenv('VERTEX_LOCATION', self.vertex_location)
        self.google_credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

        # Initialize sample texts if not provided
        if self.sample_texts is None:
            self.sample_texts = {
                "short": "Artificial Intelligence is transforming technology.",
                "medium": """
                Artificial Intelligence (AI) is a branch of computer science that aims to create
                intelligent machines that can perform tasks that typically require human intelligence.
                These tasks include learning, reasoning, problem-solving, perception, and language
                understanding. AI has applications in various fields including healthcare, finance,
                transportation, and entertainment.
                """.strip(),
                "long": """
                Artificial Intelligence (AI) represents one of the most significant technological
                advances of the 21st century. It encompasses a broad range of technologies and
                methodologies designed to enable machines to perform tasks that traditionally
                required human intelligence. The field of AI has evolved dramatically since its
                inception in the 1950s, moving from theoretical concepts to practical applications
                that impact our daily lives.

                Machine Learning, a subset of AI, has been particularly transformative. It allows
                systems to automatically learn and improve from experience without being explicitly
                programmed. Deep Learning, a further subset of Machine Learning, uses neural networks
                with multiple layers to model and understand complex patterns in data.

                The applications of AI are vast and growing. In healthcare, AI assists in medical
                diagnosis, drug discovery, and personalized treatment plans. In finance, it powers
                algorithmic trading, fraud detection, and risk assessment. Transportation has been
                revolutionized by autonomous vehicles and traffic optimization systems. Entertainment
                industries use AI for content recommendation, game development, and creative content
                generation.

                However, the rapid advancement of AI also brings challenges and ethical considerations.
                Issues such as job displacement, privacy concerns, algorithmic bias, and the need for
                responsible AI development are at the forefront of current discussions. As AI continues
                to evolve, it's crucial to balance innovation with ethical considerations and societal
                impact.
                """.strip(),
                "code": """
                def fibonacci(n):
                    '''
                    Calculate the nth Fibonacci number using dynamic programming.

                    Args:
                        n (int): The position in the Fibonacci sequence

                    Returns:
                        int: The nth Fibonacci number
                    '''
                    if n <= 1:
                        return n

                    dp = [0] * (n + 1)
                    dp[1] = 1

                    for i in range(2, n + 1):
                        dp[i] = dp[i-1] + dp[i-2]

                    return dp[n]
                """.strip(),
                "multilingual": """
                Hello, this is a test message in English.
                Hola, este es un mensaje de prueba en español.
                Bonjour, ceci est un message de test en français.
                こんにちは、これは日本語のテストメッセージです。
                你好，这是一条中文测试消息。
                """.strip()
            }

    @property
    def xai_available(self) -> bool:
        """Check if XAI API is available"""
        return self.xai_api_key is not None

    @property
    def vertex_available(self) -> bool:
        """Check if Vertex AI is available"""
        return (self.vertex_project_id is not None and
                self.google_credentials_path is not None and
                os.path.exists(self.google_credentials_path))

    @property
    def available_providers(self) -> list:
        """Get list of available providers"""
        providers = []
        if self.xai_available:
            providers.append("xAI")
        if self.vertex_available:
            providers.append("Vertex")
        return providers

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific provider"""
        if provider == "xAI":
            return {
                "provider": "xAI",
                "model": "grok-2",
                "available": self.xai_available
            }
        elif provider == "Vertex":
            return {
                "provider": "Vertex",
                "model": "gemini-2.5-pro",
                "available": self.vertex_available
            }
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def get_test_contexts(self) -> list:
        """Get test contexts for all available providers"""
        contexts = []
        for provider in self.available_providers:
            config = self.get_provider_config(provider)
            context = {
                "metadata": {
                    "provider": config["provider"],
                    "model": config["model"]
                },
                "user_id": f"test_user_{provider}",
                "session_id": f"test_session_{provider}"
            }
            contexts.append(context)
        return contexts


# Global test configuration instance
test_config = TestConfig()


def get_test_config() -> TestConfig:
    """Get the global test configuration"""
    return test_config


def validate_response_content(content: str, provider: str = None) -> bool:
    """
    Validate response content for quality and completeness

    Args:
        content: The response content to validate
        provider: The provider that generated the response

    Returns:
        bool: True if content is valid, False otherwise
    """
    if not content or not isinstance(content, str):
        return False

    content = content.strip()

    # Check minimum length
    if len(content) < test_config.min_response_length:
        return False

    # Check maximum length
    if len(content) > test_config.max_response_length:
        return False

    # Check for blocked/error responses (especially for Vertex AI)
    blocked_indicators = [
        "[Response blocked by safety filters",
        "[Response unavailable",
        "[Response error:",
        "[Response truncated"
    ]

    for indicator in blocked_indicators:
        if indicator in content:
            return False

    # Provider-specific validation
    if provider == "Vertex":
        # Vertex AI should provide substantial content
        if len(content) < 50:
            return False

    return True


def create_test_input(text_type: str = "medium", task_type: str = "summarize") -> Dict[str, Any]:
    """
    Create test input data

    Args:
        text_type: Type of text to use ("short", "medium", "long", "code", "multilingual")
        task_type: Type of task ("summarize", "explain", "compare", etc.)

    Returns:
        Dict containing test input data
    """
    if text_type not in test_config.sample_texts:
        raise ValueError(f"Unknown text type: {text_type}")

    return {
        "text": test_config.sample_texts[text_type],
        "task_type": task_type
    }


def create_test_context(provider: str, user_id: str = None, session_id: str = None) -> Dict[str, Any]:
    """
    Create test context for a specific provider

    Args:
        provider: Provider name ("xai" or "vertex")
        user_id: Optional user ID
        session_id: Optional session ID

    Returns:
        Dict containing test context
    """
    config = test_config.get_provider_config(provider)

    return {
        "metadata": {
            "provider": config["provider"],
            "model": config["model"]
        },
        "user_id": user_id or f"test_user_{provider}",
        "session_id": session_id or f"test_session_{provider}"
    }


# Test data for different scenarios
TEST_SCENARIOS = {
    "basic_summarization": {
        "input": create_test_input("medium", "summarize"),
        "expected_keywords": ["artificial intelligence", "machine", "tasks"]
    },
    "code_explanation": {
        "input": create_test_input("code", "explain"),
        "expected_keywords": ["fibonacci", "function", "dynamic programming"]
    },
    "comparison_task": {
        "input": {"text": "Compare Python and JavaScript programming languages", "task_type": "compare"},
        "expected_keywords": ["python", "javascript", "programming"]
    },
    "translation_task": {
        "input": {"text": "Hello, how are you today?", "task_type": "translate"},
        "expected_keywords": ["hello", "today"]
    },
    "long_text_summary": {
        "input": create_test_input("long", "summarize"),
        "expected_keywords": ["artificial intelligence", "machine learning", "applications"]
    }
}


# Performance benchmarks
PERFORMANCE_BENCHMARKS = {
    "response_time": {
        "xai": {"max": 30.0, "target": 15.0},  # seconds
        "vertex": {"max": 45.0, "target": 20.0}  # seconds (includes thinking time)
    },
    "token_efficiency": {
        "min_tokens_per_char": 0.1,
        "max_tokens_per_char": 0.5
    },
    "cost_efficiency": {
        "max_cost_per_1k_tokens": 0.01  # USD
    }
}
