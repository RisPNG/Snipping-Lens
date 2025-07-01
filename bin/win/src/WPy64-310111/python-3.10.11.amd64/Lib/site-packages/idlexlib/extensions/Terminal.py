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
##    Terminal Mode Extension - makes PyShell behave more like a terminal
##
##    This extension makes PyShell behave more like a terminal.
##    The cursor is confined to the input area. Up and down arrow keys
##    the navigate command history.
##
##    Selected text in the Shell Window will not be copied to the
##    input area when pressing enter.
##
##    Part of Issue2704
##
##    """

config_extension_def = """

[Terminal]
enable=1
enable_shell=1
enable_editor=0
terminal=True

[Terminal_cfgBindings]
terminal-toggle=

"""

import sys

if sys.version < '3':
    from Tkinter import INSERT, END, SEL_FIRST, SEL_LAST, SEL
else:
    from tkinter import INSERT, END, SEL_FIRST, SEL_LAST, SEL

from idlelib.configHandler import idleConf

class Terminal:

    menudefs = [
        ('options', [
                ('!Terminal Mode', '<<terminal-toggle>>'),
       ]),]


    def __init__(self, editwin):
        self.editwin = editwin
        self.text = self.editwin.text

        self.enabled = idleConf.GetOption("extensions", "Terminal",
                                          "terminal", type="bool", default=True)
        self.editwin.setvar("<<terminal-toggle>>", not not self.enabled)

        # this extension is loaded from EditorWindow.py, but before
        # PyShell.py makes its changes. Will use tk .after to make
        # changes

        self.last_insert = 'end-1c'

        if self.enabled:
            self.text.after(10, self.delay_init)

    def close(self):
        self.editwin = None
        self.text = None

    def delay_init(self):
        if hasattr(self.editwin, 'history'):
            self.terminal_mode_init()
            return
        self.text.after(100, self.delay_init)

    def terminal_toggle_event(self, event=None):
        self.enabled = not self.enabled
        self.editwin.setvar("<<terminal-toggle>>", not not self.enabled)

        if self.enabled == False:
            self.terminal_mode_exit()
        else:
            self.terminal_mode_init()

        idleConf.SetOption("extensions", "Terminal", "terminal", '%s' % self.enabled)


    def terminal_mode_init(self, event=None):
        # redefine some key bindings
        self.enabled = True

        text = self.editwin.text

        # up/down keys
        text.bind("<<term-key-up-callback>>", self.key_up_callback)
        text.bind("<<term-key-down-callback>>", self.key_down_callback)
        text.event_add("<<term-key-up-callback>>", "<Key-Up>")
        text.event_add("<<term-key-down-callback>>", "<Key-Down>")

        # page up/down keys
        text.bind("<<term-key-pgup-callback>>", self.key_pgup_callback, '+')
        text.bind("<<term-key-pgdown-callback>>", self.key_pgdown_callback, '+')
        text.event_add("<<term-key-pgup-callback>>", "<Key-Prior>")
        text.event_add("<<term-key-pgdown-callback>>", "<Key-Next>")

        # home
        text.bind("<<term-home-callback>>", self.home_callback, '+')
        text.event_add("<<term-home-callback>>", "<Key-Home>")

        # keep the cursor in the input area
        text.bind("<<key-in-input>>", self.key_in_input)
        text.event_add("<<key-in-input>>", "<Key-Left>")
        text.bind("<<mouse-press>>", self.mouse_press)
        text.event_add("<<mouse-press>>", "<ButtonPress>")
        text.bind("<<mouse-release>>", self.mouse_release)
        text.event_add("<<mouse-release>>", "<ButtonRelease>")
        

        # make sure cursor is in input
        self.key_in_input(event)

        # override the enter-recall functionality
        text.bind('<Return>', self.enter_callback)

    def enter_callback(self, ev=None):
        if self.enabled:
            self.text.tag_remove('sel', '1.0', 'end')
        return self.editwin.enter_callback(ev)

    def terminal_mode_exit(self, event=None):
        self.enabled = False
        text = self.editwin.text
        text.unbind("<<term-key-up-callback>>")
        text.unbind("<<term-key-down-callback>>")
        text.unbind("<<key-in-input>>")
        text.unbind("<<mouse-in-input>>")

    def home_callback(self, event):
        text = self.text
        if self.text.compare("insert", "<", "iomark"):
            self.text.mark_set("insert", "iomark")
            return "break"
        if self.text.compare("iomark", "==", "insert"):
            return "break"
        return

    def mouse_press(self, event=None):
        text = self.text
        self.last_insert = text.index('insert')
        if text.compare('insert', '<=', 'iomark'):
            self.last_insert = text.index('end-1c')
        
    def mouse_release(self, event=None):
        if self.enabled == False: return
        # a mouse click on the window
        text = self.text
        if text.compare('insert', '<=', 'iomark'):
            text.mark_set('insert', self.last_insert)

    def key_in_input(self, event=None):
        if self.enabled == False: return
        # some key stroke
        if self.text.compare('insert', '<=', 'iomark'):
            self.text.mark_set('insert', 'iomark')
            return "break"

    def key_pgup_callback(self, event):
        text = self.text
        text.yview_scroll(-1, 'pages')
        return "break"

    def key_pgdown_callback(self, event):
        text = self.text
        text.yview_scroll(1, 'pages')
        return "break"

    def history_ismember(self):
        """ if the current input is in the history, return true """
        s = self.editwin.text.get('iomark', 'end-1c')
        return (s in self.editwin.history.history)

    def key_up_callback(self, event):
        if self.enabled == False: return
        if self.editwin.executing:
            return "break"

        s = self.text.get('iomark', 'end-1c')

        if '\n' not in s:
            # single line input
            if self.text.compare('insert', '==', 'end-1c'):
                self.editwin.history.history_prev(event)
                return "break"
            else:
                self.text.mark_set('insert', 'end-1c')
                return "break"
        else:
            # multiline input
            if self.text.compare('insert', '==', 'end-1c'):
                if self.history_ismember():
                    self.editwin.history.history_prev(event)
                    return "break"

            elif self.text.compare('insert', '<=', 'iomark'):
                # don't leave the input area
                self.text.mark_set('insert', 'iomark')
                return "break"
            elif self.text.compare('insert-1l', '<=', 'iomark'):
                self.text.mark_set('insert', 'iomark')
                return "break"
                
            


    def key_down_callback(self, event):
        if self.enabled == False: return

        if self.editwin.executing:
            return "break"


        s = self.text.get('iomark', 'end-1c')

        if '\n' not in s:
            # single line input
            if self.text.compare('insert', '==', 'end-1c'):
                self.editwin.history.history_next(event)
                return "break"
            else:
                self.text.mark_set('insert', 'end-1c')
                return "break"

        else:
            # multiline input
            if self.text.compare('insert', '<', 'end-1c') and \
               self.text.compare('insert lineend', '==', 'end-1c'):
                self.text.mark_set('insert', 'end-1c')
                return "break"

            if self.history_ismember():
                if self.text.compare('insert', '==', 'end-1c'):
                    self.editwin.history.history_next(event)
                    return "break"
                elif self.text.compare('insert lineend', '==', 'end-1c'):
                    return "break"
