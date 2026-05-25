import base64
import json
import logging
import os
import pickle
import tempfile
from typing import Callable

from btcopilot.schema import (
    EventKind,
    DiagramData,
    PDP,
    asdict,
    from_dict,
    VariableShift,
    RelationshipKind,
    DateCertainty,
)
from PyQt5.QtTextToSpeech import QTextToSpeech, QVoice
from PyQt5.QtMultimedia import QAudioRecorder, QAudioEncoderSettings
from pkdiagram.personal.commands import HandlePDPItem, PDPAction
from pkdiagram.personal.settings import Settings
from _pkdiagram import CUtil
from pkdiagram import pepper, util
from pkdiagram.app import AppConfig
from pkdiagram.pyqt import (
    QObject,
    QApplication,
    QQmlEngine,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
    QNetworkReply,
    QNetworkRequest,
    QNetworkAccessManager,
    QQuickItem,
    QUrl,
    QMessageBox,
    QInputDialog,
    QUndoStack,
    QVariant,
    QFileDialog,
)
from PyQt5.QtCore import QLocale, QByteArray
from pkdiagram.app import Session, Analytics
from pkdiagram.personal.models import Discussion
from pkdiagram.server_types import Diagram
from pkdiagram.scene import Scene, Person, Event, Marriage, Emotion
from pkdiagram.models import SceneModel, PeopleModel
from pkdiagram.views import EventForm
from pkdiagram.personal.sarfgraphmodel import SARFGraphModel
from pkdiagram.personal.shakedetector import ShakeDetector
from pkdiagram.personal.clustermodel import ClusterModel

_log = logging.getLogger(__name__)


