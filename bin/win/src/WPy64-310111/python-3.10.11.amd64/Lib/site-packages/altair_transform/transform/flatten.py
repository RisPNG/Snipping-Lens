import altair as alt
import pandas as pd
from .visitor import visit


@visit.register(alt.FlattenTransform)
def visit_flatten(transform: alt.FlattenTransform, df: pd.DataFrame) -> pd.DataFrame:
    transform = transform.to_dict()

    fields = transform["flatten"]
    out = transform.get("as", [])

    if len(out) < len(fields):
        out = out + fields[len(out) :]
    if len(out) > len(fields):
        out = out[: len(fields)]

    if not fields:
        return df

    to_flatten = df[fields]
    others = df[[c for c in df.columns if c not in fields]]

    def flatten_row(row):
        flattened = to_flatten.iloc[row].apply(pd.Series).T
        flattened.index = flattened.shape[0] * [row]
        return flattened

    flattened = pd.concat([flatten_row(i) for i in range(df.shape[0])], axis=0)
    flattened.columns = out

    return flattened.join(others).reset_index(drop=True)
