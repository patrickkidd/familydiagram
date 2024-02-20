import logging

from .pyqt import QMessageBox, QObject, QEvent, Qt, pyqtSignal
from . import objects, util, commands
from .objects import emotions
from .qmldrawer import QmlDrawer


_log = logging.getLogger(__name__)


class AddAnythingDialog(QmlDrawer):

    QmlDrawer.registerQmlMethods(
        [
            {"name": "clear"},
        ]
    )

    def __init__(self, parent=None, sceneModel=None):
        super().__init__(
            "qml/AddAnythingDialog.qml",
            parent=parent,
            resizable=False,
            objectName="addEverythingDialog",
            sceneModel=sceneModel,
        )
        self._returnTo = None
        self._canceled = False

    def onInitQml(self):
        super().onInitQml()
        self.qml.rootObject().cancel.connect(self.onCancel)

    def eventFilter(self, o, e):
        if e.type() == QEvent.KeyPress and e.key() == Qt.Key_Escape:
            e.accept()
            self.onCancel()
            return True
        return False

    def completeClickClose(self):
        if not self.parent():  # tests
            self._returnTo = None
            return
        if self._returnTo:
            drawer, items = self._returnTo
            if drawer in (self.parent().personProps, self.parent().marriageProps):
                self.parent().setCurrentDrawer(drawer, items=items)
            else:
                self.parent().setCurrentDrawer(drawer)
        else:
            self.parent().setCurrentDrawer(None)
        self._returnTo = None

    def onDone(self):
        """Add button; supports returnTo"""
        _log.info(f"AddAnythingDialog.onDone")
        # if not self.event.dateTime() or not self.event.dateTime().isValid():
        #     QMessageBox.critical(self, 'Must set date',
        #                         'You must set a valid date before adding an event.')
        #     return
        peopleToCreate = self.rootProp("peopleToCreate")
        peopleToCreate = self.rootProp("peopleToCreate")

    def canClose(self):
        if self.property("dirty") and not self._canceled:
            discard = QMessageBox.question(
                self,
                "Discard changes?",
                "Are you sure you want to discard your changes to this event? Click 'Yes' to discard your changes, or click 'No' to finish adding the event.",
            )
            if discard == QMessageBox.No:
                return False
            self._canceled = True
        return True

    def onCancel(self):
        """Cancel button; supports returnTo"""
        if not self.canClose():
            return
        self.completeClickClose()


def __test__(scene, parent):
    dlg = AddAnythingDialog(parent)
    dlg.setScene(scene)
    dlg.show(animate=False)
    parent.show()
    parent.resize(400, 600)
    return dlg
