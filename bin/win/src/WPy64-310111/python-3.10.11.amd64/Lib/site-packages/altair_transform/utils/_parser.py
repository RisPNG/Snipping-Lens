"""
Simplified Javascript expression parser.
"""
# pylint: disable=W,C,R
import os

from typing import Tuple

import ply.lex as lex
import ply.yacc as yacc

from altair_transform.utils import ast


# TODO: regexp literals?


class ParserBase:
    """
    Base class for a lexer/parser that has the rules defined as methods
    """

    tokens: Tuple = ()
    precedence: Tuple = ()

    def __init__(self, **kw):
        self.debug = kw.get("debug", 0)
        try:
            modname = (
                os.path.split(os.path.splitext(__file__)[0])[1]
                + "_"
                + self.__class__.__name__
            )
        except ValueError:
            modname = "parser" + "_" + self.__class__.__name__
        self.debugfile = modname + ".dbg"
        self.tabmodule = modname + "_" + "parsetab"

        # Build the lexer and parser
        lex.lex(module=self, debug=self.debug)
        yacc.yacc(
            module=self,
            debug=self.debug,
            debugfile=self.debugfile,
            tabmodule=self.tabmodule,
        )

    def parse(self, expression):
        return yacc.parse(expression)


class Parser(ParserBase):

    tokens = (
        "NAME",
        "STRING",
        "FLOAT",
        "BINARY",
        "OCTAL",
        "HEX",
        "REGEX",
        "PLUS",
        "MINUS",
        "EXP",
        "TIMES",
        "DIVIDE",
        "MODULO",
        "PERIOD",
        "COMMA",
        "COLON",
        "QUESTION",
        "LPAREN",
        "RPAREN",
        "LBRACKET",
        "RBRACKET",
        "LBRACE",
        "RBRACE",
        "LOGICAL_OR",
        "LOGICAL_AND",
        "LOGICAL_NOT",
        "BITWISE_NOT",
        "BITWISE_OR",
        "BITWISE_AND",
        "BITWISE_XOR",
        "LSHIFT",
        "RSHIFT",
        "ZFRSHIFT",
        "GREATER_EQUAL",
        "GREATER",
        "LESS_EQUAL",
        "LESS",
        "IDENT",
        "NIDENT",
        "EQUAL",
        "NEQUAL",
    )

    # Tokens

    t_PLUS = r"\+"
    t_MINUS = r"-"
    t_EXP = r"\*\*"
    t_TIMES = r"\*"
    t_DIVIDE = r"/"
    t_MODULO = r"%"
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_LBRACKET = r"\["
    t_RBRACKET = r"\]"
    t_LBRACE = r"\{"
    t_RBRACE = r"\}"
    t_PERIOD = r"\."
    t_COMMA = r","
    t_COLON = r"\:"
    t_QUESTION = r"\?"
    t_LOGICAL_OR = r"\|\|"
    t_BITWISE_OR = r"\|"
    t_LOGICAL_AND = r"&&"
    t_BITWISE_AND = r"&"
    t_BITWISE_XOR = r"\^"
    t_BITWISE_NOT = r"~"
    t_LSHIFT = r"<<"
    t_ZFRSHIFT = r">>>"
    t_RSHIFT = r">>"
    t_GREATER_EQUAL = r">="
    t_GREATER = r">"
    t_LESS_EQUAL = r"<="
    t_LESS = r"<"
    t_IDENT = r"==="
    t_EQUAL = r"=="
    t_NIDENT = r"!=="
    t_NEQUAL = r"!="
    t_LOGICAL_NOT = r"!"
    t_NAME = r"[a-zA-Z_][a-zA-Z0-9_]*"

    def t_BINARY(self, t):
        r"0[bB][01]+"
        t.value = int(t.value, 2)
        return t

    def t_OCTAL(self, t):
        r"0[oO]?[0-7]+"
        t.value = int(t.value, 8)
        return t

    def t_HEX(self, t):
        r"0[xX][0-9A-Fa-f]+"
        t.value = int(t.value, 16)
        return t

    def t_FLOAT(self, t):
        r"([1-9]\d*(\.\d*)?|0?\.\d+|0)([eE]\d+)?"
        t.value = float(t.value)
        return t

    def t_STRING(self, t):
        r"""(?P<openquote>["'])((\\{2})*|(.*?[^\\](\\{2})*))(?P=openquote)"""
        t.value = bytes(t.value[1:-1], "utf-8").decode("unicode_escape")
        return t

    # TODO: actually parse & validate regexps?
    def t_REGEX(self, t):
        r"\/(?P<REGEX_pattern>(?![*+?])(?:[^\r\n\[/\\]|\\.|\[(?:[^\r\n\]\\]|\\.)*\])+)\/(?P<REGEX_flags>[gmisuy]{0,6})"
        groups = t.lexer.lexmatch.groupdict()
        t.value = {"pattern": groups["REGEX_pattern"], "flags": groups["REGEX_flags"]}
        return t

    t_ignore = " \t"

    def t_newline(self, t):
        r"\n+"
        t.lexer.lineno += t.value.count("\n")

    def t_error(self, t):
        raise ValueError("Illegal character '%s'" % t.value[0])

    # Parsing rules

    precedence = (
        ("right", "QUESTION"),
        ("left", "LOGICAL_OR"),
        ("left", "LOGICAL_AND"),
        ("left", "BITWISE_OR"),
        ("left", "BITWISE_XOR"),
        ("left", "BITWISE_AND"),
        ("left", "EQUAL", "NEQUAL", "IDENT", "NIDENT"),
        ("left", "LESS", "LESS_EQUAL", "GREATER", "GREATER_EQUAL"),
        ("left", "LSHIFT", "RSHIFT", "ZFRSHIFT"),
        ("left", "PLUS", "MINUS"),
        ("left", "TIMES", "DIVIDE", "MODULO"),
        ("left", "EXP"),
        ("right", "UMINUS", "UPLUS", "LOGICAL_NOT", "BITWISE_NOT"),
    )

    def p_expression_binop(self, p):
        """
        expression : expression PLUS expression
                   | expression MINUS expression
                   | expression TIMES expression
                   | expression DIVIDE expression
                   | expression EXP expression
                   | expression MODULO expression
                   | expression LESS expression
                   | expression LESS_EQUAL expression
                   | expression GREATER expression
                   | expression GREATER_EQUAL expression
                   | expression LSHIFT expression
                   | expression RSHIFT expression
                   | expression ZFRSHIFT expression
                   | expression EQUAL expression
                   | expression IDENT expression
                   | expression NEQUAL expression
                   | expression NIDENT expression
                   | expression BITWISE_AND expression
                   | expression BITWISE_OR expression
                   | expression BITWISE_XOR expression
                   | expression LOGICAL_OR expression
                   | expression LOGICAL_AND expression
        """
        p[0] = ast.BinOp(lhs=p[1], op=p[2], rhs=p[3])

    def p_expression_ternary(self, p):
        "expression : expression QUESTION expression COLON expression"
        p[0] = ast.TernOp(op=(p[2], p[4]), lhs=p[1], mid=p[3], rhs=p[5])

    def p_expression_unaryop(self, p):
        """
        expression : MINUS expression %prec UMINUS
                   | PLUS expression %prec UPLUS
                   | BITWISE_NOT expression
                   | LOGICAL_NOT expression
        """
        p[0] = ast.UnOp(op=p[1], rhs=p[2])

    def p_expression_atom(self, p):
        """
        expression : atom
        """
        p[0] = p[1]

    def p_atom(self, p):
        """
        atom : number
             | string
             | regex
             | global
             | list
             | object
             | group
             | attraccess
             | functioncall
             | indexing
        """
        p[0] = p[1]

    def p_number(self, p):
        """
        number : HEX
               | OCTAL
               | BINARY
               | FLOAT
        """
        p[0] = ast.Number(p[1])

    def p_string(self, p):
        "string : STRING"
        p[0] = ast.String(p[1])

    def p_regex(self, p):
        "regex : REGEX"
        p[0] = ast.Regex(p[1])

    def p_global(self, p):
        "global : NAME"
        p[0] = ast.Global(p[1])

    def p_name(self, p):
        "name : NAME"
        p[0] = ast.Name(p[1])

    def p_list(self, p):
        """
        list : LBRACKET RBRACKET
             | LBRACKET arglist RBRACKET
        """
        if len(p) == 3:
            p[0] = ast.List([])
        elif len(p) == 4:
            p[0] = ast.List(p[2])

    def p_object(self, p):
        """
        object : LBRACE RBRACE
               | LBRACE objectarglist RBRACE
        """
        if len(p) == 3:
            p[0] = ast.Object([])
        elif len(p) == 4:
            p[0] = ast.Object(p[2])

    def p_objectarglist(self, p):
        """
        objectarglist : objectarglist COMMA objectarg
                      | objectarg
        """
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1]]

    def p_objectarg(self, p):
        """
        objectarg : objectkey COLON expression
                  | name
        """
        if len(p) == 4:
            p[0] = (p[1], p[3])
        elif len(p) == 2:
            p[0] = p[1]

    def p_objectkey(self, p):
        """
        objectkey : name
                  | string
                  | number
        """
        p[0] = p[1]

    def p_group(self, p):
        "group : LPAREN expression RPAREN"
        p[0] = p[2]

    def p_attraccess(self, p):
        "attraccess : atom PERIOD NAME"
        p[0] = ast.Attr(obj=p[1], attr=p[3])

    def p_indexing(self, p):
        "indexing : atom LBRACKET expression RBRACKET"
        p[0] = ast.Item(obj=p[1], item=p[3])

    def p_functioncall(self, p):
        """
        functioncall : atom LPAREN RPAREN
                     | atom LPAREN arglist RPAREN
        """
        if len(p) == 4:
            p[0] = ast.Func(func=p[1], args=[])
        elif len(p) == 5:
            p[0] = ast.Func(func=p[1], args=p[3])

    def p_arglist(self, p):
        """
        arglist : arglist COMMA expression
                | expression
        """
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1]]

    def p_error(self, p):
        if p:
            raise ValueError(f"Syntax error at '{p.value}'")
        else:
            raise ValueError("Syntax error at EOF")


parser = Parser()
