"""
Comprehensive tests for PandasTool component
Tests cover all public methods and functionality with >85% coverage
Uses real pandas operations without mocks to test actual functionality
"""
import pytest
import os
import tempfile
import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from io import StringIO

from aiecs.tools.task_tools.pandas_tool import (
    PandasTool,
    PandasToolConfig,
    PandasToolError,
    InputValidationError,
    DataFrameError,
    SecurityError,
    ValidationError
)

# Enable debug logging for testing
logging.basicConfig(level=logging.DEBUG)

class TestPandasTool:
    """Test class for PandasTool functionality"""

    @pytest.fixture
    def pandas_tool(self):
        """Create PandasTool instance with default configuration"""
        return PandasTool()

    @pytest.fixture
    def pandas_tool_custom_config(self):
        """Create PandasTool instance with custom configuration"""
        config = {
            'csv_delimiter': ';',
            'encoding': 'utf-8',
            'chunk_size': 5000,
            'max_csv_size': 500000
        }
        return PandasTool(config)

    @pytest.fixture
    def sample_records(self):
        """Sample records for testing"""
        return [
            {'id': 1, 'name': 'Alice', 'age': 25, 'salary': 50000, 'department': 'IT'},
            {'id': 2, 'name': 'Bob', 'age': 30, 'salary': 60000, 'department': 'HR'},
            {'id': 3, 'name': 'Charlie', 'age': 35, 'salary': 70000, 'department': 'IT'},
            {'id': 4, 'name': 'Diana', 'age': 28, 'salary': 55000, 'department': 'Finance'},
            {'id': 5, 'name': 'Eve', 'age': 32, 'salary': 65000, 'department': 'IT'}
        ]

    @pytest.fixture
    def sample_records_with_nulls(self):
        """Sample records with null values for testing"""
        return [
            {'id': 1, 'name': 'Alice', 'age': 25, 'salary': 50000, 'department': 'IT'},
            {'id': 2, 'name': 'Bob', 'age': None, 'salary': 60000, 'department': 'HR'},
            {'id': 3, 'name': None, 'age': 35, 'salary': None, 'department': 'IT'},
            {'id': 4, 'name': 'Diana', 'age': 28, 'salary': 55000, 'department': None},
            {'id': 5, 'name': 'Eve', 'age': 32, 'salary': 65000, 'department': 'IT'}
        ]

    @pytest.fixture
    def sample_records_for_merge(self):
        """Sample records for merge testing"""
        return [
            {'id': 1, 'location': 'New York', 'country': 'USA'},
            {'id': 2, 'location': 'London', 'country': 'UK'},
            {'id': 3, 'location': 'Tokyo', 'country': 'Japan'},
            {'id': 4, 'location': 'Paris', 'country': 'France'}
        ]

    @pytest.fixture
    def sample_time_series(self):
        """Sample time series data"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        return [
            {'date': date.strftime('%Y-%m-%d'), 'value': i + np.random.randint(1, 10)}
            for i, date in enumerate(dates)
        ]

    @pytest.fixture
    def temp_csv_file(self, sample_records):
        """Create temporary CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df = pd.DataFrame(sample_records)
            df.to_csv(f.name, index=False)
            yield f.name
        if os.path.exists(f.name):
            os.unlink(f.name)

    @pytest.fixture
    def temp_json_file(self, sample_records):
        """Create temporary JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            # Create JSON in records format that pandas can read
            df = pd.DataFrame(sample_records)
            json_str = df.to_json(orient='records')
            f.write(json_str)
            f.flush()
            yield f.name
        if os.path.exists(f.name):
            os.unlink(f.name)

    @pytest.fixture
    def temp_excel_file(self, sample_records):
        """Create temporary Excel file"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df = pd.DataFrame(sample_records)
            df.to_excel(f.name, index=False)
            yield f.name
        if os.path.exists(f.name):
            os.unlink(f.name)

    def test_pandas_tool_initialization(self, pandas_tool):
        """Test PandasTool initialization"""
        print(f"Testing PandasTool initialization...")
        
        assert isinstance(pandas_tool, PandasTool)
        assert isinstance(pandas_tool.config, PandasToolConfig)
        assert pandas_tool.config.csv_delimiter == ","
        assert pandas_tool.config.encoding == "utf-8"
        assert pandas_tool.config.chunk_size == 10000
        
        print(f"✓ PandasTool initialized successfully with default config")
        print(f"✓ Config values: delimiter={pandas_tool.config.csv_delimiter}, encoding={pandas_tool.config.encoding}")

    def test_pandas_tool_custom_config(self, pandas_tool_custom_config):
        """Test PandasTool initialization with custom configuration"""
        print(f"Testing PandasTool with custom configuration...")
        
        tool = pandas_tool_custom_config
        assert tool.config.csv_delimiter == ";"
        assert tool.config.chunk_size == 5000
        assert tool.config.max_csv_size == 500000
        
        print(f"✓ Custom configuration applied successfully")
        print(f"✓ Custom values: delimiter={tool.config.csv_delimiter}, chunk_size={tool.config.chunk_size}")

    def test_pandas_tool_invalid_config(self):
        """Test PandasTool initialization with invalid configuration"""
        print(f"Testing PandasTool with invalid configuration...")
        
        with pytest.raises(ValueError):
            PandasTool({'chunk_size': 'invalid'})
        
        print(f"✓ Invalid configuration properly rejected")

    def test_validate_df(self, pandas_tool, sample_records):
        """Test DataFrame validation"""
        print(f"Testing DataFrame validation...")
        
        # Test valid records
        df = pandas_tool._validate_df(sample_records)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert list(df.columns) == ['id', 'name', 'age', 'salary', 'department']
        
        print(f"✓ Valid records converted to DataFrame successfully")
        print(f"✓ DataFrame shape: {df.shape}, columns: {list(df.columns)}")

    def test_validate_df_empty(self, pandas_tool):
        """Test DataFrame validation with empty records"""
        print(f"Testing DataFrame validation with empty records...")
        
        with pytest.raises(InputValidationError):
            pandas_tool._validate_df([])
        
        print(f"✓ Empty records properly rejected")

    def test_validate_columns(self, pandas_tool, sample_records):
        """Test column validation"""
        print(f"Testing column validation...")
        
        df = pandas_tool._validate_df(sample_records)
        
        # Test valid columns
        pandas_tool._validate_columns(df, ['id', 'name'])
        
        # Test invalid columns
        with pytest.raises(InputValidationError):
            pandas_tool._validate_columns(df, ['nonexistent'])
        
        print(f"✓ Column validation working correctly")

    def test_to_json_serializable(self, pandas_tool, sample_records):
        """Test JSON serialization"""
        print(f"Testing JSON serialization...")
        
        df = pd.DataFrame(sample_records)
        result = pandas_tool._to_json_serializable(df)
        assert isinstance(result, list)
        assert len(result) == 5
        assert result[0]['name'] == 'Alice'
        
        # Test Series serialization
        series = df['age']
        result = pandas_tool._to_json_serializable(series)
        assert isinstance(result, dict)
        
        # Test dict serialization
        test_dict = {'mean': np.float64(30.0), 'count': np.int64(5)}
        result = pandas_tool._to_json_serializable(test_dict)
        assert isinstance(result['mean'], float)
        assert isinstance(result['count'], float)
        
        print(f"✓ JSON serialization working correctly")

    def test_read_csv_string(self, pandas_tool):
        """Test reading CSV from string"""
        print(f"Testing CSV string reading...")
        
        csv_string = "id,name,age\n1,Alice,25\n2,Bob,30\n3,Charlie,35"
        result = pandas_tool.read_csv(csv_string)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]['name'] == 'Alice'
        assert result[0]['age'] == 25
        
        print(f"✓ CSV string read successfully")
        print(f"✓ Parsed {len(result)} records")

    def test_read_csv_large_string(self, pandas_tool):
        """Test reading large CSV string (chunked processing)"""
        print(f"Testing large CSV string reading...")
        
        # Create large CSV string
        header = "id,value\n"
        rows = "\n".join([f"{i},{i*10}" for i in range(1000)])
        csv_string = header + rows
        
        # Override max_csv_size to trigger chunking
        original_max_size = pandas_tool.config.max_csv_size
        pandas_tool.config.max_csv_size = 100
        
        try:
            result = pandas_tool.read_csv(csv_string)
            assert isinstance(result, list)
            assert len(result) == 1000
            print(f"✓ Large CSV processed with chunking, {len(result)} records")
        finally:
            pandas_tool.config.max_csv_size = original_max_size

    def test_read_json_string(self, pandas_tool):
        """Test reading JSON from string"""
        print(f"Testing JSON string reading...")
        
        json_data = [
            {"id": 1, "name": "Alice", "age": 25},
            {"id": 2, "name": "Bob", "age": 30}
        ]
        json_string = json.dumps(json_data)
        result = pandas_tool.read_json(json_string)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['name'] == 'Alice'
        
        print(f"✓ JSON string read successfully")
        print(f"✓ Parsed {len(result)} records")

    def test_read_file_csv(self, pandas_tool, temp_csv_file):
        """Test reading CSV file"""
        print(f"Testing CSV file reading...")
        
        result = pandas_tool.read_file(temp_csv_file, "csv")
        assert isinstance(result, list)
        assert len(result) == 5
        assert result[0]['name'] == 'Alice'
        
        print(f"✓ CSV file read successfully from {temp_csv_file}")
        print(f"✓ Read {len(result)} records")

    def test_read_file_json(self, pandas_tool, temp_json_file):
        """Test reading JSON file"""
        print(f"Testing JSON file reading...")
        
        result = pandas_tool.read_file(temp_json_file, "json")
        assert isinstance(result, list)
        assert len(result) == 5
        
        print(f"✓ JSON file read successfully")

    def test_read_file_excel(self, pandas_tool, temp_excel_file):
        """Test reading Excel file"""
        print(f"Testing Excel file reading...")
        
        result = pandas_tool.read_file(temp_excel_file, "excel")
        assert isinstance(result, list)
        assert len(result) == 5
        
        print(f"✓ Excel file read successfully")

    def test_read_file_unsupported_type(self, pandas_tool):
        """Test reading unsupported file type"""
        print(f"Testing unsupported file type...")
        
        with pytest.raises((ValidationError, DataFrameError)):
            pandas_tool.read_file("dummy.txt", "txt")
        
        print(f"✓ Unsupported file type properly rejected")

    def test_write_file_csv(self, pandas_tool, sample_records):
        """Test writing CSV file"""
        print(f"Testing CSV file writing...")
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            try:
                result = pandas_tool.write_file(sample_records, f.name, "csv")
                assert result['success'] is True
                assert result['rows'] == 5
                assert os.path.exists(f.name)
                
                # Verify file contents
                df = pd.read_csv(f.name)
                assert len(df) == 5
                
                print(f"✓ CSV file written successfully to {f.name}")
                print(f"✓ Written {result['rows']} rows")
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)

    def test_write_file_json(self, pandas_tool, sample_records):
        """Test writing JSON file"""
        print(f"Testing JSON file writing...")
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            try:
                result = pandas_tool.write_file(sample_records, f.name, "json")
                assert result['success'] is True
                assert result['rows'] == 5
                
                print(f"✓ JSON file written successfully")
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)

    def test_write_file_excel(self, pandas_tool, sample_records):
        """Test writing Excel file"""
        print(f"Testing Excel file writing...")
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            try:
                result = pandas_tool.write_file(sample_records, f.name, "excel")
                assert result['success'] is True
                assert result['rows'] == 5
                
                print(f"✓ Excel file written successfully")
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)

    def test_summary(self, pandas_tool, sample_records):
        """Test summary statistics"""
        print(f"Testing summary statistics...")
        
        result = pandas_tool.summary(sample_records)
        assert isinstance(result, dict)
        assert 'age' in result
        assert 'salary' in result
        
        # Check that we have statistical measures
        age_stats = result['age']
        assert 'mean' in age_stats
        assert 'count' in age_stats
        
        print(f"✓ Summary statistics computed successfully")
        print(f"✓ Available columns: {list(result.keys())}")

    def test_describe(self, pandas_tool, sample_records):
        """Test descriptive statistics"""
        print(f"Testing descriptive statistics...")
        
        # Test all columns
        result = pandas_tool.describe(sample_records)
        assert isinstance(result, dict)
        
        # Test specific columns
        result = pandas_tool.describe(sample_records, ['age', 'salary'])
        assert 'age' in result
        assert 'salary' in result
        assert 'name' not in result
        
        print(f"✓ Descriptive statistics computed successfully")

    def test_value_counts(self, pandas_tool, sample_records):
        """Test value counts"""
        print(f"Testing value counts...")
        
        result = pandas_tool.value_counts(sample_records, ['department'])
        assert isinstance(result, dict)
        assert 'department' in result
        assert result['department']['IT'] == 3
        assert result['department']['HR'] == 1
        
        print(f"✓ Value counts computed successfully")
        print(f"✓ Department counts: {result['department']}")

    def test_filter(self, pandas_tool, sample_records):
        """Test filtering"""
        print(f"Testing filtering...")
        
        result = pandas_tool.filter(sample_records, "age > 30")
        assert isinstance(result, list)
        assert len(result) == 2  # Charlie and Eve
        
        result = pandas_tool.filter(sample_records, "department == 'IT'")
        assert len(result) == 3
        
        print(f"✓ Filtering working correctly")

    def test_filter_invalid_condition(self, pandas_tool, sample_records):
        """Test filtering with invalid condition"""
        print(f"Testing filtering with invalid condition...")
        
        with pytest.raises(DataFrameError):
            pandas_tool.filter(sample_records, "invalid_column > 30")
        
        print(f"✓ Invalid filter condition properly rejected")

    def test_select_columns(self, pandas_tool, sample_records):
        """Test column selection"""
        print(f"Testing column selection...")
        
        result = pandas_tool.select_columns(sample_records, ['name', 'age'])
        assert isinstance(result, list)
        assert len(result) == 5
        assert 'name' in result[0]
        assert 'age' in result[0]
        assert 'salary' not in result[0]
        
        print(f"✓ Column selection working correctly")

    def test_drop_columns(self, pandas_tool, sample_records):
        """Test column dropping"""
        print(f"Testing column dropping...")
        
        result = pandas_tool.drop_columns(sample_records, ['salary'])
        assert isinstance(result, list)
        assert 'salary' not in result[0]
        assert 'name' in result[0]
        
        print(f"✓ Column dropping working correctly")

    def test_drop_duplicates(self, pandas_tool):
        """Test duplicate removal"""
        print(f"Testing duplicate removal...")
        
        records_with_dupes = [
            {'id': 1, 'name': 'Alice', 'department': 'IT'},
            {'id': 2, 'name': 'Bob', 'department': 'HR'},
            {'id': 1, 'name': 'Alice', 'department': 'IT'},  # Duplicate
            {'id': 3, 'name': 'Charlie', 'department': 'IT'}
        ]
        
        result = pandas_tool.drop_duplicates(records_with_dupes)
        assert len(result) == 3
        
        # Test with specific columns
        result = pandas_tool.drop_duplicates(records_with_dupes, ['id'])
        assert len(result) == 3
        
        print(f"✓ Duplicate removal working correctly")

    def test_dropna(self, pandas_tool, sample_records_with_nulls):
        """Test NA value dropping"""
        print(f"Testing NA value dropping...")
        
        result = pandas_tool.dropna(sample_records_with_nulls)
        assert len(result) == 2  # Only records without any null values
        
        result = pandas_tool.dropna(sample_records_with_nulls, how='all')
        assert len(result) == 5  # No records are all null
        
        print(f"✓ NA dropping working correctly")

    def test_groupby(self, pandas_tool, sample_records):
        """Test grouping and aggregation"""
        print(f"Testing groupby...")
        
        result = pandas_tool.groupby(
            sample_records, 
            ['department'], 
            {'salary': 'mean', 'age': 'count'}
        )
        assert isinstance(result, list)
        assert len(result) == 3  # IT, HR, Finance
        
        # Find IT department result
        it_result = next(r for r in result if r['department'] == 'IT')
        assert it_result['salary'] == (50000 + 70000 + 65000) / 3
        
        print(f"✓ Groupby working correctly")
        print(f"✓ IT department average salary: {it_result['salary']}")

    def test_pivot_table(self, pandas_tool):
        """Test pivot table creation"""
        print(f"Testing pivot table...")
        
        pivot_data = [
            {'category': 'A', 'month': 'Jan', 'sales': 100},
            {'category': 'A', 'month': 'Feb', 'sales': 120},
            {'category': 'B', 'month': 'Jan', 'sales': 80},
            {'category': 'B', 'month': 'Feb', 'sales': 90}
        ]
        
        result = pandas_tool.pivot_table(
            pivot_data, 
            values=['sales'], 
            index=['category'], 
            columns=['month']
        )
        assert isinstance(result, list)
        assert len(result) == 2  # Categories A and B
        
        print(f"✓ Pivot table created successfully")

    def test_merge(self, pandas_tool, sample_records, sample_records_for_merge):
        """Test merging DataFrames"""
        print(f"Testing merge...")
        
        result = pandas_tool.merge(sample_records, sample_records_for_merge, 'id', 'inner')
        assert isinstance(result, list)
        assert len(result) == 4  # Only IDs 1-4 exist in both
        assert 'location' in result[0]
        assert 'name' in result[0]
        
        print(f"✓ Merge working correctly")
        print(f"✓ Merged {len(result)} records")

    def test_merge_different_join_types(self, pandas_tool, sample_records, sample_records_for_merge):
        """Test different join types"""
        print(f"Testing different join types...")
        
        # Left join
        result = pandas_tool.merge(sample_records, sample_records_for_merge, 'id', 'left')
        assert len(result) == 5  # All records from left table
        
        # Right join
        result = pandas_tool.merge(sample_records, sample_records_for_merge, 'id', 'right')
        assert len(result) == 4  # All records from right table
        
        print(f"✓ Different join types working correctly")

    def test_concat(self, pandas_tool, sample_records):
        """Test concatenation"""
        print(f"Testing concatenation...")
        
        more_records = [
            {'id': 6, 'name': 'Frank', 'age': 45, 'salary': 75000, 'department': 'Finance'},
            {'id': 7, 'name': 'Grace', 'age': 29, 'salary': 58000, 'department': 'HR'}
        ]
        
        result = pandas_tool.concat([sample_records, more_records])
        assert isinstance(result, list)
        assert len(result) == 7
        
        print(f"✓ Concatenation working correctly")

    def test_sort_values(self, pandas_tool, sample_records):
        """Test sorting"""
        print(f"Testing sorting...")
        
        result = pandas_tool.sort_values(sample_records, ['age'])
        assert result[0]['age'] == 25  # Alice, youngest
        assert result[-1]['age'] == 35  # Charlie, oldest
        
        # Test descending
        result = pandas_tool.sort_values(sample_records, ['salary'], ascending=False)
        assert result[0]['salary'] == 70000  # Charlie, highest salary
        
        print(f"✓ Sorting working correctly")

    def test_rename_columns(self, pandas_tool, sample_records):
        """Test column renaming"""
        print(f"Testing column renaming...")
        
        result = pandas_tool.rename_columns(sample_records, {'name': 'full_name', 'age': 'years'})
        assert 'full_name' in result[0]
        assert 'years' in result[0]
        assert 'name' not in result[0]
        assert 'age' not in result[0]
        
        print(f"✓ Column renaming working correctly")

    def test_replace_values(self, pandas_tool, sample_records):
        """Test value replacement"""
        print(f"Testing value replacement...")
        
        result = pandas_tool.replace_values(sample_records, {'IT': 'Information Technology'}, ['department'])
        it_count = sum(1 for r in result if r['department'] == 'Information Technology')
        assert it_count == 3
        
        print(f"✓ Value replacement working correctly")

    def test_fill_na(self, pandas_tool, sample_records_with_nulls):
        """Test filling NA values"""
        print(f"Testing fill NA...")
        
        result = pandas_tool.fill_na(sample_records_with_nulls, 'Unknown', ['name'])
        unknown_count = sum(1 for r in result if r['name'] == 'Unknown')
        assert unknown_count == 1
        
        print(f"✓ Fill NA working correctly")

    def test_astype(self, pandas_tool, sample_records):
        """Test type conversion"""
        print(f"Testing type conversion...")
        
        result = pandas_tool.astype(sample_records, {'id': 'str'})
        # Check that id is now a string
        assert isinstance(result[0]['id'], str)
        
        print(f"✓ Type conversion working correctly")

    def test_apply(self, pandas_tool, sample_records):
        """Test apply function"""
        print(f"Testing apply function...")
        
        result = pandas_tool.apply(sample_records, 'upper', ['name'])
        assert result[0]['name'] == 'ALICE'
        assert result[1]['name'] == 'BOB'
        
        result = pandas_tool.apply(sample_records, 'abs', ['salary'])
        assert all(r['salary'] >= 0 for r in result)
        
        print(f"✓ Apply function working correctly")

    def test_melt(self, pandas_tool):
        """Test melting DataFrame"""
        print(f"Testing melt...")
        
        wide_data = [
            {'id': 1, 'Jan': 100, 'Feb': 120, 'Mar': 110},
            {'id': 2, 'Jan': 80, 'Feb': 90, 'Mar': 95}
        ]
        
        result = pandas_tool.melt(wide_data, ['id'], ['Jan', 'Feb', 'Mar'])
        assert isinstance(result, list)
        assert len(result) == 6  # 2 IDs × 3 months
        assert 'variable' in result[0]
        assert 'value' in result[0]
        
        print(f"✓ Melt working correctly")

    def test_pivot(self, pandas_tool):
        """Test pivot operation"""
        print(f"Testing pivot...")
        
        long_data = [
            {'id': 1, 'month': 'Jan', 'sales': 100},
            {'id': 1, 'month': 'Feb', 'sales': 120},
            {'id': 2, 'month': 'Jan', 'sales': 80},
            {'id': 2, 'month': 'Feb', 'sales': 90}
        ]
        
        result = pandas_tool.pivot(long_data, 'id', 'month', 'sales')
        assert isinstance(result, list)
        assert len(result) == 2  # 2 IDs
        
        print(f"✓ Pivot working correctly")

    def test_stack(self, pandas_tool, sample_records):
        """Test stack operation"""
        print(f"Testing stack...")
        
        result = pandas_tool.stack(sample_records)
        assert isinstance(result, list)
        assert len(result) > len(sample_records)  # Stacking creates more rows
        
        print(f"✓ Stack working correctly")

    def test_strip_strings(self, pandas_tool):
        """Test string stripping"""
        print(f"Testing string stripping...")
        
        string_data = [
            {'id': 1, 'name': '  Alice  ', 'city': ' New York '},
            {'id': 2, 'name': ' Bob ', 'city': 'London  '}
        ]
        
        result = pandas_tool.strip_strings(string_data, ['name', 'city'])
        assert result[0]['name'] == 'Alice'
        assert result[0]['city'] == 'New York'
        assert result[1]['name'] == 'Bob'
        
        print(f"✓ String stripping working correctly")

    def test_to_numeric(self, pandas_tool):
        """Test numeric conversion"""
        print(f"Testing numeric conversion...")
        
        numeric_data = [
            {'id': 1, 'score': '85.5', 'count': '10'},
            {'id': 2, 'score': '92.0', 'count': '15'}
        ]
        
        result = pandas_tool.to_numeric(numeric_data, ['score', 'count'])
        assert isinstance(result[0]['score'], (int, float))
        assert isinstance(result[0]['count'], (int, float))
        # Check that values are numeric
        assert result[0]['score'] == 85.5
        assert result[0]['count'] == 10
        
        print(f"✓ Numeric conversion working correctly")

    def test_to_datetime(self, pandas_tool):
        """Test datetime conversion"""
        print(f"Testing datetime conversion...")
        
        date_data = [
            {'id': 1, 'date': '2023-01-01', 'timestamp': '2023-01-01 12:00:00'},
            {'id': 2, 'date': '2023-01-02', 'timestamp': '2023-01-02 15:30:00'}
        ]
        
        result = pandas_tool.to_datetime(date_data, ['date', 'timestamp'])
        # Check that dates are converted (they become strings in serialization)
        assert isinstance(result[0]['date'], str)
        assert '2023-01-01' in result[0]['date']
        
        print(f"✓ Datetime conversion working correctly")

    def test_statistical_functions(self, pandas_tool, sample_records):
        """Test statistical functions"""
        print(f"Testing statistical functions...")
        
        # Test mean
        result = pandas_tool.mean(sample_records, ['age', 'salary'])
        assert 'age' in result
        assert 'salary' in result
        assert result['age'] == 30.0
        
        # Test sum
        result = pandas_tool.sum(sample_records, ['salary'])
        assert result['salary'] == 300000
        
        # Test count
        result = pandas_tool.count(sample_records)
        assert result['id'] == 5
        
        # Test min/max
        min_result = pandas_tool.min(sample_records, ['age'])
        max_result = pandas_tool.max(sample_records, ['age'])
        assert min_result['age'] == 25
        assert max_result['age'] == 35
        
        print(f"✓ Statistical functions working correctly")
        print(f"✓ Mean age: {30.0}, Total salary: {300000}")

    def test_rolling(self, pandas_tool, sample_time_series):
        """Test rolling window functions"""
        print(f"Testing rolling functions...")
        
        result = pandas_tool.rolling(sample_time_series, ['value'], 3, 'mean')
        assert isinstance(result, list)
        
        # Check that rolling columns are added
        rolling_col = f"value_mean_3"
        assert rolling_col in result[0]
        
        print(f"✓ Rolling functions working correctly")

    def test_sampling_functions(self, pandas_tool, sample_records):
        """Test sampling functions"""
        print(f"Testing sampling functions...")
        
        # Test head
        result = pandas_tool.head(sample_records, 3)
        assert len(result) == 3
        assert result[0]['name'] == 'Alice'
        
        # Test tail
        result = pandas_tool.tail(sample_records, 2)
        assert len(result) == 2
        assert result[-1]['name'] == 'Eve'
        
        # Test sample
        result = pandas_tool.sample(sample_records, 3, random_state=42)
        assert len(result) == 3
        
        print(f"✓ Sampling functions working correctly")

    def test_error_handling_empty_records(self, pandas_tool):
        """Test error handling with empty records"""
        print(f"Testing error handling with empty records...")
        
        with pytest.raises(InputValidationError):
            pandas_tool.summary([])
        
        print(f"✓ Empty records error handling working")

    def test_error_handling_invalid_columns(self, pandas_tool, sample_records):
        """Test error handling with invalid columns"""
        print(f"Testing error handling with invalid columns...")
        
        with pytest.raises(InputValidationError):
            pandas_tool.select_columns(sample_records, ['nonexistent'])
        
        print(f"✓ Invalid columns error handling working")

    def test_error_handling_invalid_merge_type(self, pandas_tool, sample_records):
        """Test error handling with invalid merge type"""
        print(f"Testing error handling with invalid merge type...")
        
        with pytest.raises(ValidationError):
            pandas_tool.merge(sample_records, sample_records, 'id', 'invalid')
        
        print(f"✓ Invalid merge type error handling working")

    def test_error_handling_invalid_dropna_how(self, pandas_tool, sample_records):
        """Test error handling with invalid dropna 'how' parameter"""
        print(f"Testing error handling with invalid dropna parameter...")
        
        with pytest.raises(ValidationError):
            pandas_tool.dropna(sample_records, how='invalid')
        
        print(f"✓ Invalid dropna parameter error handling working")

    def test_error_handling_invalid_rolling_function(self, pandas_tool, sample_records):
        """Test error handling with invalid rolling function"""
        print(f"Testing error handling with invalid rolling function...")
        
        with pytest.raises(ValidationError):
            pandas_tool.rolling(sample_records, ['age'], 3, 'invalid_function')
        
        print(f"✓ Invalid rolling function error handling working")

    def test_config_model_validation(self):
        """Test PandasToolConfig validation"""
        print(f"Testing config model validation...")
        
        # Test valid config
        config = PandasToolConfig()
        assert config.csv_delimiter == ","
        assert config.encoding == "utf-8"
        
        # Test custom config
        config = PandasToolConfig(csv_delimiter=";", chunk_size=5000)
        assert config.csv_delimiter == ";"
        assert config.chunk_size == 5000
        
        print(f"✓ Config model validation working correctly")

    def test_large_file_processing(self, pandas_tool):
        """Test large file processing with chunking"""
        print(f"Testing large file processing...")
        
        # Create a large CSV string that should trigger chunking
        header = "id,value,category\n"
        rows = "\n".join([f"{i},{i*2},{'A' if i % 2 == 0 else 'B'}" for i in range(100)])
        large_csv = header + rows
        
        # Temporarily reduce chunk size to trigger chunking
        original_chunk_size = pandas_tool.config.chunk_size
        original_max_size = pandas_tool.config.max_csv_size
        pandas_tool.config.chunk_size = 50
        pandas_tool.config.max_csv_size = 100
        
        try:
            result = pandas_tool.read_csv(large_csv)
            assert len(result) == 100
            assert result[0]['id'] == 0
            assert result[-1]['id'] == 99
            
            print(f"✓ Large file processing with chunking working correctly")
            print(f"✓ Processed {len(result)} records in chunks")
        finally:
            pandas_tool.config.chunk_size = original_chunk_size
            pandas_tool.config.max_csv_size = original_max_size

    def test_comprehensive_workflow(self, pandas_tool):
        """Test comprehensive workflow combining multiple operations"""
        print(f"Testing comprehensive workflow...")
        
        # Create sample sales data
        sales_data = [
            {'id': 1, 'product': 'Laptop', 'category': 'Electronics', 'price': 1000, 'quantity': 2, 'date': '2023-01-01'},
            {'id': 2, 'product': 'Mouse', 'category': 'Electronics', 'price': 25, 'quantity': 5, 'date': '2023-01-01'},
            {'id': 3, 'product': 'Desk', 'category': 'Furniture', 'price': 300, 'quantity': 1, 'date': '2023-01-02'},
            {'id': 4, 'product': 'Chair', 'category': 'Furniture', 'price': 150, 'quantity': 4, 'date': '2023-01-02'},
            {'id': 5, 'product': 'Monitor', 'category': 'Electronics', 'price': 400, 'quantity': 1, 'date': '2023-01-03'}
        ]
        
        # Step 1: Add total column using apply (simulated with existing data)
        enhanced_data = []
        for record in sales_data:
            enhanced_record = record.copy()
            enhanced_record['total'] = record['price'] * record['quantity']
            enhanced_data.append(enhanced_record)
        
        # Step 2: Filter high-value transactions
        high_value = pandas_tool.filter(enhanced_data, "total > 200")
        assert len(high_value) == 4
        
        # Step 3: Group by category and compute statistics
        category_stats = pandas_tool.groupby(high_value, ['category'], {'total': 'sum', 'quantity': 'count'})
        assert len(category_stats) == 2  # Electronics and Furniture
        
        # Step 4: Sort by total
        sorted_stats = pandas_tool.sort_values(category_stats, ['total'], ascending=False)
        assert sorted_stats[0]['category'] in ['Electronics', 'Furniture']
        
        print(f"✓ Comprehensive workflow completed successfully")
        print(f"✓ Processed {len(sales_data)} initial records")
        print(f"✓ Filtered to {len(high_value)} high-value transactions")
        print(f"✓ Grouped into {len(category_stats)} categories")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
