"""
Data Quality Validation for Knowledge Graph Import

Provides validation capabilities to ensure data quality during import,
including range validation, outlier detection, completeness checks, and
type consistency validation.
"""

from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Check for pandas and numpy availability
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class ViolationType(Enum):
    """Types of data quality violations"""
    RANGE_VIOLATION = "range_violation"
    OUTLIER = "outlier"
    MISSING_VALUE = "missing_value"
    TYPE_MISMATCH = "type_mismatch"


@dataclass
class ValidationViolation:
    """
    Represents a single data quality violation
    
    Attributes:
        violation_type: Type of violation
        property_name: Property that violated the rule
        row_id: Identifier of the row with violation
        value: The violating value
        expected: Expected value or constraint
        message: Human-readable description
    """
    violation_type: ViolationType
    property_name: str
    row_id: Any
    value: Any
    expected: Any
    message: str


@dataclass
class QualityReport:
    """
    Data quality validation report
    
    Attributes:
        total_rows: Total number of rows validated
        violations: List of all violations found
        completeness: Completeness percentage per property
        outlier_count: Number of outliers detected per property
        range_violations: Number of range violations per property
        type_violations: Number of type violations per property
        passed: Whether validation passed (no critical violations)
    """
    total_rows: int
    violations: List[ValidationViolation] = field(default_factory=list)
    completeness: Dict[str, float] = field(default_factory=dict)
    outlier_count: Dict[str, int] = field(default_factory=dict)
    range_violations: Dict[str, int] = field(default_factory=dict)
    type_violations: Dict[str, int] = field(default_factory=dict)
    passed: bool = True
    
    def add_violation(self, violation: ValidationViolation):
        """Add a violation to the report"""
        self.violations.append(violation)
        
        # Update counts
        if violation.violation_type == ViolationType.RANGE_VIOLATION:
            self.range_violations[violation.property_name] = \
                self.range_violations.get(violation.property_name, 0) + 1
        elif violation.violation_type == ViolationType.OUTLIER:
            self.outlier_count[violation.property_name] = \
                self.outlier_count.get(violation.property_name, 0) + 1
        elif violation.violation_type == ViolationType.TYPE_MISMATCH:
            self.type_violations[violation.property_name] = \
                self.type_violations.get(violation.property_name, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the quality report"""
        return {
            "total_rows": self.total_rows,
            "total_violations": len(self.violations),
            "range_violations": sum(self.range_violations.values()),
            "outliers": sum(self.outlier_count.values()),
            "type_violations": sum(self.type_violations.values()),
            "completeness": self.completeness,
            "passed": self.passed
        }


@dataclass
class RangeRule:
    """Range validation rule for numeric properties"""
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class ValidationConfig:
    """
    Configuration for data quality validation
    
    Attributes:
        range_rules: Range validation rules per property
        required_properties: Set of required properties
        detect_outliers: Whether to detect outliers (3 std devs)
        fail_on_violations: Whether to fail import on violations
        max_violation_rate: Maximum allowed violation rate (0.0-1.0)
    """
    range_rules: Dict[str, RangeRule] = field(default_factory=dict)
    required_properties: Set[str] = field(default_factory=set)
    detect_outliers: bool = False
    fail_on_violations: bool = False
    max_violation_rate: float = 0.1  # 10% by default


class DataQualityValidator:
    """
    Validates data quality during knowledge graph import

    Provides range validation, outlier detection, completeness checks,
    and type consistency validation.
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize validator with configuration

        Args:
            config: Validation configuration
        """
        self.config = config or ValidationConfig()
        self._property_stats: Dict[str, Dict[str, float]] = {}

    def validate_dataframe(self, df: 'pd.DataFrame', id_column: Optional[str] = None) -> QualityReport:
        """
        Validate a pandas DataFrame

        Args:
            df: DataFrame to validate
            id_column: Column to use as row identifier

        Returns:
            QualityReport with validation results
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas and numpy are required for data quality validation")

        report = QualityReport(total_rows=len(df))

        # Use index as row ID if no id_column specified
        row_ids = df[id_column] if id_column and id_column in df.columns else df.index

        # Check completeness
        self._check_completeness(df, report)

        # Check required properties
        self._check_required_properties(df, row_ids, report)

        # Validate ranges
        self._validate_ranges(df, row_ids, report)

        # Detect outliers
        if self.config.detect_outliers:
            self._detect_outliers(df, row_ids, report)

        # Check if validation passed
        violation_rate = len(report.violations) / max(report.total_rows, 1)
        if self.config.fail_on_violations and violation_rate > self.config.max_violation_rate:
            report.passed = False

        return report

    def _check_completeness(self, df: 'pd.DataFrame', report: QualityReport):
        """Check completeness of properties"""
        for col in df.columns:
            non_null_count = df[col].notna().sum()
            completeness = non_null_count / len(df) if len(df) > 0 else 0.0
            report.completeness[col] = completeness

    def _check_required_properties(self, df: 'pd.DataFrame', row_ids: Any, report: QualityReport):
        """Check that required properties are present and non-null"""
        for prop in self.config.required_properties:
            if prop not in df.columns:
                # Property missing entirely
                violation = ValidationViolation(
                    violation_type=ViolationType.MISSING_VALUE,
                    property_name=prop,
                    row_id="ALL",
                    value=None,
                    expected="required property",
                    message=f"Required property '{prop}' is missing from dataset"
                )
                report.add_violation(violation)
            else:
                # Check for null values in required property
                null_mask = df[prop].isna()
                for idx in df[null_mask].index:
                    row_id = row_ids.iloc[idx] if hasattr(row_ids, 'iloc') else row_ids[idx]
                    violation = ValidationViolation(
                        violation_type=ViolationType.MISSING_VALUE,
                        property_name=prop,
                        row_id=row_id,
                        value=None,
                        expected="non-null value",
                        message=f"Required property '{prop}' is null in row {row_id}"
                    )
                    report.add_violation(violation)

    def _validate_ranges(self, df: 'pd.DataFrame', row_ids: Any, report: QualityReport):
        """Validate numeric properties are within specified ranges"""
        for prop, rule in self.config.range_rules.items():
            if prop not in df.columns:
                continue

            # Only validate numeric columns
            if not pd.api.types.is_numeric_dtype(df[prop]):
                continue

            # Check min value
            if rule.min_value is not None:
                violations_mask = df[prop] < rule.min_value
                for idx in df[violations_mask].index:
                    row_id = row_ids.iloc[idx] if hasattr(row_ids, 'iloc') else row_ids[idx]
                    value = df[prop].iloc[idx]
                    violation = ValidationViolation(
                        violation_type=ViolationType.RANGE_VIOLATION,
                        property_name=prop,
                        row_id=row_id,
                        value=value,
                        expected=f">= {rule.min_value}",
                        message=f"Value {value} is below minimum {rule.min_value} for property '{prop}' in row {row_id}"
                    )
                    report.add_violation(violation)

            # Check max value
            if rule.max_value is not None:
                violations_mask = df[prop] > rule.max_value
                for idx in df[violations_mask].index:
                    row_id = row_ids.iloc[idx] if hasattr(row_ids, 'iloc') else row_ids[idx]
                    value = df[prop].iloc[idx]
                    violation = ValidationViolation(
                        violation_type=ViolationType.RANGE_VIOLATION,
                        property_name=prop,
                        row_id=row_id,
                        value=value,
                        expected=f"<= {rule.max_value}",
                        message=f"Value {value} is above maximum {rule.max_value} for property '{prop}' in row {row_id}"
                    )
                    report.add_violation(violation)

    def _detect_outliers(self, df: 'pd.DataFrame', row_ids: Any, report: QualityReport):
        """Detect outliers using 3 standard deviations rule"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            # Skip if all values are null
            if df[col].isna().all():
                continue

            # Calculate mean and std
            mean = df[col].mean()
            std = df[col].std()

            # Skip if std is 0 or NaN
            if pd.isna(std) or std == 0:
                continue

            # Store stats for later use
            self._property_stats[col] = {"mean": mean, "std": std}

            # Detect outliers (beyond 3 standard deviations)
            lower_bound = mean - 3 * std
            upper_bound = mean + 3 * std
            outliers_mask = (df[col] < lower_bound) | (df[col] > upper_bound)

            for idx in df[outliers_mask].index:
                row_id = row_ids.iloc[idx] if hasattr(row_ids, 'iloc') else row_ids[idx]
                value = df[col].iloc[idx]
                violation = ValidationViolation(
                    violation_type=ViolationType.OUTLIER,
                    property_name=col,
                    row_id=row_id,
                    value=value,
                    expected=f"within [{lower_bound:.2f}, {upper_bound:.2f}]",
                    message=f"Value {value} is an outlier (>3 std devs) for property '{col}' in row {row_id}"
                )
                report.add_violation(violation)

