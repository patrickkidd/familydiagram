import mock

from pkdiagram.pyqt import QDateTime, QMessageBox
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    PathItem,
    Event,
    Person,
    Marriage,
    ChildOf,
    MultipleBirth,
    Layer,
    EventKind,
)


def test_set_first_second_child():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    childA = Person(name="childA")
    childB = Person(name="childB")
    marriage = Marriage(personA=parentA, personB=parentB)
    scene.addItems(parentA, parentB, childA, childB, marriage)
    assert marriage.children == []
    assert childA.childOf == None
    assert childB.childOf == None

    childA.setParents(marriage)
    assert marriage.children == [childA]
    assert childA.parents() == marriage
    assert scene.find(childA.childOf.id) == childA.childOf
    assert scene.find(types=ChildOf) == [childA.childOf]
    assert scene.find(types=MultipleBirth) == []

    childB.setParents(marriage)
    assert marriage.children == [childA, childB]
    assert childB.parents() == marriage
    assert scene.find(childB.childOf.id) == childB.childOf
    assert scene.find(types=ChildOf) == [childA.childOf, childB.childOf]
    assert scene.find(types=MultipleBirth) == []

    childB.setParents(None)
    assert marriage.children == [childA]
    assert childB.childOf == None
    assert childB.parents() == None
    assert childA.parents() == marriage
    assert scene.find(types=ChildOf) == [childA.childOf]
    assert scene.find(types=MultipleBirth) == []

    childA.setParents(None)
    assert marriage.children == []
    assert childA.parents() == None
    assert childA.childOf == None
    assert scene.find(types=ChildOf) == []
    assert scene.find(types=MultipleBirth) == []


def test_MultipleBirth_set_second_via_ChildOf():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    tripletA = Person(name="tripletA")
    tripletB = Person(name="tripletB")
    tripletC = Person(name="tripletC")
    marriage = Marriage(personA=parentA, personB=parentB)
    scene.addItems(parentA, parentB, tripletA, tripletB, tripletC, marriage)
    tripletA.setParents(marriage)
    tripletB.setParents(tripletA.childOf)
    tripletC.setParents(tripletB.childOf)
    assert marriage.children == [tripletA, tripletB, tripletC]
    assert tripletA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == marriage
    assert tripletA.childOf != None
    assert tripletB.childOf != None
    assert tripletC.childOf != None
    assert tripletA.multipleBirth() != None
    assert tripletB.multipleBirth() == tripletB.multipleBirth()
    assert tripletC.multipleBirth() == tripletC.multipleBirth()
    assert tripletA.multipleBirth().children() == [tripletA, tripletB, tripletC]


def test_MultipleBirth_set_second_via_ChildOf_undo():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    tripletA = Person(name="tripletA")
    tripletB = Person(name="tripletB")
    tripletC = Person(name="tripletC")
    marriage = Marriage(personA=parentA, personB=parentB)
    scene.addItems(parentA, parentB, tripletA, tripletB, tripletC, marriage)
    tripletA.setParents(marriage)
    tripletB.setParents(tripletA.childOf)  # 0

    tripletC.setParents(tripletB.childOf, undo=True)  # 1
    assert marriage.children == [tripletA, tripletB, tripletC]
    assert tripletA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == marriage
    assert tripletA.childOf != None
    assert tripletB.childOf != None
    assert tripletC.childOf != None
    assert tripletA.multipleBirth() != None
    assert tripletB.multipleBirth() == tripletB.multipleBirth()
    assert tripletC.multipleBirth() == tripletC.multipleBirth()
    assert tripletA.multipleBirth().children() == [tripletA, tripletB, tripletC]

    scene.undo()  # 0
    marriage.children == [tripletA, tripletB]
    assert tripletA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == None
    assert tripletA.childOf != None
    assert tripletB.childOf != None
    assert tripletC.childOf == None
    assert tripletA.multipleBirth() != None
    assert tripletB.multipleBirth() == tripletB.multipleBirth()
    assert tripletC.multipleBirth() == None
    assert tripletA.multipleBirth().children() == [tripletA, tripletB]
    assert scene.find(types=MultipleBirth) == [tripletA.multipleBirth()]


