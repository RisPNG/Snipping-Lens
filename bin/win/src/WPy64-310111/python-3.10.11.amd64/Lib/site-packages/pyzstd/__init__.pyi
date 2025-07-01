import io
from enum import IntEnum
from os import PathLike
from typing import overload, Dict, ByteString, Optional, Union, Callable, \
                   Iterable, Literal, ClassVar, Tuple, NamedTuple, BinaryIO, \
                   TextIO

__version__: str
zstd_version: str
zstd_version_info: Tuple[int, int, int]
zstd_support_multithread: bool

class values(NamedTuple):
    default: int
    min: int
    max: int

compressionLevel_values: values

class Strategy(IntEnum):
    fast: int
    dfast: int
    greedy: int
    lazy: int
    lazy2: int
    btlazy2: int
    btopt: int
    btultra: int
    btultra2: int

class CParameter(IntEnum):
    compressionLevel: int
    windowLog: int
    hashLog: int
    chainLog: int
    searchLog: int
    minMatch: int
    targetLength: int
    strategy: int

    enableLongDistanceMatching: int
    ldmHashLog: int
    ldmMinMatch: int
    ldmBucketSizeLog: int
    ldmHashRateLog: int

    contentSizeFlag: int
    checksumFlag: int
    dictIDFlag: int

    nbWorkers: int
    jobSize: int
    overlapLog: int

    def bounds(self) -> Tuple[int, int]: ...

class DParameter(IntEnum):
    windowLogMax: int

    def bounds(self) -> Tuple[int, int]: ...

class ZstdDict:
    dict_content: bytes
    dict_id: int

    def __init__(self,
                 dict_content,
                 is_raw: bool = False) -> None: ...

class ZstdCompressor:
    CONTINUE: ClassVar[int]
    FLUSH_BLOCK: ClassVar[int]
    FLUSH_FRAME: ClassVar[int]

    last_mode: Union[ZstdCompressor.CONTINUE, ZstdCompressor.FLUSH_BLOCK, ZstdCompressor.FLUSH_FRAME]

    def __init__(self,
                 level_or_option: Union[None, int, Dict[CParameter, int]] = None,
                 zstd_dict: Optional[ZstdDict] = None) -> None: ...

    def compress(self,
                 data,
                 mode: Union[ZstdCompressor.CONTINUE, ZstdCompressor.FLUSH_BLOCK, ZstdCompressor.FLUSH_FRAME] = ZstdCompressor.CONTINUE) -> bytes: ...

    def flush(self,
              mode: Union[ZstdCompressor.FLUSH_BLOCK, ZstdCompressor.FLUSH_FRAME] = ZstdCompressor.FLUSH_FRAME) -> bytes: ...

    def _set_pledged_input_size(self, size: Union[int, None]) -> None: ...

class RichMemZstdCompressor:
    def __init__(self,
                 level_or_option: Union[None, int, Dict[CParameter, int]] = None,
                 zstd_dict: Optional[ZstdDict] = None) -> None: ...

    def compress(self, data) -> bytes: ...

class ZstdDecompressor:
    needs_input: bool
    eof: bool
    unused_data: bytes

    def __init__(self,
                 zstd_dict: Optional[ZstdDict] = None,
                 option: Optional[Dict[DParameter, int]] = None) -> None: ...

    def decompress(self,
                   data: ByteString,
                   max_length: int = -1) -> bytes: ...

class EndlessZstdDecompressor:
    needs_input: bool
    at_frame_edge: bool

    def __init__(self,
                 zstd_dict: Optional[ZstdDict] = None,
                 option: Optional[Dict[DParameter, int]] = None) -> None: ...

    def decompress(self,
                   data: ByteString,
                   max_length: int = -1) -> bytes: ...

class ZstdError(Exception):
    ...

def compress(data,
             level_or_option: Union[None, int, Dict[CParameter, int]] = None,
             zstd_dict: Optional[ZstdDict] = None) -> bytes: ...

def richmem_compress(data,
                     level_or_option: Union[None, int, Dict[CParameter, int]] = None,
                     zstd_dict: Optional[ZstdDict] = None) -> bytes: ...

