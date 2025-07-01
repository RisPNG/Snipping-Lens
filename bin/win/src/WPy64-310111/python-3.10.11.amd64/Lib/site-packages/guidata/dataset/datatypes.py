# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guidata/__init__.py for details)

"""
dataset.datatypes
=================

The ``guidata.dataset.datatypes`` module contains implementation for
DataSets (DataSet, DataSetGroup, ...) and related objects (ItemProperty,
ValueProp, ...).
"""

# pylint: disable-msg=W0622
# pylint: disable-msg=W0212

import sys
import re
import collections.abc

from guidata.utils import utf8_to_unicode, update_dataset


DEBUG_DESERIALIZE = False


class NoDefault:
    pass


class ItemProperty(object):
    def __init__(self, callable=None):
        self.callable = callable

    def __call__(self, instance, item, value):
        """Evaluate the value of the property given, the instance,
        the item and the value maintained in the instance by the item"""
        return self.callable(instance, item, value)

    def set(self, instance, item, value):
        """Sets the value of the property given an instance, item and value
        Depending on implementation the value will be stored either on the
        instance, item or self
        """
        raise NotImplementedError


FMT_GROUPS = re.compile(r"(?<!%)%\((\w+)\)")


class FormatProp(ItemProperty):
    """A Property that returns a string to help
    custom read-only representation of items"""

    def __init__(self, fmt, ignore_error=True):
        """fmt is a format string
        it can contain a single anonymous substition or
        several named substitions.
        """
        self.fmt = fmt
        self.ignore_error = ignore_error
        self.attrs = FMT_GROUPS.findall(fmt)

    def __call__(self, instance, item, value):
        if not self.attrs:
            return self.fmt % value
        dic = {}
        for attr in self.attrs:
            dic[attr] = getattr(instance, attr)
        try:
            return self.fmt % dic
        except TypeError:
            if not self.ignore_error:
                print("Wrong Format for %s : %r %% %r" % (item._name, self.fmt, dic))
                raise


class GetAttrProp(ItemProperty):
    """A property that matches the value of
    an instance's attribute"""

    def __init__(self, attr):
        self.attr = attr

    def __call__(self, instance, item, value):
        val = getattr(instance, self.attr)
        return val

    def set(self, instance, item, value):
        setattr(instance, self.attr, value)


class ValueProp(ItemProperty):
    """A property that retrieves a value stored elsewhere"""

    def __init__(self, value):
        self.value = value

    def __call__(self, instance, item, value):
        return self.value

    def set(self, instance, item, value):
        self.value = value


class NotProp(ItemProperty):
    """Not property"""

    def __init__(self, prop):
        self.property = prop

    def __call__(self, instance, item, value):
        return not self.property(instance, item, value)

    def set(self, instance, item, value):
        self.property.set(instance, item, not value)


class FuncProp(ItemProperty):
    """An 'operator property'
    prop: ItemProperty instance
    func: function
    invfunc: inverse function (optional)
    """

    def __init__(self, prop, func, invfunc=None):
        self.property = prop
        self.function = func
        if invfunc is None:
            invfunc = func
        self.inverse_function = invfunc

    def __call__(self, instance, item, value):
        return self.function(self.property(instance, item, value))

    def set(self, instance, item, value):
        self.property.set(instance, item, self.inverse_function(value))


