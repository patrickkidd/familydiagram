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
def marriage(scene, request):
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItems(personA, personB, marriage)
    return marriage


@pytest.fixture
def marriage2Children(marriage):
    childA, childB = Person(), Person()
    childA.setParents(marriage)
    childB.setParents(marriage)
    return marriage


@pytest.fixture
def simpleMarriage(scene):
    person, spouse = Person(), Person()
    marriage = Marriage(personA=person, personB=spouse)
    scene.addItems(person, spouse, marriage)
    scene.addItem(
        Event(
            EventKind.Bonded,
            person,
            spouse=spouse,
            dateTime=util.Date(1900, 1, 1),
        )
    )
    scene.addItem(
        Event(
            EventKind.Married,
            person,
            spouse=spouse,
            dateTime=util.Date(1910, 1, 1),
        )
    )
    scene.addItem(
        Event(
            EventKind.Separated,
            person,
            spouse=spouse,
            dateTime=util.Date(1920, 1, 1),
        )
    )
    scene.addItem(
        Event(
            EventKind.Moved,
            person,
            spouse=spouse,
            dateTime=util.Date(1925, 1, 1),
            location="Washington, DC",
        )
    )
    scene.addItem(
        Event(
            EventKind.Married,
            person,
            spouse=spouse,
            dateTime=util.Date(1930, 1, 1),
        )
    )
    scene.addItem(
        Event(
            EventKind.Separated,
            person,
            spouse=spouse,
            dateTime=util.Date(1940, 1, 1),
        )
    )
    scene.addItem(
        Event(
            EventKind.Divorced,
            person,
            spouse=spouse,
            dateTime=util.Date(1950, 1, 1),
        )
    )
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


def test_marriageFor_one(scene, marriage):
    personA, personB = marriage.people
    assert scene.marriageFor(personA, personB) == marriage


def test_marriagesFor_none(scene, marriage):
    personA, personB = marriage.people
    personC = Person(name="Person C")
    scene.addItem(personC)
    assert scene.marriageFor(personA, personC) == None


def test_marriagesFor_reversed(marriage):
    personA, personB = marriage.people
    assert marriage.marriageFor(personB, personA) == marriage


def test_auto_sort_events(marriage):
    person, spouse = marriage.personA(), marriage.spouse()
    one = Event(
        EventKind.Shift,
        person,
        spouse=spouse,
        description="One",
        dateTime=util.Date(1900, 1, 1),
    )
    three = Event(
        EventKind.Shift,
        person,
        spouse=spouse,
        description="Three",
        dateTime=util.Date(1970, 1, 1),
    )
    two = Event(
        EventKind.Shift,
        person,
        spouse=spouse,
        description="Two",
        dateTime=util.Date(1950, 1, 1),
    )
    events = marriage.events()
    assert events[0] == one
    assert events[1] == two
    assert events[2] == three


## shouldShowFor (1 -- parents)


def test_shouldShowFor_one_parent_hidden(monkeypatch, marriage):
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    assert marriage.shouldShowFor(QDateTime.currentDateTime()) == False


def test_shouldShowFor_both_parents_hidden(monkeypatch, marriage):
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: False
    )
    assert marriage.shouldShowFor(QDateTime.currentDateTime()) == False


