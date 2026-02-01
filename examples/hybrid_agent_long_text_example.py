"""
Example: Using HybridAgent for Continuous Long Text Generation

This example demonstrates how to configure and use HybridAgent to generate
long text across multiple rounds without abrupt truncation.
"""

import asyncio
from typing import Dict, Any

from aiecs.domain.agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.llm import OpenAIClient


async def example_basic_long_text_generation():
    """Basic example: Generate long text with proper configuration."""
    
    # Step 1: Configure agent for long text generation
    config = AgentConfiguration(
        llm_model="gpt-4-turbo-preview",
        temperature=0.7,
        max_tokens=3000,  # Per iteration - allows natural paragraph completion
        max_iterations=15,  # Allow multiple rounds for long text
        system_prompt="""You are a skilled writer capable of generating long-form content.

When generating long text:
1. Write naturally and continue seamlessly from previous content
2. Use FINAL RESPONSE: <your_content> finish only when completely done
3. If your response is cut off due to token limits, continue in the next iteration
4. Maintain consistency in style and tone throughout
5. End sentences and paragraphs naturally, even if continuing later

Format your response as:
FINAL RESPONSE: <your_long_text_content> finish

Only add 'finish' when the entire text is complete."""
    )
    
    # Step 2: Initialize agent
    llm_client = OpenAIClient(api_key="your-api-key")
    agent = HybridAgent(
        agent_id="long-text-writer",
        name="Long Text Writer",
        llm_client=llm_client,
        tools=[],  # No tools needed for pure text generation
        config=config
    )
    
    await agent.initialize()
    
    # Step 3: Create task with continuation-friendly prompt
    task = {
        "description": """Write a comprehensive 3000-word article about the impact of 
        artificial intelligence on modern society. Cover:
        - Historical development of AI
        - Current applications and use cases
        - Future prospects and challenges
        - Ethical considerations
        - Impact on employment and economy
        
        Write naturally and continue seamlessly across multiple rounds if needed.
        Only end with 'finish' when the entire article is complete."""
    }
    
    # Step 4: Execute task
    result = await agent.execute_task(task, {})
    
    # Step 5: Extract and display results
    final_text = result["output"]
    print(f"\n{'='*60}")
    print(f"Generation Complete!")
    print(f"{'='*60}")
    print(f"Iterations used: {result['iterations']}")
    print(f"Text length: {len(final_text)} characters")
    print(f"Execution time: {result['execution_time']:.2f} seconds")
    print(f"\n{'='*60}")
    print("Generated Text:")
    print(f"{'='*60}")
    print(final_text[:500] + "..." if len(final_text) > 500 else final_text)
    
    return result


async def example_streaming_long_text():
    """Example: Stream long text generation to monitor progress."""
    
    config = AgentConfiguration(
        llm_model="gpt-4-turbo-preview",
        temperature=0.7,
        max_tokens=3000,
        max_iterations=20,
        system_prompt="""You are a professional writer. Generate long-form content naturally.
        Use FINAL RESPONSE: <content> finish only when completely done.
        Continue seamlessly if cut off."""
    )
    
    llm_client = OpenAIClient(api_key="your-api-key")
    agent = HybridAgent(
        agent_id="streaming-writer",
        name="Streaming Writer",
        llm_client=llm_client,
        tools=[],
        config=config
    )
    
    await agent.initialize()
    
    task = {
        "description": "Write a detailed 4000-word guide on machine learning fundamentals."
    }
    
    # Stream generation
    full_text = []
    current_iteration = 0
    
    print("Starting generation...\n")
    
    async for event in agent.execute_task_streaming(task, {}):
        if event['type'] == 'status':
            if event['status'] == 'thinking':
                current_iteration = event['iteration']
                print(f"\n[Iteration {current_iteration}/{event['max_iterations']}]")
                print("-" * 60)
        elif event['type'] == 'token':
            full_text.append(event['content'])
            print(event['content'], end='', flush=True)
        elif event['type'] == 'result':
            print(f"\n\n{'='*60}")
            print(f"Completed in {event['iterations']} iterations")
            print(f"Total tokens: ~{len(''.join(full_text)) // 4}")
            print(f"{'='*60}")
        elif event['type'] == 'error':
            print(f"\nError: {event['error']}")
    
    return ''.join(full_text)


