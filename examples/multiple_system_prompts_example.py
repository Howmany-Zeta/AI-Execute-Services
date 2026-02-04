"""
Example: Using Multiple System Prompts with Agents

This example demonstrates how to use multiple system prompts with LLMAgent,
HybridAgent, and ToolAgent for better development experience.

Multiple system prompts allow you to:
1. Separate fixed instructions (cacheable) from dynamic context (non-cacheable)
2. Organize prompts by purpose (background knowledge, contextual info, skills, etc.)
3. Control caching individually for each system message
"""

import asyncio
from aiecs.domain.agent import LLMAgent, HybridAgent, ToolAgent, AgentConfiguration
from aiecs.llm import OpenAIClient


async def example_multiple_system_prompts():
    """Example: Multiple system prompts with individual cache control."""
    
    # Example 1: LLMAgent with multiple system prompts
    config = AgentConfiguration(
        system_prompts=[
            # Fixed instructions - can be cached
            "You are a helpful AI assistant specialized in data analysis. "
            "You have extensive knowledge of statistics, machine learning, and data visualization. "
            "Always provide clear explanations and cite your sources when possible.",
            
            # Dynamic contextual info - should not be cached
            {
                "content": "Important Contextual Info:\n"
                          "- Current Date: 2026-02-04\n"
                          "- User Location: New York\n"
                          "- Timezone: EST",
                "cache_control": False  # Don't cache dynamic context
            },
            
            # Skill body content - can be cached if stable
            "Available Skills:\n"
            "- Data visualization: Create charts and graphs\n"
            "- Statistical analysis: Perform hypothesis testing\n"
            "- Report generation: Create comprehensive reports"
        ],
        enable_prompt_caching=True,  # Global cache setting
        llm_model="gpt-4",
    )
    
    agent = LLMAgent(
        agent_id="multi_prompt_agent",
        name="Multi-Prompt Data Analyst",
        llm_client=OpenAIClient(),  # Replace with your actual client
        config=config,
    )
    
    await agent.initialize()
    
    # Use the agent
    result = await agent.execute_task(
        {"description": "Analyze sales data for Q4 2025"},
        {}
    )
    
    print("Result:", result["output"])


async def example_hybrid_agent_multiple_prompts():
    """Example: HybridAgent with multiple system prompts."""
    
    config = AgentConfiguration(
        system_prompts=[
            # Fixed background knowledge - cacheable
            "You are an expert research assistant with access to various tools. "
            "Your goal is to help users find accurate information and complete tasks efficiently.",
            
            # Dynamic context - not cacheable
            {
                "content": "Current Session Context:\n"
                          "- User preferences: Prefers concise answers\n"
                          "- Research focus: Technology trends",
                "cache_control": False
            }
        ],
        enable_prompt_caching=True,
        llm_model="gpt-4",
        react_format_enabled=True,
        tools=["search", "calculator"],  # Your tools here
    )
    
    agent = HybridAgent(
        agent_id="hybrid_multi_prompt",
        name="Multi-Prompt Research Agent",
        llm_client=OpenAIClient(),  # Replace with your actual client
        tools=["search", "calculator"],
        config=config,
    )
    
    await agent.initialize()
    
    # Use the agent
    result = await agent.execute_task(
        {"description": "Research the latest AI trends"},
        {}
    )
    
    print("Result:", result["output"])


async def example_backward_compatibility():
    """Example: Backward compatibility - single system_prompt still works."""
    
    # Old way still works
    config = AgentConfiguration(
        system_prompt="You are a helpful assistant.",
        llm_model="gpt-4",
    )
    
    agent = LLMAgent(
        agent_id="backward_compat",
        name="Backward Compatible Agent",
        llm_client=OpenAIClient(),  # Replace with your actual client
        config=config,
    )
    
    await agent.initialize()
    
    # Works exactly as before
    result = await agent.execute_task(
        {"description": "Hello!"},
        {}
    )
    
    print("Result:", result["output"])


async def example_mixed_format():
    """Example: Mixing string and dict formats in system_prompts."""
    
    config = AgentConfiguration(
        system_prompts=[
            # Simple string - uses global cache setting
            "Fixed instructions and background knowledge...",
            
            # Dict with explicit cache control
            {
                "content": "Dynamic context that changes frequently",
                "cache_control": False
            },
            
            # Dict without cache_control - uses global setting
            {
                "content": "Stable contextual information"
                # cache_control defaults to None, uses global enable_prompt_caching
            }
        ],
        enable_prompt_caching=True,
        llm_model="gpt-4",
    )
    
    agent = LLMAgent(
        agent_id="mixed_format",
        name="Mixed Format Agent",
        llm_client=OpenAIClient(),  # Replace with your actual client
        config=config,
    )
    
    await agent.initialize()
    
    messages = agent._build_messages("Hello", {})
    
    # Check system messages
    system_messages = [msg for msg in messages if msg.role == "system"]
    print(f"Number of system messages: {len(system_messages)}")
    for i, msg in enumerate(system_messages):
        print(f"System message {i+1}:")
        print(f"  Content preview: {msg.content[:50]}...")
        print(f"  Cache control: {msg.cache_control is not None}")


if __name__ == "__main__":
    print("Example: Multiple System Prompts")
    print("=" * 50)
    
    # Uncomment to run examples:
    # asyncio.run(example_multiple_system_prompts())
    # asyncio.run(example_hybrid_agent_multiple_prompts())
    # asyncio.run(example_backward_compatibility())
    # asyncio.run(example_mixed_format())
    
    print("\nNote: Replace OpenAIClient() with your actual LLM client configuration.")
    print("Examples demonstrate the API but require valid LLM client to execute.")
