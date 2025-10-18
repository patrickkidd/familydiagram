import enum


class RelationshipKind(enum.Enum):
    Fusion = "fusion"
    #
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

    def itemMode(self) -> "ItemMode":
        from pkdiagram.scene.itemmode import ItemMode

        if self == self.Cutoff:
            return ItemMode.Cutoff
        elif self == self.Conflict:
            return ItemMode.Conflict
        elif self == self.Distance:
            return ItemMode.Distance
        elif self in (self.Underfunctioning, self.Overfunctioning):
            return ItemMode.Reciprocity
        elif self == self.Projection:
            return ItemMode.Projection
        elif self == self.Toward:
            return ItemMode.Toward
        elif self == self.Away:
            return ItemMode.Away
        elif self == self.Inside:
            return ItemMode.Inside
        elif self == self.Outside:
            return ItemMode.Outside
        elif self == self.DefinedSelf:
            return ItemMode.DefinedSelf
        else:
            raise KeyError(f"No ITEM_MODE for: {self}")

    @staticmethod
    def fromItemMode(itemMode: "ItemMode") -> "RelationshipKind":
        from pkdiagram.scene import ItemMode

        mapping = {
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
