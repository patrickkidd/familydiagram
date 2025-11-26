"""
Test compatibility migration logic for legacy file formats.

IMPORTANT: All tests in this file should use DECLARATIVE style, not imperative.
- Declarative: Define expected data structure, compare with actual
- Imperative: Make assertions about individual fields step-by-step

Example of declarative style (GOOD):
    expected = {"people": [...], "events": [...]}
    compat.update_data(data)
    assert data == expected

Example of imperative style (BAD):
    compat.update_data(data)
    assert len(data["people"]) == 3
    assert data["people"][0]["name"] == "Alice"
"""

import json
import os.path
import pickle

import pytest

from btcopilot.schema import EventKind, RelationshipKind
from pkdiagram import util
from pkdiagram.models import compat
from pkdiagram.pyqt import QPointF

from . import data


@pytest.fixture
def version_dict():
    def _version_dict(version):
        base_dir = os.path.dirname(data.__file__)
        file_path = os.path.join(
            base_dir,
            f"UP_TO_{version}{util.DOT_EXTENSION}",
            "diagram.pickle",
        )
        return pickle.load(open(file_path, "rb"))

    return _version_dict


def test_up_to_2_0_12b1(version_dict):
    data = version_dict("2.0.12b1")
    compat.update_data(data)
    # Basic smoke test - just ensure it doesn't crash


def test_phase_6_2_extract_person_builtin_events():
    data = {
        "version": "2.0.11",
        "lastItemId": 10,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Alice",
                "birthEvent": {
                    "id": 2,
                    "uniqueId": "birth",
                    "dateTime": "2000-01-01T00:00:00",
                },
                "adoptedEvent": {
                    "id": 3,
                    "uniqueId": "adopted",
                    "dateTime": "2005-06-15T00:00:00",
                },
                "deathEvent": {
                    "id": 4,
                    "uniqueId": "death",
                    "dateTime": "2080-01-01T00:00:00",
                },
                "events": [],
            }
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 13,
        "people": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Alice",
                "parents": 13,
            },
            {
                "kind": "Person",
                "id": 11,
                "gender": util.PERSON_KIND_MALE,
                "size": 4,
                "itemPos": QPointF(-160.0, -240.0),
                "layers": [],
            },
            {
                "kind": "Person",
                "id": 12,
                "gender": util.PERSON_KIND_FEMALE,
                "size": 4,
                "itemPos": QPointF(160.0, -240.0),
                "layers": [],
            },
        ],
        "pair_bonds": [
            {
                "kind": "Marriage",
                "id": 13,
                "person_a": 11,
                "person_b": 12,
            }
        ],
        "emotions": [],
        "events": [
            {
                "id": 2,
                "kind": EventKind.Birth.value,
                "dateTime": "2000-01-01T00:00:00",
                "child": 1,
                "person": 11,
                "spouse": 12,
            },
            {
                "id": 3,
                "kind": EventKind.Adopted.value,
                "dateTime": "2005-06-15T00:00:00",
                "child": 1,
                "person": 11,
                "spouse": 12,
            },
            {
                "id": 4,
                "kind": EventKind.Death.value,
                "dateTime": "2080-01-01T00:00:00",
                "person": 1,
            },
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_phase_6_1_split_items_into_separate_arrays():
    data = {
        "version": "2.0.11",
        "lastItemId": 7,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Alice",
                "events": [
                    {"kind": "Event", "id": 4},
                ],
            },
            {
                "kind": "Marriage",
                "id": 2,
                "person_a": 1,
                "person_b": 3,
                "events": [
                    {"kind": "Event", "id": 8},
                ],
            },
            {"kind": "Conflict", "id": 3},
            {"kind": "Layer", "id": 5, "name": "Layer 1"},
            {"kind": "Callout", "id": 6},
            {"kind": "MultipleBirth", "id": 7},
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 7,
        "people": [{"kind": "Person", "id": 1, "name": "Alice"}],
        "pair_bonds": [
            {"kind": "Marriage", "id": 2, "person_a": 1, "person_b": 3},
        ],
        "emotions": [{"kind": RelationshipKind.Conflict.value, "id": 3}],
        "events": [
            {"id": 4, "kind": "Event", "person": 1},
            {
                "id": 8,
                "kind": "Event",
                "person": 1,
                "spouse": 3,
            },
        ],
        "layers": [{"kind": "Layer", "id": 5, "name": "Layer 1"}],
        "layerItems": [{"kind": "Callout", "id": 6}],
        "multipleBirths": [{"kind": "MultipleBirth", "id": 7}],
    }

    compat.update_data(data)
    assert data == expected


