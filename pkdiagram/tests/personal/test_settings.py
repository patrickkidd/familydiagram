from unittest.mock import MagicMock

import pytest

from pkdiagram import util
from pkdiagram.personal.settings import Settings


pytestmark = [
    pytest.mark.component("Personal"),
]


@pytest.fixture
def settings(qApp):
    qsettings = MagicMock()
    qsettings.value = MagicMock(return_value=None)
    return Settings(qsettings)


def test_value_delegates_to_qsettings(settings):
    settings._qsettings.value.return_value = "hello"
    assert settings.value("key") == "hello"
    settings._qsettings.value.assert_called_with("key", defaultValue=None)


def test_value_with_default(settings):
    settings._qsettings.value.return_value = False
    settings.value("missing", False)
    settings._qsettings.value.assert_called_with("missing", defaultValue=False)


def test_setValue_delegates_and_emits(settings):
    changed = util.Condition(settings.valueChanged)
    settings.setValue("autoReadAloud", True)
    settings._qsettings.setValue.assert_called_with("autoReadAloud", True)
    assert changed.callCount == 1
    assert changed.callArgs[0][0] == "autoReadAloud"
