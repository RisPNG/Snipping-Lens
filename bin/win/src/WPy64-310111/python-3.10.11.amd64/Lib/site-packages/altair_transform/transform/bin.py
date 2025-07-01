"""Implementation of the bin transform."""
import altair as alt
import pandas as pd
import numpy as np

from .visitor import visit

import math
from typing import List, Optional, Tuple, Union

Number = Union[int, float]


def _cut(series: pd.Series, edges: np.ndarray, return_upper: bool = False):
    """Like pd.cut(), but include outliers in the outer bins."""
    bins = pd.cut(series, edges, labels=False)
    bins[series <= edges[0]] = 0
    bins[series >= edges[-1]] = len(edges) - 2
    bins = bins.astype(int)
    bins1 = pd.Series(edges[bins.values], index=bins.index)
    if return_upper:
        bins2 = pd.Series(edges[bins.values + 1], index=bins.index)
        return bins1, bins2
    else:
        return bins1


@visit.register(alt.BinTransform)
def visit_bin(transform: alt.BinTransform, df: pd.DataFrame) -> pd.DataFrame:
    transform_dct: dict = transform.to_dict()
    col = transform_dct["as"]
    bin = transform_dct["bin"]
    field = transform_dct["field"]
    extent = df[field].min(), df[field].max()

    bins = calculate_bins(extent, **({} if bin is True else bin))

    if isinstance(col, str):
        df[col] = _cut(df[field], bins, return_upper=False)
    else:
        df[col[0]], df[col[1]] = _cut(df[field], bins, return_upper=True)

    return df


def calculate_bins(
    extent: Tuple[Number, Number],
    anchor: Optional[Number] = None,
    base: Number = 10,
    divide: List[Number] = [5, 2],
    maxbins: Number = 10,
    minstep: Number = 0,
    nice: bool = True,
    step: Optional[Number] = None,
    steps: Optional[List[Number]] = None,
    span: Optional[Number] = None,
) -> np.ndarray:
    """Calculate the bins for a given dataset.

    This is a Python translation of the Javascript function available at
    https://github.com/vega/vega/blob/v5.7.3/packages/vega-statistics/src/bin.js

    Parameters
    ----------
    extent: Tuple[Number, Number]
        A two-element ([min, max]) array indicating the range of desired bin values.
    anchor: Number
        A value in the binned domain at which to anchor the bins, shifting the bin boundaries
        if necessary to ensure that a boundary aligns with the anchor value.
        Default value: the minimum bin extent value
    base: Number
        The number base to use for automatic bin determination (default is base 10).
        Default value: 10
    divide: List[Number]
        Scale factors indicating allowable subdivisions. The default value is [5, 2],
        which indicates that for base 10 numbers (the default base), the method may
        consider dividing bin sizes by 5 and/or 2. For example, for an initial step
        size of 10, the method can check if bin sizes of 2 (= 10/5), 5 (= 10/2),
        or 1 (= 10/(5*2)) might also satisfy the given constraints.
        Default value: [5, 2]
    maxbins: Number
        Maximum number of bins.
        Default value: 10
    minstep: Number
        A minimum allowable step size (particularly useful for integer values).
    nice: boolean
        If true, attempts to make the bin boundaries use human-friendly boundaries,
        such as multiples of ten.
        Default value: True
    step: Number
        An exact step size to use between bins.
        Note: If provided, options such as maxbins will be ignored.
    steps: List[Number]
        An array of allowable step sizes to choose from.

    Returns
    -------
    bins : numpy.ndarray
        array of bin edges.
    """
    min_, max_ = extent
    assert max_ > min_
    span = span or (max_ - min_) or abs(min_) or 1
    logb = math.log(base)

    if step is not None:
        # If step is provided, we use it.
        pass
    elif steps is not None:
        # If steps provided, limit choice to acceptable sizes.
        v = span / maxbins
        steps = [step for step in steps if step < v]
        step = max(steps) if steps else steps[0]
    else:
        # Otherwise use span to determine step size.
        level = math.ceil(math.log(maxbins) / logb)
        step = max(minstep, pow(base, round(math.log(span) / logb) - level))

        # increase step size if too many bins
        while math.ceil(span / step) > maxbins:
            step *= base

        # decrease step size if allowed
        for div in divide:
            v = step / div
            if v >= minstep and span / v <= maxbins:
                step = v

    # update precision of min_ and max_
    v = math.log(step)
    precision = 0 if v >= 0 else math.floor(-v / logb) + 1
    eps = pow(base, -precision - 1)
    if nice:
        v = math.floor(min_ / step + eps) * step
        min_ = v - step if min_ < v else v
        max_ = math.ceil(max_ / step) * step

    start = min_
    stop = max_ if max_ != min_ else min_ + step
    return np.arange(start, stop + 0.01 * step, step)
