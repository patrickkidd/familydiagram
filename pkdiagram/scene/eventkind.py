import enum


class EventKind(enum.Enum):
    """
    Canonical Event uniqueId values. An Event has a uniqueId if it has a
    specific visual representation somewhere in the app, usually the diagram.
    """

    Bonded = "bonded"
    Married = "married"
    Separated = "separated"
    Divorced = "divorced"
    Moved = "moved"

    # isOffspring
    Birth = "birth"
    Adopted = "adopted"

    Death = "death"

    VariableShift = "variable-shift"

    def isOffspring(self) -> bool:
        return self in (self.Birth, self.Adopted)

    def isPairBond(self) -> bool:
        return self in (self.Bonded, self.Married, self.Separated, self.Divorced)

    @staticmethod
    def fromUniqueId(uniqueId: str) -> "EventKind | None":
        for kind in EventKind:
            if kind.value == uniqueId:
                return kind
        return None

    def menuLabel(self) -> str:
        labels = {
            self.Bonded: "Bonded",
            self.Married: "Married",
            self.Separated: "Separated",
            self.Divorced: "Divorced",
            self.Moved: "Moved",
            self.Birth: "Birth",
            self.Adopted: "Adopted",
            self.Death: "Death",
            self.VariableShift: "Shift",
        }
        return labels[self]
