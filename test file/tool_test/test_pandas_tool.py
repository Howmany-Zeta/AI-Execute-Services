import pytest
import pandas as pd
import numpy as np
import tempfile
import os
import json
from unittest.mock import patch, MagicMock

from app.tools.pandas_tool import (
    PandasTool,
    PandasToolError,
    InputValidationError,
    DataFrameError,
    SecurityError,
    ValidationError
)

# Fixtures
@pytest.fixture
def pandas_tool():
    """Create a PandasTool instance for testing."""
    tool = PandasTool({
        "csv_delimiter": ",",
        "encoding": "utf-8",
        "chunk_size": 1000,
        "cache_size": 10
    })
    return tool

@pytest.fixture
def sample_records():
    """Create sample records for testing."""
    return [
        {"id": 1, "name": "Alice", "age": 30, "city": "New York", "active": True},
        {"id": 2, "name": "Bob", "age": 25, "city": "London", "active": False},
        {"id": 3, "name": "Charlie", "age": 35, "city": "Paris", "active": True},
        {"id": 4, "name": "David", "age": 40, "city": "Tokyo", "active": True},
        {"id": 5, "name": "Eve", "age": 22, "city": "Berlin", "active": False}
    ]

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
def test_run_head(pandas_tool, sample_records):
    """Test the head operation."""
    result = pandas_tool.run('head', records=sample_records, n=3)
    
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]['id'] == 1
    assert result[1]['id'] == 2
    assert result[2]['id'] == 3

def test_run_tail(pandas_tool, sample_records):
    """Test the tail operation."""
    result = pandas_tool.run('tail', records=sample_records, n=2)
    
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['id'] == 4
    assert result[1]['id'] == 5

def test_run_sample(pandas_tool, sample_records):
    """Test the sample operation."""
    result = pandas_tool.run('sample', records=sample_records, n=2, random_state=42)
    
    assert isinstance(result, list)
    assert len(result) == 2
    # With fixed random_state, the result should be deterministic
    assert all(r['id'] in [1, 2, 3, 4, 5] for r in result)

def test_df_summary(pandas_tool, sample_records):
    """Test the summary operation."""
    result = pandas_tool.run('summary', records=sample_records)
    
    assert isinstance(result, dict)
    assert 'id' in result
    assert 'age' in result
    assert 'count' in result['age']
    assert 'mean' in result['age']
    assert 'std' in result['age']
    assert 'min' in result['age']
    assert 'max' in result['age']

def test_df_describe(pandas_tool, sample_records):
    """Test the describe operation."""
    result = pandas_tool.run('describe', records=sample_records, columns=['age'])
    
    assert isinstance(result, dict)
    assert 'age' in result
    assert 'count' in result['age']
    assert 'mean' in result['age']
    assert result['age']['mean'] == 30.4  # (30+25+35+40+22)/5 = 30.4

def test_df_value_counts(pandas_tool, sample_records):
    """Test the value_counts operation."""
    result = pandas_tool.run('value_counts', records=sample_records, columns=['city', 'active'])
    
    assert isinstance(result, dict)
    assert 'city' in result
    assert 'active' in result
    assert result['city']['New York'] == 1
    assert result['city']['London'] == 1
    assert result['active'][True] == 3
    assert result['active'][False] == 2

def test_df_filter(pandas_tool, sample_records):
    """Test the filter operation."""
    result = pandas_tool.run('filter', records=sample_records, condition='age > 30')
    
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['name'] == 'Charlie'
    assert result[1]['name'] == 'David'

def test_df_select_columns(pandas_tool, sample_records):
    """Test the select_columns operation."""
    result = pandas_tool.run('select_columns', records=sample_records, columns=['name', 'age'])
    
    assert isinstance(result, list)
    assert len(result) == 5
    assert set(result[0].keys()) == {'name', 'age'}
    assert 'city' not in result[0]
    assert 'id' not in result[0]

