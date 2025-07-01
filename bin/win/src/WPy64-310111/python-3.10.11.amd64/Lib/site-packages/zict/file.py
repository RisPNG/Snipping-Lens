from __future__ import annotations

import mmap
import os
from collections.abc import Iterator
from urllib.parse import quote, unquote

from zict.common import ZictBase


def _safe_key(key: str) -> str:
    """
    Escape key so as to be usable on all filesystems.
    """
    # Even directory separators are unsafe.
    return quote(key, safe="")


def _unsafe_key(key: str) -> str:
    """
    Undo the escaping done by _safe_key().
    """
    return unquote(key)


class File(ZictBase[str, bytes]):
    """Mutable Mapping interface to a directory

    Keys must be strings, values must be bytes

    Note this shouldn't be used for interprocess persistence, as keys
    are cached in memory.

    Parameters
    ----------
    directory: string
    mode: string, ('r', 'w', 'a'), defaults to 'a'

    Examples
    --------
    >>> z = File('myfile')  # doctest: +SKIP
    >>> z['x'] = b'123'  # doctest: +SKIP
    >>> z['x']  # doctest: +SKIP
    b'123'

    Also supports writing lists of bytes objects

    >>> z['y'] = [b'123', b'4567']  # doctest: +SKIP
    >>> z['y']  # doctest: +SKIP
    b'1234567'

    Or anything that can be used with file.write, like a memoryview

    >>> z['data'] = np.ones(5).data  # doctest: +SKIP
    """

    directory: str
    mode: str
    memmap: bool
    _keys: set[str]

    def __init__(self, directory: str, mode: str = "a", memmap: bool = False):
        self.directory = directory
        self.mode = mode
        self.memmap = memmap
        self._keys = set()
        if not os.path.exists(self.directory):
            os.makedirs(self.directory, exist_ok=True)
        else:
            for n in os.listdir(self.directory):
                self._keys.add(_unsafe_key(n))

    def __str__(self) -> str:
        return f'<File: {self.directory}, mode="{self.mode}", {len(self)} elements>'

    __repr__ = __str__

    def __getitem__(self, key: str) -> bytes:
        if key not in self._keys:
            raise KeyError(key)
        fn = os.path.join(self.directory, _safe_key(key))
        with open(fn, "rb") as fh:
            if self.memmap:
                return memoryview(mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ))
            else:
                return fh.read()

    def __setitem__(
        self,
        key: str,
        value: bytes
        | bytearray
        | list[bytes]
        | list[bytearray]
        | tuple[bytes]
        | tuple[bytearray],
    ) -> None:
        fn = os.path.join(self.directory, _safe_key(key))
        with open(fn, "wb") as fh:
            if isinstance(value, (tuple, list)):
                fh.writelines(value)
            else:
                fh.write(value)
        self._keys.add(key)

    def __contains__(self, key: object) -> bool:
        return key in self._keys

    # FIXME dictionary views https://github.com/dask/zict/issues/61
    def keys(self) -> set[str]:  # type: ignore
        return self._keys

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys)

    def __delitem__(self, key: str) -> None:
        if key not in self._keys:
            raise KeyError(key)
        os.remove(os.path.join(self.directory, _safe_key(key)))
        self._keys.remove(key)

    def __len__(self) -> int:
        return len(self._keys)
