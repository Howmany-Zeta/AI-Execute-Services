# Publishing AIECS to PyPI

## Prerequisites

1. Create an account on [PyPI](https://pypi.org/) and [TestPyPI](https://test.pypi.org/)
2. Install build tools:
   ```bash
   pip install build twine
   ```

## Build the Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build the package
python -m build
```

## Test the Package Locally

```bash
# Create a virtual environment for testing
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install the package locally
pip install dist/aiecs-1.0.0-py3-none-any.whl

# Test the installation
python -c "import aiecs; print(aiecs.__name__)"
aiecs --help
aiecs-patch-weasel --help

# Deactivate test environment
deactivate
```

## Upload to TestPyPI (Recommended First)

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ aiecs
```

## Upload to PyPI

```bash
# Upload to PyPI
python -m twine upload dist/*
```

## Post-Upload Verification

```bash
# Install from PyPI
pip install aiecs

# Verify the installation
python -c "import aiecs; print('AIECS installed successfully!')"
```

## Version Bumping

Before releasing a new version:

1. Update version in `pyproject.toml`
2. Update version in `setup.py`
3. Update version in `aiecs/main.py` (if applicable)
4. Update CHANGELOG (if you have one)
5. Commit changes
6. Tag the release: `git tag v1.1.1`
7. Push tags: `git push --tags`
