# Authors: Pierre Ablin <pierre.ablin@inria.fr>
#          Alexandre Gramfort <alexandre.gramfort@inria.fr>
#          Jean-Francois Cardoso <cardoso@iap.fr>
#
# License: BSD (3-clause)
from copy import copy
import numpy as np
from scipy.linalg import expm

from .densities import Tanh


def core_picard(X, density=Tanh(), ortho=False, extended=False, m=7,
                max_iter=1000, tol=1e-7, lambda_min=0.01, ls_tries=10,
                verbose=False, covariance=None):
    '''Runs the Picard algorithm

    The algorithm is detailed in::

        Pierre Ablin, Jean-Francois Cardoso, and Alexandre Gramfort
        Faster independent component analysis by preconditioning with Hessian
        approximations
        IEEE Transactions on Signal Processing, 2018
        https://arxiv.org/abs/1706.08171

    Parameters
    ----------
    X : array, shape (N, T)
        Matrix containing the signals that have to be unmixed. N is the
        number of signals, T is the number of samples. X has to be centered

    m : int
        Size of L-BFGS's memory. Typical values for m are in the range 3-15

    max_iter : int
        Maximal number of iterations for the algorithm

    precon : 1 or 2
        Chooses which Hessian approximation is used as preconditioner.
        1 -> H1
        2 -> H2
        H2 is more costly to compute but can greatly accelerate convergence
        (See the paper for details).

    tol : float
        tolerance for the stopping criterion. Iterations stop when the norm
        of the gradient gets smaller than tol.

    lambda_min : float
        Constant used to regularize the Hessian approximations. The
        eigenvalues of the approximation that are below lambda_min are
        shifted to lambda_min.

    ls_tries : int
        Number of tries allowed for the backtracking line-search. When that
        number is exceeded, the direction is thrown away and the gradient
        is used instead.

    verbose : boolean
        If true, prints the informations about the algorithm.

    Returns
    -------
    Y : array, shape (N, T)
        The estimated source matrix

    W : array, shape (N, N)
        The estimated unmixing matrix, such that Y = WX.
    '''
    # Init
    N, T = X.shape
    W = np.eye(N)
    Y = X
    s_list = []
    y_list = []
    r_list = []
    signs = np.ones(N)
    current_loss = _loss(Y, W, density, signs, ortho, extended)
    requested_tolerance = False
    sign_change = False
    gradient_norm = 1.
    if extended:
        if covariance is None:  # Need this for extended
            covariance = X.dot(X.T) / T
        C = covariance.copy()
    for n in range(max_iter):
        # Compute the score function
        psiY, psidY = density.score_and_der(Y)
        # Compute the relative gradient and the Hessian off-diagonal
        G = np.inner(psiY, Y) / T
        del psiY
        # Compute the squared signals
        Y_square = Y ** 2
        # Compute the kurtosis and update the gradient accordingly
        if extended:
            K = np.mean(psidY, axis=1) * np.diag(C)
            K -= np.diag(G)
            signs = np.sign(K)
            if n > 0:
                sign_change = np.any(signs != old_signs)  # noqa
            old_signs = signs  # noqa
            G *= signs[:, None]
            psidY *= signs[:, None]
            if not ortho:  # Like in extended infomax: change the gradient.
                G += C
                psidY += 1
        # Compute the Hessian off diagonal
        if ortho:
            h_off = np.diag(G).copy()
        else:
            h_off = np.ones(N)
        # Compute the Hessian approximation diagonal and regularize
        if ortho:
            psidY_mean = np.mean(psidY, axis=1)
            diag = psidY_mean[:, None] * np.ones(N)[None, :]
            h = 0.5 * (diag + diag.T - h_off[:, None] - h_off[None, :])
            h[h < lambda_min] = lambda_min
        else:
            h = np.inner(psidY, Y_square) / T
            h = _regularize_hessian(h, h_off, lambda_min)
        del psidY, Y_square
        # Project the gradient if ortho
        if ortho:
            G = (G - G.T) / 2
        else:
            G -= np.eye(N)
        # Stopping criterion
        gradient_norm = np.max(np.abs(G))
        if gradient_norm < tol:
            requested_tolerance = True
            break
        # Update the memory
        if n > 0:
            s_list.append(direction)  # noqa
            y = G - G_old  # noqa
            y_list.append(y)
            r_list.append(1. / (np.sum(direction * y)))  # noqa
            if len(s_list) > m:
                s_list.pop(0)
                y_list.pop(0)
                r_list.pop(0)
        G_old = G  # noqa
        # Flush the memory if there is a sign change.
        if extended and sign_change:
            current_loss = None
            s_list, y_list, r_list = [], [], []
        # Find the L-BFGS direction
        direction = _l_bfgs_direction(G, h, h_off, s_list, y_list, r_list,
                                      ortho)
        # Do a line_search in that direction:
        converged, new_Y, new_W, new_loss, direction =\
            _line_search(Y, W, density, direction, signs, current_loss,
                         ls_tries, verbose, ortho, extended)
        if not converged:
            direction = -G
            s_list, y_list, r_list = [], [], []
            _, new_Y, new_W, new_loss, direction =\
                _line_search(Y, W, density, direction, signs, current_loss,
                             10, False, ortho, extended)
        Y = new_Y
        W = new_W
        if covariance is not None:
            C = W.dot(covariance).dot(W.T)
        current_loss = new_loss
        if verbose:
            print('iteration %d, gradient norm = %.4g, loss = %.4g' %
                  (n + 1, gradient_norm, current_loss))
    infos = dict(converged=requested_tolerance, gradient_norm=gradient_norm,
                 n_iterations=n)
    if extended:
        infos['signs'] = signs
    return Y, W, infos


