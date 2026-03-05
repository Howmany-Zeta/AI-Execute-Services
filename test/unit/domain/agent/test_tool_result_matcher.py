"""
Unit tests for tool_result_matcher.
"""

import pytest

from aiecs.domain.agent.tool_result_matcher import matches_stop_condition


@pytest.mark.unit
class TestMatchesStopCondition:
    """Tests for matches_stop_condition."""

    def test_none_conditions_returns_false(self):
        """When conditions is None or empty, returns False."""
        assert matches_stop_condition("any result", None) is False
        assert matches_stop_condition("any result", []) is False

    def test_substring_string_condition(self):
        """String condition: substring match."""
        assert matches_stop_condition("<html>...</html>", ["</html>"]) is True
        assert matches_stop_condition("TASK_COMPLETE", ["TASK_COMPLETE"]) is True
        assert matches_stop_condition("partial match here", ["match"]) is True
        assert matches_stop_condition("no match", ["xyz"]) is False

    def test_substring_dict_condition(self):
        """Dict with type=substring."""
        assert matches_stop_condition(
            "result with done",
            [{"type": "substring", "pattern": "done"}],
        ) is True
        assert matches_stop_condition(
            "result with done",
            [{"type": "substring", "value": "done"}],
        ) is True
        assert matches_stop_condition(
            "no match",
            [{"type": "substring", "pattern": "xyz"}],
        ) is False

    def test_regex_condition(self):
        """Dict with type=regex."""
        assert matches_stop_condition(
            "<div class='x'>content</div>",
            [{"type": "regex", "pattern": r"<div[^>]*>.*</div>"}],
        ) is True
        assert matches_stop_condition(
            "status: done",
            [{"type": "regex", "pattern": r"status:\s*done"}],
        ) is True
        assert matches_stop_condition(
            "no match",
            [{"type": "regex", "pattern": r"^\d+$"}],
        ) is False

    def test_html_tag_condition(self):
        """Dict with type=html_tag."""
        assert matches_stop_condition(
            "<html><body>...</body></html>",
            [{"type": "html_tag", "pattern": "html"}],
        ) is True
        assert matches_stop_condition(
            "closing </html> tag",
            [{"type": "html_tag", "pattern": "html"}],
        ) is True
        assert matches_stop_condition(
            "plain text",
            [{"type": "html_tag", "pattern": "html"}],
        ) is False

    def test_dict_result(self):
        """Tool result as dict is JSON-serialized for matching."""
        result = {"status": "done", "data": "value"}
        assert matches_stop_condition(result, ["done"]) is True
        assert matches_stop_condition(result, ["status"]) is True
        assert matches_stop_condition(result, ["xyz"]) is False

    def test_first_match_wins(self):
        """First matching condition returns True."""
        assert matches_stop_condition(
            "contains both",
            ["both", "other"],
        ) is True
        assert matches_stop_condition(
            "contains other",
            ["none", "other"],
        ) is True
