from pkdiagram.pyqt import (
    Qt,
    QPen,
    QPointF,
    QPainterPath,
    QRectF,
    QGraphicsItem,
    QColor,
)
from pkdiagram import util
from pkdiagram.scene import PathItem


class ChildOf(PathItem):

    @staticmethod
    def personConnectionPoint(person):
        rect = QRectF(util.PERSON_RECT)
        r = QPointF(
            rect.topLeft().x() + (rect.topRight().x() - rect.topLeft().x()) / 2,
            rect.topLeft().y(),
        )
        return person.mapToScene(r)

    @staticmethod
    def pathFor(person, marriage=None, endPos=None):
        path = QPainterPath()
        if endPos:
            start = ChildOf.personConnectionPoint(person)
            y = endPos.y()
            x = endPos.x()
            path.moveTo(start)
            path.lineTo(x, y)
        elif person.childOf and not person.childOf.multipleBirth:
            start = ChildOf.personConnectionPoint(person)
            marriageSceneRect = marriage.mapToScene(
                marriage.path().controlPointRect()
            ).boundingRect()
            y = marriageSceneRect.bottomLeft().y()
            leftP = marriageSceneRect.bottomLeft()
            rightP = marriageSceneRect.bottomRight()
            x = ChildOf.personConnectionPoint(person).x()
            x = max(leftP.x(), min(rightP.x(), x))
            end = QPointF(x, y)
            path.moveTo(start)
            path.lineTo(end)
        elif (
            person.childOf
            and person.childOf.multipleBirth
            and len(person.childOf.multipleBirth.children()) > 1
        ):
            # children is less than two for intermediate step when reading scene
            # from file.
            start = ChildOf.personConnectionPoint(person)
            mRect = marriage.mapToScene(marriage.boundingRect()).boundingRect()
            end = QPointF(start.x(), person.childOf.multipleBirth.jigY())
            path = QPainterPath()
            path.moveTo(start)
            path.lineTo(end)
        return path

    def __init__(self, person, marriage):
        super().__init__()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.prop("itemPos").setLayered(False)
        self.isChildOf = True
        self.person = person
        self._parents = marriage
        self.multipleBirth = None
        self.penCapStyle = Qt.FlatCap
        self._settingHover = False

    # set data

    def write(self, chunk):
        chunk["person"] = self.person.id
        if self._parents:
            chunk["parents"] = self._parents.id
        else:
            chunk["parents"] = None
        if self.multipleBirth:
            chunk["multipleBirth"] = self.multipleBirth.id
        else:
            chunk["multipleBirth"] = None

    def read(self, chunk, byId):
        self.person = byId(chunk["person"])
        self._parents = byId(chunk["parents"])
        self._parents._onAddChild(self.person)
        self.multipleBirth = byId(chunk["multipleBirth"])

    # Cloning

    def clone(self, scene):
        x = super().clone(scene)
        x._cloned_parents_id = self._parents.id
        x._cloned_multipleBirth_id = (
            self.multipleBirth and self.multipleBirth.id or None
        )
        return x

    def remap(self, map):
        self._parents = map.find(self._cloned_parents_id)
        del self._cloned_parents_id
        self.multipleBirth = map.find(self._cloned_multipleBirth_id)
        del self._cloned_multipleBirth_id
        return True

    def parents(self):
        return self._parents

    def _onSetMultipleBirth(self, multipleBirth):
        self.multipleBirth = multipleBirth

    def _onRemoveMultipleBirth(self):
        self.multipleBirth = None

    ## Internal Data

    def shouldShowFor(self, dateTime, tags=[], layers=[]):
        """
        Just link to whether the parents are shown.
        """
        if self.scene() and self.scene().activeTriangle():
            return False
        if not self.person.shouldShowFor(dateTime, tags=tags, layers=layers):
            return False
        if self._parents and not self._parents.shouldShowFor(
            dateTime, tags=tags, layers=layers
        ):
            return False
        else:
            return True

    def updatePen(self):
        super().updatePen()
        pen = QPen(util.PEN)
        if self.person:
            if self.person.adopted() or self.person.adoptedEvents():
                pen.setStyle(Qt.DashLine)
            else:
                pen.setStyle(Qt.SolidLine)
        else:
            pen.setStyle(Qt.SolidLine)
        pen.setJoinStyle(Qt.MiterJoin)
        self.setPen(pen)

    def updateGeometry(self):
        if not self.parentItem() is self.person:  # just always check
            self.setParentItem(self.person)
        super().updateGeometry()
        self.updatePen()
        path = ChildOf.pathFor(self.person, marriage=self._parents)
        newPathSceneRect = path.controlPointRect()
        newScenePos = QPointF(
            newPathSceneRect.bottomLeft().x() + newPathSceneRect.width() / 2,
            newPathSceneRect.bottomLeft().y(),
        )
        if newScenePos != self.pos():
            self.setPos(newScenePos)
        path = self.mapFromScene(path)
        self.setPath(path)

    def setHover(self, on):
        if self._settingHover:
            return
        self._settingHover = True
        super().setHover(on)
        if self.multipleBirth:
            self.multipleBirth.setHover(on)
        self._settingHover = False