class DataItem(object):
    """
    DataSet data item

    `label` : string
    `default` : any type, optional
    `help` : string Text displayed on data item's tooltip
    """

    count = 0

    def __init__(self, label, default=None, help="", check=True):
        self._order = DataItem.count
        DataItem.count += 1
        self._name = None
        self._default = default
        self._help = utf8_to_unicode(help)
        self._props = {}  # a dict realm->dict containing realm-specific properties
        self.set_prop(
            "display", col=0, colspan=None, row=None, label=utf8_to_unicode(label)
        )
        self.set_prop("data", check_value=check)

    def get_prop(self, realm, name, default=NoDefault):
        """Get one property of this item"""
        prop = self._props.get(realm)
        if not prop:
            prop = {}
        if default is NoDefault:
            return prop[name]
        return prop.get(name, default)

    def get_prop_value(self, realm, instance, name, default=NoDefault):
        value = self.get_prop(realm, name, default)
        if isinstance(value, ItemProperty):
            return value(instance, self, self.get_value(instance))
        else:
            return value

    def set_prop(self, realm, **kwargs):
        """Set one or several properties using
        the syntax set_prop(name1=value1, ..., nameX=valueX)

        it returns self so that we can assign to the result like this:

        item = Item().set_prop(x=y)
        """
        prop = self._props.get(realm)
        if not prop:
            prop = {}
            self._props[realm] = prop
        prop.update(kwargs)
        return self

    def set_pos(self, col=0, colspan=None, row=None):
        """
        Set data item's position on a GUI layout
        """
        self.set_prop("display", col=col, colspan=colspan, row=row)
        return self

    def __str__(self):
        return self._name + ": " + self.__class__.__name__

    def get_help(self, instance):
        """
        Return data item's tooltip
        """
        auto_help = utf8_to_unicode(self.get_auto_help(instance))
        help = self._help
        if auto_help:
            if help:
                help = help + "\n(" + auto_help + ")"
            else:
                help = auto_help.capitalize()
        return help

    def get_auto_help(self, instance):
        """
        Return the automatically generated part of data item's tooltip
        """
        return ""

    def format_string(self, instance, value, fmt, func):
        """Apply format to string representation of the item's value"""
        return fmt % (func(value),)

    def get_string_value(self, instance):
        """
        Return a formatted unicode representation of the item's value
        obeying 'display' or 'repr' properties
        """
        value = self.get_value(instance)
        repval = self.get_prop_value("display", instance, "repr", None)
        if repval is not None:
            return repval
        else:
            fmt = self.get_prop_value("display", instance, "format", "%s")
            func = self.get_prop_value("display", instance, "func", lambda x: x)
            if isinstance(fmt, collections.abc.Callable) and value is not None:
                return fmt(func(value))
            if value is not None:
                text = self.format_string(instance, value, fmt, func)
            else:
                text = ""
            return text

    def set_name(self, new_name):
        """
        Set data item's name
        """
        self._name = new_name

    def set_help(self, new_help):
        """
        Set data item's help text
        """
        self._help = new_help

    def set_from_string(self, instance, string_value):
        """
        Set data item's value from specified string
        """
        value = self.from_string(string_value)
        self.__set__(instance, value)

    def set_default(self, instance):
        """
        Set data item's value to default
        """
        self.__set__(instance, self._default)

    def accept(self, visitor):
        """
        This is the visitor pattern's accept function.
        It calls the corresponding visit_MYCLASS method
        of the visitor object.

        Python's allow a generic base class implementation of
        this method so there's no need to write an accept function
        for each derived class unless you need to override the
        default behavior
        """
        funcname = "visit_" + self.__class__.__name__
        func = getattr(visitor, funcname)
        func(self)

    def __set__(self, instance, value):
        setattr(instance, "_" + self._name, value)

    def __get__(self, instance, klass):
        if instance is not None:
            return getattr(instance, "_" + self._name, self._default)
        else:
            return self

    def get_value(self, instance):
        """
        Return data item's value
        """
        return self.__get__(instance, instance.__class__)

    def check_item(self, instance):
        """
        Check data item's current value (calling method check_value)
        """
        value = getattr(instance, "_" + self._name)
        return self.check_value(value)

    def check_value(self, instance, value):
        """
        Check if `value` is valid for this data item
        """
        raise NotImplementedError()

    def from_string(self, instance, string_value):
        """
        Transform string into valid data item's value
        """
        raise NotImplementedError()

    def bind(self, instance):
        """
        Return a DataItemVariable instance bound to the data item
        """
        return DataItemVariable(self, instance)

    def serialize(self, instance, writer):
        """Serialize this item using the writer object

        this is a default implementation that should work for
        everything but new datatypes
        """
        value = self.get_value(instance)
        writer.write(value)

    def get_value_from_reader(self, reader):
        """Reads value from the reader object, inside the try...except
        statement defined in the base item `deserialize` method

        This method is reimplemented in some child classes"""
        return reader.read_any()

    def deserialize(self, instance, reader):
        """Deserialize this item using the reader object

        Default base implementation supposes the reader can
        detect expected datatype from the stream
        """
        try:
            value = self.get_value_from_reader(reader)
        except RuntimeError as e:
            if DEBUG_DESERIALIZE:
                import traceback

                print("DEBUG_DESERIALIZE enabled in datatypes.py", file=sys.stderr)
                traceback.print_stack()
                print(e, file=sys.stderr)
            self.set_default(instance)
            return
        self.__set__(instance, value)


