# IDLEX EXTENSION
##    """
##    Copyright(C) 2012 The Board of Trustees of the University of Illinois.
##    All rights reserved.
##    Developed by:   Roger D. Serwy
##                    University of Illinois
##    License: See LICENSE.txt
##    """



##
##  This extension allows for pasting of multiple lines of code into the shell
##  for execution. This addresses http://bugs.python.org/issue3559
##
  

from __future__ import print_function

config_extension_def = """
[MultiLineRun]
enable=1
enable_editor=0
enable_shell=1
"""

from idlelib.configHandler import idleConf
from idlelib.Delegator import Delegator
import time
import re
import sys
import traceback

class MultiLineDelegator(Delegator):
    def __init__(self, callback):
        Delegator.__init__(self)
        self.callback = callback
        self.paste = False
        
    def insert(self, index, chars, tags=None):
        do_insert = True
        if self.paste:
            self.paste = False
            try:
                do_insert = self.callback(chars)
            except Exception as err:
                # Must catch exception else IDLE closes
                print(' MultiLineRun Internal Error', file=sys.stderr)
                traceback.print_exc()

        if do_insert:
            self.delegate.insert(index, chars, tags)

    def delete(self, index1, index2=None):
        self.delegate.delete(index1, index2)


class MultiLineRun:

    # eol code from IOBinding.py
    eol = r"(\r\n)|\n|\r"  # \r\n (Windows), \n (UNIX), or \r (Mac)
    eol_re = re.compile(eol)

    def __init__(self, editwin):
        self.editwin = editwin      # reference to the editor window
        self.text = text = self.editwin.text

        self.mld = MultiLineDelegator(self.paste_intercept)
        self.editwin.per.insertfilter(self.mld)

        self.text.bind('<<Paste>>', self.paste, '+')
        
        wsys = text.tk.call('tk', 'windowingsystem')
        if wsys == 'x11':
            self.text.bind('<Button-2>', self.paste, '+')  # For X11 middle click

        self.playback_list = []

    def paste(self, event=None):
        self.mld.paste = True
        
    def paste_intercept(self, chars):
        self.mld.paste = False
        if self.editwin.executing:
            return True

        self.play(chars)
        
    def play(self, chars):
        chars = self.eol_re.sub(r"\n", chars)
        
        L = [] # list of entries to play into the shell
        index = 0
        while True:
            next_index = chars.find('\n', index)
            if next_index > -1:
                line = chars[index:next_index]
                L.append((line, True))
            else:
                line = chars[index:]
                L.append((line, False))
                break
            index = next_index + 1

        L = self.dedent(L)
        self.playback_list = L
        self._pre_playback()
        self.do_playback()

    def dedent(self, L):
        return L

        # TODO: make this work
        # Multiline strings may make code appear less indented than it is...
        Lcode = [line for line, ret in L if line.rstrip() and not line.startswith('#')]

        dedent_tab =0 
        while all(map(Lcode.startswith('\t'))):
            Lcode = [x[1:] for x in Lcode]
            dedent_tab += 1
        
        if not dedent_tab:
            dedent_space = 0
            while all(map(Lcode.startswith(' '))):
                Lcode = [x[1:] for x in Lcode]
                dedent_space += 1
            depth = dedent_space
            src = '\n'.join(L)
            src = re.sub(r"(?<![^\n]) {%i,%i}" % (depth, depth), "", src)
            L = src.split('\n')
        else:
            depth = dedent_tab
            src = '\n'.join(L)
            src = re.sub(r"(?<![^\n])\t{%i,%i}" % (depth, depth), "", src)
            L = src.split('\n')
        
        return L

    def _pre_playback(self):
        # newline_and_indent can be problematic - replace it momentarily
        self.n = self.editwin.newline_and_indent_event
        def simple_return(text = self.text):
            text.insert('insert', '\n')
        self.editwin.newline_and_indent_event = lambda *args, **kwargs: simple_return()

    def _post_playback(self):
        self.editwin.newline_and_indent_event = self.n
    
    def do_playback(self):
        self.mld.paste = False
        e = self.editwin
        t = self.text
        
        if not self.playback_list or e.canceled:
            self._post_playback()
            return
        
        if not e.executing:# or e.reading:
            line, enter = self.playback_list.pop(0)
            t.mark_gravity('iomark', 'left')
            t.insert('insert', line)
            if e.color:
                e.color.recolorize()
            if enter:
                t.event_generate('<Return>')
                t.see('insert')
                
        t.after(10, self.do_playback)


