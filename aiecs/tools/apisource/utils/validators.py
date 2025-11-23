"""
Shared Validation Utilities for API Providers

Common validation functions for data quality assessment:
- Detect outliers in numeric data
- Find gaps in time series
- Check data completeness
- Validate data types and ranges
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Provides common data validation methods for API providers.
    """

    @staticmethod
    def detect_outliers(values: List[float], method: str = "iqr", threshold: float = 1.5) -> List[int]:
        """
        Detect outliers in numeric data.

        Args:
            values: List of numeric values
            method: Detection method ('iqr' or 'zscore')
            threshold: Threshold for outlier detection
                      - For IQR: typically 1.5 or 3.0
                      - For Z-score: typically 2.0 or 3.0

        Returns:
            List of indices where outliers were detected
        """
        if not values or len(values) < 4:
            return []

        outlier_indices = []

        if method == "iqr":
            # Interquartile Range method
            sorted_values = sorted(values)
            n = len(sorted_values)

            q1_idx = n // 4
            q3_idx = 3 * n // 4

            q1 = sorted_values[q1_idx]
            q3 = sorted_values[q3_idx]
            iqr = q3 - q1

            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr

            for i, value in enumerate(values):
                if value < lower_bound or value > upper_bound:
                    outlier_indices.append(i)

        elif method == "zscore":
            # Z-score method
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std_dev = variance**0.5

            if std_dev == 0:
                return []

            for i, value in enumerate(values):
                z_score = abs((value - mean) / std_dev)
                if z_score > threshold:
                    outlier_indices.append(i)

        return outlier_indices

    @staticmethod
    def detect_time_gaps(
        data: List[Dict[str, Any]],
        date_field: str = "date",
        expected_frequency: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect gaps in time series data.

        Args:
            data: List of data items with date fields
            date_field: Name of the date field
            expected_frequency: Expected frequency ('daily', 'weekly', 'monthly', 'quarterly', 'annual')

        Returns:
            List of gap information dictionaries
        """
        if len(data) < 2:
            return []

        gaps = []

        # Parse dates
        dates = []
        for i, item in enumerate(data):
            if date_field in item:
                try:
                    date_str = str(item[date_field])
                    if "T" in date_str:
                        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    dates.append((i, date_obj))
                except (ValueError, TypeError):
                    continue

        if len(dates) < 2:
            return []

        # Sort by date
        dates.sort(key=lambda x: x[1])

        # Determine expected gap if not specified
        if expected_frequency is None:
            # Estimate from first few intervals
            if len(dates) >= 3:
                intervals = [(dates[i + 1][1] - dates[i][1]).days for i in range(min(3, len(dates) - 1))]
                avg_interval = sum(intervals) / len(intervals)

                if avg_interval <= 2:
                    expected_frequency = "daily"
                elif avg_interval <= 10:
                    expected_frequency = "weekly"
                elif avg_interval <= 40:
                    expected_frequency = "monthly"
                elif avg_interval <= 120:
                    expected_frequency = "quarterly"
                else:
                    expected_frequency = "annual"

        # Define expected gaps in days
        frequency_gaps = {
            "daily": 1,
            "weekly": 7,
            "monthly": 31,
            "quarterly": 92,
            "annual": 365,
        }

        expected_gap_days = frequency_gaps.get(expected_frequency or "monthly", 31)
        tolerance = expected_gap_days * 0.5  # 50% tolerance

        # Check for gaps
        for i in range(len(dates) - 1):
            idx1, date1 = dates[i]
            idx2, date2 = dates[i + 1]

            gap_days = (date2 - date1).days

            if gap_days > expected_gap_days + tolerance:
                gaps.append(
                    {
                        "start_index": idx1,
                        "end_index": idx2,
                        "start_date": date1.isoformat(),
                        "end_date": date2.isoformat(),
                        "gap_days": gap_days,
                        "expected_days": expected_gap_days,
                    }
                )

        return gaps

    @staticmethod
    def check_data_completeness(
        data: List[Dict[str, Any]],
        value_field: str = "value",
        missing_indicators: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Check completeness of data.

        Args:
            data: List of data items
            value_field: Name of the value field to check
            missing_indicators: Values that indicate missing data (e.g., ['.', None, 'NA'])

        Returns:
            Completeness statistics dictionary
        """
        if missing_indicators is None:
            missing_indicators = [".", None, "NA", "N/A", "", "null"]

        total_records = len(data)
        if total_records == 0:
            return {
                "total_records": 0,
                "missing_count": 0,
                "completeness": 1.0,
                "missing_indices": [],
            }

        missing_count = 0
        missing_indices = []

        for i, item in enumerate(data):
            if value_field in item:
                value = item[value_field]
                # Check if value is missing
                if value in missing_indicators:
                    missing_count += 1
                    missing_indices.append(i)
                elif isinstance(value, str) and value.strip() in missing_indicators:
                    missing_count += 1
                    missing_indices.append(i)
            else:
                # Field doesn't exist
                missing_count += 1
                missing_indices.append(i)

        completeness = (total_records - missing_count) / total_records

        return {
            "total_records": total_records,
            "missing_count": missing_count,
            "present_count": total_records - missing_count,
            "completeness": round(completeness, 4),
            "missing_indices": missing_indices[:10],  # Limit to first 10
        }

    @staticmethod
    def calculate_value_range(
        data: List[Dict[str, Any]],
        value_field: str = "value",
        missing_indicators: Optional[List[Any]] = None,
    ) -> Optional[Dict[str, float]]:
        """
        Calculate min, max, mean of numeric values.

        Args:
            data: List of data items
            value_field: Name of the value field
            missing_indicators: Values to skip

        Returns:
            Dictionary with min, max, mean, or None if no valid data
        """
        if missing_indicators is None:
            missing_indicators = [".", None, "NA", "N/A", "", "null"]

        numeric_values = []

        for item in data:
            if value_field in item:
                value = item[value_field]

                # Skip missing indicators
                if value in missing_indicators:
                    continue

                # Try to convert to float
                try:
                    if isinstance(value, (int, float)):
                        numeric_values.append(float(value))
                    elif isinstance(value, str):
                        # Clean string (remove commas, etc.)
                        cleaned = value.strip().replace(",", "")
                        if cleaned and cleaned not in missing_indicators:
                            numeric_values.append(float(cleaned))
                except (ValueError, TypeError):
                    continue

        if not numeric_values:
            return None

        return {
            "min": min(numeric_values),
            "max": max(numeric_values),
            "mean": sum(numeric_values) / len(numeric_values),
            "count": len(numeric_values),
        }

    @staticmethod
    def infer_data_frequency(data: List[Dict[str, Any]], date_field: str = "date") -> Optional[str]:
        """
        Infer the frequency of time series data.

        Args:
            data: List of data items with dates
            date_field: Name of the date field

        Returns:
            Frequency string or None
        """
        if len(data) < 3:
            return None

        # Parse dates
        dates = []
        for item in data:
            if date_field in item:
                try:
                    date_str = str(item[date_field])
                    if "T" in date_str:
                        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    dates.append(date_obj)
                except (ValueError, TypeError):
                    continue

        if len(dates) < 3:
            return None

        # Sort dates
        dates.sort()

        # Calculate intervals
        intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]

        # Calculate median interval
        intervals.sort()
        median_interval = intervals[len(intervals) // 2]

        # Classify frequency
        if median_interval <= 2:
            return "daily"
        elif median_interval <= 10:
            return "weekly"
        elif median_interval <= 40:
            return "monthly"
        elif median_interval <= 120:
            return "quarterly"
        elif median_interval <= 400:
            return "annual"
        else:
            return "irregular"
