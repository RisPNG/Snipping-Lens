"""
Common test cases for parser & evaljs
"""
import functools
import operator


def extract(expressions):
    """Extract expressions from multi-line strings"""
    return (
        line
        for line in expressions.splitlines()
        if line.strip() and not line.startswith("#")
    )


class Bunch:
    """A simple class to enable testing of attribute & item access"""

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    def __getitem__(self, item):
        return getattr(self, item)


NAMES = {
    "A": 10,
    "B": 20,
    "C": 30,
    "obj": Bunch(foo=1, bar=2, func=lambda x: x),
    "foo": "bar",
    "bar": "baz",
    "sum": lambda *args: sum(args),
    "prod": lambda *args: functools.reduce(operator.mul, args),
    "_123": 2.0,
    "abc_123": "hello",
    "true": True,
    "false": False,
}

EXPRESSIONS = r"""
# Integers
0
12
234
# Floats
3.14
0.10
10.
.1
1E5
2e6
3.7E02
# Binary
0x0
0X10101
# Octal
0o17
0O0
# Hex
0xffaa11
0XF0c
# Boolean
true
false
# Strings
'abc123'
'a\'b\'c123'
'abc123\\'
'\t""\n'
"abc123"
"a\"b\"c123"
"abc123\\"
"\t''\n"
# Regex
"/[0-9]+/"
"/(?P<foo>foo)(?P<bar>bar)/g"
# Globals
A
B
C
obj
foo
_123
abc_123
# Unary operations
-1
+3.5
-A
+B
~0b0101
# Binary operations
1 + 1
2E3 - 1
0xF * 5.0
A / B
2 ** 3
# Comparisons
1 < 2
A > B
5 <= 5
A >= 10
A == 10
A != 10
# Bitwise
3 | 4
3 & 4
3 ^ 4
4 << 2
4 >> 2
# Compound operations
2 * 3 % 4 / 5
2 % 3 * 4 / 5
2 + 3 % 4
2 % 3 - 4
2.5 * 3 + 4 / 5.2
2.5 + 3 * 4 - 5.0
2.5 * (3 + 4)
(2 * 3) + 4
B * 3 ** 4
1.5 + 2. * .3
-0.6 * (C / 1.5)
3 * (4 + C)
A & B | ~C + 4 * 5
# Functions
prod(1, 2, 3)
sum(1, 2, 3)
prod(1, 2 * 4, -6)
sum(1, (2 * 4), -6)
A * prod(B, C)
A * prod(B, sum(B, C))
obj.func(2)
# Lists
[]
[2]
[1 + 1]
[A, 'foo', 23 * B, []]
# Objects
{}
{'a': 4}
{'a': 5, 'b': 5}
# Attribute access
obj.foo + C / 5
obj["foo"] + C / 5
(obj).bar + C * 2
(obj)['bar'] + C * 2
['a', 'b', 'c'][1]
"""

BAD_EXPRESSIONS = r"""
"'
1.B
*24
"\"
(1, 2]
[1, 2)
B.1
(1 + 2)[]
[1;2]
009
0x01FG
00.56
true : 3 ? 4
"""

JSONLY_EXPRESSIONS = [
    ("{A, B, C: 3, 'd': 4, 1: 5}", {"A": 10, "B": 20, "C": 3, "d": 4, 1: 5}),
    ("!true", False),
    ("!false", True),
    ("true && false", False),
    ("true || false", True),
    ("-12 >>> 2", 1073741821),
    ("12 >>> 2", 3),
    ("A === 10", True),
    ("A !== 10", False),
    ("true ? 0 + 1 : 1 + 1", 1),
    ("!true ? 0 + 1 : 1 | 2", 3),
    ("(true ? 1 : 2) ? 3 : 4", 3),
    ("true ? 1 : (2 ? 3 : 4)", 1),
    ("true ? 1 : 2 ? 3 : 4", 1),
]
