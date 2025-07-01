# IDLEX EXTENSION
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
##    SubCode Extension - provides segmented code regions for IDLE
##    similar to Cell Mode in MATLAB and Cells as found in Sagemath.
##
##    Usage:
##
##        Subcode Regions are separated by "##" comment at the start of a line.
##        Subcode markers may be indented to run indented code.
##
##        The active subcode is a region where your cursor is.
##            * Ctrl+Return runs the active subcode region without
##              restarting the shell.
##            * Ctrl+Shift+Return runs the active subcode region,
##              and proceeds to the next subcode region.
##            * Ctrl+Up moves to the previous subcode region.
##            * Ctrl+Down moves to the next subcode region.
##
##        Using "Import Subcode" will import the subcode as a module
##        using the current file name.
##
##        Any lines starting with "#:" at the active subcode depth will
##        have the "#:" removed, effectively uncommenting commented code.
##        This is useful for developing logic for indented code by setting
##        test conditions.
##
##        For indented subcode markers, placing the cursor one character
##        to the left will enter the shallower subcode region.
##
##    NOTE:
##
##        This extension only works with spaces. Tabs won't work.
##
##    """

config_extension_def = """

[SubCode]
enable=1
enable_shell=0
enable_editor=1

active=True
indented=True
uncomment=True
highlighting=True

[SubCode_cfgBindings]
subcode-run=<Control-Key-Return>
subcode-run-proceed=<Control-Shift-Key-Return>
subcode-run-all=<Control-Key-F5>
subcode-import=<Alt-Key-Return>
subcode-import-proceed=<Alt-Shift-Key-Return>
subcode-import-all=
subcode-goto-previous=<Control-Key-Up>
subcode-goto-next=<Control-Key-Down>
subcode-goto-previous-same=<Control-Shift-Key-Up>
subcode-goto-next-same=<Control-Shift-Key-Down>
subcode-insert-marker=
subcode-enable-toggle=
subcode-indented-toggle=
subcode-uncomment-toggle=
subcode-highlighting-toggle=

"""



# Colors
COLOR_ADAPT = True  # Flag for adapting subcode colors to the theme
                    # If FALSE, then use the following "constants":
SUBCODE_FOREGROUND = '#DD0000'          # Foreground color for a subcode marker
SUBCODE_BACKGROUND = '#D0D0D0'          # Background color for a subcode marker
SUBCODE_HIGHLIGHT = '#DDFFDD'           # Active Region Highlighting
SUBCODE_HIGHLIGHT_OUT = '#EEFFEE'       # Active Region Unfocused Window


SUBCODE_STR = "SubCode"
SUBCODE_INSERT = '## [%s]\n' % SUBCODE_STR.lower() # Label for "Insert Subcode Marker"

HIGHLIGHT_INTERVAL = 250                # milliseconds

import sys
import os
import re
import time
import __future__
import tempfile
import shutil

from idlelib import PyShell
from idlelib.ColorDelegator import ColorDelegator, make_pat
from idlelib.configHandler import idleConf

if sys.version < '3':
    from Tkinter import END, SUNKEN, RAISED, GROOVE, RIDGE, FLAT, INSERT, Menu
    import tkMessageBox
else:
    from tkinter import END, SUNKEN, RAISED, GROOVE, RIDGE, FLAT, INSERT, Menu
    import tkinter.messagebox as tkMessageBox
    unicode = str


jn = lambda x,y: '%i.%i' % (x,y)        # join integers to text coordinates
sp = lambda x: list(map(int, x.split('.')))   # convert tkinter Text coordinate to a line and column tuple

def index(text, marker='insert', lineoffset=0):
    """ helper function to split a marker location of a text object """
    line, col = sp(text.index(marker))
    return (line + lineoffset, col)


def get_cfg(cfg, type="bool", default=True):
    return idleConf.GetOption("extensions", "SubCode",
                         cfg, type=type, default=default)

def set_cfg(cfg, b):
    return idleConf.SetOption("extensions", "SubCode",
                      cfg,'%s' % b)

def dbprint(func):  # A decorator for debugging
    def f(*args, **kwargs):
        print(func, args, kwargs)
        return func(*args, **kwargs)
    return f

# regex for startup_enable code. Only detect depth=0 markers
auto_re = '|'.join([r"(?P<MULTI>(?<![^\n])([ \t]*)##( {2,}[^\n]*\n|[ \t]*\n)(\2##[^\n]*?\n)*(\2##[^\n]*))",
        r"(?P<SUBCODE>((?<![^\n])##(( [^ \n]+[^\n]*)|[ ]*(?=\n))\n))"])
auto_detect = re.compile(auto_re)


SUBCODE_MENU = True  # TODO: make this configurable


class RunManager(object):
    """ Handles interactions with PyShell, including compiling code.
        Use the shell's compiler so that __future__ flags are synchronized.

        This is important for Python 2.x since I need __future__'s "division"
        to sync.

    """

    def __init__(self, editwin):
        self.editwin = editwin
        self.shell_flags = 0        # shell's compile flags
        self.tempfiles = []

        future_flags = self.future_flags = []

        # create mask of all valid future compile flags
        fmask = 0
        for name in __future__.all_feature_names:
            b = getattr(__future__, name)
            future_flags.append((name, b.compiler_flag))
            fmask = fmask | b.compiler_flag
        self.flag_mask = fmask

        self.temp_files = []
        self.shell = None

        self.compiler_flags = 0        # compiler flags


    def close(self):
        # delete all temp_files
        for f in self.temp_files:
            self._remove_temp(f)
            self._remove_temp(f+'c')  # for 2.x series - remove compile cache file

    def _remove_temp(self, f):
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception as err:
                print('Unable to remove temp file:', err)

    def get_shell(self):
        shell = self.editwin.flist.open_shell()
        self.shell = shell
        return shell

    def is_executing(self):
        if self.shell is None:
            return False
        return self.shell.interp.tkconsole.executing

    def is_idle(self, shell):
        try:
            if shell.interp.tkconsole.executing:
                return False # shell is busy
        except:
            return False # shell is not in a valid state
        return True

    def compile(self, source, filename, mode):
        """ Use the Interactive shell's compile flags to compile source. """
        # Side-effect - __future__ flags are remembered by the compiler
        shell = self.get_shell()
        return shell.interp.compile(source, filename, mode)

    def run(self, code, message=None):
        """ Returns True if code is actually executed in PyShell. """

        shell = self.get_shell()
        if not self.is_idle(shell):
            return False  # unable to execute

        if message:
            self.write_message(shell, '# Running ' + message)

        filename = self.editwin.io.filename
        if filename is not None:
            head, tail = os.path.split(filename)
            setup = r"""if 1:
                import sys as _sys
                if %(orig_dir)r not in _sys.path:
                    _sys.path.insert(0, %(orig_dir)r)
                del _sys
                """ % {'orig_dir':head}
            try:
                shell.interp.runcommand(setup.strip()) # BUGFIX: .strip() for Python 2.6
            except Exception as err:
                print(err)

        try:
            if isinstance(code, (str, unicode)):
                # only compile if not running from IPyIDLE
                if filename is None:
                    filename = '<untitled>'
                if isinstance(shell.interp, PyShell.ModifiedInterpreter):
                    code = shell.interp.compile(code, filename, 'exec')
                    
            shell.interp.runcode(code)
        except AttributeError as err:  # caused when holding ctrl+enter
            print('run error', err)
            return False

        return True

    def write_message(self, shell, message):
        """ Send some feedback to the Shell """
        console = shell.interp.tkconsole
        # fake out ModifiedUndoDelegator and tkconsole.
        # Using console.write can lead to runcode raising AttributeError
        console.text.insert('insert', '%s\n' % message)#, "COMMENT")
        endpos = 'insert +%ic' % (len(message)+1)
        console.text.mark_set('iomark', endpos)  # prevent history

    def run_as_import(self, code, message=None):
        """ Stuff code into a file and then import the file. Returns True if code could be run.
            May raise compiler errors.
        """
        shell = self.get_shell()
        if not self.is_idle(shell):
            return False # not able to run

        filename = self.editwin.io.filename
        if not filename:
            tkMessageBox.showwarning("Import %s" % SUBCODE_STR,
                              "The source file has no name.\nPlease save it first and then retry.",
                              parent=self.editwin.text)
            return False

        # At this point, we should be able to run the file
        head, tail = os.path.split(filename)
        mod_file = os.path.join(head, '_subcode_' + tail)

        self.temp_files.append(mod_file)


        mod, ext = os.path.splitext(os.path.basename(filename))

        target_flags, cmsg = self._get_future_flags()
        if cmsg:
            if message is not None:
                message += ('\n    # despite error: ' + cmsg)
            else:
                message = '# Error exists outside of subcode at: ' + cmsg

        fcmd = self._import_future_command(target_flags)

        try:
            f = open(mod_file, 'wb')
        except:
            # unable to open the file - present error message
            tkMessageBox.showerror("Import %s" % SUBCODE_STR,
                                   "Unable to create temporary module file: %r" % mod_file,
                                   parent=self.editwin.text)
            return False


        f.write(fcmd.encode())
        f.write(code.encode())
        f.close()

        if message:
            self.write_message(shell, '# Importing ' + message)

        setup = r"""if 1:
            import sys
            if %(orig_dir)r not in sys.path:
                sys.path.insert(0, %(orig_dir)r)
            try:
                if '_subcode_%(mod)s' not in sys.modules.keys():
                    import _subcode_%(mod)s as %(mod)s
                else:
                    import _subcode_%(mod)s as %(mod)s
                    reload(%(mod)s)
            except ImportError as err:
                print(err)
                """ % {'mod':mod,
                       'orig_dir':head}

        try:
            shell.interp.runcode(setup.strip())  # BUGFIX: .strip() for Python 2.6
        except Exception as err:
            print('Subcode - error in run_as_import:', err)
            return False

        return True

    def _get_future_flags(self):
        """ Compiles the entire module to see what __future__ flags are needed. """
        all_src = self.editwin.text.get('1.0', END)
        message = None
        try:
            c = compile(all_src, '', mode='exec')
            flags = c.co_flags & self.flag_mask
            self.compiler_flags = flags
        except Exception as err:
            #message = str(err)
            message = None
            flags = self.compiler_flags

        return flags, message

    def _import_future_command(self, target_flags):
        """ Returns the Python import command to enable a set of future flags """
        target_flags &= self.flag_mask
        future_list = []
        cmd = ''
        for name, flag in self.future_flags:
            if (target_flags & flag):
                future_list.append(name)

            if future_list:
                cmd = 'from __future__ import %s;' % ','.join(future_list)
        return cmd

    def restart_shell(self):
        """ Restart the PyShell subprocess, if possible. """
        shell = self.get_shell()
        if PyShell.use_subprocess:
            shell.restart_shell()
            return True
        return False



