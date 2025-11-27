# Custom LLM Client Integration

This document describes how to integrate custom LLM providers into the AIECS framework using the `LLMClientProtocol` interface.

## Overview

AIECS supports custom LLM providers through a protocol-based interface that allows you to:
- Integrate local LLM models (Ollama, LM Studio, etc.)
- Use proprietary or specialized LLM services
- Implement custom embedding providers
- Configure different LLMs for different operations (entity extraction, RAG strategy selection, embeddings)

## LLMClientProtocol Interface

Custom LLM clients must implement the `LLMClientProtocol` interface defined in `aiecs/llm/protocols.py`:

```python
from typing import Protocol, List, Optional, AsyncGenerator, Dict, Any

@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol that all LLM clients must implement"""

    @property
    def provider_name(self) -> str:
        """Name of the LLM provider"""
        ...

    @property
    def model_name(self) -> str:
        """Name of the model being used"""
        ...

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Generate text from a prompt"""
        ...

    async def stream_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text generation from a prompt"""
        ...

    async def get_embeddings(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        ...
```

## Implementing a Custom LLM Client

### Example 1: Local Model Client (Ollama)

```python
from typing import List, Optional, AsyncGenerator
import httpx

class OllamaClient:
    """Custom client for Ollama local models"""

    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url
        self._client = httpx.AsyncClient()

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Generate text using Ollama API"""
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False
        }

        if temperature is not None:
            payload["temperature"] = temperature

        response = await self._client.post(
            f"{self._base_url}/api/generate",
            json=payload
        )
        response.raise_for_status()
        return response.json()["response"]

    async def stream_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using Ollama API"""
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": True
        }

        if temperature is not None:
            payload["temperature"] = temperature

        async with self._client.stream(
            "POST",
            f"{self._base_url}/api/generate",
            json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]

    async def get_embeddings(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """Generate embeddings using Ollama API"""
        embeddings = []
        for text in texts:
            response = await self._client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text}
            )
            response.raise_for_status()
            embeddings.append(response.json()["embedding"])
        return embeddings

    async def close(self):
        """Clean up resources"""
        await self._client.aclose()
```

### Example 2: Custom Embedding Client

```python
from typing import List

class CustomEmbeddingClient:
    """Custom embedding client for specialized embeddings"""

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        self._model = model

    @property
    def provider_name(self) -> str:
        return "custom-embeddings"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Not used for embedding-only clients"""
        raise NotImplementedError("This client only supports embeddings")

    async def stream_text(self, prompt: str, **kwargs):
        """Not used for embedding-only clients"""
        raise NotImplementedError("This client only supports embeddings")

    async def get_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Generate custom embeddings"""
        # Example: Using a local sentence transformer model
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(self._model)
        embeddings = model.encode(texts)
        return embeddings.tolist()
```

## Registering Custom Providers

Once you've implemented a custom client, register it with the `LLMClientFactory`:

```python
from aiecs.llm import LLMClientFactory

# Create your custom client instance
ollama_client = OllamaClient(model="llama2")

# Register it with a unique provider name
LLMClientFactory.register_custom_provider("ollama", ollama_client)

# Now you can use it anywhere in AIECS
from aiecs.llm import resolve_llm_client

client = resolve_llm_client("ollama")
response = await client.generate_text("What is the capital of France?")
```

## Configuration-Driven Usage

You can configure AIECS to use custom providers through environment variables:

### Entity Extraction Configuration

```bash
# Use custom LLM for entity extraction
export KG_ENTITY_EXTRACTION_PROVIDER="ollama"
export KG_ENTITY_EXTRACTION_MODEL="llama2"
```

```python
from aiecs.application.knowledge_graph.extraction import LLMEntityExtractor

# Register your custom provider first
LLMClientFactory.register_custom_provider("ollama", OllamaClient(model="llama2"))

# Create extractor using configuration
extractor = LLMEntityExtractor.from_config()
# Will automatically use the ollama provider from environment variables
```

### RAG Strategy Selection Configuration

```bash
# Use custom LLM for query intent classification
export KG_STRATEGY_SELECTION_PROVIDER="ollama"
export KG_STRATEGY_SELECTION_MODEL="llama2"
```

