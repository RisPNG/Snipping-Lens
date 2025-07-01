# IDLEX EXTENSION
from __future__ import print_function
##    """
##    Copyright(C) 2011 The Board of Trustees of the University of Illinois.
##    All rights reserved.
##
##    Developed by:   Roger D. Serwy
##                    University of Illinois
##
##    Permission is hereby granted, free of charge, to any person obtaining
##    a copy of this software and associated documentation files (the
##    "Software"), to deal with the Software without restriction, including
##    without limitation the rights to use, copy, modify, merge, publish,
##    distribute, sublicense, and/or sell copies of the Software, and to
##    permit persons to whom the Software is furnished to do so, subject to
##    the following conditions:
##
##    + Redistributions of source code must retain the above copyright
##      notice, this list of conditions and the following disclaimers.
##    + Redistributions in binary form must reproduce the above copyright
##      notice, this list of conditions and the following disclaimers in the
##      documentation and/or other materials provided with the distribution.
##    + Neither the names of Roger D. Serwy, the University of Illinois, nor
##      the names of its contributors may be used to endorse or promote
##      products derived from this Software without specific prior written
##      permission.
##
##    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
##    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
##    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
##    IN NO EVENT SHALL THE CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR
##    ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
##    CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH
##    THE SOFTWARE OR THE USE OR OTHER DEALINGS WITH THE SOFTWARE.
##
##
##
##
##    Cython Extension - provides basic Cython support for IDLE
##
##    This intercepts calls for running the module and routes it here.
##    Also, it installs a colorizer and patches EditorWindow so it works.
##
##    Run Cython Module:
##        - restarts shell
##        - does a "from MODULE import *"
##
##    Import/Reload Cython Module
##        - does "import MODULE" if not in sys.modules
##          else does a "reload(MODULE)"
##        - does not restart shell
##
##    To properly patch the idlelib source tree, you'd need to modify
##    EditorWindow.py's "ispythonsource" to include .pyx files as well as create
##    an appropriate color delegator. Since this is not
##    likely to be accepted into IDLE, I'll stick to small monkey-patching.
##
##
##    """

config_extension_def = """

[CythonScript]
enable=1

[CythonScript_cfgBindings]
cython-run=<Control-Key-e>
cython-import=<Control-Shift-Key-E>
cython-reload=
cython-pyximport-install=

"""

import sys
import os
import re
import time
from idlelib import PyShell
from idlelib.ColorDelegator import ColorDelegator, make_pat
from idlelib.configHandler import idleConf
import idlelib.IOBinding
import imp

DEBUG = False

HAS_CYTHON = True
HAS_RELOAD = False

try:
    imp.find_module('cython')
except ImportError:
    HAS_CYTHON = False

try:
    import pyximport
except ImportError:
    HAS_CYTHON = False
    

if HAS_CYTHON:
    if 'reload_support' in pyximport.install.__code__.co_varnames:
        HAS_RELOAD = True
    else:
        HAS_RELOAD = False



if sys.version < '3':
    import tkMessageBox
else:
    import tkinter.messagebox as tkMessageBox



CYTHON_IMPORT = 'import pyximport; pyximport.install(reload_support=True)'

def any_re(groupname, re_list):
    return "(?P<%s>" % groupname + "|".join(re_list) + ")"


cythonlist = "cdef, cpdef, intern, struct, union, enum, ctypedef, void, double, public, inline, api, nogil, gil, except, cimport, NULL, char, DEF, IF, ELSEIF, ELSE, readonly, bint, by, include".split(', ')
cython_re = r"([^.'\"\\#]\b|^)" + any_re("cython", cythonlist) + r"\b"


CYTHON_BACKGROUND = '#EEDDFF'

def get_cfg(cfg, type="bool", default=True):
    return idleConf.GetOption("extensions", "CythonScript",
                         cfg, type=type, default=default)

