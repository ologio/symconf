# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information ------------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "symconf"
copyright = "2025, Sam Griesemer"
author = "Sam Griesemer"

# -- General configuration ----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    # enables a directive to be specified manually that gathers module/object
    # summary details in a table
    "sphinx.ext.autosummary",
    # allow viewing source in the HTML pages
    "sphinx.ext.viewcode",
    # only really applies to manual docs; docstrings still need RST-like
    "myst_parser",
    # enables Google-style docstring formats
    "sphinx.ext.napoleon",
    # external extension that allows arg types to be inferred by type hints
    "sphinx_autodoc_typehints",
]
autosummary_generate = True
autosummary_imported_members = True

# include __init__ definitions in autodoc
autodoc_default_options = {
    "special-members": "__init__",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output --------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
# html_sidebars = {
#    '**': ['/modules.html'],
# }
