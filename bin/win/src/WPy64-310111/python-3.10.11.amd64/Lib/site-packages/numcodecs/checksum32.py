import zlib


import numpy as np


from .abc import Codec
from .compat import ensure_contiguous_ndarray, ndarray_copy


class Checksum32(Codec):

    checksum = None

    def encode(self, buf):
        arr = ensure_contiguous_ndarray(buf).view('u1')
        checksum = self.checksum(arr) & 0xffffffff
        enc = np.empty(arr.nbytes + 4, dtype='u1')
        enc[:4].view('<u4')[0] = checksum
        ndarray_copy(arr, enc[4:])
        return enc

    def decode(self, buf, out=None):
        arr = ensure_contiguous_ndarray(buf).view('u1')
        expect = arr[:4].view('<u4')[0]
        checksum = self.checksum(arr[4:]) & 0xffffffff
        if expect != checksum:
            raise RuntimeError('checksum failed')
        return ndarray_copy(arr[4:], out)


class CRC32(Checksum32):

    codec_id = 'crc32'
    checksum = zlib.crc32


class Adler32(Checksum32):

    codec_id = 'adler32'
    checksum = zlib.adler32
