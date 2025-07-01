import pandas as pd
import tempfile

import pytest

import altair as alt
from altair_transform.utils import to_dataframe


@pytest.fixture
def df():
    return pd.DataFrame({"x": [1, 2, 3], "y": ["A", "B", "C"]})


@pytest.fixture
def csv_data(df):
    with tempfile.NamedTemporaryFile("w+", suffix=".csv") as f:
        df.to_csv(f.name, index=False)
        yield {"url": f.name}


@pytest.fixture
def json_data(df):
    with tempfile.NamedTemporaryFile("w+", suffix=".json") as f:
        df.to_json(f.name, orient="records")
        yield {"url": f.name}


@pytest.fixture
def inline_data(df):
    return {"values": df.to_dict(orient="records")}


@pytest.fixture
def named_data(df):
    return {"name": "my-dataset"}


@pytest.fixture
def sequence_data(df):
    return {"sequence": {"start": 1, "stop": 4, "as": "x"}}


@pytest.fixture
def chart(named_data, inline_data):
    return alt.Chart(
        data=named_data,
        mark="bar",
        datasets={named_data["name"]: inline_data["values"]},
    )


@pytest.mark.parametrize("data_type", [dict, alt.Data])
def test_csv_to_dataframe(df, csv_data, data_type):
    data = data_type(csv_data)
    assert df.equals(to_dataframe(data))


@pytest.mark.parametrize("data_type", [dict, alt.Data])
def test_json_to_dataframe(df, json_data, data_type):
    data = data_type(json_data)
    assert df.equals(to_dataframe(data))


@pytest.mark.parametrize("data_type", [dict, alt.Data])
def test_inline_to_dataframe(df, inline_data, data_type):
    data = data_type(inline_data)
    assert df.equals(to_dataframe(data))


@pytest.mark.parametrize("data_type", [dict, alt.Data])
def test_named_to_dataframe(df, chart, named_data, data_type):
    data = data_type(named_data)
    assert df.equals(to_dataframe(data, context=chart))


@pytest.mark.parametrize("data_type", [dict, alt.Data])
def test_sequence_to_dataframe(df, sequence_data, data_type):
    data = data_type(sequence_data)
    assert df[["x"]].equals(to_dataframe(data))
