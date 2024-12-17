import os.path, tempfile
import shutil

import pytest

from pkdiagram.app import AppConfig


pytestmark = [pytest.mark.component("AppConfig")]


# test_data_files = {}
TEST_DATA = os.path.join(os.path.dirname(__file__), "data")
# for name in os.listdir(TEST_DATA):
#     fpath = os.path.join(TEST_DATA, name)
#     with open(fpath, 'rb') as f:
#         test_data_files[name] = f.read()


@pytest.fixture
def ac():
    ifile = tempfile.NamedTemporaryFile()
    ac = AppConfig(filePath=ifile.name)
    ac.init()

    yield ac

    ifile.close()


def test_load_all_good(tmp_path):
    ac = AppConfig()
    ac.init()
    assert ac.wasTamperedWith == False
    assert ac.wasV1 == False
    assert ac.get("something") == None


def test_load_tampered(data_root):
    # load file from high sierra test box
    fpath = os.path.join(data_root, "cherries_high_sierra")
    with open(os.path.join(data_root, "cherries_high_sierra.protect"), "wb") as f:
        f.write(b"")
    ac = AppConfig(filePath=fpath)
    ac.init()
    assert ac.wasTamperedWith


def test_write_new():
    ifile = tempfile.NamedTemporaryFile()
    ac = AppConfig(filePath=ifile.name)
    ac.init()
    ac.set("something", "bleh")
    ac.write()
    ac.deinit()

    ac2 = AppConfig(None, filePath=ifile.name)
    ac2.init()
    ac2.read()
    assert ac2.wasTamperedWith == False
    assert ac2.get("something") == "bleh"

    ac2.deinit()
    ifile.close()


def test_backward_compat_with_1x(tmp_path, data_root):
    shutil.copyfile(os.path.join(data_root, "cherries_1x"), tmp_path / "cherries_1x")
    data_fpath = os.path.join(os.path.join(data_root, "cherries_1x"))
    new_fpath = os.path.join(tmp_path / "cherries_1x")
    with open(data_fpath, "rb") as rf:
        bdata = rf.read()
        with open(new_fpath, "wb") as wf:
            wf.write(bdata)

    ac = AppConfig(filePath=new_fpath)
    ac.init()
    assert ac.wasV1 == True
