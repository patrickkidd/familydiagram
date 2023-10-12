import random, collections, logging
from ..pyqt import *
from .. import util, commands
from . import Property
from ..util import CUtil
from .event import Event
from .pathitem import PathItem


DEBUG = False

log = logging.getLogger(__name__)



def showPoint(path, point, name, coords=False):
    OFFSET = 2.0
    def S(p):
        return '(%.1f, %.1f)' % (point.x(), point.y())
    dot = QRectF(0, 0, OFFSET, OFFSET)
    dot.moveCenter(point)
    path.addRoundedRect(dot, OFFSET / 2, OFFSET / 2)
    if coords is True:
        s = name + ': ' + S(point)
    else:
        s = name
    path.addText(point + QPointF(OFFSET, OFFSET), QFont('Helvetica', 6, 0), s)



class Jig:
    """ Always in scene coordinates. """

    WIDTH = 15.0
    STEP = 20.0

    def __init__(self, personA=None, personB=None, pointB=None, circA=None, circB=None,
                 width=None, step=None, pointA=None):
        if pointA is None and personA:
            pointA = personA.mapToScene(personA.boundingRect().center()) # TODO: use personA.pos()?
        if circA is None and personA: # circumference from original person
            personWidth = personA.mapToScene(personA.boundingRect()).boundingRect().width()
            if personA.gender() == 'male':
                circA = personWidth - personWidth * .25
            else:
                circA = personWidth - personWidth * .2
        if pointB is None and personB:
            pointB = personB.mapToScene(personB.boundingRect().center())
            if circB is None:
                personWidth = personB.mapToScene(personB.boundingRect()).boundingRect().width()
                if personA.gender() == 'male':
                    circB = personWidth - personWidth * .25
                else:
                    circB = personWidth - personWidth * .2
        if circB is None:
            circB = circA
        # if personA and personB:
        #     size = util.sizeForPeople(personA, personB)
        #     scale = util.scaleForPersonSize(size)
        # elif personA:
        #     scale = personA.scale()
        # else:
        #     scale = 1.0
        # stor for copying/translating in divideBy
        self.pointA = pointA
        self.pointB = pointB
        self.personA = personA
        self.personB = personB
        self.circA = circA
        self.circB = circB
        self.width = width and width or self.WIDTH
        self.step = step and step or self.STEP
        # self.width *= scale
        # start points
        self.aP = CUtil.pointOnRay(self.pointA, self.pointB, self.circA)
        self.bP = CUtil.pointOnRay(self.pointB, self.pointA, self.circB)
        # first parallel boundary
        self.p1 = CUtil.perpendicular(self.pointA, self.aP, self.width)
        self.p2 = CUtil.perpendicular(self.bP, self.pointB, self.width, True)
        # second parallel boundary
        self.p3 = CUtil.perpendicular(self.pointB, self.bP, self.width)
        self.p4 = CUtil.perpendicular(self.aP, self.pointA, self.width, True)

    def copy(self):
        return Jig(self.personA, personB=self.personB, pointB=self.pointB,
                   circA=self.circA, circB=self.circB, width=self.width, step=self.step)

    def alternatingPoints(self):
        """ Return alternating points for waves or zig-zag. """
        i = 1
        points = [self.p4]
        stopD = CUtil.distance(self.aP, self.bP)
        while True and stopD > 0:
            if i % 2:
                nextP = CUtil.pointOnRay(self.p1, self.p2, self.step * i)
                middle = CUtil.perpendicular(nextP, self.p1, self.width, True)
            else:
                nextP = CUtil.pointOnRay(self.p4, self.p3, self.step * i)
                middle = CUtil.perpendicular(self.p4, nextP, self.width, False)
            points.append(nextP)
            dist = CUtil.distance(middle, self.aP)
            if dist > stopD or dist == 0.0:
                if DEBUG:
                    showPoint(path, middle, 'middle'+str(i))
                break
            i += 1
            if i > 350:
                log.warning("Prevented infinite loop")
                break
        return points

    def divideBy(self, num):
        if num == 1:
            return [self]
        elif num == 2:
            delta = (self.p1 - self.aP) / 2 # others will be the same
            pointA = self.pointA + delta
            pointB = self.pointB + delta
            jig1 = Jig(pointA=pointA, pointB=pointB,
                       width=self.width, step=self.step,
                       circA=self.circA, circB=self.circB)
            pointA = self.pointA - delta
            pointB = self.pointB - delta
            jig2 = Jig(pointA=pointA, pointB=pointB,
                       width=self.width, step=self.step,
                       circA=self.circA, circB=self.circB)
            return [jig1, jig2]
        elif num == 3:
            delta = (self.p1 - self.aP) # others will be the same
            pointA = self.pointA + delta
            pointB = self.pointB + delta
            jig1 = Jig(pointA=pointA, pointB=pointB,
                       width=self.width, step=self.step,
                       circA=self.circA, circB=self.circB)
            pointA = self.pointA - delta
            pointB = self.pointB - delta
            jig2 = Jig(pointA=pointA, pointB=pointB,
                       width=self.width, step=self.step,
                       circA=self.circA, circB=self.circB)
            return [jig1, self, jig2]
        elif num == 4:
            delta = (self.p1 - self.aP) / 2 # others will be the same
            pointA = self.pointA + delta
            pointB = self.pointB + delta
            jig1 = Jig(pointA=pointA, pointB=pointB,
                       width=self.width, step=self.step,
                       circA=self.circA, circB=self.circB)
            pointA = self.pointA - delta
            pointB = self.pointB - delta
            jig2 = Jig(pointA=pointA, pointB=pointB,
                       width=self.width, step=self.step,
                       circA=self.circA, circB=self.circB)
            delta = (self.p1 - self.aP) * 1.5 # others will be the same
            pointA = self.pointA + delta
            pointB = self.pointB + delta
            jig3 = Jig(pointA=pointA, pointB=pointB,
                       width=self.width, step=self.step,
                       circA=self.circA, circB=self.circB)
            pointA = self.pointA - delta
            pointB = self.pointB - delta
            jig4 = Jig(pointA=pointA, pointB=pointB,
                       width=self.width, step=self.step,
                       circA=self.circA, circB=self.circB)
            return [jig1, jig2, jig3, jig4]
            
        
    def addTo(self, path):
        path.moveTo(self.aP)
        path.lineTo(self.bP)
        path.moveTo(self.p1)
        path.lineTo(self.p2)
        path.moveTo(self.p3)
        path.lineTo(self.p4)
        showPoint(path, self.aP, 'aP')
        showPoint(path, self.bP, 'bP')
        showPoint(path, self.p1, 'p1')
        showPoint(path, self.p2, 'p2')
        showPoint(path, self.p3, 'p3')
        showPoint(path, self.p4, 'p4')


class AnimGroup(QParallelAnimationGroup):

    currentTimeUpdated = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def updateCurrentTime(self, x):
        super().updateCurrentTime(x)
        self.currentTimeUpdated.emit()

    def currentTick(self):
        return self.currentTime() / self.duration()

    def start(self):
        if not util.IS_TEST:
            super().start()
        else:
            self.updateCurrentTime(self.duration())
            self.finished.emit()


