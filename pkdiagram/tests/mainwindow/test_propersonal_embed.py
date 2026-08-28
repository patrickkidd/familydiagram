"""FD-336 / WP-F: the coach embedded in Pro's MainWindow.

C3 the feature is offered only on a case the user owns and can write;
C5 the coach reads Pro's one Scene and Pro's one Session, and never re-loads
the case over the Personal JSON route;
C8 a chat turn or an extraction on unsaved work prompts to save first, and the
save completes before anything is sent;
C9 embedding drags none of the standalone app's startup peripherals or
preferences into Pro.
"""

import contextlib
import json
import os.path
from unittest.mock import patch

import pytest

from PyQt5.QtMultimedia import QAudioRecorder
from PyQt5.QtTextToSpeech import QTextToSpeech

import btcopilot
from btcopilot.extensions import db
from btcopilot.personal.models import (
    Discussion as StoredDiscussion,
    Speaker,
    SpeakerType,
)
from btcopilot.pro.models import Diagram
from btcopilot.schema import PDP, EventKind, asdict

from pkdiagram import util
from pkdiagram.app import Session
from pkdiagram.personal.shakedetector import ShakeDetector
from pkdiagram.pyqt import QMessageBox
from pkdiagram.qnam import QNAM
from pkdiagram.pyqt import QDate, QDateTime
from pkdiagram.scene import Event, Person
from pkdiagram.tests.personal.test_lifecycle import _findInstances


pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView"),
]


PERSONAL_PREFS_KEYS = ("autoReadAloud", "ttsVoiceName", "responseModel", "lastDiagramId")


@contextlib.contextmanager
def _requests():
    """Every request the app puts on the wire while the block runs, in order,
    as (verb, path)."""
    calls = []
    qnam = QNAM.instance()
    send = qnam.sendCustomRequest

    def sendCustomRequest(request, verb, data=b""):
        calls.append((verb.decode(), request.url().path()))
        return send(request, verb, data)

    with patch.object(qnam, "sendCustomRequest", sendCustomRequest):
        yield calls


@contextlib.contextmanager
def _modals():
    """Record any modal raised, dismissing it, so a test can assert none was."""
    raised = []

    def _static(parent=None, title="", text="", *args, **kwargs):
        raised.append(text)
        return QMessageBox.Cancel

    def _exec(box, *args, **kwargs):
        raised.append(box.text())
        return QMessageBox.Cancel

    with contextlib.ExitStack() as stack:
        for name in ("question", "information", "warning", "critical"):
            stack.enter_context(patch.object(QMessageBox, name, staticmethod(_static)))
        stack.enter_context(patch.object(QMessageBox, "exec_", _exec))
        stack.enter_context(patch.object(QMessageBox, "exec", _exec))
        yield raised


def _mainWindow(create_ac_mw):
    ac, mw = create_ac_mw()
    util.wait(mw.serverFileModel.updateFinished)
    return ac, mw


def _open(mw, diagram_id):
    diagram = mw.serverFileModel.findDiagram(diagram_id)
    mw.onServerFileClicked(mw.serverFileModel.pathForDiagram(diagram), diagram)
    return diagram


def _ownedId(test_user, test_user_diagrams):
    for diagram in test_user_diagrams:
        db.session.add(diagram)
    return next(x.id for x in test_user_diagrams if x.user_id == test_user.id)


def _chat(mw, action):
    if action == "send":
        mw.proPersonal().discussion.sendStatement("hi")
    else:
        mw.proPersonal().pdpController.extractFull()


def _resource(discussion_id, action):
    return f"/personal/discussions/{discussion_id}/" + (
        "statements" if action == "send" else "extract"
    )


def _body(action, speakers=(1, 2)):
    if action == "send":
        subject_id, expert_id = speakers
        return json.dumps(
            {
                "statement": "hello back",
                "statements": [
                    {"id": 1, "text": "hi", "speaker_id": subject_id, "order": 1},
                    {
                        "id": 2,
                        "text": "hello back",
                        "speaker_id": expert_id,
                        "order": 2,
                    },
                ],
            }
        )
    return json.dumps(
        {
            "pdp": asdict(PDP()),
            "people_count": 0,
            "events_count": 0,
            "pair_bonds_count": 0,
            "pending_extracted_through_order": 1,
        }
    )


