import contextlib
import json
import os
import pickle
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from pkdiagram.personal import PersonalAppController
from pkdiagram.personal.models import (
    Discussion,
    Statement,
    Speaker,
    SpeakerType,
)
from pkdiagram import util
from pkdiagram.server_types import Diagram
from pkdiagram.pyqt import QNetworkReply
from PyQt5.QtCore import QByteArray
from PyQt5.QtWidgets import QMessageBox

from btcopilot.extensions import db
from btcopilot.schema import DiagramData, PDP, Person, PairBond, asdict

pytestmark = [
    pytest.mark.component("Personal"),
    pytest.mark.depends_on("Session"),
]


@pytest.fixture
def discussion(test_user):
    from btcopilot.personal.models import Discussion

    discussion = Discussion(user_id=test_user.id, diagram_id=test_user.free_diagram_id)
    db.session.add(discussion)
    return discussion


def test_refreshDiagram(
    flask_app, test_user, discussion, personalApp: PersonalAppController
):
    # _refreshDiagram is already called by fixture via session.init -> onSessionChanged
    # Just verify the result
    assert set(x.id for x in personalApp.discussion.discussions) == {discussion.id}


@pytest.mark.parametrize("success", [True, False])
def test_sendStatement(
    server_error, test_user, discussion, personalApp: PersonalAppController, success
):

    from btcopilot.personal.chat import Response

    RESPONSE = Response(statement="some response")

    requestSent = util.Condition(personalApp.discussion.requestSent)
    responseReceived = util.Condition(personalApp.discussion.responseReceived)
    serverError = util.Condition(personalApp.discussion.serverError)
    serverDown = util.Condition(personalApp.discussion.serverDown)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("btcopilot.personal.routes.discussions.ask", return_value=RESPONSE)
        )
        stack.enter_context(
            patch.object(
                personalApp.discussion,
                "_currentDiscussion",
                Discussion(
                    id=discussion.id,
                    user_id=test_user.id,
                    diagram_id=test_user.free_diagram_id,
                    statements=[
                        Statement(
                            id=1,
                            text="blah",
                            speaker=Speaker(
                                id=1, person_id=1, name="Test", type=SpeakerType.Subject
                            ),
                        )
                    ],
                ),
            )
        )
        if not success:
            stack.enter_context(server_error())
        personalApp.discussion.sendStatement("test message")
    assert requestSent.callCount == 1
    if success:
        assert responseReceived.wait()
        assert responseReceived.callArgs[0][0] == RESPONSE.statement
        assert serverError.callCount == 0
    else:
        assert serverError.wait()
        assert responseReceived.callCount == 0
    assert serverDown.callCount == 0


def test_acceptPDPItem_undo(test_user, personalApp: PersonalAppController):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    with patch.object(personalApp.pdpController, "_doAcceptPDPItem") as accept:
        personalApp.pdpController.acceptPDPItem(-1)
        assert accept.call_count == 1
        assert personalApp._undoStack.count() == 1
        assert personalApp._undoStack.canUndo()

        personalApp._undoStack.undo()
        expected = asdict(initial_diagram_data.pdp)
        expected["committedPeople"] = []
        assert personalApp.pdpController.pdp == expected
        assert not personalApp._undoStack.canUndo()
        assert personalApp._undoStack.canRedo()

        personalApp._undoStack.redo()
        assert accept.call_count == 2
        assert not personalApp._undoStack.canRedo()


def test_rejectPDPItem_undo(test_user, personalApp: PersonalAppController):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    with patch.object(personalApp.pdpController, "_doRejectPDPItem") as reject:
        personalApp.pdpController.rejectPDPItem(-1)
        assert reject.call_count == 1
        assert personalApp._undoStack.count() == 1
        assert personalApp._undoStack.canUndo()

        personalApp._undoStack.undo()
        expected = asdict(initial_diagram_data.pdp)
        expected["committedPeople"] = []
        assert personalApp.pdpController.pdp == expected
        assert not personalApp._undoStack.canUndo()
        assert personalApp._undoStack.canRedo()

        personalApp._undoStack.redo()
        assert reject.call_count == 2
        assert not personalApp._undoStack.canRedo()


def test_pdp_surfaces_pair_bonds_and_parents_link(
    test_user, personalApp: PersonalAppController
):
    """FD-332: a pair bond (e.g. setting someone's parents) must be reviewable
    in the PDP, not silently invisible. The pdp property exposes pair_bonds and
    resolvePairBondChildren names the person whose parents it sets so the card
    can emphasize the change."""
    diagram_data = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Wally"),
                Person(id=-2, name="Louann"),
                Person(id=-3, name="Robert", parents=-10),
            ],
            pair_bonds=[PairBond(id=-10, person_a=-1, person_b=-2)],
        )
    )
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(diagram_data)),
    ))

    pdp = personalApp.pdpController.pdp
    assert [pb["id"] for pb in pdp["pair_bonds"]] == [-10]
    assert personalApp.pdpController.resolvePersonName(-1) == "Wally"
    assert personalApp.pdpController.resolvePairBondChildren(-10) == "Robert"
    assert personalApp.pdpController.resolvePairBondChildren(None) == ""


def test_undo_stack_multiple_operations(test_user, personalApp: PersonalAppController):
    diagram_data1 = DiagramData(pdp=PDP(people=[Person(id=-1, name="Person1")]))
    diagram_data2 = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="Person1"), Person(id=-2, name="Person2")])
    )

    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(diagram_data1)),
    ))

    with (
        patch.object(personalApp.pdpController, "_doAcceptPDPItem"),
        patch.object(personalApp.pdpController, "_doRejectPDPItem"),
    ):
        personalApp.pdpController.acceptPDPItem(-1)
        personalApp._diagram.setDiagramData(diagram_data2)
        personalApp.pdpController.rejectPDPItem(-2)

        assert personalApp._undoStack.count() == 2

        personalApp._undoStack.undo()
        expected2 = asdict(diagram_data2.pdp)
        expected2["committedPeople"] = []
        assert personalApp.pdpController.pdp == expected2

        personalApp._undoStack.undo()
        expected1 = asdict(diagram_data1.pdp)
        expected1["committedPeople"] = []
        assert personalApp.pdpController.pdp == expected1


def test_acceptPDPItem_failure_doesnt_push_to_stack(
    test_user, personalApp: PersonalAppController
):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    count_before = personalApp._undoStack.count()

    with patch.object(personalApp.pdpController, "_doAcceptPDPItem", return_value=False):
        result = personalApp.pdpController.acceptPDPItem(-1)

    assert result is False
    assert personalApp._undoStack.count() == count_before


