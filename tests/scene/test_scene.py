import os, os.path, pickle

import pytest

from pkdiagram.pyqt import Qt, QGraphicsView, QPointF, QRectF, QDateTime
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Item,
    Person,
    Marriage,
    Emotion,
    Event,
    MultipleBirth,
    Layer,
    EventKind,
)
from pkdiagram.models import SceneLayerModel

pytestmark = [
    pytest.mark.component("Scene"),
    pytest.mark.depends_on("Item"),
]


# class AddPeopleTest(test_util.TestCase):

#     def setUp(self):
#         s = scene.Scene()

#     def tearDown(self):
#         s = None

#     def test_addPerson(self):
#         person = Person()
#         person.setName('Patrick')
#         s.addItem(person)
#         self.assertEqual(len(s.people()), 1)
#         self.assertEqual(s.people()[0], person)


def test_query_not_all_kwargs():
    scene = Scene()
    scene.addItems(
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
        Person(name="John", lastName="Smith"),
    )
    assert scene.query(lastName="Doe", nickName="Donny") == []


def test_query_multiple():
    scene = Scene()
    scene.addItems(
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
        Person(name="John", lastName="Smith"),
    )
    person1, person2 = scene.query(lastName="Doe")
    assert person1.name() == "John"
    assert person2.name() == "Jane"


def test_query_methods():
    people = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
        Person(name="John", lastName="Smith"),
    ]
    scene = Scene()
    scene.addItems(*people)
    people = scene.query(methods={"fullNameOrAlias": "John Doe"})
    assert len(people) == 1
    assert people[0].fullNameOrAlias() == "John Doe"


def test_find_by_ids():
    person_1 = Person(name="John", lastName="Doe")
    person_2 = Person(name="Jane", lastName="Doe")
    person_3 = Person(name="John", lastName="Smith")
    scene = Scene()
    scene.addItems(person_1, person_2, person_3)

    items = scene.find(ids=[person_1.id, person_2.id])
    assert len(items) == 2
    assert set(items) == {person_1, person_2}

    items = scene.find(ids=[person_1.id, person_2.id, person_3.id])
    assert len(items) == 3
    assert set(items) == {person_1, person_2, person_3}


def test_find_by_types(simpleScene):
    """ """
    people = simpleScene.find(types=Person)
    assert len(people) == 3

    people = simpleScene.find(types=[Person])
    assert len(people) == 3

    pairBonds = simpleScene.find(types=[Marriage])
    assert len(pairBonds) == 1


def test_find_by_tags(simpleScene):
    p1 = simpleScene.query1(name="p1")
    p = simpleScene.query1(name="p")
    p1.setTags(["hello"])
    p.setTags(["hello"])
    p1.birthEvent.setTags(["hello"])

    items = simpleScene.find(tags="hello")
    assert len(items) == 3

    items = simpleScene.find(tags=["hello"])
    assert len(items) == 3


def test_find_by_types_and_tags(simpleScene):
    p1 = simpleScene.query1(name="p1")
    p2 = simpleScene.query1(name="p2")
    p = simpleScene.query1(name="p")
    p1.setTags(["hello"])
    p.setTags(["hello"])
    p1.birthEvent.setTags(["hello"])

    items = simpleScene.find(tags="hello", types=Event)
    assert len(items) == 1

    items = simpleScene.find(tags=["hello"], types=Person)
    assert len(items) == 2


def test_undo_remove_child_selected(qtbot, simpleScene):
    """People and pair-bond were selected but not child items after delete and undo."""

    p = simpleScene.query(name="p")[0]
    p1 = simpleScene.query(name="p1")[0]
    p2 = simpleScene.query(name="p2")[0]
    m = p1.marriages[0]

    assert p.childOf is not None

    m.setSelected(True)
    p.setSelected(True)
    p1.setSelected(True)
    p2.setSelected(True)

    qtbot.clickYesAfter(lambda: simpleScene.removeSelection())
    simpleScene.undo()

    assert not m.isSelected()
    assert not p.isSelected()
    assert not p1.isSelected()
    assert not p2.isSelected()
    assert not p.childOf.isSelected()


