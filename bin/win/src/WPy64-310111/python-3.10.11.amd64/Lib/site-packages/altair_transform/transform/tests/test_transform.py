import pytest

import numpy as np
import pandas as pd
from numpy.testing import assert_equal
from distutils.version import LooseVersion
from altair_transform import apply
import altair as alt
from altair.utils.data import to_values
from altair_transform.transform.aggregate import AGG_REPLACEMENTS


AGGREGATES = [
    "argmax",
    "argmin",
    "average",
    "count",
    "distinct",
    "max",
    "mean",
    "median",
    "min",
    "missing",
    "q1",
    "q3",
    "ci0",
    "ci1",
    "stderr",
    "stdev",
    "stdevp",
    "sum",
    "valid",
    "values",
    "variance",
    "variancep",
]

AGG_SKIP = ["ci0", "ci1"]  # These require scipy.


FILTER_PREDICATES = [
    ("datum.x < datum.y", lambda df: df[df.x < df.y]),
    ({"not": "datum.i < 5"}, lambda df: df[~(df.i < 5)]),
    (
        {"and": [{"field": "x", "lt": 50}, {"field": "i", "gte": 2}]},
        lambda df: df[(df.x < 50) & (df.i >= 2)],
    ),
    (
        {"or": [{"field": "y", "gt": 50}, {"field": "i", "lte": 4}]},
        lambda df: df[(df.y > 50) | (df.i <= 4)],
    ),
    ({"field": "c", "oneOf": ["A", "B"]}, lambda df: df[df.c.isin(["A", "B"])]),
    ({"field": "x", "range": [30, 60]}, lambda df: df[(df.x >= 30) & (df.x <= 60)]),
    ({"field": "c", "equal": "B"}, lambda df: df[df.c == "B"]),
]


@pytest.fixture
def data():
    rand = np.random.RandomState(42)
    return pd.DataFrame(
        {
            "x": rand.randint(0, 100, 12),
            "y": rand.randint(0, 100, 12),
            "t": pd.date_range("2012-01-15", freq="M", periods=12),
            "i": range(12),
            "c": list("AAABBBCCCDDD"),
        }
    )


def test_calculate_transform(data):
    transform = {"calculate": "datum.x + datum.y", "as": "z"}
    out1 = apply(data, transform)

    out2 = data.copy()
    out2["z"] = data.x + data.y

    assert out1.equals(out2)


@pytest.mark.parametrize("filter,calc", FILTER_PREDICATES)
def test_filter_transform(data, filter, calc):
    out1 = apply(data, {"filter": filter})
    out2 = calc(data)
    assert out1.equals(out2)


def test_flatten_transform():
    data = pd.DataFrame(
        {
            "x": [[1, 2, 3], [4, 5, 6, 7], [8, 9]],
            "y": [[1, 2], [3, 4], [5, 6]],
            "cat": list("ABC"),
        }
    )

    out = apply(data, {"flatten": ["x"]})
    assert out.shape == (9, 3)
    assert out.columns.tolist() == ["x", "y", "cat"]
    assert_equal(out.x.values, range(1, 10))
    assert_equal(out.cat.values, list("AAABBBBCC"))

    out = apply(data, {"flatten": ["x", "y"]})
    assert out.shape == (9, 3)
    assert out.columns.tolist() == ["x", "y", "cat"]
    assert_equal(out.x.values, range(1, 10))
    assert_equal(out.y.values, [1, 2, np.nan, 3, 4, np.nan, np.nan, 5, 6])
    assert_equal(out.cat.values, list("AAABBBBCC"))


@pytest.mark.skipif(
    LooseVersion(alt.__version__) < "3.1.0",
    reason="Altair 3.1 or higher required for this test.",
)
def test_flatten_transform_with_as():
    data = pd.DataFrame(
        {
            "x": [[1, 2, 3], [4, 5, 6, 7], [8, 9]],
            "y": [[1, 2], [3, 4], [5, 6]],
            "cat": list("ABC"),
        }
    )

    out = apply(data, {"flatten": ["y"], "as": ["yflat"]})
    assert out.shape == (6, 3)
    assert out.columns.tolist() == ["yflat", "x", "cat"]
    assert_equal(out.yflat.values, range(1, 7))
    assert_equal(out.cat.values, list("AABBCC"))

    out = apply(data, {"flatten": ["x", "y"], "as": ["xflat", "yflat"]})
    assert out.shape == (9, 3)
    assert out.columns.tolist() == ["xflat", "yflat", "cat"]
    assert_equal(out.xflat.values, range(1, 10))
    assert_equal(out.yflat.values, [1, 2, np.nan, 3, 4, np.nan, np.nan, 5, 6])
    assert_equal(out.cat.values, list("AAABBBBCC"))