class FannedBox(QGraphicsObject):
    """ Animate overlapping emotions out from each other. """

    DEBUG_PAINT = False
    
    FAN_IN_DELAY_MS = 2000
    SCALE = 3.0

    def __init__(self, emotions):
        super().__init__()
        self.setAcceptHoverEvents(True)
        self.animationGroup = AnimGroup(self)
        self.animationGroup.currentTimeUpdated.connect(self.onAnimationTick)
        self.animationGroup.finished.connect(self.onAnimationFinished)
        self.offsetAnimation = QVariantAnimation(self)
        self.offsetAnimation.setDuration(300)
        self.offsetAnimation.setStartValue(0.0)
        self.offsetAnimation.setEndValue(1.0)
        self.offsetAnimation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animationGroup.addAnimation(self.offsetAnimation)
        self.entries = {}
        self._toRemoveAfterAnim = []
        self._boundingRect = QRectF()
        self._shape = QPainterPath()
        self.fanInDelayTimer = None
        self.emotions = set(emotions)
        if self.emotions:
            self.dirty = True
        else:
            self.dirty = False # When &.emotions changes

    def addEmotion(self, emotion):
        if not emotion in self.emotions:
            self.emotions.add(emotion)
            self.dirty = True
            self.updateFannedState()

    def removeEmotion(self, emotion):
        if emotion in self.emotions:
            self.emotions.remove(emotion)
            self._toRemoveAfterAnim.append(emotion)
            self.dirty = True
            self.updateFannedState()
        if len(self.emotions) < 1:
            # tear down
            if self.scene():
                self.scene().removeItem(self)

    def paint(self, painter, option, widget):
        """ must be overridden."""
        if self.DEBUG_PAINT:
            painter.save()
            pen = QPen(Qt.red, 0.0)
            pen.setStyle(Qt.DotLine)
            painter.setPen(pen)
            painter.drawPath(self.shape())
            painter.restore()
        
    def boundingRect(self):
        return self._boundingRect

    def shape(self):
        # path = QPainterPath()
        # path.addRect(self._boundingRect)
        # return path
        return self._shape

    def updateGeometry(self):
        """ Keep the shape updated once fanned out to encompass the children. """
        self.prepareGeometryChange()
        rect = QRectF()
        shape = QPainterPath()
        for emotion, entry in self.entries.items():
            rect = rect.united(emotion.mapToScene(emotion.boundingRect()).boundingRect())
            jig = self.jigFor(emotion, widthScale=2.0)
            D = entry['endPosDelta']
            jigPolygon = QPolygonF([jig.p1+D, jig.p2+D, jig.p3+D, jig.p4+D])
            shapePath = QPainterPath()
            shapePath.addPolygon(jigPolygon)
            shape = shape.united(shapePath)
        self._boundingRect = self.mapFromScene(rect).boundingRect()
        self._shape = self.mapFromScene(shape)
        self.setPos(rect.center())

    def jigFor(self, emotion, widthScale=1.0):
        size = util.sizeForPeople(emotion.personA(), emotion.personB())
        scale = util.scaleForPersonSize(size)
        width = Jig.WIDTH * scale * widthScale
        jig = Jig(emotion.personA(), emotion.personB(), None, width=width)
        return jig

    def _steps(self):
        emotions = list(set(self.emotions) - set(self._toRemoveAfterAnim))
        spread = len(emotions) - 1.0
        start = -(spread / 2.0)
        steps = [i for i in util.frange(start, start+spread+1, 1.0)]
        return zip(emotions, steps)

    def updateFannedState(self):
        """ Called when the number of visible emotions changes. """
        if not self.dirty:
            # This is called once per peer per update frame, so ensure it's only called once.
            return
        self.dirty = False
        
        if self.animationGroup.state() == QAbstractAnimation.Running:
            self.animationGroup.stop()

        entries = {}
        # 1) Set starting origins for each currently visible emotion.
        for emotion, entry in self.entries.items():
            entries[emotion] = {
                'alt': None,
                'beginPosDelta': self.currentOffsetFor(emotion)
            }
        # 2) Set destinations for emotions remaining visible after animation.
        for emotion, alt in self._steps():
            if not emotion in entries:
                entries[emotion] = {}
            entries[emotion].update({
                'alt': alt,
                'endPosDelta': self.endPosDeltaFor(emotion)
            })
            if not 'beginPosDelta' in entries[emotion]:
                entries[emotion]['beginPosDelta'] = QPointF(0, 0)
        # 3) Set destination as origin for emotions hiding after this animation.
        for emotion in self._toRemoveAfterAnim:
            entries[emotion].update({
                'endPosDelta': QPointF(0, 0)
            })
            if not 'beginPosDelta' in entries[emotion]:
                entries[emotion]['beginPosDelta'] = QPointF(0, 0)
        self.entries = entries
        if self.entries: # could be destructing
            for emotion in self.entries:
                # retain selected color while still calculating new color
                emotion.updatePen()
            self.animationGroup.start()
        self.updateGeometry()
        
    def currentOffsetFor(self, emotion):
        if emotion in self.entries:
            entry = self.entries[emotion]
            beginPosDelta = entry['beginPosDelta']
            endPosDelta = entry['endPosDelta']
            delta = (endPosDelta - beginPosDelta) * self.animationGroup.currentTick()
            return beginPosDelta + delta
        else:
            return QPointF(0, 0)

    def updateOffsets(self):
        """ Called on anim tick and person move. """
        if not self.entries:
            return
        firstPersonA = list(self.entries.keys())[0].personA()
        for emotion, entry in self.entries.items():
            entry['endPosDelta'] = self.endPosDeltaFor(emotion)

    def endPosDeltaFor(self, emotion):
        if emotion in self._toRemoveAfterAnim:
            return QPointF(0, 0)
        firstPersonA = list(self.emotions)[0].personA()
        if emotion in self.entries:
            alt = self.entries[emotion]['alt']
            if alt is None:
                alt = 1.0
        else:
            for _emotion, alt in self._steps():
                if _emotion is emotion:
                    break
        if emotion.personA() != firstPersonA:
            # entries where the person order is backwards need to be moved in reverse direction
            alt *= -1
        jig = self.jigFor(emotion)
        endPos = (jig.p1 - jig.aP) * alt * self.SCALE
        return endPos

    def onAnimationTick(self):
        self.updateOffsets()
        for emotion in self.entries:
            emotion.updateGeometry()
        self.updateGeometry()

    def onAnimationFinished(self):
        # This makes it so the only ones left in self.entries are currently visible.
        for emotion in self._toRemoveAfterAnim:
            if emotion in self.entries:
                del self.entries[emotion]
                emotion.fannedBox = None
        self._toRemoveAfterAnim = []
            

def _new_color():
    colorName = random.choice(util.ABLETON_COLORS)
    color = QColor(colorName)
    # color.setAlpha(150)
    return color.name()






def pathFor_Conflict(personA, personB=None, pointB=None, withClip=False, intensity=1, **kwargs):
    path = QPainterPath()
    size = util.sizeForPeople(personA, personB)
    scale = util.scaleForPersonSize(size)
    width = Jig.WIDTH * scale
    step = Jig.STEP * scale
    main = Jig(personA, personB, pointB, step=step, width=width)
    for jig in main.divideBy(intensity):
        x = QPainterPath()
        x.moveTo(jig.p4)
        for p in jig.alternatingPoints():
            x.lineTo(p)
        path.addPath(x)
    return path


def pathFor_Projection(personA, personB=None, pointB=None, intensity=1, **kwargs):
    size = util.sizeForPeople(personA, personB)
    scale = util.scaleForPersonSize(size)
    width = Jig.WIDTH * scale
    jig = Jig(personA, personB, pointB, width=width)
    path = QPainterPath()
    if intensity == 1:
        path.moveTo(jig.aP)
        path.lineTo(jig.bP)
    elif intensity == 2:
        length = QLineF(jig.aP, jig.bP).length()
        stop = CUtil.pointOnRay(jig.aP, jig.bP, length - jig.width * 1.5)
        p1a = CUtil.perpendicular(jig.aP, stop, jig.width / 4.0)
        p2a = CUtil.perpendicular(jig.aP, stop, jig.width / 4.0, True)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(stop, jig.aP, jig.width / 4.0)
        p4a = CUtil.perpendicular(stop, jig.aP, jig.width / 4.0, True)
        path.moveTo(p3a)
        path.lineTo(p4a)
    elif intensity == 3:
        length = QLineF(jig.aP, jig.bP).length()
        stop = CUtil.pointOnRay(jig.aP, jig.bP, length - jig.width * 1.5)
        path.moveTo(jig.aP)
        path.lineTo(stop)
        p1a = CUtil.perpendicular(jig.aP, stop, jig.width / 2.0)
        p2a = CUtil.perpendicular(jig.aP, stop, jig.width / 2.0, True)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(stop, jig.aP, jig.width / 2.0)
        p4a = CUtil.perpendicular(stop, jig.aP, jig.width / 2.0, True)
        path.moveTo(p3a)
        path.lineTo(p4a)
    # arrow head
    p1 = CUtil.pointOnRay(jig.p2, jig.p1, jig.width)
    p2 = CUtil.pointOnRay(jig.p3, jig.p4, jig.width)
    path.moveTo(jig.bP)
    path.lineTo(p1)
    path.moveTo(jig.bP)
    path.lineTo(p2)
    return path


