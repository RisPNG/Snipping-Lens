# Authors: Pierre Ablin <pierre.ablin@inria.fr>
#          Alexandre Gramfort <alexandre.gramfort@inria.fr>
#          Jean-Francois Cardoso <cardoso@iap.fr>
#
# License: BSD (3-clause)

import numpy as np
import warnings
from scipy import linalg

from ._core_picard import core_picard
from ._tools import check_random_state, _ica_par, _sym_decorrelation
from .densities import Tanh, Exp, Cube, check_density


def picard(X, fun='tanh', n_components=None, ortho=True, extended=None,
           whiten=True, return_X_mean=False, return_n_iter=False,
           centering=True, max_iter=100, tol=1e-07, m=7,  ls_tries=10,
           lambda_min=0.01, check_fun=True, w_init=None, fastica_it=None,
           random_state=None, verbose=False):
    """Perform Independent Component Analysis.

    Parameters
    ----------
    X : array-like, shape (n_features, n_samples)
        Training vector, where n_samples is the number of samples and
        n_features is the number of features.

    fun : str or class, optional
        Either a built in density model ('tanh', 'exp' and 'cube'), or a custom
        density.
        A custom density is a class that should contain two methods called
        'log_lik' and 'score_and_der'. See examples in the densities.py file.


    n_components : None or int, optional
        Number of components to extract. If None no dimension reduction
        is performed.

    ortho : bool, optional
        If True, uses Picard-O. Otherwise, uses the standard Picard.

    extended : None or bool, optional
        If True, uses the extended algorithm to separate sub and super-gaussian
        sources. By default, True if `ortho == True`, `False` otherwise.
        Using a different density than `'tanh'` may lead to erratic behavior of
        the algorithm: when `extended=True`, the non-linearity used by the
        algorithm is `x +/- fun(x)`. The non-linearity should correspond to a
        density, hence `fun` should be dominated by `x ** 2`. Further,
        `x + fun(x)` should separate super-Gaussian sources and `x-fun(x)`
        should separate sub-Gaussian sources. This set of requirement is met by
        `'tanh'`.

    whiten : boolean, optional
        If True perform an initial whitening of the data.
        If False, the data is assumed to have already been
        preprocessed: it should be centered, normed and white,
        otherwise you will get incorrect results.
        In this case the parameter n_components will be ignored.

    return_X_mean : bool, optional
        If True, X_mean is returned too. Equals to 0 if centering is False.

    return_n_iter : bool, option
        Whether or not to return the number of iterations.

    centering : bool, optional
        If True, X is mean corrected.

    max_iter : int, optional
        Maximum number of iterations to perform.

    tol : float, optional
        A positive scalar giving the tolerance at which the
        un-mixing matrix is considered to have converged.

    m : int, optional
        Size of L-BFGS's memory.

    ls_tries : int, optional
        Number of attempts during the backtracking line-search.

    lambda_min : float, optional
        Threshold on the eigenvalues of the Hessian approximation. Any
        eigenvalue below lambda_min is shifted to lambda_min.

    check_fun : bool, optionnal
        Whether to check the fun provided by the user at the beginning of
        the run. Setting it to False is not safe.

    w_init : None or (n_components, n_components) array, optional
        Initial un-mixing array of dimension (n.comp,n.comp).
        If None (default) then a random rotation is used.

    fastica_it : int or None, optional (default=None)
        If an int, perform `fastica_it` iterations of FastICA before running
        Picard. It might help starting from a better point.

    random_state : int, RandomState instance or None, optional (default=None)
        Used to perform a random initialization when w_init is not provided.
        If int, random_state is the seed used by the random number generator;
        If RandomState instance, random_state is the random number generator;
        If None, the random number generator is the RandomState instance used
        by `np.random`.

    verbose : bool, optional
        Prints informations about the state of the algorithm if True.

    Returns
    -------
    K : array, shape (n_components, n_features) | None.
        If whiten is 'True', K is the pre-whitening matrix that projects data
        onto the first n_components principal components. If whiten is 'False',
        K is 'None'.

    W : array, shape (n_components, n_components)
        Estimated un-mixing matrix.
        The mixing matrix can be obtained by::

            w = np.dot(W, K)
            A = np.dot(w.T, np.linalg.inv(np.dot(w, w.T)))

    Y : array, shape (n_components, n_samples) | None
        Estimated source matrix

    X_mean : array, shape (n_features,)
        The mean over features. Returned only if return_X_mean is True.

    n_iter : int
        Number of iterations taken to converge. This is
        returned only when return_n_iter is set to `True`.
    """
    random_state = check_random_state(random_state)

    # Behaves like Fastica if ortho, standard infomax if not ortho
    if extended is None:
        extended = ortho

    # Avoid possible overflows if the density is not tanh and extended is used.
    if fun != 'tanh' and extended and not ortho:
        warnings.warn('Using a different density than tanh for extended ica '
                      'may result in wrong estimation and overflows')

    if not type(ortho) is bool:
        warnings.warn('ortho should be a boolean, got (ortho={}).'
                      'ortho is set to default: ortho=True.'.format(ortho))
    n, p = X.shape
    if fun == 'tanh':
        fun = Tanh()
    elif fun == 'exp':
        fun = Exp()
    elif fun == 'cube':
        fun = Cube()
    elif check_fun:
        check_density(fun)

    if not whiten and n_components is not None:
        warnings.warn('Whiten is set to false, ignoring parameter '
                      'n_components')
        n_components = None

    if n_components is None:
        n_components = min(n, p)

    X1 = X.copy()
    if centering:
        # Center the columns (ie the variables)
        X_mean = X1.mean(axis=-1)
        X1 -= X_mean[:, np.newaxis]
    if whiten:
        # Whitening and preprocessing by PCA
        u, d, _ = linalg.svd(X1, full_matrices=False)
        del _
        K = (u / d).T[:n_components]
        del u, d
        K *= np.sqrt(p)
        X1 = np.dot(K, X1)
        covariance = np.eye(n_components)  # For extended
    else:
        # X must be casted to floats to avoid typing issues with numpy 2.0
        X1 = X1.astype('float')
        covariance = None  # For extended

    # Initialize
    if w_init is None:
        w_init = np.asarray(random_state.normal(size=(n_components,
                            n_components)), dtype=X1.dtype)
        # decorrelate w_init to make it white
        w_init = _sym_decorrelation(w_init)
    else:
        w_init = np.asarray(w_init)
        if w_init.shape != (n_components, n_components):
            raise ValueError('w_init has invalid shape -- should be %(shape)s'
                             % {'shape': (n_components, n_components)})

    if fastica_it is not None:
        w_init = _ica_par(X1, fun, fastica_it, w_init, verbose)

    X1 = np.dot(w_init, X1)
    kwargs = {'density': fun, 'm': m, 'max_iter': max_iter, 'tol': tol,
              'lambda_min': lambda_min, 'ls_tries': ls_tries,
              'verbose': verbose, 'ortho': ortho, 'extended': extended,
              'covariance': covariance}

    with np.errstate(all='raise'):  # So code breaks if overflow/Nans
        Y, W, infos = core_picard(X1, **kwargs)

    del X1
    W = np.dot(W, w_init)
    converged = infos['converged']
    if not converged:
        gradient_norm = infos['gradient_norm']
        warnings.warn('Picard did not converge. Final gradient norm : %.4g.'
                      ' Requested tolerance : %.4g. Consider'
                      ' increasing the number of iterations or the tolerance.'
                      % (gradient_norm, tol))
    if not whiten:
        K = None
    n_iter = infos['n_iterations']
    if return_X_mean:
        if centering:
            if return_n_iter:
                return K, W, Y, X_mean, n_iter
            else:
                return K, W, Y, X_mean
        else:
            if return_n_iter:
                return K, W, Y, np.zeros(p), n_iter
            else:
                return K, W, Y, np.zeros(p)
    else:
        if return_n_iter:
            return K, W, Y, n_iter
        else:
            return K, W, Y
