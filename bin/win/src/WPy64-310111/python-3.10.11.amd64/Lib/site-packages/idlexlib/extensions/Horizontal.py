# IDLEX EXTENSION
##    """
##    Copyright(C) 2011 The Board of Trustees of the University of Illinois.
##    All rights reserved.
##    Developed by:   Roger D. Serwy
##                    University of Illinois
##    License: See LICENSE.txt
##    """


#
# Horizontal Scroll Bar Extension
# Provides a horizontal scroll bar on the Editor window.
#
# This extension is meant to be an introduction
# to writing IDLE extensions.
#


# config_extension_def is for IdleX to configure this extension.
# This would normally be placed in config-extensions.def
# in the idlelib directory.
config_extension_def = """
[Horizontal]
enable=1
enable_editor=1
enable_shell=0
visible=True
"""


# Python 2/3 compatibility
import sys
if sys.version < '3':
    import Tkinter as tk
else:
    import tkinter as tk


# get the IDLE configuration handler
from idlelib.configHandler import idleConf

class Horizontal:   # must be the same name as the file for EditorWindow.py
                    # to load it.

    menudefs = [
        ('windows', [
               ('!Show Horizontal Scrollbar', '<<horizontal-show>>'),
       ]),]

    def __init__(self, editwin):
        self.editwin = editwin      # reference to the editor window
        self.text = text = self.editwin.text
        self.text.bind("<<horizontal-show>>", self.show_toggle)

        # See __init__ in EditorWindow.py to understand
        # the widget layout
        self.xbar = xbar = tk.Scrollbar(editwin.text_frame,
                         orient=tk.HORIZONTAL)  # create the scroll bar

        xbar['command'] = text.xview    # connect it to the text widget

        text['xscrollcommand'] = xbar.set  # connext text widget to scroll bar


        self.visible =  idleConf.GetOption("extensions", "Horizontal",
                           "visible", type='bool', default=True)

        if self.visible:
            self._show_bar()

    def show_toggle(self, ev=None):
        self.visible = not self.visible
        if self.visible:
            self._show_bar()
        else:
            self._hide_bar()

        # save the option
        idleConf.SetOption("extensions", "Horizontal",
                           "visible", '%s' % self.visible)

    def _show_bar(self):
        # pack the bar so it is visible
        widgets = self.editwin.text_frame.pack_slaves()
        widgets = list(widgets) # list for Python 3 support
        self.xbar.pack(side=tk.BOTTOM,
                       fill=tk.BOTH,
                       expand=0,
                       before=widgets[0]) # pack before everything
        self.editwin.setvar("<<horizontal-show>>", True)

    def _hide_bar(self):
        # forget the packing so it is not visible
        self.xbar.pack_forget()
        self.editwin.setvar("<<horizontal-show>>", False)
