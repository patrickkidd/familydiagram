import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

# def create_lightning_bolt(angle_degrees, length=50):
#     """
#     Create a lightning bolt path at a specified angle.
#     """
#     path = QPainterPath()
#     # Basic lightning bolt shape points
#     points = [QPointF(0, 0), QPointF(-10, 20), QPointF(5, 20), QPointF(-15, 50)]
#     path.addPolygon(QPolygonF(points))
#     # Scale and rotate to the specified angle
#     transform = QTransform()
#     transform.rotate(-angle_degrees)
#     scaled_path = path * transform
#     scaled_path.translate(0, -length)  # Ensure bolt starts from center and goes outward
#     return scaled_path





app = QApplication(sys.argv)
scene = QGraphicsScene()

rect = QRectF(-25, -25, 50, 50)
square_path = QPainterPath()
square_path.addRect(rect)
square_item = QGraphicsPathItem(square_path)
square_item.setPen(Qt.white)
square_item.setPos(0, 0)
scene.addItem(square_item)

# center_path = QPainterPath()
# center_path.addRect(-1, -1, 2, 2)
# center_item = QGraphicsPathItem(center_path)
# center_item.setPen(Qt.white)
# center_item.setPos(0, 0)
# scene.addItem(center_item)



def create_lightning_bolt(degrees, width, length=50):
    """
    Create a lightning bolt path at a specified angle.
    """
    path = QPainterPath()
    path.addPolygon(QPolygonF([
        QPointF(0, 0),
        QPointF(width * -.2, width * .4),
        QPointF(width / 10, width * .35),
        QPointF(width * -.2, width * .9), # peak
        # QPointF(width / -5, width * .55),
        # QPointF(width / -2, width * .60),
        # QPointF(width * -.2, 0),
        # QPointF(0, 0),
    ]))

    nudge = QTransform()
    nudge.rotate(-10)
    path *= nudge

    # Ensure bolt starts from center and goes outward
    path.translate(0, -length)

    transform = QTransform()
    transform.rotate(degrees)
    return path * transform

def bolts_child(parent, num):
    rect = parent.boundingRect()
    SPACING = 11
    WIDTH = rect.width() * .2
    path = QPainterPath()
    for angle in [45, 135, 225, 315]:
        if num == 1:
            path.addPath(create_lightning_bolt(angle, WIDTH))
        elif num == 2:
            path.addPath(create_lightning_bolt(angle - SPACING, WIDTH))
            path.addPath(create_lightning_bolt(angle + SPACING, WIDTH))
        elif num == 3:
            path.addPath(create_lightning_bolt(angle - SPACING, WIDTH))
            path.addPath(create_lightning_bolt(angle, WIDTH))
            path.addPath(create_lightning_bolt(angle + SPACING, WIDTH))
    item = QGraphicsPathItem(path, parent)
    item.setPen(QPen(Qt.white, 1, join=Qt.PenJoinStyle.MiterJoin))
    return item

bolts_child(square_item, 3)


view = QGraphicsView(scene)
view.setRenderHint(QPainter.Antialiasing)
view.show()
view.resize(800, 600)
view.scale(5, 5)

sys.exit(app.exec_())
