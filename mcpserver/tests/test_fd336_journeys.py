"""FD-336 journeys: the real Pro and Personal apps, on the sandbox harness,
driven the way a person drives them — clicks, typing, dialog buttons — and
judged on what the canvas shows and what the server row holds.

Each test names the ticket criterion it is evidence for. Nothing here is
faked: real Qt processes, a real backend on its own database, the deterministic
LLM stand-in in place of a paid model.

    uv run pytest mcpserver/tests/test_fd336_journeys.py -k j1
"""

import contextlib
import pickle
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from btcopilot.testing.fixtures import Case

from mcpserver.mcp_server import (
    BridgeClient,
    LoginState,
    TestInstance,
    close_all_instances,
)
from mcpserver.sandbox import Llm
from mcpserver.tests.test_fd336_harness import _alive, _descendants, _login, _request

from pkdiagram.mcpbridge.inspector import DialogButton
from pkdiagram.personal.propersonal import ProPersonal
from pkdiagram.personal.savegate import SaveGate

pytestmark = pytest.mark.sandbox

TICKET = "FD-336"
FAMILY_PROFILE = "family"
HOSTILE_PROFILE = "family+hostile"
FAMILY_USER = "family@test"
HOSTILE_USER = "hostile@test"

APP_TIMEOUT = 60
HTTP_TIMEOUT = 30
SEED_TIMEOUT = 180
REAP_TIMEOUT = 20
SETTLE_TRIES = 15

FD_FIXTURE = Path(__file__).parent.parent.parent / "pkdiagram" / "tests" / "data" / "stale-refs.fd"

# Two names the coach stand-in will stage: capitalized, mid-sentence, and not
# already on the diagram. (It ignores any word its own prompts use.)
CONNIE, DELPHINE = "Connie", "Delphine"
STATEMENT = f"We saw {CONNIE} and {DELPHINE} at the funeral."
MAIN_WINDOW = "MainWindow"
DIRTY_MARKER = " *"


# ---------------------------------------------------------------------------
# Driving one app
# ---------------------------------------------------------------------------


def _cmd(instance: TestInstance, command: str, **args) -> dict:
    result = instance.bridge.send_command({"command": command, **args})
    assert result.get("success"), f"{command}{args or ''}: {result}"
    return result


def _value(instance: TestInstance, objectName: str, prop: str):
    return _cmd(instance, "get_property", objectName=objectName, property=prop)["value"]


def _exists(instance: TestInstance, objectName: str) -> bool:
    return instance.bridge.send_command(
        {"command": "find_element", "objectName": objectName}
    ).get("success", False)


def _until(condition, what: str, seconds: int = 60):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if condition():
            return
        time.sleep(0.5)
    raise AssertionError(f"timed out after {seconds}s waiting for {what}")


def _type(instance: TestInstance, objectName: str, text: str):
    """Raise the window, click to focus, type, and check it landed. The
    drawer's open animation, the canvas and a dialog that has just closed all
    take focus back, and a lost keystroke would read as a product failure."""
    for _ in range(SETTLE_TRIES):
        instance.bridge.send_command(
            {"command": "activate_window", "objectName": MAIN_WINDOW}
        )
        _cmd(instance, "set_property", objectName=objectName, property="text", value="")
        _cmd(instance, "click", objectName=objectName)
        _cmd(instance, "type_text", objectName=objectName, text=text)
        if _value(instance, objectName, "text") == text:
            return
        time.sleep(0.3)
    raise AssertionError(f"{objectName} would not take the text")


def _title(instance: TestInstance) -> str:
    windows = _cmd(instance, "get_windows")["windows"]
    return next(w["title"] for w in windows if w["className"] == MAIN_WINDOW)


def _people(instance: TestInstance) -> list[str]:
    items = _cmd(instance, "get_scene_items", type="Person")["items"]
    return [item["name"] for item in items]


def _centers(instance: TestInstance) -> dict:
    persons = _cmd(instance, "get_layout_bounds")["persons"]
    return {
        person["name"]: (
            round(person["rect"]["x"] + person["rect"]["w"] / 2),
            round(person["rect"]["y"] + person["rect"]["h"] / 2),
        )
        for person in persons
    }


def _labels(instance: TestInstance) -> dict:
    bounds = _cmd(instance, "get_layout_bounds")
    return {label["parent_id"]: label["text"] for label in bounds["labels"]}


def _openChat(instance: TestInstance, diagram_id: int):
    _cmd(instance, "open_server_diagram", diagramId=diagram_id)
    _cmd(instance, "click", objectName="chatButton")


