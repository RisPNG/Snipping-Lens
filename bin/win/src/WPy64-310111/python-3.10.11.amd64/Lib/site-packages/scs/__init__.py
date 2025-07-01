

""""""# start delvewheel patch
def _delvewheel_init_patch_1_3_5():
    import os
    import sys
    libs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, '.'))
    is_pyinstaller = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
    if not is_pyinstaller or os.path.isdir(libs_dir):
        os.add_dll_directory(libs_dir)


_delvewheel_init_patch_1_3_5()
del _delvewheel_init_patch_1_3_5
# end delvewheel patch

#!/usr/bin/env python
from warnings import warn
from scipy import sparse
import _scs_direct

__version__ = _scs_direct.version()
__sizeof_int__ = _scs_direct.sizeof_int()
__sizeof_float__ = _scs_direct.sizeof_float()

_USE_INDIRECT_DEFAULT = False


# SCS return integers correspond to one of these flags:
# (copied from scs/include/glbopts.h)
INFEASIBLE_INACCURATE = -7  # SCS best guess infeasible
UNBOUNDED_INACCURATE = -6  # SCS best guess unbounded
SIGINT = -5  # interrupted by sig int
FAILED = -4  # SCS failed
INDETERMINATE = -3  # indeterminate (norm too small)
INFEASIBLE = -2  # primal infeasible, dual unbounded
UNBOUNDED = -1  # primal unbounded, dual infeasible
UNFINISHED = 0  # never returned, used as placeholder
SOLVED = 1  # problem solved to desired accuracy
SOLVED_INACCURATE = 2  # SCS best guess solved


# Choose which SCS to import based on settings.
def _select_scs_module(stgs):
    if stgs.pop("gpu", False):  # False by default
        if not stgs.pop("use_indirect", _USE_INDIRECT_DEFAULT):
            raise NotImplementedError(
                "GPU direct solver not yet available, pass `use_indirect=True`."
            )
        import _scs_gpu

        return _scs_gpu

    if stgs.pop("mkl", False):  # False by default
        if stgs.pop("use_indirect", False):
            raise NotImplementedError(
                "MKL indirect solver not yet available, pass `use_indirect=False`."
            )
        import _scs_mkl

        return _scs_mkl

    if stgs.pop("use_indirect", _USE_INDIRECT_DEFAULT):
        import _scs_indirect

        return _scs_indirect

    return _scs_direct


class SCS(object):
    def __init__(self, data, cone, **settings):
        """Initialize the SCS solver.

        @param data     Dictionary containing keys `P`, `A`, `b`, `c`.
        @param cone     Dictionary containing cone information.
        @param settings Settings as kwargs, see docs.

        """
        self._settings = settings
        if not data or not cone:
            raise ValueError("Missing data or cone information")

        if "b" not in data or "c" not in data:
            raise ValueError("Missing one of b, c from data dictionary")
        if "A" not in data:
            raise ValueError("Missing A from data dictionary")

        A = data["A"]
        b = data["b"]
        c = data["c"]

        if A is None or b is None or c is None:
            raise ValueError("Incomplete data specification")

        if not sparse.issparse(A):
            raise TypeError("A is required to be a sparse matrix")
        if not sparse.isspmatrix_csc(A):
            warn(
                "Converting A to a CSC (compressed sparse column) matrix;"
                " may take a while."
            )
            A = A.tocsc()

        if sparse.issparse(b):
            b = b.todense()

        if sparse.issparse(c):
            c = c.todense()

        m = len(b)
        n = len(c)

        if not A.has_sorted_indices:
            A.sort_indices()
        Adata, Aindices, Acolptr = A.data, A.indices, A.indptr
        if A.shape != (m, n):
            raise ValueError("A shape not compatible with b,c")

        Pdata, Pindices, Pcolptr = None, None, None
        if "P" in data:
            P = data["P"]
            if P is not None:
                if not sparse.issparse(P):
                    raise TypeError("P is required to be a sparse matrix")
                if P.shape != (n, n):
                    raise ValueError("P shape not compatible with A,b,c")
                if not sparse.isspmatrix_csc(P):
                    warn(
                        "Converting P to a CSC (compressed sparse column) "
                        "matrix; may take a while."
                    )
                    P = P.tocsc()
                # extract upper triangular component only
                if sparse.tril(P, -1).data.size > 0:
                    P = sparse.triu(P, format="csc")
                if not P.has_sorted_indices:
                    P.sort_indices()
                Pdata, Pindices, Pcolptr = P.data, P.indices, P.indptr

        # Which scs are we using (scs_direct, scs_indirect, ...)
        _scs = _select_scs_module(self._settings)

        # Initialize solver
        self._solver = _scs.SCS(
            (m, n),
            Adata,
            Aindices,
            Acolptr,
            Pdata,
            Pindices,
            Pcolptr,
            b,
            c,
            cone,
            **self._settings
        )

    def solve(self, warm_start=True, x=None, y=None, s=None):
        """Solve the optimization problem.

        @param warm_start   Whether to warm-start. By default the solution of
                            the previous problem is used as the warm-start. The
                            warm-start can be overriden to another value by
                            passing `x`, `y`, `s` args.
        @param x            Primal warm-start override.
        @param y            Dual warm-start override.
        @param s            Slack warm-start override.

        @return dictionary with solution with keys:
             'x' - primal solution
             's' - primal slack solution
             'y' - dual solution
             'info' - information dictionary (see docs)
        """
        return self._solver.solve(warm_start, x, y, s)

    def update(self, b=None, c=None):
        """Update the `b` vector, `c` vector, or both, before another solve.

        After a solve we can reuse the SCS workspace in another solve if the
        only problem data that has changed are the `b` and `c` vectors.

        @param  b   New `b` vector.
        @param  c	New `c` vector.

        """
        self._solver.update(b, c)


# Backwards compatible helper function that simply calls the main API.
def solve(data, cone, **settings):
    solver = SCS(data, cone, **settings)

    # Hack out the warm start data from old API
    x = y = s = None
    if "x" in data:
        x = data["x"]
    if "y" in data:
        y = data["y"]
    if "s" in data:
        s = data["s"]

    return solver.solve(warm_start=True, x=x, y=y, s=s)
