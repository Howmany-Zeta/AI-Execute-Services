import pytest
import asyncio
import os
import pandas as pd
import numpy as np
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.tools.stats_tool import (
    StatsTool,
    StatsToolError,
    InputValidationError,
    FileOperationError,
    SecurityError,
    DataValidationError,
    AnalysisError,
    StatsSettings
)

# Fixtures
@pytest.fixture
def stats_tool():
    """Create a StatsTool instance for testing."""
    tool = StatsTool({
        "max_file_size_mb": 10,
        "cache_ttl_seconds": 60,
        "cache_max_items": 10,
        "threadpool_workers": 2
    })
    return tool

@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        df = pd.DataFrame({
            'id': range(1, 101),
            'value': np.random.normal(50, 10, 100),
            'category': np.random.choice(['A', 'B', 'C'], 100),
            'date': pd.date_range(start='2023-01-01', periods=100)
        })
        df.to_csv(temp_file.name, index=False)
        yield temp_file.name
        
    # Clean up after test
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)

# Basic functionality tests
@pytest.mark.asyncio
async def test_read_data(stats_tool, sample_csv_file):
    """Test reading data from a CSV file."""
    result = await stats_tool.run('read_data', file_path=sample_csv_file)
    
    assert isinstance(result, dict)
    assert 'variables' in result
    assert 'observations' in result
    assert 'dtypes' in result
    assert 'memory_usage' in result
    assert 'preview' in result
    assert len(result['variables']) == 4
    assert result['observations'] == 100
    assert len(result['preview']) > 0

@pytest.mark.asyncio
async def test_describe(stats_tool, sample_csv_file):
    """Test generating descriptive statistics."""
    result = await stats_tool.run('describe', file_path=sample_csv_file)
    
    assert isinstance(result, dict)
    assert 'statistics' in result
    assert 'summary' in result
    assert 'value' in result['statistics']
    assert 'count' in result['statistics']['value']
    assert 'mean' in result['statistics']['value']
    assert 'std' in result['statistics']['value']
    assert 'min' in result['statistics']['value']
    assert 'max' in result['statistics']['value']

@pytest.mark.asyncio
async def test_ttest(stats_tool, sample_csv_file):
    """Test performing t-test."""
    # First create a file with two columns for t-test
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        df = pd.DataFrame({
            'group1': np.random.normal(50, 10, 100),
            'group2': np.random.normal(55, 10, 100)
        })
        df.to_csv(temp_file.name, index=False)
    
    try:
        result = await stats_tool.run('ttest', file_path=temp_file.name, var1='group1', var2='group2')
        
        assert isinstance(result, dict)
        assert 'test_type' in result
        assert 'statistic' in result
        assert 'pvalue' in result
        assert 'significant' in result
        assert 'cohens_d' in result
        assert 'effect_size_interpretation' in result
        assert 'group1_mean' in result
        assert 'group2_mean' in result
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.mark.asyncio
async def test_correlation(stats_tool, sample_csv_file):
    """Test correlation analysis."""
    result = await stats_tool.run('correlation', file_path=sample_csv_file, variables=['id', 'value'])
    
    assert isinstance(result, dict)
    assert 'correlation_matrix' in result
    assert 'method' in result
    assert result['method'] == 'pearson'
    assert 'id' in result['correlation_matrix']
    assert 'value' in result['correlation_matrix']

