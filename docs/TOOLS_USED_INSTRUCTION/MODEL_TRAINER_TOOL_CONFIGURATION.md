# Model Trainer Tool Configuration Guide

## Overview

The Model Trainer Tool is an AutoML and machine learning model training tool that provides AutoML capabilities with automatic model selection for classification and regression, hyperparameter tuning, model evaluation and comparison, feature importance analysis, and model explanation support. It can train multiple model types, perform hyperparameter tuning, evaluate and compare models, generate feature importance, and provide model explanations. The tool supports various model types (logistic regression, linear regression, random forest, gradient boosting) and task types (classification, regression, clustering). The tool can be configured via environment variables using the `MODEL_TRAINER_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Model Trainer Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
MODEL_TRAINER_TEST_SIZE=0.2
MODEL_TRAINER_RANDOM_STATE=42
MODEL_TRAINER_CV_FOLDS=5
MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=false
MODEL_TRAINER_MAX_TUNING_ITERATIONS=20
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.statistics.model_trainer_tool import ModelTrainerTool

# The tool will automatically use the environment variables
model_trainer = ModelTrainerTool()
```

### Multiple Environment Files

You can use different `.env` files for different environments:

```python
import os
from dotenv import load_dotenv

# Load environment-specific configuration
env = os.getenv('APP_ENV', 'development')

if env == 'production':
    load_dotenv('.env.production')
elif env == 'staging':
    load_dotenv('.env.staging')
else:
    load_dotenv('.env.development')

from aiecs.tools.statistics.model_trainer_tool import ModelTrainerTool
model_trainer = ModelTrainerTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for robust model training
MODEL_TRAINER_TEST_SIZE=0.2
MODEL_TRAINER_RANDOM_STATE=42
MODEL_TRAINER_CV_FOLDS=10
MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=true
MODEL_TRAINER_MAX_TUNING_ITERATIONS=50
```

**Example `.env.development`:**
```bash
# Development settings - optimized for testing and debugging
MODEL_TRAINER_TEST_SIZE=0.3
MODEL_TRAINER_RANDOM_STATE=123
MODEL_TRAINER_CV_FOLDS=3
MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=false
MODEL_TRAINER_MAX_TUNING_ITERATIONS=10
```

### Best Practices for .env Files

1. **Never commit .env files to version control** - Add `.env` to your `.gitignore`:
   ```gitignore
   # .gitignore
   .env
   .env.local
   .env.*.local
   .env.production
   .env.staging
   ```

