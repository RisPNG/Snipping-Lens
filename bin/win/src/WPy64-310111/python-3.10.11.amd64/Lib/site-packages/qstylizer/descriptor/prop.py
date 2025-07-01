# coding: utf-8

import copy

import qstylizer.descriptor.stylerule


PROPERTY_VALUES = {
    "absolute",
    "active",
    "alignment",
    "alternate-base",
    "always",
    "auto",
    "base",
    "bold",
    "bottom",
    "bright-text",
    "button",
    "button-text",
    "center",
    "circle",
    "dark",
    "dashed",
    "decimal",
    "disabled",
    "disc",
    "dot-dash",
    "dot-dot-dash",
    "dotted",
    "double",
    "fixed",
    "groove",
    "highlight",
    "highlighted-text",
    "icon-size",
    "inset",
    "italic",
    "large",
    "left",
    "light",
    "line-through",
    "link",
    "link-visited",
    "lower-alpha",
    "lower-roman",
    "lowercase",
    "medium",
    "mid",
    "middle",
    "midlight",
    "native",
    "no-repeat",
    "none",
    "normal",
    "nowrap",
    "oblique",
    "off",
    "on",
    "outset",
    "overline",
    "pre",
    "pre-wrap",
    "relative",
    "repeat",
    "repeat-x",
    "repeat-xy",
    "repeat-y",
    "ridge",
    "right",
    "round",
    "scroll",
    "selected",
    "shadow",
    "small",
    "small-caps",
    "solid",
    "square",
    "static",
    "stretch",
    "sub",
    "super",
    "text",
    "top",
    "transparent",
    "underline",
    "upper-alpha",
    "upper-roman",
    "uppercase",
    "wave",
    "window",
    "window-text",
    "x-large",
    "xx-large",
}


class PropDescriptor(qstylizer.descriptor.stylerule.StyleRuleDescriptor):
    """Property descriptor."""

    @property
    def rule_cls(self):
        import qstylizer.style
        return qstylizer.style.PropRule


