import os
from unittest.mock import MagicMock, patch
import pytest

from flaskerize.exceptions import InvalidSchema
from flaskerize.parser import FzArgumentParser, Flaskerize


@pytest.fixture
def test_flaskerize_args(tmp_path):
    return [
        "fz",
        "generate",
        "app",
        "test.py",
        "--from-dir",
        str(tmp_path),
        "--dry-run",
    ]


def test_flaskerize_generate():

    status = os.system("fz generate --dry-run app my/test/app")
    assert status == 0
    assert not os.path.isfile("should_not_create.py")


@patch.dict("flaskerize.generate.a", {"blueprint": lambda params: None})
def test_bundle_calls_attach(tmp_path):
    with patch("flaskerize.attach.attach") as mock:
        fz = Flaskerize("fz bundle --from test/build/ --to app:create_app".split())
        mock.assert_called_once()


def test_bundle_calls_does_not_call_attach_w_dry_run(tmp_path):
    with patch.object(Flaskerize, "attach") as mock:
        fz = Flaskerize(
            "fz bundle --from test/build/ --to app:create_app --dry-run".split()
        )

        mock.assert_not_called()


def test_attach(tmp_path):
    APP_CONTENTS = """import os
from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.route("/health")
    def serve():
        app = Flaasdfasdfsk(__name__)
        return "{{ name }} online!"

    return app

if __name__ == "__main__":
    app = create_app()
    app.run()
"""
    app_dir = os.path.join(tmp_path, "my_app")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "app.py")
    with open(app_file, "w") as fid:
        fid.write(APP_CONTENTS)

    INDEX_CONTENTS = """<!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <link rel="shortcut icon" href="/favicon.ico" />
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <title>Test</title>
      </head>
      <body>

      </body>
    </html>"""
    site_dir = os.path.join(tmp_path, "my_site")
    os.makedirs(site_dir)
    with open(os.path.join(site_dir, "index.html"), "w") as fid:
        fid.write(INDEX_CONTENTS)
    print(f"fz bundle --from {site_dir} --to {app_file}:create_app".split())
    # fz = Flaskerize(f"fz bundle --from {site_dir} --to {app_file}:create_app".split())
    # assert fz


def test__load_schema(tmp_path):
    from flaskerize.parser import _load_schema

    CONTENTS = """{"wrong_key":[]}"""
    schematic_dir = os.path.join(tmp_path, "schematics/test_schema")
    schema_filename = os.path.join(schematic_dir, "schema.json")
    os.makedirs(schematic_dir)
    with open(schema_filename, "w") as fid:
        fid.write(CONTENTS)
    with pytest.raises(InvalidSchema):
        cfg = _load_schema(schema_filename)


def test_schema(tmp_path):
    from flaskerize.parser import FzArgumentParser

    CONTENTS = """{"options":[]}"""
    schematic_dir = os.path.join(tmp_path, "schematics/test_schema")
    schema_filename = os.path.join(schematic_dir, "schema.json")
    schema_filename2 = os.path.join(schematic_dir, "schema2.json")
    os.makedirs(schematic_dir)
    with open(schema_filename, "w") as fid:
        fid.write(CONTENTS)
    with open(schema_filename2, "w") as fid:
        fid.write(CONTENTS)
    parser = FzArgumentParser(
        schema=schema_filename, xtra_schema_files=[schema_filename2]
    )
    assert parser


def test_bundle(tmp_path):
    import os

    CONTENTS = """import os
    from flask import Flask

    def create_app():
        app = Flask(__name__)

        @app.route("/health")
        def serve():
            return "{{ name }} online!"

        return app

    if __name__ == "__main__":
        app = create_app()
        app.run()"""

    app_file = os.path.join(tmp_path, "app.py")
    with open(app_file, "w") as fid:
        fid.write(CONTENTS)

    INDEX_CONTENTS = """<!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <link rel="shortcut icon" href="/favicon.ico" />
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <title>Test</title>
      </head>
      <body>

      </body>
    </html>"""
    site_dir = tmp_path
    with open(os.path.join(site_dir, "index.html"), "w") as fid:
        fid.write(INDEX_CONTENTS)

    status = os.system(f"fz bundle --dry-run --from {site_dir} --to app:create_app")

    assert status == 0


def test__check_validate_package(test_flaskerize_args, tmp_path):
    tmp_app_path = os.path.join(tmp_path, "test.py")
    fz = Flaskerize(test_flaskerize_args)

    with pytest.raises(ModuleNotFoundError):
        fz._check_validate_package(os.path.join(tmp_path, "pkg that does not exist"))


def test__check_get_schematic_dirname(test_flaskerize_args, tmp_path):
    tmp_pkg_path = os.path.join(tmp_path, "some/pkg")
    os.makedirs(tmp_pkg_path)
    fz = Flaskerize(test_flaskerize_args)

    with pytest.raises(ValueError):
        fz._check_get_schematic_dirname(tmp_pkg_path)


def test__check_get_schematic_dirname_doesnt_append_if_already_schematics(
    test_flaskerize_args, tmp_path
):
    tmp_pkg_path = os.path.join(tmp_path, "some/pkg/schematics")
    os.makedirs(tmp_pkg_path)
    fz = Flaskerize(test_flaskerize_args)

    dirname = fz._check_get_schematic_dirname(tmp_pkg_path)

    expected = tmp_pkg_path
    assert dirname == expected


def test__check_get_schematic_path(test_flaskerize_args, tmp_path):
    tmp_schematic_path = os.path.join(tmp_path, "some/pkg")
    os.makedirs(tmp_schematic_path)
    fz = Flaskerize(test_flaskerize_args)

    with pytest.raises(ValueError):
        fz._check_get_schematic_path(
            tmp_schematic_path, "schematic that does not exist"
        )


def test__split_pkg_schematic(test_flaskerize_args, tmp_path):
    with pytest.raises(ValueError):
        tmp_app_path = os.path.join(tmp_path, "test.py")
        fz = Flaskerize(test_flaskerize_args)
        pkg, schematic = fz._split_pkg_schematic(":schematic")


def test__split_pkg_schematic_works_with_pkg(test_flaskerize_args, tmp_path):
    tmp_app_path = os.path.join(tmp_path, "test.py")
    fz = Flaskerize(test_flaskerize_args)
    pkg, schematic = fz._split_pkg_schematic("my_pkg:schematic")
    assert pkg == "my_pkg"
    assert schematic == "schematic"


def test__split_pkg_schematic_works_with_full_path(test_flaskerize_args, tmp_path):
    tmp_app_path = os.path.join(tmp_path, "test.py")
    fz = Flaskerize(test_flaskerize_args)
    pkg, schematic = fz._split_pkg_schematic("path/to/schematic:schematic")
    assert pkg == "path/to/schematic"
    assert schematic == "schematic"


def test__split_pkg_schematic_only_grabs_last_delim(test_flaskerize_args, tmp_path):
    tmp_app_path = os.path.join(tmp_path, "test.py")
    fz = Flaskerize(test_flaskerize_args)
    pkg, schematic = fz._split_pkg_schematic("path/to/:my:/schematic:schematic")
    assert pkg == "path/to/:my:/schematic"
    assert schematic == "schematic"