def test_ChildOf_MultipleBirth_set_on_both():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    childA = Person(name="childA")
    tripletB = Person(name="tripletB")
    tripletC = Person(name="tripletC")
    tripletD = Person(name="tripletD")
    marriage = Marriage(personA=parentA, personB=parentB)
    scene.addItems(parentA, parentB, childA, tripletB, tripletC, tripletD, marriage)

    # add first normal child
    childA.setParents(marriage)
    assert marriage.children == [childA]
    assert childA.parents() == marriage
    assert scene.find(childA.childOf.id) == childA.childOf
    assert scene.find(types=MultipleBirth) == []
    assert scene.find(types=ChildOf) == [childA.childOf]

    # add second normal child
    tripletB.setParents(marriage)
    assert marriage.children == [childA, tripletB]
    assert childA.parents() == marriage
    assert tripletB.parents() == marriage
    assert scene.find(tripletB.childOf.id) == tripletB.childOf
    assert scene.find(types=MultipleBirth) == []
    assert scene.find(types=ChildOf) == [childA.childOf, tripletB.childOf]

    # add first multiple birth ** via ChildOf **
    tripletC.setParents(tripletB.childOf)
    assert marriage.children == [childA, tripletB, tripletC]
    assert childA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == marriage
    assert childA.multipleBirth() == None
    assert tripletB.multipleBirth() != None
    assert tripletB.multipleBirth() == tripletC.multipleBirth()
    assert tripletB.multipleBirth().children() == [tripletB, tripletC]
    assert tripletB.childOf == scene.find(tripletB.childOf.id)
    assert tripletB.multipleBirth() == scene.find(tripletB.multipleBirth().id)
    assert tripletC.childOf == scene.find(tripletC.childOf.id)
    assert tripletC.multipleBirth() == scene.find(tripletC.multipleBirth().id)
    assert scene.find(types=MultipleBirth) == [tripletB.multipleBirth()]
    assert scene.find(types=ChildOf) == [
        childA.childOf,
        tripletB.childOf,
        tripletC.childOf,
    ]

    # add second multiple birth ** via MultipleBirth **
    tripletD.setParents(tripletB.multipleBirth())
    assert marriage.children == [childA, tripletB, tripletC, tripletD]
    assert childA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == marriage
    assert tripletD.parents() == marriage
    assert childA.multipleBirth() == None
    assert tripletB.multipleBirth() != None
    assert tripletB.multipleBirth() == tripletC.multipleBirth()
    assert tripletB.multipleBirth() == tripletD.multipleBirth()
    assert tripletB.multipleBirth().children() == [tripletB, tripletC, tripletD]
    assert tripletB.childOf == scene.find(tripletB.childOf.id)
    assert tripletB.multipleBirth() == scene.find(tripletB.multipleBirth().id)
    assert tripletC.childOf == scene.find(tripletC.childOf.id)
    assert tripletC.multipleBirth() == scene.find(tripletC.multipleBirth().id)
    assert tripletD.childOf == scene.find(tripletD.childOf.id)
    assert tripletD.multipleBirth() == scene.find(tripletD.multipleBirth().id)
    assert scene.find(types=MultipleBirth) == [tripletB.multipleBirth()]
    assert scene.find(types=ChildOf) == [
        childA.childOf,
        tripletB.childOf,
        tripletC.childOf,
        tripletD.childOf,
    ]

    # remove third triplet
    tripletD.setParents(None)
    assert marriage.children == [childA, tripletB, tripletC]
    assert childA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == marriage
    assert tripletD.parents() == None
    assert childA.multipleBirth() == None
    assert tripletB.multipleBirth() != None
    assert tripletB.multipleBirth() == tripletC.multipleBirth()
    assert tripletB.multipleBirth().children() == [tripletB, tripletC]
    assert tripletB.childOf == scene.find(tripletB.childOf.id)
    assert tripletB.multipleBirth() == scene.find(tripletB.multipleBirth().id)
    assert tripletC.childOf == scene.find(tripletC.childOf.id)
    assert tripletC.multipleBirth() == scene.find(tripletC.multipleBirth().id)
    assert tripletD.childOf == None
    assert tripletD.multipleBirth() == None
    assert scene.find(types=MultipleBirth) == [tripletB.multipleBirth()]
    assert scene.find(types=ChildOf) == [
        childA.childOf,
        tripletB.childOf,
        tripletC.childOf,
    ]

    # remove second triplet
    tripletC.setParents(None)
    assert marriage.children == [childA, tripletB]
    assert childA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == None
    assert tripletD.parents() == None
    assert childA.multipleBirth() == None
    assert tripletB.multipleBirth() == None
    assert tripletB.childOf == scene.find(tripletB.childOf.id)
    assert tripletB.multipleBirth() == None
    assert tripletC.childOf == None
    assert tripletC.multipleBirth() == None
    assert tripletD.childOf == None
    assert tripletD.multipleBirth() == None
    assert scene.find(types=MultipleBirth) == []
    assert scene.find(types=ChildOf) == [childA.childOf, tripletB.childOf]

    # remove second child
    tripletB.setParents(None)
    assert marriage.children == [childA]
    assert childA.parents() == marriage
    assert tripletB.parents() == None
    assert tripletB.childOf == None
    assert tripletB.multipleBirth() == None
    assert scene.find(childA.childOf.id) == childA.childOf
    assert scene.find(types=MultipleBirth) == []
    assert scene.find(types=ChildOf) == [childA.childOf]

    childA.setParents(None)
    assert marriage.children == []
    assert childA.parents() == None
    assert scene.find(types=ChildOf) == []


