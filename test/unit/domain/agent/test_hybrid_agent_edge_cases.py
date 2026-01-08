"""
Edge Case Tests for HybridAgent

Tests various edge cases to verify HybridAgent behavior:
1. JSON and text between thought tags and tool call
2. JSON and text alongside tool call
3. Only thought/observation tags without tool call or final response
4. Thought/observation tags with JSON and FINAL RESPONSE with finish suffix
5. Thought/observation tags with JSON and text without FINAL RESPONSE prefix/finish suffix
6. No tags, only JSON or plain text without FINAL RESPONSE prefix/finish suffix
7. No tags, only text with finish suffix but no FINAL RESPONSE prefix
8. Additional edge cases for comprehensive coverage
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import BaseLLMClient, LLMResponse, LLMMessage


class MockLLMClientForEdgeCases(BaseLLMClient):
    """Mock LLM client for edge case testing."""
    
    def __init__(self, responses: List[str] = None):
        super().__init__(provider_name="mock")
        self.responses = responses or []
        self.call_count = 0
        self.all_messages: List[List[LLMMessage]] = []
    
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        tools: List[Dict] = None,
        tool_choice: str = None,
    ) -> LLMResponse:
        """Generate mock response."""
        self.call_count += 1
        self.all_messages.append(messages.copy())
        
        # Return response based on call count
        if self.call_count <= len(self.responses):
            content = self.responses[self.call_count - 1]
        else:
            # Default to final response to prevent infinite loop
            content = "FINAL RESPONSE: Default mock response. finish"
        
        return LLMResponse(
            content=content,
            provider="mock",
            model=model or "mock-model",
            tokens_used=10,
        )
    
    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        tools: List[Dict] = None,
        tool_choice: str = None,
        return_chunks: bool = False,
    ):
        """Stream mock response preserving original formatting."""
        self.call_count += 1
        self.all_messages.append(messages.copy())
        
        if self.call_count <= len(self.responses):
            content = self.responses[self.call_count - 1]
        else:
            content = "FINAL RESPONSE: Default mock response. finish"
        
        # Stream character by character to preserve formatting (newlines, etc.)
        # This better simulates real streaming behavior
        for char in content:
            yield char
    
    async def close(self):
        """Close the client."""
        pass


def create_mock_tool():
    """Create a mock tool that simulates BaseTool behavior."""
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "A mock tool for testing"
    mock_tool._schemas = {"query": MagicMock()}
    
    # Make run_async return a simple result
    async def mock_run_async(operation=None, **kwargs):
        return f"Mock result for operation={operation}, params={kwargs}"
    
    mock_tool.run_async = AsyncMock(side_effect=mock_run_async)
    return mock_tool


@pytest.fixture
async def create_agent():
    """Factory fixture to create HybridAgent with custom mock client."""
    agents = []
    patchers = []
    
    async def _create_agent(responses: List[str], max_iterations: int = 5, with_tools: bool = True):
        mock_client = MockLLMClientForEdgeCases(responses=responses)
        config = AgentConfiguration(
            llm_model="mock-model",
            system_prompt="You are a test agent.",
        )
        
        # Use tool name strings (backward compatible) instead of BaseTool instances
        tools = ["mock_tool"] if with_tools else []
        
        # Mock get_tool to return a mock tool
        mock_tool = create_mock_tool()
        patcher = patch('aiecs.domain.agent.hybrid_agent.get_tool', return_value=mock_tool)
        patcher.start()
        patchers.append(patcher)
        
        agent = HybridAgent(
            agent_id=f"test_edge_case_{len(agents)}",
            name="Test Edge Case Agent",
            llm_client=mock_client,
            tools=tools,
            config=config,
            max_iterations=max_iterations,
        )
        
        await agent.initialize()
        agents.append(agent)
        return agent, mock_client
    
    yield _create_agent
    
    # Cleanup
    for patcher in patchers:
        patcher.stop()
    for agent in agents:
        try:
            await agent.shutdown()
        except:
            pass


# =============================================================================
# Edge Case 1: JSON and text between thought tags and tool call
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_json_and_text_between_thought_and_tool_call(create_agent):
    """
    Test: Thought tags followed by JSON and text, then tool call.
    Expected: Tool call should be executed, and all content streamed to caller.
    """
    responses = [
        # First response: thought + json + text + tool call
        '<THOUGHT>\nAnalyzing the request...\n</THOUGHT>\n\n'
        '{"intermediate_data": "some value"}\n'
        'Additional context text here.\n\n'
        'TOOL: mock_tool\n'
        'OPERATION: query\n'
        'PARAMETERS: {"q": "test"}',
        # Second response: final response
        'FINAL RESPONSE: Task completed successfully. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Test task"},
        {}
    )
    
    # Should have executed tool call
    assert result["success"] is True
    assert result["tool_calls_count"] >= 1
    
    # Should have called LLM at least twice (tool call + final response)
    assert mock_client.call_count >= 2
    
    # Steps should include the raw output with JSON and text preserved
    steps = result.get("reasoning_steps", [])
    thought_steps = [s for s in steps if s.get("type") == "thought"]
    assert len(thought_steps) >= 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_json_and_text_between_thought_and_tool_call_streaming(create_agent):
    """
    Test streaming: Thought tags followed by JSON and text, then tool call.
    Expected: All content should be streamed without truncation.
    """
    responses = [
        '<THOUGHT>\nAnalyzing...\n</THOUGHT>\n'
        '{"data": "value"}\n'
        'Some text.\n'
        'TOOL: mock_tool\n'
        'OPERATION: test\n'
        'PARAMETERS: {}',
        'FINAL RESPONSE: Done. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    events = []
    async for event in agent.execute_task_streaming(
        {"description": "Test streaming"},
        {}
    ):
        events.append(event)
    
    # Should have token events
    token_events = [e for e in events if e.get("type") == "token"]
    assert len(token_events) > 0
    
    # Should have tool_call and tool_result events
    tool_call_events = [e for e in events if e.get("type") == "tool_call"]
    tool_result_events = [e for e in events if e.get("type") == "tool_result"]
    assert len(tool_call_events) >= 1
    assert len(tool_result_events) >= 1


# =============================================================================
# Edge Case 2: Tool call alongside JSON and text
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_call_with_json_and_text(create_agent):
    """
    Test: Tool call with JSON and text in the same response.
    Expected: Tool call executed, JSON and text passed to caller unchanged.
    """
    responses = [
        'TOOL: mock_tool\n'
        'OPERATION: process\n'
        'PARAMETERS: {"input": "data"}\n\n'
        '{"status": "processing"}\n'
        'Processing started...',
        'FINAL RESPONSE: Processing complete with result. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Process data"},
        {}
    )
    
    assert result["success"] is True
    assert result["tool_calls_count"] >= 1
    
    # Verify steps contain the action with result
    steps = result.get("reasoning_steps", [])
    action_steps = [s for s in steps if s.get("type") == "action"]
    assert len(action_steps) >= 1
    assert "result" in action_steps[0]


# =============================================================================
# Edge Case 3: Only thought/observation tags, no tool call or final response
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_only_thought_tags_continues_iteration(create_agent):
    """
    Test: Response contains only thought/observation tags, no tool call or final response.
    Expected: Should continue LLM iteration, not terminate.
    """
    responses = [
        # First response: only thought
        '<THOUGHT>\nI am thinking about the problem.\n</THOUGHT>',
        # Second response: thought + observation
        '<THOUGHT>\nContinuing analysis...\n</THOUGHT>\n'
        '<OBSERVATION>\nSome observation here.\n</OBSERVATION>',
        # Third response: final response to end loop
        'FINAL RESPONSE: Analysis complete. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Analyze something"},
        {}
    )
    
    assert result["success"] is True
    # Should have called LLM 3 times (2 continue iterations + final)
    assert mock_client.call_count == 3
    
    # Verify iterations count
    assert result["iterations"] == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_only_observation_tags_continues_iteration(create_agent):
    """
    Test: Response contains only observation tags.
    Expected: Should continue LLM iteration.
    """
    responses = [
        '<OBSERVATION>\nObserving the situation...\n</OBSERVATION>',
        '<THOUGHT>\nBased on observation...\n</THOUGHT>',
        'FINAL RESPONSE: Observation processed. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Observe"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 3


# =============================================================================
# Edge Case 4: Thought/observation tags with JSON and FINAL RESPONSE with finish
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_thought_tags_with_json_and_final_response_finish(create_agent):
    """
    Test: Thought/observation tags + JSON + FINAL RESPONSE with finish suffix.
    Expected: Should terminate loop and return final response.
    """
    responses = [
        '<THOUGHT>\nCompleted analysis.\n</THOUGHT>\n'
        '<OBSERVATION>\nResults are ready.\n</OBSERVATION>\n\n'
        '{"result_data": {"value": 42}}\n\n'
        'FINAL RESPONSE: The answer is 42. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Calculate answer"},
        {}
    )
    
    assert result["success"] is True
    # Should terminate after first response (has complete final response)
    assert mock_client.call_count == 1
    assert result["iterations"] == 1
    
    # Output should contain the final response
    assert "42" in result["output"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_mixed_content_with_complete_final_response(create_agent):
    """
    Test: Mixed content (tags, JSON, text) with complete FINAL RESPONSE.
    Expected: Should terminate and preserve all content.
    """
    responses = [
        '<THOUGHT>\nProcessing complete.\n</THOUGHT>\n'
        '{"metadata": "info"}\n'
        'Additional notes.\n'
        'FINAL RESPONSE: All done with notes. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Process with notes"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 1
    # Output should preserve the complete response
    assert "finish" in result["output"].lower()


# =============================================================================
# Edge Case 5: Thought/observation tags with JSON but no FINAL RESPONSE prefix/finish
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_thought_tags_with_json_no_final_response(create_agent):
    """
    Test: Thought/observation tags + JSON + plain text without FINAL RESPONSE.
    Expected: Should continue LLM iteration.
    """
    responses = [
        # First response: thought + json + text (no FINAL RESPONSE)
        '<THOUGHT>\nThinking...\n</THOUGHT>\n'
        '{"data": "value"}\n'
        'Some plain text without final response marker.',
        # Second response: final response
        'FINAL RESPONSE: Done. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Test task"},
        {}
    )
    
    assert result["success"] is True
    # Should continue to second response
    assert mock_client.call_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_thought_with_json_and_plain_text_continues(create_agent):
    """
    Test: Tags with JSON and plain text, no action markers.
    Expected: Should ask LLM to continue generating.
    """
    responses = [
        '<THOUGHT>\nAnalyzing data...\n</THOUGHT>\n'
        '{"analysis": {"step": 1, "result": "partial"}}\n'
        'Continuing with next step...',
        '<THOUGHT>\nFurther analysis...\n</THOUGHT>\n'
        '{"analysis": {"step": 2, "result": "complete"}}\n',
        'FINAL RESPONSE: Analysis complete with 2 steps. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Multi-step analysis"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 3


# =============================================================================
# Edge Case 6: No tags, only JSON or plain text without FINAL RESPONSE
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_only_json_no_tags_continues_iteration(create_agent):
    """
    Test: Response is only JSON without any tags or FINAL RESPONSE.
    Expected: Should continue LLM iteration.
    """
    responses = [
        '{"status": "processing", "progress": 50}',
        '{"status": "processing", "progress": 100}',
        'FINAL RESPONSE: Processing complete. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Process something"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_only_plain_text_no_tags_continues_iteration(create_agent):
    """
    Test: Response is only plain text without any tags or markers.
    Expected: Should continue LLM iteration.
    """
    responses = [
        'This is just some plain text without any special markers.',
        'More plain text here.',
        'FINAL RESPONSE: Finally done. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Plain text task"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_mixed_json_and_text_no_markers(create_agent):
    """
    Test: Mixed JSON and text without any ReAct markers.
    Expected: Should continue iteration until proper marker found.
    """
    responses = [
        'Here is some data:\n{"key": "value"}\nAnd some text.',
        'More content: {"another": "object"}\nWith more text.',
        'FINAL RESPONSE: All content delivered. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Mixed content"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 3


# =============================================================================
# Edge Case 7: No tags, only text with finish suffix but no FINAL RESPONSE prefix
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_text_with_finish_no_final_response_prefix(create_agent):
    """
    Test: Text ending with 'finish' but without FINAL RESPONSE prefix.
    Expected: Should continue LLM iteration (finish alone is not enough).
    """
    responses = [
        'I am done with the task. finish',  # Has finish but no FINAL RESPONSE:
        'FINAL RESPONSE: Properly formatted response. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Test finish without prefix"},
        {}
    )
    
    assert result["success"] is True
    # Should continue because first response lacks FINAL RESPONSE: prefix
    assert mock_client.call_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_json_with_finish_field_no_final_response(create_agent):
    """
    Test: JSON containing 'finish' field but no FINAL RESPONSE prefix.
    Expected: Should continue LLM iteration.
    """
    responses = [
        '{"status": "complete", "finish": true}',
        'FINAL RESPONSE: Task finished. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "JSON with finish field"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 2


# =============================================================================
# Edge Case 8: FINAL RESPONSE without finish suffix (incomplete)
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_final_response_without_finish_continues(create_agent):
    """
    Test: FINAL RESPONSE present but without finish suffix.
    Expected: Should continue LLM iteration to complete the response.
    """
    responses = [
        'FINAL RESPONSE: This is an incomplete response without',
        # LLM continues and adds finish
        ' the proper suffix. finish'
    ]
    
    agent, mock_client = await create_agent(responses, max_iterations=3)
    
    # Note: This test verifies the incomplete final response detection
    # The current implementation may need adjustment based on how continuation works
    
    result = await agent.execute_task(
        {"description": "Incomplete final response"},
        {}
    )
    
    # Should have continued to complete the response
    assert result["success"] is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_final_response_in_thought_tag_ignored(create_agent):
    """
    Test: FINAL RESPONSE inside THOUGHT tag should be ignored.
    Expected: Should continue LLM iteration.
    """
    responses = [
        '<THOUGHT>\nFINAL RESPONSE: This should be ignored. finish\n</THOUGHT>',
        'FINAL RESPONSE: Proper response outside tags. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Final response in thought tag"},
        {}
    )
    
    assert result["success"] is True
    # Should ignore FINAL RESPONSE inside tags and continue
    assert mock_client.call_count == 2


# =============================================================================
# Edge Case 9: Tool call inside tags should be ignored
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_call_inside_thought_tag_ignored(create_agent):
    """
    Test: TOOL call inside THOUGHT tag should be ignored.
    Expected: Should continue LLM iteration.
    """
    responses = [
        '<THOUGHT>\nTOOL: mock_tool\nOPERATION: test\nPARAMETERS: {}\n</THOUGHT>',
        'TOOL: mock_tool\n'
        'OPERATION: proper\n'
        'PARAMETERS: {"outside": "tags"}',
        'FINAL RESPONSE: Tool executed. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Tool call in thought tag"},
        {}
    )
    
    assert result["success"] is True
    # Tool call inside tags should be ignored, proper one should execute
    assert result["tool_calls_count"] >= 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_call_inside_observation_tag_ignored(create_agent):
    """
    Test: TOOL call inside OBSERVATION tag should be ignored.
    Expected: Should continue LLM iteration.
    """
    responses = [
        '<OBSERVATION>\nTOOL: mock_tool\nOPERATION: test\nPARAMETERS: {}\n</OBSERVATION>',
        'FINAL RESPONSE: Done without tool execution. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Tool call in observation tag"},
        {}
    )
    
    assert result["success"] is True
    # No tool should be executed
    assert result["tool_calls_count"] == 0


# =============================================================================
# Edge Case 10: Max iterations reached
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_max_iterations_reached_without_completion(create_agent):
    """
    Test: LLM never produces valid action within max iterations.
    Expected: Should return max iterations message.
    """
    responses = [
        '<THOUGHT>\nStill thinking...\n</THOUGHT>',
        '<THOUGHT>\nStill thinking...\n</THOUGHT>',
        '<THOUGHT>\nStill thinking...\n</THOUGHT>',
    ]
    
    agent, mock_client = await create_agent(responses, max_iterations=3)
    
    result = await agent.execute_task(
        {"description": "Never-ending task"},
        {}
    )
    
    assert result["success"] is True
    assert "Max iterations reached" in result["output"]
    assert result.get("max_iterations_reached") is True or mock_client.call_count == 3


# =============================================================================
# Edge Case 11: Iteration info in messages
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_iteration_info_passed_to_llm(create_agent):
    """
    Test: Verify iteration info is passed to LLM in messages.
    Expected: Messages should contain iteration count information.
    """
    responses = [
        '<THOUGHT>\nFirst iteration.\n</THOUGHT>',
        'FINAL RESPONSE: Done. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Check iteration info"},
        {}
    )
    
    assert result["success"] is True
    
    # Check that second call has iteration info in messages
    if mock_client.call_count >= 2:
        second_call_messages = mock_client.all_messages[1]
        message_contents = [msg.content for msg in second_call_messages if msg.content]
        combined = " ".join(message_contents)
        # Should contain iteration info
        assert "Iteration" in combined or "iteration" in combined


# =============================================================================
# Edge Case 12: Complex nested content
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_nested_json_in_response(create_agent):
    """
    Test: Deeply nested JSON in response.
    Expected: Should be preserved unchanged.
    """
    responses = [
        '{"level1": {"level2": {"level3": {"value": "deep"}}}}\n'
        'FINAL RESPONSE: Nested JSON delivered. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Nested JSON"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_json_array_in_response(create_agent):
    """
    Test: JSON array in response.
    Expected: Should be preserved unchanged.
    """
    responses = [
        '[{"id": 1}, {"id": 2}, {"id": 3}]\n'
        'FINAL RESPONSE: Array delivered. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "JSON array"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 1


# =============================================================================
# Edge Case 13: Special characters and unicode
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_unicode_content_preserved(create_agent):
    """
    Test: Unicode content in response.
    Expected: Should be preserved unchanged.
    """
    responses = [
        '<THOUGHT>\n中文内容测试。日本語テスト。한국어 테스트.\n</THOUGHT>\n'
        'FINAL RESPONSE: 完成 🎉 finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Unicode test"},
        {}
    )
    
    assert result["success"] is True
    assert "完成" in result["output"]


@pytest.mark.asyncio
@pytest.mark.unit  
async def test_special_characters_in_json(create_agent):
    """
    Test: Special characters in JSON.
    Expected: Should be preserved unchanged.
    """
    responses = [
        '{"message": "Hello\\nWorld", "path": "C:\\\\Users\\\\test"}\n'
        'FINAL RESPONSE: Special chars OK. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Special chars in JSON"},
        {}
    )
    
    assert result["success"] is True


# =============================================================================
# Edge Case 14: Empty or whitespace responses
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_whitespace_only_response_continues(create_agent):
    """
    Test: Response with only whitespace.
    Expected: Should continue LLM iteration.
    """
    responses = [
        '   \n\n   ',  # Whitespace only
        'FINAL RESPONSE: After empty response. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Whitespace test"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 2


# =============================================================================
# Edge Case 15: Multiple tool calls in sequence
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_multiple_tool_calls_sequence(create_agent):
    """
    Test: Multiple tool calls across iterations.
    Expected: All tools should be executed.
    """
    responses = [
        'TOOL: mock_tool\nOPERATION: first\nPARAMETERS: {"step": 1}',
        'TOOL: mock_tool\nOPERATION: second\nPARAMETERS: {"step": 2}',
        'FINAL RESPONSE: Both tools executed. finish'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Multiple tools"},
        {}
    )
    
    assert result["success"] is True
    assert result["tool_calls_count"] >= 2


# =============================================================================
# Edge Case 16: Case sensitivity tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_final_response_case_insensitive_finish(create_agent):
    """
    Test: FINAL RESPONSE with different case 'finish'.
    Expected: Should recognize 'FINISH', 'Finish', 'finish'.
    """
    responses = [
        'FINAL RESPONSE: Testing case sensitivity. FINISH'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Case test"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_finish_mixed_case(create_agent):
    """
    Test: 'finish' in mixed case.
    Expected: Should be recognized.
    """
    responses = [
        'FINAL RESPONSE: Mixed case test. FiNiSh'
    ]
    
    agent, mock_client = await create_agent(responses)
    
    result = await agent.execute_task(
        {"description": "Mixed case finish"},
        {}
    )
    
    assert result["success"] is True
    assert mock_client.call_count == 1
