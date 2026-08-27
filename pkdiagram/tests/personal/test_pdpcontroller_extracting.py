"""The in-flight extraction state.

[Oracle: R-0043]
"""

from unittest.mock import patch

from pkdiagram.personal.pdpcontroller import PDPController


def test_the_extract_button_is_withdrawn_while_an_extraction_runs(personalApp):
    """The server admits one extraction at a time, so offering the button
    during one turns an ordinary second click into a CONFLICT the person has
    to read."""
    controller = personalApp.pdpController
    assert controller.extracting == False

    controller._setExtracting(True)
    assert controller.extracting == True

    controller._setExtracting(False)
    assert controller.extracting == False
