"""Pro's Preferences, which is where Pro's app-wide settings live."""

import pytest
from mock import MagicMock, patch

from pkdiagram import version
from pkdiagram.mainwindow.preferences import Preferences
from pkdiagram.personal.discussioncontroller import DiscussionController
from pkdiagram.pyqt import QSettings, QWidget


@pytest.fixture
def preferences(qtbot, tmp_path):
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    prefs = QSettings(QSettings.IniFormat, QSettings.UserScope, "test", "prefs")
    mw = QWidget()
    mw.session = MagicMock()
    mw.autoSaveManager = MagicMock()
    mw.document = None
    mw.scene = None
    qtbot.addWidget(mw)
    dialog = Preferences(mw)
    qtbot.addWidget(dialog)
    dialog.init(prefs)
    yield dialog, prefs
    dialog.deleteLater()


# [Oracle: R-0050]
def test_the_coaching_style_defaults_to_premium(preferences):
    dialog, _ = preferences
    assert dialog.ui.coachingStyleBox.currentData() == DiscussionController.DEFAULT_MODEL

    assert dialog.ui.coachingStyleBox.currentData() == "opus-5"


# [Oracle: R-0050]
def test_choosing_a_style_is_what_the_embedded_chat_reads(preferences):
    """One setting, so Pro's Preferences and the chat cannot disagree."""
    dialog, prefs = preferences
    other = next(
        x["id"]
        for x in DiscussionController.AVAILABLE_MODELS
        if x["id"] != DiscussionController.DEFAULT_MODEL
    )
    dialog.ui.coachingStyleBox.setCurrentIndex(
        dialog.ui.coachingStyleBox.findData(other)
    )
    assert prefs.value(DiscussionController.MODEL_KEY) == other

    # and it is no longer a candidate for the one-time default migration
    assert prefs.value(DiscussionController.MODEL_MIGRATED_KEY) in (True, "true")


# [Oracle: R-0048]
def test_the_coaching_style_is_offered_only_in_beta(preferences):
    dialog, _ = preferences
    assert dialog.ui.coachingGroupBox.isVisibleTo(dialog) == version.IS_BETA
