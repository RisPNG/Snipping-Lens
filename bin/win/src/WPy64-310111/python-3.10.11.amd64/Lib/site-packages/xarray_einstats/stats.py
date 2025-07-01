# pylint: disable=too-few-public-methods
"""Wrappers for :mod:`scipy.stats` distributions."""

from collections.abc import Sequence

import numpy as np
import xarray as xr
from numpy.linalg import LinAlgError
from scipy import special, stats

from . import _remove_indexes_to_reduce
from .linalg import cholesky, eigh

__all__ = [
    "XrContinuousRV",
    "XrDiscreteRV",
    "multivariate_normal",
    "circmean",
    "circstd",
    "circvar",
    "gmean",
    "hmean",
    "kurtosis",
    "rankdata",
    "skew",
]


def get_default_dims(dims):
    """Get default dims on which to perfom an operation.

    Whenever a function from :mod:`xarray_einstats.stats` is called with
    ``dims=None`` (the default) this function is called to choose the
    default dims on which to operate out of the list with all the dims present.

    This function is thought to be monkeypatched by domain specific applications
    as shown in the examples.

    Parameters
    ----------
    dims : list of str
        List with all the dimensions of the input DataArray in the order they
        appear.

    Returns
    -------
    list of str
        List with the dimensions on which to apply the operation.
        ``xarray_einstats`` defaults to applying the operation to all
        dimensions. Monkeypatch this function to get a different result.

    Examples
    --------
    The ``xarray_einstats`` default behaviour is operating (averaging in this case)
    over all dimensions present in the input DataArray:

    .. jupyter-execute::

        from xarray_einstats import stats, tutorial
        da = tutorial.generate_mcmc_like_dataset(3)["mu"]
        stats.hmean(da)

    Here we show how to monkeypatch ``get_default_dims`` to get a different default
    behaviour. If you use ``xarray_einstats`` and {doc}`arviz:index` to work
    with MCMC results, operating over chain and dim only might be a better default:

    .. jupyter-execute::

        def get_default_dims(dims):
            out = [dim for dim in ("chain", "draw") if dim in dims]
            if not out:  # if chain nor draw are present fall back to all dims
                return dims
            return out
        stats.get_default_dims = get_default_dims
        stats.hmean(da)

    You can still use ``dims`` explicitly to average over any custom dimension

    .. jupyter-execute::

        stats.hmean(da, dims="team")

    """
    return dims


def _asdataarray(x_or_q, dim_name):
    """Ensure input is a DataArray.

    This is designed for the x or q arguments in univariate distributions.
    It is also used in multivariate normal distribution but only as a fallback.
    """
    if isinstance(x_or_q, xr.DataArray):
        return x_or_q
    x_or_q_ary = np.asarray(x_or_q)
    if x_or_q_ary.ndim == 0:
        return xr.DataArray(x_or_q_ary)
    if x_or_q_ary.ndim == 1:
        return xr.DataArray(x_or_q_ary, dims=[dim_name], coords={dim_name: np.asarray(x_or_q)})
    raise ValueError(
        "To evaluate distribution methods on data with >=2 dims,"
        " the input needs to be a xarray.DataArray"
    )


def _wrap_method(method):
    def aux(self, *args, apply_kwargs=None, **kwargs):
        dim_name = "quantile" if method in {"ppf", "isf"} else "point"
        if apply_kwargs is None:
            apply_kwargs = {}
        meth = getattr(self.dist, method)
        if args:
            args = (_asdataarray(args[0], dim_name), *args[1:])
        args, kwargs = self._broadcast_args(args, kwargs)  # pylint: disable=protected-access
        return xr.apply_ufunc(meth, *args, kwargs=kwargs, **apply_kwargs)

    return aux


