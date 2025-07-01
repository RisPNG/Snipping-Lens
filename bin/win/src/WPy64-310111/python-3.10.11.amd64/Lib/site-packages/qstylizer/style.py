# coding: utf-8

import re
import copy
import collections
import inflection

import qstylizer.descriptor.prop
import qstylizer.descriptor.subcontrol
import qstylizer.descriptor.pseudostate
import qstylizer.descriptor.pseudoprop
import qstylizer.descriptor.qclass
import qstylizer.descriptor.stylerule


QPROPERTIES = qstylizer.descriptor.prop.PropParent.get_attr_options()
QSUBCONTROLS = qstylizer.descriptor.subcontrol.SubControlParent.get_attr_options()
QPSEUDOSTATES = qstylizer.descriptor.pseudostate.PseudoStateParent.get_attr_options()
QPSEUDOPROPS = qstylizer.descriptor.pseudoprop.PseudoPropParent.get_attr_options()
QCLASSES = qstylizer.descriptor.qclass.ClassStyleParent.get_attr_options()


class StyleRule(
    collections.OrderedDict, qstylizer.descriptor.prop.PropParent,
    qstylizer.descriptor.pseudoprop.PseudoPropParent
):
    """StyleRule Object.

    A dictionary containing nested Styles and property:value pairs.

    Example structure::

        <ClassRule name="QCheckBox" dict={
            "color": <PropRule name="color" value="red" />,
            "background-color": <PropRule name="background-color" value="black" />,
            "indicator": <SubControlRule name="indicator" dict={
                "border": <PropRule name="border" value="1px solid green" />,
                "hover": <PseudoStateRule name="hover" dict={
                    "background-color": <PropRule name="background-color" value="green" />,
                    "border": <PropRule name="border value="0px transparent black" />
                } />
            } />
        } />

    Output format::

        <selector> {
            <property>: <value>;
            <property>: <value>;
            ...
        }

    Stylesheet output::

        QCheckBox {
            color: red;
            background-color: black;
        }
        QCheckBox::indicator {
            border: 1px solid green;
        }
        QCheckBox::indicator:hover {
            background-color: green;
            border: 0px transparent black;
        }

    """
    _split_regex = r"\*|\[[A-Za-z0-9='\"]+\]|\W*\w*"

    @classmethod
    def split_selector(cls, selector):
        """Split the selector based on the _split_regex.

        Return a list of each component.
        Example::

            name = "QObject::subcontrol:pseudostate"
            return value = ["QObject", "::subcontrol", ":pseudostate"]

        :param name: String name

        """
        selector = selector.replace("-", "_")
        return re.findall(cls._split_regex, selector)[:-1]

    def __init__(self, name=None, value=None, parent=None):
        """Initialize the StyleRule dictionary.

        .. note:: All public variables will be put into ordered dictionary.

        :param name: The name of the StyleRule
        :param value: The property value
        :param parent:  The parent StyleRule

        """
        super(StyleRule, self).__init__()

        self._name = self._sanitize_key(name) if name else None
        self._parent = parent
        self._attributes = self.get_attributes()
        self._attr_options = self.get_attr_options()
        self._value = self._sanitize_value(value)
        self._child_rules = collections.OrderedDict()

    @staticmethod
    def _sanitize_key(key):
        """Strip the key of colons and replace underscores with dashes.

        :param key: A string variable

        """
        key = str(key)
        if key and key[0] not in ["Q", "#", "[", " "] and key != inflection.camelize(key) and not key.startswith("qproperty-"):
            key = inflection.underscore(key)
        return (
            key
            .replace("not_", "!")
            .replace(":", "")
            .replace("_", "-")
        )

    @staticmethod
    def _sanitize_value(value):
        """Strip the value of any semi-colons.

        :param value: A value of any type

        """
        try:
            if type(value) in [str, unicode]:
                return value.replace(";", "")
        except NameError:
            if type(value) in [str, bytes]:
                return value.replace(";", "")

        return value

    def find_or_create_child_rule(self, name):
        """Find or create a child rule from a string key.

        If the key rule already exists, return the rule.
        If there is a comma in requested key, return a StyleRuleList object.
        Otherwise create rules from the style rule names in the key and return
        the top level rule or property.

        :param name: The dictionary key

        """
        value = self.find_child_rule(name)
        if value is not None:
            return value
        if "," in name:
            rule_list = self.create_child_rule_list(name)
            return rule_list
        return self.create_child_rules(name)

    def find_child_rule(self, key):
        """Find rule from key.

        Return the sanitized key's hash value in the ordered dict.

        """
        key = self._sanitize_key(key)
        return self.get(key)

    def create_child_rule_list(self, name):
        """Create a StyleRuleList object and add it to ordered dict.

        :param name: String name

        """
        rule_list = StyleRuleList(name=name, parent=self)
        self.set_child_rule(name, rule_list)
        return rule_list

    def create_child_rules(self, selector):
        """Create child rules from selector string.

        Split the selector into individual components based on the _split_regex
        and recursively build the StyleRule hierarchy looping through
        the components.

        If selector is "QClass::subcontrol:pseudostate",
        curr_name is "QClass" and remaining is "::subcontrol:pseudostate"

        :param name: String to split

        """
        curr_name = self.split_selector(selector)[0]
        remaining = selector.split(curr_name, 1)[-1].replace("-", "_")
        rule = self.find_child_rule(curr_name)
        if rule is None:
            rule = self.create_child_rule(curr_name)
        if remaining and remaining != curr_name:
            return rule.find_or_create_child_rule(remaining)
        return rule

    def create_child_rule(self, name):
        """Create child rule from name.

        Determine subclass from name, create an instance of the subclass,
        then add it to ordered dict.

        :param name: String name

        """
        class_ = rule_class(name)
        rule = class_(name=name, parent=self)
        self.set_child_rule(name, rule)
        return rule

    def set_child_rule(self, key, value, **kwargs):
        """Set rule in ordered dictionary."""
        key = self._sanitize_key(key)
        if not isinstance(value, StyleRule):
            value = self._sanitize_value(value)
            value = PropRule(name=key, value=value, parent=self)
        self._add_child_rule(value)
        return super(StyleRule, self).__setitem__(key, value, **kwargs)

    def _add_child_rule(self, rule):
        """Add a rule to the _child_rules dictionary.

        :param rule: A StyleRule object.

        """
        if rule.selector not in self._child_rules:
            self._child_rules[rule.selector] = rule
        if self._parent is not None:
            self._parent._add_child_rule(rule)

    @property
    def selector(self):
        """Get the selector.

        Example::

            Object::subcontrol:pseudostate

        """
        if self._parent is None:
            return self.name if self.name else ""
        return self._parent.selector + self.scope_operator + self.name

    @property
    def name(self):
        """Return the name of the StyleRule (eg. "QCheckBox").

        Strip off the scope operator if it exists in name.

        """
        if (self._name and self.scope_operator and
           self._name.startswith(self.scope_operator)):
            return self._name.split(self.scope_operator, 1)[-1]
        return self._name

    @name.setter
    def name(self, name):
        self._name = self._sanitize_key(name)

    @property
    def parent(self):
        return self._parent

    @property
    def scope_operator(self):
        """Get the scope operator.

        The scope operator is the "::" or ":" that is printed in front
        of the name of the StyleRule in the selector.

        Subclasses are expected to define the scope operator or else it will
        try to guess it based on its position in the hierarchy.

        """
        if self.is_top_level():
            return ""
        elif self.is_leaf():
            return ":"
        return "::"

    def is_leaf(self):
        """Determine if StyleRule is a leaf.

        StyleRule is a leaf its child rules dictionary contains only PropRules.

        """
        for rule in self._child_rules.values():
            if not isinstance(rule, PropRule):
                return False
        return True

    def is_top_level(self):
        """Determine if StyleRule is top level.

        StyleRule is top level if its parent is of the StyleSheet class.

        """
        return isinstance(self._parent, StyleSheet)

    def _to_string_recursive(self):
        """Convert all child rules into a single stirng in css format.

        Loop through all of the rules and generate a stylesheet string.

        """
        stylesheet = self.toString(recursive=False)
        for rule in self._child_rules.values():
            stylesheet += rule.toString(recursive=False)
        return stylesheet

    def _to_string(self, recursive=False):
        """Convert to a single string in css format.

        :param recursive: Output all of the sub-style rules.

        """
        if recursive:
            return self._to_string_recursive()
        rule_template = "{selector} {{\n{properties}}}\n"
        prop_template = "    {}: {};\n"
        properties = ""
        sheet = ""
        selector = self.selector
        for key, rule in self.items():
            if rule.value is not None:
                properties += prop_template.format(key, rule.value)
        if properties:
            sheet = rule_template.format(**locals())
        return sheet

    def toString(self, *args, **kwargs):
        """Convert to a single string in css format.

        Use camelcase for function name to match PyQt/PySide.

        """
        return self._to_string(*args, **kwargs)

    def _set_values(self, *args, **kwargs):
        """Set property values in the style rule."""
        for key, value in kwargs.items():
            if "-" in key:
                self.__getitem__(key).setValue(value)
            else:
                self.__getattribute__(key).setValue(value)

    def update(self, *args, **kwargs):
        if isinstance(args[0], StyleRule):
            for key, child_rule in args[0]._child_rules.items():
                rule = self.find_or_create_child_rule(key)

                for k, v in child_rule.items():
                    if isinstance(v, StyleRule):
                        v = copy.deepcopy(v)
                        v._parent = rule

                        rule[k] = v

    def setValues(self, *args, **kwargs):
        """Set property values in the style rule.

        Use camelcase for function name to match PyQt/PySide.

        """
        self._set_values(*args, **kwargs)

    def _set_value(self, value):
        """Set property value."""
        self._value = self._sanitize_value(value)

    def setValue(self, value):
        """Set property value.

        Use camelcase for function name to match PyQt/PySide.

        """
        self._set_value(value)

    @property
    def value(self):
        return self._value

    def __getitem__(self, key):
        """Override the retrieving of a value from dictionary.

        Find or create rule in the key's hash location.

        :param key: The dictionary key

        """
        return self.find_or_create_child_rule(key)

    def __delattr__(self, name):
        """Override the deletion of an attribute.

        If attribute starts with an underscore, delete the attribute from
        the object's __dict__ otherwise delete it from the ordered dict.

        :param name: String name of attribute to delete

        """
        if name in self.__dict__:
            return super(StyleRule, self).__delattr__(name)
        return self.__delitem__(name)

    def __setattr__(self, name, val):
        """Override the setting of an attribute.

        If name is in the pre-defined attributes, call the attribute's
        descriptor's __set__ function. Otherwise, add it to ordered dict as-is.

        :param name: The attribute name
        :param val: The value to set

        """
        if name.startswith("_"):
            return super(StyleRule, self).__setattr__(name, val)
        elif name in self._attributes:
            return self._attributes[name].__set__(self, val)
        return self.set_child_rule(name, val)

    def __setitem__(self, key, value, **kwargs):
        """Override the setting of an attribute in ordered dict.

        If key is in pre-defined attributes, call attribute's descriptor's
        __set__ function. Otherwise add the value to ordered dict as-is.

        :param key: The hash key of the ordered dict
        :param value: The value to map to hash key

        """
        if key in self._attr_options:
            if "-" in key:
                key = key.replace("-", "_")
                key = inflection.camelize(key)
                key = key[0].lower() + key[1:]
            try:
                return self._attributes[key].__set__(self, value)
            except KeyError:
                pass
        return self.set_child_rule(key, value, **kwargs)

    def __deepcopy__(self, memo):
        """Override deepcopy.

        Make a deepcopy of all member attributes as well as all rule rules
        in ordered dictionary.

        """
        cls = self.__class__
        result = cls.__new__(cls)
        result._name = self._name
        result._value = self._value
        result._parent = None
        result._child_rules = collections.OrderedDict()
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k in ("_child_rules",):
                continue
            setattr(result, k, copy.deepcopy(v, memo))

        result.clear()
        for k, v in self.items():
            if isinstance(v, StyleRule):
                v = copy.deepcopy(v, memo)
                v._parent = result
                result.set_child_rule(k, v)

        result._parent = self._parent
        return result

    def __repr__(self, *args, **kwargs):
        """Set the representation to look like xml syntax."""
        value_attr = ""
        name_attr = ""
        if self.value is not None:
            value_attr = "value={0!r} ".format(self.value)
        if self.name is not None:
            name_attr = "name={0!r} ".format(self.name)
        return "<{0} {1}{2}/>".format(
            self.__class__.__name__, name_attr, value_attr
        )

    def __str__(self):
        """Call toString if StyleRule is cast to string."""
        return self.toString()


