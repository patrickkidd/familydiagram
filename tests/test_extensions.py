import sys
import traceback

import mock

from pkdiagram.pyqt import QWidget
from pkdiagram import extensions


def test_findTheMainWindow():
    window = QWidget()
    window.session = None
    app = mock.Mock()
    app.topLevelWidgets.return_value = [window]
    with mock.patch("pkdiagram.pyqt.QApplication.instance", return_value=app):
        assert extensions.findTheMainWindow() is window


def test_datadog_excepthook():
    try:
        raise ValueError("This is a simulated error for testing")
    except ValueError as e:
        # Capture the exception and its traceback
        etype, value, tb = sys.exc_info()

    mainWindow = mock.Mock()

    with mock.patch.object(extensions, "findTheMainWindow", return_value=mainWindow):
        extensions.datadog_excepthook(etype, value, tb)
    assert mainWindow.session.error.call_count == 1
    assert mainWindow.session.error.call_args[0][1] == value
