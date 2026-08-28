from unittest.mock import patch, MagicMock

import pytest

from PyQt5.QtTextToSpeech import QTextToSpeech, QVoice
from pkdiagram import util
from pkdiagram.personal import PersonalAppController


pytestmark = [
    pytest.mark.component("Personal"),
]


def test_sayAtIndex_sets_index_and_calls_say(personalApp: PersonalAppController):
    personalApp.tts._ensure()
    changed = util.Condition(personalApp.tts.playingIndexChanged)
    with (
        patch.object(personalApp.tts._speech, "say") as say,
        patch.object(personalApp.tts._speech, "stop"),
    ):
        personalApp.tts.say("hello", 3)
    assert personalApp.tts.playingIndex == 3
    assert changed.callCount >= 1
    say.assert_called_once_with("hello")


def test_stopSpeaking_calls_stop(personalApp: PersonalAppController):
    personalApp.tts._ensure()
    with patch.object(personalApp.tts._speech, "stop") as stop:
        personalApp.tts.stop()
    stop.assert_called_once()


def test_state_ready_resets_index(personalApp: PersonalAppController):
    personalApp.tts._playingIndex = 5
    changed = util.Condition(personalApp.tts.playingIndexChanged)
    personalApp.tts._onStateChanged(QTextToSpeech.Ready)
    assert personalApp.tts.playingIndex == -1
    assert changed.callCount == 1


def test_state_error_resets_index(personalApp: PersonalAppController):
    personalApp.tts._playingIndex = 2
    changed = util.Condition(personalApp.tts.playingIndexChanged)
    personalApp.tts._onStateChanged(QTextToSpeech.BackendError)
    assert personalApp.tts.playingIndex == -1
    assert changed.callCount == 1


def test_state_speaking_does_not_reset_index(personalApp: PersonalAppController):
    personalApp.tts._playingIndex = 4
    changed = util.Condition(personalApp.tts.playingIndexChanged)
    personalApp.tts._onStateChanged(QTextToSpeech.Speaking)
    assert personalApp.tts.playingIndex == 4
    assert changed.callCount == 0


def test_sayAtIndex_stops_previous(personalApp: PersonalAppController):
    personalApp.tts._ensure()
    with (
        patch.object(personalApp.tts._speech, "stop") as stop,
        patch.object(personalApp.tts._speech, "say"),
    ):
        personalApp.tts.say("first", 0)
        personalApp.tts.say("second", 1)
    assert stop.call_count == 2
    assert personalApp.tts.playingIndex == 1


def test_ttsVoices_returns_list_of_dicts(personalApp: PersonalAppController):
    voices = personalApp.tts.voices
    assert isinstance(voices, list)
    if voices:
        assert "name" in voices[0]
        assert "locale" in voices[0]


def test_setTtsVoice_persists_to_settings(personalApp: PersonalAppController):
    voices = personalApp.tts.voices
    if not voices:
        pytest.skip("No TTS voices available")
    name = voices[0]["name"]
    changed = util.Condition(personalApp.tts.voiceChanged)
    personalApp.tts.setVoice(name)
    assert personalApp.tts.voiceName == name
    assert changed.callCount == 1
    assert personalApp._settings.value("ttsVoiceName") == name


def test_initTtsVoice_restores_saved(personalApp: PersonalAppController):
    personalApp.tts._ensure()
    voices = personalApp.tts.voices
    if not voices:
        pytest.skip("No TTS voices available")
    name = voices[0]["name"]
    personalApp._settings.setValue("ttsVoiceName", name)
    personalApp.tts._initVoice()
    assert personalApp.tts._speech.voice().name() == name


def test_openSystemVoiceSettings(personalApp: PersonalAppController):
    with patch("subprocess.Popen") as popen:
        personalApp.tts.openSystemSettings()
    popen.assert_called_once()


def test_previewVoice(personalApp: PersonalAppController):
    personalApp.tts._ensure()
    voices = personalApp.tts.voices
    if not voices:
        pytest.skip("No TTS voices available")
    name = voices[0]["name"]
    with patch.object(personalApp.tts._speech, "say") as say:
        personalApp.tts.preview(name)
    assert personalApp.tts.voiceName == name
    say.assert_called_once_with("Hello, this is a preview of my voice.")
