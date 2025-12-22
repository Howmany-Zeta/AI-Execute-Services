"""
Comprehensive tests for ModelTrainerTool

Tests real functionality without mocks to verify actual behavior and output.
Includes debug output for manual verification of tool functionality.

Run with: poetry run pytest test/test_model_trainer_tool.py -v -s
Coverage: poetry run python test/run_model_trainer_coverage.py
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import pandas as pd
import numpy as np

from aiecs.tools.statistics.model_trainer_tool import (
    ModelTrainerTool,
    ModelType,
    TaskType,
    ModelTrainerSettings,
    ModelTrainerError,
    TrainingError
)


class TestModelTrainerToolInitialization:
    """Test ModelTrainerTool initialization and configuration"""
    
    def test_default_initialization(self):
        """Test tool initialization with default settings"""
        print("\n=== Testing Default Initialization ===")
        tool = ModelTrainerTool()
        
        assert tool is not None
        assert tool.settings.test_size == 0.2
        assert tool.settings.random_state == 42
        assert tool.settings.cv_folds == 5
        assert tool.settings.enable_hyperparameter_tuning is False
        assert tool.trained_models == {}
        
        print(f"✓ Tool initialized with default settings")
        print(f"  - Test size: {tool.settings.test_size}")
        print(f"  - Random state: {tool.settings.random_state}")
        print(f"  - CV folds: {tool.settings.cv_folds}")
    
    def test_custom_configuration(self):
        """Test tool initialization with custom configuration"""
        print("\n=== Testing Custom Configuration ===")
        config = {
            'test_size': 0.3,
            'random_state': 123,
            'cv_folds': 10,
            'enable_hyperparameter_tuning': True
        }
        tool = ModelTrainerTool(config=config)
        
        assert tool.settings.test_size == 0.3
        assert tool.settings.random_state == 123
        assert tool.settings.cv_folds == 10
        assert tool.settings.enable_hyperparameter_tuning is True
        
        print(f"✓ Tool initialized with custom settings")
        print(f"  - Test size: {tool.settings.test_size}")
        print(f"  - Random state: {tool.settings.random_state}")
    
    def test_invalid_configuration(self):
        """Test initialization with invalid configuration"""
        print("\n=== Testing Invalid Configuration ===")
        
        with pytest.raises(ValueError) as exc_info:
            ModelTrainerTool(config={'test_size': 'invalid'})
        
        assert "Invalid settings" in str(exc_info.value)
        print(f"✓ Correctly raised ValueError for invalid config")


class TestTrainModelClassification:
    """Test model training for classification tasks"""
    
    @pytest.fixture
    def classification_data(self):
        """Create classification dataset"""
        np.random.seed(42)
        n_samples = 200
        X = np.random.randn(n_samples, 5)
        y = (X[:, 0] + X[:, 1] > 0).astype(int)
        
        df = pd.DataFrame(X, columns=['feature1', 'feature2', 'feature3', 'feature4', 'feature5'])
        df['target'] = y
        
        return df
    
    def test_train_random_forest_classifier(self, classification_data):
        """Test training Random Forest classifier"""
        print("\n=== Testing Random Forest Classifier ===")
        tool = ModelTrainerTool()
        
        result = tool.train_model(
            data=classification_data,
            target='target',
            model_type=ModelType.RANDOM_FOREST_CLASSIFIER
        )
        
        assert 'model_id' in result
        assert result['model_type'] == ModelType.RANDOM_FOREST_CLASSIFIER.value
        assert result['task_type'] == TaskType.CLASSIFICATION.value
        assert 'performance' in result
        assert 'accuracy' in result['performance']
        assert 'feature_importance' in result
        assert 'cross_validation_scores' in result
        
        print(f"✓ Random Forest Classifier trained")
        print(f"  - Model ID: {result['model_id']}")
        print(f"  - Accuracy: {result['performance']['accuracy']:.4f}")
        print(f"  - CV mean: {result['cross_validation_scores']['mean']:.4f}")
    
    def test_train_logistic_regression(self, classification_data):
        """Test training Logistic Regression"""
        print("\n=== Testing Logistic Regression ===")
        tool = ModelTrainerTool()
        
        result = tool.train_model(
            data=classification_data,
            target='target',
            model_type=ModelType.LOGISTIC_REGRESSION
        )
        
        assert result['model_type'] == ModelType.LOGISTIC_REGRESSION.value
        assert 'accuracy' in result['performance']
        
        print(f"✓ Logistic Regression trained")
        print(f"  - Accuracy: {result['performance']['accuracy']:.4f}")
    
    def test_train_gradient_boosting_classifier(self, classification_data):
        """Test training Gradient Boosting classifier"""
        print("\n=== Testing Gradient Boosting Classifier ===")
        tool = ModelTrainerTool()
        
        result = tool.train_model(
            data=classification_data,
            target='target',
            model_type=ModelType.GRADIENT_BOOSTING_CLASSIFIER
        )
        
        assert result['model_type'] == ModelType.GRADIENT_BOOSTING_CLASSIFIER.value
        assert 'f1_score' in result['performance']
        
        print(f"✓ Gradient Boosting Classifier trained")
        print(f"  - F1 Score: {result['performance']['f1_score']:.4f}")
    
    def test_train_auto_classification(self, classification_data):
        """Test auto model selection for classification"""
        print("\n=== Testing Auto Classification ===")
        tool = ModelTrainerTool()
        
        result = tool.train_model(
            data=classification_data,
            target='target',
            model_type=ModelType.AUTO
        )
        
        assert result['task_type'] == TaskType.CLASSIFICATION.value
        assert 'model_type' in result
        
        print(f"✓ Auto classification completed")
        print(f"  - Selected model: {result['model_type']}")
        print(f"  - Accuracy: {result['performance']['accuracy']:.4f}")


class TestTrainModelRegression:
    """Test model training for regression tasks"""
    
    @pytest.fixture
    def regression_data(self):
        """Create regression dataset"""
        np.random.seed(42)
        n_samples = 200
        X = np.random.randn(n_samples, 4)
        y = 2 * X[:, 0] + 3 * X[:, 1] - X[:, 2] + np.random.randn(n_samples) * 0.5
        
        df = pd.DataFrame(X, columns=['feature1', 'feature2', 'feature3', 'feature4'])
        df['target'] = y
        
        return df
    
    def test_train_random_forest_regressor(self, regression_data):
        """Test training Random Forest regressor"""
        print("\n=== Testing Random Forest Regressor ===")
        tool = ModelTrainerTool()
        
        result = tool.train_model(
            data=regression_data,
            target='target',
            model_type=ModelType.RANDOM_FOREST_REGRESSOR
        )
        
        assert result['model_type'] == ModelType.RANDOM_FOREST_REGRESSOR.value
        assert result['task_type'] == TaskType.REGRESSION.value
        assert 'r2_score' in result['performance']
        assert 'mse' in result['performance']
        assert 'rmse' in result['performance']
        
        print(f"✓ Random Forest Regressor trained")
        print(f"  - R2 Score: {result['performance']['r2_score']:.4f}")
        print(f"  - RMSE: {result['performance']['rmse']:.4f}")
    
    def test_train_linear_regression(self, regression_data):
        """Test training Linear Regression"""
        print("\n=== Testing Linear Regression ===")
        tool = ModelTrainerTool()
        
        result = tool.train_model(
            data=regression_data,
            target='target',
            model_type=ModelType.LINEAR_REGRESSION
        )
        
        assert result['model_type'] == ModelType.LINEAR_REGRESSION.value
        assert 'r2_score' in result['performance']
        
        print(f"✓ Linear Regression trained")
        print(f"  - R2 Score: {result['performance']['r2_score']:.4f}")
    
    def test_train_gradient_boosting_regressor(self, regression_data):
        """Test training Gradient Boosting regressor"""
        print("\n=== Testing Gradient Boosting Regressor ===")
        tool = ModelTrainerTool()
        
        result = tool.train_model(
            data=regression_data,
            target='target',
            model_type=ModelType.GRADIENT_BOOSTING_REGRESSOR
        )
        
        assert result['model_type'] == ModelType.GRADIENT_BOOSTING_REGRESSOR.value
        assert 'mae' in result['performance']
        
        print(f"✓ Gradient Boosting Regressor trained")
        print(f"  - MAE: {result['performance']['mae']:.4f}")
    
    def test_train_auto_regression(self, regression_data):
        """Test auto model selection for regression"""
        print("\n=== Testing Auto Regression ===")
        tool = ModelTrainerTool()
        
        result = tool.train_model(
            data=regression_data,
            target='target',
            model_type=ModelType.AUTO
        )
        
        assert result['task_type'] == TaskType.REGRESSION.value
        assert 'model_type' in result
        
        print(f"✓ Auto regression completed")
        print(f"  - Selected model: {result['model_type']}")


class TestAutoSelectModel:
    """Test automatic model selection"""
    
    def test_auto_select_for_classification(self):
        """Test auto select model for classification task"""
        print("\n=== Testing Auto Select - Classification ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'target': np.random.choice(['A', 'B', 'C'], 100)
        })
        
        result = tool.auto_select_model(data=data, target='target')
        
        assert 'recommended_model' in result
        assert result['task_type'] == TaskType.CLASSIFICATION.value
        assert 'reasoning' in result
        assert 'confidence' in result
        
        print(f"✓ Auto selection for classification")
        print(f"  - Recommended: {result['recommended_model']}")
        print(f"  - Reasoning: {result['reasoning']}")
    
    def test_auto_select_for_regression(self):
        """Test auto select model for regression task"""
        print("\n=== Testing Auto Select - Regression ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'target': np.random.randn(100) * 100
        })
        
        result = tool.auto_select_model(data=data, target='target')
        
        assert result['task_type'] == TaskType.REGRESSION.value
        assert 'recommended_model' in result
        
        print(f"✓ Auto selection for regression")
        print(f"  - Recommended: {result['recommended_model']}")
    
    def test_auto_select_with_explicit_task_type(self):
        """Test auto select with explicit task type"""
        print("\n=== Testing Auto Select - Explicit Task Type ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'feature1': np.random.randn(50),
            'target': np.random.randint(0, 2, 50)
        })
        
        result = tool.auto_select_model(
            data=data,
            target='target',
            task_type=TaskType.CLASSIFICATION
        )
        
        assert result['task_type'] == TaskType.CLASSIFICATION.value
        
        print(f"✓ Auto selection with explicit task type")


class TestEvaluateModel:
    """Test model evaluation functionality"""
    
    @pytest.fixture
    def trained_model(self):
        """Train a model for evaluation tests"""
        tool = ModelTrainerTool()
        
        # Create training data
        np.random.seed(42)
        X = np.random.randn(200, 3)
        y = (X[:, 0] + X[:, 1] > 0).astype(int)
        df_train = pd.DataFrame(X, columns=['f1', 'f2', 'f3'])
        df_train['target'] = y
        
        # Train model
        result = tool.train_model(
            data=df_train,
            target='target',
            model_type=ModelType.RANDOM_FOREST_CLASSIFIER
        )
        
        # Create test data
        X_test = np.random.randn(50, 3)
        y_test = (X_test[:, 0] + X_test[:, 1] > 0).astype(int)
        df_test = pd.DataFrame(X_test, columns=['f1', 'f2', 'f3'])
        df_test['target'] = y_test
        
        return tool, result['model_id'], df_test
    
    def test_evaluate_trained_model(self, trained_model):
        """Test evaluation of trained model"""
        print("\n=== Testing Model Evaluation ===")
        tool, model_id, test_data = trained_model
        
        result = tool.evaluate_model(
            model_id=model_id,
            test_data=test_data,
            target='target'
        )
        
        assert 'model_id' in result
        assert 'performance' in result
        assert 'test_samples' in result
        assert 'accuracy' in result['performance']
        
        print(f"✓ Model evaluated")
        print(f"  - Model ID: {result['model_id']}")
        print(f"  - Test accuracy: {result['performance']['accuracy']:.4f}")
    
    def test_evaluate_nonexistent_model(self):
        """Test error when evaluating nonexistent model"""
        print("\n=== Testing Nonexistent Model Evaluation ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({'f1': [1, 2, 3], 'target': [0, 1, 0]})
        
        with pytest.raises(TrainingError) as exc_info:
            tool.evaluate_model(
                model_id='nonexistent',
                test_data=data,
                target='target'
            )
        
        assert "not found" in str(exc_info.value)
        print(f"✓ Correctly raised TrainingError for nonexistent model")


class TestTuneHyperparameters:
    """Test hyperparameter tuning functionality"""
    
    def test_tune_hyperparameters(self):
        """Test hyperparameter tuning"""
        print("\n=== Testing Hyperparameter Tuning ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'f1': np.random.randn(100),
            'f2': np.random.randn(100),
            'target': np.random.choice([0, 1], 100)
        })
        
        result = tool.tune_hyperparameters(
            data=data,
            target='target',
            model_type=ModelType.RANDOM_FOREST_CLASSIFIER
        )
        
        assert 'model_id' in result
        assert 'tuning_note' in result
        
        print(f"✓ Hyperparameter tuning completed")
        print(f"  - Note: {result['tuning_note']}")


class TestDataConversion:
    """Test data conversion functionality"""
    
    def test_dataframe_input(self):
        """Test with DataFrame input"""
        print("\n=== Testing DataFrame Input ===")
        tool = ModelTrainerTool()
        
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        converted = tool._to_dataframe(df)
        
        assert isinstance(converted, pd.DataFrame)
        assert converted.equals(df)
        
        print(f"✓ DataFrame input handled")
    
    def test_dict_input(self):
        """Test with dictionary input"""
        print("\n=== Testing Dict Input ===")
        tool = ModelTrainerTool()
        
        data = {'col1': 1, 'col2': 2, 'col3': 3}
        converted = tool._to_dataframe(data)
        
        assert isinstance(converted, pd.DataFrame)
        assert len(converted) == 1
        
        print(f"✓ Dict input converted")
    
    def test_list_input(self):
        """Test with list input"""
        print("\n=== Testing List Input ===")
        tool = ModelTrainerTool()
        
        data = [
            {'x': 1, 'y': 2},
            {'x': 3, 'y': 4},
            {'x': 5, 'y': 6}
        ]
        converted = tool._to_dataframe(data)
        
        assert isinstance(converted, pd.DataFrame)
        assert len(converted) == 3
        
        print(f"✓ List input converted")
    
    def test_unsupported_data_type(self):
        """Test error handling for unsupported data types"""
        print("\n=== Testing Unsupported Data Type ===")
        tool = ModelTrainerTool()
        
        with pytest.raises(TrainingError) as exc_info:
            tool._to_dataframe("invalid_data")
        
        assert "Unsupported data type" in str(exc_info.value)
        print(f"✓ Correctly raised TrainingError")


class TestTaskTypeDetermination:
    """Test task type determination"""
    
    def test_determine_classification_categorical(self):
        """Test classification detection for categorical target"""
        print("\n=== Testing Task Type - Categorical ===")
        tool = ModelTrainerTool()
        
        y = pd.Series(['A', 'B', 'C', 'A', 'B'])
        task_type = tool._determine_task_type(y)
        
        assert task_type == TaskType.CLASSIFICATION
        
        print(f"✓ Categorical target detected as classification")
    
    def test_determine_classification_integer(self):
        """Test classification detection for integer target with few unique values"""
        print("\n=== Testing Task Type - Integer Classification ===")
        tool = ModelTrainerTool()
        
        y = pd.Series([0, 1, 0, 1, 0, 1, 0])
        task_type = tool._determine_task_type(y)
        
        assert task_type == TaskType.CLASSIFICATION
        
        print(f"✓ Integer target with few unique values detected as classification")
    
    def test_determine_regression(self):
        """Test regression detection for continuous target"""
        print("\n=== Testing Task Type - Regression ===")
        tool = ModelTrainerTool()
        
        y = pd.Series(np.random.randn(100) * 10 + 50)
        task_type = tool._determine_task_type(y)
        
        assert task_type == TaskType.REGRESSION
        
        print(f"✓ Continuous target detected as regression")
    
    def test_determine_boolean(self):
        """Test classification detection for boolean target"""
        print("\n=== Testing Task Type - Boolean ===")
        tool = ModelTrainerTool()
        
        y = pd.Series([True, False, True, False, True])
        task_type = tool._determine_task_type(y)
        
        assert task_type == TaskType.CLASSIFICATION
        
        print(f"✓ Boolean target detected as classification")


class TestFeatureImportance:
    """Test feature importance extraction"""
    
    def test_feature_importance_random_forest(self):
        """Test feature importance from Random Forest"""
        print("\n=== Testing Feature Importance - Random Forest ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'f1': np.random.randn(100),
            'f2': np.random.randn(100),
            'f3': np.random.randn(100),
            'target': np.random.choice([0, 1], 100)
        })
        
        result = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.RANDOM_FOREST_CLASSIFIER
        )
        
        assert 'feature_importance' in result
        assert len(result['feature_importance']) > 0
        
        print(f"✓ Feature importance extracted")
        for feature, importance in list(result['feature_importance'].items())[:3]:
            print(f"  - {feature}: {importance:.4f}")
    
    def test_feature_importance_linear_model(self):
        """Test feature importance from linear model"""
        print("\n=== Testing Feature Importance - Linear Model ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'f1': np.random.randn(100),
            'f2': np.random.randn(100),
            'target': np.random.choice([0, 1], 100)
        })
        
        result = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.LOGISTIC_REGRESSION
        )
        
        assert 'feature_importance' in result
        assert len(result['feature_importance']) > 0
        
        print(f"✓ Coefficient-based importance extracted")


class TestPreprocessing:
    """Test data preprocessing functionality"""
    
    def test_preprocess_with_categorical(self):
        """Test preprocessing with categorical features"""
        print("\n=== Testing Preprocessing - Categorical ===")
        tool = ModelTrainerTool()
        
        X = pd.DataFrame({
            'numeric': [1, 2, 3, 4, 5],
            'categorical': ['A', 'B', 'A', 'C', 'B']
        })
        
        X_processed, feature_names = tool._preprocess_features(X)
        
        assert X_processed.shape[0] == 5
        assert X_processed.shape[1] == 2
        assert len(feature_names) == 2
        
        print(f"✓ Categorical features encoded")
        print(f"  - Shape: {X_processed.shape}")
    
    def test_preprocess_with_missing_values(self):
        """Test preprocessing with missing values"""
        print("\n=== Testing Preprocessing - Missing Values ===")
        tool = ModelTrainerTool()
        
        X = pd.DataFrame({
            'f1': [1, 2, None, 4, 5],
            'f2': [10, None, 30, 40, 50]
        })
        
        X_processed, feature_names = tool._preprocess_features(X)
        
        assert not np.isnan(X_processed).any()
        
        print(f"✓ Missing values handled")


class TestErrorHandling:
    """Test error handling and exceptions"""
    
    def test_training_error_invalid_target(self):
        """Test error when target column doesn't exist"""
        print("\n=== Testing Training Error - Invalid Target ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({'f1': [1, 2, 3], 'f2': [4, 5, 6]})
        
        with pytest.raises(TrainingError):
            tool.train_model(
                data=data,
                target='nonexistent',
                model_type=ModelType.RANDOM_FOREST_CLASSIFIER
            )
        
        print(f"✓ TrainingError raised for invalid target")
    
    def test_training_error_invalid_data(self):
        """Test error with invalid data"""
        print("\n=== Testing Training Error - Invalid Data ===")
        tool = ModelTrainerTool()
        
        with pytest.raises(TrainingError):
            tool.train_model(
                data=None,
                target='target',
                model_type=ModelType.AUTO
            )
        
        print(f"✓ TrainingError raised for invalid data")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_small_dataset(self):
        """Test training with very small dataset"""
        print("\n=== Testing Small Dataset ===")
        tool = ModelTrainerTool()
        
        # Small dataset - need enough samples for CV
        data = pd.DataFrame({
            'f1': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            'f2': [5, 4, 3, 2, 1, 6, 7, 8, 9, 10, 11, 12],
            'target': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        })
        
        result = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.LOGISTIC_REGRESSION,
            cross_validation=2  # Use 2-fold CV for small dataset
        )
        
        assert 'model_id' in result
        
        print(f"✓ Small dataset handled")
        print(f"  - Training samples: {result['training_samples']}")
    
    def test_single_feature(self):
        """Test training with single feature"""
        print("\n=== Testing Single Feature ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'feature': np.random.randn(100),
            'target': np.random.choice([0, 1], 100)
        })
        
        result = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.LOGISTIC_REGRESSION
        )
        
        assert 'model_id' in result
        
        print(f"✓ Single feature handled")


