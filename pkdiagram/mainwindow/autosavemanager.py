import os
import os.path
import pickle
import logging
from datetime import datetime

from _pkdiagram import CUtil
from pkdiagram.pyqt import QObject, QDir, pyqtSignal
from pkdiagram import util


_log = logging.getLogger(__name__)


class AutoSaveManager(QObject):
    """
    Manages automatic saving of diagrams to a dedicated autosave folder.

    Auto-saves occur:
    - Immediately when a document is opened
    - Every 30 minutes while a document is open

    Auto-saves are stored in "<user_documents>/Family Diagram Autosaves/"
    with timestamped filenames compatible with tiered retention pruning.
    """

    autoSaved = pyqtSignal(str)  # Emits the path to the auto-saved file

    AUTOSAVE_FOLDER_NAME = "Family Diagram Autosaves"

    @staticmethod
    def autosaveFolderPath():
        """Return the path to the autosave folder."""
        documentsPath = CUtil.instance().documentsFolderPath()
        return os.path.join(documentsPath, AutoSaveManager.AUTOSAVE_FOLDER_NAME)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = None
        self._document = None
        self._timerId = None
        self._autosaveFolderPath = None
        self._ensureAutosaveFolder()

    def _ensureAutosaveFolder(self):
        """Create the autosave folder if it doesn't exist."""
        self._autosaveFolderPath = AutoSaveManager.autosaveFolderPath()

        dir = QDir(self._autosaveFolderPath)
        if not dir.exists():
            if dir.mkpath("."):
                _log.debug(f"Created autosave folder: {self._autosaveFolderPath}")
            else:
                _log.error(
                    f"Failed to create autosave folder: {self._autosaveFolderPath}"
                )

    def setDocument(self, document, scene):
        """
        Set the current document and scene to auto-save.

        Called from MainWindow.setDocument() after document is fully loaded
        and serverDiagram is set (for server diagrams).

        Args:
            document: FDDocument instance or None
            scene: Scene instance or None
        """
        # Stop existing timer
        if self._timerId is not None:
            self.killTimer(self._timerId)
            self._timerId = None

        self._document = document
        self._scene = scene

        if document and scene:
            _log.debug(
                f"Starting auto-save for document: {document.url().toLocalFile()}"
            )
            self._performAutoSave()

            # Start periodic auto-save timer (30 minutes)
            self._timerId = self.startTimer(util.AUTOSAVE_INTERVAL_S * 1000)
        else:
            _log.debug("Auto-save stopped (no document)")

    def timerEvent(self, a0):
        """Called when the auto-save timer expires."""
        self._performAutoSave()

    def _performAutoSave(self):
        """Perform the actual auto-save operation."""
        if not self._scene or not self._document:
            _log.warning("Cannot auto-save: no scene or document")
            return

        # Don't auto-save read-only documents
        if self._scene.readOnly():
            _log.debug("Skipping auto-save for read-only document")
            return

        # Determine base name for autosave file
        serverDiagram = self._scene.serverDiagram()
        if serverDiagram and serverDiagram.name:
            # Server diagram - use diagram name
            baseName = serverDiagram.name
        else:
            # Local file - extract from document URL
            originalPath = self._document.url().toLocalFile()
            if originalPath:
                from pkdiagram.pyqt import QFileInfo

                fileInfo = QFileInfo(originalPath)
                baseName = fileInfo.completeBaseName()
                if baseName.endswith(".fd"):
                    baseName = baseName[:-3]
            else:
                baseName = "diagram"

        # Generate timestamp in format: YYYYMMDD_HHMMSS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create autosave filename
        autosaveFileName = f"{baseName}_{timestamp}.fd"
        autosavePath = os.path.join(self._autosaveFolderPath, autosaveFileName)

        # Serialize the scene data
        data = self._scene.data()
        bdata = pickle.dumps(data)

        # Create the .fd directory
        os.makedirs(autosavePath, exist_ok=True)

        # Write the pickle file
        picklePath = os.path.join(autosavePath, "diagram.pickle")
        with open(picklePath, "wb") as f:
            f.write(bdata)

        _log.debug(f"Auto-saved to: {autosavePath}")
        self.autoSaved.emit(autosavePath)

    def stop(self):
        """Stop auto-saving."""
        if self._timerId is not None:
            self.killTimer(self._timerId)
            self._timerId = None
        self._document = None
        self._scene = None
