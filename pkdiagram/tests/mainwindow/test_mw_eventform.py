import logging

import pytest

from btcopilot.schema import VariableShift, EventKind
from pkdiagram import util
from pkdiagram.mainwindow import MainWindow

from pkdiagram.tests.views import TestEventForm


_log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView", "EventForm"),
]


def test_close_after_adding_lots(
    test_activation, test_user_diagrams, test_user, server_down, qtbot, create_ac_mw
):
    ac, mw = create_ac_mw()
    mw.new()
    mw.documentView.eventFormDrawer.checkInitQml()
    dlg = TestEventForm(mw.documentView.eventFormDrawer)
    assert mw.scene != None
    qtbot.clickAndProcessEvents(mw.documentView.view.rightToolBar.addAnythingButton)
    assert mw.documentView.currentDrawer == dlg.view
    dlg.set_kind(EventKind.Birth)
    dlg.personPicker.set_new_person("John Doe")
    dlg.spousePicker.set_new_person("Joseph Doe")
    dlg.childPicker.set_new_person("Josephina Doe")
    dlg.set_startDateTime(util.Date(2001, 1, 1))
    dlg.clickSaveButton()

    johnDoe = mw.scene.query1(name="John", lastName="Doe")
    assert mw.documentView.currentDrawer == dlg.view
    dlg.set_kind(EventKind.Married)
    dlg.personPicker.set_existing_person(johnDoe)
    dlg.spousePicker.set_new_person("Janet Dowery")
    dlg.set_startDateTime(util.Date(2001, 2, 3))
    dlg.clickSaveButton()
    assert len(johnDoe.marriages) == 2
    assert len(mw.scene.eventsFor(johnDoe.marriages[1])) == 1

    dlg.set_kind(EventKind.Shift)
    dlg.personPicker.set_existing_person(johnDoe)
    dlg.set_startDateTime(util.Date(2010, 1, 1))
    dlg.set_description("asdasdsd ddd")
    dlg.set_anxiety(VariableShift.Up)
    dlg.clickSaveButton()
    assert len(mw.scene.eventsFor(johnDoe)) == 3
    assert mw.scene.eventsFor(johnDoe)[2].kind() == EventKind.Shift
    assert len(mw.scene.eventsFor(johnDoe.marriages[1])) == 1

    qtbot.clickYesAfter(
        lambda: mw.closeDocument(), text=MainWindow.S_CONFIRM_SAVE_CHANGES
    )
