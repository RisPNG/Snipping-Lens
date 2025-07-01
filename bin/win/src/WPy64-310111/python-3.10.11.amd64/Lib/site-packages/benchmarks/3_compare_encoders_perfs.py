"""
Benchmarks the time it takes each encoder to transform each dataset,
with different hyperparameters.
It does not benchmark the actual performances with a learner,
but only the transformations.
"""

import sklearn
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from git import Repo
from pathlib import Path
from pprint import pprint
from datetime import datetime
from time import perf_counter
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
from concurrent.futures import ProcessPoolExecutor

from dirty_cat import (
    SimilarityEncoder,
    GapEncoder,
    MinHashEncoder,
    SuperVectorizer,
)
from dirty_cat.datasets import (
    fetch_employee_salaries,
    fetch_traffic_violations,
    fetch_road_safety,
    fetch_midwest_survey,
    fetch_medical_charge,
    fetch_drug_directory,
    fetch_open_payments,
)
from dirty_cat.datasets.fetching import DatasetInfoOnly


@dataclass(unsafe_hash=True)
class Transformer:
    cls: sklearn.base.TransformerMixin
    hyperparameters: Dict[str, Any]


@dataclass(unsafe_hash=True)
class Input:
    dataset: DatasetInfoOnly
    transformer: Transformer


@dataclass(unsafe_hash=True)
class Result:
    transformer_name: str
    dataset_name: str
    hyperparameters: Dict[str, Any]
    run_duration: float


def bench(inp: Input) -> ...:
    X = (
        pd.read_csv(inp.dataset.path, **inp.dataset.read_csv_kwargs)
        .drop(inp.dataset.target, axis=1)
    )

    start = perf_counter()
    sv = SuperVectorizer(
        cardinality_threshold=3,
        low_card_cat_transformer='drop',
        high_card_cat_transformer=inp.transformer.cls(**inp.transformer.hyperparameters),
        numerical_transformer='drop',
        datetime_transformer='drop',
        auto_cast=False,
    )
    sv.fit_transform(X)

    end = perf_counter()

    return Result(
        transformer_name=inp.transformer.cls.__name__,
        dataset_name=inp.dataset.name,
        hyperparameters=inp.transformer.hyperparameters,
        run_duration=end - start,
    )


def results_to_dataframe(res: List[Result]) -> pd.DataFrame:
    return pd.DataFrame(
        [vars(r).values() for r in res],
        columns=Result.__annotations__.keys(),
    )


transformers = [
    Transformer(cls=SimilarityEncoder, hyperparameters={'dtype': np.float16}),
    Transformer(cls=GapEncoder, hyperparameters={}),
    Transformer(cls=MinHashEncoder, hyperparameters={}),
]

datasets = [
    fetch_employee_salaries(load_dataframe=False),
    fetch_traffic_violations(load_dataframe=False),
    fetch_road_safety(load_dataframe=False),
    fetch_midwest_survey(load_dataframe=False),
    fetch_medical_charge(load_dataframe=False),
    fetch_drug_directory(load_dataframe=False),
    fetch_open_payments(load_dataframe=False),
]

transformer_to_rgb: Dict[str, Tuple[int, int, int]] = {
    SimilarityEncoder.__name__: (0, 100, 80),
    GapEncoder.__name__: (0, 176, 246),
    MinHashEncoder.__name__: (231, 107, 243),
}


if __name__ == "__main__":
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(
            bench,
            [
                Input(
                    dataset=dataset,
                    transformer=transformer,
                )
                for dataset in datasets
                for transformer in transformers
            ],
        ))

    fig = go.Figure()

    df = results_to_dataframe(results)
    dataset_names = [ds.name for ds in datasets]

    dfs: Dict[str, pd.DataFrame] = {}
    for trans in transformers:
        trans_name = trans.cls.__name__
        sub_df = df[df['transformer_name'] == trans_name]
        data: List[Tuple[str, float, float, float]] = []
        for ds_name in dataset_names:
            run = sub_df[sub_df['dataset_name'] == ds_name]['run_duration']
            data.append((
                ds_name,
                run.min(),
                run.max(),
                run.mean(),
            ))
            pass
        dfs.update({
            trans_name: pd.DataFrame(data, columns=['Dataset', 'min', 'max', 'mean'])
        })

    for trans_name, df in dfs.items():
        trans_rgb = transformer_to_rgb[trans_name]
        fig.add_trace(go.Scatter(
            x=dataset_names,
            y=df['max'] + df['min'][::-1],
            fill='toself',
            fillcolor=f'rgba({",".join(map(str, trans_rgb))},0.2)',
            line_color='rgba(255,255,255,0)',
            showlegend=False,
            name=trans_name,
        ))
        fig.add_trace(go.Scatter(
            x=dataset_names,
            y=df['mean'],
            line_color=f'rgb({",".join(map(str, trans_rgb))})',
            name=trans_name,
        ))

    pprint(results)

    now = datetime.now()
    current_dir = Path(__file__).parent
    commit = Repo(current_dir.parent).active_branch.commit
    file_name = f'3_{now.year}-{now.month}-{now.day}_{commit}.html'
    fig.write_html(current_dir / 'results' / file_name)
