import logging

import pytest

from pkdiagram import util
from pkdiagram.scene import EventKind
from pkdiagram.mainwindow import MainWindow

from tests.views import TestAddAnythingDialog


_log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView", "AddAnythingDialog"),
]


def test_close_after_adding_lots(
    test_activation, test_user_diagrams, test_user, server_down, qtbot, create_ac_mw
):
    ac, mw = create_ac_mw()
    mw.new()
    mw.documentView.addAnythingDialog.checkInitQml()
    dlg = TestAddAnythingDialog(mw.documentView.addAnythingDialog)
    submitted = util.Condition(dlg.view.submitted)
    assert mw.scene != None
    qtbot.clickAndProcessEvents(mw.documentView.view.rightToolBar.addAnythingButton)
    assert mw.documentView.currentDrawer == dlg.view
    dlg.set_kind(EventKind.Birth)
    dlg.personPicker.set_new_person("John Doe")
    dlg.personAPicker.set_new_person("Joseph Doe")
    dlg.personBPicker.set_new_person("Josephina Doe")
    dlg.set_startDateTime(util.Date(2001, 1, 1))
    dlg.clickAddButton()
    assert submitted.callCount == 1

    johnDoe = mw.scene.query1(name="John", lastName="Doe")
    assert mw.documentView.currentDrawer == dlg.view
    dlg.set_kind(EventKind.Married)
    dlg.personAPicker.set_existing_person(johnDoe)
    dlg.personBPicker.set_new_person("Janet Dowery")
    dlg.set_startDateTime(util.Date(2001, 2, 3))
    dlg.clickAddButton()
    assert submitted.callCount == 2
    assert len(johnDoe.events()) == 1
    assert len(johnDoe.marriages) == 1
    assert len(johnDoe.marriages[0].events()) == 1

    DESCRIPTION = "asdasdsd ddd"
    dlg.set_kind(EventKind.CustomIndividual)
    dlg.peoplePicker.add_existing_person(johnDoe)
    dlg.set_startDateTime(util.Date(2010, 1, 1))
    dlg.set_description(DESCRIPTION)
    dlg.set_anxiety(util.VAR_VALUE_UP)
    dlg.clickAddButton()
    assert submitted.callCount == 3
    assert len(johnDoe.events()) == 2
    assert johnDoe.events()[1].uniqueId() == None

    qtbot.clickYesAfter(
        lambda: mw.closeDocument(), text=MainWindow.S_CONFIRM_SAVE_CHANGES
    )
