"""
Example: Using LLM Vision Support

This example demonstrates how to use image upload functionality with LLM clients.
"""

import asyncio
from aiecs.llm.clients.openai_client import OpenAIClient
from aiecs.llm.clients.vertex_client import VertexAIClient
from aiecs.llm.clients.googleai_client import GoogleAIClient
from aiecs.llm.clients.xai_client import XAIClient
from aiecs.llm.clients.base_client import LLMMessage


async def example_openai_vision():
    """Example: Using OpenAI with images"""
    print("=" * 60)
    print("OpenAI Vision Example")
    print("=" * 60)
    
    client = OpenAIClient()
    
    # Example 1: Image from URL
    messages = [
        LLMMessage(
            role="user",
            content="What's in this image?",
            images=["https://example.com/image.jpg"]  # Image URL
        )
    ]
    
    # Example 2: Image from file path
    messages_file = [
        LLMMessage(
            role="user",
            content="Describe this image",
            images=["/path/to/image.png"]  # Local file path
        )
    ]
    
    # Example 3: Image from base64 data URI
    messages_base64 = [
        LLMMessage(
            role="user",
            content="Analyze this image",
            images=["data:image/png;base64,iVBORw0KGgoAAAANS..."]  # Base64 data URI
        )
    ]
    
    # Example 4: Multiple images with text
    messages_multi = [
        LLMMessage(
            role="user",
            content="Compare these two images",
            images=[
                "https://example.com/image1.jpg",
                "https://example.com/image2.jpg"
            ]
        )
    ]
    
    try:
        response = await client.generate_text(
            messages=messages,
            model="gpt-4o"  # Vision-capable model
        )
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


async def example_google_vision():
    """Example: Using Google AI (Gemini) with images"""
    print("\n" + "=" * 60)
    print("Google AI Vision Example")
    print("=" * 60)
    
    client = GoogleAIClient()
    
    messages = [
        LLMMessage(
            role="user",
            content="What does this image show?",
            images=["/path/to/image.jpg"]  # File path or URL
        )
    ]
    
    try:
        response = await client.generate_text(
            messages=messages,
            model="gemini-2.5-pro"  # Vision-capable model
        )
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


async def example_vertex_vision():
    """Example: Using Vertex AI with images"""
    print("\n" + "=" * 60)
    print("Vertex AI Vision Example")
    print("=" * 60)
    
    client = VertexAIClient()
    
    messages = [
        LLMMessage(
            role="user",
            content="Describe this image in detail",
            images=["https://example.com/image.png"]  # URL or file path
        )
    ]
    
    try:
        response = await client.generate_text(
            messages=messages,
            model="gemini-2.5-pro"  # Vision-capable model
        )
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


async def example_xai_vision():
    """Example: Using xAI (Grok) with images"""
    print("\n" + "=" * 60)
    print("xAI Vision Example")
    print("=" * 60)
    
    client = XAIClient()
    
    messages = [
        LLMMessage(
            role="user",
            content="What can you see in this image?",
            images=["https://example.com/image.jpg"]  # URL, file path, or base64
        )
    ]
    
    try:
        response = await client.generate_text(
            messages=messages,
            model="grok-2-vision"  # Vision-capable model
        )
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


async def example_dict_format():
    """Example: Using dict format for images with additional options"""
    print("\n" + "=" * 60)
    print("Dict Format Example")
    print("=" * 60)
    
    client = OpenAIClient()
    
    # Using dict format for more control
    messages = [
        LLMMessage(
            role="user",
            content="Analyze this image",
            images=[
                {
                    "url": "https://example.com/image.jpg",
                    "detail": "high"  # "low", "high", or "auto" (OpenAI only)
                }
            ]
        )
    ]
    
    try:
        response = await client.generate_text(
            messages=messages,
            model="gpt-4o"
        )
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    print("LLM Vision Support Examples")
    print("\nNote: These examples require:")
    print("1. Valid API keys configured")
    print("2. Vision-capable models")
    print("3. Accessible image URLs or valid file paths")
    print("\nUncomment the example you want to run:\n")
    
    # Uncomment to run examples:
    # asyncio.run(example_openai_vision())
    # asyncio.run(example_google_vision())
    # asyncio.run(example_vertex_vision())
    # asyncio.run(example_xai_vision())
    # asyncio.run(example_dict_format())