class XrRV:
    """Base random variable wrapper class.

    Most methods have a common signature between continuous and
    discrete variables in scipy. We define a base wrapper and
    then subclass it to add the specific methods like pdf or pmf.

    Notes
    -----
    One of the main goals of this library is ease of maintenance.
    We could wrap each distribution to preserve call signatures
    and avoid different behaviour between passing input arrays
    as args or kwargs, but so far we don't consider what we'd won
    doing this to be worth the extra maintenance burden.
    """

    def __init__(self, dist, *args, **kwargs):
        self.dist = dist
        self.args = args
        self.kwargs = kwargs

    def _broadcast_args(self, args, kwargs):
        """Broadcast and combine initialization and method provided args and kwargs."""
        len_args = len(args) + len(self.args)
        all_args = [*args, *self.args, *kwargs.values(), *self.kwargs.values()]
        broadcastable = []
        non_broadcastable = []
        b_idx = []
        n_idx = []
        for i, a in enumerate(all_args):
            if isinstance(a, xr.DataArray):
                broadcastable.append(a)
                b_idx.append(i)
            else:
                non_broadcastable.append(a)
                n_idx.append(i)
        broadcasted = list(xr.broadcast(*broadcastable))
        all_args = [
            x
            for x, _ in sorted(
                zip(broadcasted + non_broadcastable, b_idx + n_idx),
                key=lambda pair: pair[1],
            )
        ]
        all_keys = list(kwargs.keys()) + list(self.kwargs.keys())
        args = all_args[:len_args]
        kwargs = dict(zip(all_keys, all_args[len_args:]))
        return args, kwargs

    def rvs(self, *args, size=1, random_state=None, dims=None, apply_kwargs=None, **kwargs):
        """Implement base rvs method.

        In scipy, rvs has a common signature that doesn't depend on continuous
        or discrete, so we can define it here.
        """
        args, kwargs = self._broadcast_args(args, kwargs)
        size_in = tuple()
        dims_in = tuple()
        for a in (*args, *kwargs.values()):
            if isinstance(a, xr.DataArray):
                size_in = a.shape
                dims_in = a.dims
                break

        if isinstance(dims, str):
            dims = [dims]

        if isinstance(size, (Sequence, np.ndarray)):
            if dims is None:
                dims = [f"rv_dim{i}" for i, _ in enumerate(size)]
            if len(dims) != len(size):
                raise ValueError("dims and size must have the same length")
            size = (*size, *size_in)
        elif size > 1:
            if dims is None:
                dims = ["rv_dim0"]
            if len(dims) != 1:
                raise ValueError("dims and size must have the same length")
            size = (size, *size_in)
        else:
            if size_in:
                size = size_in
            dims = None

        if dims is None:
            dims = tuple()

        if apply_kwargs is None:
            apply_kwargs = {}

        return xr.apply_ufunc(
            self.dist.rvs,
            *args,
            kwargs={**kwargs, "size": size, "random_state": random_state},
            input_core_dims=[dims_in for _ in args],
            output_core_dims=[[*dims, *dims_in]],
            **apply_kwargs,
        )


class XrContinuousRV(XrRV):
    """Wrapper for subclasses of :class:`~scipy.stats.rv_continuous`.

    Usage examples available at :ref:`stats_tutorial`

    See Also
    --------
    xarray_einstats.stats.XrDiscreteRV

    Examples
    --------
    Evaluate the ppf of a Student-T distribution from DataArrays that need
    broadcasting:

    .. jupyter-execute::

        from xarray_einstats import tutorial
        from xarray_einstats.stats import XrContinuousRV
        from scipy import stats
        ds = tutorial.generate_mcmc_like_dataset(3)
        dist = XrContinuousRV(stats.t, 3, ds["mu"], ds["sigma"])
        dist.ppf([.1, .5, .6])

    """


