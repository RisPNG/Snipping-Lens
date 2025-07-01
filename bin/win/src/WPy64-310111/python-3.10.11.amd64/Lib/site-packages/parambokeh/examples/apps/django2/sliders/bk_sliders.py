# cut down version of https://github.com/bokeh/bokeh/blob/master/examples/app/sliders.py

from bokeh.layouts import row
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure

import parambokeh

from .sinewave import SineWave


def app(doc):

    x,y = SineWave()
    source = ColumnDataSource(data=dict(x=x, y=y))

    import numpy as np # see TODO below about ranges
    plot = figure(plot_height=400, plot_width=400,
                  tools="crosshair,pan,reset,save,wheel_zoom",
                  x_range=[0, 4*np.pi], y_range=[-2.5, 2.5])
    plot.line('x', 'y', source=source, line_width=3, line_alpha=0.6)

    def update_sinewave(sw,**kw):
        x,y = sw()
        source.data = dict(x=x, y=y)
        # TODO couldn't figure out how to update ranges
        #plot.x_range.start,plot.x_range.end=pobj.x_range
        #plot.y_range.start,plot.y_range.end=pobj.y_range
    
    parambokeh.Widgets(SineWave, mode='server', doc=doc, callback=update_sinewave)
    doc.add_root(row(plot, width=800))