@pytest.mark.asyncio
async def test_anova(stats_tool, sample_csv_file):
    """Test ANOVA analysis."""
    # Create a file suitable for ANOVA
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        df = pd.DataFrame({
            'value': np.concatenate([
                np.random.normal(50, 10, 30),
                np.random.normal(55, 10, 30),
                np.random.normal(45, 10, 30)
            ]),
            'group': np.concatenate([
                ['A'] * 30,
                ['B'] * 30,
                ['C'] * 30
            ])
        })
        df.to_csv(temp_file.name, index=False)
    
    try:
        result = await stats_tool.run('anova', file_path=temp_file.name, dependent='value', factor='group')
        
        assert isinstance(result, dict)
        assert 'f_statistic' in result
        assert 'p_value' in result
        assert 'significant' in result
        assert 'groups' in result
        assert 'group_means' in result
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.mark.asyncio
async def test_chi_square(stats_tool):
    """Test chi-square test."""
    # Create a file suitable for chi-square test
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        df = pd.DataFrame({
            'gender': np.random.choice(['Male', 'Female'], 100),
            'response': np.random.choice(['Yes', 'No', 'Maybe'], 100)
        })
        df.to_csv(temp_file.name, index=False)
    
    try:
        result = await stats_tool.run('chi_square', file_path=temp_file.name, var1='gender', var2='response')
        
        assert isinstance(result, dict)
        assert 'chi2' in result
        assert 'p_value' in result
        assert 'dof' in result
        assert 'significant' in result
        assert 'contingency_table' in result
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.mark.asyncio
async def test_non_parametric(stats_tool):
    """Test non-parametric tests."""
    # Create a file suitable for non-parametric tests
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        df = pd.DataFrame({
            'value': np.concatenate([
                np.random.exponential(5, 30),
                np.random.exponential(7, 30)
            ]),
            'group': np.concatenate([
                ['A'] * 30,
                ['B'] * 30
            ])
        })
        df.to_csv(temp_file.name, index=False)
    
    try:
        result = await stats_tool.run('non_parametric', 
                                     file_path=temp_file.name, 
                                     test_type='mann_whitney', 
                                     variables=['value'], 
                                     grouping='group')
        
        assert isinstance(result, dict)
        assert 'test_type' in result
        assert 'statistic' in result
        assert 'p_value' in result
        assert 'significant' in result
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.mark.asyncio
async def test_regression(stats_tool, sample_csv_file):
    """Test regression analysis."""
    # Create a file suitable for regression
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        x1 = np.random.normal(0, 1, 100)
        x2 = np.random.normal(0, 1, 100)
        y = 2 * x1 + 3 * x2 + np.random.normal(0, 1, 100)
        df = pd.DataFrame({
            'y': y,
            'x1': x1,
            'x2': x2
        })
        df.to_csv(temp_file.name, index=False)
    
    try:
        result = await stats_tool.run('regression', 
                                     file_path=temp_file.name, 
                                     formula='y ~ x1 + x2')
        
        assert isinstance(result, dict)
        assert 'model_summary' in result
        assert 'coefficients' in result
        assert 'r_squared' in result
        assert 'adj_r_squared' in result
        assert 'f_statistic' in result
        assert 'p_value' in result
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.mark.asyncio
async def test_time_series(stats_tool):
    """Test time series analysis."""
    # Create a file suitable for time series analysis
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        dates = pd.date_range(start='2020-01-01', periods=100)
        values = np.cumsum(np.random.normal(0, 1, 100)) + 100
        df = pd.DataFrame({
            'date': dates,
            'value': values
        })
        df.to_csv(temp_file.name, index=False)
    
    try:
        result = await stats_tool.run('time_series', 
                                     file_path=temp_file.name, 
                                     variable='value',
                                     date_variable='date',
                                     model_type='arima',
                                     order=(1, 1, 1),
                                     forecast_periods=5)
        
        assert isinstance(result, dict)
        assert 'model_summary' in result
        assert 'forecast' in result
        assert 'forecast_dates' in result
        assert len(result['forecast']) == 5
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.mark.asyncio
async def test_preprocess(stats_tool, sample_csv_file):
    """Test data preprocessing."""
    output_path = os.path.join(os.path.dirname(sample_csv_file), 'preprocessed.csv')
    
    try:
        result = await stats_tool.run('preprocess', 
                                     file_path=sample_csv_file, 
                                     variables=['value'],
                                     operation='scale',
                                     scaler_type='standard',
                                     output_path=output_path)
        
        assert isinstance(result, dict)
        assert 'success' in result
        assert result['success'] is True
        assert 'output_path' in result
        assert os.path.exists(result['output_path'])
        
        # Verify the output file
        df = pd.read_csv(result['output_path'])
        assert 'value_scaled' in df.columns
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

# Error handling tests
@pytest.mark.asyncio
async def test_invalid_operation(stats_tool):
    """Test handling of invalid operations."""
    with pytest.raises(StatsToolError):
        await stats_tool.run('invalid_op', file_path='some_file.csv')

@pytest.mark.asyncio
async def test_file_not_found(stats_tool):
    """Test handling of non-existent files."""
    with pytest.raises(FileOperationError):
        await stats_tool.run('read_data', file_path='nonexistent_file.csv')

@pytest.mark.asyncio
async def test_invalid_extension(stats_tool):
    """Test handling of invalid file extensions."""
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        temp_file.write(b'This is not a valid data file')
    
    try:
        with pytest.raises(SecurityError):
            await stats_tool.run('read_data', file_path=temp_file.name)
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.mark.asyncio
async def test_invalid_variables(stats_tool, sample_csv_file):
    """Test handling of invalid variable names."""
    with pytest.raises(DataValidationError):
        await stats_tool.run('describe', file_path=sample_csv_file, variables=['nonexistent_column'])

@pytest.mark.asyncio
async def test_cache_functionality(stats_tool, sample_csv_file):
    """Test that caching works correctly."""
    # First call should not be cached
    result1 = await stats_tool.run('read_data', file_path=sample_csv_file)
    
    # Mock the _load_data method to verify it's not called on second run
    original_load_data = stats_tool._load_data
    mock_called = False
    
    async def mock_load_data(*args, **kwargs):
        nonlocal mock_called
        mock_called = True
        return await original_load_data(*args, **kwargs)
    
    stats_tool._load_data = mock_load_data
    
    # Second call should use cache
    result2 = await stats_tool.run('read_data', file_path=sample_csv_file)
    
    # Restore original method
    stats_tool._load_data = original_load_data
    
    assert not mock_called, "Cache was not used for the second call"
    assert result1 == result2, "Cached result should be identical to original"