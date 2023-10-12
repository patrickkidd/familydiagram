from ..pyqt import Qt, QObject, pyqtSlot, QAbstractItemModel, QAbstractTableModel, QDateTime, QModelIndex, qmlRegisterType
from .. import util, objects, commands
from ..scene import Scene
from .modelhelper import ModelHelper                
                
        

class EventPropertiesModel(QObject, ModelHelper):

    PROPERTIES = objects.Item.adjustedClassProperties(objects.Event, [
        { 'attr': 'editText' },
        { 'attr': 'nodal', 'convertTo': Qt.CheckState },
        { 'attr': 'unsure', 'convertTo': Qt.CheckState },
        { 'attr': 'numWritable', 'type': int, 'constant': True },
        { 'attr': 'parentId', 'type': int },
        { 'attr': 'addDummy', 'type': bool },
        { 'attr': 'parentIsPerson', 'type': bool },
        { 'attr': 'parentIsMarriage', 'type': bool },
        { 'attr': 'parentIsEmotion', 'type': bool },
        { 'attr': 'includeOnDiagram', 'convertTo': Qt.CheckState },
    ])

    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initModelHelper()
        
    def onItemProperty(self, prop):
        """ Filter out dynamic event properties. """
        if self.propAttrsFor(prop.name()):
            super().onItemProperty(prop)

    def get(self, attr):
        ret = None
        if attr == 'numWritable':
            numWritable = 0
            if self._scene and self._scene.readOnly():
                pass
            elif self._items:
                for item in self._items:
                    if item.uniqueId() is None:
                        numWritable += 1
                        break
            ret = numWritable
        elif attr == 'parentId':
            def getPID(item):
                if item.parent:
                    return item.parent.id
                else:
                    return -1
            ret = self.sameOf(attr, getPID)
            if ret is None:
                ret = -1
        elif attr == 'addDummy':
            ret = self.sameOf(attr, lambda item: item.addDummy)
        elif attr == 'parentIsPerson':
            ret = self.sameOf(attr, lambda item: item.parent and item.parent.isPerson or False)
        elif attr == 'parentIsMarriage':
            ret = self.sameOf(attr, lambda item: item.parent and item.parent.isMarriage or False)
        elif attr == 'parentIsEmotion':
            ret = self.sameOf(attr, lambda item: item.parent and item.parent.isEmotion or False)
        elif attr == 'notes':
            ret = self.sameOf(attr, lambda item: item.notes())
        elif attr == 'editText':
            if len(self._items) == 1:
                item = self._items[0]
                if not item.parent:
                    ret = "New Event"
                elif item.parent.isPerson:
                    itemLabel = item.parent.firstNameOrAlias()
                    if self.addMode:
                        ret = f"{itemLabel}: New Event"
                    else:
                        ret = f"{itemLabel}: {item.description()} Event"
                elif item.parent.isEmotion:
                    itemLabel = objects.Emotion.kindLabelForKind(item.parent.kind())
                    if item.uniqueId() == 'emotionStartEvent':
                        ret = f"{itemLabel}: Start Event"
                    elif item.uniqueId() == 'emotionEndEvent':
                        ret = f"{itemLabel}: End Event"
                elif item.parent.isMarriage:
                    if self.addMode:
                        ret =  f"Pair-Bond: New Event"
                    else:
                        ret =  f"Pair-Bond: {item.description()} Event"
                else:
                    ret = 'Event'
            else:
                ret = f"{len(self._items)} Events"
        else:
            ret = super().get(attr)
        return ret

    def set(self, attr, value):
        if attr == 'uniqueId' and self.parentIsMarriage: # right now marriage is the only parent type that uses uniqueId
            if self.blockNotify:
                was = self.blockNotify
                self.blockNotify = False # set to True for `addMode`
            else:
                was = None
            # Aggregate uniqueId and description props into single undo command
            # it is assumed the value is not blank
            id = commands.nextId()
            for item in self.items:
                # notify=False here so that description isn't automatically set in onProperty('uniqueId')
                # that allows the undo command ot be aggregated here.
                # This potentially sacrifices other listeners from updating, so keep eyes open for that.
                item.prop('uniqueId').set(value, notify=False, undo=id)
                newDescription = item.getDescriptionForUniqueId(value)
                item.prop('description').set(newDescription, notify=False, undo=id)
            self.refreshProperty('uniqueId')
            self.refreshProperty('description')
            for item in self.items:
                item.onProperty(item.prop('uniqueId')) # follow-up to notify=False
                item.onProperty(item.prop('description')) # follow-up to notify=False
            if was is not None:
                self.blockNotify = was
            return
        super().set(attr, value)
        if attr == 'parentId' and self._scene:
            person = self._scene.find(id=value)
            if person:
                id = commands.nextId()
                for event in self._items:
                    if event.uniqueId() is None:
                        commands.setEventParent(event, person, undo=id)
            self.refreshProperty('parentId')
        elif attr == 'items':
            self.refreshProperty('numWritable')
        elif attr == 'scene':
            self.refreshProperty('numWritable')
        elif attr == 'location' and self._scene:
            self.refreshProperty('description')
                  
    def reset(self, attr):
        if attr == 'uniqueId':
            # Aggregate uniqueId and description props into single undo command
            id = commands.nextId()
            for item in self.items:
                # notify=False here so that description isn't automatically set in onProperty('uniqueId')
                item.prop('uniqueId').reset(notify=False, undo=id)
                item.prop('description').reset(notify=False, undo=id)
            self.refreshProperty('uniqueId')
            self.refreshProperty('description')
        else:
            super().reset(attr)



qmlRegisterType(EventPropertiesModel, 'PK.Models', 1, 0, 'EventPropertiesModel')

