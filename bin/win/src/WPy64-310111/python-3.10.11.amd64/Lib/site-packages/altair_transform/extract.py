"""Tools for extracting transforms from encodings"""
from collections import defaultdict
import copy
from typing import Any, Dict, List, Tuple

import altair as alt

_EncodingType = Dict[str, dict]
_SpecType = Dict[str, Any]
_TransformType = List[_SpecType]


def extract_transform(chart: alt.Chart) -> alt.Chart:
    """Extract transforms from encodings

    This takes a chart with transforms specified within encodings, and returns
    an equivalent chart with transforms specified separately in the ``transform``
    field.

    Parameters
    ----------
    chart : alt.Chart
        Input chart, which will not be modified

    Returns
    -------
    chart : alt.Chart
        A copy of the input chart with any encoding-specified transforms moved
        to the transforms-attribute

    Example
    -------
    >>> chart = alt.Chart('data.csv').mark_bar().encode(x='mean(x):Q', y='y:N')
    >>> new_chart = extract_transform(chart)
    >>> new_chart.transform
    [AggregateTransform({
      aggregate: [AggregatedFieldDef({
        as: FieldName('mean_x'),
        field: FieldName('x'),
        op: AggregateOp('mean')
      })],
      groupby: [FieldName('y')]
    })]
    >>> new_chart.encoding
    FacetedEncoding({
      x: PositionFieldDef({
        field: FieldName('mean_x'),
        title: 'Mean of x',
        type: StandardType('quantitative')
      }),
      y: PositionFieldDef({
        field: FieldName('y'),
        type: StandardType('nominal')
      })
    })
    """

    chart = chart.copy()
    encoding_dict = chart.encoding.copy().to_dict(context={"data": chart.data})
    encoding, transform = _encoding_to_transform(encoding_dict)
    if transform:
        chart.encoding = alt.FacetedEncoding.from_dict(encoding)
        if chart.transform is alt.Undefined:
            chart.transform = []
        chart.transform.extend(alt.Transform.from_dict(t) for t in transform)
    return chart


def _encoding_to_transform(
    encoding: _EncodingType,
) -> Tuple[_EncodingType, _TransformType]:
    """Extract transforms from an encoding dict."""
    # TODO: what if one encoding has multiple transforms? Is this valid?
    by_category: Dict[str, _EncodingType] = defaultdict(dict)
    new_encoding: _EncodingType = {}
    for channel, spec in encoding.items():
        for key in ["impute", "bin", "aggregate", "timeUnit"]:
            if key in spec:
                by_category[key][channel] = copy.deepcopy(spec)
                break
        else:
            new_encoding[channel] = copy.deepcopy(spec)

    groupby: List[str] = [
        enc["field"] for enc in new_encoding.values() if "field" in enc
    ]
    transforms: _TransformType = []
    field: str = ""
    new_field: str = ""
    new_field2: str = ""

    for channel, spec in by_category["bin"].items():
        if spec["bin"] == "binned":
            new_encoding[channel] = spec
            if "field" in spec:
                groupby.append(spec["field"])
            continue
        field = spec.pop("field")
        new_field = f"{field}_binned"
        new_field2 = f"{field}_binned2"
        needs_upper_limit: bool = (
            channel in ["x", "y"]
            and spec["type"] == "quantitative"
            and f"{channel}2" not in encoding
        )
        bin_transform: _SpecType = {
            "field": field,
            "bin": spec.pop("bin"),
            "as": [new_field, new_field2] if needs_upper_limit else new_field,
        }
        spec["field"] = new_field
        spec.setdefault("title", f"{field} (binned)")
        new_encoding[channel] = spec
        groupby.append(new_field)

        if needs_upper_limit:
            spec["bin"] = "binned"
            new_encoding[f"{channel}2"] = {"field": new_field2}
            groupby.append(new_field2)
        transforms.append(bin_transform)

    for channel, spec in by_category["timeUnit"].items():
        timeUnit: str = spec[
            "timeUnit"
        ]  # leave timeUnit in spec for the sake of formatting
        field = spec.pop("field")
        new_field = f"{timeUnit}_{field}"
        spec["field"] = new_field
        spec.setdefault("title", f"{field} ({timeUnit})")
        new_encoding[channel] = spec
        transforms.append({"timeUnit": timeUnit, "field": field, "as": new_field})
        groupby.append(new_field)

    for channel, spec in by_category["impute"].items():
        keychannel = "y" if channel == "x" else "x"
        key = encoding.get(keychannel, {}).get("field", spec["field"])
        impute_transform: _SpecType = spec.pop("impute")
        impute_transform.update(
            {
                "impute": spec["field"],
                "key": key,
                "groupby": [field for field in groupby if field != key],
            }
        )
        new_encoding[channel] = spec
        transforms.append(impute_transform)

    agg_transforms: _TransformType = []
    for channel, spec in by_category["aggregate"].items():
        aggregate: str = spec.pop("aggregate")
        field = spec.pop("field", None)
        new_field = "__count" if aggregate == "count" else f"{aggregate}_{field}"
        agg_dict: Dict[str, str] = {"op": aggregate, "as": new_field}
        if field is not None:
            agg_dict["field"] = field
        agg_transforms.append(agg_dict)
        spec["field"] = new_field
        spec.setdefault(
            "title",
            (
                "Count of Records"
                if aggregate == "count"
                else f"{aggregate.title()} of {field}"
            ),
        )
        new_encoding[channel] = spec
    if agg_transforms:
        transform: Dict[str, list] = {"aggregate": agg_transforms}
        if groupby:
            transform["groupby"] = groupby
        transforms.append(transform)

    return new_encoding, transforms
