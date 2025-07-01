# IDLEX EXTENSION
from __future__ import print_function
##    """
##    Copyright(C) 2011-2012 The Board of Trustees of the University of Illinois.
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
##    """

config_extension_def = """
[idlexManager]
enable=1
missing=
"""

version = '???'  # updated from idlexMain.py

import sys

import os
import re
import imp
import __main__

if sys.version < '3':
    from StringIO import StringIO
    from Tkinter import *
    import tkFileDialog
    import tkMessageBox
else:
    from io import StringIO
    from tkinter import *
    import tkinter.filedialog as tkFileDialog
    import tkinter.messagebox as tkMessageBox
    StandardError = Exception

from idlelib.configHandler import idleConf, IdleConfParser
import idlelib.textView as textView
import webbrowser


def update_globals():  # for calling from idlex.py
    global IDLEX_URL
    global UPDATE_URL
    global DEV_EMAIL

    IDLEX_URL = 'http://idlex.sourceforge.net/'
    UPDATE_URL = '%supdate.html?version=%s' % (IDLEX_URL, version)
    DEV_EMAIL = 'serwy@illinois.edu'

update_globals()

PATCH_MENU = False   # Patch "Configure Extensions..." into options menu


class idlexManager(object):
    if not PATCH_MENU:
        menudefs = [
          ('options',
                    [('Configure Extensions...', '<<idlex-configure>>'),
                    None,
                    ]),
            ]
    else:
        menudefs = []

    menudefs.append( ('help',
               [None,
                ('About Idle_X', '<<idlex-about>>'),
                ('Check for IdleX Updates', '<<idlex-update>>')]))

    def __init__(self, editwin):
        self.editwin = editwin
        editwin.text.bind('<<idlex-configure>>',
                          self.idlex_configure_event)
        editwin.text.bind('<<idlex-about>>',
                          self.idlex_about_event)
        editwin.text.bind('<<idlex-update>>',
                          self.idlex_update_event)


        if PATCH_MENU:
            self.patch_menu()

    def close(self):
        idleConf.SaveUserCfgFiles()

    def idlex_update_event(self, ev=None):
        idlexUpdate(self.editwin.text)

    def idlex_configure_event(self, ev=None):
        idlexConfig(self.editwin.top)

    def idlex_about_event(self, ev=None):
        a = idlexAbout(self.editwin.top)

    def patch_menu(self):
        # patch "Configure Extensions" into the Options menu
        e = self.editwin
        f = e.menudict['options']
        text = e.text
        eventname = '<<idlex-configure>>'
        def command(text=text, eventname=eventname):
            text.event_generate(eventname)
        f.insert_command(2, label="Configure Extensions...", command=command)

