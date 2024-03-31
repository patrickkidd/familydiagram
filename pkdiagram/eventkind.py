import enum


class EventKind(enum.Enum):
    """
    Canonical Event uniqueId values. An Event has a uniqueId if it has a
    specific visual representation somewhere in the app, usually the diagram.
    """

    # Indibvidual
    Birth = "birth"
    Adopted = "adopted"
    Death = "death"

    CustomIndividual = "custom-individual"

    # Pair-Bond
    Bonded = "bonded"
    Married = "married"
    Separated = "separated"
    Divorced = "divorced"
    Moved = "moved"
    CustomPairBond = "custom-pairbond"

    # Emotion
    Fusion = "fusion"
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

    @classmethod
    def isMonadic(cls, x) -> bool:
        return x in (
            cls.Birth,
            cls.Adopted,
            cls.Death,
            cls.Cutoff,
            cls.CustomIndividual,
        )

    @classmethod
    def isDyadic(cls, x) -> bool:
        """
        Requires a mover and receiver. Not a pair-bond event.
        """
        return x in [
            cls.Conflict,
            cls.Distance,
            cls.Projection,
            cls.Reciprocity,
            cls.DefinedSelf,
            cls.Toward,
            cls.Away,
            cls.Inside,
            cls.Outside,
            cls.Fusion,
        ]

    @classmethod
    def isPairBond(cls, x) -> bool:
        return x in (
            cls.Bonded,
            cls.Married,
            cls.Separated,
            cls.Divorced,
            cls.Moved,
            cls.CustomPairBond,
        )

    @classmethod
    def isChild(cls, x) -> bool:
        return x in (cls.Adopted, cls.Birth)

    @classmethod
    def isCustom(cls, x) -> bool:
        """
        Requires a mover and receiver
        """
        return x in [cls.CustomIndividual, cls.CustomPairBond]

    @classmethod
    def eventLabelFor(cls, x) -> str:
        if x in (EventKind.CustomIndividual, EventKind.CustomPairBond):
            return ""
        elif cls.isMonadic(x):
            return x.name
        elif cls.isDyadic(x):
            return x.name
        elif cls.isPairBond(x):
            return x.name
        else:
            raise KeyError(f"Unknown event kind: {x}")

    @classmethod
    def menuLabelFor(cls, x) -> str:
        if x == EventKind.CustomIndividual:
            return f"Custom - Individual"
        if x == EventKind.CustomPairBond:
            return f"Custom - PairBond"
        elif cls.isMonadic(x):
            return x.name
        elif cls.isPairBond(x):
            return x.name
        elif cls.isDyadic(x):
            return x.name
        else:
            raise KeyError(f"Unknown event kind: {x}")

    @classmethod
    def menuLabels(cls) -> list[str]:
        return [EventKind.menuLabelFor(EventKind(x)) for x in cls.menuOrder()]

    @classmethod
    def menuOrder(cls) -> list[str]:
        """Sets order and label."""
        return [
            cls.Birth.value,
            cls.Adopted.value,
            cls.Death.value,
            cls.Cutoff.value,
            cls.CustomIndividual.value,
            cls.Bonded.value,
            cls.Married.value,
            cls.Separated.value,
            cls.Divorced.value,
            cls.Moved.value,
            cls.CustomPairBond.value,
            cls.Conflict.value,
            cls.Distance.value,
            cls.Projection.value,
            cls.Reciprocity.value,
            cls.DefinedSelf.value,
            cls.Toward.value,
            cls.Away.value,
            cls.Inside.value,
            cls.Outside.value,
            cls.Fusion.value,
        ]

    @classmethod
    def itemModeFor(cls, kind) -> int:
        from pkdiagram import util

        if kind == EventKind.Fusion:
            return util.ITEM_FUSION
        elif kind == EventKind.Cutoff:
            return util.ITEM_CUTOFF
        elif kind == EventKind.Conflict:
            return util.ITEM_CONFLICT
        elif kind == EventKind.Distance:
            return util.ITEM_DISTANCE
        elif kind == EventKind.Reciprocity:
            return util.ITEM_RECIPROCITY
        elif kind == EventKind.Projection:
            return util.ITEM_PROJECTION
        elif kind == EventKind.Toward:
            return util.ITEM_TOWARD
        elif kind == EventKind.Away:
            return util.ITEM_AWAY
        elif kind == EventKind.Inside:
            return util.ITEM_INSIDE
        elif kind == EventKind.Outside:
            return util.ITEM_OUTSIDE
        elif kind == EventKind.DefinedSelf:
            return util.ITEM_DEFINED_SELF
        else:
            raise KeyError(f"No ITEM_MODE for: {kind}")