def decompress(data: ByteString,
               zstd_dict: Optional[ZstdDict] = None,
               option: Optional[Dict[DParameter, int]] = None) -> bytes: ...

def compress_stream(input_stream: BinaryIO, output_stream: Union[BinaryIO, None], *,
                    level_or_option: Union[None, int, Dict[CParameter, int]] = None,
                    zstd_dict: Optional[ZstdDict] = None,
                    pledged_input_size: Optional[int] = None,
                    read_size: int = 131_072, write_size: int = 131_591,
                    callback: Optional[Callable[[int, int, memoryview, memoryview], None]] = None) -> Tuple[int, int]: ...

def decompress_stream(input_stream: BinaryIO, output_stream: Union[BinaryIO, None], *,
                      zstd_dict: Optional[ZstdDict] = None,
                      option: Optional[Dict[DParameter, int]] = None,
                      read_size: int = 131_075, write_size: int = 131_072,
                      callback: Optional[Callable[[int, int, memoryview, memoryview], None]] = None) -> Tuple[int, int]: ...

def train_dict(samples: Iterable,
               dict_size: int) -> ZstdDict: ...

def finalize_dict(zstd_dict: ZstdDict,
                  samples: Iterable,
                  dict_size: int,
                  level: int) -> ZstdDict: ...

class frame_info(NamedTuple):
    decompressed_size: Union[int, None]
    dictionary_id: int

def get_frame_info(frame_buffer: ByteString) -> frame_info: ...

def get_frame_size(frame_buffer: ByteString) -> int: ...

class ZstdFile(io.BufferedIOBase):
    def __init__(self,
                 filename: Union[str, bytes, PathLike, BinaryIO],
                 mode: str = "r",
                 *,
                 level_or_option: Union[None, int, Dict[CParameter, int], Dict[DParameter, int]] = None,
                 zstd_dict: Optional[ZstdDict] = None) -> None: ...
    def close(self) -> None: ...

    def write(self, data) -> int: ...
    def flush(self) -> None: ...

    def read(self, size: int = -1) -> bytes: ...
    def read1(self, size: int = -1) -> bytes: ...
    def readinto(self, b) -> int: ...
    def readinto1(self, b) -> int: ...
    def readline(self, size: int = -1) -> bytes: ...
    def seek(self,
             offset: int,
             whence: Union[io.SEEK_SET, io.SEEK_CUR, io.SEEK_END] = io.SEEK_SET) -> int: ...
    def peek(self, size: int = -1) -> bytes: ...

    def tell(self) -> int: ...
    def fileno(self) -> int: ...
    @property
    def closed(self) -> bool: ...
    def writable(self) -> bool: ...
    def readable(self) -> bool: ...
    def seekable(self) -> bool: ...

_BinaryMode = Literal["r", "rb", # read
                      "w", "wb", "a", "ab", "x", "xb"] # write
_TextMode = Literal["rt", # read
                    "wt", "at", "xt"] # write

@overload
def open(filename: Union[str, bytes, PathLike, BinaryIO],
         mode: _BinaryMode = "rb",
         *,
         level_or_option: Union[None, int, Dict[CParameter, int], Dict[DParameter, int]] = None,
         zstd_dict: Optional[ZstdDict] = None,
         encoding: None = None,
         errors: None = None,
         newline: None = None) -> ZstdFile: ...

@overload
def open(filename: Union[str, bytes, PathLike, BinaryIO],
         mode: _TextMode = ...,
         *,
         level_or_option: Union[None, int, Dict[CParameter, int], Dict[DParameter, int]] = None,
         zstd_dict: Optional[ZstdDict] = None,
         encoding: Optional[str] = None,
         errors: Optional[str] = None,
         newline: Optional[str] = None) -> TextIO: ...

@overload
def open(filename: Union[str, bytes, PathLike, BinaryIO],
         mode: str = "rb",
         *,
         level_or_option: Union[None, int, Dict[CParameter, int], Dict[DParameter, int]] = None,
         zstd_dict: Optional[ZstdDict] = None,
         encoding: Optional[str] = None,
         errors: Optional[str] = None,
         newline: Optional[str] = None) -> Union[ZstdFile, TextIO]: ...
