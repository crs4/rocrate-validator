# Copyright (c) 2024 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

from rocrate_validator import __version__

# update PYTHONPATH
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

# Set project metadata
project = 'rocrate-validator'
copyright = '2024, CRS4'
author = 'Marco Enrico Piras, Luca Pireddu, Simone Leo'
release = __version__

github_url = "https://github.com/crs4/rocrate-validator"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.


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

# Determine the current git branch
branch = os.popen("git rev-parse --abbrev-ref HEAD").read().strip()

# -- Options for HTML output -------------------------------------------------
html_context = {
    "display_github": True,  # Integrate GitHub
    "github_user": "crs4",  # Username
    "github_repo": "rocrate-validator",  # Repo name
    "github_version": branch,  # Version
    "conf_py_path": "/docs/",  # Path in the checkout to the docs root
}
