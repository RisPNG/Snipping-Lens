"""
Jupyter notebook interface for Param (https://github.com/ioam/param).

Given a Parameterized object, displays a box with an ipywidget for each
Parameter, allowing users to view and and manipulate Parameter values
from within a Jupyter/IPython notebook.
"""
from __future__ import absolute_import

import os
import ast
import uuid
import itertools
import json
import functools
from collections import OrderedDict

import param
import ipywidgets
from IPython.display import display, Javascript, HTML, clear_output

from . import widgets
from .widgets import wtype, apply_error_style, literal_params, Output
from .util import named_objs, get_method_owner
from .view import View, HTML as HTMLView

from param.version import Version
__version__ = str(param.Version(fpath=__file__,archive_commit="$Format:%h$",reponame="paramnb"))
del Version


def run_next_cells(n):
    if n=='all':
        n = 'NaN'
    elif n<1:
        return

    js_code = """
       var num = {0};
       var run = false;
       var current = $(this)[0];
       $.each(IPython.notebook.get_cells(), function (idx, cell) {{
          if ((cell.output_area === current) && !run) {{
             run = true;
          }} else if ((cell.cell_type == 'code') && !(num < 1) && run) {{
             cell.execute();
             num = num - 1;
          }}
       }});
    """.format(n)

    display(Javascript(js_code))


def estimate_label_width(labels):
    """
    Given a list of labels, estimate the width in pixels
    and return in a format accepted by CSS.
    Necessarily an approximation, since the font is unknown
    and is usually proportionally spaced.
    """
    max_length = max([len(l) for l in labels])
    return "{0}px".format(max(60,int(max_length*7.5)))


