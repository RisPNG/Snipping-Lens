# -*- coding: utf-8 -*

"""
Process docstrings with Sphinx

AUTHORS:
- Tim Joseph Dumol (2009-09-29): initial version
- The Spyder Development Team: Maintenance

Copyright (C) 2009 Tim Dumol <tim@timdumol.com>
Copyright (C) 2013- The Spyder Development Team
Distributed under the terms of the BSD License

Taken from the Sage project (www.sagemath.org).
See here for the original version:
http://doc.sagemath.org/html/en/reference/notebook/sagenb/misc/sphinxify.html
"""

# Stdlib imports
import codecs
import inspect
import os
import os.path as osp
import re
import shutil
import sys
import tempfile
from xml.sax.saxutils import escape

# 3rd party imports
from docutils.utils import SystemMessage as SystemMessage
from jinja2 import Environment, FileSystemLoader
import sphinx
from sphinx.application import Sphinx

# Local imports
from . import options
from .utils import PY2, to_unicode_from_fs, to_binary_string


#-----------------------------------------------------------------------------
# Globals and constants
#-----------------------------------------------------------------------------
CONFDIR_PATH = osp.dirname(__file__)
CSS_PATH = osp.join(CONFDIR_PATH, 'static', 'css')
JS_PATH = osp.join(CONFDIR_PATH, 'js')
JQUERY_PATH = JS_PATH

if os.name == 'nt':
    CACHEDIR = tempfile.gettempdir() + osp.sep + 'docrepr'
else:
    username = to_unicode_from_fs(os.environ.get('USER'))
    CACHEDIR = tempfile.gettempdir() + osp.sep + 'docrepr-' + str(username)


#-----------------------------------------------------------------------------
# Utility functions
#-----------------------------------------------------------------------------
def is_sphinx_markup(docstring):
    """Returns whether a string contains Sphinx-style ReST markup."""
    # this could be made much more clever
    return ("`" in docstring or "::" in docstring)


def warning(message):
    """Print a warning message on the rich text view"""
    env = Environment()
    env.loader = FileSystemLoader(osp.join(CONFDIR_PATH, 'templates'))
    warning = env.get_template("warning.html")
    return warning.render(css_path=CSS_PATH, text=message)


def format_argspec(argspec):
    """Format argspect, convenience wrapper around inspect's.

    This takes a dict instead of ordered arguments and calls
    inspect.format_argspec with the arguments in the necessary order.
    """
    return inspect.formatargspec(argspec['args'], argspec['varargs'],
                                 argspec['varkw'], argspec['defaults'])


def getsignaturefromtext(text, objname):
    """Get object signatures from text (object documentation)

    Return a list containing a single string in most cases
    Example of multiple signatures: PyQt4 objects
    """
    # Default values
    if not text:
        text = ''
    if not objname:
        objname = ''
    # Regexps
    oneline_re = objname + r'\([^\)].+?(?<=[\w\]\}\'"])\)(?!,)'
    multiline_re = objname + r'\([^\)]+(?<=[\w\]\}\'"])\)(?!,)'
    multiline_end_parenleft_re = r'(%s\([^\)]+(\),\n.+)+(?<=[\w\]\}\'"])\))'
    # Grabbing signatures
    sigs_1 = re.findall(oneline_re + '|' + multiline_re, text)
    sigs_2 = [g[0] for g in re.findall(multiline_end_parenleft_re % objname, text)]
    all_sigs = sigs_1 + sigs_2
    # The most relevant signature is usually the first one. There could be
    # others in doctests but those are not so important
    if all_sigs:
        sig = all_sigs[0]
        sig = '(' + sig.split('(')[-1] # Remove objname
        return sig
    else:
        return ''


def generate_conf(directory):
    """
    Generates a Sphinx configuration file in `directory`.

    Parameters
    ----------
    directory : str
        Base directory to use
    """
    # conf.py file for Sphinx
    conf = osp.join(CONFDIR_PATH, 'conf.py')

    # Docstring layout page (in Jinja):
    layout = osp.join(osp.join(CONFDIR_PATH, 'templates'), 'layout.html')

    os.makedirs(osp.join(directory, 'templates'))
    os.makedirs(osp.join(directory, 'static'))
    shutil.copy(conf, directory)
    shutil.copy(layout, osp.join(directory, 'templates'))
    open(osp.join(directory, '__init__.py'), 'w').write('')
    open(osp.join(directory, 'static', 'empty'), 'w').write('')


