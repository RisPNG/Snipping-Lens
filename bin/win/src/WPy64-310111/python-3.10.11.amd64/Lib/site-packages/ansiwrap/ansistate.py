
import sys

_PY2 = sys.version_info[0] == 2


class ANSIState(object):
    """
    Manage running state of a sequence of ANSI codes.
    """

    def __init__(self, fg=None, bg=None, style=None):
        self.fg = fg
        self.bg = bg
        self.style = style
        self.seen = []

    def consume(self, code):
        """
        Workhorse of the show. Accept a code, update the current
        state to reflect the impact of the code.
        """
        if code.startswith('\x1b['):
            code = code[2:]
        if code == 'K':
            pass # discard EL
        elif code.endswith('m'):
            # SGR code
            vals = [int(v or 0) for v in code.rstrip('m').split(';')]
            # show(vals)
            while vals:
                top = vals.pop(0)
                if top == 0:
                    self.fg = None
                    self.bg = None
                    self.style = None
                elif 1 <= top <= 9:
                    if self.style is None:
                        self.style = []
                    if top not in self.style:
                        self.style.append(top)
                    self.style = sorted(self.style)
                elif 21 <= top <= 29:
                    antitop = top - 20
                    if self.style is not None and antitop in self.style:
                        self.style = [v for v in self.style if v != antitop]
                    if not self.style:
                        self.style = None
                elif 30 <= top < 38:
                    self.fg = top
                elif top == 39:
                    self.fg = None
                elif top == 38:
                    under = vals.pop(0)
                    if under == 5:
                        self.fg = (38, 5, vals.pop(0))
                    elif under == 2:
                        self.fg = (38, 2, vals.pop(0),
                                      vals.pop(0), vals.pop(0))
                    else:
                        raise ValueError('cant parse fg')
                elif 40 <= top < 48:
                    self.bg = top
                elif top == 49:
                    self.bg = None
                elif top == 48:
                    under = vals.pop(0)
                    if under == 5:
                        self.bg = (48, 5, vals.pop(0))
                    elif under == 2:
                        self.bg = (48, 2, vals.pop(0),
                                      vals.pop(0), vals.pop(0))
                    else:
                        raise ValueError('cant parse bg')
            assert not vals
            self.seen.append(code)

    def code(self):
        """
        Return an ANSI code that creates the current state.
        """

        def codearr(c):
            if c is None:
                return []
            if isinstance(c, str):
                return [c]
            if isinstance(c, (tuple, list, set)):
                return ';'.join(str(p) for p in c)
            return [str(c)]

        raw_parts = []
        raw_parts.extend(codearr(self.fg))
        raw_parts.extend(codearr(self.bg))
        raw_parts.extend(codearr(self.style))
        parts = [p for p in raw_parts if p is not None]
        if parts:
            return '\x1b[{0}m'.format(';'.join(str(p) for p in parts))
        else:
            return ''

    def __repr__(self):
        clsname = self.__class__.__name__
        guts = 'fg={fg}, bg={bg}, style={style}'.format(**self.__dict__)
        return '{clsname}({guts})'.format(**vars())

    if _PY2:
        def __unicode__(self):
            nn = lambda x: u'\u2014' if x is None else x
            return u'({0}, {1}, {2})'.format(nn(self.fg), nn(self.bg), nn(self.style))
    else:
        def __str__(self):
            nn = lambda x: u'\u2014' if x is None else x
            return u'({0}, {1}, {2})'.format(nn(self.fg), nn(self.bg), nn(self.style))
