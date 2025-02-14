import logging

import pytest
import mock

from pkdiagram.views import CopilotView

_log = logging.getLogger(__name__)


@pytest.fixture
def view(qtbot, scene, qmlEngine):
    qmlEngine.setScene(scene)

    _view = CopilotView(qmlEngine)
    _view.resize(600, 800)
    _view.setScene(scene)
    _view.show()
    qtbot.addWidget(_view)
    qtbot.waitActive(_view)

    yield _view

    _view.setScene(None)
    _view.hide()
    _view.deinit()


# def test_init(qApp, view):
#     qApp.exec()
#     assert view