def pathFor_Distance(personA, personB=None, pointB=None, intensity=1, **kwargs):
    """ The orginal one, drawn like ---| |--- """
    size = util.sizeForPeople(personA, personB)
    scale = util.scaleForPersonSize(size)
    width = Jig.WIDTH * scale
    jig = Jig(personA, personB, pointB, width=width)
    path = QPainterPath()
    gap = jig.width * 1.5
    rightMidStop = CUtil.pointOnRay(jig.aP, jig.bP, QLineF(jig.aP, jig.bP).length() * .5 - gap)
    if intensity == 1:
        path.moveTo(rightMidStop)
        path.lineTo(jig.aP)
    elif intensity == 2:
        p1a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 4.0)
        p2a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 4.0, True)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 4.0, True)
        p4a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 4.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    elif intensity == 3:
        path.moveTo(rightMidStop)
        path.lineTo(jig.aP)
        p1a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 2.0)
        p2a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 2.0, True)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 2.0, True)
        p4a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 2.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    totalLength = QLineF(jig.aP, jig.bP).length()
    # right cross T
    cp1 = CUtil.perpendicular(jig.aP, rightMidStop, jig.width)
    cp2 = CUtil.perpendicular(rightMidStop, jig.aP, jig.width, True)
    path.moveTo(cp1)
    path.lineTo(cp2)       
    leftMidStop = CUtil.pointOnRay(jig.bP, jig.aP, QLineF(jig.aP, jig.bP).length() * .5 - gap)
    if intensity == 1:
        path.moveTo(leftMidStop)
        path.lineTo(jig.bP)
    elif intensity == 2:
        p1a = CUtil.perpendicular(leftMidStop, jig.bP, jig.width / 4.0)
        p2a = CUtil.perpendicular(leftMidStop, jig.bP, jig.width / 4.0, True)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.bP, leftMidStop, jig.width / 4.0, True)
        p4a = CUtil.perpendicular(jig.bP, leftMidStop, jig.width / 4.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    elif intensity == 3:
        path.moveTo(leftMidStop)
        path.lineTo(jig.bP)
        p1a = CUtil.perpendicular(leftMidStop, jig.bP, jig.width / 2.0)
        p2a = CUtil.perpendicular(leftMidStop, jig.bP, jig.width / 2.0, True)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.bP, leftMidStop, jig.width / 2.0, True)
        p4a = CUtil.perpendicular(jig.bP, leftMidStop, jig.width / 2.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    # left cross T
    cp3 = CUtil.perpendicular(jig.bP, leftMidStop, jig.width)
    cp4 = CUtil.perpendicular(leftMidStop, jig.bP, jig.width, True)
    path.moveTo(cp3)
    path.lineTo(cp4)       
    return path


def pathFor_Curvey(personA, personB=None, pointB=None, intensity=1, **kwargs):
    """ The old curvey version of fusion.
    use same control points as Conflict. """
    path = QPainterPath()
    size = util.sizeForPeople(personA, personB)
    scale = util.scaleForPersonSize(size)
    width = Jig.WIDTH * scale
    step = (Jig.STEP * 1.9) * scale
    main = Jig(personA, personB, pointB, step=step, width=width)
    for jig in main.divideBy(intensity):
        points = jig.alternatingPoints()
        ret = CUtil.splineFromPoints(points)
        path.addPath(ret)            
    return path


def pathFor_Fusion(personA, personB=None, pointB=None, intensity=1, **kwargs):
    """ use same control points as Conflict """
    path = QPainterPath()
    size = util.sizeForPeople(personA, personB)
    scale = util.scaleForPersonSize(size)
    width = Jig.WIDTH * scale
    main = Jig(personA, personB, pointB, width=width)
    for jig in main.divideBy(intensity+1):
        path.moveTo(jig.aP)
        path.lineTo(jig.bP)
    return path



def pathFor_Cutoff(personA=None, personB=None, pointB=None, intensity=1, **kwargs):
    # person = personA
    path = QPainterPath()
    spread = deg1 = 150
    deg2 = 90 - (spread / 2)
    rect = QRectF(util.PERSON_RECT)
    if pointB:
        rect.moveCenter(pointB)
    # # Calc angles for p0 < person.pos < p1
    # # Assumes siblings are within x-y bounds of parents.
    # if person.parents() and not None in person.parents().people:
    #     MARGIN = 15
    #     parents = person.parents().people
    #     p0 = parents[0].pos()
    #     p1 = parents[1].pos()
    #     if parents[1].x() < parents[0].x():
    #         p0, p1 = p1, p0
    #     adj = abs(person.pos().x() - p0.x())
    #     opp = abs(person.pos().y() - p0.y())
    #     hyp = (person.pos() - p0).manhattanLength()
    #     deg1 = 180 - deg2 - (math.degrees(math.asin(opp / hyp)) + MARGIN)
    #     #
    #     adj = abs(p1.x() - person.pos().x())
    #     opp = abs(person.pos().y() - p1.y())
    #     hyp = (p1 - person.pos()).manhattanLength()
    #     deg2 = math.degrees(math.asin(opp / hyp)) - MARGIN
    w = rect.width() *.25
    rect = rect.marginsAdded(QMarginsF(w, w, w, w))
    rect.setHeight(rect.height() / 2)
    if personA:
        if personA.gender() == 'male':
            rect.moveCenter(rect.center() + QPointF(0, -w * .5)) # slight nudge up
        if personA.primary():
            rect.moveCenter(rect.center() + QPointF(0, -w * .5)) # another slight nudge up
    path.arcMoveTo(rect, deg2)
    path.arcTo(rect, deg2, deg1)
    return path


def pathFor_Away(personA, personB=None, pointB=None, intensity=1, **kwargs):
    """  |<-- --->  """
    size = util.sizeForPeople(personA, personB)
    width = Jig.WIDTH * util.scaleForPersonSize(size)
    jig = Jig(personA, personB, pointB, width=width)
    path = QPainterPath()
    gap = jig.width * 1.5

    # Mover (Person A)
    rightMidStop = CUtil.pointOnRay(jig.aP, jig.bP, QLineF(jig.aP, jig.bP).length() * .5 - gap)
    # right arrow line(s)
    if intensity == 1:
        path.moveTo(rightMidStop)
        path.lineTo(jig.aP)
    elif intensity == 2:
        rightArrowStop = CUtil.pointOnRay(jig.aP, jig.bP, gap)
        p1a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 4.0)
        p2a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 4.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 4.0, True)
        p4a = CUtil.perpendicular(rightArrowStop, jig.aP, jig.width / 4.0, True)
        path.moveTo(p3a)
        path.lineTo(p4a)
    elif intensity == 3:
        rightArrowStop = CUtil.pointOnRay(jig.aP, jig.bP, gap)
        path.moveTo(rightMidStop)
        path.lineTo(rightArrowStop)
        p1a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 2.0)
        p2a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 2.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 2.0, True)
        p4a = CUtil.perpendicular(rightArrowStop, jig.aP, jig.width / 2.0, True)
        path.moveTo(p3a)
        path.lineTo(p4a)
    # Mover arrow head
    p1 = CUtil.pointOnRay(jig.p1, jig.p2, jig.width)
    p2 = CUtil.pointOnRay(jig.p4, jig.p3, jig.width)
    path.moveTo(jig.aP)
    path.lineTo(p1)
    path.moveTo(jig.aP)
    path.lineTo(p2)

    # Recipient (Person B)
    leftMidStop = CUtil.pointOnRay(jig.bP, jig.aP, QLineF(jig.aP, jig.bP).length() * .5 - gap)
    # Recipient line
    path.moveTo(leftMidStop)
    path.lineTo(jig.bP)

    return path


