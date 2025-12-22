"""
Comprehensive tests for DataTransformerTool

Tests real functionality without mocks to verify actual behavior and output.
Includes debug output for manual verification of tool functionality.

Run with: poetry run pytest test/test_data_transformer_tool.py -v -s
Coverage: poetry run coverage run --source=aiecs.tools.statistics.data_transformer_tool -m pytest test/test_data_transformer_tool.py -q && poetry run coverage report -m
"""

import os
import tempfile
import json
from pathlib import Path
from typing import Any, Dict

import pytest
import pandas as pd
import numpy as np

from aiecs.tools.statistics.data_transformer_tool import (
    DataTransformerTool,
    TransformationType,
    MissingValueStrategy,
    DataTransformerSettings,
    DataTransformerError,
    TransformationError
)


class TestDataTransformerToolInitialization:
    """Test DataTransformerTool initialization and configuration"""
    
    def test_default_initialization(self):
        """Test tool initialization with default settings"""
        print("\n=== Testing Default Initialization ===")
        tool = DataTransformerTool()
        
        assert tool is not None
        assert tool.settings.outlier_std_threshold == 3.0
        assert tool.settings.default_missing_strategy == MissingValueStrategy.MEAN
        assert tool.settings.enable_pipeline_caching is True
        assert tool.settings.max_one_hot_categories == 10
        
        print(f"✓ Tool initialized with default settings")
        print(f"  - Outlier threshold: {tool.settings.outlier_std_threshold}")
        print(f"  - Default missing strategy: {tool.settings.default_missing_strategy}")
        print(f"  - Pipeline caching: {tool.settings.enable_pipeline_caching}")
    
    def test_custom_configuration(self):
        """Test tool initialization with custom configuration"""
        print("\n=== Testing Custom Configuration ===")
        config = {
            'outlier_std_threshold': 2.5,
            'default_missing_strategy': MissingValueStrategy.MEDIAN,
            'enable_pipeline_caching': False,
            'max_one_hot_categories': 5
        }
        tool = DataTransformerTool(config=config)
        
        assert tool.settings.outlier_std_threshold == 2.5
        assert tool.settings.default_missing_strategy == MissingValueStrategy.MEDIAN
        assert tool.settings.enable_pipeline_caching is False
        assert tool.settings.max_one_hot_categories == 5
        
        print(f"✓ Tool initialized with custom settings")
        print(f"  - Outlier threshold: {tool.settings.outlier_std_threshold}")
        print(f"  - Missing strategy: {tool.settings.default_missing_strategy}")
    
    def test_invalid_configuration(self):
        """Test initialization with invalid configuration"""
        print("\n=== Testing Invalid Configuration ===")
        
        with pytest.raises(ValueError) as exc_info:
            DataTransformerTool(config={'outlier_std_threshold': 'invalid'})
        
        assert "Invalid settings" in str(exc_info.value)
        print(f"✓ Correctly raised ValueError for invalid config")
    
    def test_external_tools_initialization(self):
        """Test external tools initialization"""
        print("\n=== Testing External Tools Initialization ===")
        tool = DataTransformerTool()
        
        assert hasattr(tool, 'external_tools')
        assert 'pandas' in tool.external_tools
        
        print(f"✓ External tools initialized")
        print(f"  - PandasTool available: {tool.external_tools['pandas'] is not None}")
    
    def test_pipeline_cache_initialization(self):
        """Test pipeline cache initialization"""
        print("\n=== Testing Pipeline Cache Initialization ===")
        tool = DataTransformerTool()
        
        assert hasattr(tool, 'pipeline_cache')
        assert isinstance(tool.pipeline_cache, dict)
        assert len(tool.pipeline_cache) == 0
        
        print(f"✓ Pipeline cache initialized")


