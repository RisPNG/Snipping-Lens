from __future__ import annotations

from collections.abc import Iterable, Mapping
from itertools import chain
from typing import MutableMapping  # TODO move to collections.abc (needs Python >=3.9)
from typing import Any, TypeVar, overload

T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")


class ZictBase(MutableMapping[KT, VT]):
    """Base class for zict mappings"""

    # TODO use positional-only arguments to protect self (requires Python 3.8+)
    @overload
    def update(self, __m: Mapping[KT, VT], **kwargs: VT) -> None:
        ...

    @overload
    def update(self, __m: Iterable[tuple[KT, VT]], **kwargs: VT) -> None:
        ...

    @overload
    def update(self, **kwargs: VT) -> None:
        ...

    def update(*args, **kwds):
        # Boilerplate for implementing an update() method
        if not args:
            raise TypeError(
                "descriptor 'update' of MutableMapping object " "needs an argument"
            )
        self = args[0]
        args = args[1:]
        if len(args) > 1:
            raise TypeError("update expected at most 1 arguments, got %d" % len(args))
        items = []
        if args:
            other = args[0]
            if isinstance(other, Mapping) or hasattr(other, "items"):
                items = other.items()
            else:
                # Assuming (key, value) pairs
                items = other
        if kwds:
            items = chain(items, kwds.items())
        self._do_update(items)

    def _do_update(self, items: Iterable[tuple[KT, VT]]) -> None:
        # Default implementation, can be overriden for speed
        for k, v in items:
            self[k] = v

    def close(self) -> None:
        """Release any system resources held by this object"""

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, *args) -> None:
        self.close()


def close(*z: Any) -> None:
    """Close *z* if possible."""
    for zi in z:
        if hasattr(zi, "close"):
            zi.close()


def flush(*z: Any) -> None:
    """Flush *z* if possible."""
    for zi in z:
        if hasattr(zi, "flush"):
            zi.flush()
