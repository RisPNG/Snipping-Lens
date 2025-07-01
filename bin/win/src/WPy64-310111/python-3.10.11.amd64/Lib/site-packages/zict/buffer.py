from __future__ import annotations

from collections.abc import Callable, Iterator, MutableMapping
from itertools import chain

from zict.common import KT, VT, ZictBase, close, flush
from zict.lru import LRU


class Buffer(ZictBase[KT, VT]):
    """Buffer one dictionary on top of another

    This creates a MutableMapping by combining two MutableMappings, one that
    feeds into the other when it overflows, based on an LRU mechanism.  When
    the first evicts elements these get placed into the second. When an item
    is retrieved from the second it is placed back into the first.

    Parameters
    ----------
    fast: MutableMapping
    slow: MutableMapping
    n: float
        Total size of fast that triggers evictions to slow
    weight: f(k, v) -> float, optional
        Weight of each key/value pair (default: 1)
    fast_to_slow_callbacks: list of callables
        These functions run every time data moves from the fast to the slow
        mapping.  They take two arguments, a key and a value
        If an exception occurs during a fast_to_slow_callbacks (e.g a callback tried
        storing to disk and raised a disk full error) the key will remain in the LRU.
    slow_to_fast_callbacks: list of callables
        These functions run every time data moves form the slow to the fast
        mapping.

    Examples
    --------
    >>> fast = dict()
    >>> slow = Func(dumps, loads, File('storage/'))  # doctest: +SKIP
    >>> def weight(k, v):
    ...     return sys.getsizeof(v)
    >>> buff = Buffer(fast, slow, 1e8, weight=weight)  # doctest: +SKIP

    See Also
    --------
    LRU
    """

    fast: LRU[KT, VT]
    slow: MutableMapping[KT, VT]
    n: float
    weight: Callable[[KT, VT], float]
    fast_to_slow_callbacks: list[Callable[[KT, VT], None]]
    slow_to_fast_callbacks: list[Callable[[KT, VT], None]]

    def __init__(
        self,
        fast: MutableMapping[KT, VT],
        slow: MutableMapping[KT, VT],
        n: float,
        weight: Callable[[KT, VT], float] = lambda k, v: 1,
        fast_to_slow_callbacks: Callable[[KT, VT], None]
        | list[Callable[[KT, VT], None]]
        | None = None,
        slow_to_fast_callbacks: Callable[[KT, VT], None]
        | list[Callable[[KT, VT], None]]
        | None = None,
    ):
        self.fast = LRU(n, fast, weight=weight, on_evict=[self.fast_to_slow])
        self.slow = slow
        self.n = n
        # FIXME https://github.com/python/mypy/issues/708
        self.weight = weight  # type: ignore
        if callable(fast_to_slow_callbacks):
            fast_to_slow_callbacks = [fast_to_slow_callbacks]
        if callable(slow_to_fast_callbacks):
            slow_to_fast_callbacks = [slow_to_fast_callbacks]
        self.fast_to_slow_callbacks = fast_to_slow_callbacks or []
        self.slow_to_fast_callbacks = slow_to_fast_callbacks or []

    def fast_to_slow(self, key: KT, value: VT) -> None:
        self.slow[key] = value
        try:
            for cb in self.fast_to_slow_callbacks:
                cb(key, value)
        # LRU catches exception, raises and makes sure keys are not lost and located in
        # fast.
        except Exception:
            del self.slow[key]
            raise

    def slow_to_fast(self, key: KT) -> VT:
        value = self.slow[key]
        # Avoid useless movement for heavy values
        w = self.weight(key, value)  # type: ignore
        if w <= self.n:
            del self.slow[key]
            self.fast[key] = value
        for cb in self.slow_to_fast_callbacks:
            cb(key, value)
        return value

    def __getitem__(self, key: KT) -> VT:
        if key in self.fast:
            return self.fast[key]
        elif key in self.slow:
            return self.slow_to_fast(key)
        else:
            raise KeyError(key)

    def __setitem__(self, key: KT, value: VT) -> None:
        if key in self.slow:
            del self.slow[key]
        # This may trigger an eviction from fast to slow of older keys.
        # If the weight is individually greater than n, then key/value will be stored
        # into self.slow instead (see LRU.__setitem__).
        self.fast[key] = value

    def __delitem__(self, key: KT) -> None:
        if key in self.fast:
            del self.fast[key]
        elif key in self.slow:
            del self.slow[key]
        else:
            raise KeyError(key)

    # FIXME dictionary views https://github.com/dask/zict/issues/61
    def keys(self) -> Iterator[KT]:  # type: ignore
        return chain(self.fast.keys(), self.slow.keys())

    def values(self) -> Iterator[VT]:  # type: ignore
        return chain(self.fast.values(), self.slow.values())

    def items(self) -> Iterator[tuple[KT, VT]]:  # type: ignore
        return chain(self.fast.items(), self.slow.items())

    def __len__(self) -> int:
        return len(self.fast) + len(self.slow)

    def __iter__(self) -> Iterator[KT]:
        return chain(iter(self.fast), iter(self.slow))

    def __contains__(self, key: object) -> bool:
        return key in self.fast or key in self.slow

    def __str__(self) -> str:
        return f"Buffer<{self.fast}, {self.slow}>"

    __repr__ = __str__

    def flush(self) -> None:
        flush(self.fast, self.slow)

    def close(self) -> None:
        close(self.fast, self.slow)
