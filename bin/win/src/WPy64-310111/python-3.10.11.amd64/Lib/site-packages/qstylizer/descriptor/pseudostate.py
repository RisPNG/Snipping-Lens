# coding: utf-8

import qstylizer.descriptor.stylerule


class PseudoStateDescriptor(qstylizer.descriptor.stylerule.StyleRuleDescriptor):
    """Pseudo-state descriptor."""

    @property
    def rule_cls(self):
        import qstylizer.style
        return qstylizer.style.PseudoStateRule


class PseudoStateParent(qstylizer.descriptor.stylerule.StyleRuleParent):
    """Pseudostate setter.

    Contains descriptors for all known pseudostates.

    """
    _descriptor_cls = PseudoStateDescriptor

    active = _descriptor_cls("active")
    adjoinsItem = _descriptor_cls("adjoins-item")
    alternate = _descriptor_cls("alternate")
    checked = _descriptor_cls("checked")
    closable = _descriptor_cls("closable")
    closed = _descriptor_cls("closed")
    default = _descriptor_cls("default")
    disabled = _descriptor_cls("disabled")
    editFocus = _descriptor_cls("edit-focus")
    editable = _descriptor_cls("editable")
    enabled = _descriptor_cls("enabled")
    exclusive = _descriptor_cls("exclusive")
    first = _descriptor_cls("first")
    flat = _descriptor_cls("flat")
    floatable = _descriptor_cls("floatable")
    focus = _descriptor_cls("focus")
    hasChildren = _descriptor_cls("has-children")
    hasSiblings = _descriptor_cls("has-siblings")
    horizontal = _descriptor_cls("horizontal")
    hover = _descriptor_cls("hover")
    indeterminate = _descriptor_cls("indeterminate")
    last = _descriptor_cls("last")
    maximized = _descriptor_cls("maximized")
    middle = _descriptor_cls("middle")
    minimized = _descriptor_cls("minimized")
    movable = _descriptor_cls("movable")
    nextSelected = _descriptor_cls("next-selected")
    noFrame = _descriptor_cls("no-frame")
    nonExclusive = _descriptor_cls("non-exclusive")
    off = _descriptor_cls("off")
    on = _descriptor_cls("on")
    onlyOne = _descriptor_cls("only-one")
    open = _descriptor_cls("open")
    pressed = _descriptor_cls("pressed")
    previousSelected = _descriptor_cls("previous-selected")
    readOnly = _descriptor_cls("read-only")
    selected = _descriptor_cls("selected")
    unchecked = _descriptor_cls("unchecked")
    vertical = _descriptor_cls("vertical")
    window = _descriptor_cls("window")
