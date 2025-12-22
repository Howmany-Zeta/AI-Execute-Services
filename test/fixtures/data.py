"""
Test data fixtures for all tests.

Provides fixtures for:
- CSV test data (sample, temporary, large)
- Statistics test data (numeric, categorical, time series)
- Test data files and directories
"""

import pytest
import tempfile
import os
from pathlib import Path
import pandas as pd


@pytest.fixture(scope="session")
def sample_csv_file(test_data_dir):
    """
    Create a sample CSV file for testing.
    
    Returns:
        str: Path to sample CSV file with basic employee data
    """
    csv_file = test_data_dir / "sample_data.csv"
    if not csv_file.exists():
        data = {
            'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
            'age': [25, 30, 35, 28, 32],
            'salary': [50000, 60000, 70000, 55000, 65000],
            'department': ['IT', 'HR', 'IT', 'Finance', 'IT']
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_file, index=False)
    
    return str(csv_file)


@pytest.fixture
def temp_csv_file():
    """
    Create a temporary CSV file for testing.
    
    This fixture creates a temp file that's automatically cleaned up after the test.
    
    Returns:
        str: Path to temporary CSV file
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        data = {
            'x': [1, 2, 3, 4, 5],
            'y': [2, 4, 6, 8, 10],
            'group': ['A', 'A', 'B', 'B', 'C']
        }
        df = pd.DataFrame(data)
        df.to_csv(f.name, index=False)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture(scope="session")
def stats_test_data(test_data_dir):
    """
    Create test data for statistics tools.
    
    Creates three types of data files:
    - Numeric: For numerical analysis
    - Categorical: For categorical analysis
    - Time series: For temporal analysis
    
    Returns:
        dict: Dictionary with paths to numeric, categorical, and time_series data
    """
    # Numeric data
    numeric_file = test_data_dir / "numeric_data.csv"
    if not numeric_file.exists():
        data = {
            'value1': [1.5, 2.3, 3.1, 4.7, 5.2, 6.8, 7.1, 8.9, 9.3, 10.5],
            'value2': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            'category': ['A', 'B', 'A', 'B', 'A', 'B', 'A', 'B', 'A', 'B']
        }
        pd.DataFrame(data).to_csv(numeric_file, index=False)
    
    # Categorical data
    categorical_file = test_data_dir / "categorical_data.csv"
    if not categorical_file.exists():
        data = {
            'gender': ['M', 'F', 'M', 'F', 'M', 'F', 'M', 'F'],
            'education': ['High School', 'College', 'Graduate', 'College', 
                         'High School', 'Graduate', 'College', 'High School'],
            'income': [30000, 50000, 80000, 60000, 35000, 90000, 55000, 40000]
        }
        pd.DataFrame(data).to_csv(categorical_file, index=False)
    
    # Time series data
    time_series_file = test_data_dir / "time_series_data.csv"
    if not time_series_file.exists():
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        data = {
            'date': dates,
            'value': [i + (i % 7) * 2 for i in range(100)]
        }
        pd.DataFrame(data).to_csv(time_series_file, index=False)
    
    return {
        'numeric': str(numeric_file),
        'categorical': str(categorical_file),
        'time_series': str(time_series_file)
    }


@pytest.fixture(scope="session")
def large_test_data(test_data_dir):
    """
    Create large test data for performance testing.
    
    Creates a 10,000 row dataset for testing scalability and performance.
    
    Returns:
        str: Path to large CSV file
    """
    large_file = test_data_dir / "large_test_data.csv"
    if not large_file.exists():
        import numpy as np
        np.random.seed(42)
        
        n_rows = 10000
        data = {
            'id': range(n_rows),
            'value1': np.random.normal(100, 15, n_rows),
            'value2': np.random.exponential(2, n_rows),
            'category': np.random.choice(['A', 'B', 'C', 'D'], n_rows),
            'flag': np.random.choice([True, False], n_rows)
        }
        pd.DataFrame(data).to_csv(large_file, index=False)
    
    return str(large_file)


@pytest.fixture
def sample_json_data():
    """
    Sample JSON data for testing.
    
    Returns:
        dict: Sample JSON structure
    """
    return {
        'users': [
            {'id': 1, 'name': 'Alice', 'role': 'admin'},
            {'id': 2, 'name': 'Bob', 'role': 'user'},
            {'id': 3, 'name': 'Charlie', 'role': 'user'}
        ],
        'metadata': {
            'version': '1.0',
            'created_at': '2023-01-01'
        }
    }


@pytest.fixture
def sample_documents():
    """
    Sample document content for testing document processing.
    
    Returns:
        dict: Dictionary of document types and their content
    """
    return {
        'markdown': "# Title\n\nThis is a **test** document.",
        'text': "This is a simple text document for testing.",
        'html': "<html><body><h1>Test</h1><p>Content</p></body></html>",
        'json': '{"key": "value", "array": [1, 2, 3]}'
    }
