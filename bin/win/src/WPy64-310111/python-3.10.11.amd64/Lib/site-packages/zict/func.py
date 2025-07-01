from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, KeysView, MutableMapping
from typing import Generic, TypeVar

from zict.common import KT, VT, ZictBase, close, flush

WT = TypeVar("WT")


class Func(ZictBase[KT, VT], Generic[KT, VT, WT]):
    """Buffer a MutableMapping with a pair of input/output functions

    Parameters
    ----------
    dump: callable
        Function to call on value as we set it into the mapping
    load: callable
        Function to call on value as we pull it from the mapping
    d: MutableMapping

    Examples
    --------
    >>> def double(x):
    ...     return x * 2

    >>> def halve(x):
    ...     return x / 2

    >>> d = dict()
    >>> f = Func(double, halve, d)
    >>> f['x'] = 10
    >>> d
    {'x': 20}
    >>> f['x']
    10.0
    """

    dump: Callable[[VT], WT]
    load: Callable[[WT], VT]
    d: MutableMapping[KT, WT]

    def __init__(
        self,
        dump: Callable[[VT], WT],
        load: Callable[[WT], VT],
        d: MutableMapping[KT, WT],
    ):
        # FIXME https://github.com/python/mypy/issues/708
        self.dump = dump  # type: ignore
        self.load = load  # type: ignore
        self.d = d

    def __getitem__(self, key: KT) -> VT:
        return self.load(self.d[key])  # type: ignore

    def __setitem__(self, key: KT, value: VT) -> None:
        self.d[key] = self.dump(value)  # type: ignore

    def __contains__(self, key: object) -> bool:
        return key in self.d

    def __delitem__(self, key: KT) -> None:
        del self.d[key]

    def keys(self) -> KeysView[KT]:
        return self.d.keys()

    # FIXME dictionary views https://github.com/dask/zict/issues/61
    def values(self) -> Iterator[VT]:  # type: ignore
        return (self.load(v) for v in self.d.values())  # type: ignore

    def items(self) -> Iterator[tuple[KT, VT]]:  # type: ignore
        return ((k, self.load(v)) for k, v in self.d.items())  # type: ignore

    def _do_update(self, items: Iterable[tuple[KT, VT]]) -> None:
        it = ((k, self.dump(v)) for k, v in items)  # type: ignore
        self.d.update(it)

    def __iter__(self) -> Iterator[KT]:
        return iter(self.d)

    def __len__(self) -> int:
        return len(self.d)

    def __str__(self) -> str:
        return f"<Func: {funcname(self.dump)}<->{funcname(self.load)} {self.d}>"

    __repr__ = __str__

    def flush(self) -> None:
        flush(self.d)

    def close(self) -> None:
        close(self.d)


def funcname(func) -> str:
    """Get the name of a function."""
    while hasattr(func, "func"):
        func = func.func
    try:
        return func.__name__
    except Exception:
        return str(func)