def _acceptAll(instance: TestInstance):
    _cmd(instance, "open_pdp_sheet")
    _cmd(instance, "click", objectName="acceptAllButton")
    _until(
        lambda: not _cmd(instance, "get_personal_state", component="pdp")["model"][
            "hasPdp"
        ],
        "the staged extraction to drain",
    )


def _staged(instance: TestInstance) -> dict:
    return _cmd(instance, "get_personal_state", component="pdp")["model"]


# ---------------------------------------------------------------------------
# The server it is all judged against
# ---------------------------------------------------------------------------


def _seed(instance: TestInstance, profile: str) -> dict:
    """Seed a profile and return its case manifest — ids come from the seed,
    never hard-coded."""
    response = requests.post(
        f"{instance.manifest['url']}/test/seed",
        json={"profile": profile},
        timeout=SEED_TIMEOUT,
    )
    assert response.status_code == 200, f"seed {profile}: {response.text[:300]}"
    return response.json()["manifest"]


def _row(instance: TestInstance, diagram_id: int) -> dict:
    """The stored blob, as the next client to open the case would read it."""
    response = requests.get(
        f"{instance.manifest['url']}/test/diagrams/{diagram_id}", timeout=HTTP_TIMEOUT
    )
    assert response.status_code == 200, response.text[:300]
    return pickle.loads(response.content)


def _names(row: dict) -> list[str]:
    return [person.get("name") for person in row["people"]]


def _statements(instance: TestInstance, diagram_id: int) -> int:
    """Every statement stored against the case, over the same signed API the
    app uses — the only account of what actually reached the coach."""
    url = instance.manifest["url"]
    user = _login(url, instance.manifest["user"])
    response = _request(user, "GET", url, f"/personal/diagrams/{diagram_id}/discussions")
    assert response.status_code == 200, response.text[:300]
    return sum(len(discussion["statements"]) for discussion in response.json())


# ---------------------------------------------------------------------------
# Instances
# ---------------------------------------------------------------------------


@pytest.fixture
def journey():
    """Apps for one journey, reaped when it ends. A leaked Qt process would
    hold a database and a port for every later run."""
    instances: list[TestInstance] = []

    def launch(user: str = FAMILY_USER, personal: bool = False, server_url: str = None):
        instance = TestInstance.create(ticket=TICKET)
        ok, message = instance.launch(
            headless=True,
            personal=personal,
            ephemeral_server=server_url is None,
            server_url=server_url,
            username=user,
            auto_auth_user=user,
            login_state=LoginState.LoggedIn,
            llm=Llm.Stub.value,
            timeout=APP_TIMEOUT,
        )
        assert ok, f"launch failed: {message}"
        instances.append(instance)
        return instance

    yield launch

    owned = []
    for instance in instances:
        for child in (instance.process, instance.server_process):
            if child and child.poll() is None:
                owned.append(child.pid)
                owned.extend(_descendants(child.pid))
    close_all_instances()
    deadline = time.time() + REAP_TIMEOUT
    while time.time() < deadline and any(_alive(pid) for pid in owned):
        time.sleep(0.5)
    assert not [pid for pid in owned if _alive(pid)], "a journey leaked a process"


# ---------------------------------------------------------------------------
# C6 — the headline: chat beside the canvas ends up on the canvas and the row
# ---------------------------------------------------------------------------


def test_j1_discussion_to_committed_scene_data_on_a_pro_case(journey):
    """C6: a statement, an extraction and an accept on a case Pro has open put
    the people on that canvas and in the stored row, with the document still
    saved — and they are still there when the case is reopened."""
    pro = journey()
    diagram_id = _seed(pro, FAMILY_PROFILE)[Case.FamilyCase.value]["diagram_id"]
    _openChat(pro, diagram_id)
    assert _value(pro, "chatLoader", "active") is True, "the chat slot did not load"

    assert _exists(pro, "discussView"), "no Discuss view in Pro's case drawer"

    _type(pro, "chatTextEdit", STATEMENT)
    _cmd(pro, "click", objectName="chatSendButton")
    _until(
        lambda: _value(pro, "extractButton", "visible"),
        "the coach to answer and offer an extraction",
    )

    _cmd(pro, "click", objectName="extractButton")
    _until(lambda: _staged(pro)["hasPdp"], "the extraction to stage people")
    assert _staged(pro)["personCount"] == 2, _staged(pro)

    _acceptAll(pro)

    centers = _centers(pro)
    assert {CONNIE, DELPHINE} <= set(centers), f"accepted people are not on the canvas: {centers}"

    assert centers[CONNIE] != centers[DELPHINE], f"accepted people stack: {centers}"

    assert (0, 0) not in (centers[CONNIE], centers[DELPHINE]), f"dumped on the origin: {centers}"

    stored = _names(_row(pro, diagram_id))
    assert {CONNIE, DELPHINE} <= set(stored), f"row people: {stored}"

    assert DIRTY_MARKER not in _title(pro), f"document left unsaved: {_title(pro)!r}"

    _cmd(pro, "open_server_diagram", diagramId=diagram_id)
    assert {CONNIE, DELPHINE} <= set(_people(pro)), f"lost on reopen: {_people(pro)}"


