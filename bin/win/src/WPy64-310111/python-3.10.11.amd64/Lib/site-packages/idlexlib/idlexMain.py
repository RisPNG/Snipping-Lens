#! /usr/bin/env python

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
##    """



# This module hotpatches EditorWindow.py to load idlex extensions properly

from __future__ import print_function
import sys

from idlexlib.extensionManager import extensionManager

import idlelib
import os
import __main__
import imp
import traceback
import re

from idlelib import macosxSupport

from idlexlib._version import __version__

version = __version__   # IdleX version

IDLE_DEFAULT_EXT = []    # list of default extensions that IDLE has


if sys.version < '3':
    from StringIO import StringIO
    from Tkinter import *
    import Tkinter as tkinter
    import tkFileDialog
    import tkMessageBox
else:
    from io import StringIO
    from tkinter import *
    import tkinter
    import tkinter.filedialog as tkFileDialog
    import tkinter.messagebox as tkMessageBox


from idlelib.configHandler import idleConf, IdleConfParser

ansi_re = re.compile(r'\x01?\x1b\[(.*?)m\x02?')
def strip_ansi(s):
    return ansi_re.sub("", s)


def install_idlex_manager():
    """ install IDLEX extension manager into IDLE """

    # 2011-11-15 Bugfix - change the user config file names for IdleX
    # to avoid a problem on Windows where pythonw.exe refuses to run
    # idle.pyw when an error occurs. However python.exe runs idle.py just fine.
    # See http://bugs.python.org/issue13582
    u = idleConf.userCfg
    for key, value in list(u.items()):
        # add "idlex-" to user config file names
        fullfile = value.file
        directory, filename = os.path.split(fullfile)
        if filename.startswith('idlex-'):
            new_filename = filename
        else:
            new_filename = 'idlex-' + filename
        new_fullfile = os.path.join(directory, new_filename)
        value.file = new_fullfile
        value.Load()

    mod = extensionManager.load_extension('idlexManager')
    mod.extensionManager = extensionManager
    mod.version = version
    mod.update_globals()


    # add idlex to the extension list
    e = idleConf.userCfg['extensions']
    if not e.has_section('idlexManager'):
        e.add_section('idlexManager')
    e.set('idlexManager', 'enable', '1')


def _printExt():
    a = []
    for i in idleConf.defaultCfg['extensions'].sections():
        if i.endswith('_cfgBindings') or i.endswith('_bindings'):
            continue
        a.append(i)
    print('Extensions: %s' % a)



###########################################################################
##
## HOTPATCHING CODE
##
###########################################################################

def fix_tk86():
    tkinter._Tk = tkinter.Tk
    def wrapper(func, name):
        Tcl_Obj = tkinter._tkinter.Tcl_Obj
        def f(*args, **kwargs):
            #print(name, 'wrapped', args, kwargs)
            #t = [i for i in args if isinstance(i, Tcl_Obj)]
            #for i in t:
            #    print(name, 'FOUND arg:', repr(i), type(i), str(i))

            args = [i if not isinstance(i, Tcl_Obj) else str(i)
                    for i in args]
            for key, value in kwargs.items():
                if isinstance(value, Tcl_Obj):
                    #print(name, 'FOUND kwarg:', key, value)
                    kwargs[key] = str(value)
            return func(*args, **kwargs)
        return f

    class TkReflector(object):
        def __init__(self, tk):
            self.tk = tk
        def __getattribute__(self, name):
            a = getattr(object.__getattribute__(self, 'tk'), name)
            if name in ['splitlist']:
            #if hasattr(a, '__call__'):
                return wrapper(a, name)
            else:
                return a

    class TkFix(tkinter.Tk):
        def __init__(self, *args, **kwargs):
            tkinter._Tk.__init__(self, *args, **kwargs)
            self.__tk = self.tk
            version = self.tk.call('info', 'patchlevel')
            if version.startswith('8.6'):
                self.tk = TkReflector(self.__tk)

    tkinter.Tk = TkFix