class XrDiscreteRV(XrRV):
    """Wrapper for subclasses of :class:`~scipy.stats.rv_discrete`.

    Usage examples available at :ref:`stats_tutorial`

    See Also
    --------
    xarray_einstats.stats.XrDiscreteRV

    Examples
    --------
    Evaluate the ppf of a Student-T distribution from DataArrays that need
    broadcasting:

    .. jupyter-execute::

        from xarray_einstats import tutorial
        from xarray_einstats.stats import XrDiscreteRV
        from scipy import stats
        ds = tutorial.generate_mcmc_like_dataset(3)
        dist = XrDiscreteRV(stats.poisson, ds["mu"])
        dist.ppf([.1, .5, .6])

    """


def _add_documented_method(cls, wrapped_cls, methods, extra_docs=None):
    """Register methods to XrRV classes and document them from a template."""
    if extra_docs is None:
        extra_docs = {}
    for method_name in methods:
        extra_doc = extra_docs.get(method_name, "")
        if method_name == "rvs":
            if wrapped_cls == "rv_generic":
                continue
            method = cls.rvs
        else:
            method = _wrap_method(method_name)
        setattr(
            method,
            "__doc__",
            f"Method wrapping :meth:`scipy.stats.{wrapped_cls}.{method_name}` "
            "with :func:`xarray.apply_ufunc`\n\nUsage examples available at "
            f":ref:`stats_tutorial/dists`.\n\n{extra_doc}",
        )
        setattr(cls, method_name, method)


doc_extras = dict(
    rvs="""
Parameters
----------
args : scalar or array_like, optional
    Passed to the scipy distribution after broadcasting.
size : int of sequence of ints, optional
    The number of samples to draw *per array element*. If the distribution
    parameters broadcast to a ``(4, 10, 6)`` shape and ``size=(5, 3)`` then
    the output shape is ``(5, 3, 4, 10, 6)``. This differs from the scipy
    implementation. Here, all broadcasting and alignment is done for you,
    you give the dimensions the right names, and broadcasting just happens.
    If ``size`` followed scipy behaviour, you'd be forced to broadcast
    to provide a valid value which would defeat the ``xarray_einstats`` goal
    of handling all alignment and broadcasting for you.
random_state : optional
    Passed as is to the wrapped scipy distribution
dims : str or sequence of str, optional
    Dimension names for the dimensions created due to ``size``. If present
    it must have the same length as ``size``.
apply_kwargs : dict, optional
    Passed to :func:`xarray.apply_ufunc`
kwargs : dict, optional
    Passed to the scipy distribution after broadcasting using the same key.
"""
)
base_methods = ["cdf", "logcdf", "sf", "logsf", "ppf", "isf", "rvs"]
_add_documented_method(XrRV, "rv_generic", base_methods, doc_extras)
_add_documented_method(
    XrContinuousRV, "rv_continuous", base_methods + ["pdf", "logpdf"], doc_extras
)
_add_documented_method(XrDiscreteRV, "rv_discrete", base_methods + ["pmf", "logpmf"], doc_extras)


