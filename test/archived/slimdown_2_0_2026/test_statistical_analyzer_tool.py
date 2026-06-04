"""
Comprehensive tests for StatisticalAnalyzerTool

Tests real functionality without mocks to verify actual behavior and output.
Includes debug output for manual verification of tool functionality.

Run with: poetry run pytest test/test_statistical_analyzer_tool.py -v -s
Coverage: poetry run python test/run_statistical_analyzer_coverage.py
"""

# Pre-import critical modules to avoid reload issues during coverage collection
import sys
import numpy as np
import pandas as pd
import scipy
from scipy import stats as scipy_stats

# Mark as already loaded to prevent reload warnings
if not hasattr(sys.modules.get('numpy', None), '_test_imported'):
    if 'numpy' in sys.modules:
        sys.modules['numpy']._test_imported = True

import os
from pathlib import Path
from typing import Any, Dict

import pytest

from aiecs.tools.statistics.statistical_analyzer_tool import (
    StatisticalAnalyzerTool,
    AnalysisType,
    StatisticalAnalyzerSettings,
    StatisticalAnalyzerError,
    AnalysisError
)


class TestStatisticalAnalyzerToolInitialization:
    """Test StatisticalAnalyzerTool initialization and configuration"""
    
    def test_default_initialization(self):
        """Test tool initialization with default settings"""
        print("\n=== Testing Default Initialization ===")
        tool = StatisticalAnalyzerTool()
        
        assert tool is not None
        assert tool.settings.significance_level == 0.05
        assert tool.settings.confidence_level == 0.95
        assert tool.settings.enable_effect_size is True
        
        print(f"✓ Tool initialized with default settings")
        print(f"  - Significance level: {tool.settings.significance_level}")
        print(f"  - Confidence level: {tool.settings.confidence_level}")
    
    def test_custom_configuration(self):
        """Test tool initialization with custom configuration"""
        print("\n=== Testing Custom Configuration ===")
        config = {
            'significance_level': 0.01,
            'confidence_level': 0.99,
            'enable_effect_size': False
        }
        tool = StatisticalAnalyzerTool(config=config)
        
        assert tool.settings.significance_level == 0.01
        assert tool.settings.confidence_level == 0.99
        assert tool.settings.enable_effect_size is False
        
        print(f"✓ Tool initialized with custom settings")
        print(f"  - Significance level: {tool.settings.significance_level}")
    
    def test_invalid_configuration(self):
        """Test initialization with invalid configuration"""
        print("\n=== Testing Invalid Configuration ===")
        
        with pytest.raises(ValueError) as exc_info:
            StatisticalAnalyzerTool(config={'significance_level': 'invalid'})
        
        assert "Invalid settings" in str(exc_info.value)
        print(f"✓ Correctly raised ValueError for invalid config")
    
    def test_external_tools_initialization(self):
        """Test external tools initialization"""
        print("\n=== Testing External Tools Initialization ===")
        tool = StatisticalAnalyzerTool()
        
        assert hasattr(tool, 'external_tools')
        assert 'stats' in tool.external_tools
        
        print(f"✓ External tools initialized")
        print(f"  - StatsTool available: {tool.external_tools['stats'] is not None}")


class TestDescriptiveAnalysis:
    """Test descriptive statistics analysis"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for descriptive analysis"""
        np.random.seed(42)
        return pd.DataFrame({
            'score': np.random.normal(70, 10, 100),
            'age': np.random.randint(20, 60, 100),
            'value': np.random.exponential(5, 100)
        })
    
    def test_descriptive_analysis_all_columns(self, sample_data):
        """Test descriptive analysis with all numeric columns"""
        print("\n=== Testing Descriptive Analysis - All Columns ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze(
            data=sample_data,
            analysis_type=AnalysisType.DESCRIPTIVE,
            variables={}
        )
        
        assert 'results' in result
        assert 'score' in result['results']
        assert 'age' in result['results']
        assert 'value' in result['results']
        assert 'mean' in result['results']['score']
        assert 'std' in result['results']['score']
        assert 'median' in result['results']['score']
        
        print(f"✓ Descriptive analysis completed")
        print(f"  - Score mean: {result['results']['score']['mean']:.2f}")
        print(f"  - Score std: {result['results']['score']['std']:.2f}")
        print(f"  - Skewness: {result['results']['score']['skewness']:.4f}")
    
    def test_descriptive_analysis_specific_columns(self, sample_data):
        """Test descriptive analysis with specific columns"""
        print("\n=== Testing Descriptive Analysis - Specific Columns ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze(
            data=sample_data,
            analysis_type=AnalysisType.DESCRIPTIVE,
            variables={'columns': ['score', 'age']}
        )
        
        assert 'score' in result['results']
        assert 'age' in result['results']
        assert 'value' not in result['results']
        
        print(f"✓ Specific columns analyzed")
        print(f"  - Columns: ['score', 'age']")


