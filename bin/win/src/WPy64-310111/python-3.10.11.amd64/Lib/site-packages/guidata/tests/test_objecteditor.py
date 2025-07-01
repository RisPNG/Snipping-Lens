# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
"""
Tests for objecteditor.py
"""

import datetime

import numpy as np
import PIL.Image
from guidata import qapplication
from guidata.widgets.objecteditor import oedit

SHOW = True  # Show test in GUI-based test launcher


def test():
    """Run object editor test"""
    data = np.random.randint(255, size=(100, 100)).astype("uint8")
    image = PIL.Image.fromarray(data)
    example = {
        "str": "kjkj kj k j j kj k jkj",
        "list": [1, 3, 4, "kjkj", None],
        "dict": {"d": 1, "a": np.random.rand(10, 10), "b": [1, 2]},
        "float": 1.2233,
        "array": np.random.rand(10, 10),
        "image": image,
        "date": datetime.date(1945, 5, 8),
        "datetime": datetime.datetime(1945, 5, 8),
    }
    image = oedit(image)

    class Foobar(object):
        """ """

        def __init__(self):
            self.text = "toto"

    foobar = Foobar()
    print(oedit(foobar))
    print(oedit(example))
    print(oedit(np.random.rand(10, 10)))
    print(oedit(oedit.__doc__))
    print(example)


if __name__ == "__main__":
    from guidata import qapplication

    app = qapplication()
    test()
