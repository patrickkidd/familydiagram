import copy, pickle

import pytest

from pkdiagram.pyqt import QDateTime, Qt
from pkdiagram import util
from pkdiagram.scene import Scene, Event, Person, Marriage, EventKind


def test_no_dupe_events(simpleMarriage):
    for event in simpleMarriage.events():
        assert simpleMarriage.events().count(event) == 1


def test_no_dupe_events_from_fd(simpleMarriage):
    data = {}
    scene = simpleMarriage.scene().write(data)
    scene2 = Scene()
    scene2.read(data)
    marriage = scene2.find(types=Marriage)[0]
    events = marriage.events()
    for event in events:
        assert events.count(event) == 1


@pytest.fixture
def noEvents(scene, request):
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItems(personA, personB, marriage)
    return marriage


@pytest.fixture
def noEvents2Children(noEvents):
    childA, childB = Person(), Person()
    childA.setParents(noEvents)
    childB.setParents(noEvents)
    return noEvents


@pytest.fixture
def simpleMarriage(scene):
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    Event(
        parent=marriage,
        kind=EventKind.Bonded,
        dateTime=util.Date(1900, 1, 1),
    )
    Event(
        parent=marriage,
        kind=EventKind.Married,
        dateTime=util.Date(1910, 1, 1),
    )
    Event(
        parent=marriage,
        kind=EventKind.Separated,
        dateTime=util.Date(1920, 1, 1),
    )
    Event(
        parent=marriage,
        kind="moved",
        dateTime=util.Date(1925, 1, 1),
        location="Washington, DC",
    )
    Event(
        parent=marriage,
        kind=EventKind.Married,
        dateTime=util.Date(1930, 1, 1),
    )
    Event(
        parent=marriage,
        kind=EventKind.Separated,
        dateTime=util.Date(1940, 1, 1),
    )
    Event(
        parent=marriage,
        kind=EventKind.Divorced,
        dateTime=util.Date(1950, 1, 1),
    )
    scene.addItems(personA, personB, marriage)
    return marriage


def test_olderBirth():
    marriage_1 = Marriage(
        Person(birthDateTime=util.Date(2001, 1, 1)),
        Person(birthDateTime=util.Date(2002, 1, 1)),
    )
    assert marriage_1.olderBirth() == util.Date(2001, 1, 1)


def test_sort():
    marriage_1 = Marriage(
        Person(birthDateTime=util.Date(2001, 1, 1)),
        Person(birthDateTime=util.Date(2002, 1, 1)),
    )
    marriage_2 = Marriage(
        Person(birthDateTime=util.Date(2001, 1, 1)),
        Person(birthDateTime=util.Date(2000, 1, 1)),
    )
    assert marriage_2 < marriage_1


def test_marriagesFor_one(noEvents):
    personA, personB = noEvents.people
    assert noEvents.marriagesFor(personA, personB) == [noEvents]


def test_marriagesFor_none(noEvents):
    personA, personB = noEvents.people
    personC = Person(name="Person C")
    assert noEvents.marriagesFor(personA, personC) == []


def test_marriagesFor_reversed(noEvents):
    personA, personB = noEvents.people
    assert noEvents.marriagesFor(personB, personA) == [noEvents]


def test_auto_sort_events(noEvents):
    marriage = noEvents
    one = Event(parent=marriage, description="One", dateTime=util.Date(1900, 1, 1))
    three = Event(parent=marriage, description="Three", dateTime=util.Date(1970, 1, 1))
    two = Event(parent=marriage, description="Two", dateTime=util.Date(1950, 1, 1))
    events = marriage.events()
    assert events[0] == one
    assert events[1] == two
    assert events[2] == three


## shouldShowFor (1 -- parents)


def test_shouldShowFor_one_parent_hidden(monkeypatch, noEvents):
    marriage = noEvents
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    assert marriage.shouldShowFor(QDateTime.currentDateTime()) == False