class StyleSheet(StyleRule, qstylizer.descriptor.qclass.ClassStyleParent):
    """The StyleSheet definition.

    Contains descriptors for all class and property options.

    """
    def is_global_scope(self):
        """Determine if stylesheet is global scope.

        A StyleSheet is global scope if it has no rules.
        Resulting string should contain no brackets.
        ::

            background-color: red;
            border: none;

        """
        return self.is_leaf()

    def _to_string_recursive(self):
        """Convert all child rules into a single stirng in css format.

        Loop through all of the rules and generate a stylesheet string.

        """
        stylesheet = self.toString(recursive=False)
        for key, rule in self._child_rules.items():
            if key == "*":
                continue
            stylesheet += rule.toString(recursive=False)
        return stylesheet

    def _to_string(self, recursive=True):
        """Return the selector and properties as a single string.

        :param recursive: Loop through all rules to generate a stylesheet.

        """
        if recursive:
            return self._to_string_recursive()

        rule_template = "{selector} {{\n{properties}}}\n"
        prop_template = "    {}: {};\n"
        selector = self.selector
        if self.is_global_scope():
            rule_template = "{properties}"
            prop_template = "{}: {};\n"
        else:
            selector = "*"

        properties = ""
        sheet = ""
        for key, value in self.items():

            # Output the "*" property values if applicable.
            if key == "*":
                for global_key, global_value in self.__getitem__("*").items():
                    if not isinstance(global_value, StyleRule):
                        properties += prop_template.format(
                            global_key, global_value
                        )
                    elif global_value.value is not None:
                        properties += prop_template.format(
                            global_key, global_value.value
                        )

            if not isinstance(value, StyleRule):
                properties += prop_template.format(key, value)
            elif value.value is not None:
                properties += prop_template.format(key, value.value)

        if properties:
            sheet = rule_template.format(**locals())

        return sheet

    @property
    def name(self):
        """Return the name of the StyleSheet."""
        return self._name