def test_rejectPDPItem_failure_doesnt_push_to_stack(
    test_user, personalApp: PersonalAppController
):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    count_before = personalApp._undoStack.count()

    with patch.object(personalApp.pdpController, "_doRejectPDPItem", return_value=False):
        result = personalApp.pdpController.rejectPDPItem(-1)

    assert result is False
    assert personalApp._undoStack.count() == count_before


def test_diagram_save_shows_error_on_unexpected_status(test_user):
    from pkdiagram.pyqt import QMessageBox
    from pkdiagram.server_types import HTTPError

    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    mock_server = MagicMock()
    mock_server.blockingRequest.side_effect = HTTPError(
        "Unexpected server error", status_code=500
    )

    with patch.object(QMessageBox, "critical") as mock_critical:

        def applyChange(diagramData: DiagramData):
            return diagramData

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        success = diagram.save(
            mock_server, applyChange, stillValidAfterRefresh, useJson=True
        )

        assert success is False
        assert mock_critical.call_count == 1
        args = mock_critical.call_args[0]
        assert "500" in args[2]


def test_importJournalNotes_emits_summary_dict_with_correct_keys(
    test_user, personalApp: PersonalAppController
):
    from btcopilot.schema import DiagramData, PDP, PDPDeltas, Event, EventKind
    from unittest.mock import AsyncMock
    from pkdiagram.pyqt import QMessageBox

    initial_diagram_data = DiagramData(pdp=PDP())
    personalApp.setDiagram(Diagram(
        id=test_user.free_diagram_id,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    mock_pdp = PDP(
        people=[Person(id=-1, name="TestPerson"), Person(id=-2, name="Mom")],
        events=[Event(id=-3, kind=EventKind.Shift, description="called")],
    )
    mock_deltas = PDPDeltas(
        people=[Person(id=-1, name="TestPerson"), Person(id=-2, name="Mom")],
        events=[Event(id=-3, kind=EventKind.Shift, description="called")],
        pair_bonds=[],
    )

    with (
        patch(
            "btcopilot.pdp.import_text",
            AsyncMock(return_value=(mock_pdp, mock_deltas)),
        ),
        patch.object(QMessageBox, "information") as info_mock,
    ):
        completed = util.Condition(personalApp.pdpController.journalImportCompleted)
        personalApp.pdpController.importJournalNotes("Some journal text")
        assert completed.wait()

    summary = completed.callArgs[0][0]
    assert "people" in summary, f"'people' key missing from summary: {summary}"
    assert "events" in summary, f"'events' key missing from summary: {summary}"
    assert "pairBonds" in summary, f"'pairBonds' key missing from summary: {summary}"
    assert summary["people"] == 2
    assert summary["events"] == 1
    assert summary["pairBonds"] == 0


def test_importJournalNotes_no_diagram(test_user, personalApp: PersonalAppController):
    from pkdiagram.pyqt import QMessageBox

    personalApp.setDiagram(None)

    failed = util.Condition(personalApp.pdpController.journalImportFailed)

    with patch.object(QMessageBox, "critical"):
        personalApp.pdpController.importJournalNotes("Some journal text")
        assert failed.wait()

    assert "No diagram loaded" in failed.callArgs[0][0]


def test_acceptAllPDPItems_adds_to_scene(test_user, personalApp: PersonalAppController):
    from btcopilot.schema import Event, EventKind

    initial_diagram_data = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="TestPerson")],
            events=[Event(id=-2, kind=EventKind.Shift, person=-1, description="test")],
        )
    )
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    with patch.object(personalApp.pdpController, "_addCommittedItemsToScene") as add_mock:
        with patch.object(personalApp._diagram, "save", return_value=True):
            personalApp.pdpController.acceptAllPDPItems()
            assert add_mock.call_count == 1
            args = add_mock.call_args[0][0]
            assert "people" in args
            assert "events" in args
            assert "pair_bonds" in args


def test_dismissEmptyExtraction_advances_cursor(
    test_user, discussion, personalApp: PersonalAppController
):
    """An empty extraction shows an info dialog (not a deck); dismissing it must
    still mark the conversation covered — POST commit-pdp with empty item_ids and
    full_accept True, same cursor advance as a full accept."""
    personalApp.discussion._currentDiscussion = discussion
    server = MagicMock()
    with patch.object(personalApp.session, "server", return_value=server):
        personalApp.pdpController.dismissEmptyExtraction()

    server.nonBlockingRequest.assert_called_once()
    args, kwargs = server.nonBlockingRequest.call_args
    assert args[0] == "POST"
    assert args[1] == f"/personal/discussions/{discussion.id}/commit-pdp"
    assert kwargs["data"]["item_ids"] == []
    assert kwargs["data"]["full_accept"] is True


def test_dismissEmptyExtraction_no_discussion_is_noop(
    test_user, personalApp: PersonalAppController
):
    """No current discussion -> _postCommitPdp guard returns before building
    the f-string path off _currentDiscussion.id (would AttributeError on None).
    Must not raise and must not POST."""
    personalApp.discussion._currentDiscussion = None
    server = MagicMock()
    with patch.object(personalApp.session, "server", return_value=server):
        personalApp.pdpController.dismissEmptyExtraction()

    server.nonBlockingRequest.assert_not_called()


def test_acceptPDPItem_posts_commit_pdp_partial(
    test_user, discussion, personalApp: PersonalAppController
):
    """Accepting one of several staged items POSTs commit-pdp with that id and
    full_accept False (cursor must not advance)."""
    initial = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="A"), Person(id=-2, name="B")])
    )
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial)),
    ))
    personalApp.discussion._currentDiscussion = discussion
    server = MagicMock()
    with (
        patch.object(personalApp.pdpController, "_addCommittedItemsToScene"),
        patch.object(personalApp._diagram, "save", return_value=True),
        patch.object(personalApp.session, "server", return_value=server),
    ):
        personalApp.pdpController._doAcceptPDPItem(-1)

    server.nonBlockingRequest.assert_called_once()
    args, kwargs = server.nonBlockingRequest.call_args
    assert args[0] == "POST"
    assert args[1] == f"/personal/discussions/{discussion.id}/commit-pdp"
    assert kwargs["data"] == {"item_ids": [-1], "full_accept": False}


def test_acceptAllPDPItems_posts_commit_pdp_full(
    test_user, discussion, personalApp: PersonalAppController
):
    """Accept-all POSTs commit-pdp with every id and full_accept True so the
    re-extraction cursor advances."""
    initial = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="A"), Person(id=-2, name="B")])
    )
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial)),
    ))
    personalApp.discussion._currentDiscussion = discussion
    server = MagicMock()
    with (
        patch.object(personalApp.pdpController, "_addCommittedItemsToScene"),
        patch.object(personalApp._diagram, "save", return_value=True),
        patch.object(personalApp.session, "server", return_value=server),
    ):
        personalApp.pdpController.acceptAllPDPItems()

    server.nonBlockingRequest.assert_called_once()
    args, kwargs = server.nonBlockingRequest.call_args
    assert args[1] == f"/personal/discussions/{discussion.id}/commit-pdp"
    assert set(kwargs["data"]["item_ids"]) == {-1, -2}
    assert kwargs["data"]["full_accept"] is True