def test_no_duplicate_events_from_file(simpleScene):
    for i, person in enumerate(simpleScene.people()):
        person.setBirthDateTime(util.Date(1900, 1, 1 + i))
    events = simpleScene.events()
    for event in events:
        assert events.count(event) == 1


def _test_copy_paste_twin(simpleScene):
    s = simpleScene
    p1 = s.query1(name="p1")
    p2 = s.query1(name="p2")
    p = s.query1(name="p")

    t1 = Person(name="t1")
    t2 = Person(name="t2")
    s.addItem(t1)
    s.addItem(t2)
    multipleBirth = MultipleBirth(p.parents())
    t1.setParents(multipleBirth=multipleBirth)
    t2.setParents(multipleBirth=multipleBirth)

    t1.setSelected(True)
    s.copy()
    s.paste()


def _test_copy_paste_with_multipleBirth_selected(simpleScene):
    s = simpleScene
    p1 = s.query1(name="p1")
    p2 = s.query1(name="p2")
    p = s.query1(name="p")

    t1 = Person(name="t1")
    t2 = Person(name="t2")
    s.addItem(t1)
    s.addItem(t2)
    multipleBirth = MultipleBirth(p.parents())
    t1.setParents(multipleBirth=multipleBirth)
    t2.setParents(multipleBirth=multipleBirth)

    t1.setSelected(True)
    multipleBirth.setSelected(True)
    s.copy()
    s.paste()


def test_hide_emotional_process(simpleScene):
    s = simpleScene

    p1 = s.query1(name="p1")
    p2 = s.query1(name="p2")
    p = s.query1(name="p")

    e1 = Emotion(p1, p2, kind=util.ITEM_CONFLICT)
    s.addItem(e1)
    e2 = Emotion(p2, p1, kind=util.ITEM_PROJECTION)
    s.addItem(e2)
    e3 = Emotion(p1, p, kind=util.ITEM_DISTANCE)
    s.addItem(e3)

    assert e1.isVisible() == True
    assert e2.isVisible() == True
    assert e3.isVisible() == True

    s.setHideEmotionalProcess(True)

    assert e1.isVisible() == False
    assert e2.isVisible() == False
    assert e3.isVisible() == False

    s.setHideEmotionalProcess(False)

    assert e1.isVisible() == True
    assert e2.isVisible() == True
    assert e3.isVisible() == True


def test_hide_names():
    scene = Scene()
    person = Person(name="Person A")
    person.setDiagramNotes(
        """A multi-line
string"""
    )
    person.birthEvent.setDateTime(util.Date(2001, 1, 1))
    scene.addItem(person)
    assert (
        person.detailsText.text()
        == """Person A
b. 01/01/2001
A multi-line
string"""
    )

    scene.setHideNames(True)
    assert (
        person.detailsText.text()
        == """b. 01/01/2001
A multi-line
string"""
    )

    scene.setHideNames(False)
    assert (
        person.detailsText.text()
        == """Person A
b. 01/01/2001
A multi-line
string"""
    )


def test_rename_tag_retains_tag_on_items():
    s = Scene()
    s.setTags(["aaa", "ccc", "ddd"])
    item = Item()
    s.addItem(item)
    item.setTags(["ddd"])

    s.renameTag("ddd", "bbb")

    assert s.tags() == ["aaa", "bbb", "ccc"]
    assert item.tags() == ["bbb"]


def test_add_events_sets_currentDateTime():
    scene = Scene()
    person = Person(name="Hey", lastName="You")
    scene.addItem(person)
    event_1 = Event(person, dateTime=util.Date(2001, 1, 1))
    assert scene.currentDateTime() == event_1.dateTime()

    event_2 = Event(person, dateTime=util.Date(2002, 1, 1))
    assert scene.currentDateTime() == event_2.dateTime()


