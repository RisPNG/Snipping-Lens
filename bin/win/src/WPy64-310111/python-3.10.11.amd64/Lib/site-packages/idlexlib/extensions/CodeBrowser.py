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
##    Code Browser Extension
##
##    About:
##
##        Provides a panel for browsing class and def of a file.
##        A button in the status bar toggles it as well.
##
##
##    """

config_extension_def = """

[CodeBrowser]
enable=1
enable_shell=0
[CodeBrowser_cfgBindings]
toggle-classdefbrowser=<Key-F8>
toggle-keywordbrowser=

"""

import sys

import sys
if sys.version < '3':
    from Tkinter import *
else:
    from tkinter import *


from idlelib.configHandler import idleConf
from idlelib.Delegator import Delegator
from idlelib.Percolator import Percolator
from idlelib.ColorDelegator import ColorDelegator
from idlelib.ToolTip import ToolTip
import re


FONTUPDATEINTERVAL = 1000   # milliseconds
CODECHECKINTERVAL = 1000

sp = lambda x: list(map(int, x.split('.')))   # convert tkinter Text coordinate to a line and column tuple
jn = lambda x,y: '%i.%i' % (x,y)        # join integers to text coordinates

# TODO - provide multiline def strings


TEXTOFFSET = 1
class CodeBrowser:

    menudefs = [
        ('edit', [None,
               ('Toggle Code _Browser', '<<toggle-classdefbrowser>>'),
       ]),]

    def __init__(self, editwin):
        self.editwin = editwin
        self.text = self.editwin.text
        self.text.bind('<<toggle-classdefbrowser>>', self.toggle_classdef)
        self.text.bind('<<toggle-keywordbrowser>>', self.toggle_keyword)
        #self.text.bind('<Button-1>', self.button_click, '+')
        self.browser_text = []
        self.init_status_bar()
        self.hidden = True
        self.after_id = None

    def close(self):
        if self.after_id is not None:
            self.text.after_cancel(self.after_id)

    def init_status_bar(self):
        sb = self.editwin.status_bar
        sb.set_label('ClassDefBrowser', text="Code Browser")
        L = sb.labels['ClassDefBrowser']
        L.bind('<Button-1>', self.toggle_classdef)
        L.bind('<Button-3>', self.toggle_keyword)
        ToolTip(L, "Click to Show Classes and Definitions in buffer")

    def font_timer_event(self):
        if self.hidden:
            return
        # taken from CodeContext.py
        newtextfont = self.editwin.text["font"]
        if self.textln and newtextfont != self.textfont:
            self.textfont = newtextfont
            self.textln["font"] = self.textfont
        self.after_id = self.text.after(FONTUPDATEINTERVAL,
                                        self.font_timer_event)


    def toggle_classdef(self, ev=None):
        tag_filter = {'KEYWORD': ['def', 'class']}
        self.text.after(1, lambda: self.toggle(tag_filter))
        return "break"

    def toggle_keyword(self, ev=None):
        tag_filter = {'KEYWORD': ['def', 'class'],
               'COMMENT': True}
        #self.toggle(tag_filter)
        self.text.after(1, lambda: self.toggle(tag_filter))

    def toggle(self, tag_filter=None):
        if self.hidden:
            self.show(tag_filter)
        else:
            self.hide()


    def button_click(self, ev=None):
        print('button_click')
        # TODO - goto defintion on Ctrl+Click


    def show(self, tag_filter=None):

        if self.hidden == False:
            self.hide()
            return

        self.hidden = False

        # add a text widget, left of code text widget
        self.text_frame = text_frame = Frame(self.editwin.text_frame)
        self.vbar = vbar = Scrollbar(text_frame, name='vbar')
        vbar.pack(side=RIGHT, fill=Y)

        theme = idleConf.GetOption('main','Theme','name')
        normal_colors = idleConf.GetHighlight(theme, 'normal')
        text_options = {
                'padx': 5,
                'wrap': 'none',
                'cursor': 'arrow',
                'wrap': 'none',
                'foreground':normal_colors['foreground'],
                'background':normal_colors['background'],
                }

        self.textln = textln = Text(text_frame, **text_options)
        textln.pack(side='left',fill=BOTH, expand=YES)
        vbar['command'] = textln.yview
        textln['yscrollcommand'] = vbar.set

        # adjust font

        textln.config(font=(idleConf.GetOption('main', 'EditorWindow', 'font'),
                          idleConf.GetOption('main', 'EditorWindow', 'font-size')))



        textln.bind("<ButtonRelease>", self.focus_in_event)
        textln.bind("<Return>", self.enter_callback)
        textln.bind("<Escape>", self.escape_callback)
        textln.bind('<FocusOut>', self.focus_out, '+')

        # pass through keybindings for classdefbrowser
        keydefs = idleConf.GetExtensionBindings('CodeBrowser')
        for event, keylist in list(keydefs.items()):
            for k in keylist:
                def passthru(event, evName=event, text=self.text):
                    text.event_generate(evName)
                try:
                    textln.bind(k, passthru)
                except TclError as err:
                    print(err)
                    pass



        # start the line numbers
        self.per = per = Percolator(textln)
        self.color = ColorDelegator()

        self.per.insertfilter(self.color)

        self.line_delegator = LineDelegator()
        per.insertfilter(self.line_delegator)
        textln._insert = self.line_delegator.delegate.insert
        textln._delete = self.line_delegator.delegate.delete

        self.update_display(tag_filter)
        self.textfont = ""
        self.font_timer_event()

        self.nearest()


        text_frame.place(x=0, rely=1, relheight=1, relwidth=1, anchor=SW)
        text_frame.lift()


    def nearest(self):
        """ Enter ClassDefBrowser """
        # scroll textln to the nearest keyword found in text
        text = self.text
        textln = self.textln

        text_insert, text_col = sp(text.index(INSERT))

        text_end, col = sp(text.index(END))
        text_end -= 1
        text_top = (text.yview()[0] * text_end)
        text_bot = (text.yview()[1] * text_end)

        if text_top <= text_insert <= text_bot:
            pass
        else:
            text_insert = round((text_bot + text_top) / 2.0)
            for i in reversed(self.taglines):
                if i[0] <= text_insert:
                    text_insert = i[0]
                    break

        n = 0
        for n, i in enumerate(self.taglines):
            if i[0] > text_insert:
                target_line = n
                break
        else:
            target_line = n + 1


        textln.tag_add("NEAREST", '%i.0' % target_line, '%i.0' % (target_line+1))
        theme = idleConf.GetOption('main','Theme','name')
        hilite = idleConf.GetHighlight(theme, "hilite")
        textln.tag_configure("NEAREST", **hilite)
        textln.tag_raise('NEAREST')


        # place cursor at beginning of line text
        tline = min(target_line-1, len(self.taglines)-1)
        if self.taglines:
            origline, txt = self.taglines[tline]
            text_col = txt.find(txt.strip())
            textln.mark_set(INSERT, '%i.%i' % (target_line, text_col))


        offset = text_insert - round(text_top) - 1
        textln.yview(target_line - offset)

        textln.focus_set()

    def focus_out(self, ev=None):
        self.hide()


    def hide(self, event=None):
        if self.color:
            self.per.removefilter(self.color)
        self.text_frame.destroy()
        self.browser_text = None
        self.hidden = True
        self.text.focus_set()


    def enter_callback(self, ev=None):
        self.focus_in_event()


    def escape_callback(self, ev=None):
        self.hide()


    def focus_in_event(self, event=None):
        """ Leaves ClassDefBrowser, returns to source code."""
        if self.hidden:
            return

        # don't leave on scroll wheel events
        if event and event.state != 256: # FIXME
            return

        t = self.textln
        line, col = list(map(int, t.index(INSERT).split('.')))

        ind = line - TEXTOFFSET
        if 0 <= ind < len(self.taglines):
            L = self.taglines[ind][0]

            self.text.mark_set(INSERT, '%i.%i' % (L, col))
            self.editwin.set_line_and_column()

            line_end, col_end = sp(self.textln.index(END))

            d = self.textln.yview()[0] * line_end
            offset = L - line + round(d//1) + 1

            text_end, col_end = sp(self.text.index(END))
            self.text.yview(offset)


        self.hide()

    def nextrange(self, taglist, marker):
        text = self.text

        L = []
        for tag in taglist:
            n = text.tag_nextrange(tag, marker)
            if n:
                L.append((sp(n[0]), sp(n[1]), tag))

        if L:
            # find nearest range
            L.sort()
            line, col, tag = L[0]

            return (jn(*line), jn(*col)), tag


        else:
            return None, None


    def update_display(self, tag_filter=None):
        if self.hidden:
            return

        if tag_filter is None:
            tag_filter = {'KEYWORD': ['def', 'class'],
                           'COMMENT': True}

        text = self.text
        marker = "1.0"
        taglines = []
        lastline = 0
        lasttag = None
        while True:
            c, tag = self.nextrange(list(tag_filter.keys()), marker)

            if not c:
                break

            line, col = sp(c[0])

            if line == lastline:
                #if tag == lasttag:
                marker = c[1]
                continue

            lastline = line
            lasttag == tag

            tagtxt = text.get(c[0], c[1])

            filt = tag_filter[tag]
            if filt == True or tagtxt in filt:
                txt = text.get('%i.0' % line, '%i.0 lineend' % (line))
                taglines.append((line, txt))
            marker = c[1]


        textln = self.textln
        VIEW = textln.yview()

        text = self.editwin.text

        code_items = []

        for n, i in enumerate(taglines):
            line, t = i
            code_items.append('%4i  %s' % i)

        code_items.extend(['']*5)
        code_text = '\n'.join(code_items)

        if not code_text.strip():
            code_text = '\nCode Browser found no classes or definitions.\nPress Escape to return to editing.'

        if self.browser_text != code_text:  # check if I need to update the display, avoid flickering
            textln._delete(1.0, END)
            textln._insert(END, code_text)
            self.color.recolorize_main()
            self.browser_text = code_text
            self.taglines = taglines

        self.nearest()


class LineDelegator(Delegator):

    def insert(self, *args, **kargs):
        pass

    def delete(self, *args, **kargs):
        pass