2. **Provide a template** - Create `.env.example` with documented dummy values:
   ```bash
   # .env.example
   # Model Trainer Tool Configuration
   
   # Proportion of data to use for testing
   MODEL_TRAINER_TEST_SIZE=0.2
   
   # Random state for reproducibility
   MODEL_TRAINER_RANDOM_STATE=42
   
   # Number of cross-validation folds
   MODEL_TRAINER_CV_FOLDS=5
   
   # Whether to enable hyperparameter tuning
   MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=false
   
   # Maximum number of hyperparameter tuning iterations
   MODEL_TRAINER_MAX_TUNING_ITERATIONS=20
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Floats: Decimal numbers: `0.2`, `0.3`
   - Integers: Plain numbers: `42`, `5`, `20`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Test Size

**Environment Variable:** `MODEL_TRAINER_TEST_SIZE`

**Type:** Float

**Default:** `0.2`

**Description:** Proportion of data to use for testing. This determines how much of the dataset is reserved for model evaluation.

**Common Values:**
- `0.1` - Small test set (10% for testing)
- `0.2` - Standard test set (20% for testing, default)
- `0.3` - Large test set (30% for testing)
- `0.4` - Very large test set (40% for testing)

**Example:**
```bash
export MODEL_TRAINER_TEST_SIZE=0.2
```

**Test Size Note:** Larger test sets provide more reliable evaluation but less training data.

### 2. Random State

**Environment Variable:** `MODEL_TRAINER_RANDOM_STATE`

**Type:** Integer

**Default:** `42`

**Description:** Random state for reproducibility. This ensures consistent results across runs by controlling random number generation.

**Common Values:**
- `42` - Standard random state (default)
- `123` - Alternative random state
- `0` - Zero random state
- `None` - Truly random (not reproducible)

**Example:**
```bash
export MODEL_TRAINER_RANDOM_STATE=42
```

**Random State Note:** Use the same random state for reproducible results across experiments.

### 3. CV Folds

**Environment Variable:** `MODEL_TRAINER_CV_FOLDS`

**Type:** Integer

**Default:** `5`

**Description:** Number of cross-validation folds for model evaluation. This determines how many times the data is split for cross-validation.

**Common Values:**
- `3` - Minimal cross-validation (3 folds)
- `5` - Standard cross-validation (5 folds, default)
- `10` - Comprehensive cross-validation (10 folds)
- `20` - Extensive cross-validation (20 folds)

**Example:**
```bash
export MODEL_TRAINER_CV_FOLDS=5
```

**CV Folds Note:** More folds provide better evaluation but take longer to compute.

### 4. Enable Hyperparameter Tuning

**Environment Variable:** `MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING`

**Type:** Boolean

**Default:** `False`

**Description:** Whether to enable hyperparameter tuning. When enabled, the tool will automatically search for optimal hyperparameters.

**Values:**
- `true` - Enable hyperparameter tuning
- `false` - Disable hyperparameter tuning (default)

**Example:**
```bash
export MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=true
```

**Tuning Note:** Hyperparameter tuning improves model performance but significantly increases training time.

### 5. Max Tuning Iterations

**Environment Variable:** `MODEL_TRAINER_MAX_TUNING_ITERATIONS`

**Type:** Integer

**Default:** `20`

**Description:** Maximum number of hyperparameter tuning iterations. This limits how many different hyperparameter combinations are tested.

**Common Values:**
- `10` - Quick tuning (10 iterations)
- `20` - Standard tuning (20 iterations, default)
- `50` - Comprehensive tuning (50 iterations)
- `100` - Extensive tuning (100 iterations)

**Example:**
```bash
export MODEL_TRAINER_MAX_TUNING_ITERATIONS=50
```

**Iterations Note:** More iterations may find better hyperparameters but take much longer.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic model training parameters
export MODEL_TRAINER_TEST_SIZE=0.2
export MODEL_TRAINER_RANDOM_STATE=42
export MODEL_TRAINER_CV_FOLDS=5
export MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=false
export MODEL_TRAINER_MAX_TUNING_ITERATIONS=20

# Run your application
python app.py
```

### Example 2: Production Configuration with Tuning

```bash
# Optimized for production with hyperparameter tuning
export MODEL_TRAINER_TEST_SIZE=0.2
export MODEL_TRAINER_RANDOM_STATE=42
export MODEL_TRAINER_CV_FOLDS=10
export MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=true
export MODEL_TRAINER_MAX_TUNING_ITERATIONS=50
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export MODEL_TRAINER_TEST_SIZE=0.3
export MODEL_TRAINER_RANDOM_STATE=123
export MODEL_TRAINER_CV_FOLDS=3
export MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=false
export MODEL_TRAINER_MAX_TUNING_ITERATIONS=10
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.statistics.model_trainer_tool import ModelTrainerTool

# Initialize with custom configuration
model_trainer = ModelTrainerTool(config={
    'test_size': 0.2,
    'random_state': 42,
    'cv_folds': 5,
    'enable_hyperparameter_tuning': False,
    'max_tuning_iterations': 20
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export MODEL_TRAINER_TEST_SIZE=0.2
export MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=false
```

```python
# Override for specific instance
model_trainer = ModelTrainerTool(config={
    'test_size': 0.3,  # This overrides the environment variable
    'enable_hyperparameter_tuning': True  # This overrides the environment variable
})
```

## Configuration Priority

When the Model Trainer Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `MODEL_TRAINER_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### Float Values

Floats should be provided as decimal numbers:

```bash
export MODEL_TRAINER_TEST_SIZE=0.2
export MODEL_TRAINER_TEST_SIZE=0.3
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export MODEL_TRAINER_RANDOM_STATE=42
export MODEL_TRAINER_CV_FOLDS=5
export MODEL_TRAINER_MAX_TUNING_ITERATIONS=20
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=true
export MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=false
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `test_size` must be a float between 0 and 1
- `random_state` must be a non-negative integer
- `cv_folds` must be a positive integer
- `enable_hyperparameter_tuning` must be a boolean
- `max_tuning_iterations` must be a positive integer

