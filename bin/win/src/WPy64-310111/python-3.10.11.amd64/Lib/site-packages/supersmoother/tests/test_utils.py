from __future__ import division, absolute_import
from .. import utils
from ..utils import windowed_sum, windowed_sum_slow

import numpy as np
from numpy.testing import assert_allclose, assert_, assert_equal, assert_raises


def test_iterable():
    x = [1, 2, 3]
    y = 1
    assert_(utils.iterable(x))
    assert_(not utils.iterable(y))


def test_multiinterp(rseed=0, N=100):
    """Test of the multinterp function"""
    rng = np.random.RandomState(rseed)

    def check_match(k):
        x = np.sort(rng.rand(k))
        y = rng.rand(k, N)
        xquery = rng.rand(N)

        res1 = utils.multinterp(x, y, xquery, slow=False)
        res2 = utils.multinterp(x, y, xquery, slow=True)
        assert_allclose(res1, res2)

    for k in 3, 4, 5:
        yield check_match, k


def test_setattr_context():
    """Test of the setattr_context() function"""
    class Foo(object):
        pass
    f = Foo()
    f.attr = "abc"
    with utils.setattr_context(f, attr="123"):
        assert_equal(f.attr, "123")
    assert_equal(f.attr, "abc")

    try:
        with utils.setattr_context(f, attr="123"):
            raise ValueError()
    except:
        pass
    assert_equal(f.attr, "abc")


def test_validate_inputs_nosort(N=10, rseed=0):
    """Test input validation without sorting"""
    rng = np.random.RandomState(rseed)
    t, y = rng.rand(2, N)
    dy = 1

    t_, y_, dy_ = utils.validate_inputs(t, y, dy)
    assert_allclose(t, t_)
    assert_allclose(y, y_)
    assert_allclose(dy, dy_)


def test_validate_inputs_sort(N=10, rseed=0):
    """Test input validation with sorting"""
    rng = np.random.RandomState(rseed)
    t, y = rng.rand(2, N)
    dy = 1

    t_, y_, dy_ = utils.validate_inputs(t, y, dy, sort_by=t)
    isort = np.argsort(t)
    assert_allclose(t[isort], t_)
    assert_allclose(y[isort], y_)
    assert_allclose(dy, dy_)


def test_validate_inputs_fail():
    rng = np.random.RandomState(0)
    t, y = rng.rand(2, 10)
    dy = 1

    # bad keyword argument
    assert_raises(ValueError, utils.validate_inputs, t, y, dy,
                  blah='blah')

    # non-sortable array
    assert_raises(ValueError, utils.validate_inputs, 1, 1, 1)

    # bad sort array
    assert_raises(ValueError, utils.validate_inputs, t, y, dy, sort_by=[1])


def _fixed_span_sum(a, span, subtract_mid=False):
    """fixed-span sum; used for testing windowed_span"""
    window = np.ones(span)
    if span <= len(a):
        res = np.convolve(a, window, mode='same')
    else:
        start = (span - 1) // 2
        res = np.convolve(a, window, mode='full')[start:start + len(a)]
    if subtract_mid:
        res -= a
    return res


def _variable_span_sum(a, span, subtract_mid=False):
    """variable-span sum, using multiple runs of _fixed_span_sum"""
    a, spans = np.broadcast_arrays(a, span)
    unique_spans, inv = np.unique(spans, return_inverse=True)
    results = [_fixed_span_sum(a, s, subtract_mid) for s in unique_spans]
    return np.asarray([results[j][i] for i, j in enumerate(inv)])


def test_windowed_sum_simple():
    #"""windowed sum in the simplest case"""
    rng = np.random.RandomState(0)
        
    def check_results(wsum, N, span):
        a = rng.rand(N)
        assert_allclose([_fixed_span_sum(a, span),
                         _fixed_span_sum(a ** 2, span)],
                        wsum([a, a ** 2], span))

    for wsum in [windowed_sum, windowed_sum_slow]:
        for N in range(2, 6):
            for span in range(1, 7):
                yield check_results, wsum, N, span


def test_windowed_sum_with_t():
    #"""windowed sum with powers of t"""
    rng = np.random.RandomState(0)
        
    def check_results(wsum, N, span):
        a = rng.rand(N)
        t = np.sort(rng.rand(N))
        assert_allclose([_fixed_span_sum(a, span),
                         _fixed_span_sum(a * t, span)],
                        wsum([a, a], span, t=t, tpowers=[0, 1]))

    for wsum in [windowed_sum, windowed_sum_slow]:
        for N in range(2, 6):
            for span in range(1, 7):
                yield check_results, wsum, N, span