def global_template_vars():
    """Generate a dictionary of global variables for our templates"""
    if options['local_mathjax']:
        # TODO: Fix local use of MathJax
        MATHJAX_PATH = "file:///" + osp.join(JS_PATH, 'mathjax')
    else:
        MATHJAX_PATH = "https://cdn.mathjax.org/mathjax/latest"

    global_vars = \
    {
      'css_path': CSS_PATH,
      'js_path': JS_PATH,
      'jquery_path': JQUERY_PATH,
      'mathjax_path': MATHJAX_PATH,
      'math_on': 'true' if options['render_math'] else '',
      'platform': sys.platform,
      'collapse': options['collapse_sections'],
      'use_qt4': options['use_qt4'],
      'outline': options['outline']
    }

    return global_vars


def init_template_vars(oinfo):
    """
    Initialize variables for our templates.

    It gives default values to the most important variables
    """
    tmpl_vars = global_template_vars()

    # Object name
    if oinfo['name'] is None:
        tmpl_vars['name'] = ''
    else:
        tmpl_vars['name'] = oinfo['name']

    # Argspec
    tmpl_vars['argspec'] = ''
    if oinfo['argspec'] is None:
        argspec = getsignaturefromtext(oinfo['docstring'], oinfo['name'])
        if argspec:
            tmpl_vars['argspec'] = argspec
    else:
        argspec = oinfo['argspec']
        try:
            has_self = argspec['args'][0] == 'self'
        except (KeyError, IndexError):
            fmt_argspec = getsignaturefromtext(oinfo['docstring'], oinfo['name'])
            if fmt_argspec:
                tmpl_vars['argspec'] = fmt_argspec
            else:
                tmpl_vars['argspec'] = '(...)'
        else:
            if has_self:
                argspec['args'] = argspec['args'][1:]
                tmpl_vars['argspec'] = format_argspec(argspec)

    # Type
    if oinfo['type_name'] is None:
        tmpl_vars['note'] = ''
    else:
        tmpl_vars['note'] = '%s' % oinfo['type_name']

    return tmpl_vars


def generate_extensions(render_math):
    """Generate list of Sphinx extensions"""
    # We need jsmath to get pretty plain-text latex in docstrings
    extensions = []
    if sphinx.__version__ < "1.1" or not render_math:
        extensions = ['sphinx.ext.jsmath']
    else:
        extensions = ['sphinx.ext.mathjax']

    # For scipy and matplotlib docstrings, which need this extension to
    # be rendered correctly (see Spyder Issue #1138)
    extensions.append('sphinx.ext.autosummary')

    # Plots
    try:
        # TODO: Add an option to avoid importing mpl every time
        import matplotlib   # analysis:ignore
        extensions.append('plot_directive')
    except ImportError:
        pass

    return extensions


