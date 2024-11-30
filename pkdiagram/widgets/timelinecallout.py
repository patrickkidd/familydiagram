import logging

from pkdiagram import util
from pkdiagram.pyqt import (
    pyqtSignal,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPainter,
    QPainterPath,
    QColor,
    Qt,
    QRectF,
    QPen,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPalette,
    QApplication,
)
from pkdiagram.objects import Event

_log = logging.getLogger(__name__)


PAD = 20
WIDTH = 200
HEIGHT = 70


class TimelineCallout(QWidget):

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.events = []
        self.text = ""
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(WIDTH, HEIGHT)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label.setTextFormat(Qt.PlainText)

        # Create a layout and add a label to display the text
        Layout = QVBoxLayout(self)
        Layout.addWidget(self.label)
        Layout.setContentsMargins(7, 7, 7, PAD)
        QApplication.instance().paletteChanged.connect(self.onApplicationPaletteChanged)

    def resizeEvent(self, e):
        gradient = QLinearGradient(0, self.label.height() - 10, 0, self.label.height())
        gradient.setColorAt(0.0, QColor(0, 0, 0))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        palette = self.label.palette()
        palette.setBrush(QPalette.WindowText, gradient)
        self.label.setPalette(palette)

    def paintEvent(self, e):

        path = QPainterPath()
        rect = QRectF(self.rect())
        rect.adjust(1, 1, -1, -1)

        # Adjust the rounded rectangle so it doesn't cross above the carrot
        path.moveTo(rect.left(), rect.top() + PAD)
        # Upepr left arc
        path.arcTo(rect.left(), rect.top(), PAD, PAD, 180, -90)
        # Top line
        path.lineTo(rect.right() - PAD / 2, rect.top())
        # Upper right arc
        path.arcTo(rect.right() - PAD, rect.top(), PAD, PAD, 90, -90)
        # Right line
        path.lineTo(rect.right(), rect.bottom() - PAD)
        path.arcTo(rect.right() - PAD, rect.bottom() - PAD * 1.5, PAD, PAD, 0, -90)
        # Bottom right line
        path.lineTo(rect.width() / 2 + PAD / 2, rect.bottom() - PAD / 2)
        # Carrot
        path.lineTo(rect.width() / 2, rect.bottom())
        path.lineTo(rect.width() / 2 - PAD / 2, rect.bottom() - PAD / 2)
        # Bottom left line
        path.lineTo(rect.left() + 10, rect.bottom() - 10)
        path.arcTo(rect.left(), rect.bottom() - PAD * 1.5, PAD, PAD, -90, -90)
        path.closeSubpath()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(util.TEXT_COLOR, 2))
        # if util.IS_UI_DARK_MODE:
        #     painter.setPen(QPen(util.TEXT_COLOR, 2))
        # else:
        #     painter.setPen(QPen(QColor(0, 0, 0, 127), 2))
        # color = QColor(0, 0, 0, 100)
        painter.fillPath(path, util.WINDOW_BG)
        painter.drawPath(path)

    def onApplicationPaletteChanged(self):
        self.label.setStyleSheet(
            f"color: {QColor(util.TEXT_COLOR).name()}; background-color: transparent;"
        )
        font = QFont(util.DETAILS_FONT)
        font.setPixelSize(util.TEXT_FONT_SIZE)
        self.label.setFont(font)

    def mouseReleaseEvent(self, e):
        self.clicked.emit()
        return super().mouseReleaseEvent(e)

    def setEvents(self, events: list[Event]):
        self.events = events  # for testing
        text = "\n".join(
            [f"{util.dateString(x.dateTime())} - {x.description()}" for x in events]
        )
        # metrics = QFontMetrics(self.label.font())
        # elided_text = metrics.elidedText(text, Qt.ElideRight, self.label.width())
        # _log.info(elided_text)
        self.label.setText(text)
        self.onApplicationPaletteChanged()


if __name__ == "__main__":
    import sys
    from pkdiagram.pyqt import QApplication

    util.TEXT_COLOR = Qt.white
    util.WINDOW_BG = QColor("#1e1e1e")

    app = QApplication(sys.argv)
    parent = QWidget()
    # parent.setStyleSheet("background-color: red")
    callout = TimelineCallout(parent)
    parent.show()
    parent.resize(600, 800)
    callout.move(200, 200)
    callout.setEvents(
        [
            Event(dateTime=util.Date(2021, 1, 1), description="Event 1"),
            Event(dateTime=util.Date(2022, 1, 1), description="Event 2"),
            Event(dateTime=util.Date(2023, 1, 1), description="Event 3"),
            Event(dateTime=util.Date(2021, 1, 1), description="Event 10"),
            Event(dateTime=util.Date(2022, 1, 1), description="Event 12"),
            Event(dateTime=util.Date(2023, 1, 1), description="Event 13"),
            Event(dateTime=util.Date(2023, 1, 1), description="Event 14"),
        ]
    )
    app.exec()
