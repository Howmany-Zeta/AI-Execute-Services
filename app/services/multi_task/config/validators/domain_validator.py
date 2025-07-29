"""
Domain Configuration Validator

Validates domain lists and domain-related configurations to ensure
they contain valid domain names and proper domain specialization settings.
"""

from typing import List, Dict, Any, Set
import re
import logging
from .prompt_validator import ValidationResult

logger = logging.getLogger(__name__)


class DomainValidator:
    """
    Validator for domain configurations.

    Validates domain lists and domain-related settings to ensure
    they are properly configured and consistent.
    """

    def __init__(self):
        """Initialize the domain validator."""
        # Expected domain categories
        self.domain_categories = {
            'technology': {
                'Artificial Intelligence', 'Computer', 'Data Science',
                'Blockchain Technology', 'Biotechnology'
            },
            'business': {
                'Economics', 'Finance', 'Accounting', 'Marketing',
                'Management', 'Human Resources Management', 'Supply Chain'
            },
            'science': {
                'Medicine', 'Physics', 'Chemistry', 'Biology', 'Astronomy',
                'Earth Science', 'Mathematics', 'Statistics', 'Agricultural Science'
            },
            'social': {
                'Psychology', 'Education', 'Linguistics', 'History',
                'Literature', 'Philosophy', 'Journalism and Communication', 'Law'
            },
            'creative': {
                'Arts'
            },
            'industry': {
                'Automobile', 'Real Estate', 'Manufacturing', 'Service Industry'
            },
            'research': {
                'User Research', 'Product Manager'
            }
        }

        # Flatten all expected domains
        self.expected_domains = set()
        for category_domains in self.domain_categories.values():
            self.expected_domains.update(category_domains)

        # Domain naming patterns
        self.valid_domain_patterns = [
            r'^[A-Z][a-zA-Z\s]+$',  # Starts with capital, contains letters and spaces
            r'^[A-Z][a-zA-Z\s]+ [A-Z][a-zA-Z\s]+$',  # Multi-word domains
        ]

        # Minimum and maximum domain counts
        self.min_domains = 10
        self.max_domains = 100

        # Required core domains that should always be present
        self.core_domains = {
            'Artificial Intelligence', 'Economics', 'Medicine', 'Psychology',
            'Education', 'Data Science', 'Finance'
        }

    def validate_domains(self, domains: List[str]) -> ValidationResult:
        """
        Validate a list of domains.

        Args:
            domains: List of domain names to validate

        Returns:
            ValidationResult containing validation status and any errors
        """
        result = ValidationResult(is_valid=True, errors={}, warnings=[])

        try:
            # Basic structure validation
            self._validate_domain_structure(domains, result)

            if result.is_valid:
                # Validate individual domains
                self._validate_individual_domains(domains, result)

                # Validate domain coverage
                self._validate_domain_coverage(domains, result)

                # Validate domain consistency
                self._validate_domain_consistency(domains, result)

        except Exception as e:
            result.add_error('validation_error', f"Unexpected error during domain validation: {e}")
            logger.error(f"Error validating domains: {e}")

        return result

    def _validate_domain_structure(self, domains: List[str], result: ValidationResult) -> None:
        """Validate the basic structure of the domain list."""
        if not isinstance(domains, list):
            result.add_error('structure', 'Domains must be provided as a list')
            return

        if not domains:
            result.add_error('structure', 'Domain list cannot be empty')
            return

        # Check domain count
        if len(domains) < self.min_domains:
            result.add_warning(f"Domain list has only {len(domains)} domains, recommended minimum is {self.min_domains}")

        if len(domains) > self.max_domains:
            result.add_warning(f"Domain list has {len(domains)} domains, which may be too many (max recommended: {self.max_domains})")

        # Check for duplicates
        unique_domains = set(domains)
        if len(unique_domains) != len(domains):
            duplicates = [domain for domain in domains if domains.count(domain) > 1]
            result.add_error('duplicates', f"Duplicate domains found: {set(duplicates)}")

    def _validate_individual_domains(self, domains: List[str], result: ValidationResult) -> None:
        """Validate each individual domain."""
        invalid_domains = []
        empty_domains = []

        for domain in domains:
            # Check for empty or whitespace-only domains
            if not domain or not domain.strip():
                empty_domains.append(domain)
                continue

            # Check domain naming patterns
            is_valid_pattern = any(re.match(pattern, domain.strip()) for pattern in self.valid_domain_patterns)

            if not is_valid_pattern:
                invalid_domains.append(domain)

        if empty_domains:
            result.add_error('empty_domains', f"Empty or whitespace-only domains found: {empty_domains}")

        if invalid_domains:
            result.add_warning(f"Domains with non-standard naming patterns: {invalid_domains}")

    def _validate_domain_coverage(self, domains: List[str], result: ValidationResult) -> None:
        """Validate domain coverage across different categories."""
        domain_set = set(domain.strip() for domain in domains)

        # Check for core domains
        missing_core = self.core_domains - domain_set
        if missing_core:
            result.add_warning(f"Missing recommended core domains: {missing_core}")

        # Check category coverage
        category_coverage = {}
        for category, category_domains in self.domain_categories.items():
            covered = category_domains & domain_set
            category_coverage[category] = {
                'covered': len(covered),
                'total': len(category_domains),
                'percentage': len(covered) / len(category_domains) * 100 if category_domains else 0,
                'missing': category_domains - domain_set
            }

        # Report category coverage
        for category, coverage in category_coverage.items():
            if coverage['percentage'] < 50:
                result.add_warning(
                    f"Low coverage for {category} domains: {coverage['covered']}/{coverage['total']} "
                    f"({coverage['percentage']:.1f}%). Missing: {coverage['missing']}"
                )

        # Check for unexpected domains (not in our expected list)
        unexpected_domains = domain_set - self.expected_domains
        if unexpected_domains:
            result.add_warning(f"Unexpected domains (not in standard list): {unexpected_domains}")

    def _validate_domain_consistency(self, domains: List[str], result: ValidationResult) -> None:
        """Validate consistency in domain naming and organization."""
        domain_set = set(domain.strip() for domain in domains)

        # Check for similar domains that might be duplicates
        similar_pairs = []
        domain_list = list(domain_set)

        for i, domain1 in enumerate(domain_list):
            for domain2 in domain_list[i+1:]:
                # Check for similar names (simple similarity check)
                if self._are_domains_similar(domain1, domain2):
                    similar_pairs.append((domain1, domain2))

        if similar_pairs:
            result.add_warning(f"Similar domain names found (possible duplicates): {similar_pairs}")

        # Check for proper capitalization
        improperly_capitalized = []
        for domain in domain_set:
            if not self._is_properly_capitalized(domain):
                improperly_capitalized.append(domain)

        if improperly_capitalized:
            result.add_warning(f"Domains with improper capitalization: {improperly_capitalized}")

        # Check for overly long domain names
        long_domains = [domain for domain in domain_set if len(domain) > 50]
        if long_domains:
            result.add_warning(f"Overly long domain names: {long_domains}")

        # Check for overly short domain names
        short_domains = [domain for domain in domain_set if len(domain.strip()) < 3]
        if short_domains:
            result.add_warning(f"Very short domain names: {short_domains}")

    def _are_domains_similar(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are similar (possible duplicates)."""
        # Simple similarity check based on common words
        words1 = set(domain1.lower().split())
        words2 = set(domain2.lower().split())

        # If they share most words, they might be similar
        if words1 and words2:
            intersection = words1 & words2
            union = words1 | words2
            similarity = len(intersection) / len(union)
            return similarity > 0.7

        return False

    def _is_properly_capitalized(self, domain: str) -> bool:
        """Check if a domain name is properly capitalized."""
        # Each word should start with a capital letter
        words = domain.split()
        for word in words:
            if word and not word[0].isupper():
                return False
        return True

    def validate_domain_specialization(self, specialization_text: str, available_domains: List[str]) -> ValidationResult:
        """
        Validate domain specialization text in role configurations.

        Args:
            specialization_text: The domain specialization text to validate
            available_domains: List of available domains

        Returns:
            ValidationResult for the domain specialization
        """
        result = ValidationResult(is_valid=True, errors={}, warnings=[])

        try:
            if not specialization_text:
                result.add_warning("Domain specialization is empty")
                return result

            # Check if it references the domain list
            if 'DOMAINS' not in specialization_text and 'base.py' not in specialization_text:
                result.add_warning("Domain specialization should reference the DOMAINS list from base.py")

            # Extract mentioned domains from the text
            mentioned_domains = []
            domain_set = set(available_domains)

            for domain in domain_set:
                if domain in specialization_text:
                    mentioned_domains.append(domain)

            # Check if specific domains are mentioned
            if not mentioned_domains:
                result.add_warning("Domain specialization should include specific domain examples")
            else:
                # Validate that mentioned domains are in the available list
                invalid_domains = [domain for domain in mentioned_domains if domain not in domain_set]
                if invalid_domains:
                    result.add_error('invalid_domains', f"Referenced domains not in available list: {invalid_domains}")

            # Check for domain-specific instructions
            instruction_keywords = ['focus', 'specialize', 'adapt', 'use', 'apply']
            has_instructions = any(keyword in specialization_text.lower() for keyword in instruction_keywords)

            if not has_instructions:
                result.add_warning("Domain specialization should include specific instructions for domain adaptation")

            # Check for tool usage in domain context
            if 'tool' in specialization_text.lower() or 'operation' in specialization_text.lower():
                # This is good - domain specialization mentions tools
                pass
            else:
                result.add_warning("Domain specialization should specify how tools are used in domain context")

        except Exception as e:
            result.add_error('validation_error', f"Error validating domain specialization: {e}")
            logger.error(f"Error validating domain specialization: {e}")

        return result

    def get_domain_statistics(self, domains: List[str]) -> Dict[str, Any]:
        """
        Get statistics about the domain list.

        Args:
            domains: List of domains to analyze

        Returns:
            Dictionary containing domain statistics
        """
        domain_set = set(domain.strip() for domain in domains if domain and domain.strip())

        # Category breakdown
        category_stats = {}
        for category, category_domains in self.domain_categories.items():
            covered = category_domains & domain_set
            category_stats[category] = {
                'count': len(covered),
                'domains': list(covered),
                'coverage_percentage': len(covered) / len(category_domains) * 100 if category_domains else 0
            }

        # General statistics
        stats = {
            'total_domains': len(domain_set),
            'unique_domains': len(domain_set),
            'duplicate_count': len(domains) - len(domain_set),
            'category_breakdown': category_stats,
            'core_domains_present': len(self.core_domains & domain_set),
            'core_domains_missing': list(self.core_domains - domain_set),
            'unexpected_domains': list(domain_set - self.expected_domains),
            'average_domain_length': sum(len(domain) for domain in domain_set) / len(domain_set) if domain_set else 0,
            'longest_domain': max(domain_set, key=len) if domain_set else None,
            'shortest_domain': min(domain_set, key=len) if domain_set else None
        }

        return stats

    def suggest_missing_domains(self, current_domains: List[str]) -> List[str]:
        """
        Suggest domains that might be missing from the current list.

        Args:
            current_domains: Current list of domains

        Returns:
            List of suggested domains to add
        """
        current_set = set(domain.strip() for domain in current_domains if domain and domain.strip())

        # Start with core domains
        suggestions = list(self.core_domains - current_set)

        # Add domains from under-represented categories
        for category, category_domains in self.domain_categories.items():
            covered = category_domains & current_set
            coverage = len(covered) / len(category_domains) if category_domains else 0

            # If coverage is low, suggest more domains from this category
            if coverage < 0.5:
                missing = category_domains - current_set
                suggestions.extend(list(missing)[:2])  # Add up to 2 from each under-represented category

        return suggestions[:10]  # Return top 10 suggestions
