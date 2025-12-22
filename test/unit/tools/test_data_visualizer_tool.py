"""
Comprehensive tests for DataVisualizerTool

Tests real functionality without mocks to verify actual behavior and output.
Includes debug output for manual verification of tool functionality.

Run with: poetry run pytest test/test_data_visualizer_tool.py -v -s
Coverage: poetry run python test/run_visualizer_coverage.py
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import pandas as pd
import numpy as np

from aiecs.tools.statistics.data_visualizer_tool import (
    DataVisualizerTool,
    ChartType,
    VisualizationStyle,
    DataVisualizerSettings,
    DataVisualizerError,
    VisualizationError
)


class TestDataVisualizerToolInitialization:
    """Test DataVisualizerTool initialization and configuration"""
    
    def test_default_initialization(self):
        """Test tool initialization with default settings"""
        print("\n=== Testing Default Initialization ===")
        tool = DataVisualizerTool()
        
        assert tool is not None
        assert tool.settings.default_style == VisualizationStyle.STATIC
        assert tool.settings.default_dpi == 100
        assert tool.settings.enable_auto_recommendation is True
        
        print(f"✓ Tool initialized with default settings")
        print(f"  - Default style: {tool.settings.default_style}")
        print(f"  - Default DPI: {tool.settings.default_dpi}")
        print(f"  - Auto recommendation: {tool.settings.enable_auto_recommendation}")
    
    def test_custom_configuration(self):
        """Test tool initialization with custom configuration"""
        print("\n=== Testing Custom Configuration ===")
        config = {
            'default_style': VisualizationStyle.INTERACTIVE,
            'default_dpi': 150,
            'enable_auto_recommendation': False
        }
        tool = DataVisualizerTool(config=config)
        
        assert tool.settings.default_style == VisualizationStyle.INTERACTIVE
        assert tool.settings.default_dpi == 150
        assert tool.settings.enable_auto_recommendation is False
        
        print(f"✓ Tool initialized with custom settings")
        print(f"  - Style: {tool.settings.default_style}")
        print(f"  - DPI: {tool.settings.default_dpi}")
    
    def test_invalid_configuration(self):
        """Test initialization with invalid configuration"""
        print("\n=== Testing Invalid Configuration ===")
        
        with pytest.raises(ValueError) as exc_info:
            DataVisualizerTool(config={'default_dpi': 'invalid'})
        
        assert "Invalid settings" in str(exc_info.value)
        print(f"✓ Correctly raised ValueError for invalid config")
    
    def test_external_tools_initialization(self):
        """Test external tools initialization"""
        print("\n=== Testing External Tools Initialization ===")
        tool = DataVisualizerTool()
        
        assert hasattr(tool, 'external_tools')
        assert 'chart' in tool.external_tools
        
        print(f"✓ External tools initialized")
        print(f"  - ChartTool available: {tool.external_tools['chart'] is not None}")


class TestVisualize:
    """Test visualization functionality"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for visualization"""
        np.random.seed(42)
        return pd.DataFrame({
            'x': np.linspace(0, 10, 50),
            'y': np.linspace(0, 10, 50) + np.random.normal(0, 1, 50),
            'category': np.random.choice(['A', 'B', 'C'], 50),
            'value': np.random.randn(50) * 10 + 50
        })
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup is handled by OS temp cleanup
    
    def test_visualize_auto_chart_type(self, sample_data, temp_output_dir):
        """Test visualization with auto chart type"""
        print("\n=== Testing Visualize - Auto Chart Type ===")
        tool = DataVisualizerTool()
        
        result = tool.visualize(
            data=sample_data,
            chart_type=ChartType.AUTO,
            x='x',
            y='y',
            output_path=os.path.join(temp_output_dir, 'auto_chart.png')
        )
        
        assert 'chart_info' in result
        assert 'chart_type' in result
        assert 'recommendation_reason' in result
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Auto chart type visualization created")
        print(f"  - Chart type: {result['chart_type']}")
        print(f"  - Reason: {result['recommendation_reason']}")
        print(f"  - Output: {result['output_path']}")
    
    def test_visualize_histogram(self, sample_data, temp_output_dir):
        """Test histogram visualization"""
        print("\n=== Testing Visualize - Histogram ===")
        tool = DataVisualizerTool()
        
        result = tool.visualize(
            data=sample_data,
            chart_type=ChartType.HISTOGRAM,
            x='value',
            title="Value Distribution",
            output_path=os.path.join(temp_output_dir, 'histogram.png')
        )
        
        assert result['chart_type'] == ChartType.HISTOGRAM.value
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Histogram created")
        print(f"  - Output: {result['output_path']}")
    
    def test_visualize_scatter(self, sample_data, temp_output_dir):
        """Test scatter plot visualization"""
        print("\n=== Testing Visualize - Scatter ===")
        tool = DataVisualizerTool()
        
        result = tool.visualize(
            data=sample_data,
            chart_type=ChartType.SCATTER,
            x='x',
            y='y',
            title="Scatter Plot",
            output_path=os.path.join(temp_output_dir, 'scatter.png')
        )
        
        assert result['chart_type'] == ChartType.SCATTER.value
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Scatter plot created")
    
    def test_visualize_bar(self, sample_data, temp_output_dir):
        """Test bar chart visualization"""
        print("\n=== Testing Visualize - Bar Chart ===")
        tool = DataVisualizerTool()
        
        result = tool.visualize(
            data=sample_data,
            chart_type=ChartType.BAR,
            x='category',
            y='value',
            title="Bar Chart",
            output_path=os.path.join(temp_output_dir, 'bar.png')
        )
        
        assert result['chart_type'] == ChartType.BAR.value
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Bar chart created")
    
    def test_visualize_box(self, sample_data, temp_output_dir):
        """Test box plot visualization"""
        print("\n=== Testing Visualize - Box Plot ===")
        tool = DataVisualizerTool()
        
        result = tool.visualize(
            data=sample_data,
            chart_type=ChartType.BOX,
            y='value',
            title="Box Plot",
            output_path=os.path.join(temp_output_dir, 'box.png')
        )
        
        assert result['chart_type'] == ChartType.BOX.value
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Box plot created")
    
    def test_visualize_correlation_matrix(self, sample_data, temp_output_dir):
        """Test correlation matrix visualization"""
        print("\n=== Testing Visualize - Correlation Matrix ===")
        tool = DataVisualizerTool()
        
        result = tool.visualize(
            data=sample_data,
            chart_type=ChartType.CORRELATION_MATRIX,
            title="Correlation Matrix",
            output_path=os.path.join(temp_output_dir, 'corr_matrix.png')
        )
        
        assert result['chart_type'] == ChartType.CORRELATION_MATRIX.value
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Correlation matrix created")
    
    def test_visualize_with_dict_input(self, temp_output_dir):
        """Test visualization with dict input"""
        print("\n=== Testing Visualize - Dict Input ===")
        tool = DataVisualizerTool()
        
        data = {'x': 1, 'y': 2, 'z': 3}
        result = tool.visualize(
            data=data,
            chart_type=ChartType.BAR,
            output_path=os.path.join(temp_output_dir, 'dict_chart.png')
        )
        
        assert 'chart_info' in result
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Dict input handled")
    
    def test_visualize_with_list_input(self, temp_output_dir):
        """Test visualization with list input"""
        print("\n=== Testing Visualize - List Input ===")
        tool = DataVisualizerTool()
        
        data = [
            {'x': 1, 'y': 10},
            {'x': 2, 'y': 20},
            {'x': 3, 'y': 30}
        ]
        result = tool.visualize(
            data=data,
            chart_type=ChartType.SCATTER,
            x='x',
            y='y',
            output_path=os.path.join(temp_output_dir, 'list_chart.png')
        )
        
        assert 'chart_info' in result
        assert os.path.exists(result['output_path'])
        
        print(f"✓ List input handled")
    
    def test_visualize_auto_output_path(self, sample_data):
        """Test visualization with auto-generated output path"""
        print("\n=== Testing Visualize - Auto Output Path ===")
        tool = DataVisualizerTool()
        
        result = tool.visualize(
            data=sample_data,
            chart_type=ChartType.HISTOGRAM,
            x='value'
        )
        
        assert 'output_path' in result
        assert result['output_path'] is not None
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Auto output path generated")
        print(f"  - Path: {result['output_path']}")


