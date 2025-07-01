# IDLEX EXTENSION
##    
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
##    Reindent Extension:
##
##    Relies on ScriptBinding.py extension
##
##    Provides "Re-indent" on the Format menu.
##    Based on "reindent.py" code released to the public domain, by Tim Peters, 03 October 2000.
##
##    Part of Python Bug, issue 5150 Editing.
##
##    Modified to use IdleX October 2011
##
##
##    This code includes a patch from http://bugs.python.org/issue12930
##    to disallow strings from being modified. That code is under the PSF license,
##    based on the contributor's agreement with the PSF.
##

config_extension_def = """

[ReindentExtension]
enable=1
enable_shell=0
enable_editor=1

[ReindentExtension_cfgBindings]
reindent-apply=

"""

import sys
import tokenize

if sys.version < '3':
    from StringIO import StringIO
else:
    from io import StringIO
    xrange = range


change_strings = False  # flag for reindent code patch

def _rstrip(line, JUNK='\n \t'):
    """Return line stripped of trailing spaces, tabs, newlines.

    Note that line.rstrip() instead also strips sundry control characters,
    but at least one known Emacs user expects to keep junk like that, not
    mentioning Barry by name or anything <wink>.
    """

    i = len(line)
    while i > 0 and line[i-1] in JUNK:
        i -= 1
    return line[:i]