### Runtime Validation

When training models, the tool validates:

1. **Test size** - Test size must be reasonable for the dataset
2. **Cross-validation** - CV folds must be appropriate for data size
3. **Hyperparameter tuning** - Tuning iterations must be reasonable
4. **Data compatibility** - Data must be compatible with model training
5. **Memory requirements** - Training must not exceed memory limits

## Model Types

The Model Trainer Tool supports various model types:

### Classification Models
- **Logistic Regression** - Linear classification model
- **Random Forest Classifier** - Ensemble classification model
- **Gradient Boosting Classifier** - Gradient boosting classification

### Regression Models
- **Linear Regression** - Linear regression model
- **Random Forest Regressor** - Ensemble regression model
- **Gradient Boosting Regressor** - Gradient boosting regression

### Auto Selection
- **Auto** - Automatically select best model type

## Task Types

### Classification
- Binary classification
- Multi-class classification
- Multi-label classification

### Regression
- Linear regression
- Non-linear regression
- Time series regression

### Clustering
- K-means clustering
- Hierarchical clustering
- Density-based clustering

## Operations Supported

The Model Trainer Tool supports comprehensive machine learning operations:

### Basic Training
- `train_model` - Train machine learning models
- `train_classifier` - Train classification models
- `train_regressor` - Train regression models
- `auto_train` - Automatically train best model
- `train_multiple_models` - Train multiple model types

### Hyperparameter Tuning
- `tune_hyperparameters` - Perform hyperparameter tuning
- `grid_search` - Grid search hyperparameter optimization
- `random_search` - Random search hyperparameter optimization
- `bayesian_optimization` - Bayesian hyperparameter optimization
- `optimize_model` - Optimize model hyperparameters

### Model Evaluation
- `evaluate_model` - Evaluate model performance
- `cross_validate` - Perform cross-validation
- `compare_models` - Compare multiple models
- `generate_metrics` - Generate performance metrics
- `create_evaluation_report` - Create comprehensive evaluation report

### Feature Analysis
- `analyze_feature_importance` - Analyze feature importance
- `select_features` - Select important features
- `rank_features` - Rank features by importance
- `generate_feature_report` - Generate feature analysis report
- `visualize_features` - Visualize feature importance

### Model Management
- `save_model` - Save trained models
- `load_model` - Load saved models
- `export_model` - Export models in various formats
- `create_model_pipeline` - Create model training pipeline
- `deploy_model` - Deploy models for inference

### Advanced Operations
- `explain_model` - Generate model explanations
- `create_model_report` - Create comprehensive model report
- `validate_model` - Validate model performance
- `optimize_model_size` - Optimize model for deployment
- `benchmark_models` - Benchmark model performance

## Troubleshooting

### Issue: Model training fails

**Error:** `TrainingError` during model training

**Solutions:**
1. Check data quality and format
2. Verify feature engineering
3. Check memory availability
4. Validate hyperparameters

### Issue: Hyperparameter tuning takes too long

**Error:** Tuning process is very slow

**Solutions:**
```bash
# Reduce tuning iterations
export MODEL_TRAINER_MAX_TUNING_ITERATIONS=10

# Disable tuning for development
export MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=false
```

### Issue: Cross-validation errors

**Error:** CV validation fails

**Solutions:**
```bash
# Reduce CV folds
export MODEL_TRAINER_CV_FOLDS=3

# Check data size and quality
model_trainer.validate_data(data)
```

### Issue: Memory usage exceeded

**Error:** Out of memory during training

**Solutions:**
1. Reduce dataset size
2. Use simpler models
3. Disable hyperparameter tuning
4. Process data in batches

### Issue: Poor model performance

**Error:** Low model accuracy/scores

**Solutions:**
1. Enable hyperparameter tuning
2. Increase CV folds for better evaluation
3. Check feature engineering
4. Try different model types

### Issue: Non-reproducible results

**Error:** Results vary between runs

**Solutions:**
```bash
# Set fixed random state
export MODEL_TRAINER_RANDOM_STATE=42

# Ensure consistent data preprocessing
model_trainer.set_random_state(42)
```

### Issue: Test set too small/large

**Error:** Unreliable model evaluation

