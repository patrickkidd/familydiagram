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
from btcopilot.schema import DiagramData, PDP, Person, asdict

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
    assert set(x.id for x in personalApp.discussions) == {discussion.id}


@pytest.mark.parametrize("success", [True, False])
def test_sendStatement(
    server_error, test_user, discussion, personalApp: PersonalAppController, success
):

    from btcopilot.personal.chat import Response

    RESPONSE = Response(statement="some response")

    requestSent = util.Condition(personalApp.requestSent)
    responseReceived = util.Condition(personalApp.responseReceived)
    serverError = util.Condition(personalApp.serverError)
    serverDown = util.Condition(personalApp.serverDown)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("btcopilot.personal.routes.discussions.ask", return_value=RESPONSE)
        )
        stack.enter_context(
            patch.object(
                personalApp,
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
        personalApp.sendStatement("test message")
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
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with patch.object(personalApp, "_doAcceptPDPItem") as accept:
        personalApp.acceptPDPItem(-1)
        assert accept.call_count == 1
        assert personalApp._undoStack.count() == 1
        assert personalApp._undoStack.canUndo()

        personalApp._undoStack.undo()
        expected = asdict(initial_diagram_data.pdp)
        expected["committedPeople"] = []
        assert personalApp.pdp == expected
        assert not personalApp._undoStack.canUndo()
        assert personalApp._undoStack.canRedo()

        personalApp._undoStack.redo()
        assert accept.call_count == 2
        assert not personalApp._undoStack.canRedo()


def test_rejectPDPItem_undo(test_user, personalApp: PersonalAppController):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with patch.object(personalApp, "_doRejectPDPItem") as reject:
        personalApp.rejectPDPItem(-1)
        assert reject.call_count == 1
        assert personalApp._undoStack.count() == 1
        assert personalApp._undoStack.canUndo()

        personalApp._undoStack.undo()
        expected = asdict(initial_diagram_data.pdp)
        expected["committedPeople"] = []
        assert personalApp.pdp == expected
        assert not personalApp._undoStack.canUndo()
        assert personalApp._undoStack.canRedo()

        personalApp._undoStack.redo()
        assert reject.call_count == 2
        assert not personalApp._undoStack.canRedo()


def test_undo_stack_multiple_operations(test_user, personalApp: PersonalAppController):
    diagram_data1 = DiagramData(pdp=PDP(people=[Person(id=-1, name="Person1")]))
    diagram_data2 = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="Person1"), Person(id=-2, name="Person2")])
    )

    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(diagram_data1)),
    )

    with (
        patch.object(personalApp, "_doAcceptPDPItem"),
        patch.object(personalApp, "_doRejectPDPItem"),
    ):
        personalApp.acceptPDPItem(-1)
        personalApp._diagram.setDiagramData(diagram_data2)
        personalApp.rejectPDPItem(-2)

        assert personalApp._undoStack.count() == 2

        personalApp._undoStack.undo()
        expected2 = asdict(diagram_data2.pdp)
        expected2["committedPeople"] = []
        assert personalApp.pdp == expected2

        personalApp._undoStack.undo()
        expected1 = asdict(diagram_data1.pdp)
        expected1["committedPeople"] = []
        assert personalApp.pdp == expected1


def test_acceptPDPItem_failure_doesnt_push_to_stack(
    test_user, personalApp: PersonalAppController
):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    count_before = personalApp._undoStack.count()

    with patch.object(personalApp, "_doAcceptPDPItem", return_value=False):
        result = personalApp.acceptPDPItem(-1)

    assert result is False
    assert personalApp._undoStack.count() == count_before