```python
from aiecs.application.knowledge_graph.retrieval import QueryIntentClassifier

# Register your custom provider first
LLMClientFactory.register_custom_provider("ollama", OllamaClient(model="llama2"))

# Create classifier using configuration
classifier = QueryIntentClassifier.from_config()
# Will automatically use the ollama provider from environment variables
```

### Embedding Configuration

```bash
# Use custom embedding provider
export KG_EMBEDDING_PROVIDER="custom-embeddings"
export KG_EMBEDDING_MODEL="all-MiniLM-L6-v2"
export KG_EMBEDDING_DIMENSION=384
```

```python
from aiecs.application.knowledge_graph.builder import GraphBuilder

# Register your custom embedding provider first
embedding_client = CustomEmbeddingClient(model="all-MiniLM-L6-v2")
LLMClientFactory.register_custom_provider("custom-embeddings", embedding_client)

# Create graph builder using configuration
builder = GraphBuilder.from_config(
    graph_store=my_graph_store,
    entity_extractor=my_entity_extractor,
    relation_extractor=my_relation_extractor
)
# Will automatically use the custom embedding provider from environment variables
```

## Cost Optimization Example

Use different LLMs for different operations to optimize costs:

```python
from aiecs.llm import LLMClientFactory
from aiecs.application.knowledge_graph.extraction import LLMEntityExtractor
from aiecs.application.knowledge_graph.retrieval import QueryIntentClassifier
from aiecs.application.knowledge_graph.builder import GraphBuilder
import os

# Register custom providers
ollama_client = OllamaClient(model="llama2")  # Free local model
LLMClientFactory.register_custom_provider("ollama", ollama_client)

# Use free local model for classification (lightweight task)
os.environ["KG_STRATEGY_SELECTION_PROVIDER"] = "ollama"
os.environ["KG_STRATEGY_SELECTION_MODEL"] = "llama2"

# Use powerful cloud model for entity extraction (complex task)
os.environ["KG_ENTITY_EXTRACTION_PROVIDER"] = "OpenAI"
os.environ["KG_ENTITY_EXTRACTION_MODEL"] = "gpt-4"

# Use local embeddings to avoid API costs
embedding_client = CustomEmbeddingClient(model="all-MiniLM-L6-v2")
LLMClientFactory.register_custom_provider("local-embeddings", embedding_client)
os.environ["KG_EMBEDDING_PROVIDER"] = "local-embeddings"
os.environ["KG_EMBEDDING_MODEL"] = "all-MiniLM-L6-v2"
os.environ["KG_EMBEDDING_DIMENSION"] = "384"

# Create components - they'll use the configured providers
classifier = QueryIntentClassifier.from_config()  # Uses ollama
extractor = LLMEntityExtractor.from_config()      # Uses OpenAI GPT-4
builder = GraphBuilder.from_config(...)           # Uses local embeddings
```

## Best Practices

1. **Protocol Compliance**: Ensure your client implements all required methods of `LLMClientProtocol`
2. **Error Handling**: Implement proper error handling and retries in your client
3. **Resource Cleanup**: Implement `close()` method to clean up resources (connections, etc.)
4. **Async Support**: Use async/await for all I/O operations
5. **Type Hints**: Use proper type hints for better IDE support and type checking
6. **Testing**: Test your custom client thoroughly before using in production
7. **Configuration**: Use environment variables for configuration to avoid hardcoding values

## Troubleshooting

### Client Not Found

If you get "Unknown provider" errors:
- Ensure you've registered the provider before using it
- Check that the provider name matches exactly (case-sensitive)
- Register providers at application startup, before creating components

### Settings Cache Issues

If environment variable changes aren't picked up:
```python
from aiecs.config.config import get_settings
get_settings.cache_clear()  # Clear settings cache
```

### Client Cache Issues

If you need to force re-resolution of clients:
```python
from aiecs.llm import clear_client_cache
clear_client_cache()  # Clear all cached clients
clear_client_cache("ollama")  # Clear specific provider
```

## See Also

- [LLM Configuration](LLM_CONFIGURATION.md) - General LLM configuration
- [Base LLM Client](BASE_LLM_CLIENT.md) - Built-in LLM clients
- [LLM AI Clients](LLM_AI_CLIENTS.md) - Standard provider clients

