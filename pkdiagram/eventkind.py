import enum


class EventKind(enum.Enum):

    # Person
    Birth = "birth"
    Adopted = "adopted"
    Death = "death"

    # Pair-Bond
    Bonded = "bonded"
    Married = "married"
    Separated = "separated"
    Divorced = "divorced"

    # Emotion
    Conflict = "conflict"
    Distance = "distance"
    Projection = "projection"
    Reciprocity = "reciprocity"
    DefinedSelf = "defined_self"
    Toward = "toward"
    Away = "away"
    Inside = "inside"
    Outside = "outside"
    Cutoff = "cutoff"

    # Custom
    Custom = "custom"

    @classmethod
    def isMonadic(cls, x) -> bool:
        return x in (cls.Birth, cls.Adopted, cls.Death, cls.Cutoff, cls.Custom)

    @classmethod
    def isPairBond(cls, x) -> bool:
        return x in (cls.Bonded, cls.Married, cls.Separated, cls.Divorced)

    @classmethod
    def isEmotion(cls, x) -> bool:
        return x in (
            cls.Cutoff,
            cls.Conflict,
            cls.Distance,
            cls.Projection,
            cls.Reciprocity,
            cls.DefinedSelf,
            cls.Toward,
            cls.Away,
            cls.Inside,
            cls.Outside,
        )

    @classmethod
    def isDyadic(cls, x) -> bool:
        """
        Requires a mover and receiver
        """
        return cls.isPairBond(x) or x in [
            cls.Conflict,
            cls.Distance,
            cls.Projection,
            cls.Reciprocity,
            cls.DefinedSelf,
            cls.Toward,
            cls.Away,
            cls.Inside,
            cls.Outside,
        ]

    @classmethod
    def menuLabelFor(cls, x) -> str:
        if cls.isMonadic(x):
            return f"Individual - {x.name}"
        elif cls.isDyadic(x):
            return f"Dyad - {x.name}"
        elif cls.isPairBond(x):
            return f"Pair Bond - {x.name}"
        elif x == EventKind.Custom:
            return f"Custom"
        else:
            raise KeyError(f"Unknown event kind: {x}")

    @classmethod
    def menuLabels(cls) -> list[str]:
        return [EventKind.menuLabelFor(EventKind(x)) for x in cls.menuValues()]

    @classmethod
    def menuValues(cls) -> list[str]:
        return [
            cls.Birth.value,
            cls.Adopted.value,
            cls.Death.value,
            cls.Cutoff.value,
            cls.Bonded.value,
            cls.Married.value,
            cls.Separated.value,
            cls.Divorced.value,
            cls.Conflict.value,
            cls.Distance.value,
            cls.Projection.value,
            cls.Reciprocity.value,
            cls.DefinedSelf.value,
            cls.Toward.value,
            cls.Away.value,
            cls.Inside.value,
            cls.Outside.value,
            cls.Custom.value,
        ]

    @classmethod
    def personALabel(cls, kind) -> str:
        if cls.isEmotion(kind):
            return "Mover(s)"
        elif cls.isPairBond(kind):
            return "Person A"
        else:
            return "People"

    @classmethod
    def personBLabel(cls, kind) -> str:
        if cls.isEmotion(kind):
            return "Receiver(s)"
        elif cls.isPairBond(kind):
            return "Person B"
        else:
            return "People"
