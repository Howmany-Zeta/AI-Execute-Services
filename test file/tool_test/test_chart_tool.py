import pytest
import asyncio
import os
import pandas as pd
import numpy as np
import tempfile
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.tools.chart_tool import (
    ChartTool,
    ChartToolError,
    InputValidationError,
    FileOperationError,
    SecurityError,
    DataValidationError,
    ExportError,
    VisualizationError,
    ExportFormat,
    VisualizationType,
    ChartSettings
)

# Fixtures
@pytest.fixture
def chart_tool():
    """Create a ChartTool instance for testing."""
    tool = ChartTool({
        "plot_dpi": 100,
        "plot_figsize": (8, 6)
    })
    return tool

@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
        df = pd.DataFrame({
            'x': range(1, 101),
            'y': np.random.normal(50, 10, 100),
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
async def test_read_data(chart_tool, sample_csv_file):
    """Test reading data from a CSV file."""
    result = await chart_tool.run('read_data', file_path=sample_csv_file)
    
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
async def test_visualize_histogram(chart_tool, sample_csv_file):
    """Test creating a histogram visualization."""
    result = await chart_tool.run('visualize', 
                                 file_path=sample_csv_file,
                                 plot_type=VisualizationType.HISTOGRAM,
                                 x='y')
    
    assert isinstance(result, dict)
    assert 'plot_type' in result
    assert result['plot_type'] == VisualizationType.HISTOGRAM
    assert 'output_path' in result
    assert os.path.exists(result['output_path'])
    
    # Clean up the output file
    os.unlink(result['output_path'])

@pytest.mark.asyncio
async def test_visualize_scatter(chart_tool, sample_csv_file):
    """Test creating a scatter plot visualization."""
    result = await chart_tool.run('visualize', 
                                 file_path=sample_csv_file,
                                 plot_type=VisualizationType.SCATTER,
                                 x='x',
                                 y='y',
                                 hue='category')
    
    assert isinstance(result, dict)
    assert 'plot_type' in result
    assert result['plot_type'] == VisualizationType.SCATTER
    assert 'output_path' in result
    assert os.path.exists(result['output_path'])
    
    # Clean up the output file
    os.unlink(result['output_path'])

@pytest.mark.asyncio
async def test_visualize_bar(chart_tool, sample_csv_file):
    """Test creating a bar chart visualization."""
    result = await chart_tool.run('visualize', 
                                 file_path=sample_csv_file,
                                 plot_type=VisualizationType.BAR,
                                 x='category',
                                 y='y')
    
    assert isinstance(result, dict)
    assert 'plot_type' in result
    assert result['plot_type'] == VisualizationType.BAR
    assert 'output_path' in result
    assert os.path.exists(result['output_path'])
    
    # Clean up the output file
    os.unlink(result['output_path'])

@pytest.mark.asyncio
async def test_visualize_line(chart_tool, sample_csv_file):
    """Test creating a line chart visualization."""
    result = await chart_tool.run('visualize', 
                                 file_path=sample_csv_file,
                                 plot_type=VisualizationType.LINE,
                                 x='x',
                                 y='y')
    
    assert isinstance(result, dict)
    assert 'plot_type' in result
    assert result['plot_type'] == VisualizationType.LINE
    assert 'output_path' in result
    assert os.path.exists(result['output_path'])
    
    # Clean up the output file
    os.unlink(result['output_path'])

@pytest.mark.asyncio
async def test_visualize_heatmap(chart_tool, sample_csv_file):
    """Test creating a heatmap visualization."""
    result = await chart_tool.run('visualize', 
                                 file_path=sample_csv_file,
                                 plot_type=VisualizationType.HEATMAP,
                                 variables=['x', 'y'])
    
    assert isinstance(result, dict)
    assert 'plot_type' in result
    assert result['plot_type'] == VisualizationType.HEATMAP
    assert 'output_path' in result
    assert os.path.exists(result['output_path'])
    
    # Clean up the output file
    os.unlink(result['output_path'])

@pytest.mark.asyncio
async def test_visualize_boxplot(chart_tool, sample_csv_file):
    """Test creating a boxplot visualization."""
    result = await chart_tool.run('visualize', 
                                 file_path=sample_csv_file,
                                 plot_type=VisualizationType.BOXPLOT,
                                 x='category',
                                 y='y')
    
    assert isinstance(result, dict)
    assert 'plot_type' in result
    assert result['plot_type'] == VisualizationType.BOXPLOT
    assert 'output_path' in result
    assert os.path.exists(result['output_path'])
    
    # Clean up the output file
    os.unlink(result['output_path'])

@pytest.mark.asyncio
async def test_visualize_with_custom_output(chart_tool, sample_csv_file):
    """Test creating a visualization with custom output path."""
    output_path = os.path.join(os.path.dirname(sample_csv_file), 'custom_plot.png')
    
    result = await chart_tool.run('visualize', 
                                 file_path=sample_csv_file,
                                 plot_type=VisualizationType.SCATTER,
                                 x='x',
                                 y='y',
                                 output_path=output_path)
    
    assert isinstance(result, dict)
    assert 'output_path' in result
    assert result['output_path'] == output_path
    assert os.path.exists(output_path)
    
    # Clean up the output file
    os.unlink(output_path)

@pytest.mark.asyncio
async def test_export_data_csv(chart_tool, sample_csv_file):
    """Test exporting data to CSV format."""
    output_path = os.path.join(os.path.dirname(sample_csv_file), 'exported.csv')
    
    result = await chart_tool.run('export_data', 
                                 file_path=sample_csv_file,
                                 format=ExportFormat.CSV,
                                 export_path=output_path)
    
    assert isinstance(result, dict)
    assert 'success' in result
    assert result['success'] is True
    assert 'output_path' in result
    assert os.path.exists(output_path)
    
    # Verify the output file
    df = pd.read_csv(output_path)
    assert len(df) == 100
    assert 'x' in df.columns
    assert 'y' in df.columns
    
    # Clean up the output file
    os.unlink(output_path)

@pytest.mark.asyncio
async def test_export_data_json(chart_tool, sample_csv_file):
    """Test exporting data to JSON format."""
    output_path = os.path.join(os.path.dirname(sample_csv_file), 'exported.json')
    
    result = await chart_tool.run('export_data', 
                                 file_path=sample_csv_file,
                                 format=ExportFormat.JSON,
                                 export_path=output_path)
    
    assert isinstance(result, dict)
    assert 'success' in result
    assert result['success'] is True
    assert 'output_path' in result
    assert os.path.exists(output_path)
    
    # Verify the output file
    with open(output_path, 'r') as f:
        data = json.load(f)
    assert len(data) == 100
    assert 'x' in data[0]
    assert 'y' in data[0]
    
    # Clean up the output file
    os.unlink(output_path)

@pytest.mark.asyncio
async def test_export_data_excel(chart_tool, sample_csv_file):
    """Test exporting data to Excel format."""
    output_path = os.path.join(os.path.dirname(sample_csv_file), 'exported.xlsx')
    
    result = await chart_tool.run('export_data', 
                                 file_path=sample_csv_file,
                                 format=ExportFormat.EXCEL,
                                 export_path=output_path)
    
    assert isinstance(result, dict)
    assert 'success' in result
    assert result['success'] is True
    assert 'output_path' in result
    assert os.path.exists(output_path)
    
    # Verify the output file
    df = pd.read_excel(output_path)
    assert len(df) == 100
    assert 'x' in df.columns
    assert 'y' in df.columns
    
    # Clean up the output file
    os.unlink(output_path)

@pytest.mark.asyncio
async def test_export_data_with_selected_columns(chart_tool, sample_csv_file):
    """Test exporting data with selected columns."""
    output_path = os.path.join(os.path.dirname(sample_csv_file), 'exported_selected.csv')
    
    result = await chart_tool.run('export_data', 
                                 file_path=sample_csv_file,
                                 format=ExportFormat.CSV,
                                 export_path=output_path,
                                 variables=['x', 'y'])
    
    assert isinstance(result, dict)
    assert 'success' in result
    assert result['success'] is True
    assert 'output_path' in result
    assert os.path.exists(output_path)
    
    # Verify the output file
    df = pd.read_csv(output_path)
    assert len(df) == 100
    assert set(df.columns) == {'x', 'y'}
    assert 'category' not in df.columns
    
    # Clean up the output file
    os.unlink(output_path)

# Error handling tests
@pytest.mark.asyncio
async def test_invalid_operation(chart_tool):
    """Test handling of invalid operations."""
    with pytest.raises(ChartToolError):
        await chart_tool.run('invalid_op', file_path='some_file.csv')

@pytest.mark.asyncio
async def test_file_not_found(chart_tool):
    """Test handling of non-existent files."""
    with pytest.raises(FileOperationError):
        await chart_tool.run('read_data', file_path='nonexistent_file.csv')

@pytest.mark.asyncio
async def test_invalid_extension(chart_tool):
    """Test handling of invalid file extensions."""
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        temp_file.write(b'This is not a valid data file')
    
    try:
        with pytest.raises(SecurityError):
            await chart_tool.run('read_data', file_path=temp_file.name)
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.mark.asyncio
async def test_invalid_variables(chart_tool, sample_csv_file):
    """Test handling of invalid variable names."""
    with pytest.raises(DataValidationError):
        await chart_tool.run('visualize', 
                            file_path=sample_csv_file,
                            plot_type=VisualizationType.SCATTER,
                            x='nonexistent_column',
                            y='y')

@pytest.mark.asyncio
async def test_invalid_plot_type(chart_tool, sample_csv_file):
    """Test handling of invalid plot type."""
    with pytest.raises(InputValidationError):
        await chart_tool.run('visualize', 
                            file_path=sample_csv_file,
                            plot_type='invalid_plot_type',
                            x='x',
                            y='y')

@pytest.mark.asyncio
async def test_export_with_invalid_format(chart_tool, sample_csv_file):
    """Test handling of invalid export format."""
    with pytest.raises(InputValidationError):
        await chart_tool.run('export_data', 
                            file_path=sample_csv_file,
                            format='invalid_format',
                            export_path='output.txt')

@pytest.mark.asyncio
async def test_visualization_with_missing_required_params(chart_tool, sample_csv_file):
    """Test handling of missing required parameters for visualization."""
    # For scatter plot, both x and y are required
    with pytest.raises(DataValidationError):
        await chart_tool.run('visualize', 
                            file_path=sample_csv_file,
                            plot_type=VisualizationType.SCATTER,
                            x='x')  # Missing y parameter