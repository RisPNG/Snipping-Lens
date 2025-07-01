from functools import singledispatch
from typing import Any

import altair as alt
import pandas as pd


@singledispatch
def visit(transform: Any, df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError(f"transform of type {type(transform)}")


@visit.register(list)
def visit_list(transform: list, df: pd.DataFrame) -> pd.DataFrame:
    for t in transform:
        df = visit(t, df)
    return df


@visit.register(dict)
def visit_dict(transform: dict, df: pd.DataFrame) -> pd.DataFrame:
    transform = alt.Transform.from_dict(transform)
    return visit(transform, df)
