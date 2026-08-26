from pkdiagram.pyqt import QUndoCommand


class AcceptPDPItems(QUndoCommand):
    """One undo step for accepting staged items (FD-336 D5): the server row and
    the Scene move together, so undo brings back both the cards and the items.

    The accept has already run when the command is pushed, so the first redo
    Qt issues from push() is a no-op.
    """

    def __init__(self, controller, itemIds: list[int], prev: dict, post: dict):
        super().__init__(f"Accept {len(itemIds)} extracted item(s)")
        self.controller = controller
        self.itemIds = itemIds
        self.prev = prev
        self.post = post
        self._pushed = False

    def redo(self):
        if not self._pushed:
            self._pushed = True
            self._markClean()
            return
        result = self.controller._acceptIds(self.itemIds)
        if result:
            self.prev, self.post = result
            self._markClean()

    def undo(self):
        if self.controller._revertTo(self.prev):
            self._markClean()

    def _markClean(self):
        """The save wrote the whole Scene, so the document has nothing unsaved
        left (D4). The stack moves its index only after redo/undo returns, so
        the clean point can't be set until it has."""
        stack = self.controller.scene.stack()

        def settled(index):
            stack.indexChanged.disconnect(settled)
            stack.setClean()

        stack.indexChanged.connect(settled)
