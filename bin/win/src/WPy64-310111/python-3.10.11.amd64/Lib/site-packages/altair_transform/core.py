"""Core altair_transform routines."""

from typing import Any

import pandas as pd
import altair as alt

from altair_transform.transform import visit
from altair_transform.utils import to_dataframe
from altair_transform.extract import extract_transform

__all__ = ["apply", "extract_data", "transform_chart"]


def apply(df: pd.DataFrame, transform: Any, inplace: bool = False) -> pd.DataFrame:
    """Apply transform or transforms to dataframe.

    Parameters
    ----------
    df : pd.DataFrame
    transform : list|dict
        A transform specification or list of transform specifications.
        Each specification must be valid according to Altair's transform
        schema.
    inplace : bool
        If True, then dataframe may be modified in-place. Default: False.

    Returns
    -------
    df_transformed : pd.DataFrame
        The transformed dataframe.

    Example
    -------
    >>> import pandas as pd
    >>> data = pd.DataFrame({'x': range(5), 'y': list('ABCAB')})
    >>> chart = alt.Chart(data).transform_aggregate(sum_x='sum(x)', groupby=['y'])
    >>> apply(data, chart.transform)
       y  sum_x
    0  A      3
    1  B      5
    2  C      2
    """
    if not inplace:
        df = df.copy()
    if transform is alt.Undefined:
        return df
    return visit(transform, df)


def extract_data(
    chart: alt.Chart, apply_encoding_transforms: bool = True
) -> pd.DataFrame:
    """Extract transformed data from a chart.

    This only works with data and transform defined at the
    top level of the chart.

    Parameters
    ----------
    chart : alt.Chart
        The chart instance from which the data and transform
        will be extracted
    apply_encoding_transforms : bool
        If True (default), then apply transforms specified within an
        encoding as well as those specified directly in the transforms
        attribute.

    Returns
    -------
    df_transformed : pd.DataFrame
        The extracted and transformed dataframe.

    Example
    -------
    >>> import pandas as pd
    >>> data = pd.DataFrame({'x': range(5), 'y': list('ABCAB')})
    >>> chart = alt.Chart(data).mark_bar().encode(x='sum(x)', y='y')
    >>> extract_data(chart)
       y  sum_x
    0  A      3
    1  B      5
    2  C      2
    """
    if apply_encoding_transforms:
        chart = extract_transform(chart)
    return apply(to_dataframe(chart.data, chart), chart.transform)


def transform_chart(
    chart: alt.Chart, extract_encoding_transforms: bool = True
) -> alt.Chart:
    """Return a chart with the transformed data

    Parameters
    ----------
    chart : alt.Chart
        The chart instance from which the data and transform
        will be extracted.
    extract_encoding_transforms : bool
        If True (default), then also extract transforms from encodings.

    Returns
    -------
    chart_out : alt.Chart
        A copy of the input chart with the transformed data.

    Example
    -------
    >>> import pandas as pd
    >>> data = pd.DataFrame({'x': range(5), 'y': list('ABCAB')})
    >>> chart = alt.Chart(data).mark_bar().encode(x='sum(x)', y='y')
    >>> new_chart = transform_chart(chart)
    >>> new_chart.data
       y  sum_x
    0  A      3
    1  B      5
    2  C      2
    >>> new_chart.encoding
    FacetedEncoding({
      x: PositionFieldDef({
        field: FieldName('sum_x'),
        title: 'Sum of x',
        type: StandardType('quantitative')
      }),
      y: PositionFieldDef({
        field: FieldName('y'),
        type: StandardType('nominal')
      })
    })
    """
    if extract_encoding_transforms:
        chart = extract_transform(chart)
    chart = chart.properties(data=extract_data(chart, apply_encoding_transforms=False))
    chart.transform = alt.Undefined
    return chart