def test_df_drop_columns(pandas_tool, sample_records):
    """Test the drop_columns operation."""
    result = pandas_tool.run('drop_columns', records=sample_records, columns=['city', 'active'])
    
    assert isinstance(result, list)
    assert len(result) == 5
    assert set(result[0].keys()) == {'id', 'name', 'age'}
    assert 'city' not in result[0]
    assert 'active' not in result[0]

def test_df_drop_duplicates(pandas_tool):
    """Test the drop_duplicates operation."""
    records_with_duplicates = [
        {"id": 1, "name": "Alice", "city": "New York"},
        {"id": 2, "name": "Bob", "city": "London"},
        {"id": 3, "name": "Alice", "city": "Paris"},  # Duplicate name
        {"id": 4, "name": "David", "city": "New York"},  # Duplicate city
    ]
    
    # Drop duplicates based on name
    result = pandas_tool.run('drop_duplicates', records=records_with_duplicates, columns=['name'])
    
    assert isinstance(result, list)
    assert len(result) == 3  # Alice appears only once
    
    # Drop duplicates based on city
    result = pandas_tool.run('drop_duplicates', records=records_with_duplicates, columns=['city'])
    
    assert isinstance(result, list)
    assert len(result) == 3  # New York appears only once

def test_df_dropna(pandas_tool):
    """Test the dropna operation."""
    records_with_na = [
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": None},
        {"id": 3, "name": None, "age": 35},
        {"id": 4, "name": "David", "age": 40},
    ]
    
    # Drop rows with any NA values
    result = pandas_tool.run('dropna', records=records_with_na, axis=0, how='any')
    
    assert isinstance(result, list)
    assert len(result) == 2  # Only rows without NA values
    assert result[0]['id'] == 1
    assert result[1]['id'] == 4

def test_df_groupby(pandas_tool, sample_records):
    """Test the groupby operation."""
    result = pandas_tool.run('groupby', 
                            records=sample_records, 
                            by=['active'], 
                            agg={'age': 'mean'})
    
    assert isinstance(result, list)
    assert len(result) == 2  # Two groups: active=True and active=False
    
    # Find the group with active=True
    true_group = next(r for r in result if r['active'] == True)
    false_group = next(r for r in result if r['active'] == False)
    
    # Check aggregated values
    assert true_group['age'] == (30 + 35 + 40) / 3  # Mean age of active=True
    assert false_group['age'] == (25 + 22) / 2  # Mean age of active=False

def test_df_pivot_table(pandas_tool):
    """Test the pivot_table operation."""
    records = [
        {"product": "A", "region": "East", "sales": 100},
        {"product": "A", "region": "West", "sales": 150},
        {"product": "B", "region": "East", "sales": 200},
        {"product": "B", "region": "West", "sales": 250},
    ]
    
    result = pandas_tool.run('pivot_table', 
                            records=records, 
                            values=['sales'], 
                            index=['product'], 
                            columns=['region'],
                            aggfunc='sum')
    
    assert isinstance(result, list)
    # The result structure depends on how pandas formats the pivot table
    # We'll check that the data is correctly aggregated
    assert any(r.get('product') == 'A' and r.get('East') == 100 and r.get('West') == 150 for r in result)
    assert any(r.get('product') == 'B' and r.get('East') == 200 and r.get('West') == 250 for r in result)

def test_df_merge(pandas_tool):
    """Test the merge operation."""
    records_left = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"},
    ]
    
    records_right = [
        {"id": 1, "age": 30},
        {"id": 2, "age": 25},
        {"id": 4, "age": 40},
    ]
    
    result = pandas_tool.run('merge', 
                            records=records_left, 
                            records_right=records_right, 
                            on='id', 
                            join_type='inner')
    
    assert isinstance(result, list)
    assert len(result) == 2  # Only ids 1 and 2 are in both datasets
    assert result[0]['id'] == 1
    assert result[0]['name'] == 'Alice'
    assert result[0]['age'] == 30
    assert result[1]['id'] == 2
    assert result[1]['name'] == 'Bob'
    assert result[1]['age'] == 25

