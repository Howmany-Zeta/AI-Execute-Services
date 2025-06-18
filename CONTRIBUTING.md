# Contributing to Python Middleware

Thank you for your interest in contributing to the Python Middleware project. This guide will help you get started with the contribution process.

## Code Style Guidelines

We aim to maintain a high-quality, consistent codebase. To achieve this, we adhere to the following standards:

- **Code Formatting**: We use `black` for code formatting with a line length of 100 characters. Ensure your code is formatted using `black` before submitting a pull request.
- **Linting**: We use `flake8` for linting. Run `flake8` on your code to catch any style issues or potential errors.
- **Type Checking**: We use `mypy` for static type checking. Ensure your code passes type checks with `mypy` to maintain type safety.

Configuration files for these tools are provided in the repository (`.flake8`, `pyproject.toml`, `mypy.ini`).

## Documentation Standards

To ensure clarity and maintainability, all documentation, docstrings, and comments must be written in English and follow the NumPy documentation format. Below is an example of how to document a function using the NumPy style:

```python
def example_function(param1: int, param2: str) -> bool:
    """
    A brief description of what the function does.

    Parameters
    ----------
    param1 : int
        Description of the first parameter.
    param2 : str
        Description of the second parameter.

    Returns
    -------
    bool
        Description of the return value.

    Examples
    --------
    >>> example_function(5, "test")
    True
    """
    # Inline comments should also be in English
    return param1 > 0 and len(param2) > 0
```

Key points for documentation:
- Use descriptive, concise docstrings for all functions, classes, and modules.
- Include sections for `Parameters`, `Returns`, `Examples`, and others as applicable (e.g., `Raises`, `Notes`).
- Ensure all public APIs are thoroughly documented.

## Logging Standards

Logging should be consistent and informative. Use the `loguru` logger for all logging needs. Logs should be in English and provide clear context about the operation being performed or the error encountered.

Example of logging:
```python
from loguru import logger

logger.info(f"Processing data for user {user_id}")
logger.error(f"Failed to process data for user {user_id}: {str(error)}")
```

## Development Setup

To set up the development environment, follow these steps:

1. Clone the repository and navigate to the `python-middleware` directory.
2. Install the dependencies using:
   ```
   pip install -r requirements.txt
   ```
3. Run the linting and type checking tools to ensure your environment is set up correctly:
   ```
   flake8 .
   black . --check
   mypy .
   ```

## Pull Request Process

1. Create a branch with a descriptive name related to the feature or bug fix.
2. Make your changes, ensuring they adhere to the code style and documentation standards.
3. Run linting and type checking tools to verify your code:
   ```
   flake8 .
   black .
   mypy .
   ```
4. Commit your changes with a clear, descriptive commit message.
5. Push your branch to the repository and create a pull request.
6. Ensure your pull request includes a description of the changes and any related issues.

We appreciate your contributions and look forward to reviewing your pull request!