def test_ChildOf_MultipleBirth_set_on_both_undo():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    childA = Person(name="childA")
    tripletB = Person(name="tripletB")
    tripletC = Person(name="tripletC")
    tripletD = Person(name="tripletD")
    marriage = Marriage(personA=parentA, personB=parentB)

    scene.addItems(
        parentA, parentB, childA, tripletB, tripletC, tripletD, marriage
    )  # 0

    # add first normal child
    childA.setParents(marriage, undo=True)  # 1
    assert marriage.children == [childA]
    assert childA.parents() == marriage
    assert scene.find(childA.childOf.id) == childA.childOf
    assert scene.find(types=MultipleBirth) == []
    assert scene.find(types=ChildOf) == [childA.childOf]

    # add second normal child
    tripletB.setParents(marriage, undo=True)  # 2
    assert marriage.children == [childA, tripletB]
    assert childA.parents() == marriage
    assert tripletB.parents() == marriage
    assert scene.find(tripletB.childOf.id) == tripletB.childOf
    assert scene.find(types=MultipleBirth) == []
    assert scene.find(types=ChildOf) == [childA.childOf, tripletB.childOf]

    # add first multiple birth ** via ChildOf **
    tripletC.setParents(tripletB.childOf, undo=True)  # 3
    assert marriage.children == [childA, tripletB, tripletC]
    assert childA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == marriage
    assert childA.multipleBirth() == None
    assert tripletB.multipleBirth() != None
    assert tripletB.multipleBirth() == tripletC.multipleBirth()
    assert tripletB.multipleBirth().children() == [tripletB, tripletC]
    assert tripletB.childOf == scene.find(tripletB.childOf.id)
    assert tripletB.multipleBirth() == scene.find(tripletB.multipleBirth().id)
    assert tripletC.childOf == scene.find(tripletC.childOf.id)
    assert tripletC.multipleBirth() == scene.find(tripletC.multipleBirth().id)
    assert scene.find(types=MultipleBirth) == [tripletB.multipleBirth()]
    assert scene.find(types=ChildOf) == [
        childA.childOf,
        tripletB.childOf,
        tripletC.childOf,
    ]

    # add second multiple birth ** via MultipleBirth **
    tripletD.setParents(tripletB.multipleBirth(), undo=True)  # 4
    assert marriage.children == [childA, tripletB, tripletC, tripletD]
    assert childA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == marriage
    assert tripletD.parents() == marriage
    assert childA.multipleBirth() == None
    assert tripletB.multipleBirth() != None
    assert tripletB.multipleBirth() == tripletC.multipleBirth()
    assert tripletB.multipleBirth() == tripletD.multipleBirth()
    assert tripletB.multipleBirth().children() == [tripletB, tripletC, tripletD]
    assert tripletB.childOf == scene.find(tripletB.childOf.id)
    assert tripletB.multipleBirth() == scene.find(tripletB.multipleBirth().id)
    assert tripletC.childOf == scene.find(tripletC.childOf.id)
    assert tripletC.multipleBirth() == scene.find(tripletC.multipleBirth().id)
    assert tripletD.childOf == scene.find(tripletD.childOf.id)
    assert tripletD.multipleBirth() == scene.find(tripletD.multipleBirth().id)
    assert scene.find(types=MultipleBirth) == [tripletB.multipleBirth()]
    assert scene.find(types=ChildOf) == [
        childA.childOf,
        tripletB.childOf,
        tripletC.childOf,
        tripletD.childOf,
    ]

    # remove third triplet
    tripletD.setParents(None, undo=True)  # 5
    assert marriage.children == [childA, tripletB, tripletC]
    assert childA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == marriage
    assert tripletD.parents() == None
    assert childA.multipleBirth() == None
    assert tripletB.multipleBirth() != None
    assert tripletB.multipleBirth() == tripletC.multipleBirth()
    assert tripletB.multipleBirth().children() == [tripletB, tripletC]
    assert tripletB.childOf == scene.find(tripletB.childOf.id)
    assert tripletB.multipleBirth() == scene.find(tripletB.multipleBirth().id)
    assert tripletC.childOf == scene.find(tripletC.childOf.id)
    assert tripletC.multipleBirth() == scene.find(tripletC.multipleBirth().id)
    assert tripletD.childOf == None
    assert tripletD.multipleBirth() == None
    assert scene.find(types=MultipleBirth) == [tripletB.multipleBirth()]
    assert scene.find(types=ChildOf) == [
        childA.childOf,
        tripletB.childOf,
        tripletC.childOf,
    ]

    # remove second triplet
    tripletC.setParents(None, undo=True)  # 6
    assert marriage.children == [childA, tripletB]
    assert childA.parents() == marriage
    assert tripletB.parents() == marriage
    assert tripletC.parents() == None
    assert tripletD.parents() == None
    assert childA.multipleBirth() == None
    assert tripletB.multipleBirth() == None
    assert tripletB.childOf == scene.find(tripletB.childOf.id)
    assert tripletB.multipleBirth() == None
    assert tripletC.childOf == None
    assert tripletC.multipleBirth() == None
    assert tripletD.childOf == None
    assert tripletD.multipleBirth() == None
    assert scene.find(types=MultipleBirth) == []
    assert scene.find(types=ChildOf) == [childA.childOf, tripletB.childOf]

    # remove second child
    tripletB.setParents(None, undo=True)  # 7
    assert marriage.children == [childA]
    assert childA.parents() == marriage
    assert tripletB.parents() == None
    assert tripletB.childOf == None
    assert tripletB.multipleBirth() == None
    assert scene.find(childA.childOf.id) == childA.childOf
    assert scene.find(types=MultipleBirth) == []
    assert scene.find(types=ChildOf) == [childA.childOf]

    childA.setParents(None, undo=True)  # 8
    assert marriage.children == []
    assert childA.parents() == None
    assert scene.find(types=ChildOf) == []


