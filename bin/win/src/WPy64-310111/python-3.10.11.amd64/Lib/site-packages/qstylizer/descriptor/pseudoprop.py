# coding: utf-8

import qstylizer.descriptor.stylerule


class PseudoPropDescriptor(qstylizer.descriptor.stylerule.StyleRuleDescriptor):
    """Pseudo-property descriptor."""

    @property
    def rule_cls(self):
        import qstylizer.style
        return qstylizer.style.PseudoPropRule


class PseudoPropParent(qstylizer.descriptor.stylerule.StyleRuleParent):
    """Pseudo-property setter.

    Contains descriptors for all known pseudo-properties.

    """
    _descriptor_cls = PseudoPropDescriptor

    left = _descriptor_cls("left")
    right = _descriptor_cls("right")
    top = _descriptor_cls("top")
    bottom = _descriptor_cls("bottom")
