import altair as alt
import numpy as np
import pandas as pd
from .visitor import visit


@visit.register(alt.AggregateTransform)
def visit_aggregate(
    transform: alt.AggregateTransform, df: pd.DataFrame
) -> pd.DataFrame:
    transform = transform.to_dict()
    groupby = transform.get("groupby", [])
    agg_cols = {}
    for aggregate in transform["aggregate"]:
        op = aggregate["op"]
        col = aggregate["as"]
        field = aggregate.get("field", df.columns[0])

        op = AGG_REPLACEMENTS.get(op, op)
        if field == "*" and field not in df.columns:
            field = df.columns[0]

        if groupby:
            agg_cols[col] = df.groupby(groupby)[field].aggregate(op)
        else:
            agg_cols[col] = [df[field].aggregate(op)]

    df = pd.DataFrame(agg_cols)
    if groupby:
        df = df.reset_index()
    return df


def confidence_interval(x: np.ndarray, level: float):
    from scipy import stats

    return stats.t.interval(level, len(x) - 1, loc=x.mean(), scale=x.sem())


AGG_REPLACEMENTS = {
    "argmin": "idxmin",
    "argmax": "idxmax",
    "average": "mean",
    "ci0": lambda x: confidence_interval(x, 0.05),
    "ci1": lambda x: confidence_interval(x, 0.95),
    "distinct": "nunique",
    "stderr": "sem",
    "stdev": "std",
    "stdevp": lambda x: x.std(ddof=0),
    "missing": lambda x: x.isnull().sum(),
    "q1": lambda x: x.quantile(0.25),
    "q3": lambda x: x.quantile(0.75),
    "valid": "count",
    "values": "count",
    "variance": "var",
    "variancep": lambda x: x.var(ddof=0),
}
