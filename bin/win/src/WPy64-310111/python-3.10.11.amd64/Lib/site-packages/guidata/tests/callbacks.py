# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
Demonstrates how items may trigger callbacks when activated
"""


SHOW = True  # Show test in GUI-based test launcher


from guidata.dataset.datatypes import DataSet
from guidata.dataset.dataitems import (
    ChoiceItem,
    StringItem,
    TextItem,
    ColorItem,
    FloatItem,
)


class TestParameters(DataSet):
    def cb_example(self, item, value):
        print("\nitem: ", item, "\nvalue:", value)
        if self.results is None:
            self.results = ""
        self.results += str(value) + "\n"
        print("results:", self.results)

    def update_x1plusx2(self, item, value):
        print("\nitem: ", item, "\nvalue:", value)
        if self.x1 is not None and self.x2 is not None:
            self.x1plusx2 = self.x1 + self.x2
        else:
            self.x1plusx2 = None

    string = StringItem("String", default="foobar").set_prop(
        "display", callback=cb_example
    )
    x1 = FloatItem("x1").set_prop("display", callback=update_x1plusx2)
    x2 = FloatItem("x2").set_prop("display", callback=update_x1plusx2)
    x1plusx2 = FloatItem("x1+x2").set_prop("display", active=False)
    color = ColorItem("Color", default="red").set_prop("display", callback=cb_example)
    choice = (
        ChoiceItem(
            "Single choice",
            [(16, "first choice"), (32, "second choice"), (64, "third choice")],
            default=64,
        )
        .set_pos(col=1, colspan=2)
        .set_prop("display", callback=cb_example)
    )
    results = TextItem("Results")


if __name__ == "__main__":
    # Create QApplication
    import guidata

    _app = guidata.qapplication()

    e = TestParameters()
    print(e)
    if e.edit():
        print(e)
    e.view()