@pytest.mark.parametrize("as_", (None, ["name", "val"]))
def test_fold_transform(as_):
    data = pd.DataFrame({"x": [1, 2, 3], "y1": ["A", "B", "C"], "y2": ["D", "E", "F"]})
    if as_ is None:
        out = apply(data, {"fold": ["y1", "y2"]})
        as_ = ["key", "value"]
    else:
        out = apply(data, {"fold": ["y1", "y2"], "as": as_})

    expected = pd.DataFrame(
        {
            "x": 2 * data["x"].tolist(),
            as_[0]: 3 * ["y1"] + 3 * ["y2"],
            as_[1]: data["y1"].tolist() + data["y2"].tolist(),
        }
    )
    assert out.equals(expected)


@pytest.mark.parametrize("groupby", [True, False])
@pytest.mark.parametrize("op", set(AGGREGATES) - set(AGG_SKIP))
def test_aggregate_transform(data, groupby, op):
    field = "x"
    col = "z"
    group = "c"

    transform = {"aggregate": [{"op": op, "field": field, "as": col}]}
    if groupby:
        transform["groupby"] = [group]

    op = AGG_REPLACEMENTS.get(op, op)
    out = apply(data, transform)

    if groupby:
        grouped = data.groupby(group)[field].aggregate(op)
        grouped.name = col
        grouped = grouped.reset_index()
    else:
        grouped = pd.DataFrame({col: [data[field].aggregate(op)]})

    assert grouped.equals(out)


@pytest.mark.parametrize("method", ["value", "mean", "median", "max", "min"])
def test_impute_transform_no_groupby(method):
    data = pd.DataFrame({"x": [1, 2], "y": [2, 3]})
    transform = alt.ImputeTransform(
        impute="y", key="x", keyvals={"start": 0, "stop": 5}, value=0, method=method
    )
    if method == "value":
        value = 0
    else:
        value = data.y.agg(method)
    imputed = apply(data, transform)

    assert_equal(imputed.x.values, range(5))
    assert_equal(imputed.y[[1, 2]].values, data.y.values)
    assert_equal(imputed.y[[0, 3, 4]].values, value)


def test_impute_transform_with_groupby():
    data = pd.DataFrame(
        {"x": [1, 2, 4, 1, 3, 4], "y": [1, 2, 4, 2, 4, 5], "cat": list("AAABBB")}
    )

    transform = alt.ImputeTransform(impute="y", key="x", method="max", groupby=["cat"])

    imputed = apply(data, transform)
    assert_equal(imputed.x.values, np.tile(range(1, 5), 2))
    assert_equal(imputed.y.values, [1, 2, 4, 4, 2, 5, 4, 5])


@pytest.mark.parametrize("groupby", [True, False])
@pytest.mark.parametrize("op", set(AGGREGATES) - set(AGG_SKIP))
def test_joinaggregate_transform(data, groupby, op):
    field = "x"
    col = "z"
    group = "c"

    transform = {"joinaggregate": [{"op": op, "field": field, "as": col}]}
    if groupby:
        transform["groupby"] = [group]

    op = AGG_REPLACEMENTS.get(op, op)
    out = apply(data, transform)

    def validate(group):
        return np.allclose(group[field].aggregate(op), group[col])

    if groupby:
        assert out.groupby(group).apply(validate).all()
    else:
        assert validate(out)


@pytest.mark.parametrize("lookup_key", ["c", "c2"])
def test_lookup_transform(data, lookup_key):
    lookup = pd.DataFrame({lookup_key: list("ABCD"), "z": [3, 1, 4, 5]})
    transform = {
        "lookup": "c",
        "from": {"data": to_values(lookup), "key": lookup_key, "fields": ["z"]},
    }
    out1 = apply(data, transform)
    out2 = pd.merge(data, lookup, left_on="c", right_on=lookup_key)
    if lookup_key != "c":
        out2 = out2.drop(lookup_key, axis=1)
    assert out1.equals(out2)


