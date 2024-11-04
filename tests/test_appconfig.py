import os.path, tempfile
import pickle
import datetime

import flask
import pytest

from sqlalchemy import inspect

import fdserver
from pkdiagram.pyqt import QDateTime
from pkdiagram import util, version, appconfig, Scene, Person
import conftest


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
    ac = appconfig.AppConfig(filePath=ifile.name)
    ac.init()

    yield ac

    ifile.close()


def test_load_tampered():
    # load file from high sierra test box
    fpath = os.path.join(TEST_DATA, "cherries_high_sierra")
    ac = appconfig.AppConfig(filePath=fpath)
    ac.init()
    assert ac.wasTamperedWith


def test_write_new():
    ifile = tempfile.NamedTemporaryFile()
    ac = appconfig.AppConfig(filePath=ifile.name)
    ac.init()
    ac.set("something", "bleh")
    ac.write()
    ac.deinit()

    ac2 = appconfig.AppConfig(None, filePath=ifile.name)
    ac2.init()
    ac2.read()
    assert ac2.wasTamperedWith == False
    assert ac2.get("something") == "bleh"

    ac2.deinit()
    ifile.close()
