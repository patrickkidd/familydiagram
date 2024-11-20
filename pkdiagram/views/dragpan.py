from pkdiagram.pyqt import QGraphicsView, QGraphicsItem


class DragPanner:

    def __init__(self, view):
        self.view = view
        self._begun = False
        self.was_dragMode = None
        self.selectables = []
        self.movables = []

    def begun(self):
        return self._begun

    def begin(self, e):
        if self.begun():
            self.cancel(e)
        self.was_sceneCenter = self.view.sceneCenter()
        self.was_dragMode = self.view.dragMode()
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        # allow for dragging on people and other selectables.
        # for item in self.view.scene().items():
        #     if item.flags() & QGraphicsItem.ItemIsMovable:
        #         item.setFlag(QGraphicsItem.ItemIsMovable, False)
        #         self.movables.append(item)
        #     if item.flags() & QGraphicsItem.ItemIsSelectable:
        #         item.setFlag(QGraphicsItem.ItemIsSelectable, False)
        #         self.selectables.append(item)
        QGraphicsView.mousePressEvent(self.view, e)  # necessary for drag mod to work
        self._begun = True

    def update(self, e):
        if self.was_dragMode:
            QGraphicsView.mouseMoveEvent(self.view, e)
            return

    def end(self, e):
        if not self.begun():
            return
        QGraphicsView.mouseReleaseEvent(self.view, e)
        self.view.setDragMode(self.was_dragMode)
        # for item in self.selectables:
        #     item.setFlag(QGraphicsItem.ItemIsSelectable, True)
        # self.selectables = []
        # for item in self.movables:
        #     item.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.movables = []
        self._begun = False
        self.view.panAbsolute(self.view.sceneCenter())

    def cancel(self, e):
        if not self.begun():
            return
        QGraphicsView.mouseReleaseEvent(self.view, e)
        self.view.setDragMode(self.was_dragMode)
        for item in self.selectables:
            item.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.selectables = []
        self._begun = False