def test_acceptPDPItem_triggers_cluster_detection(
    test_user, personalApp: PersonalAppController
):
    """Auto-detect clusters after accepting a single PDP item (T7-12)."""
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    with (
        patch.object(personalApp.pdpController, "_doAcceptPDPItem", return_value=True),
        patch.object(personalApp.clusterModel, "detect") as detect_mock,
    ):
        personalApp.pdpController.acceptPDPItem(-1)
        assert detect_mock.call_count == 1


def test_acceptPDPItem_failure_skips_cluster_detection(
    test_user, personalApp: PersonalAppController
):
    """No cluster detection when PDP accept fails (T7-12)."""
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    with (
        patch.object(personalApp.pdpController, "_doAcceptPDPItem", return_value=False),
        patch.object(personalApp.clusterModel, "detect") as detect_mock,
    ):
        personalApp.pdpController.acceptPDPItem(-1)
        assert detect_mock.call_count == 0


def test_acceptAllPDPItems_triggers_cluster_detection(
    test_user, personalApp: PersonalAppController
):
    """Auto-detect clusters after accepting all PDP items (T7-12)."""
    from btcopilot.schema import Event, EventKind

    initial_diagram_data = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="TestPerson")],
            events=[Event(id=-2, kind=EventKind.Shift, person=-1, description="test")],
        )
    )
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    with (
        patch.object(personalApp.pdpController, "_addCommittedItemsToScene"),
        patch.object(personalApp._diagram, "save", return_value=True),
        patch.object(personalApp.clusterModel, "detect") as detect_mock,
    ):
        personalApp.pdpController.acceptAllPDPItems()
        assert detect_mock.call_count == 1


def test_clearDiagramData_batch_removal(test_user, personalApp: PersonalAppController):
    """clearDiagramData uses batch removal to avoid stale cross-references.

    Without batch mode, removing events one-by-one triggers _do_removeItem's
    signal emission path which calls scene.find(id=event.person) — this can
    resolve to an ItemDetails instead of a Person when IDs collide in the
    itemRegistry, causing AttributeError: 'ItemDetails' has no 'onEventRemoved'.
    """
    from pkdiagram.scene import Person as ScenePerson, Event as SceneEvent
    from btcopilot.schema import EventKind

    scene = personalApp.scene
    p1, p2 = scene.addItems(ScenePerson(name="p1"), ScenePerson(name="p2"))
    scene.addItem(SceneEvent(EventKind.Shift, p1, dateTime=util.Date(2020, 1, 1)))
    scene.addItem(SceneEvent(EventKind.Shift, p2, dateTime=util.Date(2021, 1, 1)))
    assert len(scene.events()) == 2

    initial_diagram_data = DiagramData(pdp=PDP())
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    batchCalls = []
    origSetBatch = scene.setBatchAddingRemovingItems

    def trackBatch(on):
        batchCalls.append(on)
        origSetBatch(on)

    with (
        patch.object(personalApp._diagram, "save", return_value=True),
        patch.object(scene, "setBatchAddingRemovingItems", side_effect=trackBatch),
    ):
        personalApp.pdpController.clearDiagramData(True)

    assert len(scene.events()) == 0
    assert batchCalls == [True, False], f"Expected batch mode on/off, got {batchCalls}"


def test_clearDiagramData_works_when_scene_is_None(
    test_user, personalApp: PersonalAppController
):
    """When the diagram blob is corrupt enough that Scene.read raises and
    `setScene` was never called, clearDiagramData must still run the
    server-side blob mutation. Without this, the iPhone is wedged: the user
    has no in-app recovery and the bad blob never gets rewritten.
    """
    initial_diagram_data = DiagramData(pdp=PDP())
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))
    personalApp.scene = personalApp.pdpController.scene = None

    saveCall = {"called": False, "applyChange": None}

    def fakeSave(server, applyChange, stillValid, **kwargs):
        saveCall["called"] = True
        saveCall["applyChange"] = applyChange
        return True

    with patch.object(personalApp._diagram, "save", side_effect=fakeSave):
        personalApp.pdpController.clearDiagramData(True)

    assert saveCall["called"], "save() must run even when scene is None"

    probeData = DiagramData(
        people=[{"id": 1}, {"id": 2}, {"id": 3}],
        events=[{"id": 100, "kind": "shift"}],
        pair_bonds=[{"id": 200}],
        emotions=[{"id": 300}],
        pdp=PDP(),
    )
    saveCall["applyChange"](probeData)
    assert probeData.events == []
    assert probeData.pair_bonds == []
    assert probeData.emotions == []
    assert {p["id"] for p in probeData.people} == {1, 2}
    assert probeData.pdp is None


# ── Voice Recording & Transcription Tests ──


def test_startRecording_creates_temp_file_and_records(
    personalApp: PersonalAppController,
):
    """startRecording creates a temp WAV file and calls recorder.record()."""
    personalApp.voice._ensure()
    with (
        patch.object(personalApp.voice._recorder, "setEncodingSettings"),
        patch.object(personalApp.voice._recorder, "setOutputLocation"),
        patch.object(personalApp.voice._recorder, "record") as mock_record,
    ):
        personalApp.voice.start()

    assert mock_record.call_count == 1
    assert personalApp.voice._filePath.endswith(".wav")
    assert "fd_voice_" in personalApp.voice._filePath
    # Cleanup the temp file created
    if os.path.exists(personalApp.voice._filePath):
        os.unlink(personalApp.voice._filePath)


def test_startRecording_emits_recordingFailed_on_error(
    personalApp: PersonalAppController,
):
    """startRecording emits recordingFailed if an exception occurs."""
    from pkdiagram.pyqt import QMessageBox

    failed = util.Condition(personalApp.voice.recordingFailed)

    # DiscussView.qml's onRecordingFailed handler calls util.criticalBox
    # which pops a modal QMessageBox. Patch it so emit doesn't deadlock.
    with (
        patch(
            "pkdiagram.personal.audio.tempfile.NamedTemporaryFile",
            side_effect=OSError("disk full"),
        ),
        patch.object(QMessageBox, "critical") as mock_critical,
    ):
        personalApp.voice.start()

    assert failed.callCount == 1
    assert "disk full" in failed.callArgs[0][0]
    assert mock_critical.call_count == 1