@pytest.fixture
def ownedCase(test_activation, test_user, test_user_diagrams, create_ac_mw):
    """Pro with one of the user's own server cases open and a discussion
    selected — the state every save-before-chat case starts from."""
    diagram_id = _ownedId(test_user, test_user_diagrams)
    discussion = StoredDiscussion(
        user_id=test_user.id,
        diagram_id=diagram_id,
        speakers=[
            Speaker(name="Subject", type=SpeakerType.Subject),
            Speaker(name="Coach", type=SpeakerType.Expert),
        ],
    )
    db.session.add(discussion)
    db.session.commit()
    discussion_id = discussion.id
    subject_id, expert_id = (x.id for x in discussion.speakers)

    ac, mw = _mainWindow(create_ac_mw)
    _open(mw, diagram_id)
    assert util.waitForCondition(lambda: mw.proPersonal().discussion.discussions != [])
    mw.proPersonal().discussion.setCurrentDiscussion(discussion_id)

    return mw, diagram_id, discussion_id, subject_id, expert_id


def test_coach_reads_pro_scene_and_session_without_reloading_the_case(
    test_activation, test_user, test_user_diagrams, create_ac_mw
):
    """C5: one Scene, one Session, and the case bytes Pro already loaded — a
    second load over the Personal route would give the coach a stale copy that
    diverges from what the user is editing."""
    diagram_id = _ownedId(test_user, test_user_diagrams)
    ac, mw = _mainWindow(create_ac_mw)

    with _requests() as calls:
        _open(mw, diagram_id)
        assert util.waitForCondition(
            lambda: ("GET", f"/personal/diagrams/{diagram_id}/discussions") in calls
        )
    assert ("GET", f"/personal/diagrams/{diagram_id}") not in calls

    assert mw.proPersonal().pdpController.scene is mw.scene
    assert mw.proPersonal().session is mw.session
    assert set(id(x) for x in _findInstances(mw.proPersonal(), Session)) == {
        id(mw.session)
    }


@pytest.mark.parametrize(
    "case, enabled",
    [("local", False), ("owned", True), ("shared", False), ("readOnly", False)],
)
def test_offered_only_on_a_case_the_user_owns_and_can_write(
    test_activation,
    test_user,
    test_user_2,
    test_user_diagrams,
    create_ac_mw,
    tmp_path,
    case,
    enabled,
):
    """C3: the Personal routes are owner-only, so anything else must present as
    disabled with a reason rather than as a chat that 403s on first send."""
    diagram_id = None
    if case != "local":
        for diagram in test_user_diagrams:
            db.session.add(diagram)
        if case == "owned":
            diagram_id = next(
                x.id for x in test_user_diagrams if x.user_id == test_user.id
            )
        else:
            other = next(x for x in test_user_diagrams if x.user_id != test_user.id)
            other.grant_access(
                test_user,
                (
                    btcopilot.ACCESS_READ_WRITE
                    if case == "shared"
                    else btcopilot.ACCESS_READ_ONLY
                ),
            )
            diagram_id = other.id
        db.session.commit()

    ac, mw = _mainWindow(create_ac_mw)
    if case == "local":
        fpath = os.path.join(tmp_path, "local.fd")
        util.touchFD(fpath)
        mw.open(fpath)
    else:
        _open(mw, diagram_id)

    assert mw.proPersonal().enabled == enabled
    assert bool(mw.proPersonal().disabledReason) == (not enabled)


@pytest.mark.parametrize("action", ["send", "extract"])
def test_cancelling_the_save_prompt_sends_nothing(
    qtbot, ownedCase, server_response, action
):
    """C8: declining the save must leave the case untouched — the coach reads
    the persisted row, so sending anyway would coach against stale facts."""
    mw, diagram_id, discussion_id, subject_id, expert_id = ownedCase
    mw.scene.addItem(Person(name="Unsaved"), undo=True)
    version = Diagram.query.get(diagram_id).version

    with server_response(_resource(discussion_id, action), body=_body(action, (subject_id, expert_id))):
        with _requests() as calls:
            qtbot.clickCancelAfter(lambda: _chat(mw, action))
    assert ("POST", _resource(discussion_id, action)) not in calls
    assert Diagram.query.get(diagram_id).version == version