class Widgets(param.ParameterizedFunction):

    callback = param.Callable(default=None, doc="""
        Custom callable to execute on button press
        (if `button`) else whenever a widget is changed,
        Should accept a Parameterized object argument.""")

    view_position = param.ObjectSelector(default='below',
                                         objects=['below', 'right', 'left', 'above'],
                                         doc="""
        Layout position of any View parameter widgets.""")

    next_n = param.Parameter(default=0, doc="""
        When executing cells, integer number to execute (or 'all').
        A value of zero means not to control cell execution.""")

    on_init = param.Boolean(default=False, doc="""
        Whether to do the action normally taken (executing cells
        and/or calling a callable) when first instantiating this
        object.""")

    close_button = param.Boolean(default=False, doc="""
        Whether to show a button allowing the Widgets to be closed.""")

    button = param.Boolean(default=False, doc="""
        Whether to show a button to control cell execution.
        If false, will execute `next` cells on any widget
        value change.""")

    label_width = param.Parameter(default=estimate_label_width, doc="""
        Width of the description for parameters in the list, using any
        string specification accepted by CSS (e.g. "100px" or "50%").
        If set to a callable, will call that function using the list of
        all labels to get the value.""")

    tooltips = param.Boolean(default=True, doc="""
        Whether to add tooltips to the parameter names to show their
        docstrings.""")

    show_labels = param.Boolean(default=True)

    display_threshold = param.Number(default=0,precedence=-10,doc="""
        Parameters with precedence below this value are not displayed.""")

    default_precedence = param.Number(default=1e-8,precedence=-10,doc="""
        Precedence value to use for parameters with no declared precedence.
        By default, zero predecence is available for forcing some parameters
        to the top of the list, and other values above the default_precedence
        values can be used to sort or group parameters arbitrarily.""")

    initializer = param.Callable(default=None, doc="""
        User-supplied function that will be called on initialization,
        usually to update the default Parameter values of the
        underlying parameterized object.""")

    layout = param.ObjectSelector(default='column',
                                  objects=['row','column'],doc="""
        Whether to lay out the buttons as a row or a column.""")

    continuous_update = param.Boolean(default=False, doc="""
        If true, will continuously update the next_n and/or callback,
        if any, as a slider widget is dragged.""")

    def __call__(self, parameterized, plots=[],  **params):
        self.p = param.ParamOverrides(self, params)
        if self.p.initializer:
            self.p.initializer(parameterized)

        self._id = uuid.uuid4().hex
        self._widgets = {}
        self.parameterized = parameterized

        widgets, views = self.widgets()
        layout = ipywidgets.Layout(display='flex', flex_flow=self.p.layout)
        if self.p.close_button:
            layout.border = 'solid 1px'

        widget_box = ipywidgets.VBox(children=widgets, layout=layout)
        plot_outputs = tuple(Output() for p in plots)
        if views or plots:
            outputs = tuple(views.values()) + plot_outputs
            view_box = ipywidgets.VBox(children=outputs, layout=layout)
            layout = self.p.view_position
            if layout in ['below', 'right']:
                children = [widget_box, view_box]
            else:
                children = [view_box, widget_box]
            box = ipywidgets.VBox if layout in ['below', 'above'] else ipywidgets.HBox
            widget_box = box(children=children)

        display(widget_box)
        self._widget_box = widget_box

        self._display_handles = {}
        # Render defined View parameters
        for pname, view in views.items():
            p_obj = self.parameterized.params(pname)
            value = getattr(self.parameterized, pname)
            if value is None:
                continue
            handle = self._update_trait(pname, p_obj.renderer(value))
            if handle:
                self._display_handles[pname] = handle

        # Render supplied plots
        for p, o in zip(plots, plot_outputs):
            with o:
                display(p)

        # Keeps track of changes between button presses
        self._changed = {}

        if self.p.on_init:
            self.execute()


    def _update_trait(self, p_name, p_value, widget=None):
        p_obj = self.parameterized.params(p_name)
        widget = self._widgets[p_name] if widget is None else widget
        if isinstance(p_value, tuple):
            p_value, size = p_value

            if isinstance(size, tuple) and len(size) == 2:
                if isinstance(widget, ipywidgets.Image):
                    widget.width = size[0]
                    widget.height = size[1]
                else:
                    widget.layout.min_width = '%dpx' % size[0]
                    widget.layout.min_height = '%dpx' % size[1]

        if isinstance(widget, Output):
            if isinstance(p_obj, HTMLView) and p_value:
                p_value = HTML(p_value)
            with widget:
                # clear_output required for JLab support
                # in future handle.update(p_value) should be sufficient
                handle = self._display_handles.get(p_name)
                if handle:
                    clear_output(wait=True)
                    handle.display(p_value)
                else:
                    handle = display(p_value, display_id=p_name+self._id)
                    self._display_handles[p_name] = handle
        else:
            widget.value = p_value


    def _make_widget(self, p_name):
        p_obj = self.parameterized.params(p_name)
        widget_class = wtype(p_obj)

        value = getattr(self.parameterized, p_name)

        # For ObjectSelector, pick first from objects if no default;
        # see https://github.com/ioam/param/issues/164
        if hasattr(p_obj,'objects') and len(p_obj.objects)>0 and value is None:
            value = p_obj.objects[0]
            if isinstance(p_obj,param.ListSelector):
                value = [value]
            setattr(self.parameterized, p_name, value)

        kw = dict(value=value)
        if p_obj.doc:
            kw['tooltip'] = p_obj.doc

        if isinstance(p_obj, param.Action):
            def action_cb(button):
                getattr(self.parameterized, p_name)(self.parameterized)
            kw['value'] = action_cb

        kw['name'] = p_name

        kw['continuous_update']=self.p.continuous_update

        if hasattr(p_obj, 'callbacks'):
            kw.pop('value', None)

        if hasattr(p_obj, 'get_range'):
            kw['options'] = named_objs(p_obj.get_range().items())

        if hasattr(p_obj, 'get_soft_bounds'):
            kw['min'], kw['max'] = p_obj.get_soft_bounds()

        if hasattr(p_obj,'is_instance') and p_obj.is_instance:
            kw['options'][kw['value'].__class__.__name__]=kw['value']

        w = widget_class(**kw)

        if hasattr(p_obj, 'callbacks') and value is not None:
            self._update_trait(p_name, p_obj.renderer(value), w)

        def change_event(event):
            new_values = event['new']
            error = False
            # Apply literal evaluation to values
            if (isinstance(w, ipywidgets.Text) and isinstance(p_obj, literal_params)):
                try:
                    new_values = ast.literal_eval(new_values)
                except:
                    error = 'eval'
            elif hasattr(p_obj,'is_instance') and p_obj.is_instance and isinstance(new_values,type):
                # results in new instance each time non-default option
                # is selected; could consider caching.
                try:
                    # awkward: support ParameterizedFunction
                    new_values = new_values.instance() if hasattr(new_values,'instance') else new_values()
                except:
                    error = 'instantiate'

            # If no error during evaluation try to set parameter
            if not error:
                try:
                    setattr(self.parameterized, p_name, new_values)
                except ValueError:
                    error = 'validation'

            # Style widget to denote error state
            apply_error_style(w, error)

            if not error and not self.p.button:
                self.execute({p_name: new_values})
            else:
                self._changed[p_name] = new_values

        if hasattr(p_obj, 'callbacks'):
            p_obj.callbacks[id(self.parameterized)] = functools.partial(self._update_trait, p_name)
        else:
            w.observe(change_event, 'value')

        # Hack ; should be part of Widget classes
        if hasattr(p_obj,"path"):
            def path_change_event(event):
                new_values = event['new']
                p_obj = self.parameterized.params(p_name)
                p_obj.path = new_values
                p_obj.update()

                # Update default value in widget, ensuring it's always a legal option
                selector = self._widgets[p_name].children[1]
                defaults = p_obj.default
                if not issubclass(type(defaults),list):
                    defaults = [defaults]
                selector.options.update(named_objs(zip(defaults,defaults)))
                selector.value=p_obj.default
                selector.options=named_objs(p_obj.get_range().items())

                if p_obj.objects and not self.p.button:
                    self.execute({p_name:selector.value})

            path_w = ipywidgets.Text(value=p_obj.path)
            path_w.observe(path_change_event, 'value')
            w = ipywidgets.VBox(children=[path_w,w],
                                layout=ipywidgets.Layout(margin='0'))

        return w


    def widget(self, param_name):
        """Get widget for param_name"""
        if param_name not in self._widgets:
            self._widgets[param_name] = self._make_widget(param_name)
        return self._widgets[param_name]


    def execute(self, changed={}):
        run_next_cells(self.p.next_n)
        if self.p.callback is not None:
            if get_method_owner(self.p.callback) is self.parameterized:
                self.p.callback(**changed)
            else:
                self.p.callback(self.parameterized, **changed)


    # Define some settings :)
    preamble = """
        <style>
          .widget-dropdown .dropdown-menu { width: 100% }
          .widget-select-multiple select { min-height: 100px; min-width: 300px;}
        </style>
        """

    label_format = """<div title="{2}" style="padding: 5px; width: {0};
                      text-align: right;">{1}</div>"""

    def helptip(self,obj):
        """Return HTML code formatting a tooltip if help is available"""
        helptext = obj.__doc__
        return "" if (not self.p.tooltips or not helptext) else helptext


    def widgets(self):
        """Return name,widget boxes for all parameters (i.e., a property sheet)"""

        params = self.parameterized.params().items()
        key_fn = lambda x: x[1].precedence if x[1].precedence is not None else self.p.default_precedence
        sorted_precedence = sorted(params, key=key_fn)
        outputs = [k for k, p in sorted_precedence if isinstance(p, View)]
        filtered = [(k,p) for (k,p) in sorted_precedence
                    if ((p.precedence is None) or (p.precedence >= self.p.display_threshold))
                    and k not in outputs]
        groups = itertools.groupby(filtered, key=key_fn)
        sorted_groups = [sorted(grp) for (k,grp) in groups]
        ordered_params = [el[0] for group in sorted_groups for el in group]

        # Format name specially
        widgets = [ipywidgets.HTML(self.preamble +
            '<div class="ttip"><b>{0}</b>'.format(self.parameterized.name)+"</div>")]

        label_width=self.p.label_width
        if callable(label_width):
            label_width = label_width(self.parameterized.params().keys())

        def format_name(pname):
            p = self.parameterized.params(pname)
            # omit name for buttons, which already show the name on the button
            name = "" if issubclass(type(p),param.Action) else pname
            return ipywidgets.HTML(self.label_format.format(label_width, name, self.helptip(p)))

        if self.p.show_labels:
            widgets += [ipywidgets.HBox(children=[format_name(pname),self.widget(pname)])
                        for pname in ordered_params]
        else:
            widgets += [self.widget(pname) for pname in ordered_params]

        if self.p.close_button:
            close_button = ipywidgets.Button(description="Close")
            # TODO: what other cleanup should be done?
            close_button.on_click(lambda _: self._widget_box.close())
            widgets.append(close_button)


        if self.p.button and not (self.p.callback is None and self.p.next_n==0):
            label = 'Run %s' % self.p.next_n if self.p.next_n != 'all' else "Run"
            display_button = ipywidgets.Button(description=label)
            def click_cb(button):
                # Execute and clear changes since last button press
                try:
                    self.execute(self._changed)
                except Exception as e:
                    self._changed.clear()
                    raise e
                self._changed.clear()
            display_button.on_click(click_cb)
            widgets.append(display_button)

        outputs = OrderedDict([(pname, self.widget(pname)) for pname in outputs])
        return widgets, outputs


