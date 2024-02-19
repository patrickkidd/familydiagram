import logging

from .pyqt import QMessageBox, QObject, QEvent, Qt, pyqtSignal
from . import objects, util, commands
from .objects import emotions
from .qmldrawer import QmlDrawer


_log = logging.getLogger(__name__)


class AddAnythingDialog(QmlDrawer):
    def __init__(self, view=None, sceneModel=None):
        super().__init__(
            "qml/AddAnythingDialog.qml",
            parent=view, resizable=False,
            objectName='addEverythingDialog',
            sceneModel=sceneModel
        )
        self._returnTo = None
        self._canceled = False

    def onInitQml(self):
        super().onInitQml()
        self.rootProp('emotionModel').addMode = True
        self.qml.rootObject().cancel.connect(self.onCancel)

    def eventFilter(self, o, e):
        if e.type() == QEvent.KeyPress and e.key() == Qt.Key_Escape:
            e.accept()
            self.onCancel()
            return True
        return False
    
    def onDone(self):
        """ Add button; supports returnTo """
        _log.info(f"AddAnythingDialog.onDone")
        # if not self.event.dateTime() or not self.event.dateTime().isValid():
        #     QMessageBox.critical(self, 'Must set date',
        #                         'You must set a valid date before adding an event.')
        #     return
        peopleToCreate = self.rootProp('peopleToCreate')
        peopleToCreate = self.rootProp('peopleToCreate')



def __test__(scene, parent):
    dlg = AddAnythingDialog(parent)
    dlg.setScene(scene)
    dlg.show(animate=False)
    parent.show()
    parent.resize(400, 600)
    return dlg