class TestAutoVisualizeDataset:
    """Test auto visualization functionality"""
    
    @pytest.fixture
    def dataset(self):
        """Create dataset for auto visualization"""
        np.random.seed(42)
        return pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100) * 10 + 50,
            'feature3': np.random.randn(100) * 5 + 25,
            'feature4': np.random.randn(100) * 2 + 10,
            'category': np.random.choice(['A', 'B', 'C'], 100)
        })
    
    def test_auto_visualize_default(self, dataset):
        """Test auto visualization with default settings"""
        print("\n=== Testing Auto Visualize - Default ===")
        tool = DataVisualizerTool()
        
        result = tool.auto_visualize_dataset(data=dataset)
        
        assert 'generated_charts' in result
        assert 'total_charts' in result
        assert 'focus_areas' in result
        assert result['total_charts'] > 0
        
        print(f"✓ Auto visualization completed")
        print(f"  - Total charts: {result['total_charts']}")
        print(f"  - Focus areas: {result['focus_areas']}")
    
    def test_auto_visualize_limited_charts(self, dataset):
        """Test auto visualization with max_charts limit"""
        print("\n=== Testing Auto Visualize - Limited Charts ===")
        tool = DataVisualizerTool()
        
        result = tool.auto_visualize_dataset(data=dataset, max_charts=3)
        
        assert result['total_charts'] <= 3
        
        print(f"✓ Limited auto visualization completed")
        print(f"  - Total charts: {result['total_charts']}")
    
    def test_auto_visualize_distributions_only(self, dataset):
        """Test auto visualization focusing on distributions"""
        print("\n=== Testing Auto Visualize - Distributions Only ===")
        tool = DataVisualizerTool()
        
        result = tool.auto_visualize_dataset(
            data=dataset,
            focus_areas=['distributions']
        )
        
        assert 'generated_charts' in result
        assert 'distributions' in result['focus_areas']
        
        print(f"✓ Distribution-focused visualization completed")
        print(f"  - Charts generated: {result['total_charts']}")
    
    def test_auto_visualize_correlations_only(self, dataset):
        """Test auto visualization focusing on correlations"""
        print("\n=== Testing Auto Visualize - Correlations Only ===")
        tool = DataVisualizerTool()
        
        result = tool.auto_visualize_dataset(
            data=dataset,
            focus_areas=['correlations']
        )
        
        assert 'correlations' in result['focus_areas']
        
        print(f"✓ Correlation-focused visualization completed")
    
    def test_auto_visualize_outliers_only(self, dataset):
        """Test auto visualization focusing on outliers"""
        print("\n=== Testing Auto Visualize - Outliers Only ===")
        tool = DataVisualizerTool()
        
        result = tool.auto_visualize_dataset(
            data=dataset,
            focus_areas=['outliers']
        )
        
        assert 'outliers' in result['focus_areas']
        
        print(f"✓ Outlier-focused visualization completed")
    
    def test_auto_visualize_multiple_focus_areas(self, dataset):
        """Test auto visualization with multiple focus areas"""
        print("\n=== Testing Auto Visualize - Multiple Focus Areas ===")
        tool = DataVisualizerTool()
        
        result = tool.auto_visualize_dataset(
            data=dataset,
            focus_areas=['distributions', 'correlations'],
            max_charts=10
        )
        
        assert result['total_charts'] > 0
        assert len(result['focus_areas']) == 2
        
        print(f"✓ Multi-focus auto visualization completed")
        print(f"  - Total charts: {result['total_charts']}")


