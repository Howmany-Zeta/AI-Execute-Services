"""
Comprehensive tests for DataLoaderTool

Tests real functionality without mocks to verify actual behavior and output.
Includes debug output for manual verification of tool functionality.

Run with: poetry run pytest test/test_data_loader_tool.py -v -s
Coverage: poetry run pytest test/test_data_loader_tool.py --cov=aiecs.tools.statistics.data_loader_tool --cov-report=term-missing
"""

import os
import tempfile
import json
from pathlib import Path
from typing import Any, Dict

import pytest
import pandas as pd
import numpy as np

from aiecs.tools.statistics.data_loader_tool import (
    DataLoaderTool,
    DataSourceType,
    LoadStrategy,
    DataLoaderError,
    FileFormatError,
    SchemaValidationError
)


class TestDataLoaderToolInitialization:
    """Test DataLoaderTool initialization and configuration"""
    
    def test_default_initialization(self):
        """Test tool initialization with default settings"""
        print("\n=== Testing Default Initialization ===")
        tool = DataLoaderTool()
        
        assert tool is not None
        assert tool.settings.max_file_size_mb == 500
        assert tool.settings.default_chunk_size == 10000
        assert tool.settings.enable_schema_inference is True
        assert tool.settings.enable_quality_validation is True
        print(f"✓ Tool initialized with default settings")
        print(f"  - Max file size: {tool.settings.max_file_size_mb}MB")
        print(f"  - Default chunk size: {tool.settings.default_chunk_size}")
    
    def test_custom_configuration(self):
        """Test tool initialization with custom configuration"""
        print("\n=== Testing Custom Configuration ===")
        config = {
            'max_file_size_mb': 1000,
            'default_chunk_size': 5000,
            'enable_schema_inference': False
        }
        tool = DataLoaderTool(config=config)
        
        assert tool.settings.max_file_size_mb == 1000
        assert tool.settings.default_chunk_size == 5000
        assert tool.settings.enable_schema_inference is False
        print(f"✓ Tool initialized with custom settings")
        print(f"  - Max file size: {tool.settings.max_file_size_mb}MB")
        print(f"  - Chunk size: {tool.settings.default_chunk_size}")
    
    def test_external_tools_initialization(self):
        """Test external tools initialization"""
        print("\n=== Testing External Tools Initialization ===")
        tool = DataLoaderTool()
        
        assert hasattr(tool, 'external_tools')
        assert 'pandas' in tool.external_tools
        print(f"✓ External tools initialized")
        print(f"  - PandasTool available: {tool.external_tools['pandas'] is not None}")


