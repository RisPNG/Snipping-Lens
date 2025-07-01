# IDLEX EXTENSION

##    """SearchBar.py - An IDLE extension for searching for text in windows.
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
##
##    The interface is a small bar which appears on the bottom of the window,
##    and dissapears when the user stops searching.
##
##    This extension implements the usual search options, as well as regular
##    expressions.
##
##    Another nice feature is that while searching all matches are highlighted.
##
##
##    Original Author:  Tal Einat
##
##    Modified by Roger D. Serwy to work with idlex and Python 3,
##    as well as some bugfixes and improvements.
##
##
##
##    """

config_extension_def = """
[SearchBar]
enable=1
is_incremental=1
reg_exp=0
match_case=0
whole_word=0
wrap_around=0

[Searchbar_cfgBindings]
toggle-search-bar=

"""

import time
import string
import re
import sys

if sys.version < '3':
    import Tkinter
    from Tkconstants import TOP, BOTTOM, LEFT, RIGHT, X, NONE
else:
    import tkinter as Tkinter
    from tkinter.constants import TOP, BOTTOM, LEFT, RIGHT, X, NONE

EXTNAME = 'SearchBar'

from idlelib.configHandler import idleConf
from idlelib.SearchEngine import SearchEngine


class SearchBarSearchEngine(SearchEngine):
    """ Silence regex errors.
        Incremental highlighting doesn't play well with mal-formed regex.

    """

    def __init__(self, *args, **kw):
        SearchEngine.__init__(self, *args, **kw)
        self._error_callback_ptr = None
        self._incrementalSearch = False
        self.varlist = [self.revar, self.casevar, self.wordvar, self.wrapvar]
        self.tracelist = []

    def report_error(self, pat, msg, col=-1):
        #print('report_error', pat, msg, col,self._incrementalSearch)
        if self._incrementalSearch:
            if self._error_callback_ptr:
                return self._error_callback_ptr(pat, msg, col)
            else:
                return None
        else:
            return SearchEngine.report_error(self, pat, msg, col)

    def error_callback(self, ptr):
        # This is set by FindBar and ReplaceBar instances so that it
        # calls the correct callback
        self._error_callback_ptr = ptr

    def load_cfg(self):
        # Load settings from configuration handler - RDS 2012-02-03
        self.revar.set(get_cfg('reg_exp', default=False))
        self.casevar.set(get_cfg('match_case', default=False))
        self.wordvar.set(get_cfg('whole_word', default=False))
        self.wrapvar.set(get_cfg('wrap_around', default=False))

    def save_cfg(self):
        set_cfg('reg_exp', '%s' % self.revar.get())
        set_cfg('match_case', '%s' % self.casevar.get())
        set_cfg('whole_word', '%s' % self.wordvar.get())
        set_cfg('wrap_around', '%s' % self.wrapvar.get())

    def set_var_trace(self, ptr):
        obs = []
        for v in self.varlist:
            obs.append(v.trace("w", ptr))
        self.tracelist = zip(obs, self.varlist)

    def remove_var_trace(self):
        for obs, v in self.tracelist:
            v.trace_vdelete('w', obs)
        self.tracelist = []



def get_cfg(cfg, type="bool", default=True):
    return idleConf.GetOption("extensions", EXTNAME,
                         cfg, type=type, default=default)

def set_cfg(cfg, b):
    return idleConf.SetOption("extensions", EXTNAME,
                      cfg,'%s' % b)

class SearchBar:
    menudefs = []
    def __init__(self, editwin):
        text = editwin.text
        self.engine = engine = SearchBarSearchEngine(text)
        self.fb = find_bar = FindBar(editwin, editwin.status_bar, engine)
        self.rb = replace_bar = ReplaceBar(editwin, editwin.status_bar, engine)

        def find_event(event):
            replace_bar.hide_findbar_event(event, focus=False)
            find_bar.show_findbar_event(event)
            return "break"
        text.bind("<<find>>", find_event)

        def find_again_event(event):
            find_bar.search_again_event(event)
            return "break"
        text.bind("<<find-again>>", find_again_event)

        def find_selection_event(event):
            find_bar.search_selection_event(event)
            return "break"
        text.bind("<<find-selection>>", find_selection_event)

        def replace_event(event):
            find_bar.hide_findbar_event(event, focus=False)
            replace_bar.show_findbar_event(event)
            return "break"
        text.bind("<<replace>>", replace_event)

    def close(self):
        self.engine.save_cfg()




