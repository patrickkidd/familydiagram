import os.path
import json
import logging
import contextlib
from dataclasses import asdict

import pytest
from mock import patch

# from tests.models.test_copilotengine import copilot

from pkdiagram.pyqt import QTimer, QQuickWidget, QUrl, QApplication
from pkdiagram import util
from pkdiagram.therapist import TherapistAppController
from pkdiagram.therapist.therapist import Response, Therapist, Discussion, Statement

from tests.widgets.qmlwidgets import QmlHelper


_log = logging.getLogger(__name__)


@pytest.fixture
def controller(qmlEngine):
    controller = TherapistAppController(QApplication.instance())
    with contextlib.ExitStack() as stack:
        # stack.enter_context(
        #     patch.object(
        #         controller.therapist,
        #         "_threads",
        #         [
        #             Discussion(id=1, summary="my dog flew away", user_id=123),
        #             Discussion(id=2, summary="clouds ate my cake", user_id=123),
        #         ],
        #     )
        # )
        stack.enter_context(patch.object(controller.therapist, "_refreshDiscussion"))
        stack.enter_context(patch.object(controller.therapist, "_refreshPDP"))

        controller.init(qmlEngine)

        yield controller


@pytest.fixture
def view(qtbot, test_session, qmlEngine, controller: TherapistAppController):

    FPATH = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "pkdiagram",
        "resources",
        "qml",
        "Therapist",
        "LearnView.qml",
    )

    _view = QQuickWidget(qmlEngine, None)
    _view.setSource(QUrl.fromLocalFile(FPATH))
    _view.setFormat(util.SURFACE_FORMAT)

    _view.setResizeMode(QQuickWidget.SizeRootObjectToView)
    _view.resize(600, 800)
    _view.show()
    qtbot.addWidget(_view)
    qtbot.waitActive(_view)

    yield _view

    _view.hide()
    _view.setSource(QUrl(""))


def test_init_with_pdp(view: QQuickWidget, controller: TherapistAppController):
    pdpList = view.rootObject().property("pdpList")
    assert pdpList.property("numDelegates") == 0

    controller.therapist.setPDP(
        {
            "people": [{"id": -1, "name": "Alice"}, {"id": -2, "name": "Bob"}],
            "events": [
                {"id": -3, "description": "Event 1"},
                {"id": -4, "description": "Event 2"},
            ],
        }
    )
    assert util.waitForCondition(lambda: pdpList.property("numDelegates") == 4) == True


def test_accept(view: QQuickWidget, controller: TherapistAppController):
    assert False


def test_reject(view: QQuickWidget, controller: TherapistAppController):
    assert False