class Reindenter:

    def __init__(self, f):
        self.find_stmt = 1  # next token begins a fresh stmt?
        self.level = 0      # current indent level

        # Raw file lines.
        self.raw = f.readlines()

        # File lines, rstripped & tab-expanded.  Dummy at start is so
        # that we can use tokenize's 1-based line numbering easily.
        # Note that a line is all-blank iff it's "\n".
        self.lines = [_rstrip(line).expandtabs() + "\n"
                      for line in self.raw]
        self.lines.insert(0, None)
        self.index = 1  # index into self.lines of next line

        # List of (lineno, indentlevel) pairs, one for each stmt and
        # comment line.  indentlevel is -1 for comment lines, as a
        # signal that tokenize doesn't know what to do about them;
        # indeed, they're our headache!
        self.stats = []

        # Save the newlines found in the file so they can be used to
        #  create output without mutating the newlines.
        self.newlines = '\n'  # RDS - default in IDLE

    def rstrip_and_expand_tabs(self):
        self.lines = [line for line in self.raw]
        self.lines.insert(0, None)
        # Only apply rstrip if the line is not part of a multiline string
        # and expand tabs only if not within in a string.
        tokens = tokenize.generate_tokens(self.getline)

        strmask = {}
        def addmask(line, scol, ecol):
            # Keep track of start/end columns for a string on a particular
            # line. Each element is used to toggle the string state on a line.
            if line in strmask:
                strmask[line].extend([scol, ecol])
            else:
                strmask[line] = [scol, ecol]

        lines = self.lines
        for _token in tokens:
            _type, string, slinecol, elinecol, line = _token
            if _type == tokenize.STRING:
                sl, sc = slinecol
                el, ec = elinecol
                if sl == el:
                    # Single line string
                    addmask(sl, sc, ec)
                else:
                    # Multi-line string
                    addmask(sl, sc, len(lines[sl]))
                    strmask[sl].append(-1) # Start multi-line
                    strmask[el] = [-1]  # Stop multi-line
                    addmask(el, 0, ec)

        self.index = 1  # reset index for self.getline

        n = 1
        multi = False
        while n < len(lines):
            line = lines[n]
            strtoggle = strmask.get(n, None)
            if strtoggle is None:
                if not multi:
                    lines[n] = _rstrip(line).expandtabs() + '\n'
            else:
                # Process strings on a single line
                isstr = False
                scol = 0
                processed = []
                while strtoggle:
                    ecol = strtoggle.pop(0)
                    if ecol == -1:      # toggle multiline mode
                        if not multi:
                            ecol = len(line)
                        multi = not multi
                        isstr = multi
                        continue
                    if isstr:
                        processed.append(line[scol:ecol])
                    else:
                        processed.append(line[scol:ecol].expandtabs())

                    scol = ecol
                    isstr = not isstr

                if not multi:
                    processed.append(_rstrip(line[ecol:]).expandtabs() + '\n')
                else:
                    processed.append(line[ecol:-1])

                lines[n] = ''.join(processed)
            n += 1

    def run(self):
        if not change_strings:
            self.rstrip_and_expand_tabs()
        tokens = tokenize.generate_tokens(self.getline)
        for _token in tokens:
            self.tokeneater(*_token)
        # Remove trailing empty lines.
        lines = self.lines
        while lines and lines[-1] == "\n":
            lines.pop()
        # Sentinel.
        stats = self.stats
        stats.append((len(lines), 0))
        # Map count of leading spaces to # we want.
        have2want = {}
        # Program after transformation.
        after = self.after = []
        # Copy over initial empty lines -- there's nothing to do until
        # we see a line with *something* on it.
        i = stats[0][0]
        after.extend(lines[1:i])
        for i in range(len(stats) - 1):
            thisstmt, thislevel = stats[i]
            nextstmt = stats[i + 1][0]
            have = getlspace(lines[thisstmt])
            want = thislevel * 4
            if want < 0:
                # A comment line.
                if have:
                    # An indented comment line.  If we saw the same
                    # indentation before, reuse what it most recently
                    # mapped to.
                    want = have2want.get(have, -1)
                    if want < 0:
                        # Then it probably belongs to the next real stmt.
                        for j in range(i + 1, len(stats) - 1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                if have == getlspace(lines[jline]):
                                    want = jlevel * 4
                                break
                    if want < 0:           # Maybe it's a hanging
                                           # comment like this one,
                        # in which case we should shift it like its base
                        # line got shifted.
                        for j in range(i - 1, -1, -1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                want = have + (getlspace(after[jline - 1]) -
                                               getlspace(lines[jline]))
                                break
                    if want < 0:
                        # Still no luck -- leave it alone.
                        want = have
                else:
                    want = 0
            assert want >= 0
            have2want[have] = want
            diff = want - have
            if diff == 0 or have == 0:
                after.extend(lines[thisstmt:nextstmt])
            else:
                for line in lines[thisstmt:nextstmt]:
                    if diff > 0:
                        if line == "\n":
                            after.append(line)
                        else:
                            after.append(" " * diff + line)
                    else:
                        remove = min(getlspace(line), -diff)
                        after.append(line[remove:])
        return self.raw != self.after

    def write(self, f):
        f.writelines(self.after)

    # Line-getter for tokenize.
    def getline(self):
        if self.index >= len(self.lines):
            line = ""
        else:
            line = self.lines[self.index]
            self.index += 1
        return line

    # Line-eater for tokenize.
    def tokeneater(self, type, token, slinecol, end, line,
                   INDENT=tokenize.INDENT,
                   DEDENT=tokenize.DEDENT,
                   NEWLINE=tokenize.NEWLINE,
                   COMMENT=tokenize.COMMENT,
                   NL=tokenize.NL):

        if type == NEWLINE:
            # A program statement, or ENDMARKER, will eventually follow,
            # after some (possibly empty) run of tokens of the form
            #     (NL | COMMENT)* (INDENT | DEDENT+)?
            self.find_stmt = 1

        elif type == INDENT:
            self.find_stmt = 1
            self.level += 1

        elif type == DEDENT:
            self.find_stmt = 1
            self.level -= 1

        elif type == COMMENT:
            if self.find_stmt:
                self.stats.append((slinecol[0], -1))
                # but we're still looking for a new stmt, so leave
                # find_stmt alone

        elif type == NL:
            pass

        elif self.find_stmt:
            # This is the first "real token" following a NEWLINE, so it
            # must be the first token of the next program statement, or an
            # ENDMARKER.
            self.find_stmt = 0
            if line:   # not endmarker
                self.stats.append((slinecol[0], self.level))


# Count number of leading blanks.
def getlspace(line):
    i, n = 0, len(line)
    while i < n and line[i] == " ":
        i += 1
    return i


class ReindentExtension:

    menudefs = [('format', [('Apply Reindent', '<<reindent-apply>>')])]

    def __init__(self, editwin):
        self.editwin = editwin


    def reindent_apply_event(self, event=None):

        text = self.editwin.text
        undo = self.editwin.undo

        f_in = StringIO()
        source = text.get('0.0', 'end -1 char')    # -1 char to avoid trailing \n,
                                                   # otherwise the file is always
                                                   # marked as "changed"
        f_in.write(source)
        f_in.seek(0)

        r = Reindenter(f_in)
        try:
            changed = r.run()
        except (IndentationError, SyntaxError) as err:
            msg, (errorfilename, lineno, offset, line) = err

            sb = self.editwin.extensions['ScriptBinding']
            sb.colorize_syntax_error(msg, lineno, offset)
            sb.errorbox("Syntax error",
                        "There's an error in your program:\n" + msg)
            return 'break'

        if not changed:
            return 'break'

        f_out = StringIO()
        r.write(f_out)
        f_out.seek(0)

        CUR = text.index('insert')  # save cursor index
        loc = text.yview()[0]

        undo.undo_block_start()
        text.delete('0.0', text.index('end'))
        text.insert('0.0', f_out.read())
        undo.undo_block_stop()

        text.mark_set('insert', CUR)  # restore cursor index
        text.yview_moveto(loc)

        return 'break'
