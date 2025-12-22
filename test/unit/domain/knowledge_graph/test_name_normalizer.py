"""
Unit tests for NameNormalizer

Tests name normalization including prefix/suffix stripping, initial expansion, 
and whitespace/punctuation normalization.
"""

import pytest

from aiecs.application.knowledge_graph.fusion.name_normalizer import (
    NameNormalizer,
    NormalizationResult,
)


class TestNameNormalizer:
    """Test NameNormalizer class"""

    @pytest.fixture
    def normalizer(self):
        """Create NameNormalizer instance"""
        return NameNormalizer()

    # --- Basic Normalization Tests ---

    def test_normalize_empty_string(self, normalizer):
        """Test normalization of empty string"""
        result = normalizer.normalize("")
        assert result.normalized == ""
        assert result.original == ""

    def test_normalize_simple_name(self, normalizer):
        """Test normalization of simple name"""
        result = normalizer.normalize("John Smith")
        assert result.normalized == "john smith"
        assert result.original == "John Smith"
        assert result.stripped_prefixes == []
        assert result.stripped_suffixes == []

    def test_normalize_preserves_original(self, normalizer):
        """Test that original name is preserved"""
        result = normalizer.normalize("Dr. John Smith, PhD")
        assert result.original == "Dr. John Smith, PhD"

    # --- Prefix Stripping Tests ---

    def test_strip_prefix_dr(self, normalizer):
        """Test stripping Dr. prefix"""
        result = normalizer.normalize("Dr. John Smith")
        assert result.normalized == "john smith"
        assert "Dr." in result.stripped_prefixes

    def test_strip_prefix_professor(self, normalizer):
        """Test stripping Professor prefix"""
        result = normalizer.normalize("Professor Jane Doe")
        assert result.normalized == "jane doe"
        assert "Professor" in result.stripped_prefixes

    def test_strip_prefix_mr(self, normalizer):
        """Test stripping Mr. prefix"""
        result = normalizer.normalize("Mr. James Bond")
        assert result.normalized == "james bond"
        assert "Mr." in result.stripped_prefixes

    def test_strip_multiple_prefixes(self, normalizer):
        """Test stripping multiple prefixes (though unusual)"""
        result = normalizer.normalize("Sir Lord Wellington")
        # Only first matching prefix is stripped
        assert "sir" not in result.normalized or "lord" not in result.normalized

    # --- Suffix Stripping Tests ---

    def test_strip_suffix_phd(self, normalizer):
        """Test stripping PhD suffix"""
        result = normalizer.normalize("John Smith PhD")
        assert result.normalized == "john smith"
        assert "PhD" in result.stripped_suffixes

    def test_strip_suffix_jr(self, normalizer):
        """Test stripping Jr. suffix"""
        result = normalizer.normalize("John Smith Jr.")
        assert result.normalized == "john smith"
        assert "Jr." in result.stripped_suffixes

    def test_strip_suffix_iii(self, normalizer):
        """Test stripping III suffix"""
        result = normalizer.normalize("John Smith III")
        assert result.normalized == "john smith"
        assert "III" in result.stripped_suffixes

    def test_strip_suffix_md(self, normalizer):
        """Test stripping MD suffix"""
        result = normalizer.normalize("Jane Doe MD")
        assert result.normalized == "jane doe"
        assert "MD" in result.stripped_suffixes

    # --- Combined Prefix/Suffix Tests ---

    def test_strip_prefix_and_suffix(self, normalizer):
        """Test stripping both prefix and suffix"""
        result = normalizer.normalize("Dr. John Smith, PhD")
        assert result.normalized == "john smith"
        assert len(result.stripped_prefixes) > 0
        assert len(result.stripped_suffixes) > 0

    # --- Whitespace Normalization Tests ---

    def test_normalize_multiple_spaces(self, normalizer):
        """Test normalization of multiple spaces"""
        result = normalizer.normalize("John    Smith")
        assert result.normalized == "john smith"

    def test_normalize_tabs(self, normalizer):
        """Test normalization of tabs"""
        result = normalizer.normalize("John\tSmith")
        assert result.normalized == "john smith"

    def test_normalize_leading_trailing_whitespace(self, normalizer):
        """Test normalization of leading/trailing whitespace"""
        result = normalizer.normalize("  John Smith  ")
        assert result.normalized == "john smith"

    # --- Punctuation Normalization Tests ---

    def test_normalize_comma_format(self, normalizer):
        """Test normalization of 'Smith, John' format"""
        result = normalizer.normalize("Smith, John")
        assert result.normalized == "smith john"

    def test_preserve_apostrophe(self, normalizer):
        """Test that apostrophes are preserved"""
        result = normalizer.normalize("O'Brien")
        assert "o'brien" == result.normalized

    def test_preserve_hyphen(self, normalizer):
        """Test that hyphens are preserved"""
        result = normalizer.normalize("Smith-Jones")
        assert "smith-jones" == result.normalized

    # --- Initial Detection Tests ---

    def test_detect_initials_single(self, normalizer):
        """Test detection of single initial"""
        result = normalizer.normalize("J. Smith")
        assert result.has_initials is True

    def test_detect_initials_multiple(self, normalizer):
        """Test detection of multiple initials"""
        result = normalizer.normalize("J. R. R. Tolkien")
        assert result.has_initials is True

    def test_detect_no_initials(self, normalizer):
        """Test detection when no initials present"""
        result = normalizer.normalize("John Smith")
        assert result.has_initials is False

    def test_detect_single_letter_initial(self, normalizer):
        """Test detection of single letter without period"""
        result = normalizer.normalize("J Smith")
        assert result.has_initials is True