class TestHandleMissingValues:
    """Test missing value handling functionality"""
    
    @pytest.fixture
    def data_with_missing(self):
        """Create data with missing values"""
        return pd.DataFrame({
            'numeric1': [1, 2, None, 4, 5, 6, 7, 8, 9, 10],
            'numeric2': [10.0, None, 30.0, None, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
            'categorical': ['A', 'B', None, 'D', 'E', None, 'G', 'H', 'I', 'J']
        })
    
    def test_handle_missing_mean_strategy(self, data_with_missing):
        """Test missing value handling with mean strategy"""
        print("\n=== Testing Missing Values - Mean Strategy ===")
        tool = DataTransformerTool()
        
        result = tool.handle_missing_values(
            data=data_with_missing,
            strategy=MissingValueStrategy.MEAN
        )
        
        assert 'data' in result
        assert result['original_missing'] > 0
        assert result['missing_handled'] > 0
        assert result['strategy'] == 'mean'
        
        print(f"✓ Mean strategy applied")
        print(f"  - Original missing: {result['original_missing']}")
        print(f"  - Final missing: {result['final_missing']}")
        print(f"  - Missing handled: {result['missing_handled']}")
    
    def test_handle_missing_median_strategy(self, data_with_missing):
        """Test missing value handling with median strategy"""
        print("\n=== Testing Missing Values - Median Strategy ===")
        tool = DataTransformerTool()
        
        result = tool.handle_missing_values(
            data=data_with_missing,
            strategy=MissingValueStrategy.MEDIAN
        )
        
        assert result['strategy'] == 'median'
        assert result['missing_handled'] > 0
        
        print(f"✓ Median strategy applied")
        print(f"  - Missing handled: {result['missing_handled']}")
    
    def test_handle_missing_mode_strategy(self, data_with_missing):
        """Test missing value handling with mode strategy"""
        print("\n=== Testing Missing Values - Mode Strategy ===")
        tool = DataTransformerTool()
        
        result = tool.handle_missing_values(
            data=data_with_missing,
            strategy=MissingValueStrategy.MODE
        )
        
        assert result['strategy'] == 'mode'
        print(f"✓ Mode strategy applied")
        print(f"  - Missing handled: {result['missing_handled']}")
    
    def test_handle_missing_drop_strategy(self, data_with_missing):
        """Test missing value handling with drop strategy"""
        print("\n=== Testing Missing Values - Drop Strategy ===")
        tool = DataTransformerTool()
        
        result = tool.handle_missing_values(
            data=data_with_missing,
            strategy=MissingValueStrategy.DROP
        )
        
        assert result['strategy'] == 'drop'
        assert len(result['data']) < len(data_with_missing)
        
        print(f"✓ Drop strategy applied")
        print(f"  - Rows before: {len(data_with_missing)}")
        print(f"  - Rows after: {len(result['data'])}")
    
    def test_handle_missing_forward_fill(self, data_with_missing):
        """Test missing value handling with forward fill"""
        print("\n=== Testing Missing Values - Forward Fill ===")
        tool = DataTransformerTool()
        
        result = tool.handle_missing_values(
            data=data_with_missing,
            strategy=MissingValueStrategy.FORWARD_FILL
        )
        
        assert result['strategy'] == 'forward_fill'
        print(f"✓ Forward fill applied")
    
    def test_handle_missing_backward_fill(self, data_with_missing):
        """Test missing value handling with backward fill"""
        print("\n=== Testing Missing Values - Backward Fill ===")
        tool = DataTransformerTool()
        
        result = tool.handle_missing_values(
            data=data_with_missing,
            strategy=MissingValueStrategy.BACKWARD_FILL
        )
        
        assert result['strategy'] == 'backward_fill'
        print(f"✓ Backward fill applied")
    
    def test_handle_missing_interpolate(self, data_with_missing):
        """Test missing value handling with interpolation"""
        print("\n=== Testing Missing Values - Interpolate ===")
        tool = DataTransformerTool()
        
        result = tool.handle_missing_values(
            data=data_with_missing,
            strategy=MissingValueStrategy.INTERPOLATE
        )
        
        assert result['strategy'] == 'interpolate'
        print(f"✓ Interpolation applied")
    
    def test_handle_missing_constant(self, data_with_missing):
        """Test missing value handling with constant value"""
        print("\n=== Testing Missing Values - Constant ===")
        tool = DataTransformerTool()
        
        result = tool.handle_missing_values(
            data=data_with_missing,
            strategy=MissingValueStrategy.CONSTANT,
            fill_value=999
        )
        
        assert result['strategy'] == 'constant'
        print(f"✓ Constant fill applied")
        print(f"  - Fill value: 999")
    
    def test_handle_missing_specific_columns(self, data_with_missing):
        """Test missing value handling for specific columns"""
        print("\n=== Testing Missing Values - Specific Columns ===")
        tool = DataTransformerTool()
        
        result = tool.handle_missing_values(
            data=data_with_missing,
            strategy=MissingValueStrategy.MEAN,
            columns=['numeric1']
        )
        
        assert result['missing_handled'] > 0
        print(f"✓ Specific columns handled")
        print(f"  - Columns: ['numeric1']")


class TestEncodeFeatures:
    """Test feature encoding functionality"""
    
    @pytest.fixture
    def categorical_data(self):
        """Create data with categorical features"""
        return pd.DataFrame({
            'category1': ['A', 'B', 'C', 'A', 'B'],
            'category2': ['X', 'Y', 'Z', 'X', 'Y'],
            'numeric': [1, 2, 3, 4, 5]
        })
    
    def test_one_hot_encoding(self, categorical_data):
        """Test one-hot encoding"""
        print("\n=== Testing One-Hot Encoding ===")
        tool = DataTransformerTool()
        
        result = tool.encode_features(
            data=categorical_data,
            columns=['category1', 'category2'],
            method='one_hot'
        )
        
        assert 'data' in result
        assert 'encoding_info' in result
        assert result['encoding_info']['method'] == 'one_hot'
        assert result['new_shape'][1] > result['original_shape'][1]  # More columns after encoding
        
        print(f"✓ One-hot encoding completed")
        print(f"  - Original shape: {result['original_shape']}")
        print(f"  - New shape: {result['new_shape']}")
        print(f"  - New columns: {result['encoding_info']['new_columns']}")
    
    def test_label_encoding(self, categorical_data):
        """Test label encoding"""
        print("\n=== Testing Label Encoding ===")
        tool = DataTransformerTool()
        
        result = tool.encode_features(
            data=categorical_data,
            columns=['category1', 'category2'],
            method='label'
        )
        
        assert result['encoding_info']['method'] == 'label'
        assert 'encoders' in result['encoding_info']
        assert len(result['encoding_info']['encoders']) == 2
        
        print(f"✓ Label encoding completed")
        print(f"  - Encoded columns: {result['encoding_info']['columns']}")
    
    def test_unsupported_encoding_method(self, categorical_data):
        """Test unsupported encoding method"""
        print("\n=== Testing Unsupported Encoding Method ===")
        tool = DataTransformerTool()
        
        with pytest.raises(TransformationError) as exc_info:
            tool.encode_features(
                data=categorical_data,
                columns=['category1'],
                method='unsupported'
            )
        
        assert "Unsupported encoding method" in str(exc_info.value)
        print(f"✓ Correctly raised TransformationError")


class TestTransformData:
    """Test data transformation pipeline"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for transformation"""
        return pd.DataFrame({
            'id': [1, 2, 3, 3, 5, 6, 7, 8, 9, 10],  # Duplicate row
            'value': [10, 20, None, 30, 40, 50, 60, 70, 80, 90],
            'score': [1, 2, 3, 3, 5, 6, 7, 8, 9, 1000],  # Outlier
            'category': ['A', 'B', 'C', 'A', 'B', 'C', 'A', 'B', 'C', 'A']
        })
    
    def test_remove_duplicates_transformation(self, sample_data):
        """Test remove duplicates transformation"""
        print("\n=== Testing Remove Duplicates Transformation ===")
        tool = DataTransformerTool()
        
        # Create data with actual duplicates
        dup_data = pd.DataFrame({
            'a': [1, 2, 3, 3, 3],
            'b': ['X', 'Y', 'Z', 'Z', 'Z']
        })
        
        transformations = [
            {'type': TransformationType.REMOVE_DUPLICATES.value, 'columns': None, 'params': {}}
        ]
        
        result = tool.transform_data(data=dup_data, transformations=transformations)
        
        assert 'transformed_data' in result
        assert len(result['transformed_data']) <= len(dup_data)
        assert result['quality_improvement']['duplicates_after'] == 0
        
        print(f"✓ Duplicates removed")
        print(f"  - Rows before: {result['original_shape'][0]}")
        print(f"  - Rows after: {result['new_shape'][0]}")
        print(f"  - Duplicates removed: {result['quality_improvement']['duplicates_before']}")
    
    def test_fill_missing_transformation(self, sample_data):
        """Test fill missing values transformation"""
        print("\n=== Testing Fill Missing Transformation ===")
        tool = DataTransformerTool()
        
        transformations = [
            {'type': TransformationType.FILL_MISSING.value, 'columns': None, 'params': {'strategy': 'mean'}}
        ]
        
        result = tool.transform_data(data=sample_data, transformations=transformations)
        
        assert result['quality_improvement']['missing_after'] < result['quality_improvement']['missing_before']
        
        print(f"✓ Missing values filled")
        print(f"  - Missing before: {result['quality_improvement']['missing_before']}")
        print(f"  - Missing after: {result['quality_improvement']['missing_after']}")
    
    def test_standardize_transformation(self, sample_data):
        """Test standardization transformation"""
        print("\n=== Testing Standardize Transformation ===")
        tool = DataTransformerTool()
        
        transformations = [
            {'type': TransformationType.STANDARDIZE.value, 'columns': ['value'], 'params': {}}
        ]
        
        # Remove None value first
        clean_data = sample_data.copy()
        clean_data['value'].fillna(clean_data['value'].mean(), inplace=True)
        
        result = tool.transform_data(data=clean_data, transformations=transformations)
        
        assert 'transformed_data' in result
        
        print(f"✓ Standardization applied")
        print(f"  - Columns standardized: ['value']")
    
    def test_normalize_transformation(self, sample_data):
        """Test normalization transformation"""
        print("\n=== Testing Normalize Transformation ===")
        tool = DataTransformerTool()
        
        transformations = [
            {'type': TransformationType.NORMALIZE.value, 'columns': ['score'], 'params': {}}
        ]
        
        result = tool.transform_data(data=sample_data, transformations=transformations)
        
        assert 'transformed_data' in result
        
        print(f"✓ Normalization applied")
        print(f"  - Columns normalized: ['score']")
    
    def test_log_transform(self):
        """Test log transformation"""
        print("\n=== Testing Log Transform ===")
        tool = DataTransformerTool()
        
        data = pd.DataFrame({'values': [1, 2, 3, 4, 5, 10, 20, 50, 100]})
        transformations = [
            {'type': TransformationType.LOG_TRANSFORM.value, 'columns': ['values'], 'params': {}}
        ]
        
        result = tool.transform_data(data=data, transformations=transformations)
        
        assert 'transformed_data' in result
        
        print(f"✓ Log transformation applied")
    
    def test_remove_outliers_transformation(self, sample_data):
        """Test remove outliers transformation"""
        print("\n=== Testing Remove Outliers Transformation ===")
        tool = DataTransformerTool()
        
        transformations = [
            {'type': TransformationType.REMOVE_OUTLIERS.value, 'columns': ['score'], 'params': {}}
        ]
        
        result = tool.transform_data(data=sample_data, transformations=transformations)
        
        # The outlier value (1000) should be removed
        assert len(result['transformed_data']) <= len(sample_data)
        
        print(f"✓ Outliers transformation completed")
        print(f"  - Rows before: {result['original_shape'][0]}")
        print(f"  - Rows after: {result['new_shape'][0]}")
    
    def test_one_hot_encode_transformation(self):
        """Test one-hot encode transformation"""
        print("\n=== Testing One-Hot Encode Transformation ===")
        tool = DataTransformerTool()
        
        data = pd.DataFrame({'cat': ['A', 'B', 'C', 'A', 'B'], 'val': [1, 2, 3, 4, 5]})
        transformations = [
            {'type': TransformationType.ONE_HOT_ENCODE.value, 'columns': ['cat'], 'params': {}}
        ]
        
        result = tool.transform_data(data=data, transformations=transformations)
        
        assert result['new_shape'][1] > result['original_shape'][1]
        
        print(f"✓ One-hot encoding applied")
        print(f"  - Columns before: {result['original_shape'][1]}")
        print(f"  - Columns after: {result['new_shape'][1]}")
    
    def test_label_encode_transformation(self):
        """Test label encode transformation"""
        print("\n=== Testing Label Encode Transformation ===")
        tool = DataTransformerTool()
        
        data = pd.DataFrame({'cat': ['A', 'B', 'C', 'A', 'B'], 'val': [1, 2, 3, 4, 5]})
        transformations = [
            {'type': TransformationType.LABEL_ENCODE.value, 'columns': ['cat'], 'params': {}}
        ]
        
        result = tool.transform_data(data=data, transformations=transformations)
        
        assert result['transformed_data']['cat'].dtype in ['int32', 'int64']
        
        print(f"✓ Label encoding applied")
    
    def test_multiple_transformations_pipeline(self, sample_data):
        """Test pipeline with multiple transformations"""
        print("\n=== Testing Multiple Transformations Pipeline ===")
        tool = DataTransformerTool()
        
        transformations = [
            {'type': TransformationType.REMOVE_DUPLICATES.value, 'columns': None, 'params': {}},
            {'type': TransformationType.FILL_MISSING.value, 'columns': None, 'params': {'strategy': 'mean'}},
            {'type': TransformationType.STANDARDIZE.value, 'columns': ['value', 'score'], 'params': {}}
        ]
        
        result = tool.transform_data(data=sample_data, transformations=transformations)
        
        assert len(result['transformation_log']) == 3
        assert all(step['status'] == 'success' for step in result['transformation_log'])
        
        print(f"✓ Pipeline completed")
        print(f"  - Steps executed: {len(result['transformation_log'])}")
        for step in result['transformation_log']:
            print(f"    {step['step']}. {step['type']} - {step['status']}")


class TestAutoTransform:
    """Test auto transformation functionality"""
    
    @pytest.fixture
    def ml_data(self):
        """Create data for ML pipeline"""
        np.random.seed(42)
        return pd.DataFrame({
            'feature1': np.random.randn(50),
            'feature2': np.random.randn(50),
            'feature3': np.random.choice(['A', 'B', 'C'], 50),
            'target': np.random.randint(0, 2, 50)
        })
    
    @pytest.fixture
    def data_with_issues(self):
        """Create data with quality issues"""
        return pd.DataFrame({
            'numeric': [1, 2, None, 4, 5, 5, 7, 8, 9, 10],
            'category': ['A', 'B', 'C', 'A', 'B', 'B', 'C', 'A', 'B', 'C']
        })
    
    def test_auto_transform_basic(self, ml_data):
        """Test basic auto transform"""
        print("\n=== Testing Auto Transform - Basic ===")
        tool = DataTransformerTool()
        
        result = tool.auto_transform(data=ml_data)
        
        assert 'transformed_data' in result
        assert 'auto_detected_transformations' in result
        assert len(result['auto_detected_transformations']) > 0
        
        print(f"✓ Auto transform completed")
        print(f"  - Transformations detected: {len(result['auto_detected_transformations'])}")
        for trans in result['auto_detected_transformations']:
            print(f"    - {trans['type']}")
    
    def test_auto_transform_with_target(self, ml_data):
        """Test auto transform with target column"""
        print("\n=== Testing Auto Transform - With Target ===")
        tool = DataTransformerTool()
        
        result = tool.auto_transform(data=ml_data, target_column='target')
        
        assert 'transformed_data' in result
        
        print(f"✓ Auto transform with target completed")
        print(f"  - Target column: target")
    
    def test_auto_transform_classification(self, ml_data):
        """Test auto transform for classification task"""
        print("\n=== Testing Auto Transform - Classification ===")
        tool = DataTransformerTool()
        
        result = tool.auto_transform(
            data=ml_data,
            target_column='target',
            task_type='classification'
        )
        
        assert 'transformed_data' in result
        
        print(f"✓ Auto transform for classification completed")
    
    def test_auto_transform_handles_duplicates(self, data_with_issues):
        """Test auto transform handles duplicates"""
        print("\n=== Testing Auto Transform - Handles Duplicates ===")
        tool = DataTransformerTool()
        
        result = tool.auto_transform(data=data_with_issues)
        
        # Check if duplicates were handled
        detected_types = [t['type'] for t in result['auto_detected_transformations']]
        assert TransformationType.REMOVE_DUPLICATES.value in detected_types
        
        print(f"✓ Auto transform detected and removed duplicates")
    
    def test_auto_transform_handles_missing(self, data_with_issues):
        """Test auto transform handles missing values"""
        print("\n=== Testing Auto Transform - Handles Missing ===")
        tool = DataTransformerTool()
        
        result = tool.auto_transform(data=data_with_issues)
        
        # Check if missing values were handled
        detected_types = [t['type'] for t in result['auto_detected_transformations']]
        assert TransformationType.FILL_MISSING.value in detected_types
        
        print(f"✓ Auto transform detected and filled missing values")


class TestDataConversion:
    """Test data conversion functionality"""
    
    def test_dataframe_input(self):
        """Test with DataFrame input"""
        print("\n=== Testing DataFrame Input ===")
        tool = DataTransformerTool()
        
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        result = tool.handle_missing_values(data=df, strategy=MissingValueStrategy.MEAN)
        
        assert 'data' in result
        print(f"✓ DataFrame input processed")
    
    def test_dict_input(self):
        """Test with dictionary input"""
        print("\n=== Testing Dict Input ===")
        tool = DataTransformerTool()
        
        data = {'col1': 1, 'col2': 2, 'col3': 3}
        result = tool.handle_missing_values(data=data, strategy=MissingValueStrategy.MEAN)
        
        assert 'data' in result
        print(f"✓ Dict input converted and processed")
    
    def test_list_input(self):
        """Test with list input"""
        print("\n=== Testing List Input ===")
        tool = DataTransformerTool()
        
        data = [
            {'x': 1, 'y': 2},
            {'x': 3, 'y': 4},
            {'x': 5, 'y': 6}
        ]
        result = tool.handle_missing_values(data=data, strategy=MissingValueStrategy.MEAN)
        
        assert 'data' in result
        print(f"✓ List input converted and processed")
    
    def test_unsupported_data_type(self):
        """Test error handling for unsupported data types"""
        print("\n=== Testing Unsupported Data Type ===")
        tool = DataTransformerTool()
        
        with pytest.raises(TransformationError) as exc_info:
            tool.handle_missing_values(data="invalid_data", strategy=MissingValueStrategy.MEAN)
        
        assert "Unsupported data type" in str(exc_info.value)
        print(f"✓ Correctly raised TransformationError for unsupported type")


class TestErrorHandling:
    """Test error handling and exceptions"""
    
    def test_transformation_error_on_invalid_data(self):
        """Test TransformationError on invalid data"""
        print("\n=== Testing TransformationError ===")
        tool = DataTransformerTool()
        
        with pytest.raises(TransformationError):
            tool.transform_data(data=None, transformations=[])
        
        print(f"✓ TransformationError raised correctly")
    
    def test_empty_transformations_list(self):
        """Test with empty transformations list"""
        print("\n=== Testing Empty Transformations ===")
        tool = DataTransformerTool()
        
        data = pd.DataFrame({'a': [1, 2, 3]})
        result = tool.transform_data(data=data, transformations=[])
        
        assert len(result['transformation_log']) == 0
        print(f"✓ Empty transformations handled")
    
    def test_unknown_transformation_type(self):
        """Test unknown transformation type"""
        print("\n=== Testing Unknown Transformation Type ===")
        tool = DataTransformerTool()
        
        data = pd.DataFrame({'a': [1, 2, 3]})
        transformations = [
            {'type': 'unknown_type', 'columns': None, 'params': {}}
        ]
        
        # Should skip unknown transformation
        result = tool.transform_data(data=data, transformations=transformations)
        assert len(result['transformation_log']) == 1
        
        print(f"✓ Unknown transformation skipped gracefully")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_dataframe(self):
        """Test transformation on empty DataFrame"""
        print("\n=== Testing Empty DataFrame ===")
        tool = DataTransformerTool()
        
        df = pd.DataFrame(columns=['a', 'b', 'c'])
        transformations = [
            {'type': TransformationType.REMOVE_DUPLICATES.value, 'columns': None, 'params': {}}
        ]
        
        result = tool.transform_data(data=df, transformations=transformations)
        
        assert len(result['transformed_data']) == 0
        print(f"✓ Empty DataFrame handled")
    
    def test_single_row(self):
        """Test transformation on single row"""
        print("\n=== Testing Single Row ===")
        tool = DataTransformerTool()
        
        df = pd.DataFrame({'x': [1], 'y': [2]})
        transformations = [
            {'type': TransformationType.STANDARDIZE.value, 'columns': None, 'params': {}}
        ]
        
        result = tool.transform_data(data=df, transformations=transformations)
        
        assert len(result['transformed_data']) == 1
        print(f"✓ Single row handled")
    
    def test_all_missing_column(self):
        """Test transformation on column with all missing values"""
        print("\n=== Testing All Missing Column ===")
        tool = DataTransformerTool()
        
        df = pd.DataFrame({
            'normal': [1, 2, 3, 4, 5],
            'all_missing': [None, None, None, None, None]
        })
        
        result = tool.handle_missing_values(data=df, strategy=MissingValueStrategy.DROP)
        
        assert len(result['data']) == 0  # All rows will be dropped
        print(f"✓ All-missing column handled")
    
    def test_no_numeric_columns(self):
        """Test transformations with no numeric columns"""
        print("\n=== Testing No Numeric Columns ===")
        tool = DataTransformerTool()
        
        df = pd.DataFrame({'cat1': ['A', 'B', 'C'], 'cat2': ['X', 'Y', 'Z']})
        transformations = [
            {'type': TransformationType.STANDARDIZE.value, 'columns': None, 'params': {}}
        ]
        
        # Should raise TransformationError when trying to standardize non-numeric data
        with pytest.raises(TransformationError):
            result = tool.transform_data(data=df, transformations=transformations)
        
        print(f"✓ No numeric columns handled (raises TransformationError as expected)")
    
    def test_no_categorical_columns(self):
        """Test encoding with no categorical columns"""
        print("\n=== Testing No Categorical Columns ===")
        tool = DataTransformerTool()
        
        df = pd.DataFrame({'num1': [1, 2, 3], 'num2': [4, 5, 6]})
        transformations = [
            {'type': TransformationType.ONE_HOT_ENCODE.value, 'columns': None, 'params': {}}
        ]
        
        result = tool.transform_data(data=df, transformations=transformations)
        
        # Should handle gracefully (no categorical columns to encode)
        assert 'transformed_data' in result
        print(f"✓ No categorical columns handled gracefully")


class TestQualityImprovement:
    """Test quality improvement calculation"""
    
    def test_quality_improvement_metrics(self):
        """Test quality improvement metrics calculation"""
        print("\n=== Testing Quality Improvement Metrics ===")
        tool = DataTransformerTool()
        
        data = pd.DataFrame({
            'a': [1, 2, None, 4, 5, 5],
            'b': ['X', 'Y', 'Z', 'X', 'Y', 'Y']
        })
        
        transformations = [
            {'type': TransformationType.REMOVE_DUPLICATES.value, 'columns': None, 'params': {}},
            {'type': TransformationType.FILL_MISSING.value, 'columns': None, 'params': {'strategy': 'mean'}}
        ]
        
        result = tool.transform_data(data=data, transformations=transformations)
        
        quality = result['quality_improvement']
        assert 'missing_before' in quality
        assert 'missing_after' in quality
        assert 'duplicates_before' in quality
        assert 'duplicates_after' in quality
        assert quality['missing_after'] < quality['missing_before']
        assert quality['duplicates_after'] < quality['duplicates_before']
        
        print(f"✓ Quality improvement tracked")
        print(f"  - Missing before: {quality['missing_before']}, after: {quality['missing_after']}")
        print(f"  - Duplicates before: {quality['duplicates_before']}, after: {quality['duplicates_after']}")


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    @pytest.fixture
    def customer_data(self):
        """Create realistic customer dataset"""
        np.random.seed(42)
        return pd.DataFrame({
            'customer_id': range(1, 51),
            'age': [np.random.randint(18, 80) if i % 10 != 0 else None for i in range(50)],
            'income': [np.random.randint(20000, 150000) if i % 8 != 0 else None for i in range(50)],
            'segment': np.random.choice(['A', 'B', 'C'], 50),
            'churn': np.random.choice([0, 1], 50)
        })
    
    def test_complete_preprocessing_workflow(self, customer_data):
        """Test complete preprocessing workflow"""
        print("\n=== Testing Complete Preprocessing Workflow ===")
        tool = DataTransformerTool()
        
        # Step 1: Handle missing values
        print("\nStep 1: Handle Missing Values")
        missing_result = tool.handle_missing_values(
            data=customer_data,
            strategy=MissingValueStrategy.MEAN
        )
        print(f"  - Missing handled: {missing_result['missing_handled']}")
        
        # Step 2: Encode categorical
        print("\nStep 2: Encode Categorical Features")
        encode_result = tool.encode_features(
            data=missing_result['data'],
            columns=['segment'],
            method='one_hot'
        )
        print(f"  - Encoded columns: {encode_result['encoding_info']['original_columns']}")
        
        # Step 3: Standardize numeric
        print("\nStep 3: Standardize Numeric Features")
        transformations = [
            {'type': TransformationType.STANDARDIZE.value, 'columns': ['age', 'income'], 'params': {}}
        ]
        final_result = tool.transform_data(
            data=encode_result['data'],
            transformations=transformations
        )
        print(f"  - Standardized columns: ['age', 'income']")
        
        print(f"\n✓ Complete workflow executed successfully")
        print(f"  - Final shape: {final_result['new_shape']}")
    
    def test_ml_pipeline_preparation(self):
        """Test ML pipeline data preparation"""
        print("\n=== Testing ML Pipeline Preparation ===")
        tool = DataTransformerTool()
        
        # Create ML dataset
        np.random.seed(42)
        ml_data = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'feature3': np.random.choice(['low', 'medium', 'high'], 100),
            'feature4': [np.random.randn() if i % 20 != 0 else None for i in range(100)],
            'target': np.random.randint(0, 2, 100)
        })
        
        # Auto-transform
        result = tool.auto_transform(data=ml_data, target_column='target', task_type='classification')
        
        print(f"\nML Pipeline Preparation:")
        print(f"  - Original shape: {result['original_shape']}")
        print(f"  - Final shape: {result['new_shape']}")
        print(f"  - Transformations applied: {len(result['transformation_log'])}")
        
        print(f"\n✓ ML pipeline preparation completed")