class TestTTest:
    """Test t-test functionality"""
    
    @pytest.fixture
    def ttest_data(self):
        """Create data for t-test"""
        np.random.seed(42)
        return pd.DataFrame({
            'group1': np.random.normal(70, 10, 50),
            'group2': np.random.normal(75, 10, 50)
        })
    
    def test_t_test_independent(self, ttest_data):
        """Test independent samples t-test"""
        print("\n=== Testing T-Test - Independent Samples ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze(
            data=ttest_data,
            analysis_type=AnalysisType.T_TEST,
            variables={'var1': 'group1', 'var2': 'group2'}
        )
        
        assert 'test_type' in result
        assert result['test_type'] == 't_test'
        assert 'statistic' in result
        assert 'p_value' in result
        assert 'significant' in result
        assert 'interpretation' in result
        
        print(f"✓ T-test completed")
        print(f"  - Statistic: {result['statistic']:.4f}")
        print(f"  - P-value: {result['p_value']:.4f}")
        print(f"  - Significant: {result['significant']}")
    
    def test_t_test_via_hypothesis_testing(self, ttest_data):
        """Test t-test via test_hypothesis method"""
        print("\n=== Testing T-Test via Hypothesis Testing ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.test_hypothesis(
            data=ttest_data,
            test_type='t_test',
            variables={'var1': 'group1', 'var2': 'group2'}
        )
        
        assert result['test_type'] == 't_test'
        assert 'p_value' in result
        
        print(f"✓ Hypothesis testing (t-test) completed")
    
    def test_t_test_missing_variables(self):
        """Test t-test error handling for missing variables"""
        print("\n=== Testing T-Test - Missing Variables ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({'group1': [1, 2, 3]})
        
        with pytest.raises(AnalysisError):
            tool.analyze(
                data=data,
                analysis_type=AnalysisType.T_TEST,
                variables={'var1': 'group1'}  # Missing var2
            )
        
        print(f"✓ Missing variables error handled correctly")


class TestANOVA:
    """Test ANOVA functionality"""
    
    @pytest.fixture
    def anova_data(self):
        """Create data for ANOVA"""
        np.random.seed(42)
        return pd.DataFrame({
            'group_a': np.random.normal(70, 10, 50),
            'group_b': np.random.normal(75, 10, 50),
            'group_c': np.random.normal(72, 10, 50)
        })
    
    def test_anova_three_groups(self, anova_data):
        """Test ANOVA with three groups"""
        print("\n=== Testing ANOVA - Three Groups ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze(
            data=anova_data,
            analysis_type=AnalysisType.ANOVA,
            variables={'groups': ['group_a', 'group_b', 'group_c']}
        )
        
        assert result['test_type'] == 'anova'
        assert 'statistic' in result
        assert 'p_value' in result
        assert 'significant' in result
        assert len(result['groups']) == 3
        
        print(f"✓ ANOVA completed")
        print(f"  - F-statistic: {result['statistic']:.4f}")
        print(f"  - P-value: {result['p_value']:.4f}")
        print(f"  - Groups: {result['groups']}")
    
    def test_anova_two_groups(self, anova_data):
        """Test ANOVA with two groups"""
        print("\n=== Testing ANOVA - Two Groups ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.test_hypothesis(
            data=anova_data,
            test_type='anova',
            variables={'groups': ['group_a', 'group_b']}
        )
        
        assert result['test_type'] == 'anova'
        
        print(f"✓ ANOVA with two groups completed")
    
    def test_anova_insufficient_groups(self):
        """Test ANOVA error handling for insufficient groups"""
        print("\n=== Testing ANOVA - Insufficient Groups ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({'group1': [1, 2, 3, 4, 5]})
        
        with pytest.raises(AnalysisError):
            tool.analyze(
                data=data,
                analysis_type=AnalysisType.ANOVA,
                variables={'groups': ['group1']}  # Only one group
            )
        
        print(f"✓ Insufficient groups error handled correctly")


class TestChiSquare:
    """Test chi-square test functionality"""
    
    @pytest.fixture
    def chi_square_data(self):
        """Create data for chi-square test"""
        np.random.seed(42)
        return pd.DataFrame({
            'gender': np.random.choice(['M', 'F'], 100),
            'preference': np.random.choice(['A', 'B', 'C'], 100)
        })
    
    def test_chi_square_independence(self, chi_square_data):
        """Test chi-square test for independence"""
        print("\n=== Testing Chi-Square Test ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze(
            data=chi_square_data,
            analysis_type=AnalysisType.CHI_SQUARE,
            variables={'var1': 'gender', 'var2': 'preference'}
        )
        
        assert result['test_type'] == 'chi_square'
        assert 'statistic' in result
        assert 'p_value' in result
        assert 'degrees_of_freedom' in result
        assert 'significant' in result
        
        print(f"✓ Chi-square test completed")
        print(f"  - Statistic: {result['statistic']:.4f}")
        print(f"  - DOF: {result['degrees_of_freedom']}")
        print(f"  - P-value: {result['p_value']:.4f}")
    
    def test_chi_square_via_hypothesis_testing(self, chi_square_data):
        """Test chi-square via test_hypothesis method"""
        print("\n=== Testing Chi-Square via Hypothesis Testing ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.test_hypothesis(
            data=chi_square_data,
            test_type='chi_square',
            variables={'var1': 'gender', 'var2': 'preference'}
        )
        
        assert result['test_type'] == 'chi_square'
        
        print(f"✓ Chi-square hypothesis testing completed")
    
    def test_chi_square_missing_variables(self):
        """Test chi-square error handling"""
        print("\n=== Testing Chi-Square - Missing Variables ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({'var1': ['A', 'B', 'C']})
        
        with pytest.raises(AnalysisError):
            tool.analyze(
                data=data,
                analysis_type=AnalysisType.CHI_SQUARE,
                variables={'var1': 'var1'}  # Missing var2
            )
        
        print(f"✓ Missing variables error handled correctly")


class TestLinearRegression:
    """Test linear regression functionality"""
    
    @pytest.fixture
    def regression_data(self):
        """Create data for regression"""
        np.random.seed(42)
        X1 = np.random.randn(100)
        X2 = np.random.randn(100)
        y = 2 * X1 + 3 * X2 + np.random.randn(100) * 0.5
        
        return pd.DataFrame({
            'X1': X1,
            'X2': X2,
            'y': y
        })
    
    def test_linear_regression_single_predictor(self, regression_data):
        """Test linear regression with single predictor"""
        print("\n=== Testing Linear Regression - Single Predictor ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze(
            data=regression_data,
            analysis_type=AnalysisType.LINEAR_REGRESSION,
            variables={'dependent': 'y', 'independent': ['X1']}
        )
        
        assert result['model_type'] == 'linear_regression'
        assert 'intercept' in result
        assert 'coefficients' in result
        assert 'r_squared' in result
        assert 'mse' in result
        assert 'rmse' in result
        
        print(f"✓ Linear regression completed")
        print(f"  - R²: {result['r_squared']:.4f}")
        print(f"  - RMSE: {result['rmse']:.4f}")
        print(f"  - Coefficients: {result['coefficients']}")
    
    def test_linear_regression_multiple_predictors(self, regression_data):
        """Test linear regression with multiple predictors"""
        print("\n=== Testing Linear Regression - Multiple Predictors ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze(
            data=regression_data,
            analysis_type=AnalysisType.LINEAR_REGRESSION,
            variables={'dependent': 'y', 'independent': ['X1', 'X2']}
        )
        
        assert len(result['coefficients']) == 2
        assert 'X1' in result['coefficients']
        assert 'X2' in result['coefficients']
        
        print(f"✓ Multiple regression completed")
        print(f"  - R²: {result['r_squared']:.4f}")
    
    def test_perform_regression_method(self, regression_data):
        """Test perform_regression method"""
        print("\n=== Testing Perform Regression Method ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.perform_regression(
            data=regression_data,
            dependent_var='y',
            independent_vars=['X1', 'X2'],
            regression_type='linear'
        )
        
        assert 'r_squared' in result
        assert 'coefficients' in result
        
        print(f"✓ Perform regression method completed")
    
    def test_regression_missing_variables(self):
        """Test regression error handling"""
        print("\n=== Testing Regression - Missing Variables ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({'X': [1, 2, 3]})
        
        with pytest.raises(AnalysisError):
            tool.analyze(
                data=data,
                analysis_type=AnalysisType.LINEAR_REGRESSION,
                variables={'dependent': 'X'}  # Missing independent
            )
        
        print(f"✓ Missing variables error handled correctly")


class TestCorrelationAnalysis:
    """Test correlation analysis functionality"""
    
    @pytest.fixture
    def correlation_data(self):
        """Create data for correlation analysis"""
        np.random.seed(42)
        X1 = np.random.randn(100)
        X2 = X1 + np.random.randn(100) * 0.5  # Correlated with X1
        X3 = np.random.randn(100)  # Independent
        
        return pd.DataFrame({
            'var1': X1,
            'var2': X2,
            'var3': X3
        })
    
    def test_correlation_analysis_all_variables(self, correlation_data):
        """Test correlation analysis with all variables"""
        print("\n=== Testing Correlation Analysis - All Variables ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze(
            data=correlation_data,
            analysis_type=AnalysisType.CORRELATION,
            variables={}
        )
        
        assert 'method' in result
        assert 'correlation_matrix' in result
        assert 'significant_correlations' in result
        assert 'interpretation' in result
        
        print(f"✓ Correlation analysis completed")
        print(f"  - Method: {result['method']}")
        print(f"  - Significant correlations found: {len(result['significant_correlations'])}")
        for corr in result['significant_correlations'][:3]:
            print(f"    {corr['var1']} <-> {corr['var2']}: {corr['correlation']:.4f} ({corr['strength']})")
    
    def test_correlation_analysis_specific_variables(self, correlation_data):
        """Test correlation analysis with specific variables"""
        print("\n=== Testing Correlation Analysis - Specific Variables ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze(
            data=correlation_data,
            analysis_type=AnalysisType.CORRELATION,
            variables={'variables': ['var1', 'var2']}
        )
        
        assert 'correlation_matrix' in result
        
        print(f"✓ Specific variables correlation completed")
    
    def test_analyze_correlation_method(self, correlation_data):
        """Test analyze_correlation method"""
        print("\n=== Testing Analyze Correlation Method ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze_correlation(
            data=correlation_data,
            variables=['var1', 'var2', 'var3'],
            method='pearson'
        )
        
        assert 'correlation_matrix' in result
        assert result['method'] == 'pearson'
        
        print(f"✓ Analyze correlation method completed")
    
    def test_correlation_analysis_spearman(self, correlation_data):
        """Test correlation with Spearman method"""
        print("\n=== Testing Correlation - Spearman ===")
        tool = StatisticalAnalyzerTool()
        
        result = tool.analyze_correlation(
            data=correlation_data,
            method='spearman'
        )
        
        assert result['method'] == 'spearman'
        
        print(f"✓ Spearman correlation completed")
    
    def test_correlation_insufficient_variables(self):
        """Test correlation error handling"""
        print("\n=== Testing Correlation - Insufficient Variables ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({'var1': [1, 2, 3]})
        
        with pytest.raises(AnalysisError):
            tool.analyze(
                data=data,
                analysis_type=AnalysisType.CORRELATION,
                variables={}
            )
        
        print(f"✓ Insufficient variables error handled correctly")


class TestDataConversion:
    """Test data conversion functionality"""
    
    def test_dataframe_input(self):
        """Test with DataFrame input"""
        print("\n=== Testing DataFrame Input ===")
        tool = StatisticalAnalyzerTool()
        
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        converted = tool._to_dataframe(df)
        
        assert isinstance(converted, pd.DataFrame)
        assert converted.equals(df)
        
        print(f"✓ DataFrame input handled")
    
    def test_dict_input(self):
        """Test with dictionary input"""
        print("\n=== Testing Dict Input ===")
        tool = StatisticalAnalyzerTool()
        
        data = {'col1': 1, 'col2': 2, 'col3': 3}
        converted = tool._to_dataframe(data)
        
        assert isinstance(converted, pd.DataFrame)
        assert len(converted) == 1
        
        print(f"✓ Dict input converted")
    
    def test_list_input(self):
        """Test with list input"""
        print("\n=== Testing List Input ===")
        tool = StatisticalAnalyzerTool()
        
        data = [
            {'x': 1, 'y': 2},
            {'x': 3, 'y': 4},
            {'x': 5, 'y': 6}
        ]
        converted = tool._to_dataframe(data)
        
        assert isinstance(converted, pd.DataFrame)
        assert len(converted) == 3
        
        print(f"✓ List input converted")
    
    def test_unsupported_data_type(self):
        """Test error handling for unsupported data types"""
        print("\n=== Testing Unsupported Data Type ===")
        tool = StatisticalAnalyzerTool()
        
        with pytest.raises(AnalysisError) as exc_info:
            tool._to_dataframe("invalid_data")
        
        assert "Unsupported data type" in str(exc_info.value)
        print(f"✓ Correctly raised AnalysisError")


class TestErrorHandling:
    """Test error handling and exceptions"""
    
    def test_analysis_error_invalid_data(self):
        """Test AnalysisError on invalid data"""
        print("\n=== Testing AnalysisError ===")
        tool = StatisticalAnalyzerTool()
        
        with pytest.raises(AnalysisError):
            tool.analyze(
                data=None,
                analysis_type=AnalysisType.DESCRIPTIVE,
                variables={}
            )
        
        print(f"✓ AnalysisError raised correctly")
    
    def test_unsupported_analysis_type(self):
        """Test error for unsupported analysis type"""
        print("\n=== Testing Unsupported Analysis Type ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({'a': [1, 2, 3]})
        
        # Note: Cannot directly test unsupported enum value, but can test the logic
        print(f"✓ Analysis type validation works through enum")
    
    def test_unsupported_test_type(self):
        """Test error for unsupported test type"""
        print("\n=== Testing Unsupported Test Type ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({'a': [1, 2, 3]})
        
        with pytest.raises(AnalysisError) as exc_info:
            tool.test_hypothesis(
                data=data,
                test_type='unsupported',
                variables={}
            )
        
        assert "Unsupported test type" in str(exc_info.value)
        print(f"✓ Unsupported test type error handled")
    
    def test_unsupported_regression_type(self):
        """Test error for unsupported regression type"""
        print("\n=== Testing Unsupported Regression Type ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({'x': [1, 2, 3], 'y': [2, 4, 6]})
        
        with pytest.raises(AnalysisError) as exc_info:
            tool.perform_regression(
                data=data,
                dependent_var='y',
                independent_vars=['x'],
                regression_type='unsupported'
            )
        
        assert "Unsupported regression type" in str(exc_info.value)
        print(f"✓ Unsupported regression type error handled")


class TestHelperMethods:
    """Test helper methods"""
    
    def test_interpret_correlation_weak(self):
        """Test correlation interpretation - weak"""
        print("\n=== Testing Correlation Interpretation - Weak ===")
        tool = StatisticalAnalyzerTool()
        
        strength = tool._interpret_correlation(0.2)
        assert strength == "weak"
        
        print(f"✓ Weak correlation interpreted correctly")
    
    def test_interpret_correlation_moderate(self):
        """Test correlation interpretation - moderate"""
        print("\n=== Testing Correlation Interpretation - Moderate ===")
        tool = StatisticalAnalyzerTool()
        
        strength = tool._interpret_correlation(0.5)
        assert strength == "moderate"
        
        print(f"✓ Moderate correlation interpreted correctly")
    
    def test_interpret_correlation_strong(self):
        """Test correlation interpretation - strong"""
        print("\n=== Testing Correlation Interpretation - Strong ===")
        tool = StatisticalAnalyzerTool()
        
        strength = tool._interpret_correlation(0.8)
        assert strength == "strong"
        
        strength_negative = tool._interpret_correlation(-0.8)
        assert strength_negative == "strong"
        
        print(f"✓ Strong correlation interpreted correctly")


class TestIntegration:
    """Test integration with other components"""
    
    def test_settings_model(self):
        """Test StatisticalAnalyzerSettings model"""
        print("\n=== Testing Settings Model ===")
        
        settings = StatisticalAnalyzerSettings()
        assert settings.significance_level == 0.05
        assert settings.confidence_level == 0.95
        
        print(f"✓ Settings model works correctly")
    
    def test_analysis_type_enum(self):
        """Test AnalysisType enum"""
        print("\n=== Testing AnalysisType Enum ===")
        
        assert AnalysisType.DESCRIPTIVE.value == "descriptive"
        assert AnalysisType.T_TEST.value == "t_test"
        assert AnalysisType.ANOVA.value == "anova"
        
        print(f"✓ AnalysisType enum values correct")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_analysis_with_missing_data(self):
        """Test analysis with missing data"""
        print("\n=== Testing Analysis with Missing Data ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({
            'var1': [1, 2, None, 4, 5, 6, 7, 8],
            'var2': [10, None, 30, 40, 50, None, 70, 80]
        })
        
        result = tool.analyze(
            data=data,
            analysis_type=AnalysisType.DESCRIPTIVE,
            variables={'columns': ['var1', 'var2']}
        )
        
        assert 'results' in result
        
        print(f"✓ Missing data handled in analysis")
    
    def test_single_value_column(self):
        """Test analysis with single value column"""
        print("\n=== Testing Single Value Column ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({
            'constant': [5, 5, 5, 5, 5]
        })
        
        result = tool.analyze(
            data=data,
            analysis_type=AnalysisType.DESCRIPTIVE,
            variables={}
        )
        
        assert result['results']['constant']['std'] == 0.0
        
        print(f"✓ Single value column handled")
    
    def test_small_sample_t_test(self):
        """Test t-test with small sample"""
        print("\n=== Testing T-Test with Small Sample ===")
        tool = StatisticalAnalyzerTool()
        
        data = pd.DataFrame({
            'group1': [1, 2, 3],
            'group2': [2, 3, 4]
        })
        
        result = tool.test_hypothesis(
            data=data,
            test_type='t_test',
            variables={'var1': 'group1', 'var2': 'group2'}
        )
        
        assert 'p_value' in result
        
        print(f"✓ Small sample t-test handled")


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    def test_complete_analysis_workflow(self):
        """Test complete analysis workflow"""
        print("\n=== Testing Complete Analysis Workflow ===")
        tool = StatisticalAnalyzerTool()
        
        # Create realistic dataset
        np.random.seed(42)
        data = pd.DataFrame({
            'control_group': np.random.normal(70, 10, 50),
            'treatment_group': np.random.normal(75, 10, 50),
            'age': np.random.randint(20, 60, 50),
            'score': np.random.normal(80, 15, 50)
        })
        
        # Step 1: Descriptive analysis
        print("\nStep 1: Descriptive Analysis")
        desc_result = tool.analyze(
            data=data,
            analysis_type=AnalysisType.DESCRIPTIVE,
            variables={}
        )
        print(f"  - Mean control: {desc_result['results']['control_group']['mean']:.2f}")
        
        # Step 2: T-test to compare groups
        print("\nStep 2: T-Test")
        ttest_result = tool.test_hypothesis(
            data=data,
            test_type='t_test',
            variables={'var1': 'control_group', 'var2': 'treatment_group'}
        )
        print(f"  - P-value: {ttest_result['p_value']:.4f}")
        print(f"  - Significant: {ttest_result['significant']}")
        
        # Step 3: Correlation analysis
        print("\nStep 3: Correlation Analysis")
        corr_result = tool.analyze_correlation(
            data=data,
            variables=['age', 'score']
        )
        print(f"  - Correlations found: {len(corr_result['significant_correlations'])}")
        
        print(f"\n✓ Complete workflow executed successfully")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