def FindBar(editwin, pack_after, engine):
    return SearchBarWidget(editwin, pack_after, engine, is_replace=False)
def ReplaceBar(editwin, pack_after, engine):
    return SearchBarWidget(editwin, pack_after, engine, is_replace=True)

class SearchBarWidget:
    def __init__(self, editwin, pack_after, engine, is_replace=False):
        self.text = editwin.text
        self.root = self.text._root()
        self.engine = engine
        self.window_engine = get_window_engine(editwin)
        self.is_replace = is_replace

        self.top = editwin.top
        self.pack_after = pack_after

        self.widgets_built = False
        self.shown = False

        self.find_var = Tkinter.StringVar(self.root)

        # The text widget's selection isn't shown when it doesn't have the
        # focus. Let's replicate it so it will be seen while searching as well.
        self.text.tag_configure("findsel",
            background=self.text.tag_cget("sel","background"),
            foreground=self.text.tag_cget("sel","foreground"))

        self._is_incremental = None
        self._expand_state = None

        self.text.bind('<FocusIn>', self.text_focusin_event, '+')

    def toggle_search_bar_event(self, event=None):  # RDS - 2011-10-18
        self.text.event_generate('<<find>>')
        return "break"

    def _show(self):
        if not self.widgets_built:
            self._build_widgets()

        if not self.shown:
            self.bar_frame.pack(side=BOTTOM, fill=X, expand=0, pady=1,
                                after=self.pack_after)
            self.window_engine.show_find_marks()
            self.shown = True # must be _before_ reset_selection()!
            # Add the "findsel" tag, which looks like the selection
            self._reset_selection()

        self._is_incremental = self.is_incremental()
        self._expand_state = None
        self.engine.error_callback(self._error_callback)
        self.engine.load_cfg()
        self.engine.set_var_trace(self._incremental_callback)

    def _hide(self, setcursor=False):
        if self.widgets_built and self.shown:
            v = self.text.yview()
            self.bar_frame.pack_forget()
            self.text.update_idletasks()
            try:
                self.text.yview_moveto(v[0])  # Tkinter work-around
            except Exception as err:  # This should never happen
                print('SearchBar._hide', err)

            self.window_engine.reset()
            self.window_engine.hide_find_marks()

            sel = self._get_selection()
            self.shown = False # must be _after_ get_selection()!
            if setcursor:
                if sel:
                    self._set_selection(sel[0], sel[1])
                    self.text.mark_set("insert", sel[0])
                else:
                    self._reset_selection()
                self.text.see("insert")

        self.text.tag_remove("findsel","1.0","end")
        self._is_incremental = None
        self._expand_state = None
        self.engine.error_callback(None)
        self.engine.save_cfg()
        self.engine.remove_var_trace()

    def _error_callback(self, pat, msg, col=-1):
        # A callback for the SearchBarSearchEngine .report_error method
        self.window_engine.reset()
        pass

    def is_incremental(self):
        if self._is_incremental is None:
            return get_cfg("is_incremental", default=False)
        else:
            return self._is_incremental

    def _incremental_callback(self, *args):
        self.engine._incrementalSearch = True

        if self.shown and self.is_incremental():
            if self.find_var.get():
                self._safe_search(start=self.text.index("insert"))
            else:
                self.window_engine.reset()
                self._clear_selection()
                self.text.see("insert")

        self.engine._incrementalSearch = False


    def _build_widgets(self):
        if not self.widgets_built:
            def _make_entry(parent, label, var, width=7):
                l = Tkinter.Label(parent, text=label, width=width, anchor="e")
                l.pack(side=LEFT, fill=NONE, expand=0)
                e = Tkinter.Entry(parent, textvariable=var, exportselection=0,
                                  width=30, border=1)
                e.pack(side=LEFT, fill=NONE, expand=0)
                e.bind("<Escape>", self.hide_findbar_event)
                return e

            def _make_checkbutton(parent, label, var):
                btn = Tkinter.Checkbutton(parent, anchor="w",
                                          text=label, variable=var)
                btn.pack(side=LEFT, fill=NONE, expand=0)
                btn.bind("<Escape>", self.hide_findbar_event)
                return btn

            def _make_button(parent, label, command):
                btn = Tkinter.Button(parent, text=label, command=command)
                btn.pack(side=LEFT, fill=NONE, expand=0)
                btn.bind("<Escape>", self.hide_findbar_event)
                return btn

            # Frame for the entire bar
            self.bar_frame = Tkinter.Frame(self.top, border=1, relief="flat")

            # Frame for the 'Find:' / 'Replace:' entry and direction
            self.find_frame = Tkinter.Frame(self.bar_frame, border=0)

            tabstop_top = Tkinter.Label(self.find_frame, takefocus=1, text='',
                              highlightthickness=0)
            tabstop_top.pack(side=LEFT)


            # 'Find:' / 'Replace:' entry
            if not self.is_replace: tmp = "Find:"
            else: tmp = "Replace:"
            self.find_ent = _make_entry(self.find_frame,
                                        tmp, self.find_var)

            self.find_frame.pack(side=TOP, fill=X, expand=1)

            if self.is_replace:
                # Frame for the 'With:' entry + replace options
                self.replace_frame = Tkinter.Frame(self.bar_frame, border=0)
                tmp = Tkinter.Label(self.replace_frame, takefocus=0, text='',
                              highlightthickness=0)
                tmp.pack(side=LEFT)


                self.replace_with_var = Tkinter.StringVar(self.root)
                self.replace_ent = _make_entry(self.replace_frame,"With:",
                                               self.replace_with_var)

                self.replace_frame.pack(side=TOP, fill=X, expand=0)

            # Frame for the 'Find:' options
            self.find_frame_options = Tkinter.Frame(self.bar_frame, border=0)  # RDS - 2011-11-12


            # Regular expression checkbutton
            btn = _make_checkbutton(self.find_frame_options,
                                    "Reg-Exp", self.engine.revar)
            if self.engine.isre():
                btn.select()
            self.reg_btn = btn

            # Match case checkbutton
            btn = _make_checkbutton(self.find_frame_options,
                                    "Match case", self.engine.casevar)
            if self.engine.iscase():
                btn.select()
            self.case_btn = btn

            # Whole word checkbutton
            btn = _make_checkbutton(self.find_frame_options,
                                    "Whole word", self.engine.wordvar)
            if self.engine.isword():
                btn.select()
            self.word_btn = btn

            # Wrap checkbutton
            btn = _make_checkbutton(self.find_frame_options,
                                    "Wrap around", self.engine.wrapvar)
            if self.engine.iswrap():
                btn.select()
            self.wrap_btn = btn

            self.find_frame_options.pack(side=TOP, fill=X, expand=1)

            # Replace buttons (if needed)
            if self.is_replace:
                self.replace_frame_buttons = Tkinter.Frame(self.bar_frame, border=0)
                self.find_btn = _make_button(self.replace_frame_buttons, "Find",
                             self._search)
                self.replace_btn = _make_button(self.replace_frame_buttons, "Replace",
                             self._replace_event)
                self.replace_find_btn = _make_button(self.replace_frame_buttons, "Replace+Find",
                             self._replace_find_event)
                self.replace_all_btn = _make_button(self.replace_frame_buttons, "Replace All",
                             self._replace_all_event)


                self.replace_frame_buttons.pack(side=TOP, fill=X, expand=0)

            # Place the direction checkbutton in the correct frame
            if self.is_replace:
                target = self.replace_frame
            else:
                target = self.find_frame

            # Direction checkbutton
            Tkinter.Label(target, text="Direction:").pack(side=LEFT,
                                                                   fill=NONE,
                                                                   expand=0,padx=6)

            self.direction_txt_var = Tkinter.StringVar(self.root)
            btn = Tkinter.Checkbutton(target,
                                      textvariable=self.direction_txt_var,
                                      variable=self.engine.backvar,
                                      command=self._update_direction_button,
                                      indicatoron=0,
                                      width=5,
                                      )
            btn.config(selectcolor=btn.cget("bg"))
            btn.pack(side=LEFT, fill=NONE, expand=0)

            if self.engine.isback():
                btn.select()
                self.direction_txt_var.set("Up")
            else:
                btn.deselect()
                self.direction_txt_var.set("Down")
            btn.bind("<Escape>",self.hide_findbar_event)
            self.direction_btn = btn

            self.widgets_built = True

            # Key bindings for the 'Find:' / 'Replace:' Entry widget
            self.find_ent.bind("<Control-Key-f>", self._safe_search)
            self.find_ent.bind("<Control-Key-g>", self._safe_search)
            self.find_ent.bind("<Control-Key-R>", self._toggle_reg_event)
            self.find_ent.bind("<Control-Key-C>", self._toggle_case_event)
            self.find_ent.bind("<Control-Key-W>", self._toggle_wrap_event)
            self.find_ent.bind("<Control-Key-D>", self._toggle_direction_event)
            self.find_ent_expander = EntryExpander(self.find_ent, self.text)
            self.find_ent_expander.bind("<Alt-Key-slash>")

            callback = self.find_ent._register(self._incremental_callback)
            self.find_ent.tk.call("trace", "variable", self.find_var, "w",
                                  callback)

            keySetName = idleConf.CurrentKeys()
            find_bindings = idleConf.GetKeyBinding(keySetName, '<<find-again>>')
            for key_event in find_bindings:
                self.find_ent.bind(key_event, self._search)   # RDS - 2011-11-03

            if not self.is_replace:
                # Key bindings for the 'Find:' Entry widget
                self.find_ent.bind("<Return>", self._safe_search)


                def tab_fix1(ev):
                    if ev.state & 1 == 0: # Windows Fix
                        self.find_ent.focus()
                        return "break"

                self.wrap_btn.bind('<Tab>', tab_fix1)

                def tab_fix2(ev):
                    self.wrap_btn.focus()
                    return "break"
                tabstop_top.bind('<FocusIn>', tab_fix2)

            else:
                # Key bindings for the 'Replace:' Entry widget
                self.find_ent.bind("<Return>", self._replace_bar_find_entry_return_event)

                # Key bindings for the 'With:' Entry widget
                self.replace_ent.bind("<Return>", self._replace_event)
                self.replace_ent.bind("<Shift-Return>", self._safe_search)
                self.replace_ent.bind("<Control-Key-f>", self._safe_search)
                self.replace_ent.bind("<Control-Key-g>", self._safe_search)
                self.replace_ent.bind("<Control-Key-R>", self._toggle_reg_event)
                self.replace_ent.bind("<Control-Key-C>", self._toggle_case_event)
                self.replace_ent.bind("<Control-Key-W>", self._toggle_wrap_event)
                self.replace_ent.bind("<Control-Key-D>", self._toggle_direction_event)
                self.replace_ent_expander = EntryExpander(self.replace_ent,
                                                          self.text)
                self.replace_ent_expander.bind("<Alt-Key-slash>")
                for key_event in find_bindings:
                    self.replace_ent.bind(key_event, self._search)   # RDS - 2011-11-19

                def tab_fix1(ev):
                    if ev.state & 1 == 0:  # Windows Fix
                        self.find_ent.focus()
                        return "break"
                self.replace_all_btn.bind('<Tab>', tab_fix1)

                def tab_fix2(x):
                    self.replace_all_btn.focus()
                    return "break"
                tabstop_top.bind('<FocusIn>', tab_fix2)



    def _destroy_widgets(self):
        if self.widgets_built:
            self.bar_frame.destroy()

    def show_findbar_event(self, event):
        self.text.tag_raise('findmark')
        self.text.tag_raise('findsel')
        self.text.tag_raise('sel')

        # Get the current selection
        sel = self._get_selection()
        if sel:
            # Put the current selection in the "Find:" entry
            # FIXME: don't overwrite regexp if it matches the selection
            self.find_var.set(self.text.get(sel[0],sel[1]))
            self._clear_selection()

        # Now show the FindBar in all it's glory!
        self._show()

        # Set the focus to the "Find:"/"Replace:" entry
        self.find_ent.focus()

        # Select all of the text in the "Find:"/"Replace:" entry
        self.find_ent.selection_range(0,"end")

        # Hide the findbar if the focus is lost
        #self.bar_frame.bind("<FocusOut>", self.hide_findbar_event)
        # RDS - 2012-02-02 - Don't hide on focus_out, since regex error messages
        #  trigger this.

        # Focus traversal (Tab or Shift-Tab) shouldn't return focus to
        # the text widget
        self.prev_text_takefocus_value = self.text.cget("takefocus")
        self.text.config(takefocus=0)
        self._incremental_callback()
        return "break"

    def text_focusin_event(self, event=None): # RDS - 2012-02-02
        if not self.shown:
            return
        else:
            self.hide_findbar_event(setcursor=False)

    def hide_findbar_event(self, event=None, setcursor=True, focus=True):
        if not self.shown:
            return "break"

        self._hide(setcursor=setcursor)
        if focus:
            self.text.focus()

        return "break"


    def search_again_event(self, event):
        if self.engine.getpat():
            return self._search(event)
        else:
            return self.show_findbar_event(event)

    def search_selection_event(self, event):
        # Get the current selection
        sel = self._get_selection()
        if not sel:
            # No selection - beep and leave
            self.text.bell()
            return "break"

        # Set the window's search engine's pattern to the current selection
        self.find_var.set(self.text.get(sel[0],sel[1]))

        return self._search(event)

    def _toggle_reg_event(self, event):
        self.reg_btn.invoke()
        return "break"

    def _toggle_case_event(self, event):
        self.case_btn.invoke()
        return "break"

    def _toggle_wrap_event(self, event):
        self.wrap_btn.invoke()
        return "break"

    def _toggle_direction_event(self, event):
        self.direction_btn.invoke()
        return "break"

    def _update_direction_button(self):
        if self.engine.backvar.get():
            self.direction_txt_var.set("Up")
        else:
            self.direction_txt_var.set("Down")

    def _replace_bar_find_entry_return_event(self, event=None):
        # Set the focus to the "With:" entry
        self.replace_ent.focus()
        # Select all of the text in the "With:" entry
        self.replace_ent.selection_range(0,"end")
        return "break"

    def _search_text(self, start, is_safe):
        self.engine.patvar.set(self.find_var.get())
        regexp = self.engine.getprog()

        if not regexp:
            # an error occurred.
            return None

        direction = not self.engine.isback()
        wrap = self.engine.iswrap()
        sel = self._get_selection()

        if start is None:
            if sel:
                start = sel[0]
            else:
                start = self.text.index("insert")
        if ( direction and sel and start == sel[0] and
             regexp.match(self.text.get(sel[0],sel[1])) ):
            _start = start + "+1c"
        else:
            _start = start
        res = self.window_engine.findnext(regexp,
                                          _start, direction, wrap, is_safe)

        # ring the bell if the selection was found again
        if sel and start == sel[0] and res == sel:
            self.text.bell()

        return res

    def _search(self, event=None, start=None, is_safe=False):
        t = time.time()
        res = self._search_text(start, is_safe)
        if res:
            first, last = res
            self._clear_selection()
            self._set_selection(first, last)
            self.text.see(first)
            if not self.shown:
                self.text.mark_set("insert", first)
        else:
            self._clear_selection()
            self.text.bell()
        return "break"

    def _safe_search(self, event=None, start=None):
        return self._search(event=event, start=start, is_safe=True)

    def _replace_event(self, event=None):
        self.engine.patvar.set(self.find_var.get())
        regexp = self.engine.getprog()
        if not regexp:
            return "break"

        # Replace if appropriate
        sel = self._get_selection()
        if sel and regexp.match(self.text.get(sel[0], sel[1])):
            replace_with = self.replace_with_var.get()

            self.text.undo_block_start()
            if sel[0] != sel[1]:
                self.text.delete(sel[0], sel[1])
            if replace_with:
                self.text.insert(sel[0], replace_with)
            self.text.undo_block_stop()

            self._clear_selection()
            self._set_selection(sel[0], sel[0] + '+%ic' % len(replace_with))
            self.text.mark_set("insert", sel[0] + '+%ic' % len(replace_with))

        return "break"

    def _replace_find_event(self, event=None):  # RDS - 2011-10-18
        self._replace_event(event)
        return self._search(event, is_safe=False)

    def _replace_all_event(self, event=None):
        self.engine.patvar.set(self.find_var.get())
        regexp = self.engine.getprog()
        if not regexp:
            return "break"

        direction = not self.engine.isback()
        wrap = self.engine.iswrap()
        self.window_engine.replace_all(regexp, self.replace_with_var.get())
        return "break"


    ### Selection related methods
    def _clear_selection(self):
        tagname = self.shown and "findsel" or "sel"
        self.text.tag_remove(tagname, "1.0", "end")

    def _set_selection(self, start, end):
        self._clear_selection()
        tagname = self.shown and "findsel" or "sel"
        self.text.tag_add(tagname, start, end)

    def _get_selection(self):
        tagname = self.shown and "findsel" or "sel"
        return self.text.tag_nextrange(tagname, '1.0', 'end')

    def _reset_selection(self):
        if self.shown:
            sel = self.text.tag_nextrange("sel", '1.0', 'end')
            if sel:
                self._set_selection(sel[0], sel[1])
            else:
                self._clear_selection()


