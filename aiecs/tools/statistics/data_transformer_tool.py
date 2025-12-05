"""
Data Transformer Tool - Data cleaning, transformation, and feature engineering

This tool provides comprehensive data transformation capabilities with:
- Data cleaning and preprocessing
- Feature engineering and encoding
- Normalization and standardization
- Transformation pipelines
- Missing value handling
"""

import logging
from typing import Dict, Any, List, Optional, Union
from enum import Enum

import pandas as pd  # type: ignore[import-untyped]
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class TransformationType(str, Enum):
    """Types of transformations"""

    # Cleaning operations
    REMOVE_DUPLICATES = "remove_duplicates"
    FILL_MISSING = "fill_missing"
    REMOVE_OUTLIERS = "remove_outliers"

    # Transformation operations
    NORMALIZE = "normalize"
    STANDARDIZE = "standardize"
    LOG_TRANSFORM = "log_transform"
    BOX_COX = "box_cox"

    # Encoding operations
    ONE_HOT_ENCODE = "one_hot_encode"
    LABEL_ENCODE = "label_encode"
    TARGET_ENCODE = "target_encode"

    # Feature engineering
    POLYNOMIAL_FEATURES = "polynomial_features"
    INTERACTION_FEATURES = "interaction_features"
    BINNING = "binning"
    AGGREGATION = "aggregation"


class MissingValueStrategy(str, Enum):
    """Strategies for handling missing values"""

    DROP = "drop"
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    FORWARD_FILL = "forward_fill"
    BACKWARD_FILL = "backward_fill"
    INTERPOLATE = "interpolate"
    CONSTANT = "constant"


class DataTransformerError(Exception):
    """Base exception for DataTransformer errors"""


class TransformationError(DataTransformerError):
    """Raised when transformation fails"""


