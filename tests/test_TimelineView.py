from pkdiagram.pyqt import *
from pkdiagram import util, QmlWidgetHelper, objects


class TimelineViewTest(QWidget, QmlWidgetHelper):

    QmlWidgetHelper.registerQmlMethods([{"name": "test_getDelegates", "return": True}])

    def __init__(self, parent=None):
        super().__init__(parent)
        Layout = QVBoxLayout(self)
        self.initQmlWidgetHelper("tests/qml/TimelineViewTest.qml")
        self.checkInitQml()
        self.resize(600, 800)


def test_init(qtbot, qmlScene, request):
    tvt = TimelineViewTest()
    tvt.show()
    tvt.setItemProp("timelineView", "model", qmlScene.timelineModel)

    def cleanup():
        nonlocal tvt
        tvt.hide()
        tvt = None

    request.addfinalizer(cleanup)
    qtbot.addWidget(tvt)
    qtbot.waitActive(tvt)

    p1 = qmlScene.query1(name="p1")
    objects.Event(p1, dateTime=util.Date(2001, 1, 1), description="Something happened")
    # delegates = tvt.test_getDelegates().toVariant()
    # assert tvt.itemProp('table', 'rows') == 1
    # print('asserting...')
    # assert delegates != []
    # delegates = []
    # table = tvt.findItem('table')
    # for child in table.childItems():
    #     if child.property('thisRow') is not None:
    #         delegates.append(child)
    # assert len(delegates) == 1
