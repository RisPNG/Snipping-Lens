"""Common utility functions"""
from warnings import warn
import numpy as np
import scipy.sparse as sparse
import osqp._osqp as _osqp


def linsys_solver_str_to_int(settings):
        linsys_solver_str = settings.pop('linsys_solver', '')
        if not isinstance(linsys_solver_str, str):
            raise TypeError("Setting linsys_solver " +
                            "is required to be a string.")
        linsys_solver_str = linsys_solver_str.lower()
        if linsys_solver_str == 'qdldl':
            settings['linsys_solver'] = _osqp.constant('QDLDL_SOLVER')
        elif linsys_solver_str == 'mkl pardiso':
            settings['linsys_solver'] = _osqp.constant('MKL_PARDISO_SOLVER')
        # Default solver: QDLDL
        elif linsys_solver_str == '':
            settings['linsys_solver'] = _osqp.constant('QDLDL_SOLVER')
        else:   # default solver: QDLDL
            warn("Linear system solver not recognized. " +
                 "Using default solver QDLDL.")
            settings['linsys_solver'] = _osqp.constant('QDLDL_SOLVER')
        return settings


def prepare_data(P=None, q=None, A=None, l=None, u=None, **settings):
        """
        Prepare problem data of the form

        minimize     1/2 x' * P * x + q' * x
        subject to   l <= A * x <= u

        solver settings can be specified as additional keyword arguments
        """

        #
        # Get problem dimensions
        #

        if P is None:
            if q is not None:
                n = len(q)
            elif A is not None:
                n = A.shape[1]
            else:
                raise ValueError("The problem does not have any variables")
        else:
            n = P.shape[0]
        if A is None:
            m = 0
        else:
            m = A.shape[0]

        #
        # Create parameters if they are None
        #

        if (A is None and (l is not None or u is not None)) or \
                (A is not None and (l is None and u is None)):
            raise ValueError("A must be supplied together " +
                             "with at least one bound l or u")

        # Add infinity bounds in case they are not specified
        if A is not None and l is None:
            l = -np.inf * np.ones(A.shape[0])
        if A is not None and u is None:
            u = np.inf * np.ones(A.shape[0])

        # Create elements if they are not specified
        if P is None:
            P = sparse.csc_matrix((np.zeros((0,), dtype=np.double),
                                   np.zeros((0,), dtype=int),
                                   np.zeros((n+1,), dtype=int)),
                                  shape=(n, n))
        if q is None:
            q = np.zeros(n)

        if A is None:
            A = sparse.csc_matrix((np.zeros((0,), dtype=np.double),
                                   np.zeros((0,), dtype=int),
                                   np.zeros((n+1,), dtype=int)),
                                  shape=(m, n))
            l = np.zeros(A.shape[0])
            u = np.zeros(A.shape[0])

        #
        # Check vector dimensions (not checked from C solver)
        #

        # Check if second dimension of A is correct
        # if A.shape[1] != n:
        #     raise ValueError("Dimension n in A and P does not match")
        if len(q) != n:
            raise ValueError("Incorrect dimension of q")
        if len(l) != m:
            raise ValueError("Incorrect dimension of l")
        if len(u) != m:
            raise ValueError("Incorrect dimension of u")

        #
        # Check or Sparsify Matrices
        #
        if not sparse.issparse(P) and isinstance(P, np.ndarray) and \
                len(P.shape) == 2:
            raise TypeError("P is required to be a sparse matrix")
        if not sparse.issparse(A) and isinstance(A, np.ndarray) and \
                len(A.shape) == 2:
            raise TypeError("A is required to be a sparse matrix")

        # If P is not triu, then convert it to triu
        if sparse.tril(P, -1).data.size > 0:
            P = sparse.triu(P, format='csc')

        # Convert matrices in CSC form and to individual pointers
        if not sparse.isspmatrix_csc(P):
            warn("Converting sparse P to a CSC " +
                 "(compressed sparse column) matrix. (It may take a while...)")
            P = P.tocsc()
        if not sparse.isspmatrix_csc(A):
            warn("Converting sparse A to a CSC " +
                 "(compressed sparse column) matrix. (It may take a while...)")
            A = A.tocsc()

        # Check if P an A have sorted indices
        if not P.has_sorted_indices:
            P.sort_indices()
        if not A.has_sorted_indices:
            A.sort_indices()

        # Convert infinity values to OSQP Infinity
        u = np.minimum(u, _osqp.constant('OSQP_INFTY'))
        l = np.maximum(l, -_osqp.constant('OSQP_INFTY'))

        # Convert linsys_solver string to integer
        settings = linsys_solver_str_to_int(settings)

        return ((n, m), P.data, P.indices, P.indptr, q,
                A.data, A.indices, A.indptr,
                l, u), settings