class Obj(object):
    """An object that helps build default instances for
    ObjectItems"""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class ObjectItem(DataItem):
    """Simple helper class implementing default
    for composite objects"""

    klass = None

    def set_default(self, instance):
        """Make a copy of the default value"""
        value = self.klass()
        if self._default is not None:
            update_dataset(value, self._default)
        self.__set__(instance, value)

    def deserialize(self, instance, reader):
        """Deserialize this item using the reader object

        We build a new default object and deserialize it
        """
        value = self.klass()
        value.deserialize(reader)
        self.__set__(instance, value)


class DataItemProxy(object):
    """
    Proxy for DataItem objects

    This class is needed to construct GroupItem class
    (see module guidata.qtwidgets)
    """

    def __init__(self, item):
        self.item = item

    def __str__(self):
        return self.item._name + "_proxy: " + self.__class__.__name__

    def get_help(self, instance):
        """DataItem method proxy"""
        return self.item.get_help(instance)

    def get_auto_help(self, instance):
        """DataItem method proxy"""
        return self.item.get_auto_help(instance)

    def get_string_value(self, instance):
        """DataItem method proxy"""
        return self.item.get_string_value(instance)

    def set_from_string(self, instance, string_value):
        """DataItem method proxy"""
        return self.item.set_from_string(instance, string_value)

    def set_default(self, instance):
        """DataItem method proxy"""
        return self.item.set_default(instance)

    def accept(self, visitor):
        """DataItem method proxy"""
        return self.item.accept(visitor)

    def get_value(self, instance):
        """DataItem method proxy"""
        return self.item.get_value(instance)

    def check_item(self, instance):
        """DataItem method proxy"""
        return self.item.check_item(instance)

    def check_value(self, instance, value):
        """DataItem method proxy"""
        return self.item.check_value(instance, value)

    def from_string(self, instance, string_value):
        """DataItem method proxy"""
        return self.item.from_string(instance, string_value)

    def get_prop(self, realm, name, default=NoDefault):
        """DataItem method proxy"""
        return self.item.get_prop(realm, name, default)

    def get_prop_value(self, realm, instance, name, default=NoDefault):
        """DataItem method proxy"""
        return self.item.get_prop_value(realm, instance, name, default)

    def set_prop(self, realm, **kwargs):
        """DataItem method proxy"""
        return self.item.set_prop(realm, **kwargs)

    def bind(self, instance):
        """DataItem method proxy"""
        return DataItemVariable(self, instance)


#    def __getattr__(self, name):
#        assert name in ["min_equals_max", "get_min", "get_max",
#                        "_formats", "_text", "_choices", "_shape",
#                        "_format", "_label", "_xy"]
#        val = getattr(self.item, name)
#        if callable(val):
#            return bind(val, self.instance)
#        else:
#            return val


