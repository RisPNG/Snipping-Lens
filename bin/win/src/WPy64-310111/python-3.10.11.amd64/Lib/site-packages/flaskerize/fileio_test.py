from unittest.mock import patch, MagicMock
import pytest
from os import path, makedirs

from .fileio import StagedFileSystem


@pytest.fixture
def fs(tmp_path):
    return StagedFileSystem(src_path=str(tmp_path))


def test_file_not_copied_until_commit(fs):
    outfile = path.join(fs.src_path, "my_file.txt")
    assert not fs.src_fs.exists(outfile)
    assert not fs.stg_fs.exists(outfile)
    assert not fs.src_fs.exists(outfile)

    fs.stg_fs.makedirs(path.dirname(outfile))
    with fs.open(outfile, "w") as fid:
        fid.write("Some content")
    assert not fs.src_fs.exists(outfile)
    assert fs.stg_fs.exists(outfile)

    fs.commit()
    assert fs.stg_fs.exists(outfile)
    assert fs.src_fs.exists(outfile)


def test_dry_run_true_does_not_write_changes(tmp_path):
    schematic_files_path = path.join(tmp_path, "files/")
    makedirs(schematic_files_path)
    fs = StagedFileSystem(src_path=str(tmp_path), dry_run=True)
    outfile = path.join(str(tmp_path), "my_file.txt")
    fs.stg_fs.makedirs(path.dirname(outfile))
    with fs.open(outfile, "w") as fid:
        fid.write("Some content")
    assert not fs.src_fs.exists(outfile)
    assert fs.stg_fs.exists(outfile)

    fs.commit()
    assert not fs.src_fs.exists(outfile)
    assert fs.stg_fs.exists(outfile)


def test_md5(tmp_path):
    from .fileio import md5

    outfile = path.join(tmp_path, "my_file.txt")
    with open(outfile, "w") as fid:
        fid.write("Some content")

    result = md5(lambda: open(outfile, "rb"))

    expected = "b53227da4280f0e18270f21dd77c91d0"
    assert result == expected


def test_makedirs(tmp_path, fs):
    mock = MagicMock()
    fs.render_fs.makedirs = mock
    fs.makedirs(tmp_path)
    mock.assert_called_with(tmp_path)


def test_exists(tmp_path, fs):
    mock = MagicMock()
    fs.render_fs.exists = mock
    fs.exists(tmp_path)
    mock.assert_called_with(tmp_path)


def test_isdir(tmp_path, fs):
    mock = MagicMock()
    fs.render_fs.isdir = mock
    fs.isdir(tmp_path)
    mock.assert_called_with(tmp_path)


def test_delete_raises_for_directories(tmp_path, fs):
    dirname = path.join(tmp_path, "my/dir")
    fs.stg_fs.makedirs(dirname)
    with pytest.raises(NotImplementedError):
        fs.delete(dirname)


def test_delete_correctly_removes_file(tmp_path, fs):
    dirname = path.join(tmp_path, "my/dir")
    file = path.join(dirname, "test_file.txt")
    fs.stg_fs.makedirs(dirname)
    fs.stg_fs.touch(file)
    assert fs.stg_fs.exists(file)
    fs.delete(file)
    assert not fs.stg_fs.exists(file)


def test_delete_correctly_appends_to_deleted(tmp_path, fs):
    dirname = path.join(tmp_path, "my/dir")
    file = path.join(dirname, "test_file.txt")
    fs.stg_fs.makedirs(dirname)
    fs.stg_fs.touch(file)
    fs.delete(file)
    assert file in fs._deleted_files


def test_print_fs_diff_created(fs):
    mock__print_created = MagicMock()
    mock__print_deleted = MagicMock()
    mock__print_modified = MagicMock()
    fs.get_created_directories = MagicMock(return_value=["test_dir"])
    fs.get_created_files = MagicMock(return_value=["test_create_file"])
    fs._print_created = mock__print_created
    fs._print_deleted = mock__print_deleted
    fs._print_modified = mock__print_modified

    fs.print_fs_diff()

    mock__print_created.call_count == 2
    mock__print_modified.assert_not_called()
    mock__print_deleted.assert_not_called()


def test_print_fs_diff_modified(fs):
    mock__print_created = MagicMock()
    mock__print_deleted = MagicMock()
    mock__print_modified = MagicMock()
    fs.get_modified_files = MagicMock(return_value=["test_modified_file"])
    fs._print_created = mock__print_created
    fs._print_deleted = mock__print_deleted
    fs._print_modified = mock__print_modified

    fs.print_fs_diff()

    mock__print_modified.assert_called_with("test_modified_file")
    mock__print_created.assert_not_called()
    mock__print_deleted.assert_not_called()


def test_print_fs_diff_delete(fs):
    mock__print_created = MagicMock()
    mock__print_deleted = MagicMock()
    mock__print_modified = MagicMock()
    fs.get_deleted_files = MagicMock(return_value=["test_delete_file"])
    fs._print_created = mock__print_created
    fs._print_deleted = mock__print_deleted
    fs._print_modified = mock__print_modified

    fs.print_fs_diff()

    mock__print_deleted.assert_called_once_with("test_delete_file")
    mock__print_created.assert_not_called()
    mock__print_modified.assert_not_called()
