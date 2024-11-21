# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
import os
project = 'rocrate-validator'
copyright = '2024, Marco Enrico Piras, Luca Pireddu, Simone Leo'
author = 'Marco Enrico Piras, Luca Pireddu, Simone Leo'
release = '0.4.7'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

# update PYTHONPATH
sys.path.insert(0, os.path.abspath('..'))

# Logo
# html_logo = '_static/logo.png'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosummary',
    'nbsphinx',
    'myst_parser',
    'sphinx.ext.mathjax',
    'enum_tools.autoenum',
]

templates_path = ['_templates']
# exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'experiments', 'ontologies', 'tests', 'logs', 'examples', 'debug']
# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '**.ipynb_checkpoints']


# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
# keep_warnings = False

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

autodoc_member_order = 'bysource'

autosummary_generate = True

autodoc_default_options = {
    # 'members': True,
    # Does now show base classes otherwise... why such bad defaults?
    # But with this it does show useless bases like `object`. What is one to do?
    # 'show-inheritance': True,
}