def pathFor_Toward(personA, personB=None, pointB=None, intensity=1, **kwargs):
    """ |--> <--- """
    size = util.sizeForPeople(personA, personB)
    width = Jig.WIDTH * util.scaleForPersonSize(size)
    jig = Jig(personA, personB, pointB, width=width)
    path = QPainterPath()
    gap = jig.width * 1.5
    
    # Mover (Person A)
    rightArrowPoint = CUtil.pointOnRay(jig.aP, jig.bP, QLineF(jig.aP, jig.bP).length() * .5 - gap)
    # Mover arrow line(s)
    if intensity == 1:
        rightArrowStop = CUtil.pointOnRay(jig.aP, jig.bP, QLineF(jig.aP, jig.bP).length() * .5 - gap)
        path.moveTo(rightArrowStop)
        path.lineTo(jig.aP)
    elif intensity == 2:
        rightArrowStop = CUtil.pointOnRay(jig.aP, jig.bP, QLineF(jig.aP, jig.bP).length() * .5 - gap * 2.2)
        p1a = CUtil.perpendicular(rightArrowPoint, rightArrowStop, jig.width / 4.0)
        p2a = CUtil.perpendicular(rightArrowPoint, jig.aP, jig.width / 4.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 4.0, True)
        p4a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 4.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    elif intensity == 3:
        rightArrowStop = CUtil.pointOnRay(jig.aP, jig.bP, QLineF(jig.aP, jig.bP).length() * .5 - gap * 2.2)
        path.moveTo(jig.aP)
        path.lineTo(rightArrowStop)
        p1a = CUtil.perpendicular(rightArrowPoint, rightArrowStop, jig.width / 2.0)
        p2a = CUtil.perpendicular(rightArrowPoint, jig.aP, jig.width / 2.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 2.0, True)
        p4a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 2.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    # Mover arrow head
    ap1 = CUtil.pointOnRay(jig.p1, jig.p2, QLineF(jig.aP, jig.bP).length() * .5 - gap * 2)
    ap2 = CUtil.pointOnRay(jig.p4, jig.p3, QLineF(jig.aP, jig.bP).length() * .5 - gap * 2)
    path.moveTo(rightArrowPoint)
    path.lineTo(ap1)
    path.moveTo(rightArrowPoint)
    path.lineTo(ap2)   

    # Recipient (Person B)
    leftArrowPoint = CUtil.pointOnRay(jig.bP, jig.aP, QLineF(jig.bP, jig.aP).length() * .5 - gap)
    leftArrowStop = CUtil.pointOnRay(jig.bP, jig.aP, QLineF(jig.bP, jig.aP).length() * .5 - gap * 2)
    # Recipient line
    path.moveTo(leftArrowPoint)
    path.lineTo(jig.bP)

    return path