def test_remove_last_event_sets_currentDateTime():
    person = Person(name="p1")
    event = Event(person, dateTime=util.Date(2001, 1, 1))
    scene = Scene()
    scene.addItem(person)
    assert scene.currentDateTime() == event.dateTime()

    event.setDateTime(QDateTime())
    assert scene.currentDateTime() == QDateTime()


def test_reset_last_built_event_event_sets_currentDateTime():
    person = Person(name="p1", birthDateTime=util.Date(2001, 1, 1))
    scene = Scene()
    scene.addItem(person)
    scene.addItem(person)
    assert scene.currentDateTime() == person.birthDateTime()

    person.setBirthDateTime(QDateTime())
    assert scene.currentDateTime() == QDateTime()


def test_addParentsToSelection_doesnt_reset_currentDateTime(qApp):
    scene = Scene()
    person = Person(name="Hey", lastName="You")
    scene.addItem(person)
    event = Event(person, dateTime=util.Date(2001, 1, 1))
    assert scene.currentDateTime() == event.dateTime()
    person.setSelected(True)
    scene.addParentsToSelection()
    assert scene.currentDateTime() == event.dateTime()


def test_init_has_clear_currentDateTime(qApp):
    assert Scene().currentDateTime().isNull()


def test_remove_all_events_clears_currentDateTime(qApp):
    scene = Scene()
    person = Person(name="Hey", lastName="You")
    scene.addItem(person)
    event_1 = Event(person, dateTime=util.Date(2001, 1, 1))
    assert scene.currentDateTime() == event_1.dateTime()

    scene.removeItem(event_1)
    assert Scene().currentDateTime().isNull()


def test_new_persons_get_current_layers():

    s = Scene()
    layer1 = Layer()
    s.addItem(layer1)
    p1 = Person(name="p1")
    assert p1.layers() == []

    layer1.setActive(True)
    assert layer1.id not in p1.layers()

    p2 = Person(name="p2")
    s.addItem(p2)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]

    layer2 = Layer(active=True)
    s.addItem(layer2)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]

    p3 = Person(name="p3")
    s.addItem(p3)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]
    assert p3.layers() == [layer1.id, layer2.id]

    layer1.setActive(False)
    p4 = Person(name="p4")
    s.addItem(p4)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]
    assert p3.layers() == [layer1.id, layer2.id]
    assert p4.layers() == [layer2.id]


def test_read():
    """Just try to break the most basic object constructors."""
    stuff = []

    def byId(id):
        return None

    data = {
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "events": [{"id": 2}],
                "parents": None,
                "marriages": [],
            }
        ]
    }

    scene = Scene()
    scene.read(data, byId)


# def test_read_fd():
#     """ Just test reading in an actual fd. """
#     with open(os.path.join(conftest.TIMELINE_TEST_FD, 'diagram.pickle'), 'rb') as f:
#         bdata = f.read()
#     scene = Scene()
#     data = pickle.loads(bdata)
#     assert scene.read(data) == None


def test_clean_stale_refs(data_root):
    with open(os.path.join(data_root, "stale-refs.fd/diagram.pickle"), "rb") as f:
        bdata = f.read()
    scene = Scene()
    data = pickle.loads(bdata)
    assert len(scene.prune(data)) == 9


def test_hasActiveLayers():
    scene = Scene()
    assert scene.hasActiveLayers == False

    layer = Layer(active=True)
    scene.addItem(layer)
    assert scene.hasActiveLayers == True

    layer.setActive(False)
    assert scene.hasActiveLayers == False


def __test_getPrintRect():  # was always changing by a few pixels...
    s = Scene()
    s.setTags(["NW", "NE", "SW", "SE"])
    northWest = Person(name="NW", pos=QPointF(-1000, -1000), tags=["NW"])
    northEast = Person(name="NE", pos=QPointF(1000, -1000), tags=["NE"])
    southWest = Person(name="SW", pos=QPointF(-1000, 1000), tags=["SW"])
    southEast = Person(name="SE", pos=QPointF(1000, 1000), tags=["SE"])
    s.addItems(northWest, northEast, southWest, southEast)

    fullRect = s.getPrintRect()
    assert fullRect == QRectF(-1162.5, -1181.25, 2407.5, 2343.75)

    nwRect = s.getPrintRect(forTags=["NW"])
    assert nwRect == QRectF(-1162.5, -1181.25, 417.5, 343.75)

    ## TODO: account for ChildOf, Emotions, and other Item's that don't have a layerPos()


