"""Module with numba enhanced functions."""
import numba
import numpy as np
import xarray as xr

from . import _remove_indexes_to_reduce, sort

__all__ = ["histogram", "searchsorted", "ecdf"]


@numba.guvectorize(
    [
        "void(uint8[:], uint8[:], uint8[:])",
        "void(uint16[:], uint16[:], uint16[:])",
        "void(uint32[:], uint32[:], uint32[:])",
        "void(uint64[:], uint64[:], uint64[:])",
        "void(int8[:], int8[:], int8[:])",
        "void(int16[:], int16[:], int16[:])",
        "void(int32[:], int32[:], int32[:])",
        "void(int64[:], int64[:], int64[:])",
        "void(float32[:], float32[:], float32[:])",
        "void(float64[:], float64[:], float64[:])",
    ],
    "(n),(m)->(m)",
    cache=True,
    target="parallel",
    nopython=True,
)
def hist_ufunc(data, bin_edges, res):  # pragma: no cover
    """Use :func:`numba.guvectorize` to convert numpy histogram into a ufunc.

    Notes
    -----
    ``bin_edges`` is a required argument because it is needed to have a valid call
    signature. The shape of the output must be generated from the dimensions available
    in the inputs; they can be in different order, duplicated or reduced, but the output
    can't introduce new dimensions.
    """
    # coverage doesn't seem to recognize that we do call this functions, and I assume
    # it happens with all guvectorized functions, so skipping them from coverage
    # Note: it would be nice to add something to tox.ini about *auto* skipping if guvectorized
    # TODO: check signatures
    m = len(bin_edges)
    res[:] = 0
    aux, _ = np.histogram(data, bins=bin_edges)
    for i in numba.prange(m - 1):
        res[i] = aux[i]


def histogram(da, dims, bins=None, density=False, **kwargs):
    """Numbify :func:`numpy.histogram` to suport vectorized histograms.

    Parameters
    ----------
    da : DataArray
        Data to be binned.
    dims : str or list of str
        Dimensions that should be reduced by binning.
    bins : array_like, int or str, optional
        Passed to :func:`numpy.histogram_bin_edges`. If ``None`` (the default)
        ``histogram_bin_edges`` is called without arguments. Bin edges
        are shared by all generated histograms.
    density : bool, optional
        If ``False``, the result will contain the number of samples in each bin.
        If ``True``, the result is the value of the probability density function at the bin,
        normalized such that the integral over the range is 1.
        Note that the sum of the histogram values will not be equal to 1 unless
        bins of unity width are chosen; it is not a probability mass function.
    kwargs : dict, optional
        Passed to :func:`xarray.apply_ufunc`

    Returns
    -------
    DataArray
        Returns a DataArray with the histogram results. The dimensions provided
        in ``dims`` are reduced into a ``bin`` dimension (without coordinates).
        The bin edges are returned as coordinate values indexed by the dimension
        ``bin``, left bin edges are stored as ``left_edges`` right ones as
        ``right_edges``.

    Examples
    --------
    Use `histogram` to compute multiple histograms in a vectorized fashion, binning
    along both `chain` and `draw` dimensions but not the `match` one. Consequently,
    `histogram` generates one independent histogram per `match`:

    .. jupyter-execute::

        from xarray_einstats import tutorial, numba
        ds = tutorial.generate_mcmc_like_dataset(3)
        numba.histogram(ds["score"], dims=("chain", "draw"))

    Note how the return is a single DataArray, not an array with the histogram and another
    with the bin edges. That is because the bin edges are included as coordinate values.

    See Also
    --------
    xhistogram.xarray.histogram :
        Alternative implementation (with some different features) of xarray aware histogram.
    """
    # TODO: make dask compatible even when bin edges are not passed manually
    if bins is None:
        bin_edges = np.histogram_bin_edges(da.values.flatten())
    elif isinstance(bins, (str, int)):
        bin_edges = np.histogram_bin_edges(da.values.flatten(), bins=bins)
    else:
        bin_edges = bins
    if not isinstance(dims, str):
        aux_dim = f"__hist_dim__:{','.join(dims)}"
        da = _remove_indexes_to_reduce(da, dims).stack({aux_dim: dims})
        dims = aux_dim
    histograms = xr.apply_ufunc(
        hist_ufunc,
        da,
        bin_edges,
        input_core_dims=[[dims], ["bin"]],
        output_core_dims=[["bin"]],
        **kwargs,
    )
    histograms = histograms.isel({"bin": slice(None, -1)}).assign_coords(
        left_edges=("bin", bin_edges[:-1]), right_edges=("bin", bin_edges[1:])
    )
    if density:
        return histograms / (
            histograms.sum("bin") * (histograms.right_edges - histograms.left_edges)
        )
    return histograms


