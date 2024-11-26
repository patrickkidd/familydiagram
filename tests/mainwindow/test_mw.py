import time, os, os.path, datetime
import shutil
import pickle

import pytest
import mock

import vedana
from pkdiagram import util
from pkdiagram import Person, Scene, MainWindow, AppController


pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView"),
]


def test_load_fd(test_session, test_activation, tmp_path, create_ac_mw):
    scene = Scene()
    tmp_fd_path = os.path.join(tmp_path, "test.fd")
    util.touchFD(os.path.join(tmp_path, "test.fd"))
    with open(os.path.join(tmp_fd_path, "diagram.pickle"), "rb") as f:
        data = pickle.loads(f.read())
        scene.read(data)
    scene.addItems(Person(name="You"), Person(name="Me"))
    with open(os.path.join(tmp_fd_path, "diagram.pickle"), "wb") as f:
        f.write(pickle.dumps(scene.data()))
    ac, mw = create_ac_mw()
    mw.open(tmp_fd_path)
    assert mw.documentView.sceneModel.readOnly == False
    assert mw.scene.query1(name="You")
    assert mw.scene.query1(name="Me")


def test_import_to_free_diagram(test_session, qtbot, tmp_path, create_ac_mw):

    # Write file to import
    scene = Scene(items=(Person(name="Hey"), Person(name="You")))
    filePath = os.path.join(tmp_path, "some_family.fd")
    util.touchFD(filePath, bdata=pickle.dumps(scene.data()))

    # Load a window
    ac, mw = create_ac_mw()
    assert mw.session.activeFeatures() == [vedana.LICENSE_FREE]
    assert mw.scene != None
    assert len(mw.scene.people()) == 0

    # Import the file
    qtbot.clickYesAfter(
        lambda: mw.open(filePath=filePath, importing=True),
        contains=MainWindow.S_IMPORTING_TO_FREE_DIAGRAM,
    )
    assert len(mw.scene.people()) == len(scene.people())


def test_appconfig_upgraded(qApp, tmp_path, data_root, create_ac_mw):

    PREFS_NAME = "bleh"

    shutil.copyfile(
        os.path.join(data_root, "cherries_1x"), tmp_path / f"cherries-{PREFS_NAME}"
    )

    with mock.patch("pkdiagram.pyqt.QMessageBox.warning") as warning:
        ac, mw = create_ac_mw(prefsName=PREFS_NAME)
    assert ac.appConfig.wasV1 == True
    warning.assert_called_once_with(
        None, "Login required", AppController.S_APPCONFIG_UPGRADED_LOGIN_REQUIRED
    )
