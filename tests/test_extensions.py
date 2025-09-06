import sys

from mock import patch, MagicMock

from pkdiagram import extensions


def test_datadog_excepthook():
    try:
        raise ValueError("This is a simulated error for testing")
    except ValueError as e:
        # Capture the exception and its traceback
        etype, value, tb = sys.exc_info()

    with patch("pkdiagram.extensions._activeSession", MagicMock()) as session:
        extensions.datadog_excepthook(etype, value, tb)
    assert session.error.call_count == 1
    assert session.error.call_args[0][1] == value