def test_rejectPDPItem_failure_doesnt_push_to_stack(
    test_user, personalApp: PersonalAppController
):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    count_before = personalApp._undoStack.count()

    with patch.object(personalApp, "_doRejectPDPItem", return_value=False):
        result = personalApp.rejectPDPItem(-1)

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
    personalApp._diagram = Diagram(
        id=test_user.free_diagram_id,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

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
        completed = util.Condition(personalApp.journalImportCompleted)
        personalApp.importJournalNotes("Some journal text")
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

    personalApp._diagram = None

    failed = util.Condition(personalApp.journalImportFailed)

    with patch.object(QMessageBox, "critical"):
        personalApp.importJournalNotes("Some journal text")
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
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with patch.object(personalApp, "_addCommittedItemsToScene") as add_mock:
        with patch.object(personalApp._diagram, "save", return_value=True):
            personalApp.acceptAllPDPItems()
            assert add_mock.call_count == 1
            args = add_mock.call_args[0][0]
            assert "people" in args
            assert "events" in args
            assert "pair_bonds" in args


def test_acceptPDPItem_posts_commit_pdp_partial(
    test_user, discussion, personalApp: PersonalAppController
):
    """Accepting one of several staged items POSTs commit-pdp with that id and
    full_accept False (cursor must not advance)."""
    initial = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="A"), Person(id=-2, name="B")])
    )
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial)),
    )
    personalApp._currentDiscussion = discussion
    server = MagicMock()
    with (
        patch.object(personalApp, "_addCommittedItemsToScene"),
        patch.object(personalApp._diagram, "save", return_value=True),
        patch.object(personalApp.session, "server", return_value=server),
    ):
        personalApp._doAcceptPDPItem(-1)

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
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial)),
    )
    personalApp._currentDiscussion = discussion
    server = MagicMock()
    with (
        patch.object(personalApp, "_addCommittedItemsToScene"),
        patch.object(personalApp._diagram, "save", return_value=True),
        patch.object(personalApp.session, "server", return_value=server),
    ):
        personalApp.acceptAllPDPItems()

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
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with (
        patch.object(personalApp, "_doAcceptPDPItem", return_value=True),
        patch.object(personalApp.clusterModel, "detect") as detect_mock,
    ):
        personalApp.acceptPDPItem(-1)
        assert detect_mock.call_count == 1


def test_acceptPDPItem_failure_skips_cluster_detection(
    test_user, personalApp: PersonalAppController
):
    """No cluster detection when PDP accept fails (T7-12)."""
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with (
        patch.object(personalApp, "_doAcceptPDPItem", return_value=False),
        patch.object(personalApp.clusterModel, "detect") as detect_mock,
    ):
        personalApp.acceptPDPItem(-1)
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
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with (
        patch.object(personalApp, "_addCommittedItemsToScene"),
        patch.object(personalApp._diagram, "save", return_value=True),
        patch.object(personalApp.clusterModel, "detect") as detect_mock,
    ):
        personalApp.acceptAllPDPItems()
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
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    batchCalls = []
    origSetBatch = scene.setBatchAddingRemovingItems

    def trackBatch(on):
        batchCalls.append(on)
        origSetBatch(on)

    with (
        patch.object(personalApp._diagram, "save", return_value=True),
        patch.object(scene, "setBatchAddingRemovingItems", side_effect=trackBatch),
    ):
        personalApp.clearDiagramData(True)

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
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )
    personalApp.scene = None

    saveCall = {"called": False, "applyChange": None}

    def fakeSave(server, applyChange, stillValid, **kwargs):
        saveCall["called"] = True
        saveCall["applyChange"] = applyChange
        return True

    with patch.object(personalApp._diagram, "save", side_effect=fakeSave):
        personalApp.clearDiagramData(True)

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
    personalApp._ensureAudioRecorder()
    with (
        patch.object(personalApp._audioRecorder, "setEncodingSettings"),
        patch.object(personalApp._audioRecorder, "setOutputLocation"),
        patch.object(personalApp._audioRecorder, "record") as mock_record,
    ):
        personalApp.startRecording()

    assert mock_record.call_count == 1
    assert personalApp._recordingFilePath.endswith(".wav")
    assert "fd_voice_" in personalApp._recordingFilePath
    # Cleanup the temp file created
    if os.path.exists(personalApp._recordingFilePath):
        os.unlink(personalApp._recordingFilePath)