def test_df_concat(pandas_tool):
    """Test the concat operation."""
    records1 = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]
    
    records2 = [
        {"id": 3, "name": "Charlie"},
        {"id": 4, "name": "David"},
    ]
    
    result = pandas_tool.run('concat', records_list=[records1, records2], axis=0)
    
    assert isinstance(result, list)
    assert len(result) == 4
    assert [r['id'] for r in result] == [1, 2, 3, 4]
    assert [r['name'] for r in result] == ['Alice', 'Bob', 'Charlie', 'David']

def test_df_sort_values(pandas_tool, sample_records):
    """Test the sort_values operation."""
    # Sort by age in descending order
    result = pandas_tool.run('sort_values', 
                            records=sample_records, 
                            sort_by=['age'], 
                            ascending=False)
    
    assert isinstance(result, list)
    assert len(result) == 5
    assert [r['age'] for r in result] == [40, 35, 30, 25, 22]
    assert [r['name'] for r in result] == ['David', 'Charlie', 'Alice', 'Bob', 'Eve']

def test_df_rename_columns(pandas_tool, sample_records):
    """Test the rename_columns operation."""
    result = pandas_tool.run('rename_columns', 
                            records=sample_records, 
                            mapping={'name': 'full_name', 'city': 'location'})
    
    assert isinstance(result, list)
    assert len(result) == 5
    assert 'full_name' in result[0]
    assert 'location' in result[0]
    assert 'name' not in result[0]
    assert 'city' not in result[0]
    assert result[0]['full_name'] == 'Alice'
    assert result[0]['location'] == 'New York'

def test_df_replace_values(pandas_tool, sample_records):
    """Test the replace_values operation."""
    result = pandas_tool.run('replace_values', 
                            records=sample_records, 
                            to_replace={'city': {'New York': 'NYC', 'London': 'LDN'}})
    
    assert isinstance(result, list)
    assert len(result) == 5
    assert result[0]['city'] == 'NYC'
    assert result[1]['city'] == 'LDN'
    assert result[2]['city'] == 'Paris'  # Unchanged

def test_df_fill_na(pandas_tool):
    """Test the fill_na operation."""
    records_with_na = [
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": None},
        {"id": 3, "name": None, "age": 35},
    ]
    
    result = pandas_tool.run('fill_na', 
                            records=records_with_na, 
                            value='Unknown', 
                            columns=['name'])
    
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]['name'] == 'Alice'  # Unchanged
    assert result[1]['name'] == 'Bob'  # Unchanged
    assert result[2]['name'] == 'Unknown'  # Filled
    assert result[1]['age'] is None  # Still None, not filled

def test_df_astype(pandas_tool):
    """Test the astype operation."""
    records = [
        {"id": "1", "value": "100", "active": "True"},
        {"id": "2", "value": "200", "active": "False"},
    ]
    
    result = pandas_tool.run('astype', 
                            records=records, 
                            dtypes={'id': 'int', 'value': 'float', 'active': 'bool'})
    
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0]['id'], int)
    assert isinstance(result[0]['value'], float)
    assert isinstance(result[0]['active'], bool)
    assert result[0]['id'] == 1
    assert result[0]['value'] == 100.0
    assert result[0]['active'] == True

def test_df_apply(pandas_tool, sample_records):
    """Test the apply operation."""
    # Apply a simple function to the age column
    result = pandas_tool.run('apply', 
                            records=sample_records, 
                            func='square', 
                            columns=['age'])
    
    assert isinstance(result, list)
    assert len(result) == 5
    assert result[0]['age'] == 30 * 30
    assert result[1]['age'] == 25 * 25
    
    # Test with another function
    result = pandas_tool.run('apply', 
                            records=sample_records, 
                            func='sqrt', 
                            columns=['age'])
    
    assert isinstance(result, list)
    assert len(result) == 5
    assert result[0]['age'] == np.sqrt(30)
    assert result[1]['age'] == np.sqrt(25)

