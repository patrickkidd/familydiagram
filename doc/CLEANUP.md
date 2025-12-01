CLEANUP
=================================================
- Remove eventProperties, etc from Drawer?


- Person.children leftover from first alpha version?
- Replace View.show*Details with View.show*Properties
- Move [Item Subclass].addProperties to class level for speed optimization.
- Move reading prefs for pinned value from CaseListItem => CaseList
- Marriage.jig needed now that separationIndicator is factored out?
- Rename Marriage to PairBond
- Can't copy/paste simple family with marriage
- MainWindow.__checkForUpdates|___onUpdatesReply|post_exception|post_response
- Merge SetItemLayerProperty with SetProperty as with ResetProperty
- Consolidate LayerModel|EventModel|EmotionModel => TableModel
- Rename util.PEN to util.DEFAULT_PEN
- Remove EventModel.addEvent
- Move MainWindow.post_exception stuff somewhere else
- remove marriage bugfix in Person.read
- make Person.alias() return alias with [ and ]
- Rename Property.get to Property.value
- Rename Person.name() to firstName() and Person.nameOrAlias() to name()
- Rename Scene.name() to nameOrAlias()
- Move uploadthread to ServerCache
- remove MainWindow.undoStack in favor of commands.stack(0
- Remove pyqt dependency from util_base.py
- File browser...sheesh...
- Refactor MainWindow to have blank scene state, especially for testing.
- EventDelegate.commitAndCloseEditor calls EventModel.setData() twice
- Register/deregister events in Person.itemChange() for scene change
  - considering I set `if scene` conditional in add|removeEvent
- Does MainWindow.setDocument make .setScene redundant? 
- PersonProperties.onProperty to support multiple people like eventprops
- DateEdit uses self.events but with no way to set them (delete?)
- standardize init|show for all views so init is only called once
- Check validity of not setting QObject parent for Property() (deletes ok?)
- move onProperty|propertyChanged from Person|etc to PathItem?
- Maybe port Application.event to C++?
- Scene.eventRemoved emitted twice
  - once via Person sig and once via direct Scene sig?
  - Then clean up EventDelegate.onEvent[Added|Removed|Changed] and test
- move Scene.write* to MainWindow
- move mw.undoStack to commands.init() or util.init()
- remove version.* from util.py
- Normalize show filemanager in showHome/setDocument
- seperate widgets into package
- Item.setHover -> pathitem
- onInspect, show[x]Details, [X]Properties
- debug double calls to Property.set()
- debug double calls to updateGeometry()
  - just do a standard painting optimization
  - item updateGeometry Queue in scene, based on flag and 0-second timer
  - optimize updateGeometry() by checking for change from last date to current date
- remove redundancy in [Case,Person,Marriage,Event]Properties.[show,onProperty]
- replace DateEdit.null property with method
- UndoCommand delete cutoff registers/deregisters twice
- Scene.data() being called twice on save.
- rename person.marriages to person._marriages


