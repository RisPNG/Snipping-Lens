# coding: utf-8

import copy


class StyleRuleDescriptor(object):
    """StyleRule descriptor."""

    def __init__(self, name):
        """Initialize the StyleRuleDescriptor instance.

        :param name: The attribute name of type string

        """
        self.name = name

    def __get__(self, instance, *args, **kwargs):
        """Get the value from the StyleRule's ordered dict.

        If value doesn't exist, create a new StyleRule instance and add it
        to the StyleRule's ordered dict.

        :param instance: The StyleRule instance

        """
        import qstylizer.style
        assert isinstance(instance, qstylizer.style.StyleRule)
        if instance.find_child_rule(self.name) is None:
            new_style = self.rule_cls(
                name=self.name,
                parent=instance,
            )
            instance.set_child_rule(self.name, new_style)
        return instance.find_child_rule(self.name)

    def __set__(self, instance, value):
        """Set the value in the StyleRule's ordered dict.

        If the value is a StyleRule, simply add it to the ordered dict.
        Otherwise create a new StyleRule instance, set its value
        attribute to the value, and add it to the ordered dict.

        :param instance: The StyleRule instance
        :param value: The value to set in StyleRule instance

        """
        if isinstance(value, self.rule_cls):
            value = copy.deepcopy(value)
            value._parent = instance
            instance.set_child_rule(self.name, value)
        else:
            new_style = self.rule_cls(
                name=self.name,
                parent=instance,
            )
            new_style.setValue(value)
            instance.set_child_rule(self.name, new_style)

    @property
    def rule_cls(self):
        import qstylizer.style
        return qstylizer.style.StyleRule


class StyleRuleParent(object):
    """StyleRule descriptor.

    Contains functions for getting all known attributes of the StyleRule.

    """
    _descriptor_cls = StyleRuleDescriptor

    @classmethod
    def get_attributes(cls):
        """Get all of the settable attributes of the StyleRule.

        Loop through all base classes to gather all known attributes.
        Returns a dictionary with the attribute name as the key and descriptor
        as the value.

        """
        attributes = {}
        for class_ in cls.__bases__:
            if not issubclass(class_, StyleRuleParent):
                continue
            attributes.update({
                key: value for key, value in class_.__dict__.items()
                if isinstance(value, class_._descriptor_cls)
            })
            attributes.update(class_.get_attributes())
        attributes.update({
            key: value for key, value in cls.__dict__.items()
            if isinstance(value, cls._descriptor_cls)
        })
        return attributes

    @classmethod
    def get_attr_options(cls):
        """Get all of the attribute names of the StyleRule.

        Returns a set of all possible dashcase attribute names.

        """
        return set(
            [value.name for value in cls.get_attributes().values()]
        )
