#!/usr/bin/env python3

import warnings

from .settings import _feature_flag


class _moved_beta_feature(object):
    def __init__(self, new_cls, orig_name=None):
        self.new_cls = new_cls
        self.orig_name = orig_name if orig_name is not None else "linear_operator.settings.{}".format(new_cls.__name__)

    def __call__(self, *args, **kwargs):
        warnings.warn(
            "`{}` has moved to `linear_operator.settings.{}`.".format(self.orig_name, self.new_cls.__name__),
            DeprecationWarning,
        )
        return self.new_cls(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.new_cls, name)


class default_preconditioner(_feature_flag):
    """
    Add a diagonal correction to scalable inducing point methods
    """

    pass


__all__ = ["default_preconditioner"]