class PersonalAppController(QObject):
    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(str, arguments=["statement"])
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    discussionsChanged = pyqtSignal()
    pdpChanged = pyqtSignal()
    diagramChanged = pyqtSignal()
    diagramsChanged = pyqtSignal()
    statementsChanged = pyqtSignal()
    eventFormDoneEditing = pyqtSignal()

    journalImportStarted = pyqtSignal()
    journalImportCompleted = pyqtSignal(QVariant, arguments=["summary"])
    journalImportFailed = pyqtSignal(str, arguments=["error"])

    extractStarted = pyqtSignal()
    extractCompleted = pyqtSignal(QVariant, arguments=["summary"])
    extractFailed = pyqtSignal(str, arguments=["error"])

    ttsPlayingIndexChanged = pyqtSignal()
    ttsFinished = pyqtSignal()
    ttsVoiceChanged = pyqtSignal()
    autoReadAloudChanged = pyqtSignal()
    responseModelChanged = pyqtSignal()

    transcriptionReady = pyqtSignal(str, arguments=["text"])
    transcriptionFailed = pyqtSignal(str, arguments=["error"])
    recordingFailed = pyqtSignal(str, arguments=["error"])

    def __init__(self, undoStack=None, parent=None):
        super().__init__(parent)

        self.app = QApplication.instance()
        self._diagram: Diagram | None = None
        self._diagrams: list[dict] = []
        self._discussions = []
        self._currentDiscussion: Discussion | None = None
        self._dirty: bool = False  # conversation past last accepted extraction
        self._sentSinceExtract: bool = False
        # Highest Statement.order the last extract covered, as reported by the
        # server. Echoed back on commit-pdp so the cursor advances to the
        # exact extraction being accepted, not whatever the server's pending
        # value happens to hold after a concurrent re-extract (FD-331).
        self._pendingExtractedThroughOrder: int | None = None
        self._pdp: dict | None = None
        self._rootObject = None
        self._engine: QQmlEngine | None = None
        self.scene = None
        self._undoStack = undoStack if undoStack else QUndoStack(self)

        self.util = self.app.qmlUtil()  # should be local, not global

        self.analytics = Analytics(datadog_api_key=pepper.DATADOG_API_KEY)
        self.session = Session(self.analytics)
        self.session.changed.connect(self.onSessionChanged)

        self.appConfig = AppConfig(self, prefsName="personal.alaskafamilysystems.com")
        self.sceneModel = SceneModel(self)
        self.sceneModel.session = self.session
        self.peopleModel = PeopleModel(self)
        self.sarfGraphModel = SARFGraphModel(self)
        self.clusterModel = ClusterModel(self.session, self)
        self.pdpChanged.connect(self.sarfGraphModel.refresh)
        self.diagramChanged.connect(self._onDiagramChanged)
        self.clusterModel.clustersDetected.connect(self._onClustersDetected)
        self.eventForm = None  # EventForm (from PersonalContainer drawer)
        self.shakeDetector = ShakeDetector(self)
        self.shakeDetector.shakeDetected.connect(self.undo)
        self._saving = False
        self._saveQueue = []
        self._settings = Settings(self.app.prefs(), self)
        self._tts = None
        self._ttsPlayingIndex = -1
        if self._settings.value("autoReadAloud", False):
            self._ensureTts()

        # Voice recording — lazy init to avoid activating AVAudioSession at startup
        self._audioRecorder = None
        self._recordingFilePath = ""
        self._networkManager = QNetworkAccessManager(self)

    def _ensureTts(self):
        if self._tts is not None:
            return
        self._tts = QTextToSpeech(self)
        self._tts.stateChanged.connect(self._onTtsStateChanged)
        self._initTtsVoice()

    def _initTtsVoice(self):
        saved = self._settings.value("ttsVoiceName")
        if saved:
            voice, locale = self._findVoice(saved)
            if voice:
                self._tts.setLocale(locale)
                self._tts.setVoice(voice)
                _log.debug(f"TTS voice restored: {voice.name()}")
                return
        for voice in self._tts.availableVoices():
            if voice.gender() == QVoice.Female:
                self._tts.setVoice(voice)
                _log.debug(f"TTS voice: {voice.name()}")
                return
        _log.debug("No female voice found, using default")

    def _findVoice(self, name):
        for locale in self._tts.availableLocales():
            if locale.language() != QLocale.English:
                continue
            self._tts.setLocale(locale)
            for voice in self._tts.availableVoices():
                if voice.name() == name:
                    return voice, locale
        return None, None

    def _collectVoices(self):
        if self._tts is None:
            return []
        origLocale = self._tts.locale()
        origVoice = self._tts.voice()
        voices = []
        seen = set()
        for locale in self._tts.availableLocales():
            if locale.language() != QLocale.English:
                continue
            self._tts.setLocale(locale)
            country = QLocale.countryToString(locale.country())
            localeLabel = f"English ({country})"
            for voice in self._tts.availableVoices():
                if voice.name() not in seen:
                    seen.add(voice.name())
                    voices.append({"name": voice.name(), "locale": localeLabel})
        self._tts.setLocale(origLocale)
        if origVoice.name():
            self._tts.setVoice(origVoice)
        return voices

    def _onTtsStateChanged(self, state):
        if state in (QTextToSpeech.Ready, QTextToSpeech.BackendError):
            wasPlaying = self._ttsPlayingIndex >= 0
            self._ttsPlayingIndex = -1
            self.ttsPlayingIndexChanged.emit()
            if wasPlaying and state == QTextToSpeech.Ready:
                self.ttsFinished.emit()

    def init(self, engine: QQmlEngine):
        engine.rootContext().setContextProperty("CUtil", CUtil.instance())
        engine.rootContext().setContextProperty("util", self.util)
        engine.rootContext().setContextProperty("session", self.session)
        engine.rootContext().setContextProperty("personalApp", self)
        engine.rootContext().setContextProperty("sceneModel", self.sceneModel)
        engine.rootContext().setContextProperty("peopleModel", self.peopleModel)
        engine.rootContext().setContextProperty("sarfGraphModel", self.sarfGraphModel)
        engine.rootContext().setContextProperty("clusterModel", self.clusterModel)
        engine.objectCreated[QObject, QUrl].connect(self.onQmlObjectCreated)
        self._engine = engine
        self.analytics.init()
        self.appConfig.init()
        self.session.setQmlEngine(engine)
        lastSessionData = self.appConfig.get("lastSessionData", pickled=True)
        if lastSessionData and not self.appConfig.wasTamperedWith:
            self.session.init(sessionData=lastSessionData)
        else:
            self.session.init()

    def deinit(self):
        self.shakeDetector.stop()
        self.pdpChanged.disconnect(self.sarfGraphModel.refresh)
        self.diagramChanged.disconnect(self._onDiagramChanged)
        self.clusterModel.clustersDetected.disconnect(self._onClustersDetected)
        self.sarfGraphModel.deinit()
        self.clusterModel.deinit()
        self.analytics.init()
        self.session.deinit()
        if self.eventForm:
            self.eventForm.deinit()
        self._engine = None

    def onQmlObjectCreated(self, rootObject: QQuickItem, url: QUrl):
        if self.eventForm and self.scene:
            self.eventForm.setScene(self.scene)

    def onEventFormSaved(self):
        self.saveDiagram()

    @pyqtSlot(QQuickItem)
    def initEventForm(self, eventFormItem: QQuickItem):
        if self.eventForm is None:
            self.eventForm = EventForm(eventFormItem, self)
            self.eventForm.saved.connect(self.onEventFormSaved)
            self.eventForm.doneEditing.connect(self.eventFormDoneEditing)
            if self.scene:
                self.eventForm.setScene(self.scene)

    @pyqtSlot(int)
    def editEvent(self, eventId: int):
        if not self.eventForm or not self.scene:
            return
        event = self.scene.find(id=eventId)
        if event:
            self.eventForm.editEvents([event])

    @pyqtSlot(int)
    def deleteEvent(self, eventId: int):
        if not self.scene:
            return
        event = self.scene.find(id=eventId)
        if event:
            self.scene.removeItem(event, undo=True)
            self.saveDiagram()

    @pyqtSlot()
    def undo(self):
        if self.scene:
            self.scene.undo()
            self.saveDiagram()

    def _withSaveGuard(self, fn):
        if self._saving:
            self._saveQueue.append(fn)
            return None
        self._saving = True
        try:
            return fn()
        finally:
            self._saving = False
            if self._saveQueue:
                self._withSaveGuard(self._saveQueue.pop(0))

    def saveDiagram(self):
        if not self._diagram or not self.scene:
            return

        # Snapshot baseline for the merge: Personal's Scene view at the
        # last successful save (or, on first save, what was loaded at
        # open). NOT the canonical server state, NOT the post-merge bytes
        # — those may contain other-client items Personal's Scene never
        # loaded, which would get interpreted as deletes on the next save.
        # Plan: doc/plans/2026-05-01--mvp-merge-fix/README.md
        snapshotBytes = (
            getattr(self._diagram, "_lastSavedSnapshot", None) or self._diagram.data
        )
        openSnapshot = pickle.loads(snapshotBytes) if snapshotBytes else {}

        # Capture Scene state NOW (caller-side) so we can stash it as the
        # next-save snapshot after Diagram.save returns success.
        currentSceneBytes = pickle.dumps(asdict(self.scene.diagramData()))

        def _do():
            def applyChange(diagramData: DiagramData):
                sceneDiagramData = self.scene.diagramData()
                # Scene collections — snapshot-diff merge. For each field,
                # take server's copy unless the user actually edited the
                # item (snapshot vs local differ), preventing a stale
                # snapshot from clobbering concurrent edits.
                for fname in DiagramData.SCENE_COLLECTION_FIELDS:
                    snapshot_field = openSnapshot.get(fname, [])
                    local_field = getattr(sceneDiagramData, fname)
                    setattr(
                        diagramData,
                        fname,
                        DiagramData.apply_local_changes(
                            getattr(diagramData, fname),
                            snapshot_field,
                            local_field,
                        ),
                    )
                diagramData.version = sceneDiagramData.version
                diagramData.versionCompat = sceneDiagramData.versionCompat
                diagramData.name = sceneDiagramData.name
                diagramData.lastItemId = max(
                    diagramData.lastItemId, sceneDiagramData.lastItemId
                )
                diagramData.clusters = self.clusterModel.clusters
                diagramData.clusterCacheKey = self.clusterModel.cacheKey
                return diagramData

            success = self._diagram.save(
                self.session.server(), applyChange, lambda d: True, useJson=True
            )
            if success:
                # Capture Personal's Scene view as the merge baseline for
                # the next save. NOT the post-merge bytes (other-client
                # items would leak in and get treated as deletes later).
                self._diagram._lastSavedSnapshot = currentSceneBytes

        self._withSaveGuard(_do)

    def setScene(self, scene: Scene):
        self.scene = scene
        self.peopleModel.scene = scene
        self.sceneModel.scene = scene
        self.sarfGraphModel.scene = scene
        self.clusterModel.scene = scene
        # Load persisted clusters AFTER scene is set (scene setter clears clusters)
        if self._diagram:
            diagramData = self._diagram.getDiagramData()
            if diagramData.clusters:
                self.clusterModel.setClustersData(
                    diagramData.clusters, diagramData.clusterCacheKey
                )
        if self.eventForm:
            self.eventForm.setScene(scene)
        # Re-emit pdpChanged so committedPeople gets populated from the scene
        self.pdpChanged.emit()

    def exec(self, mw):
        self.app.exec()

    def onError(self, reply: QNetworkReply):
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
            self.serverDown.emit()
        else:
            self.serverError.emit(reply.errorString())

    def _onDiagramChanged(self):
        if self._diagram:
            self.clusterModel.diagramId = self._diagram.id
        else:
            self.clusterModel.diagramId = None

    def _onClustersDetected(self):
        self.saveDiagram()

    def onSessionChanged(self, oldFeatures, newFeatures):
        if self.session.isLoggedIn():
            self.appConfig.set("lastSessionData", self.session.data(), pickled=True)
            self.shakeDetector.start()
        else:
            self.appConfig.delete("lastSessionData")
            self.shakeDetector.stop()
        self.appConfig.write()

        if not self.session.user:
            self._diagram = None
            self._diagrams = []
            self._discussions = []
            self._pdp = {}
            self._currentDiscussion = None
        else:
            self._refreshDiagrams()
            self._refreshDiagram()
        self.discussionsChanged.emit()
        self.statementsChanged.emit()
        self.pdpChanged.emit()
        self.diagramChanged.emit()
        self.diagramsChanged.emit()

    @pyqtProperty(QObject, constant=True)
    def settings(self):
        return self._settings

    # Model selection

    AVAILABLE_MODELS = [
        {
            "id": "opus-4.6",
            "name": "Premium",
            "description": "Deeper observations and more nuanced coaching. Makes connections between family patterns. Takes a moment longer to respond.",
        },
        {
            "id": "gemini-2.5-flash",
            "name": "Standard",
            "description": "Quick, focused responses. Efficient at collecting family facts and keeping the conversation moving.",
        },
    ]
    DEFAULT_MODEL = "opus-4.6"

    @pyqtProperty("QVariantList", constant=True)
    def availableModels(self):
        return self.AVAILABLE_MODELS

    @pyqtProperty(str, notify=responseModelChanged)
    def responseModel(self):
        return (
            self._settings.value("responseModel", self.DEFAULT_MODEL)
            or self.DEFAULT_MODEL
        )

    @pyqtSlot(str)
    def setResponseModel(self, modelId: str):
        if modelId == self.responseModel:
            return
        self._settings.setValue("responseModel", modelId)
        self.responseModelChanged.emit()

    # TTS

    @pyqtProperty(int, notify=ttsPlayingIndexChanged)
    def ttsPlayingIndex(self):
        return self._ttsPlayingIndex

    @pyqtProperty(bool, notify=autoReadAloudChanged)
    def autoReadAloud(self):
        return bool(self._settings.value("autoReadAloud", False))

    @pyqtSlot(bool)
    def setAutoReadAloud(self, enabled):
        self._settings.setValue("autoReadAloud", enabled)
        if enabled:
            self._ensureTts()
        self.autoReadAloudChanged.emit()

    @pyqtSlot(str, int)
    def sayAtIndex(self, text, index):
        self._ensureTts()
        self._tts.stop()
        self._ttsPlayingIndex = index
        self.ttsPlayingIndexChanged.emit()
        self._tts.say(text)

    @pyqtSlot()
    def stopSpeaking(self):
        if self._tts is not None:
            self._tts.stop()

    @pyqtProperty("QVariantList", constant=True)
    def ttsVoices(self):
        return self._collectVoices()

    @pyqtProperty(str, notify=ttsVoiceChanged)
    def ttsVoiceName(self):
        if self._tts is None:
            return ""
        return self._tts.voice().name()

    @pyqtSlot(str)
    def setTtsVoice(self, name):
        self._ensureTts()
        voice, locale = self._findVoice(name)
        if voice:
            self._tts.setLocale(locale)
            self._tts.setVoice(voice)
            self._settings.setValue("ttsVoiceName", name)
            self.ttsVoiceChanged.emit()
            _log.debug(f"TTS voice set to: {name}")

    @pyqtSlot(str)
    def previewVoice(self, name):
        self._ensureTts()
        self.setTtsVoice(name)
        self._tts.say("Hello, this is a preview of my voice.")

    @pyqtSlot()
    def openSystemVoiceSettings(self):
        import subprocess

        if util.IS_IOS:
            CUtil.openNativeUrl("App-Prefs:root=ACCESSIBILITY&path=SPEECH")
        else:
            subprocess.Popen(
                [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.universalaccess?SpokenContent",
                ]
            )

    # Voice Recording & Transcription

    def _ensureAudioRecorder(self):
        if self._audioRecorder is None:
            self._audioRecorder = QAudioRecorder(self)

    @pyqtSlot()
    def startRecording(self):
        """Start recording audio via QAudioRecorder."""
        self._ensureAudioRecorder()
        try:
            tmpFile = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, prefix="fd_voice_"
            )
            self._recordingFilePath = tmpFile.name
            tmpFile.close()

            audioSettings = QAudioEncoderSettings()
            audioSettings.setCodec("audio/pcm")
            audioSettings.setSampleRate(16000)
            audioSettings.setChannelCount(1)

            self._audioRecorder.setEncodingSettings(audioSettings)
            self._audioRecorder.setOutputLocation(
                QUrl.fromLocalFile(self._recordingFilePath)
            )
            self._audioRecorder.record()
            _log.info(f"Started recording to {self._recordingFilePath}")
        except Exception as e:
            _log.error(f"Failed to start recording: {e}")
            self.recordingFailed.emit(str(e))

    @pyqtSlot()
    def cancelRecording(self):
        """Stop recording WITHOUT transcribing (e.g. short tap or drag-off)."""
        if self._audioRecorder is None:
            return
        self._audioRecorder.stop()
        _log.info(f"Cancelled recording: {self._recordingFilePath}")
        self._cleanupRecording(self._recordingFilePath)
        self._recordingFilePath = ""

    @pyqtSlot()
    def stopRecording(self):
        """Stop recording and begin transcription."""
        if self._audioRecorder is None:
            self.transcriptionFailed.emit("Recording file not found")
            return
        self._audioRecorder.stop()
        _log.info(f"Stopped recording: {self._recordingFilePath}")

        if not self._recordingFilePath or not os.path.exists(self._recordingFilePath):
            self.transcriptionFailed.emit("Recording file not found")
            return

        self._transcribeAudio(self._recordingFilePath)

    def _transcribeAudio(self, filePath: str):
        """Fetch AssemblyAI key from server, then upload audio for transcription."""
        # Fast path: env var for desktop development
        envKey = os.environ.get("ASSEMBLYAI_API_KEY", "")
        if envKey:
            self._uploadAudio(filePath, envKey)
            return

        def onSuccess(data):
            apiKey = data.get("api_key", "")
            if not apiKey:
                self.transcriptionFailed.emit("Server returned empty AssemblyAI key")
                self._cleanupRecording(filePath)
                return
            self._uploadAudio(filePath, apiKey)

        def onError():
            errorMsg = reply.errorString()
            _log.error(f"Failed to fetch AssemblyAI key: {errorMsg}")
            self.transcriptionFailed.emit(
                f"Failed to fetch transcription key: {errorMsg}"
            )
            self._cleanupRecording(filePath)

        reply = self.session.server().nonBlockingRequest(
            "GET",
            "/personal/assemblyai-key",
            data={},
            error=onError,
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    def _uploadAudio(self, filePath: str, apiKey: str):
        """Upload audio file to AssemblyAI."""
        try:
            with open(filePath, "rb") as f:
                audioData = f.read()
        except Exception as e:
            _log.error(f"Failed to read recording file: {e}")
            self.transcriptionFailed.emit(f"Failed to read recording: {e}")
            self._cleanupRecording(filePath)
            return

        uploadRequest = QNetworkRequest(QUrl("https://api.assemblyai.com/v2/upload"))
        uploadRequest.setRawHeader(
            QByteArray(b"authorization"), QByteArray(apiKey.encode())
        )
        uploadRequest.setRawHeader(
            QByteArray(b"content-type"), QByteArray(b"application/octet-stream")
        )

        uploadReply = self._networkManager.post(uploadRequest, QByteArray(audioData))
        uploadReply.finished.connect(
            lambda: self._onUploadFinished(uploadReply, apiKey, filePath)
        )

    def _onUploadFinished(self, reply: QNetworkReply, apiKey: str, filePath: str):
        """Handle upload response, then submit for transcription."""
        error = reply.error()
        if error != QNetworkReply.NoError:
            errorMsg = reply.errorString()
            _log.error(f"Audio upload failed: {errorMsg}")
            self.transcriptionFailed.emit(f"Upload failed: {errorMsg}")
            reply.deleteLater()
            self._cleanupRecording(filePath)
            return

        responseData = json.loads(bytes(reply.readAll()))
        reply.deleteLater()
        uploadUrl = responseData.get("upload_url", "")

        if not uploadUrl:
            self.transcriptionFailed.emit("Upload succeeded but no URL returned")
            self._cleanupRecording(filePath)
            return

        _log.info(f"Audio uploaded: {uploadUrl}")

        # Step 2: Submit transcription request
        transcriptRequest = QNetworkRequest(
            QUrl("https://api.assemblyai.com/v2/transcript")
        )
        transcriptRequest.setRawHeader(
            QByteArray(b"authorization"), QByteArray(apiKey.encode())
        )
        transcriptRequest.setRawHeader(
            QByteArray(b"content-type"), QByteArray(b"application/json")
        )

        requestBody = json.dumps({"audio_url": uploadUrl}).encode()
        transcriptReply = self._networkManager.post(
            transcriptRequest, QByteArray(requestBody)
        )
        transcriptReply.finished.connect(
            lambda: self._onTranscriptSubmitted(transcriptReply, apiKey, filePath)
        )

    def _onTranscriptSubmitted(self, reply: QNetworkReply, apiKey: str, filePath: str):
        """Handle transcription submission, then start polling."""
        error = reply.error()
        if error != QNetworkReply.NoError:
            errorMsg = reply.errorString()
            _log.error(f"Transcription request failed: {errorMsg}")
            self.transcriptionFailed.emit(f"Transcription request failed: {errorMsg}")
            reply.deleteLater()
            self._cleanupRecording(filePath)
            return

        responseData = json.loads(bytes(reply.readAll()))
        reply.deleteLater()
        transcriptId = responseData.get("id", "")

        if not transcriptId:
            self.transcriptionFailed.emit("No transcript ID returned")
            self._cleanupRecording(filePath)
            return

        _log.info(f"Transcription submitted: {transcriptId}")
        self._pollTranscription(transcriptId, apiKey, filePath)

    def _pollTranscription(self, transcriptId: str, apiKey: str, filePath: str):
        """Poll AssemblyAI for transcription completion."""
        from PyQt5.QtCore import QTimer

        pollUrl = QUrl(f"https://api.assemblyai.com/v2/transcript/{transcriptId}")
        pollRequest = QNetworkRequest(pollUrl)
        pollRequest.setRawHeader(
            QByteArray(b"authorization"), QByteArray(apiKey.encode())
        )

        pollReply = self._networkManager.get(pollRequest)
        pollReply.finished.connect(
            lambda: self._onPollFinished(pollReply, transcriptId, apiKey, filePath)
        )

    def _onPollFinished(
        self,
        reply: QNetworkReply,
        transcriptId: str,
        apiKey: str,
        filePath: str,
    ):
        """Handle poll response; re-poll if still processing."""
        from PyQt5.QtCore import QTimer

        error = reply.error()
        if error != QNetworkReply.NoError:
            errorMsg = reply.errorString()
            _log.error(f"Transcription poll failed: {errorMsg}")
            self.transcriptionFailed.emit(f"Poll failed: {errorMsg}")
            reply.deleteLater()
            self._cleanupRecording(filePath)
            return

        responseData = json.loads(bytes(reply.readAll()))
        reply.deleteLater()
        status = responseData.get("status", "")

        if status == "completed":
            text = responseData.get("text", "")
            _log.info(f"Transcription completed: {text[:80]}...")
            self.transcriptionReady.emit(text)
            self._cleanupRecording(filePath)
        elif status == "error":
            errorMsg = responseData.get("error", "Unknown transcription error")
            _log.error(f"Transcription error: {errorMsg}")
            self.transcriptionFailed.emit(errorMsg)
            self._cleanupRecording(filePath)
        else:
            # Still processing — poll again after 1 second
            QTimer.singleShot(
                1000, lambda: self._pollTranscription(transcriptId, apiKey, filePath)
            )

    def _cleanupRecording(self, filePath: str):
        """Remove temporary recording file."""
        try:
            if filePath and os.path.exists(filePath):
                os.unlink(filePath)
                _log.debug(f"Cleaned up recording file: {filePath}")
        except Exception as e:
            _log.warning(f"Failed to clean up recording file: {e}")

    # Diagram

    @pyqtProperty("QVariantList", notify=diagramsChanged)
    def diagrams(self):
        return list(self._diagrams)

    def _refreshDiagrams(self):
        if not self.session.user:
            return

        def onSuccess(data):
            self._diagrams = data.get("diagrams", [])
            self.diagramsChanged.emit()
            _log.info(f"Loaded {len(self._diagrams)} diagrams")

        reply = self.session.server().nonBlockingRequest(
            "GET",
            "/personal/diagrams",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtProperty("QVariantMap", notify=diagramChanged)
    def diagram(self):
        if self._diagram is not None:
            return self._diagram.__dict__
        return {}

    def _saveLastDiagramId(self, diagramId: int):
        self.appConfig.set("lastDiagramId", diagramId)
        if self.appConfig.filePath:
            self.appConfig.write()

    def _refreshDiagram(self):
        if not self.session.user:
            return

        lastDiagramId = self.appConfig.get("lastDiagramId")
        diagramId = (
            lastDiagramId if lastDiagramId else self.session.user.free_diagram_id
        )

        def onSuccess(data):
            rawData = base64.b64decode(data["data"])
            data["data"] = rawData
            self._diagram = Diagram(**data)
            self._discussions = [Discussion.create(x) for x in data["discussions"]]
            self._saveLastDiagramId(self._diagram.id)
            self.discussionsChanged.emit()
            self.statementsChanged.emit()
            self.pdpChanged.emit()
            self.diagramChanged.emit()
            _log.info(
                f"Loaded personal diagram: {self._diagram.id}, version: {self._diagram.version}"
            )
            scene = Scene()
            try:
                scene.read(pickle.loads(rawData))
            except (
                pickle.UnpicklingError,
                KeyError,
                ValueError,
                TypeError,
                AttributeError,
            ):
                _log.exception(f"Failed to load scene for diagram {self._diagram.id}")
            else:
                self.setScene(scene)

        def onError():
            if lastDiagramId and lastDiagramId != self.session.user.free_diagram_id:
                _log.warning(
                    f"Last diagram {lastDiagramId} not found, falling back to free diagram"
                )
                self.appConfig.delete("lastDiagramId")
                if self.appConfig.filePath:
                    self.appConfig.write()
                self._refreshDiagram()
            else:
                self.onError(reply)

        reply = self.session.server().nonBlockingRequest(
            "GET",
            f"/personal/diagrams/{diagramId}",
            data={},
            error=onError,
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot(int)
    def loadDiagram(self, diagramId: int):
        if not self.session.user:
            return

        def onSuccess(data):
            rawData = base64.b64decode(data["data"])
            data["data"] = rawData
            self._diagram = Diagram(**data)
            self._discussions = [Discussion.create(x) for x in data["discussions"]]
            self._currentDiscussion = None
            self._saveLastDiagramId(self._diagram.id)
            self.discussionsChanged.emit()
            self.statementsChanged.emit()
            self.pdpChanged.emit()
            self.diagramChanged.emit()
            _log.info(
                f"Loaded diagram: {self._diagram.id}, version: {self._diagram.version}"
            )
            sceneData = pickle.loads(rawData)
            scene = Scene()
            try:
                scene.read(sceneData)
            except (pickle.UnpicklingError, KeyError, ValueError, TypeError):
                _log.exception(f"Failed to load diagram {diagramId}")
                QMessageBox.critical(
                    None,
                    "Error",
                    "The diagram file is corrupted and cannot be opened.",
                )
            else:
                self.setScene(scene)

        reply = self.session.server().nonBlockingRequest(
            "GET",
            f"/personal/diagrams/{diagramId}",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot()
    def createDiagram(self):
        if not self.session.user:
            return

        name, ok = QInputDialog.getText(
            None, "New Diagram", "Enter a name for the new diagram:"
        )

        if not ok or not name.strip():
            return

        def onSuccess(data):
            diagramData = data.get("diagram", {})
            diagramId = diagramData.get("id")
            _log.info(f"Created diagram '{name}' (ID: {diagramId})")
            self._refreshDiagrams()
            if diagramId:
                self.loadDiagram(diagramId)

        reply = self.session.server().nonBlockingRequest(
            "POST",
            "/personal/diagrams/",
            data={"name": name.strip()},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    # Discussions

    @pyqtProperty("QVariantList", notify=discussionsChanged)
    def discussions(self):
        return list(self._discussions)

    @pyqtProperty(int, notify=statementsChanged)
    def currentDiscussionId(self):
        return self._currentDiscussion.id if self._currentDiscussion else -1

    @pyqtProperty(bool, notify=statementsChanged)
    def canExtract(self) -> bool:
        """Extract button visibility. Dirty = there is conversation past the
        last accepted extraction. Transitions (no model resync needed):
        - discussion load: computed from server order vs cursor;
        - send: dirty (a new statement is always past the cursor);
        - full accept: clean, unless chat happened since the extract that
          produced the accepted PDP (then still dirty);
        - partial accept / extract-without-accept: unchanged."""
        return bool(self._currentDiscussion) and self._dirty

    @pyqtSlot()
    def createDiscussion(self):
        self._createDiscussion()

    def _createDiscussion(self, callback: Callable | None = None):
        if not self._diagram:
            _log.warning("Cannot create discussion without diagram")
            return

        def onSuccess(data):
            discussion = Discussion.create(data)
            self._discussions.append(discussion)
            self.discussionsChanged.emit()
            self._setCurrentDiscussion(discussion.id)
            if callback:
                callback()

        reply = self.session.server().nonBlockingRequest(
            "POST",
            "/personal/discussions/",
            data={"diagram_id": self._diagram.id},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    def _setCurrentDiscussion(self, discussion_id: int):
        self._currentDiscussion = next(
            x for x in self._discussions if x.id == discussion_id
        )
        self._recomputeDirtyFromModel()
        self.statementsChanged.emit()
        self.pdpChanged.emit()

    def _recomputeDirtyFromModel(self):
        """At discussion load the model is server-fresh (statements carry
        order, cursor = extracted_through_order), so compute dirty directly."""
        self._sentSinceExtract = False
        d = self._currentDiscussion
        if not d:
            self._dirty = False
            return
        self._dirty = any(
            (s.order or 0) > d.extracted_through_order for s in d.statements()
        )

    @pyqtSlot(int)
    def setCurrentDiscussion(self, discussion_id: int):
        self._setCurrentDiscussion(discussion_id)

    ## Statements

    @pyqtProperty("QVariantList", notify=statementsChanged)
    def statements(self):
        if self._currentDiscussion:
            return list(self._currentDiscussion.statements())
        else:
            return []

    @pyqtSlot(str)
    def sendStatement(self, statement: str):
        self._sendStatement(statement)

    def _sendStatement(self, statement: str):
        def _doSendStatement():
            if not self._currentDiscussion:
                QMessageBox.information(
                    self, "Cannot send statement without current discussion"
                )
                return

            def onSuccess(data):
                self.responseReceived.emit(data["statement"])

            args = {
                "statement": statement,
                "model": self.responseModel,
            }
            reply = self.session.server().nonBlockingRequest(
                "POST",
                f"/personal/discussions/{self._currentDiscussion.id}/statements",
                data=args,
                error=lambda: self.onError(reply),
                success=onSuccess,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                from_root=True,
            )
            self.session.track(f"personal.Engine.sendStatement: {statement}")
            # A new statement is always past the cursor -> dirty. No model
            # resync needed; the flag is the source of truth between loads.
            self._dirty = True
            self._sentSinceExtract = True
            self.statementsChanged.emit()
            self.requestSent.emit(statement)

        if self._currentDiscussion:
            _doSendStatement()
        else:
            self._createDiscussion(callback=_doSendStatement)

    ## PDP

    def _pdpItem(self, id: int) -> Person | Event | None:
        if self._diagram:
            diagramData = self._diagram.getDiagramData()
            if diagramData.pdp:
                for item in diagramData.pdp.people + diagramData.pdp.events:
                    if item.id == id:
                        return item
        return None

    @pyqtSlot(int, result=bool)
    def acceptPDPItem(self, id: int, undo=True):
        if id > 0:
            return self._withSaveGuard(lambda: self._doHandleCommittedItem(id, accept=True, undo=undo))
        if id == 0:
            _log.error(f"acceptPDPItem called with id 0, ignoring")
            return False

        def _do():
            prev_data = self._diagram.getDiagramData() if undo else None
            success = self._doAcceptPDPItem(id)
            if success:
                self.clusterModel.detect()
                if undo:
                    cmd = HandlePDPItem(PDPAction.Accept, self, id, prev_data)
                    self._undoStack.push(cmd)
            return success

        return self._withSaveGuard(_do)

    @pyqtSlot(int, result=bool)
    def rejectPDPItem(self, id: int, undo=True):
        if id > 0:
            return self._withSaveGuard(lambda: self._doHandleCommittedItem(id, accept=False, undo=undo))
        if id == 0:
            _log.error(f"rejectPDPItem called with id 0, ignoring")
            return False

        def _do():
            prev_data = self._diagram.getDiagramData() if undo else None
            success = self._doRejectPDPItem(id)
            if success and undo:
                cmd = HandlePDPItem(PDPAction.Reject, self, id, prev_data)
                self._undoStack.push(cmd)
            return success

        return self._withSaveGuard(_do)

    def _postCommitPdp(self, itemIds: list[int], fullAccept: bool):
        """Tell the backend which staged items were accepted so the
        re-extraction cursor advances on a full accept. Best-effort: a failure
        only means the cursor doesn't advance (next extract re-windows; the
        server-side committed-duplicate guard absorbs the repeat)."""
        # Empty itemIds is valid only as an explicit full accept of an empty
        # PDP (advance the cursor, nothing to commit).
        if not self._currentDiscussion or (not itemIds and not fullAccept):
            return

        def onError():
            _log.warning(f"commit-pdp cursor advance failed: {reply.errorString()}")

        def onSuccess(data):
            # Server confirmed the accept. Clean unless chat was sent after the
            # extract that produced this PDP (then still dirty).
            if isinstance(data, dict) and data.get("full_accept"):
                self._dirty = self._sentSinceExtract
                self.statementsChanged.emit()

        data = {"item_ids": itemIds, "full_accept": fullAccept}
        if self._pendingExtractedThroughOrder is not None:
            data["accepted_through_order"] = self._pendingExtractedThroughOrder

        reply = self.session.server().nonBlockingRequest(
            "POST",
            f"/personal/discussions/{self._currentDiscussion.id}/commit-pdp",
            data=data,
            error=onError,
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    def _doAcceptPDPItem(self, id: int) -> bool:
        _log.info(f"Accepting PDP item with id: {id}")

        committedItems = {"people": [], "events": [], "pair_bonds": [], "emotions": []}
        drained = {}

        def applyChange(diagramData: DiagramData):
            _log.info(f"Applying accept PDP item change for id: {id}")
            if not diagramData.pdp:
                _log.warning("No PDP data available")
                return diagramData
            if self.scene is not None:
                diagramData.lastItemId = max(
                    diagramData.lastItemId, self.scene.lastItemId()
                )
            # Capture IDs before commit to identify what was added
            prevPeopleIds = {p["id"] for p in diagramData.people}
            prevEventIds = {e["id"] for e in diagramData.events}
            prevPairBondIds = {pb["id"] for pb in diagramData.pair_bonds}

            diagramData.commit_pdp_items([id])

            # Find newly committed items
            committedItems["people"] = [
                p for p in diagramData.people if p["id"] not in prevPeopleIds
            ]
            committedItems["events"] = [
                e for e in diagramData.events if e["id"] not in prevEventIds
            ]
            committedItems["pair_bonds"] = [
                pb for pb in diagramData.pair_bonds if pb["id"] not in prevPairBondIds
            ]
            drained["v"] = not (
                diagramData.pdp.people
                or diagramData.pdp.events
                or diagramData.pdp.pair_bonds
            )

            return diagramData

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        success = self._diagram.save(
            self.session.server(), applyChange, stillValidAfterRefresh, useJson=True
        )

        if success:
            self._addCommittedItemsToScene(committedItems)
            self.pdpChanged.emit()
            self._postCommitPdp([id], drained.get("v", False))
        else:
            _log.warning(f"Failed to accept PDP item after retries")

        return success

    def _addCommittedItemsToScene(self, committedItems: dict):
        if self.scene is None:
            return
        if (
            not committedItems["people"]
            and not committedItems["events"]
            and not committedItems["pair_bonds"]
        ):
            return

        # Phase 1: Create items and build local map (two-phase approach like Scene.read())
        itemChunks = []
        localMap = {}

        for chunk in committedItems["people"]:
            item = Person()
            item.id = chunk["id"]
            localMap[item.id] = item
            itemChunks.append((item, chunk))

        for chunk in committedItems["pair_bonds"]:
            item = Marriage()
            item.id = chunk["id"]
            localMap[item.id] = item
            itemChunks.append((item, chunk))

        for chunk in committedItems["events"]:
            kind = EventKind(chunk["kind"])
            if kind.isPairBond() and not chunk.get("spouse"):
                _log.error(
                    f"Skipping invalid pair bond event {chunk['id']} (kind={kind.value}): missing spouse"
                )
                continue
            item = Event(kind=EventKind.Shift, person=None)
            item.id = chunk["id"]
            localMap[item.id] = item
            itemChunks.append((item, chunk))

        # Phase 2: Read all chunks before adding to scene
        def byId(id):
            return localMap.get(id) or self.scene.itemRegistry.get(id)

        for item, chunk in itemChunks:
            item.read(chunk, byId)

        # Accept is a probabilistic-origin ingress (LLM extraction). Per the
        # provenance-normalized ingress rule (scene/CLAUDE.md), it must pass
        # through the SAME shared resilience step as load (Scene.read), not a
        # per-ingress patch. Drop events whose primary refs didn't resolve
        # (full chunk logged, recoverable) so addItem can't crash on a None
        # person. FMEA 2026-05-02 L2 recurred here because only load was wired.
        dropped = self.scene._dropIrrecoverableEvents(itemChunks)
        if dropped:
            droppedSet = set(dropped)
            itemChunks = [(i, c) for (i, c) in itemChunks if i not in droppedSet]

        # Phase 3: Add all items to scene.
        # isInitializing: suppress cross-reference validation (FR-4)
        # batch mode: defer signals and geometry updates
        self.scene.isInitializing = True
        self.scene.setBatchAddingRemovingItems(True)
        try:
            for item, chunk in itemChunks:
                self.scene.addItem(item)
        finally:
            self.scene.isInitializing = False
            self.scene.setBatchAddingRemovingItems(False)

    def _doHandleCommittedItem(self, id: int, accept: bool, undo: bool = True) -> bool:
        """Accept or reject a committed item (positive id in pdp.people or pdp.delete)."""
        prev_data = self._diagram.getDiagramData() if undo else None
        result: dict = {"is_delete": False, "edit_fields": {}}

        def applyChange(diagramData: DiagramData):
            if not diagramData.pdp:
                return diagramData
            is_delete = id in (diagramData.pdp.delete or [])
            result["is_delete"] = is_delete
            if accept:
                if is_delete:
                    diagramData.accept_committed_delete(id)
                else:
                    pdp_person = next((p for p in diagramData.pdp.people if p.id == id), None)
                    if pdp_person is not None:
                        if pdp_person.name is not None:
                            result["edit_fields"]["name"] = pdp_person.name
                        if pdp_person.gender is not None:
                            result["edit_fields"]["gender"] = pdp_person.gender
                    diagramData.accept_committed_edit(id)
            else:
                if is_delete:
                    diagramData.reject_committed_delete(id)
                else:
                    diagramData.reject_committed_edit(id)
            return diagramData

        success = self._diagram.save(
            self.session.server(), applyChange, lambda d: True, useJson=True
        )

        if success:
            if self.scene is not None and accept:
                if result["is_delete"]:
                    person = self.scene.find(id=id)
                    if person is not None:
                        self.scene.removeItem(person)
                elif result["edit_fields"]:
                    person = self.scene.find(id=id)
                    if person is not None:
                        if "name" in result["edit_fields"]:
                            person.setName(result["edit_fields"]["name"])
                        if "gender" in result["edit_fields"]:
                            person.setGender(result["edit_fields"]["gender"])
            self.pdpChanged.emit()
            if undo and prev_data:
                action = PDPAction.Accept if accept else PDPAction.Reject
                self._undoStack.push(HandlePDPItem(action, self, id, prev_data))
        else:
            _log.warning(f"Failed to handle committed item {id}")

        return success

    @pyqtSlot(int, result=bool)
    def acceptCommittedEdit(self, id: int) -> bool:
        return bool(self._withSaveGuard(lambda: self._doHandleCommittedItem(id, accept=True)))

    @pyqtSlot(int, result=bool)
    def rejectCommittedEdit(self, id: int) -> bool:
        return bool(self._withSaveGuard(lambda: self._doHandleCommittedItem(id, accept=False)))

    @pyqtSlot(int, result=bool)
    def acceptCommittedDelete(self, id: int) -> bool:
        return bool(self._withSaveGuard(lambda: self._doHandleCommittedItem(id, accept=True)))

    @pyqtSlot(int, result=bool)
    def rejectCommittedDelete(self, id: int) -> bool:
        return bool(self._withSaveGuard(lambda: self._doHandleCommittedItem(id, accept=False)))

    def _doRejectPDPItem(self, id: int) -> bool:
        _log.info(f"Rejecting PDP item with id: {id}")

        def applyChange(diagramData: DiagramData):
            if not diagramData.pdp:
                _log.warning("No PDP data available")
                return diagramData
            diagramData.reject_pdp_item(id)
            return diagramData

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        success = self._diagram.save(
            self.session.server(), applyChange, stillValidAfterRefresh, useJson=True
        )

        if success:
            self.pdpChanged.emit()
        else:
            _log.warning(f"Failed to reject PDP item after retries")

        return success

    @pyqtProperty("QVariantMap", notify=pdpChanged)
    def pdp(self):
        if self._diagram:
            diagramData = self._diagram.getDiagramData()
            if diagramData.pdp:
                result = asdict(diagramData.pdp)
                # Include committed people from scene so QML can resolve relationshipTargets/Triangles
                committedPeople = []
                if self.scene:
                    for person in self.scene.people():
                        committedPeople.append(
                            {"id": person.id, "name": person.fullNameOrAlias()}
                        )
                result["committedPeople"] = committedPeople
                return result
        return {}

    # PDP helper slots - model lookups and enum mappings

    @pyqtSlot(int, result=str)
    @pyqtSlot("QVariant", result=str)
    def resolvePersonName(self, personId: int | None) -> str:
        if personId is None:
            return ""
        if not self._diagram:
            return f"Person #{personId}"
        diagramData = self._diagram.getDiagramData()
        if diagramData.pdp:
            for p in diagramData.pdp.people:
                if p.id == personId:
                    return p.name or p.last_name or ""
        if self.scene:
            for person in self.scene.people():
                if person.id == personId:
                    return person.fullNameOrAlias()
        return f"Person #{personId}"

    @pyqtSlot("QVariantList", result=str)
    def resolvePersonNames(self, personIds: list[int]) -> str:
        if not personIds:
            return ""
        names = [self.resolvePersonName(pid) for pid in personIds if pid is not None]
        return ", ".join(n for n in names if n)

    @pyqtSlot(int, result=str)
    @pyqtSlot("QVariant", result=str)
    def resolvePairBondChildren(self, pairBondId) -> str:
        if pairBondId is None:
            return ""
        if not self._diagram:
            return ""
        diagramData = self._diagram.getDiagramData()
        if not diagramData.pdp:
            return ""
        names = [
            p.name or ""
            for p in diagramData.pdp.people
            if p.parents == pairBondId and p.name
        ]
        return ", ".join(names)

    @pyqtSlot(int, result=str)
    @pyqtSlot("QVariant", result=str)
    def scenePersonKind(self, personId: int | None) -> str:
        if personId is None:
            return ""
        if self._diagram:
            for p in self._diagram.getDiagramData().people:
                if p.get("id") == personId:
                    kind = p.get("gender")
                    return util.personKindNameFromKind(kind) or "" if kind else ""
        if self.scene:
            for person in self.scene.people():
                if person.id == personId:
                    return util.personKindNameFromKind(person.gender()) or ""
        return ""

    @pyqtSlot(str, result=str)
    def kindLabel(self, kind: str) -> str:
        return util.personKindNameFromKind(kind) or ""

    @pyqtSlot(int, result=str)
    @pyqtSlot("QVariant", result=str)
    def resolveParentNames(self, parentsId: int | None) -> str:
        if parentsId is None:
            return ""
        if not self._diagram:
            return ""
        diagramData = self._diagram.getDiagramData()
        if not diagramData.pdp:
            return ""
        for pb in diagramData.pdp.pair_bonds:
            if pb.id == parentsId:
                nameA = self.resolvePersonName(pb.person_a) if pb.person_a else ""
                nameB = self.resolvePersonName(pb.person_b) if pb.person_b else ""
                if nameA and nameB:
                    return f"{nameA} & {nameB}"
                return nameA or nameB
        return ""

    @pyqtSlot(str, result=str)
    @pyqtSlot("QVariant", result=str)
    def eventKindLabel(self, kind: str | None) -> str:
        if not kind:
            return "Event"
        labels = {
            EventKind.Bonded.value: "Bonded",
            EventKind.Married.value: "Married",
            EventKind.Birth.value: "Birth",
            EventKind.Adopted.value: "Adopted",
            EventKind.Moved.value: "Moved",
            EventKind.Separated.value: "Separated",
            EventKind.Divorced.value: "Divorced",
            EventKind.Shift.value: "Shift",
            EventKind.Death.value: "Death",
        }
        return labels.get(kind, "Event")

    @pyqtSlot(str, result=str)
    @pyqtSlot("QVariant", result=str)
    def variableLabel(self, val: str | None) -> str:
        if not val:
            return ""
        labels = {
            VariableShift.Up.value: "Up",
            VariableShift.Down.value: "Down",
            VariableShift.Same.value: "Same",
        }
        return labels.get(val, "")

    @pyqtSlot(str, result=str)
    @pyqtSlot("QVariant", result=str)
    def relationshipLabel(self, val: str | None) -> str:
        if not val:
            return ""
        try:
            kind = RelationshipKind(val)
            return kind.menuLabel()
        except ValueError:
            return ""

    @pyqtSlot(str, result=str)
    @pyqtSlot("QVariant", result=str)
    def dateCertaintyLabel(self, val: str | None) -> str:
        if not val:
            return ""
        labels = {
            DateCertainty.Unknown.value: "Unknown",
            DateCertainty.Approximate.value: "Approximate",
            DateCertainty.Certain.value: "Certain",
        }
        return labels.get(val, "")

    @pyqtSlot()
    def dismissEmptyExtraction(self) -> None:
        self._postCommitPdp([], True)

    @pyqtSlot()
    def acceptAllPDPItems(self):
        if not self._diagram:
            return

        def _do():
            diagramData = self._diagram.getDiagramData()
            if not diagramData.pdp:
                return

            newIds = []
            for person in diagramData.pdp.people:
                if person.id is not None and person.id < 0:
                    newIds.append(person.id)
            for event in diagramData.pdp.events:
                if event.id < 0:
                    newIds.append(event.id)
            for pair_bond in diagramData.pdp.pair_bonds:
                if pair_bond.id is not None and pair_bond.id < 0:
                    newIds.append(pair_bond.id)

            committedEdits = [p for p in diagramData.pdp.people if p.id is not None and p.id > 0]
            deleteIds = list(diagramData.pdp.delete or [])

            if not newIds and not committedEdits and not deleteIds:
                self._postCommitPdp([], True)
                return

            _log.info(f"Accepting all PDP items: new={newIds}, edits={[p.id for p in committedEdits]}, deletes={deleteIds}")

            newItems = {"people": [], "events": [], "pair_bonds": [], "emotions": []}
            editFields: dict[int, dict] = {}
            drained = {}

            def applyChange(diagramData: DiagramData):
                if not diagramData.pdp:
                    _log.warning("No PDP data available")
                    return diagramData
                if self.scene is not None:
                    diagramData.lastItemId = max(
                        diagramData.lastItemId, self.scene.lastItemId()
                    )

                if newIds:
                    prevPeopleIds = {p["id"] for p in diagramData.people}
                    prevEventIds = {e["id"] for e in diagramData.events}
                    prevPairBondIds = {pb["id"] for pb in diagramData.pair_bonds}
                    diagramData.commit_pdp_items(newIds)
                    newItems["people"] = [p for p in diagramData.people if p["id"] not in prevPeopleIds]
                    newItems["events"] = [e for e in diagramData.events if e["id"] not in prevEventIds]
                    newItems["pair_bonds"] = [pb for pb in diagramData.pair_bonds if pb["id"] not in prevPairBondIds]

                for pdp_person in committedEdits:
                    if pdp_person.name is not None:
                        editFields.setdefault(pdp_person.id, {})["name"] = pdp_person.name
                    if pdp_person.gender is not None:
                        editFields.setdefault(pdp_person.id, {})["gender"] = pdp_person.gender
                    diagramData.accept_committed_edit(pdp_person.id)

                for del_id in deleteIds:
                    diagramData.accept_committed_delete(del_id)

                drained["v"] = not (
                    diagramData.pdp.people or diagramData.pdp.events or diagramData.pdp.pair_bonds
                )
                return diagramData

            success = self._diagram.save(
                self.session.server(), applyChange, lambda d: True, useJson=True
            )

            if success:
                self._addCommittedItemsToScene(newItems)
                if self.scene is not None:
                    for person_id, fields in editFields.items():
                        person = self.scene.find(id=person_id)
                        if person is not None:
                            if "name" in fields:
                                person.setName(fields["name"])
                            if "gender" in fields:
                                person.setGender(fields["gender"])
                    for del_id in deleteIds:
                        person = self.scene.find(id=del_id)
                        if person is not None:
                            self.scene.removeItem(person)
                self.pdpChanged.emit()
                self.clusterModel.detect()
                allIds = newIds + [p.id for p in committedEdits] + deleteIds
                self._postCommitPdp(allIds, drained.get("v", True))
            else:
                _log.warning("Failed to accept all PDP items after retries")

        self._withSaveGuard(_do)

    @pyqtSlot(int, str, "QVariant")
    def updatePDPItem(self, id: int, field: str, value):
        if not self._diagram:
            return

        def _do():
            _log.info(f"Updating PDP item {id}: {field} = {value}")

            def applyChange(diagramData: DiagramData):
                if not diagramData.pdp:
                    return diagramData

                for event in diagramData.pdp.events:
                    if event.id == id:
                        if hasattr(event, field):
                            setattr(event, field, value)
                        break

                for person in diagramData.pdp.people:
                    if person.id == id:
                        if hasattr(person, field):
                            setattr(person, field, value)
                        break

                return diagramData

            success = self._diagram.save(
                self.session.server(), applyChange, lambda d: True, useJson=True
            )

            if success:
                self.pdpChanged.emit()
            else:
                _log.warning(f"Failed to update PDP item {id} after retries")

        self._withSaveGuard(_do)

    ## Clear Diagram Data

    @pyqtSlot(bool)
    def clearDiagramData(self, clearPeople: bool):
        if not self._diagram:
            return

        def _do():
            _log.info(
                f"Clearing diagram data (clearPeople={clearPeople}, "
                f"scene-loaded={self.scene is not None})"
            )

            if self.scene is not None:
                self.scene.setBatchAddingRemovingItems(True)
                try:
                    for event in list(self.scene.events()):
                        self.scene.removeItem(event)

                    if clearPeople:
                        for emotion in list(self.scene.emotions()):
                            self.scene.removeItem(emotion)
                        for marriage in list(self.scene.marriages()):
                            self.scene.removeItem(marriage)
                        for person in list(self.scene.people()):
                            if person.id not in (1, 2):
                                self.scene.removeItem(person)
                finally:
                    self.scene.setBatchAddingRemovingItems(False)

            def applyChange(diagramData: DiagramData):
                diagramData.events = []
                diagramData.pdp = None
                if clearPeople:
                    diagramData.people = [
                        p for p in diagramData.people if p.get("id") in (1, 2)
                    ]
                    diagramData.pair_bonds = []
                    diagramData.emotions = []
                return diagramData

            success = self._diagram.save(
                self.session.server(), applyChange, lambda d: True, useJson=True
            )

            if success:
                self.pdpChanged.emit()
                _log.info("Diagram data cleared successfully")
            else:
                _log.warning("Failed to clear diagram data")

        self._withSaveGuard(_do)

    ## Journal Import

    @pyqtSlot(str)
    def importJournalNotes(self, text: str):
        if not self._diagram:
            self.journalImportFailed.emit("No diagram loaded")
            return

        self.journalImportStarted.emit()

        def onSuccess(data):
            if data.get("pdp") and self._diagram:
                # Use the optimistic-locking save loop so a concurrent
                # Pro/Personal save during the import doesn't get clobbered
                # by a blind setDiagramData. The applyChange overwrites
                # only the pdp field; everything else passes through from
                # the server's current state.
                # Wrapped in _withSaveGuard so it serializes against any
                # in-flight saveDiagram (Personal auto-save during import).
                # Plan: doc/plans/2026-05-01--mvp-merge-fix/README.md
                imported_pdp = from_dict(PDP, data["pdp"])

                def _do():
                    def applyChange(diagramData: DiagramData):
                        diagramData.pdp = imported_pdp
                        return diagramData

                    self._diagram.save(
                        self.session.server(), applyChange, lambda d: True, useJson=True
                    )

                self._withSaveGuard(_do)
            self.pdpChanged.emit()
            self.journalImportCompleted.emit(data.get("summary", {}))
            self.clusterModel.detect()

        def onError():
            self.journalImportFailed.emit(reply.errorString())

        reply = self.session.server().nonBlockingRequest(
            "POST",
            f"/personal/diagrams/{self._diagram.id}/import-text",
            data={"text": text},
            error=onError,
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot()
    def importFromFile(self):
        path, _ = QFileDialog.getOpenFileName(
            QApplication.activeWindow(),
            "Import Notes",
            "",
            "Text Files (*.txt *.md);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            self.journalImportFailed.emit(str(e))
            return
        self.importJournalNotes(text)

    ## Extract Full

    @pyqtSlot()
    def extractFull(self):
        if not self._currentDiscussion:
            self.extractFailed.emit("No discussion selected")
            return
        if not self._diagram:
            self.extractFailed.emit("No diagram loaded")
            return

        # Baseline for "chat since this extract": a later full accept is clean
        # only if no statement was sent after this extract.
        self._sentSinceExtract = False
        self.extractStarted.emit()

        def onSuccess(data):
            self._pendingExtractedThroughOrder = data.get(
                "pending_extracted_through_order"
            )
            diagramData = self._diagram.getDiagramData()
            diagramData.pdp = from_dict(PDP, data["pdp"])
            self._diagram.setDiagramData(diagramData)
            self.pdpChanged.emit()
            self.extractCompleted.emit(
                {
                    "people": data.get("people_count", 0),
                    "events": data.get("events_count", 0),
                    "pairBonds": data.get("pair_bonds_count", 0),
                }
            )

        def onError():
            self.extractFailed.emit(reply.errorString())

        reply = self.session.server().nonBlockingRequest(
            "POST",
            f"/personal/discussions/{self._currentDiscussion.id}/extract",
            data={},
            error=onError,
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )
