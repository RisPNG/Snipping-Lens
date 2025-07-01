import inspect
import reprlib
import warnings
from collections import deque
from collections.abc import Generator, Sequence
from typing import Callable

from multipledispatch import dispatch

etuple_repr = reprlib.Repr()
etuple_repr.maxstring = 100
etuple_repr.maxother = 100


class IgnoredGenerator:
    __slots__ = ("gen",)

    def __init__(self, gen):
        self.gen = gen


def trampoline_eval(z, res_filter=None):
    """Evaluate a stream of generators.

    This implementation consists of a deque that simulates an evaluation stack
    of generator-produced operations.  We're able to overcome `RecursionError`s
    this way.
    """

    if not isinstance(z, Generator):  # pragma: no cover
        return z
    elif isinstance(z, IgnoredGenerator):
        return z.gen

    stack = deque()
    z_args, z_out = None, None
    stack.append(z)

    while stack:
        z = stack[-1]
        try:
            z_out = z.send(z_args)

            if res_filter:  # pragma: no cover
                _ = res_filter(z, z_out)

            if isinstance(z_out, Generator):
                stack.append(z_out)
                z_args = None
            else:
                z_args = z_out

        except StopIteration:
            _ = stack.pop()

    if isinstance(z_out, IgnoredGenerator):
        return z_out.gen
    else:
        return z_out


class InvalidExpression(Exception):
    """An exception indicating that an `ExpressionTuple` is not a valid [S-]expression.

    This exception is raised when an attempt is made to evaluate an
    `ExpressionTuple` that does not have a valid operator (e.g. not a
    `callable`).

    """


class KwdPair(object):
    """A class used to indicate a keyword + value mapping.

    TODO: Could subclass `ast.keyword`.

    """

    __slots__ = ("arg", "value")

    def __init__(self, arg, value):
        assert isinstance(arg, str)
        self.arg = arg
        self.value = value

    def _eval_step(self):
        if isinstance(self.value, (ExpressionTuple, KwdPair)):
            value = yield self.value._eval_step()
        else:
            value = self.value

        yield KwdPair(self.arg, value)

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.arg)}, {repr(self.value)})"

    def __str__(self):
        return f"{self.arg}={self.value}"

    def _repr_pretty_(self, p, cycle):
        p.text(str(self))

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.arg == other.arg
            and self.value == other.value
        )

    def __hash__(self):
        return hash((type(self), self.arg, self.value))