def test_read_csv(pandas_tool):
    """Test reading CSV data."""
    csv_str = "id,name,age\n1,Alice,30\n2,Bob,25\n3,Charlie,35"
    
    result = pandas_tool.run('read_csv', csv_str=csv_str)
    
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]['id'] == 1
    assert result[0]['name'] == 'Alice'
    assert result[0]['age'] == 30

def test_read_json(pandas_tool):
    """Test reading JSON data."""
    json_str = """[
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 25},
        {"id": 3, "name": "Charlie", "age": 35}
    ]"""
    
    result = pandas_tool.run('read_json', json_str=json_str)
    
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]['id'] == 1
    assert result[0]['name'] == 'Alice'
    assert result[0]['age'] == 30

def test_read_file(pandas_tool, sample_csv_file):
    """Test reading data from a file."""
    result = pandas_tool.run('read_file', file_path=sample_csv_file, file_type='csv')
    
    assert isinstance(result, list)
    assert len(result) == 100
    assert 'id' in result[0]
    assert 'value' in result[0]
    assert 'category' in result[0]
    assert 'date' in result[0]

def test_write_file(pandas_tool, sample_records, tmpdir):
    """Test writing data to a file."""
    output_path = os.path.join(tmpdir, 'output.csv')
    
    result = pandas_tool.run('write_file', 
                            records=sample_records, 
                            file_path=output_path, 
                            file_type='csv')
    
    assert isinstance(result, dict)
    assert 'success' in result
    assert result['success'] is True
    assert 'file_path' in result
    assert 'rows' in result
    assert result['rows'] == 5
    assert os.path.exists(output_path)
    
    # Verify the file content by reading it back
    df = pd.read_csv(output_path)
    assert len(df) == 5
    assert list(df['name']) == ['Alice', 'Bob', 'Charlie', 'David', 'Eve']

# Error handling tests
def test_invalid_operation(pandas_tool, sample_records):
    """Test handling of invalid operations."""
    with pytest.raises(ValueError):
        pandas_tool.run('invalid_op', records=sample_records)

def test_empty_records(pandas_tool):
    """Test handling of empty records."""
    with pytest.raises(InputValidationError):
        pandas_tool.run('head', records=[])

def test_invalid_column(pandas_tool, sample_records):
    """Test handling of invalid column names."""
    with pytest.raises(InputValidationError):
        pandas_tool.run('select_columns', records=sample_records, columns=['nonexistent_column'])

def test_unsafe_filter_condition(pandas_tool, sample_records):
    """Test handling of potentially unsafe filter conditions."""
    with pytest.raises(SecurityError):
        pandas_tool.run('filter', records=sample_records, condition='__import__("os").system("echo hack")')

def test_invalid_dtypes(pandas_tool, sample_records):
    """Test handling of invalid data type conversions."""
    with pytest.raises(DataFrameError):
        pandas_tool.run('astype', records=sample_records, dtypes={'name': 'invalid_type'})

def test_cache_functionality(pandas_tool, sample_records):
    """Test that caching works correctly."""
    # First call
    result1 = pandas_tool.run('head', records=sample_records, n=3)
    
    # Get the cache key for these records
    cache_key = pandas_tool._get_cache_key(sample_records)
    
    # Verify the DataFrame is in the cache
    assert cache_key in pandas_tool._df_cache
    
    # Second call should use cached DataFrame
    with patch.object(pandas_tool, '_validate_df') as mock_validate:
        result2 = pandas_tool.run('head', records=sample_records, n=3)
        # _validate_df should not be called for cached records
        mock_validate.assert_not_called()
    
    assert result1 == result2