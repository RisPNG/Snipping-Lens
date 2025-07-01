# -*- coding: utf-8 -*-
#
# This file is part of CodraFT Project
# https://codra-ingenierie-informatique.github.io/CodraFT/
#
# Licensed under the terms of the BSD 3-Clause or the CeCILL-B License
# (see codraft/__init__.py for details)

"""
Unit test for plot items <--> JSON serialization/deserialization

How to save/restore items to/from a JSON string?

    # Plot items --> JSON:
    writer = JSONWriter(None)
    save_items(writer, items)
    text = writer.get_json()

    # JSON --> Plot items:
    items = load_items(JSONReader(text))

"""

import os.path as osp

from guiqwt.tests.loadsaveitems_pickle import IOTest

from guidata.jsonio import JSONReader, JSONWriter

SHOW = True  # Show test in GUI-based test launcher


class JSONTest(IOTest):
    """Class for JSON I/O testing"""

    FNAME = osp.join(osp.dirname(__file__), "loadsavecanvas.json")

    def restore_items(self):
        """Restore plot items"""
        self.plot.deserialize(JSONReader(self.FNAME))

    def save_items(self):
        """Save plot items"""
        writer = JSONWriter(self.FNAME)
        self.plot.serialize(writer)
        writer.save()


if __name__ == "__main__":
    import guidata

    _app = guidata.qapplication()
    test = JSONTest()
    test.run()