class SubCode(object):

    # Menu items for the regular IDLE menu configuration
    menudefs_normal = [
        ('options',[None,
                ('!Enable _%ss' % SUBCODE_STR, '<<subcode-enable-toggle>>'),
                ]),

        ('run', [None,
                 ('Run _%s'  % SUBCODE_STR, '<<subcode-run>>'),
                 ('Run %s and _Proceed'  % SUBCODE_STR, '<<subcode-run-proceed>>'),
                 ('Run _All %ss'  % SUBCODE_STR, '<<subcode-run-all>>'),
                 None,
                 ('Import %s'  % SUBCODE_STR, '<<subcode-import>>'),
                 ('Import %s and Proceed'  % SUBCODE_STR, '<<subcode-import-proceed>>'),
                 ('Import All %ss'  % SUBCODE_STR, '<<subcode-import-all>>'),
                 ]),
        ('format', [None,
                ('_Insert %s Marker'  % SUBCODE_STR, '<<subcode-insert-marker>>')]),
        ('edit', [None,
                ('Goto _Previous %s Marker'  % SUBCODE_STR, '<<subcode-goto-previous>>'),
                ('Goto _Next %s Marker'  % SUBCODE_STR, '<<subcode-goto-next>>'),
                  None]),
        ('options',
                [
                ('!Allow Indented %ss'  % SUBCODE_STR, '<<subcode-indented-toggle>>'),
                ('!Uncomment #: at depth', '<<subcode-uncomment-toggle>>'),
                ('!Highlight Active %s' % SUBCODE_STR, '<<subcode-highlighting-toggle>>'),
                 None,
                ]),
        ]


    # Menu items for a dedicated "SubCode" menu
    # Collapse the normal menu to a single menu 
    _L = []
    menudefs_dedicated = [('subcode', _L)]
    for menu, items in menudefs_normal:
        _L.extend(items)
    if _L[0] is None:
        _L.pop(0)
    if _L[-1] is None:
        _L.pop()
    del _L

    if SUBCODE_MENU:
        menudefs = menudefs_dedicated
    else:
        menudefs = menudefs_normal


    whitespace_re = {}  # cache for white space regex matchers

    SC_INSTANCES = []       # list of all subcode instances

    def __init__(self, editwin):
        ## Install the SubCode Color Delegator
        def getColorDelegator():
            """ Returns a SubCodeColorDelegator instance, properly initialized. """
            def f(*args, **kwargs):
                a = {'subcode_enable':self.enable,
                     'subcode_indented':self.indented}
                kwargs.update(a)
                return SubcodeColorDelegator(*args, **kwargs)
            return f

        self.ColorDelegatorOrig = editwin.ColorDelegator
        editwin.ColorDelegator = getColorDelegator()

        if SUBCODE_MENU:
            mbar = editwin.menubar
            menudict = editwin.menudict
            label=SUBCODE_STR
            underline=0
            menudict['subcode'] = menu = Menu(mbar, name='subcode')
            index = 5 # magic number - place SubCode after Run menu
            mbar.insert_cascade(index, label=label, menu=menu, underline=underline)
            keydefs = idleConf.GetExtensionBindings('SubCode')
            editwin.fill_menus(self.menudefs, keydefs)


        self.editwin = editwin
        self.text = editwin.text
        self.reset_id = None

        self.runmanager = RunManager(editwin)
        self.enable = False
        self.indented = False
        self.uncomment = False
        self.highlighting = False
        self.highlighter_init()
        self.subcode_indented(get_cfg("indented"), init=True)
        self.subcode_uncomment(get_cfg("uncomment"))
        self.subcode_highlighting(get_cfg("highlighting"))
        self.startup_enable()
        text = self.text
        text.bind('<FocusOut>', self.focus_out, '+')
        text.bind('<FocusIn>', self.focus_in, '+')

        text.bind('<<subcode-focus-editor>>', self.focus_editor)
        text.bind('<<toggle-tabs>>', self.using_tabs, '+')

        SubCode.SC_INSTANCES.append(self)


        text.bind("<<restart-shell>>", self.restart_shell_event, '+')
        text.bind("<<interrupt-execution>>", self.cancel_callback)

        self._BUG_FIX()

        if self.enable:
            self.ResetColorizer()


    def close(self):   # Extension is being unloaded
        self.runmanager.close()
        if self.hl_id:
            self.text.after_cancel(self.hl_id)
        idleConf.SaveUserCfgFiles()
        SubCode.SC_INSTANCES.remove(self)
        try:
            self.editwin.ColorDelegator = self.ColorDelegatorOrig
        finally:
            self.ColorDelegatorOrig = None

    def _BUG_FIX(self):
        # Two ColorDelegators get loaded on IDLE (only apparent on Windows).
        # This is a bug in IDLE itself. See Issue13495.
        # Must eliminate the ColorDelegator that is not supposed to be there.

        CD = []  # list of color delegators in the percolator chain
        per = self.editwin.per
        top = per.top
        while True:
            if isinstance(top, ColorDelegator):
                CD.append(top)
            top = top.delegate
            if top == per.bottom:
                break

        rcd = [i for i in CD if i is not self.editwin.color]
        for filt in rcd:
            print('  Removing a rogue color delegator instance.', filt)
            print('  See http://bugs.python.org/issue13495')
            per.removefilter(filt)

    def startup_enable(self):
        """ If the text buffer is empty, then use saved value.
            If text buffer has code, check if it has subcode markers.
        """
        src = self.text.get('1.0', 'end')
        if src.strip():
            m = auto_detect.search(src)
            while m:
                value = m.groupdict()['SUBCODE']
                if value:   # found depth=0 subcode marker, enable
                    if self.ispython(init=True):
                        self.subcode_enable(True, init=True)
                    break
                m = auto_detect.search(src, m.end())
        else:
            if self.ispython(init=True):
                #self.subcode_enable(False)
                self.subcode_enable(get_cfg("active"), init=True)

    def ResetColorizer(self):
        editwin = self.editwin
        editwin.ResetColorizer()
        if not isinstance(editwin.color, SubcodeColorDelegator):
            # Subcode Color Delegator is not being used.
            # Subcodes won't work. Disable subcode.
            print('  Subcode Internal Error: SubCodeColorDelegator not installed. ',
                  editwin.color)
            if self.enable:
                self.subcode_enable(b=False)

    def ispython(self, init=False):
        e = self.editwin
        filename = e.io.filename
        if filename is None:
            return True   # benefit of the doubt
        else:
            if not e.ispythonsource(filename):
                if not init and not self.enable:
                    # Show warning only if not initializing the extension.
                    # This avoids a message box when first opening
                    # non-python files.
                    self.text.after_idle(lambda:\
                    tkMessageBox.showwarning(SUBCODE_STR,
                                "%ss work only with valid Python files." % SUBCODE_STR,
                                parent=self.text))
                return False  # definitely not python
            else:
                return True

    def subcode_enable_toggle_event(self, ev=None):
        self.subcode_enable(not self.enable)
        return "break"

    def subcode_indented_toggle_event(self, ev=None):
        self.subcode_indented(not self.indented)
        return "break"

    def subcode_uncomment_toggle_event(self, ev=None):
        self.subcode_uncomment(not self.uncomment)
        return "break"

    def subcode_highlighting_toggle_event(self, ev=None):
        self.subcode_highlighting(not self.highlighting)
        return "break"


    def subcode_enable(self, b=True, init=False):
        if self.ispython(init=init):
            self.enable = b
            set_cfg("active", self.enable)
        else:
            self.enable = False

        if self.enable:
            self.text.after(1, lambda: self.text.event_generate("<<subcode-enable>>"))
            self.highlighter_schedule()
        else:
            self.text.after(1, lambda: self.text.event_generate("<<subcode-disable>>"))
            self.highlighter_schedule(cancel=True)
            self.text.tag_remove("ACTIVE", "1.0", END)

        self.editwin.setvar("<<subcode-enable-toggle>>", self.enable)
        if not init:
            self.ResetColorizer()

    def subcode_indented(self, b=True, init=False):
        self.indented = b
        set_cfg("indented", self.indented)
        self.editwin.setvar("<<subcode-indented-toggle>>", self.indented)
        if not init:
            self.ResetColorizer()

    def subcode_uncomment(self, b=True):
        self.uncomment = b
        set_cfg("uncomment", self.uncomment)
        self.editwin.setvar("<<subcode-uncomment-toggle>>", self.uncomment)

    def subcode_highlighting(self, b=True):
        self.highlighting = b
        set_cfg("highlighting", self.highlighting)
        self.editwin.setvar("<<subcode-highlighting-toggle>>", self.highlighting)
        if not b:
            self.text.tag_remove("ACTIVE", "1.0", END)
            self.hl_AC = None
        else:
            if self.enable:
                self.highlighter_schedule()

    def using_tabs(self, ev=None):
        if self.editwin.usetabs:
            tkMessageBox.showwarning("%s Tabs" % SUBCODE_STR,
                                     "%(sc)ss do not work with tabs.\nPlease convert tabs to spaces and then re-enable %(sc)ss." % {'sc':SUBCODE_STR},
                                     parent=self.editwin.text)
            self.subcode_enable(False)
        return "break"

    def _check_enable(auto=False):
        """ Decorator with arguments to intercept Tkinter event callbacks."""
        def f(func):
            def decfunc(self, ev=None):
                if self.enable:
                    if self.editwin.usetabs:
                        self.using_tabs()
                        return "break"
                    else:
                        return func(self, ev)
                else:
                    # FIXME: find more robust method to differentiate
                    # menu item events from key events.
                    if ev:
                        if ev.keysym_num == '??':  # menu event
                            tkMessageBox.showinfo("%ss Disabled" % SUBCODE_STR,
                                  "Please enable %ss to use this command." % SUBCODE_STR,
                                  parent=self.editwin.text)
                        elif auto:  # keyboard event and auto enabling
                            tkMessageBox.showinfo("%ss Enabled" % SUBCODE_STR,
                                  "%ss have just been enabled in response to your command. Please repeat your command." % SUBCODE_STR,
                                  parent=self.text)
                            self.subcode_enable()
                            return "break"

            return decfunc  # return the decorated function
        return f  # return the decorator

    @_check_enable()
    def subcode_insert_marker_event(self, event):
        # if cursor at beginning of line, insert before else insert after
        text = self.text
        sel = text.tag_ranges('sel')
        if sel: return
        offset = SUBCODE_INSERT.count('\n')
        line, column = index(text, INSERT)
        if column == 0:   # insert at the start of the line
            text.insert('insert', '%s\n' % SUBCODE_INSERT);
            text.mark_set('insert', '%i.0' % (line + 1 + offset))
        else:               # insert at the start of the next line
            text.insert('insert lineend', '\n%s' % SUBCODE_INSERT)
            text.mark_set('insert', '%i.0' % (line + 2 + offset))

    @_check_enable(auto=True)
    def subcode_run_event(self, ev=None):
        self.run_code()
        return "break"

    @_check_enable(auto=True)
    def subcode_run_proceed_event(self, ev=None):
        if self.run_code(): self.subcode_goto('nextsame')
        return "break"

    @_check_enable()
    def subcode_run_all_event(self, ev=None):
        self.run_code(entire=True)
        return "break"

    @_check_enable(auto=True)
    def subcode_import_event(self, ev=None):
        self.run_code(as_import=True)
        return "break"

    @_check_enable(auto=True)
    def subcode_import_proceed_event(self, ev=None):
        if self.run_code(as_import=True):
            self.subcode_goto('nextsame')
        return "break"

    @_check_enable()
    def subcode_import_all_event(self, ev=None):
        self.run_code(entire=True, as_import=True)
        return "break"

    def run_code(self, entire=False, as_import=False):
        """ Runs a subcode. Returns True if successful. """
        text = self.text
        fn = self.editwin.io.filename
        if fn is None:
            fn = 'untitled.py'

        file_head, file_tail = os.path.split(fn)

        if entire:
            end = text.index(END)
            sline = 1
            eline, endcol = sp(end)
            code = text.get('1.0', end)
            message = "All %ss [%s:1-%i]" % (SUBCODE_STR, file_tail, eline-1)
            depth = 0
        else:
            i = self.text.index('insert')
            sline, eline, depth = self.get_active_subcode(i)
            code = self.get_code(sline, eline, depth,
                                 header=True, uncomment=self.uncomment)
            subcodename = text.get('%i.0' % sline, '%i.0 lineend' % sline).strip()
            if sline == 1 and not subcodename.startswith('##'):
                subcodename = 'beginning of file'

            message = "%s [%s:%i-%i] '%s'" % \
                      (SUBCODE_STR, file_tail, sline, eline, subcodename)


        linestr = '%i-%i' % (sline, eline)
        filename = '%s:::%s at %s' % (fn,
                                      linestr,
                                      time.strftime("%H:%M:%S"))

        try:  # check for errors
            text.tag_remove("ERROR", '1.0', END)
            if not as_import:
                # TODO: optional syntax check for subcode
             
                code = self.runmanager.compile(code, filename, mode='exec')
                status = self.runmanager.run(code, message)
            else:
                status = self.runmanager.run_as_import(code, message)

        except (SyntaxError, OverflowError, ValueError) as err:
            self.handle_error(err, depth)
            status = False
        except Exception as err:
            # why?
            raise

        self.focus_editor()

        return status


    def handle_error(self, e, depth=0):
        """ Highlight the error and display it on the shell prompt """
        text = self.editwin.text
        try:
            msg, lineno, offset = e.msg, e.lineno, e.offset
            message = '\n    There is an error (%s) at line %i, column %i.\n' % \
              (msg, lineno, offset)
            self._highlight_error(lineno, offset, depth)
        except Exception as err:
            msg = e
            lineno = 0
            offset = 0
            message = '\n    There is an error: %s' % e

        # send error feedback to shell
        shell = self.editwin.flist.open_shell()
        shell.interp.tkconsole.stderr.write(message)
        shell.showprompt()
        self.focus_editor()

    def _highlight_error(self, lineno, offset, depth):
        text = self.text
        if offset is None:
            offset = 0
        offset += depth  # for dedented code

        pos = '0.0 + %i lines + %i chars' % (lineno - 1, offset - 1)
        pos = '%i.%i' % (lineno, offset-1)
        text.tag_add("ERROR", pos)

        if text.get(pos) != '\n':
            pos += '+1c'

        text.mark_set("insert", pos)
        text.see(pos)


    @_check_enable()
    def restart_shell_event(self, ev=None):
        self.runmanager.restart_shell()
        self.focus_editor()

    @_check_enable()
    def cancel_callback(self, ev=None):
        try:
            if self.text.compare("sel.first", "!=", "sel.last"):
                return # Active selection -- always use default binding
        except:
            pass

        # place message
        message = '# Sending KeyboardInterrupt from %s...\n' % SUBCODE_STR
        shell = self.editwin.flist.open_shell()
        if hasattr(shell, 'interp'):
            #shell.interp.tkconsole.stderr.write(message)
            shell.cancel_callback()
            self.text.update_idletasks()
            self.focus_editor()

        return "break"

    def focus_editor(self, ev=None):
        self.editwin.text.focus_set()
        self.editwin.top.lift()

    def get_prev_subcode(self, i):
        pr = self.text.tag_prevrange("SUBCODE", i)
        if pr:
            sline, depth = sp(pr[0])
        else:
            sline, depth = 1, 0
        return sline, depth

    def get_next_subcode(self, i, end=True):
        nr = self.text.tag_nextrange("SUBCODE", i+'+1c')
        if nr:
            eline, depth = sp(nr[0])
        else:
            if end:
                e = self.text.index('end')  # EOF is next subcode
                eline, depth = sp(e)
            else:
                eline, depth = sp(i)  # stay at location

        return eline, depth


    @_check_enable()
    def subcode_goto_previous_event(self, ev=None):
        return self.subcode_goto('prev')
    @_check_enable()
    def subcode_goto_next_event(self, ev=None):
        return self.subcode_goto('next')
    @_check_enable()
    def subcode_goto_previous_same_event(self, ev=None):
        return self.subcode_goto('prevsame')
    @_check_enable()
    def subcode_goto_next_same_event(self, ev=None):
        return self.subcode_goto('nextsame')

    def subcode_goto(self, w=None):
        """ Move cursor to another subcode. """
        text = self.text
        i = text.index('insert')
        goto_line, goto_col = sp(i)

        if w == 'prev':
            goto_line, goto_col = self.get_prev_subcode(i)
        elif w == 'next':
            goto_line, goto_col = self.get_next_subcode(i, end=False)

        elif w in ['nextsame', 'prevsame']:
            astart, astop, adepth = self.get_active_subcode(i)
            while True:
                if w == 'nextsame':
                    nline, ndepth = self.get_next_subcode(i, end=False)
                    test = (nline == astop + 1)

                elif w == 'prevsame':
                    nline, ndepth = self.get_prev_subcode(i+'-1c')
                    nstop = self.get_subcode_stop(jn(nline, ndepth))
                    test = (astart == nstop + 1) \
                            or i != jn(nline, ndepth)

                next_i = jn(nline, ndepth)
                if i == next_i: break   # don't loop forever
                i = next_i

                if ndepth == adepth and test:
                    goto_line, goto_col = nline, ndepth
                    break

        # make sure subcode is visible
        text.mark_set('insert', '%i.%i' % (goto_line, goto_col))
        top, bot = self.editwin.getwindowlines()
        if goto_line - 3 < top:
            text.yview(goto_line - 3)
        elif goto_line + 4 > bot:
            height = bot - top
            text.yview(goto_line - height + 4)

        return "break"


    def _get_depth_re(self, depth):
        """ Cache regular expression engines for subcode depths.
            Helper function for get_subcode_stop.
        """
        w = SubCode.whitespace_re
        if depth not in w:
            r = [r"((?<![^\n])( {%i,}[^ \n][^\n]*\n| *(#[^\n]*)?\n))" % depth]
            ac_re = any_re("DEPTH", r)
            w[depth] = re.compile(ac_re, re.S)
        return w[depth]


    def get_subcode_stop(self, subcode_start):
        """ Return the last line of the subcode. Used by get_active_subcode. """
        sline, sdepth = sp(subcode_start)
        if sdepth == 0:   # don't need to scan source to find end of depth=0 subcode
            while True:
                eline, depth = self.get_next_subcode(subcode_start, end=True)
                subcode_start = jn(eline, depth)
                if depth == 0:
                    break
            return eline - 1

        # determine the termination line due to another subcode
        while True:
            hardstop, depth = self.get_next_subcode(subcode_start, end=True)
            subcode_start = jn(hardstop, depth)
            if depth <= sdepth:
                break

        # determine the termination line due to shallower code indentation

        eline = sline   # accumulator for the end line
        grablines = 50  # number of lines to grab initially

        q = self._get_depth_re(sdepth)
        while True:
            lastb = 0   # for tracking continuity of matches
            head = '%i.0' % sline
            tail = '%i.0' % min((sline + grablines, hardstop))
            chars = self.text.get(head, tail)

            m = q.search(chars)
            span = 0  # count of lines satisfying depth >= sdepth
            while m:
                d = m.groupdict()
                if d['DEPTH']:
                    a,b = m.span('DEPTH')
                    if a == lastb:
                        span += 1
                    else:
                        break  # truncated by shallower code
                    lastb = b
                m = q.search(chars, m.end())

            eline += span
            if span != chars.count('\n'):
                break

            sline += grablines
            if sline > hardstop:
                eline = hardstop
                break

            grablines *= 4  # grab even more lines

        return eline - 1

    def get_active_subcode(self, i):
        """ Returns a tuple of the start line, end line, and subcode depth """
        lineno, col = sp(i)
        while True:
            sline, sdepth = self.get_prev_subcode(i+'+1c')
            eline = self.get_subcode_stop(jn(sline, sdepth))

            next_i = jn(sline-1, 0)
            if next_i == i: break
            i = next_i

            if eline >= lineno:
                break

        return sline, eline, sdepth


    def get_code(self, sline, eline, depth=0, header=True, uncomment=True):
        """ Returns the code to be executed """
        src = self.text.get('%i.0' % sline, '%i.0' % (eline+1))

        if uncomment:  # uncomment any #: comments at depth
            src = re.sub(r"(?<![^\n]) {%i,%i}#:" % (depth,depth),
                         ' '*depth, src)

        if depth:   # dedent indented code
            src = re.sub(r"(?<![^\n]) {%i,%i}" % (depth, depth), "", src)

        if header:
            src = '\n' * (sline - 1) + src  # to align errors to line number

        return src

    #########################################################################
    ### Highlighter Code
    def highlighter_init(self, ev=None):
        text = self.text
        # need to reorder tag priorities so highlighting works properly
        text.tag_config('ACTIVE', background=SUBCODE_HIGHLIGHT)
        low = ['ACTIVE', 'KEYWORD', 'STRING', 'hit', 'BUILTIN',
                       'DEFINITION', 'COMMENT', 'MAYBESUBCODE']
        for i in low:
            text.tag_lower(i)

        self.hl_id = None   # highlighter after id
        self.hl_AC = None   # cache for the active subcode bounds

    def _highlighter(func):
        def f(self, *args, **kwargs):
            if self.enable and self.highlighting:
                return func(self, *args, **kwargs)
            else:
                return
        return f

    @_highlighter
    def highlighter_callback(self, ev=None):
        c = self.editwin.color

        i = self.text.index('insert')
        hl_AC = self.get_active_subcode(i)
        sline, eline, depth = hl_AC

        if sline == 1:
            sline = 0  # catch highlighting of implicit subcode marker at beginning

        if hl_AC != self.hl_AC:
            if self.hl_AC is None:
                prev_sline, prev_eline, prev_depth = 0, 0, 9999
            else:
                prev_sline, prev_eline, prev_depth = self.hl_AC

            self.hl_AC = hl_AC  # save Active Code info for the next callback
            if prev_sline != sline or prev_depth != depth:
                # likely a different subcode
                self.text.tag_remove('ACTIVE', '1.0', END)
                self.text.tag_add("ACTIVE", '%i.%i' % (sline, depth),
                                        '%i.0' % (eline+1))
            else:
                # start and depth are same, endline is different. adjust
                if eline > prev_eline:
                    self.text.tag_add("ACTIVE", '%i.0' % (prev_eline),
                                        '%i.0' % (eline+1))
                else:
                    self.text.tag_remove('ACTIVE', '%i.0' % (eline+1),
                                         '%i.0' % (prev_eline+1))
        else:
            # same active subcode - make sure highlighting is present.
            r = self.text.tag_prevrange("ACTIVE", 'insert+1c')
            if not r:
                self.hl_AC = None  # invalidate cache
            else:
                sl, sc = sp(r[0])  # catch loss of highlighting at start of subcode
                if sc != 0:
                    self.hl_AC = None


        self.highlighter_schedule()

    def highlighter_schedule(self, cancel=False):
        if self.hl_id is not None:
            self.text.after_cancel(self.hl_id)

        if not cancel:
            self.hl_id = self.text.after(HIGHLIGHT_INTERVAL,
                                         self.highlighter_callback)
        else:
            self.hl_id = None

    @_highlighter
    def focus_in(self, ev=None):
        self.text.tag_config('ACTIVE', background=SUBCODE_HIGHLIGHT)
        self.highlighter_schedule()

    @_highlighter
    def focus_out(self, ev=None):
        self.text.tag_config('ACTIVE', background=SUBCODE_HIGHLIGHT_OUT)
        self.highlighter_schedule(cancel=True)


