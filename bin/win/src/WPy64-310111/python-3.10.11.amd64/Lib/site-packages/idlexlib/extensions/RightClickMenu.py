# IDLEX EXTENSION
##    """
##    Copyright(C) 2012 The Board of Trustees of the University of Illinois.
##    All rights reserved.
##    Developed by:   Roger D. Serwy
##                    University of Illinois
##    License: See LICENSE.txt
##    """


config_extension_def = """
[RightClickMenu]
enable=1
enable_editor=1
enable_shell=1
visible=True
"""


# Python 2/3 compatibility
import sys
if sys.version < '3':
    import Tkinter as tk
else:
    import tkinter as tk

from pprint import pprint

# get the IDLE configuration handler
from idlelib.configHandler import idleConf
from idlelib import macosxSupport
from idlelib.PyShell import PyShell


# A right-click menu has been added. See http://bugs.python.org/issue1207589
# from 2012-11-01. As a result, this extension is no longer necessary.


class RightClickMenu:   # must be the same name as the file for EditorWindow.py
                    # to load it.


    def __init__(self, editwin):
        self.editwin = editwin
        self.text = editwin.text
        self.is_shell = isinstance(editwin, PyShell)

        m = editwin.rmenu_specs
        if len(m) > 0:
            if len(m[0]) == 3:
                # RightClickMenu.py no longer needed. See issue1207589
                return

        self.rmenu_specs = [
             ('Cut', '<<cut>>'),
             ('Copy', '<<copy>>'),
             ('Paste', '<<paste>>'),
             None,
             ('Select All', '<<select-all>>'),
             ]

        editwin.text.after(1, self.delay)

    def delay(self):
        e = self.editwin
        m = e.rmenu_specs
##        try:
##            # This functionality in OutputWindow.py
##            # requires the cursor to leave the input area in the shell.
##            # IDLE should not do that.
##            m.remove(('Go to file/line', '<<goto-file-line>>'))
##
##        except:
##            pass

        text = self.text
        if macosxSupport.runningAsOSXApp():
            # Some OS X systems have only one mouse button,
            # so use control-click for pulldown menus there.
            #  (Note, AquaTk defines <2> as the right button if
            #   present and the Tk Text widget already binds <2>.)
            text.bind("<Control-Button-1>",self.right_menu_event)
        else:
            # Elsewhere, use right-click for pulldown menus.
            text.bind("<3>",self.right_menu_event)


        bmenu = [None]  # breakpoint options
        for i in m:
            if 'breakpoint' in i[0].lower():
                bmenu.append(i)
            else:
                self.rmenu_specs.append(i)

        if len(bmenu) > 1:
            self.rmenu_specs.extend(bmenu)


        self.make_rmenu()

    def make_rmenu(self):
        rmenu = tk.Menu(self.text, tearoff=0)
        for entry in self.rmenu_specs:
            if not entry:
                rmenu.add_separator()
            else:
                label, eventname = entry
                def command(text=self.text, eventname=eventname):
                    text.event_generate(eventname)
                rmenu.add_command(label=label, command=command)

        self.editwin.rmenu = rmenu

    def right_menu_event(self, event):

        sel_first = self.text.index('sel.first')
        if not sel_first:
            self.text.mark_set("insert", "@%d,%d" % (event.x, event.y))

        e = self.editwin
        if not e.rmenu:
            e.make_rmenu()
        rmenu = e.rmenu
        iswin = sys.platform[:3] == 'win'
        if iswin:
            e.text.config(cursor="arrow")
        rmenu.tk_popup(event.x_root, event.y_root)
        if iswin:
            e.text.config(cursor="ibeam")

