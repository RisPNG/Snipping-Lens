"""Wrappers for :mod:`numpy.linalg`."""
import numpy as np
import xarray as xr

__all__ = [
    "matrix_power",
    "matrix_transpose",
    "cholesky",
    "qr",
    "svd",
    "eig",
    "eigh",
    "eigvals",
    "eigvalsh",
    "norm",
    "cond",
    "det",
    "matrix_rank",
    "slogdet",
    "trace",
    "diagonal",
    "solve",
    "inv",
]


class MissingMonkeypatchError(Exception):
    """Error specific for the linalg module non-default yet accepted monkeypatch."""


def get_default_dims(da1_dims, d2_dims=None):
    """Get the dimensions corresponding to the matrices.

    Parameters
    ----------
    da1_dims : list of str

    da2_dims : list of str, optional
        Used only in case of multiple inputs, otherwise it will keep its default value of ``None``

    Returns
    -------
    list of str
        The dimensions indicating the matrix dimensions. Must be an iterable
        containing two strings.

    Warnings
    --------
    ``dims`` is required for functions in the linalg module.
    This function acts as a placeholder and only raises an error indicating
    that dims is a required argument unless this function is monkeypatched.

    It is documented here to show how to write and configure a substitute function.

    Examples
    --------
    The ``xarray_einstats`` default behaviour is requiring the `dims` argument
    for functions in the linalg module. Not providing it raises a `TypeError`

    .. jupyter-execute::
        :raises: TypeError

        from xarray_einstats import linalg, tutorial
        da = tutorial.generate_matrices_dataarray(5)
        linalg.inv(da)

    You need to pass the dimensions corresponding the matrix axes explicitly

    .. jupyter-execute::

        linalg.inv(da, dims=["dim", "dim2"])

    However, in many cases it will be possible to identify those dimensions
    from the list of all dimension names in the input.

    Here we show how to monkeypatch ``get_default_dims`` to get a different default
    behaviour. If you follow a convention to label the dimensions corresponding
    to the matrix axes, you can integrate this logic into ``xarray_einstats``,
    which will avoid unnecessary repetition, especially if performing several
    chained linear algebra operations:

    .. jupyter-execute::

        def get_default_dims(dims1, dims2):
            if dims2 is not None:
                raise TypeError("Default dims only valid for single input functions")
            matrix_dims = [dim for dim in dims1 if f"{dim}2" in dims1]
            if len(matrix_dims) != 1:
                raise TypeError("Unable to guess default matrix dims")
            dim = matrix_dims[0]
            return [dim, f"{dim}2"]

        linalg.get_default_dims = get_default_dims
        linalg.inv(da)

    You can still use ``dims`` explicitly to override those defaults.

    """
    raise MissingMonkeypatchError()


def _attempt_default_dims(func, da1_dims, da2_dims=None):
    """Raise a more informative warning."""
    try:
        aux = get_default_dims(da1_dims, da2_dims)
    except MissingMonkeypatchError:
        raise TypeError(
            f"{func} missing required argument dims. You must monkeypatch "
            "xarray_einstats.linalg.get_default_dims for dims=None to be supported"
        ) from None
    return aux


class PairHandler:
    def __init__(self, all_dims, keep_dims):
        self.potential_out_dims = keep_dims.union(all_dims)
        self.einsum_axes = list(
            letter
            for letter in "zyxwvutsrqponmlkjihgfedcba"
            if letter not in self.potential_out_dims
        )
        self.dim_map = {d: self.einsum_axes.pop() for d in all_dims}
        self.out_dims = []
        self.out_subscript = ""

    def process_dim_da_pair(self, da, dim_sublist):
        da_dims = da.dims
        out_dims = [
            dim for dim in da_dims if dim in self.potential_out_dims and dim not in dim_sublist
        ]
        subscripts = ""
        updated_in_dims = dim_sublist.copy()
        for dim in out_dims:
            self.out_dims.append(dim)
            sub = self.einsum_axes.pop()
            self.out_subscript += sub
            subscripts += sub
            updated_in_dims.insert(0, dim)
        for dim in dim_sublist:
            subscripts += self.dim_map[dim]
        if len(da_dims) > len(out_dims) + len(dim_sublist):
            return f"...{subscripts}", updated_in_dims
        return subscripts, updated_in_dims

    def get_out_subscript(self):
        if not self.out_subscript:
            return ""
        return f"->{self.out_subscript}"


