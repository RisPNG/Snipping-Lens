from __future__ import division, print_function, absolute_import
import numpy as np
from .utils import linear_smooth, moving_average_smooth, iterable

__all__ = ['MovingAverageSmoother', 'LinearSmoother']


class Smoother(object):
    """Base Class for Smoothers"""
    def __init__(self):
        raise NotImplementedError()

    def fit(self, t, y, dy=1, presorted=False):
        """Fit the smoother

        Parameters
        ----------
        t : array_like
            time locations of the points to smooth
        y : array_like
            y locations of the points to smooth
        dy : array_like or float (default = 1)
            Errors in the y values
        presorted : bool (default = False)
            If True, then t is assumed to be sorted.

        Returns
        -------
        self : Smoother instance
        """
        self.t, self.y, self.dy = self._validate_inputs(t, y, dy, presorted)
        self._fit(self.t, self.y, self.dy)
        return self

    def predict(self, t):
        """Predict the smoothed function value at time t

        Parameters
        ----------
        t : array_like
            Times at which to predict the result

        Returns
        -------
        y : ndarray
            Smoothed values at time t
        """
        t = np.asarray(t)
        return self._predict(np.ravel(t)).reshape(t.shape)

    def cv_values(self, cv=True):
        """Return the values of the cross-validation for the fit data"""
        return self._cv_values(cv)

    def cv_residuals(self, cv=True):
        """Return the residuals of the cross-validation for the fit data"""
        vals = self.cv_values(cv)
        return (self.y - vals) / self.dy

    def cv_error(self, cv=True, skip_endpoints=True):
        """Return the sum of cross-validation residuals for the input data"""
        resids = self.cv_residuals(cv)
        if skip_endpoints:
            resids = resids[1:-1]
        return np.mean(abs(resids))

    def _validate_inputs(self, t, y, dy, presorted=False):
        t, y, dy = np.broadcast_arrays(t, y, dy)
        if presorted:
            self.isort = slice(None)
        elif hasattr(self, 'period') and self.period:
            self.isort = np.argsort(t % self.period)
        else:
            self.isort = np.argsort(t)
        return t[self.isort], y[self.isort], dy[self.isort]

    def _fit(self, t, y, dy):
        """Private function to perform fit() on input data"""
        raise NotImplementedError()

    def _predict(self, t):
        """Private function implementing prediction for new data"""
        raise NotImplementedError()

    def _cv_values(self, cv=True):
        """Private function implementing cross-validation on fit data"""
        raise NotImplementedError()


class SpannedSmoother(Smoother):
    """Base class for smoothers based on local spans of sorted data"""
    def __init__(self, span, period=None):
        self.span = span
        self.period = period

    def _fit(self, t, y, dy):
        pass

    def span_int(self, t=None):
        if t is None:
            t = self.t

        if callable(self.span):
            spanint = self.span(t) * len(self.t)
        elif iterable(self.span):
            spanint = self.span[self.isort] * len(self.t)
        else:
            spanint = self.span * len(self.t)

        return np.clip(spanint, 3, None)

    def _predict(self, t):
        if callable(self.span):
            return self._smoothfunc(self.t, self.y, self.dy, cv=False,
                                    span_out=self.span_int(t), t_out=t,
                                    period=self.period)
        else:
            return self._smoothfunc(self.t, self.y, self.dy, cv=False,
                                    span=self.span_int(), t_out=t,
                                    period=self.period)

    def _cv_values(self, cv=True):
        return self._smoothfunc(self.t, self.y, self.dy, cv=cv,
                                span=self.span_int(), period=self.period)


class MovingAverageSmoother(SpannedSmoother):
    """Local smoother based on a moving average of adjacent points

    Parameters
    ----------
    span : float, array, or function
        The fraction of the data to use at each point of the smooth.
        If a function is passed, then this will be evaluated at each input
        time to determine the smooth.
    period : float (optional)
        If specified, then use a periodic smoother with the given period.
        Default is to assume no periodicity.
    """
    _smoothfunc = staticmethod(moving_average_smooth)


class LinearSmoother(SpannedSmoother):
    """Local smoother based on a locally linear fit of adjacent points

    Parameters
    ----------
    span : float, array, or function
        The fraction of the data to use at each point of the smooth.
        If a function is passed, then this will be evaluated at each input
        time to determine the smooth.
    period : float (optional)
        If specified, then use a periodic smoother with the given period.
        Default is to assume no periodicity.
    """
    _smoothfunc = staticmethod(linear_smooth)