def test_shouldShowFor_no_parents_hidden(monkeypatch, marriage):
    monkeypatch.setattr(
        marriage.people[0], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    monkeypatch.setattr(
        marriage.people[1], "shouldShowFor", lambda x, tags=[], layers=[]: True
    )
    assert marriage.shouldShowFor(QDateTime.currentDateTime()) == True


## shouldShowFor (2 -- any children shown)


def test_shouldShowFor_both_parents_n_all_children(monkeypatch, marriage2Children):
    marriage = marriage2Children
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


def test_shouldShowFor_both_parents_n_one_child(monkeypatch, marriage2Children):
    marriage = marriage2Children
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


def test_shouldShowFor_both_parents_n_no_children(monkeypatch, marriage2Children):
    marriage = marriage2Children
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


def test_shouldShowFor_one_parent_one_child(monkeypatch, marriage2Children):
    marriage = marriage2Children
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
    monkeypatch, marriage2Children, kind
):
    marriage = marriage2Children
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.scene().addItem(
        Event(kind, person, spouse=spouse, dateTime=util.Date(1990, 1, 1))
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
    marriage2Children, kind
):
    marriage = marriage2Children
    marriage.children[0].setBirthDateTime(util.Date(1990, 1, 1))
    marriage.children[1].setBirthDateTime(util.Date(1990, 1, 1))
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.scene().addItem(
        Event(kind, person, spouse=spouse, dateTime=util.Date(2000, 1, 1))
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
def test_penStyleFor_bonded_prior_to_first_child(marriage2Children):
    marriage = marriage2Children
    marriage.setMarried(False)
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.scene().addItem(
        Event(
            EventKind.Bonded,
            person,
            spouse=spouse,
            dateTime=util.Date(1990, 1, 1),
        )
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


def test_penStyleFor_married_prior_to_first_child(marriage2Children):
    marriage = marriage2Children
    marriage.setMarried(False)
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.scene().addItem(
        Event(
            EventKind.Married,
            person,
            spouse=spouse,
            dateTime=util.Date(1990, 1, 1),
        )
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
def test_penStyleFor_bonded_after_first_child(marriage2Children):
    marriage = marriage2Children
    marriage.setMarried(False)
    marriage.children[0].setBirthDateTime(util.Date(1990, 1, 1))
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.scene().addItem(
        Event(
            EventKind.Bonded,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )  # prior to child births
    assert (
        marriage.penStyleFor(util.Date(1980, 1, 1)) == Qt.DashLine
    )  # prior to first child
    assert (
        marriage.penStyleFor(util.Date(1995, 1, 1)) == Qt.DashLine
    )  # between first child and event
    assert marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.DashLine  # after event


def test_penStyleFor_married_after_first_child(marriage2Children):
    marriage = marriage2Children
    marriage.setMarried(False)
    marriage.children[0].setBirthDateTime(util.Date(1990, 1, 1))
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.scene().addItem(
        Event(
            EventKind.Married,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )  # prior to child births
    assert (
        marriage.penStyleFor(util.Date(1980, 1, 1)) == Qt.DashLine
    )  # prior to first child
    assert (
        marriage.penStyleFor(util.Date(1995, 1, 1)) == Qt.DashLine
    )  # between first child and event
    assert marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.SolidLine  # after event


def test_penStyleFor_between_bonded_and_married_events(marriage):
    marriage.setMarried(False)
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.scene().addItem(
        Event(
            EventKind.Bonded,
            person,
            spouse=spouse,
            dateTime=util.Date(1990, 1, 1),
        )
    )  # prior to child births
    marriage.scene().addItem(
        Event(
            EventKind.Married,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )  # prior to child births
    assert marriage.penStyleFor(util.Date(1980, 1, 1)) == Qt.DashLine  # prior to bonded
    assert marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.SolidLine  # after marriage


def test_penStyleFor_married_no_married_events(marriage):
    marriage.setMarried(True)
    assert (
        marriage.penStyleFor(QDateTime.currentDateTime()) == Qt.SolidLine
    )  # prior to first child


def test_penStyleFor_married_w_married_events(marriage):
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.setMarried(True)
    marriage.scene().addItem(
        Event(
            EventKind.Married,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )
    marriage.scene().addItem(
        Event(
            EventKind.Married,
            person,
            spouse=spouse,
            dateTime=util.Date(2010, 1, 1),
        )
    )
    assert (
        marriage.penStyleFor(QDateTime.currentDateTime()) == Qt.SolidLine
    )  # prior to first child


def test_penStyleFor_married_w_married_events_and_bonded_prior(marriage):
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.setMarried(True)
    marriage.scene().addItem(
        Event(
            EventKind.Bonded,
            person,
            spouse=spouse,
            dateTime=util.Date(1990, 1, 1),
        )
    )
    marriage.scene().addItem(
        Event(
            EventKind.Married,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )
    marriage.scene().addItem(
        Event(
            EventKind.Married,
            person,
            spouse=spouse,
            dateTime=util.Date(2010, 1, 1),
        )
    )
    assert (
        marriage.penStyleFor(util.Date(1995, 1, 1)) == Qt.DashLine
    )  # after bonded, prior to marriage
    assert marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.SolidLine  # after marriage


def test_penStyleFor_divorced_w_married_events(marriage):
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.setMarried(False)
    marriage.setDivorced(True)
    marriage.scene().addItem(
        Event(
            EventKind.Married,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )
    assert (
        marriage.penStyleFor(QDateTime.currentDateTime()) == Qt.SolidLine
    )  # prior to first child


def test_penStyleFor_divorced_w_no_married_events(marriage):
    marriage.setMarried(False)
    marriage.setDivorced(True)
    assert (
        marriage.penStyleFor(QDateTime.currentDateTime()) == Qt.SolidLine
    )  # prior to first child


def test_penStyleFor_divorced_w_divorced_events(marriage):
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.setMarried(False)
    marriage.setDivorced(True)
    marriage.scene().addItem(
        Event(
            EventKind.Divorced,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )
    assert (
        marriage.penStyleFor(QDateTime.currentDateTime()) == Qt.SolidLine
    )  # prior to first child


def test_penStyleFor_married_w_bonded_event_prior_no_married_events(marriage):
    person, spouse = marriage.personA(), marriage.spouse()
    marriage.setMarried(True)
    marriage.scene().addItem(
        Event(
            EventKind.Bonded,
            person,
            spouse=spouse,
            dateTime=util.Date(1990, 1, 1),
        )
    )
    assert (
        marriage.penStyleFor(util.Date(2005, 1, 1)) == Qt.SolidLine
    )  # after bonded event


## &.separationStatusFor


def test_separationStatusFor_no_div_sep_event_no_div_sep(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(False)
    marriage.setDivorced(False)
    assert marriage.separationStatusFor(QDateTime.currentDateTime()) == None


def test_separationStatusFor_no_div_sep_event_div_no_sep(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(False)
    marriage.setDivorced(True)
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Divorced
    )


def test_separationStatusFor_div_event_no_sep_event_no_div_sep(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(False)
    marriage.setDivorced(False)
    marriage.scene().addItem(
        Event(
            EventKind.Divorced,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Divorced
    )


def test_separationStatusFor_div_event_no_sep_event_div_no_sep(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(False)
    marriage.setDivorced(True)
    marriage.scene().addItem(
        Event(
            EventKind.Divorced,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Divorced
    )


def test_separationStatusFor_sep_event_no_div_event_no_div_sep(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(False)
    marriage.setDivorced(False)
    marriage.scene().addItem(
        Event(
            EventKind.Separated,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Separated
    )


def test_separationStatusFor_sep_event_no_div_event_sep_no_div(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(True)
    marriage.setDivorced(False)
    marriage.scene().addItem(
        Event(
            EventKind.Separated,
            person,
            spouse=spouse,
            dateTime=util.Date(2000, 1, 1),
        )
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Separated
    )


def test_separationStatusFor_one_moved_event_no_div_sep(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(False)
    marriage.setDivorced(False)
    marriage.scene().addItem(
        Event(
            EventKind.Moved,
            person,
            spouse=spouse,
            location="Somewhere",
            dateTime=util.Date(1990, 1, 1),
        )
    )
    assert marriage.separationStatusFor(QDateTime.currentDateTime()) == None


def test_separationStatusFor_one_moved_event_sep_no_div(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(True)
    marriage.setDivorced(False)
    marriage.scene().addItem(
        Event(
            EventKind.Moved,
            person,
            spouse=spouse,
            location="Somewhere",
            dateTime=util.Date(1990, 1, 1),
        )
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Separated
    )


def test_separationStatusFor_one_moved_event_div_no_sep(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(False)
    marriage.setDivorced(True)
    marriage.scene().addItem(
        Event(
            EventKind.Moved,
            person,
            spouse=spouse,
            location="Somewhere",
            dateTime=util.Date(1990, 1, 1),
        )
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Divorced
    )


def test_separationStatusFor_one_moved_event_div(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(False)
    marriage.setDivorced(True)
    marriage.scene().addItem(
        Event(
            EventKind.Moved,
            person,
            spouse=spouse,
            location="Somewhere",
            dateTime=util.Date(1990, 1, 1),
        )
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Divorced
    )


def test_separationStatusFor_one_moved_event_sep(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(True)
    marriage.setDivorced(False)
    marriage.scene().addItem(
        Event(
            EventKind.Moved,
            person,
            spouse=spouse,
            location="Somewhere",
            dateTime=util.Date(1990, 1, 1),
        )
    )
    assert (
        marriage.separationStatusFor(QDateTime.currentDateTime()) == EventKind.Separated
    )


def test_separationStatusFor_one_moved_event_sep_and_div_events(marriage):
    person, spouse = marriage.personA(), marriage.personB()
    marriage.setSeparated(False)
    marriage.setDivorced(False)
    marriage.scene().addItem(
        Event(
            EventKind.Separated,
            person,
            spouse=spouse,
            location="Somewhere",
            dateTime=util.Date(1990, 1, 1),
        )
    )
    marriage.scene().addItem(
        Event(EventKind.Moved, marriage, dateTime=util.Date(2000, 1, 1))
    )
    marriage.scene().addItem(
        Event(
            EventKind.Divorced,
            person,
            spouse=spouse,
            dateTime=util.Date(2010, 1, 1),
        )
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
    person, spouse = simpleMarriage.personA(), simpleMarriage.personB()
    somethingHappened = Event(
        EventKind.Shift,
        person,
        spouse=spouse,
        dateTime=util.Date(1922, 1, 1),
        description="Something happened",
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
    scene.addItem(
        Event(
            EventKind.Married, personA, spouse=personB, dateTime=scene.currentDateTime()
        )
    )
    scene.addItem(
        Event(
            EventKind.Shift, personA, spouse=personB, dateTime=scene.currentDateTime()
        )
    )
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