def _loss(Y, W, density, signs, ortho, extended):
    '''
    Computes the loss function for Y, W
    '''
    if not ortho:
        loss = - np.linalg.slogdet(W)[1]
    else:
        loss = 0.
    for y, s in zip(Y, signs):
        loss += s * np.mean(density.log_lik(y))
        if extended and not ortho:
            loss += 0.5 * np.mean(y ** 2)
    return loss


def _line_search(Y, W, density, direction, signs, current_loss, ls_tries,
                 verbose, ortho, extended):
    '''
    Performs a backtracking line search, starting from Y and W, in the
    direction direction. I
    '''
    N = W.shape[0]
    alpha = 1.
    if current_loss is None:
        current_loss = _loss(Y, W, density, signs, ortho, extended)
    for _ in range(ls_tries):
        if ortho:
            transform = expm(alpha * direction)
        else:
            transform = np.eye(N) + alpha * direction
        Y_new = np.dot(transform, Y)
        W_new = np.dot(transform, W)
        new_loss = _loss(Y_new, W_new, density, signs, ortho, extended)
        if new_loss < current_loss:
            return True, Y_new, W_new, new_loss, alpha * direction
        alpha /= 2.
    else:
        if verbose:
            print('line search failed, falling back to gradient')
        return False, Y_new, W_new, new_loss, alpha * direction


def _l_bfgs_direction(G, h, h_off, s_list, y_list, r_list, ortho):
    q = copy(G)
    a_list = []
    for s, y, r in zip(reversed(s_list), reversed(y_list), reversed(r_list)):
        alpha = r * np.sum(s * q)
        a_list.append(alpha)
        q -= alpha * y
    if ortho:
        z = q / h
        z = (z - z.T) / 2.
    else:
        z = _solve_hessian(h, h_off, q)
    for s, y, r, alpha in zip(s_list, y_list, r_list, reversed(a_list)):
        beta = r * np.sum(y * z)
        z += (alpha - beta) * s
    return -z


def _regularize_hessian(h, h_off, lambda_min):
    discr = np.sqrt((h - h.T) ** 2 + 4. * h_off[:, None] * h_off[None, :])
    eigenvalues = 0.5 * (h + h.T - discr)
    # Regularize
    problematic_locs = eigenvalues < lambda_min
    np.fill_diagonal(problematic_locs, False)
    i_pb, j_pb = np.where(problematic_locs)
    h[i_pb, j_pb] += lambda_min - eigenvalues[i_pb, j_pb]
    return h


def _solve_hessian(h, h_off, G):
    det = h * h.T - h_off[:, None] * h_off[None, :]
    return (h.T * G - h_off[:, None] * G.T) / det
