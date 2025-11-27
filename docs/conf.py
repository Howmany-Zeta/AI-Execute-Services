# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from datetime import datetime

# -- Path setup --------------------------------------------------------------
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'AIECS'
copyright = f'{datetime.now().year}, AIECS Team'
author = 'AIECS Team'
release = '1.5.3'
version = '1.5.3'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',           # Core autodoc extension
    'sphinx.ext.autosummary',       # Generate autodoc summaries
    'sphinx.ext.napoleon',          # Support for NumPy and Google style docstrings
    'sphinx.ext.viewcode',          # Add links to highlighted source code
    'sphinx.ext.intersphinx',       # Link to other project's documentation
    'sphinx.ext.todo',              # Support for todo items
    'sphinx.ext.coverage',          # Collect doc coverage stats
    'sphinx_autodoc_typehints',     # Automatically document type hints
    'sphinx_copybutton',            # Add copy button to code blocks
    'myst_parser',                  # Support for Markdown files
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The suffix(es) of source filenames.
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# The master toctree document.
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
    'display_version': True,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------

# -- Options for autodoc extension -------------------------------------------
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Automatically extract typehints when specified and place them in
# descriptions of the relevant function/method.
autodoc_typehints = 'description'

# Don't show class signature with the class' name.
autodoc_class_signature = 'separated'

# -- Options for autosummary extension ---------------------------------------
autosummary_generate = True

# -- Options for intersphinx extension ---------------------------------------
# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'fastapi': ('https://fastapi.tiangolo.com/', None),
    'pydantic': ('https://docs.pydantic.dev/latest/', None),
    'sqlalchemy': ('https://docs.sqlalchemy.org/en/20/', None),
}

# -- Options for todo extension ----------------------------------------------
# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# -- Options for Napoleon extension ------------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# -- Options for MyST parser -------------------------------------------------
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
    "tasklist",
]

