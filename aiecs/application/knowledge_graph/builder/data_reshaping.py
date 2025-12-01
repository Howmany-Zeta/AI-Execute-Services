"""
Data Reshaping for Knowledge Graph Import

Provides utilities to convert wide format data to normalized graph structures
and vice versa, enabling efficient import of datasets with many columns.
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Check for pandas availability
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@dataclass
class ReshapeResult:
    """
    Result of data reshaping operation
    
    Attributes:
        data: Reshaped DataFrame
        original_shape: Original (rows, cols) shape
        new_shape: New (rows, cols) shape
        id_columns: Columns used as identifiers
        variable_column: Name of variable column (for melt)
        value_column: Name of value column (for melt)
        warnings: List of warnings
    """
    data: 'pd.DataFrame'
    original_shape: tuple
    new_shape: tuple
    id_columns: List[str]
    variable_column: Optional[str] = None
    value_column: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class DataReshaping:
    """
    Utility class for reshaping structured data
    
    Provides methods to convert between wide and long formats,
    enabling normalized graph structures from wide datasets.
    """
    
    @staticmethod
    def melt(
        df: 'pd.DataFrame',
        id_vars: List[str],
        value_vars: Optional[List[str]] = None,
        var_name: str = 'variable',
        value_name: str = 'value',
        dropna: bool = True,
    ) -> ReshapeResult:
        """
        Convert wide format to long format (melt operation)
        
        Transforms data from wide format (many columns) to long format
        (fewer columns, more rows), which is ideal for normalized graph structures.
        
        Args:
            df: DataFrame to reshape
            id_vars: Columns to use as identifier variables
            value_vars: Columns to unpivot (default: all columns except id_vars)
            var_name: Name for the variable column (default: 'variable')
            value_name: Name for the value column (default: 'value')
            dropna: Whether to drop rows with missing values (default: True)
        
        Returns:
            ReshapeResult with reshaped data and metadata
        
        Example:
            ```python
            # Wide format: sample_id, option1, option2, option3
            # Long format: sample_id, variable, value
            
            result = DataReshaping.melt(
                df,
                id_vars=['sample_id'],
                value_vars=['option1', 'option2', 'option3'],
                var_name='option_name',
                value_name='option_value'
            )
            ```
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for data reshaping")
        
        original_shape = df.shape
        warnings = []
        
        # If value_vars not specified, use all columns except id_vars
        if value_vars is None:
            value_vars = [col for col in df.columns if col not in id_vars]
            warnings.append(f"Auto-detected {len(value_vars)} value columns")
        
        # Perform melt operation
        melted = pd.melt(
            df,
            id_vars=id_vars,
            value_vars=value_vars,
            var_name=var_name,
            value_name=value_name,
        )
        
        # Drop NA values if requested
        if dropna:
            rows_before = len(melted)
            melted = melted.dropna(subset=[value_name])
            rows_dropped = rows_before - len(melted)
            if rows_dropped > 0:
                warnings.append(f"Dropped {rows_dropped} rows with missing values")
        
        new_shape = melted.shape
        
        return ReshapeResult(
            data=melted,
            original_shape=original_shape,
            new_shape=new_shape,
            id_columns=id_vars,
            variable_column=var_name,
            value_column=value_name,
            warnings=warnings,
        )

    @staticmethod
    def pivot(
        df: 'pd.DataFrame',
        index: Union[str, List[str]],
        columns: str,
        values: str,
        aggfunc: str = 'first',
        fill_value: Optional[Any] = None,
    ) -> ReshapeResult:
        """
        Convert long format to wide format (pivot operation)

        Transforms data from long format to wide format, creating columns
        from unique values in the specified column.

        Args:
            df: DataFrame to reshape
            index: Column(s) to use as index (identifier)
            columns: Column whose unique values become new columns
            values: Column containing values to populate the new columns
            aggfunc: Aggregation function if multiple values per group (default: 'first')
            fill_value: Value to use for missing data (default: None)

        Returns:
            ReshapeResult with reshaped data and metadata

        Example:
            ```python
            # Long format: sample_id, option_name, option_value
            # Wide format: sample_id, option1, option2, option3

            result = DataReshaping.pivot(
                df,
                index='sample_id',
                columns='option_name',
                values='option_value'
            )
            ```
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for data reshaping")

        original_shape = df.shape
        warnings = []

        # Perform pivot operation
        try:
            pivoted = df.pivot_table(
                index=index,
                columns=columns,
                values=values,
                aggfunc=aggfunc,
                fill_value=fill_value,
            )

            # Reset index to make it a regular column
            pivoted = pivoted.reset_index()

            # Flatten column names if multi-level
            if isinstance(pivoted.columns, pd.MultiIndex):
                pivoted.columns = ['_'.join(map(str, col)).strip('_') for col in pivoted.columns.values]
                warnings.append("Flattened multi-level column names")

        except Exception as e:
            raise ValueError(f"Pivot operation failed: {e}")

        new_shape = pivoted.shape

        # Determine id_columns
        if isinstance(index, str):
            id_columns = [index]
        else:
            id_columns = list(index)

        return ReshapeResult(
            data=pivoted,
            original_shape=original_shape,
            new_shape=new_shape,
            id_columns=id_columns,
            warnings=warnings,
        )

    @staticmethod
    def detect_wide_format(
        df: 'pd.DataFrame',
        threshold_columns: int = 50,
    ) -> bool:
        """
        Detect if DataFrame is in wide format

        Wide format is characterized by many columns relative to rows.

        Args:
            df: DataFrame to analyze
            threshold_columns: Minimum number of columns to consider wide (default: 50)

        Returns:
            True if DataFrame appears to be in wide format
        """
        if not PANDAS_AVAILABLE:
            return False

        num_cols = len(df.columns)
        num_rows = len(df)

        # Wide format indicators:
        # 1. Many columns (>= threshold)
        # 2. More columns than rows (or close to it) AND at least 20 columns
        is_wide = num_cols >= threshold_columns or (num_cols >= 20 and num_cols > num_rows * 0.5)

        return is_wide

    @staticmethod
    def suggest_melt_config(
        df: 'pd.DataFrame',
        id_column_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Suggest melt configuration for wide format data

        Analyzes DataFrame structure to suggest appropriate id_vars and value_vars.

        Args:
            df: DataFrame to analyze
            id_column_patterns: Patterns to identify ID columns (default: ['id', 'key', 'name'])

        Returns:
            Dictionary with suggested melt configuration
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for data reshaping")

        if id_column_patterns is None:
            id_column_patterns = ['id', 'key', 'name', 'sample', 'subject']

        # Identify potential ID columns
        id_vars = []
        for col in df.columns:
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in id_column_patterns):
                id_vars.append(col)

        # If no ID columns found, use first column
        if not id_vars and len(df.columns) > 0:
            id_vars = [df.columns[0]]

        # Value columns are all other columns
        value_vars = [col for col in df.columns if col not in id_vars]

        return {
            'id_vars': id_vars,
            'value_vars': value_vars,
            'var_name': 'variable',
            'value_name': 'value',
            'confidence': 0.8 if id_vars else 0.5,
        }

