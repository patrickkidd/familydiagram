import enum
from copy import deepcopy

from pkdiagram.pyqt import QUndoCommand
from btcopilot.schema import DiagramData


class PDPAction(enum.Enum):
    Accept = "accept"
    Reject = "reject"


class HandlePDPItem(QUndoCommand):
    def __init__(
        self, action: PDPAction, personal, item_id: int, prev_diagramData: DiagramData
    ):
        super().__init__()
        self.action = action
        self.personal = personal
        self.item_id = item_id
        self.prev_diagramData = deepcopy(prev_diagramData)
        self.setText(f"Accept PDP Item {item_id}")
        self._initial_run = True

    def redo(self):
        if self._initial_run:
            self._initial_run = False
            return
        if self.action == PDPAction.Accept:
            self.personal._doAcceptPDPItem(self.item_id)
        else:
            self.personal._doRejectPDPItem(self.item_id)

    def undo(self):
        self.personal._diagram.setDiagramData(self.prev_diagramData)
        self.personal.pdpChanged.emit()