class TestRecommendChartType:
    """Test chart type recommendation functionality"""
    
    def test_recommend_two_numeric_columns(self):
        """Test recommendation for two numeric columns"""
        print("\n=== Testing Recommend - Two Numeric ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({
            'x': [1, 2, 3, 4, 5],
            'y': [10, 20, 30, 40, 50]
        })
        
        result = tool.recommend_chart_type(data=data, x='x', y='y')
        
        assert 'recommended_chart' in result
        assert 'reason' in result
        assert result['recommended_chart'] == ChartType.SCATTER.value
        
        print(f"✓ Recommendation: {result['recommended_chart']}")
        print(f"  - Reason: {result['reason']}")
    
    def test_recommend_single_numeric(self):
        """Test recommendation for single numeric column"""
        print("\n=== Testing Recommend - Single Numeric ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({'values': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
        
        result = tool.recommend_chart_type(data=data, x='values')
        
        # When x is specified and y is None, should recommend histogram
        assert result['recommended_chart'] in [ChartType.HISTOGRAM.value, ChartType.BAR.value]
        
        print(f"✓ Recommendation: {result['recommended_chart']}")
    
    def test_recommend_multiple_numeric_no_xy(self):
        """Test recommendation with multiple numeric columns but no x/y specified"""
        print("\n=== Testing Recommend - Multiple Numeric No XY ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({
            'a': [1, 2, 3],
            'b': [4, 5, 6],
            'c': [7, 8, 9]
        })
        
        result = tool.recommend_chart_type(data=data)
        
        assert result['recommended_chart'] == ChartType.CORRELATION_MATRIX.value
        
        print(f"✓ Recommendation: {result['recommended_chart']}")
    
    def test_recommend_categorical_data(self):
        """Test recommendation for categorical data"""
        print("\n=== Testing Recommend - Categorical ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({'category': ['A', 'B', 'C', 'D', 'E']})
        
        result = tool.recommend_chart_type(data=data)
        
        assert result['recommended_chart'] == ChartType.BAR.value
        
        print(f"✓ Recommendation: {result['recommended_chart']}")
    
    def test_recommend_mixed_types(self):
        """Test recommendation for mixed data types"""
        print("\n=== Testing Recommend - Mixed Types ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({
            'category': ['A', 'B', 'C'],
            'value': [10, 20, 30]
        })
        
        result = tool.recommend_chart_type(data=data, x='category', y='value')
        
        assert result['recommended_chart'] == ChartType.BAR.value
        
        print(f"✓ Recommendation: {result['recommended_chart']}")
    
    def test_recommend_time_series(self):
        """Test recommendation for time series data"""
        print("\n=== Testing Recommend - Time Series ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=10),
            'value': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        })
        
        # Convert date to numeric for the test
        data['date_numeric'] = (data['date'] - data['date'].min()).dt.days
        
        result = tool.recommend_chart_type(data=data, x='date_numeric', y='value')
        
        assert 'recommended_chart' in result
        
        print(f"✓ Recommendation: {result['recommended_chart']}")


