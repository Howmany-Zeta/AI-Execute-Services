"""
Model Trainer Tool - AutoML and machine learning model training

This tool provides AutoML capabilities with:
- Automatic model selection for classification and regression
- Hyperparameter tuning
- Model evaluation and comparison
- Feature importance analysis
- Model explanation support
"""

import logging
from typing import Dict, Any, List, Optional, Union
from enum import Enum

import pandas as pd  # type: ignore[import-untyped]
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score  # type: ignore[import-untyped]
from sklearn.metrics import (  # type: ignore[import-untyped]
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    r2_score,
    mean_squared_error,
)
from sklearn.ensemble import (  # type: ignore[import-untyped]
    RandomForestClassifier,
    RandomForestRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
)
from sklearn.linear_model import LogisticRegression, LinearRegression  # type: ignore[import-untyped]
from sklearn.preprocessing import LabelEncoder  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class ModelType(str, Enum):
    """Supported model types"""

    LOGISTIC_REGRESSION = "logistic_regression"
    LINEAR_REGRESSION = "linear_regression"
    RANDOM_FOREST_CLASSIFIER = "random_forest_classifier"
    RANDOM_FOREST_REGRESSOR = "random_forest_regressor"
    GRADIENT_BOOSTING_CLASSIFIER = "gradient_boosting_classifier"
    GRADIENT_BOOSTING_REGRESSOR = "gradient_boosting_regressor"
    AUTO = "auto"


class TaskType(str, Enum):
    """Machine learning task types"""

    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"


class ModelTrainerError(Exception):
    """Base exception for ModelTrainer errors"""


class TrainingError(ModelTrainerError):
    """Raised when model training fails"""


