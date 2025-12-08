"""
Evaluation Dataset for Knowledge Fusion Matching.

Contains curated test cases with known entity matches and non-matches,
including edge cases for threshold validation and A/B testing.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class EntityPair:
    """
    A pair of entity names for evaluation.

    Attributes:
        name1: First entity name
        name2: Second entity name
        entity_type: Type of entities (e.g., "Person", "Organization")
        should_match: Whether these entities should be considered a match
        match_reason: Reason why they should/shouldn't match (for documentation)
        domain: Domain context (academic, corporate, medical, etc.)
    """

    name1: str
    name2: str
    entity_type: str = "Person"
    should_match: bool = True
    match_reason: str = ""
    domain: str = "general"


@dataclass
class EvaluationDataset:
    """
    Collection of entity pairs for evaluation.

    Attributes:
        pairs: List of entity pairs to evaluate
        name: Name/description of the dataset
    """

    pairs: List[EntityPair]
    name: str = "default"

    def __len__(self) -> int:
        """Return number of pairs in dataset."""
        return len(self.pairs)

    def get_by_domain(self, domain: str) -> "EvaluationDataset":
        """Filter pairs by domain."""
        filtered = [p for p in self.pairs if p.domain == domain]
        return EvaluationDataset(pairs=filtered, name=f"{self.name}_{domain}")

    def get_by_type(self, entity_type: str) -> "EvaluationDataset":
        """Filter pairs by entity type."""
        filtered = [p for p in self.pairs if p.entity_type == entity_type]
        return EvaluationDataset(pairs=filtered, name=f"{self.name}_{entity_type}")

    def get_positive_pairs(self) -> List[EntityPair]:
        """Get pairs that should match."""
        return [p for p in self.pairs if p.should_match]

    def get_negative_pairs(self) -> List[EntityPair]:
        """Get pairs that should not match."""
        return [p for p in self.pairs if not p.should_match]


def create_default_evaluation_dataset() -> EvaluationDataset:
    """
    Create default evaluation dataset with known matches and edge cases.

    Includes:
    - Name variations (initials, titles, suffixes)
    - Abbreviations/acronyms
    - Normalization cases
    - Semantic matches
    - False positives (similar but different entities)
    """
    pairs: List[EntityPair] = []

    # ============================================================================
    # Person Entity Matches (Academic Domain)
    # ============================================================================
    academic_person_pairs = [
        # Exact matches
        EntityPair("Albert Einstein", "Albert Einstein", "Person", True, "Exact match", "academic"),
        EntityPair("Dr. John Smith", "John Smith", "Person", True, "Title prefix", "academic"),
        EntityPair("John Smith, PhD", "John Smith", "Person", True, "Suffix", "academic"),
        EntityPair("Prof. Jane Doe", "Jane Doe", "Person", True, "Professor title", "academic"),
        
        # Initial variations
        EntityPair("A. Einstein", "Albert Einstein", "Person", True, "Initial expansion", "academic"),
        EntityPair("J. Smith", "John Smith", "Person", True, "Initial expansion", "academic"),
        EntityPair("J. K. Rowling", "Joanne Rowling", "Person", True, "Initial expansion", "academic"),
        EntityPair("M. L. King", "Martin Luther King", "Person", True, "Initial expansion", "academic"),
        
        # Name order variations
        EntityPair("Smith, John", "John Smith", "Person", True, "Name order", "academic"),
        EntityPair("Einstein, Albert", "Albert Einstein", "Person", True, "Name order", "academic"),
        
        # Title combinations
        EntityPair("Dr. A. Einstein", "Albert Einstein", "Person", True, "Title + initial", "academic"),
        EntityPair("Prof. J. Smith, PhD", "John Smith", "Person", True, "Title + initial + suffix", "academic"),
        
        # False positives (should NOT match)
        EntityPair("John Smith", "Jane Smith", "Person", False, "Different first names", "academic"),
        EntityPair("A. Einstein", "A. Newton", "Person", False, "Different surnames", "academic"),
        EntityPair("John Smith", "John Smyth", "Person", False, "Similar but different surname", "academic"),
    ]
    pairs.extend(academic_person_pairs)

    # ============================================================================
    # Organization Entity Matches (Corporate Domain)
    # ============================================================================
    corporate_org_pairs = [
        # Abbreviation matches
        EntityPair("MIT", "Massachusetts Institute of Technology", "Organization", True, "Abbreviation expansion", "corporate"),
        EntityPair("IBM", "International Business Machines", "Organization", True, "Abbreviation expansion", "corporate"),
        EntityPair("NASA", "National Aeronautics and Space Administration", "Organization", True, "Abbreviation expansion", "corporate"),
        EntityPair("NYC", "New York City", "Organization", True, "Abbreviation expansion", "corporate"),
        EntityPair("USA", "United States of America", "Organization", True, "Abbreviation expansion", "corporate"),
        
        # Name variations
        EntityPair("Apple Inc.", "Apple", "Organization", True, "Incorporation suffix", "corporate"),
        EntityPair("Apple Incorporated", "Apple Inc.", "Organization", True, "Full vs abbreviated suffix", "corporate"),
        EntityPair("Microsoft Corporation", "Microsoft", "Organization", True, "Corporation suffix", "corporate"),
        EntityPair("Microsoft Corp.", "Microsoft Corporation", "Organization", True, "Corp abbreviation", "corporate"),
        
        # Common name variations
        EntityPair("The New York Times", "New York Times", "Organization", True, "Article prefix", "corporate"),
        EntityPair("AT&T", "AT and T", "Organization", True, "Symbol expansion", "corporate"),
        
        # False positives
        EntityPair("Apple Inc.", "Apple Computer", "Organization", False, "Different company names", "corporate"),
        EntityPair("Microsoft", "Microsystems", "Organization", False, "Similar but different", "corporate"),
        EntityPair("IBM", "HP", "Organization", False, "Different abbreviations", "corporate"),
    ]
    pairs.extend(corporate_org_pairs)

    # ============================================================================
    # Medical Domain Entity Matches
    # ============================================================================
    medical_pairs = [
        # Medical abbreviations
        EntityPair("COVID-19", "Coronavirus Disease 2019", "Concept", True, "Medical abbreviation", "medical"),
        EntityPair("HIV", "Human Immunodeficiency Virus", "Concept", True, "Medical abbreviation", "medical"),
        EntityPair("AIDS", "Acquired Immunodeficiency Syndrome", "Concept", True, "Medical abbreviation", "medical"),
        EntityPair("DNA", "Deoxyribonucleic Acid", "Concept", True, "Scientific abbreviation", "medical"),
        EntityPair("RNA", "Ribonucleic Acid", "Concept", True, "Scientific abbreviation", "medical"),
        
        # Medical professional titles
        EntityPair("Dr. Sarah Johnson", "Sarah Johnson, MD", "Person", True, "MD suffix", "medical"),
        EntityPair("Dr. Michael Chen", "Michael Chen, M.D.", "Person", True, "M.D. suffix", "medical"),
        EntityPair("Dr. Emily Brown", "Emily Brown, Doctor", "Person", True, "Doctor title", "medical"),
        
        # Medical institution variations
        EntityPair("Mayo Clinic", "Mayo Medical Center", "Organization", True, "Clinic vs center", "medical"),
        EntityPair("Johns Hopkins Hospital", "Johns Hopkins", "Organization", True, "Hospital suffix", "medical"),
        
        # False positives
        EntityPair("COVID-19", "COVID-20", "Concept", False, "Different disease variant", "medical"),
        EntityPair("HIV", "HPV", "Concept", False, "Different viruses", "medical"),
    ]
    pairs.extend(medical_pairs)

    # ============================================================================
    # Edge Cases - Challenging Matches
    # ============================================================================
    edge_case_pairs = [
        # Very similar but different
        EntityPair("John Smith", "Jon Smith", "Person", False, "Different spelling", "general"),
        EntityPair("Steven", "Stephen", "Person", False, "Different spelling", "general"),
        EntityPair("Catherine", "Katherine", "Person", False, "Different spelling", "general"),
        
        # Substring cases
        EntityPair("New York", "New York City", "Organization", True, "Substring match", "general"),
        EntityPair("University", "State University", "Organization", False, "Too generic", "general"),
        
        # Special characters
        EntityPair("O'Brien", "OBrien", "Person", True, "Apostrophe normalization", "general"),
        EntityPair("José", "Jose", "Person", True, "Accent normalization", "general"),
        EntityPair("Müller", "Mueller", "Person", True, "Umlaut normalization", "general"),
        
        # Multiple word variations
        EntityPair("New York University", "NYU", "Organization", True, "Multi-word abbreviation", "general"),
        EntityPair("United States", "US", "Organization", True, "Country abbreviation", "general"),
        EntityPair("United Kingdom", "UK", "Organization", True, "Country abbreviation", "general"),
        
        # Case variations
        EntityPair("APPLE INC.", "apple inc.", "Organization", True, "Case normalization", "general"),
        EntityPair("JOHN SMITH", "john smith", "Person", True, "Case normalization", "general"),
        
        # Whitespace variations
        EntityPair("John  Smith", "John Smith", "Person", True, "Whitespace normalization", "general"),
        EntityPair("New  York", "New York", "Organization", True, "Whitespace normalization", "general"),
    ]
    pairs.extend(edge_case_pairs)

    # ============================================================================
    # Semantic Similarity Cases (should match via embeddings)
    # ============================================================================
    semantic_pairs = [
        # Synonyms and related terms
        EntityPair("Doctor", "Physician", "Person", True, "Semantic synonym", "medical"),
        EntityPair("Hospital", "Medical Center", "Organization", True, "Semantic similarity", "medical"),
        EntityPair("University", "College", "Organization", True, "Semantic similarity", "academic"),
        
        # Transliterations (if supported)
        EntityPair("München", "Munich", "Organization", True, "Transliteration", "general"),
        EntityPair("Moskva", "Moscow", "Organization", True, "Transliteration", "general"),
        
        # False semantic matches
        EntityPair("Apple", "Orange", "Organization", False, "Different fruits", "general"),
        EntityPair("Microsoft", "Apple", "Organization", False, "Different companies", "corporate"),
    ]
    pairs.extend(semantic_pairs)

    return EvaluationDataset(pairs=pairs, name="default_evaluation")


def create_minimal_evaluation_dataset() -> EvaluationDataset:
    """
    Create a minimal dataset for quick testing.

    Returns a small subset of the default dataset.
    """
    pairs = [
        # Positive matches
        EntityPair("Albert Einstein", "A. Einstein", "Person", True, "Initial expansion", "academic"),
        EntityPair("MIT", "Massachusetts Institute of Technology", "Organization", True, "Abbreviation", "corporate"),
        EntityPair("Dr. John Smith", "John Smith", "Person", True, "Title prefix", "academic"),
        
        # Negative matches
        EntityPair("John Smith", "Jane Smith", "Person", False, "Different names", "academic"),
        EntityPair("Apple Inc.", "Microsoft", "Organization", False, "Different companies", "corporate"),
    ]
    
    return EvaluationDataset(pairs=pairs, name="minimal_evaluation")
