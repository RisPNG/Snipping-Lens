_zfpy = None
try:
    import zfpy as _zfpy
except ImportError:  # pragma: no cover
    pass


if _zfpy:

    from .abc import Codec
    from .compat import ndarray_copy, ensure_contiguous_ndarray, ensure_bytes
    import numpy as np

    # noinspection PyShadowingBuiltins
    class ZFPY(Codec):
        """Codec providing compression using zfpy via the Python standard
        library.

        Parameters
        ----------
        mode : integer
            One of the zfpy mode choice, e.g., ``zfpy.mode_fixed_accuracy``.
        tolerance : double, optional
            A double-precision number, specifying the compression accuracy needed.
        rate : double, optional
            A double-precision number, specifying the compression rate needed.
        precision : int, optional
            A integer number, specifying the compression precision needed.

        """

        codec_id = "zfpy"

        def __init__(
            self,
            mode=_zfpy.mode_fixed_accuracy,
            tolerance=-1,
            rate=-1,
            precision=-1,
            compression_kwargs=None,
        ):
            self.mode = mode
            if mode == _zfpy.mode_fixed_accuracy:
                self.compression_kwargs = {"tolerance": tolerance}
            elif mode == _zfpy.mode_fixed_rate:
                self.compression_kwargs = {"rate": rate}
            elif mode == _zfpy.mode_fixed_precision:
                self.compression_kwargs = {"precision": precision}
            else:
                pass

            self.tolerance = tolerance
            self.rate = rate
            self.precision = precision

        def encode(self, buf):

            # not flatten c-order array and raise exception for f-order array
            if not isinstance(buf, np.ndarray):
                raise TypeError("The zfp codec does not support none numpy arrays."
                                f" Your buffers were {type(buf)}.")
            if buf.flags.c_contiguous:
                flatten = False
            else:
                raise ValueError("The zfp codec does not support F order arrays. "
                                 f"Your arrays flags were {buf.flags}.")
            buf = ensure_contiguous_ndarray(buf, flatten=flatten)

            # do compression
            return _zfpy.compress_numpy(
                buf, write_header=True, **self.compression_kwargs
            )

        def decode(self, buf, out=None):

            # normalise inputs
            buf = ensure_bytes(buf)
            if out is not None:
                out = ensure_contiguous_ndarray(out)

            # do decompression
            dec = _zfpy.decompress_numpy(buf)

            # handle destination
            if out is not None:
                return ndarray_copy(dec, out)
            else:
                return dec

        def __repr__(self):
            r = "%s(mode=%r, tolerance=%s, rate=%s, precision=%s)" % (
                type(self).__name__,
                self.mode,
                self.tolerance,
                self.rate,
                self.precision,
            )
            return r