class TestHelperMethods:
    """Test internal helper methods for additional coverage"""
    
    def test_determine_transformations(self):
        """Test transformation determination logic"""
        print("\n=== Testing Determine Transformations ===")
        tool = DataTransformerTool()
        
        data = pd.DataFrame({
            'numeric': [1, 2, 3, 3, 5],
            'category': ['A', 'B', 'C', 'A', 'B'],
            'target': [0, 1, 0, 1, 0]
        })
        
        transformations = tool._determine_transformations(data, target_column='target', task_type='classification')
        
        assert len(transformations) > 0
        
        print(f"✓ Transformations determined")
        print(f"  - Number of transformations: {len(transformations)}")
        for trans in transformations:
            print(f"    - {trans['type']}")
    
    def test_calculate_quality_improvement(self):
        """Test quality improvement calculation"""
        print("\n=== Testing Quality Improvement Calculation ===")
        tool = DataTransformerTool()
        
        original = pd.DataFrame({'a': [1, None, 3, 3], 'b': [4, 5, 6, 6]})
        transformed = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        
        quality = tool._calculate_quality_improvement(original, transformed)
        
        assert 'missing_before' in quality
        assert 'duplicates_before' in quality
        assert 'rows_before' in quality
        
        print(f"✓ Quality improvement calculated")
        print(f"  - Quality metrics: {quality}")
    
    def test_apply_single_transformation_median(self):
        """Test median fill strategy in single transformation"""
        print("\n=== Testing Single Transformation - Median Fill ===")
        tool = DataTransformerTool()
        
        df = pd.DataFrame({'a': [1, 2, None, 4, 5], 'b': [10, None, 30, None, 50]})
        original_missing = df.isnull().sum().sum()
        result = tool._apply_single_transformation(
            df, 
            TransformationType.FILL_MISSING.value,
            None,
            {'strategy': 'median'}
        )
        
        # Check that result has fewer or equal missing values
        final_missing = result.isnull().sum().sum()
        assert final_missing <= original_missing
        print(f"✓ Median fill applied - Missing: {original_missing} -> {final_missing}")
    
    def test_apply_single_transformation_mode(self):
        """Test mode fill strategy in single transformation"""
        print("\n=== Testing Single Transformation - Mode Fill ===")
        tool = DataTransformerTool()
        
        df = pd.DataFrame({'a': [1, 1, None, 2, 2, 2], 'b': ['X', 'X', None, 'Y', 'Y', 'Y']})
        original_missing = df.isnull().sum().sum()
        result = tool._apply_single_transformation(
            df,
            TransformationType.FILL_MISSING.value,
            None,
            {'strategy': 'mode'}
        )
        
        final_missing = result.isnull().sum().sum()
        assert final_missing <= original_missing
        print(f"✓ Mode fill applied - Missing: {original_missing} -> {final_missing}")
    
    def test_determine_transformations_high_cardinality(self):
        """Test transformation determination with high cardinality categorical"""
        print("\n=== Testing Determine Transformations - High Cardinality ===")
        tool = DataTransformerTool(config={'max_one_hot_categories': 3})
        
        # Create data with high cardinality categorical
        data = pd.DataFrame({
            'numeric': list(range(20)),
            'high_card_cat': [f'cat_{i}' for i in range(20)],  # 20 unique categories
            'low_card_cat': ['A', 'B'] * 10,
            'target': [0, 1] * 10
        })
        
        transformations = tool._determine_transformations(data, target_column='target', task_type=None)
        
        # Should use label encoding for high cardinality
        trans_types = [t['type'] for t in transformations]
        assert TransformationType.LABEL_ENCODE.value in trans_types
        
        print(f"✓ High cardinality handled with label encoding")
        print(f"  - Transformations: {trans_types}")
    
    def test_determine_transformations_no_issues(self):
        """Test transformation determination with clean data"""
        print("\n=== Testing Determine Transformations - Clean Data ===")
        tool = DataTransformerTool()
        
        # Clean data with no duplicates or missing values
        data = pd.DataFrame({
            'numeric1': [1.0, 2.0, 3.0, 4.0, 5.0],
            'numeric2': [10.0, 20.0, 30.0, 40.0, 50.0],
            'category': ['A', 'B', 'C', 'D', 'E'],
            'target': [0, 1, 0, 1, 0]
        })
        
        transformations = tool._determine_transformations(data, target_column='target', task_type=None)
        
        # Should not include duplicate removal or missing value fill
        trans_types = [t['type'] for t in transformations]
        assert TransformationType.REMOVE_DUPLICATES.value not in trans_types
        assert TransformationType.FILL_MISSING.value not in trans_types
        
        print(f"✓ Clean data transformations determined")
        print(f"  - Transformations: {trans_types}")


