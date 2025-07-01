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
##    LineNumbers Extension
##
##    Provides line numbers to the left of the source code.
##
##    The width of the line numbers adapts. Limit of 99,999 lines (for proper display).
##
##    """

config_extension_def = """

[LineNumbers]
enable=1
enable_shell=0
visible=True

[LineNumbers_cfgBindings]
linenumbers-show=

"""

import sys
if sys.version < '3':
    from Tkinter import END, Text, LEFT, Y, NONE, RIGHT, NORMAL, DISABLED, Label, TOP, Frame, X
else:
    from tkinter import END, Text, LEFT, Y, NONE, RIGHT, NORMAL, DISABLED, Label, TOP, Frame, X

from idlelib.configHandler import idleConf
from idlelib.Delegator import Delegator
from idlelib.Percolator import Percolator


FONTUPDATEINTERVAL = 1000   # milliseconds

_AFTER_UNDO = True          # Flag to have the LineNumberDelegator inserted after the undo delegator

jn = lambda x,y: '%i.%i' % (x,y)        # join integers to text coordinates
sp = lambda x: map(int, x.split('.'))   # convert tkinter Text coordinate to a line and column tuple


def dbprint(func):  # A decorator for debugging
    def f(*args, **kwargs):
        print(func, args, kwargs)
        return func(*args, **kwargs)
    return f

