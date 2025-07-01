# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Tim Dumol <tim@timdumol.com>
# Copyright (C) 2013- The Spyder Development Team
# Distributed under the terms of the BSD License

"""Sphinx conf file for the docrepr library"""

import os
import sys

#==============================================================================
# General configuration
#==============================================================================

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.append(os.path.abspath('./sphinxext'))

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# MathJax load path (doesn't have effect for sphinx 1.0-)
mathjax_path = 'MathJax/MathJax.js'

# JsMath load path (doesn't have effect for sphinx 1.1+)
jsmath_path = 'easy/load.js'

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'docstring'

# General information about the project.
project = u"Docrepr library"
copyright = u''

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['.build']

# The reST default role (used for this markup: `text`) to use for all documents.
#
# TODO: This role has to be set on a per project basis, i.e. numpy, sympy,
# mpmath, etc, use different default_role's which give different rendered
# docstrings. Setting this to None until it's solved.
default_role = 'None'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

#==============================================================================
# Options for HTML output
#==============================================================================

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

# A dictionary of values to pass into the template engine’s context for all
# pages
html_context = {}

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# If false, no module index is generated.
html_use_modindex = False

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
html_copy_source = False


#==============================================================================
# Plots
#==============================================================================
plot_pre_code = """
import numpy as np
np.random.seed(0)
"""
plot_include_source = True
plot_html_show_source_link = False
plot_html_show_formats = False
plot_formats = [('png', 100)]
plot_working_directory = '/tmp'

import math
phi = (math.sqrt(5) + 1)/2

plot_rcparams = {
    'font.size': 8,
    'axes.titlesize': 8,
    'axes.labelsize': 8,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.figsize': (3*phi, 3),
    'figure.subplot.bottom': 0.2,
    'figure.subplot.left': 0.2,
    'figure.subplot.right': 0.9,
    'figure.subplot.top': 0.85,
    'figure.subplot.wspace': 0.4,
    'text.usetex': False,
}
