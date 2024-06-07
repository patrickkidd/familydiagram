from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QFont, QFontMetrics
from PyQt5.QtCore import Qt
import sys


class VoltageWidget(QWidget):
    def __init__(self):
        super().__init__()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(QFont("Arial", 30))
        painter.rotate(-90)
        text = "Voltage"
        fm = QFontMetrics(painter.font())
        textWidth = fm.width(text)
        painter.drawText(-self.height() // 2 - textWidth // 2, fm.height(), text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = VoltageWidget()
    ex.show()
    sys.exit(app.exec_())
