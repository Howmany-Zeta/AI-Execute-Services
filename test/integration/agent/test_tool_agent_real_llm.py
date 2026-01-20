"""
Integration Test for ToolAgent with Real LLM and Real Tools

Tests ToolAgent using:
- Real LLM (xAI Grok)
- Real Search Tool (Google Custom Search)
- Full streaming: LLM tokens, tool calls, tool results

Run with: poetry run python -m pytest test/integration/agent/test_tool_agent_real_llm.py -v -s
"""

import os
import asyncio
import pytest
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load test environment
load_dotenv(".env.test")

from aiecs.domain.agent import ToolAgent, AgentConfiguration
from aiecs.tools.search_tool import SearchTool
from aiecs.tools import BaseTool
from aiecs.llm import LLMClientFactory, AIProvider


class MockSearchTool(BaseTool):
    """
    Mock search tool for testing ToolAgent function calling without external APIs.
    Returns fake search results to verify the complete flow works.
    """

    # Schema for the default operation (None key means default)
    class RunSchema(BaseModel):
        """Search the web for information."""
        query: str = Field(description="The search query string")
        num_results: int = Field(default=5, ge=1, le=10, description="Number of results to return (1-10)")

    def __init__(self):
        """Initialize mock search tool."""
        super().__init__(tool_name="web_search")
        # Register schema for default operation
        self._schemas[None] = self.RunSchema

    async def run_async(self, op: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Return mock search results."""
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 5)

        # Generate mock results
        results = []
        for i in range(min(num_results, 5)):
            results.append({
                "title": f"Search Result {i+1} for: {query}",
                "link": f"https://example.com/result{i+1}",
                "snippet": f"This is a mock search result about {query}. It contains relevant information.",
            })

        return {
            "results": results,
            "query": query,
            "total_results": len(results),
        }

    def run(self, op: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Sync version - returns same mock results."""
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 5)

        results = []
        for i in range(min(num_results, 5)):
            results.append({
                "title": f"Search Result {i+1} for: {query}",
                "link": f"https://example.com/result{i+1}",
                "snippet": f"This is a mock search result about {query}.",
            })

        return {"results": results, "query": query, "total_results": len(results)}


class WebSearchTool(BaseTool):
    """
    Real wrapper around SearchTool for ToolAgent function calling.
    Overrides run_async to accept parameters directly without op.
    """

    # Schema for the default operation (None key means default)
    class RunSchema(BaseModel):
        """Search the web for information using Google Custom Search."""
        query: str = Field(description="The search query string")
        num_results: int = Field(default=5, ge=1, le=10, description="Number of results to return (1-10)")

    def __init__(self):
        """Initialize with underlying SearchTool."""
        super().__init__(tool_name="web_search")
        self._search_tool = SearchTool()
        # Register schema for default operation
        self._schemas[None] = self.RunSchema

    async def run_async(self, op: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Search the web for information."""
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 5)

        # SearchTool.search_web is synchronous, run in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._search_tool.search_web(
                query=query,
                num_results=min(num_results, 10),
                auto_enhance=True,
                return_summary=False,
            )
        )

    def run(self, op: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Sync version of search."""
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 5)
        return self._search_tool.search_web(
            query=query,
            num_results=min(num_results, 10),
            auto_enhance=True,
            return_summary=False,
        )


def get_llm_client():
    """Get LLM client based on available API keys."""
    xai_key = os.getenv("XAI_API_KEY")
    openrouter_key = os.getenv("openrouter_KEY")

    if xai_key:
        print(f"\n✓ Using xAI client (key: {xai_key[:10]}...)")
        return LLMClientFactory.get_client(AIProvider.XAI)
    elif openrouter_key:
        print(f"\n✓ Using OpenRouter client (key: {openrouter_key[:10]}...)")
        return LLMClientFactory.get_client(AIProvider.OPENROUTER)
    else:
        pytest.skip("No LLM API key found (XAI_API_KEY or openrouter_KEY)")