def test_ChildOf_set_reset_parents():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    marriageA = Marriage(personA=parentA, personB=parentB)
    parentC = Person(name="parentC")
    parentD = Person(name="parentD")
    marriageB = Marriage(personA=parentC, personB=parentD)
    child = Person(name="child")

    scene.addItems(parentA, parentB, marriageA, parentC, parentD, marriageB, child)
    assert marriageA.children == []
    assert marriageB.children == []

    child.setParents(marriageA)
    assert marriageA.children == [child]
    assert marriageB.children == []
    assert child.childOf != None
    assert child.childOf == scene.find(child.childOf.id)
    assert child.multipleBirth() == None
    assert scene.find(types=ChildOf) == [child.childOf]

    child.setParents(marriageB)
    assert marriageA.children == []
    assert marriageB.children == [child]
    assert child.childOf != None
    assert child.childOf == scene.find(child.childOf.id)
    assert child.multipleBirth() == None
    assert scene.find(types=ChildOf) == [child.childOf]

    child.setParents(None)
    assert marriageA.children == []
    assert marriageB.children == []
    assert scene.find(types=ChildOf) == []


def test_MultipleBirth_set_reset():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    childA = Person(name="childA")
    twinB = Person(name="twinB")
    twinC = Person(name="twinC")
    marriage = Marriage(personA=parentA, personB=parentB)
    scene.addItems(parentA, parentB, childA, twinB, twinC, marriage)

    childA.setParents(marriage)
    twinB.setParents(marriage)
    twinC.setParents(twinB.childOf)
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() == None
    assert twinB.multipleBirth() == twinC.multipleBirth()
    assert scene.find(types=MultipleBirth) == [twinB.multipleBirth()]

    twinC.setParents(childA.childOf)
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() != None
    assert childA.multipleBirth() == twinC.multipleBirth()
    assert twinB.multipleBirth() == None
    assert scene.find(types=MultipleBirth) == [childA.multipleBirth()]


