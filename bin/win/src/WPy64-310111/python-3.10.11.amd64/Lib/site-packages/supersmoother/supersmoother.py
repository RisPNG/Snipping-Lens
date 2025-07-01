from __future__ import division, print_function, absolute_import

import numpy as np

from .smoother import LinearSmoother
from .utils import multinterp, setattr_context


class SuperSmoother(LinearSmoother):
    """SuperSmoother for nonparametric smoothing of scatter plots.

    SuperSmoother is an adaptive component-wise linear smoother, described
    in Friedman 1984 [1].

    Parameters
    ----------
    alpha : float (optional)
        If specified, the bass enhancement / smoothing level (0 < alpha < 10).
    period : float (optional)
        If specified, then assume the data is periodic with the given period.

    Other Parameters
    ----------------
    primary_spans : array_like, default=(0.05, 0.2, 0.5)
        The primary span values used for the smooth. Must be between 0 and 1.
        Only modify these if you know exactly what you're doing!
    middle_span : float (default = 0.2)
        The middle span value used for the algorithm.
        Only modify this if you know exactly what you're doing!
    final_span : float (default = 0.05)
        The final span value used in the algorithm.
        Only modify this if you know exactly what you're doing!

    Attributes
    ----------
    primary_smooths : list of LinearSmoother
        the trained LinearSmoother instances used for the initial data pass
    span : function
        a function giving the optimal span at a given t value
        (available only after fit() is called)

    [1] Friedman 1984, "A Variable Span Smoother"
        http://www.slac.stanford.edu/cgi-wrap/getdoc/slac-pub-3477.pdf
    """
    def __init__(self, alpha=None, period=None,
                 primary_spans=(0.05, 0.2, 0.5),
                 middle_span=0.2, final_span=0.05):
        self.alpha = alpha
        self.period = period
        self.primary_spans = np.sort(np.unique(primary_spans))
        self.middle_span = middle_span
        self.final_span = final_span
        self.primary_smooths = [LinearSmoother(span, period)
                                for span in self.primary_spans]

    def _fit(self, t, y, dy):
        mid_smooth = LinearSmoother(self.middle_span, self.period)

        # 1. Compute three smoothed curves and get residuals
        ysmooth_primary = np.array([smoother.fit(t, y, dy, presorted=True)
                                            .cv_values()
                                    for smoother in self.primary_smooths])
        resids = abs((ysmooth_primary - y) / dy)

        # 2. Smooth each set of residuals with the midrange
        smoothed_resids = np.array([mid_smooth.fit(t, resid, dy,
                                                   presorted=True)
                                              .cv_values(cv=False)
                                    for resid in resids])

        # 3. Select span yielding best residual at each point
        best_spans = self.primary_spans[np.argmin(smoothed_resids, 0)]

        # 3a. Apply bass enhancement, if necessary
        if self.alpha is not None:
            alpha = np.clip(self.alpha, 0, 10)
            minresid = smoothed_resids.min(0)
            factor = (minresid / smoothed_resids[-1]) ** (10 - alpha)
            best_spans += factor * (self.primary_spans[-1] - best_spans)

        # 4. Smooth best span estimates with midrange span
        self.spansmoother = LinearSmoother(self.middle_span, self.period)
        self.spansmoother.fit(t, best_spans, dy, presorted=True)
        smoothed_spans = self.spansmoother.cv_values(cv=False)

        # 5. Interpolate the smoothed values
        smoothed_spans = np.clip(smoothed_spans,
                                 self.primary_spans[0],
                                 self.primary_spans[-1])
        self.ysmooth_raw = multinterp(self.primary_spans,
                                      ysmooth_primary,
                                      smoothed_spans)

        # The final smooth is done over self.ysmooth_raw with a constant span
        # width given by self.final_span.
        # We'll make this happen in _predict() and _cv_values() below.

        # for convenience in accessing the span values (and to make subclass
        # functions behave) set span to the spansmoother predict function.
        self.span = self.spansmoother.predict

    def _predict(self, t):
        # temporarily change y and span:
        with setattr_context(self, y=self.ysmooth_raw, span=self.final_span):
            return LinearSmoother._predict(self, t)

    def _cv_values(self, cv=True):
        # temporarily change y and span:
        with setattr_context(self, y=self.ysmooth_raw, span=self.final_span):
            # Use cv=False in all circumstances: CV is built into ysmooth_raw.
            return LinearSmoother._cv_values(self, cv=False)