class PropParent(qstylizer.descriptor.stylerule.StyleRuleParent):
    """Property setter.

    Contains descriptors for all known properties.

    """
    _descriptor_cls = PropDescriptor

    qtBackgroundRole = _descriptor_cls("-qt-background-role")
    qtBlockIndent = _descriptor_cls("-qt-block-indent")
    qtLineHeightType = _descriptor_cls("-qt-line-height-type")
    qtListIndent = _descriptor_cls("-qt-list-indent")
    qtListNumberPrefix = _descriptor_cls("-qt-list-number-prefix")
    qtListNumberSuffix = _descriptor_cls("-qt-list-number-suffix")
    qtParagraphType = _descriptor_cls("-qt-paragraph-type")
    qtStyleFeatures = _descriptor_cls("-qt-style-features")
    qtTableType = _descriptor_cls("-qt-table-type")
    qtUserState = _descriptor_cls("-qt-user-state")
    alternateBackgroundColor = _descriptor_cls("alternate-background-color")
    alignment = _descriptor_cls("alignment")
    background = _descriptor_cls("background")
    backgroundAttachment = _descriptor_cls("background-attachment")
    backgroundClip = _descriptor_cls("background-clip")
    backgroundColor = _descriptor_cls("background-color")
    backgroundImage = _descriptor_cls("background-image")
    backgroundOrigin = _descriptor_cls("background-origin")
    backgroundPosition = _descriptor_cls("background-position")
    backgroundRepeat = _descriptor_cls("background-repeat")
    border = _descriptor_cls("border")
    borderBottom = _descriptor_cls("border-bottom")
    borderBottomColor = _descriptor_cls("border-bottom-color")
    borderBottomLeftRadius = _descriptor_cls("border-bottom-left-radius")
    borderBottomRightRadius = _descriptor_cls("border-bottom-right-radius")
    borderBottomStyle = _descriptor_cls("border-bottom-style")
    borderBottomWidth = _descriptor_cls("border-bottom-width")
    borderColor = _descriptor_cls("border-color")
    borderImage = _descriptor_cls("border-image")
    borderLeft = _descriptor_cls("border-left")
    borderLeftColor = _descriptor_cls("border-left-color")
    borderLeftStyle = _descriptor_cls("border-left-style")
    borderLeftWidth = _descriptor_cls("border-left-width")
    borderRadius = _descriptor_cls("border-radius")
    borderRight = _descriptor_cls("border-right")
    borderRightColor = _descriptor_cls("border-right-color")
    borderRightStyle = _descriptor_cls("border-right-style")
    borderRightWidth = _descriptor_cls("border-right-width")
    borderStyle = _descriptor_cls("border-style")
    borderTop = _descriptor_cls("border-top")
    borderTopColor = _descriptor_cls("border-top-color")
    borderTopLeftRadius = _descriptor_cls("border-top-left-radius")
    borderTopRightRadius = _descriptor_cls("border-top-right-radius")
    borderTopStyle = _descriptor_cls("border-top-style")
    borderTopWidth = _descriptor_cls("border-top-width")
    borderWidth = _descriptor_cls("border-width")
    color = _descriptor_cls("color")
    comboboxPopup = _descriptor_cls("combobox-popup")
    float = _descriptor_cls("float")
    font = _descriptor_cls("font")
    fontFamily = _descriptor_cls("font-family")
    fontSize = _descriptor_cls("font-size")
    fontStyle = _descriptor_cls("font-style")
    fontVariant = _descriptor_cls("font-variant")
    fontWeight = _descriptor_cls("font-weight")
    height = _descriptor_cls("height")
    iconSize = _descriptor_cls("icon-size")
    image = _descriptor_cls("image")
    imagePosition = _descriptor_cls("image-position")
    lineHeight = _descriptor_cls("line-height")
    listStyle = _descriptor_cls("list-style")
    listStyleType = _descriptor_cls("list-style-type")
    margin = _descriptor_cls("margin")
    marginBottom = _descriptor_cls("margin-bottom")
    marginLeft = _descriptor_cls("margin-left")
    marginRight = _descriptor_cls("margin-right")
    marginTop = _descriptor_cls("margin-top")
    maxHeight = _descriptor_cls("max-height")
    maxWidth = _descriptor_cls("max-width")
    minHeight = _descriptor_cls("min-height")
    minWidth = _descriptor_cls("min-width")
    outline = _descriptor_cls("outline")
    outlineBottomLeftRadius = _descriptor_cls("outline-bottom-left-radius")
    outlineBottomRightRadius = _descriptor_cls("outline-bottom-right-radius")
    outlineColor = _descriptor_cls("outline-color")
    outlineOffset = _descriptor_cls("outline-offset")
    outlineRadius = _descriptor_cls("outline-radius")
    outlineStyle = _descriptor_cls("outline-style")
    outlineTopLeftRadius = _descriptor_cls("outline-top-left-radius")
    outlineTopRightRadius = _descriptor_cls("outline-top-right-radius")
    outlineWidth = _descriptor_cls("outline-width")
    padding = _descriptor_cls("padding")
    paddingBottom = _descriptor_cls("padding-bottom")
    paddingLeft = _descriptor_cls("padding-left")
    paddingRight = _descriptor_cls("padding-right")
    paddingTop = _descriptor_cls("padding-top")
    pageBreakAfter = _descriptor_cls("page-break-after")
    pageBreakBefore = _descriptor_cls("page-break-before")
    position = _descriptor_cls("position")
    selectionBackgroundColor = _descriptor_cls("selection-background-color")
    selectionColor = _descriptor_cls("selection-color")
    showDecorationSelected = _descriptor_cls("show-decoration-selected")
    spacing = _descriptor_cls("spacing")
    subcontrolOrigin = _descriptor_cls("subcontrol-origin")
    subcontrolPosition = _descriptor_cls("subcontrol-position")
    textAlign = _descriptor_cls("text-align")
    textDecoration = _descriptor_cls("text-decoration")
    textIndent = _descriptor_cls("text-indent")
    textTransform = _descriptor_cls("text-transform")
    textUnderlineStyle = _descriptor_cls("text-underline-style")
    verticalAlign = _descriptor_cls("vertical-align")
    whiteSpace = _descriptor_cls("white-space")
    width = _descriptor_cls("width")