def test_ChildOf_MultipleBirth_read_write():
    personA = Person(name="personA")
    personB = Person(name="personB")
    marriage = Marriage(personA=personA, personB=personB)
    childA = Person(name="childA")
    childB = Person(name="childB")
    twinC = Person(name="twinC")
    twinD = Person(name="twinD")
    childA.setParents(marriage)
    childB.setParents(marriage)
    twinC.setParents(marriage)
    twinD.setParents(twinC.childOf)
    scene = Scene()
    scene.addItems(personA, personB, marriage, childA, childB, twinC, twinD)
    data = {}
    scene.write(data)

    scene = Scene()
    scene.read(data)
    personA = scene.query1(name="personA")
    personB = scene.query1(name="personB")
    childA = scene.query1(name="childA")
    childB = scene.query1(name="childB")
    twinC = scene.query1(name="twinC")
    twinD = scene.query1(name="twinD")
    assert personA.parents() == None
    assert personB.parents() == None
    assert personA.multipleBirth() == personB.multipleBirth()
    assert childA.parents() != None
    assert childA.parents() == childB.parents()
    assert childA.parents() == personA.marriages[0]
    assert childA.parents() == personB.marriages[0]
    assert childA.childOf.parents() == childB.childOf.parents()
    assert childA.multipleBirth() == childB.multipleBirth()
    assert twinC.parents() == childB.parents()
    assert twinC.parents() == twinD.parents()
    assert twinC.multipleBirth() != None
    assert twinC.multipleBirth() == twinD.multipleBirth()
    assert twinC.childOf.parents() != None
    assert twinC.childOf.parents() == twinD.childOf.parents()
    assert twinC.multipleBirth().parents() != None
    assert twinC.multipleBirth().parents() == twinD.multipleBirth().parents()


def test_ChildOf_set_undo_redo():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    childA = Person(name="childA")
    marriage = Marriage(personA=parentA, personB=parentB)

    scene.addItems(parentA, parentB, childA, marriage)  # 0
    assert marriage.children == []
    assert childA.childOf == None
    assert childA.multipleBirth() == None

    childA.setParents(marriage, undo=True)  # 1
    assert marriage.children == [childA]
    assert childA.childOf != None
    assert childA.multipleBirth() == None
    assert childA.childOf.multipleBirth == None

    scene.undo()  # 0
    assert marriage.children == []
    assert childA.childOf == None
    assert childA.multipleBirth() == None

    scene.redo()  # 1
    assert marriage.children == [childA]
    assert childA.childOf != None
    assert childA.multipleBirth() == None
    assert childA.childOf.multipleBirth == None

    scene.undo()  # 0
    assert marriage.children == []
    assert childA.childOf == None
    assert childA.multipleBirth() == None


def test_MultipleBirth_undo_redo():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    twinA = Person(name="twinA")
    twinB = Person(name="twinB")
    marriage = Marriage(personA=parentA, personB=parentB)

    scene.addItems(parentA, parentB, twinA, twinB, marriage)  # 0
    assert marriage.children == []
    assert twinA.parents() == None
    assert twinA.childOf == None
    assert twinA.multipleBirth() == None
    assert twinB.parents() == None
    assert twinB.childOf == None
    assert twinB.multipleBirth() == None

    twinA.setParents(marriage, undo=True)  # 1
    assert marriage.children == [twinA]
    assert twinA.parents() == marriage
    assert twinA.childOf.multipleBirth == None
    assert twinA.multipleBirth() == None
    assert twinB.parents() == None
    assert twinB.childOf == None
    assert twinB.multipleBirth() == None

    twinB.setParents(twinA.childOf, undo=True)  # 2
    assert marriage.children == [twinA, twinB]
    assert twinA.parents() == marriage
    assert twinB.childOf.multipleBirth != None
    assert twinA.multipleBirth() != None
    assert twinB.parents() == marriage
    assert twinB.childOf != None
    assert twinB.childOf.multipleBirth == twinA.childOf.multipleBirth
    assert twinB.multipleBirth() == twinA.multipleBirth()

    scene.undo()  # 1
    assert marriage.children == [twinA]
    assert twinA.parents() == marriage
    assert twinA.childOf != None
    assert twinA.multipleBirth() == None
    assert twinB.parents() == None
    assert twinB.childOf == None
    assert twinB.multipleBirth() == None

    scene.redo()  # 2
    assert marriage.children == [twinA, twinB]
    assert twinA.parents() == marriage
    assert twinB.childOf.multipleBirth != None
    assert twinA.multipleBirth() != None
    assert twinB.parents() == marriage
    assert twinB.childOf != None
    assert twinB.childOf.multipleBirth == twinA.childOf.multipleBirth
    assert twinB.multipleBirth() == twinA.multipleBirth()

    scene.undo()  # 1
    assert marriage.children == [twinA]
    assert twinA.parents() == marriage
    assert twinA.childOf != None
    assert twinA.multipleBirth() == None
    assert twinB.parents() == None
    assert twinB.childOf == None
    assert twinB.multipleBirth() == None

    scene.undo()  # 0
    assert marriage.children == []
    assert twinA.parents() == None
    assert twinA.childOf == None
    assert twinA.multipleBirth() == None
    assert twinB.parents() == None
    assert twinB.childOf == None
    assert twinB.multipleBirth() == None


