import pytest
from pkdiagram import util, Scene, Person, PeopleModel


@pytest.fixture
def peopleModel(simpleScene):
    pm = PeopleModel()
    pm.scene = simpleScene
    return pm


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


def test_init(simpleScene, peopleModel):
    people = sortedPeople(simpleScene)
    assert len(people) > 0
    assert peopleModel.rowCount() == len(people)

    names = sortedNames(simpleScene)
    for row in range(peopleModel.rowCount()):
        index = peopleModel.index(row, 0)
        assert peopleModel.data(index) == names[row]


def test_add_person(simpleScene, peopleModel):

    beforeRows = peopleModel.rowCount()
    person = Person(name="Yo")
    simpleScene.addItem(person)
    assert peopleModel.rowCount() == beforeRows + 1

    # shouldn't increase row count
    person = Person()
    simpleScene.addItem(person)
    assert peopleModel.rowCount() == beforeRows + 1


def test_remove_person(simpleScene, peopleModel):

    beforeRows = peopleModel.rowCount()
    assert beforeRows > 0

    simpleScene.removeItem(simpleScene.people()[0])
    assert peopleModel.rowCount() == beforeRows - 1


def test_change_person(simpleScene, peopleModel):

    personA = Person(name="A")
    personB = Person(name="B")
    simpleScene.addItems(personA, personB)

    aBeforeIndex = find(simpleScene, "A")
    bBeforeIndex = find(simpleScene, "B")
    assert aBeforeIndex < bBeforeIndex

    personA.setName("C")
    aAfterIndex = find(simpleScene, "C")
    bAfterIndex = find(simpleScene, "B")
    assert aAfterIndex != aBeforeIndex
    assert bAfterIndex != bBeforeIndex
    assert aAfterIndex > bAfterIndex


def test_set_existing_persons_name():
    scene = Scene()
    model = PeopleModel()
    model.scene = scene

    rowsInserted = util.Condition(model.rowsInserted)
    personA = Person()
    scene.addItem(personA)
    assert rowsInserted.callCount == 0

    personA.setName("A")
    assert rowsInserted.callCount == 1
    assert rowsInserted.callArgs[0][1] == 0
    assert rowsInserted.callArgs[0][2] == 0
    assert find(scene, "A") == 0


def test_set_existing_peoples_names():
    scene = Scene()
    model = PeopleModel()
    model.scene = scene
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


def test_clear_existing_persons_name():
    scene = Scene()
    model = PeopleModel()
    rowsRemoved = util.Condition()
    model.rowsRemoved.connect(rowsRemoved)
    personA = Person(name="A")
    scene.addItem(personA)
    model.scene = scene
    assert find(scene, "A") == 0

    personA.prop("name").reset()
    assert rowsRemoved.callCount == 1
    assert rowsRemoved.callArgs[0][1] == 0
    assert rowsRemoved.callArgs[0][2] == 0
    assert find(scene, "A") == None


def test_clear_existing_peoples_names():
    scene = Scene()
    model = PeopleModel()
    model.scene = scene

    personA = Person(name="A")
    personB = Person(name="B")
    scene.addItems(personA, personB)
    aAfterIndex = find(scene, "A")
    bAfterIndex = find(scene, "B")
    assert aAfterIndex == 0
    assert bAfterIndex == 1

    personA.prop("name").reset()
    aAfterIndex = find(scene, "A")
    bAfterIndex = find(scene, "B")
    assert aAfterIndex == None
    assert bAfterIndex == 0


def test_accessors(peopleModel):

    assert peopleModel.idForRow(1000) == -1
    assert peopleModel.rowForId(1000) == -1

    assert peopleModel.idForRow(0) is not None
    assert peopleModel.rowForId(peopleModel.idForRow(0)) == 0


def test_sort():
    scene = Scene()
    model = PeopleModel()
    model.scene = scene

    def get(row):
        return model.data(model.index(row, 0), model.NameRole)

    # add just one
    personA = Person(name="Aaa")
    scene.addItem(personA)
    assert model.rowCount() == 1
    assert model.columnCount() == 1
    assert get(0) == "Aaa"
    assert model.idForRow(0) == personA.id
    assert model.idForRow(1) == -1

    # add out of order
    personC = Person(name="Ccc")
    personEmpty = Person()  # shouldn't be listed
    scene.addItem(personC)
    scene.addItem(personEmpty)
    assert model.rowCount() == 2
    assert get(0) == "Aaa"
    assert get(1) == "Ccc"
    assert model.idForRow(0) == personA.id
    assert model.idForRow(1) == personC.id
    assert model.idForRow(2) == -1

    # add + sort to middle
    personBD = Person(name="Bbb")
    scene.addItem(personBD)
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


def test_data():

    scene = Scene()
    personA = Person(name="Aaa")
    personC = Person(name="Ccc")
    personB = Person(name="Bbb")
    scene.addItem(personA)
    scene.addItem(personB)
    scene.addItem(personC)
    model = PeopleModel()
    model.scene = scene

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
