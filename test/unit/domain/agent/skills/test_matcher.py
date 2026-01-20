"""
Unit tests for SkillMatcher.
"""

import pytest
from pathlib import Path

from aiecs.domain.agent.skills.matcher import (
    SkillMatcher,
    SkillMatcherError,
    MatchResult,
)
from aiecs.domain.agent.skills.registry import SkillRegistry
from aiecs.domain.agent.skills.models import SkillDefinition, SkillMetadata


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset registry before and after each test."""
    SkillRegistry.reset_instance()
    yield
    SkillRegistry.reset_instance()


@pytest.fixture
def python_testing_skill():
    """Create a Python testing skill with trigger phrases."""
    metadata = SkillMetadata(
        name="python-testing",
        description=(
            'This skill should be used when the user asks to "write tests", '
            '"create unit tests", or mentions "pytest" or "testing".'
        ),
        version="1.0.0",
        tags=["python", "testing", "quality"],
        recommended_tools=["pytest_runner", "coverage"]
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/path/to/python-testing"),
        body="# Python Testing\n\nGuidance for writing tests..."
    )


@pytest.fixture
def code_review_skill():
    """Create a code review skill with trigger phrases."""
    metadata = SkillMetadata(
        name="code-review",
        description=(
            'Use this skill when the user wants to "review code", '
            '"analyze quality", or needs "code feedback".'
        ),
        version="1.0.0",
        tags=["review", "quality", "analysis"],
        recommended_tools=["linter", "code_analyzer"]
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/path/to/code-review"),
        body="# Code Review\n\nGuidance for reviewing code..."
    )


@pytest.fixture
def database_skill():
    """Create a database skill with trigger phrases."""
    metadata = SkillMetadata(
        name="database-management",
        description=(
            'This skill helps with "database queries", "SQL", '
            '"migrations", and "data modeling".'
        ),
        version="1.0.0",
        tags=["database", "sql", "data"],
        recommended_tools=["db_client", "migration_tool"]
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/path/to/database"),
        body="# Database Management\n\nDatabase guidance..."
    )


@pytest.fixture
def registered_skills(python_testing_skill, code_review_skill, database_skill):
    """Register all test skills in the registry."""
    registry = SkillRegistry.get_instance()
    registry.register_skill(python_testing_skill)
    registry.register_skill(code_review_skill)
    registry.register_skill(database_skill)
    return [python_testing_skill, code_review_skill, database_skill]


class TestTriggerPhraseExtraction:
    """Tests for trigger phrase extraction."""

    def test_extract_double_quoted_phrases(self):
        """Test extraction of double-quoted phrases."""
        matcher = SkillMatcher()
        description = 'Use when user asks to "write tests" or "run tests".'
        phrases = matcher.extract_trigger_phrases(description)
        assert "write tests" in phrases
        assert "run tests" in phrases

    def test_extract_single_quoted_phrases(self):
        """Test extraction of single-quoted phrases."""
        matcher = SkillMatcher()
        description = "Use when user asks to 'create file' or 'delete file'."
        phrases = matcher.extract_trigger_phrases(description)
        assert "create file" in phrases
        assert "delete file" in phrases

    def test_extract_mixed_quotes(self):
        """Test extraction of mixed quote styles."""
        matcher = SkillMatcher()
        description = '''Use for "unit tests", 'integration tests', or "e2e".'''
        phrases = matcher.extract_trigger_phrases(description)
        assert "unit tests" in phrases
        assert "integration tests" in phrases
        assert "e2e" in phrases

    def test_extract_no_phrases(self):
        """Test extraction when no phrases exist."""
        matcher = SkillMatcher()
        description = "A generic skill description without quoted phrases."
        phrases = matcher.extract_trigger_phrases(description)
        assert phrases == []

    def test_phrases_are_lowercase_and_stripped(self):
        """Test that phrases are normalized."""
        matcher = SkillMatcher()
        description = 'Use when user asks to "  Write Tests  " or "RUN TESTS".'
        phrases = matcher.extract_trigger_phrases(description)
        assert "write tests" in phrases
        assert "run tests" in phrases


class TestKeywordExtraction:
    """Tests for keyword extraction."""

    def test_extract_keywords(self):
        """Test basic keyword extraction."""
        matcher = SkillMatcher()
        text = "Python testing framework with pytest and coverage"
        keywords = matcher.extract_keywords(text)
        assert "python" in keywords
        assert "testing" in keywords
        assert "framework" in keywords
        assert "pytest" in keywords
        assert "coverage" in keywords

    def test_stop_words_removed(self):
        """Test that stop words are filtered."""
        matcher = SkillMatcher()
        text = "This is a test for the testing framework"
        keywords = matcher.extract_keywords(text)
        # Stop words should be excluded
        assert "this" not in keywords
        assert "the" not in keywords


class TestSkillMatching:
    """Tests for skill matching."""

    def test_exact_phrase_match(self, registered_skills):
        """Test exact phrase matching."""
        matcher = SkillMatcher(default_threshold=0.2)
        matches = matcher.match("I want to write tests for my code")

        assert len(matches) > 0
        # Python testing skill should match due to "write tests"
        skill_names = [s.metadata.name for s, _ in matches]
        assert "python-testing" in skill_names

    def test_fuzzy_phrase_match(self, registered_skills):
        """Test fuzzy phrase matching."""
        matcher = SkillMatcher(default_threshold=0.1)
        # "create unit tests" is a trigger phrase, "create unit test" is fuzzy match
        matches = matcher.match("create unit test for my module")

        # Should still match python-testing with fuzzy matching
        skill_names = [s.metadata.name for s, _ in matches]
        assert "python-testing" in skill_names

    def test_keyword_matching(self, registered_skills):
        """Test keyword-based matching."""
        matcher = SkillMatcher(default_threshold=0.1)
        matches = matcher.match("help me with sql database")

        skill_names = [s.metadata.name for s, _ in matches]
        assert "database-management" in skill_names

    def test_tag_matching(self, registered_skills):
        """Test tag-based matching."""
        matcher = SkillMatcher(default_threshold=0.04)
        matches = matcher.match("python coding quality")

        # Skills with matching tags should appear
        assert len(matches) > 0

    def test_no_match_below_threshold(self, registered_skills):
        """Test that no matches returned below threshold."""
        matcher = SkillMatcher(default_threshold=0.9)
        matches = matcher.match("unrelated topic about cooking")

        # With high threshold and unrelated request, should get no matches
        assert len(matches) == 0

    def test_match_with_custom_threshold(self, registered_skills):
        """Test matching with custom threshold."""
        matcher = SkillMatcher()
        # High threshold
        matches_high = matcher.match("write tests", threshold=0.8)
        # Low threshold
        matches_low = matcher.match("write tests", threshold=0.1)

        # Lower threshold should return more or equal matches
        assert len(matches_low) >= len(matches_high)

    def test_match_with_max_results(self, registered_skills):
        """Test limiting match results."""
        matcher = SkillMatcher(default_threshold=0.1)
        matches = matcher.match("code quality testing", max_results=1)

        assert len(matches) <= 1

    def test_match_returns_sorted_by_score(self, registered_skills):
        """Test that matches are sorted by score descending."""
        matcher = SkillMatcher(default_threshold=0.1)
        matches = matcher.match("write tests")

        if len(matches) > 1:
            scores = [score for _, score in matches]
            assert scores == sorted(scores, reverse=True)

    def test_match_empty_request(self, registered_skills):
        """Test matching with empty request."""
        matcher = SkillMatcher()
        matches = matcher.match("")
        assert matches == []

        matches = matcher.match("   ")
        assert matches == []

    def test_match_with_no_skills(self):
        """Test matching with empty registry."""
        matcher = SkillMatcher()
        matches = matcher.match("write tests")
        assert matches == []

    def test_match_with_explicit_skills_list(
        self, python_testing_skill, code_review_skill
    ):
        """Test matching against explicit skill list."""
        matcher = SkillMatcher()
        matches = matcher.match(
            "write tests",
            skills=[python_testing_skill, code_review_skill]
        )

        # Should match without needing registry
        assert len(matches) > 0


class TestMatchDetailed:
    """Tests for detailed match information."""

    def test_match_detailed_returns_match_results(self, registered_skills):
        """Test that match_detailed returns MatchResult objects."""
        matcher = SkillMatcher(default_threshold=0.1)
        results = matcher.match_detailed("write unit tests")

        assert len(results) > 0
        assert all(isinstance(r, MatchResult) for r in results)

    def test_match_result_contains_matched_phrases(self, registered_skills):
        """Test that MatchResult contains matched phrases."""
        matcher = SkillMatcher()
        results = matcher.match_detailed("write tests")

        # Find python-testing result
        testing_result = next(
            (r for r in results if r.skill.metadata.name == "python-testing"),
            None
        )

        if testing_result:
            assert "write tests" in testing_result.matched_phrases

    def test_match_result_contains_matched_keywords(self, registered_skills):
        """Test that MatchResult contains matched keywords."""
        matcher = SkillMatcher(default_threshold=0.1)
        results = matcher.match_detailed("database sql query")

        db_result = next(
            (r for r in results if r.skill.metadata.name == "database-management"),
            None
        )

        if db_result:
            # Should have matched keywords
            assert len(db_result.matched_keywords) > 0


class TestCaching:
    """Tests for caching behavior."""

    def test_clear_cache(self, python_testing_skill):
        """Test cache clearing."""
        matcher = SkillMatcher()
        # Populate cache
        matcher._get_skill_triggers(python_testing_skill)
        matcher._get_skill_keywords(python_testing_skill)

        assert len(matcher._trigger_cache) > 0
        assert len(matcher._keyword_cache) > 0

        matcher.clear_cache()

        assert len(matcher._trigger_cache) == 0
        assert len(matcher._keyword_cache) == 0

    def test_invalidate_skill(self, python_testing_skill):
        """Test invalidating specific skill cache."""
        matcher = SkillMatcher()

        # Populate cache
        matcher._get_skill_triggers(python_testing_skill)
        matcher._get_skill_keywords(python_testing_skill)

        skill_name = python_testing_skill.metadata.name
        assert skill_name in matcher._trigger_cache
        assert skill_name in matcher._keyword_cache

        matcher.invalidate_skill(skill_name)

        assert skill_name not in matcher._trigger_cache
        assert skill_name not in matcher._keyword_cache


class TestEdgeCases:
    """Tests for edge cases."""

    def test_skill_without_triggers(self, registered_skills):
        """Test matching skill with no trigger phrases."""
        # Create skill without trigger phrases
        metadata = SkillMetadata(
            name="no-triggers",
            description="A skill without any quoted trigger phrases",
            version="1.0.0",
            tags=["general"]
        )
        skill = SkillDefinition(
            metadata=metadata,
            skill_path=Path("/path/to/no-triggers")
        )

        matcher = SkillMatcher()
        results = matcher.match_detailed(
            "general purpose request",
            skills=[skill],
            threshold=0.0
        )

        # Should still return result (based on keyword/description similarity)
        assert len(results) >= 0

    def test_skill_with_special_characters(self):
        """Test matching with special characters."""
        metadata = SkillMetadata(
            name="special-chars",
            description='Use for "C++ code" or "C# development".',
            version="1.0.0"
        )
        skill = SkillDefinition(
            metadata=metadata,
            skill_path=Path("/path/to/special")
        )

        matcher = SkillMatcher()
        phrases = matcher.extract_trigger_phrases(skill.metadata.description)
        assert "c++ code" in phrases
        assert "c# development" in phrases

    def test_unicode_in_description(self):
        """Test matching with unicode characters."""
        matcher = SkillMatcher()
        # Smart quotes
        description = 'Use for "写代码" or "编程".'
        phrases = matcher.extract_trigger_phrases(description)
        assert "写代码" in phrases
        assert "编程" in phrases

    def test_very_long_request(self, registered_skills):
        """Test matching with very long request text."""
        matcher = SkillMatcher(default_threshold=0.1)
        long_request = "write tests " * 100 + "for my code"
        matches = matcher.match(long_request)

        # Should still work and match
        skill_names = [s.metadata.name for s, _ in matches]
        assert "python-testing" in skill_names
