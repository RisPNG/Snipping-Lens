from typing import Dict

import altair as alt
import pandas as pd
from .visitor import visit
from .aggregate import AGG_REPLACEMENTS


@visit.register(alt.WindowTransform)
def visit_window(transform: alt.WindowTransform, df: pd.DataFrame) -> pd.DataFrame:
    transform = transform.to_dict()
    window = transform["window"]
    frame = transform.get("frame", [None, 0])
    groupby = transform.get("groupby", [])
    ignorePeers = transform.get("ignorePeers", False)
    sort = transform.get("sort", [])

    if ignorePeers:
        raise NotImplementedError("Window transform with ignorePeers=True")

    # First sort the dataframe if required.
    if sort:
        fields = [s["field"] for s in sort]
        ascending = [s.get("order", "ascending") == "ascending" for s in sort]
        df2 = df.sort_values(fields, ascending=ascending)
    else:
        df2 = df

    if groupby:
        grouped = df2.groupby(groupby)
    else:
        grouped = df2

    # TODO: implement other frame options
    if frame == [None, 0]:
        rolling = grouped.rolling(len(df), min_periods=1)
    elif frame[1] == 0:
        rolling = grouped.rolling(frame[0] + 1, min_periods=1)
    elif frame == [None, None]:
        rolling = grouped.rolling(2 * len(df), min_periods=1, center=True)
    elif frame[0] == frame[1]:
        rolling = grouped.rolling(2 * frame[0] + 1, min_periods=1, center=True)
    else:
        raise NotImplementedError("frame={}".format(frame))

    for w in window:
        # TODO: if field not specified, must be count, rank, or dense_rank
        if "param" in w:
            raise NotImplementedError("window function with param")
        col = w.get("field", df2.columns[0])
        if col == "*" and col not in df2.columns:
            col = df2.columns[0]
        agg = w["op"]
        agg = WINDOW_AGG_REPLACEMENTS.get(agg, agg)
        df2[w["as"]] = rolling[col].aggregate(agg).reset_index(groupby, drop=True)

    return df2.loc[df.index]


# TODO: implement these.
WINDOW_AGG_REPLACEMENTS: Dict[str, object] = {
    "row_number": "row_number",
    "rank": "rank",
    "dense_rank": "dense_rank",
    "percent_rank": "percent_rank",
    "cume_dist": "cume_dist",
    "ntile": "ntile",
    "lag": "lag",
    "lead": "lead",
    "first_value": "first_value",
    "last_value": "last_value",
    "nth_value": "nth_value",
}
WINDOW_AGG_REPLACEMENTS.update(AGG_REPLACEMENTS)
