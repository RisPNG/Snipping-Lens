"""Abstract syntax tree for parser"""
from dataclasses import dataclass
import typing


class Node:
    pass


@dataclass
class Expr(Node):
    value: Node


@dataclass
class BinOp(Node):
    op: str
    lhs: Expr
    rhs: Expr


@dataclass
class UnOp(Node):
    op: str
    rhs: Expr


@dataclass
class TernOp(Node):
    op: typing.Tuple[str, str]
    lhs: Expr
    mid: Expr
    rhs: Expr


@dataclass
class Number(Node):
    value: float


@dataclass
class String(Node):
    value: str


@dataclass
class Regex(Node):
    value: typing.Dict[str, str]


@dataclass
class Global(Node):
    name: str


@dataclass
class Name(Node):
    name: str


@dataclass
class List(Node):
    entries: typing.List[Expr]


@dataclass
class Object(Node):
    entries: typing.List[typing.Union[Name, typing.Tuple[Expr, Expr]]]


@dataclass
class Attr(Node):
    obj: Expr
    attr: Name


@dataclass
class Item(Node):
    obj: Expr
    item: Expr


@dataclass
class Func(Node):
    func: Expr
    args: typing.List[Expr]
