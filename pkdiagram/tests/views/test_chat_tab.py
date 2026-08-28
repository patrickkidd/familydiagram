"""FD-336 / WP-F: the Chat tab of Pro's case drawer.

C1 a case the coach cannot open says why, in the tab, instead of showing dead
controls; C2 the embedded coach carries none of the standalone app's chrome —
its hamburger, account drawer, clear-data and logout belong to a phone app that
owns its own session and case list; C4 the tab hosts the views Personal ships
rather than a Pro-only copy of them.
"""

import pytest

from btcopilot.extensions import db
from btcopilot.pro.models import Diagram

from pkdiagram.models import ServerFileManagerModel
from pkdiagram.personal.propersonal import ProPersonal
from pkdiagram.pyqt import QObject
from pkdiagram.server_types import Diagram as fe_Diagram
from pkdiagram.views import CaseProperties


pytestmark = [pytest.mark.component("CaseProperties")]


def _container(item):
    """The embedded PersonalContainer, by QML type — the tab hosts Personal's
    own component or it hosts nothing."""
    for child in item.findChildren(QObject):
        if child.metaObject().className().startswith("PersonalContainer"):
            return child
    return None


@pytest.fixture
def chatTab(qtbot, qmlEngine, scene, test_session, test_user):
    """The case drawer open on its Chat tab, with the coach wired to Pro's
    engine the way MainWindow wires it."""
    created = []

    def _chatTab(owned=True):
        db.session.add(test_session)
        qmlEngine.session.init(sessionData=test_session.account_editor_dict())
        qmlEngine.setScene(scene)

        fileModel = ServerFileManagerModel(qmlEngine)
        proPersonal = ProPersonal(qmlEngine.session, fileModel)
        qmlEngine.setProPersonal(proPersonal)

        diagram = fe_Diagram.create(
            Diagram.query.get(test_user.free_diagram_id).as_dict()
        )
        if not owned:
            diagram.user_id = test_user.id + 1
        qmlEngine.setServerDiagram(diagram)
        proPersonal.setScene(scene)
        proPersonal.setDiagram(diagram, [])

        w = CaseProperties(qmlEngine, "qml/CaseProperties.qml", parent=None)
        w.show(animate=False, tab="chat")
        w.resize(510, 600)
        qtbot.addWidget(w)
        qtbot.waitActive(w)

        created.append((w, proPersonal))
        return w, proPersonal

    yield _chatTab

    # MainWindow's order: unbind and deinit the coach while its QML still
    # exists, then tear the drawer down.
    for w, proPersonal in created:
        proPersonal.clear()
        proPersonal.deinit()
        w.deinit()


def test_embedded_coach_hosts_personals_views_without_its_chrome(chatTab):
    """C2/C4. The qmlEngine fixture fails this test on any QML warning, which
    is the real gate: PersonalContainer instantiated inside Pro's engine
    reports every context property the embedding forgot to provide."""
    w, proPersonal = chatTab()
    assert proPersonal.enabled == True

    chatView = w.findItem("chatView")
    assert _container(chatView) is not None
    assert _container(chatView).property("embedded") == True
    assert chatView.findChild(QObject, "discussView") is not None
    assert chatView.findChild(QObject, "planView") is not None

    # The hamburger is the only way into the account drawer, and the drawer is
    # the only way to clear data, switch case or log out.
    hamburger = chatView.findChild(QObject, "hamburgerButton")
    assert hamburger is None or hamburger.property("visible") == False
    drawer = _container(chatView).property("drawer")
    assert drawer is None or drawer.property("visible") == False


def test_case_the_coach_cannot_open_says_why(chatTab):
    """C1/C3: a disabled tab that renders nothing reads as a broken feature."""
    w, proPersonal = chatTab(owned=False)
    assert proPersonal.enabled == False

    chatView = w.findItem("chatView")
    assert _container(chatView) is None
    texts = [
        x.property("text")
        for x in chatView.findChildren(QObject)
        if x.property("text") is not None
    ]
    assert proPersonal.disabledReason in texts




# [Oracle: R-0048]
def test_a_release_build_offers_no_chat_tab(chatTab):
    """Beta-only until it ships: a release build must not show the tab at all,
    not even disabled with a reason."""
    from pkdiagram import version

    w, _ = chatTab()
    chat = w.findItem("chatTabButton")
    assert chat is not None, "no Chat tab to gate"

    assert chat.property("visible") == version.IS_BETA


# [Oracle: R-0005]
def test_the_embedded_chat_actually_renders_its_controls(chatTab):
    """The tab hosting the component is not the same as the chat being usable:
    a throw during the view's construction leaves the tab present and blank."""
    w, _ = chatTab()
    chatView = w.findItem("chatView")
    for name in ("discussView", "chatTextEdit", "chatSendButton", "statementsList"):
        item = chatView.findChild(QObject, name)
        assert item is not None, f"{name} is missing from the embedded chat"

    assert chatView.findChild(QObject, "chatTextEdit").property("visible") == True
