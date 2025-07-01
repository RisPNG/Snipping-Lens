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
##    PastePyShell.py
##
##    Handle code formatting of PyShell text, per issue11838.
##    Also addresses "issue7676 - IDLE shell shouldn't use TABs"
##    where TABs are a problem due to pasting into the editor from PyShell.
##
##
##    """

config_extension_def = """
[PastePyShell]
enable=1
enable_shell=0
enable_editor=1

[PastePyShell_cfgBindings]
paste-code=<Control-Shift-Key-V>
paste-code-only=
"""
# NOTE: the "Key" in <Control-Shift-Key-V> is needed for it to work.


# get the IDLE configuration handler
from idlelib.configHandler import idleConf
from idlelib.EditorWindow import classifyws
import re

class PastePyShell:

    # A more proper place is to add the menu entry in "Bindings.py"
    # just after "Paste" under "edit".
    menudefs = [
        ('edit', [
               ('Paste from S_hell', '<<paste-code>>'),
               ('Paste from Shell (only code)', '<<paste-code-only>>')
       ]),]


    def __init__(self, editwin):
        self.editwin = editwin      # reference to the editor window
        self.text = text = self.editwin.text
        self.text.bind("<<paste-code>>", self.paste_code_event)

        r = editwin.rmenu_specs
        # See Issue1207589 patch
        if len(r) > 0:
            if len(r[0]) == 2:
                specs = [('Paste from Shell', '<<paste-code>>'),
                         ('Paste from Shell (only code)', '<<paste-code-only>>')]
            elif len(r[0]) == 3:
                specs = [('Paste from Shell', '<<paste-code>>', None),
                         ('Paste from Shell (only code)', '<<paste-code-only>>', None)]
        else:
            specs = []

        for m in specs:
            if m not in editwin.rmenu_specs:
                editwin.rmenu_specs.append(m)

    def paste_code_only_event(self, ev=None):
        self.paste_code(comments=False)
        return "break"

    def paste_code_event(self, ev=None):
        self.paste_code()
        return "break"

    def paste_code(self, comments=True):
        editwin = self.editwin
        text = self.text
        per = self.editwin.per

        try:
            chars = editwin.top.selection_get(selection="CLIPBOARD")
        except Exception:
            return "break"

        pc = PastePyShellProcessor(comments=comments)
        res = pc._paste_process(chars)
        text.insert('insert', res)
        return "break"

class PastePyShellProcessor:
    def __init__(self, tabwidth=8, usetabs=False, comments=True):
        self.tabwidth = tabwidth
        self.usetabs = usetabs
        self.comments = comments

        # TODO - allow "email" and "diff" pasting
        self.prompts = [r'^>>> ',  # standard Python ps1
                        r'^\.\.\. ',  # standard Python ps2
                        r'^[ ]*In \[[\d]*\]: ', # IPython ps1
                        r'^[ ]*[\.]*: '] # IPython ps2

    def starts_with_prompt(self, L):
        for p in self.prompts:
            m = re.match(p, L)
            if m:
                return True
        else:
            return False

    def remove_prompt(self, L):
        for p in self.prompts:
            m = re.match(p, L)
            if m:
                L = re.sub(p, '', L, count=1)
                break
        return L

    def _paste_process(self, chars):
        """ Handle code formatting of PyShell text, per issue11838. """

        # This code implements a two-state machine, where
        # "iscode" indicates the state.

        insert_blankline = False   # flag to insert blank lines around code
        include_comments = self.comments

        lines = chars.split('\n')
        iscode = False   # state indicator for >>>

        has_prompt = False

        INDENT_LIST = [' ', '\t']

        NL = []
        for L in lines:
            # handle state machine transition
            if iscode:
                # Leave "iscode" state if the line is not indented
                # and the line is not another prompt.
                if L:
                    if L[0] not in INDENT_LIST:

                        if not self.starts_with_prompt(L):
                            iscode = False
                            if insert_blankline: NL.append('')
                else:
                    #pass
                    continue # skip double blank line at end of multi-line
            else:
                # Enter "iscode" state is the line begins with a prompt.
                if self.starts_with_prompt(L):
                    if insert_blankline: NL.append('')
                    iscode = True
                    has_prompt = True


            # handle output of state machine
            if not iscode:
                if include_comments:
                    NL.append('#%s' % L)  # comment output
            else:
                # remove >>> and tabs (if necessary)
                if self.starts_with_prompt(L):
                    L = self.remove_prompt(L)

                # convert to spaces
                raw, effective = classifyws(L, self.tabwidth)
                L = self._make_blanks(effective) + L[raw:]

                # handle shell RESTART
                if "= RESTART =" in L:
                    L = '#%s' % L

                NL.append(L)

        return '\n'.join(NL)

##        # Code to fall back to normal Paste if no prompts detected in buffer
##        if has_prompt:
##            return '\n'.join(NL)
##        else:
##            return chars

    def _make_blanks(self, n):   # from EditorWindow.py
        # copied over in case EditorWindow's implementation changes.
        if self.usetabs:
            ntabs, nspaces = divmod(n, self.tabwidth)
            return '\t' * ntabs + ' ' * nspaces
        else:
            return ' ' * n



test_code = r"""Python 2.7.1+ (r271:86832, Apr 11 2011, 18:13:53)
[GCC 4.5.2] on linux2
Type "copyright", "credits" or "license()" for more information.
>>> ================================ RESTART ================================
>>> if 1:
	print(123)
	print(456)


123
456
>>> import sys
>>> print sys.version
2.7.1+ (r271:86832, Apr 11 2011, 18:13:53)
[GCC 4.5.2]
>>> for x in range(3):
	print(x**2)


0
1
4
>>> print('>>> ') # This output will be treated as a prompt...
>>>
>>>
>>>
>>> print('\tThis line will be considered code.')
        This line will be considered code.
>>>
"""

if __name__ == '__main__':
    # test
    pc = PastePyShellProcessor()
    res = pc._paste_process(test_code)
    for i in res.split('\n'):  # work-around squeezer
        print(i)