def test_stopRecording_stops_recorder_and_transcribes(
    personalApp: PersonalAppController,
):
    """stopRecording stops the recorder and begins transcription."""
    personalApp.voice._ensure()
    # Create a real temp file so the path exists check passes
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()
    personalApp.voice._filePath = tmpFile.name

    with (
        patch.object(personalApp.voice._recorder, "stop") as mock_stop,
        patch.object(personalApp.voice, "_transcribe") as mock_transcribe,
    ):
        personalApp.voice.stop()

    assert mock_stop.call_count == 1
    assert mock_transcribe.call_count == 1
    assert mock_transcribe.call_args[0][0] == tmpFile.name

    # Cleanup
    if os.path.exists(tmpFile.name):
        os.unlink(tmpFile.name)


def test_stopRecording_emits_failed_when_no_file(
    personalApp: PersonalAppController,
):
    """stopRecording emits transcriptionFailed if recording file is missing."""
    personalApp.voice._ensure()
    from pkdiagram.pyqt import QMessageBox

    failed = util.Condition(personalApp.voice.transcriptionFailed)
    personalApp.voice._filePath = "/nonexistent/path.wav"

    with (
        patch.object(personalApp.voice._recorder, "stop"),
        patch.object(QMessageBox, "critical") as mock_critical,
    ):
        personalApp.voice.stop()

    assert failed.callCount == 1
    assert "not found" in failed.callArgs[0][0]
    assert mock_critical.call_count == 1


def test_stopRecording_emits_failed_when_empty_path(
    personalApp: PersonalAppController,
):
    """stopRecording emits transcriptionFailed if _recordingFilePath is empty."""
    personalApp.voice._ensure()
    from pkdiagram.pyqt import QMessageBox

    failed = util.Condition(personalApp.voice.transcriptionFailed)
    personalApp.voice._filePath = ""

    with (
        patch.object(personalApp.voice._recorder, "stop"),
        patch.object(QMessageBox, "critical") as mock_critical,
    ):
        personalApp.voice.stop()

    assert failed.callCount == 1
    assert mock_critical.call_count == 1


def test_cancelRecording_stops_and_cleans_up(
    personalApp: PersonalAppController,
):
    """cancelRecording stops the recorder, cleans up temp file, resets path."""
    personalApp.voice._ensure()
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()
    personalApp.voice._filePath = tmpFile.name

    with patch.object(personalApp.voice._recorder, "stop") as mock_stop:
        personalApp.voice.cancel()

    assert mock_stop.call_count == 1
    assert personalApp.voice._filePath == ""
    assert not os.path.exists(tmpFile.name), "Temp file should be deleted on cancel"


def test_cancelRecording_does_not_transcribe(
    personalApp: PersonalAppController,
):
    """cancelRecording should NOT trigger transcription."""
    personalApp.voice._ensure()
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()
    personalApp.voice._filePath = tmpFile.name

    with (
        patch.object(personalApp.voice._recorder, "stop"),
        patch.object(personalApp.voice, "_transcribe") as mock_transcribe,
    ):
        personalApp.voice.cancel()

    assert mock_transcribe.call_count == 0

    # Cleanup if still present
    if os.path.exists(tmpFile.name):
        os.unlink(tmpFile.name)


def test_voice_state_idle_to_recording_to_transcribing_to_idle(
    personalApp: PersonalAppController,
):
    """Full voice state machine: idle → startRecording → stopRecording → transcriptionReady → idle."""
    personalApp.voice._ensure()
    import tempfile as _tempfile

    # Start in idle state
    assert personalApp.voice._filePath == ""

    # Transition to recording
    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()

    with (
        patch.object(personalApp.voice._recorder, "setEncodingSettings"),
        patch.object(personalApp.voice._recorder, "setOutputLocation"),
        patch.object(personalApp.voice._recorder, "record"),
    ):
        personalApp.voice.start()

    assert personalApp.voice._filePath != ""  # Now recording

    # Transition to transcribing → idle (mock the transcription pipeline)
    with (
        patch.object(personalApp.voice._recorder, "stop"),
        patch.object(personalApp.voice, "_transcribe") as mock_transcribe,
    ):
        personalApp.voice.stop()
        assert mock_transcribe.call_count == 1

    # Cleanup
    if os.path.exists(personalApp.voice._filePath):
        os.unlink(personalApp.voice._filePath)


def test_short_tap_cancel_does_not_transcribe(
    personalApp: PersonalAppController,
):
    """Simulates short tap behavior: startRecording then immediate cancelRecording (no transcription)."""
    personalApp.voice._ensure()
    import tempfile as _tempfile

    with (
        patch.object(personalApp.voice._recorder, "setEncodingSettings"),
        patch.object(personalApp.voice._recorder, "setOutputLocation"),
        patch.object(personalApp.voice._recorder, "record"),
    ):
        personalApp.voice.start()

    filePath = personalApp.voice._filePath
    assert filePath != ""

    with (
        patch.object(personalApp.voice._recorder, "stop"),
        patch.object(personalApp.voice, "_transcribe") as mock_transcribe,
    ):
        personalApp.voice.cancel()

    assert mock_transcribe.call_count == 0
    assert personalApp.voice._filePath == ""
    # Temp file should be cleaned up
    assert not os.path.exists(filePath)


def test_transcribeAudio_emits_failed_without_api_key(
    personalApp: PersonalAppController,
):
    """_transcribeAudio emits transcriptionFailed if no API key is configured."""
    import tempfile as _tempfile
    from pkdiagram.pyqt import QMessageBox

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.write(b"fake audio data")
    tmpFile.close()

    failed = util.Condition(personalApp.voice.transcriptionFailed)

    def fakeRequest(verb, path, success=None, error=None, **kwargs):
        success({"api_key": ""})
        return MagicMock()

    with (
        patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": ""}, clear=False),
        patch.object(
            personalApp.session.server(),
            "nonBlockingRequest",
            side_effect=fakeRequest,
        ),
        patch.object(QMessageBox, "critical") as mock_critical,
    ):
        personalApp.voice._transcribe(tmpFile.name)

    assert failed.callCount == 1
    assert "AssemblyAI" in failed.callArgs[0][0]
    assert not os.path.exists(tmpFile.name), "Should cleanup on failure"
    assert mock_critical.call_count == 1


def test_transcribeAudio_emits_failed_on_file_read_error(
    personalApp: PersonalAppController,
):
    """_transcribeAudio emits transcriptionFailed if audio file can't be read."""
    from pkdiagram.pyqt import QMessageBox

    failed = util.Condition(personalApp.voice.transcriptionFailed)

    with (
        patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "test-key"}, clear=False),
        patch.object(QMessageBox, "critical") as mock_critical,
    ):
        personalApp.voice._transcribe("/nonexistent/audio.wav")

    assert failed.callCount == 1
    assert "Failed to read recording" in failed.callArgs[0][0]
    assert mock_critical.call_count == 1


