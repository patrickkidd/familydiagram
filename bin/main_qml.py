import datetime
import vedana
from pkdiagram.pyqt import *
import pkdiagram
from pkdiagram import (
    util,
    commands,
    QmlDrawer,
    QmlWidgetHelper,
    Layer,
    Diagram,
    FileManager,
    GraphicalTimelineView,
    AddAnythingDialog,
    Person,
)


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


def __test__AddAnythingDialog(scene, parent, sceneModel):
    scene.setTags(["Here", "we", "are"])
    scene.addItem(Person(name="Patrick", lastName="Stinson"))
    scene.addItem(Person(name="Connie", lastName="Service"))
    scene.addItem(Person(name="Lulu", lastName="Lemon"))
    scene.addItem(Person(name="John", lastName="Doey"))
    scene.addItem(Person(name="Jayne", lastName="Thermos"))
    pp = AddAnythingDialog(parent=parent, sceneModel=sceneModel)
    pp.setScene(scene)
    pp.show(animate=False)
    pp.clear()
    parent.resize(400, 600)
    return pp


def __test__PeoplePicker(scene, parent, sceneModel):
    pp = QmlDrawer(
        "tests/qml/PeoplePickerTest.qml", parent=parent, sceneModel=sceneModel
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


def __test__EventProperties(scene, parent, sceneModel):
    scene.setTags(["here", "you", "are"])
    ep = QmlDrawer(
        "tests/qml/EventPropertiesTest.qml", parent=parent, propSheetModel="eventModel"
    )
    ep.qml.rootObject().setProperty("sceneModel", sceneModel)
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
        "qml/PK/EmotionProperties.qml", parent=parent, propSheetModel="emotionModel"
    )
    ep.setScene(scene)
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


def __test__AddEventDialog(scene, parent):
    dlg = pkdiagram.AddEventDialog(parent)
    dlg.setScene(scene)
    dlg.show(animate=False)
    parent.show()
    parent.resize(400, 600)
    return dlg


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
    pkdiagram.util.modTest(__test__, loadfile=(not hasattr(__test__, "TEST_NO_FILE")))
