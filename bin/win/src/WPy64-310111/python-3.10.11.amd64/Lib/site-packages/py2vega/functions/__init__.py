# noqa
from .math import math_functions
from .type_checking import type_checking_functions
from .type_coercing import type_coercing_functions
from .date_time import date_time_functions
from .array import array_functions
from .string import string_functions
from .formatting import formatting_functions
from .regexp import regexp_functions
from .color import color_functions
from .object import object_functions
from .scale import scale_functions

vega_functions = (
    math_functions + type_checking_functions + type_coercing_functions +
    date_time_functions + array_functions + string_functions + formatting_functions +
    regexp_functions + color_functions + object_functions + scale_functions
)
