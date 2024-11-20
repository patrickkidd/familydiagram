from pkdiagram.pyqt import QObject


class ItemGarbage(QObject):
    """A garbage collector that runs in idle time."""

    CHUNK_SIZE = 10
    ASYNC = True

    def __init__(self, parent=None, _async=None):
        super().__init__(parent)
        if _async is None:
            self._async = self.ASYNC
        else:
            self._async = _async
        self.itemRegistries = []
        self._timer = None

    def timerEvent(self, e):
        # get one chunk
        count = 0
        while self.itemRegistries and count < self.CHUNK_SIZE:
            reg = self.itemRegistries[0]
            for id, item in dict(reg).items():
                item.deinit()
                del reg[id]
                count += 1
                if count == self.CHUNK_SIZE:
                    break
            if not reg:
                self.itemRegistries.remove(reg)
        # all done
        if not self.itemRegistries:
            self.killTimer(self._timer)
            self._timer = None

    def dump(self, itemRegistry):
        if self._async:
            self.itemRegistries.append(itemRegistry)
            if self._timer is None:
                self._timer = self.startTimer(0)
        else:
            for id, item in dict(itemRegistry).items():
                item.deinit()
                del itemRegistry[item.id]
