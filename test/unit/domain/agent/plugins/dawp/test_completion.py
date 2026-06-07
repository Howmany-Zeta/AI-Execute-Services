"""
Unit tests for aiecs/domain/agent/plugins/dawp/completion.py (D0-04).

Required coverage (per task spec):
- Token inside ``` fence MUST NOT trigger
- Token in blockquote MUST NOT trigger
- Token inside <thinking> MUST NOT trigger
- Wrong Prompt Marker on final step → continue (not complete run)

Additional coverage:
- validate_marker: format, length, uniqueness
- _visible_assistant_text: thinking stripping
- iter_scannable_lines: fence state machine, blockquote skip
- marker_detected: whole-line exact match only
- prompt_step_complete: all branches of the state machine
- matches_response_trigger: trigger_once guard, re-trigger prevention
"""

import pytest

from aiecs.domain.agent.plugins.dawp.completion import (
    _visible_assistant_text,
    iter_scannable_lines,
    marker_detected,
    matches_response_trigger,
    prompt_step_complete,
    validate_marker,
)


# ---------------------------------------------------------------------------
# validate_marker
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateMarker:
    def test_valid_marker(self):
        validate_marker("prompt_marker", "<STEP_DONE>")  # no exception

    def test_valid_marker_with_numbers(self):
        validate_marker("m", "<OODA_STEP_DONE_2>")

    def test_exceeds_25_chars_raises(self):
        with pytest.raises(ValueError, match="exceeds 25 chars"):
            validate_marker("m", "<" + "A" * 24 + ">")  # 27 chars

    def test_exactly_25_chars_accepted(self):
        validate_marker("m", "<" + "A" * 23 + ">")  # 25 chars

    def test_lowercase_raises(self):
        with pytest.raises(ValueError, match="must match"):
            validate_marker("m", "<step_done>")

    def test_no_brackets_raises(self):
        with pytest.raises(ValueError, match="must match"):
            validate_marker("m", "STEP_DONE")

    def test_space_in_token_raises(self):
        with pytest.raises(ValueError, match="must match"):
            validate_marker("m", "<STEP DONE>")

    def test_same_as_other_raises(self):
        with pytest.raises(ValueError, match="must differ"):
            validate_marker("prompt_marker", "<SAME>", other="<SAME>")

    def test_different_from_other_accepted(self):
        validate_marker("prompt_marker", "<STEP_DONE>", other="<DAWP_HANDOFF>")  # no exception


# ---------------------------------------------------------------------------
# _visible_assistant_text
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVisibleAssistantText:
    def test_no_thinking_block_unchanged(self):
        text = "Hello world.\n<STEP_DONE>"
        assert _visible_assistant_text(text) == text

    def test_single_thinking_block_stripped(self):
        text = "<thinking>internal reasoning</thinking>\n<STEP_DONE>"
        result = _visible_assistant_text(text)
        assert "internal reasoning" not in result
        assert "<STEP_DONE>" in result

    def test_multiple_thinking_blocks_stripped(self):
        text = "<thinking>first</thinking>visible<thinking>second</thinking>also visible"
        result = _visible_assistant_text(text)
        assert "first" not in result
        assert "second" not in result
        assert "visible" in result
        assert "also visible" in result

    def test_case_insensitive_thinking(self):
        text = "<THINKING>hidden</THINKING>\nvisible"
        result = _visible_assistant_text(text)
        assert "hidden" not in result
        assert "visible" in result

    def test_multiline_thinking_stripped(self):
        text = "<thinking>\nline1\nline2\n</thinking>\nafter"
        result = _visible_assistant_text(text)
        assert "line1" not in result
        assert "after" in result

    def test_marker_only_in_thinking_is_stripped(self):
        text = "<thinking><STEP_DONE></thinking>\nother content"
        result = _visible_assistant_text(text)
        assert "<STEP_DONE>" not in result