def _hotpatch():
    # Fix numerous outstanding IDLE issues...
    import idlelib.EditorWindow


    EditorWindowOrig = idlelib.EditorWindow.EditorWindow
    class EditorWindow(EditorWindowOrig):


        _invalid_keybindings = []  # keep track of invalid keybindings encountered
        _valid_keybindings = []

        # Work around a bug in IDLE for handling events bound to menu items.
        # The <<event-variables>> are stored globally, not locally to
        # each editor window. Without this, toggling a checked menu item
        # in one editor window toggles the item in ALL editor windows.
        # Issue 13179
        def __init__(self, flist=None, filename=None, key=None, root=None):
            if flist is not None:
                flist.vars = {}
            EditorWindowOrig.__init__(self, flist, filename, key, root)

        # FIXME: Do not transfer custom keybindings if IDLE keyset is set to default

        # Fix broken keybindings that has plagued IDLE for years.
        # Issue 12387, 4765, 13071, 6739, 5707, 11437
        def apply_bindings(self, keydefs=None):  # SUBCLASS to catch errors
            #return EditorWindowOrig.apply_bindings(self, keydefs)
            if keydefs is None:
                keydefs = self.Bindings.default_keydefs
            text = self.text
            text.keydefs = keydefs
            invalid = []
            for event, keylist in keydefs.items():
                for key in keylist:
                    try:
                        text.event_add(event, key)
                    except TclError as err:
                        #print(' Apply bindings error:', event, key)
                        invalid.append((event, key))
            if invalid:  # notify errors
                self._keybinding_error(invalid)


        def RemoveKeybindings(self):  # SUBCLASS to catch errors
            "Remove the keybindings before they are changed."
            EditorWindow._invalid_keybindings = []
            # Called from configDialog.py
            self.Bindings.default_keydefs = keydefs = idleConf.GetCurrentKeySet()
            for event, keylist in keydefs.items():
                for key in keylist:
                    try:
                        self.text.event_delete(event, key)
                    except Exception as err:
                        print(' Caught event_delete error:', err)
                        print(' For %s, %s' % (event, key))
                        pass

            for extensionName in self.get_standard_extension_names():
                xkeydefs = idleConf.GetExtensionBindings(extensionName)
                if xkeydefs:
                    for event, keylist in xkeydefs.items():
                        for key in keylist:
                            try:
                                self.text.event_delete(event, key)
                            except Exception as err:
                                print(' Caught event_delete error:', err)
                                print(' For %s, %s' % (event, key))
                                pass


        def _keybinding_error(self, invalid):
            """ Create an error message about keybindings. """

            new_invalid = [i for i in invalid if i not in EditorWindow._invalid_keybindings]
            if new_invalid:
                msg = ['There are invalid key bindings:', '']
                for ev, k in new_invalid:
                    while ev[0] == '<' and ev[-1] == '>':
                        ev = ev[1:-1]
                    msg.append('Action:%s' % ev)
                    msg.append('Key:%s' % k)
                    msg.append('')

                msg.extend(['Please reconfigure these bindings.'])
                def errormsg(msg=msg):
                    tkMessageBox.showerror(title='Invalid Key Bindings',
                                           message='\n'.join(msg),
                                           master=self.top,
                                           parent=self.top)

                EditorWindow._invalid_keybindings.extend(new_invalid)
                self.top.after(100, errormsg)

        def load_standard_extensions(self):
            for name in self.get_standard_extension_names():

                try:
                    if name in extensionManager.IDLE_EXTENSIONS:
                        self.load_extension(name)
                    else:
                        self.load_idlex_extension(name)
                except:
                    print("Failed to load extension", repr(name))
                    import traceback
                    traceback.print_exc()

        def load_idlex_extension(self, name):
            # import from idlex
            mod = extensionManager.load_extension(name)
            if mod is None:
                print("\nFailed to import IDLEX extension: %s" % name)
                return

            cls = getattr(mod, name)
            keydefs = idleConf.GetExtensionBindings(name)
            if hasattr(cls, "menudefs"):
                self.fill_menus(cls.menudefs, keydefs)
            ins = cls(self)

            self.extensions[name] = ins
            if keydefs:
                self.apply_bindings(keydefs)
                for vevent in keydefs.keys():
                    methodname = vevent.replace("-", "_")
                    while methodname[:1] == '<':
                        methodname = methodname[1:]
                    while methodname[-1:] == '>':
                        methodname = methodname[:-1]
                    methodname = methodname + "_event"
                    if hasattr(ins, methodname):
                        self.text.bind(vevent, getattr(ins, methodname))

    idlelib.EditorWindow.EditorWindow = EditorWindow

def macosx_workaround():
    # restore "Options" menu on MacOSX
    if not macosxSupport.runningAsOSXApp():
        return

    def restore(menu_specs):
        c = [a for a,b in menu_specs]
        if "options" not in c:
            menu_specs.insert(-2, ("options", "Options"))

    import idlelib.EditorWindow
    restore(idlelib.EditorWindow.EditorWindow.menu_specs)

    import idlelib.PyShell
    restore(idlelib.PyShell.PyShell.menu_specs)


class devnull:
    # For pythonw.exe on Windows...
    def __init__(self):
        pass
    def write(self, *args, **kwargs):
        pass
    def __getattr__(self, *args, **kwargs):
        return self.write

def pythonw_workaround():
    # Work around a bug in pythonw.exe that prevents IdleX from starting.
    if sys.stderr is None:
        sys.stderr = devnull()
    if sys.stdout is None:
        sys.stdout = devnull()


def main():

    pythonw_workaround()
    _hotpatch()
    fix_tk86()

    try:
        macosx_workaround()
    except:
        pass  # Tk on OSX should not be this fragile...

    install_idlex_manager()

    extensionManager.load_idlex_extensions()

    # Force a reset on Bindings...
    # Without this, user reconfiguration of the key bindings within IDLE may
    # generate an error on MultiCall unbind.
    import idlelib.Bindings
    idlelib.Bindings.default_keydefs = idleConf.GetCurrentKeySet()

    import idlelib.PyShell
    idlelib.PyShell.main()

if __name__ == '__main__':
    # start up IDLE with IdleX
    main()
