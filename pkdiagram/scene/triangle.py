import math
from typing import TYPE_CHECKING

from pkdiagram.pyqt import (
    QPointF,
    QLineF,
    QRectF,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QTimer,
    QGraphicsPathItem,
    QPainterPath,
    QPen,
    QColor,
)
from pkdiagram import util

if TYPE_CHECKING:
    from .event import Event
    from .layer import Layer
    from .person import Person


class Triangle:

    def __init__(self, event: "Event"):
        self._event = event
        self._layer = None
        self._phase2AnimGroup = None
        self._phase2RepeatCount = 0
        self._phase2MaxRepeats = 3
        self._symbolItems = []
        self._calloutItem = None
        self._hiddenItems = []

    def event(self) -> "Event":
        return self._event

    def layer(self) -> "Layer":
        return self._layer

    def setLayer(self, layer: "Layer"):
        self._layer = layer

    def mover(self) -> "Person":
        return self._event.person()

    def targets(self) -> list:
        return self._event.relationshipTargets() or []

    def triangles(self) -> list:
        return self._event.relationshipTriangles() or []

    def allPeople(self) -> list:
        people = []
        if self.mover():
            people.append(self.mover())
        people.extend(self.targets())
        people.extend(self.triangles())
        return people

    def update(self):
        for person in self.allPeople():
            if (
                self._layer
                and self._event.scene()
                and self._layer in self._event.scene().layers()
            ):
                if self._layer.id not in person.layers():
                    person.setLayers(list(set(person.layers() + [self._layer.id])))
            else:
                person.setLayers(
                    list(x for x in person.layers() if x != self._layer.id)
                )

    def name(self) -> str:
        mover = self.mover()
        moverName = mover.name() if mover else "?"
        return f"Triangle: {moverName}"

    def __lt__(self, other) -> bool:
        return self._event < other._event

    def _calculateCentroid(self) -> QPointF | None:
        people = self.allPeople()
        # Use base positions (forLayers=[]) to get stable stored positions,
        # not visual positions which may change during animations or layer changes
        positions = [p.itemPos(forLayers=[]) for p in people]
        positions = [p for p in positions if p]
        if not positions:
            return None
        centroidX = sum(p.x() for p in positions) / len(positions)
        centroidY = sum(p.y() for p in positions) / len(positions)
        return QPointF(centroidX, centroidY)

    def calculatePositions(self, viewportSize: tuple = None) -> dict:
        from btcopilot.schema import RelationshipKind

        people = self.allPeople()
        if len(people) < 3:
            return {}

        centroid = self._calculateCentroid()
        if not centroid:
            return {}

        # Base triangle size - use viewport or default
        baseRadius = 300  # Distance from center to vertices

        neutralPositions = []
        for i in range(3):
            angle = math.radians(90 + i * 120)  # Start from top (90 degrees)
            x = centroid.x() + baseRadius * math.cos(angle)
            y = centroid.y() - baseRadius * math.sin(angle)  # Flip y for screen coords
            neutralPositions.append(QPointF(x, y))

        # Adjust for emotional proximity based on relationship kind
        relationship = self._event.relationship()
        proximityOffset = baseRadius * 0.3  # How much to shift for inside/outside

        result = {}

        mover = self.mover()
        if mover:
            moverPos = neutralPositions[0]
            if relationship == RelationshipKind.Inside:
                moverPos = QPointF(
                    moverPos.x() - proximityOffset * 0.5,
                    moverPos.y() + proximityOffset,
                )
            elif relationship == RelationshipKind.Outside:
                moverPos = QPointF(moverPos.x(), moverPos.y() - proximityOffset)
            result[mover.id] = moverPos

        targets = self.targets()
        if targets:
            targetBase = neutralPositions[1]
            for i, target in enumerate(targets):
                clusterOffset = self._clusterOffset(i, len(targets))
                result[target.id] = QPointF(
                    targetBase.x() + clusterOffset.x(),
                    targetBase.y() + clusterOffset.y(),
                )

        triangles = self.triangles()
        if triangles:
            triangleBase = neutralPositions[2]
            if relationship == RelationshipKind.Inside:
                triangleBase = QPointF(
                    triangleBase.x() + proximityOffset * 0.5,
                    triangleBase.y(),
                )
            elif relationship == RelationshipKind.Outside:
                triangleBase = QPointF(
                    triangleBase.x() - proximityOffset * 0.3,
                    triangleBase.y(),
                )
            for i, triangle in enumerate(triangles):
                clusterOffset = self._clusterOffset(i, len(triangles))
                result[triangle.id] = QPointF(
                    triangleBase.x() + clusterOffset.x(),
                    triangleBase.y() + clusterOffset.y(),
                )

        return result

    def _clusterOffset(self, index: int, total: int) -> QPointF:
        if total == 1:
            return QPointF(0, 0)
        elif total == 2:
            offsets = [QPointF(-20, 0), QPointF(20, 0)]
            return offsets[index]
        else:
            # Arrange in triangle pattern for 3+
            angle = math.radians(index * (360 / total))
            radius = 25
            return QPointF(radius * math.cos(angle), radius * math.sin(angle))

    def neutralMoverPosition(self) -> QPointF:
        people = self.allPeople()
        if len(people) < 3:
            return QPointF(0, 0)

        centroid = self._calculateCentroid()
        if not centroid:
            return QPointF(0, 0)

        # Top of equilateral triangle (90 degrees)
        baseRadius = 300
        angle = math.radians(90)
        x = centroid.x() + baseRadius * math.cos(angle)
        y = centroid.y() - baseRadius * math.sin(angle)
        return QPointF(x, y)

    def applyPositionsToLayer(self):
        if not self._layer:
            return

        positions = self.calculatePositions()
        for personId, pos in positions.items():
            self._layer.setItemProperty(personId, "itemPos", pos)

    def clusterCentroids(self) -> dict:
        positions = self.calculatePositions()
        result = {}

        # Mover centroid (just the mover position)
        mover = self.mover()
        if mover and mover.id in positions:
            result["mover"] = positions[mover.id]

        # Targets centroid
        targets = self.targets()
        if targets:
            targetPositions = [positions[t.id] for t in targets if t.id in positions]
            if targetPositions:
                cx = sum(p.x() for p in targetPositions) / len(targetPositions)
                cy = sum(p.y() for p in targetPositions) / len(targetPositions)
                result["targets"] = QPointF(cx, cy)

        # Triangles centroid
        triangles = self.triangles()
        if triangles:
            trianglePositions = [
                positions[t.id] for t in triangles if t.id in positions
            ]
            if trianglePositions:
                cx = sum(p.x() for p in trianglePositions) / len(trianglePositions)
                cy = sum(p.y() for p in trianglePositions) / len(trianglePositions)
                result["triangles"] = QPointF(cx, cy)

        return result

    def _arrowPath(self, fromPt: QPointF, toPt: QPointF, inward: bool) -> QPainterPath:
        path = QPainterPath()
        line = QLineF(fromPt, toPt)
        length = line.length()
        if length < 1:
            return path

        gap = 30
        arrowSize = 12
        midGap = 15

        startPt = line.pointAt(gap / length)
        endPt = line.pointAt(1 - gap / length)

        if inward:
            leftArrowTip = line.pointAt((0.5 * length - midGap) / length)
            leftArrowBase = line.pointAt(
                (0.5 * length - midGap - arrowSize * 2) / length
            )
            path.moveTo(startPt)
            path.lineTo(leftArrowBase)
            # Arrowhead
            normal = QLineF(leftArrowBase, leftArrowTip).normalVector()
            normal.setLength(arrowSize * 0.5)
            p1 = normal.p2()
            normal.setLength(-arrowSize * 0.5)
            p2 = normal.p2()
            path.moveTo(leftArrowTip)
            path.lineTo(p1)
            path.moveTo(leftArrowTip)
            path.lineTo(p2)

            rightArrowTip = line.pointAt((0.5 * length + midGap) / length)
            rightArrowBase = line.pointAt(
                (0.5 * length + midGap + arrowSize * 2) / length
            )
            path.moveTo(endPt)
            path.lineTo(rightArrowBase)
            # Arrowhead
            normal = QLineF(rightArrowBase, rightArrowTip).normalVector()
            normal.setLength(arrowSize * 0.5)
            p1 = normal.p2()
            normal.setLength(-arrowSize * 0.5)
            p2 = normal.p2()
            path.moveTo(rightArrowTip)
            path.lineTo(p1)
            path.moveTo(rightArrowTip)
            path.lineTo(p2)
        else:
            leftArrowTip = line.pointAt((gap + arrowSize) / length)
            leftArrowBase = line.pointAt((0.5 * length - midGap) / length)
            path.moveTo(leftArrowBase)
            path.lineTo(leftArrowTip)
            # Arrowhead
            normal = QLineF(leftArrowBase, leftArrowTip).normalVector()
            normal.setLength(arrowSize * 0.5)
            p1 = normal.p2()
            normal.setLength(-arrowSize * 0.5)
            p2 = normal.p2()
            path.moveTo(leftArrowTip)
            path.lineTo(p1)
            path.moveTo(leftArrowTip)
            path.lineTo(p2)

            rightArrowTip = line.pointAt(1 - (gap + arrowSize) / length)
            rightArrowBase = line.pointAt((0.5 * length + midGap) / length)
            path.moveTo(rightArrowBase)
            path.lineTo(rightArrowTip)
            # Arrowhead
            normal = QLineF(rightArrowBase, rightArrowTip).normalVector()
            normal.setLength(arrowSize * 0.5)
            p1 = normal.p2()
            normal.setLength(-arrowSize * 0.5)
            p2 = normal.p2()
            path.moveTo(rightArrowTip)
            path.lineTo(p1)
            path.moveTo(rightArrowTip)
            path.lineTo(p2)

        return path

    def _linePath(self, fromPt: QPointF, toPt: QPointF) -> QPainterPath:
        path = QPainterPath()
        line = QLineF(fromPt, toPt)
        length = line.length()
        if length < 1:
            return path

        gap = 30
        startPt = line.pointAt(gap / length)
        endPt = line.pointAt(1 - gap / length)
        path.moveTo(startPt)
        path.lineTo(endPt)
        return path

    def createSymbols(self):
        from btcopilot.schema import RelationshipKind

        self.removeSymbols()

        scene = self._event.scene()
        if not scene:
            return

        centroids = self.clusterCentroids()
        if len(centroids) < 3:
            return

        relationship = self._event.relationship()
        color = QColor(self._event.color()) if self._event.color() else QColor("orange")
        pen = QPen(color, 2)

        if "mover" in centroids and "targets" in centroids:
            isInside = relationship == RelationshipKind.Inside
            path = self._arrowPath(
                centroids["mover"], centroids["targets"], inward=isInside
            )
            item = QGraphicsPathItem(path)
            item.setPen(pen)
            scene.addItem(item)
            self._symbolItems.append(item)

        if "mover" in centroids and "triangles" in centroids:
            isInside = relationship != RelationshipKind.Inside
            path = self._arrowPath(
                centroids["mover"], centroids["triangles"], inward=isInside
            )
            item = QGraphicsPathItem(path)
            item.setPen(pen)
            scene.addItem(item)
            self._symbolItems.append(item)

        if "targets" in centroids and "triangles" in centroids:
            path = self._linePath(centroids["targets"], centroids["triangles"])
            item = QGraphicsPathItem(path)
            dashPen = QPen(color.darker(130), 1)
            dashPen.setDashPattern([5, 5])
            item.setPen(dashPen)
            scene.addItem(item)
            self._symbolItems.append(item)

    def removeSymbols(self):
        scene = self._event.scene()
        for item in self._symbolItems:
            if scene:
                scene.removeItem(item)
        self._symbolItems.clear()

    def createCallout(self):
        from .callout import Callout

        self.removeCallout()

        scene = self._event.scene()
        if not scene or not self._layer:
            return

        description = self._event.description()
        if not description:
            return

        positions = self.calculatePositions()
        if not positions:
            return

        # Position as header above all three clusters
        allPositions = list(positions.values())
        centerX = sum(p.x() for p in allPositions) / len(allPositions)
        topY = min(p.y() for p in allPositions) - 150

        color = self._event.color() if self._event.color() else "orange"
        callout = Callout(text=description, color=color)
        scene.addItem(callout)
        callout.setLayers([self._layer.id])
        callout.setItemPos(QPointF(centerX, topY))
        self._calloutItem = callout

    def removeCallout(self):
        scene = self._event.scene()
        if self._calloutItem and scene:
            scene.removeItem(self._calloutItem)
        self._calloutItem = None

    def hideRelationshipItems(self):
        from .marriage import Marriage
        from .childof import ChildOf

        scene = self._event.scene()
        if not scene:
            return

        self._hiddenItems = []
        for item in scene.find(types=[Marriage, ChildOf]):
            if item.opacity() > 0:
                self._hiddenItems.append(item)
                item.setPathItemVisible(False)

    def showRelationshipItems(self):
        for item in self._hiddenItems:
            item.setPathItemVisible(True)
        self._hiddenItems = []

    def startPhase2Animation(self):
        mover = self.mover()
        if not mover or not self._layer:
            return

        # Create symbols between position clusters
        self.createSymbols()
        # Create callout with event description
        self.createCallout()

        self._phase2RepeatCount = 0
        self._runPhase2Cycle()

    def _runPhase2Cycle(self):
        mover = self.mover()
        if not mover:
            return

        if self._phase2RepeatCount >= self._phase2MaxRepeats:
            self.stopPhase2Animation()
            return

        neutralPos = self.neutralMoverPosition()
        finalPositions = self.calculatePositions()
        finalPos = finalPositions.get(mover.id)
        if not finalPos:
            return

        mover.setPos(neutralPos)

        self._phase2AnimGroup = QSequentialAnimationGroup()
        anim = QPropertyAnimation(mover, b"pos")
        anim.setDuration(util.ANIM_DURATION_MS * 3)
        anim.setStartValue(neutralPos)
        anim.setEndValue(finalPos)
        self._phase2AnimGroup.addAnimation(anim)
        self._phase2AnimGroup.finished.connect(self._onPhase2CycleFinished)
        self._phase2AnimGroup.start()

    def _onPhase2CycleFinished(self):
        self._phase2RepeatCount += 1
        if self._phase2RepeatCount < self._phase2MaxRepeats:
            QTimer.singleShot(200, self._runPhase2Cycle)

    def stopPhase2Animation(self):
        if self._phase2AnimGroup:
            self._phase2AnimGroup.stop()
            self._phase2AnimGroup = None
        self._phase2RepeatCount = 0
        self.removeSymbols()
        self.removeCallout()
        self.showRelationshipItems()
