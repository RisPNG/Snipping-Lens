# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

SHOW = True  # Show test in GUI-based test launcher

"""
Tests for dataframeeditor.py
"""

import numpy as np
from numpy import nan
from pandas import DataFrame, Series
from pandas.testing import assert_frame_equal, assert_series_equal

# Local imports
from guidata import qapplication
from guidata.widgets.dataframeeditor import DataFrameEditor


def test_edit(data, title="", parent=None):
    """Test subroutine"""
    dlg = DataFrameEditor(parent=parent)

    if dlg.setup_and_check(data, title=title):
        dlg.exec_()
        return dlg.get_value()
    else:
        import sys

        sys.exit(1)


def test_dataframeeditor():
    """DataFrame editor test"""
    app = qapplication()  # analysis:ignore

    df1 = DataFrame(
        [
            [True, "bool"],
            [1 + 1j, "complex"],
            ["test", "string"],
            [1.11, "float"],
            [1, "int"],
            [np.random.rand(3, 3), "Unkown type"],
            ["Large value", 100],
            ["áéí", "unicode"],
        ],
        index=["a", "b", nan, nan, nan, "c", "Test global max", "d"],
        columns=[nan, "Type"],
    )
    out = test_edit(df1)
    assert_frame_equal(df1, out)

    result = Series([True, "bool"], index=[nan, "Type"], name="a")
    out = test_edit(df1.iloc[0])
    assert_series_equal(result, out)

    df1 = DataFrame(np.random.rand(100100, 10))
    out = test_edit(df1)
    assert_frame_equal(out, df1)

    series = Series(np.arange(10), name=0)
    out = test_edit(series)
    assert_series_equal(series, out)


if __name__ == "__main__":
    test_dataframeeditor()