def test_windowed_sum_varspan():
    #"""windowed sum with a variable span"""
    rng = np.random.RandomState(0)
        
    def check_results(wsum, N):
        a = rng.rand(N)
        span = rng.randint(1, 5, N)
        assert_allclose([_variable_span_sum(a, span),
                         _variable_span_sum(a ** 2, span)],
                        wsum([a, a ** 2], span))

    for wsum in [windowed_sum, windowed_sum_slow]:
        for N in range(2, 6):
            yield check_results, wsum, N


def test_windowed_sum_with_period():
    #"""windowed sum with period"""
    rng = np.random.RandomState(0)
        
    def check_results(wsum, N, span, tpowers, period=0.6):
        a = rng.rand(N)
        t = np.sort(period * rng.rand(N))

        # find the periodic result straightforwardly by concatenating arrays
        a_all = np.concatenate([a for i in range(6)])
        t_all = np.concatenate([t + i * period for i in range(-3, 3)])

        res1 = wsum(len(tpowers) * [a_all], span, t=t_all,
                    tpowers=tpowers, period=None)
        res1 = [res[3 * N: 4 * N] for res in res1]
        res2 = wsum(len(tpowers) * [a], span, t=t,
                    tpowers=tpowers, period=period)
        assert_allclose(res1, res2)

    for wsum in [windowed_sum, windowed_sum_slow]:
        for N in range(4, 7):
            for span in range(1, 7):
                for tpowers in [(0, 1), (0, 1, 2)]:
                    yield check_results, wsum, N, span, tpowers
    

def test_windowed_sum_with_indices():
    #"""windowed sum with indices"""
    rng = np.random.RandomState(0)
        
    def check_results(wsum, N, span):
        ind = rng.randint(0, N, 4)
        a = rng.rand(N)
        t = np.sort(rng.rand(N))

        res1 = wsum([a, a], span, t=t, tpowers=[0, 1])
        res1 = [res[ind] for res in res1]
        res2 = wsum([a, a], span, t=t, tpowers=[0, 1],
                                 indices=ind)
        
        assert_allclose(res1, res2)

    for wsum in [windowed_sum, windowed_sum_slow]:
        for N in range(4, 6):
            for span in range(1, 7):
                yield check_results, wsum, N, span


def test_windowed_sum_subtract_mid():
    #"""windowed sum, subtracting the middle item"""
    rng = np.random.RandomState(0)
        
    def check_results(wsum, N, span):
        a = rng.rand(N)
        t = np.sort(rng.rand(N))
        assert_allclose([_fixed_span_sum(a, span, subtract_mid=True),
                         _fixed_span_sum(a * t, span, subtract_mid=True)],
                        wsum([a, a], span, t=t, tpowers=[0, 1],
                             subtract_mid=True))

    for wsum in [windowed_sum, windowed_sum_slow]:
        for N in range(2, 6):
            for span in range(1, 7):
                yield check_results, wsum, N, span


def test_windowed_sum_fast_vs_slow():
    #"""Test fast vs slow windowed sum for many combinations of parameters"""
    rng = np.random.RandomState(0)
        
    def check_results(N, span, indices, subtract_mid,
                      tpowers, period, use_t):
        a = rng.rand(N)
        t = np.sort(rng.rand(N))
        if period:
            t *= period

        if np.asarray(tpowers).size == 1:
            arrs = [a]
        else:
            arrs = len(tpowers) * [a]

        if not use_t:
            t = None

        res1 = windowed_sum_slow(arrs, span, t=t, subtract_mid=subtract_mid,
                                 indices=indices, tpowers=tpowers,
                                 period=period)
        res2 = windowed_sum(arrs, span, t=t, subtract_mid=subtract_mid,
                            indices=indices, tpowers=tpowers, period=period)
        assert_allclose(res1, res2)

    for N in [3, 5, 7]:
        for span in [3, 5, rng.randint(2, 5, N)]:
            for indices in [None, rng.randint(0, N, N)]:
                for subtract_mid in [True, False]:
                    for tpowers in [0, (0, 1)]:
                        for period in (0.6, None):
                            for use_t in [True, False]:
                                if period and not use_t:
                                    continue
                                yield (check_results, N, span, indices,
                                       subtract_mid, tpowers, period, use_t)


