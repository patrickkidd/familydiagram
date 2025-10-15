import os, os.path, pickle

import pytest
from mock import patch

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
    ItemMode,
    RelationshipKind,
)
from pkdiagram.models import SceneLayerModel

pytestmark = [
    pytest.mark.component("Scene"),
    pytest.mark.depends_on("Item"),
]


## Init + File read / write


def test_init_has_clear_currentDateTime(qApp):
    assert Scene().currentDateTime().isNull()


def test_read():
    """Just try to break the most basic object constructors."""
    stuff = []

    def byId(id):
        return None

    data = {
        "people": [
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


def test_clean_stale_refs(data_root, scene):
    with open(os.path.join(data_root, "stale-refs.fd/diagram.pickle"), "rb") as f:
        bdata = f.read()
    data = pickle.loads(bdata)

    _orig_prune = Scene.prune
    numPruned = 0

    def prune(self, _data):
        nonlocal numPruned
        ret = _orig_prune(self, _data)
        numPruned = len(ret)
        return ret

    with patch(
        "pkdiagram.scene.Scene.prune", side_effect=prune, autospec=True
    ) as prune:
        scene.read(data)
    assert numPruned == 13

    newData = {}
    scene.write(newData)
    assert len(newData["pruned"]) == 13


def test_no_duplicate_events_from_file(simpleScene):
    for i, person in enumerate(simpleScene.people()):
        simpleScene.addItem(
            Event(EventKind.Birth, person, dateTime=util.Date(1900, 1, 1 + i))
        )
    events = simpleScene.events()
    for event in events:
        assert events.count(event) == 1


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


def __test_getPrintRect(scene):  # was always changing by a few pixels...
    s.setTags(["NW", "NE", "SW", "SE"])
    northWest = scene.addItem(Person(name="NW", pos=QPointF(-1000, -1000), tags=["NW"]))
    northEast = scene.addItem(Person(name="NE", pos=QPointF(1000, -1000), tags=["NE"]))
    southWest = scene.addItem(Person(name="SW", pos=QPointF(-1000, 1000), tags=["SW"]))
    southEast = scene.addItem(Person(name="SE", pos=QPointF(1000, 1000), tags=["SE"]))

    fullRect = s.getPrintRect()
    assert fullRect == QRectF(-1162.5, -1181.25, 2407.5, 2343.75)

    nwRect = s.getPrintRect(forTags=["NW"])
    assert nwRect == QRectF(-1162.5, -1181.25, 417.5, 343.75)

    ## TODO: account for ChildOf, Emotions, and other Item's that don't have a layerPos()


def test_anonymize(scene):
    patrick, bob = scene.addItems(
        Person(name="Patrick", alias="Marco", notes="Patrick Bob"),
        Person(name="Bob", nickName="Robby", alias="John"),
    )
    e1 = scene.addItem(Event(EventKind.Shift, patrick, description="Bob came home"))
    e2 = scene.addItem(
        Event(
            EventKind.Shift, patrick, description="robby came home, took Robby's place"
        )
    )
    e3 = scene.addItem(
        Event(EventKind.Shift, bob, description="Patrick came home with bob")
    )
    distance = scene.addItem(
        Emotion(
            RelationshipKind.Distance,
            bob,
            person=patrick,
            notes="""
Here is a story about Patrick
and Bob
and Robby robby
""",
        )
    )
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


#     assert (
#         distance.notes()
#         == """
# Here is a story about [Marco]
# and [John]
# and [John] [John]
# """
#     )


# test undo macro
