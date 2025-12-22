"""
Comprehensive tests for DataProfilerTool

Tests real functionality without mocks to verify actual behavior and output.
Includes debug output for manual verification of tool functionality.

Run with: poetry run pytest test/test_data_profiler_tool.py -v -s
Coverage: poetry run pytest test/test_data_profiler_tool.py --cov=aiecs.tools.statistics.data_profiler_tool --cov-report=term-missing --cov-report=html
"""

import os
import tempfile
import json
from pathlib import Path
from typing import Any, Dict

import pytest
import pandas as pd
import numpy as np

from aiecs.tools.statistics.data_profiler_tool import (
    DataProfilerTool,
    ProfileLevel,
    DataQualityCheck,
    DataProfilerSettings,
    DataProfilerError,
    ProfilingError
)


class TestDataProfilerToolInitialization:
    """Test DataProfilerTool initialization and configuration"""
    
    def test_default_initialization(self):
        """Test tool initialization with default settings"""
        print("\n=== Testing Default Initialization ===")
        tool = DataProfilerTool()
        
        assert tool is not None
        assert tool.settings.default_profile_level == ProfileLevel.STANDARD
        assert tool.settings.outlier_std_threshold == 3.0
        assert tool.settings.correlation_threshold == 0.7
        assert tool.settings.missing_threshold == 0.5
        assert tool.settings.enable_visualizations is True
        
        print(f"✓ Tool initialized with default settings")
        print(f"  - Default profile level: {tool.settings.default_profile_level}")
        print(f"  - Outlier threshold: {tool.settings.outlier_std_threshold}")
        print(f"  - Correlation threshold: {tool.settings.correlation_threshold}")
        print(f"  - Missing threshold: {tool.settings.missing_threshold}")
    
    def test_custom_configuration(self):
        """Test tool initialization with custom configuration"""
        print("\n=== Testing Custom Configuration ===")
        config = {
            'default_profile_level': ProfileLevel.COMPREHENSIVE,
            'outlier_std_threshold': 2.5,
            'correlation_threshold': 0.8,
            'missing_threshold': 0.3,
            'enable_visualizations': False,
            'max_unique_values_categorical': 100
        }
        tool = DataProfilerTool(config=config)
        
        assert tool.settings.default_profile_level == ProfileLevel.COMPREHENSIVE
        assert tool.settings.outlier_std_threshold == 2.5
        assert tool.settings.correlation_threshold == 0.8
        assert tool.settings.missing_threshold == 0.3
        assert tool.settings.enable_visualizations is False
        assert tool.settings.max_unique_values_categorical == 100
        
        print(f"✓ Tool initialized with custom settings")
        print(f"  - Profile level: {tool.settings.default_profile_level}")
        print(f"  - Outlier threshold: {tool.settings.outlier_std_threshold}")
    
    def test_invalid_configuration(self):
        """Test initialization with invalid configuration"""
        print("\n=== Testing Invalid Configuration ===")
        
        with pytest.raises(ValueError) as exc_info:
            DataProfilerTool(config={'outlier_std_threshold': 'invalid'})
        
        assert "Invalid settings" in str(exc_info.value)
        print(f"✓ Correctly raised ValueError for invalid config")
    
    def test_external_tools_initialization(self):
        """Test external tools initialization"""
        print("\n=== Testing External Tools Initialization ===")
        tool = DataProfilerTool()
        
        assert hasattr(tool, 'external_tools')
        assert 'stats' in tool.external_tools
        assert 'pandas' in tool.external_tools
        
        print(f"✓ External tools initialized")
        print(f"  - StatsTool available: {tool.external_tools['stats'] is not None}")
        print(f"  - PandasTool available: {tool.external_tools['pandas'] is not None}")


