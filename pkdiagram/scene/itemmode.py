import enum

from pkdiagram.scene import RelationshipKind


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

    def toRelationship(self) -> RelationshipKind:
        """Check if this mode creates an emotion."""
        map = {
            self.Projection: RelationshipKind.Projection,
            self.Conflict: RelationshipKind.Conflict,
            self.Cutoff: RelationshipKind.Cutoff,
            self.Distance: RelationshipKind.Distance,
            self.Toward: RelationshipKind.Toward,
            self.Away: RelationshipKind.Away,
            self.DefinedSelf: RelationshipKind.DefinedSelf,
            self.Reciprocity: RelationshipKind.Underfunctioning,
            self.Inside: RelationshipKind.Inside,
            self.Outside: RelationshipKind.Outside,
        }
        return map.get(self)

    def isPerson(self) -> bool:
        """Check if this mode creates a person."""
        return self in [self.Male, self.Female]

    def isOffSpring(self) -> bool:
        """Check if this mode creates a marriage or child relationship."""
        return self in [self.Marry, self.Child]
