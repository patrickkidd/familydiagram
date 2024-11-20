class EmotionalUnit:
    """
    This stuff should really just go into the Marriage object. One argument
    against that is that the Marriage/Pair-Bond object can just be people with
    no children?
    """

    def __init__(self, marriage):
        self._marriage = marriage
        self._layer = None

    def marriage(self):
        return self._marriage

    def layer(self):
        return self._layer

    def setLayer(self, layer):
        self._layer = layer

    def update(self):
        """
        Ensure all the people are added to the layer.
        """
        x = 1
        for person in self.people():
            if self._layer and self._marriage.scene():
                if self._layer.id not in person.layers():
                    person.setLayers(person.layers() + [self._layer.id])
            else:
                person.setLayers(x for x in person.layers() if x != self._layer.id)
        y = 2

    def name(self) -> str:
        return self._marriage.itemName()

    def __lt__(self, other) -> bool:
        return self._marriage < other._marriage

    def people(self) -> list:
        return self._marriage.people + self._marriage.children
