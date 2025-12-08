"""
Name Normalizer

Normalizes entity names for comparison to handle common variations:
- Prefixes (Dr., Prof., Mr., Mrs., Ms.)
- Suffixes (Jr., Sr., PhD, MD, III)
- Initials (J. Smith → John Smith)
- Whitespace and punctuation
"""

import re
from typing import List, Set, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class NormalizationResult:
    """Result of name normalization"""
    normalized: str
    original: str
    stripped_prefixes: List[str] = field(default_factory=list)
    stripped_suffixes: List[str] = field(default_factory=list)
    has_initials: bool = False


class NameNormalizer:
    """
    Normalize entity names for improved matching

    Handles common name variations:
    - Title prefixes (Dr., Prof., Mr., Mrs., Ms.)
    - Name suffixes (Jr., Sr., PhD, MD, III, IV)
    - Initial patterns (J. Smith, A. Einstein)
    - Whitespace and punctuation normalization

    Example:
        ```python
        normalizer = NameNormalizer()
        
        # Strip prefixes and suffixes
        result = normalizer.normalize("Dr. John Smith, PhD")
        assert result.normalized == "john smith"
        assert "Dr." in result.stripped_prefixes
        assert "PhD" in result.stripped_suffixes
        
        # Match initials with full names
        assert normalizer.names_match_with_initials("J. Smith", "John Smith")
        ```
    """

    # Common prefixes to strip (case-insensitive)
    DEFAULT_PREFIXES: Set[str] = {
        "dr", "dr.", "doctor",
        "prof", "prof.", "professor",
        "mr", "mr.", "mister",
        "mrs", "mrs.",
        "ms", "ms.", "miss",
        "sir", "dame", "lord", "lady",
        "rev", "rev.", "reverend",
        "hon", "hon.", "honorable",
        "capt", "capt.", "captain",
        "col", "col.", "colonel",
        "gen", "gen.", "general",
        "lt", "lt.", "lieutenant",
        "sgt", "sgt.", "sergeant",
    }

    # Common suffixes to strip (case-insensitive)
    DEFAULT_SUFFIXES: Set[str] = {
        "jr", "jr.", "junior",
        "sr", "sr.", "senior",
        "phd", "ph.d", "ph.d.",
        "md", "m.d", "m.d.",
        "esq", "esq.", "esquire",
        "ii", "iii", "iv", "v",
        "2nd", "3rd", "4th", "5th",
        "cpa", "c.p.a", "c.p.a.",
        "mba", "m.b.a", "m.b.a.",
        "jd", "j.d", "j.d.",
        "llb", "ll.b", "ll.b.",
        "dds", "d.d.s", "d.d.s.",
        "rn", "r.n", "r.n.",
    }

    # Pattern for detecting initials (e.g., "J.", "A. B.")
    INITIAL_PATTERN = re.compile(r'^([A-Za-z])\.$')

    def __init__(
        self,
        custom_prefixes: Optional[Set[str]] = None,
        custom_suffixes: Optional[Set[str]] = None,
    ):
        """
        Initialize name normalizer

        Args:
            custom_prefixes: Additional prefixes to strip (merged with defaults)
            custom_suffixes: Additional suffixes to strip (merged with defaults)
        """
        self.prefixes = self.DEFAULT_PREFIXES.copy()
        self.suffixes = self.DEFAULT_SUFFIXES.copy()
        
        if custom_prefixes:
            self.prefixes.update(p.lower() for p in custom_prefixes)
        if custom_suffixes:
            self.suffixes.update(s.lower() for s in custom_suffixes)

    def normalize(self, name: str) -> NormalizationResult:
        """
        Normalize a name for comparison

        Steps:
        1. Normalize whitespace (multiple spaces, tabs → single space)
        2. Normalize punctuation (remove extra, standardize)
        3. Strip prefixes (Dr., Prof., etc.)
        4. Strip suffixes (Jr., PhD, etc.)
        5. Lowercase
        6. Detect initials

        Args:
            name: Original name string

        Returns:
            NormalizationResult with normalized name and metadata
        """
        if not name:
            return NormalizationResult(normalized="", original=name)

        original = name
        
        # Step 1: Normalize whitespace
        normalized = self._normalize_whitespace(name)
        
        # Step 2: Normalize punctuation
        normalized = self._normalize_punctuation(normalized)
        
        # Step 3: Strip prefixes
        normalized, stripped_prefixes = self._strip_prefixes(normalized)
        
        # Step 4: Strip suffixes
        normalized, stripped_suffixes = self._strip_suffixes(normalized)
        
        # Step 5: Lowercase
        normalized = normalized.lower().strip()
        
        # Step 6: Detect initials
        has_initials = self._has_initials(normalized)

        return NormalizationResult(
            normalized=normalized,
            original=original,
            stripped_prefixes=stripped_prefixes,
            stripped_suffixes=stripped_suffixes,
            has_initials=has_initials,
        )

    def _normalize_whitespace(self, name: str) -> str:
        """Normalize whitespace: multiple spaces/tabs → single space"""
        return re.sub(r'\s+', ' ', name).strip()

    def _normalize_punctuation(self, name: str) -> str:
        """
        Normalize punctuation for comparison

        - "Smith, John" → "Smith John"
        - "O'Brien" → "O'Brien" (preserve apostrophes in names)
        - "Smith-Jones" → "Smith-Jones" (preserve hyphens)
        """
        # Remove commas (handles "Smith, John" format)
        name = name.replace(',', ' ')
        # Normalize whitespace after comma removal
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def _strip_prefixes(self, name: str) -> Tuple[str, List[str]]:
        """
        Strip common prefixes from name

        Returns:
            Tuple of (name_without_prefixes, list_of_stripped_prefixes)
        """
        stripped = []
        tokens = name.split()

        while tokens:
            token_lower = tokens[0].lower().rstrip('.')
            # Check if first token is a prefix
            if token_lower in self.prefixes or f"{token_lower}." in self.prefixes:
                stripped.append(tokens.pop(0))
            else:
                break

        return ' '.join(tokens), stripped

    def _strip_suffixes(self, name: str) -> Tuple[str, List[str]]:
        """
        Strip common suffixes from name

        Returns:
            Tuple of (name_without_suffixes, list_of_stripped_suffixes)
        """
        stripped = []
        tokens = name.split()

        while tokens:
            # Check last token
            token_lower = tokens[-1].lower().rstrip('.').rstrip(',')
            if token_lower in self.suffixes or f"{token_lower}." in self.suffixes:
                stripped.insert(0, tokens.pop())  # Insert at beginning to preserve order
            else:
                break

        return ' '.join(tokens), stripped

    def _has_initials(self, name: str) -> bool:
        """Check if name contains initials (e.g., 'J.' or 'A. B.')"""
        tokens = name.split()
        for token in tokens:
            if self.INITIAL_PATTERN.match(token):
                return True
            # Also check for single letters without period
            if len(token) == 1 and token.isalpha():
                return True
        return False

    def names_match_with_initials(self, name1: str, name2: str) -> bool:
        """
        Check if two names match, allowing initials to match full names

        "J. Smith" matches "John Smith", "James Smith", etc.
        "A. Einstein" matches "Albert Einstein"

        Args:
            name1: First name
            name2: Second name

        Returns:
            True if names match (accounting for initials)
        """
        # Normalize both names
        result1 = self.normalize(name1)
        result2 = self.normalize(name2)

        # Exact match after normalization
        if result1.normalized == result2.normalized:
            return True

        # If neither has initials, no match
        if not result1.has_initials and not result2.has_initials:
            return False

        # Try matching with initial expansion
        tokens1 = result1.normalized.split()
        tokens2 = result2.normalized.split()

        # Must have same number of tokens (or be comparable)
        if abs(len(tokens1) - len(tokens2)) > 1:
            return False

        return self._tokens_match_with_initials(tokens1, tokens2)

    def _tokens_match_with_initials(self, tokens1: List[str], tokens2: List[str]) -> bool:
        """
        Check if token lists match, allowing initials

        "j" matches "john" (initial to full name)
        "j." matches "john"
        """
        # Handle different lengths - pad shorter list
        len1, len2 = len(tokens1), len(tokens2)
        if len1 != len2:
            # Try to match with potential middle name difference
            if abs(len1 - len2) == 1:
                # Try skipping middle name in longer list
                if len1 > len2:
                    # Try removing middle token from tokens1
                    for i in range(len(tokens1)):
                        test_tokens = tokens1[:i] + tokens1[i+1:]
                        if self._tokens_match_exact(test_tokens, tokens2):
                            return True
                else:
                    # Try removing middle token from tokens2
                    for i in range(len(tokens2)):
                        test_tokens = tokens2[:i] + tokens2[i+1:]
                        if self._tokens_match_exact(tokens1, test_tokens):
                            return True
            return False

        return self._tokens_match_exact(tokens1, tokens2)

    def _tokens_match_exact(self, tokens1: List[str], tokens2: List[str]) -> bool:
        """Check if token lists match exactly (with initial expansion)"""
        if len(tokens1) != len(tokens2):
            return False

        for t1, t2 in zip(tokens1, tokens2):
            if not self._token_matches(t1, t2):
                return False
        return True

    def _token_matches(self, token1: str, token2: str) -> bool:
        """
        Check if two tokens match (with initial expansion)

        Returns True if:
        - Tokens are equal
        - One is an initial that matches the first letter of the other
        """
        t1 = token1.rstrip('.')
        t2 = token2.rstrip('.')

        # Exact match
        if t1 == t2:
            return True

        # Initial match: single letter matches first letter of other token
        if len(t1) == 1 and t2.startswith(t1):
            return True
        if len(t2) == 1 and t1.startswith(t2):
            return True

        return False

    def get_initial_variants(self, name: str) -> List[str]:
        """
        Generate possible variants with initials for a name

        "John Smith" → ["John Smith", "J. Smith", "J Smith"]

        Args:
            name: Full name

        Returns:
            List of name variants (including original)
        """
        result = self.normalize(name)
        tokens = result.normalized.split()

        if not tokens:
            return [name]

        variants = [result.normalized]

        # Generate variants with first name as initial
        if len(tokens) >= 2 and len(tokens[0]) > 1:
            initial_variant = f"{tokens[0][0]}. {' '.join(tokens[1:])}"
            variants.append(initial_variant)
            # Also without period
            variants.append(f"{tokens[0][0]} {' '.join(tokens[1:])}")

        return variants

