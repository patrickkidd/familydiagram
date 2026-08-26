"""Seeding decisions the launcher makes before any server is involved.

These cover the paths a flag cannot reach from outside: the guard that fires
only if a backend licences the wrong account, and the routing that decides
which endpoint a seed file goes to.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcpserver.sandbox import Sandbox

UUID = "THIS-MACHINE-UUID"
SPEC = {"users": [{"username": "spec@test"}], "diagrams": []}
EXPORT = {"user": {"id": 7, "username": "exported@test"}, "diagram": {"id": 1924}}


@pytest.fixture
def sandbox():
    return Sandbox(ticket="FD-336", hardware_uuid=UUID)


def record(sandbox) -> list:
    """Capture what would have been posted instead of posting it."""
    calls = []

    def post(route, **kwargs):
        calls.append((route, kwargs["json"]))
        return {"hardware_uuid": UUID, "primary_user": "whoever@test", "users": []}

    sandbox.post = post
    return calls


def test_a_backend_that_licenses_another_account_fails_the_launch(sandbox):
    sandbox.post = lambda route, **kwargs: {"hardware_uuid": f"{UUID}:someone@test"}
    with pytest.raises(RuntimeError, match="would open unlicensed"):
        sandbox._seed("/test/seed", {"profile": "family"})


def test_the_licence_check_passes_when_the_codes_agree(sandbox):
    sandbox.post = lambda route, **kwargs: {"hardware_uuid": UUID}
    assert sandbox._seed("/test/seed", {"profile": "family"})["hardware_uuid"] == UUID


def test_the_hardware_uuid_rides_on_every_seed(sandbox):
    calls = record(sandbox)
    sandbox.seed = "family"
    sandbox._apply_seed()
    assert calls[0][1]["hardware_uuid"] == UUID


def test_a_profile_names_the_login_account_it_must_licence(sandbox):
    calls = record(sandbox)
    sandbox.seed = "family+hostile"
    sandbox.auto_auth_user = "me@test"
    sandbox._apply_seed()
    assert calls == [
        (
            "/test/seed",
            {
                "profile": "family+hostile",
                "primary_user": "me@test",
                "hardware_uuid": UUID,
            },
        )
    ]


def test_a_seed_spec_file_is_seeded_and_an_export_is_imported(sandbox, tmp_path):
    for body, route in ((SPEC, "/test/seed"), (EXPORT, "/test/import")):
        path = tmp_path / f"{route.strip('/').replace('/', '_')}.json"
        path.write_text(json.dumps(body))
        calls = record(sandbox)
        sandbox.seed = str(path)
        sandbox._apply_seed()
        assert calls[0][0] == route


def test_with_no_seed_the_login_account_is_the_only_thing_seeded(sandbox):
    calls = record(sandbox)
    sandbox.auto_auth_user = "solo@test"
    sandbox._apply_seed()
    assert calls[0][1]["users"] == [{"username": "solo@test"}]


def test_nothing_is_seeded_when_nothing_was_asked_for(sandbox):
    calls = record(sandbox)
    assert sandbox._apply_seed() is None
    assert calls == []