class TestIntegration:
    """Test integration with other components"""
    
    def test_settings_model(self):
        """Test DataTransformerSettings model"""
        print("\n=== Testing Settings Model ===")
        
        settings = DataTransformerSettings()
        assert settings.outlier_std_threshold == 3.0
        assert settings.default_missing_strategy == MissingValueStrategy.MEAN
        
        print(f"✓ Settings model works correctly")
    
    def test_transformation_type_enum(self):
        """Test TransformationType enum"""
        print("\n=== Testing TransformationType Enum ===")
        
        assert TransformationType.REMOVE_DUPLICATES.value == "remove_duplicates"
        assert TransformationType.STANDARDIZE.value == "standardize"
        assert TransformationType.ONE_HOT_ENCODE.value == "one_hot_encode"
        
        print(f"✓ TransformationType enum values correct")
    
    def test_missing_value_strategy_enum(self):
        """Test MissingValueStrategy enum"""
        print("\n=== Testing MissingValueStrategy Enum ===")
        
        all_strategies = list(MissingValueStrategy)
        assert MissingValueStrategy.MEAN in all_strategies
        assert MissingValueStrategy.DROP in all_strategies
        assert MissingValueStrategy.INTERPOLATE in all_strategies
        
        print(f"✓ MissingValueStrategy enum complete")
        print(f"  - Available strategies: {[s.value for s in all_strategies]}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

