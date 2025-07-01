from __future__ import absolute_import, division

import numpy as np
from numpy.testing import assert_allclose, assert_array_less, assert_equal

from .. import SuperSmoother, LinearSmoother


def make_sine(N=100, err=0.05, rseed=None):
    rng = np.random.RandomState(rseed)
    t = 2 * np.pi * rng.rand(N)
    y = np.sin(t) + err * rng.randn(N)
    return t, y, err


def make_linear(N=100, err=1E-6, rseed=None):
    rng = np.random.RandomState(rseed)
    t = 10 * rng.rand(N)
    y = t + err * rng.randn(N)
    return t, y, err


def test_sine():
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)

    tfit = np.linspace(1, 5.3, 50)
    ytrue = np.sin(tfit)

    model = SuperSmoother().fit(t, y, dy)
    yfit = model.predict(tfit)
    obs_err = np.mean((yfit - ytrue) ** 2)
    assert_array_less(obs_err, 0.001)


def test_sine_cv():
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)
    ytrue = np.sin(np.sort(t)[1:-1])

    model = SuperSmoother().fit(t, y, dy)
    yfit = model.cv_values()[1:-1]
    obs_err = np.mean((yfit - ytrue) ** 2)
    assert_array_less(obs_err, 0.001)


def test_line_linear():
    t, y, dy = make_linear(err=1E-6, rseed=0)
    tfit = np.linspace(0, 10, 40)

    model = SuperSmoother().fit(t, y, dy)
    yfit = model.predict(tfit)
    assert_allclose(tfit, yfit, atol=1E-5)


def test_bass_enhancement_zero():
    """Test low-level bass enhancement"""
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)

    model1 = SuperSmoother(alpha=0).fit(t, y, dy)
    model2 = SuperSmoother().fit(t, y, dy)

    assert_allclose(model1.predict(t), model2.predict(t), atol=1E-3)


def test_bass_enhancement_10():
    """Test high-level bass enhancement"""
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)

    model1 = SuperSmoother(alpha=10).fit(t, y, dy)
    model2 = LinearSmoother(span=0.5).fit(t, y, dy)

    assert_allclose(model1.predict(t), model2.predict(t), atol=1E-1)



def test_cv_interface():
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)
    model = SuperSmoother().fit(t, y, dy)

    def check_model(cv, skip_endpoints):
        cv_values = model.cv_values(cv=cv)
        cv_residuals = (model.y - cv_values) / model.dy
        if skip_endpoints:
            cv_error = np.mean(abs(cv_residuals[1:-1]))
        else:
            cv_error = np.mean(abs(cv_residuals))

        assert_allclose(cv_residuals,
                        model.cv_residuals(cv=cv))
        assert_allclose(cv_error,
                        model.cv_error(cv=cv, skip_endpoints=skip_endpoints))

    for cv in [True, False]:
        for skip_endpoints in [True, False]:
            yield check_model, cv, skip_endpoints
