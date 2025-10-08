import enum


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

    def isRelationship(self) -> bool:
        """Check if this mode creates an emotion."""
        return self in [
            self.Projection,
            self.Conflict,
            self.Cutoff,
            self.Distance,
            self.Toward,
            self.Away,
            self.DefinedSelf,
            self.Reciprocity,
            self.Inside,
            self.Outside,
        ]

    def isPerson(self) -> bool:
        """Check if this mode creates a person."""
        return self in [self.Male, self.Female]

    def isOffSpring(self) -> bool:
        """Check if this mode creates a marriage or child relationship."""
        return self in [self.Marry, self.Child]
