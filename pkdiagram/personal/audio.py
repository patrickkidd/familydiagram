import json
import logging
import os
import tempfile

from PyQt5.QtMultimedia import QAudioRecorder, QAudioEncoderSettings
from PyQt5.QtCore import QByteArray, QTimer

from pkdiagram.app import Session
from pkdiagram.personal.api import JSON_HEADERS
from pkdiagram.pyqt import (
    QObject,
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)

_log = logging.getLogger(__name__)


class VoiceRecorder(QObject):
    """Records a spoken statement and transcribes it through AssemblyAI. The
    QAudioRecorder is created on first use so AVAudioSession isn't activated at
    launch."""

    transcriptionReady = pyqtSignal(str, arguments=["text"])
    transcriptionFailed = pyqtSignal(str, arguments=["error"])
    recordingFailed = pyqtSignal(str, arguments=["error"])

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._recorder = None
        self._filePath = ""
        self._networkManager = QNetworkAccessManager(self)

    def _ensure(self):
        if self._recorder is None:
            self._recorder = QAudioRecorder(self)

    @pyqtSlot()
    def start(self):
        self._ensure()
        try:
            tmpFile = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, prefix="fd_voice_"
            )
            self._filePath = tmpFile.name
            tmpFile.close()

            audioSettings = QAudioEncoderSettings()
            audioSettings.setCodec("audio/pcm")
            audioSettings.setSampleRate(16000)
            audioSettings.setChannelCount(1)

            self._recorder.setEncodingSettings(audioSettings)
            self._recorder.setOutputLocation(QUrl.fromLocalFile(self._filePath))
            self._recorder.record()
            _log.info(f"Started recording to {self._filePath}")
        except Exception as e:
            _log.error(f"Failed to start recording: {e}")
            self.recordingFailed.emit(str(e))

    @pyqtSlot()
    def cancel(self):
        """Stop recording WITHOUT transcribing (e.g. short tap or drag-off)."""
        if self._recorder is None:
            return
        self._recorder.stop()
        _log.info(f"Cancelled recording: {self._filePath}")
        self._cleanup(self._filePath)
        self._filePath = ""

    @pyqtSlot()
    def stop(self):
        """Stop recording and begin transcription."""
        if self._recorder is None:
            self.transcriptionFailed.emit("Recording file not found")
            return
        self._recorder.stop()
        _log.info(f"Stopped recording: {self._filePath}")

        if not self._filePath or not os.path.exists(self._filePath):
            self.transcriptionFailed.emit("Recording file not found")
            return

        self._transcribe(self._filePath)

    def _transcribe(self, filePath: str):
        """Fetch AssemblyAI key from server, then upload audio for transcription."""
        # Fast path: env var for desktop development
        envKey = os.environ.get("ASSEMBLYAI_API_KEY", "")
        if envKey:
            self._upload(filePath, envKey)
            return

        def onSuccess(data):
            apiKey = data.get("api_key", "")
            if not apiKey:
                self.transcriptionFailed.emit("Server returned empty AssemblyAI key")
                self._cleanup(filePath)
                return
            self._upload(filePath, apiKey)

        def onError():
            errorMsg = reply.errorString()
            _log.error(f"Failed to fetch AssemblyAI key: {errorMsg}")
            self.transcriptionFailed.emit(
                f"Failed to fetch transcription key: {errorMsg}"
            )
            self._cleanup(filePath)

        reply = self.session.server().nonBlockingRequest(
            "GET",
            "/personal/assemblyai-key",
            data={},
            error=onError,
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    def _upload(self, filePath: str, apiKey: str):
        try:
            with open(filePath, "rb") as f:
                audioData = f.read()
        except Exception as e:
            _log.error(f"Failed to read recording file: {e}")
            self.transcriptionFailed.emit(f"Failed to read recording: {e}")
            self._cleanup(filePath)
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
        error = reply.error()
        if error != QNetworkReply.NoError:
            errorMsg = reply.errorString()
            _log.error(f"Audio upload failed: {errorMsg}")
            self.transcriptionFailed.emit(f"Upload failed: {errorMsg}")
            reply.deleteLater()
            self._cleanup(filePath)
            return

        responseData = json.loads(bytes(reply.readAll()))
        reply.deleteLater()
        uploadUrl = responseData.get("upload_url", "")

        if not uploadUrl:
            self.transcriptionFailed.emit("Upload succeeded but no URL returned")
            self._cleanup(filePath)
            return

        _log.info(f"Audio uploaded: {uploadUrl}")

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
        error = reply.error()
        if error != QNetworkReply.NoError:
            errorMsg = reply.errorString()
            _log.error(f"Transcription request failed: {errorMsg}")
            self.transcriptionFailed.emit(f"Transcription request failed: {errorMsg}")
            reply.deleteLater()
            self._cleanup(filePath)
            return

        responseData = json.loads(bytes(reply.readAll()))
        reply.deleteLater()
        transcriptId = responseData.get("id", "")

        if not transcriptId:
            self.transcriptionFailed.emit("No transcript ID returned")
            self._cleanup(filePath)
            return

        _log.info(f"Transcription submitted: {transcriptId}")
        self._poll(transcriptId, apiKey, filePath)

    def _poll(self, transcriptId: str, apiKey: str, filePath: str):
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
        error = reply.error()
        if error != QNetworkReply.NoError:
            errorMsg = reply.errorString()
            _log.error(f"Transcription poll failed: {errorMsg}")
            self.transcriptionFailed.emit(f"Poll failed: {errorMsg}")
            reply.deleteLater()
            self._cleanup(filePath)
            return

        responseData = json.loads(bytes(reply.readAll()))
        reply.deleteLater()
        status = responseData.get("status", "")

        if status == "completed":
            text = responseData.get("text", "")
            _log.info(f"Transcription completed: {text[:80]}...")
            self.transcriptionReady.emit(text)
            self._cleanup(filePath)
        elif status == "error":
            errorMsg = responseData.get("error", "Unknown transcription error")
            _log.error(f"Transcription error: {errorMsg}")
            self.transcriptionFailed.emit(errorMsg)
            self._cleanup(filePath)
        else:
            QTimer.singleShot(
                1000, lambda: self._poll(transcriptId, apiKey, filePath)
            )

    def _cleanup(self, filePath: str):
        try:
            if filePath and os.path.exists(filePath):
                os.unlink(filePath)
                _log.debug(f"Cleaned up recording file: {filePath}")
        except Exception as e:
            _log.warning(f"Failed to clean up recording file: {e}")