class TestInitialMatching:
    """Test initial matching functionality"""

    @pytest.fixture
    def normalizer(self):
        """Create NameNormalizer instance"""
        return NameNormalizer()

    def test_match_initials_basic(self, normalizer):
        """Test basic initial matching"""
        assert normalizer.names_match_with_initials("J. Smith", "John Smith") is True

    def test_match_initials_einstein(self, normalizer):
        """Test Einstein example from spec"""
        assert normalizer.names_match_with_initials("A. Einstein", "Albert Einstein") is True

    def test_match_exact_names(self, normalizer):
        """Test exact name match"""
        assert normalizer.names_match_with_initials("John Smith", "John Smith") is True

    def test_match_case_insensitive(self, normalizer):
        """Test case-insensitive matching"""
        assert normalizer.names_match_with_initials("john smith", "JOHN SMITH") is True

    def test_no_match_different_names(self, normalizer):
        """Test no match for different names"""
        assert normalizer.names_match_with_initials("John Smith", "Jane Doe") is False

    def test_no_match_different_last_names(self, normalizer):
        """Test no match when last names differ"""
        assert normalizer.names_match_with_initials("J. Smith", "John Doe") is False

    def test_match_with_prefix_suffix(self, normalizer):
        """Test matching with prefixes and suffixes stripped"""
        assert normalizer.names_match_with_initials("Dr. J. Smith, PhD", "John Smith") is True

    def test_match_middle_name_difference(self, normalizer):
        """Test matching when middle name present in one"""
        # "J. Smith" should match "John Robert Smith" (middle name skipped)
        assert normalizer.names_match_with_initials("J. Smith", "John Robert Smith") is True

    def test_no_match_different_initials(self, normalizer):
        """Test no match when initials differ"""
        assert normalizer.names_match_with_initials("J. Smith", "Robert Smith") is False


class TestInitialVariants:
    """Test initial variant generation"""

    @pytest.fixture
    def normalizer(self):
        """Create NameNormalizer instance"""
        return NameNormalizer()

    def test_generate_variants_basic(self, normalizer):
        """Test basic variant generation"""
        variants = normalizer.get_initial_variants("John Smith")
        assert "john smith" in variants
        assert "j. smith" in variants
        assert "j smith" in variants

    def test_generate_variants_single_name(self, normalizer):
        """Test variant generation for single name"""
        variants = normalizer.get_initial_variants("John")
        # Single name shouldn't generate initial variants
        assert "john" in variants

    def test_generate_variants_empty(self, normalizer):
        """Test variant generation for empty string"""
        variants = normalizer.get_initial_variants("")
        assert "" in variants


class TestCustomPrefixesSuffixes:
    """Test custom prefix and suffix support"""

    def test_custom_prefix(self):
        """Test adding custom prefix"""
        normalizer = NameNormalizer(custom_prefixes={"saint", "st."})
        result = normalizer.normalize("Saint Patrick")
        assert result.normalized == "patrick"
        assert "Saint" in result.stripped_prefixes

    def test_custom_suffix(self):
        """Test adding custom suffix"""
        normalizer = NameNormalizer(custom_suffixes={"ceo"})
        result = normalizer.normalize("John Smith CEO")
        assert result.normalized == "john smith"
        assert "CEO" in result.stripped_suffixes

    def test_custom_and_default_combined(self):
        """Test custom prefixes/suffixes are added to defaults"""
        normalizer = NameNormalizer(custom_prefixes={"saint"})
        # Should still have default prefixes
        result = normalizer.normalize("Dr. Smith")
        assert result.normalized == "smith"


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    @pytest.fixture
    def normalizer(self):
        """Create NameNormalizer instance"""
        return NameNormalizer()

    def test_only_prefix(self, normalizer):
        """Test name that is only a prefix"""
        result = normalizer.normalize("Dr.")
        assert result.normalized == ""

    def test_only_suffix(self, normalizer):
        """Test name that is only a suffix"""
        result = normalizer.normalize("PhD")
        assert result.normalized == ""

    def test_numbers_in_name(self, normalizer):
        """Test name with numbers"""
        result = normalizer.normalize("John Smith 2nd")
        # "2nd" should be stripped as suffix
        assert "john smith" == result.normalized

    def test_unicode_name(self, normalizer):
        """Test unicode characters in name"""
        result = normalizer.normalize("José García")
        assert result.normalized == "josé garcía"

    def test_very_long_name(self, normalizer):
        """Test very long name"""
        long_name = "Dr. John Robert William Smith III PhD"
        result = normalizer.normalize(long_name)
        assert "john robert william smith" == result.normalized

