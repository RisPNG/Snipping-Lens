# -*- coding: utf-8 -*-
#
# This file is part of CodraFT Project
# https://codra-ingenierie-informatique.github.io/CodraFT/
#
# Licensed under the terms of the BSD 3-Clause or the CeCILL-B License
# (see codraft/LICENSE for details)

"""
Reader and Writer for the serialization of DataSets into JSON files
"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

import json
import os
from uuid import uuid1

import numpy as np

from guidata.userconfigio import BaseIOHandler, WriterMixin


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON Encoder"""

    def default(self, o):
        """Override JSONEncoder method"""
        if isinstance(o, np.ndarray):
            return ["array", o.tolist(), str(o.dtype)]
        if isinstance(o, np.generic):
            if isinstance(o, np.integer):
                return int(o)
            try:
                return float(o)
            except ValueError:
                return str(o)
        if isinstance(o, bytes):
            return o.decode()
        return json.JSONEncoder.default(self, o)


class CustomJSONDecoder(json.JSONDecoder):
    """Custom JSON Decoder"""

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def __iterate_dict(self, obj):
        """Iterate dictionaries"""
        if isinstance(obj, list) and len(obj) == 3:
            family, data, dtypestr = obj
            try:
                dtype = np.dtype(dtypestr)
                if family == "array":
                    return np.asarray(data, dtype)
            except TypeError:
                pass
        elif isinstance(obj, dict):
            for key, value in list(obj.items()):
                obj[key] = self.__iterate_dict(value)
        return obj

    def object_hook(self, obj: dict):  # pylint: disable=E0202
        """Object hook"""
        for key, value in list(obj.items()):
            obj[key] = self.__iterate_dict(value)
        return obj


class JSONHandler(BaseIOHandler):
    """Class handling JSON r/w"""

    def __init__(self, filename=None):
        super().__init__()
        self.jsondata = {}
        self.jsontext = None
        self.filename = filename

    def get_parent_group(self):
        """Get parent group"""
        parent = self.jsondata
        for option in self.option[:-1]:
            parent = parent.setdefault(option, {})
        return parent

    def set_json_dict(self, jsondata: dict):
        """Set JSON data dictionary"""
        self.jsondata = jsondata

    def get_json_dict(self) -> dict:
        """Return JSON data dictionary"""
        return self.jsondata

    def get_json(self, indent=None):
        """Get JSON string"""
        if self.jsondata is not None:
            return json.dumps(self.jsondata, indent=indent, cls=CustomJSONEncoder)
        return None

    def load(self):
        """Load JSON file"""
        if self.filename is not None:
            with open(self.filename, mode="rb") as fdesc:
                self.jsontext = fdesc.read().decode()
        self.jsondata = json.loads(self.jsontext, cls=CustomJSONDecoder)

    def save(self, path=None):
        """Save JSON file"""
        if self.filename is not None:
            filepath = self.filename
            if path:
                filepath = os.path.join(path, filepath)
            with open(filepath, mode="wb") as fdesc:
                fdesc.write(self.get_json(indent=4).encode())

    def close(self):
        """Expected close method: do nothing for JSON I/O handler classes"""


class JSONWriter(JSONHandler, WriterMixin):
    """Class handling JSON serialization"""

    def write_any(self, val):
        """Write any value type"""
        group = self.get_parent_group()
        group[self.option[-1]] = val

    def write_none(self):
        """Write None"""
        self.write_any(None)

    write_str = (
        write_sequence
    ) = write_unicode = write_bool = write_int = write_float = write_array = write_any

    def write_object_list(self, seq, group_name):
        """Write object sequence in group.
        Objects must implement the DataSet-like `serialize` method"""
        with self.group(group_name):
            if seq is None:
                self.write_none()
            else:
                ids = []
                for obj in seq:
                    guid = str(uuid1())
                    ids.append(guid)
                    with self.group(guid):
                        if obj is None:
                            self.write_none()
                        else:
                            obj.serialize(self)
                self.write(ids, "IDs")


class JSONReader(JSONHandler):
    """Class handling JSON deserialization"""

    def __init__(self, fname_or_jsontext):
        """JSONReader constructor:
        * fname_or_jsontext: JSON filename or JSON text"""
        JSONHandler.__init__(self, fname_or_jsontext)
        if fname_or_jsontext is not None and not os.path.isfile(fname_or_jsontext):
            self.filename = None
            self.jsontext = fname_or_jsontext
        self.load()

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
            if group_name not in group:
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
        """Read any value type"""
        group = self.get_parent_group()
        return group[self.option[-1]]

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
                return None
            seq = []
            count = len(ids)
            for idx, name in enumerate(ids):
                if progress_callback is not None:
                    if progress_callback(int(100 * float(idx) / count)):
                        break
                with self.group(name):
                    group = self.get_parent_group()
                    if name not in group:
                        # This is an attribute (not a group), meaning that
                        # the object was None when deserializing it
                        obj = None
                    else:
                        obj = klass()
                        obj.deserialize(self)
                seq.append(obj)
        return seq

    read_unicode = (
        read_sequence
    ) = read_float = read_int = read_str = read_bool = read_array = read_any
