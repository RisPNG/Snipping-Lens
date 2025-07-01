from __future__ import annotations

import weakref
from collections.abc import Iterator, KeysView, MutableMapping
from typing import TYPE_CHECKING

from zict.common import KT, VT, ZictBase, close, flush


class Cache(ZictBase[KT, VT]):
    """Transparent write-through cache around a MutableMapping with an expensive
    __getitem__ method.

    Parameters
    ----------
    data: MutableMapping
        Persistent, slow to read mapping to be cached
    cache: MutableMapping
        Fast cache for reads from data. This mapping may lose keys on its own; e.g. it
        could be a LRU.
    update_on_set: bool, optional
        If True (default), the cache will be updated both when writing and reading.
        If False, update the cache when reading, but just invalidate it when writing.

    Examples
    --------
    Keep the latest 100 accessed values in memory
    >>> from zict import File, LRU
    >>> d = Cache(File('myfile'), LRU(100, {}))  # doctest: +SKIP

    Read data from disk every time, unless it was previously accessed and it's still in
    use somewhere else in the application
    >>> d = Cache(File('myfile'), WeakValueMapping())  # doctest: +SKIP
    """

    data: MutableMapping[KT, VT]
    cache: MutableMapping[KT, VT]
    update_on_set: bool

    def __init__(
        self,
        data: MutableMapping[KT, VT],
        cache: MutableMapping[KT, VT],
        update_on_set: bool = True,
    ):
        self.data = data
        self.cache = cache
        self.update_on_set = update_on_set

    def __getitem__(self, key: KT) -> VT:
        try:
            return self.cache[key]
        except KeyError:
            pass
        value = self.data[key]
        self.cache[key] = value
        return value

    def __setitem__(self, key: KT, value: VT) -> None:
        # If the item was already in cache and data.__setitem__ fails, e.g. because it's
        # a File and the disk is full, make sure that the cache is invalidated.
        # FIXME https://github.com/python/mypy/issues/10152
        self.cache.pop(key, None)  # type: ignore

        self.data[key] = value
        if self.update_on_set:
            self.cache[key] = value

    def __delitem__(self, key: KT) -> None:
        self.cache.pop(key, None)  # type: ignore
        del self.data[key]

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> Iterator[KT]:
        return iter(self.data)

    def __contains__(self, key: object) -> bool:
        # Do not let MutableMapping call self.data[key]
        return key in self.data

    def keys(self) -> KeysView[KT]:
        # Return a potentially optimized set-like, instead of letting MutableMapping
        # build it from __iter__ on the fly
        return self.data.keys()

    def flush(self) -> None:
        flush(self.cache, self.data)

    def close(self) -> None:
        close(self.cache, self.data)


if TYPE_CHECKING:
    # TODO Python 3.9: remove this branch and just use [] in the implementation below
    class WeakValueMapping(weakref.WeakValueDictionary[KT, VT]):
        ...

else:

    class WeakValueMapping(weakref.WeakValueDictionary):
        """Variant of weakref.WeakValueDictionary which silently ignores objects that
        can't be referenced by a weakref.ref
        """

        def __setitem__(self, key: KT, value: VT) -> None:
            try:
                super().__setitem__(key, value)
            except TypeError:
                pass
