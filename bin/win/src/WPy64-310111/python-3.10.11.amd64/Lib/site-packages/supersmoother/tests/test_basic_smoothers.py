from __future__ import absolute_import, division

import numpy as np
from numpy.testing import (assert_allclose, assert_array_less,
                           assert_equal, assert_raises)

from .. import MovingAverageSmoother, LinearSmoother
from ..smoother import Smoother


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

    def check_model(Model, span, err):
        model = Model(span).fit(t, y, dy)
        yfit = model.predict(tfit)
        obs_err = np.mean((yfit - ytrue) ** 2)
        assert_array_less(obs_err, err)

    spans = [0.05, 0.2, 0.5]
    errs = [0.005, 0.01, 0.1]

    for Model in [MovingAverageSmoother, LinearSmoother]:
        for span, err in zip(spans, errs):
            yield check_model, Model, span, err


def test_sine_cv():
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)
    ytrue = np.sin(np.sort(t)[1:-1])

    def check_model(Model, span, err):
        model = Model(span).fit(t, y, dy)
        yfit = model.cv_values()[1:-1]
        obs_err = np.mean((yfit - ytrue) ** 2)
        assert_array_less(obs_err, err)

    spans = [0.05, 0.2, 0.5]
    errs = [0.005, 0.02, 0.1]

    for Model in [MovingAverageSmoother, LinearSmoother]:
        for span, err in zip(spans, errs):
            yield check_model, Model, span, err


def test_line_linear():
    t, y, dy = make_linear(rseed=0, err=1E-6)
    tfit = np.linspace(0, 10, 40)

    def check_model(span):
        model = LinearSmoother(span).fit(t, y, dy)
        yfit = model.predict(tfit)
        assert_allclose(tfit, yfit, atol=1E-5)

    for span in [0.05, 0.2, 0.5]:
        yield check_model, span



def test_variable_sine_predict():
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)

    tfit = np.linspace(1, 5.3, 50)
    ytrue = np.sin(tfit)

    def check_model(Model, span):
        model1 = Model(span * np.ones_like(t))
        model2 = Model(span)
        assert_allclose(model1.fit(t, y, dy).predict(tfit),
                        model2.fit(t, y, dy).predict(tfit))

    for Model in [MovingAverageSmoother, LinearSmoother]:
        for span in [0.05, 0.2, 0.5]:
            yield check_model, Model, span


def test_variable_sine_crossval():
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)

    tfit = np.linspace(1, 5.3, 50)
    ytrue = np.sin(tfit)

    def check_model(Model, span):
        model1 = Model(span * np.ones_like(t))
        model2 = Model(span)
        assert_allclose(model1.fit(t, y, dy).cv_values(),
                        model2.fit(t, y, dy).cv_values())

    for Model in [MovingAverageSmoother, LinearSmoother]:
        for span in [0.05, 0.2, 0.5]:
            yield check_model, Model, span


def test_func_span_const():
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)

    def check_model(Model, span, spanfunc):
        model1 = Model(span)
        model2 = Model(spanfunc)
        assert_allclose(model1.fit(t, y, dy).predict(t),
                        model2.fit(t, y, dy).predict(t))

    for Model in [MovingAverageSmoother, LinearSmoother]:
        for span in [0.05, 0.2, 0.5]:
            spanfunc = lambda t, span=span: span * np.ones_like(t)
            yield check_model, Model, span, spanfunc


def test_func_span_variable():
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)

    spanfunc = lambda t, tmax=t.max(): 0.5 + 0.05 * t / tmax
    span = spanfunc(t)

    def check_model(Model, span, spanfunc):
        model1 = Model(span)
        model2 = Model(spanfunc)
        assert_allclose(model1.fit(t, y, dy).predict(t),
                        model2.fit(t, y, dy).predict(t))

    for Model in [MovingAverageSmoother, LinearSmoother]:
        yield check_model, Model, span, spanfunc


def test_cv_interface():
    t, y, dy = make_sine(N=100, err=0.05, rseed=0)
    span = 0.2

    def check_model(Model, span, cv, skip_endpoints):
        model = Model(span).fit(t, y, dy)
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

    for Model in [MovingAverageSmoother, LinearSmoother]:
        for cv in [True, False]:
            for skip_endpoints in [True, False]:
                yield check_model, Model, span, cv, skip_endpoints


def test_span_extremes():
    """Test models with extreme values of spans"""
    t, y, dy = make_sine(10, err=0.05, rseed=0)

    def check_model(Model, span):
        model1 = Model(span).fit(t, y, dy)
        model2 = Model(span + np.zeros_like(t)).fit(t, y, dy)
        assert_allclose(model1.cv_values(False), model2.cv_values(False))

    for Model in [MovingAverageSmoother, LinearSmoother]:
        for span in (-1, 0, 1, 2):
            yield check_model, Model, span
    

def test_periodic():
    rng = np.random.RandomState(0)
    N = 10
    period = 1
    t = np.linspace(0, period, N, endpoint=False)
    y = rng.rand(N)

    t_folded = np.concatenate([-period + t, t, t + period])
    y_folded = np.concatenate([y, y, y])

    def check_model(Model, span):
        model1 = Model(span / len(t_folded), period=None)
        model2 = Model(span / len(t), period=period)

        model1.fit(t_folded, y_folded)
        model2.fit(t, y)

        assert_allclose(model1.predict(t), model2.predict(t))
    

    for Model in [MovingAverageSmoother, LinearSmoother]:
        for span in [3, 4, 5]:
            yield check_model, Model, span


def test_baseclass():
    # silly tests to bring coverage to 100%
    assert_raises(NotImplementedError, Smoother)
    class Derived(Smoother):
        def __init__(self):
            pass

    d = Derived()
    assert_raises(NotImplementedError, d.fit, [1, 2, 3], [1, 1, 1])
    assert_raises(NotImplementedError, d.predict, [1, 2, 3])
    assert_raises(NotImplementedError, d.cv_values)


def test_duplicate_inputs():
    rng = np.random.RandomState(0)
    x = np.arange(100)
    x[:10] = 10
    y = rng.rand(100)
    sm = LinearSmoother(span=0.1).fit(x, y)
    assert_raises(ValueError, sm.predict, x)