# ---------------------------------------------------------------------------
# iter_scannable_lines
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIterScannableLines:
    def _collect(self, text: str) -> list[str]:
        return list(iter_scannable_lines(text))

    def test_plain_lines_all_yielded(self):
        text = "line one\nline two\nline three"
        assert self._collect(text) == ["line one", "line two", "line three"]

    def test_fenced_block_skipped(self):
        text = "before\n```\ninside fence\n```\nafter"
        lines = self._collect(text)
        assert "inside fence" not in lines
        assert "before" in lines
        assert "after" in lines

    def test_fence_toggle_opens_and_closes(self):
        text = "a\n```\nhidden\n```\nb\n```\nalso hidden\n```\nc"
        lines = self._collect(text)
        assert lines == ["a", "b", "c"]

    def test_fenced_block_with_language_tag(self):
        text = "x\n```python\ncode\n```\ny"
        lines = self._collect(text)
        assert "code" not in lines
        assert "x" in lines
        assert "y" in lines

    def test_blockquote_line_skipped(self):
        text = "normal\n> quoted line\nalso normal"
        lines = self._collect(text)
        assert "quoted line" not in [l.lstrip("> ") for l in lines]
        assert "> quoted line" not in lines
        assert "normal" in lines
        assert "also normal" in lines

    def test_blockquote_with_leading_spaces_skipped(self):
        text = "normal\n  > indented quote\nnormal"
        lines = self._collect(text)
        assert "indented quote" not in " ".join(lines)

    def test_marker_in_fence_not_yielded(self):
        """Core requirement: token inside ``` fence MUST NOT trigger."""
        text = "before\n```\n<STEP_DONE>\n```\nafter"
        lines = self._collect(text)
        assert "<STEP_DONE>" not in lines

    def test_marker_in_blockquote_not_yielded(self):
        """Core requirement: token in blockquote MUST NOT trigger."""
        text = "before\n> <STEP_DONE>\nafter"
        lines = self._collect(text)
        assert "<STEP_DONE>" not in lines

    def test_unclosed_fence_treats_rest_as_inside(self):
        """An unclosed fence block swallows everything until EOF."""
        text = "before\n```\nhidden\nalso hidden"
        lines = self._collect(text)
        assert "hidden" not in lines
        assert "also hidden" not in lines
        assert "before" in lines

    def test_lines_are_stripped(self):
        text = "  padded line  \nnormal"
        lines = self._collect(text)
        assert "padded line" in lines  # stripped


# ---------------------------------------------------------------------------
# marker_detected
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMarkerDetected:
    def test_exact_line_match(self):
        assert marker_detected("some text\n<STEP_DONE>\nmore", "<STEP_DONE>") is True

    def test_substring_does_not_match(self):
        assert marker_detected("prefix <STEP_DONE> suffix", "<STEP_DONE>") is False

    def test_marker_inside_fence_not_detected(self):
        """Core requirement: token inside ``` fence MUST NOT trigger."""
        text = "ok\n```\n<STEP_DONE>\n```\ndone"
        assert marker_detected(text, "<STEP_DONE>") is False

    def test_marker_in_blockquote_not_detected(self):
        """Core requirement: token in blockquote MUST NOT trigger."""
        text = "ok\n> <STEP_DONE>\ndone"
        assert marker_detected(text, "<STEP_DONE>") is False

    def test_marker_in_thinking_not_detected(self):
        """Core requirement: token inside <thinking> MUST NOT trigger."""
        text = "<thinking>\n<STEP_DONE>\n</thinking>\nactual output"
        # marker_detected receives visible text; caller must strip thinking first
        # Here we test the full pipeline by calling marker_detected on stripped text
        from aiecs.domain.agent.plugins.dawp.completion import _visible_assistant_text
        visible = _visible_assistant_text(text)
        assert marker_detected(visible, "<STEP_DONE>") is False

    def test_not_present_returns_false(self):
        assert marker_detected("some other text", "<STEP_DONE>") is False

    def test_empty_text_returns_false(self):
        assert marker_detected("", "<STEP_DONE>") is False

    def test_marker_last_line(self):
        assert marker_detected("text\n<DAWP_HANDOFF>", "<DAWP_HANDOFF>") is True

    def test_marker_only_line(self):
        assert marker_detected("<STEP_DONE>", "<STEP_DONE>") is True

    def test_different_marker_not_matched(self):
        assert marker_detected("text\n<STEP_DONE>", "<DAWP_HANDOFF>") is False