@pytest.mark.parametrize("action", ["send", "extract"])
def test_saving_at_the_prompt_persists_before_sending(
    qtbot, ownedCase, server_response, action
):
    """C8: the save must land first — a send that overtakes it reaches the
    server before the facts it is supposed to be about."""
    mw, diagram_id, discussion_id, subject_id, expert_id = ownedCase
    mw.scene.addItem(Person(name="Unsaved"), undo=True)

    with server_response(_resource(discussion_id, action), body=_body(action, (subject_id, expert_id))):
        with _requests() as calls:
            qtbot.clickButtonAfter(lambda: _chat(mw, action), QMessageBox.Save)
            assert util.waitForCondition(
                lambda: ("POST", _resource(discussion_id, action)) in calls
            )
    paths = [path for _, path in calls]
    assert paths.index(f"/v1/diagrams/{diagram_id}") < paths.index(
        _resource(discussion_id, action)
    )
    assert mw.scene.stack().isClean() == True


@pytest.mark.parametrize("action", ["send", "extract"])
def test_saved_work_is_sent_without_a_prompt(ownedCase, server_response, action):
    """C8: prompting on every turn of a saved case would make the coach
    unusable."""
    mw, diagram_id, discussion_id, subject_id, expert_id = ownedCase
    assert mw.scene.stack().isClean() == True

    with server_response(_resource(discussion_id, action), body=_body(action, (subject_id, expert_id))):
        with _modals() as raised, _requests() as calls:
            _chat(mw, action)
            assert util.waitForCondition(
                lambda: ("POST", _resource(discussion_id, action)) in calls
            )
    assert raised == []


def test_reopening_the_same_case_ten_times_leaves_no_debris(
    test_activation, test_user, test_user_diagrams, create_ac_mw
):
    """Lifecycle: the drawer is rebuilt on every open, so a binding the coach
    fails to release accumulates warnings and eventually a dangling scene."""
    diagram_id = _ownedId(test_user, test_user_diagrams)
    ac, mw = _mainWindow(create_ac_mw)
    errors = []
    mw.documentView.qmlEngine().warnings.connect(
        lambda qmlErrors: errors.extend(qmlErrors)
    )

    for _ in range(10):
        _open(mw, diagram_id)
        mw.setDocument(None)

    assert [x.toString() for x in errors] == []
    assert mw.proPersonal().enabled == False


def test_pro_starts_without_personal_peripherals_or_preferences(
    test_activation, create_ac_mw, prefs, tmp_path
):
    """C9: speech, the recorder and the shake handler open OS audio/sensor
    sessions the desktop app has no business holding, and Personal's prefs keys
    would collide with Pro's own store."""
    ac, mw = _mainWindow(create_ac_mw)
    fpath = os.path.join(tmp_path, "local.fd")
    util.touchFD(fpath)
    mw.open(fpath)

    assert (
        _findInstances(mw, (QTextToSpeech, QAudioRecorder, ShakeDetector), depth=4) == []
    )
    assert mw.findChildren(ShakeDetector) == []
    assert [key for key in PERSONAL_PREFS_KEYS if prefs.contains(key)] == []



def _chatEntryPoints(mw):
    """Every way into the chat: the View menu action (and its Ctrl+4), the
    right-toolbar button, and the case-drawer tab."""
    caseProps = mw.documentView.caseProps
    # The drawer's QML is loaded lazily; a tab that does not exist yet is not
    # a way in either.
    tab = (
        caseProps.findItem("chatTabButton", noerror=True)
        if caseProps.qml is not None
        else None
    )
    return {
        "action visible": mw.ui.actionShow_Chat.isVisible(),
        # A hidden action still fires its shortcut; only a disabled one does not.
        "action enabled": mw.ui.actionShow_Chat.isEnabled(),
        "toolbar button": mw.documentView.view.rightToolBar.chatButton.visible(),
        "drawer tab": tab.property("visible") if tab is not None else False,
    }


