import param

class View(param.Parameter):
    """
    View parameters hold displayable output, they may have a callback,
    which is called when a new value is set on the parameter.
    Additionally they allow supplying a renderer function which renders
    the display output. The renderer function should return the
    appropriate output for the View parameter (e.g. HTML or PNG data),
    and may optionally supply the desired size of the viewport.
    """

    __slots__ = ['callbacks', 'renderer']

    def __init__(self, default=None, callback=None, renderer=None, **kwargs):
        self.callbacks = {}
        self.renderer = (lambda x: x) if renderer is None else renderer
        super(View, self).__init__(default, **kwargs)

    def __set__(self, obj, val):
        super(View, self).__set__(obj, val)
        obj_id = id(obj)
        if obj_id in self.callbacks:
            self.callbacks[obj_id](self.renderer(val))


class HTML(View):
    """
    HTML is a View parameter that allows displaying HTML output.
    """


class Image(View):
    """
    Image is a View parameter that allows displaying PNG bytestrings.
    """
