from os import path
import pytest

from flaskerize import utils


def test_split_file_factory():
    root, app = utils.split_file_factory("wsgi:app")

    assert root == "wsgi"
    assert app == "app"


def test_split_file_factory_with_other_delim():
    root, app = utils.split_file_factory("wsgi::app", delim="::")

    assert root == "wsgi"
    assert app == "app"


def test_split_file_factory_with_path():
    root, app = utils.split_file_factory("my/path/wsgi:app")

    assert root == "my/path/wsgi"
    assert app == "app"


def test_split_file_factory_with_py_file_existing(tmp_path):
    import os

    filename = os.path.join(tmp_path, "wsgi.py")
    with open(filename, "w") as fid:
        fid.write("")
    root, app = utils.split_file_factory(f"{filename[:-3]}:app")

    assert root == filename
    assert app == "app"


def test_split_file_factory_with_a_default_path():
    root, app = utils.split_file_factory("shake/and", default_func_name="bake")

    assert root == "shake/and"
    assert app == "bake"


def test_split_file_factory_respects_explicity_path_over_a_default_path():
    root, app = utils.split_file_factory("shake/and:bake", default_func_name="take")

    assert root == "shake/and"
    assert app == "bake"


def test_split_file_factory_handles_packages(tmp_path):
    import os

    dirname = path.join(tmp_path, "my_app")
    os.makedirs(dirname)
    with open(f"{dirname}/__init__.py", "w") as fid:
        fid.write("")

    root, app = utils.split_file_factory(dirname)

    assert "my_app" in root


def test_split_file_factory_raises_on_invalid_packages(tmp_path):
    import os

    dirname = path.join(tmp_path, "my_app")
    os.makedirs(dirname)
    with pytest.raises(SyntaxError):
        root, app = utils.split_file_factory(dirname)


def test_a():
    with pytest.raises(ValueError):
        utils.split_file_factory("oops:this:is:wrong:syntax!")

