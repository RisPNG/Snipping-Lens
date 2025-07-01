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
##    TabHighlight.py
##
##    Highlights TABS in the text, which may be useful in
##    fixing tab/space issues with files.
##
##
##    """

config_extension_def = """
[TabHighlight]
enable=1
enable_shell=0
enable_editor=1
highlight=1

[TabHighlight_cfgBindings]
tab-highlight-toggle=

"""


from idlelib.configHandler import idleConf
from idlelib.Delegator import Delegator

EXTNAME = "TabHighlight"

def get_cfg(cfg, type="bool", default=True):
    return idleConf.GetOption("extensions", EXTNAME,
                         cfg, type=type, default=default)

def set_cfg(cfg, b):
    return idleConf.SetOption("extensions", EXTNAME,
                      cfg,'%s' % b)

_AFTER_UNDO = True

class TabHighlight:  

    menudefs = [
        ('options', [
               (r"!Highlight \t tabs", '<<tab-highlight-toggle>>'),
       ]),]

    def __init__(self, editwin):
        self.editwin = editwin      # reference to the editor window
        self.text = editwin.text
        self.tabdelegator = None
        self.text.bind('<<tab-highlight-toggle>>',
                       self.tab_highlight_toggle_event)
        en = get_cfg("highlight", type="bool", default=True)
        self.tab_set_state(en)

    def close(self):
        try:
            self._tab_disable()
            self.text = None
            self.editwin = None
        except Exception as err:
            print(err)
            pass

    def tab_set_state(self, b):
        self.enabled = b
        if self.enabled:
            self._tab_enable()
        else:
            self._tab_disable()
        set_cfg("highlight", self.enabled)

    def tab_highlight_toggle_event(self, ev=None):
        self.tab_set_state(not self.enabled)

    def _tab_enable(self):
        """ Enable Tab Highlighting """
        text = self.text
        text.tag_config('TAB',
                        background='#FF0000',
                        bgstipple='gray25')

        text.tag_raise('sel')
        
        # create the tab highlighting delegator
        if self.tabdelegator:
            raise Exception('TabDelegator already exists')
        self.tabdelegator = TabDelegator()

        if _AFTER_UNDO:
            self.tabdelegator.setdelegate(self.editwin.undo.delegate)
            self.editwin.undo.setdelegate(self.tabdelegator)
        else:
            self.editwin.per.insertfilter(self.tabdelegator)
        

        # process text already in the buffer
        lines = int(text.index('end').split('.')[0]) + 1
        self.tabdelegator._do_highlight('1.0', lines)
        self.editwin.setvar('<<tab-highlight-toggle>>', True)


    def _tab_disable(self):
        """ Disable tab highlighting """
        text = self.text
        if self.tabdelegator:
            self.editwin.per.removefilter(self.tabdelegator)
            self.tabdelegator = None
        text.tag_remove('TAB', '1.0', 'end')
        self.editwin.setvar('<<tab-highlight-toggle>>', False)


class TabDelegator(Delegator):
    def insert(self, index, chars, tags=None):
        index_start = self.index(index + ' linestart')
        self.delegate.insert(index, chars, tags)

        lines = chars.count('\n')
        try:
            self._do_highlight(index_start, lines)
        except Exception as err:
            print(err)
            pass

    def _do_highlight(self, index, lines):
        text = self.delegate
        startline = int(index.split('.')[0])

        for line in range(startline, startline+lines+1):
            t = text.get('%i.0' % line, '%i.0' % (line+1))
            if '\t' in t:
                text.tag_remove('TAB', '%i.0' % line, '%i.0' % (line+1))
                col = -1
                while True:
                    col = t.find('\t', col+1)
                    if col == -1:
                        break
                    text.tag_add('TAB',
                                 '%i.%i' % (line, col),
                                 '%i.%i' % (line,col+1))
                        

        
