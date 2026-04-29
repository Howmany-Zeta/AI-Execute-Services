"""
Integration Test for VertexMaaSClient

Tests Vertex AI MaaS (Model-as-a-Service) client with real API calls.
Uses GCP credentials from .env.test.

Requirements:
- VERTEX_PROJECT_ID must be set in .env.test
- GOOGLE_APPLICATION_CREDENTIALS must point to a valid service-account key
  that has the Vertex AI MaaS models enabled in Model Garden
- Real LLM calls will be made (costs may apply)

Note:
  .env.test sets VERTEX_LOCATION=us-east5 (configured for Claude/Anthropic).
  Grok models on Vertex AI MaaS are available in us-central1, so this file
  overrides VERTEX_LOCATION to us-central1 before constructing the client.
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

from aiecs.llm.clients.vertex_maas_client import VertexMaaSClient
from aiecs.llm.clients.base_client import LLMMessage, LLMResponse

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
env_test_path = PROJECT_ROOT / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)
    print(f"✓ Loaded test environment from {env_test_path}")
else:
    print(f"⚠ .env.test not found at {env_test_path}")

# Grok partner models on Vertex AI are only available via the global endpoint.
# Override the Claude-specific region (us-east5) set in .env.test.
os.environ["VERTEX_LOCATION"] = "global"

# ---------------------------------------------------------------------------
# Model under test
# ---------------------------------------------------------------------------
_MODEL = "grok-4.1-fast-non-reasoning"

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def maas_client():
    """Create and yield a VertexMaaSClient, closing it after the test."""
    client = VertexMaaSClient()
    yield client
    await client.close()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _simple_messages(text: str = "Reply with exactly one word: hello") -> list:
    return [LLMMessage(role="user", content=text)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_text_returns_real_reply(maas_client):
    """generate_text must return a non-empty reply from the model."""
    print(f"\n=== Test: generate_text ({_MODEL}) ===")

    response = await maas_client.generate_text(
        messages=_simple_messages(),
        model=_MODEL,
        max_tokens=64,
    )

    assert isinstance(response, LLMResponse), "Response must be an LLMResponse"
    assert response.content, "Response content must not be empty"
    assert response.provider == "VertexMaaS"
    assert response.model == _MODEL

    print(f"✓ provider : {response.provider}")
    print(f"✓ model    : {response.model}")
    print(f"✓ content  : {response.content}")
    print(f"✓ tokens   : prompt={response.prompt_tokens} completion={response.completion_tokens}")


@pytest.mark.asyncio
async def test_generate_text_inline_price_bypasses_yaml(maas_client):
    """Inline input_price/output_price must be used instead of llm_models.yaml."""
    print(f"\n=== Test: generate_text with inline price ({_MODEL}) ===")

    input_price = 1.0   # $1 / 1K input tokens
    output_price = 3.0  # $3 / 1K output tokens

    response = await maas_client.generate_text(
        messages=_simple_messages(),
        model=_MODEL,
        max_tokens=64,
        input_price=input_price,
        output_price=output_price,
    )

    assert response.content, "Response content must not be empty"

    # Verify cost was calculated from inline prices, not yaml (yaml has 0.0).
    if response.prompt_tokens and response.completion_tokens:
        expected = (
            response.prompt_tokens * input_price + response.completion_tokens * output_price
        ) / 1000
        assert response.cost_estimate == pytest.approx(expected, rel=1e-6), (
            f"cost_estimate {response.cost_estimate} does not match inline-price calculation {expected}"
        )

    print(f"✓ content       : {response.content}")
    print(f"✓ cost_estimate : ${response.cost_estimate:.6f}")


@pytest.mark.asyncio
async def test_stream_text_returns_real_reply(maas_client):
    """stream_text must yield at least one non-empty token from the model."""
    print(f"\n=== Test: stream_text ({_MODEL}) ===")

    chunks: list[str] = []
    async for chunk in maas_client.stream_text(
        messages=_simple_messages("Say hello in one sentence."),
        model=_MODEL,
        max_tokens=64,
    ):
        if isinstance(chunk, str) and chunk:
            chunks.append(chunk)
            print(chunk, end="", flush=True)

    print()  # newline after streamed output

    assert chunks, "Stream must yield at least one non-empty text chunk"
    full_text = "".join(chunks)
    assert full_text.strip(), "Concatenated stream content must not be blank"

    print(f"✓ received {len(chunks)} chunk(s), total length={len(full_text)}")
