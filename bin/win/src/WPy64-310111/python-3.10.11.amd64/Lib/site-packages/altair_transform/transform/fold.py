import altair as alt
import pandas as pd
from .visitor import visit


@visit.register(alt.FoldTransform)
def visit_fold(transform: alt.FoldTransform, df: pd.DataFrame) -> pd.DataFrame:
    transform = transform.to_dict()
    fold = transform["fold"]
    var_name, value_name = transform.get("as", ("key", "value"))
    value_vars = [c for c in df.columns if c in fold]
    id_vars = [c for c in df.columns if c not in fold]
    return df.melt(
        id_vars=id_vars, value_vars=value_vars, var_name=var_name, value_name=value_name
    )