class multivariate_normal:  # pylint: disable=invalid-name
    """An xarray aware multivariate normal random variable.

    Notes
    -----
    This currently is **not** a wrapper of :class:`scipy.stats.multivariate_normal`.
    It only implements a subset of the features. The reason for reimplementing
    some of the features instead of wrapping scipy or numpy is that neither
    is capable of handling batched inputs yet.
    """

    def __init__(self, mean=None, cov=None, dims=None):
        """Initialize the multivariate_normal class."""
        self.mean = mean
        self.cov = cov
        self.dims = dims

    def _process_inputs(self, mean, cov, dims):
        base_error = (
            "No value found for parameter {param}. It needs to be defined either at class "
            "initialization time or when calling its methods"
        )
        mean = mean if mean is not None else self.mean
        if mean is None:
            raise ValueError(base_error.format(param="mean"))
        cov = cov if cov is not None else self.cov
        if cov is None:
            raise ValueError(base_error.format(param="cov"))
        dims = dims if dims is not None else self.dims
        if dims is None:
            raise ValueError(base_error.format(param="dims"))
        if len(dims) != 2:
            raise ValueError("dims must be an iterable of length 2")
        dim1, dim2 = dims
        if dim1 not in mean.dims:
            raise ValueError(f"{dim1} not found in DataArray provided as mean")
        if (dim1 not in cov.dims) or (dim2 not in cov.dims):
            raise ValueError(
                "Some dimensions provided in `dims` were not found in DataArray provided as `mean`"
            )

        return mean, cov, dims

    def rvs(self, mean=None, cov=None, dims=None, *, size=1, rv_dims=None, random_state=None):
        """Generate random samples from a multivariate normal."""
        mean, cov, dims = self._process_inputs(mean, cov, dims)
        dim1, dim2 = dims

        try:
            cov_chol = cholesky(cov, dims=dims)
        except LinAlgError:
            k = len(cov[dim1])
            eye = xr.DataArray(np.eye(k), dims=list(dims))
            cov_chol = cholesky(cov + 1e-10 * eye, dims=dims)
        std_norm = XrContinuousRV(stats.norm, xr.zeros_like(mean.rename({dim1: dim2})), 1)
        samples = std_norm.rvs(size=size, dims=rv_dims, random_state=random_state)
        return mean + xr.dot(cov_chol, samples, dims=dim2)

    def logpdf(self, x, mean=None, cov=None, dims=None):
        """Evaluate the logarithm of the multivariate normal probability density function."""
        x = _asdataarray(x, "point")
        mean, cov, dims = self._process_inputs(mean, cov, dims)
        dim1, dim2 = dims

        k = len(mean[dim1])
        vals, vecs = eigh(cov, dims=dims)
        logdet_cov = np.log(vals).sum(dim=dim2)
        u_mat = vecs * np.sqrt(1.0 / vals.rename({dim2: dim1}))
        x_mu = x - mean
        maha = np.square(xr.dot(x_mu.rename({dim1: dim2}), u_mat, dims=dim2)).sum(dim=dim1)
        return -0.5 * (k * np.log(2 * np.pi) + maha + logdet_cov)

    def pdf(self, x, mean=None, cov=None, dims=None):
        """Evaluate the multivariate normal probability density function."""
        return np.exp(self.logpdf(x, mean, cov, dims))


def _apply_nonreduce_func(func, da, dims, kwargs, func_kwargs=None):
    """Help wrap functions with a single input that return an output with the same size."""
    unstack = False

    if dims is None:
        dims = get_default_dims(da.dims)
    if not isinstance(dims, str):
        aux_dim = f"__aux_dim__:{','.join(dims)}"
        da = _remove_indexes_to_reduce(da, dims).stack({aux_dim: dims})
        core_dims = [aux_dim]
        unstack = True
    else:
        core_dims = [dims]
    out_da = xr.apply_ufunc(
        func,
        da,
        input_core_dims=[core_dims],
        output_core_dims=[core_dims],
        kwargs=func_kwargs,
        **kwargs,
    )
    if unstack:
        return _remove_indexes_to_reduce(out_da.unstack(aux_dim), dims).reindex_like(da)
    return out_da


def _apply_reduce_func(func, da, dims, kwargs, func_kwargs=None):
    """Help wrap functions with a single input that return an output after reducing some dimensions.

    It assumes that the function to be applied only takes ``int`` as ``axis`` and stacks multiple
    dimensions if necessary to support reducing multiple dimensions at once.
    """
    if dims is None:
        dims = get_default_dims(da.dims)
    if not isinstance(dims, str):
        aux_dim = f"__aux_dim__:{','.join(dims)}"
        da = _remove_indexes_to_reduce(da, dims).stack({aux_dim: dims}, create_index=False)
        core_dims = [aux_dim]
    else:
        core_dims = [dims]
    out_da = xr.apply_ufunc(
        func, da, input_core_dims=[core_dims], output_core_dims=[[]], kwargs=func_kwargs, **kwargs
    )
    return out_da