def test_MultipleBirth_set_move_undo_redo():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    childA = Person(name="childA")
    twinB = Person(name="twinB")
    twinC = Person(name="twinC")
    marriage = Marriage(personA=parentA, personB=parentB)
    childA.setParents(marriage)
    twinB.setParents(marriage)
    twinC.setParents(twinB.childOf)
    scene.addItems(parentA, parentB, childA, twinB, twinC, marriage)  # 0
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() == None
    assert twinB.multipleBirth() != None
    assert twinB.multipleBirth() == twinC.multipleBirth()
    assert scene.find(types=MultipleBirth) == [twinB.multipleBirth()]

    twinC.setParents(childA.childOf, undo=True)  # 1
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() != None
    assert childA.multipleBirth() == twinC.multipleBirth()
    assert twinB.multipleBirth() == None
    assert scene.find(types=MultipleBirth) == [childA.multipleBirth()]

    scene.undo()  # 0
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() == None
    assert twinB.multipleBirth() != None
    assert twinB.multipleBirth() == twinC.multipleBirth()
    assert scene.find(types=MultipleBirth) == [twinB.multipleBirth()]

    scene.redo()  # 1
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() != None
    assert childA.multipleBirth() == twinC.multipleBirth()
    assert twinB.multipleBirth() == None
    assert scene.find(types=MultipleBirth) == [childA.multipleBirth()]

    scene.undo()  # 0
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() == None
    assert twinB.multipleBirth() != None
    assert twinB.multipleBirth() == twinC.multipleBirth()
    assert scene.find(types=MultipleBirth) == [twinB.multipleBirth()]


def test_ChildOf_MultipleBirth_undo_redo_integration():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    childA = Person(name="childA")
    twinB = Person(name="twinB")
    twinC = Person(name="twinC")
    marriage = Marriage(personA=parentA, personB=parentB)

    scene.addItems(parentA, parentB, childA, twinB, twinC, marriage)  # 0
    assert marriage.children == []
    assert childA.multipleBirth() == None
    assert twinB.multipleBirth() == None
    assert twinC.multipleBirth() == None
    assert childA.parents() == None
    assert twinB.parents() == None
    assert twinC.parents() == None
    assert scene.find(types=ChildOf) == []
    assert scene.find(types=MultipleBirth) == []

    childA.setParents(marriage, undo=True)  # 1
    twinB.setParents(marriage, undo=True)  # 2
    twinC.setParents(twinB.childOf, undo=True)  # 3
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() == None
    assert twinB.multipleBirth() != None
    assert twinB.multipleBirth() == twinC.multipleBirth()
    assert scene.find(types=MultipleBirth) == [twinB.multipleBirth()]

    twinC.setParents(childA.childOf, undo=True)  # 4
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() != None
    assert childA.multipleBirth() == twinC.multipleBirth()
    assert twinB.multipleBirth() == None
    assert scene.find(types=MultipleBirth) == [childA.multipleBirth()]

    scene.removeItem(twinC.multipleBirth(), undo=True)  # 5
    assert marriage.children == [twinB]
    assert childA.parents() == None
    assert twinB.parents() == marriage
    assert twinC.parents() == None
    assert childA.multipleBirth() == None
    assert twinB.multipleBirth() == None
    assert twinC.multipleBirth() == None
    assert scene.find(types=MultipleBirth) == []
    assert scene.find(types=ChildOf) == [twinB.childOf]

    scene.undo()  # 4
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() != None
    assert childA.multipleBirth() == twinC.multipleBirth()
    assert twinB.multipleBirth() == None
    assert scene.find(types=MultipleBirth) == [childA.multipleBirth()]

    scene.undo()  # 3
    assert marriage.children == [childA, twinB, twinC]
    assert childA.multipleBirth() == None
    assert twinB.multipleBirth() != None
    assert twinB.multipleBirth() == twinC.multipleBirth()
    assert scene.find(types=MultipleBirth) == [twinB.multipleBirth()]

    scene.undo()  # 2
    assert marriage.children == [childA, twinB]
    assert twinB.multipleBirth() == None
    assert twinC.multipleBirth() == None
    assert twinB.parents() == marriage
    assert twinC.parents() == None
    assert scene.find(types=ChildOf) == [childA.childOf, twinB.childOf]
    assert scene.find(types=MultipleBirth) == []

    scene.undo()  # 1
    assert marriage.children == [childA]
    assert twinB.multipleBirth() == None
    assert twinC.multipleBirth() == None
    assert twinB.parents() == None
    assert twinC.parents() == None
    assert scene.find(types=ChildOf) == [childA.childOf]
    assert scene.find(types=MultipleBirth) == []

    scene.undo()  # 0
    assert marriage.children == []
    assert twinB.multipleBirth() == None
    assert twinC.multipleBirth() == None
    assert twinB.parents() == None
    assert twinC.parents() == None
    assert scene.find(types=ChildOf) == []
    assert scene.find(types=MultipleBirth) == []