def test_onUploadFinished_emits_failed_on_network_error(
    personalApp: PersonalAppController,
):
    """_onUploadFinished emits transcriptionFailed on network error."""
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()

    failed = util.Condition(personalApp.voice.transcriptionFailed)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.ConnectionRefusedError
    mockReply.errorString.return_value = "Connection refused"
    mockReply.deleteLater = MagicMock()

    with patch.object(QMessageBox, "critical") as mock_critical:
        personalApp.voice._onUploadFinished(mockReply, "test-key", tmpFile.name)

    assert failed.callCount == 1
    assert "Upload failed" in failed.callArgs[0][0]
    assert not os.path.exists(tmpFile.name)
    assert mock_critical.call_count == 1


def test_onUploadFinished_emits_failed_when_no_upload_url(
    personalApp: PersonalAppController,
):
    """_onUploadFinished emits transcriptionFailed if upload_url is missing from response."""
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()

    failed = util.Condition(personalApp.voice.transcriptionFailed)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.NoError
    mockReply.readAll.return_value = QByteArray(json.dumps({}).encode())
    mockReply.deleteLater = MagicMock()

    with patch.object(QMessageBox, "critical") as mock_critical:
        personalApp.voice._onUploadFinished(mockReply, "test-key", tmpFile.name)

    assert failed.callCount == 1
    assert "no URL" in failed.callArgs[0][0]
    assert not os.path.exists(tmpFile.name)
    assert mock_critical.call_count == 1


def test_onPollFinished_emits_transcriptionReady_on_completed(
    personalApp: PersonalAppController,
):
    """_onPollFinished emits transcriptionReady when status is 'completed'."""
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()

    ready = util.Condition(personalApp.voice.transcriptionReady)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.NoError
    mockReply.readAll.return_value = QByteArray(
        json.dumps({"status": "completed", "text": "Hello world"}).encode()
    )
    mockReply.deleteLater = MagicMock()

    personalApp.voice._onPollFinished(mockReply, "txn-123", "test-key", tmpFile.name)

    assert ready.callCount == 1
    assert ready.callArgs[0][0] == "Hello world"
    assert not os.path.exists(tmpFile.name)


def test_onPollFinished_emits_failed_on_error_status(
    personalApp: PersonalAppController,
):
    """_onPollFinished emits transcriptionFailed when status is 'error'."""
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()

    failed = util.Condition(personalApp.voice.transcriptionFailed)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.NoError
    mockReply.readAll.return_value = QByteArray(
        json.dumps({"status": "error", "error": "Audio too short"}).encode()
    )
    mockReply.deleteLater = MagicMock()

    with patch.object(QMessageBox, "critical") as mock_critical:
        personalApp.voice._onPollFinished(mockReply, "txn-123", "test-key", tmpFile.name)

    assert failed.callCount == 1
    assert "Audio too short" in failed.callArgs[0][0]
    assert not os.path.exists(tmpFile.name)
    assert mock_critical.call_count == 1


def test_onPollFinished_repolls_on_processing_status(
    personalApp: PersonalAppController,
):
    """_onPollFinished schedules a re-poll when status is 'processing'."""
    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.NoError
    mockReply.readAll.return_value = QByteArray(
        json.dumps({"status": "processing"}).encode()
    )
    mockReply.deleteLater = MagicMock()

    with patch("PyQt5.QtCore.QTimer.singleShot") as mock_timer:
        personalApp.voice._onPollFinished(mockReply, "txn-123", "test-key", "/tmp/test.wav")

    assert mock_timer.call_count == 1
    assert mock_timer.call_args[0][0] == 1000  # 1 second delay


def test_onTranscriptSubmitted_emits_failed_on_network_error(
    personalApp: PersonalAppController,
):
    """_onTranscriptSubmitted emits transcriptionFailed on network error."""
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()

    failed = util.Condition(personalApp.voice.transcriptionFailed)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.ConnectionRefusedError
    mockReply.errorString.return_value = "Connection refused"
    mockReply.deleteLater = MagicMock()

    with patch.object(QMessageBox, "critical") as mock_critical:
        personalApp.voice._onTranscriptSubmitted(mockReply, "test-key", tmpFile.name)

    assert failed.callCount == 1
    assert "failed" in failed.callArgs[0][0].lower()
    assert not os.path.exists(tmpFile.name)
    assert mock_critical.call_count == 1


def test_onTranscriptSubmitted_emits_failed_when_no_id(
    personalApp: PersonalAppController,
):
    """_onTranscriptSubmitted emits transcriptionFailed if no transcript ID returned."""
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()

    failed = util.Condition(personalApp.voice.transcriptionFailed)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.NoError
    mockReply.readAll.return_value = QByteArray(json.dumps({}).encode())
    mockReply.deleteLater = MagicMock()

    with patch.object(QMessageBox, "critical") as mock_critical:
        personalApp.voice._onTranscriptSubmitted(mockReply, "test-key", tmpFile.name)

    assert failed.callCount == 1
    assert "No transcript ID" in failed.callArgs[0][0]
    assert not os.path.exists(tmpFile.name)
    assert mock_critical.call_count == 1


def test_cleanupRecording_removes_file(personalApp: PersonalAppController):
    """_cleanupRecording deletes the temp file."""
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()
    assert os.path.exists(tmpFile.name)

    personalApp.voice._cleanup(tmpFile.name)
    assert not os.path.exists(tmpFile.name)


def test_cleanupRecording_handles_missing_file(personalApp: PersonalAppController):
    """_cleanupRecording handles gracefully when file doesn't exist."""
    # Should not raise
    personalApp.voice._cleanup("/nonexistent/file.wav")
    personalApp.voice._cleanup("")