class TestDataConversion:
    """Test data conversion functionality"""
    
    def test_dataframe_input(self):
        """Test with DataFrame input"""
        print("\n=== Testing DataFrame Input ===")
        tool = DataVisualizerTool()
        
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        converted = tool._to_dataframe(df)
        
        assert isinstance(converted, pd.DataFrame)
        assert converted.equals(df)
        
        print(f"✓ DataFrame input handled")
    
    def test_dict_input(self):
        """Test with dictionary input"""
        print("\n=== Testing Dict Input ===")
        tool = DataVisualizerTool()
        
        data = {'col1': 1, 'col2': 2, 'col3': 3}
        converted = tool._to_dataframe(data)
        
        assert isinstance(converted, pd.DataFrame)
        assert len(converted) == 1
        
        print(f"✓ Dict input converted")
    
    def test_list_input(self):
        """Test with list input"""
        print("\n=== Testing List Input ===")
        tool = DataVisualizerTool()
        
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
        tool = DataVisualizerTool()
        
        with pytest.raises(VisualizationError) as exc_info:
            tool._to_dataframe("invalid_data")
        
        assert "Unsupported data type" in str(exc_info.value)
        print(f"✓ Correctly raised VisualizationError")


class TestErrorHandling:
    """Test error handling and exceptions"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
    
    def test_visualization_error_on_invalid_data(self):
        """Test VisualizationError on invalid data"""
        print("\n=== Testing VisualizationError ===")
        tool = DataVisualizerTool()
        
        with pytest.raises(VisualizationError):
            tool.visualize(data=None, chart_type=ChartType.HISTOGRAM)
        
        print(f"✓ VisualizationError raised correctly")
    
    def test_missing_column_error(self, temp_output_dir):
        """Test error when specified column doesn't exist"""
        print("\n=== Testing Missing Column Error ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({'a': [1, 2, 3]})
        
        with pytest.raises(VisualizationError):
            tool.visualize(
                data=data,
                chart_type=ChartType.HISTOGRAM,
                x='nonexistent_column',
                output_path=os.path.join(temp_output_dir, 'error.png')
            )
        
        print(f"✓ Missing column error handled")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
    
    def test_empty_dataframe(self):
        """Test visualization with empty DataFrame"""
        print("\n=== Testing Empty DataFrame ===")
        tool = DataVisualizerTool()
        
        df = pd.DataFrame(columns=['a', 'b', 'c'])
        
        # Empty DataFrame should raise VisualizationError or handle gracefully
        try:
            result = tool.visualize(data=df, chart_type=ChartType.HISTOGRAM, x='a')
            # If it doesn't raise, check that result exists
            assert 'chart_info' in result
            print(f"✓ Empty DataFrame handled gracefully")
        except VisualizationError:
            print(f"✓ Empty DataFrame raised VisualizationError as expected")
    
    def test_single_row_dataframe(self, temp_output_dir):
        """Test visualization with single row"""
        print("\n=== Testing Single Row DataFrame ===")
        tool = DataVisualizerTool()
        
        df = pd.DataFrame({'x': [1], 'y': [2]})
        
        # Should handle gracefully
        result = tool.visualize(
            data=df,
            chart_type=ChartType.BAR,
            x='x',
            y='y',
            output_path=os.path.join(temp_output_dir, 'single_row.png')
        )
        
        assert 'chart_info' in result
        print(f"✓ Single row DataFrame handled")
    
    def test_all_null_column(self, temp_output_dir):
        """Test visualization with all-null column"""
        print("\n=== Testing All-Null Column ===")
        tool = DataVisualizerTool()
        
        df = pd.DataFrame({
            'normal': [1, 2, 3, 4, 5],
            'all_null': [None, None, None, None, None]
        })
        
        # Should skip or handle null column
        result = tool.visualize(
            data=df,
            chart_type=ChartType.HISTOGRAM,
            x='normal',
            output_path=os.path.join(temp_output_dir, 'all_null.png')
        )
        
        assert 'chart_info' in result
        print(f"✓ All-null column handled")
    
    def test_no_numeric_columns(self):
        """Test auto visualization with no numeric columns"""
        print("\n=== Testing No Numeric Columns ===")
        tool = DataVisualizerTool()
        
        df = pd.DataFrame({'cat1': ['A', 'B', 'C'], 'cat2': ['X', 'Y', 'Z']})
        
        result = tool.auto_visualize_dataset(data=df, focus_areas=['distributions'])
        
        # Should handle gracefully
        assert 'generated_charts' in result
        print(f"✓ No numeric columns handled")


class TestChartTypeRecommendation:
    """Test internal chart type recommendation logic"""
    
    def test_recommend_with_time_keywords(self):
        """Test recommendation with time-related column names"""
        print("\n=== Testing Recommend - Time Keywords ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({
            'timestamp': [1, 2, 3, 4, 5],
            'value': [10, 20, 30, 40, 50]
        })
        
        chart_type, reason = tool._recommend_chart_type(data, x='timestamp', y='value')
        
        # Should recognize time-related name
        assert chart_type in [ChartType.TIME_SERIES, ChartType.SCATTER]
        
        print(f"✓ Time keyword recognized")
        print(f"  - Chart type: {chart_type.value}")
        print(f"  - Reason: {reason}")
    
    def test_recommend_both_categorical(self):
        """Test recommendation for two categorical variables"""
        print("\n=== Testing Recommend - Both Categorical ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({
            'cat1': ['A', 'B', 'C'],
            'cat2': ['X', 'Y', 'Z']
        })
        
        chart_type, reason = tool._recommend_chart_type(data, x='cat1', y='cat2')
        
        assert chart_type == ChartType.BAR
        
        print(f"✓ Both categorical recognized")
        print(f"  - Chart type: {chart_type.value}")


