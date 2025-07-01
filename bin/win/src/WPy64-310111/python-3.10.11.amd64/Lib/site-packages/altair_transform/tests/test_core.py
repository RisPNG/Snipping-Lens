import altair as alt
from altair_transform import extract_data, transform_chart
import numpy as np
import pandas as pd
import pytest


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


@pytest.fixture
def chart(data):
    return (
        alt.Chart(data)
        .transform_calculate(xpy="datum.x + datum.y", xmy="datum.x - datum.y")
        .mark_point()
        .encode(x="xpy:Q", y="xmy:Q")
    )


def test_extract_data(data, chart):
    out1 = extract_data(chart)
    out2 = data.copy()
    out2["xpy"] = data.x + data.y
    out2["xmy"] = data.x - data.y
    assert out1.equals(out2)


def test_transform_chart(data, chart):
    original_chart = chart.copy()
    data_out = extract_data(chart)
    chart_out = transform_chart(chart)

    # Original chart not modified
    assert original_chart == chart

    # Transform applied to output chart
    assert chart_out.data.equals(data_out)
    assert chart_out.transform is alt.Undefined
    assert chart.mark == chart_out.mark
    assert chart.encoding == chart_out.encoding


def test_transform_chart_with_aggregate():
    data = pd.DataFrame({"x": list("AABBBCCCC")})
    chart = alt.Chart(data).mark_bar().encode(x="x:N", y="count():Q")
    chart_out = transform_chart(chart)
    assert chart_out.data.equals(pd.DataFrame({"x": list("ABC"), "__count": [2, 3, 4]}))
    assert chart_out.encoding.to_dict() == {
        "x": {"field": "x", "type": "nominal"},
        "y": {"field": "__count", "type": "quantitative", "title": "Count of Records"},
    }