def test_startRecording_emits_recordingFailed_on_error(
    personalApp: PersonalAppController,
):
    """startRecording emits recordingFailed if an exception occurs."""
    from pkdiagram.pyqt import QMessageBox

    failed = util.Condition(personalApp.recordingFailed)

    # DiscussView.qml's onRecordingFailed handler calls util.criticalBox
    # which pops a modal QMessageBox. Patch it so emit doesn't deadlock.
    with (
        patch(
            "pkdiagram.personal.personalappcontroller.tempfile.NamedTemporaryFile",
            side_effect=OSError("disk full"),
        ),
        patch.object(QMessageBox, "critical") as mock_critical,
    ):
        personalApp.startRecording()

    assert failed.callCount == 1
    assert "disk full" in failed.callArgs[0][0]
    assert mock_critical.call_count == 1


def test_stopRecording_stops_recorder_and_transcribes(
    personalApp: PersonalAppController,
):
    """stopRecording stops the recorder and begins transcription."""
    personalApp._ensureAudioRecorder()
    # Create a real temp file so the path exists check passes
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()
    personalApp._recordingFilePath = tmpFile.name

    with (
        patch.object(personalApp._audioRecorder, "stop") as mock_stop,
        patch.object(personalApp, "_transcribeAudio") as mock_transcribe,
    ):
        personalApp.stopRecording()

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
    personalApp._ensureAudioRecorder()
    from pkdiagram.pyqt import QMessageBox

    failed = util.Condition(personalApp.transcriptionFailed)
    personalApp._recordingFilePath = "/nonexistent/path.wav"

    with (
        patch.object(personalApp._audioRecorder, "stop"),
        patch.object(QMessageBox, "critical") as mock_critical,
    ):
        personalApp.stopRecording()

    assert failed.callCount == 1
    assert "not found" in failed.callArgs[0][0]
    assert mock_critical.call_count == 1


def test_stopRecording_emits_failed_when_empty_path(
    personalApp: PersonalAppController,
):
    """stopRecording emits transcriptionFailed if _recordingFilePath is empty."""
    personalApp._ensureAudioRecorder()
    from pkdiagram.pyqt import QMessageBox

    failed = util.Condition(personalApp.transcriptionFailed)
    personalApp._recordingFilePath = ""

    with (
        patch.object(personalApp._audioRecorder, "stop"),
        patch.object(QMessageBox, "critical") as mock_critical,
    ):
        personalApp.stopRecording()

    assert failed.callCount == 1
    assert mock_critical.call_count == 1


def test_cancelRecording_stops_and_cleans_up(
    personalApp: PersonalAppController,
):
    """cancelRecording stops the recorder, cleans up temp file, resets path."""
    personalApp._ensureAudioRecorder()
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()
    personalApp._recordingFilePath = tmpFile.name

    with patch.object(personalApp._audioRecorder, "stop") as mock_stop:
        personalApp.cancelRecording()

    assert mock_stop.call_count == 1
    assert personalApp._recordingFilePath == ""
    assert not os.path.exists(tmpFile.name), "Temp file should be deleted on cancel"


def test_cancelRecording_does_not_transcribe(
    personalApp: PersonalAppController,
):
    """cancelRecording should NOT trigger transcription."""
    personalApp._ensureAudioRecorder()
    import tempfile as _tempfile

    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()
    personalApp._recordingFilePath = tmpFile.name

    with (
        patch.object(personalApp._audioRecorder, "stop"),
        patch.object(personalApp, "_transcribeAudio") as mock_transcribe,
    ):
        personalApp.cancelRecording()

    assert mock_transcribe.call_count == 0

    # Cleanup if still present
    if os.path.exists(tmpFile.name):
        os.unlink(tmpFile.name)


def test_voice_state_idle_to_recording_to_transcribing_to_idle(
    personalApp: PersonalAppController,
):
    """Full voice state machine: idle → startRecording → stopRecording → transcriptionReady → idle."""
    personalApp._ensureAudioRecorder()
    import tempfile as _tempfile

    # Start in idle state
    assert personalApp._recordingFilePath == ""

    # Transition to recording
    tmpFile = _tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, prefix="fd_voice_"
    )
    tmpFile.close()

    with (
        patch.object(personalApp._audioRecorder, "setEncodingSettings"),
        patch.object(personalApp._audioRecorder, "setOutputLocation"),
        patch.object(personalApp._audioRecorder, "record"),
    ):
        personalApp.startRecording()

    assert personalApp._recordingFilePath != ""  # Now recording

    # Transition to transcribing → idle (mock the transcription pipeline)
    with (
        patch.object(personalApp._audioRecorder, "stop"),
        patch.object(personalApp, "_transcribeAudio") as mock_transcribe,
    ):
        personalApp.stopRecording()
        assert mock_transcribe.call_count == 1

    # Cleanup
    if os.path.exists(personalApp._recordingFilePath):
        os.unlink(personalApp._recordingFilePath)


