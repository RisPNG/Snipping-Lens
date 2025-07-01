from pytest import fixture, raises
import os
from os import path
from unittest.mock import patch, MagicMock
from typing import Callable

from .render import SchematicRenderer


@fixture
def renderer(tmp_path):
    schematic_path = path.join(tmp_path, "schematics/doodad/")
    schematic_files_path = path.join(schematic_path, "files/")
    src_path = str(tmp_path)
    output_prefix = "render/test/results/"
    os.makedirs(schematic_path)
    os.makedirs(schematic_files_path)
    yield SchematicRenderer(
        schematic_path=schematic_path,
        src_path=src_path,
        output_prefix=output_prefix,
        dry_run=True,
    )


@fixture
def renderer_no_dry_run(tmp_path):
    schematic_path = path.join(tmp_path, "schematics/doodad/")
    schematic_files_path = path.join(schematic_path, "files/")
    src_path = str(tmp_path)
    output_prefix = "render/test/results/"
    os.makedirs(schematic_path)
    os.makedirs(schematic_files_path)
    yield SchematicRenderer(
        schematic_path=schematic_path,
        src_path=src_path,
        output_prefix=output_prefix,
        dry_run=False,
    )


def test__check_get_arg_parser_returns_parser_with_schema_file(
    renderer: SchematicRenderer
):
    CONTENTS = """
    {
        "templateFilePatterns": ["**/*.template"],
        "options": [
          {
            "arg": "some_option",
            "type": "str",
            "help": "An option used in this test"
          }
        ]
    }

    """
    schema_path = path.join(renderer.schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(CONTENTS)
    parser = renderer._check_get_arg_parser(schema_path)
    assert parser is not None


def test__check_get_arg_parser_returns_functioning_parser_with_schema_file(
    renderer: SchematicRenderer
):
    CONTENTS = """
    {
        "templateFilePatterns": ["**/*.template"],
        "options": [
          {
            "arg": "some_option",
            "type": "str",
            "help": "An option used in this test"
          }
        ]
    }

    """
    schema_path = path.join(renderer.schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(CONTENTS)
    parser = renderer._check_get_arg_parser(schema_path)
    assert parser is not None
    parsed = parser.parse_args(["some_value"])
    assert parsed.some_option == "some_value"


def test_get_template_files(tmp_path):
    from pathlib import Path

    CONTENTS = """
    {
        "templateFilePatterns": ["**/*.template"],
        "options": []
    }

    """
    schematic_path = path.join(tmp_path, "schematics/doodad/")
    schematic_files_path = path.join(schematic_path, "files/")
    os.makedirs(schematic_files_path)
    schema_path = path.join(schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(CONTENTS)
    renderer = SchematicRenderer(
        schematic_path=schematic_path, src_path="./", dry_run=True
    )
    Path(path.join(schematic_files_path, "b.txt.template")).touch()
    Path(path.join(schematic_files_path, "c.notatemplate.txt")).touch()
    Path(path.join(schematic_files_path, "a.txt.template")).touch()

    template_files = renderer.get_template_files()

    assert len(template_files) == 2


def test_ignoreFilePatterns_is_respected(tmp_path):
    from pathlib import Path

    CONTENTS = """
    {
        "templateFilePatterns": ["**/*.template"],
        "ignoreFilePatterns": ["**/b.txt.template"],
        "options": []
    }

    """
    schematic_path = path.join(tmp_path, "schematics/doodad/")
    schematic_files_path = path.join(schematic_path, "files/")
    os.makedirs(schematic_files_path)
    schema_path = path.join(schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(CONTENTS)
    renderer = SchematicRenderer(
        schematic_path=schematic_path, src_path="./", dry_run=True
    )
    Path(path.join(schematic_files_path, "b.txt.template")).touch()
    Path(path.join(schematic_files_path, "c.notatemplate.txt")).touch()
    Path(path.join(schematic_files_path, "a.txt.template")).touch()

    template_files = renderer.get_template_files()

    assert len(template_files) == 1


def test__generate_outfile(renderer: SchematicRenderer):

    outfile = renderer._generate_outfile(
        template_file="my/file.txt.template", root="/base"
    )

    base, file = path.split(outfile)
    assert file == "file.txt"


@patch("flaskerize.fileio.colored")
class TestColorizingPrint:
    def test__print_created(self, colored: MagicMock, renderer: SchematicRenderer):
        renderer.fs._print_created("print me!")

        colored.assert_called_once()

    def test__print_modified(self, colored: MagicMock, renderer: SchematicRenderer):
        renderer.fs._print_modified("print me!")

        colored.assert_called_once()

    def test__print_deleted(self, colored: MagicMock, renderer: SchematicRenderer):
        renderer.fs._print_deleted("print me!")

        colored.assert_called_once()

    def test_print_summary_with_no_updates(
        self, colored: MagicMock, renderer: SchematicRenderer
    ):
        renderer.print_summary()

        # One extra call if dry run is enabled
        colored.call_count == int(renderer.dry_run)


@patch("flaskerize.render.colored")
def test_render_colored(colored, renderer):
    renderer.get_template_files = lambda: ["file1"]
    mock = MagicMock()
    renderer.render_from_file = mock

    renderer.render(name="test_resource", args=[])

    mock.assert_called_once()


def test_render_from_file_creates_directories(renderer, tmp_path):
    os.makedirs(os.path.join(renderer.schematic_files_path, "thingy/"))
    filename = os.path.join(
        renderer.schematic_files_path, "thingy/my_template.py.template"
    )
    CONTENTS = "{{ secret }}"
    with open(filename, "w") as fid:
        fid.write(CONTENTS)
    renderer._generate_outfile = MagicMock(return_value=filename)
    renderer.render_from_file(
        "thingy/my_template.py.template", context={"secret": "42"}
    )

    assert len(renderer.fs.get_created_directories()) > 0


def test_copy_static_file_no_dry_run(renderer_no_dry_run, tmp_path):
    renderer = renderer_no_dry_run
    rel_filename = "doodad/my_file.txt"
    filename_in_sch = os.path.join(renderer.schematic_files_path, rel_filename)
    filename_in_src = os.path.join(
        renderer.src_path, renderer.output_prefix, rel_filename
    )
    CONTENTS = "some static content"
    os.makedirs(os.path.dirname(filename_in_sch))
    with open(filename_in_sch, "w") as fid:
        fid.write(CONTENTS)
    renderer._generate_outfile = MagicMock(return_value=rel_filename)
    renderer.copy_static_file(rel_filename, context={})
    assert len(renderer.fs.get_created_files()) > 0

    renderer.fs.commit()  # TODO: create a context manager to handle committing on success
    assert os.path.exists(filename_in_src)


def test_copy_static_file_dry_run_true(renderer, tmp_path):
    rel_filename = "doodad/my_file.txt"
    filename_in_sch = os.path.join(renderer.schematic_files_path, rel_filename)
    filename_in_src = os.path.join(
        renderer.src_path, renderer.output_prefix, rel_filename
    )
    CONTENTS = "some static content"
    os.makedirs(os.path.dirname(filename_in_sch))
    with open(filename_in_sch, "w") as fid:
        fid.write(CONTENTS)
    renderer._generate_outfile = MagicMock(return_value=rel_filename)
    renderer.copy_static_file(rel_filename, context={})
    renderer.fs.commit()  # TODO: create a context manager to handle committing on success

    assert len(renderer.fs.get_created_files()) > 0
    assert not os.path.exists(filename_in_src)


def test_copy_static_file_does_not_modify_if_exists_and_contents_unchanged(tmp_path):
    rel_filename = "my_file.txt"
    schematic_path = path.join(tmp_path, "schematics/doodad/")
    schematic_files_path = path.join(schematic_path, "files/")
    src_path = path.join(tmp_path, "out/path/")
    os.makedirs(schematic_path)
    os.makedirs(schematic_files_path)
    os.makedirs(src_path)

    filename_in_sch = os.path.join(schematic_files_path, rel_filename)
    CONTENTS = "some static content"
    with open(filename_in_sch, "w") as fid:
        fid.write(CONTENTS)
    filename_in_src = os.path.join(src_path, rel_filename)
    with open(filename_in_src, "w") as fid:
        fid.write(CONTENTS)
    renderer = SchematicRenderer(schematic_path=schematic_path, src_path=src_path)
    renderer._generate_outfile = MagicMock(return_value=rel_filename)
    renderer.copy_static_file(rel_filename, context={})
    assert len(renderer.fs.get_created_files()) == 0
    assert len(renderer.fs.get_modified_files()) == 0
    assert len(renderer.fs.get_unchanged_files()) == 1
    renderer.fs.commit()
    assert os.path.exists(filename_in_src)


def test_copy_static_file_modifies_file_if_exists_and_contents_changes(tmp_path):
    rel_filename = "my_file.txt"
    schematic_path = path.join(tmp_path, "schematics/doodad/")
    schematic_files_path = path.join(schematic_path, "files/")
    src_path = path.join(tmp_path, "out/path/")
    os.makedirs(schematic_path)
    os.makedirs(schematic_files_path)
    os.makedirs(src_path)

    filename_in_sch = os.path.join(schematic_files_path, rel_filename)
    CONTENTS = "some static content"
    with open(filename_in_sch, "w") as fid:
        fid.write(CONTENTS)
    filename_in_src = os.path.join(src_path, rel_filename)
    with open(filename_in_src, "w") as fid:
        fid.write(CONTENTS + "...")
    renderer = SchematicRenderer(schematic_path=schematic_path, src_path=src_path)
    renderer._generate_outfile = MagicMock(return_value=rel_filename)
    renderer.copy_static_file(rel_filename, context={})
    assert len(renderer.fs.get_created_files()) == 0
    assert len(renderer.fs.get_modified_files()) == 1
    renderer.fs.commit()
    assert os.path.exists(filename_in_src)


def test_run_with_static_files(renderer, tmp_path):
    from flaskerize.render import default_run

    filename = os.path.join(renderer.schematic_files_path, "my_file.txt")
    CONTENTS = "some existing content"
    with open(filename, "w") as fid:
        fid.write(CONTENTS)

    renderer._generate_outfile = MagicMock(return_value="my_file.txt")
    default_run(renderer=renderer, context={})

    assert len(renderer.fs.get_created_files()) > 0


def test__load_run_function_raises_if_colliding_parameter_provided(tmp_path):
    CONTENTS = """
    {
        "options": [
          {
            "arg": "name",
            "type": "str",
            "help": "An option that is reserved and will cause an error"
          }
        ]
    }

    """

    os.makedirs(path.join(tmp_path, "schematics/doodad/files"))
    schematic_path = path.join(tmp_path, "schematics/doodad")
    schema_path = path.join(schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(CONTENTS)
    renderer = SchematicRenderer(
        schematic_path=schematic_path, src_path="./", dry_run=True
    )
    with raises(ValueError):
        renderer.render(name="test_resource", args=["test_name"])


def test__load_run_function_raises_if_invalid_run_py(tmp_path):
    SCHEMA_CONTENTS = """{"options": []}"""
    os.makedirs(path.join(tmp_path, "schematics/doodad/files/"))
    schematic_path = path.join(tmp_path, "schematics/doodad")
    schema_path = path.join(schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(SCHEMA_CONTENTS)

    RUN_CONTENTS = """from typing import Any, Dict

from flaskerize import SchematicRenderer


def wrong_named_run(renderer: SchematicRenderer, context: Dict[str, Any]) -> None:
    return
"""
    run_path = path.join(schematic_path, "run.py")
    with open(run_path, "w") as fid:
        fid.write(RUN_CONTENTS)

    renderer = SchematicRenderer(
        schematic_path=schematic_path, src_path="./", dry_run=True
    )
    with raises(ValueError):
        renderer._load_run_function(path=path.join(renderer.schematic_path, "run.py"))


def test__load_run_function_uses_custom_run(tmp_path):
    SCHEMA_CONTENTS = """{"options": []}"""
    os.makedirs(path.join(tmp_path, "schematics/doodad/files/"))
    schematic_path = path.join(tmp_path, "schematics/doodad/")
    schema_path = path.join(schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(SCHEMA_CONTENTS)

    RUN_CONTENTS = """from typing import Any, Dict

from flaskerize import SchematicRenderer


def run(renderer: SchematicRenderer, context: Dict[str, Any]) -> None:
    return "result from the custom run function"
"""
    run_path = path.join(schematic_path, "run.py")
    with open(run_path, "w") as fid:
        fid.write(RUN_CONTENTS)

    renderer = SchematicRenderer(
        schematic_path=schematic_path, src_path="./", dry_run=True
    )
    run = renderer._load_run_function(path=path.join(renderer.schematic_path, "run.py"))

    result = run(renderer=renderer, context={})

    assert result == "result from the custom run function"


def test__load_run_function_uses_custom_run_with_context_correctly(tmp_path):
    SCHEMA_CONTENTS = """{"options": []}"""
    os.makedirs(path.join(tmp_path, "schematics/doodad/files/"))
    schematic_path = path.join(tmp_path, "schematics/doodad/")
    schema_path = path.join(schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(SCHEMA_CONTENTS)

    RUN_CONTENTS = """from typing import Any, Dict

from flaskerize import SchematicRenderer


def run(renderer: SchematicRenderer, context: Dict[str, Any]) -> None:
    return context["value"]
"""
    run_path = path.join(schematic_path, "run.py")
    with open(run_path, "w") as fid:
        fid.write(RUN_CONTENTS)

    renderer = SchematicRenderer(
        schematic_path=schematic_path, src_path="./", dry_run=True
    )
    run = renderer._load_run_function(path=path.join(renderer.schematic_path, "run.py"))

    result = run(renderer=renderer, context={"value": "secret password"})

    assert result == "secret password"


@patch("flaskerize.render.default_run")
def test_default_run_executed_if_no_custom_run(mock: MagicMock, tmp_path):
    SCHEMA_CONTENTS = """{"options": []}"""
    os.makedirs(path.join(tmp_path, "schematics/doodad/files/"))
    schematic_path = path.join(tmp_path, "schematics/doodad/")
    schema_path = path.join(schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(SCHEMA_CONTENTS)
    renderer = SchematicRenderer(
        schematic_path=schematic_path, src_path="./", dry_run=True
    )

    renderer.render(name="test_resource", args=[])

    mock.assert_called_once()


def test_render(tmp_path: str):
    schematic_path = path.join(tmp_path, "schematic/doodad/")
    schematic_files_path = path.join(schematic_path, "files")
    os.makedirs(schematic_files_path)
    SCHEMA_CONTENTS = """
    {
        "templateFilePatterns": ["**/*.template"],
        "options": [
          {
            "arg": "some_option",
            "type": "str",
            "help": "An option used in this test"
          }
        ]
    }

    """
    schema_path = path.join(schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(SCHEMA_CONTENTS)

    TEMPLATE_CONTENT = "Hello {{ some_option }}!"
    template_path = path.join(schematic_files_path, "output.txt.template")
    with open(template_path, "w") as fid:
        fid.write(TEMPLATE_CONTENT)

    renderer = SchematicRenderer(
        schematic_path=schematic_path,
        src_path=path.join(tmp_path, "results/"),
        dry_run=False,
    )
    renderer.render(name="Test schematic", args=["there"])

    outfile = path.join(tmp_path, "results/output.txt")
    assert path.exists(outfile)
    with open(outfile, "r") as fid:
        contents = fid.read()
    assert contents == "Hello there!"


def test_render_with_custom_function(tmp_path: str):

    schematic_path = path.join(tmp_path, "schematic/doodad/")
    schematic_files_path = path.join(schematic_path, "files/")
    os.makedirs(schematic_files_path)
    SCHEMA_CONTENTS = """
    {
        "templateFilePatterns": ["**/*.template"],
        "options": [
          {
            "arg": "some_option",
            "type": "str",
            "help": "An option used in this test"
          }
        ]
    }

    """
    schema_path = path.join(schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(SCHEMA_CONTENTS)

    CUSTOM_FUNCTIONS_CONTENTS = """from flaskerize import register_custom_function  # noqa


@register_custom_function
def derp_case(val: str) -> str:
    from itertools import zip_longest

    downs = val[::2].lower()
    ups = val[1::2].upper()
    result = ""
    for i, j in zip_longest(downs, ups):
        if i is not None:
            result += i
        if j is not None:
            result += j
    return result

    """
    custom_functions_path = path.join(schematic_path, "custom_functions.py")
    with open(custom_functions_path, "w") as fid:
        fid.write(CUSTOM_FUNCTIONS_CONTENTS)

    TEMPLATE_CONTENT = "Hello {{ derp_case(some_option) }}!"
    template_path = path.join(schematic_files_path, "output.txt.template")
    with open(template_path, "w") as fid:
        fid.write(TEMPLATE_CONTENT)

    renderer = SchematicRenderer(
        schematic_path=schematic_path,
        src_path=path.join(tmp_path, "results/"),
        dry_run=False,
    )
    renderer.render(name="Test schematic", args=["there"])

    outfile = path.join(tmp_path, "results/output.txt")
    assert path.exists(outfile)
    with open(outfile, "r") as fid:
        contents = fid.read()
    assert contents == "Hello tHeRe!"


def test_render_with_custom_function_parameterized(tmp_path: str):

    schematic_path = path.join(tmp_path, "schematic/doodad")
    schematic_files_path = path.join(schematic_path, "files")
    os.makedirs(schematic_files_path)
    SCHEMA_CONTENTS = """
    {
        "templateFilePatterns": ["**/*.template"],
        "options": [
          {
            "arg": "some_option",
            "type": "str",
            "help": "An option used in this test"
          }
        ]
    }

    """
    schema_path = path.join(schematic_path, "schema.json")
    with open(schema_path, "w") as fid:
        fid.write(SCHEMA_CONTENTS)

    CUSTOM_FUNCTIONS_CONTENTS = """from flaskerize import register_custom_function  # noqa


@register_custom_function
def truncate(val: str, max_length: int) -> str:
    return val[:max_length]

    """
    custom_functions_path = path.join(schematic_path, "custom_functions.py")
    with open(custom_functions_path, "w") as fid:
        fid.write(CUSTOM_FUNCTIONS_CONTENTS)

    TEMPLATE_CONTENT = "Hello {{ truncate(some_option, 2) }}!"
    template_path = path.join(schematic_files_path, "output.txt.template")
    with open(template_path, "w") as fid:
        fid.write(TEMPLATE_CONTENT)

    renderer = SchematicRenderer(
        schematic_path=schematic_path,
        src_path=path.join(tmp_path, "results/"),
        dry_run=False,
    )
    renderer.render(name="Test schematic", args=["there"])

    outfile = path.join(tmp_path, "results/output.txt")
    assert path.exists(outfile)
    with open(outfile, "r") as fid:
        contents = fid.read()
    assert contents == "Hello th!"


# def test_copy_static_file(tmp_path):
#     schematic_path = path.join(tmp_path, "schematics/doodad/")
#     schematic_files_path = path.join(schematic_path, "files/")
#     os.makedirs(schematic_files_path)
#     src_path = path.join(tmp_path, "out/path/")
#     renderer = SchematicRenderer(schematic_path=schematic_path, src_path=src_path)

#     filename = os.path.join(renderer.schematic_files_path, "out/path/my_file.txt")
#     os.makedirs(os.path.dirname(filename))
#     CONTENTS = "some static content"
#     with open(filename, "w") as fid:
#         fid.write(CONTENTS)

#     rel_output_path = "out/path/my_file.txt"
#     renderer._get_rel_path = MagicMock(return_value=rel_output_path)
#     renderer.copy_static_file(filename, context={})
#     renderer.fs.commit()
#     # assert len(renderer._files_created) > 0

#     full_output_path = os.path.join(src_path, "my_file.txt")

#     assert os.path.exists(full_output_path)
