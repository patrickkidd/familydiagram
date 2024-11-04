from .pyqt import QMessageBox, QObject, QEvent, Qt, pyqtSignal
from . import util, objects, commands
from .qmldrawer import QmlDrawer


class AddEventDialog(QmlDrawer):

    def __init__(self, engine, view=None, sceneModel=None):
        super().__init__(
            engine,
            "qml/EventPropertiesDrawer.qml",
            parent=view,
            resizable=False,
            propSheetModel="eventModel",
            objectName="addEventDialog",
            sceneModel=sceneModel,
        )
        self.event = None
        self._returnTo = None
        self._canceled = False
        self.installEventFilter(self)

    def onInitQml(self):
        super().onInitQml()
        self.rootProp("eventModel").addMode = True
        self.qml.rootObject().submit.connect(self.onDone)
        self.qml.rootObject().cancel.connect(self.onCancel)

    def show(self, returnTo=None, parent=None, animate=True, tab=None):
        self.event = objects.Event(addDummy=True, parent=parent)
        for entry in self.scene.eventProperties():
            self.event.addDynamicProperty(entry["attr"])
        if returnTo:
            self._returnTo = returnTo
        super().show([self.event], animate=animate)
        self.rootProp("eventModel").dirty = False
        self._canceled = False

    def hide(self, **kwargs):
        self.event = None
        super().hide(**kwargs)

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
        """Done button; supports returnTo"""
        if not self.event:
            return  # double-call
        if not self.event.dateTime() or not self.event.dateTime().isValid():
            QMessageBox.critical(
                self,
                "Must set date",
                "You must set a valid date before adding an event.",
            )
            return
        elif not self.event.parent:
            QMessageBox.critical(
                self, "Must set parent", "You must set a parent before adding an event."
            )
            return
        elif not self.event.description():
            QMessageBox.critical(
                self,
                "Must set description",
                "You must add a description before adding an event.",
            )
            return
        self.event.addDummy = False
        commands.addEvent(self.event.parent, self.event)
        self.event = None
        self._canceled = True  # hack
        self.completeClickClose()

    def canClose(self):
        if self.rootModel().dirty and not self._canceled:
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
    dlg = AddEventDialog(parent)
    dlg.setScene(scene)
    dlg.show(animate=False)
    parent.show()
    parent.resize(400, 600)
    return dlg
