##### existing parameterized class

import param
import datetime as dt

class Example(param.Parameterized):
    """Example Parameterized class"""
    log = []
    x            = param.Number(default=1.0,bounds=(0,100),precedence=0,doc="X position")
    write_to_log = param.Action(lambda obj: obj.log.append((dt.datetime.now(),obj.x)), 
                                doc="""Record value of x and timestamp.""",precedence=1)

##### create a properties frame for Example

import parambokeh
w = parambokeh.Widgets(Example, mode='server')


##### display value of Example.log in bokeh app

from bokeh.io import curdoc
from bokeh.layouts import layout
from bokeh.models import Div

log = Div()

def update_log():
    log.text = "<br />".join(["%s -- %s"%(t[0].strftime('%H:%M:%S.%f'),t[1]) for t in Example.log])

curdoc().add_periodic_callback(update_log, 200)

layout = layout([log])
curdoc().add_root(layout)
curdoc().title = "simple parambokeh + bokeh server example"