class ClassRule(
    StyleRule, qstylizer.descriptor.subcontrol.SubControlParent,
    qstylizer.descriptor.pseudostate.PseudoStateParent
):
    """The ClassRule definition.

    Example class rule name: "QCheckBox".
    Contains descriptors for all subcontrols and pseudostates.

    """


class ObjectRule(ClassRule):
    """The ObjectRule definition.

    Example object rule name: "#objectName".
    Inherits from ClassRule. Only difference is "#" is the scope operator.

    """
    @property
    def scope_operator(self):
        return "#"


class ChildClassRule(ClassRule):
    """The ChildClassRule definition.

    Example object rule name: " QFrame".
    Inherits from ClassRule.
    ::

        QWidget QFrame {
            property: value
        }

    """
    @property
    def scope_operator(self):
        return " "


class ObjectPropRule(ClassRule):
    """The ObjectPropRule definition.

    Example object property rule name: "[echoMode="2"]".

    """
    @property
    def scope_operator(self):
        return ""


class StyleRuleList(StyleRule):
    """The StyleRuleList definition.

    Example rule list name: "QCheckBox, QComboBox".

    """

    @staticmethod
    def _sanitize_key(key):
        """Strip the key of newlines only."""
        return str(key).replace("\n", "")

    def _create_child_rules_in_parent(self, name, val):
        """Find or create value in parent StyleRule

        Will loop through all components in name separated by a comma and set the
        property in each of the rules in the parent StyleRule.

        :param name: The attribute name
        :param val: The value

        """
        rule_names = self.name.split(",")
        for rule_name in rule_names:
            self._parent.find_or_create_child_rule(rule_name).__setattr__(
                name, val
            )
        return None

    @property
    def scope_operator(self):
        return ""

    def __setattr__(self, name, val):
        """Override the setting of an attribute.

        :param name: The attribute name
        :param val: The value to set

        """
        if name.startswith("_"):
            return super(StyleRule, self).__setattr__(name, val)
        return self._create_child_rules_in_parent(name, val)

    def __setitem__(self, key, value, **kwargs):
        """Override the setting of a value in ordered dict.

        :param key: The hash key of the ordered dict
        :param value: The value to map to hash key

        """
        return self._create_child_rules_in_parent(key, value)

    @property
    def name(self):
        """Return the name with no spaces."""
        return self._name.replace(" ", "")