def any_re(groupname, re_list):
    return "(?P<%s>" % groupname + "|".join(re_list) + ")"


class SubcodeColorDelegator(ColorDelegator):
    """ Performs a two-pass highlighting of subcode markers, to work around Python's
        RE having a fixed-width lookbehind. Subcode markers should be preceeded
        by white space only, but this whitespace should not be highlighted.

        The first pass identifies possible subcodes using IDLE's original
        "recolorize_main". This pass matches the preceeding whitespace as well.

        The second pass colorizes properly indented subcode markers, while
        ignoring consecutive double-comment lines, which can be caused by
        "Comment Out Region".

    """

    # Require subcode markers be unlabeled or strictly labeled,
    # i.e. only one space between ## and the label or carriage return
    subcode = [r"(?<!#)(##)(( [^ \n]+[^\n]*)|[ ]*(?=\n))\n"]

    subcode_re = any_re("SUBCODE", subcode)
    # RE for multi-line double comments, like those produced by "Comment Out Region"
    #multi_re = r"(?P<MULTI>(?<![^\n])([ ]*)##(?! [^ \n])[^\n]*\n(\2##[^\n]*\n)+)"
    multi_re = r"(?P<MULTI>(?<![^\n])([ ]*)##( {2,}[^\n]*\n|[ ]*\n)(\2##[^\n]*?\n)*(\2##[^\n]*))"
    subcodeprog = re.compile(multi_re + "|" + subcode_re, re.S)

    maybe_indented = [r"(?<![^\n])[ ]*##[^\n]*\n"]
    maybe_indented_re = any_re("MAYBESUBCODE", maybe_indented)

    maybe = [r"(?<![^\n])##[^\n]*\n"]
    maybe_re = any_re("MAYBESUBCODE", maybe)

    """ add subcode highlighting to the color delegator """
    def __init__(self, subcode_enable=False, subcode_indented=False):
        ColorDelegator.__init__(self)

        self.set_enable(subcode_enable)
        self.set_indented(subcode_indented)



        self.subcodeprog = SubcodeColorDelegator.subcodeprog


    def config_colors(self):

        if COLOR_ADAPT:
            try:
                self.set_subcode_colors()
            except Exception as err:
                print('color_adapt', err)

        font=(idleConf.GetOption('main', 'EditorWindow', 'font'),
              idleConf.GetOption('main', 'EditorWindow', 'font-size'),
              'bold')


        self.tagdefs['SUBCODE'] = self.tagdefs['COMMENT'].copy()
        self.tagdefs['SUBCODE'].update({'background': SUBCODE_BACKGROUND,
                                'font':font,
                                })

        self.tagdefs['MAYBESUBCODE'] = self.tagdefs['COMMENT']

        ColorDelegator.config_colors(self)

        self.tag_raise('SUBCODE')
        self.tag_raise('sel')  # 2011-12-29 - bug fix for highlighting


    def toggle_colorize_event(self, event):
        """ Override the base class. Don't disable the colorizer,
            otherwise SubCode's will not be detected.
        """
        print('toggle_colorize_event')
        return "break"

    def set_enable(self, b=True):
        self.init_values = False
        self.subcode_enable = b

    def regenerate_re(self):
        rlist = []
        if self.subcode_indented:
            rlist.append(SubcodeColorDelegator.maybe_indented_re)
        else:
            rlist.append(SubcodeColorDelegator.maybe_re)

        rlist.append(make_pat())
        ret = re.compile('|'.join(rlist), re.S)
        self.prog = ret

    def set_indented(self, b=True):
        self.init_values = False
        self.subcode_indented = b
        self.regenerate_re()

    def recolorize_main(self):
        if not self.subcode_enable:
            return ColorDelegator.recolorize_main(self)
        else:
            return self.subcode_recolorize_main()

    def subcode_recolorize_main(self):

        # monkey patch update to avoid flickering of subcode markers
        _update = self.update
        try:
            self.update = lambda:None
            ColorDelegator.recolorize_main(self)
        finally:
            self.update = _update  # must restore update function

        item = self.tag_nextrange("TODO", '1.0')
        if item:
            self.update()
            return  # colorizer didn't finish labeling MAYBESUBCODE, abort

        # colorize the MAYBESUBCODE as SUBCODE if it is, else comment
        next = "1.0"
        while True:
            item = self.tag_nextrange("MAYBESUBCODE", next)
            if not item:
                break
            # remove MAYBESUBCODE and replace with COMMENT
            head, tail = item
            self.tag_remove("MAYBESUBCODE", head, tail)
            self.tag_add("COMMENT", head, tail)

            chars = self.get(head, tail)
            #print 'consider', repr(chars)

            # tag multiline comments then subcode markers
            m = self.subcodeprog.search(chars)

            while m:
                value = m.groupdict()['SUBCODE']
                if value:
                    a, b = m.span("SUBCODE")
                    start = head + "+%dc" % a
                    stop = head + "+%dc" % b
                    if not chars[:a].strip(): # fix subtle bug for ##  ## lines
                        self.tag_remove("COMMENT",start, stop)
                        self.tag_add("SUBCODE", start, stop)

                m = self.subcodeprog.search(chars, m.end())
            next = tail

        self.update()

    def set_subcode_colors(self):
        # This is a HACK to allow for sane coloring with other
        # color themes. Patches are welcome!
        from . import SubCode
        theme = idleConf.GetOption('main','Theme','name')
        normal_colors = idleConf.GetHighlight(theme, 'normal')
        background = normal_colors['background']

        def rgb_h2d(c):
            # Take a '#RRGGBB' and convert to integer tuple
            R = c[1:3]
            G = c[3:5]
            B = c[5:7]
            return tuple([int(x, 16) for x in (R, G, B)])

        def rgb_d2h(c):
            # (R, B, G) -> '#RRGGBB'
            c = [min((255, int(x))) for x in c]
            c = [max((0, int(x))) for x in c]
            return '#%02X%02X%02X' % tuple(c)

        def colorhack(rgb, target):
            # apply some DC offset and "gamma" correction
            R, G, B = map(float, rgb)
            mR, mG, mB = target
            m = lambda x, y: (x + y[0])**y[1] if x < 128 else (x - y[0]) ** (1/y[1])
            R = m(R, mR)
            G = m(G, mG)
            B = m(B, mB)
            return (R, G, B)

        def average(a, b):
            return [(x[0]+x[1])/2.0 for x in zip(a,b)]

        BACK = rgb_h2d(background)

        a = (10, 1.03)
        SubCode.SUBCODE_BACKGROUND = rgb_d2h(colorhack(BACK, (a,a,a)))

        a = (10, 1.019)
        b = (10, .98)
        c = colorhack(BACK, (a,b,a))
        HL = rgb_d2h(c)
        SubCode.SUBCODE_HIGHLIGHT = HL

        d = average(BACK, c)
        SubCode.SUBCODE_HIGHLIGHT_OUT = rgb_d2h(d)

        self.tag_config('ACTIVE', background=SUBCODE_HIGHLIGHT)