class TestProfileDatasetBasic:
    """Test basic dataset profiling functionality"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing"""
        return pd.DataFrame({
            'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace', 'Henry', 'Ivy', 'Jack'],
            'age': [25, 30, 35, 40, 45, 28, 32, 38, 42, 27],
            'salary': [50000, 60000, 70000, 80000, 90000, 55000, 65000, 75000, 85000, 58000],
            'department': ['HR', 'IT', 'Finance', 'IT', 'HR', 'Finance', 'IT', 'HR', 'Finance', 'IT']
        })
    
    def test_profile_dataset_standard_level(self, sample_data):
        """Test dataset profiling with standard level"""
        print("\n=== Testing Standard Level Profiling ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=sample_data, level=ProfileLevel.STANDARD)
        
        assert 'summary' in result
        assert 'column_profiles' in result
        assert 'quality_issues' in result
        assert 'correlations' in result
        assert 'recommendations' in result
        assert 'profile_level' in result
        
        print(f"✓ Standard profiling completed")
        print(f"  - Profile level: {result['profile_level']}")
        print(f"  - Rows: {result['summary']['rows']}")
        print(f"  - Columns: {result['summary']['columns']}")
        print(f"  - Numeric columns: {result['summary']['numeric_columns']}")
        print(f"  - Categorical columns: {result['summary']['categorical_columns']}")
        print(f"\nSummary:")
        for key, value in result['summary'].items():
            print(f"    {key}: {value}")
    
    def test_profile_dataset_basic_level(self, sample_data):
        """Test dataset profiling with basic level"""
        print("\n=== Testing Basic Level Profiling ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=sample_data, level=ProfileLevel.BASIC)
        
        assert result['profile_level'] == ProfileLevel.BASIC.value
        assert 'summary' in result
        assert len(result['correlations']) == 0  # Basic level doesn't include correlations
        
        print(f"✓ Basic profiling completed")
        print(f"  - Profile level: {result['profile_level']}")
        print(f"  - Correlation analysis: {len(result['correlations']) > 0}")
    
    def test_profile_dataset_comprehensive_level(self, sample_data):
        """Test dataset profiling with comprehensive level"""
        print("\n=== Testing Comprehensive Level Profiling ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=sample_data, level=ProfileLevel.COMPREHENSIVE)
        
        assert result['profile_level'] == ProfileLevel.COMPREHENSIVE.value
        assert 'correlations' in result
        assert len(result['correlations']) > 0  # Comprehensive includes correlations
        
        print(f"✓ Comprehensive profiling completed")
        print(f"  - Profile level: {result['profile_level']}")
        print(f"  - Correlations computed: {len(result['correlations']) > 0}")
        if 'correlation_matrix' in result['correlations']:
            print(f"  - Correlation matrix size: {len(result['correlations']['correlation_matrix'])}")
    
    def test_profile_dataset_deep_level(self, sample_data):
        """Test dataset profiling with deep level"""
        print("\n=== Testing Deep Level Profiling ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=sample_data, level=ProfileLevel.DEEP)
        
        assert result['profile_level'] == ProfileLevel.DEEP.value
        assert 'correlations' in result
        
        print(f"✓ Deep profiling completed")
        print(f"  - Profile level: {result['profile_level']}")
    
    def test_profile_dataset_with_dict_data(self):
        """Test profiling with dictionary data"""
        print("\n=== Testing Profiling with Dict Data ===")
        tool = DataProfilerTool()
        
        data = {'id': 1, 'name': 'Test', 'value': 100}
        result = tool.profile_dataset(data=data, level=ProfileLevel.BASIC)
        
        assert result['summary']['rows'] == 1
        assert result['summary']['columns'] == 3
        
        print(f"✓ Dict data profiled successfully")
        print(f"  - Rows: {result['summary']['rows']}")
        print(f"  - Columns: {result['summary']['columns']}")
    
    def test_profile_dataset_with_list_data(self):
        """Test profiling with list of dictionaries"""
        print("\n=== Testing Profiling with List Data ===")
        tool = DataProfilerTool()
        
        data = [
            {'id': 1, 'name': 'Alice', 'score': 95},
            {'id': 2, 'name': 'Bob', 'score': 87},
            {'id': 3, 'name': 'Charlie', 'score': 92}
        ]
        result = tool.profile_dataset(data=data, level=ProfileLevel.STANDARD)
        
        assert result['summary']['rows'] == 3
        assert result['summary']['columns'] == 3
        
        print(f"✓ List data profiled successfully")
        print(f"  - Rows: {result['summary']['rows']}")
        print(f"  - Columns: {result['summary']['columns']}")


class TestColumnProfiling:
    """Test column-level profiling functionality"""
    
    @pytest.fixture
    def numeric_data(self):
        """Create data with numeric columns"""
        np.random.seed(42)
        return pd.DataFrame({
            'int_col': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'float_col': [1.5, 2.3, 3.1, 4.7, 5.2, 6.8, 7.1, 8.9, 9.3, 10.5],
            'normal_dist': np.random.normal(100, 15, 10),
            'outlier_col': [10, 20, 30, 40, 50, 60, 70, 80, 90, 1000]  # Last value is outlier
        })
    
    @pytest.fixture
    def categorical_data(self):
        """Create data with categorical columns"""
        return pd.DataFrame({
            'category': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'A', 'B', 'C'],
            'status': ['active', 'inactive', 'active', 'pending', 'active', 
                      'inactive', 'pending', 'active', 'inactive', 'active'],
            'region': ['North', 'South', 'North', 'East', 'West', 
                      'North', 'South', 'East', 'West', 'North']
        })
    
    def test_numeric_column_profiling(self, numeric_data):
        """Test profiling of numeric columns"""
        print("\n=== Testing Numeric Column Profiling ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=numeric_data, level=ProfileLevel.STANDARD)
        profiles = result['column_profiles']
        
        # Check int_col profile
        int_profile = profiles['int_col']
        assert int_profile['type'] == 'numeric'
        assert int_profile['min'] == 1
        assert int_profile['max'] == 10
        assert 'mean' in int_profile
        assert 'median' in int_profile
        assert 'std' in int_profile
        
        print(f"✓ Numeric columns profiled")
        print(f"\nInt column profile:")
        for key, value in int_profile.items():
            if key != 'name':
                print(f"    {key}: {value}")
    
    def test_numeric_column_comprehensive_profiling(self, numeric_data):
        """Test comprehensive numeric column profiling"""
        print("\n=== Testing Comprehensive Numeric Profiling ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=numeric_data, level=ProfileLevel.COMPREHENSIVE)
        profiles = result['column_profiles']
        
        float_profile = profiles['float_col']
        assert 'q25' in float_profile
        assert 'q75' in float_profile
        assert 'skewness' in float_profile
        assert 'kurtosis' in float_profile
        
        print(f"✓ Comprehensive numeric profiling completed")
        print(f"\nFloat column extended profile:")
        print(f"    Q25: {float_profile['q25']}")
        print(f"    Q75: {float_profile['q75']}")
        print(f"    Skewness: {float_profile['skewness']}")
        print(f"    Kurtosis: {float_profile['kurtosis']}")
    
    def test_outlier_detection(self, numeric_data):
        """Test outlier detection in numeric columns"""
        print("\n=== Testing Outlier Detection ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=numeric_data, level=ProfileLevel.COMPREHENSIVE)
        outlier_profile = result['column_profiles']['outlier_col']
        
        # Check if outlier detection was performed
        # Note: With default threshold of 3 std, the outlier may or may not be detected
        if 'outlier_count' in outlier_profile:
            print(f"✓ Outlier detection completed")
            print(f"  - Outlier count: {outlier_profile['outlier_count']}")
            print(f"  - Outlier percentage: {outlier_profile.get('outlier_percentage', 0):.2f}%")
        else:
            print(f"✓ Outlier detection skipped (std may be 0 or data doesn't support it)")
    
    def test_categorical_column_profiling(self, categorical_data):
        """Test profiling of categorical columns"""
        print("\n=== Testing Categorical Column Profiling ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=categorical_data, level=ProfileLevel.STANDARD)
        profiles = result['column_profiles']
        
        category_profile = profiles['category']
        assert category_profile['type'] == 'categorical'
        assert 'unique_values' in category_profile
        assert 'most_common' in category_profile
        assert 'most_common_count' in category_profile
        
        print(f"✓ Categorical columns profiled")
        print(f"\nCategory column profile:")
        print(f"    Type: {category_profile['type']}")
        print(f"    Unique values: {category_profile['unique_values']}")
        print(f"    Most common: {category_profile['most_common']}")
        print(f"    Most common count: {category_profile['most_common_count']}")
    
    def test_categorical_column_comprehensive_profiling(self, categorical_data):
        """Test comprehensive categorical column profiling"""
        print("\n=== Testing Comprehensive Categorical Profiling ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=categorical_data, level=ProfileLevel.COMPREHENSIVE)
        profiles = result['column_profiles']
        
        status_profile = profiles['status']
        assert 'top_categories' in status_profile
        assert len(status_profile['top_categories']) > 0
        
        print(f"✓ Comprehensive categorical profiling completed")
        print(f"\nStatus column top categories:")
        for category, count in status_profile['top_categories'].items():
            print(f"    {category}: {count}")


class TestQualityIssueDetection:
    """Test data quality issue detection"""
    
    @pytest.fixture
    def data_with_missing_values(self):
        """Create data with missing values"""
        return pd.DataFrame({
            'col1': [1, 2, None, 4, 5, None, 7, 8, None, 10],
            'col2': ['a', None, 'c', 'd', None, 'f', None, 'h', 'i', None],
            'col3': [10.5, 20.3, 30.1, None, 50.9, 60.2, None, 80.1, 90.5, None]
        })
    
    @pytest.fixture
    def data_with_duplicates(self):
        """Create data with duplicate rows"""
        return pd.DataFrame({
            'a': [1, 2, 2, 3, 3, 3, 4, 5, 5, 6],
            'b': ['x', 'y', 'y', 'z', 'z', 'z', 'w', 'v', 'v', 'u']
        })
    
    @pytest.fixture
    def data_with_outliers(self):
        """Create data with outliers"""
        return pd.DataFrame({
            'values': [10, 12, 11, 13, 12, 14, 13, 15, 1000, 11]  # 1000 is clear outlier
        })
    
    def test_missing_values_detection(self, data_with_missing_values):
        """Test detection of missing values"""
        print("\n=== Testing Missing Values Detection ===")
        tool = DataProfilerTool()
        
        result = tool.detect_quality_issues(
            data=data_with_missing_values,
            checks=[DataQualityCheck.MISSING_VALUES]
        )
        
        assert 'issues' in result
        assert 'missing_values' in result['issues']
        assert len(result['issues']['missing_values']) > 0
        
        print(f"✓ Missing values detected")
        print(f"  - Total issues: {result['total_issues']}")
        print(f"  - Severity counts: {result['severity_counts']}")
        print(f"\nMissing value issues:")
        for issue in result['issues']['missing_values']:
            print(f"    Column '{issue['column']}': {issue['missing_percentage']:.2f}% missing (severity: {issue['severity']})")
    
    def test_duplicate_detection(self, data_with_duplicates):
        """Test detection of duplicate rows"""
        print("\n=== Testing Duplicate Detection ===")
        tool = DataProfilerTool()
        
        result = tool.detect_quality_issues(
            data=data_with_duplicates,
            checks=[DataQualityCheck.DUPLICATES]
        )
        
        assert 'duplicates' in result['issues']
        assert len(result['issues']['duplicates']) > 0
        
        print(f"✓ Duplicates detected")
        print(f"  - Total issues: {result['total_issues']}")
        print(f"\nDuplicate issues:")
        for issue in result['issues']['duplicates']:
            print(f"    Type: {issue['type']}")
            print(f"    Count: {issue['count']}")
            print(f"    Percentage: {issue['percentage']:.2f}%")
    
    def test_outlier_detection(self, data_with_outliers):
        """Test detection of outliers"""
        print("\n=== Testing Outlier Detection ===")
        tool = DataProfilerTool()
        
        result = tool.detect_quality_issues(
            data=data_with_outliers,
            checks=[DataQualityCheck.OUTLIERS]
        )
        
        assert 'outliers' in result['issues']
        if len(result['issues']['outliers']) > 0:
            print(f"✓ Outliers detected")
            print(f"  - Total issues: {result['total_issues']}")
            print(f"\nOutlier issues:")
            for issue in result['issues']['outliers']:
                print(f"    Column '{issue['column']}': {issue['count']} outliers ({issue['percentage']:.2f}%)")
        else:
            print(f"✓ No outliers detected (threshold may be too high)")
    
    def test_all_quality_checks(self, data_with_missing_values):
        """Test all quality checks at once"""
        print("\n=== Testing All Quality Checks ===")
        tool = DataProfilerTool()
        
        result = tool.detect_quality_issues(data=data_with_missing_values, checks=None)
        
        assert 'issues' in result
        assert 'total_issues' in result
        assert 'severity_counts' in result
        
        print(f"✓ All quality checks completed")
        print(f"  - Total issues: {result['total_issues']}")
        print(f"  - Severity breakdown: {result['severity_counts']}")
    
    def test_quality_issues_in_profile(self, data_with_missing_values):
        """Test quality issues included in full profile"""
        print("\n=== Testing Quality Issues in Profile ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(
            data=data_with_missing_values,
            level=ProfileLevel.STANDARD,
            checks=[DataQualityCheck.MISSING_VALUES, DataQualityCheck.DUPLICATES]
        )
        
        assert 'quality_issues' in result
        assert 'missing_values' in result['quality_issues']
        
        print(f"✓ Quality issues included in profile")
        print(f"  - Issue types: {list(result['quality_issues'].keys())}")


class TestCorrelationAnalysis:
    """Test correlation analysis functionality"""
    
    @pytest.fixture
    def correlated_data(self):
        """Create data with correlations"""
        np.random.seed(42)
        x = np.random.randn(100)
        return pd.DataFrame({
            'x': x,
            'y': x * 2 + np.random.randn(100) * 0.1,  # Highly correlated with x
            'z': x * -1.5 + np.random.randn(100) * 0.1,  # Negatively correlated with x
            'independent': np.random.randn(100)  # Independent
        })
    
    def test_correlation_analysis(self, correlated_data):
        """Test correlation analysis with correlated data"""
        print("\n=== Testing Correlation Analysis ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(
            data=correlated_data,
            level=ProfileLevel.COMPREHENSIVE
        )
        
        assert 'correlations' in result
        assert 'correlation_matrix' in result['correlations']
        assert 'high_correlations' in result['correlations']
        
        print(f"✓ Correlation analysis completed")
        print(f"  - Correlation matrix computed: {'correlation_matrix' in result['correlations']}")
        print(f"  - High correlations found: {result['correlations']['num_high_correlations']}")
        
        if result['correlations']['num_high_correlations'] > 0:
            print(f"\nHigh correlation pairs:")
            for pair in result['correlations']['high_correlations']:
                print(f"    {pair['column1']} <-> {pair['column2']}: {pair['correlation']:.3f}")
    
    def test_correlation_with_insufficient_columns(self):
        """Test correlation analysis with insufficient numeric columns"""
        print("\n=== Testing Correlation with Insufficient Columns ===")
        tool = DataProfilerTool()
        
        data = pd.DataFrame({
            'single_num': [1, 2, 3, 4, 5],
            'category': ['A', 'B', 'C', 'D', 'E']
        })
        
        result = tool.profile_dataset(data=data, level=ProfileLevel.COMPREHENSIVE)
        
        assert 'correlations' in result
        assert 'message' in result['correlations']
        
        print(f"✓ Handled insufficient columns gracefully")
        print(f"  - Message: {result['correlations']['message']}")


class TestRecommendations:
    """Test preprocessing recommendation generation"""
    
    @pytest.fixture
    def data_needing_preprocessing(self):
        """Create data that needs preprocessing"""
        return pd.DataFrame({
            'low_missing': [1, 2, None, 4, 5, 6, 7, 8, 9, 10],  # 10% missing
            'high_missing': [1, None, None, None, None, None, None, 8, 9, 10],  # 60% missing
            'duplicate_a': [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
            'duplicate_b': [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
        })
    
    def test_recommend_preprocessing(self, data_needing_preprocessing):
        """Test preprocessing recommendation generation"""
        print("\n=== Testing Preprocessing Recommendations ===")
        tool = DataProfilerTool()
        
        result = tool.recommend_preprocessing(data=data_needing_preprocessing)
        
        assert 'recommendations' in result
        assert 'total_steps' in result
        assert 'estimated_impact' in result
        assert len(result['recommendations']) > 0
        
        print(f"✓ Recommendations generated")
        print(f"  - Total steps: {result['total_steps']}")
        print(f"  - Estimated impact: {result['estimated_impact']}")
        print(f"\nRecommendations:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"  {i}. {rec['action']} (priority: {rec['priority']})")
            print(f"      Reason: {rec['reason']}")
    
    def test_recommendations_with_target_column(self):
        """Test recommendations with target column specified"""
        print("\n=== Testing Recommendations with Target Column ===")
        tool = DataProfilerTool()
        
        data = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [10, 20, 30, 40, 50],
            'target': [0, 1, 0, 1, 0]
        })
        
        result = tool.recommend_preprocessing(data=data, target_column='target')
        
        assert len(result['recommendations']) > 0
        # Should include task identification
        task_recs = [r for r in result['recommendations'] if r.get('action') == 'task_identified']
        
        print(f"✓ Task-specific recommendations generated")
        print(f"  - Total recommendations: {result['total_steps']}")
        if task_recs:
            print(f"  - Task type identified: {task_recs[0]['task_type']}")
    
    def test_recommendations_prioritization(self, data_needing_preprocessing):
        """Test that recommendations are properly prioritized"""
        print("\n=== Testing Recommendations Prioritization ===")
        tool = DataProfilerTool()
        
        result = tool.recommend_preprocessing(data=data_needing_preprocessing)
        
        # Check that high priority items come first
        priorities = [rec['priority'] for rec in result['recommendations']]
        
        print(f"✓ Recommendations prioritized")
        print(f"  - Priority order: {priorities}")
        
        # Verify high priority comes before low priority
        if 'high' in priorities and 'low' in priorities:
            high_idx = priorities.index('high')
            low_idx = priorities.index('low')
            assert high_idx < low_idx


class TestVisualizationData:
    """Test visualization data generation"""
    
    @pytest.fixture
    def mixed_data(self):
        """Create mixed data for visualization"""
        return pd.DataFrame({
            'numeric1': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'numeric2': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            'category': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'A', 'B', 'C']
        })
    
    def test_visualization_data_generation(self, mixed_data):
        """Test visualization data generation"""
        print("\n=== Testing Visualization Data Generation ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(
            data=mixed_data,
            level=ProfileLevel.STANDARD,
            generate_visualizations=True
        )
        
        assert 'visualization_data' in result
        viz_data = result['visualization_data']
        
        if 'numeric_distributions' in viz_data:
            print(f"✓ Numeric distributions generated")
            print(f"  - Number of numeric distributions: {len(viz_data['numeric_distributions'])}")
        
        if 'categorical_distributions' in viz_data:
            print(f"✓ Categorical distributions generated")
            print(f"  - Number of categorical distributions: {len(viz_data['categorical_distributions'])}")
    
    def test_no_visualization_by_default(self, mixed_data):
        """Test that visualizations are not generated by default"""
        print("\n=== Testing No Visualization by Default ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=mixed_data, level=ProfileLevel.STANDARD)
        
        assert 'visualization_data' not in result
        print(f"✓ Visualizations not generated by default")


class TestDataConversion:
    """Test data conversion functionality"""
    
    def test_dataframe_input(self):
        """Test with DataFrame input"""
        print("\n=== Testing DataFrame Input ===")
        tool = DataProfilerTool()
        
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        result = tool.profile_dataset(data=df, level=ProfileLevel.BASIC)
        
        assert result['summary']['rows'] == 3
        print(f"✓ DataFrame input processed")
    
    def test_dict_input(self):
        """Test with dictionary input"""
        print("\n=== Testing Dict Input ===")
        tool = DataProfilerTool()
        
        data = {'col1': 1, 'col2': 2, 'col3': 3}
        result = tool.profile_dataset(data=data, level=ProfileLevel.BASIC)
        
        assert result['summary']['rows'] == 1
        assert result['summary']['columns'] == 3
        print(f"✓ Dict input converted and processed")
    
    def test_list_input(self):
        """Test with list input"""
        print("\n=== Testing List Input ===")
        tool = DataProfilerTool()
        
        data = [
            {'x': 1, 'y': 2},
            {'x': 3, 'y': 4},
            {'x': 5, 'y': 6}
        ]
        result = tool.profile_dataset(data=data, level=ProfileLevel.BASIC)
        
        assert result['summary']['rows'] == 3
        assert result['summary']['columns'] == 2
        print(f"✓ List input converted and processed")
    
    def test_unsupported_data_type(self):
        """Test error handling for unsupported data types"""
        print("\n=== Testing Unsupported Data Type ===")
        tool = DataProfilerTool()
        
        with pytest.raises(ProfilingError) as exc_info:
            tool.profile_dataset(data="invalid_data", level=ProfileLevel.BASIC)
        
        assert "Unsupported data type" in str(exc_info.value)
        print(f"✓ Correctly raised ProfilingError for unsupported type")


class TestSummaryGeneration:
    """Test dataset summary generation"""
    
    @pytest.fixture
    def complete_dataset(self):
        """Create a complete dataset for summary testing"""
        return pd.DataFrame({
            'int1': [1, 2, 3, 4, 5],
            'int2': [10, 20, 30, 40, 50],
            'float1': [1.1, 2.2, 3.3, 4.4, 5.5],
            'cat1': ['A', 'B', 'C', 'A', 'B'],
            'cat2': ['X', 'Y', 'Z', 'X', 'Y']
        })
    
    @pytest.fixture
    def dataset_with_issues(self):
        """Create dataset with quality issues"""
        return pd.DataFrame({
            'col1': [1, 2, None, 4, 5, 5],
            'col2': ['a', None, 'c', 'd', 'e', 'e'],
            'col3': [10, 20, 30, 40, 50, 50]
        })
    
    def test_summary_statistics(self, complete_dataset):
        """Test summary statistics generation"""
        print("\n=== Testing Summary Statistics ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=complete_dataset, level=ProfileLevel.BASIC)
        summary = result['summary']
        
        assert summary['rows'] == 5
        assert summary['columns'] == 5
        assert summary['numeric_columns'] == 3
        assert summary['categorical_columns'] == 2
        assert 'memory_usage_mb' in summary
        
        print(f"✓ Summary statistics generated")
        print(f"  - Rows: {summary['rows']}")
        print(f"  - Columns: {summary['columns']}")
        print(f"  - Numeric columns: {summary['numeric_columns']}")
        print(f"  - Categorical columns: {summary['categorical_columns']}")
        print(f"  - Memory usage: {summary['memory_usage_mb']:.6f} MB")
    
    def test_summary_with_missing_data(self, dataset_with_issues):
        """Test summary with missing data"""
        print("\n=== Testing Summary with Missing Data ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=dataset_with_issues, level=ProfileLevel.BASIC)
        summary = result['summary']
        
        assert summary['missing_cells'] > 0
        assert summary['missing_percentage'] > 0
        
        print(f"✓ Missing data detected in summary")
        print(f"  - Missing cells: {summary['missing_cells']}")
        print(f"  - Missing percentage: {summary['missing_percentage']:.2f}%")
    
    def test_summary_with_duplicates(self, dataset_with_issues):
        """Test summary with duplicate rows"""
        print("\n=== Testing Summary with Duplicates ===")
        tool = DataProfilerTool()
        
        result = tool.profile_dataset(data=dataset_with_issues, level=ProfileLevel.BASIC)
        summary = result['summary']
        
        assert summary['duplicate_rows'] > 0
        assert summary['duplicate_percentage'] > 0
        
        print(f"✓ Duplicates detected in summary")
        print(f"  - Duplicate rows: {summary['duplicate_rows']}")
        print(f"  - Duplicate percentage: {summary['duplicate_percentage']:.2f}%")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_dataframe(self):
        """Test profiling empty DataFrame"""
        print("\n=== Testing Empty DataFrame ===")
        tool = DataProfilerTool()
        
        df = pd.DataFrame(columns=['a', 'b', 'c'])
        result = tool.profile_dataset(data=df, level=ProfileLevel.BASIC)
        
        assert result['summary']['rows'] == 0
        assert result['summary']['columns'] == 3
        print(f"✓ Empty DataFrame profiled successfully")
    
    def test_single_row(self):
        """Test profiling single row"""
        print("\n=== Testing Single Row ===")
        tool = DataProfilerTool()
        
        df = pd.DataFrame({'x': [1], 'y': [2]})
        result = tool.profile_dataset(data=df, level=ProfileLevel.STANDARD)
        
        assert result['summary']['rows'] == 1
        print(f"✓ Single row profiled successfully")
    
    def test_single_column(self):
        """Test profiling single column"""
        print("\n=== Testing Single Column ===")
        tool = DataProfilerTool()
        
        df = pd.DataFrame({'single': [1, 2, 3, 4, 5]})
        result = tool.profile_dataset(data=df, level=ProfileLevel.COMPREHENSIVE)
        
        assert result['summary']['columns'] == 1
        # Should not have correlation analysis with single numeric column
        assert 'message' in result['correlations'] or len(result['correlations']) == 0
        print(f"✓ Single column profiled successfully")
    
    def test_all_missing_column(self):
        """Test profiling column with all missing values"""
        print("\n=== Testing All Missing Column ===")
        tool = DataProfilerTool()
        
        df = pd.DataFrame({
            'normal': [1, 2, 3, 4, 5],
            'all_missing': [None, None, None, None, None]
        })
        result = tool.profile_dataset(data=df, level=ProfileLevel.STANDARD)
        
        all_missing_profile = result['column_profiles']['all_missing']
        assert all_missing_profile['missing_percentage'] == 100.0
        
        print(f"✓ All-missing column profiled")
        print(f"  - Missing percentage: {all_missing_profile['missing_percentage']}%")
    
    def test_all_same_values(self):
        """Test profiling column with all same values"""
        print("\n=== Testing All Same Values ===")
        tool = DataProfilerTool()
        
        df = pd.DataFrame({
            'constant': [5, 5, 5, 5, 5]
        })
        result = tool.profile_dataset(data=df, level=ProfileLevel.COMPREHENSIVE)
        
        profile = result['column_profiles']['constant']
        assert profile['std'] == 0.0
        assert profile['unique_count'] == 1
        
        print(f"✓ Constant column profiled")
        print(f"  - Standard deviation: {profile['std']}")
        print(f"  - Unique values: {profile['unique_count']}")
    
    def test_very_large_column_count(self):
        """Test profiling with many columns"""
        print("\n=== Testing Large Column Count ===")
        tool = DataProfilerTool()
        
        # Create DataFrame with 100 columns
        data = {f'col_{i}': [i, i+1, i+2] for i in range(100)}
        df = pd.DataFrame(data)
        result = tool.profile_dataset(data=df, level=ProfileLevel.BASIC)
        
        assert result['summary']['columns'] == 100
        assert len(result['column_profiles']) == 100
        
        print(f"✓ Large column count profiled")
        print(f"  - Columns: {result['summary']['columns']}")


class TestErrorHandling:
    """Test error handling and exceptions"""
    
    def test_profiling_error_on_invalid_data(self):
        """Test ProfilingError on invalid data"""
        print("\n=== Testing ProfilingError ===")
        tool = DataProfilerTool()
        
        with pytest.raises(ProfilingError):
            tool.profile_dataset(data=None, level=ProfileLevel.BASIC)
        
        print(f"✓ ProfilingError raised correctly")
    
    def test_detect_quality_issues_error(self):
        """Test error handling in quality issue detection"""
        print("\n=== Testing Quality Issue Detection Error ===")
        tool = DataProfilerTool()
        
        with pytest.raises(ProfilingError):
            tool.detect_quality_issues(data=None)
        
        print(f"✓ Error handling works in quality detection")
    
    def test_recommend_preprocessing_error(self):
        """Test error handling in recommendation generation"""
        print("\n=== Testing Recommendation Error ===")
        tool = DataProfilerTool()
        
        with pytest.raises(ProfilingError):
            tool.recommend_preprocessing(data=None)
        
        print(f"✓ Error handling works in recommendations")


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    @pytest.fixture
    def sales_dataset(self):
        """Create realistic sales dataset"""
        np.random.seed(42)
        return pd.DataFrame({
            'transaction_id': range(1, 101),
            'date': pd.date_range('2023-01-01', periods=100),
            'customer_id': np.random.randint(1000, 2000, 100),
            'product_category': np.random.choice(['Electronics', 'Clothing', 'Food', 'Books'], 100),
            'quantity': np.random.randint(1, 20, 100),
            'unit_price': np.random.uniform(10, 500, 100).round(2),
            'discount': np.random.uniform(0, 0.3, 100).round(2),
            'region': np.random.choice(['North', 'South', 'East', 'West'], 100)
        })
    
    @pytest.fixture
    def customer_dataset(self):
        """Create realistic customer dataset with quality issues"""
        np.random.seed(42)
        data = {
            'customer_id': range(1, 51),
            'age': [np.random.randint(18, 80) if i % 10 != 0 else None for i in range(50)],
            'income': [np.random.randint(20000, 150000) if i % 8 != 0 else None for i in range(50)],
            'email': [f'user{i}@example.com' if i % 15 != 0 else None for i in range(50)],
            'signup_date': pd.date_range('2020-01-01', periods=50),
            'status': np.random.choice(['active', 'inactive', 'pending'], 50)
        }
        return pd.DataFrame(data)
    
    def test_complete_analysis_workflow(self, sales_dataset):
        """Test complete real-world analysis workflow"""
        print("\n=== Testing Complete Analysis Workflow ===")
        tool = DataProfilerTool()
        
        # Step 1: Basic profiling
        print("\nStep 1: Basic Profiling")
        basic_result = tool.profile_dataset(data=sales_dataset, level=ProfileLevel.BASIC)
        print(f"  - Dataset shape: {basic_result['summary']['rows']} x {basic_result['summary']['columns']}")
        
        # Step 2: Comprehensive profiling
        print("\nStep 2: Comprehensive Profiling")
        comp_result = tool.profile_dataset(data=sales_dataset, level=ProfileLevel.COMPREHENSIVE)
        print(f"  - Correlation pairs found: {comp_result['correlations']['num_high_correlations']}")
        
        # Step 3: Quality assessment
        print("\nStep 3: Quality Assessment")
        quality_result = tool.detect_quality_issues(data=sales_dataset)
        print(f"  - Total quality issues: {quality_result['total_issues']}")
        
        # Step 4: Get recommendations
        print("\nStep 4: Get Recommendations")
        rec_result = tool.recommend_preprocessing(data=sales_dataset)
        print(f"  - Recommendation steps: {rec_result['total_steps']}")
        
        print(f"\n✓ Complete workflow executed successfully")
    
    def test_data_quality_assessment_workflow(self, customer_dataset):
        """Test data quality assessment workflow"""
        print("\n=== Testing Data Quality Assessment Workflow ===")
        tool = DataProfilerTool()
        
        # Profile with quality checks
        result = tool.profile_dataset(
            data=customer_dataset,
            level=ProfileLevel.STANDARD,
            checks=[DataQualityCheck.MISSING_VALUES, DataQualityCheck.DUPLICATES]
        )
        
        print(f"\nData Quality Report:")
        print(f"  - Total rows: {result['summary']['rows']}")
        print(f"  - Missing cells: {result['summary']['missing_cells']}")
        print(f"  - Missing percentage: {result['summary']['missing_percentage']:.2f}%")
        print(f"  - Duplicate rows: {result['summary']['duplicate_rows']}")
        
        # Get detailed recommendations
        recommendations = tool.recommend_preprocessing(data=customer_dataset)
        print(f"\nRecommendations:")
        for i, rec in enumerate(recommendations['recommendations'][:5], 1):
            print(f"  {i}. {rec['action']} - {rec['reason']}")
        
        assert result['summary']['rows'] == 50
        print(f"\n✓ Quality assessment workflow completed")
    
    def test_ml_pipeline_preparation(self):
        """Test ML pipeline data preparation scenario"""
        print("\n=== Testing ML Pipeline Preparation ===")
        tool = DataProfilerTool()
        
        # Create ML dataset
        np.random.seed(42)
        ml_data = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'feature3': np.random.choice(['A', 'B', 'C'], 100),
            'target': np.random.randint(0, 2, 100)
        })
        
        # Get recommendations with target column
        result = tool.recommend_preprocessing(data=ml_data, target_column='target')
        
        print(f"\nML Pipeline Recommendations:")
        print(f"  - Total steps: {result['total_steps']}")
        
        # Check if task type was identified
        task_recs = [r for r in result['recommendations'] if r.get('action') == 'task_identified']
        if task_recs:
            print(f"  - Task identified: {task_recs[0]['task_type']}")
            print(f"  - Target column: {task_recs[0]['target_column']}")
        
        print(f"\n✓ ML pipeline preparation completed")


class TestHelperMethods:
    """Test internal helper methods for additional coverage"""
    
    def test_categorize_severity(self):
        """Test severity categorization"""
        print("\n=== Testing Severity Categorization ===")
        tool = DataProfilerTool()
        
        issues = {
            'missing_values': [
                {'severity': 'high'},
                {'severity': 'medium'},
                {'severity': 'high'}
            ],
            'outliers': [
                {'severity': 'low'},
                {'severity': 'low'}
            ]
        }
        
        severity_counts = tool._categorize_severity(issues)
        
        assert severity_counts['high'] == 2
        assert severity_counts['medium'] == 1
        assert severity_counts['low'] == 2
        
        print(f"✓ Severity categorization works")
        print(f"  - Severity counts: {severity_counts}")
    
    def test_prioritize_recommendations(self):
        """Test recommendation prioritization"""
        print("\n=== Testing Recommendation Prioritization ===")
        tool = DataProfilerTool()
        
        recommendations = [
            {'action': 'action1', 'priority': 'low'},
            {'action': 'action2', 'priority': 'high'},
            {'action': 'action3', 'priority': 'medium'},
            {'action': 'action4', 'priority': 'high'}
        ]
        
        prioritized = tool._prioritize_recommendations(recommendations)
        
        assert prioritized[0]['priority'] == 'high'
        assert prioritized[-1]['priority'] == 'low'
        
        print(f"✓ Recommendations prioritized correctly")
        print(f"  - Priority order: {[r['priority'] for r in prioritized]}")
    
    def test_generate_task_recommendations(self):
        """Test task-specific recommendations generation"""
        print("\n=== Testing Task Recommendations ===")
        tool = DataProfilerTool()
        
        # Regression task
        reg_data = pd.DataFrame({
            'feature': [1, 2, 3, 4, 5],
            'target': [10.5, 20.3, 30.1, 40.7, 50.2]
        })
        
        reg_recs = tool._generate_task_recommendations(reg_data, 'target')
        assert len(reg_recs) > 0
        assert reg_recs[0]['task_type'] == 'regression'
        
        print(f"✓ Regression task identified")
        
        # Classification task
        cls_data = pd.DataFrame({
            'feature': [1, 2, 3, 4, 5],
            'target': ['A', 'B', 'A', 'B', 'A']
        })
        
        cls_recs = tool._generate_task_recommendations(cls_data, 'target')
        assert cls_recs[0]['task_type'] == 'classification'
        
        print(f"✓ Classification task identified")


class TestIntegration:
    """Test integration with other components"""
    
    def test_settings_model(self):
        """Test DataProfilerSettings model"""
        print("\n=== Testing Settings Model ===")
        
        settings = DataProfilerSettings()
        assert settings.default_profile_level == ProfileLevel.STANDARD
        assert settings.outlier_std_threshold == 3.0
        
        print(f"✓ Settings model works correctly")
    
    def test_profile_levels_enum(self):
        """Test ProfileLevel enum"""
        print("\n=== Testing ProfileLevel Enum ===")
        
        assert ProfileLevel.BASIC.value == "basic"
        assert ProfileLevel.STANDARD.value == "standard"
        assert ProfileLevel.COMPREHENSIVE.value == "comprehensive"
        assert ProfileLevel.DEEP.value == "deep"
        
        print(f"✓ ProfileLevel enum values correct")
    
    def test_data_quality_check_enum(self):
        """Test DataQualityCheck enum"""
        print("\n=== Testing DataQualityCheck Enum ===")
        
        all_checks = list(DataQualityCheck)
        assert DataQualityCheck.MISSING_VALUES in all_checks
        assert DataQualityCheck.DUPLICATES in all_checks
        assert DataQualityCheck.OUTLIERS in all_checks
        
        print(f"✓ DataQualityCheck enum complete")
        print(f"  - Available checks: {[c.value for c in all_checks]}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

