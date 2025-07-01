import altair as alt
import numpy as np
import pandas as pd
from .visitor import visit


@visit.register(alt.SampleTransform)
def visit_sample(transform: alt.SampleTransform, df: pd.DataFrame) -> pd.DataFrame:
    transform = transform.to_dict()
    sample = transform["sample"]

    if sample < df.shape[0]:
        index = np.sort(np.random.permutation(df.shape[0])[:sample])
        df = df.iloc[index]
    return df