@register_tool("data_transformer")
class DataTransformerTool(BaseTool):
    """
    Advanced data transformation tool that can:
    1. Clean and preprocess data
    2. Engineer features
    3. Transform and normalize data
    4. Build transformation pipelines

    Integrates with pandas_tool for core operations.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the data transformer tool
        
        Automatically reads from environment variables with DATA_TRANSFORMER_ prefix.
        Example: DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD -> outlier_std_threshold
        """

        model_config = SettingsConfigDict(env_prefix="DATA_TRANSFORMER_")

        outlier_std_threshold: float = Field(
            default=3.0,
            description="Standard deviation threshold for outlier detection",
        )
        default_missing_strategy: str = Field(
            default="mean",
            description="Default strategy for handling missing values",
        )
        enable_pipeline_caching: bool = Field(
            default=True,
            description="Whether to enable transformation pipeline caching",
        )
        max_one_hot_categories: int = Field(
            default=10,
            description="Maximum number of categories for one-hot encoding",
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize DataTransformerTool with settings.

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/data_transformer.yaml)
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

        # Initialize transformation pipeline cache
        self.pipeline_cache: Dict[str, Any] = {}

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
    class TransformDataSchema(BaseModel):
        """Schema for transform_data operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data to transform")
        transformations: List[Dict[str, Any]] = Field(description="List of transformation steps")
        enable_validation: bool = Field(default=True, description="Validate transformations")

    class AutoTransformSchema(BaseModel):
        """Schema for auto_transform operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data to transform")
        target_column: Optional[str] = Field(default=None, description="Target column name")
        task_type: Optional[str] = Field(default=None, description="Task type: classification or regression")

    class HandleMissingValuesSchema(BaseModel):
        """Schema for handle_missing_values operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data with missing values")
        strategy: MissingValueStrategy = Field(
            default=MissingValueStrategy.MEAN,
            description="Strategy for handling missing values",
        )
        columns: Optional[List[str]] = Field(default=None, description="Specific columns to handle")
        fill_value: Optional[Any] = Field(default=None, description="Value for constant strategy")

    class EncodeFeaturesSchema(BaseModel):
        """Schema for encode_features operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data to encode")
        columns: List[str] = Field(description="Columns to encode")
        method: str = Field(default="one_hot", description="Encoding method: one_hot or label")

    def transform_data(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        transformations: List[Dict[str, Any]],
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Apply transformation pipeline to data.

        Args:
            data: Data to transform
            transformations: List of transformation steps, each containing:
                - type: TransformationType
                - columns: List of columns (optional)
                - params: Additional parameters
            validate: Whether to validate transformations

        Returns:
            Dict containing:
                - transformed_data: Transformed DataFrame
                - transformation_log: Log of applied transformations
                - quality_improvement: Quality metrics comparison

        Raises:
            TransformationError: If transformation fails
        """
        try:
            df = self._to_dataframe(data)
            original_df = df.copy()

            transformation_log = []

            for i, transform in enumerate(transformations):
                trans_type = transform.get("type")
                if not isinstance(trans_type, str):
                    raise ValueError(f"Invalid transformation type: {trans_type}, expected string")
                columns = transform.get("columns")
                params = transform.get("params", {})

                self.logger.info(f"Applying transformation {i+1}/{len(transformations)}: {trans_type}")

                # Apply transformation
                df = self._apply_single_transformation(df, trans_type, columns, params)

                transformation_log.append(
                    {
                        "step": i + 1,
                        "type": trans_type,
                        "columns": columns,
                        "params": params,
                        "status": "success",
                    }
                )

            # Calculate quality improvement
            quality_improvement = self._calculate_quality_improvement(original_df, df)

            return {
                "transformed_data": df,
                "transformation_log": transformation_log,
                "quality_improvement": quality_improvement,
                "original_shape": original_df.shape,
                "new_shape": df.shape,
            }

        except Exception as e:
            self.logger.error(f"Error in transformation pipeline: {e}")
            raise TransformationError(f"Transformation failed: {e}")

    def auto_transform(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        target_column: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Automatically determine and apply optimal transformations.

        Args:
            data: Data to transform
            target_column: Target column for ML tasks
            task_type: Type of task (classification or regression)

        Returns:
            Dict containing transformed data and applied transformations
        """
        try:
            df = self._to_dataframe(data)

            # Determine transformations needed
            transformations = self._determine_transformations(df, target_column, task_type)

            # Apply transformations
            result = self.transform_data(df, transformations, validate=True)
            result["auto_detected_transformations"] = transformations

            return result

        except Exception as e:
            self.logger.error(f"Error in auto transform: {e}")
            raise TransformationError(f"Auto transform failed: {e}")

    def handle_missing_values(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        strategy: MissingValueStrategy = MissingValueStrategy.MEAN,
        columns: Optional[List[str]] = None,
        fill_value: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Handle missing values in data.

        Args:
            data: Data with missing values
            strategy: Strategy for handling missing values
            columns: Specific columns to handle (None for all)
            fill_value: Value for constant strategy

        Returns:
            Dict containing data with handled missing values
        """
        try:
            df = self._to_dataframe(data)
            original_missing = df.isnull().sum().sum()

            # Select columns to handle
            cols_to_handle = columns if columns else df.columns.tolist()

            # Apply strategy
            if strategy == MissingValueStrategy.DROP:
                df = df.dropna(subset=cols_to_handle)
            elif strategy == MissingValueStrategy.MEAN:
                for col in cols_to_handle:
                    if df[col].dtype in ["int64", "float64"]:
                        df[col].fillna(df[col].mean(), inplace=True)
            elif strategy == MissingValueStrategy.MEDIAN:
                for col in cols_to_handle:
                    if df[col].dtype in ["int64", "float64"]:
                        df[col].fillna(df[col].median(), inplace=True)
            elif strategy == MissingValueStrategy.MODE:
                for col in cols_to_handle:
                    if not df[col].mode().empty:
                        df[col].fillna(df[col].mode()[0], inplace=True)
            elif strategy == MissingValueStrategy.FORWARD_FILL:
                df[cols_to_handle] = df[cols_to_handle].fillna(method="ffill")
            elif strategy == MissingValueStrategy.BACKWARD_FILL:
                df[cols_to_handle] = df[cols_to_handle].fillna(method="bfill")
            elif strategy == MissingValueStrategy.INTERPOLATE:
                for col in cols_to_handle:
                    if df[col].dtype in ["int64", "float64"]:
                        df[col] = df[col].interpolate()
            elif strategy == MissingValueStrategy.CONSTANT:
                df[cols_to_handle] = df[cols_to_handle].fillna(fill_value)

            final_missing = df.isnull().sum().sum()

            return {
                "data": df,
                "original_missing": int(original_missing),
                "final_missing": int(final_missing),
                "missing_handled": int(original_missing - final_missing),
                "strategy": strategy.value,
            }

        except Exception as e:
            self.logger.error(f"Error handling missing values: {e}")
            raise TransformationError(f"Failed to handle missing values: {e}")

    def encode_features(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        columns: List[str],
        method: str = "one_hot",
    ) -> Dict[str, Any]:
        """
        Encode categorical features.

        Args:
            data: Data to encode
            columns: Columns to encode
            method: Encoding method (one_hot or label)

        Returns:
            Dict containing encoded data
        """
        try:
            df = self._to_dataframe(data)

            if method == "one_hot":
                # One-hot encoding
                df_encoded = pd.get_dummies(df, columns=columns, prefix=columns)
                encoding_info: Dict[str, Any] = {
                    "method": "one_hot",
                    "original_columns": columns,
                    "new_columns": [col for col in df_encoded.columns if col not in df.columns],
                }
            elif method == "label":
                # Label encoding
                df_encoded = df.copy()
                encoders: Dict[str, Any] = {}
                for col in columns:
                    le = LabelEncoder()
                    df_encoded[col] = le.fit_transform(df[col].astype(str))
                    encoders[col] = le
                encoding_info = {
                    "method": "label",
                    "columns": columns,
                    "encoders": encoders,
                }
            else:
                raise TransformationError(f"Unsupported encoding method: {method}")

            return {
                "data": df_encoded,
                "encoding_info": encoding_info,
                "original_shape": df.shape,
                "new_shape": df_encoded.shape,
            }

        except Exception as e:
            self.logger.error(f"Error encoding features: {e}")
            raise TransformationError(f"Feature encoding failed: {e}")

    # Internal helper methods

    def _to_dataframe(self, data: Union[Dict, List, pd.DataFrame]) -> pd.DataFrame:
        """Convert data to DataFrame"""
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            return pd.DataFrame([data])
        else:
            raise TransformationError(f"Unsupported data type: {type(data)}")

    def _apply_single_transformation(
        self,
        df: pd.DataFrame,
        trans_type: str,
        columns: Optional[List[str]],
        params: Dict[str, Any],
    ) -> pd.DataFrame:
        """Apply a single transformation"""
        if trans_type == TransformationType.REMOVE_DUPLICATES.value:
            return df.drop_duplicates()

        elif trans_type == TransformationType.FILL_MISSING.value:
            strategy = params.get("strategy", "mean")
            for col in columns or df.columns:
                if df[col].isnull().any():
                    if strategy == "mean" and df[col].dtype in [
                        "int64",
                        "float64",
                    ]:
                        df[col].fillna(df[col].mean(), inplace=True)
                    elif strategy == "median" and df[col].dtype in [
                        "int64",
                        "float64",
                    ]:
                        df[col].fillna(df[col].median(), inplace=True)
                    elif strategy == "mode":
                        if not df[col].mode().empty:
                            df[col].fillna(df[col].mode()[0], inplace=True)
            return df

        elif trans_type == TransformationType.REMOVE_OUTLIERS.value:
            for col in columns or df.select_dtypes(include=[np.number]).columns:
                if df[col].std() > 0:
                    z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                    df = df[z_scores < self.config.outlier_std_threshold]
            return df

        elif trans_type == TransformationType.STANDARDIZE.value:
            scaler = StandardScaler()
            cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
            df[cols] = scaler.fit_transform(df[cols])
            return df

        elif trans_type == TransformationType.NORMALIZE.value:
            scaler = MinMaxScaler()
            cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
            df[cols] = scaler.fit_transform(df[cols])
            return df

        elif trans_type == TransformationType.LOG_TRANSFORM.value:
            cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
            for col in cols:
                if (df[col] > 0).all():
                    df[col] = np.log(df[col])
            return df

        elif trans_type == TransformationType.ONE_HOT_ENCODE.value:
            cols = columns or df.select_dtypes(include=["object"]).columns.tolist()
            return pd.get_dummies(df, columns=cols)

        elif trans_type == TransformationType.LABEL_ENCODE.value:
            cols = columns or df.select_dtypes(include=["object"]).columns.tolist()
            for col in cols:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
            return df

        else:
            self.logger.warning(f"Transformation type {trans_type} not implemented, skipping")
            return df

    def _determine_transformations(
        self,
        df: pd.DataFrame,
        target_column: Optional[str],
        task_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Determine transformations needed for data"""
        transformations: List[Dict[str, Any]] = []

        # Remove duplicates if present
        if df.duplicated().sum() > 0:
            transformations.append(
                {
                    "type": TransformationType.REMOVE_DUPLICATES.value,
                    "columns": None,
                    "params": {},
                }
            )

        # Handle missing values
        if df.isnull().sum().sum() > 0:
            transformations.append(
                {
                    "type": TransformationType.FILL_MISSING.value,
                    "columns": None,
                    "params": {"strategy": "mean"},
                }
            )

        # Encode categorical variables
        categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()
        if target_column and target_column in categorical_cols:
            categorical_cols.remove(target_column)

        if len(categorical_cols) > 0:
            # Use label encoding if too many categories, otherwise one-hot
            for col in categorical_cols:
                if df[col].nunique() > self.config.max_one_hot_categories:
                    transformations.append(
                        {
                            "type": TransformationType.LABEL_ENCODE.value,
                            "columns": [col],
                            "params": {},
                        }
                    )
                else:
                    transformations.append(
                        {
                            "type": TransformationType.ONE_HOT_ENCODE.value,
                            "columns": [col],
                            "params": {},
                        }
                    )

        # Standardize numeric features
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if target_column and target_column in numeric_cols:
            numeric_cols.remove(target_column)

        if len(numeric_cols) > 0:
            transformations.append(
                {
                    "type": TransformationType.STANDARDIZE.value,
                    "columns": numeric_cols,
                    "params": {},
                }
            )

        return transformations

    def _calculate_quality_improvement(self, original_df: pd.DataFrame, transformed_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate quality improvement metrics"""
        return {
            "missing_before": int(original_df.isnull().sum().sum()),
            "missing_after": int(transformed_df.isnull().sum().sum()),
            "duplicates_before": int(original_df.duplicated().sum()),
            "duplicates_after": int(transformed_df.duplicated().sum()),
            "rows_before": len(original_df),
            "rows_after": len(transformed_df),
            "columns_before": len(original_df.columns),
            "columns_after": len(transformed_df.columns),
        }
