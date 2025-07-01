# IDLEX EXTENSION
##    """
##    Squeezer - using this extension will make long texts become a small button.
##
##    Copyright (c) 2011 Tal Einat
##    All rights reserved.
##
##    Developed by:           Tal Einat
##
##    Permission is hereby granted, free of charge, to any person obtaining a
##    copy of this software and associated documentation files (the "Software"),
##    to deal with the Software without restriction, including without limitation
##    the rights to use, copy, modify, merge, publish, distribute, sublicense,
##    and/or sell copies of the Software, and to permit persons to whom the
##    Software is furnished to do so, subject to the following conditions:
##
##        Redistributions of source code must retain the above copyright notice,
##        this list of conditions and the following disclaimers.
##
##        Redistributions in binary form must reproduce the above copyright notice,
##        this list of conditions and the following disclaimers in the documentation
##        and/or other materials provided with the distribution.
##
##        Neither the name of Tal Einat, nor the names of its contributors may be
##        used to endorse or promote products derived from this Software without
##        specific prior written permission. 
##
##    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
##    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
##    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
##    IN NO EVENT SHALL THE CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR
##    ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
##    TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
##    OR THE USE OR OTHER DEALINGS WITH THE SOFTWARE. 
##
##
##    Original Author: Noam Raphael
##    Maintained by:   Tal Einat
##
##    Modified by Roger D. Serwy to work with idleX and Python 3.
##    Some minor tweaks to the code were made. 
##
##    """

config_extension_def = """
[Squeezer]
enable=1
enable_shell=1
enable_editor=0
max-num-of-lines=150
preview-command-posix=(xterm -e less %(fn)s; rm -f %(fn)s) &
preview-command-win=notepad %(fn)s
preview-command-mac=
[Squeezer_cfgBindings]
squeeze-last-output=<Control-Key-equal>
expand-last-squeezed=<Control-Key-plus> <Control-Shift-Key-equal> <Control-Shift-Key-plus>
preview-last-squeezed=<Control-Key-minus>
"""

import re
from idlelib.PyShell import PyShell
from idlelib.configHandler import idleConf

import sys

if sys.version < '3':
    import Tkinter
    import tkFont
else:
    import tkinter as Tkinter
    import tkinter.font as tkFont
    xrange = range

import os


# define IDLE-infrastructure specific functions

def _get_base_text(editwin):
    "Return the base Text widget of an editwin, which can be changed before "\
    "the iomark."
    return editwin.per.bottom


# define a function to count the number of lines in a given string
_TABWIDTH = 8
_LINEWIDTH = 80
_tab_newline_re = re.compile(r"[\t\n]")
_tab_table_cache = {}

def _countlines(s, linewidth=_LINEWIDTH, tabwidth=_TABWIDTH):
    if (tabwidth, linewidth) not in _tab_table_cache:
        _tab_table_cache[(tabwidth, linewidth)] = \
            [ncols+tabwidth-(ncols%tabwidth) for ncols in xrange(linewidth)]
    tab_table = _tab_table_cache[(tabwidth, linewidth)]

    pos = 0
    linecount = 1
    current_column = 0

    for m in _tab_newline_re.finditer(s):
        # process the normal chars up to tab or newline
        numchars = m.start() - pos
        if numchars > 0: # must special-case, otherwise divmod(-1, linewidth)
            # If the length was exactly linewidth, divmod would give
            # (1,0), even though a new line hadn't yet been started.
            # Therefore subtract 1 before doing divmod, and later add
            # 1 to the column to compensate.
            lines, column = divmod(current_column + numchars - 1, linewidth)
            linecount += lines
            current_column = column + 1
            pos += numchars

        # deal with tab or newline
        if s[pos] == '\n':
            linecount += 1
            current_column = 0
        else:
            assert s[pos] == '\t'
            current_column = tab_table[current_column]

        pos += 1 # after the tab or newline

    # process remaining chars (no more tabs or newlines)
    numchars = len(s) - pos
    if numchars > 0: # must special-case, otherwise divmod(-1, linewidth)
        linecount += (current_column + numchars - 1) // linewidth
    return linecount


