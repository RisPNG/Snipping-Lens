from abc import ABC, ABCMeta, abstractmethod
from collections import OrderedDict, UserString
from collections.abc import ByteString, ItemsView, Iterator, Mapping, Sequence
from functools import reduce
from itertools import chain, islice
from operator import length_hint

from multipledispatch import dispatch

# This is the constructor/type used for `ConsNull` value `None`.
default_ConsNull = list


class ConsError(ValueError):
    pass


class ConsType(ABCMeta):
    def __instancecheck__(self, o):
        return issubclass(type(o), (ConsPair, MaybeCons)) and length_hint(o, 0) > 0


class ConsNullType(ABCMeta):
    def __instancecheck__(self, o):
        if o is None:
            return True
        elif issubclass(type(o), MaybeCons):
            lhint = length_hint(o, -1)
            if lhint == 0:
                return True
            elif lhint > 0:
                return False
            else:
                return None
        else:
            return False


class ConsNull(metaclass=ConsNullType):
    """A class used to indicate a Lisp/cons-like null.

    A "Lisp-like" null object is one that can be used as a `cdr` to produce a
    non-`ConsPair` collection (e.g. `None`, `[]`, `()`, `OrderedDict`, etc.)

    It's important that this function be used when considering an arbitrary
    object as the terminating `cdr` for a given collection (e.g. when unifying
    `cons` objects); otherwise, fixed choices for the terminating `cdr`, such
    as `None` or `[]`, will severely limit the applicability of the
    decomposition.

    Also, for relevant collections with no concrete length information, `None`
    is returned, and it signifies the uncertainty of the negative assertion.
    """

    @abstractmethod
    def __init__(self):
        raise NotImplementedError()


class ConsPair(metaclass=ConsType):
    """An object representing cons pairs.

    These objects, and the class constructor alias `cons`, serve as a sort of
    generalized delayed append operation for various collection types.  When
    used with the built-in Python collection types, `cons` behaves like the
    concatenate operator between the given types, if any.

    A Python `list` is returned when the cdr is a `list` or `None`; otherwise,
    a `ConsPair` is returned.

    The arguments to `ConsPair` can be a car & cdr pair, or a sequence of
    objects to be nested in `cons`es, e.g.

        ConsPair(car_1, car_2, car_3, cdr) ==
            ConsPair(car_1, ConsPair(car_2, ConsPair(car_3, cdr)))
    """

    __slots__ = ["car", "cdr"]

    def __new__(cls, *parts):
        if len(parts) > 2:
            res = reduce(lambda x, y: ConsPair(y, x), reversed(parts))
        elif len(parts) == 2:
            car_part, cdr_part = parts

            if isinstance(cdr_part, (ConsNull, ConsPair, Iterator)) and not issubclass(
                type(cdr_part), ConsPair
            ):
                res = cls.cons_merge(car_part, cdr_part)
            else:
                instance = super(ConsPair, cls).__new__(cls)
                instance.car = car_part
                instance.cdr = cdr_part
                res = instance

        else:
            raise ValueError("Number of arguments must be greater than 2.")

        return res

    @classmethod
    def cons_merge(cls, car_part, cdr_part):

        if cdr_part is None:
            cdr_part = default_ConsNull()

        if isinstance(cdr_part, Mapping):
            cdr_part = cdr_part.items()

        if isinstance(cdr_part, ItemsView):

            return OrderedDict(chain((car_part,), cdr_part))

        elif hasattr(cdr_part, "__add__") or hasattr(cdr_part, "__radd__"):
            # TODO: What about adding `list.extend`?  We're already
            # constructing an instance of the CDR type.
            return type(cdr_part)((car_part,)) + cdr_part

        return chain((car_part,), cdr_part)

    def __hash__(self):
        return hash((self.car, self.cdr))

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.car == other.car
            and self.cdr == other.cdr
        )

    def __repr__(self):
        return "{}({}, {})".format(
            self.__class__.__name__, repr(self.car), repr(self.cdr)
        )

    def __str__(self):
        return "({} . {})".format(self.car, self.cdr)


cons = ConsPair


class MaybeConsType(ABCMeta):
    def __subclasscheck__(self, o):

        if issubclass(o, tuple(_cdr.funcs.keys())) and not issubclass(o, NonCons):
            return True

        return False


class MaybeCons(metaclass=MaybeConsType):
    """A class used to dynamically determine potential cons types from non-ConsPairs.

    For example,

        issubclass(tuple, MaybeCons) is True
        issubclass(ConsPair, MaybeCons) is False

    The potential cons types are drawn from the implemented `cdr` dispatch
    functions.

    """  # noqa: E501

    @abstractmethod
    def __init__(self):
        raise NotImplementedError()


class ProperSequenceType(MaybeConsType):
    """An abstract type that can be used as an instance check for proper sequences.

    A proper sequence is a sequence according to `cons` but not a `ConsPair`.
    """

    def __instancecheck__(self, o):
        return issubclass(type(o), MaybeCons)


class ProperSequence(metaclass=ProperSequenceType):
    """A sequence according to `cons` but not a `ConsPair`."""

    @abstractmethod
    def __init__(self):
        raise NotImplementedError()


class NonCons(ABC):
    """A class (and its subclasses) that is *not* considered a cons.

    This type/class can be used as a means of excluding certain types from
    consideration as a cons pair (i.e. via `NotCons.register`).
    """

    @abstractmethod
    def __init__(self):
        raise NotImplementedError()


for t in (type(None), str, set, UserString, ByteString):
    NonCons.register(t)


def car(z):
    if issubclass(type(z), ConsPair):
        return z.car

    try:
        return _car(z)
    except NotImplementedError:
        raise ConsError("Not a cons pair")


@dispatch(Sequence)
def _car(z):
    try:
        return next(iter(z))
    except StopIteration:
        raise ConsError("Not a cons pair")


@_car.register(Iterator)
def _car_Iterator(z):
    """Return the first element in the given iterator.

    Warning: `car` necessarily draws from the iterator, and we can't do
    much--within this function--to make copies (e.g. with `tee`) that will
    appropriately replace the original iterator.
    Callers must handle this themselves.
    """
    try:
        # z, _ = tee(z)
        return next(iter(z))
    except StopIteration:
        raise ConsError("Not a cons pair")


@_car.register(OrderedDict)
def _car_OrderedDict(z):
    if len(z) == 0:
        raise ConsError("Not a cons pair")

    return next(iter(z.items()))


@_car.register(NonCons)
def _car_NonCons(z):
    raise ConsError(f"{z} is a NonCons type")


def cdr(z):
    if issubclass(type(z), ConsPair):
        return z.cdr

    try:
        return _cdr(z)
    except NotImplementedError:
        raise ConsError("Not a cons pair")


@dispatch(Sequence)
def _cdr(z):
    if len(z) == 0:
        raise ConsError("Not a cons pair")
    return z[1:]


@_cdr.register(Iterator)
def _cdr_Iterator(z):
    if length_hint(z, 1) == 0:
        raise ConsError("Not a cons pair")

    if isinstance(z, Iterator) and length_hint(z, 2) <= 1:
        return iter([])

    return islice(z, 1, None)


@_cdr.register(OrderedDict)
def _cdr_OrderedDict(z):
    if len(z) == 0:
        raise ConsError("Not a cons pair")
    return cdr(list(z.items()))


@_cdr.register(NonCons)
def _cdr_NonCons(z):
    raise ConsError(f"{z} is a NonCons type")
