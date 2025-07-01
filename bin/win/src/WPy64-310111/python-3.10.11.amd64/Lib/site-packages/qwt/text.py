# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
Text widgets
------------

QwtText
~~~~~~~

.. autoclass:: QwtText
   :members:

QwtTextLabel
~~~~~~~~~~~~

.. autoclass:: QwtTextLabel
   :members:

Text engines
------------

QwtTextEngine
~~~~~~~~~~~~~

.. autoclass:: QwtTextEngine
   :members:

QwtPlainTextEngine
~~~~~~~~~~~~~~~~~~

.. autoclass:: QwtPlainTextEngine
   :members:

QwtRichTextEngine
~~~~~~~~~~~~~~~~~

.. autoclass:: QwtRichTextEngine
   :members:
"""

import math
import os
import struct

from qtpy.QtGui import (
    QPainter,
    QPalette,
    QFont,
    QFontMetrics,
    QColor,
    QTextDocument,
    QTextOption,
    QFontMetricsF,
    QPixmap,
    QFontInfo,
    QTransform,
    QAbstractTextDocumentLayout,
)
from qtpy.QtWidgets import QFrame, QWidget, QSizePolicy, QApplication
from qtpy.QtCore import Qt, QSizeF, QSize, QRectF

from qwt.painter import QwtPainter
from qwt.qthelpers import qcolor_from_str

QWIDGETSIZE_MAX = (1 << 24) - 1

QT_API = os.environ["QT_API"]


def taggedRichText(text, flags):
    richText = text
    if flags & Qt.AlignJustify:
        richText = '<div align="justify">' + richText + "</div>"
    elif flags & Qt.AlignRight:
        richText = '<div align="right">' + richText + "</div>"
    elif flags & Qt.AlignHCenter:
        richText = '<div align="center">' + richText + "</div>"
    return richText


class QwtRichTextDocument(QTextDocument):
    def __init__(self, text, flags, font):
        super(QwtRichTextDocument, self).__init__(None)
        self.setUndoRedoEnabled(False)
        self.setDefaultFont(font)
        self.setHtml(text)

        option = self.defaultTextOption()
        if flags & Qt.TextWordWrap:
            option.setWrapMode(QTextOption.WordWrap)
        else:
            option.setWrapMode(QTextOption.NoWrap)

        option.setAlignment(flags)
        self.setDefaultTextOption(option)

        root = self.rootFrame()
        fm = root.frameFormat()
        fm.setBorder(0)
        fm.setMargin(0)
        fm.setPadding(0)
        fm.setBottomMargin(0)
        fm.setLeftMargin(0)
        root.setFrameFormat(fm)

        self.adjustSize()


class QwtTextEngine(object):
    """
    Abstract base class for rendering text strings

    A text engine is responsible for rendering texts for a
    specific text format. They are used by `QwtText` to render a text.

    `QwtPlainTextEngine` and `QwtRichTextEngine` are part of the
    `PythonQwt` library.
    The implementation of `QwtMathMLTextEngine` uses code from the
    `Qt` solution package. Because of license implications it is built into
    a separate library.

    .. seealso::

        :py:meth:`qwt.text.QwtText.setTextEngine()`
    """

    def __init__(self):
        pass

    def heightForWidth(self, font, flags, text, width):
        """
        Find the height for a given width

        :param QFont font: Font of the text
        :param int flags: Bitwise OR of the flags used like in QPainter::drawText
        :param str text: Text to be rendered
        :param float width: Width
        :return: Calculated height
        """
        pass

    def textSize(self, font, flags, text):
        """
        Returns the size, that is needed to render text

        :param QFont font: Font of the text
        :param int flags: Bitwise OR of the flags like in for QPainter::drawText
        :param str text: Text to be rendered
        :return: Calculated size
        """
        pass

    def mightRender(self, text):
        """
        Test if a string can be rendered by this text engine

        :param str text: Text to be tested
        :return: True, if it can be rendered
        """
        pass

    def textMargins(self, font):
        """
        Return margins around the texts

        The textSize might include margins around the
        text, like QFontMetrics::descent(). In situations
        where texts need to be aligned in detail, knowing
        these margins might improve the layout calculations.

        :param QFont font: Font of the text
        :return: tuple (left, right, top, bottom) representing margins
        """
        pass

    def draw(self, painter, rect, flags, text):
        """
        Draw the text in a clipping rectangle

        :param QPainter painter: Painter
        :param QRectF rect: Clipping rectangle
        :param int flags: Bitwise OR of the flags like in for QPainter::drawText()
        :param str text: Text to be rendered
        """
        pass


ASCENTCACHE = {}


def get_screen_resolution():
    """Return screen resolution: tuple of floats (DPIx, DPIy)"""
    try:
        desktop = QApplication.desktop()
        return (desktop.logicalDpiX(), desktop.logicalDpiY())
    except AttributeError:
        screen = QApplication.primaryScreen()
        return (screen.logicalDotsPerInchX(), screen.logicalDotsPerInchY())


def qwtUnscaleFont(painter):
    if painter.font().pixelSize() >= 0:
        return
    dpix, dpiy = get_screen_resolution()
    pd = painter.device()
    if pd.logicalDpiX() != dpix or pd.logicalDpiY() != dpiy:
        pixelFont = QFont(painter.font(), QApplication.desktop())
        pixelFont.setPixelSize(QFontInfo(pixelFont).pixelSize())
        painter.setFont(pixelFont)


class QwtPlainTextEngine(QwtTextEngine):
    """
    A text engine for plain texts

    `QwtPlainTextEngine` renders texts using the basic `Qt` classes
    `QPainter` and `QFontMetrics`.
    """

    def __init__(self):
        self.qrectf_max = QRectF(0, 0, QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        self._fm_cache = {}
        self._fm_cache_f = {}

    def fontmetrics(self, font):
        fid = font.toString()
        try:
            return self._fm_cache[fid]
        except KeyError:
            return self._fm_cache.setdefault(fid, QFontMetrics(font))

    def fontmetrics_f(self, font):
        fid = font.toString()
        try:
            return self._fm_cache_f[fid]
        except KeyError:
            return self._fm_cache_f.setdefault(fid, QFontMetricsF(font))

    def heightForWidth(self, font, flags, text, width):
        """
        Find the height for a given width

        :param QFont font: Font of the text
        :param int flags: Bitwise OR of the flags used like in QPainter::drawText
        :param str text: Text to be rendered
        :param float width: Width
        :return: Calculated height
        """
        fm = self.fontmetrics_f(font)
        rect = fm.boundingRect(QRectF(0, 0, width, QWIDGETSIZE_MAX), flags, text)
        return rect.height()

    def textSize(self, font, flags, text):
        """
        Returns the size, that is needed to render text

        :param QFont font: Font of the text
        :param int flags: Bitwise OR of the flags like in for QPainter::drawText
        :param str text: Text to be rendered
        :return: Calculated size
        """
        fm = self.fontmetrics_f(font)
        rect = fm.boundingRect(self.qrectf_max, flags, text)
        return rect.size()

    def effectiveAscent(self, font):
        global ASCENTCACHE
        fontKey = font.key()
        ascent = ASCENTCACHE.get(fontKey)
        if ascent is not None:
            return ascent
        return ASCENTCACHE.setdefault(fontKey, self.findAscent(font))

    def findAscent(self, font):
        dummy = "E"
        white = QColor(Qt.white)

        fm = self.fontmetrics(font)
        boundingr = fm.boundingRect(dummy)
        pm = QPixmap(boundingr.width(), boundingr.height())
        pm.fill(white)

        p = QPainter(pm)
        p.setFont(font)
        p.drawText(0, 0, pm.width(), pm.height(), 0, dummy)
        p.end()

        img = pm.toImage()

        w = pm.width()
        linebytes = w * 4
        for row in range(img.height()):
            if QT_API.startswith("pyside"):
                line = bytes(img.scanLine(row))
            else:
                line = img.scanLine(row).asstring(linebytes)
            for col in range(w):
                color = struct.unpack("I", line[col * 4 : (col + 1) * 4])[0]
                if color != white.rgb():
                    return fm.ascent() - row + 1
        return fm.ascent()

    def textMargins(self, font):
        """
        Return margins around the texts

        The textSize might include margins around the
        text, like QFontMetrics::descent(). In situations
        where texts need to be aligned in detail, knowing
        these margins might improve the layout calculations.

        :param QFont font: Font of the text
        :return: tuple (left, right, top, bottom) representing margins
        """
        left = right = 0
        fm = self.fontmetrics(font)
        top = fm.ascent() - self.effectiveAscent(font)
        bottom = fm.descent()
        return left, right, top, bottom

    def draw(self, painter, rect, flags, text):
        """
        Draw the text in a clipping rectangle

        :param QPainter painter: Painter
        :param QRectF rect: Clipping rectangle
        :param int flags: Bitwise OR of the flags like in for QPainter::drawText()
        :param str text: Text to be rendered
        """
        painter.save()
        qwtUnscaleFont(painter)
        painter.drawText(rect, flags, text)
        painter.restore()

    def mightRender(self, text):
        """
        Test if a string can be rendered by this text engine

        :param str text: Text to be tested
        :return: True, if it can be rendered
        """
        return True


class QwtRichTextEngine(QwtTextEngine):
    """
    A text engine for `Qt` rich texts

    `QwtRichTextEngine` renders `Qt` rich texts using the classes
    of the Scribe framework of `Qt`.
    """

    def __init__(self):
        pass

    def heightForWidth(self, font, flags, text, width):
        """
        Find the height for a given width

        :param QFont font: Font of the text
        :param int flags: Bitwise OR of the flags used like in QPainter::drawText
        :param str text: Text to be rendered
        :param float width: Width
        :return: Calculated height
        """
        doc = QwtRichTextDocument(text, flags, font)
        doc.setPageSize(QSizeF(width, QWIDGETSIZE_MAX))
        return doc.documentLayout().documentSize().height()

    def textSize(self, font, flags, text):
        """
        Returns the size, that is needed to render text

        :param QFont font: Font of the text
        :param int flags: Bitwise OR of the flags like in for QPainter::drawText
        :param str text: Text to be rendered
        :return: Calculated size
        """
        doc = QwtRichTextDocument(text, flags, font)
        option = doc.defaultTextOption()
        if option.wrapMode() != QTextOption.NoWrap:
            option.setWrapMode(QTextOption.NoWrap)
            doc.setDefaultTextOption(option)
            doc.adjustSize()
        return doc.size()

    def draw(self, painter, rect, flags, text):
        """
        Draw the text in a clipping rectangle

        :param QPainter painter: Painter
        :param QRectF rect: Clipping rectangle
        :param int flags: Bitwise OR of the flags like in for QPainter::drawText()
        :param str text: Text to be rendered
        """
        txt = QwtRichTextDocument(text, flags, painter.font())
        painter.save()
        unscaledRect = QRectF(rect)
        if painter.font().pixelSize() < 0:
            dpix, dpiy = get_screen_resolution()
            pd = painter.device()
            if pd.logicalDpiX() != dpix or pd.logicalDpiY() != dpiy:
                transform = QTransform()
                transform.scale(
                    dpix / float(pd.logicalDpiX()), dpiy / float(pd.logicalDpiY())
                )
                painter.setWorldTransform(transform, True)
                invtrans, _ok = transform.inverted()
                unscaledRect = invtrans.mapRect(rect)
        txt.setDefaultFont(painter.font())
        txt.setPageSize(QSizeF(unscaledRect.width(), QWIDGETSIZE_MAX))
        layout = txt.documentLayout()
        height = layout.documentSize().height()
        y = unscaledRect.y()
        if flags & Qt.AlignBottom:
            y += unscaledRect.height() - height
        elif flags & Qt.AlignVCenter:
            y += (unscaledRect.height() - height) / 2
        context = QAbstractTextDocumentLayout.PaintContext()
        context.palette.setColor(QPalette.Text, painter.pen().color())
        painter.translate(unscaledRect.x(), y)
        layout.draw(painter, context)
        painter.restore()

    def taggedText(self, text, flags):
        return taggedRichText(text, flags)

    def mightRender(self, text):
        """
        Test if a string can be rendered by this text engine

        :param str text: Text to be tested
        :return: True, if it can be rendered
        """
        try:
            return Qt.mightBeRichText(text)
        except AttributeError:
            return True

    def textMargins(self, font):
        """
        Return margins around the texts

        The textSize might include margins around the
        text, like QFontMetrics::descent(). In situations
        where texts need to be aligned in detail, knowing
        these margins might improve the layout calculations.

        :param QFont font: Font of the text
        :return: tuple (left, right, top, bottom) representing margins
        """
        return 0, 0, 0, 0


class QwtText_PrivateData(object):
    def __init__(self):
        self.renderFlags = Qt.AlignCenter
        self.borderRadius = 0
        self.borderPen = Qt.NoPen
        self.backgroundBrush = Qt.NoBrush
        self.paintAttributes = 0
        self.layoutAttributes = 0
        self.textEngine = None

        self.text = None
        self.font = None
        self.color = None


class QwtText_LayoutCache(object):
    def __init__(self):
        self.textSize = QSizeF()
        self.font = None

    def invalidate(self):
        self.textSize = QSizeF()


class QwtText(object):
    """
    A class representing a text

    A `QwtText` is a text including a set of attributes how to render it.

      - Format:

      A text might include control sequences (f.e tags) describing
      how to render it. Each format (f.e MathML, TeX, Qt Rich Text)
      has its own set of control sequences, that can be handles by
      a special `QwtTextEngine` for this format.

      - Background:

      A text might have a background, defined by a `QPen` and `QBrush`
      to improve its visibility. The corners of the background might
      be rounded.

      - Font:

      A text might have an individual font.

      - Color

      A text might have an individual color.

      - Render Flags

      Flags from `Qt.AlignmentFlag` and `Qt.TextFlag` used like in
      `QPainter.drawText()`.

    ..seealso::

        :py:meth:`qwt.text.QwtTextEngine`,
        :py:meth:`qwt.text.QwtTextLabel`

    Text formats:

      * `QwtText.AutoText`:

        The text format is determined using `QwtTextEngine.mightRender()` for
        all available text engines in increasing order > PlainText.
        If none of the text engines can render the text is rendered
        like `QwtText.PlainText`.

      * `QwtText.PlainText`:

        Draw the text as it is, using a QwtPlainTextEngine.

      * `QwtText.RichText`:

        Use the Scribe framework (Qt Rich Text) to render the text.

      * `QwtText.MathMLText`:

        Use a MathML (http://en.wikipedia.org/wiki/MathML) render engine
        to display the text. The Qwt MathML extension offers such an engine
        based on the MathML renderer of the Qt solutions package.
        To enable MathML support the following code needs to be added to the
        application::

            QwtText.setTextEngine(QwtText.MathMLText, QwtMathMLTextEngine())

      * `QwtText.TeXText`:

        Use a TeX (http://en.wikipedia.org/wiki/TeX) render engine
        to display the text ( not implemented yet ).

      * `QwtText.OtherFormat`:

        The number of text formats can be extended using `setTextEngine`.
        Formats >= `QwtText.OtherFormat` are not used by Qwt.

    Paint attributes:

      * `QwtText.PaintUsingTextFont`: The text has an individual font.
      * `QwtText.PaintUsingTextColor`: The text has an individual color.
      * `QwtText.PaintBackground`: The text has an individual background.

    Layout attributes:

      * `QwtText.MinimumLayout`:

        Layout the text without its margins. This mode is useful if a
        text needs to be aligned accurately, like the tick labels of a scale.
        If `QwtTextEngine.textMargins` is not implemented for the format
        of the text, `MinimumLayout` has no effect.

    .. py:class:: QwtText([text=None], [textFormat=None], [other=None])

        :param str text: Text content
        :param int textFormat: Text format
        :param qwt.text.QwtText other: Object to copy (text and textFormat arguments are ignored)
    """

    # enum TextFormat
    AutoText, PlainText, RichText, MathMLText, TeXText = list(range(5))
    OtherFormat = 100

    # enum PaintAttribute
    PaintUsingTextFont = 0x01
    PaintUsingTextColor = 0x02
    PaintBackground = 0x04

    # enum LayoutAttribute
    MinimumLayout = 0x01

    # Optimization: a single text engine for all QwtText objects
    # (this is not how it's implemented in Qwt6 C++ library)
    __map = {PlainText: QwtPlainTextEngine(), RichText: QwtRichTextEngine()}

    def __init__(self, text=None, textFormat=None, other=None):
        if text is None:
            text = ""
        if textFormat is None:
            textFormat = self.AutoText
        if other is not None:
            text = other
        if isinstance(text, QwtText):
            self.__data = text.__data
            self.__layoutCache = text.__layoutCache
        else:
            self.__data = QwtText_PrivateData()
            self.__data.text = text
            self.__data.textEngine = self.textEngine(text, textFormat)
            self.__layoutCache = QwtText_LayoutCache()

    @classmethod
    def make(
        cls,
        text=None,
        textformat=None,
        renderflags=None,
        font=None,
        family=None,
        pointsize=None,
        weight=None,
        color=None,
        borderradius=None,
        borderpen=None,
        brush=None,
    ):
        """
        Create and setup a new `QwtText` object (convenience function).

        :param str text: Text content
        :param int textformat: Text format
        :param int renderflags: Flags from `Qt.AlignmentFlag` and `Qt.TextFlag`
        :param font: Font
        :type font: QFont or None
        :param family: Font family (default: Helvetica)
        :type family: str or None
        :param pointsize: Font point size (default: 10)
        :type pointsize: int or None
        :param weight: Font weight (default: QFont.Normal)
        :type weight: int or None
        :param color: Pen color
        :type color: QColor or str or None
        :param borderradius: Radius for the corners of the border frame
        :type borderradius: float or None
        :param borderpen: Background pen
        :type borderpen: QPen or None
        :param brush: Background brush
        :type brush: QBrush or None

        .. seealso::

            :py:meth:`setText()`
        """
        item = cls(text=text, textFormat=textformat)
        if renderflags is not None:
            item.setRenderFlags(renderflags)
        if font is not None:
            item.setFont(font)
        elif family is not None or pointsize is not None or weight is not None:
            family = "Helvetica" if family is None else family
            pointsize = 10 if pointsize is None else pointsize
            weight = QFont.Normal if weight is None else weight
            item.setFont(QFont(family, pointsize, weight))
        if color is not None:
            item.setColor(qcolor_from_str(color, Qt.black))
        if borderradius is not None:
            item.setBorderRadius(borderradius)
        if borderpen is not None:
            item.setBorderPen(borderpen)
        if brush is not None:
            item.setBackgroundBrush(brush)
        return item

    def __eq__(self, other):
        return (
            self.__data.renderFlags == other.__data.renderFlags
            and self.__data.text == other.__data.text
            and self.__data.font == other.__data.font
            and self.__data.color == other.__data.color
            and self.__data.borderRadius == other.__data.borderRadius
            and self.__data.borderPen == other.__data.borderPen
            and self.__data.backgroundBrush == other.__data.backgroundBrush
            and self.__data.paintAttributes == other.__data.paintAttributes
            and self.__data.textEngine == other.__data.textEngine
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def isEmpty(self):
        """
        :return: True if text is empty
        """
        return len(self.text()) == 0

    def setText(self, text, textFormat=None):
        """
        Assign a new text content

        :param str text: Text content
        :param int textFormat: Text format

        .. seealso::

            :py:meth:`text()`
        """
        if textFormat is None:
            textFormat = self.AutoText
        self.__data.text = text
        self.__data.textEngine = self.textEngine(text, textFormat)
        self.__layoutCache.invalidate()

    def text(self):
        """
        :return: Text content

        .. seealso::

            :py:meth:`setText()`
        """
        return self.__data.text

    def setRenderFlags(self, renderFlags):
        """
        Change the render flags

        The default setting is `Qt.AlignCenter`

        :param int renderFlags: Bitwise OR of the flags used like in `QPainter.drawText()`

        .. seealso::

            :py:meth:`renderFlags()`,
            :py:meth:`qwt.text.QwtTextEngine.draw()`
        """
        renderFlags = Qt.AlignmentFlag(renderFlags)
        if renderFlags != self.__data.renderFlags:
            self.__data.renderFlags = renderFlags
            self.__layoutCache.invalidate()

    def renderFlags(self):
        """
        :return: Render flags

        .. seealso::

            :py:meth:`setRenderFlags()`
        """
        return self.__data.renderFlags

    def setFont(self, font):
        """
        Set the font.

        :param QFont font: Font

        .. note::

            Setting the font might have no effect, when
            the text contains control sequences for setting fonts.

        .. seealso::

            :py:meth:`font()`, :py:meth:`usedFont()`
        """
        self.__data.font = font
        self.setPaintAttribute(self.PaintUsingTextFont)

    def font(self):
        """
        :return: Return the font

        .. seealso::

            :py:meth:`setFont()`, :py:meth:`usedFont()`
        """
        return self.__data.font

    def usedFont(self, defaultFont):
        """
        Return the font of the text, if it has one.
        Otherwise return defaultFont.

        :param QFont defaultFont: Default font
        :return: Font used for drawing the text

        .. seealso::

            :py:meth:`setFont()`, :py:meth:`font()`
        """
        if self.__data.paintAttributes & self.PaintUsingTextFont:
            return self.__data.font
        return defaultFont

    def setColor(self, color):
        """
        Set the pen color used for drawing the text.

        :param QColor color: Color

        .. note::

            Setting the color might have no effect, when
            the text contains control sequences for setting colors.

        .. seealso::

            :py:meth:`color()`, :py:meth:`usedColor()`
        """
        self.__data.color = QColor(color)
        self.setPaintAttribute(self.PaintUsingTextColor)

    def color(self):
        """
        :return: Return the pen color, used for painting the text

        .. seealso::

            :py:meth:`setColor()`, :py:meth:`usedColor()`
        """
        return self.__data.color

    def usedColor(self, defaultColor):
        """
        Return the color of the text, if it has one.
        Otherwise return defaultColor.

        :param QColor defaultColor: Default color
        :return: Color used for drawing the text

        .. seealso::

            :py:meth:`setColor()`, :py:meth:`color()`
        """
        if self.__data.paintAttributes & self.PaintUsingTextColor:
            return self.__data.color
        return defaultColor

    def setBorderRadius(self, radius):
        """
        Set the radius for the corners of the border frame

        :param float radius: Radius of a rounded corner

        .. seealso::

            :py:meth:`borderRadius()`, :py:meth:`setBorderPen()`,
            :py:meth:`setBackgroundBrush()`
        """
        self.__data.borderRadius = max([0.0, radius])

    def borderRadius(self):
        """
        :return: Radius for the corners of the border frame

        .. seealso::

            :py:meth:`setBorderRadius()`, :py:meth:`borderPen()`,
            :py:meth:`backgroundBrush()`
        """
        return self.__data.borderRadius

    def setBorderPen(self, pen):
        """
        Set the background pen

        :param QPen pen: Background pen

        .. seealso::

            :py:meth:`borderPen()`, :py:meth:`setBackgroundBrush()`
        """
        self.__data.borderPen = pen
        self.setPaintAttribute(self.PaintBackground)

    def borderPen(self):
        """
        :return: Background pen

        .. seealso::

            :py:meth:`setBorderPen()`, :py:meth:`backgroundBrush()`
        """
        return self.__data.borderPen

    def setBackgroundBrush(self, brush):
        """
        Set the background brush

        :param QBrush brush: Background brush

        .. seealso::

            :py:meth:`backgroundBrush()`, :py:meth:`setBorderPen()`
        """
        self.__data.backgroundBrush = brush
        self.setPaintAttribute(self.PaintBackground)

    def backgroundBrush(self):
        """
        :return: Background brush

        .. seealso::

            :py:meth:`setBackgroundBrush()`, :py:meth:`borderPen()`
        """
        return self.__data.backgroundBrush

    def setPaintAttribute(self, attribute, on=True):
        """
        Change a paint attribute

        :param int attribute: Paint attribute
        :param bool on: On/Off

        .. note::

            Used by `setFont()`, `setColor()`, `setBorderPen()`
            and `setBackgroundBrush()`

        .. seealso::

            :py:meth:`testPaintAttribute()`
        """
        if on:
            self.__data.paintAttributes |= attribute
        else:
            self.__data.paintAttributes &= ~attribute

    def testPaintAttribute(self, attribute):
        """
        Test a paint attribute

        :param int attribute: Paint attribute
        :return: True, if attribute is enabled

        .. seealso::

            :py:meth:`setPaintAttribute()`
        """
        return self.__data.paintAttributes & attribute

    def setLayoutAttribute(self, attribute, on=True):
        """
        Change a layout attribute

        :param int attribute: Layout attribute
        :param bool on: On/Off

        .. seealso::

            :py:meth:`testLayoutAttribute()`
        """
        if on:
            self.__data.layoutAttributes |= attribute
        else:
            self.__data.layoutAttributes &= ~attribute

    def testLayoutAttribute(self, attribute):
        """
        Test a layout attribute

        :param int attribute: Layout attribute
        :return: True, if attribute is enabled

        .. seealso::

            :py:meth:`setLayoutAttribute()`
        """
        return self.__data.layoutAttributes & attribute

    def heightForWidth(self, width, defaultFont=None):
        """
        Find the height for a given width

        :param float width: Width
        :param QFont defaultFont: Font, used for the calculation if the text has no font
        :return: Calculated height
        """
        if defaultFont is None:
            defaultFont = QFont()
        font = QFont(self.usedFont(defaultFont))
        h = 0
        if self.__data.layoutAttributes & self.MinimumLayout:
            (left, right, top, bottom) = self.__data.textEngine.textMargins(font)
            h = self.__data.textEngine.heightForWidth(
                font, self.__data.renderFlags, self.__data.text, width + left + right
            )
            h -= top + bottom
        else:
            h = self.__data.textEngine.heightForWidth(
                font, self.__data.renderFlags, self.__data.text, width
            )
        return h

    def textSize(self, defaultFont):
        """
        Returns the size, that is needed to render text

        :param QFont defaultFont Font, used for the calculation if the text has no font
        :return: Caluclated size
        """
        font = QFont(self.usedFont(defaultFont))
        if (
            not self.__layoutCache.textSize.isValid()
            or self.__layoutCache.font is not font
        ):
            self.__layoutCache.textSize = self.__data.textEngine.textSize(
                font, self.__data.renderFlags, self.__data.text
            )
            self.__layoutCache.font = font
        sz = self.__layoutCache.textSize
        if self.__data.layoutAttributes & self.MinimumLayout:
            (left, right, top, bottom) = self.__data.textEngine.textMargins(font)
            sz -= QSizeF(left + right, top + bottom)
        return sz

    def draw(self, painter, rect):
        """
        Draw a text into a rectangle

        :param QPainter painter: Painter
        :param QRectF rect: Rectangle
        """
        if self.__data.paintAttributes & self.PaintBackground:
            if (
                self.__data.borderPen != Qt.NoPen
                or self.__data.backgroundBrush != Qt.NoBrush
            ):
                painter.save()
                painter.setPen(self.__data.borderPen)
                painter.setBrush(self.__data.backgroundBrush)
                if self.__data.borderRadius == 0:
                    painter.drawRect(rect)
                else:
                    painter.setRenderHint(QPainter.Antialiasing, True)
                    painter.drawRoundedRect(
                        rect, self.__data.borderRadius, self.__data.borderRadius
                    )
                painter.restore()
        painter.save()
        if self.__data.paintAttributes & self.PaintUsingTextFont:
            painter.setFont(self.__data.font)
        if self.__data.paintAttributes & self.PaintUsingTextColor:
            if self.__data.color.isValid():
                painter.setPen(self.__data.color)
        expandedRect = rect
        if self.__data.layoutAttributes & self.MinimumLayout:
            font = QFont(painter.font())
            (left, right, top, bottom) = self.__data.textEngine.textMargins(font)
            expandedRect.setTop(rect.top() - top)
            expandedRect.setBottom(rect.bottom() + bottom)
            expandedRect.setLeft(rect.left() - left)
            expandedRect.setRight(rect.right() + right)
        self.__data.textEngine.draw(
            painter, expandedRect, self.__data.renderFlags, self.__data.text
        )
        painter.restore()

    def textEngine(self, text=None, format_=None):
        """
        Find the text engine for a text format

        In case of `QwtText.AutoText` the first text engine
        (beside `QwtPlainTextEngine`) is returned, where
        `QwtTextEngine.mightRender` returns true.
        If there is none `QwtPlainTextEngine` is returned.

        If no text engine is registered for the format `QwtPlainTextEngine`
        is returned.

        :param str text: Text, needed in case of AutoText
        :param int format: Text format
        :return: Corresponding text engine
        """
        if text is None:
            return self.__map.get(format_)
        elif format_ is not None:
            if format_ == QwtText.AutoText:
                for key, engine in list(self.__map.items()):
                    if key != QwtText.PlainText:
                        if engine and engine.mightRender(text):
                            return engine
            engine = self.__map.get(format_)
            if engine is not None:
                return engine
            return self.__map[QwtText.PlainText]
        else:
            raise TypeError(
                "%s().textEngine() takes 1 or 2 argument(s) (none"
                " given)" % self.__class__.__name__
            )

    def setTextEngine(self, format_, engine):
        """
        Assign/Replace a text engine for a text format

        With setTextEngine it is possible to extend `PythonQwt` with
        other types of text formats.

        For `QwtText.PlainText` it is not allowed to assign a engine to None.

        :param int format_: Text format
        :param qwt.text.QwtTextEngine engine: Text engine

        .. seealso::

            :py:meth:`setPaintAttribute()`

        .. warning::

            Using `QwtText.AutoText` does nothing.
        """
        if format_ == QwtText.AutoText:
            return
        if format_ == QwtText.PlainText and engine is None:
            return
        self.__map.setdefault(format_, engine)


class QwtTextLabel_PrivateData(object):
    def __init__(self):
        self.indent = 4
        self.margin = 0
        self.text = QwtText()


class QwtTextLabel(QFrame):
    """
    A Widget which displays a QwtText

    .. py:class:: QwtTextLabel(parent)

        :param QWidget parent: Parent widget

    .. py:class:: QwtTextLabel([text=None], [parent=None])
        :noindex:

        :param str text: Text
        :param QWidget parent: Parent widget
    """

    def __init__(self, *args):
        if len(args) == 0:
            text, parent = None, None
        elif len(args) == 1:
            if isinstance(args[0], QWidget):
                text = None
                (parent,) = args
            else:
                parent = None
                (text,) = args
        elif len(args) == 2:
            text, parent = args
        else:
            raise TypeError(
                "%s() takes 0, 1 or 2 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )
        super(QwtTextLabel, self).__init__(parent)
        self.init()
        if text is not None:
            self.__data.text = text

    def init(self):
        self.__data = QwtTextLabel_PrivateData()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

    def setPlainText(self, text):
        """
        Interface for the designer plugin - does the same as setText()

        :param str text: Text

        .. seealso::

            :py:meth:`plainText()`
        """
        self.setText(QwtText(text))

    def plainText(self):
        """
        Interface for the designer plugin

        :return: Text as plain text

        .. seealso::

            :py:meth:`setPlainText()`
        """
        return self.__data.text.text()

    def setText(self, text, textFormat=QwtText.AutoText):
        """
        Change the label's text, keeping all other QwtText attributes

        :param text: New text
        :type text: qwt.text.QwtText or str
        :param int textFormat: Format of text

        .. seealso::

            :py:meth:`text()`
        """
        if isinstance(text, QwtText):
            self.__data.text = text
        else:
            self.__data.text.setText(text, textFormat)
        self.update()
        self.updateGeometry()

    def text(self):
        """
        :return: Return the text

        .. seealso::

            :py:meth:`setText()`
        """
        return self.__data.text

    def clear(self):
        """
        Clear the text and all `QwtText` attributes
        """
        self.__data.text = QwtText()
        self.update()
        self.updateGeometry()

    def indent(self):
        """
        :return: Label's text indent in pixels

        .. seealso::

            :py:meth:`setIndent()`
        """
        return self.__data.indent

    def setIndent(self, indent):
        """
        Set label's text indent in pixels

        :param int indent: Indentation in pixels

        .. seealso::

            :py:meth:`indent()`
        """
        if indent < 0:
            indent = 0
        self.__data.indent = indent
        self.update()
        self.updateGeometry()

    def margin(self):
        """
        :return: Label's text indent in pixels

        .. seealso::

            :py:meth:`setMargin()`
        """
        return self.__data.margin

    def setMargin(self, margin):
        """
        Set label's margin in pixels

        :param int margin: Margin in pixels

        .. seealso::

            :py:meth:`margin()`
        """
        self.__data.margin = margin
        self.update()
        self.updateGeometry()

    def sizeHint(self):
        """
        Return a size hint
        """
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        """
        Return a minimum size hint
        """
        sz = self.__data.text.textSize(self.font())
        mw = 2 * (self.frameWidth() + self.__data.margin)
        mh = mw
        indent = self.__data.indent
        if indent <= 0:
            indent = self.defaultIndent()
        if indent > 0:
            align = self.__data.text.renderFlags()
            if align & Qt.AlignLeft or align & Qt.AlignRight:
                mw += self.__data.indent
            elif align & Qt.AlignTop or align & Qt.AlignBottom:
                mh += self.__data.indent
        sz += QSizeF(mw, mh)
        return QSize(math.ceil(sz.width()), math.ceil(sz.height()))

    def heightForWidth(self, width):
        """
        :param int width: Width
        :return: Preferred height for this widget, given the width.
        """
        renderFlags = self.__data.text.renderFlags()
        indent = self.__data.indent
        if indent <= 0:
            indent = self.defaultIndent()
        width -= 2 * self.frameWidth()
        if renderFlags & Qt.AlignLeft or renderFlags & Qt.AlignRight:
            width -= indent
        height = math.ceil(self.__data.text.heightForWidth(width, self.font()))
        if renderFlags & Qt.AlignTop or renderFlags & Qt.AlignBottom:
            height += indent
        height += 2 * self.frameWidth()
        return height

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.contentsRect().contains(event.rect()):
            painter.save()
            painter.setClipRegion(event.region() & self.frameRect())
            self.drawFrame(painter)
            painter.restore()
        painter.setClipRegion(event.region() & self.contentsRect())
        self.drawContents(painter)

    def drawContents(self, painter):
        """
        Redraw the text and focus indicator

        :param QPainter painter: Painter
        """
        r = self.textRect()
        if r.isEmpty():
            return
        painter.setFont(self.font())
        painter.setPen(self.palette().color(QPalette.Active, QPalette.Text))
        self.drawText(painter, QRectF(r))
        if self.hasFocus():
            m = 2
            focusRect = self.contentsRect().adjusted(m, m, -m + 1, -m + 1)
            QwtPainter.drawFocusRect(painter, self, focusRect)

    def drawText(self, painter, textRect):
        """
        Redraw the text

        :param QPainter painter: Painter
        :param QRectF textRect: Text rectangle
        """
        self.__data.text.draw(painter, textRect)

    def textRect(self):
        """
        Calculate geometry for the text in widget coordinates

        :return: Geometry for the text
        """
        r = self.contentsRect()
        if not r.isEmpty() and self.__data.margin > 0:
            r.setRect(
                r.x() + self.__data.margin,
                r.y() + self.__data.margin,
                r.width() - 2 * self.__data.margin,
                r.height() - 2 * self.__data.margin,
            )
        if not r.isEmpty():
            indent = self.__data.indent
            if indent <= 0:
                indent = self.defaultIndent()
            if indent > 0:
                renderFlags = self.__data.text.renderFlags()
                if renderFlags & Qt.AlignLeft:
                    r.setX(r.x() + indent)
                elif renderFlags & Qt.AlignRight:
                    r.setWidth(r.width() - indent)
                elif renderFlags & Qt.AlignTop:
                    r.setY(r.y() + indent)
                elif renderFlags & Qt.AlignBottom:
                    r.setHeight(r.height() - indent)
        return r

    def defaultIndent(self):
        if self.frameWidth() <= 0:
            return 0
        if self.__data.text.testPaintAttribute(QwtText.PaintUsingTextFont):
            fnt = self.__data.text.font()
        else:
            fnt = self.font()
        return QFontMetrics(fnt).boundingRect("x").width() / 2
