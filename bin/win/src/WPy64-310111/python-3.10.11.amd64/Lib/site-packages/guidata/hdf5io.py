# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
Reader and Writer for the serialization of DataSets into HDF5 files
"""

import sys
from uuid import uuid1

import h5py
import numpy as np

from guidata.utils import utf8_to_unicode
from guidata.userconfigio import BaseIOHandler, WriterMixin


class TypeConverter(object):
    def __init__(self, to_type, from_type=None):
        self._to_type = to_type
        if from_type:
            self._from_type = from_type
        else:
            self._from_type = to_type

    def to_hdf(self, value):
        try:
            return self._to_type(value)
        except:
            print("ERR", repr(value), file=sys.stderr)
            raise

    def from_hdf(self, value):
        return self._from_type(value)


unicode_hdf = TypeConverter(lambda x: x.encode("utf-8"), lambda x: str(x, "utf-8"))
int_hdf = TypeConverter(int)


class Attr(object):
    """Helper class representing class attribute that
    should be saved/restored to/from a corresponding HDF5 attribute

    hdf_name : name of the attribute in the HDF5 file
    struct_name : name of the attribute in the object (default to hdf_name)
    type : attribute type (guess it if None)
    optional : indicates whether we should fail if the attribute is not present
    """

    def __init__(self, hdf_name, struct_name=None, type=None, optional=False):
        self.hdf_name = hdf_name
        if struct_name is None:
            struct_name = hdf_name
        self.struct_name = struct_name
        self.type = type
        self.optional = optional

    def get_value(self, struct):
        if self.optional:
            return getattr(struct, self.struct_name, None)
        else:
            return getattr(struct, self.struct_name)

    def set_value(self, struct, value):
        setattr(struct, self.struct_name, value)

    def save(self, group, struct):
        value = self.get_value(struct)
        if self.optional and value is None:
            # print ".-", self.hdf_name, value
            if self.hdf_name in group.attrs:
                del group.attrs[self.hdf_name]
            return
        if self.type is not None:
            value = self.type.to_hdf(value)
        # print ".", self.hdf_name, value, self.optional
        try:
            group.attrs[self.hdf_name] = value
        except:
            print("ERROR saving:", repr(value), "into", self.hdf_name, file=sys.stderr)
            raise

    def load(self, group, struct):
        # print "LoadAttr:", group, self.hdf_name
        if self.optional:
            if self.hdf_name not in group.attrs:
                self.set_value(struct, None)
                return
        try:
            value = group.attrs[self.hdf_name]
        except KeyError:
            raise KeyError("Unable to locate attribute %s" % self.hdf_name)
        if self.type is not None:
            value = self.type.from_hdf(value)
        self.set_value(struct, value)


def createdset(group, name, value):
    group.create_dataset(
        name,
        compression=None,
        # compression_opts=3,
        data=value,
    )


class Dset(Attr):
    """
    Generic load/save for an hdf5 dataset:
    scalar=float -> used to convert the value when it is scalar
    """

    def __init__(
        self, hdf_name, struct_name=None, type=None, scalar=None, optional=False
    ):
        Attr.__init__(self, hdf_name, struct_name, type, optional)
        self.scalar = scalar

    def save(self, group, struct):
        value = self.get_value(struct)
        if isinstance(value, float):
            value = np.float64(value)
        elif isinstance(value, int):
            value = np.int32(value)
        if value is None or value.size == 0:
            value = np.array([0.0])
        if value.shape == ():
            value = value.reshape((1,))
        group.require_dataset(
            self.hdf_name,
            shape=value.shape,
            dtype=value.dtype,
            data=value,
            compression="gzip",
            compression_opts=1,
        )

    def load(self, group, struct):
        if self.optional:
            if self.hdf_name not in group:
                self.set_value(struct, None)
                return
        try:
            value = group[self.hdf_name][...]
        except KeyError:
            raise KeyError("Unable to locate dataset %s" % self.hdf_name)
        if self.scalar is not None:
            value = self.scalar(value)
        self.set_value(struct, value)


class Dlist(Dset):
    def get_value(self, struct):
        return np.array(getattr(struct, self.struct_name))

    def set_value(self, struct, value):
        setattr(struct, self.struct_name, list(value))


# ==============================================================================
# Base HDF5 Store object: do not break API compatibility here as this class is
# used in various critical projects for saving/loading application data
# ==============================================================================
class H5Store(object):
    def __init__(self, filename):
        self.filename = filename
        self.h5 = None

    def open(self, mode="a"):
        """Open an hdf5 file"""
        if self.h5:
            return self.h5
        try:
            self.h5 = h5py.File(self.filename, mode=mode)
        except Exception:
            print(
                "Error trying to load:",
                self.filename,
                "in mode:",
                mode,
                file=sys.stderr,
            )
            raise
        return self.h5

    def close(self):
        if self.h5:
            self.h5.close()
        self.h5 = None

    def generic_save(self, parent, source, structure):
        """save the data from source into the file using 'structure'
        as a descriptor.

        structure is a list of Attribute Descriptor (Attr, Dset, Dlist or anything
        with a save interface) that describe the conversion of data and the name
        of the attribute in the source and in the file
        """
        for instr in structure:
            instr.save(parent, source)

    def generic_load(self, parent, dest, structure):
        """load the data from the file into dest using 'structure'
        as a descriptor.

        structure is the same as in generic_save
        """
        for instr in structure:
            try:
                instr.load(parent, dest)
            except Exception:
                print("Error loading HDF5 item:", instr.hdf_name, file=sys.stderr)
                raise


# ==============================================================================
# HDF5 reader/writer: do not break API compatibility here as this class is
# used in various critical projects for saving/loading application data and
# in guiqwt for saving/loading plot items.
# ==============================================================================
class HDF5Handler(H5Store, BaseIOHandler):
    """Base HDF5 I/O Handler object"""

    def __init__(self, filename):
        H5Store.__init__(self, filename)
        self.option = []

    def get_parent_group(self):
        parent = self.h5
        for option in self.option[:-1]:
            parent = parent.require_group(option)
        return parent


class HDF5Writer(HDF5Handler, WriterMixin):
    """Writer for HDF5 files"""

    def __init__(self, filename):
        super(HDF5Writer, self).__init__(filename)
        self.open("w")

    def write_any(self, val):
        group = self.get_parent_group()
        group.attrs[self.option[-1]] = val

    write_int = write_float = write_any

    def write_bool(self, val):
        self.write_int(int(val))

    write_str = write_any

    def write_unicode(self, val):
        group = self.get_parent_group()
        group.attrs[self.option[-1]] = val.encode("utf-8")

    write_unicode = write_str

    def write_array(self, val):
        group = self.get_parent_group()
        group[self.option[-1]] = val

    write_sequence = write_any

    def write_none(self):
        group = self.get_parent_group()
        group.attrs[self.option[-1]] = ""

    def write_object_list(self, seq, group_name):
        """Write object sequence in group.
        Objects must implement the DataSet-like `serialize` method"""
        with self.group(group_name):
            if seq is None:
                self.write_none()
            else:
                ids = []
                for obj in seq:
                    guid = bytes(str(uuid1()), "utf-8")
                    ids.append(guid)
                    with self.group(guid):
                        if obj is None:
                            self.write_none()
                        else:
                            obj.serialize(self)
                self.write(ids, "IDs")


class HDF5Reader(HDF5Handler):
    """Reader for HDF5 files"""

    def __init__(self, filename):
        super(HDF5Reader, self).__init__(filename)
        self.open("r")

    def read(self, group_name=None, func=None, instance=None):
        """Read value within current group or group_name.

        Optional argument `instance` is an object which
        implements the DataSet-like `deserialize` method."""
        if group_name:
            self.begin(group_name)
        if instance is None:
            if func is None:
                func = self.read_any
            val = func()
        else:
            group = self.get_parent_group()
            if group_name in group.attrs:
                # This is an attribute (not a group), meaning that
                # the object was None when deserializing it
                val = None
            else:
                instance.deserialize(self)
                val = instance
        if group_name:
            self.end(group_name)
        return val

    def read_any(self):
        group = self.get_parent_group()
        value = group.attrs[self.option[-1]]
        if isinstance(value, bytes):
            return value.decode("utf-8")
        else:
            return value

    def read_bool(self):
        val = self.read_any()
        if val != "":
            return bool(val)

    def read_int(self):
        val = self.read_any()
        if val != "":
            return int(val)

    def read_float(self):
        val = self.read_any()
        if val != "":
            return float(val)

    read_unicode = read_str = read_any

    def read_array(self):
        group = self.get_parent_group()
        return group[self.option[-1]][...]

    def read_sequence(self):
        group = self.get_parent_group()
        return list(group.attrs[self.option[-1]])

    def read_object_list(self, group_name, klass, progress_callback=None):
        """Read object sequence in group.
        Objects must implement the DataSet-like `deserialize` method.
        `klass` is the object class which constructor requires no argument.

        progress_callback: if not None, this function is called with
        an integer argument (progress: 0 --> 100). Function returns the
        `cancel` state (True: progress dialog has been canceled, False
        otherwise)
        """
        with self.group(group_name):
            try:
                ids = self.read("IDs", func=self.read_sequence)
            except ValueError:
                # None was saved instead of list of objects
                self.end("IDs")
                return
            seq = []
            count = len(ids)
            for idx, name in enumerate(ids):
                if progress_callback is not None:
                    if progress_callback(int(100 * float(idx) / count)):
                        break
                with self.group(name):
                    group = self.get_parent_group()
                    if name in group.attrs:
                        # This is an attribute (not a group), meaning that
                        # the object was None when deserializing it
                        obj = None
                    else:
                        obj = klass()
                        obj.deserialize(self)
                seq.append(obj)
        return seq

    read_none = read_any
