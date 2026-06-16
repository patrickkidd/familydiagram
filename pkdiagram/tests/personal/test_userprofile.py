"""FD-321 — user-details profile capture/edit on the primary person node."""

import pickle
from datetime import datetime
from unittest.mock import patch

import pytest

from pkdiagram import util
from pkdiagram.personal import PersonalAppController
from pkdiagram.scene import Person, Event
from pkdiagram.server_types import Diagram
from btcopilot.schema import DiagramData, PDP, asdict, EventKind

pytestmark = [
    pytest.mark.component("Personal"),
    pytest.mark.depends_on("Session"),
]


@pytest.fixture(autouse=True)
def _stub_account_sync(monkeypatch):
    """The account write-back (Session.updateName) hits the server. Stub it by
    default so node-behavior tests stay offline; the dedicated link tests patch
    it on the instance to assert the call."""
    from pkdiagram.app.session import Session

    monkeypatch.setattr(Session, "updateName", lambda self, f, l: True)


def _give_client_diagram(personalApp, test_user):
    """A diagram that is NOT the user's free diagram — e.g. a clinician's client
    file. The account name must never be read from or written to here."""
    personalApp._diagram = Diagram(
        id=(test_user.free_diagram_id or 0) + 1000,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(DiagramData(pdp=PDP()))),
    )


def _give_diagram(personalApp, test_user):
    """Attach a server Diagram so saveDiagram() has something to write to; its
    save() is patched off in tests so no network happens."""
    personalApp._diagram = Diagram(
        id=test_user.free_diagram_id,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(DiagramData(pdp=PDP()))),
    )


def test_saveUserProfile_lands_name_and_birth_event_on_primary(
    test_user, personalApp: PersonalAppController
):
    _give_diagram(personalApp, test_user)
    with patch.object(personalApp, "saveDiagram") as save:
        ok = personalApp.saveUserProfile("Patrick", "Stinson", 1980, 3, 15)

    assert ok is True
    assert save.call_count == 1
    person = personalApp._primaryPerson()
    assert person is not None and person.primary()
    assert person.name() == "Patrick"
    assert person.lastName() == "Stinson"
    birth = person.birthEvent()
    assert birth is not None
    assert birth.dateTime().date() == util.Date(1980, 3, 15).date()


def test_saveUserProfile_empty_birth_leaves_no_event(
    test_user, personalApp: PersonalAppController
):
    """A fully-empty birth date (year<=0) is allowed: name lands, no Birth event."""
    _give_diagram(personalApp, test_user)
    with patch.object(personalApp, "saveDiagram"):
        personalApp.saveUserProfile("Solo", "", 0, 0, 0)

    person = personalApp._primaryPerson()
    assert person.name() == "Solo"
    assert person.lastName() is None
    assert person.birthEvent() is None


def test_saveUserProfile_edits_existing_primary(
    test_user, personalApp: PersonalAppController
):
    """Settings edit: an existing primary person with a birth event is updated
    in place, not duplicated."""
    person = personalApp.scene.addItem(Person(name="Old", lastName="Name", primary=True))
    personalApp.scene.addItem(
        Event(EventKind.Birth, person=person, child=person, dateTime=util.Date(1970, 1, 1))
    )
    _give_diagram(personalApp, test_user)

    with patch.object(personalApp, "saveDiagram"):
        personalApp.saveUserProfile("New", "Person", 1990, 6, 20)

    people = personalApp.scene.people()
    assert len(people) == 1
    assert people[0].name() == "New"
    assert people[0].lastName() == "Person"
    assert len([e for e in people[0].events() if e.kind() == EventKind.Birth]) == 1
    assert people[0].birthEvent().dateTime().date() == util.Date(1990, 6, 20).date()


def test_saveUserProfile_clears_birth_event_when_emptied(
    test_user, personalApp: PersonalAppController
):
    person = personalApp.scene.addItem(Person(name="Had", primary=True))
    personalApp.scene.addItem(
        Event(EventKind.Birth, person=person, child=person, dateTime=util.Date(1970, 1, 1))
    )
    _give_diagram(personalApp, test_user)

    with patch.object(personalApp, "saveDiagram"):
        personalApp.saveUserProfile("Had", "", 0, 0, 0)

    assert person.birthEvent() is None


def test_userProfile_reads_back_primary(
    test_user, personalApp: PersonalAppController
):
    person = personalApp.scene.addItem(
        Person(name="Read", lastName="Back", primary=True)
    )
    personalApp.scene.addItem(
        Event(EventKind.Birth, person=person, child=person, dateTime=util.Date(1985, 12, 3))
    )

    profile = personalApp.userProfile
    assert profile["firstName"] == "Read"
    assert profile["lastName"] == "Back"
    assert profile["birthYear"] == "1985"
    assert profile["birthMonth"] == "12"
    assert profile["birthDay"] == "3"


def test_userProfile_prefills_account_name_on_own_diagram(
    test_user, personalApp: PersonalAppController
):
    """On the user's own (free) diagram with an unnamed primary, the profile
    pre-fills from the account name set at signup."""
    profile = personalApp.userProfile
    assert profile["firstName"] == test_user.first_name
    assert profile["lastName"] == test_user.last_name
    assert profile["birthYear"] == ""


def test_userProfile_does_not_prefill_on_client_diagram(
    test_user, personalApp: PersonalAppController
):
    """A client file (not the free diagram) never pre-fills from the account."""
    _give_client_diagram(personalApp, test_user)
    profile = personalApp.userProfile
    assert profile == {
        "firstName": "",
        "lastName": "",
        "birthYear": "",
        "birthMonth": "",
        "birthDay": "",
    }


