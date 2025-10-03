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
            self.VariableShift: "Variable Shift",
        }
        return labels[self]