def test_phase_6_2_extract_person_custom_events():
    data = {
        "version": "2.0.11",
        "lastItemId": 10,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Alice",
                "events": [
                    {
                        "id": 5,
                        "uniqueId": "CustomIndividual",
                        "dateTime": "2020-05-01T00:00:00",
                    }
                ],
            }
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 10,
        "people": [{"kind": "Person", "id": 1, "name": "Alice"}],
        "pair_bonds": [],
        "emotions": [],
        "events": [
            {
                "id": 5,
                "kind": EventKind.Shift.value,
                "dateTime": "2020-05-01T00:00:00",
                "person": 1,
            }
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_phase_6_2_extract_marriage_events():
    data = {
        "version": "2.0.11",
        "lastItemId": 20,
        "items": [
            {
                "kind": "Marriage",
                "id": 10,
                "person_a": 1,
                "person_b": 2,
                "events": [
                    {"id": 15, "uniqueId": "bonded", "dateTime": "2015-06-01T00:00:00"},
                    {
                        "id": 16,
                        "uniqueId": "married",
                        "dateTime": "2016-06-01T00:00:00",
                    },
                    {
                        "id": 17,
                        "uniqueId": "moved",
                        "dateTime": "2018-03-15T00:00:00",
                        "location": "NYC",
                    },
                    {
                        "id": 18,
                        "uniqueId": "separated",
                        "dateTime": "2019-09-01T00:00:00",
                    },
                    {
                        "id": 19,
                        "uniqueId": "divorced",
                        "dateTime": "2020-06-01T00:00:00",
                    },
                ],
            }
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 20,
        "people": [],
        "pair_bonds": [{"kind": "Marriage", "id": 10, "person_a": 1, "person_b": 2}],
        "emotions": [],
        "events": [
            {
                "id": 15,
                "kind": EventKind.Bonded.value,
                "dateTime": "2015-06-01T00:00:00",
                "person": 1,
                "spouse": 2,
            },
            {
                "id": 16,
                "kind": EventKind.Married.value,
                "dateTime": "2016-06-01T00:00:00",
                "person": 1,
                "spouse": 2,
            },
            {
                "id": 17,
                "kind": EventKind.Moved.value,
                "dateTime": "2018-03-15T00:00:00",
                "location": "NYC",
                "person": 1,
                "spouse": 2,
            },
            {
                "id": 18,
                "kind": EventKind.Separated.value,
                "dateTime": "2019-09-01T00:00:00",
                "person": 1,
                "spouse": 2,
            },
            {
                "id": 19,
                "kind": EventKind.Divorced.value,
                "dateTime": "2020-06-01T00:00:00",
                "person": 1,
                "spouse": 2,
            },
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_phase_6_2_extract_emotion_events_with_date_range():
    data = {
        "version": "2.0.11",
        "lastItemId": 30,
        "items": [
            {
                "kind": "Conflict",
                "id": 20,
                "person_a": 1,
                "person_b": 2,
                "intensity": 7,
                "notes": "Test conflict",
                "isDateRange": True,
                "startEvent": {
                    "id": 25,
                    "uniqueId": "emotionStartEvent",
                    "dateTime": "2020-01-01T00:00:00",
                },
                "endEvent": {
                    "id": 26,
                    "uniqueId": "emotionEndEvent",
                    "dateTime": "2020-12-31T00:00:00",
                },
            }
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 30,
        "people": [],
        "pair_bonds": [],
        "emotions": [
            {
                "kind": RelationshipKind.Conflict.value,
                "id": 20,
                "event": 25,
                "target": 2,
            }
        ],
        "events": [
            {
                "id": 25,
                "kind": EventKind.Shift.value,
                "dateTime": "2020-01-01T00:00:00",
                "endDateTime": "2020-12-31T00:00:00",
                "person": 1,
                "relationshipTargets": [2],
                "relationshipIntensity": 7,
                "dynamicProperties": {
                    "relationship": RelationshipKind.Conflict.value,
                },
                "notes": "Test conflict",
            }
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_phase_6_2_extract_emotion_events_singular_date():
    data = {
        "version": "2.0.11",
        "lastItemId": 30,
        "items": [
            {
                "kind": "Distance",
                "id": 20,
                "person_a": 1,
                "person_b": 2,
                "intensity": 3,
                "startEvent": {
                    "id": 25,
                    "uniqueId": "emotionStartEvent",
                    "dateTime": "2020-01-01T00:00:00",
                },
            }
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 30,
        "people": [],
        "pair_bonds": [],
        "emotions": [
            {
                "kind": RelationshipKind.Distance.value,
                "id": 20,
                "event": 25,
                "target": 2,
            }
        ],
        "events": [
            {
                "id": 25,
                "kind": EventKind.Shift.value,
                "dateTime": "2020-01-01T00:00:00",
                "person": 1,
                "relationshipTargets": [2],
                "relationshipIntensity": 3,
                "dynamicProperties": {
                    "relationship": RelationshipKind.Distance.value,
                },
            }
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_phase_6_2_migrate_uniqueid_to_kind():
    data = {
        "version": "2.0.11",
        "lastItemId": 20,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Alice",
                "childOf": {"person": 1, "parents": 10, "multipleBirth": None},
                "events": [
                    {"id": 3, "uniqueId": "death"},
                    {"id": 16, "uniqueId": "birth"},
                    {"id": 17, "uniqueId": "adopted"},
                    {"id": 9, "uniqueId": "CustomIndividual"},
                    {"id": 11, "uniqueId": ""},
                    {"id": 12, "uniqueId": None},
                    {"id": 13},
                ],
            },
            {"kind": "Person", "id": 4, "name": "Parent1"},
            {"kind": "Person", "id": 5, "name": "Parent2"},
            {
                "kind": "Marriage",
                "id": 10,
                "person_a": 4,
                "person_b": 5,
                "events": [
                    {"id": 6, "uniqueId": "married"},
                    {"id": 7, "uniqueId": "bonded"},
                    {"id": 14, "uniqueId": "separated"},
                    {"id": 15, "uniqueId": "divorced"},
                    {"id": 8, "uniqueId": "moved"},
                    {"id": 18, "uniqueId": "emotionStartEvent"},
                    {"id": 19, "uniqueId": ""},
                    {"id": 20, "uniqueId": None},
                ],
            },
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 20,
        "people": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Alice",
                "parents": 10,
            },
            {"kind": "Person", "id": 4, "name": "Parent1"},
            {"kind": "Person", "id": 5, "name": "Parent2"},
        ],
        "pair_bonds": [{"kind": "Marriage", "id": 10, "person_a": 4, "person_b": 5}],
        "emotions": [],
        "events": [
            {"id": 3, "kind": EventKind.Death.value, "person": 1},
            {
                "id": 16,
                "kind": EventKind.Birth.value,
                "child": 1,
                "person": 4,
                "spouse": 5,
            },
            {
                "id": 17,
                "kind": EventKind.Adopted.value,
                "child": 1,
                "person": 4,
                "spouse": 5,
            },
            {"id": 9, "kind": EventKind.Shift.value, "person": 1},
            {"id": 11, "kind": EventKind.Shift.value, "person": 1},
            {"id": 12, "kind": EventKind.Shift.value, "person": 1},
            {"id": 13, "kind": EventKind.Shift.value, "person": 1},
            {"id": 6, "kind": EventKind.Married.value, "person": 4, "spouse": 5},
            {"id": 7, "kind": EventKind.Bonded.value, "person": 4, "spouse": 5},
            {"id": 14, "kind": EventKind.Separated.value, "person": 4, "spouse": 5},
            {"id": 15, "kind": EventKind.Divorced.value, "person": 4, "spouse": 5},
            {"id": 8, "kind": EventKind.Moved.value, "person": 4, "spouse": 5},
            {"id": 18, "kind": EventKind.Shift.value, "person": 4, "spouse": 5},
            {"id": 19, "kind": EventKind.Shift.value, "person": 4, "spouse": 5},
            {"id": 20, "kind": EventKind.Shift.value, "person": 4, "spouse": 5},
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_phase_6_2_assign_event_ids():
    data = {
        "version": "2.0.11",
        "lastItemId": 5,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "birthEvent": {"uniqueId": "birth", "dateTime": "2000-01-01T00:00:00"},
                "events": [{"uniqueId": "moved", "dateTime": "2020-01-01T00:00:00"}],
            }
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 10,
        "people": [
            {
                "kind": "Person",
                "id": 1,
                "parents": 9,
            },
            {
                "kind": "Person",
                "id": 7,
                "gender": util.PERSON_KIND_MALE,
                "size": 4,
                "itemPos": QPointF(-160.0, -240.0),
                "layers": [],
            },
            {
                "kind": "Person",
                "id": 8,
                "gender": util.PERSON_KIND_FEMALE,
                "size": 4,
                "itemPos": QPointF(160.0, -240.0),
                "layers": [],
            },
        ],
        "pair_bonds": [
            {
                "kind": "Marriage",
                "id": 9,
                "person_a": 7,
                "person_b": 8,
            }
        ],
        "emotions": [],
        "events": [
            {
                "id": 6,
                "kind": EventKind.Birth.value,
                "dateTime": "2000-01-01T00:00:00",
                "child": 1,
                "person": 7,
                "spouse": 8,
            },
            {
                "id": 10,
                "kind": EventKind.Moved.value,
                "dateTime": "2020-01-01T00:00:00",
                "person": 1,
            },
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_phase_6_unknown_item_types_preserved():
    data = {
        "version": "2.0.11",
        "lastItemId": 3,
        "items": [
            {"kind": "Person", "id": 1},
            {"kind": "UnknownFutureType", "id": 2},
            {"kind": "AnotherUnknown", "id": 3},
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 3,
        "people": [{"kind": "Person", "id": 1}],
        "pair_bonds": [],
        "emotions": [],
        "events": [],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
        "items": [
            {"kind": "UnknownFutureType", "id": 2},
            {"kind": "AnotherUnknown", "id": 3},
        ],
    }

    compat.update_data(data)
    assert data == expected


def test_phase_6_empty_arrays_handling():
    data = {
        "version": "2.0.11",
        "lastItemId": 5,
        "items": [
            {"kind": "Person", "id": 1, "events": []},
            {"kind": "Marriage", "id": 2, "person_a": 1, "person_b": 3, "events": []},
            {"kind": "Conflict", "id": 3},
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 5,
        "people": [{"kind": "Person", "id": 1}],
        "pair_bonds": [{"kind": "Marriage", "id": 2, "person_a": 1, "person_b": 3}],
        "emotions": [{"kind": RelationshipKind.Conflict.value, "id": 3}],
        "events": [],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_birth_event_with_existing_parents():
    """Test birth event migration when child has existing parents via childOf."""
    data = {
        "version": "2.0.11",
        "lastItemId": 5,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Alice",
                "size": 3,
                "birthEvent": {
                    "id": 4,
                    "uniqueId": "birth",
                    "dateTime": "2000-01-01T00:00:00",
                },
                "childOf": {
                    "person": 1,
                    "parents": 5,
                    "multipleBirth": None,
                },
            },
            {"kind": "Person", "id": 2, "name": "Parent1"},
            {"kind": "Person", "id": 3, "name": "Parent2"},
            {"kind": "Marriage", "id": 5, "person_a": 2, "person_b": 3},
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 5,
        "people": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Alice",
                "size": 3,
                "parents": 5,
            },
            {"kind": "Person", "id": 2, "name": "Parent1"},
            {"kind": "Person", "id": 3, "name": "Parent2"},
        ],
        "pair_bonds": [{"kind": "Marriage", "id": 5, "person_a": 2, "person_b": 3}],
        "emotions": [],
        "events": [
            {
                "id": 4,
                "kind": EventKind.Birth.value,
                "dateTime": "2000-01-01T00:00:00",
                "child": 1,
                "person": 2,  # Parent1
                "spouse": 3,  # Parent2
            }
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_birth_event_without_parents_creates_inferred():
    """Test birth event migration when child has no parents - creates inferred parents."""
    data = {
        "version": "2.0.11",
        "lastItemId": 2,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Orphan",
                "size": 3,
                "itemPos": {"x": 100, "y": 100},
                "birthEvent": {
                    "id": 2,
                    "uniqueId": "birth",
                    "dateTime": "2000-01-01T00:00:00",
                },
            }
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 5,
        "people": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Orphan",
                "size": 3,
                "itemPos": {"x": 100, "y": 100},
                "parents": 5,
            },
            {
                "kind": "Person",
                "id": 3,
                "gender": util.PERSON_KIND_MALE,
                "size": 2,
                "itemPos": QPointF(68.0, 52.0),
                "layers": [],
            },
            {
                "kind": "Person",
                "id": 4,
                "gender": util.PERSON_KIND_FEMALE,
                "size": 2,
                "itemPos": QPointF(132.0, 52.0),
                "layers": [],
            },
        ],
        "pair_bonds": [
            {
                "kind": "Marriage",
                "id": 5,
                "person_a": 3,
                "person_b": 4,
            }
        ],
        "emotions": [],
        "events": [
            {
                "id": 2,
                "kind": EventKind.Birth.value,
                "dateTime": "2000-01-01T00:00:00",
                "child": 1,
                "person": 3,
                "spouse": 4,
            }
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_adopted_event_with_existing_parents():
    """Test adopted event migration when child has existing parents."""
    data = {
        "version": "2.0.11",
        "lastItemId": 5,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Bob",
                "adoptedEvent": {
                    "id": 4,
                    "uniqueId": "adopted",
                    "dateTime": "2005-06-15T00:00:00",
                },
                "childOf": {
                    "person": 1,
                    "parents": 5,
                    "multipleBirth": None,
                },
            },
            {"kind": "Person", "id": 2, "name": "AdoptiveParent1"},
            {"kind": "Person", "id": 3, "name": "AdoptiveParent2"},
            {"kind": "Marriage", "id": 5, "person_a": 2, "person_b": 3},
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 5,
        "people": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Bob",
                "parents": 5,
            },
            {"kind": "Person", "id": 2, "name": "AdoptiveParent1"},
            {"kind": "Person", "id": 3, "name": "AdoptiveParent2"},
        ],
        "pair_bonds": [{"kind": "Marriage", "id": 5, "person_a": 2, "person_b": 3}],
        "emotions": [],
        "events": [
            {
                "id": 4,
                "kind": EventKind.Adopted.value,
                "dateTime": "2005-06-15T00:00:00",
                "child": 1,
                "person": 2,
                "spouse": 3,
            }
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_death_event_only_sets_person():
    """Test death event migration only sets person reference, not spouse/child."""
    data = {
        "version": "2.0.11",
        "lastItemId": 2,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Charlie",
                "deathEvent": {
                    "id": 2,
                    "uniqueId": "death",
                    "dateTime": "2080-01-01T00:00:00",
                },
            }
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 2,
        "people": [{"kind": "Person", "id": 1, "name": "Charlie"}],
        "pair_bonds": [],
        "emotions": [],
        "events": [
            {
                "id": 2,
                "kind": EventKind.Death.value,
                "dateTime": "2080-01-01T00:00:00",
                "person": 1,
            }
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_birth_event_in_custom_events_without_parents():
    """Test birth event in Person.events array without parents creates inferred parents."""
    data = {
        "version": "2.0.11",
        "lastItemId": 5,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Child",
                "size": 2,
                "events": [
                    {
                        "id": 5,
                        "uniqueId": "birth",
                        "dateTime": "1990-01-01T00:00:00",
                    }
                ],
            }
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 8,
        "people": [
            {
                "kind": "Person",
                "id": 1,
                "name": "Child",
                "size": 2,
                "parents": 8,
            },
            {
                "kind": "Person",
                "id": 6,
                "gender": util.PERSON_KIND_MALE,
                "size": 1,
                "itemPos": QPointF(-12.8, -19.2),
                "layers": [],
            },
            {
                "kind": "Person",
                "id": 7,
                "gender": util.PERSON_KIND_FEMALE,
                "size": 1,
                "itemPos": QPointF(12.8, -19.2),
                "layers": [],
            },
        ],
        "pair_bonds": [
            {
                "kind": "Marriage",
                "id": 8,
                "person_a": 6,
                "person_b": 7,
            }
        ],
        "emotions": [],
        "events": [
            {
                "id": 5,
                "kind": EventKind.Birth.value,
                "dateTime": "1990-01-01T00:00:00",
                "child": 1,
                "person": 6,
                "spouse": 7,
            }
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected


def test_inferred_parent_size_minimum():
    """Test inferred parent size doesn't go below 1."""
    data = {
        "version": "2.0.11",
        "lastItemId": 2,
        "items": [
            {
                "kind": "Person",
                "id": 1,
                "name": "TinyChild",
                "size": 1,
                "birthEvent": {
                    "id": 2,
                    "uniqueId": "birth",
                    "dateTime": "2000-01-01T00:00:00",
                },
            }
        ],
    }

    expected = {
        "version": "2.0.11",
        "lastItemId": 5,
        "people": [
            {
                "kind": "Person",
                "id": 1,
                "name": "TinyChild",
                "size": 1,
                "parents": 5,
            },
            {
                "kind": "Person",
                "id": 3,
                "gender": util.PERSON_KIND_MALE,
                "size": 1,  # max(1 - 1, 1) = 1
                "itemPos": QPointF(-12.8, -19.2),
                "layers": [],
            },
            {
                "kind": "Person",
                "id": 4,
                "gender": util.PERSON_KIND_FEMALE,
                "size": 1,  # max(1 - 1, 1) = 1
                "itemPos": QPointF(12.8, -19.2),
                "layers": [],
            },
        ],
        "pair_bonds": [
            {
                "kind": "Marriage",
                "id": 5,
                "person_a": 3,
                "person_b": 4,
            }
        ],
        "emotions": [],
        "events": [
            {
                "id": 2,
                "kind": EventKind.Birth.value,
                "dateTime": "2000-01-01T00:00:00",
                "child": 1,
                "person": 3,
                "spouse": 4,
            }
        ],
        "layerItems": [],
        "layers": [],
        "multipleBirths": [],
    }

    compat.update_data(data)
    assert data == expected
