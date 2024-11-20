import datetime
import logging
import vedana
from pkdiagram.app import commands
from pkdiagram.pyqt import *
import pkdiagram
from pkdiagram import (
    util,
    QmlDrawer,
    QmlWidgetHelper,
    Layer,
    Diagram,
    FileManager,
    GraphicalTimelineView,
    AddAnythingDialog,
    Person,
    QmlEngine,
)

_log = logging.getLogger(__name__)


def modTest(__test__, loadfile=True, useMW=False):
    """Run a test app with __test__(scene) as callback."""

    import os.path
    import pickle
    import sys, inspect, signal
    import tempfile

    import mock

    from pkdiagram.pyqt import (
        QObject,
        QTimer,
        QMainWindow,
        QWidget,
        QHBoxLayout,
        QEvent,
        QDateTime,
        QUrl,
    )
    from pkdiagram.util import CUtil
    from pkdiagram import util, Scene, Application, QmlEngine, Session

    FDDocument = util.FDDocument

    sys.path.append(os.path.realpath(os.path.join(__file__, "..", "..", "tests")))
    import test_util

    def _makeSettings():
        dpath = os.path.join(tempfile.mkdtemp(), "settings.ini")
        prefs = util.Settings(dpath, "vedanamedia")
        return prefs

    with mock.patch("pkdiagram.Application.makeSettings", side_effect=_makeSettings):
        app = Application(sys.argv)

    def _quit(x, y):
        app.quit()

    signal.signal(signal.SIGINT, _quit)

    if useMW:
        parent = QMainWindow()
        modTest.Layout = None
    else:
        parent = QWidget()
        Layout = modTest.Layout = QHBoxLayout(parent)
        Layout.setContentsMargins(0, 0, 0, 0)
        parent.setLayout(Layout)

    class EventFilter(QObject):
        def eventFilter(self, o, e):
            print(e.type(), util.qenum(QEvent, e.type()))
            if e.type() == QEvent.Close:
                app.quit()
            return False

    sig = inspect.signature(__test__)
    # app.installEventFilter(EventFilter(app))
    parent.show()

    def onFileOpened(document):
        scene = modTest.scene = Scene(document=document)
        bdata = document.diagramData()
        data = pickle.loads(bdata)
        ret = scene.read(data)
        scene.setCurrentDateTime(QDateTime.currentDateTime())
        if len(sig.parameters) == 2:
            w = __test__(modTest.scene, parent)
        elif len(sig.parameters) == 3:
            engine = QmlEngine(Session())
            engine.setScene(scene)
            w = __test__(modTest.scene, parent, engine)
            engine.deinit()
        if w is None:
            _log.error("modTest returned None")
            Application.quit()
            return
        if useMW:
            parent.setCentralWidget(w)
        else:
            modTest.Layout.addWidget(w)

    def noFileOpened():
        scene = modTest.scene = Scene()
        if len(sig.parameters) == 2:
            w = __test__(modTest.scene, parent)
        elif len(sig.parameters) == 3:
            engine = QmlEngine(Session())
            engine.setScene(scene)
            w = __test__(modTest.scene, parent, engine)
            engine.deinit()
        modTest.Layout.addWidget(w)

    def onInit():
        ROOT = os.path.realpath(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
        )

        filePath = os.path.join(ROOT, "tests", "data", "mod_test.fd")
        # filePath = os.path.join(ROOT, "tests", "data", "TIMELINE_TEST.fd")

        CUtil.instance().openExistingFile(QUrl.fromLocalFile(filePath))

    if loadfile:
        QTimer.singleShot(0, onInit)
    else:
        noFileOpened()

    CUtil.instance().init()
    CUtil.instance().fileOpened[FDDocument].connect(onFileOpened)

    app.exec()
    app.deinit()


modTest.scene = None


def __test__FileManager(scene, parent):
    w = FileManager(parent)
    parent.resize(400, 600)
    parent.show()
    return w


def __test__LayerView(scene, parent, sceneModel):
    class LayerViewTest(QWidget, QmlWidgetHelper):
        def __init__(self, parent=None):
            super().__init__(parent)
            Layout = QVBoxLayout(self)
            self.initQmlWidgetHelper("qml/PK/LayerView.qml", sceneModel=sceneModel)
            self.checkInitQml()
            self.model = pkdiagram.SceneLayerModel(self)
            self.model.scene = scene
            self.setRootProp("model", self.model)

    w = LayerViewTest(parent)
    scene.find(types=Layer)[0].setStoreGeometry(True)
    parent.resize(550, 400)
    w.show()
    return w