#-----------------------------------------------------------------------------
# Sphinxify
#-----------------------------------------------------------------------------
def sphinxify(docstring, srcdir, output_format='html', temp_confdir=False):
    """
    Runs Sphinx on a docstring and outputs the processed content

    Parameters
    ----------
    docstring : str
        a ReST-formatted docstring

    srcdir : str
        Source directory where Sphinx is going to be run

    output_format:  str
        It can be either `html` or `text`.

    temp_confdir : bool
        Whether to create a temp conf dir for Sphinx

    Returns
    -------
    An Sphinx-processed string, in either HTML or plain text format, depending
    on the value of `output_format`
    """
    if docstring is None:
        docstring = ''
    
    # Rst file to sphinxify
    base_name = osp.join(srcdir, 'docstring')
    rst_name = base_name + '.rst'

    # Output file name
    if output_format == 'html':
        suffix = '.html'
    else:
        suffix = '.txt'
    output_name = base_name + suffix

    # This is needed so users can type \\ on latex eqnarray envs inside raw
    # docstrings
    template_vars = global_template_vars()
    if template_vars['math_on']:
        docstring = docstring.replace('\\\\', '\\\\\\\\')

    if not docstring or docstring == '<no docstring>':
        template_vars['warning'] = 'true'
        template_vars['warn_message'] = "No documentation available"

    # Write docstring to rst_name
    with codecs.open(rst_name, 'w', encoding='utf-8') as rst_file:
        rst_file.write(docstring)

    # Create confdir
    if temp_confdir:
        # TODO: This may be inefficient. Find a faster way to do it.
        confdir = tempfile.mkdtemp()
        confdir = to_unicode_from_fs(confdir)
        generate_conf(confdir)
    else:
        confdir = CONFDIR_PATH

    # Get extensions list
    extensions = generate_extensions(options['render_math'])

    # Override conf variables
    confoverrides = {'html_context': template_vars, 'extensions': extensions}

    # Create Sphinx app
    doctreedir = osp.join(srcdir, 'doctrees')
    sphinx_app = Sphinx(srcdir, confdir, srcdir, doctreedir, output_format,
                        confoverrides, status=None, warning=None,
                        freshenv=True, warningiserror=False, tags=None)

    # Run the app
    try:
        sphinx_app.build(None, [rst_name])
    except SystemMessage:
        # TODO: Make this message configurable, so that it can be translated
        error_message = "It was not possible to get rich help for this object"
        output = warning(error_message)
        return output

    # Some adjustments to the output
    if osp.exists(output_name):
        output = codecs.open(output_name, 'r', encoding='utf-8').read()
        output = output.replace('<pre>', '<pre class="literal-block">')
    else:
        error_message = "It was not possible to get rich help for this object"
        output = warning(error_message)

    # Remove temp confdir
    if temp_confdir:
        shutil.rmtree(confdir, ignore_errors=True)

    # Return contents
    return output


def rich_repr(oinfo):
    """
    Generate a rich representation of an object's docstring and several
    other metadata associated with it.

    These data are contained in an `oinfo` dict, as computed by the
    IPython.core.oinspect library

    Parameters
    ----------
    oinfo : dict
        An object info dictionary

    Returns
    -------
    The url of the page that contains the rich representation
    """
    # Create srcdir
    if not osp.isdir(CACHEDIR):
        os.mkdir(CACHEDIR)
    srcdir = tempfile.mkdtemp(dir=CACHEDIR)
    srcdir = to_unicode_from_fs(srcdir)

    output_file = osp.join(srcdir, 'rich_repr_output.html')

    template_vars = init_template_vars(oinfo)

    # Sphinxified dsocstring contents
    obj_doc = sphinxify(oinfo['docstring'], srcdir)
    template_vars['docstring'] = obj_doc

    if oinfo.get('class_docstring'):
        class_doc = sphinxify(oinfo['class_docstring'], srcdir)
        template_vars['class_docstring'] = class_doc
    else:
        template_vars['class_docstring'] = ''

    # Add link to docs.python.org
    # TODO: Make this really work (e.g. for the math module)
    template_vars['docs_py_org'] = ''
    file_def = oinfo.get('file')
    if file_def:
        lib_dirs = ['site-packages', 'dist-packages', 'pymodules']
        if not any([d in file_def for d in lib_dirs]):
            mod = file_def.split(os.sep)[-1]
            mod_name = mod.split('.')[0]
            if PY2:
                link = "https://docs.python.org/2/library/{0}.html#{0}.{1}".format(
                        mod_name, oinfo['name'])
            else:
                link = "https://docs.python.org/3/library/{0}.html#{0}.{1}".format(
                        mod_name, oinfo['name'])
            template_vars['docs_py_org'] = link

    # Add a class to several characters on the argspec. This way we can
    # highlight them using css, in a similar way to what IPython does.
    # NOTE: Before doing this, we escape common html chars so that they
    # don't interfere with the rest of html present in the page
    argspec = escape(template_vars['argspec'])
    for char in ['=', ',', '(', ')', '*', '**']:
        argspec = argspec.replace(char,
                         '<span class="argspec-highlight">' + char + '</span>')
    template_vars['argspec'] = argspec

    # Replace vars on the template
    env = Environment()
    env.loader = FileSystemLoader(osp.join(CONFDIR_PATH, 'templates'))
    page = env.get_template("rich_repr.html")
    output = page.render(**template_vars)

    # Rewrite output contents after adjustments
    with open(output_file, 'wb') as f:
        f.write(to_binary_string(output, encoding='utf-8'))

    # Return output file name
    return output_file
