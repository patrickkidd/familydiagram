import pytest

from pkdiagram.pyqt import QApplication, QQmlApplicationEngine
from pkdiagram import util
from pkdiagram.scene import Scene
from pkdiagram.personal import PersonalAppController


@pytest.fixture
def personalApp(qApp, test_session):
    app = PersonalAppController()
    engine = QQmlApplicationEngine()

    qmlErrors = []
    engine.warnings.connect(lambda errors: qmlErrors.extend(errors))

    engine.addImportPath("resources:")
    app.init(engine)
    app.session.init(
        sessionData=test_session.account_editor_dict(), syncWithServer=False
    )
    engine.load("resources:qml/PersonalApplication.qml")

    QApplication.processEvents()
    util.waitALittle()

    if qmlErrors:
        pytest.fail(f"QML load errors: {[e.toString() for e in qmlErrors]}")
    if not engine.rootObjects():
        pytest.fail("QML failed to load - rootObjects() is empty")

    scene = Scene()
    app.setScene(scene)

    yield app

    app.sceneModel.scene = None
    app.peopleModel.scene = None
    scene.deinit()
    engine.clearComponentCache()