def test_anonymize():
    scene = Scene()
    patrick = Person(name="Patrick", alias="Marco", notes="Patrick Bob")
    bob = Person(name="Bob", nickName="Robby", alias="John")
    e1 = Event(parent=patrick, description="Bob came home")
    e2 = Event(parent=patrick, description="robby came home, took Robby's place")
    e3 = Event(parent=bob, description="Patrick came home with bob")
    distance = Emotion(
        kind=util.ITEM_DISTANCE,
        personA=patrick,
        personB=bob,
        notes="""
Here is a story about Patrick
and Bob
and Robby robby
""",
    )
    scene.addItems(patrick, bob, distance)
    assert patrick.notes() == "Patrick Bob"
    assert e1.description() == "Bob came home"
    assert e2.description() == "robby came home, took Robby's place"
    assert e3.description() == "Patrick came home with bob"
    assert (
        distance.notes()
        == """
Here is a story about Patrick
and Bob
and Robby robby
"""
    )

    scene.setShowAliases(True)
    patrick.notes() == "[Marco] [John]"
    assert e1.description() == "[John] came home"
    assert e2.description() == "[John] came home, took [John]'s place"
    assert e3.description() == "[Marco] came home with [John]"
    assert (
        distance.notes()
        == """
Here is a story about [Marco]
and [John]
and [John] [John]
"""
    )


def test_layers():
    scene = Scene()
    layer1 = Layer(name="View 1", internal=True)
    layer2 = Layer(name="View 2", internal=True)
    layer3 = Layer(name="View 3")
    scene.addItems(layer1, layer2, layer3)
    assert scene.layers() == [layer1, layer2, layer3]


def test_layers_onlyInternal():
    scene = Scene()
    layer1 = Layer(name="View 1", internal=True)
    layer2 = Layer(name="View 2", internal=True)
    layer3 = Layer(name="View 3")
    scene.addItems(layer1, layer2, layer3)
    assert set(scene.layers(onlyInternal=True)) == set([layer1, layer2])


def test_layers_includeInternal():
    scene = Scene()
    layer1 = Layer(name="View 1", internal=True)
    layer2 = Layer(name="View 2", internal=True)
    layer3 = Layer(name="View 3")
    scene.addItems(layer1, layer2, layer3)
    assert set(scene.layers(includeInternal=False)) == set([layer3])


