"""
Abbreviation Expander

Handles acronym and abbreviation expansion for entity matching.
Supports configurable dictionaries and bidirectional matching.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AbbreviationMatch:
    """Result of abbreviation lookup"""
    abbreviation: str
    full_forms: List[str]
    category: Optional[str] = None  # e.g., "organization", "geographic", "technical"


class AbbreviationExpander:
    """
    Expand and match abbreviations/acronyms.
    
    Supports:
    - Configurable abbreviation dictionaries (JSON format)
    - Common patterns (organization, geographic, technical)
    - Bidirectional matching (abbreviation ↔ full form)
    - Domain-specific dictionary loading
    
    Example:
        ```python
        expander = AbbreviationExpander()
        
        # Load common abbreviations
        expander.load_common_abbreviations()
        
        # Add custom abbreviation
        expander.add_abbreviation("MIT", ["Massachusetts Institute of Technology"])
        
        # Bidirectional lookup
        match = expander.lookup("MIT")
        assert "Massachusetts Institute of Technology" in match.full_forms
        
        match = expander.lookup("Massachusetts Institute of Technology")
        assert match.abbreviation == "MIT"
        ```
    """

    def __init__(self):
        """Initialize AbbreviationExpander"""
        # abbreviation -> full forms
        self._abbrev_to_full: Dict[str, List[str]] = {}
        # full form (lowercase) -> abbreviation
        self._full_to_abbrev: Dict[str, str] = {}
        # category for each abbreviation
        self._categories: Dict[str, str] = {}

    def add_abbreviation(
        self,
        abbreviation: str,
        full_forms: List[str],
        category: Optional[str] = None,
    ) -> None:
        """
        Add an abbreviation mapping.
        
        Args:
            abbreviation: The abbreviation (e.g., "MIT")
            full_forms: List of full forms (e.g., ["Massachusetts Institute of Technology"])
            category: Optional category (e.g., "organization")
        """
        abbrev_key = abbreviation.lower()
        self._abbrev_to_full[abbrev_key] = full_forms
        
        if category:
            self._categories[abbrev_key] = category
        
        # Build reverse index for bidirectional lookup
        for full_form in full_forms:
            self._full_to_abbrev[full_form.lower()] = abbreviation

    def lookup(self, text: str) -> Optional[AbbreviationMatch]:
        """
        Look up an abbreviation or full form.
        
        Supports bidirectional matching:
        - "MIT" → full forms
        - "Massachusetts Institute of Technology" → abbreviation
        
        Args:
            text: The text to look up
            
        Returns:
            AbbreviationMatch if found, None otherwise
        """
        text_lower = text.lower()
        
        # Try abbreviation -> full form
        if text_lower in self._abbrev_to_full:
            return AbbreviationMatch(
                abbreviation=text,
                full_forms=self._abbrev_to_full[text_lower],
                category=self._categories.get(text_lower),
            )
        
        # Try full form -> abbreviation
        if text_lower in self._full_to_abbrev:
            abbrev = self._full_to_abbrev[text_lower]
            abbrev_lower = abbrev.lower()
            return AbbreviationMatch(
                abbreviation=abbrev,
                full_forms=self._abbrev_to_full.get(abbrev_lower, [text]),
                category=self._categories.get(abbrev_lower),
            )
        
        return None

    def get_all_forms(self, text: str) -> Set[str]:
        """
        Get all equivalent forms of a text (abbreviation + full forms).
        
        Args:
            text: The text to expand
            
        Returns:
            Set of all equivalent forms (including original)
        """
        forms = {text, text.lower()}
        
        match = self.lookup(text)
        if match:
            forms.add(match.abbreviation)
            forms.add(match.abbreviation.lower())
            for full_form in match.full_forms:
                forms.add(full_form)
                forms.add(full_form.lower())
        
        return forms

    def matches(self, text1: str, text2: str) -> bool:
        """
        Check if two texts match via abbreviation expansion.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            True if texts match (same abbreviation or same full form)
        """
        forms1 = self.get_all_forms(text1)
        forms2 = self.get_all_forms(text2)
        return bool(forms1 & forms2)

    def load_from_dict(
        self,
        data: Dict[str, List[str]],
        category: Optional[str] = None,
    ) -> int:
        """
        Load abbreviations from a dictionary.

        Args:
            data: Dictionary of abbreviation -> full forms
            category: Optional category for all entries

        Returns:
            Number of abbreviations loaded
        """
        count = 0
        for abbrev, full_forms in data.items():
            self.add_abbreviation(abbrev, full_forms, category)
            count += 1
        return count

    def load_from_json(self, filepath: str, category: Optional[str] = None) -> int:
        """
        Load abbreviations from a JSON file.

        JSON format:
        ```json
        {
            "MIT": ["Massachusetts Institute of Technology", "MIT"],
            "NYC": ["New York City", "New York", "NYC"]
        }
        ```

        Args:
            filepath: Path to JSON file
            category: Optional category for all entries

        Returns:
            Number of abbreviations loaded
        """
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Abbreviation file not found: {filepath}")
            return 0

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self.load_from_dict(data, category)

    def load_common_abbreviations(self) -> int:
        """
        Load common abbreviation patterns.

        Categories:
        - Organization abbreviations (MIT, NASA, etc.)
        - Geographic abbreviations (NYC, LA, etc.)
        - Technical abbreviations (API, CPU, etc.)

        Returns:
            Number of abbreviations loaded
        """
        total = 0

        # Organization abbreviations
        org_abbrevs = {
            "MIT": ["Massachusetts Institute of Technology"],
            "NASA": ["National Aeronautics and Space Administration"],
            "IBM": ["International Business Machines"],
            "AT&T": ["American Telephone and Telegraph", "AT and T"],
            "FBI": ["Federal Bureau of Investigation"],
            "CIA": ["Central Intelligence Agency"],
            "WHO": ["World Health Organization"],
            "UN": ["United Nations"],
            "EU": ["European Union"],
            "NATO": ["North Atlantic Treaty Organization"],
            "OPEC": ["Organization of the Petroleum Exporting Countries"],
            "IMF": ["International Monetary Fund"],
            "WTO": ["World Trade Organization"],
            "UNICEF": ["United Nations Children's Fund"],
            "UNESCO": ["United Nations Educational, Scientific and Cultural Organization"],
        }
        total += self.load_from_dict(org_abbrevs, "organization")

        # Geographic abbreviations
        geo_abbrevs = {
            "NYC": ["New York City", "New York"],
            "LA": ["Los Angeles"],
            "SF": ["San Francisco"],
            "DC": ["District of Columbia", "Washington DC", "Washington D.C."],
            "UK": ["United Kingdom", "Great Britain"],
            "USA": ["United States of America", "United States", "US"],
            "UAE": ["United Arab Emirates"],
        }
        total += self.load_from_dict(geo_abbrevs, "geographic")

        # Technical abbreviations
        tech_abbrevs = {
            "API": ["Application Programming Interface"],
            "CPU": ["Central Processing Unit"],
            "GPU": ["Graphics Processing Unit"],
            "RAM": ["Random Access Memory"],
            "ROM": ["Read Only Memory"],
            "SSD": ["Solid State Drive"],
            "HDD": ["Hard Disk Drive"],
            "URL": ["Uniform Resource Locator"],
            "HTML": ["HyperText Markup Language"],
            "CSS": ["Cascading Style Sheets"],
            "JSON": ["JavaScript Object Notation"],
            "XML": ["Extensible Markup Language"],
            "SQL": ["Structured Query Language"],
            "AI": ["Artificial Intelligence"],
            "ML": ["Machine Learning"],
            "NLP": ["Natural Language Processing"],
            "LLM": ["Large Language Model"],
        }
        total += self.load_from_dict(tech_abbrevs, "technical")

        logger.info(f"Loaded {total} common abbreviations")
        return total

    def get_abbreviations_by_category(self, category: str) -> List[str]:
        """
        Get all abbreviations in a category.

        Args:
            category: Category name (e.g., "organization")

        Returns:
            List of abbreviations in that category
        """
        return [
            abbrev for abbrev, cat in self._categories.items()
            if cat == category
        ]

    def size(self) -> int:
        """Get number of abbreviations in the expander"""
        return len(self._abbrev_to_full)

    def clear(self) -> None:
        """Clear all abbreviations"""
        self._abbrev_to_full.clear()
        self._full_to_abbrev.clear()
        self._categories.clear()

    def to_dict(self) -> Dict[str, List[str]]:
        """
        Export abbreviations as dictionary.

        Returns:
            Dictionary of abbreviation -> full forms
        """
        return dict(self._abbrev_to_full)

    def save_to_json(self, filepath: str) -> None:
        """
        Save abbreviations to a JSON file.

        Args:
            filepath: Path to output JSON file
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._abbrev_to_full, f, indent=2)