@numba.guvectorize(
    [
        "void(uint8[:], uint8[:], uint8[:])",
        "void(uint16[:], uint16[:], uint16[:])",
        "void(uint32[:], uint32[:], uint32[:])",
        "void(uint64[:], uint64[:], uint64[:])",
        "void(int8[:], int8[:], int8[:])",
        "void(int16[:], int16[:], int16[:])",
        "void(int32[:], int32[:], int32[:])",
        "void(int64[:], int64[:], int64[:])",
        "void(float32[:], float32[:], float32[:])",
        "void(float64[:], float64[:], float64[:])",
    ],
    "(n),(m)->(m)",
    cache=True,
    target="parallel",
    nopython=True,
)
def searchsorted_ufunc(da, v, res):  # pragma: no cover
    """Use :func:`numba.guvectorize` to convert numpy searchsorted into a vectorized ufunc.

    Notes
    -----
    As of now, its only intended use is in for `ecdf`, so the `side` is
    hardcoded and the rest of the library will assume so.
    """
    res[:] = np.searchsorted(da, v, side="right")


def searchsorted(da, v, dims=None, **kwargs):
    """Numbify :func:`numpy.searchsorted` to support vectorized computations.

    Parameters
    ----------
    da : DataArray
        Input data
    v : DataArray
        The values to insert into `da`.
    dims : str or iterable of str, optional
        The dimensions over which to apply the searchsort. Computation
        will be parallelized over the rest with numba.
    **kwargs : dict, optional
        Keyword arguments passed as-is to :func:`xarray.apply_ufunc`.

    Notes
    -----
    It has been designed to be used by :func:`~xarray_einstats.numba.ecdf`,
    so its setting of input and output core dims makes some assumptions
    based on that, it doesn't aim to be general use vectorized/parallelized
    searchsorted.
    """
    if dims is None:
        dims = [d for d in da.dims if d not in v.dims]
    if not isinstance(dims, str):
        aux_dim = f"__aux_dim__:{','.join(dims)}"
        da = _remove_indexes_to_reduce(da, dims).stack({aux_dim: dims}, create_index=False)
        core_dims = [aux_dim]
    else:
        aux_dim = dims
        core_dims = [dims]

    v_dims = [d for d in v.dims if d not in da.dims]

    return xr.apply_ufunc(
        searchsorted_ufunc,
        sort(da, dim=aux_dim),
        v,
        input_core_dims=[core_dims, v_dims],
        output_core_dims=[v_dims],
        **kwargs,
    )


def ecdf(da, dims=None, *, npoints=None, **kwargs):
    """Compute the x and y values of ecdf plots in a vectorized way.

    Parameters
    ----------
    da : DataArray
        Input data containing the samples on which we want to compute the ecdf.
    dims : str or iterable of str, optional
        Dimensions over which the ecdf should be computed. They are flattened
        and converted to a ``quantile`` dimension that contains the values
        to plot; the other dimensions should be used for facetting and aesthetics.
        The default is computing the ecdf over the flattened input.
    npoints : int, optional
        Number of points on which to evaluate the ecdf. It defaults
        to the minimum between 200 and the total number of points in each
        block defined by `dims`.
    **kwargs : dict, optional
        Keyword arguments passed as-is to :func:`xarray.apply_ufunc` through
        :func:`~xarray_einstats.numba.searchsorted`.

    Returns
    -------
    Dataset
        Dataset with two data variables: ``x`` and ``y`` with the values to plot.

    Examples
    --------
    Compute and plot the ecdf over all the data:

    .. plot::
       :context: close-figs

        from xarray_einstats import tutorial, numba
        import matplotlib.pyplot as plt

        ds = tutorial.generate_mcmc_like_dataset(3)
        out = numba.ecdf(ds["mu"], dims=("chain", "draw", "team"))
        plt.plot(out["x"], out["y"], drawstyle="steps-post");

    Compute vectorized ecdf values to plot multiple subplots and
    multiple lines in each with different hue:

    .. plot::
       :context: close-figs

        out = numba.ecdf(ds["mu"], dims="draw")
        out["y"].assign_coords(x=out["x"]).plot.line(
            x="x", hue="chain", col="team", col_wrap=3, drawstyle="steps-post"
        );

    Warnings
    --------
    New and experimental feature, its API might change.

    """
    if dims is None:
        dims = da.dims
    elif isinstance(dims, str):
        dims = [dims]
    total_points = np.product([da.sizes[d] for d in dims])
    if npoints is None:
        npoints = min(total_points, 200)
    x = xr.DataArray(np.linspace(0, 1, npoints), dims=["quantile"])
    max_da = da.max(dims)
    min_da = da.min(dims)
    x = (max_da - min_da) * x + min_da

    y = searchsorted(da, x, dims=dims, **kwargs) / total_points
    return xr.Dataset({"x": x, "y": y})
