"""
Statistical Analyzer Tool - Advanced statistical analysis and hypothesis testing

This tool provides comprehensive statistical analysis with:
- Descriptive and inferential statistics
- Hypothesis testing (t-test, ANOVA, chi-square)
- Regression analysis
- Time series analysis
- Correlation and causality analysis
"""

import logging
from typing import Dict, Any, List, Optional, Union
from enum import Enum

import pandas as pd  # type: ignore[import-untyped]
import numpy as np
from scipy import stats as scipy_stats  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class AnalysisType(str, Enum):
    """Types of statistical analyses"""

    DESCRIPTIVE = "descriptive"
    T_TEST = "t_test"
    ANOVA = "anova"
    CHI_SQUARE = "chi_square"
    LINEAR_REGRESSION = "linear_regression"
    LOGISTIC_REGRESSION = "logistic_regression"
    CORRELATION = "correlation"
    TIME_SERIES = "time_series"


class StatisticalAnalyzerError(Exception):
    """Base exception for StatisticalAnalyzer errors"""


class AnalysisError(StatisticalAnalyzerError):
    """Raised when analysis fails"""


@register_tool("statistical_analyzer")
class StatisticalAnalyzerTool(BaseTool):
    """
    Advanced statistical analysis tool that can:
    1. Perform hypothesis testing
    2. Conduct regression analysis
    3. Analyze time series
    4. Perform correlation and causal analysis

    Integrates with stats_tool for core statistical operations.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the statistical analyzer tool
        
        Automatically reads from environment variables with STATISTICAL_ANALYZER_ prefix.
        Example: STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL -> significance_level
        """

        model_config = SettingsConfigDict(env_prefix="STATISTICAL_ANALYZER_")

        significance_level: float = Field(
            default=0.05,
            description="Significance level for hypothesis testing",
        )
        confidence_level: float = Field(
            default=0.95,
            description="Confidence level for statistical intervals",
        )
        enable_effect_size: bool = Field(
            default=True,
            description="Whether to calculate effect sizes in analyses",
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize StatisticalAnalyzerTool with settings

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/statistical_analyzer.yaml)
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

        try:
            from aiecs.tools.task_tools.stats_tool import StatsTool

            self.external_tools["stats"] = StatsTool()
            self.logger.info("StatsTool initialized successfully")
        except ImportError:
            self.logger.warning("StatsTool not available")
            self.external_tools["stats"] = None

    # Schema definitions
    class AnalyzeSchema(BaseModel):
        """Schema for analyze operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data to analyze")
        analysis_type: AnalysisType = Field(description="Type of analysis to perform")
        variables: Dict[str, Any] = Field(description="Variables specification")
        params: Optional[Dict[str, Any]] = Field(default=None, description="Additional parameters")

    class TestHypothesisSchema(BaseModel):
        """Schema for test_hypothesis operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data for hypothesis testing")
        test_type: str = Field(description="Type of test: t_test, anova, chi_square")
        variables: Dict[str, Any] = Field(description="Variables for testing")

    class PerformRegressionSchema(BaseModel):
        """Schema for perform_regression operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data for regression")
        dependent_var: str = Field(description="Dependent variable")
        independent_vars: List[str] = Field(description="Independent variables")
        regression_type: str = Field(default="linear", description="Type: linear or logistic")

    class AnalyzeCorrelationSchema(BaseModel):
        """Schema for analyze_correlation operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data for correlation analysis")
        variables: Optional[List[str]] = Field(default=None, description="Variables to analyze")
        method: str = Field(default="pearson", description="Correlation method")

    def analyze(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        analysis_type: AnalysisType,
        variables: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform statistical analysis.

        Args:
            data: Data to analyze
            analysis_type: Type of analysis
            variables: Variables specification (dependent, independent, etc.)
            params: Additional parameters

        Returns:
            Dict containing analysis results with statistics, p-values, interpretations
        """
        try:
            df = self._to_dataframe(data)
            params = params or {}

            if analysis_type == AnalysisType.DESCRIPTIVE:
                result = self._descriptive_analysis(df, variables)
            elif analysis_type == AnalysisType.T_TEST:
                result = self._t_test_analysis(df, variables, params)
            elif analysis_type == AnalysisType.ANOVA:
                result = self._anova_analysis(df, variables, params)
            elif analysis_type == AnalysisType.CHI_SQUARE:
                result = self._chi_square_analysis(df, variables, params)
            elif analysis_type == AnalysisType.LINEAR_REGRESSION:
                result = self._linear_regression_analysis(df, variables, params)
            elif analysis_type == AnalysisType.CORRELATION:
                result = self._correlation_analysis(df, variables, params)
            else:
                raise AnalysisError(f"Unsupported analysis type: {analysis_type}")

            result["analysis_type"] = analysis_type.value
            return result

        except Exception as e:
            self.logger.error(f"Error in analysis: {e}")
            raise AnalysisError(f"Analysis failed: {e}")

    def test_hypothesis(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        test_type: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform hypothesis testing"""
        try:
            df = self._to_dataframe(data)

            if test_type == "t_test":
                return self._t_test_analysis(df, variables, {})
            elif test_type == "anova":
                return self._anova_analysis(df, variables, {})
            elif test_type == "chi_square":
                return self._chi_square_analysis(df, variables, {})
            else:
                raise AnalysisError(f"Unsupported test type: {test_type}")

        except Exception as e:
            self.logger.error(f"Error in hypothesis testing: {e}")
            raise AnalysisError(f"Hypothesis testing failed: {e}")

    def perform_regression(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        dependent_var: str,
        independent_vars: List[str],
        regression_type: str = "linear",
    ) -> Dict[str, Any]:
        """Perform regression analysis"""
        try:
            df = self._to_dataframe(data)
            variables = {
                "dependent": dependent_var,
                "independent": independent_vars,
            }

            if regression_type == "linear":
                return self._linear_regression_analysis(df, variables, {})
            else:
                raise AnalysisError(f"Unsupported regression type: {regression_type}")

        except Exception as e:
            self.logger.error(f"Error in regression: {e}")
            raise AnalysisError(f"Regression failed: {e}")

    def analyze_correlation(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        variables: Optional[List[str]] = None,
        method: str = "pearson",
    ) -> Dict[str, Any]:
        """Perform correlation analysis"""
        try:
            df = self._to_dataframe(data)
            var_dict = {"variables": variables} if variables else {}
            return self._correlation_analysis(df, var_dict, {"method": method})

        except Exception as e:
            self.logger.error(f"Error in correlation analysis: {e}")
            raise AnalysisError(f"Correlation analysis failed: {e}")

    # Internal analysis methods

    def _to_dataframe(self, data: Union[Dict, List, pd.DataFrame]) -> pd.DataFrame:
        """Convert data to DataFrame"""
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            return pd.DataFrame([data])
        else:
            raise AnalysisError(f"Unsupported data type: {type(data)}")

    def _descriptive_analysis(self, df: pd.DataFrame, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Perform descriptive statistics analysis"""
        cols = variables.get("columns", df.select_dtypes(include=[np.number]).columns.tolist())

        results = {}
        for col in cols:
            if col in df.columns:
                series = df[col].dropna()
                results[col] = {
                    "count": int(len(series)),
                    "mean": float(series.mean()),
                    "std": float(series.std()),
                    "min": float(series.min()),
                    "q25": float(series.quantile(0.25)),
                    "median": float(series.median()),
                    "q75": float(series.quantile(0.75)),
                    "max": float(series.max()),
                    "skewness": float(series.skew()),
                    "kurtosis": float(series.kurt()),
                }

        return {
            "results": results,
            "interpretation": "Descriptive statistics computed successfully",
        }

    def _t_test_analysis(
        self,
        df: pd.DataFrame,
        variables: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform t-test"""
        var1_name = variables.get("var1")
        var2_name = variables.get("var2")

        if not var1_name or not var2_name:
            raise AnalysisError("T-test requires var1 and var2")

        var1 = df[var1_name].dropna()
        var2 = df[var2_name].dropna()

        statistic, pvalue = scipy_stats.ttest_ind(var1, var2)

        return {
            "test_type": "t_test",
            "statistic": float(statistic),
            "p_value": float(pvalue),
            "significant": pvalue < self.config.significance_level,
            "interpretation": f"{'Significant' if pvalue < self.config.significance_level else 'Not significant'} difference at α={self.config.significance_level}",
            "variables": [var1_name, var2_name],
        }

    def _anova_analysis(
        self,
        df: pd.DataFrame,
        variables: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform ANOVA"""
        groups = variables.get("groups", [])

        if len(groups) < 2:
            raise AnalysisError("ANOVA requires at least 2 groups")

        group_data = [df[group].dropna() for group in groups if group in df.columns]

        if len(group_data) < 2:
            raise AnalysisError("Insufficient valid groups for ANOVA")

        statistic, pvalue = scipy_stats.f_oneway(*group_data)

        return {
            "test_type": "anova",
            "statistic": float(statistic),
            "p_value": float(pvalue),
            "significant": pvalue < self.config.significance_level,
            "interpretation": f"{'Significant' if pvalue < self.config.significance_level else 'Not significant'} difference between groups",
            "groups": groups,
        }

    def _chi_square_analysis(
        self,
        df: pd.DataFrame,
        variables: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform chi-square test"""
        var1_name = variables.get("var1")
        var2_name = variables.get("var2")

        if not var1_name or not var2_name:
            raise AnalysisError("Chi-square test requires var1 and var2")

        contingency_table = pd.crosstab(df[var1_name], df[var2_name])
        statistic, pvalue, dof, expected = scipy_stats.chi2_contingency(contingency_table)

        return {
            "test_type": "chi_square",
            "statistic": float(statistic),
            "p_value": float(pvalue),
            "degrees_of_freedom": int(dof),
            "significant": pvalue < self.config.significance_level,
            "interpretation": f"{'Significant' if pvalue < self.config.significance_level else 'Not significant'} association",
            "variables": [var1_name, var2_name],
        }

    def _linear_regression_analysis(
        self,
        df: pd.DataFrame,
        variables: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform linear regression"""
        from sklearn.linear_model import LinearRegression  # type: ignore[import-untyped]
        from sklearn.metrics import r2_score, mean_squared_error  # type: ignore[import-untyped]

        dependent = variables.get("dependent")
        independent = variables.get("independent", [])

        if not dependent or not independent:
            raise AnalysisError("Regression requires dependent and independent variables")

        X = df[independent].dropna()
        y = df[dependent].loc[X.index]

        model = LinearRegression()
        model.fit(X, y)

        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)
        mse = mean_squared_error(y, y_pred)

        coefficients = {var: float(coef) for var, coef in zip(independent, model.coef_)}

        return {
            "model_type": "linear_regression",
            "intercept": float(model.intercept_),
            "coefficients": coefficients,
            "r_squared": float(r2),
            "mse": float(mse),
            "rmse": float(np.sqrt(mse)),
            "interpretation": f"Model explains {r2*100:.2f}% of variance",
            "dependent_variable": dependent,
            "independent_variables": independent,
        }

    def _correlation_analysis(
        self,
        df: pd.DataFrame,
        variables: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform correlation analysis"""
        method = params.get("method", "pearson")
        cols = variables.get("variables")

        if cols:
            numeric_df = df[cols].select_dtypes(include=[np.number])
        else:
            numeric_df = df.select_dtypes(include=[np.number])

        if numeric_df.shape[1] < 2:
            raise AnalysisError("Correlation requires at least 2 numeric variables")

        corr_matrix = numeric_df.corr(method=method)

        # Find significant correlations
        significant_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > 0.3:  # Threshold for noteworthy correlation
                    significant_pairs.append(
                        {
                            "var1": corr_matrix.columns[i],
                            "var2": corr_matrix.columns[j],
                            "correlation": float(corr_value),
                            "strength": self._interpret_correlation(corr_value),
                        }
                    )

        return {
            "method": method,
            "correlation_matrix": corr_matrix.to_dict(),
            "significant_correlations": significant_pairs,
            "interpretation": f"Found {len(significant_pairs)} significant correlations",
        }

    def _interpret_correlation(self, corr: float) -> str:
        """Interpret correlation strength"""
        abs_corr = abs(corr)
        if abs_corr < 0.3:
            return "weak"
        elif abs_corr < 0.7:
            return "moderate"
        else:
            return "strong"