# define the extension's classes

class ExpandingButton(Tkinter.Button):

    color_pat = re.compile('\x01?\x1b\[(.*?)m\x02?')
    
    def __init__(self, s, tags, numoflines, squeezer):
        self.s = self.strip_ansi_colors(s)
        self.tags = tags
        self.squeezer = squeezer
        self.editwin = editwin = squeezer.editwin
        self.text = text = editwin.text
        
        caption = "Squeezed text (about %d lines).\n"\
                  "Double-click to expand, middle-click to copy" % numoflines
        if squeezer._PREVIEW_COMMAND:
            caption += ", right-click to preview."
        else:
            caption += "."
        Tkinter.Button.__init__(self, text,
                                text=caption,
                                background="#FFFFC0",
                                activebackground="#FFFFE0",
                                justify='left',
                                font=self.editwin.text["font"])
        self.bind("<Double-Button-1>", self.expand)
        self.bind("<Button-2>", self.copy)
        if squeezer._PREVIEW_COMMAND:
            self.bind("<Button-3>", self.preview)
        self.selection_handle(lambda offset,length: s[int(offset):int(offset)+int(length)])

        self.bind("<Button-4>", lambda x: self.text.event_generate('<Button-4>'))
        self.bind("<Button-5>", lambda x: self.text.event_generate('<Button-5>'))

    def strip_ansi_colors(self, s):  # For IPython compatibility
        return self.color_pat.sub("", s)
    
    def expand(self, event):
        # We must use the original insert and delete methods of the Text widget,
        # to be able to change text before the iomark.
        basetext = _get_base_text(self.editwin)
        basetext.insert(self.text.index(self), self.s, self.tags)
        basetext.delete(self)
        self.squeezer.expandingbuttons.remove(self)
        basetext.see('insert')
        
    def copy(self, event):
        self.clipboard_clear()
        self.clipboard_append(self.s, type='STRING')
        self.selection_own()

    def preview(self, event):
        from tempfile import mktemp
        fn = mktemp("longidletext")
        f = open(fn, "w")
        f.write(self.s)
        f.close()
        os.system(self.squeezer._PREVIEW_COMMAND % {"fn":fn})
            

