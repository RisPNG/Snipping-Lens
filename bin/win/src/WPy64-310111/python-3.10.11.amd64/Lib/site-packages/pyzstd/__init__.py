import _compression
import io
from sys import maxsize
try:
    from os import PathLike
except ImportError:
    # For Python 3.5
    class PathLike:
        pass

try:
    # Import C implementation
    from .c.c_pyzstd import *
    from .c.c_pyzstd import _train_dict, _finalize_dict, \
                            _ZSTD_DStreamInSize
except ImportError:
    try:
        # Import CFFI implementation
        from .cffi.cffi_pyzstd import *
        from .cffi.cffi_pyzstd import _train_dict, _finalize_dict, \
                                      _ZSTD_DStreamInSize
    except ImportError:
        raise ImportError(
            "pyzstd module: Neither C implementation nor CFFI implementation "
            "can be imported. If pyzstd module is dynamically linked to zstd "
            "library, make sure not to remove zstd library, and the run-time "
            "zstd library's version can't be lower than that at compile-time.")

__version__ = '0.15.4'

__doc__ = '''\
Python bindings to Zstandard (zstd) compression library, the API style is
similar to Python's bz2/lzma/zlib modules.

Command line interface of this module: python -m pyzstd --help

Documentation: https://pyzstd.readthedocs.io
GitHub: https://github.com/animalize/pyzstd
PyPI: https://pypi.org/project/pyzstd'''

__all__ = ('ZstdCompressor', 'RichMemZstdCompressor',
           'ZstdDecompressor', 'EndlessZstdDecompressor',
           'CParameter', 'DParameter', 'Strategy', 'ZstdError',
           'compress', 'richmem_compress', 'decompress',
           'compress_stream', 'decompress_stream',
           'ZstdDict', 'train_dict', 'finalize_dict',
           'get_frame_info', 'get_frame_size', 'ZstdFile', 'open',
           'zstd_version', 'zstd_version_info',
           'zstd_support_multithread', 'compressionLevel_values')


zstd_support_multithread = (CParameter.nbWorkers.bounds() != (0, 0))


def compress(data, level_or_option=None, zstd_dict=None):
    """Compress a block of data, return a bytes object.

    Compressing b'' will get an empty content frame (9 bytes or more).

    Parameters
    data:            A bytes-like object, data to be compressed.
    level_or_option: When it's an int object, it represents compression level.
                     When it's a dict object, it contains advanced compression
                     parameters.
    zstd_dict:       A ZstdDict object, pre-trained dictionary for compression.
    """
    comp = ZstdCompressor(level_or_option, zstd_dict)
    return comp.compress(data, ZstdCompressor.FLUSH_FRAME)


def richmem_compress(data, level_or_option=None, zstd_dict=None):
    """Compress a block of data, return a bytes object.

    Use rich memory mode, it's faster than compress() in some cases, but
    allocates more memory.

    Compressing b'' will get an empty content frame (9 bytes or more).

    Parameters
    data:            A bytes-like object, data to be compressed.
    level_or_option: When it's an int object, it represents compression level.
                     When it's a dict object, it contains advanced compression
                     parameters.
    zstd_dict:       A ZstdDict object, pre-trained dictionary for compression.
    """
    comp = RichMemZstdCompressor(level_or_option, zstd_dict)
    return comp.compress(data)


def _nbytes(dat):
    if isinstance(dat, (bytes, bytearray)):
        return len(dat)
    return memoryview(dat).nbytes


def train_dict(samples, dict_size):
    """Train a zstd dictionary, return a ZstdDict object.

    Parameters
    samples:   An iterable of samples, a sample is a bytes-like object
               represents a file.
    dict_size: The dictionary's maximum size, in bytes.
    """
    # Check argument's type
    if not isinstance(dict_size, int):
        raise TypeError('dict_size argument should be an int object.')

    # Prepare data
    chunks = []
    chunk_sizes = []
    for chunk in samples:
        chunks.append(chunk)
        chunk_sizes.append(_nbytes(chunk))

    chunks = b''.join(chunks)
    if not chunks:
        raise ValueError("The samples are empty content, can't train dictionary.")

    # samples_bytes: samples be stored concatenated in a single flat buffer.
    # samples_size_list: a list of each sample's size.
    # dict_size: size of the dictionary, in bytes.
    dict_content = _train_dict(chunks, chunk_sizes, dict_size)

    return ZstdDict(dict_content)


