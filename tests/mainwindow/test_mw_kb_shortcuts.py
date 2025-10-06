import pytest

from pkdiagram.pyqt import Qt
from pkdiagram import util
from pkdiagram.scene import Person, Marriage, Emotion
from pkdiagram.documentview import RightDrawerView

pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView"),
]


def test_person_kb_shortcut_item(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()

    person = Person()
    mw.scene.addItems(person)
    assert mw.documentView.personProps.isVisible() == False
    assert mw.documentView.personProps.currentTab() == "item"

    person.setSelected(True)
    qtbot.keyClick(mw, Qt.Key_I, Qt.ShiftModifier | Qt.ControlModifier)
    assert mw.documentView.personProps.isVisible() == True
    assert mw.documentView.personProps.currentTab() == "item"


def test_person_kb_shortcut_notes(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()

    person = Person()
    mw.scene.addItems(person)
    assert mw.documentView.personProps.isVisible() == False
    assert mw.documentView.personProps.currentTab() == "item"

    person.setSelected(True)
    qtbot.keyClick(mw, Qt.Key_N, Qt.ShiftModifier | Qt.ControlModifier)
    assert mw.documentView.personProps.isVisible() == True
    assert mw.documentView.personProps.currentTab() == "notes"


def test_person_kb_shortcut_timeline(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()

    person = Person()
    mw.scene.addItems(person)
    assert mw.documentView.personProps.isVisible() == False
    assert mw.documentView.personProps.currentTab() == "item"

    person.setSelected(True)
    qtbot.keyClick(mw, Qt.Key_T, Qt.ShiftModifier | Qt.ControlModifier)
    assert mw.documentView.personProps.isVisible() == True
    assert mw.documentView.personProps.currentTab() == "item"


def test_marriage_kb_shortcut_item(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()

    personA, personB = Person(), Person()
    marriage = Marriage(personA, personB)
    mw.scene.addItems(personA, personB, marriage)
    assert mw.documentView.marriageProps.isVisible() == False
    assert mw.documentView.marriageProps.currentTab() == "item"

    marriage.setSelected(True)
    qtbot.keyClick(mw, Qt.Key_I, Qt.ShiftModifier | Qt.ControlModifier)
    assert mw.documentView.marriageProps.isVisible() == True
    assert mw.documentView.marriageProps.currentTab() == "item"


def test_marriage_kb_shortcut_notes(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()

    personA, personB = Person(), Person()
    marriage = Marriage(personA, personB)
    mw.scene.addItems(personA, personB, marriage)
    assert mw.documentView.marriageProps.isVisible() == False
    assert mw.documentView.marriageProps.currentTab() == "item"

    marriage.setSelected(True)
    qtbot.keyClick(mw, Qt.Key_N, Qt.ShiftModifier | Qt.ControlModifier)
    assert mw.documentView.marriageProps.isVisible() == True
    assert mw.documentView.marriageProps.currentTab() == "notes"


def test_marriage_kb_shortcut_timeline(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()

    personA, personB = Person(), Person()
    marriage = Marriage(personA, personB)
    mw.scene.addItems(personA, personB, marriage)
    assert mw.documentView.marriageProps.isVisible() == False
    assert mw.documentView.marriageProps.currentTab() == "item"

    marriage.setSelected(True)
    qtbot.keyClick(mw, Qt.Key_T, Qt.ShiftModifier | Qt.ControlModifier)
    assert mw.documentView.marriageProps.isVisible() == True
    assert mw.documentView.marriageProps.currentTab() == "item"


def test_emotion_kb_shortcut_item(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()

    personA, personB = Person(), Person()
    conflict = Emotion(personA=personA, personB=personB, kind=util.ITEM_CONFLICT)
    mw.scene.addItems(personA, personB, conflict)
    assert mw.documentView.emotionProps.isVisible() == False
    assert mw.documentView.emotionProps.currentTab() == "item"

    conflict.setSelected(True)
    qtbot.keyClick(mw, Qt.Key_I, Qt.ShiftModifier | Qt.ControlModifier)
    assert mw.documentView.emotionProps.isVisible() == True
    assert mw.documentView.emotionProps.currentTab() == "item"


def test_emotion_kb_shortcut_notes(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()

    personA, personB = Person(), Person()
    conflict = Emotion(personA=personA, personB=personB, kind=util.ITEM_CONFLICT)
    mw.scene.addItems(personA, personB, conflict)
    assert mw.documentView.emotionProps.isVisible() == False
    assert mw.documentView.emotionProps.currentTab() == "item"

    conflict.setSelected(True)
    qtbot.keyClick(mw, Qt.Key_N, Qt.ShiftModifier | Qt.ControlModifier)
    assert mw.documentView.emotionProps.isVisible() == True
    assert mw.documentView.emotionProps.currentTab() == "notes"


def test_emotion_kb_shortcut_meta(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()

    personA, personB = Person(), Person()
    conflict = Emotion(personA=personA, personB=personB, kind=util.ITEM_CONFLICT)
    mw.scene.addItems(personA, personB, conflict)
    assert mw.documentView.emotionProps.isVisible() == False
    assert mw.documentView.emotionProps.currentTab() == "item"

    conflict.setSelected(True)
    qtbot.keyClick(mw, Qt.Key_M, Qt.ShiftModifier | Qt.ControlModifier)
    assert mw.documentView.emotionProps.isVisible() == True
    assert mw.documentView.emotionProps.currentTab() == "meta"