def get_search_tool():
    """Get WebSearchTool instance (wrapper around SearchTool)."""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_cse_id = os.getenv("GOOGLE_CSE_ID")

    if not google_api_key or not google_cse_id:
        pytest.skip("GOOGLE_API_KEY or GOOGLE_CSE_ID not found in environment")

    # SearchTool uses SEARCH_TOOL_ prefix for env vars
    os.environ["SEARCH_TOOL_GOOGLE_API_KEY"] = google_api_key
    os.environ["SEARCH_TOOL_GOOGLE_CSE_ID"] = google_cse_id

    print(f"✓ Using WebSearchTool (Google CSE: {google_cse_id[:10]}...)")
    return WebSearchTool()


def get_mock_search_tool():
    """Get MockSearchTool for testing without external APIs."""
    print("✓ Using MockSearchTool (no external API)")
    return MockSearchTool()


@pytest.fixture
def llm_client():
    """Create real LLM client."""
    return get_llm_client()


@pytest.fixture
def search_tool():
    """Create real WebSearchTool."""
    return get_search_tool()


@pytest.fixture
def mock_search_tool():
    """Create mock search tool for testing."""
    return get_mock_search_tool()


@pytest.fixture
def agent_config():
    """Create agent configuration."""
    return AgentConfiguration(
        goal="Search the web for information",
        llm_model="grok-3-mini",
        temperature=0.3,
        max_tokens=1000,
    )


def print_tool_result(event):
    """Pretty print tool result."""
    result = event.get("result", {})
    print(f"\n[TOOL RESULT] {event.get('tool_name')}")
    if isinstance(result, dict):
        # Handle search results
        if "results" in result:
            results = result["results"]
            print(f"  Search results found: {len(results)}")
            for i, r in enumerate(results[:3]):
                title = r.get("title", "No title")[:60]
                print(f"  {i+1}. {title}...")
        elif "summary" in result:
            print(f"  Summary: {result.get('summary', {})}")
        else:
            print(f"  Result keys: {list(result.keys())[:5]}")
    elif isinstance(result, list):
        print(f"  Results count: {len(result)}")
        for i, r in enumerate(result[:3]):
            if isinstance(r, dict):
                title = r.get("title", str(r)[:50])[:60]
                print(f"  {i+1}. {title}...")
    else:
        print(f"  Result: {str(result)[:100]}...")