def test_importJournalNotes_triggers_cluster_detection(
    test_user, personalApp: PersonalAppController
):
    """Auto-detect clusters after journal import completes (T7-12)."""
    from btcopilot.schema import DiagramData, PDP, PDPDeltas, Event, EventKind
    from unittest.mock import AsyncMock
    from pkdiagram.pyqt import QMessageBox

    initial_diagram_data = DiagramData(pdp=PDP())
    personalApp.setDiagram(Diagram(
        id=test_user.free_diagram_id,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    mock_pdp = PDP(
        people=[Person(id=-1, name="TestPerson")],
        events=[Event(id=-2, kind=EventKind.Shift, description="called")],
    )
    mock_deltas = PDPDeltas(
        people=[Person(id=-1, name="TestPerson")],
        events=[Event(id=-2, kind=EventKind.Shift, description="called")],
        pair_bonds=[],
    )

    with (
        patch(
            "btcopilot.pdp.import_text",
            AsyncMock(return_value=(mock_pdp, mock_deltas)),
        ),
        patch.object(QMessageBox, "information"),
        patch.object(personalApp.clusterModel, "detect") as detect_mock,
    ):
        completed = util.Condition(personalApp.pdpController.journalImportCompleted)
        personalApp.pdpController.importJournalNotes("Some journal text")
        assert completed.wait()
        assert detect_mock.call_count == 1


def test_canExtract_gates_on_dirty_statements(
    test_user, personalApp: PersonalAppController
):
    """Extract button visibility: only when statements exist after the
    re-extraction cursor (FD-319)."""
    from pkdiagram.personal.models import Discussion, Statement, Speaker, SpeakerType

    spk = Speaker(id=1, person_id=1, name="C", type=SpeakerType.Subject)

    def disc(stmt_orders, cursor):
        return Discussion(
            id=1,
            user_id=test_user.id,
            diagram_id=1,
            summary="d",
            speakers=[spk],
            statements=[
                Statement(id=i, text="x", speaker=spk, order=o)
                for i, o in enumerate(stmt_orders)
            ],
            extracted_through_order=cursor,
        )

    personalApp.discussion._currentDiscussion = None
    personalApp.discussion._recomputeDirtyFromModel()
    assert personalApp.discussion.canExtract is False

    # Load: computed from server-fresh model (order vs cursor).
    personalApp.discussion._currentDiscussion = disc([], None)
    personalApp.discussion._recomputeDirtyFromModel()
    assert personalApp.discussion.canExtract is False  # no statements

    personalApp.discussion._currentDiscussion = disc([0, 1], None)
    personalApp.discussion._recomputeDirtyFromModel()
    assert personalApp.discussion.canExtract is True  # never extracted -> dirty

    personalApp.discussion._currentDiscussion = disc([0, 1], 1)
    personalApp.discussion._recomputeDirtyFromModel()
    assert personalApp.discussion.canExtract is False  # all <= cursor

    personalApp.discussion._currentDiscussion = disc([0, 1, 2], 1)
    personalApp.discussion._recomputeDirtyFromModel()
    assert personalApp.discussion.canExtract is True  # order 2 > cursor 1

    # Transitions (no model resync): full accept -> clean unless chat since
    # the extract; a send always makes it dirty again.
    personalApp.discussion._sentSinceExtract = False
    personalApp.discussion._dirty = personalApp.discussion._sentSinceExtract  # full accept onSuccess
    assert personalApp.discussion.canExtract is False
    personalApp.discussion._dirty = True  # send
    personalApp.discussion._sentSinceExtract = True
    assert personalApp.discussion.canExtract is True
    personalApp.discussion._sentSinceExtract = True  # chat happened after extract
    personalApp.discussion._dirty = personalApp.discussion._sentSinceExtract  # full accept onSuccess
    assert personalApp.discussion.canExtract is True  # still dirty


def test_acceptAll_empty_pdp_clears_extract_button(
    test_user, personalApp: PersonalAppController
):
    """J2 end-to-end: re-extracting an already-covered discussion yields an
    empty PDP. 'Accept all' on it must still issue a full-accept commit-pdp
    and, on success, clear the Extract button (canExtract -> False). This is
    the exact failure the user hit repeatedly."""
    from unittest.mock import MagicMock
    from pkdiagram.personal.models import Discussion, Speaker, SpeakerType

    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(DiagramData(pdp=PDP()))),  # empty PDP
    ))
    spk = Speaker(id=1, person_id=1, name="C", type=SpeakerType.Subject)
    personalApp.discussion._currentDiscussion = Discussion(
        id=60, user_id=test_user.id, diagram_id=1, summary="d", speakers=[spk]
    )
    # State after a re-extract that produced nothing, no chat since extract.
    personalApp.discussion._dirty = True
    personalApp.discussion._sentSinceExtract = False
    assert personalApp.discussion.canExtract is True  # button currently shown

    captured = {}

    def fake_nbr(verb, path, **kw):
        captured["verb"] = verb
        captured["path"] = path
        captured["data"] = kw.get("data")
        kw["success"](
            {
                "success": True,
                "full_accept": True,
                "committed": 0,
                "extracted_through_order": 20,
            }
        )
        return MagicMock()

    server = MagicMock()
    server.nonBlockingRequest.side_effect = fake_nbr
    with patch.object(personalApp.session, "server", return_value=server):
        personalApp.pdpController.acceptAllPDPItems()

    assert captured["verb"] == "POST"
    assert captured["path"] == "/personal/discussions/60/commit-pdp"
    assert captured["data"] == {"item_ids": [], "full_accept": True}
    assert personalApp.discussion.canExtract is False  # button cleared


# --- FD-333: committed entity edits and deletes ---

from btcopilot.schema import Event, EventKind


def test_acceptCommittedEdit_applies_and_undoes(
    test_user, personalApp: PersonalAppController
):
    initial_diagram_data = DiagramData(
        people=[{"id": 10, "name": "Alice"}],
        pdp=PDP(people=[Person(id=10, name="Alicia")]),
    )
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    result = personalApp.pdpController.acceptCommittedEdit(10)
    assert result is True
    diagramData = personalApp._diagram.getDiagramData()
    assert diagramData.people[0]["name"] == "Alicia"
    assert diagramData.pdp.people == []
    assert personalApp._undoStack.canUndo()

    personalApp._undoStack.undo()
    diagramData = personalApp._diagram.getDiagramData()
    assert diagramData.people[0]["name"] == "Alice"
    assert len(diagramData.pdp.people) == 1


def test_rejectCommittedEdit_discards_and_undoes(
    test_user, personalApp: PersonalAppController
):
    initial_diagram_data = DiagramData(
        people=[{"id": 10, "name": "Alice"}],
        pdp=PDP(people=[Person(id=10, name="Alicia")]),
    )
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    result = personalApp.pdpController.rejectCommittedEdit(10)
    assert result is True
    diagramData = personalApp._diagram.getDiagramData()
    assert diagramData.people[0]["name"] == "Alice"
    assert diagramData.pdp.people == []
    assert personalApp._undoStack.canUndo()

    personalApp._undoStack.undo()
    diagramData = personalApp._diagram.getDiagramData()
    assert len(diagramData.pdp.people) == 1


def test_acceptCommittedDelete_cascade_and_undoes(
    test_user, personalApp: PersonalAppController
):
    initial_diagram_data = DiagramData(
        people=[{"id": 10, "name": "Alice"}, {"id": 11, "name": "Bob"}],
        events=[
            {
                "id": 20,
                "kind": "shift",
                "person": 10,
                "description": "x",
                "dateTime": "2000-01-01",
            }
        ],
        pair_bonds=[{"id": 30, "person_a": 10, "person_b": 11}],
        pdp=PDP(delete=[10]),
    )
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    result = personalApp.pdpController.acceptCommittedDelete(10)
    assert result is True
    diagramData = personalApp._diagram.getDiagramData()
    assert all(p["id"] != 10 for p in diagramData.people)
    assert diagramData.events == []
    assert diagramData.pair_bonds == []
    assert 10 not in diagramData.pdp.delete
    assert personalApp._undoStack.canUndo()

    personalApp._undoStack.undo()
    diagramData = personalApp._diagram.getDiagramData()
    assert any(p["id"] == 10 for p in diagramData.people)
    assert len(diagramData.pdp.delete) == 1