def _einsum_parent(dims, *operands, keep_dims=frozenset()):
    """Preprocess inputs to call :func:`numpy.einsum` or :func:`numpy.einsum_path`.

    Parameters
    ----------
    dims : list of list of str
        List of lists of dimension names. It must have the same length or be
        only one item longer than ``operands``. If both have the same
        length, the generated pattern passed to {func}`numpy.einsum`
        won't have ``->`` nor right hand side. Otherwise, the last
        item is assumed to be the dimension specification of the output
        DataArray, and it can be an empty list to add ``->`` but no
        subscripts.
    operands : DataArray
        DataArrays for the operation. Multiple DataArrays are accepted.
    keep_dims : set, optional
        Dimensions to exclude from summation unless specifically specified in ``dims``

    See Also
    --------
    xarray_einstats.einsum, xarray_einstats.einsum_path
    numpy.einsum, numpy.einsum_path
    xarray_einstats.einops.reduce
    """
    if len(dims) == len(operands):
        in_dims = dims
        out_dims = None
    elif len(dims) == len(operands) + 1:
        in_dims = dims[:-1]
        out_dims = dims[-1]
    else:
        raise ValueError("length of dims and operands not compatible")

    all_dims = set(dim for sublist in dims for dim in sublist)
    handler = PairHandler(all_dims, keep_dims)
    in_subscripts = []
    updated_in_dims = []
    for da, sublist in zip(operands, in_dims):
        in_subs, up_dims = handler.process_dim_da_pair(da, sublist)
        in_subscripts.append(in_subs)
        updated_in_dims.append(up_dims)

    in_subscript = ",".join(in_subscripts)
    if out_dims is None:
        out_subscript = handler.get_out_subscript()
        out_dims = handler.out_dims
    elif not out_dims:
        out_subscript = "->"
    else:
        out_subscript = "->" + "".join(handler.dim_map[dim] for dim in out_dims)
    if out_subscript and "..." in in_subscript:
        out_subscript = "->..." + out_subscript[2:]
    subscripts = in_subscript + out_subscript
    return subscripts, updated_in_dims, out_dims


def einsum_path(dims, *operands, keep_dims=frozenset(), optimize=None, **kwargs):
    """Wrap :func:`numpy.einsum_path`.

    See :func:`xarray_einstats.einsum` for a detailed description of ``dims``
    and ``operands``.

    Parameters
    ----------
    dims : list of list of str
    operands : DataArray
    optimize : str, optional
        ``optimize`` argument for :func:`numpy.einsum_path`. It defaults to None so that
        we always default to numpy's default, without needing to keep the call signature
        here up to date.
    kwargs : dict, optional
        Passed to :func:`xarray.apply_ufunc`
    """
    op_kwargs = {} if optimize is None else dict(optimize=optimize)

    subscripts, in_dims, _ = _einsum_parent(dims, *operands, keep_dims=keep_dims)
    updated_in_dims = []
    for sublist, da in zip(in_dims, operands):
        updated_in_dims.append([dim for dim in da.dims if dim not in sublist] + sublist)

    return xr.apply_ufunc(
        np.einsum_path,
        subscripts,
        *operands,
        input_core_dims=[[], *updated_in_dims],
        output_core_dims=[[]],
        kwargs=op_kwargs,
        **kwargs,
    ).values.item()


def einsum(dims, *operands, keep_dims=frozenset(), out_append="{i}", einsum_kwargs=None, **kwargs):
    """Preprocess inputs to call :func:`numpy.einsum` or :func:`numpy.einsum_path`.

    Usage examples of all arguments is available at the
    :ref:`einsum section <linalg_tutorial/einsum>` of the linear algebra module tutorial.

    Parameters
    ----------
    dims : list of list of str
        List of lists of dimension names. It must have the same length or be
        only one item longer than ``operands``. If both have the same
        length, the generated pattern passed to {func}`numpy.einsum`
        won't have ``->`` nor right hand side. Otherwise, the last
        item is assumed to be the dimension specification of the output
        DataArray, and it can be an empty list to add ``->`` but no
        subscripts.
    operands : DataArray
        DataArrays for the operation. Multiple DataArrays are accepted.
    keep_dims : set, optional
        Dimensions to exclude from summation unless specifically specified in ``dims``
    out_append : str, optional
        Pattern to append to repeated dimension names in the output (if any). The pattern should
        contain a substitution for variable ``i``, which indicates the number of the current
        dimension among the repeated ones. Its default value is ``"{i}"``.
        To keep repeated dimension names use ``""``.

        The first occurrence will keep the original name and not use ``out_append``.
        It will therefore inherit the coordinate values in case there were any.
    einsum_kwargs : dict, optional
        Passed to :func:`numpy.einsum`
    kwargs : dict, optional
        Passed to :func:`xarray.apply_ufunc`

    Notes
    -----
    Dimensions present in ``dims`` will be reduced, but unlike {func}`xarray.dot` it does so only
    for that variable.

    """
    if einsum_kwargs is None:
        einsum_kwargs = {}

    subscripts, updated_in_dims, out_dims = _einsum_parent(dims, *operands, keep_dims=keep_dims)

    updated_out_dims = []
    for i, dim in enumerate(out_dims):
        totalcount = out_dims.count(dim)
        count = out_dims[:i].count(dim) + 1
        updated_out_dims.append(
            dim + out_append.format(i=count) if (totalcount > 1) and (count > 1) else dim
        )
    return xr.apply_ufunc(
        np.einsum,
        subscripts,
        *operands,
        input_core_dims=[[], *updated_in_dims],
        output_core_dims=[updated_out_dims],
        kwargs=einsum_kwargs,
        **kwargs,
    )


