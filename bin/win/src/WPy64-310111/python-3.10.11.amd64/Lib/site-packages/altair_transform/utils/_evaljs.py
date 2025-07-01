"""Functionality to evaluate contents of the ast"""
from functools import singledispatch, wraps
import operator
import re
from typing import Any, Dict, List, Union

from altair_transform.utils import ast, Parser

__all__ = ["evaljs", "undefined", "JSRegex"]


class _UndefinedType(object):
    def __repr__(self):
        return "undefined"


undefined = _UndefinedType()


class JSRegex:
    _flagmap: Dict[str, re.RegexFlag] = {
        "i": re.I,
        "m": re.M,
        "s": re.S,
        "u": re.U,
    }

    def __init__(self, pattern: str, flags: str = ""):
        self._pattern = pattern
        self._flags = flags
        self._regex = re.compile(pattern, self._reflags())

    def __eq__(self, other):
        if isinstance(other, JSRegex):
            return (self._pattern, self._flags) == (other._pattern, other._flags)

    def _reflags(self) -> re.RegexFlag:
        flags = re.RegexFlag(0)
        for key, flag in self._flagmap.items():
            if key in self._flags:
                flags |= flag
        return flags

    def test(self, string: str) -> bool:
        if "y" in self._flags:
            return bool(self._regex.match(string))
        else:
            return bool(self._regex.search(string))

    def replace(self, string: str, replacement: str) -> str:
        if "g" in self._flags:
            return self._regex.sub(replacement, string)
        else:
            return self._regex.sub(replacement, string, count=1)


def evaljs(expression: Union[str, ast.Expr], namespace: dict = None) -> Any:
    """Evaluate a javascript expression, optionally with a namespace."""
    if isinstance(expression, str):
        parser = Parser()
        expression = parser.parse(expression)
    return visit(expression, namespace or {})


@singledispatch
def visit(obj: Any, namespace: dict) -> Any:
    return obj


@visit.register(ast.Expr)
def _visit_expr(obj: ast.Expr, namespace: dict) -> Any:
    return obj.value


@visit.register(ast.BinOp)
def _visit_binop(obj: ast.BinOp, namespace: dict) -> Any:
    if obj.op not in BINARY_OPERATORS:
        raise NotImplementedError(f"Binary Operator A {obj.op} B")
    op = BINARY_OPERATORS[obj.op]
    return op(visit(obj.lhs, namespace), visit(obj.rhs, namespace))


@visit.register(ast.UnOp)
def _visit_unop(obj: ast.UnOp, namespace: dict) -> Any:
    if obj.op not in UNARY_OPERATORS:
        raise NotImplementedError(f"Unary Operator {obj.op}x")
    op = UNARY_OPERATORS[obj.op]
    return op(visit(obj.rhs, namespace))


@visit.register(ast.TernOp)
def _visit_ternop(obj: ast.TernOp, namespace: dict) -> Any:
    if obj.op not in TERNARY_OPERATORS:
        raise NotImplementedError(f"Ternary Operator A {obj.op[0]} B {obj.op[1]} C")
    op = TERNARY_OPERATORS[obj.op]
    return op(
        visit(obj.lhs, namespace), visit(obj.mid, namespace), visit(obj.rhs, namespace)
    )


@visit.register(ast.Number)
def _visit_number(obj: ast.Number, namespace: dict) -> Any:
    return obj.value


@visit.register(ast.String)
def _visit_string(obj: ast.String, namespace: dict) -> Any:
    return obj.value


@visit.register(ast.Regex)
def _visit_regex(obj: ast.Regex, namespace: dict) -> JSRegex:
    return JSRegex(obj.value["pattern"], obj.value["flags"])


@visit.register(ast.Global)
def _visit_global(obj: ast.Global, namespace: dict) -> Any:
    if obj.name not in namespace:
        raise NameError("{0} is not a valid name".format(obj.name))
    return namespace[obj.name]


@visit.register(ast.Name)
def _visit_name(obj: ast.Name, namespace: dict) -> str:
    return obj.name


@visit.register(ast.List)
def _visit_list(obj: ast.List, namespace: dict) -> List:
    return [visit(entry, namespace) for entry in obj.entries]


@visit.register(ast.Object)
def _visit_object(obj: ast.Object, namespace: dict) -> Any:
    def _visit(entry):
        if isinstance(entry, tuple):
            return tuple(visit(e, namespace) for e in entry)
        if isinstance(entry, ast.Name):
            return (visit(entry, namespace), visit(ast.Global(entry.name), namespace))

    return dict(_visit(entry) for entry in obj.entries)


@visit.register(ast.Attr)
def _visit_attr(obj: ast.Attr, namespace: dict) -> Any:
    obj_ = visit(obj.obj, namespace)
    attr = visit(obj.attr, namespace)
    if isinstance(obj_, dict):
        return obj_.get(attr, undefined)
    else:
        return getattr(obj_, attr, undefined)


@visit.register(ast.Item)
def _visit_item(obj: ast.Item, namespace: dict) -> Any:
    obj_ = visit(obj.obj, namespace)
    item = visit(obj.item, namespace)
    if isinstance(obj_, list) and isinstance(item, float):
        item = int(item)
    try:
        return obj_[item]
    except (KeyError, IndexError):
        return undefined


@visit.register(ast.Func)
def _visit_func(obj: ast.Func, namespace: dict) -> Any:
    func = visit(obj.func, namespace)
    args = [visit(arg, namespace) for arg in obj.args]
    return func(*args)


def int_inputs(func):
    @wraps(func)
    def wrapper(*args):
        return float(func(*map(int, args)))

    return wrapper


@int_inputs
def zerofill_rshift(lhs: int, rhs: int) -> int:
    if lhs < 0:
        lhs = lhs + 0x100000000
    return lhs >> rhs


# TODO: do implicit type conversions ugh...
UNARY_OPERATORS = {
    "~": int_inputs(operator.inv),
    "-": operator.neg,
    "+": operator.pos,
    "!": operator.not_,
}


BINARY_OPERATORS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "**": operator.pow,
    "%": operator.mod,
    "&": int_inputs(operator.and_),
    "|": int_inputs(operator.or_),
    "^": int_inputs(operator.xor),
    "<<": int_inputs(operator.lshift),
    ">>": int_inputs(operator.rshift),
    ">>>": zerofill_rshift,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "===": operator.eq,
    "!=": operator.ne,
    "!==": operator.ne,
    "&&": lambda a, b: a and b,
    "||": lambda a, b: a or b,
}


TERNARY_OPERATORS = {("?", ":"): lambda a, b, c: b if a else c}