def rankdata(da, dims=None, *, method=None, **kwargs):
    """Wrap and extend :func:`scipy.stats.rankdata`.

    Usage examples available at :ref:`stats_tutorial`

    See Also
    --------
    xarray.DataArray.rank : Similar function but without a ``method`` argument available.
    """
    rank_kwargs = {"axis": -1}
    if method is not None:
        rank_kwargs["method"] = method
    return _apply_nonreduce_func(stats.rankdata, da, dims, kwargs, rank_kwargs)


def gmean(da, dims=None, dtype=None, *, weights=None, **kwargs):
    """Wrap and extend :func:`scipy.stats.gmean`.

    Usage examples available at :ref:`stats_tutorial`
    """
    gmean_kwargs = {"axis": -1}
    if dtype is not None:
        gmean_kwargs["dtype"] = dtype
    if weights is not None:
        gmean_kwargs["weights"] = weights
    return _apply_reduce_func(stats.gmean, da, dims, kwargs, gmean_kwargs)


def hmean(da, dims=None, *, dtype=None, **kwargs):
    """Wrap and extend :func:`scipy.stats.hmean`.

    Usage examples available at :ref:`stats_tutorial`
    """
    hmean_kwargs = {"axis": -1}
    if dtype is not None:
        hmean_kwargs["dtype"] = dtype
    return _apply_reduce_func(stats.hmean, da, dims, kwargs, hmean_kwargs)


def circmean(da, dims=None, *, high=2 * np.pi, low=0, nan_policy=None, **kwargs):
    """Wrap and extend :func:`scipy.stats.circmean`.

    Usage examples available at :ref:`stats_tutorial`
    """
    circmean_kwargs = dict(axis=-1, high=high, low=low)
    if nan_policy is not None:
        circmean_kwargs["nan_policy"] = nan_policy
    return _apply_reduce_func(stats.circmean, da, dims, kwargs, circmean_kwargs)


def circvar(da, dims=None, *, high=2 * np.pi, low=0, nan_policy=None, **kwargs):
    """Wrap and extend :func:`scipy.stats.circvar`.

    Usage examples available at :ref:`stats_tutorial`
    """
    circvar_kwargs = dict(axis=-1, high=high, low=low)
    if nan_policy is not None:
        circvar_kwargs["nan_policy"] = nan_policy
    return _apply_reduce_func(stats.circvar, da, dims, kwargs, circvar_kwargs)


def circstd(da, dims=None, *, high=2 * np.pi, low=0, nan_policy=None, **kwargs):
    """Wrap and extend :func:`scipy.stats.circstd`.

    Usage examples available at :ref:`stats_tutorial`
    """
    circstd_kwargs = dict(axis=-1, high=high, low=low)
    if nan_policy is not None:
        circstd_kwargs["nan_policy"] = nan_policy
    return _apply_reduce_func(stats.circstd, da, dims, kwargs, circstd_kwargs)


def kurtosis(da, dims=None, *, fisher=True, bias=True, nan_policy=None, **kwargs):
    """Wrap and extend :func:`scipy.stats.kurtosis`.

    Usage examples available at :ref:`stats_tutorial`
    """
    kurtosis_kwargs = dict(axis=-1, fisher=fisher, bias=bias)
    if nan_policy is not None:
        kurtosis_kwargs["nan_policy"] = nan_policy
    return _apply_reduce_func(stats.kurtosis, da, dims, kwargs, kurtosis_kwargs)


def skew(da, dims=None, *, bias=True, nan_policy=None, **kwargs):
    """Wrap and extend :func:`scipy.stats.skew`.

    Usage examples available at :ref:`stats_tutorial`
    """
    skew_kwargs = dict(axis=-1, bias=bias)
    if nan_policy is not None:
        skew_kwargs["nan_policy"] = nan_policy
    return _apply_reduce_func(stats.skew, da, dims, kwargs, skew_kwargs)