def raw_einsum(
    subscripts, *operands, keep_dims=frozenset(), out_append="{i}", einsum_kwargs=None, **kwargs
):
    """Wrap :func:`numpy.einsum` crudely.

    Usage examples of all arguments is available at the
    :ref:`einsum section <linalg_tutorial/einsum>` of the linear algebra module tutorial.

    The description of all the arguments except `subscripts` is available at
    :func:`xarray_einstats.einsum`.

    Parameters
    ----------
    subscripts : str
        Specify the subscripts for the summation as dimension names. Spaces indicate
        multiple dimensions in a DataArray and commas indicate multiple DataArray
        operands. Only dimensions with no spaces, nor commas nor ``->`` characters
        are valid.
    operands : DataArray
    keep_dims : set, optional
    out_append : str, optional
    einsum_kwargs : dict, optional
    kwargs : optional
    """
    if "->" in subscripts:
        in_subscripts, out_subscript = subscripts.split("->")
    else:
        in_subscripts = subscripts
        out_subscript = None
    in_dims = [
        [dim.strip(", ") for dim in in_subscript.split(" ")]
        for in_subscript in in_subscripts.split(",")
    ]
    if out_subscript is None:
        dims = in_dims
    elif not out_subscript:
        dims = [*in_dims, []]
    else:
        out_dims = [dim.strip(", ") for dim in out_subscript.split(" ")]
        dims = [*in_dims, out_dims]
    return einsum(
        dims,
        *operands,
        keep_dims=keep_dims,
        out_append=out_append,
        einsum_kwargs=einsum_kwargs,
        **kwargs,
    )


def matmul(da, db, dims=None, *, out_append="2", **kwargs):
    """Wrap :func:`numpy.linalg.matmul`.

    Usage examples of all arguments is available at the
    :ref:`matmul section <linalg_tutorial/matmul>` of the linear algebra module tutorial.
    """
    rename = False
    if dims is None:
        dims = _attempt_default_dims("matmul", da.dims, db.dims)
    if len(dims) == 3:
        dim1, dim2, dim3 = dims
        dims1 = [dim1, dim2]
        dims2 = [dim2, dim3]
        out_dims = [dim1, dim3]
        if dim1 == dim3:
            db = db.rename({dim3: dim3 + out_append})
            dims2 = [dim2, dim3 + out_append]
            out_dims = [dim1, dim3 + out_append]
        else:
            if dim3 in da.dims:
                da = da.rename({dim3: dim3 + out_append})
            if dim1 in db.dims:
                db = db.rename({dim1: dim1 + out_append})
    elif len(dims) != 2:
        raise ValueError(
            "matmul can be one of '[str, str]', '[str, str, str]' or '[[str, str], [str, str]]'"
        )
    elif isinstance(dims[0], str):
        dims1 = dims
        dims2 = dims
        out_dims = dims
    else:
        rename = True
        dim11, dim12 = dims[0]
        dim21, dim22 = dims[1]
        da = da.rename({dim11: "__aux_dim11__", dim12: "__aux_dim12__"})
        db = db.rename({dim21: "__aux_dim21__", dim22: "__aux_dim22__"})
        dims1 = ["__aux_dim11__", "__aux_dim12__"]
        dims2 = ["__aux_dim21__", "__aux_dim22__"]
        out_dims = ["__aux_dim11__", "__aux_dim22__"]
    matmul_aux = xr.apply_ufunc(
        np.matmul,
        da,
        db,
        input_core_dims=[dims1, dims2],
        output_core_dims=[out_dims],
        **kwargs,
    )
    if rename:
        return matmul_aux.rename(
            __aux_dim11__=dim11, __aux_dim22__=dim22 + out_append if dim22 == dim11 else dim22
        )
    return matmul_aux


