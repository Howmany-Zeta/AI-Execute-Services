"""
Domain Configuration Schema

Pydantic schema definitions for domain configuration validation.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from datetime import datetime
import re


class DomainSchema(BaseModel):
    """Schema for individual domain validation."""

    name: str = Field(..., min_length=3, max_length=50, description="Domain name")
    category: Optional[str] = Field(None, description="Domain category")
    description: Optional[str] = Field(None, description="Domain description")

    @validator('name')
    def validate_domain_name(cls, v):
        """Validate the domain name."""
        if not v.strip():
            raise ValueError("Domain name cannot be empty")

        # Check for proper capitalization (each word should start with capital)
        words = v.strip().split()
        for word in words:
            if word and not word[0].isupper():
                raise ValueError(f"Domain name should be properly capitalized: {v}")

        # Check for valid characters (letters, spaces, and some special characters)
        if not re.match(r'^[A-Za-z\s\-&]+$', v):
            raise ValueError(f"Domain name contains invalid characters: {v}")

        return v.strip()

    @validator('category')
    def validate_category(cls, v):
        """Validate the domain category."""
        if v is None:
            return v

        valid_categories = {
            'technology', 'business', 'science', 'social', 'creative', 'industry', 'research'
        }

        if v.lower() not in valid_categories:
            raise ValueError(f"Invalid category: {v}. Valid categories: {valid_categories}")

        return v.lower()

    class Config:
        """Pydantic configuration."""
        extra = "forbid"


class DomainListSchema(BaseModel):
    """Schema for the complete domain list."""

    domains: List[str] = Field(..., min_items=10, max_items=100, description="List of domain names")
    domain_count: Optional[int] = Field(None, description="Total number of domains")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")

    @validator('domains')
    def validate_domains_list(cls, v):
        """Validate the domains list."""
        if not v:
            raise ValueError("Domains list cannot be empty")

        # Check for duplicates
        unique_domains = set(v)
        if len(unique_domains) != len(v):
            duplicates = [domain for domain in v if v.count(domain) > 1]
            raise ValueError(f"Duplicate domains found: {set(duplicates)}")

        # Validate each domain
        for domain in v:
            if not domain or not domain.strip():
                raise ValueError("Domain list contains empty or whitespace-only entries")

            # Check domain naming pattern
            if not re.match(r'^[A-Z][a-zA-Z\s\-&]+$', domain.strip()):
                raise ValueError(f"Invalid domain name format: {domain}")

        # Check for core domains
        core_domains = {
            'Artificial Intelligence', 'Economics', 'Medicine', 'Psychology',
            'Education', 'Data Science', 'Finance'
        }

        domain_set = set(domain.strip() for domain in v)
        missing_core = core_domains - domain_set
        if missing_core:
            raise ValueError(f"Missing recommended core domains: {missing_core}")

        return v

    @validator('domain_count')
    def validate_domain_count(cls, v, values):
        """Validate the domain count matches the actual list length."""
        if v is not None and 'domains' in values:
            actual_count = len(values['domains'])
            if v != actual_count:
                raise ValueError(f"Domain count mismatch: specified {v}, actual {actual_count}")
        return v

    @validator('last_updated')
    def validate_last_updated(cls, v):
        """Validate the last updated timestamp."""
        if v is None:
            return v

        try:
            # Try to parse as ISO format
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}")

        return v

    class Config:
        """Pydantic configuration."""
        extra = "forbid"
        validate_assignment = True


class DomainCategorySchema(BaseModel):
    """Schema for domain category information."""

    category_name: str = Field(..., description="Name of the category")
    domains: List[str] = Field(..., description="Domains in this category")
    count: int = Field(..., description="Number of domains in category")
    coverage_percentage: float = Field(..., ge=0, le=100, description="Coverage percentage")

    @validator('category_name')
    def validate_category_name(cls, v):
        """Validate the category name."""
        valid_categories = {
            'technology', 'business', 'science', 'social', 'creative', 'industry', 'research'
        }

        if v.lower() not in valid_categories:
            raise ValueError(f"Invalid category: {v}. Valid categories: {valid_categories}")

        return v.lower()

    @validator('count')
    def validate_count(cls, v, values):
        """Validate the count matches the domains list length."""
        if 'domains' in values:
            actual_count = len(values['domains'])
            if v != actual_count:
                raise ValueError(f"Count mismatch: specified {v}, actual {actual_count}")
        return v

    class Config:
        """Pydantic configuration."""
        extra = "forbid"


class DomainStatisticsSchema(BaseModel):
    """Schema for domain statistics."""

    total_domains: int = Field(..., ge=0, description="Total number of domains")
    unique_domains: int = Field(..., ge=0, description="Number of unique domains")
    duplicate_count: int = Field(..., ge=0, description="Number of duplicate entries")
    category_breakdown: Dict[str, DomainCategorySchema] = Field(
        default_factory=dict, description="Breakdown by category"
    )
    core_domains_present: int = Field(..., ge=0, description="Number of core domains present")
    core_domains_missing: List[str] = Field(default_factory=list, description="Missing core domains")
    unexpected_domains: List[str] = Field(default_factory=list, description="Unexpected domains")
    average_domain_length: float = Field(..., ge=0, description="Average domain name length")
    longest_domain: Optional[str] = Field(None, description="Longest domain name")
    shortest_domain: Optional[str] = Field(None, description="Shortest domain name")

    @validator('unique_domains')
    def validate_unique_domains(cls, v, values):
        """Validate unique domains count."""
        if 'total_domains' in values and 'duplicate_count' in values:
            expected_unique = values['total_domains'] - values['duplicate_count']
            if v != expected_unique:
                raise ValueError(f"Unique domains count inconsistent: {v} != {expected_unique}")
        return v

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class DomainValidationSchema(BaseModel):
    """Schema for domain validation results."""

    is_valid: bool = Field(..., description="Whether the domain configuration is valid")
    errors: Dict[str, List[str]] = Field(default_factory=dict, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    statistics: Optional[DomainStatisticsSchema] = Field(None, description="Domain statistics")
    suggestions: List[str] = Field(default_factory=list, description="Suggested improvements")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class DomainSpecializationSchema(BaseModel):
    """Schema for domain specialization validation."""

    specialization_text: str = Field(..., description="Domain specialization text")
    referenced_domains: List[str] = Field(default_factory=list, description="Domains referenced in text")
    has_domain_reference: bool = Field(..., description="Whether it references the DOMAINS list")
    has_specific_examples: bool = Field(..., description="Whether it includes specific examples")
    has_tool_instructions: bool = Field(..., description="Whether it includes tool usage instructions")
    validation_result: DomainValidationSchema = Field(..., description="Validation result")

    @validator('specialization_text')
    def validate_specialization_text(cls, v):
        """Validate the specialization text."""
        if not v.strip():
            raise ValueError("Domain specialization text cannot be empty")

        # Check minimum length
        if len(v.strip()) < 50:
            raise ValueError("Domain specialization text is too short (minimum 50 characters)")

        return v.strip()

    @validator('has_domain_reference')
    def validate_domain_reference(cls, v, values):
        """Validate domain reference check."""
        if 'specialization_text' in values:
            text = values['specialization_text']
            actual_has_reference = 'DOMAINS' in text or 'base.py' in text
            if v != actual_has_reference:
                raise ValueError("Domain reference flag doesn't match actual content")
        return v

    class Config:
        """Pydantic configuration."""
        extra = "forbid"


class DomainConfigSchema(BaseModel):
    """Schema for the complete domain configuration."""

    domains: DomainListSchema = Field(..., description="Domain list configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Custom validation rules")

    class Config:
        """Pydantic configuration."""
        extra = "allow"
        validate_assignment = True
