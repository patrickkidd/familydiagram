import logging
import subprocess

from PyQt5.QtTextToSpeech import QTextToSpeech, QVoice
from PyQt5.QtCore import QLocale

from _pkdiagram import CUtil
from pkdiagram import util
from pkdiagram.pyqt import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from pkdiagram.personal.settings import Settings

_log = logging.getLogger(__name__)


class TextToSpeech(QObject):
    """Reads statements aloud. The QTextToSpeech backend is created on first
    use so a launch that never speaks doesn't pay for it."""

    playingIndexChanged = pyqtSignal()
    finished = pyqtSignal()
    voiceChanged = pyqtSignal()
    autoReadAloudChanged = pyqtSignal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._speech = None
        self._playingIndex = -1
        if self._settings.value("autoReadAloud", False):
            self._ensure()

    def _ensure(self):
        if self._speech is not None:
            return
        self._speech = QTextToSpeech(self)
        self._speech.stateChanged.connect(self._onStateChanged)
        self._initVoice()

    def _initVoice(self):
        saved = self._settings.value("ttsVoiceName")
        if saved:
            voice, locale = self._findVoice(saved)
            if voice:
                self._speech.setLocale(locale)
                self._speech.setVoice(voice)
                _log.debug(f"TTS voice restored: {voice.name()}")
                return
        for voice in self._speech.availableVoices():
            if voice.gender() == QVoice.Female:
                self._speech.setVoice(voice)
                _log.debug(f"TTS voice: {voice.name()}")
                return
        _log.debug("No female voice found, using default")

    def _findVoice(self, name):
        for locale in self._speech.availableLocales():
            if locale.language() != QLocale.English:
                continue
            self._speech.setLocale(locale)
            for voice in self._speech.availableVoices():
                if voice.name() == name:
                    return voice, locale
        return None, None

    def _collectVoices(self):
        if self._speech is None:
            return []
        origLocale = self._speech.locale()
        origVoice = self._speech.voice()
        voices = []
        seen = set()
        for locale in self._speech.availableLocales():
            if locale.language() != QLocale.English:
                continue
            self._speech.setLocale(locale)
            country = QLocale.countryToString(locale.country())
            localeLabel = f"English ({country})"
            for voice in self._speech.availableVoices():
                if voice.name() not in seen:
                    seen.add(voice.name())
                    voices.append({"name": voice.name(), "locale": localeLabel})
        self._speech.setLocale(origLocale)
        if origVoice.name():
            self._speech.setVoice(origVoice)
        return voices

    def _onStateChanged(self, state):
        if state in (QTextToSpeech.Ready, QTextToSpeech.BackendError):
            wasPlaying = self._playingIndex >= 0
            self._playingIndex = -1
            self.playingIndexChanged.emit()
            if wasPlaying and state == QTextToSpeech.Ready:
                self.finished.emit()

    @pyqtProperty(int, notify=playingIndexChanged)
    def playingIndex(self):
        return self._playingIndex

    @pyqtProperty(bool, notify=autoReadAloudChanged)
    def autoReadAloud(self):
        return bool(self._settings.value("autoReadAloud", False))

    @pyqtSlot(bool)
    def setAutoReadAloud(self, enabled):
        self._settings.setValue("autoReadAloud", enabled)
        if enabled:
            self._ensure()
        self.autoReadAloudChanged.emit()

    @pyqtSlot(str, int)
    def say(self, text, index):
        self._ensure()
        self._speech.stop()
        self._playingIndex = index
        self.playingIndexChanged.emit()
        self._speech.say(text)

    @pyqtSlot()
    def stop(self):
        if self._speech is not None:
            self._speech.stop()

    @pyqtProperty("QVariantList", constant=True)
    def voices(self):
        return self._collectVoices()

    @pyqtProperty(str, notify=voiceChanged)
    def voiceName(self):
        if self._speech is None:
            return ""
        return self._speech.voice().name()

    @pyqtSlot(str)
    def setVoice(self, name):
        self._ensure()
        voice, locale = self._findVoice(name)
        if voice:
            self._speech.setLocale(locale)
            self._speech.setVoice(voice)
            self._settings.setValue("ttsVoiceName", name)
            self.voiceChanged.emit()
            _log.debug(f"TTS voice set to: {name}")

    @pyqtSlot(str)
    def preview(self, name):
        self._ensure()
        self.setVoice(name)
        self._speech.say("Hello, this is a preview of my voice.")

    @pyqtSlot()
    def openSystemSettings(self):
        if util.IS_IOS:
            CUtil.openNativeUrl("App-Prefs:root=ACCESSIBILITY&path=SPEECH")
        else:
            subprocess.Popen(
                [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.universalaccess?SpokenContent",
                ]
            )
