from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction, QKeySequence


class PersonalDevMenu:
    def __init__(self, controller):
        self.controller = controller
        self.menuBar = QMenuBar()
        self._setupMenus()

    def _setupMenus(self):
        deviceMenu = self.menuBar.addMenu("Device")

        shakeAction = QAction("Shake (Undo)", self.menuBar)
        shakeAction.setShortcut(QKeySequence("Ctrl+Z"))
        shakeAction.triggered.connect(self.controller.undo)
        deviceMenu.addAction(shakeAction)
