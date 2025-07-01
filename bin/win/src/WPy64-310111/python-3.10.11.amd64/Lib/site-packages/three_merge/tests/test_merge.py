# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see LICENSE for details)

"""Three way merge tests."""

# Local imports
from three_merge import merge


def test_unrelated_additions():
    base = '123456789101112'
    source = '0123456789101112'
    target = '12345678910111213'
    expected = '012345678910111213'
    merged = merge(source, target, base)
    assert merged == expected

    merged = merge(target, source, base)
    assert merged == expected


def test_unrelated_deletions():
    base = '123456789101112'
    source = '1256789101112'
    target = '12345678912'
    expected = '125678912'
    merged = merge(source, target, base)
    assert merged == expected

    merged = merge(target, source, base)
    assert merged == expected


def test_multiple_additions():
    base = '123456789101112'
    source = '1234(56789101112'
    target = '1234567)89101112'
    expected = '1234(567)89101112'
    merged = merge(source, target, base)
    assert merged == expected

    merged = merge(target, source, base)
    assert merged == expected


def test_multiple_deletions():
    base = '123456789101112'
    source = '126789101112'
    target = '123489101112'
    expected = '1289101112'
    merged = merge(source, target, base)
    assert merged == expected

    # breakpoint()
    merged = merge(target, source, base)
    assert merged == expected


def test_addition_deletion():
    base = '123456789101112'
    source = '123456789ab101112'
    target = '123789101112'
    expected = '123789ab101112'
    merged = merge(source, target, base)
    assert merged == expected

    merged = merge(target, source, base)
    assert merged == expected


def test_addition_conflict():
    base = '123456789101112'
    source = '123a456789101112'
    target = '123b456789101112'
    expected = '123<<<<<<< ++ a ======= ++ b >>>>>>>456789101112'
    merged = merge(source, target, base)
    assert merged == expected

    expected = '123<<<<<<< ++ b ======= ++ a >>>>>>>456789101112'
    merged = merge(target, source, base)
    assert merged == expected


def test_addition_deletion_conflict():
    base = '123456789101112'
    source = '123a456789101112'
    target = '12356789101112'
    expected = '123<<<<<<< ++ a ======= -- 4 >>>>>>>56789101112'
    merged = merge(source, target, base)
    assert merged == expected

    expected = '123<<<<<<< ++ a ======= -- 4 >>>>>>>56789101112'
    merged = merge(target, source, base)
    assert merged == expected


def test_deletion_composition():
    base = '123456789101112'
    source = '12346789101112'
    target = '12346789101112'
    expected = '12346789101112'
    merged = merge(source, target, base)
    assert merged == expected


def test_deletion_addition_conflict():
    base = '123456789101112'
    source = '123789101112'
    target = '1234a56789101112'
    expected = '123<<<<<<< ++ a ======= -- 56 >>>>>>>789101112'
    merged = merge(source, target, base)
    assert expected == merged

    merged = merge(target, source, base)
    assert merged == expected


def test_triple_addition():
    base = '123456789101112'
    source = '123\n    456789101112'
    target = '12345678910(11)12'
    expected = '123\n    45678910(11)12'
    merged = merge(source, target, base)
    assert merged == expected

    merged = merge(target, source, base)
    assert merged == expected
