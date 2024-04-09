import logging

from pkdiagram import util, EventKind, MainWindow
from pkdiagram.widgets.qml.personpicker import set_new_person, set_existing_person
from pkdiagram.widgets.qml.peoplepicker import add_new_person, add_existing_person


_log = logging.getLogger(__name__)


def test_close_after_adding_lots(
    test_activation, test_user_diagrams, test_user, server_down, qtbot, create_ac_mw
):
    ac, mw = create_ac_mw()
    mw.show()
    mw.new()
    dlg = mw.documentView.addAnythingDialog
    submitted = util.Condition(dlg.submitted)
    assert mw.scene != None
    qtbot.mouseClick(mw.documentView.view.rightToolBar.addAnythingButton)
    assert mw.documentView.currentDrawer == dlg
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_new_person("personAPicker", "Joseph Doe")
    dlg.set_new_person("personBPicker", "Josephina Doe")
    dlg.set_startDateTime(util.Date(2001, 1, 1))
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1

    johnDoe = mw.scene.query1(name="John", lastName="Doe")
    # qtbot.mouseClick(mw.documentView.view.rightToolBar.addAnythingButton)
    assert mw.documentView.currentDrawer == dlg
    dlg.set_kind(EventKind.Married)
    dlg.set_existing_person("personAPicker", johnDoe)
    dlg.set_new_person("personBPicker", "Janet Dowery")
    dlg.set_startDateTime(util.Date(2001, 1, 1))
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 2

    qtbot.clickYesAfter(
        lambda: mw.closeDocument(), text=MainWindow.S_CONFIRM_SAVE_CHANGES
    )
