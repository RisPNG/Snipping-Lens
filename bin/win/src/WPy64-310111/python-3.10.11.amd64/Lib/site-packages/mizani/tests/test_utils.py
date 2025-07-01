import numpy as np
import pandas as pd
import pytest

from mizani.utils import (
    first_element,
    get_categories,
    match,
    min_max,
    multitype_sort,
    precision,
    round_any,
    same_log10_order_of_magnitude,
)


def test_round_any():
    x = 4.632
    assert round_any(x, 1) == 5
    assert round_any(x, 2) == 4
    assert round_any(x, 3) == 6
    assert round_any(x, 4) == 4
    assert round_any(x, 5) == 5
    assert round_any(x, 1.5) == 4.5

    # Maintains the same index
    s = pd.Series([1.1, 2.2, 3.3], index=[3, 2, 1])
    result = round_any(s, 2)
    assert s.index.equals(result.index)


def test_min_max():
    x = [1, 2, 3, 4, 5]
    _min, _max = min_max(x)
    assert _min == 1
    assert _max == 5

    x = [1, float("-inf"), 3, 4, 5]
    _min, _max = min_max(x)
    assert _min == 1
    assert _max == 5

    _min, _max = min_max(x, finite=False)
    assert _min == float("-inf")
    assert _max == 5

    x = [1, 2, float("nan"), 4, 5]
    _min, _max = min_max(x, na_rm=True)
    assert _min == 1
    assert _max == 5

    x = [1, 2, float("nan"), 4, 5, float("inf")]
    _min, _max = min_max(x, na_rm=True, finite=False)
    assert _min == 1
    assert _max == float("inf")

    _min, _max = min_max(x)
    assert str(_min) == "nan"
    assert str(_max) == "nan"

    x = [float("nan"), float("nan"), float("nan")]
    _min, _max = min_max(x, na_rm=True)
    assert _min == float("-inf")
    assert _max == float("inf")


def test_match():
    v1 = [0, 1, 2, 3, 4, 5]
    v2 = [5, 4, 3, 2, 1, 0]
    result = match(v1, v2)
    assert result == v2

    # Positions of the first match
    result = match(v1, v2 + v2)
    assert result == v2

    result = match(v1, v2, incomparables=[1, 2])
    assert result == [5, -1, -1, 2, 1, 0]

    result = match(v1, v2, start=1)
    assert result == [6, 5, 4, 3, 2, 1]

    v2 = [5, 99, 3, 2, 1, 0]
    result = match(v1, v2)
    assert result == [5, 4, 3, 2, -1, 0]


def test_precision():
    assert precision(0.0037) == 0.001
    assert precision(0.5) == 0.1
    assert precision(9) == 1
    assert precision(24) == 10
    assert precision(784) == 100
    assert precision([0, 0]) == 1


def test_first_element():
    x = [3, 4, 5]
    s = pd.Series(x)
    a = np.array([3, 4, 5])

    assert first_element(x) == 3
    assert first_element(s) == 3
    assert first_element(s[1:]) == 4
    assert first_element(a) == 3
    assert first_element(a[1:]) == 4

    with pytest.raises(StopIteration):
        first_element([])

    with pytest.raises(RuntimeError):
        first_element(iter(x))


def test_multitype_sort():
    a = ["c", float("nan"), 1, "b", "a", 2.0, 0]
    result = multitype_sort(a)
    # Any consecutive elements of the sametype are
    # sorted
    for i, x in enumerate(result[1:], start=1):
        x_prev = result[i - 1]
        if type(x_prev) is type(x):
            # cannot compare nan with anything
            if isinstance(x, float) and (np.isnan(x_prev) or np.isnan(x)):
                continue
            assert x_prev <= x


def test_same_log10_order_of_magnitude():
    # Default delta
    assert same_log10_order_of_magnitude((2, 8))
    assert same_log10_order_of_magnitude((35, 80.8))
    assert same_log10_order_of_magnitude((232.3, 730))

    assert not same_log10_order_of_magnitude((1, 18))
    assert not same_log10_order_of_magnitude((35, 800))
    assert not same_log10_order_of_magnitude((32, 730))

    assert not same_log10_order_of_magnitude((1, 9.9))
    assert not same_log10_order_of_magnitude((35, 91))
    assert not same_log10_order_of_magnitude((232.3, 950))

    # delta = 0
    assert same_log10_order_of_magnitude((1, 9.9), delta=0)
    assert same_log10_order_of_magnitude((35, 91), delta=0)
    assert same_log10_order_of_magnitude((232.3, 950), delta=0)


def test_get_categories():
    lst = list("abcd")
    s = pd.Series(lst)
    c = pd.Categorical(lst)
    sc = pd.Series(c)

    categories = pd.Index(lst)
    assert categories.equals(get_categories(c))
    assert categories.equals(get_categories(sc))

    with pytest.raises(TypeError):
        assert categories.equals(get_categories(lst))

    with pytest.raises(TypeError):
        assert categories.equals(get_categories(s))
