"""
Data Loader Tool - Universal data loading from multiple file formats

This tool provides comprehensive data loading capabilities with:
- Auto-detection of file formats
- Multiple loading strategies (full, streaming, chunked, lazy)
- Data quality validation on load
- Schema inference and validation
- Support for CSV, Excel, JSON, Parquet, and other formats
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union, Iterator
from enum import Enum
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class DataSourceType(str, Enum):
    """Supported data source types"""

    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    PARQUET = "parquet"
    FEATHER = "feather"
    HDF5 = "hdf5"
    STATA = "stata"
    SAS = "sas"
    SPSS = "spss"
    AUTO = "auto"


class LoadStrategy(str, Enum):
    """Data loading strategies"""

    FULL_LOAD = "full_load"
    STREAMING = "streaming"
    CHUNKED = "chunked"
    LAZY = "lazy"
    INCREMENTAL = "incremental"


class DataLoaderError(Exception):
    """Base exception for DataLoader errors"""


class FileFormatError(DataLoaderError):
    """Raised when file format is unsupported or invalid"""


class SchemaValidationError(DataLoaderError):
    """Raised when schema validation fails"""


class DataQualityError(DataLoaderError):
    """Raised when data quality issues are detected"""


@register_tool("data_loader")
class DataLoaderTool(BaseTool):
    """
    Universal data loading tool that can:
    1. Load data from multiple file formats
    2. Auto-detect data formats and schemas
    3. Handle large datasets with streaming
    4. Validate data quality on load

    Integrates with pandas_tool for core data operations.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the data loader tool
        
        Automatically reads from environment variables with DATA_LOADER_ prefix.
        Example: DATA_LOADER_MAX_FILE_SIZE_MB -> max_file_size_mb
        """

        model_config = SettingsConfigDict(env_prefix="DATA_LOADER_")

        max_file_size_mb: int = Field(default=500, description="Maximum file size in megabytes")
        default_chunk_size: int = Field(default=10000, description="Default chunk size for chunked loading")
        max_memory_usage_mb: int = Field(default=2000, description="Maximum memory usage in megabytes")
        enable_schema_inference: bool = Field(
            default=True,
            description="Whether to enable automatic schema inference",
        )
        enable_quality_validation: bool = Field(
            default=True,
            description="Whether to enable data quality validation",
        )
        default_encoding: str = Field(
            default="utf-8",
            description="Default text encoding for file operations",
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize DataLoaderTool with settings.

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/data_loader.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)

        Args:
            config: Optional configuration overrides
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Initialize external tools
        self._init_external_tools()

    def _init_external_tools(self):
        """Initialize external task tools"""
        self.external_tools = {}

        # Initialize PandasTool for data operations
        try:
            from aiecs.tools.task_tools.pandas_tool import PandasTool

            self.external_tools["pandas"] = PandasTool()
            self.logger.info("PandasTool initialized successfully")
        except ImportError:
            self.logger.warning("PandasTool not available")
            self.external_tools["pandas"] = None

    # Schema definitions
    class LoadDataSchema(BaseModel):
        """Schema for load_data operation"""

        source: str = Field(description="Path to data source file")
        source_type: Optional[DataSourceType] = Field(default=DataSourceType.AUTO, description="Data source type")
        strategy: LoadStrategy = Field(default=LoadStrategy.FULL_LOAD, description="Loading strategy")
        data_schema: Optional[Dict[str, Any]] = Field(default=None, description="Expected schema for validation")
        validation_rules: Optional[Dict[str, Any]] = Field(default=None, description="Data quality validation rules")
        nrows: Optional[int] = Field(default=None, description="Number of rows to load")
        chunk_size: Optional[int] = Field(default=None, description="Chunk size for chunked loading")
        encoding: Optional[str] = Field(default=None, description="File encoding")

    class DetectFormatSchema(BaseModel):
        """Schema for detect_format operation"""

        source: str = Field(description="Path to data source file")

    class ValidateSchemaSchema(BaseModel):
        """Schema for validate_schema operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data to validate")
        data_schema: Dict[str, Any] = Field(description="Expected schema")

    class StreamDataSchema(BaseModel):
        """Schema for stream_data operation"""

        source: str = Field(description="Path to data source file")
        chunk_size: int = Field(default=10000, description="Chunk size for streaming")
        source_type: Optional[DataSourceType] = Field(default=DataSourceType.AUTO, description="Data source type")

    def load_data(
        self,
        source: str,
        source_type: DataSourceType = DataSourceType.AUTO,
        strategy: LoadStrategy = LoadStrategy.FULL_LOAD,
        schema: Optional[Dict[str, Any]] = None,
        validation_rules: Optional[Dict[str, Any]] = None,
        nrows: Optional[int] = None,
        chunk_size: Optional[int] = None,
        encoding: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load data from source with automatic format detection.

        Args:
            source: Path to data source file
            source_type: Type of data source (auto-detected if not specified)
            strategy: Loading strategy to use
            schema: Expected schema for validation
            validation_rules: Data quality validation rules
            nrows: Number of rows to load (None for all)
            chunk_size: Chunk size for chunked loading
            encoding: File encoding

        Returns:
            Dict containing:
                - data: Loaded DataFrame or data structure
                - metadata: Metadata about loaded data
                - quality_report: Quality assessment results

        Raises:
            DataLoaderError: If loading fails
            FileFormatError: If format is unsupported
        """
        try:
            # Validate source exists
            if not os.path.exists(source):
                raise DataLoaderError(f"Source file not found: {source}")

            # Detect format if auto
            if source_type == DataSourceType.AUTO:
                source_type = self._detect_format(source)

            # Check file size
            file_size_mb = os.path.getsize(source) / (1024 * 1024)
            if file_size_mb > self.config.max_file_size_mb:
                self.logger.warning(f"File size {file_size_mb:.2f}MB exceeds recommended limit")

            # Load data based on strategy
            if strategy == LoadStrategy.FULL_LOAD:
                data = self._load_full(source, source_type, nrows, encoding)
            elif strategy == LoadStrategy.CHUNKED:
                data = self._load_chunked(
                    source,
                    source_type,
                    chunk_size or self.config.default_chunk_size,
                    encoding,
                )
            elif strategy == LoadStrategy.STREAMING:
                data = self._load_streaming(
                    source,
                    source_type,
                    chunk_size or self.config.default_chunk_size,
                    encoding,
                )
            elif strategy == LoadStrategy.LAZY:
                data = self._load_lazy(source, source_type, encoding)
            else:
                raise DataLoaderError(f"Unsupported loading strategy: {strategy}")

            # Generate metadata
            metadata = self._generate_metadata(data, source, source_type)

            # Validate schema if provided
            if schema and self.config.enable_schema_inference:
                schema_valid = self._validate_schema_internal(data, schema)
                metadata["schema_valid"] = schema_valid

            # Validate quality if enabled
            quality_report = {}
            if self.config.enable_quality_validation and isinstance(data, pd.DataFrame):
                quality_report = self._validate_quality(data, validation_rules)

            self.logger.info(f"Successfully loaded data from {source}")

            return {
                "data": data,
                "metadata": metadata,
                "quality_report": quality_report,
                "source": source,
                "source_type": source_type.value,
                "strategy": strategy.value,
            }

        except Exception as e:
            self.logger.error(f"Error loading data from {source}: {e}")
            raise DataLoaderError(f"Failed to load data: {e}")

    def detect_format(self, source: str) -> Dict[str, Any]:
        """
        Detect file format from source.

        Args:
            source: Path to data source file

        Returns:
            Dict containing detected format information
        """
        try:
            detected_type = self._detect_format(source)

            return {
                "source": source,
                "detected_type": detected_type.value,
                "file_extension": Path(source).suffix.lower(),
                "confidence": "high",
            }
        except Exception as e:
            self.logger.error(f"Error detecting format: {e}")
            raise FileFormatError(f"Failed to detect format: {e}")

    def validate_schema(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate data against expected schema.

        Args:
            data: Data to validate
            schema: Expected schema definition

        Returns:
            Dict containing validation results
        """
        try:
            # Convert to DataFrame if needed
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = data

            is_valid = self._validate_schema_internal(df, schema)

            issues = []
            if not is_valid:
                # Check column presence
                expected_columns = set(schema.get("columns", {}).keys())
                actual_columns = set(df.columns)
                missing = expected_columns - actual_columns
                extra = actual_columns - expected_columns

                if missing:
                    issues.append(f"Missing columns: {missing}")
                if extra:
                    issues.append(f"Extra columns: {extra}")

            return {
                "valid": is_valid,
                "issues": issues,
                "expected_columns": list(schema.get("columns", {}).keys()),
                "actual_columns": list(df.columns),
            }

        except Exception as e:
            self.logger.error(f"Error validating schema: {e}")
            raise SchemaValidationError(f"Schema validation failed: {e}")

    def stream_data(
        self,
        source: str,
        chunk_size: int = 10000,
        source_type: DataSourceType = DataSourceType.AUTO,
    ) -> Dict[str, Any]:
        """
        Stream data in chunks for large files.

        Args:
            source: Path to data source file
            chunk_size: Size of each chunk
            source_type: Type of data source

        Returns:
            Dict containing streaming iterator information
        """
        try:
            if source_type == DataSourceType.AUTO:
                source_type = self._detect_format(source)

            # Create iterator based on format
            if source_type == DataSourceType.CSV:
                iterator = pd.read_csv(source, chunksize=chunk_size)
            elif source_type == DataSourceType.JSON:
                iterator = pd.read_json(source, lines=True, chunksize=chunk_size)
            else:
                raise FileFormatError(f"Streaming not supported for format: {source_type}")

            return {
                "iterator": iterator,
                "chunk_size": chunk_size,
                "source_type": source_type.value,
                "message": "Streaming iterator created successfully",
            }

        except Exception as e:
            self.logger.error(f"Error creating stream: {e}")
            raise DataLoaderError(f"Failed to create stream: {e}")

    # Internal helper methods

    def _detect_format(self, source: str) -> DataSourceType:
        """Detect file format from extension"""
        ext = Path(source).suffix.lower()

        format_map = {
            ".csv": DataSourceType.CSV,
            ".xlsx": DataSourceType.EXCEL,
            ".xls": DataSourceType.EXCEL,
            ".json": DataSourceType.JSON,
            ".parquet": DataSourceType.PARQUET,
            ".feather": DataSourceType.FEATHER,
            ".h5": DataSourceType.HDF5,
            ".hdf": DataSourceType.HDF5,
            ".dta": DataSourceType.STATA,
            ".sas7bdat": DataSourceType.SAS,
            ".sav": DataSourceType.SPSS,
        }

        detected = format_map.get(ext)
        if not detected:
            raise FileFormatError(f"Unsupported file format: {ext}")

        return detected

    def _load_full(
        self,
        source: str,
        source_type: DataSourceType,
        nrows: Optional[int],
        encoding: Optional[str],
    ) -> pd.DataFrame:
        """Load entire dataset into memory"""
        encoding = encoding or self.config.default_encoding

        if source_type == DataSourceType.CSV:
            return pd.read_csv(source, nrows=nrows, encoding=encoding)
        elif source_type == DataSourceType.EXCEL:
            return pd.read_excel(source, nrows=nrows)
        elif source_type == DataSourceType.JSON:
            return pd.read_json(source, nrows=nrows, encoding=encoding)
        elif source_type == DataSourceType.PARQUET:
            return pd.read_parquet(source)
        elif source_type == DataSourceType.FEATHER:
            return pd.read_feather(source)
        elif source_type == DataSourceType.HDF5:
            return pd.read_hdf(source)
        elif source_type == DataSourceType.STATA:
            df = pd.read_stata(source)
            if nrows:
                return df.head(nrows)
            return df
        elif source_type == DataSourceType.SAS:
            return pd.read_sas(source)
        elif source_type == DataSourceType.SPSS:
            try:
                import pyreadstat  # type: ignore[import-untyped]

                df, meta = pyreadstat.read_sav(source)
                return df
            except ImportError:
                raise DataLoaderError("pyreadstat required for SPSS files")
        else:
            raise FileFormatError(f"Unsupported format for full load: {source_type}")

    def _load_chunked(
        self,
        source: str,
        source_type: DataSourceType,
        chunk_size: int,
        encoding: Optional[str],
    ) -> pd.DataFrame:
        """Load data in chunks and combine"""
        encoding = encoding or self.config.default_encoding
        chunks = []

        if source_type == DataSourceType.CSV:
            for chunk in pd.read_csv(source, chunksize=chunk_size, encoding=encoding):
                chunks.append(chunk)
        elif source_type == DataSourceType.JSON:
            for chunk in pd.read_json(source, lines=True, chunksize=chunk_size, encoding=encoding):
                chunks.append(chunk)
        else:
            raise FileFormatError(f"Chunked loading not supported for: {source_type}")

        return pd.concat(chunks, ignore_index=True)

    def _load_streaming(
        self,
        source: str,
        source_type: DataSourceType,
        chunk_size: int,
        encoding: Optional[str],
    ) -> Iterator[pd.DataFrame]:
        """Create streaming iterator"""
        encoding = encoding or self.config.default_encoding

        if source_type == DataSourceType.CSV:
            return pd.read_csv(source, chunksize=chunk_size, encoding=encoding)
        elif source_type == DataSourceType.JSON:
            return pd.read_json(source, lines=True, chunksize=chunk_size, encoding=encoding)
        else:
            raise FileFormatError(f"Streaming not supported for: {source_type}")

    def _load_lazy(self, source: str, source_type: DataSourceType, encoding: Optional[str]) -> Any:
        """Create lazy loading wrapper"""
        # For now, return full load with warning
        self.logger.warning("Lazy loading not fully implemented, using full load")
        return self._load_full(source, source_type, None, encoding)

    def _generate_metadata(self, data: Any, source: str, source_type: DataSourceType) -> Dict[str, Any]:
        """Generate metadata about loaded data"""
        if isinstance(data, pd.DataFrame):
            return {
                "rows": len(data),
                "columns": len(data.columns),
                "column_names": list(data.columns),
                "dtypes": {col: str(dtype) for col, dtype in data.dtypes.items()},
                "memory_usage_mb": data.memory_usage(deep=True).sum() / (1024 * 1024),
                "file_size_mb": os.path.getsize(source) / (1024 * 1024),
            }
        else:
            return {
                "type": str(type(data)),
                "file_size_mb": os.path.getsize(source) / (1024 * 1024),
            }

    def _validate_schema_internal(self, data: pd.DataFrame, schema: Dict[str, Any]) -> bool:
        """Internal schema validation"""
        if "columns" not in schema:
            return True

        expected_columns = set(schema["columns"].keys())
        actual_columns = set(data.columns)

        return expected_columns.issubset(actual_columns)

    def _validate_quality(self, data: pd.DataFrame, validation_rules: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate data quality"""
        quality_report = {
            "total_rows": len(data),
            "total_columns": len(data.columns),
            "missing_values": data.isnull().sum().to_dict(),
            "duplicate_rows": data.duplicated().sum(),
            "quality_score": 1.0,
        }

        # Calculate quality score
        missing_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns)) if len(data) > 0 else 0
        duplicate_ratio = quality_report["duplicate_rows"] / len(data) if len(data) > 0 else 0

        quality_score = 1.0 - (missing_ratio * 0.5 + duplicate_ratio * 0.5)
        quality_report["quality_score"] = max(0.0, min(1.0, quality_score))

        # Add issues list
        issues = []
        if missing_ratio > 0.1:
            issues.append(f"High missing value ratio: {missing_ratio:.2%}")
        if duplicate_ratio > 0.05:
            issues.append(f"High duplicate ratio: {duplicate_ratio:.2%}")

        quality_report["issues"] = issues

        return quality_report
