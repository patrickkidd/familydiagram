import pytest


pytest.skip(
    "All of these tests are for deprecated or removed features", allow_module_level=True
)


@pytest.mark.parametrize("state", ("dirty", "clean"))
@pytest.mark.parametrize("cancel_method", ("escape", "cancel"))
def test_cancel_add_event_escape(qtbot, dv, state, cancel_method):
    dv.ui.actionAdd_Event.trigger()
    if state == "dirty":
        dv.addEventDialog.keyClicks(
            "descriptionEdit", "asdasd", returnToFinish=False
        )  # set dirty
    assert dv.addEventDialog.shown == True
    if state == "dirty":
        if cancel_method == "escape":
            qtbot.clickYesAfter(
                lambda: QTest.keyClick(dv.addEventDialog, Qt.Key_Escape, Qt.NoModifier)
            )
        else:
            qtbot.clickYesAfter(lambda: dv.addEventDialog.mouseClick("cancelButton"))
    else:
        if cancel_method == "escape":
            QTest.keyClick(dv.addEventDialog, Qt.Key_Escape, Qt.NoModifier)
        else:
            dv.addEventDialog.mouseClick("cancelButton")
    assert dv.addEventDialog.shown == False
    assert dv.currentDrawer == None


def test_add_event_cancel_confirm_on_show_timeline(qtbot, dv):
    dv.ui.actionAdd_Event.triggered.emit()
    assert dv.currentDrawer is dv.addEventDialog

    # just to set dirty
    dv.addEventDialog.keyClicks(
        "descriptionEdit",
        "Some description",
        returnToFinish=False,  # Don't submit
    )
    # don't cancel
    qtbot.clickNoAfter(lambda: dv.ui.actionShow_Timeline.triggered.emit())
    assert dv.currentDrawer is dv.addEventDialog

    # cancel
    qtbot.clickYesAfter(lambda: dv.ui.actionShow_Timeline.triggered.emit())
    assert dv.currentDrawer is dv.caseProps


def test_add_emotion_cancel_confirm_on_show_timeline(qtbot, dv):
    dv.ui.actionAdd_Relationship.triggered.emit()
    assert dv.currentDrawer is dv.addEmotionDialog

    # just to set dirty
    dv.addEmotionDialog.clickComboBoxItem(
        "intensityBox", util.emotionIntensityNameForIntensity(2)
    )
    # don't cancel
    qtbot.clickNoAfter(lambda: dv.ui.actionShow_Timeline.triggered.emit())
    assert dv.currentDrawer is dv.addEmotionDialog

    # cancel
    qtbot.clickYesAfter(lambda: dv.ui.actionShow_Timeline.triggered.emit())
    assert dv.currentDrawer is dv.caseProps