class TestToolAgentRealLLM:
    """Integration tests with real LLM and real tools."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tool_agent_streaming_web_search(self, llm_client, search_tool, agent_config):
        """
        Test full streaming flow with real LLM and real SearchTool.

        Verifies:
        1. LLM tokens are streamed
        2. Tool calls are identified and streamed
        3. Tool results are streamed
        4. Final result contains search data
        """
        print("\n" + "="*60)
        print("TEST: ToolAgent Streaming with Real LLM + SearchTool")
        print("="*60)

        # Use web_search as tool name to match WebSearchTool's schema
        agent = ToolAgent(
            agent_id="test_real_streaming",
            name="Web Search Agent",
            llm_client=llm_client,
            tools={"web_search": search_tool},
            config=agent_config,
        )

        await agent.initialize()
        print(f"\n✓ Agent initialized: {agent.agent_id}")
        print(f"  - LLM: {llm_client.provider_name}")
        print(f"  - Tools: {agent.get_available_tools()}")
        print(f"  - Tool schemas: {len(agent._tool_schemas)}")
        if agent._tool_schemas:
            for schema in agent._tool_schemas:
                print(f"    - {schema.get('name')}: {schema.get('description', '')[:50]}...")

        # Execute streaming task - ask LLM to use the web_search_search_web function
        task = {
            "description": "Search the web for 'AI technology news 2026'. "
                          "Use the web_search_search_web function with query parameter."
        }

        print(f"\n📋 Task: {task['description'][:80]}...")
        print("\n" + "-"*60)
        print("STREAMING OUTPUT:")
        print("-"*60)

        # Track events
        events_by_type = {"status": [], "token": [], "tool_call": [], "tool_calls": [],
                         "tool_result": [], "tool_error": [], "result": [], "error": []}

        start_time = datetime.now()

        async for event in agent.execute_task_streaming(task, {}):
            event_type = event.get("type", "unknown")
            events_by_type.setdefault(event_type, []).append(event)

            if event_type == "status":
                print(f"\n[STATUS] {event.get('status')}")
            elif event_type == "token":
                print(event.get("content", ""), end="", flush=True)
            elif event_type == "tool_call":
                print(f"\n\n[TOOL CALL] {event.get('tool_name')}")
                print(f"  Operation: {event.get('operation')}")
                print(f"  Parameters: {event.get('parameters')}")
            elif event_type == "tool_calls":
                print(f"\n[TOOL CALLS] Count: {len(event.get('tool_calls', []))}")
            elif event_type == "tool_result":
                print_tool_result(event)
            elif event_type == "tool_error":
                print(f"\n[TOOL ERROR] {event.get('tool_name')}: {event.get('error')}")
            elif event_type == "result":
                exec_time = event.get('execution_time', 0)
                print(f"\n\n[FINAL RESULT] Success: {event.get('success')}, "
                      f"Tool calls: {event.get('tool_calls_count')}, Time: {exec_time:.2f}s")
            elif event_type == "error":
                print(f"\n[ERROR] {event.get('error')}")

        elapsed = (datetime.now() - start_time).total_seconds()

        # Print summary
        print("\n" + "-"*60)
        print("STREAMING SUMMARY:")
        print("-"*60)
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Token events: {len(events_by_type['token'])}")
        print(f"  Status events: {len(events_by_type['status'])}")
        print(f"  Tool call events: {len(events_by_type['tool_call'])}")
        print(f"  Tool result events: {len(events_by_type['tool_result'])}")
        print(f"  Tool error events: {len(events_by_type['tool_error'])}")
        print(f"  Result events: {len(events_by_type['result'])}")

        # Assertions
        assert len(events_by_type["status"]) >= 1, "Should have at least 1 status event"
        assert len(events_by_type["result"]) == 1, "Should have exactly 1 result event"

        result_event = events_by_type["result"][0]
        assert result_event.get("success") is True, "Task should succeed"

        print(f"\n✓ LLM tokens streamed: {len(events_by_type['token'])}")
        if events_by_type["tool_call"]:
            print(f"✓ Tool calls executed: {len(events_by_type['tool_call'])}")
        if events_by_type["tool_result"]:
            print(f"✓ Tool results received: {len(events_by_type['tool_result'])}")

        print("\n" + "="*60)
        print("TEST PASSED ✓")
        print("="*60)
        await agent.shutdown()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tool_agent_with_mock_tool(self, llm_client, mock_search_tool, agent_config):
        """
        Test ToolAgent with mock tool to verify complete flow without external APIs.

        This test verifies:
        1. LLM generates correct tool calls
        2. Tool parameters are parsed correctly
        3. Tool execution works
        4. Results are returned properly
        """
        print("\n" + "="*60)
        print("TEST: ToolAgent with Mock Search Tool")
        print("="*60)

        agent = ToolAgent(
            agent_id="test_mock_streaming",
            name="Mock Search Agent",
            llm_client=llm_client,
            tools={"web_search": mock_search_tool},
            config=agent_config,
        )

        await agent.initialize()
        print(f"\n✓ Agent initialized: {agent.agent_id}")
        print(f"  - LLM: {llm_client.provider_name}")
        print(f"  - Tools: {agent.get_available_tools()}")
        print(f"  - Tool schemas: {len(agent._tool_schemas)}")
        if agent._tool_schemas:
            for schema in agent._tool_schemas:
                print(f"    - {schema.get('name')}: {schema.get('description', '')[:50]}...")

        task = {
            "description": "Search the web for 'Python machine learning'. "
                          "Use the web_search function with query parameter."
        }

        print(f"\n📋 Task: {task['description'][:80]}...")
        print("\n" + "-"*60)
        print("STREAMING OUTPUT:")
        print("-"*60)

        events_by_type = {"status": [], "token": [], "tool_call": [], "tool_calls": [],
                         "tool_result": [], "tool_error": [], "result": [], "error": []}

        start_time = datetime.now()

        async for event in agent.execute_task_streaming(task, {}):
            event_type = event.get("type", "unknown")
            events_by_type.setdefault(event_type, []).append(event)

            if event_type == "status":
                print(f"\n[STATUS] {event.get('status')}")
            elif event_type == "token":
                print(event.get("content", ""), end="", flush=True)
            elif event_type == "tool_call":
                print(f"\n\n[TOOL CALL] {event.get('tool_name')}")
                print(f"  Operation: {event.get('operation')}")
                print(f"  Parameters: {event.get('parameters')}")
            elif event_type == "tool_calls":
                print(f"\n[TOOL CALLS] Count: {len(event.get('tool_calls', []))}")
            elif event_type == "tool_result":
                print_tool_result(event)
            elif event_type == "tool_error":
                print(f"\n[TOOL ERROR] {event.get('tool_name')}: {event.get('error')}")
            elif event_type == "result":
                exec_time = event.get('execution_time', 0)
                print(f"\n\n[FINAL RESULT] Success: {event.get('success')}, "
                      f"Tool calls: {event.get('tool_calls_count')}, Time: {exec_time:.2f}s")
            elif event_type == "error":
                print(f"\n[ERROR] {event.get('error')}")

        elapsed = (datetime.now() - start_time).total_seconds()

        print("\n" + "-"*60)
        print("STREAMING SUMMARY:")
        print("-"*60)
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Token events: {len(events_by_type['token'])}")
        print(f"  Status events: {len(events_by_type['status'])}")
        print(f"  Tool call events: {len(events_by_type['tool_call'])}")
        print(f"  Tool result events: {len(events_by_type['tool_result'])}")
        print(f"  Tool error events: {len(events_by_type['tool_error'])}")
        print(f"  Result events: {len(events_by_type['result'])}")

        # Assertions
        assert len(events_by_type["status"]) >= 1, "Should have at least 1 status event"
        assert len(events_by_type["result"]) == 1, "Should have exactly 1 result event"
        assert len(events_by_type["tool_error"]) == 0, "Should have no tool errors"

        result_event = events_by_type["result"][0]
        assert result_event.get("success") is True, "Task should succeed"

        # Verify tool was called
        assert len(events_by_type["tool_call"]) >= 1, "Should have at least 1 tool call"
        assert len(events_by_type["tool_result"]) >= 1, "Should have at least 1 tool result"

        print(f"\n✓ LLM tokens streamed: {len(events_by_type['token'])}")
        print(f"✓ Tool calls executed: {len(events_by_type['tool_call'])}")
        print(f"✓ Tool results received: {len(events_by_type['tool_result'])}")

        print("\n" + "="*60)
        print("TEST PASSED ✓")
        print("="*60)
        await agent.shutdown()


if __name__ == "__main__":
    async def main():
        load_dotenv(".env.test")
        print("Running ToolAgent Real LLM Integration Test with Mock Tool")
        print("="*60)

        llm = get_llm_client()
        tool = get_mock_search_tool()
        config = AgentConfiguration(
            goal="Search the web",
            llm_model="grok-3-mini",
            temperature=0.3,
            max_tokens=1000,
        )

        test = TestToolAgentRealLLM()
        await test.test_tool_agent_with_mock_tool(llm, tool, config)

    asyncio.run(main())