# ---------------------------------------------------------------------------
# C3 — offered only where the coach can actually write
# ---------------------------------------------------------------------------


def test_j2_local_file_offers_no_chat(journey):
    """C3: with a local .fd open there is no server case to coach against, so
    the slot says why instead of presenting a chat that cannot save."""
    pro = journey()
    diagram_id = _seed(pro, FAMILY_PROFILE)[Case.FamilyCase.value]["diagram_id"]
    _openChat(pro, diagram_id)
    assert _value(pro, "chatLoader", "active") is True

    local = Path(tempfile.mkdtemp()) / "local.fd"
    shutil.copytree(FD_FIXTURE, local)
    _cmd(pro, "open_file", filePath=str(local))
    _until(
        lambda: _cmd(pro, "get_status")["serverDiagramId"] is None,
        "the local file to open",
    )

    assert _value(pro, "chatLoader", "active") is False

    assert _value(pro, "chatDisabledReason", "text") == ProPersonal.S_NO_SERVER_CASE

    assert not _exists(pro, "discussView"), "a Discuss view on a local file"


def test_j3_shared_cases_offer_no_chat(journey):
    """C3: the coach's routes are owner-only, so a case shared with the user —
    either way rights fall — has to present as disabled rather than 403 on the
    first send. The user's own case is the one that opens."""
    pro = journey(user=HOSTILE_USER)
    cases = _seed(pro, HOSTILE_PROFILE)

    _openChat(pro, cases[Case.SharedReadOnly.value]["diagram_id"])
    assert _value(pro, "chatDisabledReason", "text") == ProPersonal.S_READ_ONLY

    assert _value(pro, "chatLoader", "active") is False

    _cmd(pro, "open_server_diagram", diagramId=cases[Case.SharedReadWrite.value]["diagram_id"])
    assert _value(pro, "chatDisabledReason", "text") == ProPersonal.S_NOT_OWNER

    assert _value(pro, "chatLoader", "active") is False

    _cmd(pro, "open_server_diagram", diagramId=cases[Case.EmptyDiagram.value]["diagram_id"])
    assert _value(pro, "chatDisabledReason", "text") == ""

    assert _value(pro, "chatLoader", "active") is True


# ---------------------------------------------------------------------------
# C8 — unsaved work is saved before the coach reads the row
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _sendWithDialog(instance: TestInstance):
    """Send a statement and hand back the modal it raises. The send blocks the
    main thread inside the dialog, so the dialog is answered over a second
    bridge connection, exactly as a person answers it while the app waits."""
    watcher = BridgeClient(port=instance._bridge_port)
    assert watcher.connect(timeout=10), "second bridge connection refused"
    sent = {}
    worker = threading.Thread(
        target=lambda: sent.update(
            result=instance.bridge.send_command(
                {"command": "click", "objectName": "chatSendButton"}
            )
        ),
        daemon=True,
    )
    worker.start()
    try:
        yield watcher, sent
    finally:
        worker.join(timeout=APP_TIMEOUT)
        watcher.disconnect()


def _modal(client: BridgeClient) -> dict | None:
    windows = client.send_command({"command": "get_windows"}).get("windows", [])
    return next((w for w in windows if w["className"] == "QMessageBox"), None)


def _awaitModal(client: BridgeClient) -> dict:
    deadline = time.time() + 30
    while time.time() < deadline:
        found = _modal(client)
        if found:
            return found
        time.sleep(0.25)
    raise AssertionError("no save prompt appeared on a dirty document")