# TODO: this is awkward. An alternative would be to import Widgets in
# widgets.py only at the point(s) where Widgets is needed rather than
# at the top level (to avoid circular imports). Probably some
# reorganization would be better, though.
widgets.editor = functools.partial(Widgets,close_button=True)


class JSONInit(param.Parameterized):
    """
    Callable that can be passed to Widgets.initializer to set Parameter
    values using JSON. There are three approaches that may be used:

    1. If the json_file argument is specified, this takes precedence.
    2. The JSON file path can be specified via an environment variable.
    3. The JSON can be read directly from an environment variable.

    Here is an easy example of setting such an environment variable on
    the commandline:

    PARAMNB_INIT='{"p1":5}' jupyter notebook

    This addresses any JSONInit instances that are inspecting the
    default environment variable called PARAMNB_INIT, instructing it to set
    the 'p1' parameter to 5.
    """

    varname = param.String(default='PARAMNB_INIT', doc="""
        The name of the environment variable containing the JSON
        specification.""")

    target = param.String(default=None, doc="""
        Optional key in the JSON specification dictionary containing the
        desired parameter values.""")

    json_file = param.String(default=None, doc="""
        Optional path to a JSON file containing the parameter settings.""")


    def __call__(self, parameterized):

        warnobj = param.main if isinstance(parameterized, type) else parameterized
        param_class = (parameterized if isinstance(parameterized, type)
                       else parameterized.__class__)


        target = self.target if self.target is not None else param_class.__name__

        env_var = os.environ.get(self.varname, None)
        if env_var is None and self.json_file is None: return

        if self.json_file or env_var.endswith('.json'):
            try:
                fname = self.json_file if self.json_file else env_var
                spec = json.load(open(os.path.abspath(fname), 'r'))
            except:
                warnobj.warning('Could not load JSON file %r' % spec)
        else:
            spec = json.loads(env_var)

        if not isinstance(spec, dict):
            warnobj.warning('JSON parameter specification must be a dictionary.')
            return

        if target in spec:
            params = spec[target]
        else:
            params = spec

        for name, value in params.items():
           try:
               parameterized.set_param(**{name:value})
           except ValueError as e:
               warnobj.warning(str(e))


##
# make pyct's example/data commands available if possible
from functools import partial
try:
    from pyct.cmd import copy_examples as _copy, fetch_data as _fetch, examples as _examples
    copy_examples = partial(_copy, 'paramnb')
    fetch_data = partial(_fetch, 'paramnb')
    examples = partial(_examples, 'paramnb')
except ImportError:
    def _missing_cmd(*args,**kw): return("install pyct to enable this command (e.g. `conda install pyct` or `pip install pyct[cmd]`)")
    _copy = _fetch = _examples = _missing_cmd
    def _err(): raise ValueError(_missing_cmd())
    fetch_data = copy_examples = examples = _err
del partial, _examples, _copy, _fetch
##