def logsumexp(da, dims=None, *, b=True, return_sign=False, **kwargs):
    """Wrap and extend :func:`scipy.special.logsumexp`.

    Usage examples available at :ref:`stats_tutorial`
    """
    if dims is None:
        dims = get_default_dims(da.dims)
    if not isinstance(dims, str):
        core_dims = dims
        axis = tuple(-1 - i for i in reversed(range(len(dims))))
    else:
        core_dims = [dims]
        axis = -1

    if return_sign:
        out_dims = [[], []]
    else:
        out_dims = [[]]

    b_dims = []
    b_dims_to_keep = []
    if isinstance(b, xr.DataArray):
        b_dims_to_keep = [d for d in b.dims if d in da.dims and d not in core_dims]
        b_dims = [d for d in b.dims if d in core_dims]
        out_dims[0].extend(b_dims_to_keep)

    try:
        return xr.apply_ufunc(
            lambda a, b, **kwargs: special.logsumexp(a, b=b, **kwargs),
            da,
            b,
            input_core_dims=[b_dims_to_keep + core_dims, b_dims_to_keep + b_dims],
            output_core_dims=out_dims,
            kwargs=dict(return_sign=return_sign, axis=axis),
            **kwargs,
        )
    except ValueError:
        out_dims[0] = []
        return xr.apply_ufunc(
            lambda a, b, **kwargs: special.logsumexp(a, b=b, **kwargs),
            *xr.broadcast(da, b),
            input_core_dims=[core_dims, core_dims],
            output_core_dims=out_dims,
            kwargs=dict(return_sign=return_sign, axis=axis),
            **kwargs,
        )


def median_abs_deviation(da, dims=None, *, center=None, scale=1, nan_policy=None, **kwargs):
    """Wrap and extend :func:`scipy.stats.median_abs_deviation`.

    Usage examples available at :ref:`stats_tutorial`.

    All parameters take the same values and types as the scipy counterpart
    with the exception of ``scale``. Here ``scale`` can also take
    :class:`~xarray.DataArray` values in which case, broadcasting
    is handled by xarray, as shown in the example.


    Examples
    --------
    Use a ``DataArray`` as ``scale``.

    .. jupyter-execute::

        import xarray as xr
        from xarray_einstats import tutorial, stats
        ds = tutorial.generate_mcmc_like_dataset(3)
        s_da = xr.DataArray([1, 2, 1, 1], coords={"chain": ds.chain})
        stats.median_abs_deviation(ds["mu"], dims="draw", scale=s_da)

    Note that this doesn't work with the scipy counterpart because
    `s_da` can't be broadcasted with the output:

    .. jupyter-execute::
        :raises: ValueError

        from scipy import stats
        stats.median_abs_deviation(ds["mu"], axis=1, scale=s_da)

    """
    mad_kwargs = dict(axis=-1)
    if center is not None:
        mad_kwargs["center"] = center
    if nan_policy is not None:
        mad_kwargs["nan_policy"] = nan_policy

    if dims is None:
        dims = get_default_dims(da.dims)
    if not isinstance(dims, str):
        aux_dim = f"__aux_dim__:{','.join(dims)}"
        da = _remove_indexes_to_reduce(da, dims).stack({aux_dim: dims})
        core_dims = [aux_dim]
    else:
        core_dims = [dims]

    scale_dims = []
    if isinstance(scale, xr.DataArray):
        scale_dims = [d for d in scale.dims if d in core_dims]

    return xr.apply_ufunc(
        lambda a, s, **kwargs: stats.median_abs_deviation(a, scale=s, **kwargs),
        da,
        scale,
        input_core_dims=[core_dims, scale_dims],
        output_core_dims=[[]],
        kwargs=mad_kwargs,
        **kwargs,
    )