def pathFor_DefinedSelf(personA, personB=None, pointB=None, intensity=1, **kwargs):
    size = util.sizeForPeople(personA, personB)
    width = Jig.WIDTH * util.scaleForPersonSize(size)
    jig = Jig(personA, personB, pointB, width=width)
    path = QPainterPath()
    gap = jig.width * 1.5

    rightMidStop = CUtil.pointOnRay(jig.aP, jig.bP, QLineF(jig.aP, jig.bP).length() * .5 - gap)
    if intensity == 1:
        path.moveTo(rightMidStop)
        path.lineTo(jig.aP)
    elif intensity == 2:
        p1a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 4.0)
        p2a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 4.0, True)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 4.0, True)
        p4a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 4.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    elif intensity == 3:
        path.moveTo(rightMidStop)
        path.lineTo(jig.aP)
        p1a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 2.0)
        p2a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 2.0, True)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 2.0, True)
        p4a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 2.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    totalLength = QLineF(jig.aP, jig.bP).length()
    # right cross T
    cp1 = CUtil.perpendicular(jig.aP, rightMidStop, jig.width)
    cp2 = CUtil.perpendicular(rightMidStop, jig.aP, jig.width, True)
    path.moveTo(cp1)
    path.lineTo(cp2)       

    leftArrowPoint = CUtil.pointOnRay(jig.bP, jig.aP, QLineF(jig.bP, jig.aP).length() * .5 - gap)
    # left arrow line(s)
    if intensity == 1:
        path.moveTo(leftArrowPoint)
        path.lineTo(jig.bP)
    elif intensity == 2:
        leftArrowStop = CUtil.pointOnRay(jig.bP, jig.aP, QLineF(jig.bP, jig.aP).length() * .5 - gap * 2.2)
        p1a = CUtil.perpendicular(leftArrowPoint, leftArrowStop, jig.width / 4.0)
        p2a = CUtil.perpendicular(leftArrowPoint, jig.bP, jig.width / 4.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.bP, leftArrowStop, jig.width / 4.0, True)
        p4a = CUtil.perpendicular(jig.bP, leftArrowStop, jig.width / 4.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    elif intensity == 3:
        leftArrowStop = CUtil.pointOnRay(jig.bP, jig.aP, QLineF(jig.bP, jig.aP).length() * .5 - gap * 2.2)
        path.moveTo(jig.bP)
        path.lineTo(leftArrowStop)
        p1a = CUtil.perpendicular(leftArrowPoint, leftArrowStop, jig.width / 2.0)
        p2a = CUtil.perpendicular(leftArrowPoint, jig.bP, jig.width / 2.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.bP, leftArrowStop, jig.width / 2.0, True)
        p4a = CUtil.perpendicular(jig.bP, leftArrowStop, jig.width / 2.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    # # left arrow head
    # ap1 = CUtil.pointOnRay(jig.p2, jig.p1, QLineF(jig.bP, jig.aP).length() * .5 - gap * 2)
    # ap2 = CUtil.pointOnRay(jig.p3, jig.p4, QLineF(jig.bP, jig.aP).length() * .5 - gap * 2)
    # path.moveTo(leftArrowPoint)
    # path.lineTo(ap1)
    # path.moveTo(leftArrowPoint)
    # path.lineTo(ap2)

    return path


def pathFor_Inside(personA, personB=None, pointB=None, intensity=1, **kwargs):
    """  ---> <---  """
    size = util.sizeForPeople(personA, personB)
    width = Jig.WIDTH * util.scaleForPersonSize(size)
    jig = Jig(personA, personB, pointB, width=width)
    path = QPainterPath()
    gap = jig.width * 1.5
    rightArrowPoint = CUtil.pointOnRay(jig.aP, jig.bP, QLineF(jig.aP, jig.bP).length() * .5 - gap)
    rightArrowStop = CUtil.pointOnRay(jig.aP, jig.bP, QLineF(jig.aP, jig.bP).length() * .5 - gap * 2)
    # right arrow line(s)
    if intensity == 1:
        path.moveTo(rightArrowStop)
        path.lineTo(jig.aP)
    elif intensity == 2:
        p1a = CUtil.perpendicular(rightArrowPoint, rightArrowStop, jig.width / 4.0)
        p2a = CUtil.perpendicular(rightArrowPoint, jig.aP, jig.width / 4.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 4.0, True)
        p4a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 4.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    elif intensity == 3:
        path.moveTo(jig.aP)
        path.lineTo(rightArrowStop)
        p1a = CUtil.perpendicular(rightArrowPoint, rightArrowStop, jig.width / 2.0)
        p2a = CUtil.perpendicular(rightArrowPoint, jig.aP, jig.width / 2.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 2.0, True)
        p4a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 2.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    # right arrow head
    ap1 = CUtil.pointOnRay(jig.p1, jig.p2, QLineF(jig.aP, jig.bP).length() * .5 - gap * 2)
    ap2 = CUtil.pointOnRay(jig.p4, jig.p3, QLineF(jig.aP, jig.bP).length() * .5 - gap * 2)
    path.moveTo(rightArrowPoint)
    path.lineTo(ap1)
    path.moveTo(rightArrowPoint)
    path.lineTo(ap2)

    leftArrowPoint = CUtil.pointOnRay(jig.bP, jig.aP, QLineF(jig.bP, jig.aP).length() * .5 - gap)
    leftArrowStop = CUtil.pointOnRay(jig.bP, jig.aP, QLineF(jig.bP, jig.aP).length() * .5 - gap * 2)
    # left arrow line(s)
    if intensity == 1:
        path.moveTo(leftArrowPoint)
        path.lineTo(jig.bP)
    elif intensity == 2:
        p1a = CUtil.perpendicular(leftArrowPoint, leftArrowStop, jig.width / 4.0)
        p2a = CUtil.perpendicular(leftArrowPoint, jig.bP, jig.width / 4.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.bP, leftArrowStop, jig.width / 4.0, True)
        p4a = CUtil.perpendicular(jig.bP, leftArrowStop, jig.width / 4.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    elif intensity == 3:
        path.moveTo(jig.bP)
        path.lineTo(leftArrowStop)
        p1a = CUtil.perpendicular(leftArrowPoint, leftArrowStop, jig.width / 2.0)
        p2a = CUtil.perpendicular(leftArrowPoint, jig.bP, jig.width / 2.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(jig.bP, leftArrowStop, jig.width / 2.0, True)
        p4a = CUtil.perpendicular(jig.bP, leftArrowStop, jig.width / 2.0)
        path.moveTo(p3a)
        path.lineTo(p4a)
    # left arrow head
    ap1 = CUtil.pointOnRay(jig.p2, jig.p1, QLineF(jig.bP, jig.aP).length() * .5 - gap * 2)
    ap2 = CUtil.pointOnRay(jig.p3, jig.p4, QLineF(jig.bP, jig.aP).length() * .5 - gap * 2)
    path.moveTo(leftArrowPoint)
    path.lineTo(ap1)
    path.moveTo(leftArrowPoint)
    path.lineTo(ap2)

    return path


def pathFor_Outside(personA, personB=None, pointB=None, intensity=1, **kwargs):
    """  <--- --->  """
    size = util.sizeForPeople(personA, personB)
    width = Jig.WIDTH * util.scaleForPersonSize(size)
    jig = Jig(personA, personB, pointB, width=width)
    path = QPainterPath()
    gap = jig.width * 1.5
    rightMidStop = CUtil.pointOnRay(jig.aP, jig.bP, QLineF(jig.aP, jig.bP).length() * .5 - gap)
    # right arrow line(s)
    if intensity == 1:
        path.moveTo(rightMidStop)
        path.lineTo(jig.aP)
    elif intensity == 2:
        rightArrowStop = CUtil.pointOnRay(jig.aP, jig.bP, gap)
        p1a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 4.0)
        p2a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 4.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 4.0, True)
        p4a = CUtil.perpendicular(rightArrowStop, jig.aP, jig.width / 4.0, True)
        path.moveTo(p3a)
        path.lineTo(p4a)
    elif intensity == 3:
        rightArrowStop = CUtil.pointOnRay(jig.aP, jig.bP, gap)
        path.moveTo(rightMidStop)
        path.lineTo(rightArrowStop)
        p1a = CUtil.perpendicular(jig.aP, rightMidStop, jig.width / 2.0)
        p2a = CUtil.perpendicular(jig.aP, rightArrowStop, jig.width / 2.0)
        path.moveTo(p1a)
        path.lineTo(p2a)
        p3a = CUtil.perpendicular(rightMidStop, jig.aP, jig.width / 2.0, True)
        p4a = CUtil.perpendicular(rightArrowStop, jig.aP, jig.width / 2.0, True)
        path.moveTo(p3a)
        path.lineTo(p4a)
    # right arrow head
    p1 = CUtil.pointOnRay(jig.p1, jig.p2, jig.width)
    p2 = CUtil.pointOnRay(jig.p4, jig.p3, jig.width)
    path.moveTo(jig.aP)
    path.lineTo(p1)
    path.moveTo(jig.aP)
    path.lineTo(p2)

    leftMidStop = CUtil.pointOnRay(jig.bP, jig.aP, QLineF(jig.aP, jig.bP).length() * .5 - gap)
    # left arrow line
    if intensity == 1:
        path.moveTo(leftMidStop)
        path.lineTo(jig.bP)
    elif intensity == 2:
        leftArrowStop = CUtil.pointOnRay(jig.bP, jig.aP, gap)
        p1b = CUtil.perpendicular(jig.bP, leftMidStop, jig.width / 4.0)
        p2b = CUtil.perpendicular(jig.bP, leftArrowStop, jig.width / 4.0)
        path.moveTo(p1b)
        path.lineTo(p2b)
        p3b = CUtil.perpendicular(leftMidStop, jig.bP, jig.width / 4.0, True)
        p4b = CUtil.perpendicular(leftArrowStop, jig.bP, jig.width / 4.0, True)
        path.moveTo(p3b)
        path.lineTo(p4b)
    elif intensity == 3:
        leftArrowStop = CUtil.pointOnRay(jig.bP, jig.aP, gap)
        path.moveTo(leftMidStop)
        path.lineTo(leftArrowStop)
        p1b = CUtil.perpendicular(jig.bP, leftMidStop, jig.width / 2.0)
        p2b = CUtil.perpendicular(jig.bP, leftArrowStop, jig.width / 2.0)
        path.moveTo(p1b)
        path.lineTo(p2b)
        p3b = CUtil.perpendicular(leftMidStop, jig.bP, jig.width / 2.0, True)
        p4b = CUtil.perpendicular(leftArrowStop, jig.bP, jig.width / 2.0, True)
        path.moveTo(p3b)
        path.lineTo(p4b)
    # arrow head
    p1 = CUtil.pointOnRay(jig.p2, jig.p1, jig.width)
    p2 = CUtil.pointOnRay(jig.p3, jig.p4, jig.width)
    path.moveTo(jig.bP)
    path.lineTo(p1)
    path.moveTo(jig.bP)
    path.lineTo(p2)
    return path


def pathFor_Reciprocity(personA, personB=None, pointB=None, intensity=1,
                        hoverPerson=None, **kwargs):
    path = QPainterPath()

    # drawing drag line
    if personB is None:
        path.moveTo(personA.pos())
        path.lineTo(pointB)
        if hoverPerson is None or hoverPerson is personA:
            # show drag line + show up-arrow on personA
            pass
        else:
            # show drag line + show up-arrow on personA + show down-arrow when hovering over other person
            personB = hoverPerson

    personARect = util.personRectForSize(personA.size())
    if personB:
        personBRect = util.personRectForSize(personB.size())
    else:
        personBRect = personARect
    size = util.sizeForPeople(personA, personB)
    scale = util.scaleForPersonSize(size)
    armH = 15 * scale
    armW = 15 * scale
 
    # Determine which side of each person to draw the arrows on.
    if personB is None or personA.x() < personB.x():
        leftPerson, rightPerson = personA, personB
    else:
        leftPerson, rightPerson = personB, personA

    nudge = .9
    if personA is leftPerson:
        personAXDelta = -personARect.width() * nudge
        personBXDelta = personBRect.width() * nudge
    else:
        personAXDelta = personARect.width() * nudge
        personBXDelta = -personBRect.width() * nudge

    # personA is always the higher functioning person.
    size = personA.size()
    scale = util.scaleForPersonSize(size)
    armH = 15 * scale
    armW = 15 * scale
    h = personARect.height() * .5 # arrow height
    upArrow = QPainterPath()
    upArrow.moveTo(0, h) # below center
    upArrow.lineTo(0, 0) # top of arrow point
    upArrow.lineTo(-armW, armH)
    upArrow.moveTo(0, 0)
    upArrow.lineTo(armW, armH)
    personACenter = personA.mapToScene(personA.boundingRect().center())
    upArrow.translate(personACenter + QPointF(personAXDelta, -h))
    path.addPath(upArrow)

    if personB is not None:
        size = personB.size()
        scale = util.scaleForPersonSize(size)
        armH = 15 * scale
        armW = 15 * scale
        h = personBRect.height() * .5 # arrow height
        
        downArrow = QPainterPath()
        downArrow.moveTo(0, -h) # above center, for easier math below
        downArrow.lineTo(0, 0) # bottom of arrow point, at scene center
        downArrow.lineTo(armW, -armH)
        downArrow.moveTo(0, 0)
        downArrow.lineTo(-armW, -armH)
        downArrow.translate(0, h)
        personBCenter = personB.mapToScene(personB.boundingRect().center())
        downArrow.translate(personBCenter + QPointF(personBXDelta, -h))
        path.addPath(downArrow)
    
    return path



class Emotion(PathItem):

    personAChanged = pyqtSignal(int)
    personBChanged = pyqtSignal(int)

    UNDER_PEN = QColor(100, 100, 100, 50)

    PathItem.registerProperties([
        { 'attr': 'kind', 'type': int, 'default': -1, 'onset': 'updateGeometry' },
        { 'attr': 'intensity', 'type': int, 'default': util.DEFAULT_EMOTION_INTENSITY, 'onset': 'updateGeometry' },
        { 'attr': 'parentName' },
        { 'attr': 'color', 'default': _new_color() },
        { 'attr': 'isDateRange', 'type': bool, 'default': False },
        { 'attr': 'notes' }
    ])

    ITEM_MAP = collections.OrderedDict([
        (util.ITEM_CONFLICT, {
            'pathFunc': pathFor_Conflict,
            'label': 'Conflict',
            'slug': 'Conflict'
        }),
        (util.ITEM_DISTANCE, {
            'pathFunc': pathFor_Distance,
            'label': 'Distance',
            'slug': 'Distance'
        }),
        (util.ITEM_RECIPROCITY, {
            'pathFunc': pathFor_Reciprocity,
            'label': 'Reciprocity',
            'slug': 'Reciprocity'
        }),
        (util.ITEM_PROJECTION, {
            'pathFunc': pathFor_Projection,
            'label': 'Projection',
            'slug': 'Projection'
        }),
        (util.ITEM_FUSION, {
            'pathFunc': pathFor_Fusion,
            'label': 'Fusion',
            'slug': 'Fusion'
        }),
        (util.ITEM_CUTOFF, {
            'pathFunc': pathFor_Cutoff,
            'label': 'Cutoff',
            'slug': 'Cutoff'
        }),
        (util.ITEM_DEFINED_SELF, {
            'pathFunc': pathFor_DefinedSelf,
            'label': 'Defined Self',
            'slug': 'DefinedSelf'
        }),
        (util.ITEM_AWAY, {
            'pathFunc': pathFor_Away,
            'label': 'Away',
            'slug': 'Away'
        }),
        (util.ITEM_TOWARD, {
            'pathFunc': pathFor_Toward,
            'label': 'Toward',
            'slug': 'Toward'
        }),
        (util.ITEM_INSIDE, {
            'pathFunc': pathFor_Inside,
            'label': 'Inside',
            'slug': 'Inside'
        }),
        (util.ITEM_OUTSIDE, {
            'pathFunc': pathFor_Outside,
            'label': 'Outside',
            'slug': 'Outside'
        }),
    ])

    @staticmethod
    def kinds():
        return list(Emotion.ITEM_MAP.keys())

    @staticmethod
    def kindSlugs():
        return [entry['slug'] for kind, entry in Emotion.ITEM_MAP.items()]

    @staticmethod
    def kindLabels():
        return [entry['label'] for kind, entry in Emotion.ITEM_MAP.items()]

    @staticmethod
    def kindForKindSlug(slug):
        for kind, entry in Emotion.ITEM_MAP.items():
            if slug == entry['slug']:
                return kind

    @staticmethod
    def kindSlugForKind(kind):
        return Emotion.ITEM_MAP[kind]['slug']

    @staticmethod
    def kindLabelForKind(kind):
        return Emotion.ITEM_MAP[kind]['label']

    @staticmethod
    def pathFor(kind, *args, **kwargs):
        if not kind in Emotion.ITEM_MAP:
            return QPainterPath()
        entry = Emotion.ITEM_MAP.get(kind)
        return entry['pathFunc'](*args, **kwargs)

    ITEM_Z = util.EMOTION_Z

    def __init__(self, personA=None, personB=None, addDummy=False, **kwargs):
        super().__init__(**kwargs)
        self.isInit = False
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.prop('itemPos').setLayered(False)
        self.isEmotion = True
        self.isCreating = False # don't hide if not initially part of selected scenetags
        self._aliasNotes = None
        self._aliasParentName = None
        self._onShowAliases = False
        self.addDummy = addDummy
        self.people = [personA, personB]
        self.startEvent = Event(self, uniqueId='emotionStartEvent')
        self.endEvent = Event(self, uniqueId='emotionEndEvent')
        # self.hoverTimer = QTimer(self)
        # self.hoverTimer.setInterval(500)
        # self.hoverTimer.timeout.connect(self.onHoverTimer)
        self.fannedBox = None
        self.isLatest = True
        self.onPeopleChanged()
        if self.people[0]:
            self.people[0]._onAddEmotion(self)
        if self.people[1]:
            self.people[1]._onAddEmotion(self)
        if not self.isDyadic() and personA:
            self.setParentItem(personA)
        self.isInit = True
        if 'startDateTime' in kwargs:
            self.startEvent.setDateTime(kwargs['startDateTime'])
            self.startEvent.updateDescription()
        if 'endDateTime' in kwargs:
            self.endEvent.setDateTime(kwargs['endDateTime'])
            self.endEvent.updateDescription()
        if self.prop('loggedDateTime').isset():
            self.startEvent.setLoggedDateTime(self.loggedDateTime())
            self.endEvent.setLoggedDateTime(self.loggedDateTime())

    def __repr__(self, exclude=[]):
        """ Forked from Item.__repr___(). """
        if not isinstance(exclude, list):
            exclude = [exclude]
        if not 'id' in exclude:
            exclude.append('id')
        exclude.append('kind')
        props = {
            'kindLabel': self.kindLabel()
        }
        for prop in self.props:
            if not prop.layered and prop.get() != prop.default:
                props[prop.attr] = prop.get()
        s = util.pretty(props, exclude=exclude)
        if s:
            s = ': ' + s
        return '<%s[%s]%s>' % (self.__class__.__name__, self.id, s)

    def __lt__(self, other):
        if other.isEvent:
            return False
        elif self.startDateTime() and not other.startDateTime():
            return True
        elif not self.startDateTime() and other.startDateTime():
            return False
        elif self.startDateTime() and other.startDateTime():
            return self.startDateTime() < other.startDateTime()
        elif not self.startDateTime() and not other.startDateTime():
            if self.id and not other.id:
                return True
            elif not self.id and other.id:
                return False
            elif not self.id and not other.id:
                return True
            else:
                return self.id < other.id

    def events(self):
        return [self.startEvent, self.endEvent]

    def startDateTime(self):
        """ Backwards compat """
        return self.startEvent.dateTime()

    def endDateTime(self):
        """ Backwards compat """
        return self.endEvent.dateTime()

    def onEventProperty(self, prop):
        if prop.name() == 'dateTime':
            if not self.prop('isDateRange').get() and prop.item == self.startEvent:
                self.endEvent.setDateTime(prop.get())
            self.startEvent.updateDescription()
            self.endEvent.updateDescription()

    def isDyadic(self):
        return self.kind() != util.ITEM_CUTOFF

    def canFanOut(self):
        return self.kind() not in (util.ITEM_CUTOFF, util.ITEM_RECIPROCITY)
    
    def shouldShowAliases(self):
        scene = self.scene()
        return scene and scene.shouldShowAliases()

    def isSingularDate(self):
        """ Dates are the same. """
        return self.startEvent.dateTime() and self.endEvent.dateTime() and self.startEvent.dateTime() == self.endEvent.dateTime()

    def kindLabel(self):
        return self.kindLabelForKind(self.kind())

    @util.fblocked
    def updateNotes(self):
        """ Force re-write of aliases. """
        prop = self.prop('notes')
        notes = prop.get()
        if notes is not None:
            self._aliasNotes = self.scene().anonymize(notes)
        else:
            self._aliasNotes = None

    def notes(self):
        if self.shouldShowAliases():
            if self._aliasNotes is None and self.prop('notes').get(): # first time
                self.updateNotes()
            return self._aliasNotes
        else:
            return self.prop('notes').get()

    def notesIconPos(self):
        if self.kind() in (util.ITEM_CONFLICT, util.ITEM_DISTANCE,
                           util.ITEM_RECIPROCITY, util.ITEM_PROJECTION,
                           util.ITEM_FUSION, util.ITEM_AWAY, util.ITEM_TOWARD):
            return QPointF(0, self._notesIcon.boundingRect().height() * -.25)
        else:
            return super().notesIconPos()

    def parentName(self):
        if self.shouldShowAliases():
            if self._aliasParentName is None and self.prop('parentName').get(): # first time
                self.updateParentName()
            return self._aliasParentName
        else:
            return self.prop('parentName').get()

    def updateParentName(self):
        prop = self.prop('parentName')
        newParentName = None
        if self.isDyadic():
            personAName = (self.personA() and self.personA().name()) and self.personA().name() or 'Unnamed'
            personBName = (self.personB() and self.personB().name()) and self.personB().name() or 'Unnamed'
            if (personAName, personBName) != (None, None):
                if self.kind() == util.ITEM_TOWARD:
                    newParentName = '%s to %s' % (personAName,
                                                personBName)
                elif self.kind() == util.ITEM_AWAY:
                    newParentName = '%s from %s' % (personAName,
                                                personBName)
                else:
                    newParentName = '%s & %s' % (personAName,
                                                personBName)
        else:
            if self.personA() is not None:
                newParentName = self.personA().name()
        if newParentName != prop.get():
            prop.set(newParentName, notify=False)
        if prop.get() is not None and self.scene():
            self._aliasParentName = self.scene().anonymize(prop.get())
        else:
            self._aliasParentName = None
        self.startEvent.updateParentName()
        self.endEvent.updateParentName()

    def onShowAliases(self):
        self._onShowAliases = True
        prop = self.prop('notes')
        if prop.get() != self._aliasNotes:
            self.onProperty(prop)
        prop = self.prop('parentName')
        if prop.get() != self._aliasParentName:
            self.onProperty(prop)
        self._onShowAliases = False

    ## Data

    def write(self, chunk):
        super().write(chunk)
        chunk['kind'] = Emotion.kindSlugForKind(self.kind())
        chunk['startEvent'] = {}
        self.startEvent.write(chunk['startEvent'])
        chunk['endEvent'] = {}
        self.endEvent.write(chunk['endEvent'])
        if self.people[0]: # when adding from dialog, dummy write
            chunk['person_a'] = self.people[0].id
        else:
            chunk['person_a'] = None
        if self.people[1]:
            chunk['person_b'] = self.people[1].id
        else:
            chunk['person_b'] = None

    def read(self, chunk, byId):
        chunk['kind'] = Emotion.kindForKindSlug(chunk['kind'])
        super().read(chunk, byId)
        self.startEvent.read(chunk.get('startEvent', {}), byId)
        self.endEvent.read(chunk.get('endEvent', {}), byId)
        self.people = [
            byId(chunk.get('person_a', None)),
            byId(chunk.get('person_b', None))
        ]
        if self.people[0]: # when adding from dialog, duymmy write
            self.people[0]._onAddEmotion(self)
        if self.people[1]:
            self.people[1]._onAddEmotion(self)
        self.startEvent.updateParentName()
        self.startEvent.updateDescription()
        self.endEvent.updateParentName()
        self.endEvent.updateDescription()

    ## Cloning

    def clone(self, scene):
        x = super().clone(scene)
        x.startEvent = self.startEvent.clone(scene)
        x.endEvent = self.endEvent.clone(scene)
        if self.isDyadic():
            x._cloned_people_ids = []
            for p in self.people:
                x._cloned_people_ids.append(p.id)
        else:
            x._cloned_person_id = self.people[0].id
        return x

    def remap(self, map):
        self.startEvent.setParent(self)
        self.endEvent.setParent(self)
        if self.isDyadic():
            self.people = [map.find(id) for id in self._cloned_people_ids]
            delattr(self, '_cloned_people_ids')
            return None not in self.people
        else:
            self.people = [map.find(self._cloned_person_id), None]
            self.setParentItem(self.personA())
            delattr(self, '_cloned_person_id')
            return self.people[0] is not None

    ## Scene Events

    def shouldShowFor(self, dateTime, tags=[], layers=[]):
        if self.isSelected(): # sort of an override to prevent prop sheets disappearing, updated in ItemSelectedChange
            return True
        if self.scene().hideEmotionalProcess() is True:
            return False
        for person in self.people:
            if person and person.shouldShowFor(dateTime, tags=tags, layers=layers) is False:
                return False
        if not self.hasTags(tags): # hack
            return False
        on = False
        if not self.startDateTime() and not self.endDateTime():
            on = True
        elif self.startDateTime() and not self.endDateTime():
            on = self.startDateTime() <= dateTime
        elif not self.startDateTime() and self.endDateTime():
            on = self.endDateTime() > dateTime
        elif self.startDateTime() and self.endDateTime():
            if self.startDateTime() == self.endDateTime():
                on = dateTime == self.startDateTime()
            else:
                on = self.startDateTime() <= dateTime and self.endDateTime() > dateTime
        return on

    def updatePathItemVisible(self):
        if not self.scene():
            return
        on = self.shouldShowFor(self.scene().currentDateTime(),
                                tags=self.scene().searchModel.tags,
                                layers=self.scene().activeLayers())
        if not on:
            self.setPathItemVisible(False)
        else:
            opacity = 1.0
            for person in self.people:
                if not person:
                    continue
                o = person.itemOpacity()
                if o is not None and (o > 0 and o < 1.0):
                    opacity = o
            self.setPathItemVisible(True, opacity=opacity)

    def onActiveLayersChanged(self):
        super().onActiveLayersChanged()
        self.updatePen()
        self.updateFannedBox()

    def updatePen(self):
        super().updatePen()
        self.setBrush(Qt.transparent)
        #
        if self.personA() and self.personB():
            size = util.sizeForPeople(self.personA(), self.personB())
        elif self.personA():
            size = self.personA().size()
        #
        pen = QPen(util.PEN)
        # if self.isSelected():
        #     pen.setColor(util.SELECTION_PEN.color())
        # elif self.hover:
        if self.hover:
            pen.setColor(util.HOVER_PEN.color())
        else:
            if not self.scene() or self.scene().hideEmotionColors():
                pen.setColor(util.PEN.color())
            else:
                pen.setColor(QColor(self.color()))
        self.setPen(pen)
        
    def updateGeometry(self):
        """ TODO: Cache path when person positions haven't changed at all during fanning? """
        super().updateGeometry()
        if self.isDyadic() and None in [self.personA(), self.personB()]:
            pass
        elif self.personA() is None:
            pass
        else:
            size = util.sizeForPeople(*self.people)
            scale = util.scaleForPersonSize(size)
            if self.isDyadic():
                self.setScale(scale)
            path = self.pathFor(self.kind(),
                                 personA=self.personA(),
                                 personB=self.personB(), intensity=self.intensity())
            if self.isDyadic(): # cutoff stays @ (0, 0)
                if self.fannedBox:
                    offset = self.fannedBox.currentOffsetFor(self)
                    path.translate(offset)
                sceneCenter = path.controlPointRect().center()
                self.setPos(sceneCenter)
                path = self.mapFromScene(path)
            self.setPath(path)
        self.updateDetails()
        self.updatePen()
        if self.kind() == util.ITEM_CUTOFF:
            self.setPos(0, 0)

    def onUpdateAll(self):
        super().onUpdateAll()
        self.updatePen()
        for peer in self.peers():
            peer.updatePen()

    def itemChange(self, change, variant):
        if change == QGraphicsItem.ItemSceneChange:
            if self.scene():
                self.scene().removeItem(self.startEvent)
                self.scene().removeItem(self.endEvent)
        elif change == QGraphicsItem.ItemSceneHasChanged:
            if self.scene() and not self.isCreating:
                if self.isDyadic() and self.personA() and self.personB():
                    self.onCurrentDateTime()
                elif not self.isDyadic() and self.personA():
                    self.onCurrentDateTime()
            if self.scene():
                self.scene().addItem(self.startEvent)
                self.scene().addItem(self.endEvent)
            if not self.scene() or not self.scene().isBatchAddingRemovingItems():
                self.updateFannedBox()
        elif change == QGraphicsItem.ItemSelectedChange:
            if variant is False:
                self.updateAll() # update after override in shouldShowFor
                # if self.fannedBox:
                #     self.fannedBox.onEmotionDeselected(self)
        return super().itemChange(change, variant)   

    def onPeopleChanged(self):
        was = self.parentName()
        self.updateParentName()
        if was != self.parentName():
            self.onProperty(self.prop('parentName'))
        self.updateGeometry()
        for peer in self.peers():
            peer.updatePen()
        if self.scene(): # defered b/c it's called on the scene
            self.updateFannedBox()

    def peopleNames(self):
        ret = ''
        if not None in self.people:
            name1 = self.people[0].name()
            name2 = self.people[1].name()
            if name1 and name2:
                ret += '%s & %s' % (name1, name2)
            elif name1:
                ret += '%s' % name1
            elif name2:
                ret += '%s' % name2
        return ret

    def peers(self):
        """ Return other visible emotions that have the same people.
            Returns empty list when self is not shown.
        """
        ret = set()
        if self.scene() is None:
            return ret
        if self.personA() is None:
            return ret
        if not self.shouldShowRightNow():
            return ret
        for emotion in self.personA().emotions():
            _canFanOut = emotion.canFanOut()
            _notSelf = emotion is not self
            _samePeople = len(set(emotion.people) & set(self.people)) == len(self.people)
            _shouldShow = emotion.shouldShowRightNow()
            if _canFanOut and _notSelf and _samePeople and _shouldShow and emotion.scene():
                ret.add(emotion)
        return ret

    def updateFannedBox(self):
        """ Main entry-point to CRUD fanned-out box + add/remove emotions. """
        peers = self.peers()
        if peers:

            # Grab the first box from the first peer
            foundInPeer = None
            for peer in peers:
                if peer.fannedBox:
                    foundInPeer = peer.fannedBox # defered to after fan-in animation in .addEmotion()
                    break

            if foundInPeer:
                if self.fannedBox is not foundInPeer:
                    if self.fannedBox:
                        self.fannedBox.removeEmotion(self)
                    if foundInPeer:
                        foundInPeer.addEmotion(self)
                    self.fannedBox = foundInPeer
            else:
                if self.fannedBox:
                    self.fannedBox.removeEmotion(self)
                self.fannedBox = FannedBox(peers | {self})
                for peer in peers:
                    peer.fannedBox = self.fannedBox
                self.scene().addItem(self.fannedBox)

        else:
            # Remove from fanned box
            if self.fannedBox and not self.shouldShowRightNow():
                self.fannedBox.removeEmotion(self)
                fannedBox = self.fannedBox
                # self.fannedBox = None # Do this after anim is done.
                self.updateGeometry()
                if fannedBox: # is None for tests
                    for emotion in list(fannedBox.emotions):
                        emotion.updateFannedBox()
                    if not fannedBox.emotions and fannedBox.scene():
                        fannedBox.scene().removeItem(fannedBox)


    def beginUpdateFrame(self):
        self.updateFannedBox()
        return super().beginUpdateFrame()

    def endUpdateFrame(self):
        if self.fannedBox:
            # The only call that utilizes &.dirty.
            self.fannedBox.updateFannedState()
        return super().endUpdateFrame()

    def _hoverEnterEvent(self, e):
        """ Disabled in favor of always fanning out. """
        super().hoverEnterEvent(e)
        if self.fannedBox:
            return
        peers = self.peers()
        if peers:
            self.hoverTimer.start()

    def _hoverLeaveEvent(self, e):
        """ Disabled in favor of always fanning out. """
        super().hoverLeaveEvent(e)
        if self.fannedBox:
            return
        elif self.hoverTimer.isActive():
            self.hoverTimer.stop()

    def _onHoverTimer(self):
        """ Disabled in favor of always fanning out. """
        """ Fan out.
        4: [-1.5, -.5, .5, 1.5]
        3: [-1, 0, 1]
        2: [-.5, .5]
        """
        self.hoverTimer.stop()
        self.fannedBox = FannedBox(self.peers() + [self])
        self.scene().addItem(self.fannedBox)
        self.fannedBox.fanOut()

    ## Attributes

    def itemName(self):
        ret = self.__class__.__name__
        if self.personA() and self.personB():
            ret = ret + ' (%s & %s)' % (self.personA().itemName(),
                                        self.personB().itemName())
        elif self.personA():
            ret = ret + ' (%s)' % (self.personA().itemName())
        return ret

    def onProperty(self, prop):
        if self.id is not None: # don't notify if not added to scene yet
            # these optimize timelineviews for person props
            if self.personA():
                self.personA().onEmotionProperty(prop)
            if self.personB():
                self.personB().onEmotionProperty(prop)
        # send it out to the scene for the timelineview in case props
        if prop.name() == 'notes':
            if not self._onShowAliases:
                self.updateNotes()
        elif prop.name() == 'isDateRange':
            self.endEvent.setDateTime(self.startEvent.dateTime())
        super().onProperty(prop)
        if prop.name() in ('tags', 'color'):
            self.updateAll()

    def personA(self):
        return self.people[0]

    def personB(self):
        return self.people[1]

    def swapPeople(self):
        self.people = [self.people[1], self.people[0]]
        self.personAChanged.emit(self.people[0].id)
        self.personBChanged.emit(self.people[0].id)
        self.onPeopleChanged()

    def setPersonA(self, person, undo=False):
        if self.people[0] == person:
            return
        if undo:
            commands.setEmotionPerson(self, personA=person)
        else:
            if self.people[0]:
                self.people[0]._onRemoveEmotion(self)
            self.people[0] = person
            if not self.isDyadic():
                self.setParentItem(person)
            if self.people[0] and not self.addDummy:
                self.people[0]._onAddEmotion(self)
                self.personAChanged.emit(person.id)
            else:
                self.personAChanged.emit(None)
            self.onPeopleChanged()
        
    def setPersonB(self, person, undo=False):
        if self.people[1] == person:
            return
        if undo:
            commands.setEmotionPerson(self, personB=person)
        else:
            if self.people[1]:
                self.people[1]._onRemoveEmotion(self)
            self.people[1] = person
            if self.people[1] and not self.addDummy:
                self.people[1]._onAddEmotion(self)
                self.personBChanged.emit(person.id)
            else:
                self.personBChanged.emit(None)
            self.onPeopleChanged()

