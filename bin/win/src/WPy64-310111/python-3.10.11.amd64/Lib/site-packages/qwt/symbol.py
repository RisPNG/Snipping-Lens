# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtSymbol
---------

.. autoclass:: QwtSymbol
   :members:
"""

import math

from qwt.graphic import QwtGraphic
from qwt.painter import QwtPainter

from qtpy.QtGui import (
    QPainter,
    QTransform,
    QPixmap,
    QPen,
    QPolygonF,
    QPainterPath,
    QBrush,
)
from qtpy.QtCore import QSize, QRect, QPointF, QRectF, QSizeF, Qt, QPoint, QLineF
from qtpy.QtSvg import QSvgRenderer


class QwtTriangle(object):

    # enum Type
    Left, Right, Up, Down = list(range(4))


def qwtPathGraphic(path, pen, brush):
    graphic = QwtGraphic()
    graphic.setRenderHint(QwtGraphic.RenderPensUnscaled)
    painter = QPainter(graphic)
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.drawPath(path)
    painter.end()
    return graphic


def qwtScaleBoundingRect(graphic, size):
    scaledSize = QSize(size)
    if scaledSize.isEmpty():
        scaledSize = graphic.defaultSize()
    sz = graphic.controlPointRect().size()
    sx = 1.0
    if sz.width() > 0.0:
        sx = scaledSize.width() / sz.width()
    sy = 1.0
    if sz.height() > 0.0:
        sy = scaledSize.height() / sz.height()
    return graphic.scaledBoundingRect(sx, sy)


def qwtDrawPixmapSymbols(painter, points, numPoints, symbol):
    size = symbol.size()
    if size.isEmpty():
        size = symbol.pixmap().size()
    transform = QTransform(painter.transform())
    if transform.isScaling():
        r = QRect(0, 0, size.width(), size.height())
        size = transform.mapRect(r).size()
    pm = QPixmap(symbol.pixmap())
    if pm.size() != size:
        pm = pm.scaled(size)
    pinPoint = QPointF(0.5 * size.width(), 0.5 * size.height())
    if symbol.isPinPointEnabled():
        pinPoint = symbol.pinPoint()
    painter.resetTransform()
    for pos in points:
        pos = QPointF(transform.map(pos)) - pinPoint
        QwtPainter.drawPixmap(painter, QRect(pos.toPoint(), pm.size()), pm)


def qwtDrawSvgSymbols(painter, points, numPoints, renderer, symbol):
    if renderer is None or not renderer.isValid():
        return
    viewBox = QRectF(renderer.viewBoxF())
    if viewBox.isEmpty():
        return
    sz = QSizeF(symbol.size())
    if not sz.isValid():
        sz = viewBox.size()
    sx = sz.width() / viewBox.width()
    sy = sz.height() / viewBox.height()
    pinPoint = QPointF(viewBox.center())
    if symbol.isPinPointEnabled():
        pinPoint = symbol.pinPoint()
    dx = sx * (pinPoint.x() - viewBox.left())
    dy = sy * (pinPoint.y() - viewBox.top())
    for pos in points:
        x = pos.x() - dx
        y = pos.y() - dy
        renderer.render(painter, QRectF(x, y, sz.width(), sz.height()))


def qwtDrawGraphicSymbols(painter, points, numPoint, graphic, symbol):
    pointRect = QRectF(graphic.controlPointRect())
    if pointRect.isEmpty():
        return
    sx = 1.0
    sy = 1.0
    sz = symbol.size()
    if sz.isValid():
        sx = sz.width() / pointRect.width()
        sy = sz.height() / pointRect.height()
    pinPoint = QPointF(pointRect.center())
    if symbol.isPinPointEnabled():
        pinPoint = symbol.pinPoint()
    transform = QTransform(painter.transform())
    for pos in points:
        tr = QTransform(transform)
        tr.translate(pos.x(), pos.y())
        tr.scale(sx, sy)
        tr.translate(-pinPoint.x(), -pinPoint.y())
        painter.setTransform(tr)
        graphic.render(painter)
    painter.setTransform(transform)


def qwtDrawEllipseSymbols(painter, points, numPoints, symbol):
    painter.setBrush(symbol.brush())
    painter.setPen(symbol.pen())
    size = symbol.size()
    sw = size.width()
    sh = size.height()
    sw2 = 0.5 * size.width()
    sh2 = 0.5 * size.height()
    for pos in points:
        x = pos.x()
        y = pos.y()
        r = QRectF(x - sw2, y - sh2, sw, sh)
        painter.drawEllipse(r)


def qwtDrawRectSymbols(painter, points, numPoints, symbol):
    size = symbol.size()
    pen = QPen(symbol.pen())
    pen.setJoinStyle(Qt.MiterJoin)
    painter.setPen(pen)
    painter.setBrush(symbol.brush())
    painter.setRenderHint(QPainter.Antialiasing, False)
    sw = size.width()
    sh = size.height()
    sw2 = 0.5 * size.width()
    sh2 = 0.5 * size.height()
    for pos in points:
        x = pos.x()
        y = pos.y()
        r = QRectF(x - sw2, y - sh2, sw, sh)
        painter.drawRect(r)


def qwtDrawDiamondSymbols(painter, points, numPoints, symbol):
    size = symbol.size()
    pen = QPen(symbol.pen())
    pen.setJoinStyle(Qt.MiterJoin)
    painter.setPen(pen)
    painter.setBrush(symbol.brush())
    for pos in points:
        x1 = pos.x() - 0.5 * size.width()
        y1 = pos.y() - 0.5 * size.height()
        x2 = x1 + size.width()
        y2 = y1 + size.height()
        polygon = QPolygonF()
        polygon.append(QPointF(pos.x(), y1))
        polygon.append(QPointF(x1, pos.y()))
        polygon.append(QPointF(pos.x(), y2))
        polygon.append(QPointF(x2, pos.y()))
        painter.drawPolygon(polygon)


def qwtDrawTriangleSymbols(painter, type, points, numPoint, symbol):
    size = symbol.size()
    pen = QPen(symbol.pen())
    pen.setJoinStyle(Qt.MiterJoin)
    painter.setPen(pen)
    painter.setBrush(symbol.brush())
    sw2 = 0.5 * size.width()
    sh2 = 0.5 * size.height()
    for pos in points:
        x = pos.x()
        y = pos.y()
        x1 = x - sw2
        x2 = x1 + size.width()
        y1 = y - sh2
        y2 = y1 + size.height()
        if type == QwtTriangle.Left:
            triangle = [QPointF(x2, y1), QPointF(x1, y), QPointF(x2, y2)]
        elif type == QwtTriangle.Right:
            triangle = [QPointF(x1, y1), QPointF(x2, y), QPointF(x1, y2)]
        elif type == QwtTriangle.Up:
            triangle = [QPointF(x1, y2), QPointF(x, y1), QPointF(x2, y2)]
        elif type == QwtTriangle.Down:
            triangle = [QPointF(x1, y1), QPointF(x, y2), QPointF(x2, y1)]
        else:
            raise TypeError("Unknown triangle type %s" % type)
        painter.drawPolygon(QPolygonF(triangle))


def qwtDrawLineSymbols(painter, orientations, points, numPoints, symbol):
    size = symbol.size()
    pen = QPen(symbol.pen())
    if pen.width() > 1:
        pen.setCapStyle(Qt.FlatCap)
    painter.setPen(pen)
    painter.setRenderHint(QPainter.Antialiasing, False)
    sw = size.width()
    sh = size.height()
    sw2 = 0.5 * size.width()
    sh2 = 0.5 * size.height()
    for pos in points:
        if orientations & Qt.Horizontal:
            x = round(pos.x()) - sw2
            y = round(pos.y())
            painter.drawLine(QLineF(x, y, x + sw, y))
        if orientations & Qt.Vertical:
            x = round(pos.x())
            y = round(pos.y()) - sh2
            painter.drawLine(QLineF(x, y, x, y + sh))


def qwtDrawXCrossSymbols(painter, points, numPoints, symbol):
    size = symbol.size()
    pen = QPen(symbol.pen())
    if pen.width() > 1:
        pen.setCapStyle(Qt.FlatCap)
    painter.setPen(pen)
    sw = size.width()
    sh = size.height()
    sw2 = 0.5 * size.width()
    sh2 = 0.5 * size.height()
    for pos in points:
        x1 = pos.x() - sw2
        x2 = x1 + sw
        y1 = pos.y() - sh2
        y2 = y1 + sh
        painter.drawLine(QLineF(x1, y1, x2, y2))
        painter.drawLine(QLineF(x2, y1, x1, y2))


def qwtDrawStar1Symbols(painter, points, numPoints, symbol):
    size = symbol.size()
    painter.setPen(symbol.pen())
    sqrt1_2 = math.sqrt(0.5)
    r = QRectF(0, 0, size.width(), size.height())
    for pos in points:
        r.moveCenter(pos.toPoint())
        c = QPointF(r.center())
        d1 = r.width() / 2.0 * (1.0 - sqrt1_2)
        painter.drawLine(
            QLineF(r.left() + d1, r.top() + d1, r.right() - d1, r.bottom() - d1)
        )
        painter.drawLine(
            QLineF(r.left() + d1, r.bottom() - d1, r.right() - d1, r.top() + d1)
        )
        painter.drawLine(QLineF(c.x(), r.top(), c.x(), r.bottom()))
        painter.drawLine(QLineF(r.left(), c.y(), r.right(), c.y()))


def qwtDrawStar2Symbols(painter, points, numPoints, symbol):
    pen = QPen(symbol.pen())
    if pen.width() > 1:
        pen.setCapStyle(Qt.FlatCap)
    pen.setJoinStyle(Qt.MiterJoin)
    painter.setPen(pen)
    painter.setBrush(symbol.brush())
    cos30 = math.cos(30 * math.pi / 180.0)
    dy = 0.25 * symbol.size().height()
    dx = 0.5 * symbol.size().width() * cos30 / 3.0
    for pos in points:
        x = pos.x()
        y = pos.y()
        x1 = x - 3 * dx
        y1 = y - 2 * dy
        x2 = x1 + 1 * dx
        x3 = x1 + 2 * dx
        x4 = x1 + 3 * dx
        x5 = x1 + 4 * dx
        x6 = x1 + 5 * dx
        x7 = x1 + 6 * dx
        y2 = y1 + 1 * dy
        y3 = y1 + 2 * dy
        y4 = y1 + 3 * dy
        y5 = y1 + 4 * dy
        star = [
            QPointF(x4, y1),
            QPointF(x5, y2),
            QPointF(x7, y2),
            QPointF(x6, y3),
            QPointF(x7, y4),
            QPointF(x5, y4),
            QPointF(x4, y5),
            QPointF(x3, y4),
            QPointF(x1, y4),
            QPointF(x2, y3),
            QPointF(x1, y2),
            QPointF(x3, y2),
        ]
        painter.drawPolygon(QPolygonF(star))


def qwtDrawHexagonSymbols(painter, points, numPoints, symbol):
    painter.setBrush(symbol.brush())
    painter.setPen(symbol.pen())
    cos30 = math.cos(30 * math.pi / 180.0)
    dx = 0.5 * (symbol.size().width() - cos30)
    dy = 0.25 * symbol.size().height()
    for pos in points:
        x = pos.x()
        y = pos.y()
        x1 = x - dx
        y1 = y - 2 * dy
        x2 = x1 + 1 * dx
        x3 = x1 + 2 * dx
        y2 = y1 + 1 * dy
        y3 = y1 + 3 * dy
        y4 = y1 + 4 * dy
        hexa = [
            QPointF(x2, y1),
            QPointF(x3, y2),
            QPointF(x3, y3),
            QPointF(x2, y4),
            QPointF(x1, y3),
            QPointF(x1, y2),
        ]
        painter.drawPolygon(QPolygonF(hexa))


class QwtSymbol_PrivateData(object):
    def __init__(self, st, br, pn, sz):
        self.style = st
        self.size = sz
        self.brush = br
        self.pen = pn
        self.isPinPointEnabled = False
        self.pinPoint = QPointF()

        class Path(object):
            def __init__(self):
                self.path = QPainterPath()
                self.graphic = QwtGraphic()

        self.path = Path()

        class Pixmap(object):
            def __init__(self):
                self.pixmap = QPixmap()

        self.pixmap = None  # Pixmap()

        class Graphic(object):
            def __init__(self):
                self.graphic = QwtGraphic()

        self.graphic = Graphic()

        class SVG(object):
            def __init__(self):
                self.renderer = QSvgRenderer()

        self.svg = SVG()

        class PaintCache(object):
            def __init__(self):
                self.policy = 0
                self.pixmap = None  # QPixmap()

        self.cache = PaintCache()


class QwtSymbol(object):
    """
    A class for drawing symbols

    Symbol styles:

      * `QwtSymbol.NoSymbol`: No Style. The symbol cannot be drawn.
      * `QwtSymbol.Ellipse`: Ellipse or circle
      * `QwtSymbol.Rect`: Rectangle
      * `QwtSymbol.Diamond`: Diamond
      * `QwtSymbol.Triangle`: Triangle pointing upwards
      * `QwtSymbol.DTriangle`: Triangle pointing downwards
      * `QwtSymbol.UTriangle`: Triangle pointing upwards
      * `QwtSymbol.LTriangle`: Triangle pointing left
      * `QwtSymbol.RTriangle`: Triangle pointing right
      * `QwtSymbol.Cross`: Cross (+)
      * `QwtSymbol.XCross`: Diagonal cross (X)
      * `QwtSymbol.HLine`: Horizontal line
      * `QwtSymbol.VLine`: Vertical line
      * `QwtSymbol.Star1`: X combined with +
      * `QwtSymbol.Star2`: Six-pointed star
      * `QwtSymbol.Hexagon`: Hexagon
      * `QwtSymbol.Path`: The symbol is represented by a painter path, where
        the origin (0, 0) of the path coordinate system is mapped to the
        position of the symbol

        ..seealso::

            :py:meth:`setPath()`, :py:meth:`path()`
      * `QwtSymbol.Pixmap`: The symbol is represented by a pixmap.
        The pixmap is centered or aligned to its pin point.

        ..seealso::

            :py:meth:`setPinPoint()`
      * `QwtSymbol.Graphic`: The symbol is represented by a graphic.
        The graphic is centered or aligned to its pin point.

        ..seealso::

            :py:meth:`setPinPoint()`
      * `QwtSymbol.SvgDocument`: The symbol is represented by a SVG graphic.
        The graphic is centered or aligned to its pin point.

        ..seealso::

            :py:meth:`setPinPoint()`
      * `QwtSymbol.UserStyle`: Styles >= `QwtSymbol.UserStyle` are reserved
        for derived classes of `QwtSymbol` that overload `drawSymbols()` with
        additional application specific symbol types.

    Cache policies:

        Depending on the render engine and the complexity of the
        symbol shape it might be faster to render the symbol
        to a pixmap and to paint this pixmap.

        F.e. the raster paint engine is a pure software renderer
        where in cache mode a draw operation usually ends in
        raster operation with the the backing store, that are usually
        faster, than the algorithms for rendering polygons.
        But the opposite can be expected for graphic pipelines
        that can make use of hardware acceleration.

        The default setting is AutoCache

        ..seealso::

            :py:meth:`setCachePolicy()`, :py:meth:`cachePolicy()`

        .. note::

            The policy has no effect, when the symbol is painted
            to a vector graphics format (PDF, SVG).

        .. warning::

            Since Qt 4.8 raster is the default backend on X11

        Valid cache policies:

          * `QwtSymbol.NoCache`: Don't use a pixmap cache
          * `QwtSymbol.Cache`: Always use a pixmap cache
          * `QwtSymbol.AutoCache`: Use a cache when the symbol is rendered
            with the software renderer (`QPaintEngine.Raster`)

    .. py:class:: QwtSymbol([style=QwtSymbol.NoSymbol])

        The symbol is constructed with gray interior,
        black outline with zero width, no size and style 'NoSymbol'.

        :param int style: Symbol Style

    .. py:class:: QwtSymbol(style, brush, pen, size)
        :noindex:

        :param int style: Symbol Style
        :param QBrush brush: Brush to fill the interior
        :param QPen pen: Outline pen
        :param QSize size: Size

    .. py:class:: QwtSymbol(path, brush, pen)
        :noindex:

        :param QPainterPath path: Painter path
        :param QBrush brush: Brush to fill the interior
        :param QPen pen: Outline pen

    .. seealso::

        :py:meth:`setPath()`, :py:meth:`setBrush()`,
        :py:meth:`setPen()`, :py:meth:`setSize()`
    """

    # enum Style
    Style = int
    NoSymbol = -1
    (
        Ellipse,
        Rect,
        Diamond,
        Triangle,
        DTriangle,
        UTriangle,
        LTriangle,
        RTriangle,
        Cross,
        XCross,
        HLine,
        VLine,
        Star1,
        Star2,
        Hexagon,
        Path,
        Pixmap,
        Graphic,
        SvgDocument,
    ) = list(range(19))
    UserStyle = 1000

    # enum CachePolicy
    NoCache, Cache, AutoCache = list(range(3))

    def __init__(self, *args):
        if len(args) in (0, 1):
            if args:
                (style,) = args
            else:
                style = QwtSymbol.NoSymbol
            self.__data = QwtSymbol_PrivateData(
                style, QBrush(Qt.gray), QPen(Qt.black, 0), QSize()
            )
        elif len(args) == 4:
            style, brush, pen, size = args
            self.__data = QwtSymbol_PrivateData(style, brush, pen, size)
        elif len(args) == 3:
            path, brush, pen = args
            self.__data = QwtSymbol_PrivateData(QwtSymbol.Path, brush, pen, QSize())
            self.setPath(path)
        else:
            raise TypeError(
                "%s() takes 1, 3, or 4 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )

    @classmethod
    def make(
        cls,
        style=None,
        brush=None,
        pen=None,
        size=None,
        path=None,
        pixmap=None,
        graphic=None,
        svgdocument=None,
        pinpoint=None,
    ):
        """
        Create and setup a new `QwtSymbol` object (convenience function).

        :param style: Symbol Style
        :type style: int or None
        :param brush: Brush to fill the interior
        :type brush: QBrush or None
        :param pen: Outline pen
        :type pen: QPen or None
        :param size: Size
        :type size: QSize or None
        :param path: Painter path
        :type path: QPainterPath or None
        :param path: Painter path
        :type path: QPainterPath or None
        :param pixmap: Pixmap as symbol
        :type pixmap: QPixmap or None
        :param graphic: Graphic
        :type graphic: qwt.graphic.QwtGraphic or None
        :param svgdocument: SVG icon as symbol

        .. seealso::

            :py:meth:`setPixmap()`, :py:meth:`setGraphic()`, :py:meth:`setPath()`
        """
        style = QwtSymbol.NoSymbol if style is None else style
        brush = QBrush(Qt.gray) if brush is None else QBrush(brush)
        pen = QPen(Qt.black, 0) if pen is None else QPen(pen)
        size = QSize() if size is None else size
        if not isinstance(size, QSize):
            if isinstance(size, tuple) and len(size) == 2:
                size = QSize(size[0], size[1])
            else:
                raise TypeError("Invalid size %r" % size)
        item = cls(style, brush, pen, size)
        if path is not None:
            item.setPath(path)
        elif pixmap is not None:
            item.setPixmap(pixmap)
        elif graphic is not None:
            item.setGraphic(graphic)
        elif svgdocument is not None:
            item.setSvgDocument(svgdocument)
        if pinpoint is not None:
            item.setPinPoint(pinpoint)
        return item

    def setCachePolicy(self, policy):
        """
        Change the cache policy

        The default policy is AutoCache

        :param int policy: Cache policy

        .. seealso::

            :py:meth:`cachePolicy()`
        """
        if self.__data.cache.policy != policy:
            self.__data.cache.policy = policy
            self.invalidateCache()

    def cachePolicy(self):
        """
        :return: Cache policy

        .. seealso::

            :py:meth:`setCachePolicy()`
        """
        return self.__data.cache.policy

    def setPath(self, path):
        """
        Set a painter path as symbol

        The symbol is represented by a painter path, where the
        origin (0, 0) of the path coordinate system is mapped to
        the position of the symbol.

        When the symbol has valid size the painter path gets scaled
        to fit into the size. Otherwise the symbol size depends on
        the bounding rectangle of the path.

        The following code defines a symbol drawing an arrow::

            from qtpy.QtGui import QApplication, QPen, QPainterPath, QTransform
            from qtpy.QtCore import Qt, QPointF
            from qwt import QwtPlot, QwtPlotCurve, QwtSymbol
            import numpy as np

            app = QApplication([])

            # --- Construct custom symbol ---

            path = QPainterPath()
            path.moveTo(0, 8)
            path.lineTo(0, 5)
            path.lineTo(-3, 5)
            path.lineTo(0, 0)
            path.lineTo(3, 5)
            path.lineTo(0, 5)

            transform = QTransform()
            transform.rotate(-30.0)
            path = transform.map(path)

            pen = QPen(Qt.black, 2 );
            pen.setJoinStyle(Qt.MiterJoin)

            symbol = QwtSymbol()
            symbol.setPen(pen)
            symbol.setBrush(Qt.red)
            symbol.setPath(path)
            symbol.setPinPoint(QPointF(0., 0.))
            symbol.setSize(10, 14)

            # --- Test it within a simple plot ---

            curve = QwtPlotCurve()
            curve_pen = QPen(Qt.blue)
            curve_pen.setStyle(Qt.DotLine)
            curve.setPen(curve_pen)
            curve.setSymbol(symbol)
            x = np.linspace(0, 10, 10)
            curve.setData(x, np.sin(x))

            plot = QwtPlot()
            curve.attach(plot)
            plot.resize(600, 300)
            plot.replot()
            plot.show()

            app.exec_()

        .. image:: /images/symbol_path_example.png

        :param QPainterPath path: Painter path

        .. seealso::

            :py:meth:`path()`, :py:meth:`setSize()`
        """
        self.__data.style = QwtSymbol.Path
        self.__data.path.path = path
        self.__data.path.graphic.reset()

    def path(self):
        """
        :return: Painter path for displaying the symbol

        .. seealso::

            :py:meth:`setPath()`
        """
        return self.__data.path.path

    def setPixmap(self, pixmap):
        """
        Set a pixmap as symbol

        :param QPixmap pixmap: Pixmap

        .. seealso::

            :py:meth:`pixmap()`, :py:meth:`setGraphic()`

        .. note::

            The `style()` is set to `QwtSymbol.Pixmap`

        .. note::

            `brush()` and `pen()` have no effect
        """
        self.__data.style = QwtSymbol.Pixmap
        self.__data.pixmap.pixmap = pixmap

    def pixmap(self):
        """
        :return: Assigned pixmap

        .. seealso::

            :py:meth:`setPixmap()`
        """
        return self.__data.pixmap.pixmap

    def setGraphic(self, graphic):
        """
        Set a graphic as symbol

        :param qwt.graphic.QwtGraphic graphic: Graphic

        .. seealso::

            :py:meth:`graphic()`, :py:meth:`setPixmap()`

        .. note::

            The `style()` is set to `QwtSymbol.Graphic`

        .. note::

            `brush()` and `pen()` have no effect
        """
        self.__data.style = QwtSymbol.Graphic
        self.__data.graphic.graphic = graphic

    def graphic(self):
        """
        :return: Assigned graphic

        .. seealso::

            :py:meth:`setGraphic()`
        """
        return self.__data.graphic.graphic

    def setSvgDocument(self, svgDocument):
        """
        Set a SVG icon as symbol

        :param svgDocument: SVG icon

        .. seealso::

            :py:meth:`setGraphic()`, :py:meth:`setPixmap()`

        .. note::

            The `style()` is set to `QwtSymbol.SvgDocument`

        .. note::

            `brush()` and `pen()` have no effect
        """
        self.__data.style = QwtSymbol.SvgDocument
        if self.__data.svg.renderer is None:
            self.__data.svg.renderer = QSvgRenderer()
        self.__data.svg.renderer.load(svgDocument)

    def setSize(self, *args):
        """
        Specify the symbol's size

        .. py:method:: setSize(width, [height=-1])
            :noindex:

            :param int width: Width
            :param int height: Height

        .. py:method:: setSize(size)
            :noindex:

            :param QSize size: Size

        .. seealso::

            :py:meth:`size()`
        """
        if len(args) == 2:
            width, height = args
            if width >= 0 and height < 0:
                height = width
            self.setSize(QSize(width, height))
        elif len(args) == 1:
            if isinstance(args[0], QSize):
                (size,) = args
                if size.isValid() and size != self.__data.size:
                    self.__data.size = size
                    self.invalidateCache()
            else:
                (width,) = args
                self.setSize(width, -1)
        else:
            raise TypeError(
                "%s().setSize() takes 1 or 2 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )

    def size(self):
        """
        :return: Size

        .. seealso::

            :py:meth:`setSize()`
        """
        return self.__data.size

    def setBrush(self, brush):
        """
        Assign a brush

        The brush is used to draw the interior of the symbol.

        :param QBrush brush: Brush

        .. seealso::

            :py:meth:`brush()`
        """
        if brush != self.__data.brush:
            self.__data.brush = brush
            self.invalidateCache()
            if self.__data.style == QwtSymbol.Path:
                self.__data.path.graphic.reset()

    def brush(self):
        """
        :return: Brush

        .. seealso::

            :py:meth:`setBrush()`
        """
        return self.__data.brush

    def setPen(self, *args):
        """
        Build and/or assign a pen, depending on the arguments.

        .. py:method:: setPen(color, width, style)
            :noindex:

            Build and assign a pen

            In Qt5 the default pen width is 1.0 ( 0.0 in Qt4 ) what makes it
            non cosmetic (see `QPen.isCosmetic()`). This method signature has
            been introduced to hide this incompatibility.

            :param QColor color: Pen color
            :param float width: Pen width
            :param Qt.PenStyle style: Pen style

        .. py:method:: setPen(pen)
            :noindex:

            Assign a pen

            :param QPen pen: New pen

        .. seealso::

            :py:meth:`pen()`, :py:meth:`brush()`
        """
        if len(args) == 3:
            color, width, style = args
            self.setPen(QPen(color, width, style))
        elif len(args) == 1:
            (pen,) = args
            if pen != self.__data.pen:
                self.__data.pen = pen
                self.invalidateCache()
                if self.__data.style == QwtSymbol.Path:
                    self.__data.path.graphic.reset()
        else:
            raise TypeError(
                "%s().setPen() takes 1 or 3 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )

    def pen(self):
        """
        :return: Pen

        .. seealso::

            :py:meth:`setPen()`, :py:meth:`brush()`
        """
        return self.__data.pen

    def setColor(self, color):
        """
        Set the color of the symbol

        Change the color of the brush for symbol types with a filled area.
        For all other symbol types the color will be assigned to the pen.

        :param QColor color: Color

        .. seealso::

            :py:meth:`setPen()`, :py:meth:`setBrush()`,
            :py:meth:`brush()`, :py:meth:`pen()`
        """
        if self.__data.style in (
            QwtSymbol.Ellipse,
            QwtSymbol.Rect,
            QwtSymbol.Diamond,
            QwtSymbol.Triangle,
            QwtSymbol.UTriangle,
            QwtSymbol.DTriangle,
            QwtSymbol.RTriangle,
            QwtSymbol.LTriangle,
            QwtSymbol.Star2,
            QwtSymbol.Hexagon,
        ):
            if self.__data.brush.color() != color:
                self.__data.brush.setColor(color)
                self.invalidateCache()
        elif self.__data.style in (
            QwtSymbol.Cross,
            QwtSymbol.XCross,
            QwtSymbol.HLine,
            QwtSymbol.VLine,
            QwtSymbol.Star1,
        ):
            if self.__data.pen.color() != color:
                self.__data.pen.setColor(color)
                self.invalidateCache()
        else:
            if self.__data.brush.color() != color or self.__data.pen.color() != color:
                self.invalidateCache()
            self.__data.brush.setColor(color)
            self.__data.pen.setColor(color)

    def setPinPoint(self, pos, enable=True):
        """
        Set and enable a pin point

        The position of a complex symbol is not always aligned to its center
        ( f.e an arrow, where the peak points to a position ). The pin point
        defines the position inside of a Pixmap, Graphic, SvgDocument
        or PainterPath symbol where the represented point has to
        be aligned to.

        :param QPointF pos: Position
        :enable bool enable: En/Disable the pin point alignment

        .. seealso::

            :py:meth:`pinPoint()`, :py:meth:`setPinPointEnabled()`
        """
        if self.__data.pinPoint != pos:
            self.__data.pinPoint = pos
            if self.__data.isPinPointEnabled:
                self.invalidateCache()
        self.setPinPointEnabled(enable)

    def pinPoint(self):
        """
        :return: Pin point

        .. seealso::

            :py:meth:`setPinPoint()`, :py:meth:`setPinPointEnabled()`
        """
        return self.__data.pinPoint

    def setPinPointEnabled(self, on):
        """
        En/Disable the pin point alignment

        :param bool on: Enabled, when on is true

        .. seealso::

            :py:meth:`setPinPoint()`, :py:meth:`isPinPointEnabled()`
        """
        if self.__data.isPinPointEnabled != on:
            self.__data.isPinPointEnabled = on
            self.invalidateCache()

    def isPinPointEnabled(self):
        """
        :return: True, when the pin point translation is enabled

        .. seealso::

            :py:meth:`setPinPoint()`, :py:meth:`setPinPointEnabled()`
        """
        return self.__data.isPinPointEnabled

    def drawSymbols(self, painter, points, numPoints=None):
        """
        Render an array of symbols

        Painting several symbols is more effective than drawing symbols
        one by one, as a couple of layout calculations and setting of pen/brush
        can be done once for the complete array.

        :param QPainter painter: Painter
        :param QPolygonF points: Positions of the symbols in screen coordinates
        """
        # TODO: remove argument numPoints (not necessary in `PythonQwt`)
        if numPoints is not None and numPoints <= 0:
            return
        painter.save()
        self.renderSymbols(painter, points, numPoints)
        painter.restore()

    def drawSymbol(self, painter, point_or_rect):
        """
        Draw the symbol into a rectangle

        The symbol is painted centered and scaled into the target rectangle.
        It is always painted uncached and the pin point is ignored.

        This method is primarily intended for drawing a symbol to the legend.

        :param QPainter painter: Painter
        :param point_or_rect: Position or target rectangle of the symbol in screen coordinates
        :type point_or_rect: QPointF or QPoint or QRectF
        """
        if isinstance(point_or_rect, (QPointF, QPoint)):
            # drawSymbol( QPainter *, const QPointF & )
            self.drawSymbols(painter, [point_or_rect])
            return
        # drawSymbol( QPainter *, const QRectF & )
        rect = point_or_rect
        assert isinstance(rect, QRectF)
        if self.__data.style == QwtSymbol.NoSymbol:
            return
        if self.__data.style == QwtSymbol.Graphic:
            self.__data.graphic.graphic.render(painter, rect, Qt.KeepAspectRatio)
        elif self.__data.style == QwtSymbol.Path:
            if self.__data.path.graphic.isNull():
                self.__data.path.graphic = qwtPathGraphic(
                    self.__data.path.path, self.__data.pen, self.__data.brush
                )
            self.__data.path.graphic.render(painter, rect, Qt.KeepAspectRatio)
            return
        elif self.__data.style == QwtSymbol.SvgDocument:
            if self.__data.svg.renderer is not None:
                scaledRect = QRectF()
                sz = QSizeF(self.__data.svg.renderer.viewBoxF().size())
                if not sz.isEmpty():
                    sz.scale(rect.size(), Qt.KeepAspectRatio)
                    scaledRect.setSize(sz)
                    scaledRect.moveCenter(rect.center())
                else:
                    scaledRect = rect
                self.__data.svg.renderer.render(painter, scaledRect)
        else:
            br = QRect(self.boundingRect())
            ratio = min([rect.width() / br.width(), rect.height() / br.height()])
            painter.save()
            painter.translate(rect.center())
            painter.scale(ratio, ratio)
            isPinPointEnabled = self.__data.isPinPointEnabled
            self.__data.isPinPointEnabled = False
            pos = QPointF()
            self.renderSymbols(painter, pos, 1)
            self.__data.isPinPointEnabled = isPinPointEnabled
            painter.restore()

    def renderSymbols(self, painter, points, numPoints=None):
        """
        Render the symbol to series of points

        :param QPainter painter: Painter
        :param point_or_rect: Positions of the symbols
        """
        # TODO: remove argument numPoints (not necessary in `PythonQwt`)
        try:
            assert numPoints is None
        except AssertionError:
            raise RuntimeError(
                "argument numPoints is not implemented " "in `PythonQwt`"
            )
        if self.__data.style == QwtSymbol.Ellipse:
            qwtDrawEllipseSymbols(painter, points, numPoints, self)
        elif self.__data.style == QwtSymbol.Rect:
            qwtDrawRectSymbols(painter, points, numPoints, self)
        elif self.__data.style == QwtSymbol.Diamond:
            qwtDrawDiamondSymbols(painter, points, numPoints, self)
        elif self.__data.style == QwtSymbol.Cross:
            qwtDrawLineSymbols(
                painter, Qt.Horizontal | Qt.Vertical, points, numPoints, self
            )
        elif self.__data.style == QwtSymbol.XCross:
            qwtDrawXCrossSymbols(painter, points, numPoints, self)
        elif self.__data.style in (QwtSymbol.Triangle, QwtSymbol.UTriangle):
            qwtDrawTriangleSymbols(painter, QwtTriangle.Up, points, numPoints, self)
        elif self.__data.style == QwtSymbol.DTriangle:
            qwtDrawTriangleSymbols(painter, QwtTriangle.Down, points, numPoints, self)
        elif self.__data.style == QwtSymbol.RTriangle:
            qwtDrawTriangleSymbols(painter, QwtTriangle.Right, points, numPoints, self)
        elif self.__data.style == QwtSymbol.LTriangle:
            qwtDrawTriangleSymbols(painter, QwtTriangle.Left, points, numPoints, self)
        elif self.__data.style == QwtSymbol.HLine:
            qwtDrawLineSymbols(painter, Qt.Horizontal, points, numPoints, self)
        elif self.__data.style == QwtSymbol.VLine:
            qwtDrawLineSymbols(painter, Qt.Vertical, points, numPoints, self)
        elif self.__data.style == QwtSymbol.Star1:
            qwtDrawStar1Symbols(painter, points, numPoints, self)
        elif self.__data.style == QwtSymbol.Star2:
            qwtDrawStar2Symbols(painter, points, numPoints, self)
        elif self.__data.style == QwtSymbol.Hexagon:
            qwtDrawHexagonSymbols(painter, points, numPoints, self)
        elif self.__data.style == QwtSymbol.Path:
            if self.__data.path.graphic.isNull():
                self.__data.path.graphic = qwtPathGraphic(
                    self.__data.path.path, self.__data.pen, self.__data.brush
                )
            qwtDrawGraphicSymbols(
                painter, points, numPoints, self.__data.path.graphic, self
            )
        elif self.__data.style == QwtSymbol.Pixmap:
            qwtDrawPixmapSymbols(painter, points, numPoints, self)
        elif self.__data.style == QwtSymbol.Graphic:
            qwtDrawGraphicSymbols(
                painter, points, numPoints, self.__data.graphic.graphic, self
            )
        elif self.__data.style == QwtSymbol.SvgDocument:
            qwtDrawSvgSymbols(
                painter, points, numPoints, self.__data.svg.renderer, self
            )

    def boundingRect(self):
        """
        Calculate the bounding rectangle for a symbol at position (0,0).

        :return: Bounding rectangle
        """
        rect = QRectF()
        pinPointTranslation = False
        if self.__data.style in (QwtSymbol.Ellipse, QwtSymbol.Rect, QwtSymbol.Hexagon):
            pw = 0.0
            if self.__data.pen.style() != Qt.NoPen:
                pw = max([self.__data.pen.widthF(), 1.0])
            rect.setSize(QSizeF(self.__data.size) + QSizeF(pw, pw))
            rect.moveCenter(QPointF(0.0, 0.0))
        elif self.__data.style in (
            QwtSymbol.XCross,
            QwtSymbol.Diamond,
            QwtSymbol.Triangle,
            QwtSymbol.UTriangle,
            QwtSymbol.DTriangle,
            QwtSymbol.RTriangle,
            QwtSymbol.LTriangle,
            QwtSymbol.Star1,
            QwtSymbol.Star2,
        ):
            pw = 0.0
            if self.__data.pen.style() != Qt.NoPen:
                pw = max([self.__data.pen.widthF(), 1.0])
            rect.setSize(QSizeF(self.__data.size) + QSizeF(2 * pw, 2 * pw))
            rect.moveCenter(QPointF(0.0, 0.0))
        elif self.__data.style == QwtSymbol.Path:
            if self.__data.path.graphic.isNull():
                self.__data.path.graphic = qwtPathGraphic(
                    self.__data.path.path, self.__data.pen, self.__data.brush
                )
            rect = qwtScaleBoundingRect(self.__data.path.graphic, self.__data.size)
            pinPointTranslation = True
        elif self.__data.style == QwtSymbol.Pixmap:
            if self.__data.size.isEmpty():
                rect.setSize(self.__data.pixmap.pixmap.size())
            else:
                rect.setSize(self.__data.size)
            pinPointTranslation = True
        elif self.__data.style == QwtSymbol.Graphic:
            rect = qwtScaleBoundingRect(self.__data.graphic.graphic, self.__data.size)
            pinPointTranslation = True
        elif self.__data.style == QwtSymbol.SvgDocument:
            if self.__data.svg.renderer is not None:
                rect = self.__data.svg.renderer.viewBoxF()
            if self.__data.size.isValid() and not rect.isEmpty():
                sz = QSizeF(rect.size())
                sx = self.__data.size.width() / sz.width()
                sy = self.__data.size.height() / sz.height()
                transform = QTransform()
                transform.scale(sx, sy)
                rect = transform.mapRect(rect)
            pinPointTranslation = True
        else:
            rect.setSize(self.__data.size)
            rect.moveCenter(QPointF(0.0, 0.0))
        if pinPointTranslation:
            pinPoint = QPointF(0.0, 0.0)
            if self.__data.isPinPointEnabled:
                pinPoint = rect.center() - self.__data.pinPoint
            rect.moveCenter(pinPoint)
        r = QRect()
        r.setLeft(math.floor(rect.left()))
        r.setTop(math.floor(rect.top()))
        r.setRight(math.floor(rect.right()))
        r.setBottom(math.floor(rect.bottom()))
        if self.__data.style != QwtSymbol.Pixmap:
            r.adjust(-1, -1, 1, 1)
        return r

    def invalidateCache(self):
        """
        Invalidate the cached symbol pixmap

        The symbol invalidates its cache, whenever an attribute is changed
        that has an effect ob how to display a symbol. In case of derived
        classes with individual styles (>= `QwtSymbol.UserStyle`) it
        might be necessary to call invalidateCache() for attributes
        that are relevant for this style.

        .. seealso::

            :py:meth:`setCachePolicy()`, :py:meth:`drawSymbols()`
        """
        if self.__data.cache.pixmap is not None:
            self.__data.cache.pixmap = QPixmap()

    def setStyle(self, style):
        """
        Specify the symbol style

        :param int style: Style

        .. seealso::

            :py:meth:`style()`
        """
        if self.__data.style != style:
            self.__data.style = style
            self.invalidateCache()

    def style(self):
        """
        :return: Current symbol style

        .. seealso::

            :py:meth:`setStyle()`
        """
        return self.__data.style