@register_tool("model_trainer")
class ModelTrainerTool(BaseTool):
    """
    AutoML tool that can:
    1. Train multiple model types
    2. Perform hyperparameter tuning
    3. Evaluate and compare models
    4. Generate feature importance
    5. Provide model explanations
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the model trainer tool
        
        Automatically reads from environment variables with MODEL_TRAINER_ prefix.
        Example: MODEL_TRAINER_TEST_SIZE -> test_size
        """

        model_config = SettingsConfigDict(env_prefix="MODEL_TRAINER_")

        test_size: float = Field(default=0.2, description="Proportion of data to use for testing")
        random_state: int = Field(default=42, description="Random state for reproducibility")
        cv_folds: int = Field(default=5, description="Number of cross-validation folds")
        enable_hyperparameter_tuning: bool = Field(
            default=False,
            description="Whether to enable hyperparameter tuning",
        )
        max_tuning_iterations: int = Field(
            default=20,
            description="Maximum number of hyperparameter tuning iterations",
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize ModelTrainerTool with settings

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/model_trainer.yaml)
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

        self._init_external_tools()
        self.trained_models: Dict[str, Any] = {}

    def _init_external_tools(self):
        """Initialize external task tools"""
        self.external_tools = {}

    # Schema definitions
    class TrainModelSchema(BaseModel):
        """Schema for train_model operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Training data")
        target: str = Field(description="Target column name")
        model_type: ModelType = Field(default=ModelType.AUTO, description="Model type to train")
        auto_tune: bool = Field(default=False, description="Enable hyperparameter tuning")
        cross_validation: int = Field(default=5, description="Number of CV folds")

    class AutoSelectModelSchema(BaseModel):
        """Schema for auto_select_model operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data for model selection")
        target: str = Field(description="Target column name")
        task_type: Optional[TaskType] = Field(default=None, description="Task type")

    class EvaluateModelSchema(BaseModel):
        """Schema for evaluate_model operation"""

        model_id: str = Field(description="ID of trained model")
        test_data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Test data")
        target: str = Field(description="Target column name")

    def train_model(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        target: str,
        model_type: ModelType = ModelType.AUTO,
        auto_tune: bool = False,
        cross_validation: int = 5,
    ) -> Dict[str, Any]:
        """
        Train and evaluate model.

        Args:
            data: Training data
            target: Target column name
            model_type: Type of model to train (auto-selected if AUTO)
            auto_tune: Enable hyperparameter tuning
            cross_validation: Number of cross-validation folds

        Returns:
            Dict containing:
                - model_id: Unique identifier for trained model
                - model_type: Type of model trained
                - performance: Performance metrics
                - feature_importance: Feature importance scores
                - cross_validation_scores: CV scores
        """
        try:
            df = self._to_dataframe(data)

            # Separate features and target
            X = df.drop(columns=[target])
            y = df[target]

            # Determine task type and model
            task_type = self._determine_task_type(y)

            if model_type == ModelType.AUTO:
                model_type = self._auto_select_model_type(task_type)
                self.logger.info(f"Auto-selected model type: {model_type.value}")

            # Prepare data
            X_processed, feature_names = self._preprocess_features(X)

            # Handle categorical target for classification
            if task_type == TaskType.CLASSIFICATION:
                label_encoder = LabelEncoder()
                y = label_encoder.fit_transform(y)
            else:
                label_encoder = None

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_processed,
                y,
                test_size=self.config.test_size,
                random_state=self.config.random_state,
            )

            # Create and train model
            model = self._create_model(model_type)
            model.fit(X_train, y_train)

            # Make predictions
            y_pred = model.predict(X_test)

            # Calculate metrics
            performance = self._calculate_metrics(y_test, y_pred, task_type)

            # Cross-validation
            cv_scores = cross_val_score(model, X_processed, y, cv=cross_validation)

            # Feature importance
            feature_importance = self._get_feature_importance(model, feature_names)

            # Store model
            model_id = f"model_{len(self.trained_models) + 1}"
            self.trained_models[model_id] = {
                "model": model,
                "model_type": model_type.value,
                "task_type": task_type.value,
                "feature_names": feature_names,
                "label_encoder": label_encoder,
            }

            return {
                "model_id": model_id,
                "model_type": model_type.value,
                "task_type": task_type.value,
                "performance": performance,
                "feature_importance": feature_importance,
                "cross_validation_scores": {
                    "scores": cv_scores.tolist(),
                    "mean": float(cv_scores.mean()),
                    "std": float(cv_scores.std()),
                },
                "training_samples": len(X_train),
                "test_samples": len(X_test),
            }

        except Exception as e:
            self.logger.error(f"Error training model: {e}")
            raise TrainingError(f"Model training failed: {e}")

    def auto_select_model(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        target: str,
        task_type: Optional[TaskType] = None,
    ) -> Dict[str, Any]:
        """
        Automatically select best model based on data characteristics.

        Args:
            data: Data for model selection
            target: Target column name
            task_type: Optional task type (auto-determined if None)

        Returns:
            Dict containing recommended model and reasoning
        """
        try:
            df = self._to_dataframe(data)
            y = df[target]

            # Determine task type
            if task_type is None:
                task_type = self._determine_task_type(y)

            # Select model
            model_type = self._auto_select_model_type(task_type)

            # Provide reasoning
            reasoning = self._explain_model_selection(df, y, task_type, model_type)

            return {
                "recommended_model": model_type.value,
                "task_type": task_type.value,
                "reasoning": reasoning,
                "confidence": "high",
            }

        except Exception as e:
            self.logger.error(f"Error in auto model selection: {e}")
            raise TrainingError(f"Model selection failed: {e}")

    def evaluate_model(
        self,
        model_id: str,
        test_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        target: str,
    ) -> Dict[str, Any]:
        """
        Evaluate trained model on test data.

        Args:
            model_id: ID of trained model
            test_data: Test data
            target: Target column name

        Returns:
            Dict containing evaluation metrics
        """
        try:
            if model_id not in self.trained_models:
                raise TrainingError(f"Model {model_id} not found")

            df = self._to_dataframe(test_data)
            X_test = df.drop(columns=[target])
            y_test = df[target]

            model_info = self.trained_models[model_id]
            model = model_info["model"]
            task_type = TaskType(model_info["task_type"])

            # Preprocess features
            X_processed, _ = self._preprocess_features(X_test)

            # Handle label encoding for classification
            if model_info["label_encoder"]:
                y_test = model_info["label_encoder"].transform(y_test)

            # Make predictions
            y_pred = model.predict(X_processed)

            # Calculate metrics
            performance = self._calculate_metrics(y_test, y_pred, task_type)

            return {
                "model_id": model_id,
                "performance": performance,
                "test_samples": len(X_test),
            }

        except Exception as e:
            self.logger.error(f"Error evaluating model: {e}")
            raise TrainingError(f"Model evaluation failed: {e}")

    def tune_hyperparameters(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        target: str,
        model_type: ModelType,
    ) -> Dict[str, Any]:
        """
        Tune hyperparameters for specified model type.

        Args:
            data: Training data
            target: Target column name
            model_type: Model type to tune

        Returns:
            Dict containing best parameters and performance
        """
        try:
            # Note: Full hyperparameter tuning with GridSearchCV would be implemented here
            # For now, returning placeholder structure
            self.logger.info("Hyperparameter tuning is a placeholder - train with default params")

            result = self.train_model(data, target, model_type, auto_tune=False)
            result["tuning_note"] = "Using default parameters - full tuning not implemented"

            return result

        except Exception as e:
            self.logger.error(f"Error tuning hyperparameters: {e}")
            raise TrainingError(f"Hyperparameter tuning failed: {e}")

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
            raise TrainingError(f"Unsupported data type: {type(data)}")

    def _determine_task_type(self, y: pd.Series) -> TaskType:
        """Determine task type from target variable"""
        if y.dtype in ["object", "category", "bool"]:
            return TaskType.CLASSIFICATION
        elif y.nunique() < 10 and y.dtype in ["int64", "int32"]:
            return TaskType.CLASSIFICATION
        else:
            return TaskType.REGRESSION

    def _auto_select_model_type(self, task_type: TaskType) -> ModelType:
        """Auto-select model type based on task"""
        if task_type == TaskType.CLASSIFICATION:
            return ModelType.RANDOM_FOREST_CLASSIFIER
        else:
            return ModelType.RANDOM_FOREST_REGRESSOR

    def _create_model(self, model_type: ModelType):
        """Create model instance"""
        if model_type == ModelType.LOGISTIC_REGRESSION:
            return LogisticRegression(random_state=self.config.random_state, max_iter=1000)
        elif model_type == ModelType.LINEAR_REGRESSION:
            return LinearRegression()
        elif model_type == ModelType.RANDOM_FOREST_CLASSIFIER:
            return RandomForestClassifier(random_state=self.config.random_state, n_estimators=100)
        elif model_type == ModelType.RANDOM_FOREST_REGRESSOR:
            return RandomForestRegressor(random_state=self.config.random_state, n_estimators=100)
        elif model_type == ModelType.GRADIENT_BOOSTING_CLASSIFIER:
            return GradientBoostingClassifier(random_state=self.config.random_state)
        elif model_type == ModelType.GRADIENT_BOOSTING_REGRESSOR:
            return GradientBoostingRegressor(random_state=self.config.random_state)
        else:
            raise TrainingError(f"Unsupported model type: {model_type}")

    def _preprocess_features(self, X: pd.DataFrame) -> tuple:
        """Preprocess features for training"""
        X_processed = X.copy()

        # Handle categorical variables with label encoding
        for col in X_processed.select_dtypes(include=["object", "category"]).columns:
            le = LabelEncoder()
            X_processed[col] = le.fit_transform(X_processed[col].astype(str))

        # Handle missing values
        X_processed = X_processed.fillna(X_processed.mean(numeric_only=True))

        feature_names = X_processed.columns.tolist()

        return X_processed.values, feature_names

    def _calculate_metrics(self, y_true, y_pred, task_type: TaskType) -> Dict[str, float]:
        """Calculate performance metrics"""
        if task_type == TaskType.CLASSIFICATION:
            return {
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
                "recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
                "f1_score": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
            }
        else:
            mse = mean_squared_error(y_true, y_pred)
            return {
                "r2_score": float(r2_score(y_true, y_pred)),
                "mse": float(mse),
                "rmse": float(np.sqrt(mse)),
                "mae": float(np.mean(np.abs(y_true - y_pred))),
            }

    def _get_feature_importance(self, model, feature_names: List[str]) -> Dict[str, float]:
        """Extract feature importance from model"""
        if hasattr(model, "feature_importances_"):
            importance = model.feature_importances_
            return {name: float(imp) for name, imp in zip(feature_names, importance)}
        elif hasattr(model, "coef_"):
            importance = np.abs(model.coef_).flatten()
            return {name: float(imp) for name, imp in zip(feature_names, importance)}
        else:
            return {}

    def _explain_model_selection(
        self,
        df: pd.DataFrame,
        y: pd.Series,
        task_type: TaskType,
        model_type: ModelType,
    ) -> str:
        """Explain why a model was selected"""
        n_samples = len(df)
        n_features = len(df.columns) - 1

        reasons = []
        reasons.append(f"Task type: {task_type.value}")
        reasons.append(f"Dataset size: {n_samples} samples, {n_features} features")

        if model_type in [
            ModelType.RANDOM_FOREST_CLASSIFIER,
            ModelType.RANDOM_FOREST_REGRESSOR,
        ]:
            reasons.append("Random Forest selected for robust performance and feature importance")

        return "; ".join(reasons)