class idlexAbout(Toplevel):
    # some code borrowed from aboutDialog.py, covered by the PSF License.
    def __init__(self, parent):
        Toplevel.__init__(self, parent)
        title = 'About IdleX'# (version %s)' % __version__
        self.configure(borderwidth=5)
        self.geometry("+%d+%d" % (parent.winfo_rootx()+30,
                                  parent.winfo_rooty()+30))
        self.CreateWidgets()
        self.resizable(height=FALSE, width=FALSE)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.parent = parent
        self.buttonOk.focus_set()
        self.bind('<Return>',self.close)
        self.bind('<Escape>',self.close)
        self.wait_window()

    def CreateWidgets(self):
        frameMain = Frame(self, borderwidth=2, relief=SUNKEN)
        frameButtons = Frame(self)
        frameButtons.pack(side=BOTTOM, fill=X)
        frameMain.pack(side=TOP, expand=TRUE, fill=BOTH)

        self.buttonUpdate = Button(frameButtons, text='Check for Updates',
                                 command=self.check_updates)
        self.buttonUpdate.pack(padx=5, pady=5, side=LEFT)

        self.buttonOk = Button(frameButtons, text='Close',
                               command=self.close)
        self.buttonOk.pack(padx=5, pady=5, side=RIGHT)



        t = Text(frameMain)
        t.configure(width=40, height=15,
                    bg="#6091b0",
                    fg="#FFFFFF",
                    padx=10,
                    pady=10,
                    wrap=WORD,
                    borderwidth=0)
        t.pack(expand=TRUE, fill=BOTH, side=LEFT)

        vbar = Scrollbar(frameMain, name='vbar')
        vbar.pack(side=RIGHT, fill=Y)

        vbar['command'] = t.yview
        t['yscrollcommand'] = vbar.set

        t.tag_configure('CAP',
                        font=('courier', 24, 'bold'))
        t.tag_configure('MINICAP',
                        font=('courier', 20, 'bold'))
        t.tag_configure('TITLE',
                        background="#b37900",
                        foreground="#ffcf61",
                        relief=RIDGE,
                        borderwidth=5,
                        justify=LEFT,
                        )
        # make IdleX title
        t.insert('insert', ' I', 'CAP TITLE')
        t.insert('insert', 'DLE', 'MINICAP TITLE')
        t.insert('insert', 'X ', 'CAP TITLE')
        t.insert('insert', '\n'*1)

        # make message
        msg = ['IDLE Extensions for Python',
               'version %s' % version,
               '',
               'email:  %s' % DEV_EMAIL,
               'www:    %s' % IDLEX_URL,
               '',
               'Copyright(C) 2011-2012 The Board of Trustees of the University of Illinois.',
               'All rights reserved.',
               '',
               'See LICENSE.txt for more details',
               '',
               'IdleX includes some third-party extensions that are covered by their respective licenses and copyrights as found in the "license" directory.',
               '',
               'SearchBar.py and Squeezer.py',
               'Copyright (c) 2011 Tal Einat',
               'All rights reserved.',
               '',
               'IDLE2HTML.py',
               'Copyright (c) 2001-2010 Python Software Foundation; All Rights Reserved.',
               '\n'*4,

            ]
        t.insert('insert', '\n'.join(msg))

        t.config(state=DISABLED)

    def close(self, event=None):
        self.destroy()

    def check_updates(self, ev=None):
        idlexUpdate(self.parent)
        return "break"


class idlexUpdate:
    def __init__(self, text):
        if sys.platform[:3] == 'win':
            try:
                os.startfile(UPDATE_URL)
            except WindowsError as why:
                tkMessageBox.showerror(title='Unable to load IdleX update page.',
                    message=str(why), parent=text)
        else:
            webbrowser.open(UPDATE_URL)