def test_layered_properties():
    """Ensure correct layered prop updates for marriage+marriage-indicators."""
    scene = Scene()
    male = Person(name="Male", kind="male")
    female = Person(name="Female", kind="female")
    marriage = Marriage(personA=male, personB=female)
    divorcedEvent = Event(
        parent=marriage,
        uniqueId=EventKind.Divorced.value,
        dateTime=util.Date(1900, 1, 1),
    )
    layer = Layer(name="View 1")
    scene.addItems(male, female, marriage, layer)
    #
    unlayered = {
        "male": QPointF(-100, -50),
        "maleDetails": QPointF(100, 100),
        "female": QPointF(100, -50),
        "femaleDetails": QPointF(-100, -200),
        "marriageSep": QPointF(100, 0),
        "marriageDetails": QPointF(-25, 0),
    }
    layered = {
        "male": QPointF(-200, -150),
        "maleDetails": QPointF(-100, -100),
        "female": QPointF(100, 50),
        "femaleDetails": QPointF(100, 200),
        "marriageSep": QPointF(100, 0),
        "marriageDetails": QPointF(25, -100),
    }
    # layered
    layer.setItemProperty(male.id, "itemPos", layered["male"])
    layer.setItemProperty(male.detailsText.id, "itemPos", layered["maleDetails"])
    layer.setItemProperty(female.id, "itemPos", layered["female"])
    layer.setItemProperty(female.detailsText.id, "itemPos", layered["femaleDetails"])
    layer.setItemProperty(
        marriage.detailsText.id, "itemPos", layered["marriageDetails"]
    )
    layer.setItemProperty(
        marriage.separationIndicator.id, "itemPos", layered["marriageSep"]
    )
    # unlayered
    male.setItemPos(unlayered["male"], undo=False)
    male.detailsText.setItemPos(unlayered["maleDetails"], undo=False)
    female.setItemPos(unlayered["female"], undo=False)
    female.detailsText.setItemPos(unlayered["femaleDetails"], undo=False)
    # marriage.setDivorced(True, undo=False)
    marriage.separationIndicator.setItemPos(unlayered["marriageSep"], undo=False)
    marriage.detailsText.setItemPos(unlayered["marriageDetails"], undo=False)

    assert male.pos() == unlayered["male"]
    assert male.detailsText.pos() == unlayered["maleDetails"]
    assert female.pos() == unlayered["female"]
    assert female.detailsText.pos() == unlayered["femaleDetails"]
    assert marriage.detailsText.pos() == unlayered["marriageDetails"]
    assert marriage.separationIndicator.pos() == unlayered["marriageSep"]

    layer.setActive(True)
    assert male.pos() == layered["male"]
    assert male.detailsText.pos() == layered["maleDetails"]
    assert female.pos() == layered["female"]
    assert female.detailsText.pos() == layered["femaleDetails"]
    assert marriage.detailsText.pos() == layered["marriageDetails"]
    assert marriage.separationIndicator.pos() == layered["marriageSep"]

    layer.setActive(False)
    assert male.pos() == unlayered["male"]
    assert male.detailsText.pos() == unlayered["maleDetails"]
    assert female.pos() == unlayered["female"]
    assert female.detailsText.pos() == unlayered["femaleDetails"]
    assert marriage.detailsText.pos() == unlayered["marriageDetails"]
    assert marriage.separationIndicator.pos() == unlayered["marriageSep"]

    layer.resetItemProperty(male.prop("itemPos"))
    layer.resetItemProperty(male.detailsText.prop("itemPos"))
    layer.resetItemProperty(female.prop("itemPos"))
    layer.resetItemProperty(female.detailsText.prop("itemPos"))
    layer.resetItemProperty(marriage.detailsText.prop("itemPos"))
    layer.resetItemProperty(marriage.separationIndicator.prop("itemPos"))
    layer.setActive(True)
    assert male.pos() == unlayered["male"]
    assert male.detailsText.pos() == unlayered["maleDetails"]
    assert female.pos() == unlayered["female"]
    assert female.detailsText.pos() == unlayered["femaleDetails"]
    assert marriage.detailsText.pos() == unlayered["marriageDetails"]
    assert marriage.separationIndicator.pos() == unlayered["marriageSep"]


