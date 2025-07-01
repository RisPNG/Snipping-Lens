# IDLEX EXTENSION
##    """
##    Copyright(C) 2012 The Board of Trustees of the University of Illinois.
##    All rights reserved.
##    Developed by:   Roger D. Serwy
##                    University of Illinois
##    License: See LICENSE.txt
##    """


config_extension_def = """
[ZoomFont]
enable=1
enable_editor=1
enable_shell=1

[ZoomFont_cfgBindings]
zoomfont-default=
zoomfont-increase=
zoomfont-decrease=
"""


# Python 2/3 compatibility
import sys
if sys.version < '3':
    import Tkinter as tk
    import tkFont
else:
    import tkinter as tk
    import tkinter.font as tkFont


# get the IDLE configuration handler
from idlelib.configHandler import idleConf

from pprint import pprint

def printit(func):
    def f(*args, **kw):
        return func(*args, **kw)
    return f



jn = lambda x,y: '%i.%i' % (x,y)        # join integers to text coordinates
sp = lambda x: list(map(int, x.split('.')))   # convert tkinter Text coordinate to a line and column tuple

class ZoomFont:   # must be the same name as the file for EditorWindow.py
                    # to load it.

    menudefs = [
        ('options', [
                None,
               ('Increase Font Size', '<<zoomfont-increase>>'),
               ('Default Font Size', '<<zoomfont-default>>'),
               ('Decrease Font Size', '<<zoomfont-decrease>>'),
       ]),]

    def __init__(self, editwin):
        self.editwin = editwin      # reference to the editor window
        self.text = text = self.editwin.text
        self.text.bind('<Control-4>', self.zoomfont_increase_event)
        self.text.bind('<Control-5>', self.zoomfont_decrease_event)
        self.text.bind('<Control-KeyRelease>', self.control_release, '+')
        self.offset = 0
        self._ratio = 0
        self._zero_pause = False
        self._pause_id = None



    def create_font(self, F, offset):

        # Python3 tkinter does not translate the TCL list properly
        if isinstance(F, str):
            F = self.text.tk.split(F)

        fn = F[0]
        if isinstance(fn, str):
            fontname = fn
        else:
            fontname = ' '.join(fn)
        fontsize = int(F[1])
        fontweight = F[2]

        if fontsize + offset < 1:
            offset = fontsize - 1

        F = (str(fontname),
             str(fontsize+offset),
             fontweight)
        return F, offset

    accum = 0
    hit_timer = None
    def accumulate(func):
        def f(self, offset=0):        
            if self.hit_timer is None:
                self.hit_timer = self.text.after(200, self._consolidate)
                return func(self, offset)
            else:
                if not self._zero_pause:
                    self.accum += offset
                return 0
        return f

    def _consolidate(self):
        self.hit_timer = None
        a = self.accum 
        if a > 3:
            a = 3
        if a < -3:
            a = -3
        if a != 0:
            o = self.offset
            if o < 0 and o+a >= 0:
                a = -o
                self.pause_at_default()
            elif o > 0 and o+a <= 0:
                a = -o
                self.pause_at_default()
            offset = self.set_font(a)
            self.offset += offset
            self.accum = 0

    @accumulate
    def set_font(self, offset=0):
        text = self.text
        font = text.configure('font')
        F = font[-1]
        if F:
            F, actual_offset = self.create_font(F, offset)
            offset = actual_offset
            self.text.configure(font=F)

        for tag in text.tag_names():
            c = text.tag_configure(tag)
            font = c.get('font', None)
            F = font[-1]
            if F:
                F, actual_offset = self.create_font(F, offset)
                if offset != actual_offset:
                    print('A tag has a font size that is smaller than the text widget font size. %s' % tag)
                text.tag_configure(tag, font=F)

        # This is a hack to work with LineNumbers
        # font resizing. Ideally, something should broadcast a configuration
        # change so that everything else can respond appropriately.
        L = self.editwin.extensions.get('LineNumbers', None)
        if L:
            L.adjust_font()

        return offset

    def store_cursor(self, event):
        x, y = event.x, event.y
        text = self.text
        line, col = sp(text.index('@%d,%d' % (x,y)))
        top, bot = self.editwin.getwindowlines()
        self._store = (line, top, bot)

    def restore_cursor(self):
        line, top, bot = self._store
        new_top, new_bot = self.editwin.getwindowlines()
        new_h = max([new_bot - new_top - 1, 1])

        h = max([bot - top, 1])

        ratio = (line - top) / (1.0 * h)
        top2 = int(line - new_h * ratio)
        top2 = max([top2, 0])

        self.text.yview(jn(top2, 0))


    def cursor(func):
        # Decorator function for handling yview
        def f(self, event):
            if self._zero_pause:
                self.pause_at_default()
                return "break"
            self.store_cursor(event)
            ret = func(self, event)
            self.restore_cursor()
            return ret
        return f

    @cursor
    def zoomfont_increase_event(self, event=None):
        offset = self.set_font(1)
        self.offset += offset
        return "break"

    @cursor
    def zoomfont_decrease_event(self, event=None):
        offset = self.set_font(-1)
        self.offset += offset
        return "break"

    @cursor
    def zoomfont_default_event(self, event=None):
        self.set_font(-self.offset)
        self.offset = 0
        return "break"

    def control_release(self, event=None):
        self._zero_pause = False

    def pause_at_default(self, event=None):
        self._zero_pause = True
        if self._pause_id:
            self.text.after_cancel(self._pause_id)

        def unpause():
            self._zero_pause = False

        self._pause_id = self.text.after(250, unpause)
