"""FD-336 / C10: an accepted person must carry the name the extraction gave it.

Two ingresses have to agree. C10a is the stored row reopened — including rows
the pre-FD-336 writer left with a last name under the schema's snake_case key,
which the Scene never read and so rendered blank. C10b is the live accept,
which puts the same people into the open Scene without a round trip. Same
three people, same three labels, or a person changes name by being reopened.
"""

import pytest

from btcopilot.schema import Person as SchemaPerson, committed_person_chunk

from pkdiagram.models.diagramsaver import DiagramSaver
from pkdiagram.personal.pdpcontroller import PDPController
from pkdiagram.app import Session
from pkdiagram.scene import Scene


pytestmark = [pytest.mark.component("Scene")]


PDP_PEOPLE = [
    SchemaPerson(id=101, name="Connie"),
    SchemaPerson(id=102, name="Connie", last_name="Stinson"),
    SchemaPerson(id=103, last_name="Stinson"),
]

LABELS = ["Connie", "Connie Stinson", "Stinson"]

# The version the previous release wrote, so the migration is gated on rows
# older than this build rather than on a long-past release.
OLD_WRITER_VERSION = "2.1.22"


def _labels(scene: Scene) -> list:
    return [p.fullNameOrAlias() for p in sorted(scene.people(), key=lambda p: p.id)]


def test_stored_people_label_on_reopen(scene):
    """C10a: the first two rows are what the current writer emits; the third is
    what the old writer left behind. All three must label after the migration,
    and the last-name-only person must not come back as 'Stinson Stinson'."""
    data = {
        "version": OLD_WRITER_VERSION,
        "people": [
            {"id": 101, "name": "Connie"},
            {"id": 102, "name": "Connie", "lastName": "Stinson"},
            {"id": 103, "name": None, "last_name": "Stinson"},
        ],
    }

    scene.read(data)
    assert _labels(scene) == LABELS


def test_accepted_people_label_in_the_open_scene(scene):
    """C10b: accept writes Scene keys straight into the open Scene, so a label
    that only appears after a reopen is a defect, not a refresh."""
    session = Session()
    controller = PDPController(session, DiagramSaver(session, lambda id: None))
    controller.setScene(scene)

    controller._addCommittedItemsToScene(
        {
            "people": [committed_person_chunk(p) for p in PDP_PEOPLE],
            "events": [],
            "pair_bonds": [],
            "emotions": [],
        }
    )
    assert _labels(scene) == LABELS