def finalize_dict(zstd_dict, samples, dict_size, level):
    """Finalize a zstd dictionary, return a ZstdDict object.

    Given a custom content as a basis for dictionary, and a set of samples,
    finalize dictionary by adding headers and statistics according to the zstd
    dictionary format.

    You may compose an effective dictionary content by hand, which is used as
    basis dictionary, and use some samples to finalize a dictionary. The basis
    dictionary can be a "raw content" dictionary, see is_raw parameter in
    ZstdDict.__init__ method.

    Parameters
    zstd_dict: A ZstdDict object, basis dictionary.
    samples:   An iterable of samples, a sample is a bytes-like object
               represents a file.
    dict_size: The dictionary's maximum size, in bytes.
    level:     The compression level expected to use in production. The
               statistics for each compression level differ, so tuning the
               dictionary for the compression level can help quite a bit.
    """
    if zstd_version_info < (1, 4, 5):
        msg = ("This function only available when the underlying zstd "
               "library's version is greater than or equal to v1.4.5, "
               "the current underlying zstd library's version is v%s.") % zstd_version
        raise NotImplementedError(msg)

    # Check arguments' type
    if not isinstance(zstd_dict, ZstdDict):
        raise TypeError('zstd_dict argument should be a ZstdDict object.')
    if not isinstance(dict_size, int):
        raise TypeError('dict_size argument should be an int object.')
    if not isinstance(level, int):
        raise TypeError('level argument should be an int object.')

    # Prepare data
    chunks = []
    chunk_sizes = []
    for chunk in samples:
        chunks.append(chunk)
        chunk_sizes.append(_nbytes(chunk))

    chunks = b''.join(chunks)
    if not chunks:
        raise ValueError("The samples are empty content, can't finalize dictionary.")

    # custom_dict_bytes: existing dictionary.
    # samples_bytes: samples be stored concatenated in a single flat buffer.
    # samples_size_list: a list of each sample's size.
    # dict_size: maximal size of the dictionary, in bytes.
    # compression_level: compression level expected to use in production.
    dict_content = _finalize_dict(zstd_dict.dict_content,
                                  chunks, chunk_sizes,
                                  dict_size, level)

    return ZstdDict(dict_content)


# In pyzstd module's blocks output buffer, the first block is 32 KiB. It has a
# fast path for this size, if the output data is 32 KiB, it only allocates
# memory and copies data once.
_32_KiB = 32*1024

# Copied from Python stdlib (_compression.py), except:
# 1, ZstdDecompressReader.read():
#      Uses ZSTD_DStreamInSize() (131,075 in zstd v1.x) instead of
#      _compression.BUFFER_SIZE (default is 8 KiB) as read size.
# 2, ZstdDecompressReader.seek():
#      Uses 32 KiB instead of io.DEFAULT_BUFFER_SIZE (default is 8 KiB) as
#      max_length. See _32_KiB's comment for details.
class ZstdDecompressReader(_compression.DecompressReader):
    # Add .readall() method for speedup
    # https://bugs.python.org/issue41486
    def readall(self):
        chunks = []
        while True:
            # sys.maxsize means the max length of output buffer is unlimited,
            # so that the whole input buffer can be decompressed within one
            # .decompress() call.
            data = self.read(maxsize)
            if not data:
                break
            chunks.append(data)
        return b''.join(chunks)

    # Compare to super().read():
    # 1, Use ZSTD_DStreamInSize() instead of BUFFER_SIZE (default is 8 KiB)
    # 2, Use EndlessZstdDecompressor to simplify the code
    def read(self, size=-1):
        if size < 0:
            return self.readall()
        if not size or self._eof:
            return b""

        # Depending on the input data, our call to the decompressor may not
        # return any data. In this case, try again after reading another block.
        while True:
            if self._decompressor.needs_input:
                rawblock = self._fp.read(_ZSTD_DStreamInSize)
                if not rawblock:
                    if self._decompressor.at_frame_edge:
                        self._eof = True
                        self._size = self._pos
                        return b""
                    else:
                        raise EOFError("Compressed file ended before the "
                                       "end-of-stream marker was reached")
            else:
                rawblock = b""

            data = self._decompressor.decompress(rawblock, size)
            if data:
                self._pos += len(data)
                return data

    # Copied from base class, except use 32 KiB instead of
    # io.DEFAULT_BUFFER_SIZE (default is 8 KiB) as max_length.
    def seek(self, offset, whence=io.SEEK_SET):
        # Recalculate offset as an absolute file position.
        if whence == io.SEEK_SET:
            pass
        elif whence == io.SEEK_CUR:
            offset = self._pos + offset
        elif whence == io.SEEK_END:
            # Seeking relative to EOF - we need to know the file's size.
            if self._size < 0:
                while self.read(_32_KiB):
                    pass
            offset = self._size + offset
        else:
            raise ValueError("Invalid value for whence: {}".format(whence))

        # Make it so that offset is the number of bytes to skip forward.
        if offset < self._pos:
            self._rewind()
        else:
            offset -= self._pos

        # Read and discard data until we reach the desired position.
        while offset > 0:
            data = self.read(min(_32_KiB, offset))
            if not data:
                break
            offset -= len(data)

        return self._pos


