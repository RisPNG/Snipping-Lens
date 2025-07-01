import pytest

from altair_transform.extract import _encoding_to_transform
from typing import Any, Dict, List, NamedTuple


class _TestCase(NamedTuple):
    encoding: Dict[str, Dict[str, Any]]
    expected_encoding: Dict[str, Dict[str, Any]]
    expected_transform: List[Dict[str, Any]]


@pytest.mark.parametrize(
    _TestCase._fields,
    [
        _TestCase(
            encoding={"x": {"aggregate": "count", "type": "quantitative"}},
            expected_encoding={
                "x": {
                    "field": "__count",
                    "type": "quantitative",
                    "title": "Count of Records",
                }
            },
            expected_transform=[{"aggregate": [{"op": "count", "as": "__count"}]}],
        ),
        _TestCase(
            encoding={"x": {"field": "foo", "bin": True, "type": "ordinal"}},
            expected_encoding={
                "x": {"field": "foo_binned", "type": "ordinal", "title": "foo (binned)"}
            },
            expected_transform=[{"bin": True, "field": "foo", "as": "foo_binned"}],
        ),
        _TestCase(
            encoding={
                "x": {"aggregate": "sum", "field": "people", "type": "quantitative"},
                "y": {"field": "age", "type": "ordinal"},
            },
            expected_encoding={
                "x": {
                    "field": "sum_people",
                    "type": "quantitative",
                    "title": "Sum of people",
                },
                "y": {"field": "age", "type": "ordinal"},
            },
            expected_transform=[
                {
                    "aggregate": [{"op": "sum", "field": "people", "as": "sum_people"}],
                    "groupby": ["age"],
                }
            ],
        ),
        _TestCase(
            encoding={
                "x": {"aggregate": "count", "type": "quantitative"},
                "y": {"field": "age", "bin": {"maxbins": 10}, "type": "quantitative"},
            },
            expected_encoding={
                "x": {
                    "field": "__count",
                    "type": "quantitative",
                    "title": "Count of Records",
                },
                "y": {
                    "field": "age_binned",
                    "bin": "binned",
                    "type": "quantitative",
                    "title": "age (binned)",
                },
                "y2": {"field": "age_binned2"},
            },
            expected_transform=[
                {
                    "bin": {"maxbins": 10},
                    "field": "age",
                    "as": ["age_binned", "age_binned2"],
                },
                {
                    "aggregate": [{"op": "count", "as": "__count"}],
                    "groupby": ["age_binned", "age_binned2"],
                },
            ],
        ),
        _TestCase(
            encoding={
                "x": {"aggregate": "count", "type": "quantitative"},
                "y": {"field": "age", "bin": True, "type": "ordinal"},
            },
            expected_encoding={
                "x": {
                    "field": "__count",
                    "type": "quantitative",
                    "title": "Count of Records",
                },
                "y": {
                    "field": "age_binned",
                    "type": "ordinal",
                    "title": "age (binned)",
                },
            },
            expected_transform=[
                {"bin": True, "field": "age", "as": "age_binned"},
                {
                    "aggregate": [{"op": "count", "as": "__count"}],
                    "groupby": ["age_binned"],
                },
            ],
        ),
        _TestCase(
            encoding={
                "x": {"aggregate": "count", "field": "x", "type": "quantitative"},
                "y": {"field": "y", "timeUnit": "day", "type": "ordinal"},
            },
            expected_encoding={
                "x": {
                    "field": "__count",
                    "type": "quantitative",
                    "title": "Count of Records",
                },
                "y": {
                    "field": "day_y",
                    "timeUnit": "day",
                    "type": "ordinal",
                    "title": "y (day)",
                },
            },
            expected_transform=[
                {"timeUnit": "day", "field": "y", "as": "day_y"},
                {
                    "aggregate": [{"field": "x", "op": "count", "as": "__count"}],
                    "groupby": ["day_y"],
                },
            ],
        ),
        _TestCase(
            encoding={
                "x": {"field": "xval", "type": "ordinal"},
                "y": {
                    "field": "yval",
                    "type": "quantitative",
                    "impute": {"value": 0, "method": "mean", "keyvals": [1, 2, 3]},
                },
                "color": {"field": "cval", "type": "nominal"},
            },
            expected_encoding={
                "x": {"field": "xval", "type": "ordinal"},
                "y": {"field": "yval", "type": "quantitative"},
                "color": {"field": "cval", "type": "nominal"},
            },
            expected_transform=[
                {
                    "impute": "yval",
                    "key": "xval",
                    "keyvals": [1, 2, 3],
                    "groupby": ["cval"],
                    "value": 0,
                    "method": "mean",
                }
            ],
        ),
        _TestCase(
            encoding={
                "x": {"field": "xval", "bin": "binned", "type": "ordinal"},
                "y": {"aggregate": "count", "type": "quantitative"},
            },
            expected_encoding={
                "x": {"field": "xval", "bin": "binned", "type": "ordinal"},
                "y": {
                    "field": "__count",
                    "title": "Count of Records",
                    "type": "quantitative",
                },
            },
            expected_transform=[
                {"aggregate": [{"op": "count", "as": "__count"}], "groupby": ["xval"]}
            ],
        ),
    ],
)
def test_extract_simple_aggregate(encoding, expected_encoding, expected_transform):
    encoding, transform = _encoding_to_transform(encoding)
    assert encoding == expected_encoding
    assert transform == expected_transform
