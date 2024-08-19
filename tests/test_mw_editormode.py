import logging

import pytest
import mock

from pkdiagram.pyqt import Qt, QWidget, QSize, QMainWindow
from pkdiagram import MainWindow
from pkdiagram.mainwindow_form import Ui_MainWindow
from pkdiagram.toolbars import SceneToolBar, RightToolBar, ItemToolBar

_log = logging.getLogger(__name__)


def assert_itemToolBar_InEditorMode(itemToolBar: ItemToolBar, on: bool):
    assert itemToolBar.isVisible() == on


def assert_sceneToolBar_InEditorMode(sceneToolBar: SceneToolBar, on: bool):
    assert sceneToolBar.isVisible() == True
    assert sceneToolBar.zoomFitButton.requestedVisible() == on
    assert sceneToolBar.dateSliderButton.requestedVisible() == on
    assert sceneToolBar.hideButton.requestedVisible() == on
    assert sceneToolBar.notesButton.requestedVisible() == on
    assert sceneToolBar.prevLayerButton.requestedVisible() == on
    assert sceneToolBar.nextLayerButton.requestedVisible() == on
    assert sceneToolBar.undoButton.requestedVisible() == on
    assert sceneToolBar.redoButton.requestedVisible() == on
    assert sceneToolBar.helpButton.requestedVisible() == on


def assert_rightToolBar_InEditorMode(rightToolBar: RightToolBar, on: bool):
    assert rightToolBar.isVisible() == True
    assert rightToolBar.timelineButton.requestedVisible() == on
    assert rightToolBar.settingsButton.requestedVisible() == on
    assert rightToolBar.detailsButton.requestedVisible() == on


def assert_mw_editorMode(mw: MainWindow, on: bool):
    assert mw.prefs.value("editorMode", defaultValue=False, type=bool) == on
    assert mw.ui.actionEditor_Mode.isChecked() == on
    assert_itemToolBar_InEditorMode(mw.documentView.view.itemToolBar, on)
    assert_sceneToolBar_InEditorMode(mw.documentView.view.sceneToolBar, on)
    assert_rightToolBar_InEditorMode(mw.documentView.view.rightToolBar, on)


@pytest.mark.parametrize(
    "prefs_editorMode, on", [(None, False), (True, True), (False, False)]
)
def test_prefs_mw_editorMode(create_ac_mw, prefs_editorMode, on):
    ac, mw = create_ac_mw(editorMode=prefs_editorMode)
    assert_mw_editorMode(mw, on)


@pytest.mark.parametrize("editorMode", [True, False])
def test_prefs_enable_disable_editorMode(qtbot, create_ac_mw, editorMode):
    ac, mw = create_ac_mw(editorMode=not editorMode)
    assert_mw_editorMode(mw, not editorMode)

    def _set():
        mw.prefsDialog.ui.editorModeBox.setChecked(editorMode)
        mw.prefsDialog.accept()

    qtbot.callAfter(lambda: mw.ui.actionPreferences.trigger(), _set)
    assert_mw_editorMode(mw, editorMode)


@pytest.fixture
def sceneToolBar(qApp):
    parent = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(parent)
    w = SceneToolBar(parent, ui)
    parent.show()
    yield w


@pytest.mark.parametrize("downloadAvailable", [True, False])
def test_downloadAvailable(sceneToolBar, downloadAvailable):
    with mock.patch.object(
        sceneToolBar.ui.actionInstall_Update,
        "isEnabled",
        return_value=downloadAvailable,
    ):
        sceneToolBar.onItemsVisibilityChanged()
    assert sceneToolBar.downloadUpdateButton.requestedVisible() == downloadAvailable


def test_sceneToolBar_responsive_all(sceneToolBar):
    sceneToolBar.ui.actionInstall_Update.setEnabled(True)
    sceneToolBar.ui.actionEditor_Mode.setChecked(True)
    sceneToolBar.adjust(QSize(1000, 600))
    assert sceneToolBar.isVisible() == True
    assert_sceneToolBar_InEditorMode(sceneToolBar, True)


@pytest.mark.parametrize("width", [800, 600, 400, 300, 250, 200, 150, 100])
def test_sceneToolBar_responsive_up_to_prevLayerButton(sceneToolBar, width):
    sceneToolBar.ui.actionEditor_Mode.setChecked(True)
    sceneToolBar.adjust(QSize(width, 600))
    w = sceneToolBar.prevLayerButton
    # shouldShow = bool(width >= 272 + sceneToolBar.RESPONSIVE_MARGIN * 2)
    # _log.info(
    #     f"width={width}, w.x()={w.x()}, w.width()={w.width()}, shouldShow={shouldShow}"
    # )
    assert sceneToolBar.isInBounds(w) == bool(width > 400)


def test_sceneToolBar_responsive_none(sceneToolBar):
    sceneToolBar.ui.actionEditor_Mode.setChecked(True)
    sceneToolBar.adjust(QSize(10, 10))
    assert sceneToolBar.isVisible() == False
