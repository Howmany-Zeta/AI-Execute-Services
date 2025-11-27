# AIECS Documentation

This directory contains the Sphinx documentation for AIECS.

## Building Documentation Locally

### Prerequisites

Install the documentation dependencies:

```bash
pip install -e ".[docs]"
```

Or install the dependencies directly:

```bash
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints myst-parser sphinx-copybutton
```

### Build HTML Documentation

```bash
cd docs
make html
```

Or on Windows:

```bash
cd docs
make.bat html
```

The built documentation will be in `docs/_build/html/`. Open `index.html` in your browser to view it.

### Build PDF Documentation

```bash
cd docs
make latexpdf
```

### Clean Build Files

```bash
cd docs
make clean
```

## Documentation Structure

```
docs/
├── conf.py              # Sphinx configuration
├── index.rst            # Main documentation index
├── installation.rst     # Installation guide
├── quickstart.rst       # Quick start guide
├── configuration.rst    # Configuration guide
├── usage.rst            # Advanced usage guide
├── contributing.rst     # Contributing guide
├── changelog.rst        # Changelog
├── api/                 # API reference
│   ├── core.rst
│   ├── domain.rst
│   ├── application.rst
│   ├── infrastructure.rst
│   ├── tools.rst
│   └── llm.rst
├── Makefile            # Build automation (Unix)
└── make.bat            # Build automation (Windows)
```

## Read the Docs

The documentation is automatically built and hosted on Read the Docs at:
https://aiecs.readthedocs.io

The build is configured via `.readthedocs.yaml` in the project root.

## Writing Documentation

### reStructuredText

Most documentation files use reStructuredText (.rst) format. Here are some common patterns:

**Headings:**
```rst
Main Title
==========

Section
-------

Subsection
~~~~~~~~~~
```

**Code Blocks:**
```rst
.. code-block:: python

   def example():
       return "Hello"
```

**Links:**
```rst
:doc:`installation`  # Link to another doc
`External Link <https://example.com>`_
```

### Markdown

You can also use Markdown (.md) files thanks to the MyST parser extension.

### Docstrings

Use Google or NumPy style docstrings in your Python code:

```python
def example_function(param1: str, param2: int) -> bool:
    """Brief description of the function.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When something goes wrong
    """
    pass
```

## Troubleshooting

### Sphinx Not Found

If you get "sphinx-build: command not found", install the docs dependencies:

```bash
pip install -e ".[docs]"
```

### Import Errors

If autodoc can't import modules, ensure AIECS is installed:

```bash
pip install -e .
```

### Build Warnings

Fix any warnings before committing. Run with warnings as errors:

```bash
make html SPHINXOPTS="-W"
```

## Contributing

When adding new features:

1. Update relevant documentation files
2. Add docstrings to new code
3. Build docs locally to check for errors
4. Include documentation updates in your PR

For more details, see the [Contributing Guide](contributing.rst).

