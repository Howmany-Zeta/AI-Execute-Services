"""
Data Profiler Tool - Comprehensive data profiling and quality assessment

This tool provides advanced data profiling capabilities with:
- Statistical summaries and distributions
- Data quality issue detection
- Pattern and anomaly identification
- Preprocessing recommendations
- Column-level and dataset-level analysis
"""

import logging
from typing import Dict, Any, List, Optional, Union
from enum import Enum

import pandas as pd  # type: ignore[import-untyped]
import numpy as np
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class ProfileLevel(str, Enum):
    """Data profiling depth levels"""

    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    DEEP = "deep"


class DataQualityCheck(str, Enum):
    """Types of data quality checks"""

    MISSING_VALUES = "missing_values"
    DUPLICATES = "duplicates"
    OUTLIERS = "outliers"
    INCONSISTENCIES = "inconsistencies"
    DATA_TYPES = "data_types"
    DISTRIBUTIONS = "distributions"
    CORRELATIONS = "correlations"


class DataProfilerError(Exception):
    """Base exception for DataProfiler errors"""


class ProfilingError(DataProfilerError):
    """Raised when profiling operation fails"""


@register_tool("data_profiler")
class DataProfilerTool(BaseTool):
    """
    Comprehensive data profiling tool that can:
    1. Generate statistical summaries
    2. Detect data quality issues
    3. Identify patterns and anomalies
    4. Recommend preprocessing steps

    Integrates with stats_tool and pandas_tool for core operations.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the data profiler tool
        
        Automatically reads from environment variables with DATA_PROFILER_ prefix.
        Example: DATA_PROFILER_DEFAULT_PROFILE_LEVEL -> default_profile_level
        """

        model_config = SettingsConfigDict(env_prefix="DATA_PROFILER_")

        default_profile_level: str = Field(default="standard", description="Default profiling depth level")
        outlier_std_threshold: float = Field(
            default=3.0,
            description="Standard deviation threshold for outlier detection",
        )
        correlation_threshold: float = Field(
            default=0.7,
            description="Correlation threshold for identifying strong relationships",
        )
        missing_threshold: float = Field(
            default=0.5,
            description="Missing value threshold for quality assessment",
        )
        enable_visualizations: bool = Field(
            default=True,
            description="Whether to enable visualization generation",
        )
        max_unique_values_categorical: int = Field(
            default=50,
            description="Maximum unique values for categorical analysis",
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize DataProfilerTool with settings.

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/data_profiler.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)

        Args:
            config: Optional configuration overrides
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Initialize external tools
        self._init_external_tools()

    def _init_external_tools(self):
        """Initialize external task tools"""
        self.external_tools = {}

        # Initialize StatsTool for statistical operations
        try:
            from aiecs.tools.task_tools.stats_tool import StatsTool

            self.external_tools["stats"] = StatsTool()
            self.logger.info("StatsTool initialized successfully")
        except ImportError:
            self.logger.warning("StatsTool not available")
            self.external_tools["stats"] = None

        # Initialize PandasTool for data operations
        try:
            from aiecs.tools.task_tools.pandas_tool import PandasTool

            self.external_tools["pandas"] = PandasTool()
            self.logger.info("PandasTool initialized successfully")
        except ImportError:
            self.logger.warning("PandasTool not available")
            self.external_tools["pandas"] = None

    # Schema definitions
    class ProfileDatasetSchema(BaseModel):
        """Schema for profile_dataset operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data to profile")
        level: ProfileLevel = Field(default=ProfileLevel.STANDARD, description="Profiling depth level")
        checks: Optional[List[DataQualityCheck]] = Field(default=None, description="Specific quality checks to perform")
        generate_visualizations: bool = Field(default=False, description="Generate visualization data")

    class DetectQualityIssuesSchema(BaseModel):
        """Schema for detect_quality_issues operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data to check")
        checks: Optional[List[DataQualityCheck]] = Field(default=None, description="Specific checks to perform")

    class RecommendPreprocessingSchema(BaseModel):
        """Schema for recommend_preprocessing operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data to analyze")
        target_column: Optional[str] = Field(default=None, description="Target column for ML tasks")

    def profile_dataset(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        level: ProfileLevel = ProfileLevel.STANDARD,
        checks: Optional[List[DataQualityCheck]] = None,
        generate_visualizations: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive data profile.

        Args:
            data: Data to profile (dict, list of dicts, or DataFrame)
            level: Profiling depth level
            checks: Specific quality checks to perform (all if None)
            generate_visualizations: Whether to generate visualization data

        Returns:
            Dict containing:
                - summary: Dataset-level summary
                - column_profiles: Column-level profiles
                - quality_issues: Detected quality issues
                - correlations: Correlation analysis
                - recommendations: Preprocessing recommendations

        Raises:
            ProfilingError: If profiling fails
        """
        try:
            # Convert to DataFrame if needed
            df = self._to_dataframe(data)

            self.logger.info(f"Profiling dataset with {len(df)} rows and {len(df.columns)} columns")

            # Generate summary
            summary = self._generate_summary(df)

            # Generate column profiles
            column_profiles = self._profile_columns(df, level)

            # Detect quality issues
            quality_issues = self._detect_quality_issues(df, checks)

            # Correlation analysis (for comprehensive and deep levels)
            correlations = {}
            if level in [ProfileLevel.COMPREHENSIVE, ProfileLevel.DEEP]:
                correlations = self._analyze_correlations(df)

            # Generate recommendations
            recommendations = self._generate_recommendations(df, quality_issues, level)

            # Generate visualization data if requested
            visualization_data = {}
            if generate_visualizations:
                visualization_data = self._generate_visualization_data(df)

            result = {
                "summary": summary,
                "column_profiles": column_profiles,
                "quality_issues": quality_issues,
                "correlations": correlations,
                "recommendations": recommendations,
                "profile_level": level.value,
            }

            if visualization_data:
                result["visualization_data"] = visualization_data

            self.logger.info("Dataset profiling completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Error profiling dataset: {e}")
            raise ProfilingError(f"Failed to profile dataset: {e}")

    def detect_quality_issues(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        checks: Optional[List[DataQualityCheck]] = None,
    ) -> Dict[str, Any]:
        """
        Detect data quality issues.

        Args:
            data: Data to check
            checks: Specific checks to perform (all if None)

        Returns:
            Dict containing detected issues by category
        """
        try:
            df = self._to_dataframe(data)
            issues = self._detect_quality_issues(df, checks)

            return {
                "issues": issues,
                "total_issues": sum(len(v) for v in issues.values()),
                "severity_counts": self._categorize_severity(issues),
            }

        except Exception as e:
            self.logger.error(f"Error detecting quality issues: {e}")
            raise ProfilingError(f"Failed to detect quality issues: {e}")

    def recommend_preprocessing(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        target_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Recommend preprocessing steps based on data analysis.

        Args:
            data: Data to analyze
            target_column: Target column for ML tasks (if applicable)

        Returns:
            Dict containing recommended preprocessing steps
        """
        try:
            df = self._to_dataframe(data)

            # Detect quality issues
            quality_issues = self._detect_quality_issues(df, None)

            # Generate recommendations
            recommendations = self._generate_recommendations(df, quality_issues, ProfileLevel.COMPREHENSIVE)

            # Add task-specific recommendations
            if target_column and target_column in df.columns:
                task_recommendations = self._generate_task_recommendations(df, target_column)
                recommendations.extend(task_recommendations)

            # Prioritize recommendations
            prioritized = self._prioritize_recommendations(recommendations)

            return {
                "recommendations": prioritized,
                "total_steps": len(prioritized),
                "estimated_impact": "medium",  # Placeholder for impact estimation
            }

        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            raise ProfilingError(f"Failed to generate recommendations: {e}")

    # Internal helper methods

    def _to_dataframe(self, data: Union[Dict, List, pd.DataFrame]) -> pd.DataFrame:
        """Convert data to DataFrame"""
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            return pd.DataFrame([data])
        else:
            raise ProfilingError(f"Unsupported data type: {type(data)}")

    def _generate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate dataset-level summary"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns

        return {
            "rows": len(df),
            "columns": len(df.columns),
            "numeric_columns": len(numeric_cols),
            "categorical_columns": len(categorical_cols),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "missing_cells": df.isnull().sum().sum(),
            "missing_percentage": ((df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100) if len(df) > 0 else 0),
            "duplicate_rows": df.duplicated().sum(),
            "duplicate_percentage": ((df.duplicated().sum() / len(df) * 100) if len(df) > 0 else 0),
        }

    def _profile_columns(self, df: pd.DataFrame, level: ProfileLevel) -> Dict[str, Dict[str, Any]]:
        """Generate column-level profiles"""
        profiles = {}

        for col in df.columns:
            profile = {
                "name": col,
                "dtype": str(df[col].dtype),
                "missing_count": df[col].isnull().sum(),
                "missing_percentage": ((df[col].isnull().sum() / len(df) * 100) if len(df) > 0 else 0),
                "unique_count": df[col].nunique(),
                "unique_percentage": ((df[col].nunique() / len(df) * 100) if len(df) > 0 else 0),
            }

            # Add type-specific statistics
            if df[col].dtype in ["int64", "float64"]:
                profile.update(self._profile_numeric_column(df[col], level))
            else:
                profile.update(self._profile_categorical_column(df[col], level))

            profiles[col] = profile

        return profiles

    def _profile_numeric_column(self, series: pd.Series, level: ProfileLevel) -> Dict[str, Any]:
        """Profile numeric column"""
        profile = {
            "type": "numeric",
            "min": float(series.min()) if not series.empty else None,
            "max": float(series.max()) if not series.empty else None,
            "mean": float(series.mean()) if not series.empty else None,
            "median": float(series.median()) if not series.empty else None,
            "std": float(series.std()) if not series.empty else None,
        }

        if level in [ProfileLevel.COMPREHENSIVE, ProfileLevel.DEEP]:
            profile.update(
                {
                    "q25": (float(series.quantile(0.25)) if not series.empty else None),
                    "q75": (float(series.quantile(0.75)) if not series.empty else None),
                    "skewness": (float(series.skew()) if not series.empty else None),
                    "kurtosis": (float(series.kurt()) if not series.empty else None),
                }
            )

            # Detect outliers
            if not series.empty and series.std() > 0:
                z_scores = np.abs((series - series.mean()) / series.std())
                outlier_count = (z_scores > self.config.outlier_std_threshold).sum()
                profile["outlier_count"] = int(outlier_count)
                profile["outlier_percentage"] = float(outlier_count / len(series) * 100)

        return profile

    def _profile_categorical_column(self, series: pd.Series, level: ProfileLevel) -> Dict[str, Any]:
        """Profile categorical column"""
        value_counts = series.value_counts()

        profile = {
            "type": "categorical",
            "unique_values": int(series.nunique()),
            "most_common": (str(value_counts.index[0]) if not value_counts.empty else None),
            "most_common_count": (int(value_counts.iloc[0]) if not value_counts.empty else None),
        }

        if level in [ProfileLevel.COMPREHENSIVE, ProfileLevel.DEEP]:
            # Add top categories
            top_n = min(10, len(value_counts))
            profile["top_categories"] = {str(k): int(v) for k, v in value_counts.head(top_n).items()}

        return profile

    def _detect_quality_issues(self, df: pd.DataFrame, checks: Optional[List[DataQualityCheck]]) -> Dict[str, List[Dict[str, Any]]]:
        """Detect data quality issues"""
        issues: Dict[str, List[Dict[str, Any]]] = {
            "missing_values": [],
            "duplicates": [],
            "outliers": [],
            "inconsistencies": [],
            "data_types": [],
            "distributions": [],
            "correlations": [],
        }

        # All checks by default
        if checks is None:
            checks = list(DataQualityCheck)

        # Missing values check
        if DataQualityCheck.MISSING_VALUES in checks:
            for col in df.columns:
                missing_pct = (df[col].isnull().sum() / len(df) * 100) if len(df) > 0 else 0
                if missing_pct > 0:
                    issues["missing_values"].append(
                        {
                            "column": col,
                            "missing_percentage": missing_pct,
                            "severity": ("high" if missing_pct > self.config.missing_threshold * 100 else "medium"),
                        }
                    )

        # Duplicates check
        if DataQualityCheck.DUPLICATES in checks:
            dup_count = df.duplicated().sum()
            if dup_count > 0:
                issues["duplicates"].append(
                    {
                        "type": "row_duplicates",
                        "count": int(dup_count),
                        "percentage": (float(dup_count / len(df) * 100) if len(df) > 0 else 0),
                        "severity": "medium",
                    }
                )

        # Outliers check
        if DataQualityCheck.OUTLIERS in checks:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if df[col].std() > 0:
                    z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                    outlier_count = (z_scores > self.config.outlier_std_threshold).sum()
                    if outlier_count > 0:
                        issues["outliers"].append(
                            {
                                "column": col,
                                "count": int(outlier_count),
                                "percentage": float(outlier_count / len(df) * 100),
                                "severity": "low",
                            }
                        )

        return issues

    def _analyze_correlations(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze correlations between numeric columns"""
        numeric_df = df.select_dtypes(include=[np.number])

        if numeric_df.shape[1] < 2:
            return {"message": "Insufficient numeric columns for correlation analysis"}

        corr_matrix = numeric_df.corr()

        # Find high correlations
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > self.config.correlation_threshold:
                    high_corr_pairs.append(
                        {
                            "column1": corr_matrix.columns[i],
                            "column2": corr_matrix.columns[j],
                            "correlation": float(corr_value),
                        }
                    )

        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "high_correlations": high_corr_pairs,
            "num_high_correlations": len(high_corr_pairs),
        }

    def _generate_recommendations(
        self,
        df: pd.DataFrame,
        quality_issues: Dict[str, List],
        level: ProfileLevel,
    ) -> List[Dict[str, Any]]:
        """Generate preprocessing recommendations"""
        recommendations = []

        # Missing value recommendations
        for issue in quality_issues.get("missing_values", []):
            if issue["missing_percentage"] < 5:
                recommendations.append(
                    {
                        "action": "drop_missing_rows",
                        "column": issue["column"],
                        "reason": f"Low missing percentage ({issue['missing_percentage']:.2f}%)",
                        "priority": "medium",
                    }
                )
            elif issue["missing_percentage"] < 50:
                recommendations.append(
                    {
                        "action": "impute_missing",
                        "column": issue["column"],
                        "method": ("mean" if df[issue["column"]].dtype in ["int64", "float64"] else "mode"),
                        "reason": f"Moderate missing percentage ({issue['missing_percentage']:.2f}%)",
                        "priority": "high",
                    }
                )
            else:
                recommendations.append(
                    {
                        "action": "consider_dropping_column",
                        "column": issue["column"],
                        "reason": f"High missing percentage ({issue['missing_percentage']:.2f}%)",
                        "priority": "high",
                    }
                )

        # Duplicate recommendations
        if quality_issues.get("duplicates"):
            recommendations.append(
                {
                    "action": "remove_duplicates",
                    "reason": f"{quality_issues['duplicates'][0]['count']} duplicate rows found",
                    "priority": "high",
                }
            )

        # Outlier recommendations
        if quality_issues.get("outliers"):
            for issue in quality_issues["outliers"]:
                if issue["percentage"] > 5:
                    recommendations.append(
                        {
                            "action": "handle_outliers",
                            "column": issue["column"],
                            "method": "winsorize or cap",
                            "reason": f"Significant outliers detected ({issue['percentage']:.2f}%)",
                            "priority": "medium",
                        }
                    )

        return recommendations

    def _generate_task_recommendations(self, df: pd.DataFrame, target_column: str) -> List[Dict[str, Any]]:
        """Generate task-specific recommendations"""
        recommendations = []

        # Check if target is numeric or categorical
        if df[target_column].dtype in ["int64", "float64"]:
            task_type = "regression"
        else:
            task_type = "classification"

        recommendations.append(
            {
                "action": "task_identified",
                "task_type": task_type,
                "target_column": target_column,
                "reason": f"Based on target column type: {df[target_column].dtype}",
                "priority": "info",
            }
        )

        return recommendations

    def _prioritize_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize recommendations by importance"""
        priority_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
        return sorted(
            recommendations,
            key=lambda x: priority_order.get(x.get("priority", "low"), 2),
        )

    def _categorize_severity(self, issues: Dict[str, List]) -> Dict[str, int]:
        """Categorize issues by severity"""
        severity_counts = {"high": 0, "medium": 0, "low": 0}

        for issue_list in issues.values():
            for issue in issue_list:
                severity = issue.get("severity", "low")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return severity_counts

    def _generate_visualization_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate data for visualizations"""
        viz_data = {}

        # Numeric distributions
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            viz_data["numeric_distributions"] = {
                col: {
                    # Sample for performance
                    "values": df[col].dropna().tolist()[:1000],
                    "bins": 30,
                }
                for col in numeric_cols[:5]  # Limit to first 5
            }

        # Categorical distributions
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns
        if len(categorical_cols) > 0:
            viz_data["categorical_distributions"] = {col: df[col].value_counts().head(10).to_dict() for col in categorical_cols[:5]}  # Limit to first 5

        return viz_data
