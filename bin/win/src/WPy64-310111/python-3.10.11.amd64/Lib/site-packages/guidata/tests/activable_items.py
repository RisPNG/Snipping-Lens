# -*- coding: utf-8 -*-
#
# Copyright © 2012 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
Example with activable items: items which active state is changed depending 
on another item's value.
"""

SHOW = True  # Show test in GUI-based test launcher

from guidata.dataset.dataitems import ChoiceItem, FloatItem
from guidata.dataset.datatypes import DataSet, GetAttrProp, FuncProp

choices = (("A", "Choice #1: A"), ("B", "Choice #2: B"), ("C", "Choice #3: C"))


class Test(DataSet):
    _prop = GetAttrProp("choice")
    choice = ChoiceItem("Choice", choices).set_prop("display", store=_prop)
    x1 = FloatItem("x1")
    x2 = FloatItem("x2").set_prop("display", active=FuncProp(_prop, lambda x: x == "B"))
    x3 = FloatItem("x3").set_prop("display", active=FuncProp(_prop, lambda x: x == "C"))


if __name__ == "__main__":
    # Create QApplication
    import guidata

    _app = guidata.qapplication()

    test = Test()
    test.edit()