def set_cfg(cfg, b):
    return idleConf.SetOption("extensions", "CythonScript",
                      cfg,'%s' % b)

def dbprint(*args, **kwargs):
    args = (' CythonScript:',) + tuple(args)
    if DEBUG:
        print(*args, **kwargs)


if HAS_CYTHON or True:
    # add to filetypes in IOBinding
    f = idlelib.IOBinding.IOBinding.filetypes
    f.insert(1, ("Cython files", "*.pyx"))
    f.insert(0, ("Python/Cython files", "*.py *.pyw *.pyx", "TEXT"))


class CythonScript(object):
    menudefs = [
        ('run', [None,
            ('Run Cython Module', '<<cython-run>>'),
            ('Import/Reload Cython Module', '<<cython-import>>'),
            ]),
        ('shell', [('Install PyxImport', '<<cython-pyximport-install>>')]),
        ]

    def __init__(self, editwin):

        self.editwin = editwin
        self.text = editwin.text

        if isinstance(editwin, PyShell.PyShell):
            dbprint('running in shell', editwin)
            self.inshell = True
            return
        else:
            dbprint('running in editor', editwin)
        self.inshell = False
        self.ispythonsource_orig = editwin.ispythonsource
        editwin.ispythonsource = self.ispythonsource

        self.ec_id = None
        if self.iscython():
            self.text.after(10, self.editwin.ResetColorizer)

        self.text.after(10, self.ec_timer)


    def close(self):   # Extension is being unloaded
        if not self.inshell:
            self.editwin.ispythonsource = self.ispythonsource_orig
            self.ispythonsource_orig = None
            text = self.text
            text.unbind(self.cython_run_event)
            text.unbind(self.check_cython_event)
            self.ec_cancel()
        self.editwin = None
        self.text = None
        self.shell = None

    def _has_cython(func):  # decorator function
        def f(self, *args, **kwargs):
            if HAS_CYTHON:
                return func(self, *args, **kwargs)
            else:
                tkMessageBox.showerror("Cython not Found",
                                  "Cython was not found by IDLE. Make sure it is installed or disable the CythonScript extension. "
                                  "For more details about Cython, visit http://cython.org/",
                                  parent=self.editwin.text)
                return "break"
        return f



    def ec_timer(self, ev=None):
        """ Periodically try to install the colorizer. """
        self.ec_cancel()
        self.extend_colorizer()
        self.ec_id = self.text.after(1000, self.ec_timer)

    def ec_cancel(self):
        if self.ec_id is not None:
            self.text.after_cancel(self.ec_id)
            self.ec_id = None

    def extend_colorizer(self):
        """ Provides syntax highlighting for cython by patching the existing colorizer. """
        color = self.editwin.color
        if color is None:
            return

        p = color.prog.pattern
        if 'cython' in p:
            return # already extended

        if self.iscython() == False:
            return
        dbprint('extending colorizer')

        color.tagdefs['cython'] = color.tagdefs['KEYWORD'].copy()
        #color.tagdefs['cython']['background'] = CYTHON_BACKGROUND
        color.config_colors()

        rlist = []
        rlist.append(cython_re)
        rlist.append(p)

        color.prog = re.compile('|'.join(rlist), re.S)
        color.notify_range('1.0', 'end')

    @_has_cython
    def cython_pyximport_install_event(self, ev=None):
        dbprint('install_pyximport_event')
        if self.inshell:
            text = self.text
            runit = self.editwin.runit
        else:
            shell = self.editwin.flist.open_shell()
            text = shell.text
            runit = shell.runit

        text.delete('iomark', 'end-1c')
        text.insert('iomark', CYTHON_IMPORT)
        text.mark_set('insert', 'end-1c')

        text.after(1, runit)   # allow colorizer to kick in


    def ispythonsource(self, filename):
        """ Patch to EditorWindow's ispythonsource to detect .pyx files """
        # The ResetColorizer code calls into ispythonsource. Trick it.
        if filename:
            base, ext = os.path.splitext(os.path.basename(filename))
            if os.path.normcase(ext) in (".pyx",):
                return True
        return self.ispythonsource_orig(filename)


    def iscython(self, filename=None):
        if filename is None:
            filename = self.editwin.io.filename   # in case nothing specified
            if filename is None:  # still? this means the buffer is not saved
                return False
        base, ext = os.path.splitext(os.path.basename(filename))
        ext_list = (".pyx", ".pxd")
        if os.path.normcase(ext) in ext_list:
            return True
        else:
            return False

    @_has_cython
    def check_cython_event(self, ev=None):
        dbprint('check_cython_event')
        return "break"

    @_has_cython
    def add_cython_event(self, ev=None):
        self.text.insert('insert', CYTHON_IMPORT)

    def getfilename(self):
        if self.inshell:
            return None

        filename = self.editwin.io.filename
        if filename is None:
            tkMessageBox.showerror("No File Name",
                                  "Please save the buffer (with a .pyx extension).",
                                  parent=self.editwin.text)
        return filename

    @_has_cython
    def cython_import_event(self, ev=None):
        dbprint('cython_import_event')
        self.cython_run_event(do_import=True)

    @_has_cython
    def cython_run_event(self, ev=None, do_import=False):
        self.text.tag_remove("ERROR", "1.0", "end")

        filename = self.getfilename()
        if filename is None:
            return

        if not self.iscython(filename):
            dbprint('filename not cython')
            self.not_cython_message()
            return

        base, ext = os.path.splitext(os.path.basename(filename))
        modname = base
        dirname = os.path.dirname(filename)

        try:
            f = imp.find_module(modname)
            if f[2][0] != '.pyx':
                dbprint('Conflicting with .py', f)
                self.pycy_conflict(f[1])
                return "break"

        except ImportError as err:
            # good, .py or .pyc not found
            pass


        self.editwin.io.save(None)  # save the cython module so it is reloaded properly

        self.shell = shell = self.editwin.flist.open_shell()
        interp = shell.interp
        if PyShell.use_subprocess and not do_import:
            shell.restart_shell()

        interp.prepend_syspath(filename)
        src = r"""if 1:
            _filename = %(filename)r
            import sys as _sys
            from os.path import basename as _basename
            if (not _sys.argv or
                _basename(_sys.argv[0]) != _basename(_filename)):
                _sys.argv = [_filename]
            import os as _os
            _os.chdir(%(dirname)r)
            del _filename, _basename, _os
            
            if "pyximport" not in _sys.modules:
                import pyximport
                if %(has_reload)s:
                    pyximport.install(reload_support=True)
                else:
                    pyximport.install()
            try:
                if not %(do_import)s:
                    from %(modname)s import *
                else:
                    if "%(modname)s" not in _sys.modules:
                        #print('importing')
                        import %(modname)s
                    elif %(has_reload)s:
                        #print('reloading')
                        import %(modname)s
                        reload(%(modname)s)
                    else:
                        print('\nUnable to reload module. Your Cython version does not support module reloading.\n')
            except ImportError as err:
                print('\nThe Cython Module could not be built.\n')

            """ % {'filename':filename,
                   'dirname':dirname,
                   'modname':modname,
                   'do_import':do_import,
                   'has_reload':str(HAS_RELOAD)}
        interp.runcode(src.strip())  # BUGFIX: .strip() for Python 2.6 
        return "break"

    def not_cython_message(self):
        tkMessageBox.showerror("Not a Cython Script",
                              "This buffer is not a Cython script.\n" + \
                               "Save with a .pyx extension.",
                              parent=self.editwin.text)
    def pycy_conflict(self, filename):
        tkMessageBox.showerror("Cython Import Collision",
                              'The file "%s"\nconflicts with importing this Cython script. Please relocate the file or rename this buffer.' % (filename),
                              parent=self.editwin.text)