**Solutions:**
```bash
# Adjust test size
export MODEL_TRAINER_TEST_SIZE=0.2

# Or use cross-validation instead
export MODEL_TRAINER_CV_FOLDS=10
```

## Best Practices

### Performance Optimization

1. **Test Size Selection** - Choose appropriate test size for dataset
2. **CV Folds** - Use appropriate number of CV folds
3. **Hyperparameter Tuning** - Enable only when needed
4. **Model Selection** - Choose appropriate model types
5. **Feature Engineering** - Optimize feature selection

### Error Handling

1. **Graceful Degradation** - Handle training failures gracefully
2. **Validation** - Validate data before training
3. **Fallback Strategies** - Provide fallback model types
4. **Error Logging** - Log errors for debugging and monitoring
5. **User Feedback** - Provide clear error messages

### Security

1. **Data Privacy** - Ensure data privacy during training
2. **Model Security** - Secure trained models
3. **Access Control** - Control access to training results
4. **Audit Logging** - Log training activities
5. **Compliance** - Ensure compliance with regulations

### Resource Management

1. **Memory Monitoring** - Monitor memory usage during training
2. **Processing Time** - Set reasonable timeouts
3. **Storage Optimization** - Optimize model storage
4. **Cleanup** - Clean up temporary files
5. **Resource Limits** - Set appropriate resource limits

### Integration

1. **Tool Dependencies** - Ensure required tools are available
2. **API Compatibility** - Maintain API compatibility
3. **Error Propagation** - Properly propagate errors
4. **Logging Integration** - Integrate with logging systems
5. **Monitoring** - Monitor tool performance and usage

### Development vs Production

**Development:**
```bash
MODEL_TRAINER_TEST_SIZE=0.3
MODEL_TRAINER_RANDOM_STATE=123
MODEL_TRAINER_CV_FOLDS=3
MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=false
MODEL_TRAINER_MAX_TUNING_ITERATIONS=10
```

**Production:**
```bash
MODEL_TRAINER_TEST_SIZE=0.2
MODEL_TRAINER_RANDOM_STATE=42
MODEL_TRAINER_CV_FOLDS=10
MODEL_TRAINER_ENABLE_HYPERPARAMETER_TUNING=true
MODEL_TRAINER_MAX_TUNING_ITERATIONS=50
```

### Error Handling

Always wrap training operations in try-except blocks:

```python
from aiecs.tools.statistics.model_trainer_tool import ModelTrainerTool, ModelTrainerError, TrainingError

model_trainer = ModelTrainerTool()

try:
    model = model_trainer.train_model(
        X_train=X_train,
        y_train=y_train,
        model_type='auto',
        task_type='classification'
    )
except TrainingError as e:
    print(f"Training error: {e}")
except ModelTrainerError as e:
    print(f"Model trainer error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv

# Install data processing dependencies
pip install pandas numpy scikit-learn

# Install machine learning dependencies
pip install scikit-learn xgboost lightgbm
```

### Optional Dependencies

```bash
# For hyperparameter tuning
pip install optuna hyperopt scikit-optimize

# For model explanation
pip install shap lime

# For advanced models
pip install catboost

# For model deployment
pip install joblib pickle
```

### Verification

```python
# Test dependency availability
try:
    import pandas
    import numpy
    import sklearn
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test ML libraries availability
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    print("Scikit-learn available")
except ImportError:
    print("Scikit-learn not available")

# Test hyperparameter tuning availability
try:
    import optuna
    print("Hyperparameter tuning available")
except ImportError:
    print("Hyperparameter tuning not available")

# Test model explanation availability
try:
    import shap
    import lime
    print("Model explanation available")
except ImportError:
    print("Model explanation not available")
```

## Related Documentation

- Tool implementation details in the source code
- Statistics tool documentation for statistical analysis
- Data transformer tool documentation for feature engineering
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Model Trainer Tool configuration:
- Check the tool source code for implementation details
- Review statistics tool documentation for statistical analysis
- Consult the main aiecs documentation for architecture overview
- Test with simple datasets first to isolate configuration vs. training issues
- Verify data compatibility and format requirements
- Check model type and task type settings
- Ensure proper hyperparameter tuning configuration
- Validate data quality and preprocessing requirements
