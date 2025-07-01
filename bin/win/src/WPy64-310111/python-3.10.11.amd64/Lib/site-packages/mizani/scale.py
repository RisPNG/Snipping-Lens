"""
According to *On the theory of scales of measurement* by **S.S. Stevens**,
scales can be classified in four ways -- *nominal*, *ordinal*,
*interval* and *ratio*. Using current(2016) terminology, *nominal* data
is made up of unordered categories, *ordinal* data is made up of ordered
categories and the two can be classified as *discrete*. On the other hand
both *interval* and *ratio* data are *continuous*.

The scale classes below show how the rest of the Mizani package can be
used to implement the two categories of scales. The key tasks are
*training* and *mapping* and these correspond to the **train** and
**map** methods.

To train a scale on data means, to make the scale learn the limits of
the data. This is elaborate (or worthy of a dedicated method) for two
reasons:

    - *Practical* -- data may be split up across more than one object,
      yet all will be represented by a single scale.
    - *Conceptual* -- training is a key action that may need to be inserted
      into multiple locations of the data processing pipeline before a
      graphic can be created.

To map data onto a scale means, to associate data values with
values(potential readings) on a scale. This is perhaps the most important
concept unpinning a scale.

The **apply** methods are simple examples of how to put it all together.
"""
import numpy as np
import pandas as pd
import pandas.api.types as pdtypes

from .bounds import censor, rescale
from .utils import (
    CONTINUOUS_KINDS,
    DISCRETE_KINDS,
    get_categories,
    match,
    min_max,
)

__all__ = ["scale_continuous", "scale_discrete"]


class scale_continuous:
    """
    Continuous scale
    """

    @classmethod
    def apply(cls, x, palette, na_value=None, trans=None):
        """
        Scale data continuously

        Parameters
        ----------
        x : array_like
            Continuous values to scale
        palette : callable ``f(x)``
            Palette to use
        na_value : object
            Value to use for missing values.
        trans : trans
            How to transform the data before scaling. If
            ``None``, no transformation is done.

        Returns
        -------
        out : array_like
            Scaled values
        """
        if trans is not None:
            x = trans.transform(x)

        limits = cls.train(x)
        return cls.map(x, palette, limits, na_value)

    @classmethod
    def train(cls, new_data, old=None):
        """
        Train a continuous scale

        Parameters
        ----------
        new_data : array_like
            New values
        old : array_like
            Old range. Most likely a tuple of length 2.

        Returns
        -------
        out : tuple
            Limits(range) of the scale
        """
        if not len(new_data):
            return old

        if not hasattr(new_data, "dtype"):
            new_data = np.asarray(new_data)

        if new_data.dtype.kind not in CONTINUOUS_KINDS:
            raise TypeError("Discrete value supplied to continuous scale")

        if old is not None:
            new_data = np.hstack([new_data, old])

        return min_max(new_data, na_rm=True, finite=True)

    @classmethod
    def map(cls, x, palette, limits, na_value=None, oob=censor):
        """
        Map values to a continuous palette

        Parameters
        ----------
        x : array_like
            Continuous values to scale
        palette : callable ``f(x)``
            palette to use
        na_value : object
            Value to use for missing values.
        oob : callable ``f(x)``
            Function to deal with values that are
            beyond the limits

        Returns
        -------
        out : array_like
            Values mapped onto a palette
        """
        x = oob(rescale(x, _from=limits))
        pal = palette(x)
        try:
            pal[pd.isnull(x)] = na_value
        except TypeError:
            pal = [v if not pd.isnull(v) else na_value for v in pal]

        return pal


class scale_discrete:
    """
    Discrete scale
    """

    @classmethod
    def apply(cls, x, palette, na_value=None):
        """
        Scale data discretely

        Parameters
        ----------
        x : array_like
            Discrete values to scale
        palette : callable ``f(x)``
            Palette to use
        na_value : object
            Value to use for missing values.

        Returns
        -------
        out : array_like
            Scaled values
        """
        limits = cls.train(x)
        return cls.map(x, palette, limits, na_value)

    @classmethod
    def train(cls, new_data, old=None, drop=False, na_rm=False):
        """
        Train a continuous scale

        Parameters
        ----------
        new_data : array_like
            New values
        old : array_like
            Old range. List of values known to the scale.
        drop : bool
            Whether to drop(not include) unused categories
        na_rm : bool
            If ``True``, remove missing values. Missing values
            are either ``NaN`` or ``None``.

        Returns
        -------
        out : list
            Values covered by the scale
        """
        if not len(new_data):
            return old

        if old is None:
            old = []
        else:
            old = list(old)

        # Get the missing values (NaN & Nones) locations and remove them
        nan_bool_idx = pd.isnull(new_data)
        has_na = np.any(nan_bool_idx)
        if not hasattr(new_data, "dtype"):
            new_data = np.asarray(new_data)
        new_data = new_data[~nan_bool_idx]

        if new_data.dtype.kind not in DISCRETE_KINDS:
            raise TypeError("Continuous value supplied to discrete scale")

        # Train i.e. get the new values
        if pdtypes.is_categorical_dtype(new_data):
            categories = get_categories(new_data)
            if drop:
                present = set(new_data.drop_duplicates())
                new = [i for i in categories if i in present]
            else:
                new = list(categories)
        else:
            new = np.unique(new_data)
            new.sort()

        # update old
        old_set = set(old)
        if pdtypes.is_categorical_dtype(new_data):
            # The limits are in the order of the categories
            all_set = old_set | set(new)
            ordered_cats = categories.union(old, sort=False)
            limits = [c for c in ordered_cats if c in all_set]
        else:
            limits = old + [i for i in new if (i not in old_set)]

        # Add nan if required
        has_na_limits = any(pd.isnull(limits))
        if not has_na_limits and not na_rm and has_na:
            limits.append(np.nan)
        return limits

    @classmethod
    def map(cls, x, palette, limits, na_value=None):
        """
        Map values to a discrete palette

        Parameters
        ----------
        palette : callable ``f(x)``
            palette to use
        x : array_like
            Continuous values to scale
        na_value : object
            Value to use for missing values.

        Returns
        -------
        out : array_like
            Values mapped onto a palette
        """
        n = len(limits)
        pal = palette(n)[match(x, limits)]
        try:
            pal[pd.isnull(x)] = na_value
        except TypeError:
            pal = [v if not pd.isnull(v) else na_value for v in pal]

        return pal
