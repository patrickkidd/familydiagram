"""
Multi-instance concurrent-save harness test.

Scenario (Journey-1A shape):
  1. Pro and Personal both open the same diagram (same ephemeral server, same user).
  2. Pro adds a person and saves first.
  3. Personal (with a stale local version) saves second.
  4. Personal's save must trigger a 409 → applyChange merge fires.

This test validates HARNESS capabilities only:
  - Two instances (Pro + Personal) can connect to a shared ephemeral server.
  - Bridge save commands are synchronous and correctly ordered.
  - The 409 conflict path is exercised (conflicts > 0 on Personal's save).

Step 5 (re-open + verify merged scene) is intentionally omitted: it requires
app-level fixes (applyChange 3-way merge, headless QMessageBox suppression)
that are out of scope for this branch. See doc/plans/2026-05-01--harness-multi-instance.md.

Run:
    uv run pytest mcpserver/tests/test_concurrent_save.py -v

Launches two real apps against one sandbox backend; excluded from the default
run by pytest.ini's testpaths, so it only runs when named. See doc/SANDBOX.md.
"""

import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcpserver.mcp_server import LoginState, TestInstance

pytestmark = pytest.mark.sandbox


USER_EMAIL = "harness@example.com"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def pro_instance():
    """Pro on its own sandbox backend — the default, no server_url anywhere."""
    instance = TestInstance.create()
    ok, msg = instance.launch(
        headless=True,
        personal=False,
        auto_auth_user=USER_EMAIL,
        login_state=LoginState.LoggedIn,
        username=USER_EMAIL,
        timeout=45,
    )
    assert ok, f"Pro launch failed: {msg}"
    assert instance.manifest["checkouts"]["familydiagram"]["path"] == str(
        instance.project_root
    )
    yield instance
    instance.close(force=True)


@pytest.fixture(scope="function")
def shared_diagram_id(pro_instance):
    """Return free_diagram_id for USER_EMAIL, looking it up via the idempotent seed endpoint."""
    resp = requests.post(
        f"{pro_instance.manifest['url']}/test/seed",
        json={"users": [{"username": USER_EMAIL, "status": "confirmed"}]},
        timeout=10,
    )
    assert resp.status_code == 200, f"Seed lookup failed: {resp.text}"
    seed_data = resp.json()
    assert seed_data["users"], "No user returned from seed"
    free_diagram_id = seed_data["users"][0].get("free_diagram_id")
    assert free_diagram_id, "User has no free_diagram_id"
    return free_diagram_id


@pytest.fixture(scope="function")
def personal_instance(pro_instance):
    """Personal sharing Pro's backend — the only way two apps get one database."""
    instance = TestInstance.create()
    ok, msg = instance.launch(
        headless=True,
        personal=True,
        ephemeral_server=False,
        server_url=pro_instance.manifest["url"],
        login_state=LoginState.LoggedIn,
        username=USER_EMAIL,
        timeout=45,
    )
    assert ok, f"Personal launch failed: {msg}"
    yield instance
    instance.close(force=True)


def test_no_backend_is_an_error_not_a_default():
    instance = TestInstance.create()
    with pytest.raises(ValueError, match="never targets a server it did not start"):
        instance.launch(ephemeral_server=False)
    instance.close(force=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _send(instance: TestInstance, command: dict) -> dict:
    assert instance.bridge and instance.bridge.is_connected, "Bridge not connected"
    return instance.bridge.send_command(command)


def _open_diagram(instance: TestInstance, diagram_id: int) -> None:
    resp = _send(instance, {"command": "open_server_diagram", "diagramId": diagram_id})
    assert resp.get("success"), f"open_server_diagram failed: {resp}"


def _save(instance: TestInstance) -> dict:
    resp = _send(instance, {"command": "save_diagram"})
    assert resp.get("success"), f"save_diagram failed: {resp}"
    return resp


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_concurrent_save_triggers_409(
    pro_instance, personal_instance, shared_diagram_id
):
    """
    Harness test: Pro saves first (V→V+1); Personal (stale V) saves second and gets a 409.

    Asserts harness-observable facts only:
      - Both instances open the same diagram successfully.
      - Pro's save completes with no conflict.
      - Personal's save detects at least one version conflict (409 path fired).
    """
    diagram_id = shared_diagram_id

    # 1. Both apps open the same diagram.
    _open_diagram(pro_instance, diagram_id)
    _open_diagram(personal_instance, diagram_id)

    # 2. Pro adds a person so there is something to save.
    add_resp = _send(pro_instance, {"command": "add_person"})
    assert add_resp.get("success"), f"add_person failed: {add_resp}"

    # 3. Pro saves — version V → V+1. Bridge blocks until save completes.
    pro_save = _save(pro_instance)
    assert pro_save["conflicts"] == 0, "Pro save should not conflict (saves first)"

    # 4. Personal saves with stale version V → server returns 409 → applyChange fires.
    personal_save = _save(personal_instance)
    assert personal_save["conflicts"] >= 1, (
        "Personal's save must detect a version conflict (409). "
        "conflicts == 0 means ordering was not enforced or Pro's save did not advance the version."
    )
