import altair as alt
import pandas as pd
from .visitor import visit
from ..vegaexpr import eval_vegajs


@visit.register(alt.CalculateTransform)
def visit_calculate(
    transform: alt.CalculateTransform, df: pd.DataFrame
) -> pd.DataFrame:
    transform = transform.to_dict()
    col = transform["as"]
    calc = transform["calculate"]
    df[col] = df.apply(lambda datum: eval_vegajs(calc, datum), axis=1)
    return df
