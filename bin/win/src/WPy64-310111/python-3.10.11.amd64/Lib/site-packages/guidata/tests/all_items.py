# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
All guidata DataItem objects demo

A DataSet object is a set of parameters of various types (integer, float,
boolean, string, etc.) which may be edited in a dialog box thanks to the
'edit' method. Parameters are defined by assigning DataItem objects to a
DataSet class definition: each parameter type has its own DataItem class
(IntItem for integers, FloatItem for floats, StringItem for strings, etc.)
"""


SHOW = True  # Show test in GUI-based test launcher

import tempfile, atexit, shutil, datetime, numpy as np

import guidata.dataset.datatypes as gdt
import guidata.dataset.dataitems as gdi


# Creating temporary files and registering cleanup functions
TEMPDIR = tempfile.mkdtemp(prefix="test_")
atexit.register(shutil.rmtree, TEMPDIR)
FILE_ETA = tempfile.NamedTemporaryFile(suffix=".eta", dir=TEMPDIR)
atexit.register(FILE_ETA.close)
FILE_CSV = tempfile.NamedTemporaryFile(suffix=".csv", dir=TEMPDIR)
atexit.register(FILE_CSV.close)


class TestParameters(gdt.DataSet):
    """
    DataSet test
    The following text is the DataSet 'comment': <br>Plain text or
    <b>rich text<sup>2</sup></b> are both supported,
    as well as special characters (α, β, γ, δ, ...)
    """

    dir = gdi.DirectoryItem("Directory", TEMPDIR)
    fname = gdi.FileOpenItem("Open file", ("csv", "eta"), FILE_CSV.name)
    fnames = gdi.FilesOpenItem("Open files", "csv", FILE_CSV.name)
    fname_s = gdi.FileSaveItem("Save file", "eta", FILE_ETA.name)
    string = gdi.StringItem("String")
    text = gdi.TextItem("Text")
    float_slider = gdi.FloatItem(
        "Float (with slider)", default=0.5, min=0, max=1, step=0.01, slider=True
    )
    integer = gdi.IntItem("Integer", default=5, min=3, max=16, slider=True).set_pos(
        col=1
    )
    dtime = gdi.DateTimeItem("Date/time", default=datetime.datetime(2010, 10, 10))
    date = gdi.DateItem("Date", default=datetime.date(2010, 10, 10)).set_pos(col=1)
    bool1 = gdi.BoolItem("Boolean option without label")
    bool2 = gdi.BoolItem("Boolean option with label", "Label")
    _bg = gdt.BeginGroup("A sub group")
    color = gdi.ColorItem("Color", default="red")
    choice = gdi.ChoiceItem(
        "Single choice 1",
        [("16", "first choice"), ("32", "second choice"), ("64", "third choice")],
    )
    mchoice2 = gdi.ImageChoiceItem(
        "Single choice 2",
        [
            ("rect", "first choice", "gif.png"),
            ("ell", "second choice", "txt.png"),
            ("qcq", "third choice", "file.png"),
        ],
    )
    _eg = gdt.EndGroup("A sub group")
    floatarray = gdi.FloatArrayItem(
        "Float array", default=np.ones((50, 5), float), format=" %.2e "
    ).set_pos(col=1)
    mchoice3 = gdi.MultipleChoiceItem(
        "MC type 1", [str(i) for i in range(12)]
    ).horizontal(4)
    mchoice1 = (
        gdi.MultipleChoiceItem(
            "MC type 2", ["first choice", "second choice", "third choice"]
        )
        .vertical(1)
        .set_pos(col=1)
    )


if __name__ == "__main__":
    # Create QApplication
    import guidata

    _app = guidata.qapplication()

    e = TestParameters()
    e.floatarray[:, 0] = np.linspace(-5, 5, 50)
    print(e)
    if e.edit():
        print(e)
    e.view()
