from ..pyqt import Qt, QPen, QPointF, QPainterPath, QRectF, QGraphicsItem
from .. import util
from .pathitem import PathItem
from .childof import ChildOf


class MultipleBirth(PathItem):

    @staticmethod
    def pathFor(children, marriage):
        path = QPainterPath()
        marriageSceneRect = marriage.mapToScene(
            marriage.path().boundingRect()
        ).boundingRect()

        children = [c for c in children if c.isVisible()]
        each = [(children[i], x) for i, x in enumerate(children[1:])]

        # left to right
        children = sorted(children, key=lambda x: x.scenePos().x())

        if not each:
            return path

        # # vertical rise
        # size = 0
        # for a, b in each:
        #     size = max(size, util.sizeForPeople(a, b))
        # personRect = util.personRectForSize(size)
        # rise = personRect.height() / 2.9

        xMin = None
        xMax = None
        for a, b in each:
            aP = ChildOf.personConnectionPoint(a)
            bP = ChildOf.personConnectionPoint(b)
            if xMin is None:
                xMin = min(aP.x(), bP.x())
            else:
                xMin = min(xMin, min(aP.x(), bP.x()))
            if xMax is None:
                xMax = max(aP.x(), bP.x())
            else:
                xMax = max(xMax, max(aP.x(), bP.x()))

        jigY = None
        for child in children:  # not always set when loading
            if child.childOf.multipleBirth:
                jigY = children[0].childOf.multipleBirth.jigY()
                break
        if jigY is None:
            return path

        # horizontal line
        path.moveTo(xMin, jigY)
        path.lineTo(xMax, jigY)

        # vertical line
        x = xMin + (xMax - xMin) / 2
        path.moveTo(x, jigY)
        leftP = marriageSceneRect.bottomLeft()
        rightP = marriageSceneRect.bottomRight()
        x = max(leftP.x(), min(rightP.x(), x))
        path.lineTo(x, leftP.y())

        return path

    def __init__(self, marriage=None, firstChildOf=None, secondChild=None):
        super().__init__()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.prop("itemPos").setLayered(False)
        self.isMultipleBirth = True
        self._children = []
        if firstChildOf:
            self._children.append(firstChildOf.person)
        if secondChild:
            self._children.append(secondChild)
        self._parents = marriage
        self._settingHover = False
        self.updateGeometry()

    ## copy/paste

    def write(self, chunk):
        super().write(chunk)
        chunk["children"] = [c.id for c in self._children]
        chunk["parents"] = self._parents.id

    def read(self, chunk, byId):
        super().read(chunk, byId)
        self._children = [byId(id) for id in chunk["children"]]
        self._parents = byId(chunk["parents"])

    def clone(self, scene):
        x = super().clone(scene)
        x._cloned_children_ids = [c.id for c in self._children]
        x._cloned_parents_id = self._parents.id
        return x

    def remap(self, map):
        self._parents = map.find(self._cloned_parents_id)
        delattr(self, "_cloned_parents_id")
        self._children = [map.find(x) for x in self._cloned_children_ids]
        delattr(self, "_cloned_children_ids")
        if not self._parents:
            return False
        else:
            return True

    ## Scene events

    def _onSetParents(self, parents):
        self._parents = parents

    def _onUnsetParents(self):
        self._parents = None

    def _onAddChild(self, person):
        if not person in self._children:
            self._children.append(person)
        self.updateScale()
        self.updateGeometry()

    def _onRemoveChild(self, person):
        if person in self._children:
            self._children.remove(person)
        if len(self._children) < 2:  # deinit
            # self._parents = None # never clear so undo works
            self._children = []
        else:
            self.updateScale()
            self.updateGeometry()

    def updatePen(self):
        super().updatePen()
        if self.hover:
            pen = QPen(util.HOVER_PEN)
        else:
            pen = QPen(util.PEN)
        pen.setCapStyle(self.penCapStyle)
        self.setPen(pen)

    ##

    def jigY(self):
        children = [c for c in self._children]
        each = [(children[i], x) for i, x in enumerate(children[1:])]
        # vertical rise
        size = 0
        for a, b in each:
            size = max(size, util.sizeForPeople(a, b))
        personRect = util.personRectForSize(size)
        rise = personRect.height() / 2.9

        assert each != []

        # highest child
        y_top = 1000000000
        for a, b in each:
            aP = ChildOf.personConnectionPoint(a)
            bP = ChildOf.personConnectionPoint(b)
            y_top = min(y_top, min(aP.y(), bP.y()))
        jigY = y_top - rise
        return jigY

    def parents(self):
        return self._parents

    def children(self):
        return self._children

    def shouldShowFor(self, dateTime, tags=[], layers=[]):
        for person in self._children:
            if person.childOf.shouldShowFor(dateTime, tags=tags, layers=layers):
                return True
        return False

    def dependents(self):
        return [person.childOf for person in self._children]

    def updateDependents(self):
        for item in self.dependents():
            item.updateGeometry()

    def updateGeometry(self):
        if len(self._children) > 1:
            path = self.pathFor(self._children, marriage=self._parents)
            self.setPos(path.boundingRect().center())
            path = self.mapFromScene(path)
        else:
            path = QPainterPath()
        if path != self.path():
            super().updateGeometry()
            self.setPath(path)
            self.updateDependents()
            self.updatePen()

    def updateScale(self):
        size = 0
        for person in self._children:
            size = max(size, person.size())
        scale = util.scaleForPersonSize(size)
        if scale != self.scale():
            self.setScale(scale)
            self.updateGeometry()

    def setHover(self, on):
        if self._settingHover:
            return
        self._settingHover = True
        super().setHover(on)
        for person in self._children:
            person.childOf.setHover(on)
        self._settingHover = False