def test_j4_unsaved_edits_prompt_before_a_statement_is_sent(journey):
    """C8: the coach reads the persisted row, so a statement sent over unsaved
    edits would be answered against facts the row does not have. Declining
    sends nothing; saving sends after the write lands; a saved document is
    never asked."""
    pro = journey()
    diagram_id = _seed(pro, FAMILY_PROFILE)[Case.FamilyCase.value]["diagram_id"]
    _openChat(pro, diagram_id)
    _cmd(pro, "add_person")
    assert DIRTY_MARKER in _title(pro), "adding a person left the document clean"

    people_before = _names(_row(pro, diagram_id))
    statements_before = _statements(pro, diagram_id)

    _type(pro, "chatTextEdit", STATEMENT)
    with _sendWithDialog(pro) as (watcher, sent):
        dialog = _awaitModal(watcher)
        assert dialog["className"] == "QMessageBox"

        watcher.send_command(
            {"command": "dismiss_dialog", "button": DialogButton.Cancel.value}
        )
    assert DIRTY_MARKER in _title(pro), "cancelling still saved"

    assert _names(_row(pro, diagram_id)) == people_before, "cancelling still wrote"

    assert _statements(pro, diagram_id) == statements_before, "cancelling still sent"

    # The declined send still cleared the input (F-008), so it is typed again.
    _type(pro, "chatTextEdit", STATEMENT)
    with _sendWithDialog(pro) as (watcher, sent):
        _awaitModal(watcher)
        answer = watcher.send_command(
            {"command": "dismiss_dialog", "button": DialogButton.Save.value}
        )
        assert answer.get("text") == SaveGate.S_PROMPT, answer
    _until(
        lambda: _value(pro, "extractButton", "visible"),
        "the statement to reach the coach after saving",
    )
    assert DIRTY_MARKER not in _title(pro), "the save did not clean the document"

    assert len(_names(_row(pro, diagram_id))) == len(people_before) + 1, "the added person was not saved"

    assert _statements(pro, diagram_id) > statements_before, "the statement never reached the coach"

    _type(pro, "chatTextEdit", "We talked about the funeral again.")
    started = time.time()
    _cmd(pro, "click", objectName="chatSendButton")
    assert time.time() - started < 5, "a saved document was asked to save again"

    assert _modal(pro.bridge) is None, "a saved document raised the save prompt"


# ---------------------------------------------------------------------------
# C7 — one writer, both apps
# ---------------------------------------------------------------------------


def test_j5_both_apps_write_the_same_case_through_one_saver(journey):
    """C7: Personal's accept and Pro's save are the same write path against the
    same row, so what one app commits the other opens, and a save that follows
    a fresh open never has to merge."""
    pro = journey()
    diagram_id = _seed(pro, FAMILY_PROFILE)[Case.FamilyCase.value]["diagram_id"]
    personal = journey(personal=True, server_url=pro.manifest["url"])

    _cmd(personal, "open_server_diagram", diagramId=diagram_id)
    _cmd(
        personal,
        "inject_pdp_data",
        data={"people": [{"id": -1, "name": CONNIE}], "events": [], "pair_bonds": []},
    )
    _acceptAll(personal)
    assert CONNIE in _names(_row(pro, diagram_id)), "Personal's accept never reached the row"

    _cmd(pro, "open_server_diagram", diagramId=diagram_id)
    assert CONNIE in _people(pro), f"Pro cannot see Personal's person: {_people(pro)}"

    _cmd(pro, "add_person")
    saved = _cmd(pro, "save_diagram")
    assert saved["conflicts"] == 0, f"a save after a fresh open had to merge: {saved}"


# ---------------------------------------------------------------------------
# C10a/b — a committed person is legible on the canvas
# ---------------------------------------------------------------------------


def test_j6_committed_people_carry_a_visible_label(journey):
    """C10a/b: a person the coach commits has to be readable on the diagram —
    including one the conversation only ever gave a last name."""
    pro = journey()
    diagram_id = _seed(pro, FAMILY_PROFILE)[Case.FamilyCase.value]["diagram_id"]
    _openChat(pro, diagram_id)
    _cmd(
        pro,
        "inject_pdp_data",
        data={
            "people": [
                {"id": -1, "last_name": "Okonkwo"},
                {"id": -2, "name": "Ruth", "last_name": "Bader"},
            ],
            "events": [],
            "pair_bonds": [],
        },
    )
    _acceptAll(pro)

    labels = set(_labels(pro).values())
    assert "Okonkwo" in labels, f"last-name-only person has no label: {labels}"

    assert "Ruth Bader" in labels, f"last name dropped at commit: {labels}"
