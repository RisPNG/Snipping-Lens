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
##    EventLoop.py
##
##    Drive a GUI event loop within the subprocess from the IDLE event loop.
##    Allows for interactive GUI development.
##
##    Supports the following toolkits:
##        * Tkinter
##        * GTK
##        * Qt
##        * Qt4
##        * PySide
##        * wx
##
##    A callback function gets called periodically from the IDLE gui when
##    the shell is idle... (pun intended)
##
##
##    """

config_extension_def = """

[EventLoop]
enable=1
active=False
toolkit=TK

[EventLoop_cfgBindings]
eventloop-toggle=<Key-F7>

"""

INTERVAL = 100          # milliseconds
INSTALL_DELAY = 250     # milliseconds

from idlelib.configHandler import idleConf

import sys
if sys.version < '3':
    from Tkinter import *
else:
    from tkinter import *


import idlelib.PyShell as PyShell
import idlelib.ToolTip as ToolTip
import threading
import time

# subprocess initialization code
gui_init = r"""

def __IDLE_eventloop_set(kit='TK'):
    " Sets up a callback function for a GUI toolkit. See EventLoop.py."
    global __IDLE_eventloop, __IDLE_eventloop_counter
    import sys
    if not hasattr(sys, 'ps1'):
        sys.ps1 = '>>> '   # hack for matplotlib...
    guiptr = None

    if kit == 'CUSTOM':
        if '__IDLE_eventloop' not in globals() or hasattr(__IDLE_eventloop, 'default'):
            def __IDLE_eventloop():
                if __IDLE_eventloop.message:
                    print(__IDLE_eventloop.message)
                    __IDLE_eventloop.message = None
            msg = ['\n',
                   'You have chosen to use a custom callback function for the event loop.',
                   'Please define a callback function of the following form:',
                   '',
                   '    def __IDLE_eventloop():',
                   '        pass  # Your GUI callback code here',
                   '',
                   "(Press Enter if you don't have a >>> prompt.)\n"
                   ]

            __IDLE_eventloop.message = '\n'.join(msg)
            return

    elif kit == 'TK':
        if sys.version < '3':
            guiptr = sys.modules.get('Tkinter')
        else:
            guiptr = sys.modules.get('tkinter')

        if guiptr:
            tcl = guiptr.Tcl()
            def __IDLE_eventloop(guiptr=guiptr, tcl=tcl):
                tcl.eval('update')

    elif kit == 'GTK':
        guiptr = sys.modules.get('gtk')
        def __IDLE_eventloop(guiptr=guiptr):
            while guiptr.events_pending():
                guiptr.main_iteration()

    elif kit == 'QT4':
        guiptr = sys.modules.get('PyQt4.QtGui')
        def __IDLE_eventloop(guiptr=guiptr):
            guiptr.qApp.processEvents()

    elif kit == 'QT':
        guiptr = sys.modules.get('qt')
        def __IDLE_eventloop(guiptr=guiptr):
            guiptr.qApp.processEvents()

    elif kit == 'PYSIDE':
        guiptr = sys.modules.get('PySide.QtGui')
        def __IDLE_eventloop(guiptr=guiptr):
            guiptr.qApp.processEvents()

    elif kit == 'WX':
        guiptr = sys.modules.get('wx')
        def __IDLE_eventloop(guiptr=guiptr):
            guiptr.Yield()

    elif kit == 'FLTK':     # TODO
        pass

    else: # Well this is a problem. The "kit" argument is not valid.
        print("EventLoop.py: %r is not a supported toolkit." % kit)
        def __IDLE_eventloop():
            pass

    if guiptr is None:
        # The toolkit has not been imported yet.
        # Install a callback that will check periodically and
        # do a proper install.

        __IDLE_eventloop_counter = 0   # only check periodically if Toolkit is not imported
        def __IDLE_eventloop():
            global __IDLE_eventloop_counter
            __IDLE_eventloop_counter = (__IDLE_eventloop_counter + 1) % 25
            if __IDLE_eventloop_counter == 0:
                __IDLE_eventloop_set(kit=kit)

    if kit != 'CUSTOM' and '__IDLE_eventloop' in globals():
        __IDLE_eventloop.default = True

def __IDLE_eventloop_error(err):
    " For when the __IDLE_eventloop callback experiences an error. "
    global __IDLE_eventloop
    msg = [ '',
            'An error has occurred in the __IDLE_eventloop callback:',
            '',
            str(err),
            '',
            'The callback function has been reset to do nothing.',
            "(Press Enter if you don't have a >>> prompt.)",
            ]
    print('\n'.join(msg))
    def __IDLE_eventloop():  # avoid displaying errors repeatedly
        pass

"""

