import os.path
import logging
import contextlib

import pytest
import mock

# from tests.models.test_copilotengine import copilot

from pkdiagram.pyqt import QWidget, QUrl, QHBoxLayout, QTimer
from pkdiagram import util
from pkdiagram.therapist import TherapistView
from pkdiagram.app import Session


class TestTherapistView(TherapistView):
    pass


_log = logging.getLogger(__name__)


@pytest.fixture
def view(qtbot):
    session = Session()
    # session.init(sessionData=test_session.account_editor_dict())

    FPATH = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "pkdiagram",
        "resources",
        "qml",
        "CopilotView.qml",
    )
    _view = TestTherapistView(session)
    _view.resize(600, 800)
    _view.show()
    qtbot.addWidget(_view)
    qtbot.waitActive(_view)

    yield _view

    _view.hide()
    _view.deinit()


def test_init(view):
    pass
