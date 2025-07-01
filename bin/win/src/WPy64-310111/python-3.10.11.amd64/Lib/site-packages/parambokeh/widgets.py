import decimal

import param
from param.parameterized import classlist

from bokeh.layouts import column
from bokeh.models.widgets import (
    Button, TextInput, Div, Slider, CheckboxGroup,
    DatePicker, MultiSelect, Select, RangeSlider
)

from .util import as_unicode
from .view import Plot, HTML


def TextWidget(*args, **kw):
    """Forces a parameter value to be text"""
    kw['value'] = str(kw['value'])
    kw.pop('options', None)
    return TextInput(*args,**kw)

def StaticText(*args, **kw):
    kw['text'] = '<b>{title}</b>: {value}'.format(title=kw.pop('title'),
                                                  value=as_unicode(kw.pop('value')))
    return Div(*args, **kw)

def Checkbox(*args, **kw):
    val = kw.pop('value')
    kw['active'] = [0] if val else []
    kw['labels'] = [kw.pop('title')]
    return CheckboxGroup(*args, **kw)

def ButtonWidget(*args, **kw):
    kw['label'] = kw.pop('title')
    kw.pop('value') # button doesn't have value (value attached as click callback)
    return Button(*args, **kw)

# TODO: make a composite box/slider widget; slider only appears if
# there's a range.

# TODO: There's confusion about the thing being represented and the
# thing doing the representing. I will rework the widgets more
# comprehensively once we have things working as-is in bokeh 0.12.10.

def FloatSlider(*args,**kw):
    if kw.get('start') is None or kw.get('end') is None:
        kw.pop('start',None)
        kw.pop('end',None)
        kw.pop('step',None)
        kw['value'] = str(kw['value'])
        return TextInput(*args,**kw)
    else:
        ###
        # TODO: some improvement will come from composite box/optional
        # slider widget - will be able to get appropriate step from
        # user-entered value.
        p = decimal.Decimal(str(kw['value'])).as_tuple()[2]
        kw['step'] = 10**p
        #kw['format'] = "0[.]" + "0".zfill(-p)
        kw['format'] = "0[.]" + "".rjust(-p,'0')
        ###
        if kw.get('value', None) is None:
            kw['value'] = kw['start']
        return Slider(*args, **kw)


def IntSlider(*args, **kw):
    if kw.get('start') is None or kw.get('end') is None:
        kw.pop('start',None)
        kw.pop('end',None)
        kw.pop('step',None)
        kw['value'] = str(kw['value'])
        return TextInput(*args,**kw)
    else:
        kw['step'] = 1
        if kw.get('value', None) is None:
            kw['value'] = kw['start']
        return Slider(*args, **kw)

def DateWidget(*args, **kw):
    kw['min_date'] = kw.pop('start')
    kw['max_date'] = kw.pop('end')
    return DatePicker(*args,**kw)

def RangeWidget(*args, **kw):
    if not 'start' in kw and 'end' in kw:
        kw['start'], kw['end'] = kw['value']
    elif 'value' not in kw:
        kw['value'] = (kw['start'], kw['end'])
    # TODO: should use param definition of integer (when that is
    # itself fixed...).
    if isinstance(kw['start'], int) and isinstance(kw['end'], int):
        kw['step'] = 1
    return RangeSlider(*args, **kw)

def PlotWidget(*args, **kw):
    return column(name=kw['name'])

def HTMLWidget(*args, **kw):
    return Div(name=kw['name'])


ptype2wtype = {
    param.Parameter:     TextWidget,
    param.Dict:          TextWidget,
    param.Selector:      Select,
    param.Boolean:       Checkbox,
    param.Number:        FloatSlider,
    param.Integer:       IntSlider,
    param.Range:         RangeWidget,
    param.ListSelector:  MultiSelect,
    param.Action:        ButtonWidget,
    param.Date:          DateWidget,
    Plot:                PlotWidget,
    HTML:                HTMLWidget

}

def wtype(pobj):
    if pobj.constant: # Ensure constant parameters cannot be edited
        return StaticText
    for t in classlist(type(pobj))[::-1]:
        if t in ptype2wtype:
            return ptype2wtype[t]


# Define parameters which should be evaluated using ast.literal_eval
literal_params = (param.Dict, param.List, param.Tuple, param.Number)