_MODE_CLOSED = 0
_MODE_READ   = 1
_MODE_WRITE  = 2

# Copied from Python stdlib (lzma.py), except:
# 1, Add .readinto()/.readinto1() methods.
# 2, Implement .flush() method.
# 3, Remove BaseStream._check_*() overheads.
#    The implementation needs to ensure:
#      If in _MODE_READ mode, ._buffer is an io.BufferedReader object.
#      If in _MODE_WRITE mode, ._compressor is a ZstdCompressor object.
#      If in _MODE_CLOSED mode, they and ._fp don't exist or are None.
#    Then if not in a mode, perform the corresponding actions will raise
#    AttributeError, and ._check_mode() will raise a proper exception.
# 4, ZstdFile.__init__():
#      io.BufferedReader uses 32 KiB buffer size instead of default value
#      io.DEFAULT_BUFFER_SIZE (default is 8 KiB).
#      See _32_KiB's comment for details.
# 5, ZstdFile.read1():
#      Uses 32 KiB instead of io.DEFAULT_BUFFER_SIZE (default is 8 KiB).
#      Consistent with ZstdFile.__init__().
class ZstdFile(io.BufferedIOBase):
    """A file object providing transparent zstd (de)compression.

    A ZstdFile can act as a wrapper for an existing file object, or refer
    directly to a named file on disk.

    Note that ZstdFile provides a *binary* file interface - data read is
    returned as bytes, and data to be written must be given as bytes.
    """

    def __init__(self, filename, mode="r", *,
                 level_or_option=None, zstd_dict=None):
        """Open a zstd compressed file in binary mode.

        filename can be either an actual file name (given as a str, bytes, or
        PathLike object), in which case the named file is opened, or it can be
        an existing file object to read from or write to.

        mode can be "r" for reading (default), "w" for (over)writing, "x" for
        creating exclusively, or "a" for appending. These can equivalently be
        given as "rb", "wb", "xb" and "ab" respectively.

        Parameters
        level_or_option: When it's an int object, it represents compression
            level. When it's a dict object, it contains advanced compression
            parameters. Note, in read mode (decompression), it can only be a
            dict object, that represents decompression option. It doesn't
            support int type compression level in this case.
        zstd_dict: A ZstdDict object, pre-trained dictionary for compression /
            decompression.
        """
        self._fp = None
        self._closefp = False
        self._mode = _MODE_CLOSED

        if not isinstance(zstd_dict, (type(None), ZstdDict)):
            raise TypeError("zstd_dict argument should be a ZstdDict object.")

        # Read or write mode
        if mode in ("r", "rb"):
            if not isinstance(level_or_option, (type(None), dict)):
                msg = ("In read mode (decompression), level_or_option argument "
                       "should be a dict object, that represents decompression "
                       "option. It doesn't support int type compression level "
                       "in this case.")
                raise TypeError(msg)
            mode_code = _MODE_READ
        elif mode in ("w", "wb", "a", "ab", "x", "xb"):
            if not isinstance(level_or_option, (type(None), int, dict)):
                msg = "level_or_option argument should be int or dict object."
                raise TypeError(msg)
            mode_code = _MODE_WRITE
            self._compressor = ZstdCompressor(level_or_option, zstd_dict)
            self._pos = 0
        else:
            raise ValueError("Invalid mode: {!r}".format(mode))

        # File object
        if isinstance(filename, (str, bytes, PathLike)):
            if "b" not in mode:
                mode += "b"
            self._fp = io.open(filename, mode)
            self._closefp = True
            # Set ._mode here for ._closefp in .close(). If the following code
            # fails, IOBase's cleanup code will call .close(), so that ._fp can
            # be closed.
            self._mode = mode_code
        elif hasattr(filename, "read") or hasattr(filename, "write"):
            self._fp = filename
            self._mode = mode_code
        else:
            raise TypeError("filename must be a str, bytes, file or PathLike object")

        # ZstdDecompressReader
        if mode_code == _MODE_READ:
            raw = ZstdDecompressReader(self._fp, EndlessZstdDecompressor,
                                       trailing_error=ZstdError,
                                       zstd_dict=zstd_dict, option=level_or_option)
            self._buffer = io.BufferedReader(raw, _32_KiB)

    def close(self):
        """Flush and close the file.

        May be called more than once without error. Once the file is
        closed, any other operation on it will raise a ValueError.
        """
        if self._mode == _MODE_CLOSED:
            return

        try:
            # In .__init__ method, if fails after setting ._mode to _MODE_READ,
            # ._buffer doesn't exist.
            if hasattr(self, "_buffer"):
                try:
                    self._buffer.close()
                finally:
                    # Set to None for ._check_mode()
                    self._buffer = None
            elif self._mode == _MODE_WRITE:
                try:
                    self._fp.write(self._compressor.flush())
                finally:
                    # Set to None for ._check_mode()
                    self._compressor = None
        finally:
            try:
                if self._closefp:
                    self._fp.close()
            finally:
                self._fp = None
                self._closefp = False
                self._mode = _MODE_CLOSED

    # None argument means the file should be closed
    def _check_mode(self, expected_mode=None):
        # If closed, raise ValueError.
        if self._mode == _MODE_CLOSED:
            raise ValueError("I/O operation on closed file")

        # Check _MODE_READ/_MODE_WRITE mode
        if expected_mode == _MODE_READ:
            if self._mode != _MODE_READ:
                raise io.UnsupportedOperation("File not open for reading")
        elif expected_mode == _MODE_WRITE:
            if self._mode != _MODE_WRITE:
                raise io.UnsupportedOperation("File not open for writing")

        # Re-raise other AttributeError exception
        raise

    def write(self, data):
        """Write a bytes-like object to the file.

        Returns the number of uncompressed bytes written, which is
        always the length of data in bytes. Note that due to buffering,
        the file on disk may not reflect the data written until close()
        is called.
        """
        # Get the length of uncompressed data
        if isinstance(data, (bytes, bytearray)):
            length = len(data)
        else:
            # Accept any data that supports the buffer protocol
            data = memoryview(data)
            length = data.nbytes

        # Compress
        try:
            compressed = self._compressor.compress(data)
        except AttributeError:
            self._check_mode(_MODE_WRITE)

        # Write to file. If haven't gathered enough uncompressed data for one
        # zstd block (128 KiB at most), `compressed` is b''.
        if compressed:
            self._fp.write(compressed)

        self._pos += length
        return length

    def flush(self):
        """Flush remaining data to the underlying stream.

        It uses ZstdCompressor.FLUSH_BLOCK mode. Abuse of this method will
        reduce compression ratio, use it only when necessary.

        If the program is interrupted afterwards, all data can be recovered.
        To ensure saving to disk, also need to use os.fsync(fd).

        This method does nothing in reading mode.
        """
        # Like IOBase.flush(), do nothing in reading mode.
        # TextIOWrapper.close() relies on this behavior.
        if self._mode == _MODE_READ:
            return

        # Flush zstd block
        try:
            compressed = self._compressor.flush(ZstdCompressor.FLUSH_BLOCK)
        except AttributeError:
            # Closed, raise ValueError.
            self._check_mode()

        # Write to file
        if compressed:
            self._fp.write(compressed)

        # Flush the file. Some file-like objects don't have .flush() method.
        if hasattr(self._fp, "flush"):
            self._fp.flush()

    def read(self, size=-1):
        """Read up to size uncompressed bytes from the file.

        If size is negative or omitted, read until EOF is reached.
        Returns b"" if the file is already at EOF.
        """
        try:
            return self._buffer.read(size)
        except AttributeError:
            self._check_mode(_MODE_READ)

    def read1(self, size=-1):
        """Read up to size uncompressed bytes, while trying to avoid
        making multiple reads from the underlying stream. Reads up to a
        buffer's worth of data if size is negative.

        Returns b"" if the file is at EOF.
        """
        if size < 0:
            size = _32_KiB

        try:
            return self._buffer.read1(size)
        except AttributeError:
            self._check_mode(_MODE_READ)

    def readinto(self, b):
        """Read bytes into b.

        Returns the number of bytes read (0 for EOF).
        """
        try:
            return self._buffer.readinto(b)
        except AttributeError:
            self._check_mode(_MODE_READ)

    def readinto1(self, b):
        """Read bytes into b, while trying to avoid making multiple reads
        from the underlying stream.

        Returns the number of bytes read (0 for EOF).
        """
        try:
            return self._buffer.readinto1(b)
        except AttributeError:
            self._check_mode(_MODE_READ)

    def readline(self, size=-1):
        """Read a line of uncompressed bytes from the file.

        The terminating newline (if present) is retained. If size is
        non-negative, no more than size bytes will be read (in which
        case the line may be incomplete). Returns b'' if already at EOF.
        """
        try:
            return self._buffer.readline(size)
        except AttributeError:
            self._check_mode(_MODE_READ)

    def seek(self, offset, whence=io.SEEK_SET):
        """Change the file position.

        The new position is specified by offset, relative to the
        position indicated by whence. Possible values for whence are:

            0: start of stream (default): offset must not be negative
            1: current stream position
            2: end of stream; offset must not be positive

        Returns the new file position.

        Note that seeking is emulated, so depending on the arguments,
        this operation may be extremely slow.
        """
        try:
            # BufferedReader.seek() checks seekable
            return self._buffer.seek(offset, whence)
        except AttributeError:
            self._check_mode(_MODE_READ)

    def peek(self, size=-1):
        """Return buffered data without advancing the file position.

        Always returns at least one byte of data, unless at EOF.
        The exact number of bytes returned is unspecified.
        """
        # Relies on the undocumented fact that BufferedReader.peek() always
        # returns at least one byte (except at EOF)
        try:
            return self._buffer.peek(size)
        except AttributeError:
            self._check_mode(_MODE_READ)

    def __iter__(self):
        try:
            self._buffer
        except AttributeError:
            self._check_mode(_MODE_READ)
        return self

    def __next__(self):
        ret = self._buffer.readline()
        if ret:
            return ret
        raise StopIteration

    def tell(self):
        """Return the current file position."""
        if self._mode == _MODE_READ:
            return self._buffer.tell()
        elif self._mode == _MODE_WRITE:
            return self._pos

        # Closed, raise ValueError.
        self._check_mode()

    def fileno(self):
        """Return the file descriptor for the underlying file."""
        try:
            return self._fp.fileno()
        except AttributeError:
            # Closed, raise ValueError.
            self._check_mode()

    @property
    def closed(self):
        """True if this file is closed."""
        return self._mode == _MODE_CLOSED

    def writable(self):
        """Return whether the file was opened for writing."""
        if self._mode == _MODE_WRITE:
            return True
        elif self._mode == _MODE_READ:
            return False

        # Closed, raise ValueError.
        self._check_mode()

    def readable(self):
        """Return whether the file was opened for reading."""
        if self._mode == _MODE_READ:
            return True
        elif self._mode == _MODE_WRITE:
            return False

        # Closed, raise ValueError.
        self._check_mode()

    def seekable(self):
        """Return whether the file supports seeking."""
        if self._mode == _MODE_READ:
            return self._buffer.seekable()
        elif self._mode == _MODE_WRITE:
            return False

        # Closed, raise ValueError.
        self._check_mode()