class EntryExpander(object):
    """Expand words in an entry, taking possible words from a text widget."""
    def __init__(self, entry, text):
        self.text = text
        self.entry = entry
        self.reset()

        self.entry.bind('<Map>', self.reset)

    def reset(self, event=None):
        self._state = None

    def bind(self, event_string):
        self.entry.bind(event_string, self._expand_word_event)

    def _expand_word_event(self, event=None):
        curinsert = self.entry.index("insert")
        curline = self.entry.get()
        if not self._state:
            words = self._get_expand_words()
            index = 0
        else:
            words, index, insert, line = self._state
            if insert != curinsert or line != curline:
                words = self._get_expand_words()
                index = 0
        if not words:
            self.text.bell()
            return "break"

        curword = self._get_curr_word()
        newword = words[index]
        index = (index + 1) % len(words)
        if index == 0:
            self.text.bell() # Warn the user that we cycled around

        idx = int(self.entry.index("insert"))
        self.entry.delete(str(idx - len(curword)), str(idx))
        self.entry.insert("insert", newword)

        curinsert = self.entry.index("insert")
        curline = self.entry.get()
        self._state = words, index, curinsert, curline
        return "break"

    def _get_expand_words(self):
        curword = self._get_curr_word()
        if not curword:
            return []

        regexp = re.compile(r"\b" + curword + r"\w+\b")
        # Start at 'insert wordend' so current word is first
        beforewords = regexp.findall(self.text.get("1.0", "insert wordend"))
        beforewords.reverse()
        afterwords = regexp.findall(self.text.get("insert wordend", "end"))
        # Interleave the lists of words
        # (This is the next best thing to sorting by distance)
        allwords = []
        for a,b in zip(beforewords, afterwords):
            allwords += [a,b]
        minlen = len(allwords)/2
        allwords += beforewords[minlen:] + afterwords[minlen:]

        words_list = []
        words_dict = {}
        for w in allwords:
            if w not in words_dict:
                words_dict[w] = w
                words_list.append(w)
        words_list.append(curword)
        return words_list

    _wordchars = string.ascii_letters + string.digits + "_"
    def _get_curr_word(self):
        line = self.entry.get()
        i = j = self.entry.index("insert")
        while i > 0 and line[i-1] in self._wordchars:
            i = i-1
        return line[i:j]


