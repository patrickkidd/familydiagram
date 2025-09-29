import enum


class LifeChange(enum.Enum):
    """
    Canonical Event uniqueId values. An Event has a uniqueId if it has a
    specific visual representation somewhere in the app, usually the diagram.
    """

    # Individual
    Birth = "birth"
    Adopted = "adopted"
    Death = "death"

    # Pair-Bond
    Bonded = "bonded"
    Married = "married"
    Separated = "separated"
    Divorced = "divorced"
    Moved = "moved"

    @classmethod
    def isMonadic(cls, x) -> bool:
        return x in (
            cls.Birth,
            cls.Adopted,
            cls.Death,
        )

    @classmethod
    def isPairBond(cls, x) -> bool:
        return x in (
            cls.Bonded,
            cls.Married,
            cls.Separated,
            cls.Divorced,
            cls.Moved,
        )

    @classmethod
    def isChild(cls, x) -> bool:
        return x in (cls.Adopted, cls.Birth)

    @classmethod
    def eventLabelFor(cls, x) -> str:
        if cls.isMonadic(x):
            return x.name
        elif cls.isPairBond(x):
            return x.name
        else:
            raise KeyError(f"Unknown event kind: {x}")

    @classmethod
    def menuLabelFor(cls, x) -> str:
        if cls.isMonadic(x):
            return x.name
        elif cls.isPairBond(x):
            return x.name
        else:
            raise KeyError(f"Unknown event kind: {x}")

    @classmethod
    def menuLabels(cls) -> list[str]:
        return [cls.menuLabelFor(cls(x)) for x in cls.menuOrder()]

    @classmethod
    def menuOrder(cls) -> list[str]:
        """Sets order and label."""
        return [
            cls.Birth.value,
            cls.Adopted.value,
            cls.Death.value,
            #
            cls.Bonded.value,
            cls.Married.value,
            cls.Separated.value,
            cls.Divorced.value,
            cls.Moved.value,
        ]