class TestIntegration:
    """Test integration with other components"""
    
    def test_settings_model(self):
        """Test ModelTrainerSettings model"""
        print("\n=== Testing Settings Model ===")
        
        settings = ModelTrainerSettings()
        assert settings.test_size == 0.2
        assert settings.random_state == 42
        
        print(f"✓ Settings model works correctly")
    
    def test_model_type_enum(self):
        """Test ModelType enum"""
        print("\n=== Testing ModelType Enum ===")
        
        assert ModelType.LOGISTIC_REGRESSION.value == "logistic_regression"
        assert ModelType.AUTO.value == "auto"
        
        print(f"✓ ModelType enum values correct")
    
    def test_task_type_enum(self):
        """Test TaskType enum"""
        print("\n=== Testing TaskType Enum ===")
        
        all_types = list(TaskType)
        assert TaskType.CLASSIFICATION in all_types
        assert TaskType.REGRESSION in all_types
        
        print(f"✓ TaskType enum complete")
        print(f"  - Available types: {[t.value for t in all_types]}")


class TestCrossValidation:
    """Test cross-validation functionality"""
    
    def test_cross_validation_scores(self):
        """Test that cross-validation scores are computed"""
        print("\n=== Testing Cross-Validation ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'f1': np.random.randn(100),
            'f2': np.random.randn(100),
            'target': np.random.choice([0, 1], 100)
        })
        
        result = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.RANDOM_FOREST_CLASSIFIER,
            cross_validation=3
        )
        
        assert 'cross_validation_scores' in result
        assert 'scores' in result['cross_validation_scores']
        assert 'mean' in result['cross_validation_scores']
        assert 'std' in result['cross_validation_scores']
        assert len(result['cross_validation_scores']['scores']) == 3
        
        print(f"✓ Cross-validation completed")
        print(f"  - Mean CV score: {result['cross_validation_scores']['mean']:.4f}")
        print(f"  - Std CV score: {result['cross_validation_scores']['std']:.4f}")