def test_undo_add_remove_layered_item_props(qtbot):
    scene = Scene()
    male = Person(name="Male", kind="male")
    female = Person(name="Female", kind="female")
    marriage = Marriage(personA=male, personB=female)
    divorcedEvent = Event(
        parent=marriage,
        uniqueId=EventKind.Divorced.value,
        dateTime=util.Date(1900, 1, 1),
    )
    layer = Layer(name="View 1")
    scene.addItems(male, female, marriage, layer)
    #
    unlayered = {
        "male": QPointF(-100, -50),
        "maleDetails": QPointF(100, 100),
        "female": QPointF(100, -50),
        "femaleDetails": QPointF(-100, -200),
        "marriageSep": QPointF(100, 0),
        "marriageDetails": QPointF(-25, 0),
    }
    layered = {
        "male": QPointF(-200, -150),
        "maleDetails": QPointF(-100, -100),
        "female": QPointF(100, 50),
        "femaleDetails": QPointF(100, 200),
        "marriageSep": QPointF(100, 0),
        "marriageDetails": QPointF(25, -100),
    }
    # layered
    layer.setItemProperty(male.id, "itemPos", layered["male"])
    layer.setItemProperty(male.detailsText.id, "itemPos", layered["maleDetails"])
    layer.setItemProperty(female.id, "itemPos", layered["female"])
    layer.setItemProperty(female.detailsText.id, "itemPos", layered["femaleDetails"])
    layer.setItemProperty(
        marriage.detailsText.id, "itemPos", layered["marriageDetails"]
    )
    layer.setItemProperty(
        marriage.separationIndicator.id, "itemPos", layered["marriageSep"]
    )
    # unlayered
    male.setItemPos(unlayered["male"], undo=False)
    male.detailsText.setItemPos(unlayered["maleDetails"], undo=False)
    female.setItemPos(unlayered["female"], undo=False)
    female.detailsText.setItemPos(unlayered["femaleDetails"], undo=False)
    # marriage.setDivorced(True, undo=False)
    marriage.separationIndicator.setItemPos(unlayered["marriageSep"], undo=False)
    marriage.detailsText.setItemPos(unlayered["marriageDetails"], undo=False)
    assert len(scene.items()) == 24

    scene.selectAll()
    qtbot.clickYesAfter(lambda: scene.removeSelection())
    assert len(scene.items()) == 0

    scene.undo()
    assert len(scene.items()) == 24

    scene.redo()
    assert len(scene.items()) == 0


def test_read_write_layered_props():
    """Item.write was not explicitly requesting non-layered prop values."""
    scene = Scene()
    person = Person()
    layer = Layer(name="View 1", active=True)
    scene.addItems(person, layer)
    person.setLayers([layer.id])
    person.setItemPos(QPointF(10, 10))
    person.setColor("#ff0000")
    #
    data = {}
    scene.write(data)
    scene = Scene()
    scene.read(data)
    assert scene.people()[0].pos() == QPointF(10, 10)
    assert scene.people()[0].color() == "#ff0000"
    assert scene.people()[0].pen().color().name() == "#ff0000"

    scene.layers()[0].setActive(False)
    assert scene.people()[0].color() == None
    assert scene.people()[0].pen().color().name() == util.PEN.color().name()

    scene.layers()[0].setActive(True)
    assert scene.people()[0].color() == "#ff0000"
    assert scene.people()[0].pen().color().name() == "#ff0000"


def test_reset_layered_props():
    """Item.write was not explicitly requesting non-layered prop values."""
    scene = Scene()
    person = Person()
    layer = Layer(name="View 1", active=True, storeGeometry=True)
    scene.addItems(person, layer)
    person.setItemPos(QPointF(10, 10))
    assert layer.active() == True
    assert person.pos() == QPointF(10, 10)

    scene.resetAll()  # was throwing exception in commands.py
    assert person.itemPos() == QPointF()
    assert person.pos() == QPointF()


def test_exclusiveLayerSelection():
    scene = Scene()
    layerModel = SceneLayerModel()
    layerModel.scene = scene
    layerModel.items = [scene]
    layer1 = Layer(name="View 1", active=True)
    layer2 = Layer(name="View 2")
    scene.addItems(layer1, layer2)
    assert layer1.active() == True

    layerModel.setActiveExclusively(1)
    assert layer1.active() == False
    assert layer2.active() == True


