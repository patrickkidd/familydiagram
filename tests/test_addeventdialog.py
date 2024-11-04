import pytest
from pkdiagram import util, Scene, Person, Qt, SceneModel
from pkdiagram.addeventdialog import AddEventDialog
from test_eventproperties import eventProps, runEventProperties, assertEventProperties


@pytest.fixture
def aed(qtbot, request, qmlEngine):
    scene = Scene()
    qmlEngine.setScene(scene)
    ret = AddEventDialog(qmlEngine)
    ret.setScene(scene)
    ret.show()
    ret.resize(600, 800)  # default size to small for elements to be clickable.

    qtbot.addWidget(ret)
    qtbot.waitActive(ret)

    yield ret

    ret.setScene(None)
    ret.hide()
    ret.deinit()
    scene.deinit()


def test_add_event_to_person(aed, eventProps):

    person = Person(name="Harold")
    aed.scene.addItem(person)

    assert aed.itemProp("event_doneButton", "text") == "Add"

    eventAdded = util.Condition()
    aed.scene.eventAdded.connect(eventAdded)
    assert aed.itemProp("nameBox", "currentIndex") == -1
    assert aed.itemProp("nameBox", "currentText") == ""
    assert aed.itemProp("stack", "enabled") == True
    runEventProperties(aed, eventProps, personName=person.name())
    assert eventAdded.callCount == 2

    event = eventAdded.callArgs[0][0]
    assertEventProperties(event, eventProps, personName=person.name())


def test_complaints(aed, qtbot, qmlEngine):

    qtbot.clickOkAfter(
        lambda: aed.mouseClick("event_doneButton"),
        text="You must set a valid date before adding an event.",
    )

    aed.focusItem("dateButtons.dateTextInput")
    aed.keyClick("dateButtons.dateTextInput", Qt.Key_Backspace)
    aed.keyClicks("dateButtons.dateTextInput", "01/02/2003", returnToFinish=False)

    qtbot.clickOkAfter(
        lambda: aed.mouseClick("event_doneButton"),
        text="You must set a parent before adding an event.",
    )

    scene = qmlEngine.sceneModel.scene
    person = Person(name="Person")
    scene.addItem(person)
    aed.clickComboBoxItem("nameBox", person.name())
    opened = aed.itemProp("nameBox", "opened")
    if opened:
        aed.findItem("nameBox").close()
    assert aed.itemProp("nameBox", "currentText") == person.name()

    qtbot.clickOkAfter(
        lambda: aed.mouseClick("event_doneButton"),
        text="You must add a description before adding an event.",
    )
    aed.keyClicks("descriptionEdit", "Some description", returnToFinish=False)

    aed.mouseClick("event_doneButton")
    assert scene.events()[1].parent is person
