import os.path
import sys

import pytest

import numcodecs.registry


here = os.path.abspath(os.path.dirname(__file__))
pytest.importorskip("entrypoints")


@pytest.fixture()
def set_path():
    sys.path.append(here)
    numcodecs.registry.run_entrypoints()
    yield
    sys.path.remove(here)
    numcodecs.registry.run_entrypoints()
    numcodecs.registry.codec_registry.pop("test")


def test_entrypoint_codec(set_path):
    cls = numcodecs.registry.get_codec({"id": "test"})
    assert cls.codec_id == "test"