class Squeezer:

    menudefs = [
        ('edit', [
            None,   # Separator
            ("Expand last squeezed text", "<<expand-last-squeezed>>"),
        ]),
        #('options', [('!Enable Squeezer', '<<squeezer-enable>>')]),
    ]
    #if _PREVIEW_COMMAND:
    if True:
        menudefs[0][1].append(("Preview last squeezed text",
                               "<<preview-last-squeezed>>"))

        
    def __init__(self, editwin):

        self._MAX_NUM_OF_LINES = idleConf.GetOption("extensions", "Squeezer",
                                           "max-num-of-lines", type="int",
                                           default=30)

        self._PREVIEW_COMMAND = idleConf.GetOption(
            "extensions", "Squeezer",
            "preview-command-"+{"nt":"win"}.get(os.name, os.name),
            
        default="", raw=True)
        self.editwin = editwin
        self.text = text = editwin.text
        self.expandingbuttons = []
        if isinstance(editwin, PyShell):
            # If we get a PyShell instance, replace its write method with a
            # wrapper, which inserts an ExpandingButton instead of a long text.
            def mywrite(s, tags=(), write=editwin.write):
                if tags != "stdout":
                    return write(s, tags)
                else:
                    numoflines = self.count_lines(s)
                    if numoflines < self._MAX_NUM_OF_LINES:
                        return write(s, tags)
                    else:
                        expandingbutton = ExpandingButton(s, tags, numoflines,
                                                          self)
                        text.mark_gravity("iomark", Tkinter.RIGHT)
                        text.window_create("iomark",window=expandingbutton,
                                           padx=2, pady=5)
                        text.see("iomark")
                        text.update()
                        text.mark_gravity("iomark", Tkinter.LEFT)
                        self.expandingbuttons.append(expandingbutton)
            editwin.write = mywrite

        #text.bind('<<squeezer-enable>>', self.squeezer_enable_event)

    def squeezer_enable_event(self, event=None):
        
        # TODO - configure dialog        
        pass

    def count_lines(self, s):
        "Calculate number of lines in given text.\n\n" \
        "Before calculation, the tab width and line length of the text are" \
        "fetched, so that up-to-date values are used."
        # Tab width is configurable
        tabwidth = self.editwin.tabwidth

        text = self.editwin.text
        # Get the Text widget's size
        linewidth = text.winfo_width()
        # Deduct the border and padding
        linewidth -= 2*sum([int(text.cget(opt))
                            for opt in ('border','padx')])

        # Get the Text widget's font
        font = tkFont.Font(text, name=text.cget('font'))

        # Divide the size of the Text widget by the font's width.
        # According to Tk8.4 docs, the Text widget's width is set
        # according to the width of its font's '0' (zero) character,
        # so we will use this as an approximation.
        linewidth //= font.measure('0')

        try:
            result = _countlines(s, linewidth, tabwidth)
        except TypeError:
            result = 0
        return result 

    def expand_last_squeezed_event(self, event):
        if self.expandingbuttons:
            self.expandingbuttons[-1].expand(event)
        else:
            self.text.bell()
        return "break"

    def preview_last_squeezed_event(self, event):
        if self._PREVIEW_COMMAND and self.expandingbuttons:
            self.expandingbuttons[-1].preview(event)
        else:
            self.text.bell()
        return "break"

    def squeeze_last_output_event(self, event):
        last_console = self.text.tag_prevrange("console",Tkinter.END)
        if not last_console:
            return "break"

        prev_ranges = []
        for tag_name in ("stdout","stderr"):
            rng = last_console
            while rng:
                rng = self.text.tag_prevrange(tag_name, rng[0])
                if rng and self.text.get(*rng).strip():
                    prev_ranges.append((rng, tag_name))
                    break
        if not prev_ranges:
            return "break"

        if not self.squeeze_range(*max(prev_ranges)):
            self.text.bell()
        return "break"
        
    def squeeze_current_text_event(self, event):
        insert_tag_names = self.text.tag_names(Tkinter.INSERT)
        for tag_name in ("stdout","stderr"):
            if tag_name in insert_tag_names:
                break
        else: # no tag associated with the index
            self.text.bell()
            return "break"

        # find the range to squeeze
        rng = self.text.tag_prevrange(tag_name, Tkinter.INSERT+"+1c")
        if not self.squeeze_range(rng, tag_name):
            self.text.bell()
        return "break"

    def squeeze_range(self, rng, tag_name):
        if not rng or rng[0]==rng[1]:
            return False
        start, end = rng
        
        s = self.text.get(start, end)
        # if the last char is a newline, remove it from the range
        if s and s[-1] == '\n':
            end = self.text.index("%s-1c" % end)
            s = s[:-1]
        # delete the text
        _get_base_text(self.editwin).delete(start, end)
        # prepare an ExpandingButton
        numoflines = self.count_lines(s)
        expandingbutton = ExpandingButton(s, tag_name, numoflines, self)
        # insert the ExpandingButton to the Text
        self.text.window_create(start, window=expandingbutton,
                                padx=3, pady=5)
        # insert the ExpandingButton to the list of ExpandingButtons
        i = len(self.expandingbuttons)
        while i > 0 and self.text.compare(self.expandingbuttons[i-1],
                                          ">", expandingbutton):
            i -= 1
        self.expandingbuttons.insert(i, expandingbutton)
        return True
