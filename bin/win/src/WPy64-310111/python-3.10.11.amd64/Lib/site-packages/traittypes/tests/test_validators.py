#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import pytest

from traitlets import HasTraits, TraitError

from ..traittypes import SciType


def test_coercion_validator():
    # Test with a squeeze coercion
    def truncate(trait, value):
        return value[:10]

    class Foo(HasTraits):
        bar = SciType().valid(truncate)

    foo = Foo(bar=list(range(20)))
    assert foo.bar == list(range(10))
    foo.bar = list(range(10, 40))
    assert foo.bar == list(range(10, 20))


def test_validaton_error():
    # Test with a squeeze coercion
    def maxlen(trait, value):
        if len(value) > 10:
            raise ValueError('Too long sequence!')
        return value

    class Foo(HasTraits):
        bar = SciType().valid(maxlen)

    # Check that it works as expected:
    foo = Foo(bar=list(range(5)))
    assert foo.bar == list(range(5))
    # Check that it fails as expected:
    with pytest.raises(TraitError):  # Should convert ValueError to TraitError
        foo.bar = list(range(10, 40))
    assert foo.bar == list(range(5))
    # Check that it can again be set correctly
    foo = Foo(bar=list(range(5, 10)))
    assert foo.bar == list(range(5, 10))
