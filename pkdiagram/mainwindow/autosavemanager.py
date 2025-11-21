import os
import os.path
import pickle
import logging
from datetime import datetime
from pathlib import Path

from _pkdiagram import CUtil
from pkdiagram.pyqt import QObject, QTimer, QDir, QFileInfo, pyqtSignal
from pkdiagram import util


log = logging.getLogger(__name__)


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = None
        self._document = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._onTimerTimeout)
        self._autosaveFolderPath = None
        self._ensureAutosaveFolder()

    def _ensureAutosaveFolder(self):
        """Create the autosave folder if it doesn't exist."""
        documentsPath = CUtil.instance().documentsFolderPath()
        self._autosaveFolderPath = os.path.join(
            documentsPath, self.AUTOSAVE_FOLDER_NAME
        )

        dir = QDir(self._autosaveFolderPath)
        if not dir.exists():
            if dir.mkpath("."):
                log.info(
                    f"Created autosave folder: {self._autosaveFolderPath}"
                )
            else:
                log.error(
                    f"Failed to create autosave folder: {self._autosaveFolderPath}"
                )

    def setDocument(self, document, scene):
        """
        Set the current document and scene to auto-save.

        Args:
            document: FDDocument instance or None
            scene: Scene instance or None
        """
        # Stop existing timer
        self._timer.stop()

        self._document = document
        self._scene = scene

        if document and scene:
            # Perform immediate auto-save when document is opened
            log.info(f"Starting auto-save for document: {document.url().toLocalFile()}")
            self._performAutoSave()

            # Start periodic auto-save timer (30 minutes)
            self._timer.start(util.AUTOSAVE_INTERVAL_S * 1000)
        else:
            log.info("Auto-save stopped (no document)")

    def _onTimerTimeout(self):
        """Called when the auto-save timer expires."""
        self._performAutoSave()

    def _performAutoSave(self):
        """Perform the actual auto-save operation."""
        if not self._scene or not self._document:
            log.warning("Cannot auto-save: no scene or document")
            return

        # Don't auto-save read-only documents
        if self._scene.readOnly():
            log.debug("Skipping auto-save for read-only document")
            return

        try:
            # Get the original file path and name
            originalPath = self._document.url().toLocalFile()
            fileInfo = QFileInfo(originalPath)

            # Extract base name without .fd extension
            baseName = fileInfo.completeBaseName()
            if baseName.endswith(".fd"):
                baseName = baseName[:-3]

            # Generate timestamp in format: YYYYMMDD_HHMMSS
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Create autosave filename
            autosaveFileName = f"{baseName}_autosave_{timestamp}.fd"
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

            log.info(f"Auto-saved to: {autosavePath}")
            self.autoSaved.emit(autosavePath)

        except Exception as e:
            log.error(f"Auto-save failed: {e}", exc_info=True)

    def stop(self):
        """Stop auto-saving."""
        self._timer.stop()
        self._document = None
        self._scene = None