class LineNumbers(object):

    menudefs = [('options', [('!Show Line Numbers', '<<linenumbers-show>>')])]

    def __init__(self, editwin):
        self.editwin = editwin
        self.text = self.editwin.text
        self.textfont = None
        self.width = 2
        self.after_id = None

        self.create_linenumbers()

        e = idleConf.GetOption("extensions", "LineNumbers",
                               "visible", type="bool", default=True)
        self.set_visible(e)

        self.code_context_fix()

    def close(self):
        if self.after_id:
            self.text.after_cancel(self.after_id)
        self.visible = False

    def adjust_font(self):
        try:
            # taken from CodeContext.py
            newtextfont = self.editwin.text["font"]
            if self.textln and newtextfont != self.textfont:
                self.textfont = newtextfont
                self.textln["font"] = self.textfont
                if self._cc_text:
                    self._cc_text["font"] = self.textfont
            self.update_numbers()
        except Exception as err:
            import traceback; traceback.print_exc()

    def font_timer(self):
        if not self.visible:
            return

        self.adjust_font()

        if self.after_id:
            self.text.after_cancel(self.after_id)
        self.after_id = self.text.after(FONTUPDATEINTERVAL, self.font_timer)
        if not _AFTER_UNDO:
            self.update_numbers()  # fixes a bug due to this percolator being ahead of undo percolator.

    def set_visible(self, b=True):
        self.visible = b

        if self.visible:
            self.text.after(1, self.font_timer)  # avoid a start-up bug
            self.show()
            # use .after to avoid a start-up error caused by update_idletasks in update_numbers
            self.text.after(1, self.update_numbers)
        else:
            self.hide()

        idleConf.SetOption("extensions", "LineNumbers",
                           "visible", '%s' % self.visible)

        self.editwin.setvar("<<linenumbers-show>>", self.visible)

    def linenumbers_show_event(self, ev=None):
        self.set_visible(not self.visible)
        self._code_context_toggle()

    def create_linenumbers(self):
        """ Create the widget for displaying line numbers. """
        editwin = self.editwin
        text = self.text
        text_frame = editwin.text_frame
        self.textln = textln = Text(text_frame, width=self.width,
                                    height=1, wrap=NONE)

        # adjust font
        textln.config(font=(idleConf.GetOption('main', 'EditorWindow', 'font'),
                          idleConf.GetOption('main', 'EditorWindow', 'font-size')))

        textln.bind("<FocusIn>", self.focus_in_event)
        textln.bind('<Button-1>', self.button_ignore)
        textln.bind('<Button-2>', self.button_ignore)
        textln.bind('<Button-3>', self.button_ignore)
        textln.bind('<B1-Motion>', self.button_ignore)
        textln.bind('<B2-Motion>', self.button_ignore)
        textln.bind('<B3-Motion>', self.button_ignore)

        textln.bind("<Button-4>", self.button4)
        textln.bind("<Button-5>", self.button5)

        textln.tag_config('LINE', justify=RIGHT)
        textln.insert(END, '1')
        textln.tag_add('LINE', '1.0', END)

        # start the line numbers
        self.per = per = Percolator(textln)
        self.line_delegator = LineDelegator()
        per.insertfilter(self.line_delegator)
        textln._insert = self.line_delegator.delegate.insert
        textln._delete = self.line_delegator.delegate.delete


        lines = LineNumberDelegator(self)
        if _AFTER_UNDO:
            # Percolator.py's .insertfilter should have an "after=" argument
            lines.setdelegate(editwin.undo.delegate)
            editwin.undo.setdelegate(lines)
        else:
            editwin.per.insertfilter(lines)

        editwin.vbar['command'] = self.vbar_split
        editwin.text['yscrollcommand'] = self.yscroll_split

    def button4(self, ev=None):
        self.text.event_generate("<Button-4>")
        return "break"

    def button5(self, ev=None):
        self.text.event_generate("<Button-5>")
        return "break"

    def button_ignore(self, ev=None):
        return "break"

    def show(self):
        self.textln.pack(side=LEFT, fill=Y, before=self.editwin.text)

    def hide(self):
        self.textln.pack_forget()

    def focus_in_event(self, event=None):
        self.editwin.text.focus_set()
        self.textln.tag_remove('sel', '1.0', 'end')
        #self.editwin.text.event_generate("<<goto-line>>")

    def generate_goto_event(self, event=None):
        self.editwin.text.event_generate("<<goto-line>>")
        return "break"

    def vbar_split(self, *args, **kwargs):
        """ split scrollbar commands to the editor text widget and the line number widget """
        self.textln.yview(*args, **kwargs)
        self.text.yview(*args, **kwargs)

    def yscroll_split(self, *args, **kwargs):
        """ send yview commands to both the scroll bar and line number listing """
        #import traceback; traceback.print_stack()
        self.editwin.vbar.set(*args)
        self.textln.yview_moveto(args[0])

    def update_numbers(self, add=None, remove=None):
        if not self.visible: return

        textln = self.textln
        text = self.editwin.text


        endline1, col1 = sp(text.index(END))
        endline2, col2 = sp(textln.index(END))


        if endline1 < endline2:
            # delete numbers
            textln._delete('%i.0' % endline1, END)
        elif endline1 > endline2:
            # add numbers
            q = range(endline2, endline1)
            r = map(lambda x: '%i' % x, q)
            s = '\n' + '\n'.join(r)
            textln._insert(END, s)
            textln.tag_add('LINE', '1.0', END)

        # adjust width of textln, if needed. (counts from 1, not zero)
        if endline1 <= 100:
            width = 2
        elif endline1 <= 1000:
            width = 3
        elif endline1 <= 10000:
            width = 4
        else:
            width = 5 # more than 9999 lines in IDLE? Really?

        # XXX: If your code requires width>5, i.e > 100,000 lines of code,
        # you probably should not be using IDLE.

        if width > self.width:  # 2011-12-18 - only grow, not shrink
            self.width = width
            textln.configure(width=width)
            if self._cc_text:  # adjust CC width
                self._cc_text.configure(width=width)

        self.textln.update_idletasks()
        a = self.text.yview()
        self.textln.yview_moveto(a[0])

    def code_context_fix(self):
        self._cc_text = None
        self._cc_frame = None
        def f():
            self.text.bind('<<toggle-code-context>>', self._code_context_toggle, '+')
            self._code_context_toggle()
        self.text.after(10, f)

    def _code_context_toggle(self, event=None):
        cc = self.editwin.extensions.get('CodeContext', None)
        if cc is None:
            return

        if not self.visible:
            if self._cc_frame:
                L = cc.label
                L.pack_forget()
                self._cc_frame.destroy()
                L.pack(side=TOP, fill=X, expand=False,
                       before=self.editwin.text_frame)
            return


        editwin = self.editwin
        text = self.text
        text_frame = editwin.text_frame

        # repack the Label in a frame
        if cc.label:
            cc.label.pack_forget()
            F = Frame(self.editwin.top)
            F.lower() # fix Z-order
            t = Text(F, width=self.width, height=1,
                     takefocus=0)
            t.bind("<FocusIn>", lambda x: self.text.focus())
            t["font"] = self.textln.cget('font')
            t.pack(side=LEFT, fill=Y)
            cc.label.pack(in_=F, fill=X, expand=False)

            F.pack(side=TOP, before=text_frame, fill=X, expand=False)
            self._cc_frame = F
            self._cc_text = t
        else:
            if self._cc_frame:
                self._cc_frame.destroy()
                self._cc_frame = None
                self._cc_text = None




class LineNumberDelegator(Delegator):
    # for editwin.text
    def __init__(self, line_number_instance):
        Delegator.__init__(self)
        self.ext = line_number_instance

    def insert(self, index, chars, tags=None):
        self.delegate.insert(index, chars, tags)
        if '\n' in chars:
            self.ext.update_numbers()#add=chars.count('\n'))
    def delete(self, index1, index2=None):
        t = self.get(index1, index2)
        self.delegate.delete(index1, index2)
        if '\n' in t:
            self.ext.update_numbers()#remove=t.count('\n'))


class LineDelegator(Delegator):
    # for textln
    def insert(self, *args, **kargs):
        pass

    def delete(self, *args, **kargs):
        pass