def test_saveUserProfile_syncs_account_name_on_own_diagram(
    test_user, personalApp: PersonalAppController
):
    """Saving on the free diagram writes the name back to the account."""
    _give_diagram(personalApp, test_user)
    with patch.object(personalApp, "saveDiagram"), patch.object(
        personalApp.session, "updateName"
    ) as updateName:
        personalApp.saveUserProfile("Dana", "Reed", 0, 0, 0)
    updateName.assert_called_once_with("Dana", "Reed")


def test_saveUserProfile_does_not_sync_account_on_client_diagram(
    test_user, personalApp: PersonalAppController
):
    """Saving on a client file must NOT touch the account name."""
    _give_client_diagram(personalApp, test_user)
    with patch.object(personalApp, "saveDiagram"), patch.object(
        personalApp.session, "updateName"
    ) as updateName:
        personalApp.saveUserProfile("Client", "Person", 0, 0, 0)
    updateName.assert_not_called()
    assert personalApp._primaryPerson().name() == "Client"


def test_primaryPerson_falls_back_when_none_marked(
    test_user, personalApp: PersonalAppController
):
    """C6: a pre-existing diagram with no node marked primary is still editable —
    fall back to the lowest-id person deterministically."""
    p1 = personalApp.scene.addItem(Person(name="First"))
    p2 = personalApp.scene.addItem(Person(name="Second"))
    assert p1.id < p2.id

    assert personalApp._primaryPerson() is p1


def test_primaryPerson_prefers_marked_over_id(
    test_user, personalApp: PersonalAppController
):
    personalApp.scene.addItem(Person(name="Lowest"))
    p2 = personalApp.scene.addItem(Person(name="Marked", primary=True))

    assert personalApp._primaryPerson() is p2


def test_shouldPromptProfile_true_when_unset_and_no_name(
    test_user, personalApp: PersonalAppController
):
    personalApp.appConfig.delete("personalProfilePrompted")
    assert personalApp.shouldPromptProfile is True


def test_shouldPromptProfile_false_when_primary_named(
    test_user, personalApp: PersonalAppController
):
    personalApp.appConfig.delete("personalProfilePrompted")
    personalApp.scene.addItem(Person(name="Named", primary=True))
    assert personalApp.shouldPromptProfile is False


def test_markProfilePrompted_suppresses_wizard(
    test_user, personalApp: PersonalAppController
):
    """Skip path: setting the pref prevents the wizard even with a nameless
    diagram."""
    personalApp.appConfig.delete("personalProfilePrompted")
    assert personalApp.shouldPromptProfile is True

    with patch.object(personalApp.appConfig, "write"):
        personalApp.markProfilePrompted()

    assert personalApp.shouldPromptProfile is False


def test_saveUserProfile_sets_prompted_pref(
    test_user, personalApp: PersonalAppController
):
    """Completing the wizard via save also stops it reappearing."""
    personalApp.appConfig.delete("personalProfilePrompted")
    _give_diagram(personalApp, test_user)

    with (
        patch.object(personalApp, "saveDiagram"),
        patch.object(personalApp.appConfig, "write"),
    ):
        personalApp.saveUserProfile("X", "", 0, 0, 0)

    assert personalApp.shouldPromptProfile is False


def test_saveUserProfile_no_scene_returns_false(
    test_user, personalApp: PersonalAppController
):
    personalApp.scene = None
    assert personalApp.saveUserProfile("X", "", 0, 0, 0) is False


def _findChild(root, objectName):
    from pkdiagram.pyqt import QQuickItem

    for child in root.findChildren(QQuickItem):
        if child.objectName() == objectName:
            return child
    return None


def test_userDetailsForm_validates_on_first_name(qApp, test_session):
    """The reusable form (mounted in the wizard inside PersonalContainer) gates
    `valid` on a non-blank first name, which drives the Get Started/Save button.
    Loaded through the app's own engine so lazy QML binding errors surface."""
    from pkdiagram.pyqt import QQmlApplicationEngine, QApplication
    from pkdiagram.scene import Scene

    app = PersonalAppController()
    engine = QQmlApplicationEngine()
    errors = []
    engine.warnings.connect(lambda errs: errors.extend(errs))
    engine.addImportPath("resources:")
    app.init(engine)
    app.session.init(
        sessionData=test_session.account_editor_dict(), syncWithServer=False
    )
    app.setScene(Scene())
    engine.load("resources:qml/PersonalApplication.qml")
    QApplication.processEvents()
    util.waitALittle()
    assert not errors, [e.toString() for e in errors]

    root = engine.rootObjects()[0]
    # Force the wizard active so its UserDetailsForm instantiates (lazy Loader).
    app.appConfig.delete("personalProfilePrompted")
    app.userProfileChanged.emit()
    QApplication.processEvents()
    util.waitALittle()

    form = _findChild(root, "userDetailsForm")
    assert form is not None, "wizard form did not mount"
    # The wizard pre-fills the first name from the account; clear it to exercise
    # the empty-name gate.
    assert form.property("firstName") != ""
    form.setProperty("firstName", "")
    assert form.property("valid") is False
    form.setProperty("firstName", "Patrick")
    assert form.property("valid") is True

    # Empty birth date -> 0 (optional, allowed).
    assert form.property("birthYear") == 0
    assert form.property("birthMonth") == 0
    assert form.property("birthDay") == 0

    # Setting the canonical birthDateTime flows to the derived Y/M/D ints the
    # controller consumes (reuses the EventForm date idiom).
    from PyQt5.QtCore import QDateTime, QDate

    form.setProperty("birthDateTime", QDateTime(QDate(1980, 3, 15)))
    QApplication.processEvents()
    assert form.property("birthYear") == 1980
    assert form.property("birthMonth") == 3
    assert form.property("birthDay") == 15

    engine.clearComponentCache()