# Copied from lzma module
def open(filename, mode="rb", *, level_or_option=None, zstd_dict=None,
         encoding=None, errors=None, newline=None):
    """Open a zstd compressed file in binary or text mode.

    filename can be either an actual file name (given as a str, bytes, or
    PathLike object), in which case the named file is opened, or it can be an
    existing file object to read from or write to.

    The mode parameter can be "r", "rb" (default), "w", "wb", "x", "xb", "a",
    "ab" for binary mode, or "rt", "wt", "xt", "at" for text mode.

    The level_or_option and zstd_dict parameters specify the settings, as for
    ZstdCompressor, ZstdDecompressor and ZstdFile.

    When using read mode (decompression), the level_or_option parameter can
    only be a dict object, that represents decompression option. It doesn't
    support int type compression level in this case.

    For binary mode, this function is equivalent to the ZstdFile constructor:
    ZstdFile(filename, mode, ...). In this case, the encoding, errors and
    newline parameters must not be provided.

    For text mode, an ZstdFile object is created, and wrapped in an
    io.TextIOWrapper instance with the specified encoding, error handling
    behavior, and line ending(s).
    """

    if "t" in mode:
        if "b" in mode:
            raise ValueError("Invalid mode: %r" % (mode,))
    else:
        if encoding is not None:
            raise ValueError("Argument 'encoding' not supported in binary mode")
        if errors is not None:
            raise ValueError("Argument 'errors' not supported in binary mode")
        if newline is not None:
            raise ValueError("Argument 'newline' not supported in binary mode")

    zstd_mode = mode.replace("t", "")
    binary_file = ZstdFile(filename, zstd_mode,
                           level_or_option=level_or_option, zstd_dict=zstd_dict)

    if "t" in mode:
        return io.TextIOWrapper(binary_file, encoding, errors, newline)
    else:
        return binary_file
