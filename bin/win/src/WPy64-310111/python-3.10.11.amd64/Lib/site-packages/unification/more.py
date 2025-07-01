from collections.abc import Mapping

from .core import _reify, _unify, construction_sentinel


def unifiable(cls):
    """Register standard unify and reify operations on a class.

    This uses the type and __dict__ or __slots__ attributes to define the
    nature of the term.

    >>> class A(object):
    ...     def __init__(self, a, b):
    ...         self.a = a
    ...         self.b = b
    >>> unifiable(A)
    <class 'unification.more.A'>

    >>> x = var('x')
    >>> a = A(1, 2)
    >>> b = A(1, x)

    >>> unify(a, b, {})
    {~x: 2}
    """
    _unify.add((cls, cls, Mapping), _unify_object)
    _reify.add((cls, Mapping), _reify_object)

    return cls


def _reify_object(o, s):
    """Reify a Python object with a substitution.

    >>> class Foo(object):
    ...     def __init__(self, a, b):
    ...         self.a = a
    ...         self.b = b
    ...     def __str__(self):
    ...         return "Foo(%s, %s)"%(str(self.a), str(self.b))

    >>> x = var('x')
    >>> f = Foo(1, x)
    >>> print(f)
    Foo(1, ~x)
    >>> print(reify_object(f, {x: 2}))
    Foo(1, 2)
    """
    if hasattr(o, "__slots__"):
        return _reify_object_slots(o, s)
    else:
        return _reify_object_dict(o, s)


def _reify_object_dict(o, s):
    obj = type(o).__new__(type(o))

    d = yield _reify(o.__dict__, s)

    yield construction_sentinel

    if d == o.__dict__:
        yield o
    else:
        obj.__dict__.update(d)
        yield obj


def _reify_object_slots(o, s):
    attrs = [getattr(o, attr) for attr in o.__slots__]
    new_attrs = yield _reify(attrs, s)

    yield construction_sentinel

    if attrs == new_attrs:
        yield o
    else:
        newobj = object.__new__(type(o))
        for slot, attr in zip(o.__slots__, new_attrs):
            setattr(newobj, slot, attr)

        yield newobj


def _unify_object(u, v, s):
    """Unify two Python objects.

    Unifies their type and ``__dict__`` attributes

    >>> class Foo(object):
    ...     def __init__(self, a, b):
    ...         self.a = a
    ...         self.b = b
    ...     def __str__(self):
    ...         return "Foo(%s, %s)"%(str(self.a), str(self.b))

    >>> x = var('x')
    >>> f = Foo(1, x)
    >>> g = Foo(1, 2)
    >>> unify_object(f, g, {})
    {~x: 2}
    """
    if type(u) != type(v):
        yield False
        return

    if hasattr(u, "__slots__"):
        yield _unify(
            tuple(getattr(u, slot) for slot in u.__slots__),
            tuple(getattr(v, slot) for slot in v.__slots__),
            s,
        )
    else:
        yield _unify(u.__dict__, v.__dict__, s)