class ExpressionTuple(Sequence):
    """A tuple-like object that represents an expression.

    This object caches the return value resulting from evaluation of the
    expression it represents.  Likewise, it holds onto the "parent" expression
    from which it was derived (e.g. as a slice), if any, so that it can
    preserve the return value through limited forms of concatenation/cons-ing
    that would reproduce the parent expression.

    TODO: Should probably use weakrefs for that.
    """

    __slots__ = ("_evaled_obj", "_tuple", "_parent")
    null = object()

    def __new__(cls, seq=None, **kwargs):

        # XXX: This doesn't actually remove the entry from the kwargs
        # passed to __init__!
        # It does, however, remove it for the check below.
        kwargs.pop("evaled_obj", None)

        if seq is not None and not kwargs and type(seq) == cls:
            return seq

        res = super().__new__(cls)

        return res

    def __init__(self, seq=None, **kwargs):
        """Create an expression tuple.

        If the keyword 'evaled_obj' is given, the `ExpressionTuple`'s
        evaluated object is set to the corresponding value.
        XXX: There is no verification/check that the arguments evaluate to the
        user-specified 'evaled_obj', so be careful.
        """

        _evaled_obj = kwargs.pop("evaled_obj", self.null)
        etuple_kwargs = tuple(KwdPair(k, v) for k, v in kwargs.items())

        if seq:
            self._tuple = tuple(seq) + etuple_kwargs
        else:
            self._tuple = etuple_kwargs

        # TODO: Consider making these a weakrefs.
        self._evaled_obj = _evaled_obj
        self._parent = None

    @property
    def evaled_obj(self):
        """Return the evaluation of this expression tuple."""
        res = self._eval_step()
        return trampoline_eval(res)

    @evaled_obj.setter
    def evaled_obj(self, obj):
        raise ValueError("Value of evaluated expression cannot be set!")

    @property
    def eval_obj(self):
        warnings.warn(
            "`eval_obj` is deprecated; use `evaled_obj`.",
            DeprecationWarning,
            stacklevel=2,
        )
        return trampoline_eval(self._eval_step())

    def _eval_apply_fn(self, op: Callable) -> Callable:
        """Return the callable used to evaluate the expression tuple.

        The expression tuple's operator can be any `Callable`, i.e. either
        a function or an instance of a class that defines `__call__`. In
        the latter case, one can evalute the expression tuple using a
        method other than `__call__` by overloading this method.

        """
        return op

    def _eval_step(self):
        if len(self._tuple) == 0:
            raise InvalidExpression("Empty expression.")

        if self._evaled_obj is not self.null:
            yield self._evaled_obj
        else:
            op = self._tuple[0]

            if isinstance(op, (ExpressionTuple, KwdPair)):
                op = yield op._eval_step()

            if not callable(op):
                raise InvalidExpression(
                    "ExpressionTuple does not have a callable operator."
                )

            evaled_args = []
            evaled_kwargs = []
            for i in self._tuple[1:]:
                if isinstance(i, (ExpressionTuple, KwdPair)):
                    i = yield i._eval_step()

                if isinstance(i, KwdPair):
                    evaled_kwargs.append(i)
                else:
                    evaled_args.append(i)

            try:
                op_sig = inspect.signature(self._eval_apply_fn(op))
            except ValueError:
                # This handles some builtin function types
                _evaled_obj = op(*(evaled_args + [kw.value for kw in evaled_kwargs]))
            else:
                op_args = op_sig.bind(
                    *evaled_args, **{kw.arg: kw.value for kw in evaled_kwargs}
                )
                op_args.apply_defaults()

                _evaled_obj = self._eval_apply_fn(op)(*op_args.args, **op_args.kwargs)

            if isinstance(_evaled_obj, Generator):
                self._evaled_obj = _evaled_obj
                yield IgnoredGenerator(_evaled_obj)
            else:
                self._evaled_obj = _evaled_obj
                yield self._evaled_obj

    def __add__(self, x):
        res = self._tuple + x
        if self._parent is not None and res == self._parent._tuple:
            return self._parent
        return type(self)(res)

    def __contains__(self, *args):
        return self._tuple.__contains__(*args)

    def __ge__(self, *args):
        return self._tuple.__ge__(*args)

    def __getitem__(self, key):
        tuple_res = self._tuple[key]
        if isinstance(key, slice) and isinstance(tuple_res, tuple):
            tuple_res = type(self)(tuple_res)
            tuple_res._parent = self
        return tuple_res

    def __gt__(self, *args):
        return self._tuple.__gt__(*args)

    def __iter__(self, *args):
        return self._tuple.__iter__(*args)

    def __le__(self, *args):
        return self._tuple.__le__(*args)

    def __len__(self, *args):
        return self._tuple.__len__(*args)

    def __lt__(self, *args):
        return self._tuple.__lt__(*args)

    def __mul__(self, *args):
        return type(self)(self._tuple.__mul__(*args))

    def __rmul__(self, *args):
        return type(self)(self._tuple.__rmul__(*args))

    def __radd__(self, x):
        res = x + self._tuple  # type(self)(x + self._tuple)
        if self._parent is not None and res == self._parent._tuple:
            return self._parent
        return type(self)(res)

    def __str__(self):
        return f"e({', '.join(tuple(str(i) for i in self._tuple))})"

    def __repr__(self):
        return f"ExpressionTuple({etuple_repr.repr(self._tuple)})"

    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text("e(...)")  # pragma: no cover
        else:
            with p.group(2, "e(", ")"):
                p.breakable(sep="")
                for idx, item in enumerate(self._tuple):
                    if idx:
                        p.text(",")
                        p.breakable()
                    p.pretty(item)

    def __eq__(self, other):

        # Built-in `==` won't work in CPython for deeply nested structures.

        # TODO: We could track the level of `ExpressionTuple`-only nesting and
        # apply TCO only when it reaches a certain level.

        if not isinstance(other, Sequence):
            return NotImplemented

        if len(other) != len(self):
            return False

        queue = deque(zip(self._tuple, other))

        while queue:
            i_s, i_o = queue.pop()

            if (
                isinstance(i_s, Sequence)
                and isinstance(i_o, Sequence)
                and (
                    isinstance(i_s, ExpressionTuple) or isinstance(i_o, ExpressionTuple)
                )
            ):
                queue.extend(zip(i_s, i_o))
            elif i_s != i_o:
                return False

        return True

    def __hash__(self):
        # XXX: CPython fails for deeply nested tuples!
        return hash(self._tuple)


@dispatch([object])
def etuple(*args, **kwargs):
    """Create an ExpressionTuple from the argument list.

    In other words:
        etuple(1, 2, 3) == ExpressionTuple((1, 2, 3))

    """
    return ExpressionTuple(args, **kwargs)