def __test__TimelineView(scene, parent, sceneModel):
    class TimelineViewTest(QWidget, QmlWidgetHelper):
        def __init__(self, parent=None):
            super().__init__(parent)
            Layout = QVBoxLayout(self)
            self.initQmlWidgetHelper("qml/PK/TimelineView.qml", sceneModel=sceneModel)
            self.checkInitQml()

    w = TimelineViewTest(parent)
    w.rootProp("model").items = [p for p in scene.people() if p.id in (201, 605)]
    parent.resize(900, 800)
    w.show()
    return w


def _init_scene_for_people_picker(scene):
    return [
        scene.addItem(Person(name="Patrick", lastName="Stinson")),
        scene.addItem(Person(name="Connie", lastName="Service")),
        scene.addItem(Person(name="Lulu", lastName="Lemon")),
        scene.addItem(Person(name="John", lastName="Doe")),
        scene.addItem(Person(name="Jayne", lastName="Thermos")),
    ]


def __test__TestDialog(scene, parent, sceneModel):

    class TestDialog(QWidget, QmlWidgetHelper):

        def __init__(self, sceneModel, parent=None):
            super().__init__(parent)
            QVBoxLayout(self)
            self.initQmlWidgetHelper("qml/TestDialog.qml", sceneModel=sceneModel)
            self.checkInitQml()

    pp = TestDialog(parent=parent, sceneModel=sceneModel)
    pp.show()
    parent.resize(400, 600)
    return pp


def __test__AddAnythingDialog(scene, parent, engine: QmlEngine):
    _init_scene_for_people_picker(scene)
    pp = AddAnythingDialog(engine, parent)
    pp.setScene(scene)
    pp.show(animate=False)
    pp.initForSelection([])
    pp.clear()
    parent.resize(400, 600)
    return pp


def __test__PeoplePicker(scene, parent, sceneModel):
    from pkdiagram.widgets.qml.peoplepicker import add_existing_person

    class PeoplePickerTest(QWidget, QmlWidgetHelper):

        QmlWidgetHelper.registerQmlMethods(
            [
                {"name": "setExistingPeople"},
                {"name": "peopleEntries", "return": True},
            ]
        )

        def __init__(self, sceneModel, parent=None):
            super().__init__(parent)
            QVBoxLayout(self)
            self.initQmlWidgetHelper(
                "tests/qml/PeoplePickerTest.qml", sceneModel=sceneModel
            )
            self.checkInitQml()

        def test_setExistingPeople(self, people):
            peoplePickerItem = self.findItem("peoplePicker")
            itemAddDone = util.Condition(peoplePickerItem.itemAddDone)
            self.setExistingPeople(people)
            while itemAddDone.callCount < len(people):
                _log.info(
                    f"Waiting for {len(people) - itemAddDone.callCount} / {len(people)} itemAddDone signals"
                )
                assert itemAddDone.wait() == True
            # _log.info(f"Got {itemAddDone.callCount} / {len(people)} itemAddDone signals")

    people = _init_scene_for_people_picker(scene)
    pp = PeoplePickerTest(parent=parent, sceneModel=sceneModel)
    pp.show()
    parent.resize(400, 600)
    parent.show()
    pp.test_setExistingPeople(people[:1])
    return pp


def __test__PersonPicker(scene, parent, sceneModel):
    _init_scene_for_people_picker(scene)
    pp = QmlDrawer(
        "tests/qml/PersonPickerTest.qml", parent=parent, sceneModel=sceneModel
    )
    pp.setScene(scene)
    pp.show(animate=False)
    parent.resize(400, 600)
    parent.show()
    return pp


def __test__CaseProperties(scene, parent, sceneModel):
    w = QmlDrawer("qml/CaseProperties.qml", parent=parent, sceneModel=sceneModel)
    scene.setTags(scene.tags() + ["here", "you", "are"])
    w.show(animate=False, tab="settings")
    w.setItemProp("settingsView", "contentY", 643)
    for layer in scene.layers():
        layer.setTags(["here", "you", "are"])
    # w.layerModel.modelReset.emit()
    scene.setCurrentDateTime(QDate(1925, 10, 14))
    _user = {
        "id": 1,
        "username": "patrickkidd@gmail.com",
        "first_name": "Patrick",
        "last_name": "Stinson",
        "free_diagram_id": 123,
        "roles": [],
        "licenses": [
            {
                "active": True,
                "canceled": False,
                "policy": {
                    "product": vedana.LICENSE_PROFESSIONAL,
                    "name": "prof",
                    "code": vedana.LICENSE_PROFESSIONAL_ANNUAL,
                },
                "activations": [{"machine": {"code": util.HARDWARE_UUID}}],
            }
        ],
        "secret": "1232345",
    }
    sceneModel.setServerDiagram(
        Diagram(
            id=1,
            user_id=1,
            access_rights=[],
            created_at=datetime.datetime.now(),
            user=_user,
        )
    )
    # session = Session()
    sceneModel.session.init(
        sessionData={
            "session": {"token": "1234", "user": _user},
            "users": [_user],
            "deactivated_versions": [],
        }
    )
    # sceneModel.setSession(session)
    # sceneModel.setActiveFeatures([vedana.LICENSE_PROFESSIONAL])
    parent.resize(510, 600)
    return w


