"""
Unit tests for AbbreviationExpander

Tests abbreviation/acronym expansion, bidirectional matching,
dictionary loading, and common patterns.
"""

import json
import tempfile
import pytest

from aiecs.application.knowledge_graph.fusion.abbreviation_expander import (
    AbbreviationExpander,
    AbbreviationMatch,
)


class TestAbbreviationExpander:
    """Test AbbreviationExpander class"""

    @pytest.fixture
    def expander(self):
        """Create AbbreviationExpander instance"""
        return AbbreviationExpander()

    # --- Basic Operations ---

    def test_add_and_lookup_abbreviation(self, expander):
        """Test adding and looking up an abbreviation"""
        expander.add_abbreviation("MIT", ["Massachusetts Institute of Technology"])
        
        match = expander.lookup("MIT")
        assert match is not None
        assert match.abbreviation == "MIT"
        assert "Massachusetts Institute of Technology" in match.full_forms

    def test_lookup_case_insensitive(self, expander):
        """Test case-insensitive lookup"""
        expander.add_abbreviation("MIT", ["Massachusetts Institute of Technology"])
        
        # Should find with different cases
        assert expander.lookup("mit") is not None
        assert expander.lookup("Mit") is not None
        assert expander.lookup("MIT") is not None

    def test_lookup_nonexistent(self, expander):
        """Test lookup for nonexistent abbreviation"""
        assert expander.lookup("NONEXISTENT") is None

    # --- Bidirectional Matching ---

    def test_bidirectional_lookup_abbrev_to_full(self, expander):
        """Test lookup from abbreviation to full form"""
        expander.add_abbreviation("NASA", ["National Aeronautics and Space Administration"])
        
        match = expander.lookup("NASA")
        assert match is not None
        assert "National Aeronautics and Space Administration" in match.full_forms

    def test_bidirectional_lookup_full_to_abbrev(self, expander):
        """Test lookup from full form to abbreviation"""
        expander.add_abbreviation("NASA", ["National Aeronautics and Space Administration"])
        
        match = expander.lookup("National Aeronautics and Space Administration")
        assert match is not None
        assert match.abbreviation == "NASA"

    def test_bidirectional_matches(self, expander):
        """Test matches() for bidirectional matching"""
        expander.add_abbreviation("NYC", ["New York City", "New York"])
        
        # Should match abbreviation to full form
        assert expander.matches("NYC", "New York City") is True
        assert expander.matches("New York", "NYC") is True
        
        # Should match full forms to each other
        assert expander.matches("New York City", "New York") is True

    def test_no_match_different_abbreviations(self, expander):
        """Test that different abbreviations don't match"""
        expander.add_abbreviation("NYC", ["New York City"])
        expander.add_abbreviation("LA", ["Los Angeles"])
        
        assert expander.matches("NYC", "LA") is False
        assert expander.matches("New York City", "Los Angeles") is False

    # --- Get All Forms ---

    def test_get_all_forms(self, expander):
        """Test getting all equivalent forms"""
        expander.add_abbreviation("MIT", ["Massachusetts Institute of Technology", "M.I.T."])
        
        forms = expander.get_all_forms("MIT")
        assert "MIT" in forms
        assert "mit" in forms
        assert "Massachusetts Institute of Technology" in forms
        assert "M.I.T." in forms

    def test_get_all_forms_unknown(self, expander):
        """Test get_all_forms for unknown text"""
        forms = expander.get_all_forms("Unknown Text")
        assert "Unknown Text" in forms
        assert "unknown text" in forms
        assert len(forms) == 2

    # --- Categories ---

    def test_category_assignment(self, expander):
        """Test category assignment"""
        expander.add_abbreviation("MIT", ["Massachusetts Institute of Technology"], category="organization")
        
        match = expander.lookup("MIT")
        assert match.category == "organization"

    def test_get_by_category(self, expander):
        """Test getting abbreviations by category"""
        expander.add_abbreviation("MIT", ["Massachusetts Institute of Technology"], category="organization")
        expander.add_abbreviation("NASA", ["National Aeronautics and Space Administration"], category="organization")
        expander.add_abbreviation("NYC", ["New York City"], category="geographic")
        
        org_abbrevs = expander.get_abbreviations_by_category("organization")
        assert len(org_abbrevs) == 2
        assert "mit" in org_abbrevs
        assert "nasa" in org_abbrevs

    # --- Dictionary Loading ---

    def test_load_from_dict(self, expander):
        """Test loading from dictionary"""
        data = {
            "MIT": ["Massachusetts Institute of Technology"],
            "NASA": ["National Aeronautics and Space Administration"],
        }
        
        count = expander.load_from_dict(data)
        assert count == 2
        assert expander.lookup("MIT") is not None
        assert expander.lookup("NASA") is not None

    def test_load_from_json(self, expander):
        """Test loading from JSON file"""
        data = {
            "API": ["Application Programming Interface"],
            "CPU": ["Central Processing Unit"],
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        
        count = expander.load_from_json(temp_path, category="technical")
        assert count == 2
        
        match = expander.lookup("API")
        assert match is not None
        assert match.category == "technical"

    def test_load_from_nonexistent_json(self, expander):
        """Test loading from nonexistent JSON file"""
        count = expander.load_from_json("/nonexistent/path.json")
        assert count == 0


class TestCommonAbbreviations:
    """Test common abbreviation patterns"""

    @pytest.fixture
    def expander(self):
        """Create AbbreviationExpander with common abbreviations"""
        exp = AbbreviationExpander()
        exp.load_common_abbreviations()
        return exp

    def test_organization_abbreviations(self, expander):
        """Test organization abbreviations are loaded"""
        assert expander.lookup("MIT") is not None
        assert expander.lookup("NASA") is not None
        assert expander.lookup("IBM") is not None

    def test_geographic_abbreviations(self, expander):
        """Test geographic abbreviations are loaded"""
        assert expander.lookup("NYC") is not None
        assert expander.lookup("LA") is not None
        assert expander.lookup("USA") is not None

    def test_technical_abbreviations(self, expander):
        """Test technical abbreviations are loaded"""
        assert expander.lookup("API") is not None
        assert expander.lookup("CPU") is not None
        assert expander.lookup("AI") is not None
        assert expander.lookup("LLM") is not None

    def test_common_bidirectional(self, expander):
        """Test bidirectional matching with common abbreviations"""
        assert expander.matches("MIT", "Massachusetts Institute of Technology") is True
        assert expander.matches("New York City", "NYC") is True
        assert expander.matches("Artificial Intelligence", "AI") is True


class TestExportImport:
    """Test export and import functionality"""

    @pytest.fixture
    def expander(self):
        """Create AbbreviationExpander instance"""
        return AbbreviationExpander()

    def test_to_dict(self, expander):
        """Test exporting to dictionary"""
        expander.add_abbreviation("MIT", ["Massachusetts Institute of Technology"])
        expander.add_abbreviation("NASA", ["National Aeronautics and Space Administration"])

        data = expander.to_dict()
        assert "mit" in data
        assert "nasa" in data

    def test_save_to_json(self, expander):
        """Test saving to JSON file"""
        expander.add_abbreviation("API", ["Application Programming Interface"])

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        expander.save_to_json(temp_path)

        # Verify file contents
        with open(temp_path, "r") as f:
            data = json.load(f)

        assert "api" in data
        assert "Application Programming Interface" in data["api"]

    def test_size_and_clear(self, expander):
        """Test size and clear operations"""
        assert expander.size() == 0

        expander.add_abbreviation("MIT", ["Massachusetts Institute of Technology"])
        expander.add_abbreviation("NASA", ["National Aeronautics and Space Administration"])
        assert expander.size() == 2

        expander.clear()
        assert expander.size() == 0
        assert expander.lookup("MIT") is None


class TestMultipleFullForms:
    """Test handling multiple full forms for an abbreviation"""

    @pytest.fixture
    def expander(self):
        """Create AbbreviationExpander instance"""
        return AbbreviationExpander()

    def test_multiple_full_forms(self, expander):
        """Test abbreviation with multiple full forms"""
        expander.add_abbreviation("DC", [
            "District of Columbia",
            "Washington DC",
            "Washington D.C.",
        ])

        match = expander.lookup("DC")
        assert len(match.full_forms) == 3
        assert "District of Columbia" in match.full_forms
        assert "Washington DC" in match.full_forms
        assert "Washington D.C." in match.full_forms

    def test_any_full_form_matches(self, expander):
        """Test that any full form matches the abbreviation"""
        expander.add_abbreviation("DC", [
            "District of Columbia",
            "Washington DC",
        ])

        # All forms should match
        assert expander.matches("DC", "District of Columbia") is True
        assert expander.matches("DC", "Washington DC") is True
        assert expander.matches("District of Columbia", "Washington DC") is True