class SubControlRule(StyleRule, qstylizer.descriptor.pseudostate.PseudoStateParent):
    """The SubControlRule definition.

    Example subcontrol name: "::indicator".

    """
    @property
    def scope_operator(self):
        return "::"


class PseudoStateRule(SubControlRule):
    """The PseudoStateRule definition.

    Example pseudostate name: ":hover".

    """
    @property
    def scope_operator(self):
        return ":"


class PseudoPropRule(PseudoStateRule):
    """The PseudoPropRule definition.

    The PseudoPropRule covers PseudoStates and properties that have the same
    name like "top", "bottom", "left", and "right".

    It is basically a PseudoStateRule that also stores a property value.
    In the following example, *top* is the PseudoPropRule.

    .. code-block:: python

        >>> css.QWidget.tab.top = "0"
        >>> css.QWidget.tab.top.color = "green"
        >>> print(css.toString())
        QWidget::tab {
            top: 0;
        }
        QWidget::tab:top {
            color: green;
        }

    """


class PropRule(StyleRule):
    """The PropRule definition.

    Example prop rule name: "background-color".

    """


def rule_class(name):
    """Determine StyleRule subclass from string name.

    :param name: name of type string

    """
    if "!" in name:
        name = name.replace("!", "")
        name = name[0].lower() + name[1:]
    class_ = StyleRule
    if name.startswith("::") or name in QSUBCONTROLS:
        class_ = SubControlRule
    elif name.startswith(":") or name in QPSEUDOSTATES:
        class_ = PseudoStateRule
    elif name.startswith("#"):
        class_ = ObjectRule
    elif name.startswith(" "):
        class_ = ChildClassRule
    elif name in QCLASSES or name.startswith("Q"):
        class_ = ClassRule
    elif "=" in name:
        class_ = ObjectPropRule
    return class_
