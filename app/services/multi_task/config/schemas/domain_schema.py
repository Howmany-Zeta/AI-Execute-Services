"""
Domain Configuration Schema

Pydantic schema definitions for domain configuration validation.
"""

from pydantic import field_validator, model_validator, ConfigDict, BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from datetime import datetime
import re


class DomainSchema(BaseModel):
    """Schema for individual domain validation."""

    name: str = Field(..., min_length=3, max_length=50, description="Domain name")
    category: Optional[str] = Field(None, description="Domain category")
    description: Optional[str] = Field(None, description="Domain description")

    @field_validator('name')
    @classmethod
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

    @field_validator('category')
    @classmethod
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
    model_config = ConfigDict(extra="forbid")


class DomainListSchema(BaseModel):
    """Schema for the complete domain list."""

    domains: List[str] = Field(..., min_length=10, max_length=100, description="List of domain names")
    domain_count: Optional[int] = Field(None, description="Total number of domains")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")

    @field_validator('domains')
    @classmethod
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

    @model_validator(mode='after')
    def validate_domain_count(self) -> 'DomainListSchema':
        """Validate that the domain_count field matches the actual length of the domains list."""
        domain_count = self.domain_count
        domains = self.domains

        if domain_count is not None and domains is not None:
            actual_count = len(domains)
            if domain_count != actual_count:
                raise ValueError(f"Domain count mismatch: specified {domain_count}, but found {actual_count} domains in the list.")

        # Always return the self instance at the end
        return self

    @field_validator('last_updated')
    @classmethod
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
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class DomainCategorySchema(BaseModel):
    """Schema for domain category information."""

    category_name: str = Field(..., description="Name of the category")
    domains: List[str] = Field(..., description="Domains in this category")
    count: int = Field(..., description="Number of domains in category")
    coverage_percentage: float = Field(..., ge=0, le=100, description="Coverage percentage")

    @field_validator('category_name')
    @classmethod
    def validate_category_name(cls, v):
        """Validate the category name."""
        valid_categories = {
            'technology', 'business', 'science', 'social', 'creative', 'industry', 'research'
        }

        if v.lower() not in valid_categories:
            raise ValueError(f"Invalid category: {v}. Valid categories: {valid_categories}")

        return v.lower()

    @model_validator(mode='after')
    def validate_count(self) -> 'DomainCategorySchema':
        """Validate that the count field matches the actual length of the domains list."""
        # Use self to access the model's fields
        count = self.count
        domains = self.domains

        if domains is not None:
            actual_count = len(domains)
            if count != actual_count:
                raise ValueError(f"Count mismatch: specified count is {count}, but found {actual_count} domains in the list.")

        # Always return the self instance at the end
        return self

    model_config = ConfigDict(extra="forbid")


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

    @model_validator(mode='after')
    def validate_unique_domains(self) -> 'DomainStatisticsSchema':
        """Validate that the unique_domains count is consistent with total_domains and duplicate_count."""
        # Use self to access the model's fields
        unique_domains = self.unique_domains
        total_domains = self.total_domains
        duplicate_count = self.duplicate_count

        if total_domains is not None and duplicate_count is not None:
            expected_unique = total_domains - duplicate_count
            if unique_domains != expected_unique:
                raise ValueError(f"Unique domains count is inconsistent: expected {expected_unique}, but got {unique_domains}")

        # Always return the self instance at the end
        return self

    model_config = ConfigDict(extra="allow")


class DomainValidationSchema(BaseModel):
    """Schema for domain validation results."""

    is_valid: bool = Field(..., description="Whether the domain configuration is valid")
    errors: Dict[str, List[str]] = Field(default_factory=dict, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    statistics: Optional[DomainStatisticsSchema] = Field(None, description="Domain statistics")
    suggestions: List[str] = Field(default_factory=list, description="Suggested improvements")
    model_config = ConfigDict(extra="allow")


class DomainSpecializationSchema(BaseModel):
    """Schema for domain specialization validation."""

    specialization_text: str = Field(..., description="Domain specialization text")
    referenced_domains: List[str] = Field(default_factory=list, description="Domains referenced in text")
    has_domain_reference: bool = Field(..., description="Whether it references the DOMAINS list")
    has_specific_examples: bool = Field(..., description="Whether it includes specific examples")
    has_tool_instructions: bool = Field(..., description="Whether it includes tool usage instructions")
    validation_result: DomainValidationSchema = Field(..., description="Validation result")

    @field_validator('specialization_text')
    @classmethod
    def validate_specialization_text(cls, v):
        """Validate the specialization text."""
        if not v.strip():
            raise ValueError("Domain specialization text cannot be empty")

        # Check minimum length
        if len(v.strip()) < 50:
            raise ValueError("Domain specialization text is too short (minimum 50 characters)")

        return v.strip()

    @model_validator(mode='after')
    def validate_domain_reference(self) -> 'DomainSpecializationSchema':
        """Validates that the has_domain_reference flag correctly reflects the content of specialization_text."""
        # Use self to access the model's fields
        has_domain_reference = self.has_domain_reference
        specialization_text = self.specialization_text

        if specialization_text is not None:
            actual_has_reference = 'DOMAINS' in specialization_text or 'base.py' in specialization_text
            if has_domain_reference != actual_has_reference:
                raise ValueError("The 'has_domain_reference' flag does not match the actual content of 'specialization_text'.")

        # Always return the self instance at the end
        return self

    model_config = ConfigDict(extra="forbid")


class DomainConfigSchema(BaseModel):
    """Schema for the complete domain configuration."""

    domains: DomainListSchema = Field(..., description="Domain list configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Custom validation rules")
    model_config = ConfigDict(extra="allow", validate_assignment=True)