async def example_custom_continuation_prompt():
    """Example: Custom system prompt for seamless continuation."""
    
    config = AgentConfiguration(
        llm_model="gpt-4-turbo-preview",
        temperature=0.7,
        max_tokens=2500,  # Slightly lower for more iterations
        max_iterations=25,  # More iterations for very long text
        system_prompt="""You are a professional writer generating long-form content.

CONTINUATION GUIDELINES:
1. When continuing from previous output, start naturally without repetition
2. Use transitional phrases to connect with previous content (e.g., "Building on this...", "Furthermore...", "In addition...")
3. Maintain narrative flow and coherence across iterations
4. Only use FINAL RESPONSE: <content> finish when 100% complete
5. If your response is cut off, continue seamlessly in the next round

Example continuation:
Previous: "The history of AI dates back to the 1950s..."
Next: "Building on this foundation, modern AI systems have evolved..."

Write naturally and maintain consistency in style and tone."""
    )
    
    llm_client = OpenAIClient(api_key="your-api-key")
    agent = HybridAgent(
        agent_id="custom-writer",
        name="Custom Continuation Writer",
        llm_client=llm_client,
        tools=[],
        config=config
    )
    
    await agent.initialize()
    
    task = {
        "description": """Write a comprehensive 6000-word research paper on neural networks.
        
        Structure:
        1. Introduction and background
        2. Architecture and design principles
        3. Training methodologies
        4. Applications and use cases
        5. Challenges and limitations
        6. Future directions
        7. Conclusion
        
        Write academically and continue seamlessly across iterations."""
    }
    
    result = await agent.execute_task(task, {})
    
    # Check if generation completed successfully
    if result.get("max_iterations_reached"):
        print("Warning: Reached max_iterations. Consider increasing it.")
    
    # Extract final response (remove FINAL RESPONSE: prefix and finish suffix if present)
    final_text = result["output"]
    if "FINAL RESPONSE:" in final_text:
        # Extract content between FINAL RESPONSE: and finish
        parts = final_text.split("FINAL RESPONSE:", 1)
        if len(parts) > 1:
            content = parts[1].rsplit("finish", 1)[0].strip()
            final_text = content
    
    print(f"\nGenerated {len(final_text)} characters in {result['iterations']} iterations")
    return final_text


async def example_monitoring_and_handling():
    """Example: Monitor generation and handle edge cases."""
    
    config = AgentConfiguration(
        llm_model="gpt-4-turbo-preview",
        temperature=0.7,
        max_tokens=3000,
        max_iterations=10,  # Start with lower limit
        system_prompt="""Generate long-form content. Use FINAL RESPONSE: <content> finish when done."""
    )
    
    llm_client = OpenAIClient(api_key="your-api-key")
    agent = HybridAgent(
        agent_id="monitored-writer",
        name="Monitored Writer",
        llm_client=llm_client,
        tools=[],
        config=config
    )
    
    await agent.initialize()
    
    task = {
        "description": "Write a detailed 5000-word article about quantum computing."
    }
    
    result = await agent.execute_task(task, {})
    
    # Monitor results
    print(f"Iterations used: {result['iterations']}")
    print(f"Max iterations: {config.max_iterations}")
    print(f"Text length: {len(result['output'])} characters")
    
    # Check if we hit the limit
    if result.get("max_iterations_reached"):
        print("\n⚠️  Reached max_iterations limit!")
        print("Consider:")
        print(f"  1. Increasing max_iterations (current: {config.max_iterations})")
        print(f"  2. Increasing max_tokens per iteration (current: {config.max_tokens})")
        print(f"  3. Checking if LLM is outputting 'finish' prematurely")
        
        # Optionally retry with higher limits
        config.max_iterations = 20
        agent = HybridAgent(
            agent_id="monitored-writer-retry",
            name="Monitored Writer Retry",
            llm_client=llm_client,
            tools=[],
            config=config
        )
        await agent.initialize()
        result = await agent.execute_task(task, {})
        print(f"\nRetry: Completed in {result['iterations']} iterations")
    
    # Check if generation completed naturally
    if "finish" not in result["output"].lower():
        print("\n⚠️  Generation may be incomplete (no 'finish' marker found)")
    
    return result


async def main():
    """Run all examples."""
    print("HybridAgent Long Text Generation Examples")
    print("=" * 60)
    
    # Uncomment the example you want to run:
    
    # Example 1: Basic long text generation
    # await example_basic_long_text_generation()
    
    # Example 2: Streaming mode
    # await example_streaming_long_text()
    
    # Example 3: Custom continuation prompt
    # await example_custom_continuation_prompt()
    
    # Example 4: Monitoring and handling
    # await example_monitoring_and_handling()
    
    print("\nExamples completed!")


if __name__ == "__main__":
    asyncio.run(main())
