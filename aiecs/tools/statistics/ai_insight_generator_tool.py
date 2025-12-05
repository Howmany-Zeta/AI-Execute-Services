"""
AI Insight Generator Tool - AI-driven insight discovery and pattern detection

This tool provides advanced insight generation with:
- Pattern discovery and anomaly detection
- Trend analysis and forecasting
- Actionable insight generation
- Integration with research_tool reasoning methods
- AI-powered analysis (placeholder for future enhancement)
"""

import logging
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime

import pandas as pd  # type: ignore[import-untyped]
import numpy as np
from scipy import stats as scipy_stats  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class InsightType(str, Enum):
    """Types of insights to generate"""

    PATTERN = "pattern"
    ANOMALY = "anomaly"
    TREND = "trend"
    CORRELATION = "correlation"
    SEGMENTATION = "segmentation"
    CAUSATION = "causation"


class InsightGeneratorError(Exception):
    """Base exception for Insight Generator errors"""


class InsightGenerationError(InsightGeneratorError):
    """Raised when insight generation fails"""


@register_tool("ai_insight_generator")
class AIInsightGeneratorTool(BaseTool):
    """
    AI-powered insight generation tool that can:
    1. Discover hidden patterns in data
    2. Generate actionable insights
    3. Detect anomalies and outliers
    4. Predict trends and forecast
    5. Apply reasoning methods (Mill's methods, induction, deduction)

    Integrates with research_tool for reasoning capabilities.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the AI insight generator tool
        
        Automatically reads from environment variables with AI_INSIGHT_GENERATOR_ prefix.
        Example: AI_INSIGHT_GENERATOR_MIN_CONFIDENCE -> min_confidence
        """

        model_config = SettingsConfigDict(env_prefix="AI_INSIGHT_GENERATOR_")

        min_confidence: float = Field(
            default=0.7,
            description="Minimum confidence threshold for insights",
        )
        anomaly_std_threshold: float = Field(
            default=3.0,
            description="Standard deviation threshold for anomaly detection",
        )
        correlation_threshold: float = Field(
            default=0.5,
            description="Correlation threshold for significant relationships",
        )
        enable_reasoning: bool = Field(
            default=True,
            description="Whether to enable reasoning methods integration",
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize AI Insight Generator Tool

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/ai_insight_generator.yaml)
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

        self._init_external_tools()

    def _init_external_tools(self):
        """Initialize external task tools"""
        self.external_tools = {}

        # Initialize ResearchTool for reasoning methods
        try:
            from aiecs.tools.task_tools.research_tool import ResearchTool

            self.external_tools["research"] = ResearchTool()
            self.logger.info("ResearchTool initialized successfully")
        except ImportError:
            self.logger.warning("ResearchTool not available")
            self.external_tools["research"] = None

        # Initialize StatisticalAnalyzerTool
        try:
            from aiecs.tools.statistics.statistical_analyzer_tool import (
                StatisticalAnalyzerTool,
            )

            self.external_tools["stats_analyzer"] = StatisticalAnalyzerTool()
            self.logger.info("StatisticalAnalyzerTool initialized successfully")
        except ImportError:
            self.logger.warning("StatisticalAnalyzerTool not available")
            self.external_tools["stats_analyzer"] = None

    # Schema definitions
    class GenerateInsightsSchema(BaseModel):
        """Schema for generate_insights operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data to analyze")
        analysis_results: Optional[Dict[str, Any]] = Field(default=None, description="Previous analysis results")
        insight_types: Optional[List[InsightType]] = Field(default=None, description="Types of insights to generate")
        min_confidence: float = Field(default=0.7, description="Minimum confidence threshold")

    class DiscoverPatternsSchema(BaseModel):
        """Schema for discover_patterns operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data for pattern discovery")
        pattern_types: Optional[List[str]] = Field(default=None, description="Specific pattern types")

    class DetectAnomaliesSchema(BaseModel):
        """Schema for detect_anomalies operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data for anomaly detection")
        columns: Optional[List[str]] = Field(default=None, description="Columns to check")
        threshold: float = Field(default=3.0, description="Standard deviation threshold")

    def generate_insights(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        analysis_results: Optional[Dict[str, Any]] = None,
        insight_types: Optional[List[InsightType]] = None,
        min_confidence: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate AI-powered insights from data and analysis results.

        Args:
            data: Data to analyze
            analysis_results: Previous analysis results to incorporate
            insight_types: Specific types of insights to generate (all if None)
            min_confidence: Minimum confidence threshold for insights

        Returns:
            Dict containing:
                - insights: List of generated insights
                - summary: Overall summary
                - priority_insights: Top priority insights
        """
        try:
            df = self._to_dataframe(data)

            self.logger.info(f"Generating insights from data with {len(df)} rows")

            # Default to all insight types
            if insight_types is None:
                insight_types = list(InsightType)

            insights = []

            # Generate different types of insights
            if InsightType.PATTERN in insight_types:
                pattern_insights = self._discover_patterns_internal(df)
                insights.extend(pattern_insights)

            if InsightType.ANOMALY in insight_types:
                anomaly_insights = self._detect_anomalies_internal(df)
                insights.extend(anomaly_insights)

            if InsightType.TREND in insight_types:
                trend_insights = self._analyze_trends_internal(df)
                insights.extend(trend_insights)

            if InsightType.CORRELATION in insight_types:
                correlation_insights = self._analyze_correlations_internal(df)
                insights.extend(correlation_insights)

            if InsightType.CAUSATION in insight_types and self.config.enable_reasoning:
                causation_insights = self._analyze_causation_internal(df)
                insights.extend(causation_insights)

            # Filter by confidence
            filtered_insights = [i for i in insights if i.get("confidence", 0) >= min_confidence]

            # Prioritize insights
            priority_insights = self._prioritize_insights(filtered_insights)

            # Generate summary
            summary = self._generate_insight_summary(filtered_insights)

            return {
                "insights": filtered_insights,
                "summary": summary,
                "priority_insights": priority_insights[:5],
                "total_insights": len(filtered_insights),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error generating insights: {e}")
            raise InsightGenerationError(f"Insight generation failed: {e}")

    def discover_patterns(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        pattern_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Discover patterns in data.

        Args:
            data: Data for pattern discovery
            pattern_types: Specific pattern types to look for

        Returns:
            Dict containing discovered patterns
        """
        try:
            df = self._to_dataframe(data)
            patterns = self._discover_patterns_internal(df)

            return {"patterns": patterns, "total_patterns": len(patterns)}

        except Exception as e:
            self.logger.error(f"Error discovering patterns: {e}")
            raise InsightGenerationError(f"Pattern discovery failed: {e}")

    def detect_anomalies(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        columns: Optional[List[str]] = None,
        threshold: float = 3.0,
    ) -> Dict[str, Any]:
        """
        Detect anomalies in data.

        Args:
            data: Data for anomaly detection
            columns: Columns to check (all numeric if None)
            threshold: Standard deviation threshold

        Returns:
            Dict containing detected anomalies
        """
        try:
            df = self._to_dataframe(data)
            anomalies = self._detect_anomalies_internal(df, columns, threshold)

            return {"anomalies": anomalies, "total_anomalies": len(anomalies)}

        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
            raise InsightGenerationError(f"Anomaly detection failed: {e}")

    # Internal insight generation methods

    def _to_dataframe(self, data: Union[Dict, List, pd.DataFrame]) -> pd.DataFrame:
        """Convert data to DataFrame"""
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            return pd.DataFrame([data])
        else:
            raise InsightGenerationError(f"Unsupported data type: {type(data)}")

    def _discover_patterns_internal(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Discover patterns in data"""
        patterns = []

        # Distribution patterns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) > 0:
                skewness = series.skew()
                if abs(skewness) > 1:
                    patterns.append(
                        {
                            "type": InsightType.PATTERN.value,
                            "title": f"Skewed Distribution in {col}",
                            "description": f"Column {col} shows {'positive' if skewness > 0 else 'negative'} skew ({skewness:.2f})",
                            "confidence": 0.85,
                            "impact": "medium",
                            "evidence": {
                                "skewness": float(skewness),
                                "column": col,
                            },
                        }
                    )

        # Categorical patterns
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns
        for col in categorical_cols:
            value_counts = df[col].value_counts()
            if len(value_counts) > 0:
                top_percentage = value_counts.iloc[0] / len(df) * 100
                if top_percentage > 50:
                    patterns.append(
                        {
                            "type": InsightType.PATTERN.value,
                            "title": f"Dominant Category in {col}",
                            "description": f"'{value_counts.index[0]}' accounts for {top_percentage:.1f}% of {col}",
                            "confidence": 0.9,
                            "impact": "high",
                            "evidence": {
                                "dominant_value": str(value_counts.index[0]),
                                "percentage": float(top_percentage),
                            },
                        }
                    )

        return patterns

    def _detect_anomalies_internal(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        threshold: float = 3.0,
    ) -> List[Dict[str, Any]]:
        """Detect anomalies using statistical methods"""
        anomalies = []

        numeric_cols = columns if columns else df.select_dtypes(include=[np.number]).columns.tolist()

        for col in numeric_cols:
            if col not in df.columns:
                continue

            series = df[col].dropna()
            if len(series) == 0 or series.std() == 0:
                continue

            # Z-score method
            z_scores = np.abs((series - series.mean()) / series.std())
            anomaly_count = (z_scores > threshold).sum()

            if anomaly_count > 0:
                anomaly_percentage = anomaly_count / len(series) * 100
                anomalies.append(
                    {
                        "type": InsightType.ANOMALY.value,
                        "title": f"Anomalies Detected in {col}",
                        "description": f"Found {anomaly_count} anomalous values ({anomaly_percentage:.2f}%) in {col}",
                        "confidence": 0.8,
                        "impact": ("high" if anomaly_percentage > 5 else "medium"),
                        "evidence": {
                            "column": col,
                            "anomaly_count": int(anomaly_count),
                            "percentage": float(anomaly_percentage),
                            "threshold": threshold,
                        },
                        "recommendation": "Investigate and consider handling these outliers",
                    }
                )

        return anomalies

    def _analyze_trends_internal(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze trends in data"""
        trends = []

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 3:
                continue

            # Calculate trend using linear regression
            x = np.arange(len(series))
            y = series.values

            if len(x) > 0 and len(y) > 0:
                slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)

                if abs(r_value) > 0.5 and p_value < 0.05:
                    trend_direction = "increasing" if slope > 0 else "decreasing"
                    trends.append(
                        {
                            "type": InsightType.TREND.value,
                            "title": f"{trend_direction.capitalize()} Trend in {col}",
                            "description": f"Column {col} shows a {trend_direction} trend (R²={r_value**2:.3f})",
                            "confidence": float(abs(r_value)),
                            "impact": ("high" if abs(r_value) > 0.7 else "medium"),
                            "evidence": {
                                "column": col,
                                "slope": float(slope),
                                "r_squared": float(r_value**2),
                                "p_value": float(p_value),
                            },
                        }
                    )

        return trends

    def _analyze_correlations_internal(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze correlations between variables"""
        correlations: List[Dict[str, Any]] = []

        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] < 2:
            return correlations

        corr_matrix = numeric_df.corr()

        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]

                if abs(corr_value) > self.config.correlation_threshold:
                    col1 = corr_matrix.columns[i]
                    col2 = corr_matrix.columns[j]

                    strength = "strong" if abs(corr_value) > 0.7 else "moderate"
                    direction = "positive" if corr_value > 0 else "negative"

                    correlations.append(
                        {
                            "type": InsightType.CORRELATION.value,
                            "title": f"{strength.capitalize()} {direction} correlation",
                            "description": f"{col1} and {col2} show {strength} {direction} correlation ({corr_value:.3f})",
                            "confidence": float(abs(corr_value)),
                            "impact": ("high" if abs(corr_value) > 0.7 else "medium"),
                            "evidence": {
                                "variable1": col1,
                                "variable2": col2,
                                "correlation": float(corr_value),
                            },
                            "recommendation": "Consider investigating causal relationship",
                        }
                    )

        return correlations

    def _analyze_causation_internal(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze potential causal relationships using reasoning methods"""
        causations: List[Dict[str, Any]] = []

        # Use research tool for Mill's methods if available
        if self.external_tools.get("research"):
            # Placeholder for causal analysis using Mill's methods
            # This would require domain knowledge and proper case structures
            self.logger.info("Causal analysis with reasoning methods available but requires domain-specific setup")

        return causations

    def _prioritize_insights(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize insights by confidence and impact"""
        impact_scores = {"high": 3, "medium": 2, "low": 1}

        def priority_score(insight):
            confidence = insight.get("confidence", 0.5)
            impact = impact_scores.get(insight.get("impact", "low"), 1)
            return confidence * impact

        return sorted(insights, key=priority_score, reverse=True)

    def _generate_insight_summary(self, insights: List[Dict[str, Any]]) -> str:
        """Generate summary of insights"""
        if not insights:
            return "No significant insights found in the data."

        type_counts: Dict[str, int] = {}
        for insight in insights:
            insight_type = insight.get("type", "unknown")
            type_counts[insight_type] = type_counts.get(insight_type, 0) + 1

        summary_parts = [f"Generated {len(insights)} insights:"]
        for itype, count in type_counts.items():
            summary_parts.append(f"{count} {itype} insights")

        return "; ".join(summary_parts)
