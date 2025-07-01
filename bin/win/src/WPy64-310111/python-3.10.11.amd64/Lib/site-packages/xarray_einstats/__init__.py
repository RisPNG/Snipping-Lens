"""Stats, linear algebra and einops for xarray."""

from __future__ import annotations

import numpy as np
import xarray as xr

from .linalg import einsum, raw_einsum, einsum_path, matmul

__all__ = ["einsum", "raw_einsum", "einsum_path", "matmul", "zeros_ref", "ones_ref", "empty_ref"]

__version__ = "0.5.1"


def sort(da, dim, **kwargs):
    """Sort along dimension using DataArray values."""
    sort_kwargs = dict(axis=-1)
    if "kind" in kwargs:
        sort_kwargs["kind"] = kwargs.pop("kind")
    return xr.apply_ufunc(
        np.sort,
        da,
        input_core_dims=[[dim]],
        output_core_dims=[[dim]],
        kwargs=sort_kwargs,
        **kwargs,
    )


def _remove_indexes_to_reduce(da, dims):
    """Remove indexes related to provided dims.

    Removes indexes related to dims on which we need to operate.
    As many functions only support integer `axis` or None,
    in order to have our functions operate on multiple dimensions
    we need to stack/flatten them. If some of those dimensions
    are already indexed by a multiindex this doesn't work, so we
    remove the indexes. As they are reduced, that information
    will end up being lost eventually either way.
    """
    index_keys = list(da.indexes)
    remove_indicator = [
        (any(da.indexes[k] is index for k in index_keys if k in dims))
        for name, index in da.indexes.items()
    ]
    indexes_to_remove = [k for k, remove in zip(index_keys, remove_indicator) if remove]
    da = da.drop_indexes(indexes_to_remove)
    coords_to_remove = [coord for coord in da.coords if coord in indexes_to_remove or coord in dims]
    return da.reset_coords(coords_to_remove, drop=True)


def _find_index(elem, to_search_in):
    for i, da in enumerate(to_search_in):
        if elem in da.dims:
            return (i, elem)
    raise ValueError(f"{elem} not found in any reference object")


def _create_ref(*args, dims, np_creator, dtype=None):
    if dtype is None and all(isinstance(arg, xr.DataArray) for arg in args):
        dtype = np.result_type(*[arg.dtype for arg in args])
    ref_idxs = [_find_index(dim, args) for dim in dims]
    shape = [len(args[idx][dim]) for idx, dim in ref_idxs]
    # TODO: keep non indexing coords?
    coords = {dim: args[idx][dim] for idx, dim in ref_idxs if dim in args[idx].coords}
    return xr.DataArray(
        np_creator(shape, dtype=dtype),
        dims=dims,
        coords=coords,
    )


def zeros_ref(*args, dims, dtype=None):
    """Create a zeros DataArray from reference object(s).

    Creates a DataArray filled with zeros from reference
    DataArrays or Datasets and a list with the desired dimensions.

    Parameters
    ----------
    *args : iterable of DataArray or Dataset
        Reference objects from which the lengths and coordinate values (if any)
        of the given `dims` will be taken.
    dims : list of hashable
        List of dimensions of the output DataArray. Passed as is to the
        {class}`~xarray.DataArray` constructor.
    dtype : dtype, optional
        The dtype of the output array.
        If it is not provided it will be inferred from the reference
        DataArrays in `args` with :func:`numpy.result_type`.

    Returns
    -------
    DataArray

    See Also
    --------
    ones_ref, empty_ref
    """
    return _create_ref(*args, dims=dims, np_creator=np.zeros, dtype=dtype)


def empty_ref(*args, dims, dtype=None):
    """Create an empty DataArray from reference object(s).

    Creates an empty DataArray from reference
    DataArrays or Datasets and a list with the desired dimensions.

    Parameters
    ----------
    *args : iterable of DataArray or Dataset
        Reference objects from which the lengths and coordinate values (if any)
        of the given `dims` will be taken.
    dims : list of hashable
        List of dimensions of the output DataArray. Passed as is to the
        {class}`~xarray.DataArray` constructor.
    dtype : dtype, optional
        The dtype of the output array.
        If it is not provided it will be inferred from the reference
        DataArrays in `args` with :func:`numpy.result_type`.

    Returns
    -------
    DataArray

    See Also
    --------
    ones_ref, zeros_ref
    """
    return _create_ref(*args, dims=dims, np_creator=np.empty, dtype=dtype)


def ones_ref(*args, dims, dtype=None):
    """Create a ones DataArray from reference object(s).

    Creates a DataArray filled with ones from reference
    DataArrays or Datasets and a list with the desired dimensions.

    Parameters
    ----------
    *args : iterable of DataArray or Dataset
        Reference objects from which the lengths and coordinate values (if any)
        of the given `dims` will be taken.
    dims : list of hashable
        List of dimensions of the output DataArray. Passed as is to the
        {class}`~xarray.DataArray` constructor.
    dtype : dtype, optional
        The dtype of the output array.
        If it is not provided it will be inferred from the reference
        DataArrays in `args` with :func:`numpy.result_type`.

    Returns
    -------
    DataArray

    See Also
    --------
    empty_ref, zeros_ref
    """
    return _create_ref(*args, dims=dims, np_creator=np.ones, dtype=dtype)
