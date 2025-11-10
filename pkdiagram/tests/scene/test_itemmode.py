import pytest

from btcopilot.schema import RelationshipKind
from pkdiagram.scene import ItemMode


def test_toRelationshipKind_all_emotions():
    assert ItemMode.Fusion.toRelationshipKind() == RelationshipKind.Fusion
    assert ItemMode.Conflict.toRelationshipKind() == RelationshipKind.Conflict
    assert ItemMode.Cutoff.toRelationshipKind() == RelationshipKind.Cutoff
    assert ItemMode.Distance.toRelationshipKind() == RelationshipKind.Distance
    assert ItemMode.Projection.toRelationshipKind() == RelationshipKind.Projection
    assert (
        ItemMode.Reciprocity.toRelationshipKind() == RelationshipKind.Underfunctioning
    )
    assert ItemMode.DefinedSelf.toRelationshipKind() == RelationshipKind.DefinedSelf
    assert ItemMode.Toward.toRelationshipKind() == RelationshipKind.Toward
    assert ItemMode.Away.toRelationshipKind() == RelationshipKind.Away
    assert ItemMode.Inside.toRelationshipKind() == RelationshipKind.Inside
    assert ItemMode.Outside.toRelationshipKind() == RelationshipKind.Outside


def test_toRelationshipKind_non_emotions():
    assert ItemMode.Male.toRelationshipKind() is None
    assert ItemMode.Female.toRelationshipKind() is None
    assert ItemMode.Marry.toRelationshipKind() is None
    assert ItemMode.Child.toRelationshipKind() is None
    assert ItemMode.Pencil.toRelationshipKind() is None
    assert ItemMode.Eraser.toRelationshipKind() is None
    assert ItemMode.Callout.toRelationshipKind() is None


def test_fromRelationshipKind_all_emotions():
    assert ItemMode.fromRelationshipKind(RelationshipKind.Fusion) == ItemMode.Fusion
    assert ItemMode.fromRelationshipKind(RelationshipKind.Conflict) == ItemMode.Conflict
    assert ItemMode.fromRelationshipKind(RelationshipKind.Cutoff) == ItemMode.Cutoff
    assert ItemMode.fromRelationshipKind(RelationshipKind.Distance) == ItemMode.Distance
    assert (
        ItemMode.fromRelationshipKind(RelationshipKind.Projection)
        == ItemMode.Projection
    )
    assert (
        ItemMode.fromRelationshipKind(RelationshipKind.Underfunctioning)
        == ItemMode.Reciprocity
    )
    assert (
        ItemMode.fromRelationshipKind(RelationshipKind.Overfunctioning)
        == ItemMode.Reciprocity
    )
    assert (
        ItemMode.fromRelationshipKind(RelationshipKind.DefinedSelf)
        == ItemMode.DefinedSelf
    )
    assert ItemMode.fromRelationshipKind(RelationshipKind.Toward) == ItemMode.Toward
    assert ItemMode.fromRelationshipKind(RelationshipKind.Away) == ItemMode.Away
    assert ItemMode.fromRelationshipKind(RelationshipKind.Inside) == ItemMode.Inside
    assert ItemMode.fromRelationshipKind(RelationshipKind.Outside) == ItemMode.Outside


def test_roundtrip_conversions():
    emotion_modes = [
        ItemMode.Fusion,
        ItemMode.Conflict,
        ItemMode.Cutoff,
        ItemMode.Distance,
        ItemMode.Projection,
        ItemMode.Reciprocity,
        ItemMode.DefinedSelf,
        ItemMode.Toward,
        ItemMode.Away,
        ItemMode.Inside,
        ItemMode.Outside,
    ]

    for mode in emotion_modes:
        kind = mode.toRelationshipKind()
        assert kind is not None
        assert ItemMode.fromRelationshipKind(kind) in [mode, ItemMode.Reciprocity]
