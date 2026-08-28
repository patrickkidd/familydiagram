from pkdiagram.pyqt import QMessageBox, QObject, pyqtSignal
from pkdiagram.scene import Scene


class SaveGate(QObject):
    """Keeps the server row abreast of the Scene before a chat action reads it
    (FD-336 D6). Called before a send or an extract: a dirty stack prompts, and
    only a completed save lets the action through.

    The save itself belongs to whoever owns the document, so it is requested by
    signal rather than by a callable handed down."""

    S_TITLE = "Unsaved changes"
    S_PROMPT = "Save changes before chatting?"

    saveRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene: Scene | None = None

    def isClean(self) -> bool:
        return self.scene is None or self.scene.stack().isClean()

    def save(self) -> bool:
        self.saveRequested.emit()
        return self.isClean()

    def __call__(self) -> bool:
        if self.isClean():
            return True
        button = QMessageBox.question(
            None,
            self.S_TITLE,
            self.S_PROMPT,
            QMessageBox.Save | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if button != QMessageBox.Save:
            return False
        return self.save()