# ---------------------------------------------------------------------------
# prompt_step_complete state machine
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptStepComplete:
    # --- non-last step ---

    def test_non_last_prompt_marker_seen_returns_prompt_done(self):
        result = prompt_step_complete(
            "analysis done.\n<STEP_DONE>",
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=False,
        )
        assert result == "prompt_done"

    def test_non_last_dawp_marker_seen_returns_dawp_done(self):
        """Non-last step may emit dawp_marker for early handoff."""
        result = prompt_step_complete(
            "early done.\n<DAWP_HANDOFF>",
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=False,
        )
        assert result == "dawp_done"

    def test_non_last_no_marker_returns_continue(self):
        result = prompt_step_complete(
            "still working...",
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=False,
        )
        assert result == "continue"

    def test_non_last_marker_in_fence_returns_continue(self):
        """Token inside fence must not trigger on non-last step."""
        text = "analysis:\n```\n<STEP_DONE>\n```\nstill going"
        result = prompt_step_complete(
            text,
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=False,
        )
        assert result == "continue"

    def test_non_last_marker_in_blockquote_returns_continue(self):
        """Token in blockquote must not trigger on non-last step."""
        text = "> <STEP_DONE>\nstill going"
        result = prompt_step_complete(
            text,
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=False,
        )
        assert result == "continue"

    def test_non_last_marker_in_thinking_returns_continue(self):
        """Token inside <thinking> must not trigger on non-last step."""
        text = "<thinking>\n<STEP_DONE>\n</thinking>\nstill going"
        result = prompt_step_complete(
            text,
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=False,
        )
        assert result == "continue"

    # --- last step ---

    def test_last_step_dawp_marker_seen_returns_dawp_done(self):
        result = prompt_step_complete(
            "all done.\n<DAWP_HANDOFF>",
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=True,
        )
        assert result == "dawp_done"

    def test_last_step_wrong_marker_prompt_marker_only_returns_continue(self):
        """Core requirement: wrong Prompt Marker on final step → continue (not complete run).

        §6.0.2: 末步误输出 Prompt Marker → 视为未完成；继续当前 Prompt。
        """
        result = prompt_step_complete(
            "done?\n<STEP_DONE>",
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=True,
        )
        assert result == "continue"

    def test_last_step_no_marker_returns_continue(self):
        result = prompt_step_complete(
            "still working...",
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=True,
        )
        assert result == "continue"

    def test_last_step_marker_in_fence_returns_continue(self):
        """Token inside fence must not trigger on last step."""
        text = "done:\n```\n<DAWP_HANDOFF>\n```\noutput"
        result = prompt_step_complete(
            text,
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=True,
        )
        assert result == "continue"

    def test_last_step_both_markers_returns_dawp_done(self):
        """If both appear, dawp_marker takes precedence on last step."""
        text = "first step marker:\n<STEP_DONE>\nfinal:\n<DAWP_HANDOFF>"
        result = prompt_step_complete(
            text,
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=True,
        )
        assert result == "dawp_done"

    def test_custom_ooda_markers(self):
        """Markers are not hardcoded; custom OODA markers must work."""
        result = prompt_step_complete(
            "strategic review complete.\n<OODA_REVIEW_COMPLETE>",
            prompt_marker="<OODA_STEP_DONE>",
            dawp_marker="<OODA_REVIEW_COMPLETE>",
            is_last=True,
        )
        assert result == "dawp_done"

    def test_non_last_custom_markers(self):
        result = prompt_step_complete(
            "step done.\n<OODA_STEP_DONE>",
            prompt_marker="<OODA_STEP_DONE>",
            dawp_marker="<OODA_REVIEW_COMPLETE>",
            is_last=False,
        )
        assert result == "prompt_done"