def get_window_engine(editwin):
    if not hasattr(editwin, "_window_search_engine"):
        editwin._window_search_engine = WindowSearchEngine(editwin.text)
    return editwin._window_search_engine

class WindowSearchEngine:
    def __init__(self, text):
        self.text = text

        # Initialize 'findmark' tag
        self.hide_find_marks()

        self.reset()

    def __del__(self):
        try:
            self.text.tag_delete("findmark")
        except:
            pass

    def show_find_marks(self):
        # Get the highlight colors for 'hit'
        # Do this here (and not in __init__) for color config changes to take
        # effect immediately
        currentTheme = idleConf.CurrentTheme()
        mark_fg = idleConf.GetHighlight(currentTheme, 'hit', fgBg='fg')
        mark_bg = idleConf.GetHighlight(currentTheme, 'hit', fgBg='bg')

        self.text.tag_configure("findmark",
                                foreground=mark_fg,
                                background=mark_bg)

    def hide_find_marks(self):
        self.text.tag_configure("findmark",
                                foreground='',
                                background='')

    def reset(self):
        self.text.tag_remove("findmark", "1.0", "end")
        self.regexp = None

    def _pos2idx(self, pos):
        "Convert a position in the text string to a Text widget index"
        return self.text.index("1.0+%dc"%pos)

    def _set_regexp(self, regexp):
        "Set the current regexp; search for and mark all matches in the text"
        ## When searching for an extension of the previous search,
        ## i.e. regexp.startswith(self.regexp), update hits instead of starting from
        ## scratch
        self.reset()
        self.regexp = regexp

        txt = self.text.get("1.0", "end-1c")
        prev = 0
        line = 1
        rfind = txt.rfind
        tag_add = self.text.tag_add
        for res in regexp.finditer(txt):
            start, end = res.span()
            line += txt[prev:start].count('\n')
            prev = start
            start_idx = "%d.%d" % (line,
                                   start - (rfind('\n', 0, start) + 1))
            end_idx = start_idx + '+%dc'%(end-start)
            tag_add("findmark", start_idx, end_idx)

    def findnext(self, regexp, start, direction=1, wrap=True, is_safe=False,
                 last=False):
        """Find the next text sequence which matches the given regexp.

        The 'next' sequence is the one after the selection or the insert
        cursor, or before if the direction is up instead of down.

        The 'is_safe' argument tells whether it is safe to assume that the text
        being searched has not been changed since the previous search; if the
        text hasn't been changed then the search is almost trivial (due to
        pre-processing).

        """
        if regexp != self.regexp or not is_safe:
            self._set_regexp(regexp)

        # Search!
        if direction:
            next = self.text.tag_nextrange("findmark", start)
            if not next:
                if wrap:
                    # TODO: give message about wrap
                    next = self.text.tag_nextrange("findmark", '1.0', start)
                else:
                    # TODO: no more matches message
                    pass
        else:
            next = self.text.tag_prevrange("findmark", start)
            if not next:
                if wrap:
                    # TODO: give message about wrap
                    next = self.text.tag_prevrange("findmark", 'end', start)
                else:
                    # TODO: no more matches message
                    pass

        if not last and not next:
            if direction==1:
                delta='-1c'
            else:
                delta='+1c'
            q1 = self.text.index(start+delta)
            next = self.findnext(regexp, q1, direction=direction,
                                 wrap=wrap, is_safe=is_safe, last=True)
            # the "last=True" flag is to prevent infinite recursion if something
            # should go wrong with tag_nextrange or prevrange.

        return next

    def replace_all(self, regexp, replace_with):

        oldhit = None
        searchfrom = '1.0'
        self.text.undo_block_start()
        while True:
            hit = self.findnext(regexp, searchfrom,
                            direction=1, wrap=False, is_safe=False)
            if not hit or hit == oldhit:
                break
            oldhit = hit  # avoid infinite loop due to ModifiedUndoDelegator in PyShell
            first, last = hit
            if first != last:
                self.text.delete(first, last)
            if replace_with:
                self.text.insert(first, replace_with)

            searchfrom = last

        self.text.undo_block_stop()


def get_selection(text):
    "Get the selection range in a text widget"
    tmp = text.tag_nextrange("sel","1.0","end")
    if tmp:
        first, last = tmp
    else:
        first = last = text.index("insert")
    return first, last

##def idx2ints(idx):
##    "Convert a Text widget index to a (line, col) pair"
##    line, col = map(int,idx.split(".")) # Fails on invalid index
##    return line, col

##def ints2idx(ints):
##    "Convert a (line, col) pair to Tk's Text widget's format."
##    return "%d.%d" % ints # Fails on invalid index
