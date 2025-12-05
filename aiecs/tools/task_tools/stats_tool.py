import os
import logging
import tempfile
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass

import pandas as pd  # type: ignore[import-untyped]
import numpy as np
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool

# Enums for configuration options


class ScalerType(str, Enum):
    STANDARD = "standard"
    MINMAX = "minmax"
    ROBUST = "robust"
    NONE = "none"


# Exceptions
class StatsToolError(Exception):
    pass


class FileOperationError(StatsToolError):
    pass


class AnalysisError(StatsToolError):
    pass


# Utility Dataclass for Statistical Results


@dataclass
class StatsResult:
    """Structured statistical result."""

    test_type: str
    statistic: float
    pvalue: float
    significant: bool
    additional_metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_type": self.test_type,
            "statistic": self.statistic,
            "pvalue": self.pvalue,
            "significant": self.significant,
            **self.additional_metrics,
        }


@register_tool("stats")
class StatsTool(BaseTool):
    """Enhanced statistical analysis tool for various data formats and operations."""

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the stats tool
        
        Automatically reads from environment variables with STATS_TOOL_ prefix.
        Example: STATS_TOOL_MAX_FILE_SIZE_MB -> max_file_size_mb
        """

        model_config = SettingsConfigDict(env_prefix="STATS_TOOL_")

        max_file_size_mb: int = Field(default=200, description="Maximum file size in megabytes")
        allowed_extensions: List[str] = Field(
            default=[
                ".sav",
                ".sas7bdat",
                ".por",
                ".csv",
                ".xlsx",
                ".xls",
                ".json",
                ".parquet",
                ".feather",
            ],
            description="Allowed file extensions",
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize StatsTool with settings and resources.

        Args:
            config (Dict, optional): Configuration overrides for StatsTool.
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/stats.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(h)
        self.logger.setLevel(logging.INFO)

    def _load_data(
        self,
        file_path: str,
        nrows: Optional[int] = None,
        sheet_name: Optional[Union[str, int]] = 0,
    ) -> pd.DataFrame:
        """Load data from various file formats into a pandas DataFrame."""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in [".sav", ".sas7bdat", ".por"]:
                import pyreadstat  # type: ignore[import-untyped]

                if ext == ".sav":
                    df, meta = pyreadstat.read_sav(file_path)
                elif ext == ".sas7bdat":
                    df, meta = pyreadstat.read_sas7bdat(file_path)
                else:
                    df, meta = pyreadstat.read_por(file_path)
                return df
            elif ext == ".csv":
                return pd.read_csv(file_path, nrows=nrows)
            elif ext in [".xlsx", ".xls"]:
                return pd.read_excel(file_path, sheet_name=sheet_name, nrows=nrows)
            elif ext == ".json":
                return pd.read_json(file_path)
            elif ext == ".parquet":
                return pd.read_parquet(file_path)
            elif ext == ".feather":
                return pd.read_feather(file_path)
            else:
                raise FileOperationError(f"Unsupported file format: {ext}")
        except Exception as e:
            raise FileOperationError(f"Error reading file {file_path}: {str(e)}")

    def _validate_variables(self, df: pd.DataFrame, vars_to_check: List[str]) -> None:
        """Validate variables exist in the dataset."""
        if not vars_to_check:
            return
        available_vars = df.columns.tolist()
        missing_vars = [var for var in vars_to_check if var not in available_vars]
        if missing_vars:
            raise FileOperationError(f"Variables not found in dataset: {', '.join(missing_vars)}")

    def _interpret_effect_size(self, d: float) -> str:
        """Interpret Cohen's d or Cramer's V effect size."""
        thresholds = [(0.2, "negligible"), (0.5, "small"), (0.8, "medium")]
        for threshold, label in thresholds:
            if abs(d) < threshold:
                return label
        return "large"

    def read_data(
        self,
        file_path: str,
        nrows: Optional[int] = None,
        sheet_name: Optional[Union[str, int]] = 0,
    ) -> Dict[str, Any]:
        """Read data from various file formats."""
        df = self._load_data(file_path, nrows, sheet_name)
        return {
            "variables": df.columns.tolist(),
            "observations": len(df),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "memory_usage": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "preview": df.head(5).to_dict(orient="records"),
        }

    def describe(
        self,
        file_path: str,
        variables: Optional[List[str]] = None,
        include_percentiles: bool = False,
        percentiles: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Generate descriptive statistics for variables."""
        df = self._load_data(file_path)
        if variables:
            self._validate_variables(df, variables)
            df = df[variables]
        desc = df.describe()
        if include_percentiles and percentiles:
            additional_percentiles = [p for p in percentiles if p not in [0.25, 0.5, 0.75]]
            if additional_percentiles:
                additional_desc = df.describe(percentiles=percentiles)
                desc = pd.concat(
                    [
                        desc,
                        additional_desc.loc[[f"{int(p*100)}%" for p in additional_percentiles]],
                    ]
                )
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if numeric_cols.any():
            desc.loc["skew"] = df[numeric_cols].skew()
            desc.loc["kurtosis"] = df[numeric_cols].kurt()
        return {"statistics": desc.to_dict(), "summary": desc.to_string()}

    def ttest(
        self,
        file_path: str,
        var1: str,
        var2: str,
        equal_var: bool = True,
        paired: bool = False,
    ) -> Dict[str, Any]:
        """Perform t-tests (independent or paired). Also handles legacy ttest_ind."""
        df = self._load_data(file_path)
        self._validate_variables(df, [var1, var2])
        import scipy.stats as stats  # type: ignore[import-untyped]

        a = df[var1].dropna().values
        b = df[var2].dropna().values
        if paired:
            min_len = min(len(a), len(b))
            stat, p = stats.ttest_rel(a[:min_len], b[:min_len])
            test_type = "paired t-test"
        else:
            stat, p = stats.ttest_ind(a, b, equal_var=equal_var)
            test_type = "independent t-test (equal variance)" if equal_var else "Welch's t-test (unequal variance)"
        mean_a = np.mean(a)
        mean_b = np.mean(b)
        std_a = np.std(a, ddof=1)
        std_b = np.std(b, ddof=1)
        if equal_var:
            pooled_std = np.sqrt(((len(a) - 1) * std_a**2 + (len(b) - 1) * std_b**2) / (len(a) + len(b) - 2))
            cohens_d = (mean_a - mean_b) / pooled_std
        else:
            cohens_d = (mean_a - mean_b) / np.sqrt((std_a**2 + std_b**2) / 2)
        return StatsResult(
            test_type=test_type,
            statistic=float(stat),
            pvalue=float(p),
            significant=p < 0.05,
            additional_metrics={
                "cohens_d": float(cohens_d),
                "effect_size_interpretation": self._interpret_effect_size(cohens_d),
                "group1_mean": float(mean_a),
                "group2_mean": float(mean_b),
                "group1_std": float(std_a),
                "group2_std": float(std_b),
                "group1_n": int(len(a)),
                "group2_n": int(len(b)),
            },
        ).to_dict()

    # Legacy method (now an alias)
    ttest_ind = ttest

    def correlation(
        self,
        file_path: str,
        variables: Optional[List[str]] = None,
        var1: Optional[str] = None,
        var2: Optional[str] = None,
        method: str = "pearson",
    ) -> Dict[str, Any]:
        """Perform correlation analysis."""
        df = self._load_data(file_path)
        if variables:
            self._validate_variables(df, variables)
        if var1 and var2:
            self._validate_variables(df, [var1, var2])
        import scipy.stats as stats  # type: ignore[import-untyped]

        result = {}
        if variables:
            corr_matrix = df[variables].corr(method=method)
            result["correlation_matrix"] = corr_matrix.to_dict()
            flat_corrs = [
                {
                    "var1": v1,
                    "var2": v2,
                    "correlation": corr_matrix.loc[v1, v2],
                    "abs_correlation": abs(corr_matrix.loc[v1, v2]),
                }
                for i, v1 in enumerate(variables)
                for j, v2 in enumerate(variables)
                if i < j
            ]
            flat_corrs.sort(key=lambda x: x["abs_correlation"], reverse=True)
            result["pairs"] = flat_corrs
        elif var1 and var2:
            x = df[var1].dropna()
            y = df[var2].dropna()
            method_map = {
                "pearson": (stats.pearsonr, "Pearson's r"),
                "spearman": (stats.spearmanr, "Spearman's rho"),
                "kendall": (stats.kendalltau, "Kendall's tau"),
            }
            func, method_name = method_map[method]
            corr, p = func(x, y)
            result = {
                "method": method_name,
                "correlation": float(corr),
                "pvalue": float(p),
                "significant": p < 0.05,
                "n": len(x),
            }
        return result

    def anova(
        self,
        file_path: str,
        dependent: str,
        factor: str,
        post_hoc: bool = False,
    ) -> Dict[str, Any]:
        """Perform one-way ANOVA with optional post-hoc tests."""
        df = self._load_data(file_path)
        self._validate_variables(df, [dependent, factor])
        import scipy.stats as stats  # type: ignore[import-untyped]  # type: ignore[import-untyped]
        from statsmodels.stats.multicomp import pairwise_tukeyhsd  # type: ignore[import-untyped]

        dependent_var = df[dependent].dropna()
        factor_var = df[factor].dropna()
        min_len = min(len(dependent_var), len(factor_var))
        dependent_var = dependent_var[:min_len]
        factor_var = factor_var[:min_len]
        groups = {name: group[dependent].dropna().values for name, group in df.groupby(factor)}
        stat, p = stats.f_oneway(*groups.values())
        result = {
            "F": float(stat),
            "pvalue": float(p),
            "significant": p < 0.05,
            "groups": len(groups),
            "group_sizes": {name: len(values) for name, values in groups.items()},
            "group_means": {name: float(np.mean(values)) for name, values in groups.items()},
            "group_std": {name: float(np.std(values, ddof=1)) for name, values in groups.items()},
        }
        if post_hoc:
            post_hoc_df = pd.DataFrame({"value": dependent_var, "group": factor_var})
            tukey = pairwise_tukeyhsd(post_hoc_df["value"], post_hoc_df["group"])
            from itertools import combinations

            group_pairs = list(combinations(tukey.groupsunique, 2))
            tukey_results = [
                {
                    "group1": str(group1),
                    "group2": str(group2),
                    "mean_difference": float(mean_diff),
                    "p_adjusted": float(p_adj),
                    "significant": bool(reject),
                    "conf_lower": float(lower),
                    "conf_upper": float(upper),
                }
                for (
                    group1,
                    group2,
                ), mean_diff, p_adj, lower, upper, reject in zip(
                    group_pairs,
                    tukey.meandiffs,
                    tukey.pvalues,
                    tukey.confint[:, 0],
                    tukey.confint[:, 1],
                    tukey.reject,
                )
            ]
            result["post_hoc"] = {
                "method": "Tukey HSD",
                "alpha": 0.05,  # Standard significance level for Tukey HSD
                "comparisons": tukey_results,
            }
        return result

    def chi_square(self, file_path: str, var1: str, var2: str, correction: bool = True) -> Dict[str, Any]:
        """Perform chi-square test of independence."""
        df = self._load_data(file_path)
        self._validate_variables(df, [var1, var2])
        import scipy.stats as stats  # type: ignore[import-untyped]

        contingency = pd.crosstab(df[var1], df[var2])
        chi2, p, dof, expected = stats.chi2_contingency(contingency, correction=correction)
        n = contingency.sum().sum()
        min_dim = min(contingency.shape) - 1
        cramers_v = np.sqrt(chi2 / (n * min_dim))
        return {
            "chi2": float(chi2),
            "pvalue": float(p),
            "dof": int(dof),
            "significant": p < 0.05,
            "cramers_v": float(cramers_v),
            "effect_size_interpretation": self._interpret_effect_size(cramers_v),
            "contingency_table": contingency.to_dict(),
            "expected_frequencies": pd.DataFrame(expected, index=contingency.index, columns=contingency.columns).to_dict(),
            "test_type": ("Chi-square test with Yates correction" if correction else "Chi-square test"),
        }

    def non_parametric(
        self,
        file_path: str,
        test_type: str,
        variables: List[str],
        grouping: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform non-parametric statistical tests."""
        df = self._load_data(file_path)
        self._validate_variables(df, variables + ([grouping] if grouping else []))
        import scipy.stats as stats  # type: ignore[import-untyped]

        if test_type == "mann_whitney":
            if len(variables) != 2:
                raise AnalysisError("Mann-Whitney U test requires exactly 2 variables")
            x = df[variables[0]].dropna().values
            y = df[variables[1]].dropna().values
            u_stat, p_value = stats.mannwhitneyu(x, y)
            return StatsResult(
                test_type="Mann-Whitney U test",
                statistic=float(u_stat),
                pvalue=float(p_value),
                significant=p_value < 0.05,
                additional_metrics={
                    "n1": len(x),
                    "n2": len(y),
                    "median1": float(np.median(x)),
                    "median2": float(np.median(y)),
                },
            ).to_dict()
        elif test_type == "wilcoxon":
            if len(variables) != 2:
                raise AnalysisError("Wilcoxon signed-rank test requires exactly 2 variables")
            x = df[variables[0]].dropna().values
            y = df[variables[1]].dropna().values
            min_len = min(len(x), len(y))
            x = x[:min_len]
            y = y[:min_len]
            w_stat, p_value = stats.wilcoxon(x, y)
            return StatsResult(
                test_type="Wilcoxon signed-rank test",
                statistic=float(w_stat),
                pvalue=float(p_value),
                significant=p_value < 0.05,
                additional_metrics={
                    "n_pairs": min_len,
                    "median_difference": float(np.median(x - y)),
                },
            ).to_dict()
        elif test_type == "kruskal":
            if not grouping:
                raise AnalysisError("Kruskal-Wallis test requires a grouping variable")
            groups = {f"{var}_{name}": group[var].dropna().values for name, group in df.groupby(grouping) for var in variables}
            h_stat, p_value = stats.kruskal(*groups.values())
            return StatsResult(
                test_type="Kruskal-Wallis H test",
                statistic=float(h_stat),
                pvalue=float(p_value),
                significant=p_value < 0.05,
                additional_metrics={
                    "groups": len(groups),
                    "group_sizes": {name: len(values) for name, values in groups.items()},
                    "group_medians": {name: float(np.median(values)) for name, values in groups.items()},
                },
            ).to_dict()
        elif test_type == "friedman":
            if len(variables) < 2:
                raise AnalysisError("Friedman test requires at least 2 variables")
            data = df[variables].dropna()
            chi2, p_value = stats.friedmanchisquare(*[data[var].values for var in variables])
            return StatsResult(
                test_type="Friedman test",
                statistic=float(chi2),
                pvalue=float(p_value),
                significant=p_value < 0.05,
                additional_metrics={
                    "n_measures": len(variables),
                    "n_samples": len(data),
                    "variable_medians": {var: float(np.median(data[var])) for var in variables},
                },
            ).to_dict()
        else:
            raise AnalysisError(f"Unsupported non-parametric test type: {test_type}. Supported types: mann_whitney, wilcoxon, kruskal, friedman")

    def regression(
        self,
        file_path: str,
        formula: str,
        regression_type: str = "ols",
        robust: bool = False,
        structured_output: bool = True,
    ) -> Dict[str, Any]:
        """Perform regression analysis with various models."""
        df = self._load_data(file_path)
        import statsmodels.formula.api as smf  # type: ignore[import-untyped]

        try:
            model_map = {
                "ols": smf.ols,
                "logit": smf.logit,
                "probit": smf.probit,
                "poisson": smf.poisson,
            }
            model = model_map[regression_type](formula=formula, data=df)
            fit = model.fit(cov_type="HC3" if robust else "nonrobust")
            if structured_output:
                result = {
                    "model_type": regression_type,
                    "formula": formula,
                    "n_observations": int(fit.nobs),
                    "r_squared": (float(fit.rsquared) if hasattr(fit, "rsquared") else None),
                    "adj_r_squared": (float(fit.rsquared_adj) if hasattr(fit, "rsquared_adj") else None),
                    "aic": float(fit.aic) if hasattr(fit, "aic") else None,
                    "bic": float(fit.bic) if hasattr(fit, "bic") else None,
                    "f_statistic": (float(fit.fvalue) if hasattr(fit, "fvalue") else None),
                    "f_pvalue": (float(fit.f_pvalue) if hasattr(fit, "f_pvalue") else None),
                    "log_likelihood": (float(fit.llf) if hasattr(fit, "llf") else None),
                    "coefficients": {
                        var: {
                            "coef": float(fit.params[var]),
                            "std_err": float(fit.bse[var]),
                            "t_value": (float(fit.tvalues[var]) if hasattr(fit, "tvalues") else None),
                            "p_value": float(fit.pvalues[var]),
                            "significant": fit.pvalues[var] < 0.05,
                            "conf_lower": float(fit.conf_int().loc[var, 0]),
                            "conf_upper": float(fit.conf_int().loc[var, 1]),
                        }
                        for var in fit.params.index
                    },
                }
                return {
                    "summary_text": fit.summary().as_text(),
                    "structured": result,
                }
            return {"summary": fit.summary().as_text()}
        except Exception as e:
            raise AnalysisError(f"Regression error: {str(e)}")

    def time_series(
        self,
        file_path: str,
        variable: str,
        date_variable: Optional[str] = None,
        model_type: str = "arima",
        order: Optional[Tuple[int, int, int]] = (1, 1, 1),
        seasonal_order: Optional[Tuple[int, int, int, int]] = None,
        forecast_periods: int = 10,
    ) -> Dict[str, Any]:
        """Perform time series analysis."""
        df = self._load_data(file_path)
        self._validate_variables(df, [variable] + ([date_variable] if date_variable else []))
        from statsmodels.tsa.arima.model import ARIMA  # type: ignore[import-untyped]
        from statsmodels.tsa.statespace.sarimax import SARIMAX  # type: ignore[import-untyped]

        try:
            ts_data = df[variable].dropna()
            if date_variable and date_variable in df.columns:
                ts_data.index = df[date_variable]
            if model_type == "arima":
                model = ARIMA(ts_data, order=order)
                fit = model.fit()
                model_type_name = "ARIMA"
            elif model_type == "sarima":
                if not seasonal_order:
                    raise AnalysisError("seasonal_order must be provided for SARIMA model")
                model = SARIMAX(ts_data, order=order, seasonal_order=seasonal_order)
                fit = model.fit(disp=False)
                model_type_name = "SARIMA"
            else:
                raise AnalysisError(f"Unsupported time series model: {model_type}")
            forecast = fit.forecast(steps=forecast_periods)
            forecast_index = pd.date_range(
                start=(ts_data.index[-1] if isinstance(ts_data.index, pd.DatetimeIndex) else len(ts_data)),
                periods=forecast_periods + 1,
                freq="D",
            )[1:]
            return {
                "model_type": model_type_name,
                "order": order,
                "seasonal_order": (seasonal_order if model_type == "sarima" else None),
                "aic": float(fit.aic),
                "bic": float(fit.bic),
                "forecast": {
                    "values": (forecast.tolist() if isinstance(forecast, np.ndarray) else forecast.values.tolist()),
                    "index": (forecast_index.strftime("%Y-%m-%d").tolist() if isinstance(forecast_index, pd.DatetimeIndex) else list(range(len(forecast)))),
                },
                "summary": str(fit.summary()),
            }
        except Exception as e:
            raise AnalysisError(f"Time series analysis error: {str(e)}")

    def preprocess(
        self,
        file_path: str,
        variables: List[str],
        operation: str,
        scaler_type: ScalerType = ScalerType.STANDARD,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Preprocess data with various operations."""
        df = self._load_data(file_path)
        self._validate_variables(df, variables)
        data = df[variables].copy()
        result: Dict[str, Any] = {"operation": operation}
        if operation == "scale":
            from sklearn.preprocessing import (  # type: ignore[import-untyped]
                StandardScaler,
                MinMaxScaler,
                RobustScaler,
            )

            scaler_map = {
                ScalerType.STANDARD: (StandardScaler, "StandardScaler"),
                ScalerType.MINMAX: (MinMaxScaler, "MinMaxScaler"),
                ScalerType.ROBUST: (RobustScaler, "RobustScaler"),
            }
            scaler_cls, scaler_name = scaler_map[scaler_type]
            scaler = scaler_cls()
            scaled_data = scaler.fit_transform(data)
            scaled_df = pd.DataFrame(
                scaled_data,
                columns=[f"{col}_scaled" for col in data.columns],
                index=data.index,
            )
            result.update(
                {
                    "scaler": scaler_name,
                    "original_stats": data.describe().to_dict(),
                    "scaled_stats": scaled_df.describe().to_dict(),
                    "preview": scaled_df.head(5).to_dict(orient="records"),
                }
            )
            processed_df = scaled_df
        elif operation == "impute":
            import numpy as np

            imputed_df = data.copy()
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                imputed_df[col] = data[col].fillna(data[col].mean())
            cat_cols = data.select_dtypes(exclude=[np.number]).columns
            for col in cat_cols:
                imputed_df[col] = data[col].fillna(data[col].mode()[0] if not data[col].mode().empty else None)
            result.update(
                {
                    "imputation_method": {
                        "numeric": "mean",
                        "categorical": "mode",
                    },
                    "missing_counts_before": data.isna().sum().to_dict(),
                    "missing_counts_after": imputed_df.isna().sum().to_dict(),
                    "preview": imputed_df.head(5).to_dict(orient="records"),
                }
            )
            processed_df = imputed_df
        if output_path:
            output_path = os.path.abspath(output_path) if os.path.isabs(output_path) else os.path.join(tempfile.gettempdir(), "stats_outputs", output_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            processed_df.to_csv(output_path)
            result["output_file"] = output_path
        return result