class idlexConfig(Toplevel):
    def __init__(self, parent):
        Toplevel.__init__(self, parent)
        self.restart = False        # Flag for displaying restart dialog
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.gui = {}
        self.parent = parent
        self.build_gui()
        self.populate_gui()

    def close(self, ev=None):
        if self.restart:
            self.recommend_restart()
        self.destroy()


    def build_gui(self):
        top = self
        top.title('IdleX Extension Manager')
        top.configure(borderwidth=5)
        parent = self.parent
        top.geometry("=+%d+%d" % (parent.winfo_rootx()+20,
                        parent.winfo_rooty()+30))

        mainFrame = LabelFrame(top, borderwidth=0)
        mainFrame.pack(side=TOP, fill=BOTH, expand=True, padx=3, pady=3)

        ### gui for enable/disable extension
        f2 = LabelFrame(mainFrame, borderwidth=2, relief=GROOVE,
                        text='Enable/Disable Extensions:')

        lbframe = Frame(f2, borderwidth=0)
        scrollbar = Scrollbar(lbframe, orient=VERTICAL)
        lb = Listbox(lbframe, yscrollcommand=scrollbar.set)
        scrollbar.config(command=lb.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        lb.pack(side=TOP, fill=BOTH, expand=True)
        lbframe.pack(side=TOP, fill=BOTH, padx=6, pady=6, expand=True)
        lb.bind("<Double-Button-1>", self.toggle)

        tog_B = Button(f2, text='Enable/Disable', command=self.toggle)
        tog_B.pack(side=LEFT, padx=6, pady=3)

        clear_B = Button(f2, text='Use Extension Defaults',
                         command=self.clear_custom)
        clear_B.pack(side=LEFT, padx=6, pady=3)


        f2.pack(side=TOP, fill=BOTH, expand=True)

        self.gui['extension_list'] = lb

        ### dialog
        close_B = Button(mainFrame, text='Close',
                         command=self.close)
        close_B.pack(side=RIGHT)

    def populate_gui(self):
        IDLE_DEFAULT_EXT = extensionManager.IDLE_EXTENSIONS
        ext_list = idleConf.GetExtensions(active_only=False)
        ext_list.sort(key=str.lower)
        if 'idlexManager' in ext_list:
            ext_list.remove('idlexManager')  # idlex enabled by default.

        lb = self.gui['extension_list']
        lb.delete(0, END)  # reset the list

        for item in ext_list:
            ext_found = True
            try:
                extensionManager.find_extension(item)
            except ImportError:
                ext_found = False

            en = idleConf.GetOption('extensions', item, 'enable', type='int')
            info = ''
            if item in IDLE_DEFAULT_EXT:
                info += ' (built-in) '

            if not ext_found:
                if item not in IDLE_DEFAULT_EXT:
                    if sys.modules.get('idlexlib.extensions.%s' % item) is not None:
                        info += ' (RESTART TO UNLOAD) '
                    else:
                        info +=  ' (NOT FOUND IN PATH) '

            if en:
                enstr = '1'
            else:
                enstr = '0'

            text = ' [%s]  %s  %s' % (enstr, item, info)
            lb.insert(END, text)

        self.extensions = ext_list

    def get_sel(self):
        LB = self.gui['extension_list']
        sel = LB.curselection()
        if not sel:
            return None
        else:
            return int(sel[0])

    def toggle(self, ev=None):
        """ Toggle the selected extension's enable status """
        sel = self.get_sel()
        if sel is None: return

        item = self.extensions[sel]
        en = not idleConf.GetOption('extensions', item, 'enable',
                                    type='bool', default=True)
        en = int(en)

        idleConf.SetOption('extensions', item, 'enable', '%s' % en)
        idleConf.SaveUserCfgFiles()
        self.repopulate_list()

        self.restart = True

    def repopulate_list(self):
        sel = self.get_sel()
        # remember the list box settings
        lb = self.gui['extension_list']
        y = lb.yview()

        self.populate_gui()

        if sel > lb.index(END):
            sel = lb.index(END)

        # restore the list box settings
        lb.yview_moveto(y[0])
        lb.activate(sel)
        lb.select_set(sel)
        lb.focus_set()

    def clear_custom(self):
        """ Delete the configuration for an extension from the
            user configuration found in .idlerc/config-extensions.cfg """
        sel = self.get_sel()
        if sel is None: return

        ext_name = self.extensions[sel]
        idleConf.userCfg['extensions'].remove_section(ext_name)
        idleConf.userCfg['extensions'].remove_section(ext_name + '_cfgBindings')
        # reload this extension config

        extensionManager.reload_cfg(ext_name)
        self.repopulate_list()


    def recommend_restart(self):
        msg = """The extension configuration has changed. Changes
                 will take effect on newly opened editors and shells.
                 A restart is recommended, but not required.
                 """

        msg = re.sub(r"[\s]{2,}", " ", msg)
        tkMessageBox.showinfo(parent=self,
            title="IDLE Restart Recommended",
            message=msg)

################################################################


##
##def _about():
##    root = Tk()
##    idlexAbout(root)
##    root.mainloop()
##
##if __name__ == '__main__':
##    _about()