class DataItemVariable(object):
    """An instance of a DataItemVariable represent a binding between
    an item and a dataset.

    could be called a bound property.

    since DataItem instances are class attributes they need to have a
    DataSet instance to store their value. This class binds the two
    together.
    """

    def __init__(self, item, instance):
        self.item = item
        self.instance = instance

    def get_prop_value(self, realm, name, default=NoDefault):
        """DataItem method proxy"""
        return self.item.get_prop_value(realm, self.instance, name, default)

    def get_prop(self, realm, name, default=NoDefault):
        """DataItem method proxy"""
        return self.item.get_prop(realm, name, default)

    #    def set_prop(self, realm, **kwargs):
    #        """DataItem method proxy"""
    #        self.item.set_prop(realm, **kwargs)
    #
    #    def __getattr__(self, name):
    #        assert name in ["min_equals_max", "get_min", "get_max",
    #                        "_formats","_text", "_choices", "_shape",
    #                        "_format", "_label", "_xy"]
    #        val = getattr(self.item, name)
    #        if callable(val):
    #            return bind(val, self.instance)
    #        else:
    #            return val
    def get_help(self):
        """Re-implement DataItem method"""
        return self.item.get_help(self.instance)

    def get_auto_help(self):
        """Re-implement DataItem method"""
        # XXX incohérent ?
        return self.item.get_auto_help(self.instance)

    def get_string_value(self):
        """
        Return a unicode representation of the item's value
        obeying 'display' or 'repr' properties
        """
        return self.item.get_string_value(self.instance)

    def set_default(self):
        """Re-implement DataItem method"""
        return self.item.set_default(self.instance)

    def get(self):
        """Re-implement DataItem method"""
        return self.item.get_value(self.instance)

    def set(self, value):
        """Re-implement DataItem method"""
        return self.item.__set__(self.instance, value)

    def set_from_string(self, string_value):
        """Re-implement DataItem method"""
        return self.item.set_from_string(self.instance, string_value)

    def check_item(self):
        """Re-implement DataItem method"""
        return self.item.check_item(self.instance)

    def check_value(self, value):
        """Re-implement DataItem method"""
        return self.item.check_value(value)

    def from_string(self, string_value):
        """Re-implement DataItem method"""
        return self.item.from_string(string_value)

    def label(self):
        """Re-implement DataItem method"""
        return self.item.get_prop("display", "label")


class DataSetMeta(type):
    """
    DataSet metaclass

    Create class attribute `_items`: list of the DataSet class attributes,
    created in the same order as these attributes were written
    """

    def __new__(cls, name, bases, dct):
        items = {}
        for base in bases:
            if getattr(base, "__metaclass__", None) is DataSetMeta:
                for item in base._items:
                    items[item._name] = item

        for attrname, value in list(dct.items()):
            if isinstance(value, DataItem):
                value.set_name(attrname)
                if attrname in items:
                    value._order = items[attrname]._order
                items[attrname] = value
        items_list = list(items.values())
        items_list.sort(key=lambda x: x._order)
        dct["_items"] = items_list
        return type.__new__(cls, name, bases, dct)


Meta_Py3Compat = DataSetMeta("Meta_Py3Compat", (object,), {})