def test_ChildOf_delete_undo_redo(qtbot):
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    twinA = Person(name="twinA")
    twinB = Person(name="twinB")
    marriage = Marriage(parentA, parentB)
    marriedEvent = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=QDateTime(util.Date(1900, 1, 1)),
    )
    twinA.setParents(marriage)
    twinB.setParents(twinA.childOf)
    scene.addItems(parentA, parentB, marriage, twinA, twinB)  # 0

    twinA.childOf.setSelected(True)
    qtbot.clickYesAfter(lambda: scene.removeSelection())  # 1
    assert marriage.children == [twinB]
    assert twinA.parents() == None
    assert twinB.parents() == marriage
    assert twinA.childOf == None
    assert twinA.multipleBirth() == None
    assert twinA.multipleBirth() == twinB.multipleBirth()
    assert scene.find(types=[ChildOf]) == [twinB.childOf]
    assert scene.find(types=[MultipleBirth]) == []

    scene.undo()  # 0
    assert marriage.children == [twinA, twinB]
    assert twinA.childOf != None
    assert twinA.multipleBirth() != None
    assert twinA.multipleBirth() == twinB.multipleBirth()
    assert twinA.parents() == marriage
    assert twinB.parents() == marriage

    scene.redo()  # 1
    assert marriage.children == [twinB]
    assert twinA.parents() == None
    assert twinB.parents() == marriage
    assert twinA.childOf == None
    assert twinA.multipleBirth() == None
    assert twinA.multipleBirth() == twinB.multipleBirth()
    assert scene.find(types=[ChildOf]) == [twinB.childOf]
    assert scene.find(types=[MultipleBirth]) == []

    scene.undo()  # 0
    assert marriage.children == [twinA, twinB]
    assert twinA.childOf != None
    assert twinA.multipleBirth() != None
    assert twinA.multipleBirth() == twinB.multipleBirth()
    assert twinA.parents() == marriage
    assert twinB.parents() == marriage


def test_MultipleBirth_delete_undo_redo(qtbot):

    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    twinA = Person(name="twinA")
    twinB = Person(name="twinB")
    marriage = Marriage(parentA, parentB)
    marriedEvent = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=QDateTime(util.Date(1900, 1, 1)),
    )
    twinA.setParents(marriage)
    twinB.setParents(twinA.childOf)
    scene.addItems(parentA, parentB, marriage, twinA, twinB)  # 0

    twinA.multipleBirth().setSelected(True)
    qtbot.clickYesAfter(lambda: scene.removeSelection())  # 1
    assert marriage.children == []
    assert twinA.parents() == None
    assert twinB.parents() == None
    assert twinA.childOf == None
    assert twinA.multipleBirth() == None
    assert twinA.multipleBirth() == twinB.multipleBirth()
    assert scene.find(types=[ChildOf, MultipleBirth]) == []

    scene.undo()  # 0
    assert marriage.children == [twinA, twinB]
    assert twinA.childOf != None
    assert twinA.multipleBirth() != None
    assert twinA.multipleBirth() == twinB.multipleBirth()
    assert twinA.parents() == marriage
    assert twinB.parents() == marriage
    assert scene.find(types=[ChildOf]) == [twinA.childOf, twinB.childOf]
    assert scene.find(types=[MultipleBirth]) == [twinA.multipleBirth()]

    scene.redo()  # 1
    assert marriage.children == []
    assert twinA.parents() == None
    assert twinB.parents() == None
    assert twinA.childOf == None
    assert twinA.multipleBirth() == None
    assert twinA.multipleBirth() == twinB.multipleBirth()
    assert scene.find(types=[ChildOf, MultipleBirth]) == []

    scene.undo()  # 0
    assert marriage.children == [twinA, twinB]
    assert twinA.childOf != None
    assert twinA.multipleBirth() != None
    assert twinA.multipleBirth() == twinB.multipleBirth()
    assert twinA.parents() == marriage
    assert twinB.parents() == marriage
    assert scene.find(types=[ChildOf]) == [twinA.childOf, twinB.childOf]
    assert scene.find(types=[MultipleBirth]) == [twinA.multipleBirth()]


