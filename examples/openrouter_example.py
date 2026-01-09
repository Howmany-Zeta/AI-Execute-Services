"""
Example: Using OpenRouter Client

This example demonstrates how to use the OpenRouter client with various models.
"""

import asyncio
from aiecs.llm.clients.openrouter_client import OpenRouterClient
from aiecs.llm.clients.base_client import LLMMessage
from aiecs.llm.client_factory import LLMClientFactory, AIProvider


async def example_basic():
    """Basic usage example"""
    print("=" * 60)
    print("OpenRouter Basic Example")
    print("=" * 60)
    
    client = OpenRouterClient()
    
    messages = [
        LLMMessage(
            role="user",
            content="What is the meaning of life?"
        )
    ]
    
    try:
        response = await client.generate_text(
            messages=messages,
            model="openai/gpt-4o"
        )
        print(f"Response: {response.content}")
        print(f"Model: {response.model}")
        print(f"Provider: {response.provider}")
        print(f"Tokens used: {response.tokens_used}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


async def example_with_extra_headers():
    """Example with extra headers for OpenRouter rankings"""
    print("\n" + "=" * 60)
    print("OpenRouter with Extra Headers Example")
    print("=" * 60)
    
    client = OpenRouterClient()
    
    messages = [
        LLMMessage(
            role="user",
            content="Explain quantum computing in simple terms"
        )
    ]
    
    try:
        response = await client.generate_text(
            messages=messages,
            model="openai/gpt-4o",
            http_referer="https://myapp.com",  # Optional: for rankings
            x_title="My App"  # Optional: for rankings
        )
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


async def example_streaming():
    """Streaming example"""
    print("\n" + "=" * 60)
    print("OpenRouter Streaming Example")
    print("=" * 60)
    
    client = OpenRouterClient()
    
    messages = [
        LLMMessage(
            role="user",
            content="Write a short poem about AI"
        )
    ]
    
    try:
        print("Streaming response:")
        async for chunk in client.stream_text(
            messages=messages,
            model="openai/gpt-4o"
        ):
            print(chunk, end="", flush=True)
        print("\n")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        await client.close()


async def example_vision():
    """Vision example with images"""
    print("\n" + "=" * 60)
    print("OpenRouter Vision Example")
    print("=" * 60)
    
    client = OpenRouterClient()
    
    messages = [
        LLMMessage(
            role="user",
            content="What's in this image?",
            images=["https://example.com/image.jpg"]
        )
    ]
    
    try:
        response = await client.generate_text(
            messages=messages,
            model="openai/gpt-4o"  # Vision-capable model
        )
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


async def example_function_calling():
    """Function calling example"""
    print("\n" + "=" * 60)
    print("OpenRouter Function Calling Example")
    print("=" * 60)
    
    client = OpenRouterClient()
    
    messages = [
        LLMMessage(
            role="user",
            content="What's the weather in San Francisco?"
        )
    ]
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    try:
        response = await client.generate_text(
            messages=messages,
            model="openai/gpt-4o",
            tools=tools
        )
        print(f"Response: {response.content}")
        if response.tool_calls:
            print(f"Tool calls: {response.tool_calls}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


async def example_factory():
    """Example using LLMClientFactory"""
    print("\n" + "=" * 60)
    print("OpenRouter via Factory Example")
    print("=" * 60)
    
    client = LLMClientFactory.get_client(AIProvider.OPENROUTER)
    
    messages = [
        LLMMessage(
            role="user",
            content="Hello from OpenRouter!"
        )
    ]
    
    try:
        response = await client.generate_text(
            messages=messages,
            model="openai/gpt-4o"
        )
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


async def example_different_models():
    """Example with different models available on OpenRouter"""
    print("\n" + "=" * 60)
    print("OpenRouter Different Models Example")
    print("=" * 60)
    
    client = OpenRouterClient()
    
    models = [
        "openai/gpt-4o",
        "anthropic/claude-3.5-sonnet",
        "google/gemini-pro-1.5"
    ]
    
    messages = [
        LLMMessage(
            role="user",
            content="Say hello in one sentence"
        )
    ]
    
    for model in models:
        try:
            print(f"\nUsing model: {model}")
            response = await client.generate_text(
                messages=messages,
                model=model
            )
            print(f"Response: {response.content}")
        except Exception as e:
            print(f"Error with {model}: {e}")
    
    await client.close()


if __name__ == "__main__":
    print("OpenRouter Client Examples")
    print("\nNote: These examples require:")
    print("1. OPENROUTER_API_KEY environment variable set")
    print("2. Valid OpenRouter API key")
    print("\nUncomment the example you want to run:\n")
    
    # Uncomment to run examples:
    # asyncio.run(example_basic())
    # asyncio.run(example_with_extra_headers())
    # asyncio.run(example_streaming())
    # asyncio.run(example_vision())
    # asyncio.run(example_function_calling())
    # asyncio.run(example_factory())
    # asyncio.run(example_different_models())
