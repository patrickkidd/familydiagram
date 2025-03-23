import sys
import os, os.path
import shutil
import pickle
import traceback

import pytest
import mock

import vedana
from pkdiagram import util
from pkdiagram.pyqt import QApplication
from pkdiagram.scene import Person, Scene, Marriage, Layer
from pkdiagram.mainwindow import MainWindow
from pkdiagram.documentview import DocumentController
from pkdiagram.app import AppController
from pkdiagram.extensions import datadog_excepthook


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


def test_exception_logging(test_session, test_activation, tmp_path, create_ac_mw):
    ac, mw = create_ac_mw()
    try:
        raise ValueError("This is a simulated error for testing")
    except ValueError as e:
        # Capture the exception and its traceback
        etype, value, tb = sys.exc_info()
    with mock.patch("pkdiagram.app.Analytics.send") as send:
        datadog_excepthook(etype, value, tb)
    assert send.call_count == 1
    assert send.call_args[0][0].message == "".join(
        traceback.format_exception(etype, value, tb)
    )


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


def test_add_complex_fd_does_not_set_dirty(tmp_path, create_ac_mw):
    """
    There are many listeners that can pass undo=True, setting the undo stack
    dirty. Keep adding conditions here when discovered.
    """

    # Write file with a bunch fo stuff in it; add more when necessary
    scene = Scene(
        showAliases=True,
        hideNames=True,
        hideToolBars=True,
        hideEmotionalProcess=True,
        hideEmotionColors=True,
        hideDateSlider=True,
    )
    layer = Layer(name="Layer 1", storeGeometry=True)
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    twinA = Person(name="twinA")
    twinB = Person(name="twinB")
    marriage = Marriage(parentA, parentB)
    scene.addItems(layer, parentA, parentB, marriage, twinA, twinB)
    twinA.setParents(marriage)
    twinB.setParents(twinA.childOf)
    filePath = os.path.join(tmp_path, "some_family.fd")
    util.touchFD(filePath, bdata=pickle.dumps(scene.data()))

    ac, mw = create_ac_mw()
    mw.open(filePath=filePath)
    QApplication.instance().processEvents()
    assert mw.scene.stack().isClean() == True


def test_save_to_excel(tmp_path, create_ac_mw):
    FD_PATH = os.path.join(tmp_path, "documents", "some_family.fd")
    XLSX_PATH = FD_PATH.replace(".fd", ".xlsx")

    scene = Scene(items=(Person(name="Hey"), Person(name="You")))
    util.touchFD(FD_PATH, bdata=pickle.dumps(scene.data()))
    ac, mw = create_ac_mw()
    mw.prefs.setValue("lastFileSavePath", os.path.join(tmp_path, "some_prev_file.fd"))
    mw.open(filePath=FD_PATH)
    with mock.patch(
        "PyQt5.QtWidgets.QFileDialog.getSaveFileName",
        return_value=(XLSX_PATH, None),
    ) as getSaveFileName:
        with mock.patch.object(DocumentController, "writeExcel") as writeExcel:
            mw.saveAs()
    assert getSaveFileName.call_count == 1
    assert getSaveFileName.call_args[0] == (
        mw,
        "Save File",
        XLSX_PATH.replace(".xlsx", ""),
        util.SAVE_FILE_TYPES,
    )
    assert writeExcel.call_count == 1
    assert writeExcel.call_args[0][0] == XLSX_PATH
    assert len(writeExcel.call_args[0]) == 1
