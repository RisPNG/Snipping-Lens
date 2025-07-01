from .utils import ignoring
from .encode import Encode
from functools import partial

__all__ = []


def bytes_concat(L):
    return b''.join(L)


with ignoring(ImportError, AttributeError):
    # In case snappy is not installed, or another package called snappy that does not implement compress / decompress.
    # For example, SnapPy (https://pypi.org/project/snappy/)
    import snappy
    Snappy = partial(Encode,
                     snappy.compress,
                     snappy.decompress,
                     bytes_concat)
    __all__.append('Snappy')


with ignoring(ImportError):
    import zlib
    ZLib = partial(Encode,
                   zlib.compress,
                   zlib.decompress,
                   bytes_concat)
    __all__.append('ZLib')


with ignoring(ImportError):
    import bz2
    BZ2 = partial(Encode,
                  bz2.compress,
                  bz2.decompress,
                  bytes_concat)
    __all__.append('BZ2')


with ignoring(ImportError):
    import blosc
    Blosc = partial(Encode,
                    blosc.compress,
                    blosc.decompress,
                    bytes_concat)
    __all__.append('Blosc')
