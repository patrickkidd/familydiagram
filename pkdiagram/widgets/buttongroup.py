from pkdiagram.pyqt import QObject, QSignalMapper, pyqtSignal
from pkdiagram import util


class ButtonGroup(QObject):

    changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons = {}
        self.currentButton = None
        self.blocked = False
        self.mapper = QSignalMapper(self)
        self.mapper.mapped[int].connect(self.onClicked)

    def addButton(self, button, i):
        self.buttons[i] = button
        button.setCheckable(True)
        self.mapper.setMapping(button, i)
        button.clicked.connect(self.mapper.map)

    def button(self, i):
        for k, v in self.buttons.items():
            if k == i:
                return v

    def setCheckedButton(self, i):
        if self.blocked:
            return
        self.blocked = True
        if i in self.buttons:
            button = self.buttons[i]
            button.setChecked(True)  # should be blocked by onClick
            self.currentButton = i
            for k, v in self.buttons.items():
                if v != button:
                    v.setChecked(False)
        self.blocked = False

    def checkedButton(self):
        return self.currentButton

    def clear(self):
        if self.blocked:
            return
        self.blocked = True
        button = self.buttons.get(self.currentButton, None)
        if button:
            button.setChecked(False)
        self.currentButton = None
        self.blocked = False

    #    @blocked
    def onClicked(self, i):
        if self.blocked:
            return
        self.blocked = True
        button = self.buttons[i]
        if i == self.currentButton:  # allow toggle
            button.setChecked(False)
            self.currentButton = None
        else:
            self.currentButton = i
            for k, v in self.buttons.items():
                if k != self.currentButton:
                    v.setChecked(False)
        self.changed.emit(self.currentButton)
        self.blocked = False
