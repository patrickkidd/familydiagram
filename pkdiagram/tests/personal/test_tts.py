from unittest.mock import patch, MagicMock

import pytest

from PyQt5.QtTextToSpeech import QTextToSpeech, QVoice
from pkdiagram import util
from pkdiagram.personal import PersonalAppController


pytestmark = [
    pytest.mark.component("Personal"),
]


def test_sayAtIndex_sets_index_and_calls_say(personalApp: PersonalAppController):
    changed = util.Condition(personalApp.ttsPlayingIndexChanged)
    with (
        patch.object(personalApp._tts, "say") as say,
        patch.object(personalApp._tts, "stop"),
    ):
        personalApp.sayAtIndex("hello", 3)
    assert personalApp.ttsPlayingIndex == 3
    assert changed.callCount >= 1
    say.assert_called_once_with("hello")


def test_stopSpeaking_calls_stop(personalApp: PersonalAppController):
    with patch.object(personalApp._tts, "stop") as stop:
        personalApp.stopSpeaking()
    stop.assert_called_once()


def test_state_ready_resets_index(personalApp: PersonalAppController):
    personalApp._ttsPlayingIndex = 5
    changed = util.Condition(personalApp.ttsPlayingIndexChanged)
    personalApp._onTtsStateChanged(QTextToSpeech.Ready)
    assert personalApp.ttsPlayingIndex == -1
    assert changed.callCount == 1


def test_state_error_resets_index(personalApp: PersonalAppController):
    personalApp._ttsPlayingIndex = 2
    changed = util.Condition(personalApp.ttsPlayingIndexChanged)
    personalApp._onTtsStateChanged(QTextToSpeech.BackendError)
    assert personalApp.ttsPlayingIndex == -1
    assert changed.callCount == 1


def test_state_speaking_does_not_reset_index(personalApp: PersonalAppController):
    personalApp._ttsPlayingIndex = 4
    changed = util.Condition(personalApp.ttsPlayingIndexChanged)
    personalApp._onTtsStateChanged(QTextToSpeech.Speaking)
    assert personalApp.ttsPlayingIndex == 4
    assert changed.callCount == 0


def test_sayAtIndex_stops_previous(personalApp: PersonalAppController):
    with (
        patch.object(personalApp._tts, "stop") as stop,
        patch.object(personalApp._tts, "say"),
    ):
        personalApp.sayAtIndex("first", 0)
        personalApp.sayAtIndex("second", 1)
    assert stop.call_count == 2
    assert personalApp.ttsPlayingIndex == 1


def test_ttsVoices_returns_list_of_dicts(personalApp: PersonalAppController):
    voices = personalApp.ttsVoices
    assert isinstance(voices, list)
    if voices:
        assert "name" in voices[0]
        assert "locale" in voices[0]


def test_setTtsVoice_persists_to_settings(personalApp: PersonalAppController):
    voices = personalApp.ttsVoices
    if not voices:
        pytest.skip("No TTS voices available")
    name = voices[0]["name"]
    changed = util.Condition(personalApp.ttsVoiceChanged)
    personalApp.setTtsVoice(name)
    assert personalApp.ttsVoiceName == name
    assert changed.callCount == 1
    assert personalApp._settings.value("ttsVoiceName") == name


def test_initTtsVoice_restores_saved(personalApp: PersonalAppController):
    voices = personalApp.ttsVoices
    if not voices:
        pytest.skip("No TTS voices available")
    name = voices[0]["name"]
    personalApp._settings.setValue("ttsVoiceName", name)
    personalApp._initTtsVoice()
    assert personalApp._tts.voice().name() == name


def test_openSystemVoiceSettings(personalApp: PersonalAppController):
    with patch("subprocess.Popen") as popen:
        personalApp.openSystemVoiceSettings()
    popen.assert_called_once()


def test_previewVoice(personalApp: PersonalAppController):
    voices = personalApp.ttsVoices
    if not voices:
        pytest.skip("No TTS voices available")
    name = voices[0]["name"]
    with patch.object(personalApp._tts, "say") as say:
        personalApp.previewVoice(name)
    assert personalApp.ttsVoiceName == name
    say.assert_called_once_with("Hello, this is a preview of my voice.")