def test_shouldShowFor_both_parents_hidden(monkeypatch, noEvents):
    marriage = noEvents
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    assert marriage.shouldShowFor(QDateTime.currentDateTime()) == False


def test_shouldShowFor_no_parents_hidden(monkeypatch, noEvents):
    marriage = noEvents
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    assert marriage.shouldShowFor(QDateTime.currentDateTime()) == True


## shouldShowFor (2 -- any children shown)


def test_shouldShowFor_both_parents_n_all_children(monkeypatch, noEvents2Children):
    marriage = noEvents2Children
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.children[0], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.children[1], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    assert marriage.shouldShowFor(QDateTime.currentDateTime()) == True


def test_shouldShowFor_both_parents_n_one_child(monkeypatch, noEvents2Children):
    marriage = noEvents2Children
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.children[0], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    monkeypatch.setattr(
        marriage.children[1], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    assert marriage.shouldShowFor(QDateTime.currentDateTime()) == True


def test_shouldShowFor_both_parents_n_no_children(monkeypatch, noEvents2Children):
    marriage = noEvents2Children
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.children[0], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    monkeypatch.setattr(
        marriage.children[1], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    assert marriage.shouldShowFor(QDateTime.currentDateTime()) == True


def test_shouldShowFor_one_parent_one_child(monkeypatch, noEvents2Children):
    marriage = noEvents2Children
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    monkeypatch.setattr(
        marriage.children[0], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.children[1], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    assert marriage.shouldShowFor(QDateTime.currentDateTime()) == False


## shouldShowFor (3 -- Bonded / married events)


@pytest.mark.parametrize("kind", [EventKind.Bonded, EventKind.Married])
def test_shouldShowFor_first_bonded_event_prior_to_first_child(
    monkeypatch, noEvents2Children, kind
):
    marriage = noEvents2Children
    Event(
        parent=marriage, kind=kind, dateTime=util.Date(1990, 1, 1)
    )  # prior to child births
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    marriage.children[0].setBirthDateTime(util.Date(2000, 1, 1))
    marriage.children[1].setBirthDateTime(util.Date(2010, 1, 1))
    assert marriage.shouldShowFor(util.Date(1980, 1, 1)) == False  # prior to event
    assert (
        marriage.shouldShowFor(util.Date(1995, 1, 1)) == True
    )  # between event and first birth


# Children incorrectly added prior to bonded/married events)
@pytest.mark.parametrize("kind", [EventKind.Bonded, EventKind.Married])
def test_shouldShowFor_first_bonded_married_event_after_first_child(
    noEvents2Children, kind
):
    marriage = noEvents2Children
    marriage.children[0].setBirthDateTime(util.Date(1990, 1, 1))
    marriage.children[1].setBirthDateTime(util.Date(1990, 1, 1))
    Event(
        parent=marriage, kind=kind, dateTime=util.Date(2000, 1, 1)
    )  # prior to child births
    assert (
        marriage.shouldShowFor(util.Date(1980, 1, 1)) == False
    )  # prior to first child
    assert (
        marriage.shouldShowFor(util.Date(1995, 1, 1)) == True
    )  # between first child and event
    assert marriage.shouldShowFor(util.Date(2005, 1, 1)) == True  # after event


## &.penStyleFor


# Test that child births do not affect pen style
def test_penStyleFor_bonded_prior_to_first_child(noEvents2Children):
    marriage = noEvents2Children
    marriage.setMarried(False)
    Event(
        parent=marriage,
        kind=EventKind.Bonded,
        dateTime=util.Date(1990, 1, 1),
    )  # prior to child births
    marriage.children[0].setBirthDateTime(util.Date(2000, 1, 1))
    marriage.children[1].setBirthDateTime(util.Date(2010, 1, 1))
    assert marriage.penStyleFor(util.Date(1980, 1, 1)) == Qt.DashLine  # prior to event
    assert (
        marriage.penStyleFor(util.Date(1995, 1, 1)) == Qt.DashLine
    )  # between event and first birth
    assert (
        marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.DashLine
    )  # after first birth


def test_penStyleFor_married_prior_to_first_child(noEvents2Children):
    marriage = noEvents2Children
    marriage.setMarried(False)
    Event(
        parent=marriage,
        kind=EventKind.Married,
        dateTime=util.Date(1990, 1, 1),
    )  # prior to child births
    marriage.children[0].setBirthDateTime(util.Date(2000, 1, 1))
    marriage.children[1].setBirthDateTime(util.Date(2010, 1, 1))
    assert marriage.penStyleFor(util.Date(1980, 1, 1)) == Qt.DashLine  # prior to event
    assert (
        marriage.penStyleFor(util.Date(1995, 1, 1)) == Qt.SolidLine
    )  # between event and first birth
    assert (
        marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.SolidLine
    )  # after first birth


# Incorrect data entry, but still needs to display something when children are shown
def test_penStyleFor_bonded_after_first_child(noEvents2Children):
    marriage = noEvents2Children
    marriage.setMarried(False)
    marriage.children[0].setBirthDateTime(util.Date(1990, 1, 1))
    Event(
        parent=marriage,
        kind=EventKind.Bonded,
        dateTime=util.Date(2000, 1, 1),
    )  # prior to child births
    assert (
        marriage.penStyleFor(util.Date(1980, 1, 1)) == Qt.DashLine
    )  # prior to first child
    assert (
        marriage.penStyleFor(util.Date(1995, 1, 1)) == Qt.DashLine
    )  # between first child and event
    assert marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.DashLine  # after event


def test_penStyleFor_married_after_first_child(noEvents2Children):
    marriage = noEvents2Children
    marriage.setMarried(False)
    marriage.children[0].setBirthDateTime(util.Date(1990, 1, 1))
    Event(
        parent=marriage,
        kind=EventKind.Married,
        dateTime=util.Date(2000, 1, 1),
    )  # prior to child births
    assert (
        marriage.penStyleFor(util.Date(1980, 1, 1)) == Qt.DashLine
    )  # prior to first child
    assert (
        marriage.penStyleFor(util.Date(1995, 1, 1)) == Qt.DashLine
    )  # between first child and event
    assert marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.SolidLine  # after event


def test_penStyleFor_between_bonded_and_married_events(noEvents):
    marriage = noEvents
    marriage.setMarried(False)
    Event(
        parent=marriage,
        kind=EventKind.Bonded,
        dateTime=util.Date(1990, 1, 1),
    )  # prior to child births
    Event(
        parent=marriage,
        kind=EventKind.Married,
        dateTime=util.Date(2000, 1, 1),
    )  # prior to child births
    assert marriage.penStyleFor(util.Date(1980, 1, 1)) == Qt.DashLine  # prior to bonded
    assert marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.SolidLine  # after marriage


def test_penStyleFor_married_no_married_events(noEvents):
    marriage = noEvents
    marriage.setMarried(True)
    assert (
        marriage.penStyleFor(QDateTime.currentDateTime()) == Qt.SolidLine
    )  # prior to first child


def test_penStyleFor_married_w_married_events(noEvents):
    marriage = noEvents
    marriage.setMarried(True)
    Event(
        parent=marriage,
        kind=EventKind.Married,
        dateTime=util.Date(2000, 1, 1),
    )
    Event(
        parent=marriage,
        kind=EventKind.Married,
        dateTime=util.Date(2010, 1, 1),
    )
    assert (
        marriage.penStyleFor(QDateTime.currentDateTime()) == Qt.SolidLine
    )  # prior to first child


def test_penStyleFor_married_w_married_events_and_bonded_prior(noEvents):
    marriage = noEvents
    marriage.setMarried(True)
    Event(
        parent=marriage,
        kind=EventKind.Bonded,
        dateTime=util.Date(1990, 1, 1),
    )
    Event(
        parent=marriage,
        kind=EventKind.Married,
        dateTime=util.Date(2000, 1, 1),
    )
    Event(
        parent=marriage,
        kind=EventKind.Married,
        dateTime=util.Date(2010, 1, 1),
    )
    assert (
        marriage.penStyleFor(util.Date(1995, 1, 1)) == Qt.DashLine
    )  # after bonded, prior to marriage
    assert marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.SolidLine  # after marriage


def test_penStyleFor_divorced_w_married_events(noEvents):
    marriage = noEvents
    marriage.setMarried(False)
    marriage.setDivorced(True)
    Event(
        parent=marriage,
        kind=EventKind.Married,
        dateTime=util.Date(2000, 1, 1),
    )
    assert (
        marriage.penStyleFor(QDateTime.currentDateTime()) == Qt.SolidLine
    )  # prior to first child


def test_penStyleFor_divorced_w_no_married_events(noEvents):
    marriage = noEvents
    marriage.setMarried(False)
    marriage.setDivorced(True)
    assert (
        marriage.penStyleFor(QDateTime.currentDateTime()) == Qt.SolidLine
    )  # prior to first child


def test_penStyleFor_divorced_w_divorced_events(noEvents):
    marriage = noEvents
    marriage.setMarried(False)
    marriage.setDivorced(True)
    Event(
        parent=marriage,
        kind=EventKind.Divorced,
        dateTime=util.Date(2000, 1, 1),
    )
    assert (
        marriage.penStyleFor(QDateTime.currentDateTime()) == Qt.SolidLine
    )  # prior to first child


def test_penStyleFor_married_w_bonded_event_prior_no_married_events(noEvents):
    marriage = noEvents
    marriage.setMarried(True)
    Event(
        parent=marriage,
        kind=EventKind.Bonded,
        dateTime=util.Date(1990, 1, 1),
    )
    assert (
        marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.SolidLine
    )  # after bonded event


## &.separationStatusFor


def test_separationStatusFor_no_div_sep_event_no_div_sep(noEvents):
    marriage = noEvents
    marriage.setSeparated(False)
    marriage.setDivorced(False)
    assert marriage.separationStatusFor(QDateTime.currentDateTime()) == None


def test_separationStatusFor_no_div_sep_event_div_no_sep(noEvents):
    marriage = noEvents
    marriage.setSeparated(False)
    marriage.setDivorced(True)
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Divorced
    )


def test_separationStatusFor_div_event_no_sep_event_no_div_sep(noEvents):
    marriage = noEvents
    marriage.setSeparated(False)
    marriage.setDivorced(False)
    Event(
        parent=marriage,
        kind=EventKind.Divorced,
        dateTime=util.Date(2000, 1, 1),
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Divorced
    )


def test_separationStatusFor_div_event_no_sep_event_div_no_sep(noEvents):
    marriage = noEvents
    marriage.setSeparated(False)
    marriage.setDivorced(True)
    Event(
        parent=marriage,
        kind=EventKind.Divorced,
        dateTime=util.Date(2000, 1, 1),
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Divorced
    )


def test_separationStatusFor_sep_event_no_div_event_no_div_sep(noEvents):
    marriage = noEvents
    marriage.setSeparated(False)
    marriage.setDivorced(False)
    Event(
        parent=marriage,
        kind=EventKind.Separated,
        dateTime=util.Date(2000, 1, 1),
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Separated
    )


def test_separationStatusFor_sep_event_no_div_event_sep_no_div(noEvents):
    marriage = noEvents
    marriage.setSeparated(True)
    marriage.setDivorced(False)
    Event(
        parent=marriage,
        kind=EventKind.Separated,
        dateTime=util.Date(2000, 1, 1),
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Separated
    )


def test_separationStatusFor_one_moved_event_no_div_sep(noEvents):
    marriage = noEvents
    marriage.setSeparated(False)
    marriage.setDivorced(False)
    Event(
        parent=marriage,
        kind="moved",
        location="Somewhere",
        dateTime=util.Date(1990, 1, 1),
    )
    assert marriage.separationStatusFor(QDateTime.currentDateTime()) == None


def test_separationStatusFor_one_moved_event_sep_no_div(noEvents):
    marriage = noEvents
    marriage.setSeparated(True)
    marriage.setDivorced(False)
    Event(
        parent=marriage,
        kind="moved",
        location="Somewhere",
        dateTime=util.Date(1990, 1, 1),
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Separated
    )


def test_separationStatusFor_one_moved_event_div_no_sep(noEvents):
    marriage = noEvents
    marriage.setSeparated(False)
    marriage.setDivorced(True)
    Event(
        parent=marriage,
        kind="moved",
        location="Somewhere",
        dateTime=util.Date(1990, 1, 1),
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Divorced
    )


def test_separationStatusFor_one_moved_event_div(noEvents):
    marriage = noEvents
    marriage.setSeparated(False)
    marriage.setDivorced(True)
    Event(
        parent=marriage,
        kind="moved",
        location="Somewhere",
        dateTime=util.Date(1990, 1, 1),
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Divorced
    )


def test_separationStatusFor_one_moved_event_sep(noEvents):
    marriage = noEvents
    marriage.setSeparated(True)
    marriage.setDivorced(False)
    Event(
        parent=marriage,
        kind="moved",
        location="Somewhere",
        dateTime=util.Date(1990, 1, 1),
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Separated
    )


def test_separationStatusFor_one_moved_event_sep_and_div_events(noEvents):
    marriage = noEvents
    marriage.setSeparated(False)
    marriage.setDivorced(False)
    Event(
        parent=marriage,
        kind=EventKind.Separated,
        location="Somewhere",
        dateTime=util.Date(1990, 1, 1),
    )
    Event(parent=marriage, kind="moved", dateTime=util.Date(2000, 1, 1))
    Event(
        parent=marriage,
        kind=EventKind.Divorced,
        dateTime=util.Date(2010, 1, 1),
    )
    assert (
        marriage.separationStatusFor(util.Date(1985, 1, 1)) == None
    )  # before separation
    assert (
        marriage.separationStatusFor(util.Date(1995, 1, 1)) == EventKind.Separated
    )  # after separation
    assert (
        marriage.separationStatusFor(util.Date(2005, 1, 1)) == EventKind.Separated
    )  # after move
    assert (
        marriage.separationStatusFor(util.Date(2015, 1, 1)) == EventKind.Divorced
    )  # after divorce


## Miscellaneous


def test_detailsText_lines(simpleMarriage):
    somethingHappened = Event(
        parent=simpleMarriage,
        description="Something happened",
        dateTime=util.Date(1922, 1, 1),
    )
    scene = simpleMarriage.scene()

    scene.setCurrentDateTime(util.Date(1899, 1, 1))  # 0
    assert simpleMarriage.detailsText.text() == ""

    scene.setCurrentDateTime(util.Date(1900, 1, 1))  # 1
    assert simpleMarriage.detailsText.text() == "b. 01/01/1900"

    scene.setCurrentDateTime(util.Date(1910, 1, 1))  # 2
    assert simpleMarriage.detailsText.text() == "b. 01/01/1900\nm. 01/01/1910"

    scene.setCurrentDateTime(util.Date(1920, 1, 1))  # 3
    assert (
        simpleMarriage.detailsText.text()
        == "b. 01/01/1900\nm. 01/01/1910\ns. 01/01/1920"
    )

    scene.setCurrentDateTime(util.Date(1930, 1, 1))  # 4
    assert (
        simpleMarriage.detailsText.text()
        == "b. 01/01/1900\nm. 01/01/1910\ns. 01/01/1920\n01/01/1925 Moved to Washington, DC\nm. 01/01/1930"
    )

    somethingHappened.setIncludeOnDiagram(True)
    assert (
        simpleMarriage.detailsText.text()
        == "b. 01/01/1900\nm. 01/01/1910\ns. 01/01/1920\n01/01/1922 Something happened\n01/01/1925 Moved to Washington, DC\nm. 01/01/1930"
    )

    scene.setCurrentDateTime(util.Date(1940, 1, 1))  # 5
    assert (
        simpleMarriage.detailsText.text()
        == "b. 01/01/1900\nm. 01/01/1910\ns. 01/01/1920\n01/01/1922 Something happened\n01/01/1925 Moved to Washington, DC\nm. 01/01/1930\ns. 01/01/1940"
    )

    scene.setCurrentDateTime(util.Date(1950, 1, 1))  # 6
    assert (
        simpleMarriage.detailsText.text()
        == "b. 01/01/1900\nm. 01/01/1910\ns. 01/01/1920\n01/01/1922 Something happened\n01/01/1925 Moved to Washington, DC\nm. 01/01/1930\ns. 01/01/1940\nd. 01/01/1950"
    )


@pytest.fixture
def detailsText_marriage():
    scene = Scene()
    scene.setCurrentDateTime(util.Date(2001, 1, 1))
    personA, personB = Person(name="Roger"), Person(name="Sally")
    marriage = Marriage(personA, personB, diagramNotes="here are some notes")
    scene.addItems(personA, personB, marriage)
    married = Event(marriage, kind=EventKind.Married, dateTime=scene.currentDateTime())
    custom = Event(marriage, dateTime=scene.currentDateTime())
    marriage.updateDetails()
    return marriage


def test_detailsText_all(detailsText_marriage):
    marriage = detailsText_marriage
    assert marriage.detailsText.isVisible() == True
    assert "m. " in marriage.detailsText.text()
    assert marriage.diagramNotes() in marriage.detailsText.text()


def test_detailsText_none(detailsText_marriage):
    marriage = detailsText_marriage
    marriage.setHideDetails(True)
    marriage.setHideDates(True)
    assert marriage.detailsText.isVisible() == False
    assert marriage.detailsText.isEmpty() == True


def test_detailsText_hideDetails(detailsText_marriage):
    marriage = detailsText_marriage
    marriage.setHideDetails(True)
    assert marriage.detailsText.isVisible() == True
    assert "m. " in marriage.detailsText.text()
    assert marriage.diagramNotes() not in marriage.detailsText.text()


def test_detailsText_hideDates(detailsText_marriage):
    marriage = detailsText_marriage
    marriage.setHideDates(True)
    assert marriage.detailsText.isVisible() == True
    assert "m. " not in marriage.detailsText.text()
    assert marriage.diagramNotes() in marriage.detailsText.text()


def test_compat_marriage_events(data_root):
    import os.path

    with open(os.path.join(data_root, "v114a7_simplefamily.pickle"), "rb") as f:
        v1147_simplefamily = pickle.loads(f.read())

    data = copy.deepcopy(v1147_simplefamily)

    scene = Scene()
    scene.read(data)

    marriage = scene.marriages()[0]
    events = marriage.events()
    assert len(events) == 5
    marriedEvent = next(e for e in events if e.kind() == EventKind.Married)
    separatedEvent = next(e for e in events if e.kind() == EventKind.Separated)
    divorcedEvent = next(e for e in events if e.kind() == EventKind.Divorced)
    movedEvents = [e for e in events if e.kind() == "moved"]
    assert marriedEvent.dateTime() == util.Date(1900, 1, 1)
    assert separatedEvent.dateTime() == util.Date(1910, 1, 1)
    assert divorcedEvent.dateTime() == util.Date(1920, 1, 1)
    assert movedEvents[0].dateTime() == util.Date(1905, 1, 1)
    assert movedEvents[1].dateTime() == util.Date(1915, 1, 1)
    assert marriedEvent.location() == "Here"
    assert separatedEvent.location() == "You"
    assert divorcedEvent.location() == "Go"
    assert movedEvents[0].location() == "Washington,  DC"
    assert movedEvents[1].location() == "Denver, CO"