class TestIntegration:
    """Test integration with other components"""
    
    def test_settings_model(self):
        """Test DataVisualizerSettings model"""
        print("\n=== Testing Settings Model ===")
        
        settings = DataVisualizerSettings()
        assert settings.default_style == VisualizationStyle.STATIC
        assert settings.default_dpi == 100
        
        print(f"✓ Settings model works correctly")
    
    def test_chart_type_enum(self):
        """Test ChartType enum"""
        print("\n=== Testing ChartType Enum ===")
        
        assert ChartType.LINE.value == "line"
        assert ChartType.BAR.value == "bar"
        assert ChartType.AUTO.value == "auto"
        
        print(f"✓ ChartType enum values correct")
    
    def test_visualization_style_enum(self):
        """Test VisualizationStyle enum"""
        print("\n=== Testing VisualizationStyle Enum ===")
        
        all_styles = list(VisualizationStyle)
        assert VisualizationStyle.STATIC in all_styles
        assert VisualizationStyle.INTERACTIVE in all_styles
        
        print(f"✓ VisualizationStyle enum complete")
        print(f"  - Available styles: {[s.value for s in all_styles]}")


class TestMatplotlibFallback:
    """Test matplotlib fallback functionality"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
    
    def test_matplotlib_histogram(self, temp_output_dir):
        """Test matplotlib fallback for histogram"""
        print("\n=== Testing Matplotlib Fallback - Histogram ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({'values': np.random.randn(100)})
        result = tool._create_chart_matplotlib(
            df=data,
            chart_type=ChartType.HISTOGRAM,
            x='values',
            y=None,
            hue=None,
            title="Test Histogram",
            output_path=os.path.join(temp_output_dir, 'mpl_hist.png')
        )
        
        assert result['status'] == 'success'
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Matplotlib histogram created")
    
    def test_matplotlib_scatter(self, temp_output_dir):
        """Test matplotlib fallback for scatter plot"""
        print("\n=== Testing Matplotlib Fallback - Scatter ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({'x': [1, 2, 3, 4, 5], 'y': [2, 4, 6, 8, 10]})
        result = tool._create_chart_matplotlib(
            df=data,
            chart_type=ChartType.SCATTER,
            x='x',
            y='y',
            hue=None,
            title="Test Scatter",
            output_path=os.path.join(temp_output_dir, 'mpl_scatter.png')
        )
        
        assert result['status'] == 'success'
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Matplotlib scatter plot created")
    
    def test_matplotlib_default_fallback(self, temp_output_dir):
        """Test matplotlib default chart fallback"""
        print("\n=== Testing Matplotlib Fallback - Default ===")
        tool = DataVisualizerTool()
        
        data = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
        result = tool._create_chart_matplotlib(
            df=data,
            chart_type=ChartType.LINE,  # Not explicitly handled, should use default
            x='x',
            y='y',
            hue=None,
            title="Test Default",
            output_path=os.path.join(temp_output_dir, 'mpl_default.png')
        )
        
        assert result['status'] == 'success'
        assert os.path.exists(result['output_path'])
        
        print(f"✓ Matplotlib default chart created")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

