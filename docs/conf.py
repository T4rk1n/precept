# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

from precept import __version__ as version

# -- Project information -----------------------------------------------------

project = 'precept'
copyright = '2019, Philippe Duval'
author = 'Philippe Duval'

# The short X.Y version
# The full version, including alpha/beta/rc tags
release = version

# Configs

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'm2r',
]

templates_path = ['_templates']
source_suffix = ['.rst', '.md']
master_doc = 'contents'
language = None

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

pygments_style = 'friendly'

html_theme = 'flask'
html_theme_options = {'index_logo': None}
html_static_path = ['_static']

html_sidebars = {
    "**": [
        "globaltoc.html",
        "relations.html",
        "links.html",
        "sourcelink.html",
        "searchbox.html",
    ]
}
htmlhelp_basename = 'precept-docs'

# -- Extension configuration -------------------------------------------------


def skip(app, what, name, obj, skip, options):
    if name == "__init__":
        return False
    return skip


def setup(app):
    app.connect("autodoc-skip-member", skip)
    app.add_stylesheet('styles.css')

