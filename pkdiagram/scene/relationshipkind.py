import enum

from pkdiagram import util


class RelationshipKind(enum.Enum):
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
    def isRSymbol(cls, x) -> bool:
        return cls.isDyadic(x) or x == cls.Cutoff

    @classmethod
    def menuOrder(cls) -> list[str]:
        """Sets order and label."""
        return [
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
            cls.Cutoff.value,
        ]

    @classmethod
    def itemModeFor(cls, kind) -> int:
        if kind == cls.Fusion:
            return util.ITEM_FUSION
        elif kind == cls.Cutoff:
            return util.ITEM_CUTOFF
        elif kind == cls.Conflict:
            return util.ITEM_CONFLICT
        elif kind == cls.Distance:
            return util.ITEM_DISTANCE
        elif kind == cls.Reciprocity:
            return util.ITEM_RECIPROCITY
        elif kind == cls.Projection:
            return util.ITEM_PROJECTION
        elif kind == cls.Toward:
            return util.ITEM_TOWARD
        elif kind == cls.Away:
            return util.ITEM_AWAY
        elif kind == cls.Inside:
            return util.ITEM_INSIDE
        elif kind == cls.Outside:
            return util.ITEM_OUTSIDE
        elif kind == cls.DefinedSelf:
            return util.ITEM_DEFINED_SELF
        else:
            raise KeyError(f"No ITEM_MODE for: {kind}")