def test_short_tap_cancel_does_not_transcribe(
    personalApp: PersonalAppController,
):
    """Simulates short tap behavior: startRecording then immediate cancelRecording (no transcription)."""
    personalApp._ensureAudioRecorder()
    import tempfile as _tempfile

    with (
        patch.object(personalApp._audioRecorder, "setEncodingSettings"),
        patch.object(personalApp._audioRecorder, "setOutputLocation"),
        patch.object(personalApp._audioRecorder, "record"),
    ):
        personalApp.startRecording()

    filePath = personalApp._recordingFilePath
    assert filePath != ""

    with (
        patch.object(personalApp._audioRecorder, "stop"),
        patch.object(personalApp, "_transcribeAudio") as mock_transcribe,
    ):
        personalApp.cancelRecording()

    assert mock_transcribe.call_count == 0
    assert personalApp._recordingFilePath == ""
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

    failed = util.Condition(personalApp.transcriptionFailed)

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
        personalApp._transcribeAudio(tmpFile.name)

    assert failed.callCount == 1
    assert "AssemblyAI" in failed.callArgs[0][0]
    assert not os.path.exists(tmpFile.name), "Should cleanup on failure"
    assert mock_critical.call_count == 1


def test_transcribeAudio_emits_failed_on_file_read_error(
    personalApp: PersonalAppController,
):
    """_transcribeAudio emits transcriptionFailed if audio file can't be read."""
    from pkdiagram.pyqt import QMessageBox

    failed = util.Condition(personalApp.transcriptionFailed)

    with (
        patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": "test-key"}, clear=False),
        patch.object(QMessageBox, "critical") as mock_critical,
    ):
        personalApp._transcribeAudio("/nonexistent/audio.wav")

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

    failed = util.Condition(personalApp.transcriptionFailed)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.ConnectionRefusedError
    mockReply.errorString.return_value = "Connection refused"
    mockReply.deleteLater = MagicMock()

    with patch.object(QMessageBox, "critical") as mock_critical:
        personalApp._onUploadFinished(mockReply, "test-key", tmpFile.name)

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

    failed = util.Condition(personalApp.transcriptionFailed)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.NoError
    mockReply.readAll.return_value = QByteArray(json.dumps({}).encode())
    mockReply.deleteLater = MagicMock()

    with patch.object(QMessageBox, "critical") as mock_critical:
        personalApp._onUploadFinished(mockReply, "test-key", tmpFile.name)

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

    ready = util.Condition(personalApp.transcriptionReady)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.NoError
    mockReply.readAll.return_value = QByteArray(
        json.dumps({"status": "completed", "text": "Hello world"}).encode()
    )
    mockReply.deleteLater = MagicMock()

    personalApp._onPollFinished(mockReply, "txn-123", "test-key", tmpFile.name)

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

    failed = util.Condition(personalApp.transcriptionFailed)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.NoError
    mockReply.readAll.return_value = QByteArray(
        json.dumps({"status": "error", "error": "Audio too short"}).encode()
    )
    mockReply.deleteLater = MagicMock()

    with patch.object(QMessageBox, "critical") as mock_critical:
        personalApp._onPollFinished(mockReply, "txn-123", "test-key", tmpFile.name)

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
        personalApp._onPollFinished(mockReply, "txn-123", "test-key", "/tmp/test.wav")

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

    failed = util.Condition(personalApp.transcriptionFailed)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.ConnectionRefusedError
    mockReply.errorString.return_value = "Connection refused"
    mockReply.deleteLater = MagicMock()

    with patch.object(QMessageBox, "critical") as mock_critical:
        personalApp._onTranscriptSubmitted(mockReply, "test-key", tmpFile.name)

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

    failed = util.Condition(personalApp.transcriptionFailed)

    mockReply = MagicMock()
    mockReply.error.return_value = QNetworkReply.NoError
    mockReply.readAll.return_value = QByteArray(json.dumps({}).encode())
    mockReply.deleteLater = MagicMock()

    with patch.object(QMessageBox, "critical") as mock_critical:
        personalApp._onTranscriptSubmitted(mockReply, "test-key", tmpFile.name)

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

    personalApp._cleanupRecording(tmpFile.name)
    assert not os.path.exists(tmpFile.name)


