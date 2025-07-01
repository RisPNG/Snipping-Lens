import os
import shutil
from pathlib import Path

import pytest

from jupyter_server_fileid.manager import ArbitraryFileIdManager, LocalFileIdManager


@pytest.fixture
def jp_server_config(jp_server_config):
    return {"ServerApp": {"jpserver_extensions": {"jupyter_server_fileid": True}}}


@pytest.fixture
def fid_db_path(jp_data_dir):
    """Fixture that returns the file ID DB path used for tests."""
    return str(jp_data_dir / "fileidmanager_test.db")


@pytest.fixture(autouse=True)
def delete_fid_db(fid_db_path):
    """Fixture that automatically deletes the DB file after each test."""
    yield
    try:
        os.remove(fid_db_path)
    except OSError:
        pass


@pytest.fixture
def fid_manager(fid_db_path, jp_root_dir):
    """Fixture returning a test-configured instance of `LocalFileIdManager`."""
    fid_manager = LocalFileIdManager(db_path=fid_db_path, root_dir=str(jp_root_dir))
    # disable journal so no temp journal file is created under `tmp_path`.
    # reduces test flakiness since sometimes journal file has same ino and
    # crtime as a deleted file, so FID manager detects it wrongly as a move
    # also makes tests run faster :)
    fid_manager.con.execute("PRAGMA journal_mode = OFF")
    return fid_manager


@pytest.fixture
def arbitrary_fid_manager(fid_db_path, jp_root_dir):
    """Fixture returning a test-configured instance of `ArbitraryFileIdManager`."""
    arbitrary_fid_manager = ArbitraryFileIdManager(db_path=fid_db_path, root_dir=str(jp_root_dir))
    arbitrary_fid_manager.con.execute("PRAGMA journal_mode = OFF")
    return arbitrary_fid_manager


@pytest.fixture(params=["local", "arbitrary"])
def any_fid_manager_class(request):
    """Parametrized fixture that runs the test with each of the default File ID
    manager implementations."""
    class_by_param = {"local": LocalFileIdManager, "arbitrary": ArbitraryFileIdManager}
    return class_by_param[request.param]


@pytest.fixture
def any_fid_manager(any_fid_manager_class, fid_db_path, jp_root_dir):
    fid_manager = any_fid_manager_class(db_path=fid_db_path, root_dir=str(jp_root_dir))
    fid_manager.con.execute("PRAGMA journal_mode = OFF")
    return fid_manager


@pytest.fixture
def fs_helpers(jp_root_dir):
    class FsHelpers:
        # seconds after test start that the `touch` and `move` methods set
        # timestamps to
        fake_time = 1

        def touch(self, path, dir=False):
            """Creates a new file at `path`. The modified times of the file and
            its parent directory are guaranteed to be unique. If given a
            relative path, it is assumed to be relative to jp_root_dir.
            """
            if not os.path.isabs(path):
                path = os.path.join(jp_root_dir, path)

            if dir:
                os.mkdir(path)
            else:
                Path(path).touch()

            parent = Path(path).parent
            stat = os.stat(path)
            current_time = stat.st_mtime + self.fake_time

            os.utime(parent, (stat.st_atime, current_time))
            os.utime(path, (current_time, current_time))

            self.fake_time += 1

        def move(self, old_path, new_path):
            """Moves a file from `old_path` to `new_path` while changing the modified
            timestamp of the parent directory accordingly. The modified time of the
            parent is guaranteed to be unique. If given a relative path, it is
            assumed to be relative to jp_root_dir."""
            if not os.path.isabs(old_path):
                old_path = os.path.join(jp_root_dir, old_path)
            if not os.path.isabs(new_path):
                new_path = os.path.join(jp_root_dir, new_path)

            os.rename(old_path, new_path)
            parent = Path(new_path).parent
            stat = os.stat(parent)
            current_time = stat.st_mtime + self.fake_time

            os.utime(parent, (stat.st_atime, current_time))

            self.fake_time += 1

        def edit(self, path):
            """Simulates editing a file at `path` by updating its modified time
            accordingly.  The modified time of the file is guaranteed to be
            unique. If given a relative path, it is assumed to be relative to
            jp_root_dir."""
            if not os.path.isabs(path):
                path = os.path.join(jp_root_dir, path)

            stat = os.stat(path)
            os.utime(path, (stat.st_atime, stat.st_mtime + self.fake_time))
            self.fake_time += 1

        def delete(self, path):
            """Deletes a file at `path` while changing the modified timestamp of
            the parent directory accordingly. The modified time of the parent is
            guaranteed to be unique. If given a relative path, it is assumed to
            be relative to jp_root_dir."""
            if not os.path.isabs(path):
                path = os.path.join(jp_root_dir, path)

            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

            parent = Path(path).parent
            stat = os.stat(parent)
            current_time = stat.st_mtime + self.fake_time

            os.utime(parent, (stat.st_atime, current_time))

            self.fake_time += 1

        def copy(self, old_path, new_path):
            """Copies a file from `old_path` to `new_path` while changing the
            modified timestamp of the parent directory accordingly. The modified
            time of the parent is guaranteed to be unique. If given a relative
            path, it is assumed to be relative to jp_root_dir."""
            if not os.path.isabs(old_path):
                old_path = os.path.join(jp_root_dir, old_path)
            if not os.path.isabs(new_path):
                new_path = os.path.join(jp_root_dir, new_path)

            if os.path.isdir(old_path):
                shutil.copytree(old_path, new_path)
            else:
                shutil.copyfile(old_path, new_path)

            parent = Path(old_path).parent
            stat = os.stat(parent)
            current_time = stat.st_mtime + self.fake_time

            os.utime(parent, (stat.st_atime, current_time))

            self.fake_time += 1

    return FsHelpers()