# [Oracle: R-0048]
def test_a_release_build_hides_the_chat_entirely(
    test_activation, test_user, test_user_diagrams, create_ac_mw
):
    """Clearing ALPHABETA in version.py removes every way in. The suite runs as
    a release build, so this is the default state."""
    from pkdiagram import version

    assert version.IS_BETA == False, "the suite runs as a release build"

    ac, mw = _mainWindow(create_ac_mw)
    assert _chatEntryPoints(mw) == {
        "action visible": False,
        "action enabled": False,
        "toolbar button": False,
        "drawer tab": False,
    }


# [Oracle: R-0048]
@pytest.mark.beta
def test_a_beta_build_offers_the_chat(
    test_activation, test_user, test_user_diagrams, create_ac_mw
):
    """The mirror of the release case. A beta build honours beta licences and
    strips every other one, so this needs the beta licence its marker grants --
    without it the launch has no active features and blocks on the "Beta
    License Required" modal."""
    ac, mw = _mainWindow(create_ac_mw)
    offered = _chatEntryPoints(mw)
    assert offered["action visible"] == True

    assert offered["action enabled"] == True

    assert offered["toolbar button"] == True


# [Oracle: R-0048]
@pytest.mark.beta
def test_clicking_a_tab_selects_its_toolbar_button_and_action(
    test_activation, test_user, test_user_diagrams, create_ac_mw
):
    """A tab clicked in the drawer is as much a selection as the toolbar
    button, so exactly one button and one action end up checked."""
    diagram_id = _ownedId(test_user, test_user_diagrams)
    ac, mw = _mainWindow(create_ac_mw)
    _open(mw, diagram_id)
    toolBar = mw.documentView.view.rightToolBar

    # The drawer is open on the timeline, as the toolbar just put it.
    mw.documentView.showTimeline(True)
    assert util.waitForCondition(lambda: mw.ui.actionShow_Timeline.isChecked())

    mw.documentView.caseProps.setCurrentTab("chat")
    assert util.waitForCondition(lambda: toolBar.chatButton.isChecked())

    assert mw.ui.actionShow_Timeline.isChecked() == False

    assert toolBar.settingsButton.isChecked() == False

    assert toolBar.trianglesButton.isChecked() == False

    mw.documentView.caseProps.setCurrentTab("triangles")
    assert util.waitForCondition(lambda: toolBar.trianglesButton.isChecked())

    assert toolBar.chatButton.isChecked() == False


def _shift(person, year):
    return Event(
        kind=EventKind.Shift,
        person=person,
        dateTime=QDateTime(QDate(year, 5, 15)),
    )


# [Oracle: R-0061]
@pytest.mark.beta
@pytest.mark.parametrize("batched", [False, True])
def test_a_pro_edit_reaches_the_embedded_personal_views(
    test_activation, test_user, test_user_diagrams, create_ac_mw, batched
):
    """The ticket's promise: the embedded views read Pro's Scene, so an edit
    made in Pro shows up in them. Its failure mode is silent -- two views
    quietly disagreeing -- and a batch is the case that breaks, because it
    suppresses the per-item scene signals and never replays them, which is how
    a commit and a file load both arrive."""
    diagram_id = _ownedId(test_user, test_user_diagrams)
    ac, mw = _mainWindow(create_ac_mw)
    _open(mw, diagram_id)
    graph = mw.proPersonal().sarfGraphModel
    assert graph.scene is mw.scene, "the embedded views are not on Pro's Scene"

    person = Person(name="Connie")
    event = _shift(person, 1990)
    if batched:
        mw.scene.addItems(person, event, batch=True)
    else:
        mw.scene.addItem(person)
        mw.scene.addItem(event)

    assert [x["year"] for x in graph.events] == [1990]

    assert graph.events[0]["who"] == "Connie"