def test_rejectCommittedDelete_preserves_entity(
    test_user, personalApp: PersonalAppController
):
    initial_diagram_data = DiagramData(
        people=[{"id": 10, "name": "Alice"}],
        pdp=PDP(delete=[10]),
    )
    personalApp.setDiagram(Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    ))

    result = personalApp.pdpController.rejectCommittedDelete(10)
    assert result is True
    diagramData = personalApp._diagram.getDiagramData()
    assert any(p["id"] == 10 for p in diagramData.people)
    assert diagramData.pdp.delete == []
    assert personalApp._undoStack.canUndo()


# --- FD-338: parents-only edit rows are the server-applied channel ---


def test_isParentsEdit_slot(personalApp: PersonalAppController):
    assert personalApp.pdpController.isParentsEdit({"id": 10, "parents": 30}) is True
    assert (
        personalApp.pdpController.isParentsEdit({"id": 10, "name": "Alicia", "parents": 30}) is False
    )
    assert personalApp.pdpController.isParentsEdit({"id": -1, "name": "Mom"}) is False


def _diagram_with_pdp(test_user, pdp):
    return Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(
            asdict(DiagramData(people=[{"id": 10, "name": "Alice"}], pdp=pdp))
        ),
    )


def test_acceptAll_excludes_parents_only_row(
    test_user, personalApp: PersonalAppController
):
    """Parents-only rows are not user-reviewable: not applied client-side, not
    echoed in item_ids, and don't block full_accept. The row stays staged for
    the server to apply on full accept."""
    personalApp.setDiagram(_diagram_with_pdp(
        test_user,
        PDP(people=[Person(id=-1, name="Mom"), Person(id=10, parents=30)]),
    ))
    with (
        patch.object(personalApp.pdpController, "_addCommittedItemsToScene"),
        patch.object(personalApp.clusterModel, "detect"),
        patch.object(personalApp.pdpController, "_postCommitPdp") as post,
    ):
        personalApp.pdpController.acceptAllPDPItems()

    post.assert_called_once_with([-1], True)
    diagramData = personalApp._diagram.getDiagramData()
    assert [p.id for p in diagramData.pdp.people] == [10]
    alice = next(p for p in diagramData.people if p["id"] == 10)
    assert alice.get("parents") is None  # application is the server's job


def test_acceptPDPItem_last_negative_full_accept_with_parents_row_staged(
    test_user, personalApp: PersonalAppController
):
    personalApp.setDiagram(_diagram_with_pdp(
        test_user,
        PDP(people=[Person(id=-1, name="Mom"), Person(id=10, parents=30)]),
    ))
    with (
        patch.object(personalApp.pdpController, "_addCommittedItemsToScene"),
        patch.object(personalApp.pdpController, "_postCommitPdp") as post,
    ):
        personalApp.pdpController._doAcceptPDPItem(-1)

    post.assert_called_once_with([-1], True)


def test_acceptAll_name_edit_row_still_echoed(
    test_user, personalApp: PersonalAppController
):
    """FD-333 Update-card contract unchanged: rows with name/gender are
    applied client-side and echoed in item_ids."""
    personalApp.setDiagram(_diagram_with_pdp(
        test_user, PDP(people=[Person(id=10, name="Alicia")])
    ))
    with (
        patch.object(personalApp.pdpController, "_addCommittedItemsToScene"),
        patch.object(personalApp.clusterModel, "detect"),
        patch.object(personalApp.pdpController, "_postCommitPdp") as post,
    ):
        personalApp.pdpController.acceptAllPDPItems()

    post.assert_called_once_with([10], True)
    diagramData = personalApp._diagram.getDiagramData()
    assert next(p for p in diagramData.people if p["id"] == 10)["name"] == "Alicia"


def test_acceptCommittedEdit_posts_full_accept_when_last_card(
    test_user, personalApp: PersonalAppController
):
    """Per-item review ending on an Update card must still advance the cursor:
    accepting it POSTs commit-pdp with full_accept True."""
    personalApp.setDiagram(_diagram_with_pdp(
        test_user, PDP(people=[Person(id=10, name="Alicia")])
    ))
    with patch.object(personalApp.pdpController, "_postCommitPdp") as post:
        assert personalApp.pdpController.acceptCommittedEdit(10) is True

    post.assert_called_once_with([10], True)


# --- FD-338: rebuildDiagram ---


def _rebuild_diagram(user_id=1):
    return Diagram(
        id=42,
        user_id=user_id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(DiagramData(people=[{"id": 1, "name": "Alice"}]))),
    )


def test_rebuildDiagram_posts_correct_k(qApp):
    controller = PersonalAppController()
    controller.setDiagram(_rebuild_diagram())
    controller.discussion._currentDiscussion = Discussion(id=7, user_id=1, diagram_id=42)
    server = MagicMock()
    server.nonBlockingRequest.return_value = MagicMock()

    with patch.object(controller.session, "server", return_value=server):
        controller.pdpController.rebuildDiagram(8)

    server.nonBlockingRequest.assert_called_once()
    args, kwargs = server.nonBlockingRequest.call_args
    assert args[0] == "POST"
    assert args[1] == "/personal/discussions/7/deep-reextract"
    assert kwargs["data"] == {"k": 8}


def test_rebuildDiagram_posts_k1(qApp):
    controller = PersonalAppController()
    controller.setDiagram(_rebuild_diagram())
    controller.discussion._currentDiscussion = Discussion(id=7, user_id=1, diagram_id=42)
    server = MagicMock()
    server.nonBlockingRequest.return_value = MagicMock()

    with patch.object(controller.session, "server", return_value=server):
        controller.pdpController.rebuildDiagram(1)

    args, kwargs = server.nonBlockingRequest.call_args
    assert kwargs["data"] == {"k": 1}


def test_rebuildDiagram_emits_extractStarted_and_rebuildProgress(qApp):
    controller = PersonalAppController()
    controller.setDiagram(_rebuild_diagram())
    controller.discussion._currentDiscussion = Discussion(id=7, user_id=1, diagram_id=42)
    started = util.Condition(controller.pdpController.extractStarted)
    progress = util.Condition(controller.pdpController.rebuildProgress)

    server = MagicMock()
    server.nonBlockingRequest.return_value = MagicMock()

    with patch.object(controller.session, "server", return_value=server):
        controller.pdpController.rebuildDiagram(8)

    assert started.callCount == 1
    assert progress.callCount >= 1
    assert progress.callArgs[0][0] == 0  # first percent is 0


