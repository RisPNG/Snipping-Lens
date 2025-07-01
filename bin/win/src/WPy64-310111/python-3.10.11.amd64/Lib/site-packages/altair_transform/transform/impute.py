import altair as alt
import numpy as np
import pandas as pd
from .visitor import visit


@visit.register(alt.ImputeTransform)
def visit_impute(transform: alt.ImputeTransform, df: pd.DataFrame) -> pd.DataFrame:
    transform = transform.to_dict()

    field = transform["impute"]
    key = transform["key"]

    frame = transform.get("frame", None)
    if frame:
        raise NotImplementedError("Impute Transform frame argument.")

    # Keyvals are the values at which the field is imputed.
    keyvals = transform.get("keyvals", [])
    if isinstance(keyvals, dict):
        start = keyvals.get("start", 0)
        stop = keyvals["stop"]
        step = keyvals.get("step", np.sign(stop - start))
        keyvals = np.arange(start, stop, step)
    keyvals = np.sort(np.unique(np.concatenate([keyvals, df[key].values])))
    keyvals = pd.Series(keyvals, name=key)

    groupby = transform.get("groupby", [])

    method = transform.get("method", "value")
    value = transform.get("value", None)
    if "method" not in transform and "value" not in transform:
        raise ValueError("Must specify either method or value.")
    if method == "value" and "value" not in transform:
        raise ValueError("For method='value', must supply a value argument.")

    def _impute(group):
        imputed = pd.merge(keyvals, group, on=key, how="left")
        if method == "value":
            fill = value
        else:
            fill = group[field].agg(method)
        imputed[field].fillna(fill, inplace=True)
        for col in groupby:
            imputed[col].fillna(group[col].iloc[0], inplace=True)
        return imputed

    if groupby:
        imputed = df.groupby(groupby).apply(_impute).reset_index(drop=True)
    else:
        imputed = _impute(df)

    return imputed
