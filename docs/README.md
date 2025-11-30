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
├── check_documentation.py  # Script to check for Chinese content and broken links
├── api/                 # API reference (auto-generated)
│   ├── core.rst
│   ├── domain.rst
│   ├── application.rst
│   ├── infrastructure.rst
│   ├── tools.rst
│   └── llm.rst
├── user/                # User-facing documentation (Markdown files)
│   ├── USAGE_GUIDE.md
│   ├── PROJECT_SUMMARY.md
│   ├── APPLICATION/     # Application layer documentation
│   ├── CONFIG/          # Configuration management
│   ├── CORE/            # Core interfaces and abstractions
│   ├── DOMAIN_AGENT/    # Agent domain documentation
│   ├── DOMAIN_COMMUNITY/# Community domain documentation
│   ├── DOMAIN_CONTEXT/  # Context domain documentation
│   ├── DOMAIN_EXECUTION/# Execution domain documentation
│   ├── DOMAIN_TASK/     # Task domain documentation
│   ├── INFRASTRUCTURE_MESSAGEING/  # Messaging infrastructure
│   ├── INFRASTRUCTURE_MONITORING/  # Monitoring infrastructure
│   ├── INFRASTRUCTURE_PERSISTENCE/  # Persistence infrastructure
│   ├── LLM/             # LLM integration documentation
│   ├── TASKS/           # Task execution documentation
│   ├── TOOLS/           # Tool framework documentation
│   ├── TOOLS_USED_INSTRUCTION/  # Tool usage instructions
│   ├── UTILS/           # Utility documentation
│   └── knowledge_graph/ # Knowledge graph documentation
├── developer/           # Developer documentation (not included in user build)
├── Makefile            # Build automation (Unix)
└── make.bat            # Build automation (Windows)
```

### User Documentation

The `user/` directory contains all user-facing documentation written in Markdown format. These files are:
- Translated to English (no Chinese content)
- Linked correctly (no broken internal links)
- Organized by domain/module for easy navigation
- Included in the Sphinx build via `index.rst`

All user documentation files are automatically included in the documentation build. To verify coverage, run:

```bash
cd docs
python check_documentation.py
python check_documentation.py --links-only
```

## Read the Docs

The documentation is automatically built and hosted on Read the Docs at:
https://aiecs.readthedocs.io

The build is configured via `.readthedocs.yaml` in the project root.

## Documentation Maintenance

### Checking Documentation Quality

The `check_documentation.py` script helps maintain documentation quality:

```bash
cd docs
# Check for Chinese content
python check_documentation.py

# Check for broken links only
python check_documentation.py --links-only

# Check for Chinese content only
python check_documentation.py --chinese-only
```

### Translation and Update Process

When updating user documentation:

1. **Translate any Chinese content**: All user-facing documentation must be in English
2. **Fix broken links**: Ensure all internal markdown links point to existing files
3. **Update API references**: Verify code examples match current API signatures
4. **Run quality checks**: Use `check_documentation.py` before committing
5. **Rebuild documentation**: Test the build locally with `make html`
6. **Update index.rst**: Ensure new files are added to the appropriate toctree section

### Adding New Documentation Files

When adding new markdown files to `docs/user/`:

1. Create the file in the appropriate directory
2. Add the file reference to `docs/index.rst` in the correct toctree section
3. Ensure the file path matches: `user/DIRECTORY/FILENAME` (without `.md` extension)
4. Verify the file builds correctly: `make html`
5. Run quality checks: `python check_documentation.py`

## Writing Documentation

### Markdown (User Documentation)

User-facing documentation in `docs/user/` uses Markdown format (.md). The MyST parser enables Sphinx to process these files.

**Headings:**
```markdown
# Main Title

## Section

### Subsection
```

**Code Blocks:**
```markdown
```python
def example():
    return "Hello"
```
```

**Internal Links:**
```markdown
[Link Text](./RELATIVE_PATH.md)
[Link Text](../PARENT_DIR/FILE.md)
[Link Text](../../developer/DIR/FILE.md)  # Links to developer docs
```

**Important Notes:**
- Use relative paths for internal links
- Links to developer documentation should use `../../developer/` prefix
- Avoid linking to code files (`.py`) - use API documentation instead
- Test all links with `check_documentation.py --links-only`

### reStructuredText

Core documentation files use reStructuredText (.rst) format. Here are some common patterns:

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

