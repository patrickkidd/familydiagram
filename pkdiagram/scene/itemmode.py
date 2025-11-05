import enum

from btcopilot.schema import RelationshipKind


class ItemMode(enum.Enum):
    """Drawing modes for creating items on the diagram."""

    # People
    Male = "male"
    Female = "female"

    # Relationships
    Marry = "marry"
    Child = "child"

    # Emotions (relationships)
    Fusion = "fusion"
    Cutoff = "cutoff"
    Conflict = "conflict"
    Projection = "projection"
    Distance = "distance"
    Toward = "toward"
    Away = "away"
    DefinedSelf = "defined-self"
    Reciprocity = "reciprocity"
    Inside = "inside"
    Outside = "outside"

    # UI Tools
    Pencil = "pencil"
    Eraser = "eraser"
    Callout = "callout"

    def isPerson(self) -> bool:
        """Check if this mode creates a person."""
        return self in [self.Male, self.Female]

    def isOffSpring(self) -> bool:
        """Check if this mode creates a marriage or child relationship."""
        return self in [self.Marry, self.Child]

    @staticmethod
    def fromRelationshipKind(kind: RelationshipKind) -> "ItemMode | None":
        """Get the ItemMode for a RelationshipKind, if any."""
        if kind == RelationshipKind.Fusion:
            return ItemMode.Fusion
        elif kind == RelationshipKind.Cutoff:
            return ItemMode.Cutoff
        elif kind == RelationshipKind.Conflict:
            return ItemMode.Conflict
        elif kind == RelationshipKind.Distance:
            return ItemMode.Distance
        elif kind in (
            RelationshipKind.Underfunctioning,
            RelationshipKind.Overfunctioning,
        ):
            return ItemMode.Reciprocity
        elif kind == RelationshipKind.Projection:
            return ItemMode.Projection
        elif kind == RelationshipKind.Toward:
            return ItemMode.Toward
        elif kind == RelationshipKind.Away:
            return ItemMode.Away
        elif kind == RelationshipKind.Inside:
            return ItemMode.Inside
        elif kind == RelationshipKind.Outside:
            return ItemMode.Outside
        elif kind == RelationshipKind.DefinedSelf:
            return ItemMode.DefinedSelf
        else:
            raise KeyError(f"No ITEM_MODE for: {kind}")

    def toRelationshipKind(self) -> RelationshipKind | None:
        """Get the RelationshipKind for this ItemMode, if any."""
        mapping = {
            ItemMode.Fusion: RelationshipKind.Fusion,
            ItemMode.Conflict: RelationshipKind.Conflict,
            ItemMode.Distance: RelationshipKind.Distance,
            ItemMode.Reciprocity: RelationshipKind.Underfunctioning,
            ItemMode.Projection: RelationshipKind.Projection,
            ItemMode.DefinedSelf: RelationshipKind.DefinedSelf,
            ItemMode.Toward: RelationshipKind.Toward,
            ItemMode.Away: RelationshipKind.Away,
            ItemMode.Inside: RelationshipKind.Inside,
            ItemMode.Outside: RelationshipKind.Outside,
            ItemMode.Cutoff: RelationshipKind.Cutoff,
        }
        return mapping.get(self)
