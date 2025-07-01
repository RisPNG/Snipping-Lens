from __future__ import absolute_import

from functools import partial

import numpy as np
import pandas as pd
from pandas.core.internals import create_block_manager_from_blocks, make_block

from . import numpy as pnp
from .core import Interface
from .compatibility import pickle
from .encode import Encode
from .utils import extend, framesplit, frame

try:
    # pandas >= 0.24.0
    from pandas.api.types import is_extension_array_dtype
except ImportError:
    def is_extension_array_dtype(dtype):
        return False

try:
    # Some `ExtensionArray`s can have a `.dtype` which is not a `ExtensionDtype`
    # (e.g. they can be backed by a NumPy dtype). For these cases we check
    # whether the instance is a `ExtensionArray`.
    # https://github.com/dask/partd/issues/48
    from pandas.api.extensions import ExtensionArray
    def is_extension_array(x):
        return isinstance(x, ExtensionArray)
except ImportError:
    def is_extension_array(x):
        return False


dumps = partial(pickle.dumps, protocol=pickle.HIGHEST_PROTOCOL)


class PandasColumns(Interface):
    def __init__(self, partd=None):
        self.partd = pnp.Numpy(partd)
        Interface.__init__(self)

    def append(self, data, **kwargs):
        for k, df in data.items():
            self.iset(extend(k, '.columns'), dumps(list(df.columns)))
            self.iset(extend(k, '.index-name'), dumps(df.index.name))

        # TODO: don't use values, it does some work.  Look at _blocks instead
        #       pframe/cframe do this well
        arrays = dict((extend(k, col), df[col].values)
                       for k, df in data.items()
                       for col in df.columns)
        arrays.update(dict((extend(k, '.index'), df.index.values)
                            for k, df in data.items()))
        # TODO: handle categoricals
        self.partd.append(arrays, **kwargs)

    def _get(self, keys, columns=None, **kwargs):
        if columns is None:
            columns = self.partd.partd.get([extend(k, '.columns') for k in keys],
                                           **kwargs)
            columns = list(map(pickle.loads, columns))
        else:
            columns = [columns] * len(keys)
        index_names = self.partd.partd.get([extend(k, '.index-name')
                                            for k in keys], **kwargs)
        index_names = map(pickle.loads, index_names)

        keys = [[extend(k, '.index'), [extend(k, col) for col in cols]]
                 for k, cols in zip(keys, columns)]

        arrays = self.partd.get(keys, **kwargs)

        return [pd.DataFrame(dict(zip(cols, arrs)), columns=cols,
                             index=pd.Index(index, name=iname))
            for iname, (index, arrs), cols in zip(index_names, arrays, columns)]

    def __getstate__(self):
        return {'partd': self.partd}

    def _iset(self, key, value):
        return self.partd._iset(key, value)

    def drop(self):
        return self.partd.drop()

    @property
    def lock(self):
        return self.partd.partd.lock

    def __exit__(self, *args):
        self.drop()
        self.partd.__exit__(self, *args)

    def __del__(self):
        self.partd.__del__()


def index_to_header_bytes(ind):
    # These have special `__reduce__` methods, just use pickle
    if isinstance(ind, (pd.DatetimeIndex,
                        pd.MultiIndex,
                        pd.RangeIndex)):
        return None, dumps(ind)

    if isinstance(ind, pd.CategoricalIndex):
        cat = (ind.ordered, ind.categories)
        values = ind.codes
    else:
        cat = None
        values = ind.values

    header = (type(ind), ind._get_attributes_dict(), values.dtype, cat)
    bytes = pnp.compress(pnp.serialize(values), values.dtype)
    return header, bytes


def index_from_header_bytes(header, bytes):
    if header is None:
        return pickle.loads(bytes)

    typ, attr, dtype, cat = header
    data = pnp.deserialize(pnp.decompress(bytes, dtype), dtype, copy=True)
    if cat:
        data = pd.Categorical.from_codes(data, cat[1], ordered=cat[0])
    return typ.__new__(typ, data=data, **attr)


def block_to_header_bytes(block):
    values = block.values
    try:
        # pandas >= 0.19
        from pandas.api.types import is_datetime64tz_dtype
    except ImportError:
        from pandas.core.common import is_datetime64tz_dtype

    if isinstance(values, pd.Categorical):
        extension = ('categorical_type', (values.ordered, values.categories))
        values = values.codes
    elif is_datetime64tz_dtype(block):
        extension = ('datetime64_tz_type', (block.values.tzinfo,))
        values = values.view('i8')
    elif is_extension_array_dtype(block.dtype) or is_extension_array(values):
        extension = ("other", ())
    else:
        extension = ('numpy_type', ())

    header = (block.mgr_locs.as_array, values.dtype, values.shape, extension)
    if extension == ("other", ()):
        bytes = pickle.dumps(values)
    else:
        bytes = pnp.compress(pnp.serialize(values), values.dtype)
    return header, bytes


def block_from_header_bytes(header, bytes):
    placement, dtype, shape, (extension_type, extension_values) = header

    if extension_type == "other":
        values = pickle.loads(bytes)
    else:
        values = pnp.deserialize(pnp.decompress(bytes, dtype), dtype,
                                 copy=True).reshape(shape)
    if extension_type == 'categorical_type':
        values = pd.Categorical.from_codes(values,
                                           extension_values[1],
                                           ordered=extension_values[0])
    elif extension_type == 'datetime64_tz_type':
        tz_info = extension_values[0]
        values = pd.DatetimeIndex(values).tz_localize('utc').tz_convert(
            tz_info)
    return make_block(values, placement=placement)


def serialize(df):
    """ Serialize and compress a Pandas DataFrame

    Uses Pandas blocks, snappy, and blosc to deconstruct an array into bytes
    """
    col_header, col_bytes = index_to_header_bytes(df.columns)
    ind_header, ind_bytes = index_to_header_bytes(df.index)
    headers = [col_header, ind_header]
    bytes = [col_bytes, ind_bytes]

    for block in df._data.blocks:
        h, b = block_to_header_bytes(block)
        headers.append(h)
        bytes.append(b)

    frames = [dumps(headers)] + bytes
    return b''.join(map(frame, frames))


def deserialize(bytes):
    """ Deserialize and decompress bytes back to a pandas DataFrame """
    frames = list(framesplit(bytes))
    headers = pickle.loads(frames[0])
    bytes = frames[1:]
    axes = [index_from_header_bytes(headers[0], bytes[0]),
            index_from_header_bytes(headers[1], bytes[1])]
    blocks = [block_from_header_bytes(h, b)
              for (h, b) in zip(headers[2:], bytes[2:])]
    return pd.DataFrame(create_block_manager_from_blocks(blocks, axes))


def join(dfs):
    if not dfs:
        return pd.DataFrame()
    else:
        return pd.concat(dfs)

PandasBlocks = partial(Encode, serialize, deserialize, join)