def matrix_transpose(da, dims):
    """Transpose the underlying matrix without modifying the dimensions.

    This convenience function uses :meth:`~xarray.DataArray.swap_dims` followed
    by :meth:`~xarray.DataArray.transpose` to get the equivalent of a matrix transposition.

    Parameters
    ----------
    da : DataArray
        Input DataArray
    dims : list of str
        Matrix dimensions

    Returns
    -------
    DataArray
        The DataArray after transposing the matrix data but leaving the dimensions untouched.
    """
    if dims is None:
        dims = _attempt_default_dims("matrix_power", da.dims)
    dim1, dim2 = dims
    return da.swap_dims({dim1: dim2, dim2: dim1}).transpose(..., *dims)


def matrix_power(da, n, dims=None, **kwargs):
    """Wrap :func:`numpy.linalg.matrix_power`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("matrix_power", da.dims)
    return xr.apply_ufunc(
        np.linalg.matrix_power, da, n, input_core_dims=[dims, []], output_core_dims=[dims], **kwargs
    )


def cholesky(da, dims=None, **kwargs):
    """Wrap :func:`numpy.linalg.cholesky`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("cholesky", da.dims)
    return xr.apply_ufunc(
        np.linalg.cholesky, da, input_core_dims=[dims], output_core_dims=[dims], **kwargs
    )


def qr(da, dims=None, *, mode="reduced", out_append="2", **kwargs):  # pragma: no cover
    """Wrap :func:`numpy.linalg.qr`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("qr", da.dims)
    m_dim, n_dim = dims
    m, n = len(da[m_dim]), len(da[n_dim])
    k, k_dim = (m, m_dim) if n >= m else (n, n_dim)
    mode = mode.lower()
    if mode == "reduced":
        out_dims = [
            [m_dim, k_dim + (out_append if k_dim == m_dim else "")],
            [k_dim, n_dim + (out_append if k_dim == n_dim else "")],
        ]
    elif mode == "complete":
        out_dims = [[m_dim, m_dim + out_append], [m_dim, n_dim]]
    elif mode == "r":
        out_dims = [[m_dim if k == m else n_dim + out_append, n_dim]]
    elif mode == "raw":
        out_dims = [[n_dim, m_dim], [m_dim if k == m else n_dim]]
    else:
        raise ValueError("mode not recognized")

    return xr.apply_ufunc(
        np.linalg.qr,
        da,
        input_core_dims=[dims],
        output_core_dims=out_dims,
        kwargs=dict(mode=mode),
        **kwargs,
    )


def svd(
    da, dims=None, *, full_matrices=True, compute_uv=True, hermitian=False, out_append="2", **kwargs
):
    """Wrap :func:`numpy.linalg.svd`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("svd", da.dims)
    m_dim, n_dim = dims
    m, n = len(da[m_dim]), len(da[n_dim])
    k, k_dim = (m, m_dim) if m <= n else (n, n_dim)
    s_dims = [k_dim]
    if full_matrices:
        u_dims = [m_dim, m_dim + out_append]
        vh_dims = [n_dim, n_dim + out_append]
    else:
        if m == k:
            u_dims = [m_dim, k_dim + out_append]
            vh_dims = [k_dim, n_dim]
        else:
            u_dims = [m_dim, k_dim]
            vh_dims = [k_dim, n_dim + out_append]
    if compute_uv:
        out_dims = [u_dims, s_dims, vh_dims]
    else:
        out_dims = [s_dims]
    return xr.apply_ufunc(
        np.linalg.svd,
        da,
        input_core_dims=[dims],
        output_core_dims=out_dims,
        kwargs=dict(full_matrices=full_matrices, compute_uv=compute_uv, hermitian=hermitian),
        **kwargs,
    )


def eig(da, dims=None, **kwargs):
    """Wrap :func:`numpy.linalg.eig`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("eig", da.dims)
    return xr.apply_ufunc(
        np.linalg.eig, da, input_core_dims=[dims], output_core_dims=[dims[-1:], dims], **kwargs
    )


def eigh(da, dims=None, *, UPLO="L", **kwargs):  # pylint: disable=invalid-name
    """Wrap :func:`numpy.linalg.eigh`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("eigh", da.dims)
    return xr.apply_ufunc(
        np.linalg.eigh,
        da,
        input_core_dims=[dims],
        output_core_dims=[dims[-1:], dims],
        kwargs=dict(UPLO=UPLO),
        **kwargs,
    )


