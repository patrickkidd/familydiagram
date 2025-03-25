import logging

from pkdiagram.pyqt import (
    QGraphicsOpacityEffect,
    QPropertyAnimation,
    QAbstractAnimation,
    QRect,
    Qt,
    QPoint,
    QVariantAnimation,
    QItemSelectionModel,
    QFrame,
    pyqtSignal,
    QApplication,
    QDateTime,
    QItemSelectionModel,
    QColor,
)
from pkdiagram import util
from pkdiagram.scene import Property
from pkdiagram.widgets import PixmapToolButton, PixmapButtonHelper
from .graphicaltimeline import GraphicalTimeline


_log = logging.getLogger(__name__)


class GraphicalTimelineView(QFrame):
    """
    Contracts into a dateslider, expands into full-blown graphical timeline.
    """

    MARGIN_X = util.MARGIN_X
    MARGIN_Y = util.MARGIN_Y

    EXPANDED = "expanded"
    EXPANDING = "expanding"
    CONTRACTING = "contracting"
    CONTRACTED = "contracted"

    LIGHT_MODE_SS = """
    GraphicalTimelineView {
        background-color: rgba(255, 255, 255, 1.0);
        border-top: 1px solid #d8d8d8;
    }
    """

    DARK_MODE_SS = """
    GraphicalTimelineView {
        background-color: rgba(75, 75, 82, 1.0);
        border-top: 1px solid #545358;
    }
    """

    nextTaggedDate = pyqtSignal()
    prevTaggedDate = pyqtSignal()
    expandedChanged = pyqtSignal(bool)
    dateTimeClicked = pyqtSignal(QDateTime)

    def __init__(
        self,
        searchModel,
        timelineModel,
        parent=None,
    ):
        super().__init__(parent)
        self.scene = None
        self.documentView = parent if util.isInstance(parent, "DocumentView") else None
        self.searchModel = searchModel
        self.timelineModel = timelineModel
        self.selectionModel = None

        self.timeline = GraphicalTimeline(searchModel, timelineModel, self)
        self.timeline.setStyleSheet("background-color: transparent")
        self.timeline.canvas.setStyleSheet("background-color: transparent")
        self.lastScaleFactor = self.timeline.scaleFactor
        self.lastHScrollCoeff = self.timeline.horizontalScrollBar().value()

        # retain scale between expand & contract
        self.scaleAnimation = QVariantAnimation(self)
        self.scaleAnimation.setDuration(util.ANIM_DURATION_MS * 2)
        self.scaleAnimation.setEasingCurve(util.ANIM_EASING)
        self.scaleAnimation.valueChanged.connect(self.onScaleAnimationTick)

        self.prevButton = PixmapToolButton(self, uncheckedPixmapPath="back-button.png")
        self.prevButtonOpacityEffect = QGraphicsOpacityEffect(self)
        self.prevButton.setGraphicsEffect(self.prevButtonOpacityEffect)
        self.prevButton.clicked.connect(self.prevTaggedDate)

        self.nextButton = PixmapToolButton(
            self, uncheckedPixmapPath="forward-button.png"
        )
        self.nextButtonOpacityEffect = QGraphicsOpacityEffect(self)
        self.nextButton.setGraphicsEffect(self.nextButtonOpacityEffect)
        self.nextButton.clicked.connect(self.nextTaggedDate)

        self.expandButton = PixmapToolButton(
            self,
            uncheckedPixmapPath="expand-up-button.png",
            checkedPixmapPath="contract-down-button.png",
        )
        self.expandButton.setCheckable(True)
        self.expandButton.toggled[bool].connect(self.setExpanded)

        self.searchButton = PixmapToolButton(
            self, uncheckedPixmapPath="search-button.png"
        )
        self.searchButtonOpacityEffect = QGraphicsOpacityEffect(self)
        self.searchButton.setGraphicsEffect(self.searchButtonOpacityEffect)

        self.inspectButton = PixmapToolButton(
            self, uncheckedPixmapPath="details-button.png"
        )
        self.inspectButtonOpacityEffect = QGraphicsOpacityEffect(self)
        self.inspectButton.setGraphicsEffect(self.inspectButtonOpacityEffect)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(util.ANIM_DURATION_MS * 2)
        self.animation.setEasingCurve(util.ANIM_EASING)
        self.animation.valueChanged.connect(self.onAnimationTick)
        self.animation.finished.connect(self.onAnimationFinished)

        if util.ENABLE_DROP_SHADOWS:
            self.setGraphicsEffect(
                util.makeDropShadow(
                    offset=0, blurRadius=2, color=QColor(100, 100, 100, 70)
                )
            )
        self.setMinimumHeight(self.timeline.height())
        self.state = self.CONTRACTED

        # Was previously in init()...not sure why
        self.searchButton.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.searchButtonOpacityEffect.setOpacity(0)
        self.inspectButtonOpacityEffect.setOpacity(0)
        QApplication.instance().paletteChanged.connect(self.onApplicationPaletteChanged)

    def setScene(self, scene):
        if self.scene:
            self.scene.propertyChanged[Property].disconnect(self.onSceneProperty)
        self.expandButton.setChecked(False)  # triggers signal + contract
        self.scene = scene
        if scene:
            scene.propertyChanged[Property].connect(self.onSceneProperty)
        self.timeline.setScene(self.scene)
        self.state = self.CONTRACTING  # hack.1
        if scene:
            self.onAnimationFinished()  # hack.2

    def setSelectionModel(self, selectionModel: QItemSelectionModel):
        self.selectionModel = selectionModel
        self.timeline.setSelectionModel(selectionModel)
        self.selectionModel.selectionChanged.connect(self.onSelectionChanged)

    @util.blocked
    def setExpanded(self, on):
        if self.expandButton.isChecked() != on:
            self.expandButton.setChecked(on)
        if on:
            self.expand()
        else:
            self.contract()

    @util.blocked
    def onSceneProperty(self, prop):
        if prop.name() == "currentDateTime":
            self.update()
        elif prop.name() == "showAliases":
            self.timeline.updatePersonNames()

    def onSelectionChanged(self):
        rows = set([x.row() for x in self.selectionModel.selectedRows()])
        if rows:
            self.inspectButton.show()
        else:
            self.inspectButton.hide()

    def contract(self):
        if not self.parent():
            return

        self.state = self.CONTRACTING
        hScroll = self.timeline.horizontalScrollBar()
        if hScroll.maximum() != hScroll.minimum():
            self.lastHScrollCoeff = hScroll.value() / hScroll.maximum()
        else:
            self.lastHScrollCoeff = 1.0
        if self.animation.state() == QAbstractAnimation.Running:
            self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(
            QRect(
                0,
                self.parent().height() - util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT,
                self.geometry().width(),
                self.timeline.height(),
            )
        )
        self.animation.start()
        self.lastScaleFactor = self.timeline.scaleFactor
        self.scaleAnimation.setStartValue(self.lastScaleFactor)
        self.scaleAnimation.setEndValue(1.0)
        self.scaleAnimation.start()

    def expand(self):
        if not self.parent():
            return

        self.state = self.EXPANDING
        if self.animation.state() == QAbstractAnimation.Running:
            self.animation.stop()
        self.animation.setStartValue(self.geometry())
        # retain width for when drawer is shown.
        endValue = self.parent().rect()
        endValue.setWidth(self.geometry().width())
        self.animation.setEndValue(endValue)
        self.animation.start()
        self.scaleAnimation.setStartValue(1.0)
        self.scaleAnimation.setEndValue(self.lastScaleFactor)
        self.scaleAnimation.start()
        self.timeline.setIsSlider(False)

    def isExpanded(self):
        return self.state == self.EXPANDED

    def isContracted(self):
        return self.state == self.CONTRACTED

    def onScaleAnimationTick(self):
        scaleFactor = self.scaleAnimation.currentValue()
        self.timeline.zoomAbsolute(scaleFactor)
        hScroll = self.timeline.horizontalScrollBar()
        x = (hScroll.maximum() - hScroll.minimum()) * self.lastHScrollCoeff
        self.timeline.horizontalScrollBar().setValue(round(x))

    def onAnimationTick(self):
        self.adjust()

    def onAnimationFinished(self):
        if self.state == self.CONTRACTING:
            self.state = self.CONTRACTED
            self.timeline.setIsSlider(True)
            self.searchButton.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        elif self.state == self.EXPANDING:
            self.state = self.EXPANDED
            self.searchButton.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.onApplicationPaletteChanged()
        if self.timeline.isSlider() and self.documentView:
            self.documentView.adjust()  # wasn't updating after contracting
        else:
            self.adjust()
        self.expandedChanged.emit(self.isExpanded())

    def onApplicationPaletteChanged(self):
        if util.IS_UI_DARK_MODE:
            self.setStyleSheet(self.DARK_MODE_SS)
        else:
            self.setStyleSheet(self.LIGHT_MODE_SS)
        for child in self.findChildren(PixmapButtonHelper):
            if isinstance(child, PixmapButtonHelper):
                child.onApplicationPaletteChanged()

    def adjust(self, freezeScroll=False):
        if self.state == self.CONTRACTED:
            expanded = 0.0
        if self.state == self.CONTRACTING or self.state == self.EXPANDING:
            if self.animation.duration():
                progress = self.animation.currentTime() / self.animation.duration()
            else:
                progress = 1.0
            if self.state == self.CONTRACTING:
                expanded = 1 - progress
            elif self.state == self.EXPANDING:
                expanded = progress
        elif self.state == self.EXPANDED:
            expanded = 1.0

        self.expandButton.move(
            self.width() - self.expandButton.width() - self.MARGIN_X, self.MARGIN_Y
        )
        self.searchButton.move(
            self.expandButton.x() - self.searchButton.width() - self.MARGIN_X,
            self.expandButton.y(),
        )
        self.searchButtonOpacityEffect.setOpacity(expanded)
        self.inspectButton.move(
            self.searchButton.x() - self.inspectButton.width() - self.MARGIN_X,
            self.searchButton.y(),
        )
        self.inspectButtonOpacityEffect.setOpacity(expanded)

        prevButtonIn = self.MARGIN_X
        prevButtonOut = -self.prevButton.width() - self.MARGIN_X
        prevButtonStride = prevButtonIn - prevButtonOut
        nextButtonIn = self.searchButton.x()
        nextButtonOut = self.width() + self.nextButton.width() + self.MARGIN_X
        nextButtonStride = nextButtonOut - nextButtonIn
        self.prevButton.move(
            round(prevButtonOut + (prevButtonStride * (1 - expanded))), self.MARGIN_Y
        )
        self.nextButton.move(
            round(nextButtonIn + (nextButtonStride * expanded)), self.MARGIN_Y
        )
        self.prevButtonOpacityEffect.setOpacity(1 - expanded)
        self.nextButtonOpacityEffect.setOpacity(1 - expanded)

        if self.state in (self.CONTRACTING, self.EXPANDING):
            # keep the canvas in place visually
            y = self.mapFromParent(QPoint(0, 0)).y()
            height = self.parent().height()
        else:
            y = 0
            height = self.height()
        leftStop = self.prevButton.x() + self.prevButton.width()
        rightStop = self.nextButton.x()
        old = self.geometry()
        new = QRect(leftStop, y, rightStop - leftStop, height)
        self.timeline._freezeScroll = freezeScroll
        self.timeline.setGeometry(new)
        self.timeline._freezeScroll = False


def __test__(scene, parent):
    scene.setTags(["Tag 1", "Tag 2"])
    for i, event in enumerate(scene.events()):
        if i % 2:
            event.setTag("Tag 1")
        else:
            event.setTag("Tag 2")
    w = GraphicalTimelineView(parent)
    w.setScene(scene)
    w.expand()
    # w.onSearch()
    w.show()
    parent.layout().addWidget(w)
    parent.resize(800, 600)
    w.adjust()
    return w