@pytest.mark.parametrize("lookup_key", ["c", "c2"])
@pytest.mark.parametrize("default", [None, "missing"])
def test_lookup_transform_default(data, lookup_key, default):
    lookup = pd.DataFrame({lookup_key: list("ABC"), "z": [3, 1, 4]})
    transform = {
        "lookup": "c",
        "from": {"data": to_values(lookup), "key": lookup_key, "fields": ["z"]},
    }
    if default is not None:
        transform["default"] = default

    out = apply(data, transform)
    undef = out["c"] == "D"
    if default is None:
        assert out.loc[undef, "z"].isnull().all()
    else:
        assert (out.loc[undef, "z"] == default).all()


def test_bin_transform_simple(data):
    transform = {"bin": True, "field": "x", "as": "xbin"}
    out = apply(data, transform)
    assert "xbin" in out.columns

    transform = {"bin": True, "field": "x", "as": ["xbin1", "xbin2"]}
    out = apply(data, transform)
    assert "xbin1" in out.columns
    assert "xbin2" in out.columns


@pytest.mark.parametrize("maxbins", [5, 10, 20])
@pytest.mark.parametrize("nice", [True, False])
def test_bin_transform_maxbins(nice, maxbins):
    data = pd.DataFrame({"x": np.arange(100)})
    transform = {"bin": {"maxbins": maxbins, "nice": nice}, "field": "x", "as": "xbin"}
    out = apply(data, transform)
    bins = np.sort(out.xbin.unique())
    assert len(bins) - 1 <= maxbins
    assert not out.xbin.isnull().any()


@pytest.mark.parametrize("step", [5, 10, 20])
@pytest.mark.parametrize("nice", [True, False])
def test_bin_transform_step(nice, step):
    data = pd.DataFrame({"x": np.arange(100)})
    transform = {"bin": {"step": step, "nice": nice}, "field": "x", "as": "xbin"}
    out = apply(data, transform)
    bins = np.sort(out.xbin.unique())
    assert np.allclose(bins[1:] - bins[:-1], step)
    assert not out.xbin.isnull().any()


@pytest.mark.parametrize("nice", [True, False])
def test_bin_transform_steps(nice, steps=[5, 10, 20]):
    data = pd.DataFrame({"x": range(100)})
    transform = {"bin": {"steps": steps, "nice": nice}, "field": "x", "as": "xbin"}
    out = apply(data, transform)
    bins = np.sort(out.xbin.unique())
    assert bins[1] - bins[0] in steps
    assert not out.xbin.isnull().any()


@pytest.mark.parametrize("N", [1, 5, 50])
def test_sample_transform(data, N):
    transform = {"sample": N}
    out = apply(data, transform)

    # Ensure the shape is correct
    assert out.shape == (min(N, data.shape[0]), data.shape[1])

    # Ensure the content are correct
    assert out.equals(data.iloc[out.index])


def test_timeunit_transform(data):
    transform = {"timeUnit": "year", "field": "t", "as": "year"}
    out = apply(data, transform)
    assert (out.year == pd.to_datetime("2012-01-01")).all()


def test_window_transform_basic(data):
    transform = {"window": [{"op": "sum", "field": "x", "as": "xsum"}]}
    out = apply(data, transform)
    expected = data["x"].cumsum()
    assert out["xsum"].equals(expected.astype(float))


def test_window_transform_sorted(data):
    transform = {
        "window": [{"op": "sum", "field": "x", "as": "xsum"}],
        "sort": [{"field": "x"}],
    }
    out = apply(data, transform)
    expected = data["x"].sort_values().cumsum().sort_index()
    assert out["xsum"].equals(expected.astype(float))


def test_window_transform_grouped(data):
    transform = {
        "window": [{"op": "sum", "field": "x", "as": "xsum"}],
        "groupby": ["y"],
    }
    out = apply(data, transform)
    expected = data.groupby("y").rolling(len(data), min_periods=1)
    expected = expected["x"].sum().reset_index("y", drop=True).sort_index()
    assert out["xsum"].equals(expected)


def test_multiple_transforms(data):
    transform = [
        {"calculate": "0.5 * (datum.x + datum.y)", "as": "xy_mean"},
        {"filter": "datum.x < datum.xy_mean"},
    ]
    out1 = apply(data, transform)
    out2 = data.copy()
    out2["xy_mean"] = 0.5 * (data.x + data.y)
    out2 = out2[out2.x < out2.xy_mean]

    assert out1.equals(out2)