# subprocess callback code
gui_ping_src = r"""
try:
    __IDLE_eventloop()
except Exception as err:
    try:
        __IDLE_eventloop_error(err)
    except:
        pass
"""

GUI_PING_CODE = gui_ping_src

TOOLTIP_TEXT = 'Click to toggle Event Loop driver'

# Methods and state for threading
EV_ACTIVE = False
DO_PING = False         # Flag to allow for sending ping
INTERP = None           # pointer to Interpreter object
PING_RUNNING = False    # Flag for pinging thread

def ping_eventloop():
    global DO_PING, PING_RUNNING
    PING_RUNNING = True
    request = ("QUEUE", ("exec", "runcode", (GUI_PING_CODE,), {}))
    while EV_ACTIVE:
        if INTERP is None:
            time.sleep(0.050)
        elif INTERP.tkconsole.executing:
            # wait longer before trying again
            time.sleep(0.050)
        else:
            # By waiting for the idleEV extension to set the DO_PING flag,
            # the rpcclt.asyncqueue command will return. Otherwise, during
            # a shell restart, this thread will be blocked on the
            # asyncqueue command.
            if DO_PING:
                try:
                    # BUGFIX - 2011-11-30
                    # Using .asyncqueue caused a massive memory "leak" because
                    # responses were not cleared. Putting message with sequence 0
                    # into the RPC works and doesn't cause a leak.
                    #print('putting', request)
                    INTERP.rpcclt.putmessage((0, request))
                except:
                    pass
            DO_PING = False
            time.sleep(0.010)
    PING_RUNNING = False