class TestAdditionalCoverage:
    """Additional tests to improve coverage"""
    
    def test_categorical_target_with_strings(self):
        """Test classification with string target labels"""
        print("\n=== Testing Categorical Target - Strings ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'f1': np.random.randn(100),
            'f2': np.random.randn(100),
            'f3': np.random.randn(100),
            'target': np.random.choice(['cat', 'dog', 'bird'], 100)
        })
        
        result = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.RANDOM_FOREST_CLASSIFIER
        )
        
        assert result['task_type'] == TaskType.CLASSIFICATION.value
        assert 'model_id' in result
        
        print(f"✓ String categorical target handled")
        print(f"  - Accuracy: {result['performance']['accuracy']:.4f}")
    
    def test_evaluate_with_label_encoder(self):
        """Test evaluation with label encoder"""
        print("\n=== Testing Evaluation with Label Encoder ===")
        tool = ModelTrainerTool()
        
        # Train with categorical target
        train_data = pd.DataFrame({
            'f1': np.random.randn(100),
            'f2': np.random.randn(100),
            'target': np.random.choice(['A', 'B'], 100)
        })
        
        result = tool.train_model(
            data=train_data,
            target='target',
            model_type=ModelType.LOGISTIC_REGRESSION
        )
        
        # Evaluate
        test_data = pd.DataFrame({
            'f1': np.random.randn(50),
            'f2': np.random.randn(50),
            'target': np.random.choice(['A', 'B'], 50)
        })
        
        eval_result = tool.evaluate_model(
            model_id=result['model_id'],
            test_data=test_data,
            target='target'
        )
        
        assert 'performance' in eval_result
        
        print(f"✓ Evaluation with label encoder completed")
    
    def test_preprocess_with_only_numeric(self):
        """Test preprocessing with only numeric features"""
        print("\n=== Testing Preprocessing - Only Numeric ===")
        tool = ModelTrainerTool()
        
        X = pd.DataFrame({
            'f1': [1.5, 2.5, 3.5, 4.5, 5.5],
            'f2': [10.0, 20.0, 30.0, 40.0, 50.0]
        })
        
        X_processed, feature_names = tool._preprocess_features(X)
        
        assert X_processed.shape == (5, 2)
        assert len(feature_names) == 2
        
        print(f"✓ Only numeric features preprocessed")
    
    def test_get_feature_importance_no_importance(self):
        """Test feature importance extraction from model without importance"""
        print("\n=== Testing Feature Importance - No Importance ===")
        tool = ModelTrainerTool()
        
        # Create a simple custom model without feature_importances_ or coef_
        class DummyModel:
            pass
        
        model = DummyModel()
        feature_names = ['f1', 'f2']
        
        importance = tool._get_feature_importance(model, feature_names)
        
        assert importance == {}
        
        print(f"✓ No feature importance handled")
    
    def test_explain_model_selection(self):
        """Test model selection explanation"""
        print("\n=== Testing Model Selection Explanation ===")
        tool = ModelTrainerTool()
        
        df = pd.DataFrame({
            'f1': np.random.randn(100),
            'f2': np.random.randn(100),
            'f3': np.random.randn(100),
            'target': np.random.choice([0, 1], 100)
        })
        
        y = df['target']
        task_type = TaskType.CLASSIFICATION
        model_type = ModelType.RANDOM_FOREST_CLASSIFIER
        
        explanation = tool._explain_model_selection(df, y, task_type, model_type)
        
        assert 'Task type' in explanation
        assert 'Dataset size' in explanation
        
        print(f"✓ Model selection explained")
        print(f"  - Explanation: {explanation}")
    
    def test_multiclass_classification_metrics(self):
        """Test metrics calculation for multiclass classification"""
        print("\n=== Testing Multiclass Classification Metrics ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'f1': np.random.randn(150),
            'f2': np.random.randn(150),
            'f3': np.random.randn(150),
            'target': np.random.choice([0, 1, 2], 150)
        })
        
        result = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.RANDOM_FOREST_CLASSIFIER
        )
        
        assert 'precision' in result['performance']
        assert 'recall' in result['performance']
        assert 'f1_score' in result['performance']
        
        print(f"✓ Multiclass metrics calculated")
        print(f"  - F1 Score: {result['performance']['f1_score']:.4f}")
    
    def test_regression_with_negative_values(self):
        """Test regression with negative target values"""
        print("\n=== Testing Regression - Negative Values ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'f1': np.random.randn(100),
            'f2': np.random.randn(100),
            'target': np.random.randn(100) * 50 - 25  # Negative values included
        })
        
        result = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.LINEAR_REGRESSION
        )
        
        assert 'mae' in result['performance']
        assert 'rmse' in result['performance']
        
        print(f"✓ Regression with negative values handled")
        print(f"  - MAE: {result['performance']['mae']:.4f}")
    
    def test_train_with_missing_in_features(self):
        """Test training with missing values in features"""
        print("\n=== Testing Training with Missing Values ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'f1': [1, 2, None, 4, 5, 6, 7, 8, 9, 10],
            'f2': [10, None, 30, 40, 50, 60, 70, 80, 90, 100],
            'f3': np.random.randn(10),
            'target': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        })
        
        result = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.LOGISTIC_REGRESSION,
            cross_validation=2
        )
        
        assert 'model_id' in result
        
        print(f"✓ Missing values in features handled")
    
    def test_auto_select_with_large_dataset(self):
        """Test auto selection with large dataset"""
        print("\n=== Testing Auto Select - Large Dataset ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'f1': np.random.randn(500),
            'f2': np.random.randn(500),
            'f3': np.random.randn(500),
            'f4': np.random.randn(500),
            'f5': np.random.randn(500),
            'target': np.random.choice(['A', 'B', 'C'], 500)
        })
        
        result = tool.auto_select_model(data=data, target='target')
        
        assert 'recommended_model' in result
        assert 'reasoning' in result
        
        print(f"✓ Auto selection for large dataset")
        print(f"  - Recommended: {result['recommended_model']}")
    
    def test_model_storage(self):
        """Test that trained models are stored correctly"""
        print("\n=== Testing Model Storage ===")
        tool = ModelTrainerTool()
        
        data = pd.DataFrame({
            'f1': np.random.randn(50),
            'f2': np.random.randn(50),
            'target': np.random.choice([0, 1], 50)
        })
        
        result1 = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.LOGISTIC_REGRESSION,
            cross_validation=2
        )
        
        result2 = tool.train_model(
            data=data,
            target='target',
            model_type=ModelType.RANDOM_FOREST_CLASSIFIER,
            cross_validation=2
        )
        
        assert len(tool.trained_models) == 2
        assert result1['model_id'] != result2['model_id']
        
        print(f"✓ Models stored correctly")
        print(f"  - Total models: {len(tool.trained_models)}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

