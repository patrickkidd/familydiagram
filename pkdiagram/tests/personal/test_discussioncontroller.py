import pytest

from btcopilot.llmutil import MODEL_ALIASES, DEFAULT_RESPONSE_MODEL_ALIAS

from pkdiagram.personal.discussioncontroller import DiscussionController
from pkdiagram.personal.settings import Settings


pytestmark = [
    pytest.mark.component("Personal"),
]


class Prefs:
    """In-memory stand-in for the QSettings store behind Settings."""

    def __init__(self, values=None):
        self.values = dict(values or {})

    def value(self, key, defaultValue=None):
        return self.values.get(key, defaultValue)

    def setValue(self, key, value):
        self.values[key] = value


def controller(prefs):
    """One launch of the app against a prefs store."""
    return DiscussionController(None, Settings(prefs))


def test_menu_offers_the_new_premium_first(qApp):
    assert [x["id"] for x in controller(Prefs()).availableModels] == [
        "opus-5",
        "opus-4.6",
        "gemini-2.5-flash",
    ]


def test_menu_ids_are_server_aliases(qApp):
    models = controller(Prefs()).availableModels
    assert [x for x in models if x["id"] not in MODEL_ALIASES] == []
    assert DiscussionController.DEFAULT_MODEL == DEFAULT_RESPONSE_MODEL_ALIAS


def test_fresh_store_defaults_to_opus_5_without_writing(qApp):
    prefs = Prefs()
    assert controller(prefs).responseModel == "opus-5"
    assert prefs.values == {}


def test_old_default_migrates_once(qApp):
    prefs = Prefs({"responseModel": "opus-4.6"})
    assert controller(prefs).responseModel == "opus-5"
    assert prefs.values["responseModelMigrated"] is True


def test_explicit_old_model_survives_relaunch(qApp):
    prefs = Prefs({"responseModel": "opus-4.6"})
    controller(prefs)
    controller(prefs).setResponseModel("opus-4.6")
    assert controller(prefs).responseModel == "opus-4.6"


def test_migration_leaves_a_chosen_model_alone(qApp):
    prefs = Prefs({"responseModel": "gemini-2.5-flash"})
    assert controller(prefs).responseModel == "gemini-2.5-flash"
