from .pyqt import QMessageBox, QObject, QEvent, Qt, pyqtSignal
from . import objects, util, commands
from .objects import emotions
from .qmldrawer import QmlDrawer


class AddEmotionDialog(QmlDrawer):

    def __init__(self, view=None, sceneModel=None):
        super().__init__(
            "qml/EmotionPropertiesDrawer.qml",
            parent=view,
            resizable=False,
            propSheetModel="emotionModel",
            objectName="addEmotionDialog",
            sceneModel=sceneModel,
        )
        self._returnTo = None
        self._canceled = False

    def onInitQml(self):
        super().onInitQml()
        self.rootProp("emotionModel").addMode = True
        self.qml.rootObject().cancel.connect(self.onCancel)

    def eventFilter(self, o, e):
        if e.type() == QEvent.KeyPress and e.key() == Qt.Key_Escape:
            e.accept()
            self.onCancel()
            return True
        return False

    def show(self, returnTo=None, personA=None, personB=None, **kwargs):
        emotion = objects.Emotion(personA=personA, personB=personB, addDummy=True)
        if returnTo:
            self._returnTo = returnTo
        super().show([emotion], **kwargs)
        self.rootProp("emotionModel").dirty = False
        self._canceled = False

    def canClose(self):
        if self.rootModel().dirty and not self._canceled:
            discard = QMessageBox.question(
                self,
                "Discard changes?",
                "Are you sure you want to discard your changes to this relationship? Click 'Yes' to discard your changes, or click 'No' to finish adding the event.",
            )
            if discard == QMessageBox.No:
                return False
            self._canceled = True
        return True

    def completeClickClose(self):
        if not self.parent():  # tests
            self._returnTo = None
            return
        if self._returnTo and self.parent():
            drawer, items = self._returnTo
            if drawer in (self.parent().personProps, self.parent().marriageProps):
                self.parent().setCurrentDrawer(drawer, items=items)
            else:
                self.parent().setCurrentDrawer(drawer)
        elif self.parent():
            self.parent().setCurrentDrawer(None)
        self._returnTo = None

    def onDone(self):
        emotion = self.rootProp("emotionModel").items[0]
        if emotion.kind() == -1:
            QMessageBox.critical(
                self,
                "Must select kind",
                "You must choose the kind of relationship you want to add.",
            )
            return False
        # if None in [emotion.startDateTime()]:
        #     QMessageBox.critical(self, 'Must set start date',
        #                          'You must set a start date to add a relationship.')
        #     return False
        elif emotion.isDyadic() and None in [emotion.personA(), emotion.personB()]:
            QMessageBox.critical(
                self,
                "Must set people",
                "You must set both people to add a dyadic relationship.",
            )
            return False
        elif not emotion.isDyadic() and emotion.personA() is None:
            QMessageBox.critical(
                self,
                "Must set parent",
                "You must set person A to add a monadic relationship.",
            )
            return False
        commands.addEmotion(self.scene, emotion)
        self._canceled = True  # hack
        self.completeClickClose()

    def onCancel(self):
        if not self.canClose():
            return
        self.completeClickClose()


def __test__(scene, parent):
    dlg = AddEmotionDialog(parent)
    dlg.setScene(scene)
    dlg.show(animate=False)
    parent.show()
    parent.resize(400, 600)
    return dlg
