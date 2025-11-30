Contributing to AIECS
=====================

We welcome contributions to AIECS! This guide will help you get started.

Getting Started
---------------

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your feature or bugfix
4. Make your changes
5. Run tests to ensure everything works
6. Submit a pull request

Development Setup
-----------------

Prerequisites
~~~~~~~~~~~~~

* Python 3.10 or higher
* Git
* PostgreSQL (for integration tests)
* Redis (for integration tests)

Setting Up Development Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Clone your fork
   git clone https://github.com/YOUR_USERNAME/aiecs.git
   cd aiecs

   # Create a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install development dependencies
   pip install -e ".[dev]"

   # Install pre-commit hooks (optional)
   pre-commit install

Running Tests
-------------

Unit Tests
~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run specific test file
   pytest test/unit_tests/test_agent.py

   # Run with coverage
   pytest --cov=aiecs --cov-report=html

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run integration tests
   pytest test/integration_tests/

   # Run specific integration test
   pytest test/integration_tests/test_database.py

Code Quality
------------

Linting
~~~~~~~

.. code-block:: bash

   # Run flake8
   flake8 aiecs

   # Run mypy for type checking
   mypy aiecs

Formatting
~~~~~~~~~~

.. code-block:: bash

   # Format code with black
   black aiecs

   # Check formatting
   black --check aiecs

Code Style Guidelines
---------------------

* Follow PEP 8 style guide
* Use type hints for all function parameters and return values
* Write docstrings for all public functions and classes
* Keep functions small and focused
* Use meaningful variable names

Documentation
-------------

Writing Documentation
~~~~~~~~~~~~~~~~~~~~~

* Use reStructuredText format for documentation
* Include docstrings in Google or NumPy style
* Add examples to docstrings when appropriate
* Update relevant documentation when adding features

Building Documentation Locally
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Install documentation dependencies
   pip install -e ".[docs]"

   # Build documentation
   cd docs
   sphinx-build -b html . _build/html

   # View documentation
   open _build/html/index.html  # On macOS
   # Or navigate to docs/_build/html/index.html in your browser

Pull Request Process
--------------------

1. **Create a feature branch**: ``git checkout -b feature/your-feature-name``
2. **Make your changes**: Implement your feature or bugfix
3. **Add tests**: Ensure your changes are covered by tests
4. **Update documentation**: Update relevant documentation
5. **Run tests**: Make sure all tests pass
6. **Commit your changes**: Use clear, descriptive commit messages
7. **Push to your fork**: ``git push origin feature/your-feature-name``
8. **Submit a pull request**: Open a PR against the main repository

Commit Message Guidelines
-------------------------

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

Example:

.. code-block:: text

   Add support for custom LLM providers

   - Implement provider interface
   - Add configuration options
   - Update documentation

   Fixes #123

Reporting Bugs
--------------

When reporting bugs, please include:

* Your operating system and version
* Python version
* AIECS version
* Steps to reproduce the bug
* Expected behavior
* Actual behavior
* Any error messages or logs

Feature Requests
----------------

We welcome feature requests! Please:

* Check if the feature has already been requested
* Clearly describe the feature and its use case
* Explain why this feature would be useful
* Provide examples if possible

Code of Conduct
---------------

* Be respectful and inclusive
* Welcome newcomers
* Focus on constructive feedback
* Respect differing viewpoints

Questions?
----------

If you have questions about contributing, feel free to:

* Open an issue on GitHub
* Join our community discussions
* Contact the maintainers

Thank you for contributing to AIECS!