def test_setPathItemVisible():
    scene = Scene(exclusiveLayerSelection=True)
    layer1 = Layer(name="View 1")
    layer2 = Layer(name="View 2")
    layer3 = Layer(name="View 3")
    layer4 = Layer(name="View 4")
    personA = Person(name="A")
    personB = Person(name="B")
    marriage = Marriage(personA=personA, personB=personB)
    divorcedEvent = Event(
        parent=marriage,
        uniqueId=EventKind.Divorced.value,
        dateTime=util.Date(1900, 1, 1),
    )
    scene.addItems(layer1, layer2, layer3, layer4, personA, personB, marriage)
    personA.setLayers([layer2.id, layer4.id])
    personB.setLayers([layer3.id])
    layerModel = SceneLayerModel()
    layerModel.scene = scene
    layerModel.items = [scene]
    OPACITY = 0.1
    personA.setItemOpacity(OPACITY, forLayers=[layer2, layer4])

    assert personA.opacity() == 1.0
    assert personB.opacity() == 1.0
    assert marriage.opacity() == 1.0
    assert personA.isVisible() == True
    assert personB.isVisible() == True
    assert marriage.isVisible() == True

    layerModel.setActiveExclusively(0)
    assert personA.opacity() == 0.0
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == False
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    # deemphasis and other marriage-person hidden should not show marriage
    layerModel.setActiveExclusively(1)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    layerModel.setActiveExclusively(2)
    assert personA.opacity() == 0.0
    assert personB.opacity() == 1.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == False
    assert personB.isVisible() == True
    assert marriage.isVisible() == False

    # deemphasis and other marriage-person hidden should not show marriage
    layerModel.setActiveExclusively(3)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    layerModel.setActiveExclusively(1)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False


def test_setPathItemVisible_2():
    scene = Scene(exclusiveLayerSelection=True)
    layer1 = Layer(name="View 1")
    layer2 = Layer(name="View 2")
    personA = Person(name="A")
    personB = Person(name="B")
    marriage = Marriage(personA=personA, personB=personB)
    divorcedEvent = Event(
        parent=marriage,
        uniqueId=EventKind.Divorced.value,
        dateTime=util.Date(1900, 1, 1),
    )
    scene.addItems(layer1, layer2, personA, personB, marriage)
    personA.setLayers([layer1.id, layer2.id])
    layerModel = SceneLayerModel()
    layerModel.scene = scene
    layerModel.items = [scene]
    OPACITY = 0.1
    personA.setItemOpacity(OPACITY, forLayers=[layer2])

    # Only personA shown, and at full opacity
    layerModel.setActiveExclusively(0)
    assert personA.opacity() == 1.0
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    # Only personA shown, and at partial opacity
    layerModel.setActiveExclusively(1)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False


def test_save_load_delete_items(qtbot):
    """ItemDetails and SeparationIndicator that were saved to disk were
    not retaining ids stored in the fd, causing addItem() to asign new ids.
    Then item properties in layers would be out of sync, etc.
    Fixed by not adding items until after read().
    """
    scene = Scene()
    person = Person()
    person.setDiagramNotes("here are some notes")
    scene.addItem(person)
    data = {}
    scene.write(data)
    bdata = pickle.dumps(data)
    #
    scene = Scene()
    scene.read(data)
    ## added to ensure that ItemDetails|SeparationIndicator id's match the id's in the file
    for id, item in scene.itemRegistry.items():
        assert id == item.id
    scene.selectAll()
    qtbot.clickYesAfter(lambda: scene.removeSelection())  # would throw exception


class View(QGraphicsView):
    def getVisibleSceneScaleRatio(self):
        return 1.0


def test_drag_create_emotion(qtbot):
    scene = Scene()
    view = View()
    view.resize(600, 800)
    view.show()
    view.setScene(scene)
    personA, personB = Person(name="A", pos=QPointF(50, 50)), Person(
        name="B", pos=QPointF(-50, 50)
    )
    scene.addItems(personA, personB)
    scene.setItemMode(util.ITEM_CONFLICT)
    qtbot.mousePress(
        view.viewport(), Qt.LeftButton, pos=view.mapFromScene(personA.pos())
    )
    qtbot.mouseMove(view.viewport(), view.mapFromScene(personA.pos() - personB.pos()))
    qtbot.mouseRelease(
        view.viewport(), Qt.LeftButton, pos=view.mapFromScene(personB.pos())
    )
    assert len(scene.emotions()) == 1
    emotion = scene.emotions()[0]
    assert emotion.personA() == personA
    assert emotion.personB() == personB
    assert emotion.kind() == util.ITEM_CONFLICT