# The IDLE EV Extension
class EventLoop(object):

    TOOLKITS = [('!Use Tkinter', '<<eventloop-tkinter>>', 'TK'),
                ('!Use GTK', '<<eventloop-gtk>>', 'GTK'),
                ('!Use Qt', '<<eventloop-qt>>', 'QT'),
                ('!Use Qt4', '<<eventloop-qt4>>', 'QT4'),
                ('!Use PySide', '<<eventloop-pyside>>', 'PYSIDE'),
                ('!Use wx', '<<eventloop-wx>>', 'WX'),
                #('!Use FLTK', '<<eventloop-fltk>>', 'FLTK'),  # TODO
                ('!Use Custom Callback', '<<eventloop-custom>>', 'CUSTOM'),
                ]

    # Build the menudefs entry
    _shell = [None,
             ('!Enable GUI Event Loop', '<<eventloop-toggle>>'),
             None]

    for _menu_item, _event, _kit_id in TOOLKITS:
        _shell.append((_menu_item, _event))
    _shell.append(None)

    menudefs = [('shell', _shell)]   # build menu entries


    shell_instance = None   # pointer to the PyShell instance

    def __init__(self, editwin):
        self.is_shell = False
        self.editwin = editwin
        if isinstance(editwin, PyShell.PyShell):
            self.editwin.top.after(1,lambda: self.init_pyshell())
        else:
            self.init_editor()

    def init_editor(self):
        # initialize in an Editor. Only do key binding.
        def eventloop_toggle_editor(ev=None):
            if EventLoop.shell_instance:
                EventLoop.shell_instance.eventloop_toggle()
        self.editwin.text.bind('<<eventloop-toggle>>', eventloop_toggle_editor)

    def init_pyshell(self):
        if not PyShell.use_subprocess:
            print('EventLoop.py only works with a subprocess.')
            return
        EventLoop.shell_instance = self    # set class variable - it is singleton anyways

        self.is_shell = True
        text = self.text = self.editwin.text
        text.bind('<<eventloop-toggle>>', self.eventloop_toggle)

        self.after_id = None
        self.delay_id = None

        self.install_socket = None
        self.active = False

        self.active = idleConf.GetOption("extensions", "EventLoop",
                              "active", type="bool", default=True)

        self.kit = idleConf.GetOption("extensions", "EventLoop",
                             "toolkit", type="raw", default="TK")

        if self.kit == 'CUSTOM':
            self.active = False  # avoid needless startup message

        self.init_status_bar()
        for menu, event, kit_id in EventLoop.TOOLKITS:
            text.bind(event, lambda ev, kit=kit_id: self.use_kit(kit))

        self.use_kit(self.kit, install=False)
        self.eventloop_enable(self.active)



    def init_status_bar(self):  # for PyShell instance
        """ Place a status box into the status bar. It is also a clickable toggle."""
        sb = self.editwin.status_bar
        sb.set_label('EventLoop', text="")
        L = sb.labels['EventLoop']
        L.bind('<Button-1>', self.eventloop_toggle)
        self.tooltip = ToolTip.ToolTip(L, TOOLTIP_TEXT)
        self.display_state()

    def display_state(self):
        """ Update the state of the extension. """
        sb = self.editwin.status_bar
        if self.active:
            s = 'ON'
        else:
            s = 'OFF'

        txt = 'GUI: %s (%s)' % (s, self.kit)
        sb.set_label('EventLoop', text=txt)

    def close(self):
        if self.is_shell:
            self.close_pyshell()
        self.editwin = None
        self.text = None


    def close_pyshell(self):
        global INTERP, DO_PING
        idleConf.SetOption("extensions", "EventLoop", "active",
                           '%s' % self.active)
        idleConf.SetOption("extensions", "EventLoop",
                        "toolkit", self.kit)
        idleConf.SaveUserCfgFiles()

        self.eventloop_enable(False)

        INTERP = None
        DO_PING = False


    def eventloop_enable(self, b=True):
        global EV_ACTIVE
        self.active = b
        self.editwin.setvar("<<eventloop-toggle>>", self.active)
        EV_ACTIVE = self.active

        if self.active:
            self.use_kit(self.kit)
        else:
            if self.after_id:
                self.text.after_cancel(self.after_id)
                self.after_id = None
            if self.delay_id:
                self.text.after_cancel(self.delay_id)
                self.delay_id = None

        self.display_state()

    def eventloop_toggle(self, event=None):
        # Tk callback to the <<eventloop-toggle>> event
        self.eventloop_enable(not self.active)
        return "break"

    def use_kit(self, kit=None, install=True):

        toolkits = EventLoop.TOOLKITS
        if kit not in [i[2] for i in toolkits]:
            print('Need to specify a valid kit. %s not valid' % kit)
            kit = 'TK'  # do default

        editwin = self.editwin
        for menu, event, kit_id in toolkits:
            if kit == kit_id:
                editwin.setvar(event, True)
            else:
                editwin.setvar(event, False)

        self.tooltip.text = TOOLTIP_TEXT + ' for %s' % kit

        if kit != self.kit:
            self.kit = kit
            self.install_socket = None  # invalidate cache
            install = True

        if install:
            self.delay_install()

        self.display_state()

    ### Code for handling installing and running the GUI Callbacks in the Shell

    def start_threading(self):
        global EV_ACTIVE
        EV_ACTIVE = True
        if not PING_RUNNING:
            t = threading.Thread(target=ping_eventloop)
            t.daemon = True
            t.start()
            self.do_update()
        else:
            raise Exception('Ping Thread still running when it should not be running')

    def stop_threading(self):
        global EV_ACTIVE
        EV_ACTIVE = False
        if self.after_id:
            self.text.after_cancel(self.after_id)
            self.after_id = None

    def delay_install(self):
        if self.delay_id:
            self.text.after_cancel(self.delay_id)
        self.delay_id = self.text.after(INSTALL_DELAY, self._do_install)

    def _do_install(self, count=200):
        global INTERP
        if not self.active:
            return
        if count == 0:
            self.eventloop_enable(False)
            return

        self.stop_threading()  # make sure PING loop is disabled while installing the event handler
        tryagain = True
        interp = self.editwin.interp
        if interp:
            if not interp.tkconsole.executing:
                if interp.rpcclt:
                    if not interp.debugger:
                        try:
                            cmd = '%s\n%s' % (gui_init,
                                              "__IDLE_eventloop_set(%r)" % self.kit)
                            interp.runcommand(cmd)
                            self.install_socket = interp.rpcclt.sock
                            self.compile_gui_ping()
                            tryagain = False
                            INTERP = interp
                            self.text.after(1, lambda: self.start_threading())
                        except Exception as err:
                            print(err)
                            pass

        if tryagain:
            self.text.after(INSTALL_DELAY, lambda: self._do_install())
        else:
            self.delay_id = None

    def compile_gui_ping(self):
        global GUI_PING_CODE
        GUI_PING_CODE = self.editwin.interp.compile(gui_ping_src, '', 'exec')

    def do_update(self, event=None):
        """ periodic callback to set flags for pinging eventloop """
        global DO_PING, INTERP
        if not self.active: return
        self.after_id = self.text.after(INTERVAL, self.do_update)
        interp = self.editwin.interp
        if interp:
            if interp.rpcclt and interp.rpcclt.sock is self.install_socket:
                # same subprocess
                if not interp.tkconsole.executing and interp.debugger is None \
                   and interp.rpcclt:
                    DO_PING = True
            else:
                # different subprocess
                self.stop_threading()
                if self.delay_id is None:
                    self.delay_install()
