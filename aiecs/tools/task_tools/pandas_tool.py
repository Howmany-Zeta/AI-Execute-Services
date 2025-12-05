from io import StringIO
import pandas as pd  # type: ignore[import-untyped]
import numpy as np
from typing import List, Dict, Union, Optional, cast
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool

# Custom exceptions


class PandasToolError(Exception):
    """Base exception for PandasTool errors."""


class InputValidationError(PandasToolError):
    """Input validation error."""


class DataFrameError(PandasToolError):
    """DataFrame operation error."""


class SecurityError(PandasToolError):
    """Security-related error."""


class ValidationError(PandasToolError):
    """Validation error."""


@register_tool("pandas")
class PandasTool(BaseTool):
    """
    Tool encapsulating pandas functionality for data processing, supporting 30+ operations including:
      - Data reading/writing (CSV, JSON, Excel).
      - Descriptive statistics (summary, describe, value_counts).
      - Filtering and selection (filter, select_columns, drop_columns).
      - Grouping and aggregation (groupby, pivot_table).
      - Merging and concatenation (merge, concat).
      - Data transformation (sort_values, rename_columns, replace_values, fill_na, astype, apply).
      - Data reshaping (melt, pivot, stack, unstack).
      - Data cleaning (strip_strings, to_numeric, to_datetime).
      - Statistical computations (mean, sum, count, min, max).
      - Window functions (rolling).
      - Sampling and viewing (head, tail, sample).

    Inherits from BaseTool to leverage ToolExecutor for caching, concurrency, and error handling.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the pandas tool
        
        Automatically reads from environment variables with PANDAS_TOOL_ prefix.
        Example: PANDAS_TOOL_CSV_DELIMITER -> csv_delimiter
        """

        model_config = SettingsConfigDict(env_prefix="PANDAS_TOOL_")

        csv_delimiter: str = Field(default=",", description="Delimiter for CSV files")
        encoding: str = Field(default="utf-8", description="Encoding for file operations")
        default_agg: Dict[str, str] = Field(
            default={"numeric": "mean", "object": "count"},
            description="Default aggregation functions",
        )
        chunk_size: int = Field(default=10000, description="Chunk size for large file processing")
        max_csv_size: int = Field(default=1000000, description="Threshold for chunked CSV processing")
        allowed_file_extensions: List[str] = Field(
            default=[".csv", ".xlsx", ".json"],
            description="Allowed file extensions",
        )

    def __init__(self, config: Optional[Dict] = None, **kwargs):
        """
        Initialize PandasTool with configuration.

        Args:
            config (Dict, optional): Configuration overrides for PandasTool.
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Raises:
            ValueError: If config is invalid.

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/pandas.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)
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

    def _validate_df(self, records: List[Dict]) -> pd.DataFrame:
        """
        Convert records to a DataFrame and validate.

        Args:
            records (List[Dict]): List of records to convert.

        Returns:
            pd.DataFrame: Validated DataFrame.

        Raises:
            InputValidationError: If records are empty or invalid.
        """
        if not records:
            raise InputValidationError("Records list is empty")
        try:
            df = pd.DataFrame(records)
            if df.empty:
                raise InputValidationError("DataFrame is empty")
            return df
        except Exception as e:
            raise InputValidationError(f"Failed to create DataFrame: {e}")

    def _validate_columns(self, df: pd.DataFrame, columns: List[str]) -> None:
        """
        Validate column names exist in DataFrame.

        Args:
            df (pd.DataFrame): DataFrame to validate.
            columns (List[str]): Columns to check.

        Raises:
            InputValidationError: If columns are not found.
        """
        if not columns:
            return
        available_columns = set(df.columns)
        missing = [col for col in columns if col not in available_columns]
        if missing:
            raise InputValidationError(f"Columns not found: {missing}. Available columns: {list(available_columns)}")

    def _to_json_serializable(self, result: Union[pd.DataFrame, pd.Series, Dict]) -> Union[List[Dict], Dict]:
        """
        Convert result to JSON-serializable format.

        Args:
            result (Union[pd.DataFrame, pd.Series, Dict]): Result to convert.

        Returns:
            Union[List[Dict], Dict]: JSON-serializable result.
        """
        if isinstance(result, pd.DataFrame):
            for col in result.select_dtypes(include=["datetime64"]).columns:
                result[col] = result[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            return result.to_dict(orient="records")
        elif isinstance(result, pd.Series):
            if pd.api.types.is_datetime64_any_dtype(result):
                result = result.dt.strftime("%Y-%m-%d %H:%M:%S")
            return result.to_dict()
        elif isinstance(result, dict):

            def convert_value(v):
                if isinstance(v, (np.floating, np.integer)):
                    return float(v)
                elif isinstance(v, np.bool_):
                    return bool(v)
                elif isinstance(v, (pd.Timestamp, np.datetime64)):
                    return str(v)
                elif isinstance(v, np.ndarray):
                    return v.tolist()
                elif pd.isna(v):
                    return None
                return v

            return {k: convert_value(v) for k, v in result.items()}
        return result

    def read_csv(self, csv_str: str) -> List[Dict]:
        """Read CSV string into a DataFrame."""
        try:
            if len(csv_str) > self.config.max_csv_size:
                chunks = []
                for chunk in pd.read_csv(
                    StringIO(csv_str),
                    sep=self.config.csv_delimiter,
                    encoding=self.config.encoding,
                    chunksize=self.config.chunk_size,
                ):
                    chunks.append(chunk)
                df = pd.concat(chunks)
            else:
                df = pd.read_csv(
                    StringIO(csv_str),
                    sep=self.config.csv_delimiter,
                    encoding=self.config.encoding,
                )
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Failed to read CSV: {e}")

    def read_json(self, json_str: str) -> List[Dict]:
        """Read JSON string into a DataFrame."""
        try:
            df = pd.read_json(StringIO(json_str))
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Failed to read JSON: {e}")

    def read_file(self, file_path: str, file_type: str = "csv") -> List[Dict]:
        """Read data from a file (CSV, Excel, JSON)."""
        try:
            if file_type == "csv":
                file_size = sum(1 for _ in open(file_path, "r", encoding=self.config.encoding))
                if file_size > self.config.chunk_size:
                    chunks = []
                    for chunk in pd.read_csv(
                        file_path,
                        sep=self.config.csv_delimiter,
                        encoding=self.config.encoding,
                        chunksize=self.config.chunk_size,
                    ):
                        chunks.append(chunk)
                    df = pd.concat(chunks)
                else:
                    df = pd.read_csv(
                        file_path,
                        sep=self.config.csv_delimiter,
                        encoding=self.config.encoding,
                    )
            elif file_type == "excel":
                df = pd.read_excel(file_path)
            elif file_type == "json":
                df = pd.read_json(file_path)
            else:
                raise ValidationError(f"Unsupported file type: {file_type}")
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except ValidationError:
            raise
        except Exception as e:
            raise DataFrameError(f"Failed to read file: {e}")

    def write_file(self, records: List[Dict], file_path: str, file_type: str = "csv") -> Dict:
        """Write DataFrame to a file."""
        df = self._validate_df(records)
        try:
            if file_type == "csv":
                df.to_csv(
                    file_path,
                    index=False,
                    sep=self.config.csv_delimiter,
                    encoding=self.config.encoding,
                )
            elif file_type == "excel":
                df.to_excel(file_path, index=False)
            elif file_type == "json":
                df.to_json(file_path, orient="records")
            else:
                raise ValidationError(f"Unsupported file type: {file_type}")
            return {"success": True, "file_path": file_path, "rows": len(df)}
        except Exception as e:
            raise DataFrameError(f"Failed to write file: {e}")

    def summary(self, records: List[Dict]) -> Dict:
        """Compute summary statistics for DataFrame."""
        df = self._validate_df(records)
        desc = df.describe(include="all").to_dict()
        result = self._to_json_serializable(desc)
        return cast(Dict, result)

    def describe(self, records: List[Dict], columns: Optional[List[str]] = None) -> Dict:
        """Compute descriptive statistics for specified columns."""
        df = self._validate_df(records)
        if columns:
            self._validate_columns(df, columns)
            df = df[columns]
        desc = df.describe().to_dict()
        result = self._to_json_serializable(desc)
        return cast(Dict, result)

    def value_counts(self, records: List[Dict], columns: List[str]) -> Dict:
        """Compute value counts for specified columns."""
        df = self._validate_df(records)
        self._validate_columns(df, columns)
        result = {col: df[col].value_counts().to_dict() for col in columns}
        converted = self._to_json_serializable(result)
        return cast(Dict, converted)

    def filter(self, records: List[Dict], condition: str) -> List[Dict]:
        """Filter DataFrame based on a condition."""
        df = self._validate_df(records)
        try:
            df = df.query(condition, engine="python")
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Invalid query condition: {e}")

    def select_columns(self, records: List[Dict], columns: List[str]) -> List[Dict]:
        """Select specified columns from DataFrame."""
        df = self._validate_df(records)
        self._validate_columns(df, columns)
        result = self._to_json_serializable(df[columns])
        return cast(List[Dict], result)

    def drop_columns(self, records: List[Dict], columns: List[str]) -> List[Dict]:
        """Drop specified columns from DataFrame."""
        df = self._validate_df(records)
        self._validate_columns(df, columns)
        result = self._to_json_serializable(df.drop(columns=columns))
        return cast(List[Dict], result)

    def drop_duplicates(self, records: List[Dict], columns: Optional[List[str]] = None) -> List[Dict]:
        """Drop duplicate rows based on specified columns."""
        df = self._validate_df(records)
        if columns:
            self._validate_columns(df, columns)
        result = self._to_json_serializable(df.drop_duplicates(subset=columns))
        return cast(List[Dict], result)

    def dropna(self, records: List[Dict], axis: int = 0, how: str = "any") -> List[Dict]:
        """Drop rows or columns with missing values."""
        df = self._validate_df(records)
        if how not in ["any", "all"]:
            raise ValidationError("how must be 'any' or 'all'")
        result = self._to_json_serializable(df.dropna(axis=axis, how=how))
        return cast(List[Dict], result)

    def groupby(self, records: List[Dict], by: List[str], agg: Dict[str, str]) -> List[Dict]:
        """Group DataFrame and apply aggregations."""
        df = self._validate_df(records)
        self._validate_columns(df, by + list(agg.keys()))
        try:
            df = df.groupby(by).agg(agg).reset_index()
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Groupby failed: {e}")

    def pivot_table(
        self,
        records: List[Dict],
        values: List[str],
        index: List[str],
        columns: List[str],
        aggfunc: str = "mean",
    ) -> List[Dict]:
        """Create a pivot table from DataFrame."""
        df = self._validate_df(records)
        self._validate_columns(df, values + index + columns)
        try:
            df = pd.pivot_table(
                df,
                values=values,
                index=index,
                columns=columns,
                aggfunc=aggfunc,
            )
            result = self._to_json_serializable(df.reset_index())
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Pivot table failed: {e}")

    def merge(
        self,
        records: List[Dict],
        records_right: List[Dict],
        on: Union[str, List[str]],
        join_type: str = "inner",
    ) -> List[Dict]:
        """Merge two DataFrames."""
        df_left = self._validate_df(records)
        df_right = self._validate_df(records_right)
        if join_type not in ["inner", "left", "right", "outer"]:
            raise ValidationError("join_type must be one of: inner, left, right, outer")
        self._validate_columns(df_left, [on] if isinstance(on, str) else on)
        self._validate_columns(df_right, [on] if isinstance(on, str) else on)
        try:
            df = df_left.merge(df_right, on=on, how=join_type)
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Merge failed: {e}")

    def concat(self, records_list: List[List[Dict]], axis: int = 0) -> List[Dict]:
        """Concatenate multiple DataFrames."""
        if not records_list or not all(records_list):
            raise ValidationError("Records list is empty")
        dfs = [self._validate_df(records) for records in records_list]
        try:
            df = pd.concat(dfs, axis=axis, ignore_index=True)
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Concat failed: {e}")

    def sort_values(
        self,
        records: List[Dict],
        sort_by: List[str],
        ascending: Union[bool, List[bool]] = True,
    ) -> List[Dict]:
        """Sort DataFrame by specified columns."""
        df = self._validate_df(records)
        self._validate_columns(df, sort_by)
        try:
            df = df.sort_values(by=sort_by, ascending=ascending)
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Sort failed: {e}")

    def rename_columns(self, records: List[Dict], mapping: Dict[str, str]) -> List[Dict]:
        """Rename DataFrame columns."""
        df = self._validate_df(records)
        self._validate_columns(df, list(mapping.keys()))
        result = self._to_json_serializable(df.rename(columns=mapping))
        return cast(List[Dict], result)

    def replace_values(
        self,
        records: List[Dict],
        to_replace: Dict,
        columns: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Replace values in DataFrame."""
        df = self._validate_df(records)
        if columns:
            self._validate_columns(df, columns)
            df = df[columns]
        result = self._to_json_serializable(df.replace(to_replace))
        return cast(List[Dict], result)

    def fill_na(
        self,
        records: List[Dict],
        value: Union[str, int, float],
        columns: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Fill missing values in DataFrame."""
        df = self._validate_df(records)
        if columns:
            self._validate_columns(df, columns)
            df[columns] = df[columns].fillna(value)
        else:
            df = df.fillna(value)
        result = self._to_json_serializable(df)
        return cast(List[Dict], result)

    def astype(self, records: List[Dict], dtypes: Dict[str, str]) -> List[Dict]:
        """Convert column types in DataFrame."""
        df = self._validate_df(records)
        self._validate_columns(df, list(dtypes.keys()))
        try:
            df = df.astype(dtypes)
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Type conversion failed: {e}")

    def apply(self, records: List[Dict], func: str, columns: List[str], axis: int = 0) -> List[Dict]:
        """Apply a function to specified columns or rows."""
        df = self._validate_df(records)
        self._validate_columns(df, columns)
        allowed_funcs = {
            "upper": lambda x: x.upper() if isinstance(x, str) else x,
            "lower": lambda x: x.lower() if isinstance(x, str) else x,
            "strip": lambda x: x.strip() if isinstance(x, str) else x,
            "capitalize": lambda x: (x.capitalize() if isinstance(x, str) else x),
            "title": lambda x: x.title() if isinstance(x, str) else x,
            "len": lambda x: len(str(x)) if pd.notna(x) else 0,
            "abs": lambda x: (abs(float(x)) if pd.notna(x) and not isinstance(x, str) else x),
            "round": lambda x: (round(float(x)) if pd.notna(x) and not isinstance(x, str) else x),
            "ceil": lambda x: (np.ceil(float(x)) if pd.notna(x) and not isinstance(x, str) else x),
            "floor": lambda x: (np.floor(float(x)) if pd.notna(x) and not isinstance(x, str) else x),
            "int": lambda x: (int(float(x)) if pd.notna(x) and not isinstance(x, str) else None),
            "float": lambda x: (float(x) if pd.notna(x) and not isinstance(x, str) else None),
            "str": lambda x: str(x) if pd.notna(x) else "",
            "bool": lambda x: bool(x) if pd.notna(x) else False,
            "date_only": lambda x: (x.date() if isinstance(x, pd.Timestamp) else x),
            "year": lambda x: x.year if isinstance(x, pd.Timestamp) else None,
            "month": lambda x: (x.month if isinstance(x, pd.Timestamp) else None),
            "day": lambda x: x.day if isinstance(x, pd.Timestamp) else None,
        }
        try:
            if axis == 0:
                for col in columns:
                    df[col] = df[col].apply(allowed_funcs[func])
            else:
                df[columns] = df[columns].apply(allowed_funcs[func], axis=1)
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Apply failed: {e}")

    def melt(self, records: List[Dict], id_vars: List[str], value_vars: List[str]) -> List[Dict]:
        """Melt DataFrame to long format."""
        df = self._validate_df(records)
        self._validate_columns(df, id_vars + value_vars)
        try:
            df = pd.melt(df, id_vars=id_vars, value_vars=value_vars)
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Melt failed: {e}")

    def pivot(self, records: List[Dict], index: str, columns: str, values: str) -> List[Dict]:
        """Pivot DataFrame to wide format."""
        df = self._validate_df(records)
        self._validate_columns(df, [index, columns, values])
        try:
            df = df.pivot(index=index, columns=columns, values=values)
            result = self._to_json_serializable(df.reset_index())
            # Ensure we return a list
            if isinstance(result, dict):
                return [result]
            return result
        except Exception as e:
            raise DataFrameError(f"Pivot failed: {e}")

    def stack(self, records: List[Dict]) -> List[Dict]:
        """Stack DataFrame columns into rows."""
        df = self._validate_df(records)
        try:
            df = df.stack().reset_index()
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Stack failed: {e}")

    def unstack(self, records: List[Dict], level: Union[int, str] = -1) -> List[Dict]:
        """Unstack DataFrame rows into columns."""
        df = self._validate_df(records)
        try:
            df = df.unstack(level=level).reset_index()
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Unstack failed: {e}")

    def strip_strings(self, records: List[Dict], columns: List[str]) -> List[Dict]:
        """Strip whitespace from string columns."""
        df = self._validate_df(records)
        self._validate_columns(df, columns)
        for col in columns:
            if df[col].dtype == "object":
                df[col] = df[col].str.strip()
        result = self._to_json_serializable(df)
        return cast(List[Dict], result)

    def to_numeric(self, records: List[Dict], columns: List[str]) -> List[Dict]:
        """Convert columns to numeric type."""
        df = self._validate_df(records)
        self._validate_columns(df, columns)
        try:
            for col in columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"To numeric failed: {e}")

    def to_datetime(
        self,
        records: List[Dict],
        columns: List[str],
        format: Optional[str] = None,
    ) -> List[Dict]:
        """Convert columns to datetime type."""
        df = self._validate_df(records)
        self._validate_columns(df, columns)
        try:
            for col in columns:
                df[col] = pd.to_datetime(df[col], format=format, errors="coerce")
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"To datetime failed: {e}")

    def mean(self, records: List[Dict], columns: Optional[List[str]] = None) -> Dict:
        """Compute mean of numeric columns."""
        df = self._validate_df(records)
        if columns:
            self._validate_columns(df, columns)
            df = df[columns]
        result = self._to_json_serializable(df.select_dtypes(include=np.number).mean())
        return cast(Dict, result)

    def sum(self, records: List[Dict], columns: Optional[List[str]] = None) -> Dict:
        """Compute sum of numeric columns."""
        df = self._validate_df(records)
        if columns:
            self._validate_columns(df, columns)
            df = df[columns]
        result = self._to_json_serializable(df.select_dtypes(include=np.number).sum())
        return cast(Dict, result)

    def count(self, records: List[Dict], columns: Optional[List[str]] = None) -> Dict:
        """Compute count of non-null values."""
        df = self._validate_df(records)
        if columns:
            self._validate_columns(df, columns)
            df = df[columns]
        result = self._to_json_serializable(df.count())
        return cast(Dict, result)

    def min(self, records: List[Dict], columns: Optional[List[str]] = None) -> Dict:
        """Compute minimum values."""
        df = self._validate_df(records)
        if columns:
            self._validate_columns(df, columns)
            df = df[columns]
        result = self._to_json_serializable(df.min())
        return cast(Dict, result)

    def max(self, records: List[Dict], columns: Optional[List[str]] = None) -> Dict:
        """Compute maximum values."""
        df = self._validate_df(records)
        if columns:
            self._validate_columns(df, columns)
            df = df[columns]
        result = self._to_json_serializable(df.max())
        return cast(Dict, result)

    def rolling(
        self,
        records: List[Dict],
        columns: List[str],
        window: int,
        function: str = "mean",
    ) -> List[Dict]:
        """Apply rolling window function to columns."""
        df = self._validate_df(records)
        self._validate_columns(df, columns)
        allowed_funcs = ["mean", "sum", "min", "max", "std", "count", "median"]
        if function not in allowed_funcs:
            raise ValidationError(f"Function '{function}' not allowed. Available: {allowed_funcs}")
        try:
            for col in columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[f"{col}_{function}_{window}"] = getattr(df[col].rolling(window), function)()
            result = self._to_json_serializable(df)
            return cast(List[Dict], result)
        except Exception as e:
            raise DataFrameError(f"Rolling operation failed: {e}")

    def head(self, records: List[Dict], n: int = 5) -> List[Dict]:
        """Return first n rows of DataFrame."""
        df = self._validate_df(records)
        result = self._to_json_serializable(df.head(n))
        return cast(List[Dict], result)

    def tail(self, records: List[Dict], n: int = 5) -> List[Dict]:
        """Return last n rows of DataFrame."""
        df = self._validate_df(records)
        result = self._to_json_serializable(df.tail(n))
        return cast(List[Dict], result)

    def sample(
        self,
        records: List[Dict],
        n: int = 5,
        random_state: Optional[int] = None,
    ) -> List[Dict]:
        """Return random sample of n rows from DataFrame."""
        df = self._validate_df(records)
        result = self._to_json_serializable(df.sample(n=min(n, len(df)), random_state=random_state))
        return cast(List[Dict], result)