# ---------------------------------------------------------------------------
# matches_response_trigger
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMatchesResponseTrigger:
    def test_trigger_detected_on_scannable_line(self):
        state: dict = {}
        result = matches_response_trigger(
            "analysis done.\n<START_OODA_REVIEW>",
            "<START_OODA_REVIEW>",
            plugin_state=state,
        )
        assert result is True

    def test_trigger_not_detected_absent(self):
        state: dict = {}
        result = matches_response_trigger(
            "nothing special here",
            "<START_OODA_REVIEW>",
            plugin_state=state,
        )
        assert result is False

    def test_trigger_once_prevents_second_fire(self):
        state: dict = {}
        text = "ready.\n<START_OODA_REVIEW>"
        first = matches_response_trigger(text, "<START_OODA_REVIEW>", trigger_once=True, plugin_state=state)
        second = matches_response_trigger(text, "<START_OODA_REVIEW>", trigger_once=True, plugin_state=state)
        assert first is True
        assert second is False

    def test_trigger_once_false_allows_re_trigger(self):
        state: dict = {}
        text = "ready.\n<START_OODA_REVIEW>"
        first = matches_response_trigger(text, "<START_OODA_REVIEW>", trigger_once=False, plugin_state=state)
        second = matches_response_trigger(text, "<START_OODA_REVIEW>", trigger_once=False, plugin_state=state)
        assert first is True
        assert second is True

    def test_trigger_in_fence_not_detected(self):
        """Core requirement: token inside ``` fence MUST NOT trigger."""
        state: dict = {}
        text = "context:\n```yaml\ndawp_trigger: <START_OODA_REVIEW>\n```\nmore output"
        result = matches_response_trigger(text, "<START_OODA_REVIEW>", plugin_state=state)
        assert result is False

    def test_trigger_in_blockquote_not_detected(self):
        """Core requirement: token in blockquote MUST NOT trigger."""
        state: dict = {}
        text = "as noted:\n> <START_OODA_REVIEW>\ncontinuing"
        result = matches_response_trigger(text, "<START_OODA_REVIEW>", plugin_state=state)
        assert result is False

    def test_trigger_in_thinking_not_detected(self):
        """Core requirement: token inside <thinking> MUST NOT trigger."""
        state: dict = {}
        text = "<thinking>should I trigger? <START_OODA_REVIEW></thinking>\nvisible output"
        result = matches_response_trigger(text, "<START_OODA_REVIEW>", plugin_state=state)
        assert result is False

    def test_state_key_is_per_trigger_token(self):
        """Different trigger tokens have independent trigger_once guards."""
        state: dict = {}
        text_a = "ready.\n<START_A>"
        text_b = "ready.\n<START_B>"
        matches_response_trigger(text_a, "<START_A>", trigger_once=True, plugin_state=state)
        # <START_B> has not been triggered yet
        result = matches_response_trigger(text_b, "<START_B>", trigger_once=True, plugin_state=state)
        assert result is True

    def test_trigger_substring_not_matched(self):
        """Trigger must be a whole line, not a substring."""
        state: dict = {}
        text = "prefix <START_OODA_REVIEW> suffix"
        result = matches_response_trigger(text, "<START_OODA_REVIEW>", plugin_state=state)
        assert result is False

    def test_no_state_mutation_when_not_detected(self):
        """plugin_state must not be mutated when trigger is absent."""
        state: dict = {}
        matches_response_trigger("nothing here", "<START_WF>", trigger_once=True, plugin_state=state)
        assert "dawp.triggered.<START_WF>" not in state
