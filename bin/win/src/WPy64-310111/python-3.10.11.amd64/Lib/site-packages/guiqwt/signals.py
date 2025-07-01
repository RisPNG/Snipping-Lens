# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
guiqwt.signals
--------------

In `guiqwt` version 2, the `signals` module used to contain constants defining 
the custom Qt SIGNAL objects used by `guiqwt`: the signals definition were 
gathered here to avoid misspelling signals at connect and emit sites (with 
old-style signals, any misspelled signal string would have lead to a silent 
failure of signal emission or connection).

Since version 3, to ensure PyQt5 compatibility, `guiqwt` is using only 
new-style signals and slots.

However, all signals are summarized below, in order to facilitate migration 
from `guiqwt` v2 to `guiqwt` v3.

Signals available:
    :py:data:`guiqwt.baseplot.BasePlot.SIG_ITEM_MOVED`
        Emitted by plot when an IBasePlotItem-like object was moved from 
        (x0, y0) to (x1, y1)
        
        Arguments: item object, x0, y0, x1, y1
    :py:data:`guiqwt.baseplot.BasePlot.SIG_MARKER_CHANGED`
        Emitted by plot when a `guiqwt.shapes.Marker` position changes
        
        Arguments: `guiqwt.shapes.Marker` object
    :py:data:`guiqwt.baseplot.BasePlot.SIG_AXES_CHANGED`
        Emitted by plot when a `guiqwt.shapes.Axes` position (or angle) changes
        
        Arguments: `guiqwt.shapes.Axes` object
    :py:data:`guiqwt.baseplot.BasePlot.SIG_ANNOTATION_CHANGED`
        Emitted by plot when an annotations.AnnotatedShape position changes
        
        Arguments: annotation item
    :py:data:`guiqwt.baseplot.BasePlot.SIG_RANGE_CHANGED`
        Emitted by plot when a shapes.XRangeSelection range changes
        
        Arguments: range object, lower_bound, upper_bound
    :py:data:`guiqwt.baseplot.BasePlot.SIG_ITEMS_CHANGED`
        Emitted by plot when item list has changed (item removed, added, ...)
        
        Arguments: plot
    :py:data:`guiqwt.baseplot.BasePlot.SIG_ACTIVE_ITEM_CHANGED`
        Emitted by plot when selected item has changed
        
        Arguments: plot
    :py:data:`guiqwt.baseplot.BasePlot.SIG_ITEM_REMOVED`
        Emitted by plot when an item was deleted from the itemlist or using 
        the delete item tool
        
        Arguments: removed item
    :py:data:`guiqwt.baseplot.BasePlot.SIG_ITEM_SELECTION_CHANGED`
        Emitted by plot when an item is selected

        Arguments: plot
    :py:data:`guiqwt.baseplot.BasePlot.SIG_PLOT_LABELS_CHANGED`
        Emitted (by plot) when plot's title or any axis label has changed
        
        Arguments: plot
    :py:data:`guiqwt.baseplot.BasePlot.SIG_AXIS_DIRECTION_CHANGED`
        Emitted (by plot) when any plot axis direction has changed
        
        Arguments: plot
    :py:data:`guiqwt.histogram.LevelsHistogram.SIG_VOI_CHANGED`
        Emitted by "contrast" panel's histogram when the lut range of some items
        changed (for now, this signal is for guiqwt.histogram module's internal 
        use only - the 'public' counterpart of this signal is SIG_LUT_CHANGED, 
        see below)
        
    :py:data:`guiqwt.baseplot.BasePlot.SIG_LUT_CHANGED`
        Emitted by plot when LUT has been changed by the user

        Arguments: plot
    :py:data:`guiqwt.baseplot.BasePlot.SIG_MASK_CHANGED`
        Emitted by plot when image mask has changed

        Arguments: MaskedImageItem object
    :py:data:`guiqwt.baseplot.BasePlot.SIG_CS_CURVE_CHANGED`
        Emitted by cross section plot when cross section curve data has changed
        
        Arguments: plot
    :py:data:`guiqwt.panels.PanelWidget.SIG_VISIBILITY_CHANGED`
        Emitted for example by panels when their visibility has changed

        Arguments: state (boolean)
    :py:data:`guiqwt.tools.InteractiveTool.SIG_VALIDATE_TOOL`
        Emitted by an interactive tool to notify that the tool has just been 
        "validated", i.e. <ENTER>, <RETURN> or <SPACE> was pressed

        Arguments: filter
    :py:data:`guiqwt.tools.InteractiveTool.SIG_TOOL_JOB_FINISHED`
        Emitted by an interactive tool to notify that it is finished doing its job
    :py:data:`guiqwt.tools.OpenFileTool.SIG_OPEN_FILE`
        Emitted by an open file tool
    :py:data:`guiqwt.tools.ImageMaskTool.SIG_APPLIED_MASK_TOOL`
        Emitted by the ImageMaskTool when applying the shape-defined mask
"""