def test_hide_ChildOf_honor_marriage_tags():
    scene = Scene(tags=["here"])
    parentA = Person(name="parentA", tags=["here"])
    parentB = Person(name="parentB")
    childA = Person(name="childA")
    marriage = Marriage(parentA, parentB)
    marriedEvent = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=util.Date(1900, 1, 1),
    )
    layer = Layer(name="View 1", tags=["here"])
    childA.setParents(marriage)

    # assert childA.shouldShowFor(QDateTime(), tags=['here']) == True

    scene.addItems(parentA, parentB, marriage, childA, layer)
    assert scene.find(types=ChildOf) == [childA.childOf]
    assert childA.childOf != None
    assert childA.childOf.isVisible() == True

    layer.setActive(True)
    assert childA.childOf != None
    assert childA.childOf.isVisible() == False

    layer.setActive(False)
    assert childA.childOf != None
    assert childA.childOf.isVisible() == True


def test_multiple_ChildOf_in_MultipleBirth_delete_undo(qtbot):
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    twinA = Person(name="twinA")
    twinB = Person(name="twinB")
    twinC = Person(name="twinC")
    marriage = Marriage(parentA, parentB)
    marriedEvent = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=util.Date(1900, 1, 1),
    )
    twinA.setParents(marriage)
    twinB.setParents(twinA.childOf)
    twinC.setParents(twinB.multipleBirth())
    scene.addItems(parentA, parentB, marriage, twinA, twinB, twinC)  # 0

    twinA.childOf.setSelected(True)
    twinC.childOf.setSelected(True)
    qtbot.clickYesAfter(lambda: scene.removeSelection())  # 1
    assert len(scene.find(types=MultipleBirth)) == 0
    assert len(scene.find(types=ChildOf)) == 1
    assert len(scene.find(types=Person)) == 5

    scene.undo()  # 0
    assert len(scene.find(types=MultipleBirth)) == 1
    assert len(scene.find(types=ChildOf)) == 3
    assert len(scene.find(types=Person)) == 5


def test_ChildOf_in_MultipleBirth_delete_undo(qtbot):
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    twinA = Person(name="twinA")
    twinB = Person(name="twinB")
    marriage = Marriage(parentA, parentB)
    marriedEvent = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=util.Date(1900, 1, 1),
    )
    twinA.setParents(marriage)
    twinB.setParents(twinA.childOf)
    scene.addItems(parentA, parentB, marriage, twinA, twinB)  # 0

    twinA.childOf.setSelected(True)
    qtbot.clickYesAfter(lambda: scene.removeSelection())  # 1
    assert len(scene.find(types=MultipleBirth)) == 0
    assert len(scene.find(types=ChildOf)) == 1
    assert len(scene.find(types=Person)) == 4

    scene.undo()  # 0
    assert len(scene.find(types=MultipleBirth)) == 1
    assert len(scene.find(types=ChildOf)) == 2
    assert len(scene.find(types=Person)) == 4


def test_MultipleBirth_pathFor_hidden_person():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    twinA = Person(name="twinA")
    twinB = Person(name="twinB")
    marriage = Marriage(parentA, parentB)
    twinA.setParents(marriage)
    twinB.setParents(twinA.childOf)
    scene.addItems(parentA, parentB, marriage, twinA, twinB)  # 0

    twinB.hide()
    twinB.childOf.updateGeometry()
