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
##    SubCode Toolbar - provides a toolbar for SubCode.py
##
##    About:
##
##        [>] - list of subcode labels
##        [##] - insert a subcode marker
##
##        [-] 1.0 [+]  - add or subtract from number by cursor
##        [/] 1.1 [*]  - divide or multiply number by cursor
##
##        [RS] - Run SubCode
##        [RSP] - Run SubCode and Proceed
##        [RA] - Run All subcodes
##
##
##    """

config_extension_def = """

[SubCodeToolbar]
enable=1
enable_shell=0
enable_editor=1

visible=True

[SubCodeToolbar_cfgBindings]
subcode-toolbar=
subcode-toolbar-plus=<Control-Key-equal> <Control-Key-plus>
subcode-toolbar-minus=<Control-Key-minus> <Control-Shift-Key-minus>
"""

import re
from idlelib.configHandler import idleConf
from idlelib import macosxSupport

import sys
if sys.version < '3':
    from Tkinter import *
else:
    from tkinter import *

import idlelib.ToolTip as ToolTip
from . import SubCode

SUBCODE_STR = SubCode.SUBCODE_STR

class SubCodeToolbar(object):


    menudefs = [
               ('options' if not SubCode.SUBCODE_MENU else 'subcode',
                [
                ('!Show %s Toolbar' % SUBCODE_STR, '<<subcode-toolbar>>'),
                ]),
               ]

    def __init__(self, editwin):
        self.editwin = editwin
        self.text = editwin.text

        self.TB = None  # pointer to toolbar tkinter object

        self.visible = idleConf.GetOption("extensions", "SubCodeToolbar",
                             "visible", type="bool", default=True)

        self.setvars()

        self.text.bind('<<subcode-enable>>', self.subcode_enable_event, '+')
        self.text.bind('<<subcode-disable>>', self.subcode_disable_event, '+')
        #self.text.bind('<<subcode-toolbar-plus>>', self.subcode_plus_event, '+')
        #self.text.bind('<<subcode-toolbar-minus>>', self.subcode_minus_event, '+')
        sc = self.editwin.extensions.get('SubCode')

        if sc and sc.enable:
            self.subcode_enable_event()

    def close(self):
        idleConf.SetOption("extensions", "SubCodeToolbar",
                             "visible", '%s' % self.visible)
        idleConf.SaveUserCfgFiles()


    def subcode_enable_event(self, ev=None):
        if self.visible:
            self.toolbar_enable(True)

    def subcode_disable_event(self, ev=None):
        self.toolbar_enable(False)


    def subcode_toolbar_event(self, ev=None):
        self.visible = not self.visible
        self.toolbar_enable(self.visible)
        self.setvars()


    def setvars(self):
        try:
            self.editwin.setvar("<<subcode-toolbar>>", self.visible)
        except Exception as err:
            pass

    def toolbar_enable(self, b=True):
        sc = self.editwin.extensions.get('SubCode', None)
        if b:
            if sc and sc.enable:
                self._make_toolbar()
        else:
            self._destroy_toolbar()

    def _destroy_toolbar(self):
        self.TITLES = None
        if self.TB is not None:
            self.TB.destroy()
            self.TB = None


    def _make_toolbar(self):
        if self.TB is not None:
            return  # toolbar exists

        top = self.editwin.top

        f = Frame(top)
        widgets = self.editwin.top.pack_slaves()
        widgets = list(widgets) # list for Python 3 support
        f.pack(side='top', fill=X, before=widgets[0])  # make toolbar play nicely with CodeContext


        f.config(height=8)
        mvar = [StringVar(top), StringVar(top)]
        Separator = Label

        try:
            osx = (macosxSupport.runningAsOSXApp() or
                    sys.platform == 'darwin')
        except:
            osx = False

        toolbar = [(Button(f, command=lambda: self.toolbar('titles'), text='>',
                           width=1 if not osx else 2),
                    None, 'Show %s Labels' % SUBCODE_STR),

                   (Button(f, command=lambda: self.toolbar('ins'), text='##',
                           width=2 if not osx else 3),
                    None, 'Insert %s Marker' % SUBCODE_STR),

                   (Separator(f), {'fill':Y, 'pady':0, 'padx':4}, None),

                   (Button(f, command=lambda: self.toolbar('minus'), text='-',
                           width=1 if not osx else 2),
                    None, 'Subtract from number by cursor then run %s' % SUBCODE_STR.lower()),

                   (Entry(f, width=6, justify='center', textvar=mvar[0]), {'fill':Y},
                    '+ - value'),

                   (Button(f, command=lambda: self.toolbar('plus'), text='+',
                           width=1 if not osx else 2),
                    None, 'Add to number by cursor then run %s' % SUBCODE_STR.lower()),

                   (Separator(f), {'fill':Y, 'pady':0, 'padx':4}, None),

                   (Button(f, command=lambda: self.toolbar('div'), text='/',
                           width=1 if not osx else 2),
                    None, 'Divide number by cursor then run %s' % SUBCODE_STR.lower()),

                   (Entry(f, width=6, justify='center',
                          textvar=mvar[1]), {'fill':Y},
                    '* / value'),

                   (Button(f, command=lambda: self.toolbar('mult'), text='*',
                           width=1 if not osx else 2),
                    None, 'Multiply number by cursor then run %s' % SUBCODE_STR.lower()),

                   (Separator(f), {'fill':Y, 'pady':0, 'padx':4}, None),

                   (Button(f, command=lambda: self.toolbar('run_subcode'), text='R%s' %
                           SUBCODE_STR[0].upper(),
                           width=2 if not osx else 4),
                    None, 'Run %s' % SUBCODE_STR),

                   (Button(f, command=lambda: self.toolbar('run_subcode_proceed'), text='R%sP' %
                           SUBCODE_STR[0].upper(),
                           width=3 if not osx else 4),
                    None, 'Run %s and Proceed' % SUBCODE_STR),

                   (Button(f, command=lambda: self.toolbar('run_all'), text='RA',
                           width=2 if not osx else 4),
                    None, 'Run All %ss' % SUBCODE_STR),

                   (Separator(f), {'fill':Y, 'pady':0, 'padx':4}, None),

                    ]

        mvar[0].set('1.0')
        mvar[1].set('1.1')
        self.mvar = mvar

        for i, cfg, tooltip  in toolbar:
            if cfg is None:
                cfg = {}
            try:
                i.configure(pady=0, padx=7)
                i.configure(wraplength=0)
                i.configure(borderwidth=1)
            except:  # catch ALL THE ERRORS
                #print 'error',i, cfg, tooltip
                pass
            i.pack(side='left', **cfg)
            if tooltip is not None:
                ToolTip.ToolTip(i, ' %s ' % tooltip)

        self.TB = f
        self.TITLES = toolbar[0][0]  # pointer to the titles button


    def toolbar(self, cmd):
        text = self.editwin.text
        text.focus()
        if cmd in ['plus', 'minus', 'mult', 'div']:
            self.process_number(cmd)
        if cmd == 'run_subcode':
            text.event_generate("<<subcode-run>>")
        if cmd == 'run_subcode_proceed':
            text.event_generate("<<subcode-run-proceed>>")
        if cmd == 'run_all':
            text.event_generate("<<subcode-run-all>>")
        if cmd == 'ins':
            text.event_generate("<<subcode-insert-marker>>")
        if cmd == 'titles':
            self.titles()


    def titles(self):
        # make a popup menu of all subcodes in file
        text = self.editwin.text
        c = text.tag_ranges('SUBCODE')

        L = []
        if len(c) == 0 or c[0].string != '1.0':
            L.append(('1.0', '## beginning of file'))

        for tr in c[::2]:  # only grab start of ranges
            line, col = map(float, tr.string.split('.'))
            L.append((tr.string, text.get(line, line+1)))

        B = self.TITLES

        rmenu = Menu(B, tearoff=0)
        for line, label in L:
            def jump(lineno=line):
                self.text.mark_set('insert', lineno)
                self.text.event_generate('<<set-line-and-column>>')
                self.text.yview(lineno)

            #m1 = label[0:min([50,len(label)])].strip()[2:]
            m1 = label.strip()[2:]
            lineno, col = map(int, line.split('.'))

            m2 = '%s[%6s] %-50s' % (' '*col, line, m1)
            rmenu.add_command(label=m2, command=jump)

        x = B.winfo_rootx()
        y = B.winfo_rooty() + B.winfo_height()
        rmenu.tk_popup(x,y)

    def shell_busy(self):
        shell = self.editwin.flist.open_shell()
        self.editwin.text.event_generate('<<subcode-focus-editor>>')
        try:
            if shell.interp.tkconsole.executing:
                return True # shell is busy
        except:
            return True   # shell is not in a valid state

        return False

    def process_number(self, cmd):

        text = self.editwin.text
        undo = self.editwin.undo

        lineno, col = map(float, text.index(INSERT).split('.'))
        txt = text.get(lineno, lineno + 1)
        # get the number
        pattern = r"([-]?[\d]+[\.]?[\d]*|\.[\d]+)"
        p = re.compile(pattern)
        h = p.finditer(txt)
        j = [i for i in h if i.start()<=col and i.end()>=col]
        if j:
            if j[0].group() == '':
                return
            s,e,t = j[0].start(), j[0].end(), j[0].group()
        else:
            return

        # at this point, a number has been found
        if self.shell_busy():
            return

        a = float(self.mvar[0].get())
        m = float(self.mvar[1].get())

        if cmd == 'plus':
            r = float(t) + a
        elif cmd == 'minus':
            r = float(t) - a
        elif cmd == 'mult':
            r = float(t) * m
        elif cmd == 'div':
            r = float(t) / m

        if cmd in ['plus', 'minus']:
            if '.' not in t:              # keep integers as integers
                r = int(round(r))

        new_t = str(r)

        undo.undo_block_start()
        text.delete('%i.%i' % (lineno, s), '%i.%i' % (lineno, e))
        text.insert('%i.%i' % (lineno, s), new_t)
        text.mark_set(INSERT, '%i.%i' % (lineno, s + len(new_t)))
        undo.undo_block_stop()

        text.event_generate("<<subcode-run>>")


    def subcode_toolbar_plus_event(self, ev=None):
        self.toolbar('plus')
    def subcode_toolbar_minus_event(self, ev=None):
        self.toolbar('minus')

