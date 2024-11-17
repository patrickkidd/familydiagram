from pkdiagram.objects import Marriage, Person, Layer


class EmotionalUnit:

    def __init__(self, marriage, layer):
        self._marriage = marriage
        self._layer = layer

    def marriage(self):
        return self._marriage

    def layer(self):
        return self._layer

    def __lt__(self, other) -> bool:
        return self._marriage < other._marriage
