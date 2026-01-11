import math
from typing import TYPE_CHECKING

from pkdiagram.pyqt import QPointF
from pkdiagram import util

if TYPE_CHECKING:
    from .event import Event
    from .layer import Layer
    from .person import Person


class Triangle:

    def __init__(self, event: "Event"):
        self._event = event
        self._layer = None
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

    def createSymbols(self):
        from btcopilot.schema import RelationshipKind
        from .emotions import Emotion

        self.removeSymbols()

        scene = self._event.scene()
        if not scene or not self._layer:
            return

        mover = self.mover()
        targets = self.targets()
        triangles = self.triangles()
        if not mover or not targets or not triangles:
            return

        relationship = self._event.relationship()
        isInside = relationship == RelationshipKind.Inside
        eventColor = self._event.color()
        # Use default white/black when event has no meaningful color
        if eventColor in (None, "transparent", "#ffffff", "#000000"):
            eventColor = "#ffffff" if util.IS_UI_DARK_MODE else "#000000"

        # Inside Event:
        #   Inside: Mover → Targets
        #   Outside: Mover → Triangles
        #   Outside: Targets → Triangles
        # Outside Event:
        #   Outside: Mover → Targets
        #   Outside: Mover → Triangles
        #   Inside: Targets → Triangles

        # Mover → Targets (first target)
        moverTargetKind = (
            RelationshipKind.Inside if isInside else RelationshipKind.Outside
        )
        emotion1 = Emotion(kind=moverTargetKind, person=mover, target=targets[0])
        emotion1.setColor(eventColor)
        emotion1.setLayers([self._layer.id])
        self._symbolItems.append(emotion1)
        scene.addItem(emotion1)
        emotion1.setZValue(1000)

        # Mover → Triangles (first triangle person)
        emotion2 = Emotion(
            kind=RelationshipKind.Outside, person=mover, target=triangles[0]
        )
        emotion2.setColor(eventColor)
        emotion2.setLayers([self._layer.id])
        self._symbolItems.append(emotion2)
        scene.addItem(emotion2)
        emotion2.setZValue(1000)

        # Targets → Triangles
        targetTriangleKind = (
            RelationshipKind.Outside if isInside else RelationshipKind.Inside
        )
        emotion3 = Emotion(
            kind=targetTriangleKind, person=targets[0], target=triangles[0]
        )
        emotion3.setColor(eventColor)
        emotion3.setLayers([self._layer.id])
        self._symbolItems.append(emotion3)
        scene.addItem(emotion3)
        emotion3.setZValue(1000)

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
        topY = min(p.y() for p in allPositions) - 350

        color = self._event.color() if self._event.color() else "orange"
        callout = Callout(text=description, color=color, scale=2.0)
        callout.setLayers([self._layer.id])
        scene.addItem(callout)
        callout.setItemPosNow(
            QPointF(centerX - (callout.sceneBoundingRect().width() / 2), topY)
        )
        self._calloutItem = callout

    def removeCallout(self):
        scene = self._event.scene()
        if self._calloutItem and scene:
            scene.removeItem(self._calloutItem)
        self._calloutItem = None

    def hideRelationshipItems(self):
        from .marriage import Marriage
        from .childof import ChildOf
        from .emotions import Emotion

        scene = self._event.scene()
        if not scene:
            return

        self._hiddenItems = []
        for item in scene.find(types=[Marriage, ChildOf, Emotion]):
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

    def stopPhase2Animation(self):
        self.removeSymbols()
        self.removeCallout()
        self.showRelationshipItems()
