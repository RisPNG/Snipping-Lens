from .abc import Codec
from .compat import ensure_ndarray, ndarray_copy, ensure_text


import numpy as np


class Categorize(Codec):
    """Filter encoding categorical string data as integers.

    Parameters
    ----------
    labels : sequence of strings
        Category labels.
    dtype : dtype
        Data type to use for decoded data.
    astype : dtype, optional
        Data type to use for encoded data.

    Examples
    --------
    >>> import numcodecs
    >>> import numpy as np
    >>> x = np.array(['male', 'female', 'female', 'male', 'unexpected'], dtype=object)
    >>> x
    array(['male', 'female', 'female', 'male', 'unexpected'],
          dtype=object)
    >>> codec = numcodecs.Categorize(labels=['female', 'male'], dtype=object)
    >>> y = codec.encode(x)
    >>> y
    array([2, 1, 1, 2, 0], dtype=uint8)
    >>> z = codec.decode(y)
    >>> z
    array(['male', 'female', 'female', 'male', ''],
          dtype=object)

    """

    codec_id = 'categorize'

    def __init__(self, labels, dtype, astype='u1'):
        self.dtype = np.dtype(dtype)
        if self.dtype.kind not in 'UO':
            raise TypeError("only unicode ('U') and object ('O') dtypes are "
                            "supported")
        self.labels = [ensure_text(label) for label in labels]
        self.astype = np.dtype(astype)
        if self.astype == object:
            raise TypeError('encoding as object array not supported')

    def encode(self, buf):

        # normalise input
        if self.dtype == object:
            arr = np.asarray(buf, dtype=object)
        else:
            arr = ensure_ndarray(buf).view(self.dtype)

        # flatten to simplify implementation
        arr = arr.reshape(-1, order='A')

        # setup output array
        enc = np.zeros_like(arr, dtype=self.astype)

        # apply encoding, reserving 0 for values not specified in labels
        for i, l in enumerate(self.labels):
            enc[arr == l] = i + 1

        return enc

    def decode(self, buf, out=None):

        # normalise input
        enc = ensure_ndarray(buf).view(self.astype)

        # flatten to simplify implementation
        enc = enc.reshape(-1, order='A')

        # setup output
        dec = np.full_like(enc, fill_value='', dtype=self.dtype)

        # apply decoding
        for i, l in enumerate(self.labels):
            dec[enc == (i + 1)] = l

        # handle output
        dec = ndarray_copy(dec, out)

        return dec

    def get_config(self):
        config = dict(
            id=self.codec_id,
            labels=self.labels,
            dtype=self.dtype.str,
            astype=self.astype.str
        )
        return config

    def __repr__(self):
        # make sure labels part is not too long
        labels = repr(self.labels[:3])
        if len(self.labels) > 3:
            labels = labels[:-1] + ', ...]'
        r = '%s(dtype=%r, astype=%r, labels=%s)' % \
            (type(self).__name__, self.dtype.str, self.astype.str, labels)
        return r
