# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

SHOW = True  # Show test in GUI-based test launcher

"""
Tests for collectionseditor.py
"""

import datetime
import numpy as np

# Local imports
from guidata import qapplication
from guidata.widgets.collectionseditor import CollectionsEditor


def get_test_data():
    """Create test data."""
    import numpy as np
    from PIL import Image

    image = Image.fromarray(np.random.randint(256, size=(100, 100)), mode="P")
    testdict = {"d": 1, "a": np.random.rand(10, 10), "b": [1, 2]}
    testdate = datetime.date(1945, 5, 8)
    test_timedelta = datetime.timedelta(days=-1, minutes=42, seconds=13)

    try:
        import pandas as pd
    except (ModuleNotFoundError, ImportError):
        test_timestamp = None
        test_pd_td = None
        test_dtindex = None
        test_series = None
        test_df = None
    else:
        test_timestamp = pd.Timestamp("1945-05-08T23:01:00.12345")
        test_pd_td = pd.Timedelta(days=2193, hours=12)
        test_dtindex = pd.date_range(start="1939-09-01T", end="1939-10-06", freq="12H")
        test_series = pd.Series({"series_name": [0, 1, 2, 3, 4, 5]})
        test_df = pd.DataFrame(
            {
                "string_col": ["a", "b", "c", "d"],
                "int_col": [0, 1, 2, 3],
                "float_col": [1.1, 2.2, 3.3, 4.4],
                "bool_col": [True, False, False, True],
            }
        )

    class Foobar(object):
        """ """

        def __init__(self):
            self.text = "toto"
            self.testdict = testdict
            self.testdate = testdate

    foobar = Foobar()
    return {
        "object": foobar,
        "module": np,
        "str": "kjkj kj k j j kj k jkj",
        "unicode": "éù",
        "list": [1, 3, [sorted, 5, 6], "kjkj", None],
        "tuple": ([1, testdate, testdict, test_timedelta], "kjkj", None),
        "dict": testdict,
        "float": 1.2233,
        "int": 223,
        "bool": True,
        "array": np.random.rand(10, 10).astype(np.int64),
        "masked_array": np.ma.array(
            [[1, 0], [1, 0]], mask=[[True, False], [False, False]]
        ),
        "1D-array": np.linspace(-10, 10).astype(np.float16),
        "3D-array": np.random.randint(2, size=(5, 5, 5)).astype(np.bool_),
        "empty_array": np.array([]),
        "image": image,
        "date": testdate,
        "datetime": datetime.datetime(1945, 5, 8, 23, 1, 0, int(1.5e5)),
        "timedelta": test_timedelta,
        "complex": 2 + 1j,
        "complex64": np.complex64(2 + 1j),
        "complex128": np.complex128(9j),
        "int8_scalar": np.int8(8),
        "int16_scalar": np.int16(16),
        "int32_scalar": np.int32(32),
        "int64_scalar": np.int64(64),
        "float16_scalar": np.float16(16),
        "float32_scalar": np.float32(32),
        "float64_scalar": np.float64(64),
        "bool_scalar": bool,
        "bool__scalar": np.bool_(8),
        "timestamp": test_timestamp,
        "timedelta_pd": test_pd_td,
        "datetimeindex": test_dtindex,
        "series": test_series,
        "ddataframe": test_df,
        "None": None,
        "unsupported1": np.arccos,
        "unsupported2": np.cast,
        # Test for Issue #3518
        "big_struct_array": np.zeros(
            1000, dtype=[("ID", "f8"), ("param1", "f8", 5000)]
        ),
    }


def test_collectionseditor():
    """Test Collections editor."""
    app = qapplication()

    dialog = CollectionsEditor()
    dialog.setup(get_test_data())
    dialog.show()
    app.exec_()


if __name__ == "__main__":
    test_collectionseditor()