def test_rebuildDiagram_no_discussion_emits_extractFailed(qApp):
    controller = PersonalAppController()
    controller.discussion._currentDiscussion = None
    failed = util.Condition(controller.pdpController.extractFailed)
    controller.pdpController.rebuildDiagram(8)
    assert failed.callCount == 1


def test_rebuildDiagram_no_diagram_emits_extractFailed(qApp):
    controller = PersonalAppController()
    controller.setDiagram(None)
    controller.discussion._currentDiscussion = Discussion(id=7, user_id=1, diagram_id=42)
    failed = util.Condition(controller.pdpController.extractFailed)
    controller.pdpController.rebuildDiagram(8)
    assert failed.callCount == 1


def _fake_poll_sequence(responses):
    """Return a nonBlockingRequest side_effect that serves responses in order,
    calling success with each dict in turn."""
    call_index = {"i": 0}

    def side_effect(verb, path, success=None, error=None, **kwargs):
        i = call_index["i"]
        call_index["i"] += 1
        if i < len(responses):
            success(responses[i])
        return MagicMock()

    return side_effect


def test_pollRebuild_progress_to_complete_applies_pdp_and_emits_signals(qApp):
    """_pollRebuild: progress→complete applies the PDP and emits pdpChanged+extractCompleted.
    We call _pollRebuild directly to avoid the 1-second QTimer between polls."""
    controller = PersonalAppController()
    controller.setDiagram(_rebuild_diagram())
    controller.discussion._currentDiscussion = Discussion(id=7, user_id=1, diagram_id=42)

    rebuilt_pdp = PDP(people=[Person(id=-1, name="Bob")])
    complete_response = {
        "status": "complete",
        "people_count": 1,
        "events_count": 0,
        "pair_bonds_count": 0,
        "pdp": asdict(rebuilt_pdp),
        "lcc_pct": 100,
        "k": 6,
    }
    progress_response = {
        "status": "progress",
        "current": 3,
        "total": 6,
        "label": "Rebuild 3 of 6",
    }

    pdpChanged = util.Condition(controller.pdpController.pdpChanged)
    completed = util.Condition(controller.pdpController.extractCompleted)
    rebuildProgress = util.Condition(controller.pdpController.rebuildProgress)

    # Two poll calls: first returns progress, second returns complete.
    call_index = {"i": 0}
    responses = [progress_response, complete_response]

    def fake_nbr(verb, path, success=None, error=None, **kwargs):
        i = call_index["i"]
        call_index["i"] += 1
        if i < len(responses):
            success(responses[i])
        return MagicMock()

    server = MagicMock()
    server.nonBlockingRequest.side_effect = fake_nbr

    with (
        patch.object(controller.session, "server", return_value=server),
        patch.object(controller._diagram, "save", return_value=True),
    ):
        # Call _pollRebuild directly; the progress handler schedules a QTimer for
        # the second poll. Run event loop inside the mock context to fire the timer.
        controller.pdpController._pollRebuild(7, "task-abc")
        # First poll fires synchronously: emits rebuildProgress(50, ...) and
        # schedules QTimer(1000) for second poll.
        assert rebuildProgress.callCount >= 1
        progress_args = rebuildProgress.callArgs[0]
        assert progress_args[0] == 50
        assert progress_args[1] == "Rebuild 3 of 6"

        # Wait for the 1-second timer to fire and complete the second poll.
        assert completed.wait(maxMS=2000)
        summary = completed.callArgs[0][0]
        assert summary["people"] == 1
        assert summary["events"] == 0
        assert summary["pairBonds"] == 0

        assert pdpChanged.callCount >= 1


def test_pollRebuild_error_emits_extractFailed(qApp):
    """_pollRebuild: error status emits extractFailed with the error message."""
    controller = PersonalAppController()
    failed = util.Condition(controller.pdpController.extractFailed)

    def fake_nbr(verb, path, success=None, error=None, **kwargs):
        success({"status": "error", "error": "Model overload"})
        return MagicMock()

    server = MagicMock()
    server.nonBlockingRequest.side_effect = fake_nbr

    with patch.object(controller.session, "server", return_value=server):
        controller.pdpController._pollRebuild(7, "task-xyz")

    assert failed.callCount == 1
    assert "Model overload" in failed.callArgs[0][0]


def test_rebuild_watchdog_fails_when_progress_stalls(qApp):
    """A crashed/killed worker never advances progress; the poller must fail
    after REBUILD_STALL_MS instead of spinning on a dead task forever."""
    from pkdiagram.personal.pdpcontroller import REBUILD_STALL_MS

    controller = PersonalAppController()
    base = 1000
    controller.pdpController._rebuildLastProgressMs = base
    failed = util.Condition(controller.pdpController.extractFailed)

    assert controller.pdpController._rebuildStalled(base + REBUILD_STALL_MS - 1) is False
    assert failed.callCount == 0
    assert controller.pdpController._rebuildStalled(base + REBUILD_STALL_MS + 1) is True
    assert failed.callCount == 1
    assert "stopped responding" in failed.callArgs[0][0]


def test_cancelRebuild_stops_polling_posts_cancel_and_emits(qApp):
    """Cancel stops the poll loop, tells the server to abort, and emits
    rebuildCancelled so the overlay dismisses without an error dialog."""
    controller = PersonalAppController()
    controller.setDiagram(_rebuild_diagram())
    controller.discussion._currentDiscussion = Discussion(id=7, user_id=1, diagram_id=42)
    controller.pdpController._rebuildTaskId = "task-abc"
    cancelled = util.Condition(controller.pdpController.rebuildCancelled)
    server = MagicMock()
    server.nonBlockingRequest.return_value = MagicMock()

    with patch.object(controller.session, "server", return_value=server):
        controller.pdpController.cancelRebuild()

    assert controller.pdpController._rebuildCancelled is True
    assert cancelled.callCount == 1
    args, kwargs = server.nonBlockingRequest.call_args
    assert args[0] == "POST"
    assert "/deep-reextract/task-abc/cancel" in args[1]


def test_canRebuild_false_without_discussion(qApp):
    controller = PersonalAppController()
    controller.discussion._currentDiscussion = None
    assert controller.pdpController.canRebuild is False


def test_canRebuild_false_without_people(qApp):
    controller = PersonalAppController()
    controller.setDiagram(Diagram(
        id=42,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(DiagramData())),
    ))
    controller.discussion._currentDiscussion = Discussion(id=7, user_id=1, diagram_id=42)
    assert controller.pdpController.canRebuild is False


def test_canRebuild_true_with_people(qApp):
    controller = PersonalAppController()
    controller.setDiagram(_rebuild_diagram())
    controller.discussion._currentDiscussion = Discussion(id=7, user_id=1, diagram_id=42)
    assert controller.pdpController.canRebuild is True