def __test__PersonProperties(scene, parent, sceneModel):
    scene.setTags(["Here", "we", "are"])
    pp = QmlDrawer(
        "qml/PersonProperties.qml",
        parent=parent,
        propSheetModel="personModel",
        sceneModel=sceneModel,
    )
    scene.searchModel.description = "Proj"
    pp.setScene(scene)
    # scene.layers()[0].setActive(True)
    person = scene.people()[0]
    pp.show([person], animate=False)
    parent.resize(400, 600)
    return pp


def __test__MarriageProperties(scene, parent, sceneModel):
    scene.setTags(["here", "you", "are"])
    mp = QmlDrawer(
        "qml/MarriageProperties.qml", parent=parent, propSheetModel="marriageModel"
    )
    mp.qml.rootObject().setProperty("sceneModel", sceneModel)
    Debug(scene.marriages()[0].events())

    mp.setScene(scene)
    mp.show([scene.marriages()[0]], animate=False)
    parent.resize(400, 600)
    return mp


def __test__EventProperties(scene, parent, engine):
    scene.setTags(["here", "you", "are"])
    ep = QmlDrawer(
        engine,
        "tests/qml/EventPropertiesTest.qml",
        parent=parent,
        propSheetModel="eventModel",
    )
    ep.setScene(scene)
    for event in scene.events():
        if not event.uniqueId():
            break
    ep.show([event], animate=False)
    parent.resize(400, 600)
    return ep


def __test__EmotionProperties(scene, parent, sceneModel):
    scene.setTags(["here", "you", "are"])
    ep = QmlDrawer(
        "qml/PK/EmotionProperties.qml",
        parent=parent,
        sceneModel=sceneModel,
        propSheetModel="emotionModel",
    )
    # ep.setScene(scene)
    ep.show([scene.emotions()[0]], animate=False)
    parent.resize(400, 600)
    return ep


def __test__LayerItemProperties(scene, parent, sceneModel):
    def addLayer():
        name = util.newNameOf(scene.layers(), tmpl="View %i", key=lambda x: x.name())
        layer = pkdiagram.Layer(name=name)
        commands.addLayer(scene, layer)

    addLayer()
    addLayer()
    addLayer()
    callout = pkdiagram.Callout()
    callout.setLayers([scene.layers()[1].id, scene.layers()[3].id])
    scene.addItem(callout)
    lip = QmlDrawer(
        "qml/LayerItemProperties.qml",
        parent=parent,
        propSheetModel="layerItemModel",
        resizable=False,
    )
    lip.setScene(scene)
    lip.show(scene.layerItems(), animate=False)
    parent.resize(400, 600)
    return lip


def __test__GraphicalTimelineView(scene, parent):
    scene.setTags(["Tag 1", "Tag 2"])
    for i, event in enumerate(scene.events()):
        if i % 2:
            event.setTag("Tag 1")
        else:
            event.setTag(";Tag 2")
    w = GraphicalTimelineView(parent)
    w.setScene(scene)
    w.expand()
    w.onSearch()
    w.show()
    parent.layout().addWidget(w)
    parent.resize(800, 400)
    w.adjust()
    return w


def __test__SearchView(scene, parent):
    def noop(x):
        pass

    w = pkdiagram.SearchView(parent, noop)
    w.WIDTH = util.DRAWER_WIDTH
    w.checkInitQml()
    w.show(scene.layerItems(), animate=False)
    w.adjust()
    parent.resize(200, 600)
    return w


# from qml_tests import *


def __test__AccountDialog(scene, parent):
    parent.resize(400, 400)  # must go before widgets.Dialog.show()
    dlg = pkdiagram.AccountDialog(parent)
    dlg.init()
    dlg.show()
    dlg.login("patrickkidd@gmail.com", "v4n4gon3")
    dlg.adjust()
    return dlg


def run(modname):
    __test__ = globals()["__test__" + modname]
    modTest(__test__, loadfile=(not hasattr(__test__, "TEST_NO_FILE")))
