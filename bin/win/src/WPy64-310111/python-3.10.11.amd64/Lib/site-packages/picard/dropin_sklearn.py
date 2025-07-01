# Authors: Pierre Ablin <pierre.ablin@inria.fr>
#
# License: BSD (3-clause)
import warnings

import numpy as np

from scipy import linalg

from sklearn.decomposition import FastICA
from sklearn.utils import check_random_state, as_float_array
from sklearn.utils.validation import FLOAT_DTYPES

from .solver import picard


class Picard(FastICA):
    """Picard: a **very** fast algorithm for Independent Component Analysis.

    Parameters
    ----------
    n_components : int, default=None
        Number of components to use. If None is passed, all are used.
    ortho : bool, optional
        If True, uses Picard-O and enforce an orthogonal constraint.
        Otherwise, uses the standard Picard.
    extended : None or bool, optional
        If True, uses the extended algorithm to separate sub and super-gaussian
        sources. If ``None`` (default), it is set to True if `ortho == True`,
        and `False` otherwise. With `extended=True` we recommend you keep the
        different density to `'tanh'`. See notes below.
    whiten : bool, default=True
        If whiten is false, the data is already considered to be
        whitened, and no whitening is performed.
    fun : str or class, optional
        Either a built-in density model ('tanh', 'exp' and 'cube'), or a custom
        density.
        A custom density is a class that should contain two methods called
        'log_lik' and 'score_and_der'. See examples in the densities.py file.
    max_iter : int, default=200
        Maximum number of iterations during fit.
    tol : float, default=1e-7
        Tolerance on update at each iteration.
    w_init : ndarray of shape (n_components, n_components), default=None
        The mixing matrix to be used to initialize the algorithm.
    m : int, optional
        Size of L-BFGS's memory.
    ls_tries : int, optional
        Number of attempts during the backtracking line-search.
    lambda_min : float, optional
        Threshold on the eigenvalues of the Hessian approximation. Any
        eigenvalue below lambda_min is shifted to lambda_min.
    random_state : int, RandomState instance or None, default=None
        Used to initialize ``w_init`` when not specified, with a
        normal distribution. Pass an int, for reproducible results
        across multiple function calls.

    Attributes
    ----------
    components_ : ndarray of shape (n_components, n_features)
        The linear operator to apply to the data to get the independent
        sources. This is equal to the unmixing matrix when ``whiten`` is
        False, and equal to ``np.dot(unmixing_matrix, self.whitening_)`` when
        ``whiten`` is True.
    mixing_ : ndarray of shape (n_features, n_components)
        The pseudo-inverse of ``components_``. It is the linear operator
        that maps independent sources to the data.
    mean_ : ndarray of shape(n_features,)
        The mean over features. Only set if `self.whiten` is True.
    whitening_ : ndarray of shape (n_components, n_features)
        Only set if whiten is 'True'. This is the pre-whitening matrix
        that projects data onto the first `n_components` principal components.

    Examples
    --------
    >>> from sklearn.datasets import load_digits
    >>> from picard import Picard
    >>> X, _ = load_digits(return_X_y=True)
    >>> transformer = Picard(n_components=7,
    ...         random_state=0)
    >>> X_transformed = transformer.fit_transform(X)
    >>> X_transformed.shape
    (1797, 7)

    Notes
    -----
    Using a different density than `'tanh'` may lead to erratic behavior of
    the algorithm: when `extended=True`, the non-linearity used by the
    algorithm is `x +/- fun(x)`. The non-linearity should correspond to a
    density, hence `fun` should be dominated by `x ** 2`. Further,
    `x + fun(x)` should separate super-Gaussian sources and `x-fun(x)`
    should separate sub-Gaussian sources. This set of requirement is met by
    `'tanh'`.
    """
    def __init__(self, n_components=None, *, ortho=True, extended=None,
                 whiten=True, fun='tanh', max_iter=200, tol=1e-7,
                 w_init=None, m=7,  ls_tries=10, lambda_min=0.01,
                 random_state=None):
        super().__init__()
        if max_iter < 1:
            raise ValueError("max_iter should be greater than 1, got "
                             "(max_iter={})".format(max_iter))
        self.n_components = n_components
        self.ortho = ortho
        self.extended = extended
        self.whiten = whiten
        self.fun = fun
        self.max_iter = max_iter
        self.tol = tol
        self.w_init = w_init
        self.m = m
        self.ls_tries = ls_tries
        self.lambda_min = lambda_min
        self.random_state = random_state

    def _fit(self, X, compute_sources=False):
        """Fit the model

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Training data, where n_samples is the number of samples
            and n_features is the number of features.
        compute_sources : bool, default=False
            If False, sources are not computes but only the rotation matrix.
            This can save memory when working with big data. Defaults to False.

        Returns
        -------
        X_new : ndarray of shape (n_samples, n_components)
            The estimated sources.
        """

        X = self._validate_data(X, copy=self.whiten, dtype=FLOAT_DTYPES,
                                ensure_min_samples=2).T
        random_state = check_random_state(self.random_state)

        n_samples, n_features = X.shape

        n_components = self.n_components
        if not self.whiten and n_components is not None:
            n_components = None
            warnings.warn('Ignoring n_components with whiten=False.')

        if n_components is None:
            n_components = min(n_samples, n_features)
        if (n_components > min(n_samples, n_features)):
            n_components = min(n_samples, n_features)
            warnings.warn(
                'n_components is too large: it will be set to %s'
                % n_components
            )

        if self.whiten:
            # Centering the columns (ie the variables)
            X_mean = X.mean(axis=-1)
            X -= X_mean[:, np.newaxis]

            # Whitening and preprocessing by PCA
            u, d, _ = linalg.svd(X, full_matrices=False, check_finite=False)

            del _
            K = (u / d).T[:n_components]
            del u, d
            X1 = np.dot(K, X)
            X1 *= np.sqrt(n_features)
        else:
            # X must be casted to floats to avoid typing issues with numpy
            # 2.0 and the line below
            X1 = as_float_array(X, copy=False)  # copy has been taken care of

        w_init = self.w_init

        kwargs = {'tol': self.tol,
                  'fun': self.fun,
                  'ortho': self.ortho,
                  'extended': self.extended,
                  'max_iter': self.max_iter,
                  'w_init': w_init,
                  'whiten': None,  # Already done above
                  'm': self.m,
                  'ls_tries': self.ls_tries,
                  'lambda_min': self.lambda_min,
                  'random_state': random_state}
        _, W, _ = picard(X1, **kwargs)
        del X1

        if compute_sources:
            if self.whiten:
                S = np.linalg.multi_dot([W, K, X]).T
            else:
                S = np.dot(W, X).T
        else:
            S = None

        if self.whiten:
            self.components_ = np.dot(W, K)
            self.mean_ = X_mean
            self.whitening_ = K
        else:
            self.components_ = W

        self.mixing_ = linalg.pinv(self.components_, check_finite=False)
        self._unmixing = W

        return S