class DataSet(Meta_Py3Compat):
    """
    Construct a DataSet object is a set of DataItem objects
        * title [string]
        * comment [string]: text shown on the top of the first data item
        * icon [QIcon or string]: icon show on the button (optional)
          (string: icon filename as in guidata/guiqwt image search paths)
    """

    __metaclass__ = DataSetMeta  # keep it even with Python 3 (see DataSetMeta)

    def __init__(self, title=None, comment=None, icon=""):
        self.__title = title
        self.__comment = comment
        self.__icon = icon
        comp_title, comp_comment = self._compute_title_and_comment()
        if title is None:
            self.__title = comp_title
        if comment is None:
            self.__comment = comp_comment
        self.__changed = False
        # Set default values
        self.set_defaults()

    def _get_translation(self):
        """We try to find the translation function (_) from the module
        this class was created in

        This function is unused but could be useful to translate strings that
        cannot be translated at the time they are created.
        """
        module = sys.modules[self.__class__.__module__]
        if hasattr(module, "_"):
            return module._
        else:
            return lambda x: x

    def _compute_title_and_comment(self):
        """
        Private method to compute title and comment of the data set
        """
        comp_title = self.__class__.__name__
        comp_comment = None
        if self.__doc__:
            doc_lines = utf8_to_unicode(self.__doc__).splitlines()
            # Remove empty lines at the begining of comment
            while doc_lines and not doc_lines[0].strip():
                del doc_lines[0]
            if doc_lines:
                comp_title = doc_lines.pop(0).strip()
            if doc_lines:
                comp_comment = "\n".join([x.strip() for x in doc_lines])
        return comp_title, comp_comment

    def get_title(self):
        """
        Return data set title
        """
        return self.__title

    def get_comment(self):
        """
        Return data set comment
        """
        return self.__comment

    def get_icon(self):
        """
        Return data set icon
        """
        return self.__icon

    def set_defaults(self):
        """Set default values"""
        for item in self._items:
            item.set_default(self)

    def __str__(self):
        return self.to_string(debug=False)

    def check(self):
        """
        Check the dataset item values
        """
        errors = []
        for item in self._items:
            if not item.check_item(self):
                errors.append(item._name)
        return errors

    def text_edit(self):
        """
        Edit data set with text input only
        """
        from guidata.dataset import textedit

        self.accept(textedit.TextEditVisitor(self))

    def edit(self, parent=None, apply=None, size=None):
        """
        Open a dialog box to edit data set
            * parent: parent widget (default is None, meaning no parent)
            * apply: apply callback (default is None)
            * size: dialog size (QSize object or integer tuple (width, height))
        """
        from guidata.dataset.qtwidgets import DataSetEditDialog

        win = DataSetEditDialog(
            self, icon=self.__icon, parent=parent, apply=apply, size=size
        )
        return win.exec_()

    def view(self, parent=None, size=None):
        """
        Open a dialog box to view data set
            * parent: parent widget (default is None, meaning no parent)
            * size: dialog size (QSize object or integer tuple (width, height))
        """
        from guidata.dataset.qtwidgets import DataSetShowDialog

        win = DataSetShowDialog(self, icon=self.__icon, parent=parent, size=size)
        return win.exec_()

    def to_string(self, debug=False, indent=None, align=False):
        """
        Return readable string representation of the data set
        If debug is True, add more details on data items
        """
        if indent is None:
            indent = "\n    "
        txt = self.__title + ":"

        def _get_label(item):
            if debug:
                return item._name
            else:
                return item.get_prop_value("display", self, "label")

        length = 0
        if align:
            for item in self._items:
                item_length = len(_get_label(item))
                if item_length > length:
                    length = item_length
        for item in self._items:
            if isinstance(item, ObjectItem):
                composite_dataset = item.get_value(self)
                txt += indent + composite_dataset.to_string(
                    debug=debug, indent=indent + "  "
                )
                continue
            elif isinstance(item, BeginGroup):
                txt += indent + item._name + ":"
                indent += "  "
                continue
            elif isinstance(item, EndGroup):
                indent = indent[:-2]
                continue
            value = getattr(self, "_" + item._name)
            if value is None:
                value_str = "-"
            else:
                value_str = item.get_string_value(self)
            if debug:
                label = item._name
            else:
                label = item.get_prop_value("display", self, "label")
            if length:
                label = label.ljust(length)
            txt += indent + label + ": " + value_str
            if debug:
                txt += " (" + item.__class__.__name__ + ")"
        return txt

    def accept(self, vis):
        """
        helper function that passes the visitor to the accept methods of all
        the items in this dataset
        """
        for item in self._items:
            item.accept(vis)

    def serialize(self, writer):
        for item in self._items:
            with writer.group(item._name):
                item.serialize(self, writer)

    def deserialize(self, reader):
        for item in self._items:
            with reader.group(item._name):
                try:
                    item.deserialize(self, reader)
                except RuntimeError as error:
                    if DEBUG_DESERIALIZE:
                        import traceback

                        print(
                            "DEBUG_DESERIALIZE enabled in datatypes.py", file=sys.stderr
                        )
                        traceback.print_stack()
                        print(error, file=sys.stderr)
                    item.set_default(self)

    def read_config(self, conf, section, option):
        from guidata.userconfigio import UserConfigReader

        reader = UserConfigReader(conf, section, option)
        self.deserialize(reader)

    def write_config(self, conf, section, option):
        from guidata.userconfigio import UserConfigWriter

        writer = UserConfigWriter(conf, section, option)
        self.serialize(writer)

    @classmethod
    def set_global_prop(klass, realm, **kwargs):
        for item in klass._items:
            item.set_prop(realm, **kwargs)


