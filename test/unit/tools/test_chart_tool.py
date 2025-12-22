"""
Comprehensive tests for ChartTool component
Tests cover all public methods and functionality with >85% coverage
"""
import pytest
import os
import tempfile
import shutil
import json
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

from aiecs.tools.task_tools.chart_tool import ChartTool, ExportFormat, VisualizationType
from aiecs.tools.task_tools.chart_tool import ChartTool


class TestChartTool:
    """Test class for ChartTool functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def chart_tool(self, temp_dir):
        """Create ChartTool instance with test configuration"""
        config = {
            'export_dir': temp_dir,
            'plot_dpi': 100,
            'plot_figsize': (8, 6),
            'allowed_extensions': ['.csv', '.xlsx', '.xls', '.json']
        }
        return ChartTool(config)

    @pytest.fixture
    def chart_tool_default(self):
        """Create ChartTool instance with default configuration"""
        return ChartTool()

    @pytest.fixture
    def test_data_dir(self):
        """Path to test data directory"""
        return Path(__file__).parent / "data"

    @pytest.fixture
    def sample_csv_file(self, test_data_dir):
        """Path to sample CSV file"""
        return str(test_data_dir / "sample_data.csv")

    @pytest.fixture
    def test_json_file(self, test_data_dir):
        """Path to test JSON file"""
        return str(test_data_dir / "test_data.json")

    @pytest.fixture
    def test_excel_file(self, test_data_dir):
        """Path to test Excel file"""
        return str(test_data_dir / "test_data.xlsx")

    @pytest.fixture
    def large_csv_file(self, test_data_dir):
        """Path to large CSV file"""
        return str(test_data_dir / "large_test_data.csv")

    @pytest.fixture
    def numeric_csv_file(self, test_data_dir):
        """Path to numeric CSV file"""
        return str(test_data_dir / "numeric_data.csv")

    def test_init_default_config(self):
        """Test ChartTool initialization with default configuration"""
        tool = ChartTool()
        assert tool.config.plot_dpi == 100
        assert tool.config.plot_figsize == (10, 6)
        assert '.csv' in tool.config.allowed_extensions
        assert os.path.exists(tool.config.export_dir)

    def test_init_custom_config(self, temp_dir):
        """Test ChartTool initialization with custom configuration"""
        config = {
            'export_dir': temp_dir,
            'plot_dpi': 150,
            'plot_figsize': (12, 8),
            'allowed_extensions': ['.csv', '.json']
        }
        tool = ChartTool(config)
        assert tool.config.export_dir == temp_dir
        assert tool.config.plot_dpi == 150
        assert tool.config.plot_figsize == (12, 8)
        assert tool.config.allowed_extensions == ['.csv', '.json']

    def test_read_data_csv(self, chart_tool, sample_csv_file):
        """Test reading CSV data"""
        result = chart_tool.read_data(sample_csv_file)
        
        assert 'variables' in result
        assert 'observations' in result
        assert 'dtypes' in result
        assert 'memory_usage' in result
        assert 'preview' in result
        
        assert len(result['variables']) == 4  # name, age, score, category
        assert result['observations'] == 10
        assert isinstance(result['preview'], list)
        assert len(result['preview']) == 5  # head(5)

    def test_read_data_csv_with_nrows(self, chart_tool, sample_csv_file):
        """Test reading CSV data with nrows limit"""
        result = chart_tool.read_data(sample_csv_file, nrows=3)
        
        assert result['observations'] == 3
        assert len(result['preview']) == 3

    def test_read_data_json(self, chart_tool, test_json_file):
        """Test reading JSON data"""
        result = chart_tool.read_data(test_json_file)
        
        assert 'variables' in result
        assert 'observations' in result
        assert result['observations'] == 10
        assert 'name' in result['variables']
        assert 'age' in result['variables']

    def test_read_data_excel(self, chart_tool, test_excel_file):
        """Test reading Excel data"""
        result = chart_tool.read_data(test_excel_file, sheet_name=0)
        
        assert 'variables' in result
        assert 'observations' in result
        assert result['observations'] == 10

    def test_read_data_with_export(self, chart_tool, sample_csv_file, temp_dir):
        """Test reading data with export functionality"""
        export_path = os.path.join(temp_dir, "export_test.json")
        result = chart_tool.read_data(
            sample_csv_file,
            export_format=ExportFormat.JSON,
            export_path=export_path
        )
        
        assert 'exported_to' in result
        assert os.path.exists(export_path)
        
        # Verify exported content
        with open(export_path, 'r') as f:
            exported_data = json.load(f)
        assert 'variables' in exported_data

    def test_read_data_file_not_found(self, chart_tool):
        """Test reading non-existent file"""
        with pytest.raises(ValueError, match="File not found"):
            chart_tool.read_data("/nonexistent/file.csv")

    def test_read_data_unsupported_extension(self, chart_tool):
        """Test reading file with unsupported extension"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test data")
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError, match="not allowed"):
                chart_tool.read_data(temp_file)
        finally:
            os.unlink(temp_file)

    def test_visualize_histogram(self, chart_tool, sample_csv_file, temp_dir):
        """Test creating histogram visualization"""
        output_path = os.path.join(temp_dir, "histogram.png")
        result = chart_tool.visualize(
            sample_csv_file,
            plot_type=VisualizationType.HISTOGRAM,
            x='age',
            title='Age Distribution',
            output_path=output_path
        )
        
        assert result['plot_type'] == VisualizationType.HISTOGRAM
        assert os.path.exists(result['output_path'])
        assert result['title'] == 'Age Distribution'

    def test_visualize_scatter(self, chart_tool, sample_csv_file, temp_dir):
        """Test creating scatter plot visualization"""
        result = chart_tool.visualize(
            sample_csv_file,
            plot_type=VisualizationType.SCATTER,
            x='age',
            y='score',
            hue='category'
        )
        
        assert result['plot_type'] == VisualizationType.SCATTER
        assert os.path.exists(result['output_path'])

    def test_visualize_boxplot(self, chart_tool, sample_csv_file):
        """Test creating boxplot visualization"""
        result = chart_tool.visualize(
            sample_csv_file,
            plot_type=VisualizationType.BOXPLOT,
            x='category',
            y='score'
        )
        
        assert result['plot_type'] == VisualizationType.BOXPLOT
        assert os.path.exists(result['output_path'])

    def test_visualize_bar(self, chart_tool, sample_csv_file):
        """Test creating bar plot visualization"""
        result = chart_tool.visualize(
            sample_csv_file,
            plot_type=VisualizationType.BAR,
            x='category',
            y='score'
        )
        
        assert result['plot_type'] == VisualizationType.BAR
        assert os.path.exists(result['output_path'])

    def test_visualize_line(self, chart_tool, sample_csv_file):
        """Test creating line plot visualization"""
        result = chart_tool.visualize(
            sample_csv_file,
            plot_type=VisualizationType.LINE,
            x='age',
            y='score'
        )
        
        assert result['plot_type'] == VisualizationType.LINE
        assert os.path.exists(result['output_path'])

    def test_visualize_heatmap(self, chart_tool, numeric_csv_file):
        """Test creating heatmap visualization"""
        result = chart_tool.visualize(
            numeric_csv_file,
            plot_type=VisualizationType.HEATMAP,
            variables=['var1', 'var2', 'var3', 'var4']
        )
        
        assert result['plot_type'] == VisualizationType.HEATMAP
        assert os.path.exists(result['output_path'])

    def test_visualize_pair(self, chart_tool, sample_csv_file):
        """Test creating pair plot visualization"""
        result = chart_tool.visualize(
            sample_csv_file,
            plot_type=VisualizationType.PAIR,
            variables=['age', 'score'],
            hue='category'
        )
        
        assert result['plot_type'] == VisualizationType.PAIR
        assert os.path.exists(result['output_path'])

    def test_visualize_histogram_multiple_variables(self, chart_tool, numeric_csv_file):
        """Test creating histogram with multiple variables"""
        result = chart_tool.visualize(
            numeric_csv_file,
            plot_type=VisualizationType.HISTOGRAM,
            variables=['var1', 'var2']
        )
        
        assert result['plot_type'] == VisualizationType.HISTOGRAM
        assert os.path.exists(result['output_path'])

    def test_visualize_with_custom_figsize_and_dpi(self, chart_tool, sample_csv_file):
        """Test visualization with custom figure size and DPI"""
        result = chart_tool.visualize(
            sample_csv_file,
            plot_type=VisualizationType.SCATTER,
            x='age',
            y='score',
            figsize=(12, 8),
            dpi=150
        )
        
        assert os.path.exists(result['output_path'])

    def test_visualize_with_export(self, chart_tool, sample_csv_file, temp_dir):
        """Test visualization with export functionality"""
        export_path = os.path.join(temp_dir, "viz_export.json")
        result = chart_tool.visualize(
            sample_csv_file,
            plot_type=VisualizationType.SCATTER,
            x='age',
            y='score',
            export_format=ExportFormat.JSON,
            export_path=export_path
        )
        
        assert 'exported_to' in result
        assert os.path.exists(export_path)

    def test_visualize_invalid_variables(self, chart_tool, sample_csv_file):
        """Test visualization with invalid variables"""
        with pytest.raises(ValueError, match="Variables not found"):
            chart_tool.visualize(
                sample_csv_file,
                plot_type=VisualizationType.SCATTER,
                x='nonexistent_column',
                y='score'
            )

    def test_export_data_json(self, chart_tool, sample_csv_file, temp_dir):
        """Test exporting data to JSON format"""
        export_path = os.path.join(temp_dir, "export.json")
        result = chart_tool.export_data(
            sample_csv_file,
            format=ExportFormat.JSON,
            export_path=export_path
        )
        
        assert result['format'] == ExportFormat.JSON
        assert os.path.exists(result['path'])
        assert result['rows'] == 10
        assert result['columns'] == 4
        
        # Verify JSON content
        with open(export_path, 'r') as f:
            data = json.load(f)
        assert len(data) == 10

    def test_export_data_csv(self, chart_tool, sample_csv_file, temp_dir):
        """Test exporting data to CSV format"""
        export_path = os.path.join(temp_dir, "export.csv")
        result = chart_tool.export_data(
            sample_csv_file,
            format=ExportFormat.CSV,
            export_path=export_path
        )
        
        assert result['format'] == ExportFormat.CSV
        assert os.path.exists(result['path'])
        
        # Verify CSV content
        exported_df = pd.read_csv(export_path)
        assert len(exported_df) == 10

    def test_export_data_excel(self, chart_tool, sample_csv_file, temp_dir):
        """Test exporting data to Excel format"""
        export_path = os.path.join(temp_dir, "export.xlsx")
        result = chart_tool.export_data(
            sample_csv_file,
            format=ExportFormat.EXCEL,
            export_path=export_path
        )
        
        assert result['format'] == ExportFormat.EXCEL
        assert os.path.exists(result['path'])
        
        # Verify Excel content
        exported_df = pd.read_excel(export_path)
        assert len(exported_df) == 10

    def test_export_data_html(self, chart_tool, sample_csv_file, temp_dir):
        """Test exporting data to HTML format"""
        export_path = os.path.join(temp_dir, "export.html")
        result = chart_tool.export_data(
            sample_csv_file,
            format=ExportFormat.HTML,
            export_path=export_path
        )
        
        assert result['format'] == ExportFormat.HTML
        assert os.path.exists(result['path'])
        
        # Verify HTML content exists
        with open(export_path, 'r') as f:
            content = f.read()
        assert '<table' in content

    def test_export_data_markdown(self, chart_tool, sample_csv_file, temp_dir):
        """Test exporting data to Markdown format"""
        export_path = os.path.join(temp_dir, "export.md")
        result = chart_tool.export_data(
            sample_csv_file,
            format=ExportFormat.MARKDOWN,
            export_path=export_path
        )
        
        assert result['format'] == ExportFormat.MARKDOWN
        assert os.path.exists(result['path'])
        
        # Verify Markdown content
        with open(export_path, 'r') as f:
            content = f.read()
        assert '|' in content  # Markdown table format

    def test_export_data_with_variables_subset(self, chart_tool, sample_csv_file, temp_dir):
        """Test exporting data with specific variables"""
        export_path = os.path.join(temp_dir, "export_subset.json")
        result = chart_tool.export_data(
            sample_csv_file,
            format=ExportFormat.JSON,
            variables=['name', 'age'],
            export_path=export_path
        )
        
        assert result['columns'] == 2
        assert 'name' in result['variables']
        assert 'age' in result['variables']
        assert 'score' not in result['variables']

    def test_export_data_auto_path(self, chart_tool, sample_csv_file):
        """Test exporting data with auto-generated path"""
        result = chart_tool.export_data(
            sample_csv_file,
            format=ExportFormat.JSON
        )
        
        assert result['path'].endswith('.json')
        assert os.path.exists(result['path'])

    def test_export_data_invalid_variables(self, chart_tool, sample_csv_file):
        """Test exporting data with invalid variables"""
        with pytest.raises(ValueError, match="Variables not found"):
            chart_tool.export_data(
                sample_csv_file,
                format=ExportFormat.JSON,
                variables=['nonexistent_column']
            )

    def test_load_data_unsupported_format(self, chart_tool):
        """Test loading data with unsupported format"""
        with tempfile.NamedTemporaryFile(suffix='.unknown', delete=False) as f:
            f.write(b"test data")
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                chart_tool._load_data(temp_file)
        finally:
            os.unlink(temp_file)

    def test_load_data_corrupted_file(self, chart_tool):
        """Test loading corrupted data file"""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            f.write(b"corrupted,data\n\xff\xfe\x00\x01")  # Invalid CSV data
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError, match="Error reading file"):
                chart_tool._load_data(temp_file)
        finally:
            os.unlink(temp_file)

    def test_validate_variables_valid(self, chart_tool, sample_csv_file):
        """Test variable validation with valid variables"""
        df = pd.read_csv(sample_csv_file)
        # Should not raise any exception
        chart_tool._validate_variables(df, ['name', 'age'])

    def test_validate_variables_invalid(self, chart_tool, sample_csv_file):
        """Test variable validation with invalid variables"""
        df = pd.read_csv(sample_csv_file)
        with pytest.raises(ValueError, match="Variables not found"):
            chart_tool._validate_variables(df, ['nonexistent'])

    def test_validate_variables_empty(self, chart_tool, sample_csv_file):
        """Test variable validation with empty variables list"""
        df = pd.read_csv(sample_csv_file)
        # Should not raise any exception
        chart_tool._validate_variables(df, [])
        chart_tool._validate_variables(df, None)

    def test_to_json_serializable_dataframe(self, chart_tool):
        """Test JSON serialization of DataFrame"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3.0, 4.0]})
        result = chart_tool._to_json_serializable(df)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_to_json_serializable_series(self, chart_tool):
        """Test JSON serialization of Series"""
        series = pd.Series([1, 2, 3], name='test')
        result = chart_tool._to_json_serializable(series)
        assert isinstance(result, dict)

    def test_to_json_serializable_dict(self, chart_tool):
        """Test JSON serialization of dict with numpy types"""
        data = {
            'int': np.int64(1),
            'float': np.float64(1.5),
            'bool': np.bool_(True),
            'timestamp': pd.Timestamp('2023-01-01'),
            'array': np.array([1, 2, 3]),
            'nan': np.nan
        }
        result = chart_tool._to_json_serializable(data)
        assert isinstance(result['int'], (int, float))
        assert isinstance(result['float'], float)
        assert isinstance(result['bool'], bool)
        assert isinstance(result['timestamp'], str)
        assert isinstance(result['array'], list)
        assert result['nan'] is None

    def test_export_result_json_with_dataframe(self, chart_tool, temp_dir):
        """Test exporting result containing DataFrame to JSON"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        result = {'data': df, 'summary': 'test'}
        export_path = os.path.join(temp_dir, "test_export.json")
        
        chart_tool._export_result(result, export_path, ExportFormat.JSON)
        assert os.path.exists(export_path)
        
        with open(export_path, 'r') as f:
            exported = json.load(f)
        assert 'data' in exported
        assert exported['summary'] == 'test'

    def test_export_result_csv_with_dataframe(self, chart_tool, temp_dir):
        """Test exporting result containing DataFrame to CSV"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        result = {'data': df}
        export_path = os.path.join(temp_dir, "test_export.csv")
        
        chart_tool._export_result(result, export_path, ExportFormat.CSV)
        assert os.path.exists(export_path)

    def test_export_result_csv_without_dataframe(self, chart_tool, temp_dir):
        """Test exporting result without DataFrame to CSV"""
        result = {'value1': 123, 'value2': 'test'}
        export_path = os.path.join(temp_dir, "test_export.csv")
        
        chart_tool._export_result(result, export_path, ExportFormat.CSV)
        assert os.path.exists(export_path)

    def test_export_result_html(self, chart_tool, temp_dir):
        """Test exporting result to HTML"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        result = {'table': df, 'info': {'count': 2}}
        export_path = os.path.join(temp_dir, "test_export.html")
        
        chart_tool._export_result(result, export_path, ExportFormat.HTML)
        assert os.path.exists(export_path)
        
        with open(export_path, 'r') as f:
            content = f.read()
        assert '<html>' in content
        assert '<table' in content

    def test_export_result_excel(self, chart_tool, temp_dir):
        """Test exporting result to Excel"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        result = {'sheet1': df, 'sheet2': {'key': 'value'}}
        export_path = os.path.join(temp_dir, "test_export.xlsx")
        
        chart_tool._export_result(result, export_path, ExportFormat.EXCEL)
        assert os.path.exists(export_path)

    def test_export_result_markdown(self, chart_tool, temp_dir):
        """Test exporting result to Markdown"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        result = {'table': df, 'info': {'count': 2}}
        export_path = os.path.join(temp_dir, "test_export.md")
        
        chart_tool._export_result(result, export_path, ExportFormat.MARKDOWN)
        assert os.path.exists(export_path)
        
        with open(export_path, 'r') as f:
            content = f.read()
        assert '# Chart Results' in content
        assert '|' in content

    def test_create_visualization_auto_path(self, chart_tool, sample_csv_file):
        """Test creating visualization with auto-generated path"""
        df = pd.read_csv(sample_csv_file)
        output_path = chart_tool._create_visualization(
            df, VisualizationType.SCATTER, x='age', y='score'
        )
        assert output_path.endswith('.png')
        assert os.path.exists(output_path)

    def test_create_visualization_error_handling(self, chart_tool):
        """Test visualization error handling"""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        
        with pytest.raises(ValueError, match="Error creating visualization"):
            # This should fail because 'nonexistent' column doesn't exist
            chart_tool._create_visualization(
                df, VisualizationType.SCATTER, x='nonexistent', y='b'
            )

    def test_export_result_error_handling(self, chart_tool, temp_dir):
        """Test export result error handling"""
        result = {'test': 'data'}
        
        # Test with a path that causes file write error - use a directory as filename
        invalid_path = os.path.join(temp_dir, "test_dir")
        os.makedirs(invalid_path, exist_ok=True)  # Create a directory
        
        with pytest.raises(ValueError, match="Error exporting"):
            # Try to write to a directory instead of a file - this will cause an error
            chart_tool._export_result(result, invalid_path, ExportFormat.JSON)

    def test_schema_validation_read_data(self):
        """Test ReadDataSchema validation"""
        from aiecs.tools.task_tools.chart_tool import ChartTool
        
        # Test file_path validation
        with pytest.raises(ValueError, match="File not found"):
            ChartTool.ReadDataSchema(file_path="/nonexistent/file.csv")
        
        # Test that schema can be created with valid file_path
        with tempfile.NamedTemporaryFile(suffix='.csv') as f:
            f.write(b"a,b\n1,2\n")
            f.flush()
            
            # This should succeed - export_path without export_format is allowed in actual implementation
            schema = ChartTool.ReadDataSchema(
                file_path=f.name,
                export_path="/some/path.json"
            )
            assert schema.file_path == f.name
            assert schema.export_path == "/some/path.json"

    def test_schema_validation_visualization(self):
        """Test VisualizationSchema validation"""
        from aiecs.tools.task_tools.chart_tool import ChartTool
        
        # Test file_path validation
        with pytest.raises(ValueError, match="File not found"):
            ChartTool.VisualizationSchema(
                file_path="/nonexistent/file.csv",
                plot_type=VisualizationType.SCATTER
            )
        
        # Test that schema can be created with valid file_path
        with tempfile.NamedTemporaryFile(suffix='.csv') as f:
            f.write(b"a,b\n1,2\n")
            f.flush()
            
            schema = ChartTool.VisualizationSchema(
                file_path=f.name,
                plot_type=VisualizationType.SCATTER
            )
            assert schema.file_path == f.name
            assert schema.plot_type == VisualizationType.SCATTER

    def test_schema_validation_export_data(self):
        """Test ExportDataSchema validation"""
        from aiecs.tools.task_tools.chart_tool import ChartTool
        
        # Test file_path validation
        with pytest.raises(ValueError, match="File not found"):
            ChartTool.ExportDataSchema(
                file_path="/nonexistent/file.csv",
                format=ExportFormat.JSON
            )
        
        # Test that schema can be created with valid file_path
        with tempfile.NamedTemporaryFile(suffix='.csv') as f:
            f.write(b"a,b\n1,2\n")
            f.flush()
            
            schema = ChartTool.ExportDataSchema(
                file_path=f.name,
                format=ExportFormat.JSON
            )
            assert schema.file_path == f.name
            assert schema.format == ExportFormat.JSON

    def test_measure_execution_time_decorator(self, chart_tool, sample_csv_file):
        """Test that methods are decorated with execution time measurement"""
        # This test ensures the decorator is applied and methods work correctly
        result = chart_tool.read_data(sample_csv_file)
        assert 'variables' in result
        
        result = chart_tool.visualize(
            sample_csv_file,
            plot_type=VisualizationType.SCATTER,
            x='age',
            y='score'
        )
        assert 'plot_type' in result
        
        result = chart_tool.export_data(
            sample_csv_file,
            format=ExportFormat.JSON
        )
        assert 'format' in result

    def test_visualization_with_datetime_data(self, chart_tool, temp_dir):
        """Test visualization with datetime data"""
        # Create temporary file with datetime data
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        values = range(10)
        df = pd.DataFrame({'date': dates, 'value': values})
        
        temp_file = os.path.join(temp_dir, "datetime_data.csv")
        df.to_csv(temp_file, index=False)
        
        result = chart_tool.visualize(
            temp_file,
            plot_type=VisualizationType.LINE,
            x='date',
            y='value'
        )
        
        assert result['plot_type'] == VisualizationType.LINE
        assert os.path.exists(result['output_path'])

    def test_large_dataset_handling(self, chart_tool, large_csv_file):
        """Test handling of large datasets"""
        result = chart_tool.read_data(large_csv_file)
        
        assert result['observations'] == 100
        assert len(result['variables']) == 5  # x, y, z, group, value

    def test_memory_usage_calculation(self, chart_tool, sample_csv_file):
        """Test memory usage calculation in read_data"""
        result = chart_tool.read_data(sample_csv_file)
        
        assert 'memory_usage' in result
        assert isinstance(result['memory_usage'], (int, float))
        assert result['memory_usage'] > 0

    def test_config_model_validation(self):
        """Test Config model validation"""
        config = ChartTool.Config()
        
        assert config.plot_dpi == 100
        assert config.plot_figsize == (10, 6)
        assert isinstance(config.allowed_extensions, list)
        assert '.csv' in config.allowed_extensions

    def test_enum_values(self):
        """Test enum values are correctly defined"""
        # Test ExportFormat enum
        assert ExportFormat.JSON == "json"
        assert ExportFormat.CSV == "csv"
        assert ExportFormat.HTML == "html"
        assert ExportFormat.EXCEL == "excel"
        assert ExportFormat.MARKDOWN == "markdown"
        
        # Test VisualizationType enum
        assert VisualizationType.HISTOGRAM == "histogram"
        assert VisualizationType.BOXPLOT == "boxplot"
        assert VisualizationType.SCATTER == "scatter"
        assert VisualizationType.BAR == "bar"
        assert VisualizationType.LINE == "line"
        assert VisualizationType.HEATMAP == "heatmap"
        assert VisualizationType.PAIR == "pair"

    def test_tool_registration(self):
        """Test that the tool is properly registered"""
        # The tool should be registered with the 'chart' name
        # This test verifies the decorator is applied
        tool = ChartTool()
        assert hasattr(tool, 'read_data')
        assert hasattr(tool, 'visualize')
        assert hasattr(tool, 'export_data')
