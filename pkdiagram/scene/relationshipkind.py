import enum

from pkdiagram import util


class RelationshipKind(enum.Enum):
    # Fusion = "fusion"
    Conflict = "conflict"
    Distance = "distance"
    Overfunctioning = "overfunctioning"
    Underfunctioning = "underfunctioning"
    Projection = "projection"
    DefinedSelf = "defined-self"
    Toward = "toward"
    Away = "away"
    Inside = "inside"
    Outside = "outside"
    Cutoff = "cutoff"

    def itemMode(self) -> int:
        # if kind == self.Fusion:
        #     return util.ITEM_FUSION
        if self == self.Cutoff:
            return util.ITEM_CUTOFF
        elif self == self.Conflict:
            return util.ITEM_CONFLICT
        elif self == self.Distance:
            return util.ITEM_DISTANCE
        elif self in (self.Underfunctioning, self.Overfunctioning):
            return util.ITEM_RECIPROCITY
        elif self == self.Projection:
            return util.ITEM_PROJECTION
        elif self == self.Toward:
            return util.ITEM_TOWARD
        elif self == self.Away:
            return util.ITEM_AWAY
        elif self == self.Inside:
            return util.ITEM_INSIDE
        elif self == self.Outside:
            return util.ITEM_OUTSIDE
        elif self == self.DefinedSelf:
            return util.ITEM_DEFINED_SELF
        else:
            raise KeyError(f"No ITEM_MODE for: {self}")

    @staticmethod
    def fromItemMode(itemMode: int) -> "RelationshipKind":
        mapping = {
            # util.ITEM_FUSION: RelationshipKind.Fusion,
            util.ITEM_CONFLICT: RelationshipKind.Conflict,
            util.ITEM_DISTANCE: RelationshipKind.Distance,
            util.ITEM_RECIPROCITY: RelationshipKind.Underfunctioning,  # or Underfunctioning
            util.ITEM_RECIPROCITY: RelationshipKind.Overfunctioning,  # or Underfunctioning
            util.ITEM_PROJECTION: RelationshipKind.Projection,
            util.ITEM_DEFINED_SELF: RelationshipKind.DefinedSelf,
            util.ITEM_TOWARD: RelationshipKind.Toward,
            util.ITEM_AWAY: RelationshipKind.Away,
            util.ITEM_INSIDE: RelationshipKind.Inside,
            util.ITEM_OUTSIDE: RelationshipKind.Outside,
            util.ITEM_CUTOFF: RelationshipKind.Cutoff,
        }
        if itemMode in mapping:
            return mapping[itemMode]
        else:
            raise KeyError(f"No RelationshipKind for ITEM_MODE: {itemMode}")

    def menuLabel(self) -> str:
        labels = {
            # self.Fusion: "Fusion",
            self.Conflict: "Conflict",
            self.Distance: "Distance",
            self.Overfunctioning: "Overfunctioning",
            self.Underfunctioning: "Underfunctioning",
            self.Projection: "Projection",
            self.DefinedSelf: "Defined Self",
            self.Toward: "Toward",
            self.Away: "Away",
            self.Inside: "Triangle to inside",
            self.Outside: "Triangle to outside",
            self.Cutoff: "Cutoff",
        }
        return labels[self]
