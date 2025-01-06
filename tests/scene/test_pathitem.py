import pytest

from pkdiagram.pyqt import QPointF
from pkdiagram.scene import PathItem


pytestmark = [
    pytest.mark.component("PathItem"),
    pytest.mark.depends_on("Item"),
]


def test_set_pos_undo(scene):
    item = PathItem(itemPos=QPointF(50, 50))
    scene.addItem(item)

    # simulate drag-move to ensure capture of initial position
    item.setPos(QPointF(100, 200))

    # Now simulate release of mouse
    item.setItemPos(QPointF(200, 300), undo=True)  # 1
    assert item.pos() == QPointF(200, 300)
    assert item.itemPos() == QPointF(200, 300)

    scene.undo()
    assert item.pos() == QPointF(50, 50)
    assert item.itemPos() == QPointF(50, 50)
