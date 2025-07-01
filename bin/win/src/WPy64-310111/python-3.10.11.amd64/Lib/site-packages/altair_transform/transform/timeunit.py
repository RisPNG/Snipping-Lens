import altair as alt
import pandas as pd
from .visitor import visit
from ..utils.timeunit import compute_timeunit


@visit.register(alt.TimeUnitTransform)
def visit_timeunit(transform: alt.TimeUnitTransform, df: pd.DataFrame) -> pd.DataFrame:
    transform = transform.to_dict()
    df[transform["as"]] = compute_timeunit(
        df[transform["field"]], transform["timeUnit"]
    )
    return df
