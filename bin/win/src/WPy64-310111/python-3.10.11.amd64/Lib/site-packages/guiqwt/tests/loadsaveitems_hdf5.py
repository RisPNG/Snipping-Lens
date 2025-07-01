# -*- coding: utf-8 -*-
#
# Copyright © 2012 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Load/save items from/to HDF5 file"""

SHOW = True  # Show test in GUI-based test launcher

# WARNING:
# This script requires read/write permissions on current directory

from guidata.hdf5io import HDF5Reader, HDF5Writer

from guiqwt.tests.loadsaveitems_pickle import IOTest


class HDF5Test(IOTest):
    FNAME = "loadsavecanvas.h5"

    def restore_items(self):
        reader = HDF5Reader(self.FNAME)
        self.plot.deserialize(reader)
        reader.close()

    def save_items(self):
        writer = HDF5Writer(self.FNAME)
        self.plot.serialize(writer)
        writer.close()


if __name__ == "__main__":
    import guidata

    _app = guidata.qapplication()
    test = HDF5Test()
    test.run()