def test_windowed_sum_bad_args(N=10):
    #"""windowed sum in the simplest case"""
    rng = np.random.RandomState(0)
    a = rng.rand(N)
    t = np.arange(N)

    for wsum in [windowed_sum, windowed_sum_slow]:
        wsum(arrays=[a, a], span=5, t=t)
        assert_raises(ValueError, wsum, arrays=[a, a], span=5, t=t[:-1])
        assert_raises(ValueError, wsum, arrays=[a, a[:-1]], span=5, t=t)

    for wsum in [windowed_sum, windowed_sum_slow]:
        wsum(arrays=[a, a], span=5, tpowers=[0, 1])
        assert_raises(ValueError, wsum, arrays=[a, a],
                      span=5, tpowers=[0, 1, 2])


def test_windowed_sum_period_zero(N=10):
    """Regression test: make sure period=0 is handled correctly"""
    #"""windowed sum with period"""
    rng = np.random.RandomState(0)
    a = rng.rand(N)
    t = np.sort(0.6 * rng.rand(N))
        
    def check_results(wsum, span=3):
        res1 = wsum(arrays=[a], span=3, tpowers=[0], period=None)
        res2 = wsum(arrays=[a], span=3, tpowers=[0], period=0)

        assert_allclose(res1, res2)

    for wsum in [windowed_sum, windowed_sum_slow]:
        check_results(wsum)


def make_linear(N=100, err=1E-6, rseed=None):
    rng = np.random.RandomState(rseed)
    t = 10 * rng.rand(N)
    y = t + err * rng.randn(N)
    return t, y, err


def test_perfect_sine(N=100, rseed=0):
    """Test approximate recovery of a sine wave with no noise"""
    t = np.linspace(0, 10, 200)
    y = np.sin(t)
    dy = 1

    for method in [utils.moving_average_smooth, utils.linear_smooth]:
        yfit = method(t, y, dy, span=5)
        assert_allclose(y[3:-3], yfit[3:-3], atol=0.005)


def test_constant_data(N=100, rseed=0):
    """Test linear & moving average smoothers on constant data"""
    rng = np.random.RandomState(rseed)
    t = 10 * rng.rand(N)
    y = 1.0
    dy = 1.0
    span = 5

    for method in [utils.moving_average_smooth, utils.linear_smooth]:
        yfit = method(t, y, dy, span=5)
        assert_allclose(y, yfit)


def test_equal_spaced_linear_data(N=100, rseed=0):
    """Test linear & moving average smoothers on equally-spaced linear data"""
    t = np.linspace(0, 10, N)
    y = 1 + 2 * t
    dy = 1
    span = 5

    for method in [utils.moving_average_smooth, utils.linear_smooth]:
        yfit = method(t, y, dy, span=5)
        assert_allclose(y[3:-3], yfit[3:-3])


def test_random_linear_data(N=100, rseed=0):
    """Test linear smoother on linear data"""
    rng = np.random.RandomState(rseed)
    t = 10 * rng.rand(N)
    y = 1 + 2 * t
    dy = 1.0
    span = 5

    yfit = utils.linear_smooth(t, y, dy, span=5)
    assert_allclose(y, yfit)


def test_t_vs_t_out(N=100, rseed=0):
    """Test two means of arriving at the same answer"""
    rng = np.random.RandomState(rseed)
    t = np.sort(10 * rng.rand(N))
    y = np.sin(t)
    dy = 1.0
    span = 5

    for method in [utils.linear_smooth, utils.moving_average_smooth]:
        yfit1 = method(t, y, dy, span=5, cv=False)
        yfit2 = method(t, y, dy, span_out=5, t_out=t, cv=False)
        assert_allclose(yfit1, yfit2)


def test_smooth_assertions():
    """Test errors and assertions in linear_smooth and moving_average_smooth"""
    rng = np.random.RandomState(0)
    t = 10 * rng.rand(10)
    y = np.sin(t)
    dy = 1.0

    for method in [utils.linear_smooth, utils.moving_average_smooth]:
        # No span set
        assert_raises(ValueError, method, t, y, dy)

        # Both spans set
        assert_raises(ValueError, method, t, y, dy, span=1,
                      t_out=t, span_out=1)

        # span_out set without t_out
        assert_raises(ValueError, method, t, y, dy, span_out=1)
