# coding: utf-8

import qstylizer.descriptor.stylerule


class SubControlDescriptor(qstylizer.descriptor.stylerule.StyleRuleDescriptor):
    """Subcontrol descriptor."""

    @property
    def rule_cls(self):
        import qstylizer.style
        return qstylizer.style.SubControlRule


class SubControlParent(qstylizer.descriptor.stylerule.StyleRuleParent):
    """Subcontrol setter.

    Contains descriptors for all known subcontrols.

    """
    _descriptor_cls = SubControlDescriptor

    addLine = _descriptor_cls("add-line")
    addPage = _descriptor_cls("add-page")
    branch = _descriptor_cls("branch")
    chunk = _descriptor_cls("chunk")
    closeButton = _descriptor_cls("close-button")
    corner = _descriptor_cls("corner")
    downArrow = _descriptor_cls("down-arrow")
    downButton = _descriptor_cls("down-button")
    dropDown = _descriptor_cls("drop-down")
    floatButton = _descriptor_cls("float-button")
    groove = _descriptor_cls("groove")
    indicator = _descriptor_cls("indicator")
    handle = _descriptor_cls("handle")
    icon = _descriptor_cls("icon")
    item = _descriptor_cls("item")
    leftArrow = _descriptor_cls("left-arrow")
    leftCorner = _descriptor_cls("left-corner")
    menuArrow = _descriptor_cls("menu-arrow")
    menuButton = _descriptor_cls("menu-button")
    menuIndicator = _descriptor_cls("menu-indicator")
    rightArrow = _descriptor_cls("right-arrow")
    pane = _descriptor_cls("pane")
    rightCorner = _descriptor_cls("right-corner")
    scroller = _descriptor_cls("scroller")
    section = _descriptor_cls("section")
    separator = _descriptor_cls("separator")
    subLine = _descriptor_cls("sub-line")
    subPage = _descriptor_cls("sub-page")
    tab = _descriptor_cls("tab")
    tabBar = _descriptor_cls("tab-bar")
    tear = _descriptor_cls("tear")
    tearoff = _descriptor_cls("tearoff")
    text = _descriptor_cls("text")
    title = _descriptor_cls("title")
    upArrow = _descriptor_cls("up-arrow")
    upButton = _descriptor_cls("up-button")