def test_cleanupRecording_handles_missing_file(personalApp: PersonalAppController):
    """_cleanupRecording handles gracefully when file doesn't exist."""
    # Should not raise
    personalApp._cleanupRecording("/nonexistent/file.wav")
    personalApp._cleanupRecording("")


def test_importJournalNotes_triggers_cluster_detection(
    test_user, personalApp: PersonalAppController
):
    """Auto-detect clusters after journal import completes (T7-12)."""
    from btcopilot.schema import DiagramData, PDP, PDPDeltas, Event, EventKind
    from unittest.mock import AsyncMock
    from pkdiagram.pyqt import QMessageBox

    initial_diagram_data = DiagramData(pdp=PDP())
    personalApp._diagram = Diagram(
        id=test_user.free_diagram_id,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

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
        completed = util.Condition(personalApp.journalImportCompleted)
        personalApp.importJournalNotes("Some journal text")
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

    personalApp._currentDiscussion = None
    personalApp._recomputeDirtyFromModel()
    assert personalApp.canExtract is False

    # Load: computed from server-fresh model (order vs cursor).
    personalApp._currentDiscussion = disc([], None)
    personalApp._recomputeDirtyFromModel()
    assert personalApp.canExtract is False  # no statements

    personalApp._currentDiscussion = disc([0, 1], None)
    personalApp._recomputeDirtyFromModel()
    assert personalApp.canExtract is True  # never extracted -> dirty

    personalApp._currentDiscussion = disc([0, 1], 1)
    personalApp._recomputeDirtyFromModel()
    assert personalApp.canExtract is False  # all <= cursor

    personalApp._currentDiscussion = disc([0, 1, 2], 1)
    personalApp._recomputeDirtyFromModel()
    assert personalApp.canExtract is True  # order 2 > cursor 1

    # Transitions (no model resync): full accept -> clean unless chat since
    # the extract; a send always makes it dirty again.
    personalApp._sentSinceExtract = False
    personalApp._dirty = personalApp._sentSinceExtract  # full accept onSuccess
    assert personalApp.canExtract is False
    personalApp._dirty = True  # send
    personalApp._sentSinceExtract = True
    assert personalApp.canExtract is True
    personalApp._sentSinceExtract = True  # chat happened after extract
    personalApp._dirty = personalApp._sentSinceExtract  # full accept onSuccess
    assert personalApp.canExtract is True  # still dirty


def test_acceptAll_empty_pdp_clears_extract_button(
    test_user, personalApp: PersonalAppController
):
    """J2 end-to-end: re-extracting an already-covered discussion yields an
    empty PDP. 'Accept all' on it must still issue a full-accept commit-pdp
    and, on success, clear the Extract button (canExtract -> False). This is
    the exact failure the user hit repeatedly."""
    from unittest.mock import MagicMock
    from pkdiagram.personal.models import Discussion, Speaker, SpeakerType

    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(DiagramData(pdp=PDP()))),  # empty PDP
    )
    spk = Speaker(id=1, person_id=1, name="C", type=SpeakerType.Subject)
    personalApp._currentDiscussion = Discussion(
        id=60, user_id=test_user.id, diagram_id=1, summary="d", speakers=[spk]
    )
    # State after a re-extract that produced nothing, no chat since extract.
    personalApp._dirty = True
    personalApp._sentSinceExtract = False
    assert personalApp.canExtract is True  # button currently shown

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
        personalApp.acceptAllPDPItems()

    assert captured["verb"] == "POST"
    assert captured["path"] == "/personal/discussions/60/commit-pdp"
    assert captured["data"] == {"item_ids": [], "full_accept": True}
    assert personalApp.canExtract is False  # button cleared
