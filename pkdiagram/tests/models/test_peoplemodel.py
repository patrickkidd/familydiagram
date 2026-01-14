import pytest

from pkdiagram import util
from pkdiagram.scene import Scene, Person
from pkdiagram.models import PeopleModel


@pytest.fixture
def model(scene):
    _model = PeopleModel()
    _model.scene = scene
    return _model


def sortedPeople(scene):
    return sorted(
        [p for p in scene.people() if p.fullNameOrAlias()],
        key=lambda x: x.fullNameOrAlias(),
    )


def sortedNames(scene):
    return [p.fullNameOrAlias() for p in sortedPeople(scene)]


def find(scene, name):
    for i, p in enumerate(sortedPeople(scene)):
        if p.name() == name:
            return i


def test_init(scene, model):
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    people = sortedPeople(scene)
    assert len(people) > 0
    assert model.rowCount() == len(people)

    names = sortedNames(scene)
    for row in range(model.rowCount()):
        index = model.index(row, 0)
        assert model.data(index) == names[row]


def test_add_person(scene, model):

    beforeRows = model.rowCount()
    person = scene.addItem(Person(name="Yo"))
    assert model.rowCount() == beforeRows + 1

    # shouldn't increase row count
    person = scene.addItem(Person())
    assert model.rowCount() == beforeRows + 1


def test_remove_person(scene, model):
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))

    beforeRows = model.rowCount()
    assert beforeRows > 0

    scene.removeItem(scene.people()[0])
    assert model.rowCount() == beforeRows - 1


def test_change_person(scene, model):

    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))

    aBeforeIndex = find(scene, "A")
    bBeforeIndex = find(scene, "B")
    assert aBeforeIndex < bBeforeIndex

    personA.setName("C")
    aAfterIndex = find(scene, "C")
    bAfterIndex = find(scene, "B")
    assert aAfterIndex != aBeforeIndex
    assert bAfterIndex != bBeforeIndex
    assert aAfterIndex > bAfterIndex


def test_set_existing_persons_name(scene, model):

    rowsInserted = util.Condition(model.rowsInserted)
    personA = Person()
    scene.addItem(personA)
    assert rowsInserted.callCount == 0

    personA.setName("A")
    assert rowsInserted.callCount == 1
    assert rowsInserted.callArgs[0][1] == 0
    assert rowsInserted.callArgs[0][2] == 0
    assert find(scene, "A") == 0


def test_set_existing_peoples_names(scene, model):
    personA = Person()
    personB = Person(name="B")
    scene.addItems(personA, personB)
    assert model.rowCount() == 1
    assert model.index(0, 0).data() == "B"
    assert model.index(0, 0).data(model.IdRole) == personB.id

    dataChanged = util.Condition(model.dataChanged)
    rowsInserted = util.Condition(model.rowsInserted)
    personA.setName("A")
    assert rowsInserted.callCount == 1
    assert rowsInserted.callArgs[0][1] == 0
    assert rowsInserted.callArgs[0][2] == 0
    assert model.rowCount() == 2
    assert model.index(0, 0).data() == "A"
    assert model.index(1, 0).data() == "B"
    assert model.index(0, 0).data(model.IdRole) == personA.id
    assert model.index(1, 0).data(model.IdRole) == personB.id


def test_clear_existing_persons_name(scene, model):
    rowsRemoved = util.Condition(model.rowsRemoved)
    personA = scene.addItem(Person(name="A"))
    assert find(scene, "A") == 0

    personA.prop("name").reset()
    assert rowsRemoved.callCount == 1
    assert rowsRemoved.callArgs[0][1] == 0
    assert rowsRemoved.callArgs[0][2] == 0
    assert find(scene, "A") == None


def test_clear_existing_peoples_names(scene, model):
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    aAfterIndex = find(scene, "A")
    bAfterIndex = find(scene, "B")
    assert aAfterIndex == 0
    assert bAfterIndex == 1

    personA.prop("name").reset()
    aAfterIndex = find(scene, "A")
    bAfterIndex = find(scene, "B")
    assert aAfterIndex == None
    assert bAfterIndex == 0


def test_accessors(scene, model):
    p1 = scene.addItem(Person(name="p1"))

    assert model.idForRow(1000) == -1
    assert model.rowForId(1000) == -1

    assert model.idForRow(0) is not None
    assert model.rowForId(model.idForRow(0)) == 0


def test_sort(scene, model):

    def get(row):
        return model.data(model.index(row, 0), model.NameRole)

    # add just one
    personA = scene.addItem(Person(name="Aaa"))
    assert model.rowCount() == 1
    assert model.columnCount() == 1
    assert get(0) == "Aaa"
    assert model.idForRow(0) == personA.id
    assert model.idForRow(1) == -1

    # add out of order
    personC = scene.addItem(Person(name="Ccc"))
    personEmpty = scene.addItem(Person())  # shouldn't be listed
    assert model.rowCount() == 2
    assert get(0) == "Aaa"
    assert get(1) == "Ccc"
    assert model.idForRow(0) == personA.id
    assert model.idForRow(1) == personC.id
    assert model.idForRow(2) == -1

    # add + sort to middle
    personBD = scene.addItem(Person(name="Bbb"))
    assert model.rowCount() == 3
    assert get(0) == "Aaa"
    assert get(1) == "Bbb"
    assert get(2) == "Ccc"
    assert model.idForRow(0) == personA.id
    assert model.idForRow(1) == personBD.id
    assert model.idForRow(2) == personC.id
    assert model.idForRow(3) == -1

    # remove middle
    scene.removeItem(personA)
    assert model.rowCount() == 2
    assert get(0) == "Bbb"
    assert get(1) == "Ccc"
    assert model.idForRow(0) == personBD.id
    assert model.idForRow(1) == personC.id
    assert model.idForRow(2) == -1

    # change name
    personBD.setName("Ddd")
    assert model.rowCount() == 2
    assert get(0) == "Ccc"
    assert get(1) == "Ddd"
    assert model.idForRow(0) == personC.id
    assert model.idForRow(1) == personBD.id
    assert model.idForRow(2) == -1


def test_dataChanged_emitted_on_rename_same_position(scene, model):
    """dataChanged must emit when name changes even if sort order unchanged."""
    personA, personB = scene.addItems(Person(name="Aaa"), Person(name="Ccc"))
    assert model.data(model.index(0, 0)) == "Aaa"
    assert model.data(model.index(1, 0)) == "Ccc"

    dataChanged = util.Condition(model.dataChanged)
    personA.setName("Bbb")
    assert dataChanged.callCount == 1
    assert model.data(model.index(0, 0)) == "Bbb"
    assert model.data(model.index(1, 0)) == "Ccc"


def test_data(scene, model):

    personA, personB, personC = scene.addItems(
        Person(name="Aaa"), Person(name="Bbb"), Person(name="Ccc")
    )

    def getName(row):
        return model.data(model.index(row, 0), model.NameRole)

    def getId(row):
        return model.data(model.index(row, 0), model.IdRole)

    assert getName(0) == "Aaa"
    assert getName(1) == "Bbb"
    assert getName(2) == "Ccc"
    assert getId(0) == personA.id
    assert getId(1) == personB.id
    assert getId(2) == personC.id
