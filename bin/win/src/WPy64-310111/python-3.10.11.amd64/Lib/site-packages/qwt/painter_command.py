# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# Copyright (c) 2002 Uwe Rathmann, for the original C++ code
# Copyright (c) 2015 Pierre Raybaut, for the Python translation/optimization
# (see LICENSE file for more details)

"""
QwtPainterCommand
-----------------

.. autoclass:: QwtPainterCommand
   :members:
"""

from qtpy.QtGui import QPainterPath, QPaintEngine
import copy


class PixmapData(object):
    def __init__(self):
        self.rect = None
        self.pixmap = None
        self.subRect = None


class ImageData(object):
    def __init__(self):
        self.rect = None
        self.image = None
        self.subRect = None
        self.flags = None


class StateData(object):
    def __init__(self):
        self.flags = None
        self.pen = None
        self.brush = None
        self.brushOrigin = None
        self.backgroundBrush = None
        self.backgroundMode = None
        self.font = None
        self.matrix = None
        self.transform = None
        self.clipOperation = None
        self.clipRegion = None
        self.clipPath = None
        self.isClipEnabled = None
        self.renderHints = None
        self.compositionMode = None
        self.opacity = None


class QwtPainterCommand(object):
    """
    `QwtPainterCommand` represents the attributes of a paint operation
    how it is used between `QPainter` and `QPaintDevice`

    It is used by :py:class:`qwt.graphic.QwtGraphic` to record and replay
    paint operations

    .. seealso::

        :py:meth:`qwt.graphic.QwtGraphic.commands()`


    .. py:class:: QwtPainterCommand()

        Construct an invalid command

    .. py:class:: QwtPainterCommand(path)
        :noindex:

        Copy constructor

        :param QPainterPath path: Source

    .. py:class:: QwtPainterCommand(rect, pixmap, subRect)
        :noindex:

        Constructor for Pixmap paint operation

        :param QRectF rect: Target rectangle
        :param QPixmap pixmap: Pixmap
        :param QRectF subRect: Rectangle inside the pixmap

    .. py:class:: QwtPainterCommand(rect, image, subRect, flags)
        :noindex:

        Constructor for Image paint operation

        :param QRectF rect: Target rectangle
        :param QImage image: Image
        :param QRectF subRect: Rectangle inside the image
        :param Qt.ImageConversionFlags flags: Conversion flags

    .. py:class:: QwtPainterCommand(state)
        :noindex:

        Constructor for State paint operation

        :param QPaintEngineState state: Paint engine state
    """

    # enum Type
    Invalid = -1
    Path, Pixmap, Image, State = list(range(4))

    def __init__(self, *args):
        if len(args) == 0:
            self.__type = self.Invalid
        elif len(args) == 1:
            (arg,) = args
            if isinstance(arg, QPainterPath):
                path = arg
                self.__type = self.Path
                self.__path = QPainterPath(path)
            elif isinstance(arg, QwtPainterCommand):
                other = arg
                self.copy(other)
            else:
                state = arg
                self.__type = self.State
                self.__stateData = StateData()
                self.__stateData.flags = state.state()
                if self.__stateData.flags & QPaintEngine.DirtyPen:
                    self.__stateData.pen = state.pen()
                if self.__stateData.flags & QPaintEngine.DirtyBrush:
                    self.__stateData.brush = state.brush()
                if self.__stateData.flags & QPaintEngine.DirtyBrushOrigin:
                    self.__stateData.brushOrigin = state.brushOrigin()
                if self.__stateData.flags & QPaintEngine.DirtyFont:
                    self.__stateData.font = state.font()
                if self.__stateData.flags & QPaintEngine.DirtyBackground:
                    self.__stateData.backgroundMode = state.backgroundMode()
                    self.__stateData.backgroundBrush = state.backgroundBrush()
                if self.__stateData.flags & QPaintEngine.DirtyTransform:
                    self.__stateData.transform = state.transform()
                if self.__stateData.flags & QPaintEngine.DirtyClipEnabled:
                    self.__stateData.isClipEnabled = state.isClipEnabled()
                if self.__stateData.flags & QPaintEngine.DirtyClipRegion:
                    self.__stateData.clipRegion = state.clipRegion()
                    self.__stateData.clipOperation = state.clipOperation()
                if self.__stateData.flags & QPaintEngine.DirtyClipPath:
                    self.__stateData.clipPath = state.clipPath()
                    self.__stateData.clipOperation = state.clipOperation()
                if self.__stateData.flags & QPaintEngine.DirtyHints:
                    self.__stateData.renderHints = state.renderHints()
                if self.__stateData.flags & QPaintEngine.DirtyCompositionMode:
                    self.__stateData.compositionMode = state.compositionMode()
                if self.__stateData.flags & QPaintEngine.DirtyOpacity:
                    self.__stateData.opacity = state.opacity()
        elif len(args) == 3:
            rect, pixmap, subRect = args
            self.__type = self.Pixmap
            self.__pixmapData = PixmapData()
            self.__pixmapData.rect = rect
            self.__pixmapData.pixmap = pixmap
            self.__pixmapData.subRect = subRect
        elif len(args) == 4:
            rect, image, subRect, flags = args
            self.__type = self.Image
            self.__imageData = ImageData()
            self.__imageData.rect = rect
            self.__imageData.image = image
            self.__imageData.subRect = subRect
            self.__imageData.flags = flags
        else:
            raise TypeError(
                "%s() takes 0, 1, 3 or 4 argument(s) (%s given)"
                % (self.__class__.__name__, len(args))
            )

    def copy(self, other):
        self.__type = other.__type
        if other.__type == self.Path:
            self.__path = QPainterPath(other.__path)
        elif other.__type == self.Pixmap:
            self.__pixmapData = copy.deepcopy(other.__pixmapData)
        elif other.__type == self.Image:
            self.__imageData = copy.deepcopy(other.__imageData)
        elif other.__type == self.State:
            self.__stateData == copy.deepcopy(other.__stateData)

    def reset(self):
        self.__type = self.Invalid

    def type(self):
        return self.__type

    def path(self):
        return self.__path

    def pixmapData(self):
        return self.__pixmapData

    def imageData(self):
        return self.__imageData

    def stateData(self):
        return self.__stateData
