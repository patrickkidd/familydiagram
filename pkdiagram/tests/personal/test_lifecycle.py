"""FD-336 WP-D: decomposition (C9) and async-callback lifecycle.

Written against the decomposed contract: PersonalAppController is a composition
root owning `discussion`, `pdpController` and `loader`, all sharing the root's
one Session, and every async server callback is bound to the Diagram it was
issued for.
"""

import pickle
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from PyQt5.QtMultimedia import QAudioRecorder
from PyQt5.QtTextToSpeech import QTextToSpeech

from btcopilot.extensions import db
from btcopilot.schema import DiagramData, PDP, Person, asdict

from pkdiagram import util
from pkdiagram.app import Session
from pkdiagram.personal import PersonalAppController
from pkdiagram.personal.models import Discussion
from pkdiagram.pyqt import QObject
from pkdiagram.scene import Scene
from pkdiagram.server_types import Diagram

pytestmark = [pytest.mark.component("Personal")]


@pytest.fixture
def stored_discussion(test_user):
    from btcopilot.personal.models import Discussion as StoredDiscussion

    discussion = StoredDiscussion(
        user_id=test_user.id, diagram_id=test_user.free_diagram_id
    )
    db.session.add(discussion)
    return discussion


def _diagram(user_id, id=1):
    return Diagram(
        id=id,
        user_id=user_id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(DiagramData(pdp=PDP()))),
    )


def _findInstances(root, types, depth=2):
    """Instances of `types` held by `root` or by any QObject it holds, to
    `depth` hops. Deep enough to find a component's member either on the root
    or one level down after decomposition."""
    found, seen, level = [], {id(root)}, [root]
    for _ in range(depth):
        nextLevel = []
        for obj in level:
            for value in getattr(obj, "__dict__", {}).values():
                if isinstance(value, types):
                    found.append(value)
                elif isinstance(value, QObject) and id(value) not in seen:
                    seen.add(id(value))
                    nextLevel.append(value)
        level = nextLevel
    return found


def test_components_share_the_root_session(personalApp: PersonalAppController):
    """C9: decomposition must not introduce a second Session — a second one
    would authenticate separately and desync the token."""
    assert personalApp.discussion.session is personalApp.session
    assert personalApp.pdpController.session is personalApp.session

    sessions = _findInstances(personalApp, Session)
    assert set(id(x) for x in sessions) == {id(personalApp.session)}


def test_no_speech_or_audio_objects_until_used(personalApp: PersonalAppController):
    """C9: TTS and the audio recorder stay lazy — constructing either at
    startup activates the OS audio session on iOS."""
    assert _findInstances(personalApp, (QTextToSpeech, QAudioRecorder)) == []

    personalApp.tts.setAutoReadAloud(True)
    assert len(_findInstances(personalApp, QTextToSpeech)) == 1
    assert _findInstances(personalApp, QAudioRecorder) == []


def test_extract_response_after_diagram_switch_leaves_new_diagram_untouched(
    test_user, personalApp: PersonalAppController
):
    """An extract issued for case A whose response lands after the user switched
    to case B must not write A's people into B."""
    pdpController = personalApp.pdpController
    sceneA, sceneB = Scene(), Scene()
    diagramA, diagramB = _diagram(test_user.id, id=1), _diagram(test_user.id, id=2)
    personalApp.setScene(sceneA)
    personalApp.setDiagram(
        diagramA, [Discussion(id=7, user_id=test_user.id, diagram_id=diagramA.id)]
    )
    personalApp.discussion.setCurrentDiscussion(7)

    callbacks = []

    def nonBlockingRequest(verb, path, success=None, **kwargs):
        callbacks.append(success)
        return MagicMock()

    server = MagicMock()
    server.nonBlockingRequest.side_effect = nonBlockingRequest
    with patch.object(personalApp.session, "server", return_value=server):
        pdpController.extractFull()
    assert len(callbacks) == 1

    personalApp.setScene(sceneB)
    personalApp.setDiagram(diagramB)

    pdpChanged = util.Condition(pdpController.pdpChanged)
    extractCompleted = util.Condition(pdpController.extractCompleted)
    callbacks[0](
        {
            "pdp": asdict(PDP(people=[Person(id=-1, name="Ghost")])),
            "people_count": 1,
            "events_count": 0,
            "pair_bonds_count": 0,
            "pending_extracted_through_order": 3,
        }
    )
    assert diagramB.getDiagramData().pdp.people == []
    assert pdpChanged.callCount == 0
    assert extractCompleted.callCount == 0

    sceneA.deinit()
    sceneB.deinit()


def test_rebuild_poll_after_unbind_stops(test_user, personalApp: PersonalAppController):
    """Unbinding the diagram mid-rebuild must stop the poll loop: a poll reply
    arriving afterwards drives no progress and schedules no further request."""
    pdpController = personalApp.pdpController
    scene = Scene()
    personalApp.setScene(scene)
    personalApp.setDiagram(
        _diagram(test_user.id), [Discussion(id=7, user_id=test_user.id, diagram_id=1)]
    )
    personalApp.discussion.setCurrentDiscussion(7)

    polls = []

    def nonBlockingRequest(verb, path, success=None, **kwargs):
        if path.endswith("/deep-reextract"):
            success({"task_id": "task-1"})
        else:
            polls.append(success)
        return MagicMock()

    server = MagicMock()
    server.nonBlockingRequest.side_effect = nonBlockingRequest
    with patch.object(personalApp.session, "server", return_value=server):
        pdpController.rebuildDiagram(6)
        assert len(polls) == 1

        pdpController.setDiagram(None)
        requestsBeforeLatePoll = server.nonBlockingRequest.call_count
        rebuildProgress = util.Condition(pdpController.rebuildProgress)
        polls[0](
            {
                "status": "progress",
                "current": 3,
                "total": 6,
                "label": "Rebuilding 3 of 6",
            }
        )
        assert rebuildProgress.wait(maxMS=1500) is False
        assert server.nonBlockingRequest.call_count == requestsBeforeLatePoll

    scene.deinit()


def test_diagramLoaded_wires_scene_and_discussions(
    test_user, stored_discussion, personalApp: PersonalAppController
):
    """Standalone regression lock: the load the fixture already ran, plus a
    second load, must leave the PDP controller on the loaded scene and the
    discussion controller holding the loaded discussions."""
    assert set(x.id for x in personalApp.discussion.discussions) == {
        stored_discussion.id
    }
    assert personalApp.pdpController.scene is personalApp.scene

    scene = Scene()
    diagram = _diagram(test_user.id, id=2)
    discussions = [Discussion(id=99, user_id=test_user.id, diagram_id=diagram.id)]
    personalApp.diagramLoader.diagramLoaded.emit(diagram, scene, discussions)
    assert personalApp.pdpController.scene is scene
    assert [x.id for x in personalApp.discussion.discussions] == [99]

    scene.deinit()
