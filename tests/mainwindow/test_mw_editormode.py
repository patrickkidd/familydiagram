import logging

import pytest
import mock

from pkdiagram.pyqt import QSize, QMainWindow
from pkdiagram import MainWindow
from pkdiagram.mainwindow_form import Ui_MainWindow
from pkdiagram.toolbars import SceneToolBar, RightToolBar, ItemToolBar

_log = logging.getLogger(__name__)


pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView"),
]


def assert_itemToolBar_InEditorMode(itemToolBar: ItemToolBar, on: bool):
    assert itemToolBar.isVisible() == True
    assert itemToolBar.maleButton.requestedVisible() == True
    assert itemToolBar.femaleButton.requestedVisible() == True
    assert itemToolBar.marriageButton.requestedVisible() == True
    assert itemToolBar.childButton.requestedVisible() == True
    assert itemToolBar.parentsButton.requestedVisible() == True
    assert itemToolBar.sep1.requestedVisible() == on
    assert itemToolBar.distanceButton.requestedVisible() == on
    assert itemToolBar.conflictButton.requestedVisible() == on
    assert itemToolBar.reciprocityButton.requestedVisible() == on
    assert itemToolBar.projectionButton.requestedVisible() == on
    assert itemToolBar.sep2.requestedVisible() == on
    assert itemToolBar.cutoffButton.requestedVisible() == on
    assert itemToolBar.fusionButton.requestedVisible() == on
    assert itemToolBar.insideButton.requestedVisible() == on
    assert itemToolBar.outsideButton.requestedVisible() == on
    assert itemToolBar.sep3.requestedVisible() == on
    assert itemToolBar.towardButton.requestedVisible() == on
    assert itemToolBar.awayButton.requestedVisible() == on
    assert itemToolBar.definedSelfButton.requestedVisible() == on
    assert itemToolBar.sep4.requestedVisible() == on
    assert itemToolBar.calloutButton.requestedVisible() == on
    assert itemToolBar.pencilButton.requestedVisible() == on


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
    # assert rightToolBar.timelineButton.requestedVisible() == on
    assert rightToolBar.settingsButton.requestedVisible() == True
    assert rightToolBar.detailsButton.requestedVisible() == on


def assert_mw_editorMode(mw: MainWindow, on: bool):
    assert mw.prefs.value("editorMode", defaultValue=False, type=bool) == on
    assert mw.ui.actionEditor_Mode.isChecked() == on
    # assert mw.documentView.caseProps.itemProp("variablesBox", "visible") == on
    # assert mw.documentView.caseProps.itemProp("tagsAndLayersBox", "visible") == on
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
