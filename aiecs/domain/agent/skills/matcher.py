"""
Skill Matcher

Provides intelligent matching of user requests to skills based on
trigger phrases extracted from skill descriptions.

Supports:
- Trigger phrase extraction from quoted strings in descriptions
- Exact and fuzzy pattern matching
- Keyword-based matching
- Configurable thresholds and result limits
- Scoring and ranking

Usage:
    from aiecs.domain.agent.skills.matcher import SkillMatcher

    matcher = SkillMatcher(registry)
    matches = matcher.match("write unit tests for my code", threshold=0.5)
    for skill, score in matches:
        print(f"{skill.metadata.name}: {score:.2f}")
"""

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable, Dict, List, Optional, Set, Tuple

from .models import SkillDefinition, SkillMetadata
from .registry import SkillRegistry

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a skill match operation."""
    skill: SkillDefinition
    score: float
    matched_phrases: List[str]
    matched_keywords: List[str]

    def __repr__(self) -> str:
        return (
            f"MatchResult(skill={self.skill.metadata.name!r}, "
            f"score={self.score:.3f}, "
            f"matched_phrases={self.matched_phrases}, "
            f"matched_keywords={self.matched_keywords})"
        )


class SkillMatcher:
    """
    Matches user requests to skills based on trigger patterns.

    The matcher extracts trigger phrases from skill descriptions
    and uses fuzzy matching to find relevant skills for a request.

    Trigger phrases are extracted from quoted strings in descriptions:
        "This skill should be used when the user asks to 'write tests',
        'create unit tests', or mentions 'pytest'."

    Matching uses a combination of:
    - Exact phrase matching (highest weight)
    - Fuzzy phrase matching (medium weight)
    - Keyword matching from tags (lower weight)

    Attributes:
        registry: SkillRegistry to get skills from
        default_threshold: Default minimum score for matches
        default_max_results: Default maximum results to return
    """

    # Regex to extract quoted phrases from descriptions
    # Matches: "phrase", 'phrase', or "phrase" (smart quotes)
    TRIGGER_PHRASE_PATTERN = re.compile(
        r'["\'\u201c\u201d]([^"\'\u201c\u201d]+)["\'\u201c\u201d]'
    )

    # Common words to ignore in keyword matching
    STOP_WORDS = {
        'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'up',
        'about', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'under', 'again', 'further', 'then', 'once',
        'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either', 'neither',
        'not', 'only', 'own', 'same', 'than', 'too', 'very', 'just', 'also',
        'this', 'that', 'these', 'those', 'it', 'its', 'i', 'me', 'my',
        'you', 'your', 'he', 'she', 'we', 'they', 'who', 'which', 'when',
        'where', 'why', 'how', 'all', 'each', 'every', 'any', 'some', 'no',
        'user', 'asks', 'mentions', 'wants', 'skill', 'used', 'when',
    }

    # Weights for different match types
    EXACT_PHRASE_WEIGHT = 1.0
    FUZZY_PHRASE_WEIGHT = 0.7
    KEYWORD_WEIGHT = 0.5  # Increased from 0.3 to give description keywords more weight
    TAG_WEIGHT = 0.4      # Increased from 0.2 to give tags more weight

    def __init__(
        self,
        registry: Optional[SkillRegistry] = None,
        default_threshold: float = 0.3,
        default_max_results: int = 5
    ):
        """
        Initialize the skill matcher.

        Args:
            registry: SkillRegistry to get skills from (uses singleton if None)
            default_threshold: Default minimum score threshold (0.0 to 1.0)
            default_max_results: Default maximum number of results
        """
        self._registry = registry or SkillRegistry.get_instance()
        self._default_threshold = default_threshold
        self._default_max_results = default_max_results

        # Cache for extracted trigger phrases
        self._trigger_cache: Dict[str, List[str]] = {}
        self._keyword_cache: Dict[str, Set[str]] = {}

    def extract_trigger_phrases(self, description: str) -> List[str]:
        """
        Extract trigger phrases from a skill description.

        Trigger phrases are quoted strings in the description that
        indicate when the skill should be triggered.

        Args:
            description: Skill description text

        Returns:
            List of trigger phrases (lowercase, stripped)
        """
        matches = self.TRIGGER_PHRASE_PATTERN.findall(description)
        return [phrase.strip().lower() for phrase in matches if phrase.strip()]

    def extract_keywords(self, text: str) -> Set[str]:
        """
        Extract meaningful keywords from text.

        Removes stop words and returns unique lowercase keywords.

        Args:
            text: Text to extract keywords from

        Returns:
            Set of keywords
        """
        # Split on non-word characters
        words = re.split(r'\W+', text.lower())
        # Filter stop words and short words
        return {
            word for word in words
            if word and len(word) > 2 and word not in self.STOP_WORDS
        }

    def _get_skill_triggers(self, skill: SkillDefinition) -> List[str]:
        """Get cached trigger phrases for a skill."""
        name = skill.metadata.name
        if name not in self._trigger_cache:
            self._trigger_cache[name] = self.extract_trigger_phrases(
                skill.metadata.description
            )
        return self._trigger_cache[name]

    def _get_skill_keywords(self, skill: SkillDefinition) -> Set[str]:
        """Get cached keywords for a skill (from description and tags)."""
        name = skill.metadata.name
        if name not in self._keyword_cache:
            keywords = self.extract_keywords(skill.metadata.description)
            # Add tags as keywords
            if skill.metadata.tags:
                keywords.update(tag.lower() for tag in skill.metadata.tags)
            self._keyword_cache[name] = keywords
        return self._keyword_cache[name]

    def _fuzzy_match_score(self, s1: str, s2: str) -> float:
        """
        Calculate fuzzy match score between two strings.

        Uses SequenceMatcher for similarity calculation.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def _phrase_in_text(self, phrase: str, text: str) -> bool:
        """Check if phrase appears in text (case-insensitive)."""
        return phrase.lower() in text.lower()

    def _score_skill(
        self,
        skill: SkillDefinition,
        request: str,
        request_keywords: Set[str]
    ) -> MatchResult:
        """
        Score how well a skill matches a request.

        Uses a "best match" scoring strategy where matching any single trigger
        phrase yields a high score. Multiple triggers increase matching
        opportunities, not difficulty.

        Scoring considers:
        - Exact trigger phrase matches (weight: 1.0)
        - Fuzzy trigger phrase matches (weight: 0.7)
        - Keyword overlap (weight: 0.3)
        - Tag matches (weight: 0.2)

        Args:
            skill: Skill to score
            request: User request text
            request_keywords: Pre-extracted keywords from request

        Returns:
            MatchResult with score and match details
        """
        triggers = self._get_skill_triggers(skill)
        skill_keywords = self._get_skill_keywords(skill)

        matched_phrases: List[str] = []
        matched_keywords: List[str] = []

        # === New "best match" scoring logic ===
        # Track the best trigger score (not cumulative)
        best_trigger_score = 0.0
        request_lower = request.lower()

        for trigger in triggers:
            # Check exact match
            if trigger in request_lower:
                best_trigger_score = max(best_trigger_score, self.EXACT_PHRASE_WEIGHT)
                matched_phrases.append(trigger)
            else:
                # Check fuzzy match
                fuzzy_score = self._fuzzy_match_score(trigger, request_lower)
                if fuzzy_score > 0.6:  # Threshold for fuzzy match consideration
                    score_contribution = fuzzy_score * self.FUZZY_PHRASE_WEIGHT
                    best_trigger_score = max(best_trigger_score, score_contribution)
                    matched_phrases.append(f"~{trigger}")

        # Give a small bonus for matching multiple triggers (max 0.15 bonus)
        trigger_score = best_trigger_score
        if len(matched_phrases) > 1:
            # Each additional match adds 0.05, capped at 0.15
            bonus = min(0.05 * (len(matched_phrases) - 1), 0.15)
            trigger_score = min(best_trigger_score + bonus, 1.0)

        # Score keyword overlap (0.0 to KEYWORD_WEIGHT)
        # Use the ratio of matched keywords relative to REQUEST keywords (not skill keywords)
        # This way, if user's request keywords mostly match the skill, we get a high score
        keyword_score = 0.0
        common_keywords = request_keywords.intersection(skill_keywords)
        if common_keywords and request_keywords:
            # How much of the user's request is covered by this skill?
            request_coverage = len(common_keywords) / len(request_keywords)
            # Also consider absolute match count (bonus for more matches)
            match_bonus = min(len(common_keywords) * 0.1, 0.3)  # Up to 0.3 bonus
            keyword_score = min((request_coverage + match_bonus) * self.KEYWORD_WEIGHT, self.KEYWORD_WEIGHT)
            matched_keywords.extend(common_keywords)

        # Score tag matches (0.0 to TAG_WEIGHT)
        # Tags are explicit markers, so matching ANY tag should give significant score
        tag_score = 0.0
        if skill.metadata.tags:
            tag_matches = [
                tag for tag in skill.metadata.tags
                if tag.lower() in request_lower
            ]
            if tag_matches:
                # Any tag match gives at least 0.7 of TAG_WEIGHT
                base_score = 0.7
                # Bonus for matching multiple tags
                bonus = min(len(tag_matches) * 0.1, 0.3)
                tag_score = (base_score + bonus) * self.TAG_WEIGHT
                matched_keywords.extend(tag_matches)

        # === Final score calculation ===
        # Use weighted combination where trigger match dominates, but keywords can also reach threshold
        if trigger_score > 0:
            # Trigger matched: trigger dominates (60%), keywords (25%), tags (15%)
            final_score = (
                trigger_score * 0.6 +
                keyword_score * 0.25 +
                tag_score * 0.15
            )
        elif keyword_score > 0 or tag_score > 0:
            # No trigger match: keywords and tags can still reach threshold
            # keyword_score max = 0.5, tag_score max = 0.4
            # With these weights, max possible = 0.5 * 0.7 + 0.4 * 0.5 = 0.55
            final_score = keyword_score * 0.7 + tag_score * 0.5
        else:
            # No matches at all - use basic text similarity as fallback
            final_score = self._fuzzy_match_score(
                skill.metadata.description, request
            ) * 0.4  # Increased from 0.3

        # Ensure score is in valid range
        final_score = min(max(final_score, 0.0), 1.0)

        logger.debug(
            f"Skill '{skill.metadata.name}' scoring: "
            f"trigger_score={trigger_score:.3f}, "
            f"keyword_score={keyword_score:.3f}, "
            f"tag_score={tag_score:.3f}, "
            f"final={final_score:.3f}, "
            f"matched_phrases={matched_phrases}"
        )

        return MatchResult(
            skill=skill,
            score=final_score,
            matched_phrases=matched_phrases,
            matched_keywords=list(set(matched_keywords))
        )

    def match(
        self,
        request: str,
        threshold: Optional[float] = None,
        max_results: Optional[int] = None,
        skills: Optional[List[SkillDefinition]] = None
    ) -> List[Tuple[SkillDefinition, float]]:
        """
        Match a request to skills and return ranked results.

        Args:
            request: User request text
            threshold: Minimum score threshold (uses default if None)
            max_results: Maximum results to return (uses default if None)
            skills: Skills to match against (uses registry if None)

        Returns:
            List of (skill, score) tuples, sorted by score descending
        """
        if not request or not request.strip():
            return []

        threshold = threshold if threshold is not None else self._default_threshold
        max_results = max_results if max_results is not None else self._default_max_results

        # Get skills to match against
        skills_to_match = skills or self._registry.get_all_skills()
        if not skills_to_match:
            return []

        # Pre-extract request keywords
        request_keywords = self.extract_keywords(request)

        # Score all skills
        results: List[MatchResult] = []
        for skill in skills_to_match:
            result = self._score_skill(skill, request, request_keywords)
            if result.score >= threshold:
                results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        # Limit results
        results = results[:max_results]

        # Log matches
        if results:
            logger.debug(
                f"Matched {len(results)} skills for request: "
                f"{request[:50]}{'...' if len(request) > 50 else ''}"
            )
            for result in results:
                logger.debug(f"  {result}")

        # Return as (skill, score) tuples for backward compatibility
        return [(r.skill, r.score) for r in results]

    def match_detailed(
        self,
        request: str,
        threshold: Optional[float] = None,
        max_results: Optional[int] = None,
        skills: Optional[List[SkillDefinition]] = None
    ) -> List[MatchResult]:
        """
        Match a request to skills with detailed match information.

        Same as match() but returns MatchResult objects with
        matched phrases and keywords.

        Args:
            request: User request text
            threshold: Minimum score threshold
            max_results: Maximum results to return
            skills: Skills to match against

        Returns:
            List of MatchResult objects, sorted by score descending
        """
        if not request or not request.strip():
            return []

        threshold = threshold if threshold is not None else self._default_threshold
        max_results = max_results if max_results is not None else self._default_max_results

        skills_to_match = skills or self._registry.get_all_skills()
        if not skills_to_match:
            return []

        request_keywords = self.extract_keywords(request)

        results: List[MatchResult] = []
        for skill in skills_to_match:
            result = self._score_skill(skill, request, request_keywords)
            if result.score >= threshold:
                results.append(result)

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

    def clear_cache(self) -> None:
        """Clear the trigger phrase and keyword caches."""
        self._trigger_cache.clear()
        self._keyword_cache.clear()

    def invalidate_skill(self, skill_name: str) -> None:
        """
        Invalidate cache for a specific skill.

        Call this when a skill is updated or removed.

        Args:
            skill_name: Name of the skill to invalidate
        """
        self._trigger_cache.pop(skill_name, None)
        self._keyword_cache.pop(skill_name, None)


class SkillMatcherError(Exception):
    """Raised when skill matching fails."""
    pass