class ActivableDataSet(DataSet):
    """
    An ActivableDataSet instance must have an "enable" class attribute which
    will set the active state of the dataset instance
    (see example in: tests/activable_dataset.py)
    """

    _ro = True  # default *instance* attribute value
    _active = True
    _ro_prop = GetAttrProp("_ro")
    _active_prop = GetAttrProp("_active")

    def __init__(self, title=None, comment=None, icon=""):
        DataSet.__init__(self, title, comment, icon)

    #        self.set_readonly()

    @classmethod
    def active_setup(klass):
        """
        This class method must be called after the child class definition
        in order to setup the dataset active state
        """
        klass.set_global_prop("display", active=klass._active_prop)
        klass.enable.set_prop(
            "display", active=True, hide=klass._ro_prop, store=klass._active_prop
        )

    def set_readonly(self):
        """
        The dataset is now in read-only mode, i.e. all data items are disabled
        """
        self._ro = True
        self._active = self.enable

    def set_writeable(self):
        """
        The dataset is now in read/write mode, i.e. all data items are enabled
        """
        self._ro = False
        self._active = self.enable


class DataSetGroup(object):
    """
    Construct a DataSetGroup object, used to group several datasets together
        * datasets [list of DataSet objects]
        * title [string]
        * icon [QIcon or string]: icon show on the button (optional)
          (string: icon filename as in guidata/guiqwt image search paths)

    This class tries to mimics the DataSet interface.

    The GUI should represent it as a notebook with one page for each
    contained dataset.
    """

    def __init__(self, datasets, title=None, icon=""):
        self.__icon = icon
        self.datasets = datasets
        if title:
            self.__title = title
        else:
            self.__title = self.__class__.__name__

    def __str__(self):
        return "\n".join([dataset.__str__() for dataset in self.datasets])

    def get_title(self):
        """
        Return data set group title
        """
        return self.__title

    def get_comment(self):
        """
        Return data set group comment --> not implemented (will return None)
        """
        return None

    def check(self):
        """
        Check data set group items
        """
        return [dataset.check() for dataset in self.datasets]

    def text_edit(self):
        """
        Edit data set with text input only
        """
        raise NotImplementedError()

    def edit(self, parent=None, apply=None):
        """
        Open a dialog box to edit data set
        """
        from guidata.dataset.qtwidgets import DataSetGroupEditDialog

        win = DataSetGroupEditDialog(self, icon=self.__icon, parent=parent, apply=apply)
        return win.exec_()

    def accept(self, vis):
        """
        helper function that passes the visitor to the accept methods of all
        the items in this dataset
        """
        for dataset in self.datasets:
            dataset.accept(vis)


class GroupItem(DataItemProxy):
    """GroupItem proxy"""

    def __init__(self, item):
        DataItemProxy.__init__(self, item)
        self.group = []


class BeginGroup(DataItem):
    """
    Data item which does not represent anything
    but a begin flag to define a data set group
    """

    def serialize(self, instance, writer):
        pass

    def deserialize(self, instance, reader):
        pass

    def get_group(self):
        return GroupItem(self)


class EndGroup(DataItem):
    """
    Data item which does not represent anything
    but an end flag to define a data set group
    """

    def serialize(self, instance, writer):
        pass

    def deserialize(self, instance, reader):
        pass


class TabGroupItem(GroupItem):
    pass


class BeginTabGroup(BeginGroup):
    def get_group(self):
        return TabGroupItem(self)


class EndTabGroup(EndGroup):
    pass
