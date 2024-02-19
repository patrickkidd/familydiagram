import sys, logging
from PyQt5.QtCore import *
from PyQt5.QtGui import *



def one():
    from .pkdiagram import debug


    logging.basicConfig(stream=sys.stdout, format='%(filename)s:%(lineno)s %(message)s')

    log = logging.getLogger(__name__)

    log.setLevel(logging.INFO)
    o1, c1 = QObject(), QColor()
    log.info(f'here, {o1}, {c1}')


    bleh = Debug()



def create_lightning_and_square_path(start_x, start_y, size, intensity=1.0):
    """
    Creates a QPainterPath object with a square and lightning bolts from each corner.

    Args:
        start_x (int): The x-coordinate of the top-left corner of the square.
        start_y (int): The y-coordinate of the top-left corner of the square.
        size (int): The size of the square (side length).
        intensity (float, optional): A value between 0.0 and 1.0 controlling the
            size/intensity of the lightning bolts. Defaults to 1.0.

    Returns:
        QPainterPath: The path object representing the square and lightning bolts.
    """


    # Draw sparks
    sparksPath = QPainterPath()
    # Example spark 1 - A line spark
    sparksPath.moveTo(100, 50)  # Starting point of the spark
    sparksPath.lineTo(110, 65)  # Ending point of the spark
    # Example spark 2 - A triangular spark
    sparksPath.moveTo(150, 50)  # Starting point of the spark
    sparksPath.lineTo(160, 65)  # Mid point of the spark
    sparksPath.lineTo(145, 65)  # End point of the spark
    sparksPath.closeSubpath()  # Close the path to create a filled shape
    return sparksPath


    path = QPainterPath()

    # # Create square path
    # path.moveTo(start_x, start_y)
    # path.lineTo(start_x + size, start_y)
    # path.lineTo(start_x + size, start_y + size)
    # path.lineTo(start_x, start_y + size)
    # path.closeSubpath()

    # Adjust lightning bolt size based on intensity
    bolt_size = size * intensity / 2

    # Create lightning bolt paths from each corner
    # Top-right corner
    path.moveTo(start_x + size, start_y)
    path.lineTo(start_x + size - bolt_size, start_y - bolt_size * 2)
    path.lineTo(start_x + size + bolt_size, start_y - bolt_size)
    path.lineTo(start_x + size - bolt_size * 2, start_y + bolt_size)
    path.lineTo(start_x + size, start_y + bolt_size * 2)
    path.closeSubpath()

    # Top-left corner
    path.moveTo(start_x, start_y)
    path.lineTo(start_x + bolt_size, start_y - bolt_size * 2)
    path.lineTo(start_x - bolt_size, start_y - bolt_size)
    path.lineTo(start_x + bolt_size * 2, start_y + bolt_size)
    path.lineTo(start_x, start_y + bolt_size * 2)
    path.closeSubpath()

    # Bottom-right corner
    path.moveTo(start_x + size, start_y + size)
    path.lineTo(start_x + size - bolt_size, start_y + size + bolt_size * 2)
    path.lineTo(start_x + size + bolt_size, start_y + size + bolt_size)
    path.lineTo(start_x + size - bolt_size * 2, start_y + size - bolt_size)
    path.lineTo(start_x + size, start_y + size - bolt_size * 2)
    path.closeSubpath()

    # Bottom-left corner
    path.moveTo(start_x, start_y + size)
    path.lineTo(start_x + bolt_size, start_y + size + bolt_size * 2)
    path.lineTo(start_x - bolt_size, start_y + size + bolt_size)
    path.lineTo(start_x + bolt_size * 2, start_y + size - bolt_size)
    path.lineTo(start_x, start_y + size - bolt_size * 2)
    path.closeSubpath()

    return path




def two():

    import sys
    from PyQt5.QtWidgets import QApplication, QWidget
    from PyQt5.QtGui import QPainter, QPainterPath
    from PyQt5.QtCore import Qt

    class LightningSquareWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Lightning Square")
            self.resize(400, 400)

        def paintEvent(self, event):
            painter = QPainter(self)

            path = create_lightning_and_square_path(100, 100, 200, intensity=0.8)  # Adjust intensity as desired

            # Customize colors and styles as needed
            painter.setPen(QPen(Qt.yellow, 5))  # Yellow outline for the square
            painter.setBrush(Qt.blue)  # Blue fill for the square
            painter.drawPath(path)

            painter.setPen(QPen(Qt.white, 2))  # White outline for the lightning bolts
            painter.setBrush(Qt.white)  # White fill for the lightning bolts
            painter.drawPath(path)

    app = QApplication(sys.argv)
    window = LightningSquareWidget()
    window.show()
    sys.exit(app.exec_())


two()