def eigvals(da, dims=None, **kwargs):
    """Wrap :func:`numpy.linalg.eigvals`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("eigvals", da.dims)
    return xr.apply_ufunc(
        np.linalg.eigvals, da, input_core_dims=[dims], output_core_dims=[dims[-1:]], **kwargs
    )


def eigvalsh(da, dims=None, *, UPLO="L", **kwargs):  # pylint: disable=invalid-name
    """Wrap :func:`numpy.linalg.eigvalsh`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("eigvalsh", da.dims)
    return xr.apply_ufunc(
        np.linalg.eigvalsh,
        da,
        input_core_dims=[dims],
        output_core_dims=[dims[-1:]],
        kwargs=dict(UPLO=UPLO),
        **kwargs,
    )


def norm(da, dims=None, *, ord=None, **kwargs):  # pylint: disable=redefined-builtin
    """Wrap :func:`numpy.linalg.norm`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("norm", da.dims)
    norm_kwargs = {"ord": ord}
    if isinstance(dims, str):
        in_dims = [dims]
        norm_kwargs["axis"] = -1
    else:
        in_dims = dims
        norm_kwargs["axis"] = (-2, -1)
    return xr.apply_ufunc(
        np.linalg.norm, da, input_core_dims=[in_dims], kwargs=norm_kwargs, **kwargs
    )


def cond(da, dims=None, *, p=None, **kwargs):  # pylint: disable=invalid-name
    """Wrap :func:`numpy.linalg.cond`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("cond", da.dims)
    return xr.apply_ufunc(np.linalg.cond, da, input_core_dims=[dims], kwargs=dict(p=p), **kwargs)


def det(da, dims=None, **kwargs):
    """Wrap :func:`numpy.linalg.det`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("det", da.dims)
    return xr.apply_ufunc(np.linalg.det, da, input_core_dims=[dims], **kwargs)


def matrix_rank(da, dims=None, *, tol=None, hermitian=False, **kwargs):
    """Wrap :func:`numpy.linalg.matrix_rank`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("matrix_rank", da.dims)
    return xr.apply_ufunc(
        np.linalg.matrix_rank,
        da,
        input_core_dims=[dims],
        kwargs=dict(tol=tol, hermitian=hermitian),
        **kwargs,
    )


def slogdet(da, dims=None, **kwargs):
    """Wrap :func:`numpy.linalg.slogdet`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("slogdet", da.dims)
    return xr.apply_ufunc(
        np.linalg.slogdet, da, input_core_dims=[dims], output_core_dims=[[], []], **kwargs
    )


def trace(da, dims=None, *, offset=0, dtype=None, out=None, **kwargs):
    """Wrap :func:`numpy.trace`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("trace", da.dims)
    trace_kwargs = dict(offset=offset, dtype=dtype, out=out, axis1=-2, axis2=-1)
    return xr.apply_ufunc(np.trace, da, input_core_dims=[dims], kwargs=trace_kwargs, **kwargs)


def diagonal(da, dims=None, *, offset=0, **kwargs):
    """Wrap :func:`numpy.diagonal`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("diagonal", da.dims)
    diagonal_kwargs = dict(offset=offset, axis1=-2, axis2=-1)
    out_dims = [dims[0] if offset == 0 else "diag_id"]
    return xr.apply_ufunc(
        np.diagonal,
        da,
        input_core_dims=[dims],
        output_core_dims=[out_dims],
        kwargs=diagonal_kwargs,
        **kwargs,
    )


def solve(da, db, dims=None, **kwargs):
    """Wrap :func:`numpy.linalg.solve`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("solve", da.dims, db.dims)
    if len(dims) == 3:
        b_dim = dims[0] if dims[0] in db.dims else dims[1]
        in_dims = [dims[:2], [b_dim, dims[-1]]]
        out_dims = [[b_dim, dims[-1]]]
    else:
        in_dims = [dims, dims[:1]]
        out_dims = [dims[:1]]
    return xr.apply_ufunc(
        np.linalg.solve, da, db, input_core_dims=in_dims, output_core_dims=out_dims, **kwargs
    )


def inv(da, dims=None, **kwargs):
    """Wrap :func:`numpy.linalg.inv`.

    Usage examples of all arguments is available at the :ref:`linalg_tutorial` page.
    """
    if dims is None:
        dims = _attempt_default_dims("inv", da.dims)
    return xr.apply_ufunc(
        np.linalg.inv, da, input_core_dims=[dims], output_core_dims=[dims], **kwargs
    )