class TestDataLoaderCSV:
    """Test CSV file loading functionality"""
    
    @pytest.fixture
    def sample_csv_file(self, tmp_path):
        """Create a sample CSV file for testing"""
        csv_path = tmp_path / "test_data.csv"
        df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
            'age': [25, 30, 35, 40, 45],
            'salary': [50000, 60000, 70000, 80000, 90000],
            'department': ['HR', 'IT', 'Finance', 'IT', 'HR']
        })
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    @pytest.fixture
    def csv_with_missing_values(self, tmp_path):
        """Create CSV with missing values for quality testing"""
        csv_path = tmp_path / "test_missing.csv"
        df = pd.DataFrame({
            'col1': [1, 2, None, 4, 5],
            'col2': ['a', None, 'c', 'd', None],
            'col3': [10.5, 20.3, 30.1, None, 50.9]
        })
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    @pytest.fixture
    def csv_with_duplicates(self, tmp_path):
        """Create CSV with duplicate rows"""
        csv_path = tmp_path / "test_duplicates.csv"
        df = pd.DataFrame({
            'a': [1, 2, 2, 3, 3, 3],
            'b': ['x', 'y', 'y', 'z', 'z', 'z']
        })
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    def test_load_csv_full(self, sample_csv_file):
        """Test full CSV loading"""
        print("\n=== Testing Full CSV Load ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=sample_csv_file, source_type=DataSourceType.CSV)
        
        assert 'data' in result
        assert 'metadata' in result
        assert 'quality_report' in result
        assert isinstance(result['data'], pd.DataFrame)
        assert len(result['data']) == 5
        assert result['metadata']['rows'] == 5
        assert result['metadata']['columns'] == 5
        
        print(f"✓ CSV loaded successfully")
        print(f"  - Rows: {result['metadata']['rows']}")
        print(f"  - Columns: {result['metadata']['columns']}")
        print(f"  - Column names: {result['metadata']['column_names']}")
        print(f"  - Quality score: {result['quality_report']['quality_score']:.2f}")
        print(f"\nData preview:")
        print(result['data'].head())
    
    def test_load_csv_with_nrows(self, sample_csv_file):
        """Test CSV loading with row limit"""
        print("\n=== Testing CSV Load with Row Limit ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=sample_csv_file, nrows=3)
        
        assert len(result['data']) == 3
        assert result['metadata']['rows'] == 3
        print(f"✓ Loaded {len(result['data'])} rows (limit: 3)")
        print(f"\nLimited data:")
        print(result['data'])
    
    def test_load_csv_auto_detect(self, sample_csv_file):
        """Test CSV loading with auto format detection"""
        print("\n=== Testing CSV Auto-Detection ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=sample_csv_file, source_type=DataSourceType.AUTO)
        
        assert result['source_type'] == 'csv'
        assert isinstance(result['data'], pd.DataFrame)
        print(f"✓ Format auto-detected as: {result['source_type']}")
    
    def test_csv_quality_validation(self, csv_with_missing_values):
        """Test quality validation with missing values"""
        print("\n=== Testing CSV Quality Validation ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=csv_with_missing_values)
        
        quality_report = result['quality_report']
        assert quality_report['total_rows'] == 5
        assert quality_report['total_columns'] == 3
        assert sum(quality_report['missing_values'].values()) > 0
        assert quality_report['quality_score'] < 1.0
        
        print(f"✓ Quality validation completed")
        print(f"  - Total rows: {quality_report['total_rows']}")
        print(f"  - Missing values: {dict(quality_report['missing_values'])}")
        print(f"  - Quality score: {quality_report['quality_score']:.2f}")
        print(f"  - Issues: {quality_report['issues']}")
    
    def test_csv_duplicate_detection(self, csv_with_duplicates):
        """Test duplicate row detection"""
        print("\n=== Testing Duplicate Detection ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=csv_with_duplicates)
        
        quality_report = result['quality_report']
        assert quality_report['duplicate_rows'] > 0
        print(f"✓ Duplicates detected")
        print(f"  - Total duplicates: {quality_report['duplicate_rows']}")
        print(f"  - Quality score: {quality_report['quality_score']:.2f}")


class TestDataLoaderJSON:
    """Test JSON file loading functionality"""
    
    @pytest.fixture
    def sample_json_file(self, tmp_path):
        """Create a sample JSON file for testing"""
        json_path = tmp_path / "test_data.json"
        data = [
            {'id': 1, 'name': 'Alice', 'score': 95.5},
            {'id': 2, 'name': 'Bob', 'score': 87.3},
            {'id': 3, 'name': 'Charlie', 'score': 92.1}
        ]
        with open(json_path, 'w') as f:
            json.dump(data, f)
        return str(json_path)
    
    def test_load_json_full(self, sample_json_file):
        """Test full JSON loading"""
        print("\n=== Testing Full JSON Load ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=sample_json_file, source_type=DataSourceType.JSON)
        
        assert isinstance(result['data'], pd.DataFrame)
        assert len(result['data']) == 3
        assert 'id' in result['data'].columns
        assert 'name' in result['data'].columns
        
        print(f"✓ JSON loaded successfully")
        print(f"  - Rows: {len(result['data'])}")
        print(f"  - Columns: {list(result['data'].columns)}")
        print(f"\nData:")
        print(result['data'])
    
    def test_load_json_auto_detect(self, sample_json_file):
        """Test JSON auto-detection"""
        print("\n=== Testing JSON Auto-Detection ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=sample_json_file)
        
        assert result['source_type'] == 'json'
        print(f"✓ Format auto-detected as: {result['source_type']}")


class TestDataLoaderExcel:
    """Test Excel file loading functionality"""
    
    @pytest.fixture
    def sample_excel_file(self, tmp_path):
        """Create a sample Excel file for testing"""
        excel_path = tmp_path / "test_data.xlsx"
        df = pd.DataFrame({
            'product': ['A', 'B', 'C', 'D'],
            'quantity': [10, 20, 30, 40],
            'price': [100.0, 200.0, 300.0, 400.0]
        })
        df.to_excel(excel_path, index=False, engine='openpyxl')
        return str(excel_path)
    
    def test_load_excel_full(self, sample_excel_file):
        """Test full Excel loading"""
        print("\n=== Testing Full Excel Load ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=sample_excel_file, source_type=DataSourceType.EXCEL)
        
        assert isinstance(result['data'], pd.DataFrame)
        assert len(result['data']) == 4
        assert 'product' in result['data'].columns
        
        print(f"✓ Excel loaded successfully")
        print(f"  - Rows: {len(result['data'])}")
        print(f"  - Columns: {list(result['data'].columns)}")
        print(f"\nData:")
        print(result['data'])
    
    def test_load_excel_auto_detect(self, sample_excel_file):
        """Test Excel auto-detection"""
        print("\n=== Testing Excel Auto-Detection ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=sample_excel_file)
        
        assert result['source_type'] == 'excel'
        print(f"✓ Format auto-detected as: {result['source_type']}")


class TestDataLoaderParquet:
    """Test Parquet file loading functionality"""
    
    @pytest.fixture
    def sample_parquet_file(self, tmp_path):
        """Create a sample Parquet file for testing"""
        parquet_path = tmp_path / "test_data.parquet"
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=5),
            'value': [100, 200, 300, 400, 500],
            'category': ['A', 'B', 'A', 'B', 'C']
        })
        df.to_parquet(parquet_path, engine='pyarrow')
        return str(parquet_path)
    
    def test_load_parquet_full(self, sample_parquet_file):
        """Test full Parquet loading"""
        print("\n=== Testing Full Parquet Load ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=sample_parquet_file, source_type=DataSourceType.PARQUET)
        
        assert isinstance(result['data'], pd.DataFrame)
        assert len(result['data']) == 5
        
        print(f"✓ Parquet loaded successfully")
        print(f"  - Rows: {len(result['data'])}")
        print(f"  - Columns: {list(result['data'].columns)}")
        print(f"\nData:")
        print(result['data'])
    
    def test_load_parquet_auto_detect(self, sample_parquet_file):
        """Test Parquet auto-detection"""
        print("\n=== Testing Parquet Auto-Detection ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=sample_parquet_file)
        
        assert result['source_type'] == 'parquet'
        print(f"✓ Format auto-detected as: {result['source_type']}")


class TestDataLoaderStrategies:
    """Test different loading strategies"""
    
    @pytest.fixture
    def large_csv_file(self, tmp_path):
        """Create a larger CSV file for strategy testing"""
        csv_path = tmp_path / "large_data.csv"
        df = pd.DataFrame({
            'id': range(1, 1001),
            'value': np.random.randn(1000),
            'category': np.random.choice(['A', 'B', 'C', 'D'], 1000)
        })
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    def test_chunked_loading(self, large_csv_file):
        """Test chunked loading strategy"""
        print("\n=== Testing Chunked Loading ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(
            source=large_csv_file,
            strategy=LoadStrategy.CHUNKED,
            chunk_size=200
        )
        
        assert isinstance(result['data'], pd.DataFrame)
        assert len(result['data']) == 1000
        assert result['strategy'] == 'chunked'
        
        print(f"✓ Chunked loading completed")
        print(f"  - Total rows loaded: {len(result['data'])}")
        print(f"  - Strategy: {result['strategy']}")
    
    def test_lazy_loading(self, large_csv_file):
        """Test lazy loading strategy (falls back to full load)"""
        print("\n=== Testing Lazy Loading ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(
            source=large_csv_file,
            strategy=LoadStrategy.LAZY
        )
        
        assert isinstance(result['data'], pd.DataFrame)
        assert result['strategy'] == 'lazy'
        
        print(f"✓ Lazy loading completed")
        print(f"  - Rows: {len(result['data'])}")


class TestDataLoaderStreaming:
    """Test streaming functionality"""
    
    @pytest.fixture
    def stream_csv_file(self, tmp_path):
        """Create CSV for streaming tests"""
        csv_path = tmp_path / "stream_data.csv"
        df = pd.DataFrame({
            'x': range(1, 501),
            'y': np.random.randn(500)
        })
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    def test_stream_data_csv(self, stream_csv_file):
        """Test CSV streaming"""
        print("\n=== Testing CSV Streaming ===")
        tool = DataLoaderTool()
        
        result = tool.stream_data(source=stream_csv_file, chunk_size=100)
        
        assert 'iterator' in result
        assert result['chunk_size'] == 100
        assert result['source_type'] == 'csv'
        
        # Test iterator
        iterator = result['iterator']
        chunk_count = 0
        total_rows = 0
        for chunk in iterator:
            chunk_count += 1
            total_rows += len(chunk)
            print(f"  - Chunk {chunk_count}: {len(chunk)} rows")
        
        print(f"✓ Streaming completed")
        print(f"  - Total chunks: {chunk_count}")
        print(f"  - Total rows: {total_rows}")
        
        assert total_rows == 500


class TestFormatDetection:
    """Test format detection functionality"""
    
    def test_detect_csv_format(self, tmp_path):
        """Test CSV format detection"""
        print("\n=== Testing CSV Format Detection ===")
        csv_path = tmp_path / "test.csv"
        pd.DataFrame({'a': [1, 2]}).to_csv(csv_path, index=False)
        
        tool = DataLoaderTool()
        result = tool.detect_format(source=str(csv_path))
        
        assert result['detected_type'] == 'csv'
        assert result['file_extension'] == '.csv'
        assert result['confidence'] == 'high'
        
        print(f"✓ Format detected: {result['detected_type']}")
        print(f"  - Extension: {result['file_extension']}")
        print(f"  - Confidence: {result['confidence']}")
    
    def test_detect_json_format(self, tmp_path):
        """Test JSON format detection"""
        print("\n=== Testing JSON Format Detection ===")
        json_path = tmp_path / "test.json"
        with open(json_path, 'w') as f:
            json.dump([{'a': 1}], f)
        
        tool = DataLoaderTool()
        result = tool.detect_format(source=str(json_path))
        
        assert result['detected_type'] == 'json'
        print(f"✓ Format detected: {result['detected_type']}")
    
    def test_detect_excel_format(self, tmp_path):
        """Test Excel format detection"""
        print("\n=== Testing Excel Format Detection ===")
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({'a': [1, 2]}).to_excel(excel_path, index=False)
        
        tool = DataLoaderTool()
        result = tool.detect_format(source=str(excel_path))
        
        assert result['detected_type'] == 'excel'
        print(f"✓ Format detected: {result['detected_type']}")
    
    def test_detect_unsupported_format(self, tmp_path):
        """Test unsupported format detection"""
        print("\n=== Testing Unsupported Format ===")
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("some text")
        
        tool = DataLoaderTool()
        
        with pytest.raises(FileFormatError) as exc_info:
            tool.detect_format(source=str(txt_path))
        
        assert "Unsupported file format" in str(exc_info.value)
        print(f"✓ Correctly raised FileFormatError for .txt file")


class TestSchemaValidation:
    """Test schema validation functionality"""
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for schema validation"""
        return pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['A', 'B', 'C'],
            'value': [10, 20, 30]
        })
    
    def test_validate_schema_success(self, sample_data):
        """Test successful schema validation"""
        print("\n=== Testing Successful Schema Validation ===")
        tool = DataLoaderTool()
        
        schema = {
            'columns': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'}
            }
        }
        
        result = tool.validate_schema(data=sample_data, schema=schema)
        
        assert result['valid'] is True
        assert len(result['issues']) == 0
        
        print(f"✓ Schema validation passed")
        print(f"  - Valid: {result['valid']}")
        print(f"  - Expected columns: {result['expected_columns']}")
        print(f"  - Actual columns: {result['actual_columns']}")
    
    def test_validate_schema_missing_columns(self, sample_data):
        """Test schema validation with missing columns"""
        print("\n=== Testing Schema Validation with Missing Columns ===")
        tool = DataLoaderTool()
        
        schema = {
            'columns': {
                'id': {'type': 'integer'},
                'missing_col': {'type': 'string'}
            }
        }
        
        result = tool.validate_schema(data=sample_data, schema=schema)
        
        assert result['valid'] is False
        assert len(result['issues']) > 0
        
        print(f"✓ Schema validation detected issues")
        print(f"  - Valid: {result['valid']}")
        print(f"  - Issues: {result['issues']}")
    
    def test_validate_schema_with_list_data(self):
        """Test schema validation with list data"""
        print("\n=== Testing Schema Validation with List Data ===")
        tool = DataLoaderTool()
        
        data = [
            {'id': 1, 'name': 'A'},
            {'id': 2, 'name': 'B'}
        ]
        
        schema = {
            'columns': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'}
            }
        }
        
        result = tool.validate_schema(data=data, schema=schema)
        
        assert result['valid'] is True
        print(f"✓ List data validated successfully")


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_load_nonexistent_file(self):
        """Test loading nonexistent file"""
        print("\n=== Testing Nonexistent File Error ===")
        tool = DataLoaderTool()
        
        with pytest.raises(DataLoaderError) as exc_info:
            tool.load_data(source="/nonexistent/path/file.csv")
        
        assert "not found" in str(exc_info.value).lower()
        print(f"✓ Correctly raised DataLoaderError for nonexistent file")
    
    def test_unsupported_strategy(self, tmp_path):
        """Test unsupported loading strategy"""
        print("\n=== Testing Unsupported Strategy ===")
        csv_path = tmp_path / "test.csv"
        pd.DataFrame({'a': [1]}).to_csv(csv_path, index=False)
        
        tool = DataLoaderTool()
        
        # Note: INCREMENTAL is defined but not implemented
        with pytest.raises(DataLoaderError) as exc_info:
            tool.load_data(source=str(csv_path), strategy=LoadStrategy.INCREMENTAL)
        
        assert "Unsupported loading strategy" in str(exc_info.value)
        print(f"✓ Correctly raised error for unsupported strategy")
    
    def test_invalid_configuration(self):
        """Test invalid configuration"""
        print("\n=== Testing Invalid Configuration ===")
        
        with pytest.raises(ValueError):
            DataLoaderTool(config={'max_file_size_mb': 'invalid'})
        
        print(f"✓ Correctly raised ValueError for invalid config")


class TestMetadataGeneration:
    """Test metadata generation"""
    
    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create sample CSV"""
        csv_path = tmp_path / "metadata_test.csv"
        df = pd.DataFrame({
            'int_col': [1, 2, 3],
            'float_col': [1.1, 2.2, 3.3],
            'str_col': ['a', 'b', 'c']
        })
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    def test_metadata_generation(self, sample_csv):
        """Test metadata generation for loaded data"""
        print("\n=== Testing Metadata Generation ===")
        tool = DataLoaderTool()
        
        result = tool.load_data(source=sample_csv)
        metadata = result['metadata']
        
        assert 'rows' in metadata
        assert 'columns' in metadata
        assert 'column_names' in metadata
        assert 'dtypes' in metadata
        assert 'memory_usage_mb' in metadata
        assert 'file_size_mb' in metadata
        
        print(f"✓ Metadata generated successfully")
        print(f"  - Rows: {metadata['rows']}")
        print(f"  - Columns: {metadata['columns']}")
        print(f"  - Column names: {metadata['column_names']}")
        print(f"  - Data types: {metadata['dtypes']}")
        print(f"  - Memory usage: {metadata['memory_usage_mb']:.4f} MB")
        print(f"  - File size: {metadata['file_size_mb']:.4f} MB")


class TestToolExecutorIntegration:
    """Test integration with BaseTool executor"""
    
    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create sample CSV"""
        csv_path = tmp_path / "executor_test.csv"
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    def test_run_method(self, sample_csv):
        """Test using run method interface"""
        print("\n=== Testing run() Method ===")
        tool = DataLoaderTool()
        
        result = tool.run('load_data', source=sample_csv)
        
        assert 'data' in result
        assert isinstance(result['data'], pd.DataFrame)
        
        print(f"✓ run() method executed successfully")
        print(f"  - Loaded {len(result['data'])} rows")
    
    def test_run_detect_format(self, sample_csv):
        """Test detect_format via run method"""
        print("\n=== Testing detect_format via run() ===")
        tool = DataLoaderTool()
        
        result = tool.run('detect_format', source=sample_csv)
        
        assert result['detected_type'] == 'csv'
        print(f"✓ detect_format executed via run()")
        print(f"  - Detected: {result['detected_type']}")
    
    def test_run_validate_schema(self):
        """Test validate_schema via run method"""
        print("\n=== Testing validate_schema via run() ===")
        tool = DataLoaderTool()
        
        data = [{'id': 1, 'name': 'test'}]
        schema = {'columns': {'id': {}, 'name': {}}}
        
        result = tool.run('validate_schema', data=data, schema=schema)
        
        assert result['valid'] is True
        print(f"✓ validate_schema executed via run()")
        print(f"  - Valid: {result['valid']}")


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    @pytest.fixture
    def realistic_dataset(self, tmp_path):
        """Create a realistic dataset"""
        csv_path = tmp_path / "sales_data.csv"
        np.random.seed(42)
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=100),
            'product_id': np.random.randint(1, 20, 100),
            'quantity': np.random.randint(1, 100, 100),
            'price': np.random.uniform(10, 1000, 100).round(2),
            'customer_id': np.random.randint(1000, 2000, 100),
            'region': np.random.choice(['North', 'South', 'East', 'West'], 100)
        })
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    def test_complete_loading_workflow(self, realistic_dataset):
        """Test complete real-world loading workflow"""
        print("\n=== Testing Complete Loading Workflow ===")
        tool = DataLoaderTool()
        
        # Step 1: Detect format
        format_result = tool.detect_format(source=realistic_dataset)
        print(f"\nStep 1: Format Detection")
        print(f"  - Detected type: {format_result['detected_type']}")
        
        # Step 2: Load data
        load_result = tool.load_data(source=realistic_dataset)
        print(f"\nStep 2: Data Loading")
        print(f"  - Rows loaded: {load_result['metadata']['rows']}")
        print(f"  - Columns: {load_result['metadata']['column_names']}")
        
        # Step 3: Validate quality
        quality = load_result['quality_report']
        print(f"\nStep 3: Quality Assessment")
        print(f"  - Quality score: {quality['quality_score']:.2f}")
        print(f"  - Missing values: {sum(quality['missing_values'].values())}")
        print(f"  - Duplicates: {quality['duplicate_rows']}")
        
        # Step 4: Validate schema
        schema = {
            'columns': {
                'date': {},
                'product_id': {},
                'quantity': {},
                'price': {}
            }
        }
        schema_result = tool.validate_schema(
            data=load_result['data'],
            schema=schema
        )
        print(f"\nStep 4: Schema Validation")
        print(f"  - Schema valid: {schema_result['valid']}")
        
        # Verify all steps completed successfully
        assert format_result['detected_type'] == 'csv'
        assert load_result['metadata']['rows'] == 100
        assert quality['quality_score'] == 1.0  # No issues in clean data
        assert schema_result['valid'] is True
        
        print(f"\n✓ Complete workflow executed successfully")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_csv(self, tmp_path):
        """Test loading empty CSV (with headers but no data)"""
        print("\n=== Testing Empty CSV ===")
        csv_path = tmp_path / "empty.csv"
        # Create CSV with headers but no data rows
        pd.DataFrame(columns=['a', 'b', 'c']).to_csv(csv_path, index=False)
        
        tool = DataLoaderTool()
        result = tool.load_data(source=str(csv_path))
        
        assert len(result['data']) == 0
        assert result['metadata']['columns'] == 3
        print(f"✓ Empty CSV loaded successfully")
        print(f"  - Rows: {len(result['data'])}")
        print(f"  - Columns: {result['metadata']['columns']}")
    
    def test_single_row_csv(self, tmp_path):
        """Test loading CSV with single row"""
        print("\n=== Testing Single Row CSV ===")
        csv_path = tmp_path / "single.csv"
        pd.DataFrame({'a': [1]}).to_csv(csv_path, index=False)
        
        tool = DataLoaderTool()
        result = tool.load_data(source=str(csv_path))
        
        assert len(result['data']) == 1
        print(f"✓ Single row CSV loaded successfully")
    
    def test_large_column_count(self, tmp_path):
        """Test loading CSV with many columns"""
        print("\n=== Testing Large Column Count ===")
        csv_path = tmp_path / "many_cols.csv"
        data = {f'col_{i}': [i] for i in range(100)}
        pd.DataFrame(data).to_csv(csv_path, index=False)
        
        tool = DataLoaderTool()
        result = tool.load_data(source=str(csv_path))
        
        assert result['metadata']['columns'] == 100
        print(f"✓ CSV with {result['metadata']['columns']} columns loaded")


class TestAdditionalCoverage:
    """Additional tests to increase coverage over 85%"""
    
    def test_load_data_with_schema_validation(self, tmp_path):
        """Test loading with schema validation enabled"""
        print("\n=== Testing Load with Schema Validation ===")
        csv_path = tmp_path / "schema_test.csv"
        pd.DataFrame({'id': [1, 2], 'name': ['a', 'b']}).to_csv(csv_path, index=False)
        
        tool = DataLoaderTool()
        schema = {'columns': {'id': {}, 'name': {}}}
        
        result = tool.load_data(
            source=str(csv_path),
            schema=schema
        )
        
        assert result['metadata']['schema_valid'] is True
        print(f"✓ Schema validated during load")
    
    def test_load_stata_format(self, tmp_path):
        """Test STATA format detection"""
        print("\n=== Testing STATA Format Detection ===")
        stata_path = tmp_path / "test.dta"
        df = pd.DataFrame({'a': [1, 2, 3]})
        df.to_stata(stata_path, write_index=False)
        
        tool = DataLoaderTool()
        result = tool.detect_format(source=str(stata_path))
        
        assert result['detected_type'] == 'stata'
        print(f"✓ STATA format detected")
    
    def test_load_stata_file(self, tmp_path):
        """Test loading STATA file"""
        print("\n=== Testing STATA File Loading ===")
        stata_path = tmp_path / "data.dta"
        df = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
        df.to_stata(stata_path, write_index=False)
        
        tool = DataLoaderTool()
        result = tool.load_data(source=str(stata_path), source_type=DataSourceType.STATA)
        
        assert len(result['data']) == 3
        assert result['source_type'] == 'stata'
        print(f"✓ STATA file loaded: {len(result['data'])} rows")
    
    def test_load_feather_format(self, tmp_path):
        """Test Feather format loading"""
        print("\n=== Testing Feather Format ===")
        feather_path = tmp_path / "test.feather"
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        df.to_feather(feather_path)
        
        tool = DataLoaderTool()
        result = tool.load_data(source=str(feather_path))
        
        assert result['source_type'] == 'feather'
        assert len(result['data']) == 2
        print(f"✓ Feather file loaded")
    
    def test_load_json_lines_chunked(self, tmp_path):
        """Test JSON lines chunked loading"""
        print("\n=== Testing JSON Lines Chunked ===")
        json_path = tmp_path / "lines.json"
        with open(json_path, 'w') as f:
            for i in range(10):
                f.write(json.dumps({'id': i, 'value': i*10}) + '\n')
        
        tool = DataLoaderTool()
        result = tool.load_data(
            source=str(json_path),
            source_type=DataSourceType.JSON,
            strategy=LoadStrategy.CHUNKED,
            chunk_size=3
        )
        
        assert len(result['data']) == 10
        print(f"✓ JSON lines loaded in chunks: {len(result['data'])} rows")
    
    def test_stream_json_data(self, tmp_path):
        """Test JSON streaming"""
        print("\n=== Testing JSON Streaming ===")
        json_path = tmp_path / "stream.json"
        with open(json_path, 'w') as f:
            for i in range(20):
                f.write(json.dumps({'n': i}) + '\n')
        
        tool = DataLoaderTool()
        result = tool.stream_data(
            source=str(json_path),
            source_type=DataSourceType.JSON,
            chunk_size=5
        )
        
        iterator = result['iterator']
        chunks = list(iterator)
        assert len(chunks) == 4
        print(f"✓ JSON streamed in {len(chunks)} chunks")
    
    def test_quality_validation_with_high_issues(self, tmp_path):
        """Test quality validation with significant issues"""
        print("\n=== Testing Quality Validation with Issues ===")
        csv_path = tmp_path / "bad_quality.csv"
        df = pd.DataFrame({
            'a': [1, None, None, None, None],
            'b': [None, None, None, None, None],
            'c': [1, 1, 1, 2, 2]
        })
        df.to_csv(csv_path, index=False)
        
        tool = DataLoaderTool()
        result = tool.load_data(source=str(csv_path))
        
        quality = result['quality_report']
        assert quality['quality_score'] < 0.7
        assert len(quality['issues']) > 0
        print(f"✓ Quality issues detected")
        print(f"  - Quality score: {quality['quality_score']:.2f}")
        print(f"  - Issues: {quality['issues']}")
    
    def test_metadata_for_non_dataframe(self, tmp_path):
        """Test metadata generation for non-DataFrame data"""
        print("\n=== Testing Non-DataFrame Metadata ===")
        csv_path = tmp_path / "test.csv"
        pd.DataFrame({'a': [1]}).to_csv(csv_path, index=False)
        
        tool = DataLoaderTool()
        result = tool.load_data(
            source=str(csv_path),
            strategy=LoadStrategy.STREAMING,
            chunk_size=10
        )
        
        # Streaming returns iterator, check metadata handling
        metadata = result['metadata']
        assert 'file_size_mb' in metadata
        print(f"✓ Metadata generated for iterator type")
    
    def test_schema_without_columns_key(self):
        """Test schema validation without columns key"""
        print("\n=== Testing Schema Without Columns ===")
        tool = DataLoaderTool()
        
        data = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        schema = {'other_key': 'value'}  # No 'columns' key
        
        result = tool.validate_schema(data=data, schema=schema)
        
        assert result['valid'] is True  # Should pass when no columns specified
        print(f"✓ Schema validation passed without columns key")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

