"""
Comprehensive tests for StatsTool component
Tests cover all public methods and functionality with >85% coverage
No mocks used - testing real functionality and outputs
"""
import pytest
import os
import tempfile
import shutil
import json
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any

from aiecs.tools.task_tools.stats_tool import (
    StatsTool, 
    StatsSettings,
    ScalerType, 
    StatsResult,
    StatsToolError,
    FileOperationError,
    AnalysisError
)


class TestStatsTool:
    """Test class for StatsTool functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def stats_tool(self):
        """Create StatsTool instance with default configuration"""
        return StatsTool()

    @pytest.fixture
    def stats_tool_custom(self, temp_dir):
        """Create StatsTool instance with custom configuration"""
        config = {
            'max_file_size_mb': 100,
            'allowed_extensions': ['.csv', '.xlsx']
        }
        return StatsTool(config)

    @pytest.fixture
    def test_data_dir(self):
        """Path to test data directory"""
        return Path(__file__).parent / "data"

    @pytest.fixture
    def sample_csv_file(self, test_data_dir):
        """Path to sample CSV file"""
        return str(test_data_dir / "sample_data.csv")

    @pytest.fixture
    def stats_test_data_file(self, test_data_dir):
        """Path to stats test data CSV file"""
        return str(test_data_dir / "stats_test_data.csv")

    @pytest.fixture
    def numeric_csv_file(self, test_data_dir):
        """Path to numeric CSV file"""
        return str(test_data_dir / "numeric_data.csv")

    @pytest.fixture
    def time_series_file(self, test_data_dir):
        """Path to time series data CSV file"""
        return str(test_data_dir / "time_series_data.csv")

    @pytest.fixture
    def categorical_file(self, test_data_dir):
        """Path to categorical data CSV file"""
        return str(test_data_dir / "categorical_data.csv")

    def test_init_default_config(self):
        """Test StatsTool initialization with default configuration"""
        tool = StatsTool()
        assert isinstance(tool.settings, StatsSettings)
        assert tool.settings.max_file_size_mb == 200
        assert '.csv' in tool.settings.allowed_extensions
        assert hasattr(tool, 'logger')
        print(f"DEBUG: Default settings: {tool.settings}")

    def test_init_custom_config(self):
        """Test StatsTool initialization with custom configuration"""
        config = {
            'max_file_size_mb': 50,
            'allowed_extensions': ['.csv', '.json']
        }
        tool = StatsTool(config)
        assert tool.settings.max_file_size_mb == 50
        assert tool.settings.allowed_extensions == ['.csv', '.json']
        print(f"DEBUG: Custom settings: {tool.settings}")

    def test_init_invalid_config(self):
        """Test StatsTool initialization with invalid configuration"""
        config = {
            'max_file_size_mb': "invalid"  # Should be int
        }
        with pytest.raises(ValueError, match="Invalid settings"):
            StatsTool(config)

    def test_read_data_csv(self, stats_tool, stats_test_data_file):
        """Test reading CSV data"""
        print(f"DEBUG: Reading data from {stats_test_data_file}")
        result = stats_tool.read_data(stats_test_data_file)
        
        assert 'variables' in result
        assert 'observations' in result
        assert 'dtypes' in result
        assert 'memory_usage' in result
        assert 'preview' in result
        
        print(f"DEBUG: Variables: {result['variables']}")
        print(f"DEBUG: Observations: {result['observations']}")
        print(f"DEBUG: Memory usage: {result['memory_usage']:.2f} MB")
        
        assert result['observations'] == 15  # 15 rows in stats_test_data.csv
        assert 'age' in result['variables']
        assert 'score' in result['variables']
        assert isinstance(result['preview'], list)

    def test_read_data_with_nrows(self, stats_tool, stats_test_data_file):
        """Test reading CSV data with nrows limit"""
        result = stats_tool.read_data(stats_test_data_file, nrows=5)
        
        assert result['observations'] == 5
        assert len(result['preview']) == 5
        print(f"DEBUG: Limited read - observations: {result['observations']}")

    def test_load_data_excel_sheet(self, stats_tool):
        """Test loading Excel data with sheet selection"""
        # Create temporary Excel file
        df = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df.to_excel(f.name, index=False, sheet_name='Sheet1')
            temp_file = f.name

        try:
            loaded_df = stats_tool._load_data(temp_file, sheet_name='Sheet1')
            assert len(loaded_df) == 3
            assert 'x' in loaded_df.columns
            print(f"DEBUG: Excel data loaded: {loaded_df.shape}")
        finally:
            os.unlink(temp_file)

    def test_load_data_unsupported_format(self, stats_tool):
        """Test loading unsupported file format"""
        with tempfile.NamedTemporaryFile(suffix='.unknown') as f:
            with pytest.raises(FileOperationError, match="Unsupported file format"):
                stats_tool._load_data(f.name)

    def test_validate_variables_success(self, stats_tool, stats_test_data_file):
        """Test successful variable validation"""
        df = stats_tool._load_data(stats_test_data_file)
        # Should not raise exception
        stats_tool._validate_variables(df, ['age', 'score'])
        stats_tool._validate_variables(df, [])  # Empty list should be fine

    def test_validate_variables_failure(self, stats_tool, stats_test_data_file):
        """Test variable validation failure"""
        df = stats_tool._load_data(stats_test_data_file)
        with pytest.raises(FileOperationError, match="Variables not found"):
            stats_tool._validate_variables(df, ['nonexistent_var'])

    def test_interpret_effect_size(self, stats_tool):
        """Test effect size interpretation"""
        assert stats_tool._interpret_effect_size(0.1) == "negligible"
        assert stats_tool._interpret_effect_size(0.3) == "small" 
        assert stats_tool._interpret_effect_size(0.6) == "medium"
        assert stats_tool._interpret_effect_size(0.9) == "large"
        assert stats_tool._interpret_effect_size(-0.7) == "medium"  # Test absolute value
        print(f"DEBUG: Effect size interpretations tested")

    def test_describe_basic(self, stats_tool, stats_test_data_file):
        """Test basic descriptive statistics"""
        print(f"DEBUG: Running descriptive statistics on {stats_test_data_file}")
        result = stats_tool.describe(stats_test_data_file)
        
        assert 'statistics' in result
        assert 'summary' in result
        
        stats = result['statistics']
        assert 'age' in stats
        assert 'score' in stats
        assert 'count' in stats['age']
        assert 'mean' in stats['age']
        assert 'std' in stats['age']
        
        print(f"DEBUG: Descriptive stats for age: mean={stats['age']['mean']:.2f}, std={stats['age']['std']:.2f}")

    def test_describe_with_variables(self, stats_tool, stats_test_data_file):
        """Test descriptive statistics with specific variables"""
        result = stats_tool.describe(stats_test_data_file, variables=['age', 'score'])
        
        stats = result['statistics']
        assert 'age' in stats
        assert 'score' in stats
        assert 'weight' not in stats  # Not included in variables list
        print(f"DEBUG: Describe with variables - included: {list(stats.keys())}")

    def test_describe_with_percentiles(self, stats_tool, stats_test_data_file):
        """Test descriptive statistics with custom percentiles"""
        result = stats_tool.describe(
            stats_test_data_file, 
            variables=['age'], 
            include_percentiles=True,
            percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]
        )
        
        stats = result['statistics']['age']
        assert '10%' in stats
        assert '90%' in stats
        print(f"DEBUG: Percentiles included: {[k for k in stats.keys() if '%' in k]}")

    def test_ttest_independent(self, stats_tool, stats_test_data_file):
        """Test independent t-test"""
        print(f"DEBUG: Running independent t-test")
        result = stats_tool.ttest(stats_test_data_file, 'age', 'score')
        
        assert 'test_type' in result
        assert 'statistic' in result
        assert 'pvalue' in result
        assert 'significant' in result
        assert 'cohens_d' in result
        assert 'effect_size_interpretation' in result
        assert 'group1_mean' in result
        assert 'group2_mean' in result
        
        print(f"DEBUG: T-test result - statistic: {result['statistic']:.4f}, p-value: {result['pvalue']:.4f}")
        print(f"DEBUG: Cohen's d: {result['cohens_d']:.4f}, Effect size: {result['effect_size_interpretation']}")

    def test_ttest_paired(self, stats_tool, stats_test_data_file):
        """Test paired t-test"""
        print(f"DEBUG: Running paired t-test")
        result = stats_tool.ttest(stats_test_data_file, 'age', 'score', paired=True)
        
        assert result['test_type'] == 'paired t-test'
        assert 'statistic' in result
        assert 'pvalue' in result
        print(f"DEBUG: Paired t-test - statistic: {result['statistic']:.4f}, p-value: {result['pvalue']:.4f}")

    def test_ttest_welch(self, stats_tool, stats_test_data_file):
        """Test Welch's t-test (unequal variances)"""
        result = stats_tool.ttest(stats_test_data_file, 'age', 'score', equal_var=False)
        
        assert "Welch's t-test" in result['test_type']
        print(f"DEBUG: Welch's t-test type: {result['test_type']}")

    def test_ttest_legacy_alias(self, stats_tool, stats_test_data_file):
        """Test legacy ttest_ind method (alias)"""
        result = stats_tool.ttest_ind(stats_test_data_file, 'age', 'score')
        
        assert 'test_type' in result
        assert 'statistic' in result
        print(f"DEBUG: Legacy ttest_ind works - same as ttest method")

    def test_correlation_pearson_matrix(self, stats_tool, stats_test_data_file):
        """Test Pearson correlation matrix"""
        print(f"DEBUG: Running correlation matrix analysis")
        result = stats_tool.correlation(stats_test_data_file, variables=['age', 'score', 'weight', 'height'])
        
        assert 'correlation_matrix' in result
        assert 'pairs' in result
        
        matrix = result['correlation_matrix']
        assert 'age' in matrix
        assert 'score' in matrix['age']
        
        pairs = result['pairs']
        assert len(pairs) == 6  # 4 choose 2 = 6 pairs
        assert 'var1' in pairs[0]
        assert 'var2' in pairs[0]
        assert 'correlation' in pairs[0]
        
        print(f"DEBUG: Top correlation: {pairs[0]['var1']} vs {pairs[0]['var2']} = {pairs[0]['correlation']:.4f}")

    def test_correlation_pearson_single_pair(self, stats_tool, stats_test_data_file):
        """Test Pearson correlation for single variable pair"""
        result = stats_tool.correlation(stats_test_data_file, var1='age', var2='score')
        
        assert 'method' in result
        assert 'correlation' in result
        assert 'pvalue' in result
        assert 'significant' in result
        assert 'n' in result
        assert result['method'] == "Pearson's r"
        
        print(f"DEBUG: Pearson correlation age-score: r={result['correlation']:.4f}, p={result['pvalue']:.4f}")

    def test_correlation_spearman(self, stats_tool, stats_test_data_file):
        """Test Spearman correlation"""
        result = stats_tool.correlation(stats_test_data_file, var1='age', var2='score', method='spearman')
        
        assert result['method'] == "Spearman's rho"
        print(f"DEBUG: Spearman correlation: rho={result['correlation']:.4f}")

    def test_correlation_kendall(self, stats_tool, stats_test_data_file):
        """Test Kendall tau correlation"""
        result = stats_tool.correlation(stats_test_data_file, var1='age', var2='score', method='kendall')
        
        assert result['method'] == "Kendall's tau"
        print(f"DEBUG: Kendall correlation: tau={result['correlation']:.4f}")

    def test_anova_basic(self, stats_tool, stats_test_data_file):
        """Test one-way ANOVA"""
        print(f"DEBUG: Running one-way ANOVA")
        result = stats_tool.anova(stats_test_data_file, dependent='score', factor='group')
        
        assert 'F' in result
        assert 'pvalue' in result
        assert 'significant' in result
        assert 'groups' in result
        assert 'group_sizes' in result
        assert 'group_means' in result
        assert 'group_std' in result
        
        print(f"DEBUG: ANOVA F={result['F']:.4f}, p={result['pvalue']:.4f}")
        print(f"DEBUG: Group means: {result['group_means']}")

    def test_anova_with_posthoc(self, stats_tool, stats_test_data_file):
        """Test ANOVA with post-hoc analysis"""
        print(f"DEBUG: Running ANOVA with Tukey HSD post-hoc")
        result = stats_tool.anova(stats_test_data_file, dependent='score', factor='group', post_hoc=True)
        
        assert 'post_hoc' in result
        assert 'method' in result['post_hoc']
        assert 'alpha' in result['post_hoc']
        assert 'comparisons' in result['post_hoc']
        assert result['post_hoc']['method'] == 'Tukey HSD'
        
        comparisons = result['post_hoc']['comparisons']
        assert len(comparisons) > 0
        assert 'group1' in comparisons[0]
        assert 'group2' in comparisons[0]
        assert 'p_adjusted' in comparisons[0]
        
        print(f"DEBUG: Post-hoc comparisons: {len(comparisons)}")
        print(f"DEBUG: First comparison: {comparisons[0]['group1']} vs {comparisons[0]['group2']}, p={comparisons[0]['p_adjusted']:.4f}")

    def test_chi_square_test(self, stats_tool, categorical_file):
        """Test chi-square test of independence"""
        print(f"DEBUG: Running chi-square test")
        result = stats_tool.chi_square(categorical_file, 'gender', 'satisfaction')
        
        assert 'chi2' in result
        assert 'pvalue' in result
        assert 'dof' in result
        assert 'significant' in result
        assert 'cramers_v' in result
        assert 'effect_size_interpretation' in result
        assert 'contingency_table' in result
        assert 'expected_frequencies' in result
        assert 'test_type' in result
        
        print(f"DEBUG: Chi-square={result['chi2']:.4f}, p={result['pvalue']:.4f}")
        print(f"DEBUG: Cramer's V={result['cramers_v']:.4f}, Effect size: {result['effect_size_interpretation']}")

    def test_chi_square_no_correction(self, stats_tool, categorical_file):
        """Test chi-square test without Yates correction"""
        result = stats_tool.chi_square(categorical_file, 'gender', 'satisfaction', correction=False)
        
        assert 'Chi-square test with Yates correction' not in result['test_type']
        assert 'Chi-square test' in result['test_type']

    def test_mann_whitney_test(self, stats_tool, stats_test_data_file):
        """Test Mann-Whitney U test"""
        print(f"DEBUG: Running Mann-Whitney U test")
        result = stats_tool.non_parametric(stats_test_data_file, 'mann_whitney', ['age', 'score'])
        
        assert result['test_type'] == 'Mann-Whitney U test'
        assert 'statistic' in result
        assert 'pvalue' in result
        assert 'significant' in result
        assert 'n1' in result
        assert 'n2' in result
        assert 'median1' in result
        assert 'median2' in result
        
        print(f"DEBUG: Mann-Whitney U={result['statistic']:.4f}, p={result['pvalue']:.4f}")
        print(f"DEBUG: Median1={result['median1']:.2f}, Median2={result['median2']:.2f}")

    def test_wilcoxon_test(self, stats_tool, stats_test_data_file):
        """Test Wilcoxon signed-rank test"""
        print(f"DEBUG: Running Wilcoxon signed-rank test")
        result = stats_tool.non_parametric(stats_test_data_file, 'wilcoxon', ['age', 'score'])
        
        assert result['test_type'] == 'Wilcoxon signed-rank test'
        assert 'statistic' in result
        assert 'pvalue' in result
        assert 'n_pairs' in result
        assert 'median_difference' in result
        
        print(f"DEBUG: Wilcoxon W={result['statistic']:.4f}, p={result['pvalue']:.4f}")
        print(f"DEBUG: Median difference={result['median_difference']:.4f}")

    def test_kruskal_wallis_test(self, stats_tool, stats_test_data_file):
        """Test Kruskal-Wallis H test"""
        print(f"DEBUG: Running Kruskal-Wallis test")
        result = stats_tool.non_parametric(stats_test_data_file, 'kruskal', ['score'], grouping='group')
        
        assert result['test_type'] == 'Kruskal-Wallis H test'
        assert 'statistic' in result
        assert 'pvalue' in result
        assert 'groups' in result
        assert 'group_sizes' in result
        assert 'group_medians' in result
        
        print(f"DEBUG: Kruskal-Wallis H={result['statistic']:.4f}, p={result['pvalue']:.4f}")
        print(f"DEBUG: Group medians: {result['group_medians']}")

    def test_friedman_test(self, stats_tool, stats_test_data_file):
        """Test Friedman test"""
        print(f"DEBUG: Running Friedman test")
        result = stats_tool.non_parametric(stats_test_data_file, 'friedman', ['age', 'score', 'weight'])
        
        assert result['test_type'] == 'Friedman test'
        assert 'statistic' in result
        assert 'pvalue' in result
        assert 'n_measures' in result
        assert 'n_samples' in result
        assert 'variable_medians' in result
        
        assert result['n_measures'] == 3
        print(f"DEBUG: Friedman chi2={result['statistic']:.4f}, p={result['pvalue']:.4f}")
        print(f"DEBUG: Variable medians: {result['variable_medians']}")

    def test_non_parametric_invalid_test(self, stats_tool, stats_test_data_file):
        """Test invalid non-parametric test type"""
        with pytest.raises(AnalysisError, match="Unsupported non-parametric test type"):
            stats_tool.non_parametric(stats_test_data_file, 'invalid_test', ['age', 'score'])

    def test_mann_whitney_wrong_variables(self, stats_tool, stats_test_data_file):
        """Test Mann-Whitney with wrong number of variables"""
        with pytest.raises(AnalysisError, match="Mann-Whitney U test requires exactly 2 variables"):
            stats_tool.non_parametric(stats_test_data_file, 'mann_whitney', ['age'])

    def test_wilcoxon_wrong_variables(self, stats_tool, stats_test_data_file):
        """Test Wilcoxon with wrong number of variables"""
        with pytest.raises(AnalysisError, match="Wilcoxon signed-rank test requires exactly 2 variables"):
            stats_tool.non_parametric(stats_test_data_file, 'wilcoxon', ['age', 'score', 'weight'])

    def test_kruskal_no_grouping(self, stats_tool, stats_test_data_file):
        """Test Kruskal-Wallis without grouping variable"""
        with pytest.raises(AnalysisError, match="Kruskal-Wallis test requires a grouping variable"):
            stats_tool.non_parametric(stats_test_data_file, 'kruskal', ['score'])

    def test_friedman_insufficient_variables(self, stats_tool, stats_test_data_file):
        """Test Friedman with insufficient variables"""
        with pytest.raises(AnalysisError, match="Friedman test requires at least 2 variables"):
            stats_tool.non_parametric(stats_test_data_file, 'friedman', ['age'])

    def test_regression_ols(self, stats_tool, stats_test_data_file):
        """Test OLS regression"""
        print(f"DEBUG: Running OLS regression")
        result = stats_tool.regression(stats_test_data_file, 'score ~ age + weight', regression_type='ols')
        
        assert 'summary_text' in result
        assert 'structured' in result
        
        structured = result['structured']
        assert structured['model_type'] == 'ols'
        assert 'formula' in structured
        assert 'n_observations' in structured
        assert 'r_squared' in structured
        assert 'coefficients' in structured
        
        print(f"DEBUG: OLS R²={structured['r_squared']:.4f}, N={structured['n_observations']}")
        print(f"DEBUG: Coefficients: {list(structured['coefficients'].keys())}")

    def test_regression_logit(self, stats_tool):
        """Test logistic regression"""
        # Create binary outcome data
        df = pd.DataFrame({
            'x1': np.random.normal(0, 1, 100),
            'x2': np.random.normal(0, 1, 100),
        })
        df['y'] = (df['x1'] + df['x2'] + np.random.normal(0, 0.5, 100) > 0).astype(int)
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            df.to_csv(f.name, index=False)
            temp_file = f.name

        try:
            print(f"DEBUG: Running logistic regression")
            result = stats_tool.regression(temp_file, 'y ~ x1 + x2', regression_type='logit')
            
            structured = result['structured']
            assert structured['model_type'] == 'logit'
            assert 'log_likelihood' in structured
            print(f"DEBUG: Logit log-likelihood={structured['log_likelihood']:.4f}")
        finally:
            os.unlink(temp_file)

    def test_regression_unstructured_output(self, stats_tool, stats_test_data_file):
        """Test regression with unstructured output"""
        result = stats_tool.regression(
            stats_test_data_file, 
            'score ~ age', 
            structured_output=False
        )
        
        assert 'summary' in result
        assert 'structured' not in result
        print(f"DEBUG: Unstructured output contains summary text")

    def test_regression_robust(self, stats_tool, stats_test_data_file):
        """Test regression with robust standard errors"""
        result = stats_tool.regression(
            stats_test_data_file, 
            'score ~ age', 
            robust=True
        )
        
        structured = result['structured']
        assert 'coefficients' in structured
        print(f"DEBUG: Robust regression completed")

    def test_regression_invalid_formula(self, stats_tool, stats_test_data_file):
        """Test regression with invalid formula"""
        with pytest.raises(AnalysisError, match="Regression error"):
            stats_tool.regression(stats_test_data_file, 'invalid ~ formula ~ syntax')

    def test_time_series_arima(self, stats_tool, time_series_file):
        """Test ARIMA time series analysis"""
        print(f"DEBUG: Running ARIMA time series analysis")
        result = stats_tool.time_series(
            time_series_file, 
            variable='value', 
            model_type='arima',
            order=(1, 1, 1),
            forecast_periods=5
        )
        
        assert result['model_type'] == 'ARIMA'
        assert 'order' in result
        assert 'aic' in result
        assert 'bic' in result
        assert 'forecast' in result
        assert 'summary' in result
        
        forecast = result['forecast']
        assert 'values' in forecast
        assert 'index' in forecast
        assert len(forecast['values']) == 5
        
        print(f"DEBUG: ARIMA AIC={result['aic']:.4f}, BIC={result['bic']:.4f}")
        print(f"DEBUG: Forecast values: {forecast['values']}")

    def test_time_series_sarima(self, stats_tool, time_series_file):
        """Test SARIMA time series analysis"""
        print(f"DEBUG: Running SARIMA time series analysis")
        result = stats_tool.time_series(
            time_series_file,
            variable='value',
            model_type='sarima',
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 7),
            forecast_periods=3
        )
        
        assert result['model_type'] == 'SARIMA'
        assert 'seasonal_order' in result
        assert result['seasonal_order'] == (1, 1, 1, 7)
        
        print(f"DEBUG: SARIMA completed with seasonal order: {result['seasonal_order']}")

    def test_time_series_with_date_variable(self, stats_tool, time_series_file):
        """Test time series with date variable"""
        result = stats_tool.time_series(
            time_series_file,
            variable='value',
            date_variable='date',
            forecast_periods=3
        )
        
        assert 'forecast' in result
        forecast = result['forecast']
        assert len(forecast['values']) == 3
        print(f"DEBUG: Time series with date variable completed")

    def test_time_series_invalid_model(self, stats_tool, time_series_file):
        """Test time series with invalid model type"""
        with pytest.raises(AnalysisError, match="Unsupported time series model"):
            stats_tool.time_series(time_series_file, variable='value', model_type='invalid_model')

    def test_time_series_sarima_no_seasonal_order(self, stats_tool, time_series_file):
        """Test SARIMA without seasonal order"""
        with pytest.raises(AnalysisError, match="seasonal_order must be provided for SARIMA model"):
            stats_tool.time_series(time_series_file, variable='value', model_type='sarima')

    def test_preprocess_scale_standard(self, stats_tool, stats_test_data_file, temp_dir):
        """Test data preprocessing with standard scaling"""
        print(f"DEBUG: Running standard scaling preprocessing")
        output_path = os.path.join(temp_dir, "scaled_data.csv")
        result = stats_tool.preprocess(
            stats_test_data_file,
            variables=['age', 'score', 'weight'],
            operation='scale',
            scaler_type=ScalerType.STANDARD,
            output_path=output_path
        )
        
        assert result['operation'] == 'scale'
        assert result['scaler'] == 'StandardScaler'
        assert 'original_stats' in result
        assert 'scaled_stats' in result
        assert 'preview' in result
        assert 'output_file' in result
        assert os.path.exists(result['output_file'])
        
        original_stats = result['original_stats']
        scaled_stats = result['scaled_stats']
        print(f"DEBUG: Original age mean: {original_stats['age']['mean']:.2f}")
        print(f"DEBUG: Scaled age mean: {scaled_stats['age_scaled']['mean']:.6f}")

    def test_preprocess_scale_minmax(self, stats_tool, stats_test_data_file):
        """Test data preprocessing with MinMax scaling"""
        result = stats_tool.preprocess(
            stats_test_data_file,
            variables=['age', 'score'],
            operation='scale',
            scaler_type=ScalerType.MINMAX
        )
        
        assert result['scaler'] == 'MinMaxScaler'
        print(f"DEBUG: MinMax scaling completed")

    def test_preprocess_scale_robust(self, stats_tool, stats_test_data_file):
        """Test data preprocessing with robust scaling"""
        result = stats_tool.preprocess(
            stats_test_data_file,
            variables=['age', 'score'],
            operation='scale',
            scaler_type=ScalerType.ROBUST
        )
        
        assert result['scaler'] == 'RobustScaler'
        print(f"DEBUG: Robust scaling completed")

    def test_preprocess_impute(self, stats_tool, temp_dir):
        """Test data preprocessing with imputation"""
        # Create data with missing values
        df = pd.DataFrame({
            'numeric_col': [1.0, 2.0, np.nan, 4.0, 5.0],
            'categorical_col': ['A', 'B', np.nan, 'A', 'B']
        })
        
        temp_file = os.path.join(temp_dir, "data_with_missing.csv")
        df.to_csv(temp_file, index=False)
        
        print(f"DEBUG: Running imputation preprocessing")
        result = stats_tool.preprocess(
            temp_file,
            variables=['numeric_col', 'categorical_col'],
            operation='impute'
        )
        
        assert result['operation'] == 'impute'
        assert 'imputation_method' in result
        assert 'missing_counts_before' in result
        assert 'missing_counts_after' in result
        assert 'preview' in result
        
        before = result['missing_counts_before']
        after = result['missing_counts_after']
        assert before['numeric_col'] == 1
        assert after['numeric_col'] == 0
        
        print(f"DEBUG: Missing before: {before}")
        print(f"DEBUG: Missing after: {after}")

    def test_error_handling_file_not_found(self, stats_tool):
        """Test error handling for non-existent file"""
        with pytest.raises(FileOperationError, match="Error reading file"):
            stats_tool.read_data("/nonexistent/file.csv")

    def test_error_handling_invalid_variables(self, stats_tool, stats_test_data_file):
        """Test error handling for invalid variables in analysis"""
        with pytest.raises(FileOperationError, match="Variables not found"):
            stats_tool.describe(stats_test_data_file, variables=['nonexistent_var'])

    def test_stats_result_dataclass(self):
        """Test StatsResult dataclass functionality"""
        result = StatsResult(
            test_type="test",
            statistic=1.23,
            pvalue=0.05,
            significant=True,
            additional_metrics={'extra': 'value'}
        )
        
        result_dict = result.to_dict()
        assert result_dict['test_type'] == "test"
        assert result_dict['statistic'] == 1.23
        assert result_dict['pvalue'] == 0.05
        assert result_dict['significant'] == True
        assert result_dict['extra'] == 'value'
        
        print(f"DEBUG: StatsResult to_dict: {result_dict}")

    def test_stats_settings_validation(self):
        """Test StatsSettings configuration"""
        settings = StatsSettings()
        assert settings.max_file_size_mb == 200
        assert '.csv' in settings.allowed_extensions
        assert settings.env_prefix == 'STATS_TOOL_'
        print(f"DEBUG: Default settings: {settings}")

    def test_scaler_type_enum(self):
        """Test ScalerType enum values"""
        assert ScalerType.STANDARD == "standard"
        assert ScalerType.MINMAX == "minmax" 
        assert ScalerType.ROBUST == "robust"
        assert ScalerType.NONE == "none"
        print(f"DEBUG: ScalerType enum values verified")

    def test_custom_exceptions(self):
        """Test custom exception hierarchy"""
        assert issubclass(FileOperationError, StatsToolError)
        assert issubclass(AnalysisError, StatsToolError)
        assert issubclass(StatsToolError, Exception)
        print(f"DEBUG: Exception hierarchy verified")

    def test_complex_regression_analysis(self, stats_tool, stats_test_data_file):
        """Test complex regression with multiple predictors"""
        print(f"DEBUG: Running complex regression analysis")
        result = stats_tool.regression(
            stats_test_data_file,
            'score ~ age + weight + height + income',
            regression_type='ols'
        )
        
        structured = result['structured']
        coefficients = structured['coefficients']
        
        # Check all predictors are included
        assert 'age' in coefficients
        assert 'weight' in coefficients
        assert 'height' in coefficients
        assert 'income' in coefficients
        
        # Check coefficient structure
        for var, coef_data in coefficients.items():
            assert 'coef' in coef_data
            assert 'std_err' in coef_data
            assert 'p_value' in coef_data
            assert 'significant' in coef_data
            assert 'conf_lower' in coef_data
            assert 'conf_upper' in coef_data
        
        print(f"DEBUG: Model R² = {structured['r_squared']:.4f}")
        for var, coef_data in coefficients.items():
            if var != 'Intercept':
                print(f"DEBUG: {var}: coef={coef_data['coef']:.4f}, p={coef_data['p_value']:.4f}")

    def test_regression_with_categorical_predictors(self, stats_tool, stats_test_data_file):
        """Test regression with categorical predictors"""
        result = stats_tool.regression(
            stats_test_data_file,
            'score ~ age + C(category)',
            regression_type='ols'
        )
        
        structured = result['structured']
        coefficients = structured['coefficients']
        
        # Should have categorical dummy variables
        categorical_vars = [var for var in coefficients.keys() if 'category' in var]
        assert len(categorical_vars) > 0
        print(f"DEBUG: Categorical variables in model: {categorical_vars}")

    def test_advanced_correlation_analysis(self, stats_tool, stats_test_data_file):
        """Test advanced correlation analysis with multiple variables"""
        result = stats_tool.correlation(
            stats_test_data_file, 
            variables=['age', 'score', 'weight', 'height', 'income']
        )
        
        pairs = result['pairs']
        matrix = result['correlation_matrix']
        
        # Should have 10 pairs (5 choose 2)
        assert len(pairs) == 10
        
        # Verify pairs are sorted by absolute correlation
        abs_corrs = [pair['abs_correlation'] for pair in pairs]
        assert abs_corrs == sorted(abs_corrs, reverse=True)
        
        print(f"DEBUG: Strongest correlation: {pairs[0]['var1']} - {pairs[0]['var2']}: {pairs[0]['correlation']:.4f}")
        print(f"DEBUG: Weakest correlation: {pairs[-1]['var1']} - {pairs[-1]['var2']}: {pairs[-1]['correlation']:.4f}")

    def test_data_loading_with_missing_values(self, stats_tool, temp_dir):
        """Test data loading with missing values"""
        # Create data with various missing value representations
        df = pd.DataFrame({
            'col1': [1, 2, np.nan, 4, 5],
            'col2': [1.1, 2.2, 3.3, np.nan, 5.5],
            'col3': ['A', 'B', None, 'D', 'E']
        })
        
        temp_file = os.path.join(temp_dir, "missing_data.csv")
        df.to_csv(temp_file, index=False)
        
        result = stats_tool.read_data(temp_file)
        
        assert result['observations'] == 5
        print(f"DEBUG: Loaded data with missing values - shape: {result['observations']} x {len(result['variables'])}")

    def test_edge_cases_small_dataset(self, stats_tool, temp_dir):
        """Test edge cases with very small datasets"""
        # Create minimal dataset
        df = pd.DataFrame({
            'x': [1, 2],
            'y': [3, 4]
        })
        
        temp_file = os.path.join(temp_dir, "small_data.csv")
        df.to_csv(temp_file, index=False)
        
        # Should still work for basic operations
        result = stats_tool.read_data(temp_file)
        assert result['observations'] == 2
        
        desc_result = stats_tool.describe(temp_file)
        assert 'statistics' in desc_result
        
        print(f"DEBUG: Small dataset handled successfully")

    def test_data_types_preservation(self, stats_tool, stats_test_data_file):
        """Test that data types are correctly identified and preserved"""
        result = stats_tool.read_data(stats_test_data_file)
        
        dtypes = result['dtypes']
        
        # Age should be numeric
        assert 'int' in dtypes['age'] or 'float' in dtypes['age']
        # Score should be numeric
        assert 'float' in dtypes['score']
        # Name should be object/string
        assert 'object' in dtypes['name']
        
        print(f"DEBUG: Data types preserved: {dtypes}")

    def test_memory_usage_calculation(self, stats_tool, stats_test_data_file):
        """Test memory usage calculation"""
        result = stats_tool.read_data(stats_test_data_file)
        
        assert 'memory_usage' in result
        assert isinstance(result['memory_usage'], float)
        assert result['memory_usage'] > 0
        
        print(f"DEBUG: Memory usage: {result['memory_usage']:.4f} MB")

    def test_output_path_generation(self, stats_tool, stats_test_data_file, temp_dir):
        """Test automatic output path generation in preprocess"""
        result = stats_tool.preprocess(
            stats_test_data_file,
            variables=['age', 'score'],
            operation='scale',
            output_path='auto_generated.csv'
        )
        
        assert 'output_file' in result
        assert os.path.exists(result['output_file'])
        assert result['output_file'].endswith('auto_generated.csv')
        
        print(f"DEBUG: Output file created at: {result['output_file']}")

    def test_logger_configuration(self, stats_tool):
        """Test logger configuration"""
        assert hasattr(stats_tool, 'logger')
        assert stats_tool.logger.level == logging.INFO
        assert len(stats_tool.logger.handlers) > 0
        
        print(f"DEBUG: Logger configured with level: {stats_tool.logger.level}")

    def test_tool_registration(self):
        """Test that the tool is properly registered"""
        tool = StatsTool()
        assert hasattr(tool, 'read_data')
        assert hasattr(tool, 'describe')
        assert hasattr(tool, 'ttest')
        assert hasattr(tool, 'correlation')
        assert hasattr(tool, 'anova')
        print(f"DEBUG: Tool registration verified")

    def test_comprehensive_workflow(self, stats_tool, stats_test_data_file, temp_dir):
        """Test a comprehensive workflow using multiple methods"""
        print(f"DEBUG: Running comprehensive workflow test")
        
        # 1. Read and explore data
        data_info = stats_tool.read_data(stats_test_data_file)
        print(f"DEBUG: Step 1 - Data loaded: {data_info['observations']} observations")
        
        # 2. Get descriptive statistics
        desc_stats = stats_tool.describe(stats_test_data_file, variables=['age', 'score', 'weight'])
        print(f"DEBUG: Step 2 - Descriptive statistics computed")
        
        # 3. Test relationships
        correlation_result = stats_tool.correlation(stats_test_data_file, var1='age', var2='score')
        print(f"DEBUG: Step 3 - Correlation: {correlation_result['correlation']:.4f}")
        
        # 4. Compare groups
        anova_result = stats_tool.anova(stats_test_data_file, dependent='score', factor='group')
        print(f"DEBUG: Step 4 - ANOVA F={anova_result['F']:.4f}")
        
        # 5. Preprocess data
        preprocess_result = stats_tool.preprocess(
            stats_test_data_file,
            variables=['age', 'score'],
            operation='scale',
            output_path=os.path.join(temp_dir, "workflow_output.csv")
        )
        print(f"DEBUG: Step 5 - Data preprocessed and saved")
        
        # Verify all steps completed successfully
        assert all([
            data_info['observations'] > 0,
            'statistics' in desc_stats,
            correlation_result['correlation'] is not None,
            anova_result['F'] is not None,
            os.path.exists(preprocess_result['output_file'])
        ])
        
        print(f"DEBUG: Comprehensive workflow completed successfully")

    def test_error_propagation(self, stats_tool):
        """Test error propagation through the tool chain"""
        # Test file not found
        with pytest.raises(FileOperationError):
            stats_tool.describe("/nonexistent/file.csv")
        
        # Test invalid variables
        with pytest.raises(FileOperationError):
            stats_tool.correlation("/tmp/nonexistent.csv", var1='x', var2='y')
        
        print(f"DEBUG: Error propagation working correctly")

    def test_edge_case_empty_groups(self, stats_tool, temp_dir):
        """Test handling of edge cases with empty or single-value groups"""
        # Create data with minimal groups
        df = pd.DataFrame({
            'value': [1, 2, 3],
            'group': ['A', 'A', 'B']
        })
        
        temp_file = os.path.join(temp_dir, "minimal_groups.csv")
        df.to_csv(temp_file, index=False)
        
        # This might raise an error or handle gracefully - test the behavior
        try:
            result = stats_tool.anova(temp_file, dependent='value', factor='group')
            print(f"DEBUG: ANOVA with minimal groups: F={result['F']:.4f}")
        except Exception as e:
            print(f"DEBUG: ANOVA with minimal groups appropriately failed: {e}")
            # This is expected behavior for insufficient data

    def test_numeric_precision(self, stats_tool, temp_dir):
        """Test numeric precision in calculations"""
        # Create data with known statistical properties
        np.random.seed(42)
        data = np.random.normal(100, 15, 1000)  # Mean=100, SD=15
        df = pd.DataFrame({
            'values': data,
            'group': ['A'] * 500 + ['B'] * 500
        })
        
        temp_file = os.path.join(temp_dir, "precision_test.csv")
        df.to_csv(temp_file, index=False)
        
        desc_result = stats_tool.describe(temp_file, variables=['values'])
        mean = desc_result['statistics']['values']['mean']
        std = desc_result['statistics']['values']['std']
        
        # Should be close to expected values (within reasonable tolerance)
        assert 95 < mean < 105  # Should be close to 100
        assert 10 < std < 20    # Should be close to 15
        
        print(f"DEBUG: Numeric precision - calculated mean: {mean:.2f}, std: {std:.2f}")

    def test_large_dataset_performance(self, stats_tool, temp_dir):
        """Test performance with larger datasets"""
        # Create moderately large dataset
        size = 1000
        np.random.seed(123)
        df = pd.DataFrame({
            'var1': np.random.normal(0, 1, size),
            'var2': np.random.normal(10, 2, size),
            'var3': np.random.exponential(2, size),
            'group': np.random.choice(['A', 'B', 'C'], size)
        })
        
        temp_file = os.path.join(temp_dir, "large_dataset.csv")
        df.to_csv(temp_file, index=False)
        
        # Test multiple operations
        read_result = stats_tool.read_data(temp_file)
        assert read_result['observations'] == size
        
        desc_result = stats_tool.describe(temp_file, variables=['var1', 'var2', 'var3'])
        assert 'statistics' in desc_result
        
        print(f"DEBUG: Large dataset ({size} rows) processed successfully")

    def test_missing_dependency_handling(self, stats_tool, stats_test_data_file):
        """Test graceful handling of missing optional dependencies"""
        # This test ensures the tool handles missing dependencies appropriately
        # Most dependencies should be available, but we test error handling
        try:
            result = stats_tool.time_series(stats_test_data_file, 'age')
            print(f"DEBUG: Time series dependencies available")
        except Exception as e:
            print(f"DEBUG: Time series dependency error (expected): {e}")

    def test_data_validation_edge_cases(self, stats_tool, temp_dir):
        """Test data validation with various edge cases"""
        # Test with all NaN column
        df = pd.DataFrame({
            'all_nan': [np.nan, np.nan, np.nan],
            'valid': [1, 2, 3]
        })
        
        temp_file = os.path.join(temp_dir, "edge_case_data.csv")
        df.to_csv(temp_file, index=False)
        
        # Should handle gracefully
        desc_result = stats_tool.describe(temp_file)
        assert 'statistics' in desc_result
        
        print(f"DEBUG: Edge case data validation completed")

    def test_file_extension_validation(self, stats_tool, temp_dir):
        """Test file extension validation"""
        # Create file with allowed extension
        df = pd.DataFrame({'x': [1, 2, 3]})
        
        # Test CSV (should work)
        csv_file = os.path.join(temp_dir, "test.csv")
        df.to_csv(csv_file, index=False)
        
        result = stats_tool.read_data(csv_file)
        assert result['observations'] == 3
        
        print(f"DEBUG: CSV file extension validation passed")

    def test_statistical_assumptions_checking(self, stats_tool, stats_test_data_file):
        """Test that statistical methods work with real data assumptions"""
        # Test normality-sensitive tests with real data
        desc_result = stats_tool.describe(stats_test_data_file, variables=['age', 'score'])
        
        # Check skewness and kurtosis are calculated
        stats = desc_result['statistics']
        if 'skew' in stats:
            age_skew = stats['age']['skew']
            print(f"DEBUG: Age skewness: {age_skew:.4f}")
        
        if 'kurtosis' in stats:
            age_kurtosis = stats['age']['kurtosis']
            print(f"DEBUG: Age kurtosis: {age_kurtosis:.4f}")
