"""
E2E Tests for Anthropic (Claude) on Vertex AI Integration

Performs real Anthropic API calls through ``AsyncAnthropicVertex`` using the
Google Cloud credentials configured in ``.env.test``.  The test passes only
when a complete, non-empty response is received from Claude.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from test.e2e.base import E2ELLMTestBase, log_test_info


# Load .env.test explicitly (the shared conftest only loads .env).
_ENV_TEST = Path(__file__).resolve().parents[2].parent / ".env.test"
if _ENV_TEST.exists():
    load_dotenv(_ENV_TEST, override=True)


@pytest.fixture(scope="session")
def anthropic_vertex_config():
    """Resolve Anthropic-on-Vertex credentials from the environment."""
    project_id = os.getenv("VERTEX_PROJECT_ID_ANTHROPIC") or os.getenv("VERTEX_PROJECT_ID")
    location = os.getenv("VERTEX_LOCATION_ANTHROPIC") or os.getenv("VERTEX_LOCATION")
    credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_VERTEX_ANTHROPIC") or os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )

    if not project_id:
        pytest.skip("VERTEX_PROJECT_ID_ANTHROPIC or VERTEX_PROJECT_ID not set in environment")
    if not location:
        pytest.skip("VERTEX_LOCATION_ANTHROPIC or VERTEX_LOCATION not set in environment")
    if not credentials or not Path(credentials).exists():
        pytest.skip(
            "GOOGLE_APPLICATION_CREDENTIALS_VERTEX_ANTHROPIC or GOOGLE_APPLICATION_CREDENTIALS file not found"
        )

    return {
        "project_id": project_id,
        "location": location,
        "credentials": credentials,
    }


@pytest.mark.e2e
@pytest.mark.requires_api
class TestAnthropicVertexE2E(E2ELLMTestBase):
    """E2E tests for Claude on Vertex AI."""

    @pytest.fixture(autouse=True)
    def setup(self, anthropic_vertex_config, cost_tracker):
        """Configure the AnthropicVertex client for each test."""
        self.project_id = anthropic_vertex_config["project_id"]
        self.location = anthropic_vertex_config["location"]
        self.cost_tracker = cost_tracker
        # Vertex partner model id (see Google Cloud “Request predictions with Claude models”).
        self.model = "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_anthropic_vertex_complete_response(self):
        """Verify that AnthropicVertexClient returns a complete Claude response."""
        log_test_info(
            "Anthropic on Vertex - Complete Response",
            model=self.model,
            project=self.project_id,
            location=self.location,
        )

        try:
            from aiecs.llm.clients.anthropic_client import AnthropicVertexClient
            from aiecs.llm.clients.base_client import LLMMessage, LLMResponse
        except ImportError as e:
            pytest.skip(f"Anthropic Vertex client not available: {e}")

        client = AnthropicVertexClient()
        messages = [
            LLMMessage(role="user", content="Reply with just the word: OK"),
        ]

        try:
            response, latency = await self.measure_latency_async(
                client.generate_text,
                messages=messages,
                model=self.model,
                temperature=0.0,
                max_tokens=32,
            )
        except Exception as e:
            pytest.fail(f"Anthropic Vertex API call failed: {e}")

        assert isinstance(response, LLMResponse), \
            f"Expected LLMResponse, got {type(response).__name__}"
        assert response.provider == "AnthropicVertex"
        assert response.model == self.model

        self.assert_llm_response_valid(response.content)
        assert latency < 30.0, f"Response took {latency:.2f}s (should be < 30s)"

        assert response.prompt_tokens is not None and response.prompt_tokens > 0, \
            "Expected prompt_tokens to be reported by Anthropic"
        assert response.completion_tokens is not None and response.completion_tokens > 0, \
            "Expected completion_tokens to be reported by Anthropic"

        stop_reason = (response.metadata or {}).get("stop_reason")
        assert stop_reason in ("end_turn", "stop_sequence", "max_tokens"), \
            f"Unexpected stop_reason: {stop_reason!r}"

        self.cost_tracker.record_call(
            provider="AnthropicVertex",
            model=self.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cost=response.cost_estimate or 0.0,
        )

        print(f"\n✅ Anthropic Vertex response received in {latency:.2f}s")
        print(f"📝 Content: {response.content!r}")
        print(
            f"🔢 Tokens: prompt={response.prompt_tokens}, "
            f"completion={response.completion_tokens}"
        )
        print(f"🛑 stop_reason={stop_reason}")
        if response.cost_estimate is not None:
            print(f"💵 Estimated cost: ${response.cost_estimate:.6f}")
