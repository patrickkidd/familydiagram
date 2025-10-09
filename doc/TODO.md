Flatten / Events, Fix Event/Emotion relationship: https://alaskafamilysystems.atlassian.net/browse/FD-244
=====================================

Spec
---------------------------------------------
- Two major ways Emotions / Person gets created:
  - Drawing like a chalk board without an Event
  - Created to represent a dated Event
- Remove all Person/Marriage/Emotion event references for computer properties,
  Scene as single source of truth
  - Remove Person.onAddEvent, etc.
- Have Person.updateEvents() only listen for Shift since it only updates self.variablesDatabase?
- Add TimelineRow dataclass instead of dummy events; _ensureEvent(adds 1 or 2 for dateTime & endDateTime)
  ```
    def _ensureEvent(self, event: Event):
        # Start row
        self._rows.add(TimelineRow(
            dateTime=event.dateTime(),
            description=event.description(),
            source_event=event,
        ))

        # End row (if needed)
        if event.endDateTime():
            self._rows.add(TimelineRow(
                dateTime=event.endDateTime(),
                description=f"{event.kind().name} ended",
                source_event=event,
                is_end_marker=True,
            ))
  ```
- Remove dateTime editors from PersonProperties in favor of a button to edit those singleton events, just like EmotionProperties.


Edit events with EventForm
------------------------------------
- Test out adding events with tags, setting tags on Emotion. See if it feels right.
  - Kind of like editing color + notes on either item
- Ensure that ChildOf objects are generated for Birth/Adopted events just like emotions
- Migrate CustomPairBond events to VariableShift for person/spouse
- Probably need to add person=None to Event.__init__ as mutually exclusive to event for drawing use case.
- event.includeOnDiagram
- Event.color
- Add link to edit emotion if kind == Shift
- Remove event field edits from EmotionProperties, just add links to start event
- Disable isDateRange when not editing Emotion's
- Legacy births, leave person/spouse empty if none exist if possible
- Shift -> Shift
- Storing EventKind on Event.uniqueId or new Event.kind?
  - Going to end up replacing `uniqueId` with `kind` anyway?
  - But still duplicates data?
- Update person geometry/details when birth/adopted/death events change
- delete commands.SetEmotionPerson
- Check that updating pairbond events update Marriage details (Marriage.onEventProperty removed)
- ITEM_MODE -> EventKind | RelationshipKind
  - Emotion
- Remove Emotion.notes and in EmotionProperties
- Double check undo/redo works for adding emotions from Scene.addItem
- Double check can delete event and emotion still remains, and vice-versa (is that even what we want?)
- Scene data:
  - data["items"] -> data["events"]
  - data["items"] -> data["people"]
- compat
  - CustomIndividual -> 'variable-shift' (kind can never be `None`)
  - [in &.read()] Marriage.events, Person.Events, Emotion.events -> Scene.events
  - Event.kind is None -> kind = Shift
  - Marriage.events -> Scene.events
    - personA -> Event.person
    - personB -> Event.spouse
  - Emotion.startEvent['emotionStartEvent'] -> Emotion.startEvent['variable-shift']
  - Emotion.isDateRange (isSingularDate()) -> Event.endEvent
  - Emotion.notes -> Emotion.event().notes
  - Emotion.kind -> RelationshipKind
  - Emotion.person_a -> Event.person
  - Emotion.person_b -> Emotion.target
  - Emotion.intensity -> Event.intensity

Cleanup
------------------------------------------------


BUGS
------------------------------------
- View tag, add R symbol, lots of things are hidden
  - Guiterrez, `Out of Jail, Housing Incident`
- Notes in add data point field doesn't store / show icon
- Aliases can be frustrating in timeline (Guittierez)
  - Switch back, at least [Jett] doesn't always chnge back.
  - Sometimes alias applied within alias
  - Sometimes only applied to substrings (Gabriella applied as Gabriel -> [Shawn]la)

IDEAS
------------------------------------
- Add visual distinction between start and end markers in the graphical timeline
- Automatically add a person to the Person Picker and focus it if none exists when choosing event type.
- Rename event "Description" to "summary"
- For reciprocity
  - Change label mover(s) to up/overfunction
  - Change label receiver(s) to down/underfunctions
- Add pregnancy
  - Change miscarraige to have X through it like death
- Prompt for variable shifts for additional people when entering data point
  - Under the hood, add separate events for each person
  - Collapse events with the same timestamp into the same row
- Hide or disable variables for R symbols
- Allow "Is Date Range" without entering an end date to allow it to persist
- Help/prompt: "Does a shift in R preceed or proceed this?"
- Add ribbon to Add form?: Prompt for "next event in sequence?"
  - Laura: "What happens next and for whom?"
- Need to hide those logged columns
- Move search view to hovering overlay over entire document with click screen?
  - So you can see the diagram and timeline change while entering values
  - Add search button to top or bottom of timeline
- Need add button for Person views tab
- Speed up mainwindow tests. Need account login and everything?
- Command+Enter to submit EventForm; need more obvious active field aura
- PersonPicker
  - Focus box around PersonPicker, kindBox on initial tab after show, functioning box
  - Make PersonPicker yellow, then green when submitted? (same as create account dialog)
  - New people picker PersonPicker text edit doesn't get focus in new row

BUGS
2024-12-06 07:09:45,848 ERROR application.py:78          Traceback (most recent call last):
2024-12-06 07:09:45,848 ERROR application.py:78            File "/Users/patrick/dev/familydiagram/pkdiagram/analytics.py", line 170, in onFinished
    finished()
2024-12-06 07:09:45,849 ERROR application.py:78          TypeError: Analytics._postNextEvents.<locals>.onFinished() missing 1 required positional argument: 'reply'
- Skipping cutoffs warning in terminal?
- Can drag divorce separation bar beyond pair bond bounds?
- Can't set parents for existing person and existing parents from add anything form
- Send warning to bugsnag when detecting emotion that doesn't have one of the people set
- 2024-11-01 09:17:35,489 DEBUG analytics.pyo:217          Attempting to send 1 profiles to Mixpanel...
  2024-11-01 09:17:35,927 DEBUG server_types.pyo:208       https://api.mixpanel.com/engage#profile-batch-update: status_code: None, SSL handshake with server failed.
- 2024-11-01 09:17:33,548 ERROR application.pyo:82         TypeError: Server.nonBlockingRequest.<locals>.onSSLErrors() missing 1 required positional argument: 'errors'
  2024-11-01 09:17:33,657 ERROR application.pyo:82         TypeError: Server.nonBlockingRequest.<locals>.onSSLErrors() missing 1 required positional argument: 'errors'
- 024-10-31 15:51:08,076 DEBUG qmlutil.pyo:563             <---- Returning PersonPicker: PersonPicker_QMLTYPE_192_QML_202(0x6000088f1600, "dRoot"), personName: Lillian Anne Havstad, person: Person(0x600000b765d0), gender: female
  2024-10-31 15:51:08,076 DEBUG qmlutil.pyo:563             found PK.PersonPicker at index: 0
  2024-10-31 15:51:08,076 DEBUG qmlutil.pyo:563             found PK.PersonPicker at index: 1
  2024-10-31 15:51:08,076 DEBUG qmlutil.pyo:563             found PK.PersonPicker at index: 2
- 2024-10-31 15:53:43,213 INFO :0                         QUndoStack::setClean(): cannot set clean in the middle of a macro
- 2024-10-31 15:52:13,721 INFO :0                         QUnifiedTimer::stopAnimationDriver: driver is not running
- Reset diagram sets hideDateSlider to True?
- Undo delete all events doesn't set Scene.setCurrentDate() to valid date, bottom timeline doesn't come back
- Can't switch between 1.5.4 and beta, get "app tampered with message"
- Clicking tab in CaseProps doesn't update right toolbar button state
- CaseProps Settings view is still visible in editor mode
- Set search start date time always paints a bubble at the beginning even when there is no event on that date.
- Start w empty diagram, set birth kind, submit new person name, switch to Married, observe:
  file:///Users/patrick/dev/familydiagram/pkdiagram/resources/qml/PK/PersonPicker.qml:90: TypeError: Cannot call method 'listLabel' of null
- tab order for single-field FormField entries
  file:///Users/patrick/dev/familydiagram/pkdiagram/resources/qml/PK/FormField.qml:56:13: Unable to assign [undefined] to QQuickItem*
  file:///Users/patrick/dev/familydiagram/pkdiagram/resources/qml/PK/FormField.qml:57:13: Unable to assign [undefined] to QQuickItem*
- On switching to some event kind with people selected
  - file:///Users/patrick/dev/familydiagram/pkdiagram/resources/qml/PK/PersonPicker.qml:86: TypeError: Cannot call method 'listLabel' of null
- Fade in/out timeline callout
  - When deleting Patrick + Connie Pair-Bond with bonded and married events
  Traceback (most recent call last):
    File "/Users/patrick/dev/familydiagram/pkdiagram/models/peoplemodel.py", line 166, in personForRow
      personId = self._sortedIds[row]
  IndexError: list index out of range
- On close file:
  Traceback (most recent call last):
  2024-04-04 21:30:27,775 application.py:147           File "/Users/patrick/dev/familydiagram/pkdiagram/models/timelinemodel.py", line 386, in data
      ret = self.flags(index)
  2024-04-04 21:30:27,783 application.py:147           File "/Users/patrick/dev/familydiagram/pkdiagram/models/timelinemodel.py", line 537, in flags
      elif self.dynamicPropertyAttr(index):
  2024-04-04 21:30:27,792 application.py:147           File "/Users/patrick/dev/familydiagram/pkdiagram/models/timelinemodel.py", line 578, in dynamicPropertyAttr
      eventProperties = self._scene.eventProperties()
  2024-04-04 21:30:27,800 application.py:147         AttributeError: 'NoneType' object has no attribute 'eventProperties'


v1.5.2
=============================================================================
BUGS
- Server Diagram in Recents -> Close File -> Close App -> Open App -> Open Other File -> Close App -> Open App -> Open Server Diagram in Recents -> 
  -> Title bar fpath w/ diagram ID in server cache, doesn't save to server.
- Can't select all events on timeline and delete (Kathy's `Fann In Bug.fd`)
- graphical timeline doesn't show within-day time granularity
- R symbols don't fan in when new tags selected in search
  Traceback (most recent call last):
    File "/Users/patrick/dev/familydiagram/pkdiagram/scene.py", line 1531, in onSearchChanged
      self._updateAllItemsForLayersAndTags()
    File "/Users/patrick/dev/familydiagram/pkdiagram/scene.py", line 1550, in _updateAllItemsForLayersAndTags
      item.onActiveLayersChanged()
    File "/Users/patrick/dev/familydiagram/pkdiagram/objects/emotions.py", line 1405, in onActiveLayersChanged
      self.updateFannedBox()
    File "/Users/patrick/dev/familydiagram/pkdiagram/objects/emotions.py", line 1559, in updateFannedBox
      self.fannedBox.removeEmotion(self)
    File "/Users/patrick/dev/familydiagram/pkdiagram/objects/emotions.py", line 246, in removeEmotion
      self.updateFannedState()
    File "/Users/patrick/dev/familydiagram/pkdiagram/objects/emotions.py", line 331, in updateFannedState
      entries[emotion].update({
  KeyError: <Emotion[19]: loggedDateTime: PyQt5.QtCore.QDateTime(2023, 3, 3, 13, 47, 10, 303), itemPos: PyQt5.QtCore.QPointF(807.508878949319, -199.5893386291309), kind: 6, parentName: Unnamed & Unnamed, color: #31a30d>


v1.5.3
=============================================================================
BUGS
- Printing doesn't work
- App slow to open without internet when last file on server (esp. Windows?).
  - Slow on Session.init() GET /init
- Save server diagram w/o internet -> No warning?
- No warning about unsaved changes when exiting app?
- Save server diagram w/ internet error, save w/ internet -> file corruption?
- No alert when opening server diagram w/o internet?
- Poor loading behavior on windows?
  - Need some loading indicator
  - Don't momentarily show windows console
- Save as file name resolves to python method object
- Don't flash child-of with person?


v1.5.1
=============================================================================
BUGS
- Session.activeFeatures() should not return Client along with Professional.
- Dbl-click edit date -> doesn't mark diagram dirty.
- Don't show cached file name (which is a number) in window title for server file.
- Tab order for event properties (at least add event dlg)
- Checks for updates even when auto check prefs disabled
- Item Details drag grab area much bigger than text. (Grandpa [Joseph] for JoseJ)
- DocumentView has no attriute `eventProps` (documentview.py)
FEATURES
- Ctrl+Shift+N to show notes for selected event in timeline
- Add watermark in timeline when no events shown, with reset button
- Add Emotion events for increase/decrease in intensity?
- Add a place to add questions about parts of family.
  - Add theoretical notes where appropriate+possible.
    - "Theory" tab for each prop sheet?
    - NFEP under Pair-Bond.
    - NSM under Event/Timeline
    - Include standard initial family assessment questions??
      - Would be cool way to help use theory
- Full diagram search, notes fields, etc.
  - Add quick search to timeline?
  - Or quick search to diagram?
    - Highlight matching people
    - Checkbox to include events, notes, etc?
  - Replace "description" field in search view to include notes?
  - How to show events, people, etc that have matching text/notes fields.
- Scroll to and highlight event just added in timeline

THINGS TO TEST:
- Create Layer, move some items, items move back as expected.
- Check jumpy timeline scrolling.
- Remove reference to deprecated "unsure" box in Manual.
- Autosave does not work?
- Updates on graphical timeline
  - Click to set current date on graphical timeline doesn't repaint until mouse move
  - Next/Prev event doesn't work when showing graphical timeline.
  - Window title doesn't update when clicking, next/prev date shortcut
  - Exception: variablesdatabase.py:39     KeyError(QDate)        elif date < attrEntry.peekitem(0)[0]:
- Traceback (most recent call last):
    File "/Users/patrick/dev/familydiagram/pkdiagram/commands.py", line 291, in redo
      item.setParent(None)
    File "/Users/patrick/dev/familydiagram/pkdiagram/objects/event.py", line 133, in setParent
      was._onRemoveEvent(self)
    File "/Users/patrick/dev/familydiagram/pkdiagram/objects/person.py", line 697, in _onRemoveEvent
      self.updateEvents()
    File "/Users/patrick/dev/familydiagram/pkdiagram/objects/person.py", line 621, in updateEvents
      self.variablesDatabase.unset(prop.attr, event.dateTime())
    File "/Users/patrick/dev/familydiagram/pkdiagram/objects/variablesdatabase.py", line 29, in unset
      del attrEntry[date]
    File "/Users/patrick/dev/familydiagram/lib/site-packages/sortedcontainers/sorteddict.py", line 248, in __delitem__
      dict.__delitem__(self, key)
    KeyError: PyQt5.QtCore.QDateTime(1986, 1, 1, 0, 0)

- 'DocumentView' object has no attribute 'showSearchView'
  Traceback (most recent call last):
    File ":/pkdiagram/graphicaltimelineview.pyo", line 122, in onSearch
  AttributeError: 'DocumentView' object has no attribute 'showSearchView'
- AttributeError 'NoneType' object has no attribute '_onAddMarriage' 
    pkdiagram\commands.pyo:480 redo
- AttributeError 'NoneType' object has no attribute 'itemOpacity' 
    pkdiagram\objects\marriage.pyo:589 updatePathItemVisible
    pkdiagram\objects\person.pyo:644 updatePathItemVisible
    pkdiagram\util.pyo:617 go
    pkdiagram\objects\pathitem.pyo:281 onCurrentDateTime
    pkdiagram\scene.pyo:1440 onProperty
    pkdiagram\objects\property.pyo:170 set
    pkdiagram\scene.pyo:1865 resetAll
    pkdiagram\mainwindow.pyo:2201 onResetAll
- AttributeError 'PersonPropertiesModel' object has no attribute 'deceasedDate'
    pkdiagram\models\personpropertiesmodel.pyo:142 · set
    pkdiagram\models\qobjecthelper.pyo:263 · _cachedPropSetter
    pkdiagram\models\qobjecthelper.pyo:50 · propSetter
- On select all in the timeline and delete:
  Traceback (most recent call last):
    File "/Users/patrick/dev/familydiagram/pkdiagram/mainwindow.py", line 1973, in onFlashPathItems
      if item.isEvent:
  AttributeError: 'NoneType' object has no attribute 'isEvent'  
- AttributeError pkdiagram\objects\marriage.pyo:589
  - 'NoneType' object has no attribute 'itemOpacity'
  - https://app.bugsnag.com/vedana-media/family-diagram-python/errors/617adf5ccf85a30007fe4a5c?event_id=617adf5c008941e277920000&i=em&m=nw
- AttributeErrorpkdiagram\commands.pyo:480
  - 'NoneType' object has no attribute '_onAddMarriage'
  - https://app.bugsnag.com/vedana-media/family-diagram-python/errors/617adea79f80210008294d0b?filters[event.since]=30d&filters[error.status]=open&pivot_tab=event
- Manual Testing Ideas:
  - Open via 1) Double click in Finder, 2) drop on Dock icon, 3) Double-click in Windows
    - Stored free license shouldn't open file
  - Load free diagram from appConfig session
  - Save show current date in prefs
  - Import free diagram
  - Init logged in w/ client license, but w/o server clears free diagram
  - Tabular Timeline doesn't update on current date
  - Server updates when logging in 1 / out / in 2
    - Log in as user 1 w/ access rights to user 2's free diagram
    - Observe can see user 2's free diagram
    - Log in as user 2, remove access right
    - log in as user 1, observe user 2's free diagram gone from server view
    - test when user 2's free diagram is last opened file that it closes or doesn't open it after updating access from server
  - App with cached session can recover if user deleted on server.
  - bugsnag_before_notify
- Hitting Escape with pair-bond item mode leaves orphaned pair-bond dragCreateItem


WISHLIST
=============================================================================
- Show/Hide graphical timeline doesn't work on windows.
- Next/Prev event doesn't work on windows
- QUndoStack Timeline in Qml?
- Zoom graphical timeline by rubber-banding a time window.
- FileManager icons too low constrast in dark mode
- Auto-commit session in SQLAlchemy()?
- Audit table:
  - Store per-day backups for user convenience
  - Revert UI as with public diagrams
- Add more color markers for rows (only "nodal" is not enough)
  - Arbitrary colors or categoies?
  - Categories: Nodal, Symptom 
- Marriage doesn't highlight when adding child.
- Show variables for marriage events on diagram
- Editing variable values requires close/open to show on diagram
- Add callout and all items disappear (creates layer, everything disappears)
- Timeline Variables:
  - Have to repeatedly click to enter a variable value when creating an event. 
  - Manual variable sorting.
  - can't scroll the list of variables in the Settings area. Same with Tags.
  - Save custom variable templates.
  - Add current cell notion on click for variables list. Should allow typing adfter a single click to enter a value.
  - Add optional range of values to each variable.
    - Float/Integer range
    - Custom string-based combobox selection
- Add diagram notes field to user manual
- Add person meta properties to user manual:
    Because the app is based on Bowen Theory, extra care is taken to separate what is a part of theory and what is not. Substance use would be “content” of emotional “process,” and so does not have a specific feature in the app for it. In fact, the main difference with the genogram is that McGoldrick and Guerin began adding a multitude of symbols for every piece of content that as was requested. The only built-in features in the app pertain to the aspects of emotional process described in Bowen Theory.
    That said, it is still useful to keep track of the content of emotional process and to somehow illustrate it in presentations. That was Layers are for. Layers allow you to make content-oriented annotations on the diagram in a way that is separate from the data of emotional process required by theory. You can add any number of layers that function like powerpoint slides in a presentation. For people, Color is a property stored in a layer and can be found in the Meta tab when you inspect a person. To set color, you have to add a layer to the diagram and click the Active checkbox. Then just inspect the person and set the color under the meta tab. A Color for that person is then stored in that Layer and is visible whenever the layer is active. Clicking the Reset Diagram button in the top toolbar deactivates all layers and hides all meta properties.
- Limit number of activations per license
  - Allow to manually reset number, i.e. after user calls in to support
- Add indicator for how many events are hidden in timeline
  - Associate clear button with indicator?
  - Add as pop-up horizontal rect at bottom of timeline?
- Show "No events under current search criteria."
- Test set person properties on active Views
- Windows: Sign app
  - Get SSL cert
  - https://docs.microsoft.com/en-us/windows/win32/appxpkg/how-to-sign-a-package-using-signtool
  - MAKE PACKAGE: https://docs.microsoft.com/en-us/windows/win32/appxpkg/make-appx-package--makeappx-exe-
- Add reverse tags again? (Good grief...)
  - Or just specialize into "Basic Pattern" checkbox.
- Can't backtab from DatePickerButtons
- Be able to move pair-bond lines up and down?
- Set View active with no people added screws up scene.
- Pair-Bond Events out of order (Priscilla Friesen email 2pm 4/6/21)
- Show/Hide Items with Notes on diagram doesn't apply to currently hidden items.
  - Sometimes showing/hiding with tags and/or layers re-shows notes icon in diagram.
- Clicking "& Ended" event in timeline doesn't flash symbol item in diagram.
- New case doesn't create file on iCloud Drive.
  - Click new button -> local folder changes from iCloud drive folder to local docs folder.
- Add way to add a person without a birth date as a "buddy" to another person so that they are not shown until the buddy is shown?
- Scrolled timeline doesn't reset scrollY on search. Search results do not show until first scroll event which resets scrollY.
- Adding event for today sorts after "now event". Should sort before.
- Name not shown for Janis O's brother Jim's death
- Licensing bugs:
  - License not activated on dev w dev server.
  - Email confirmation code box is not full width.
  - Changing password with free license invalidates free diagram and erases it.
- Free license status doesn't automatically open free diagram, and file browser is frozen.
- Double-check commands.RemoveItems.undo() re-adds layers to scene when no LayerItems exist.
- Write test for SceneModel.hasActiveLayers - doesn't have "()" in &.get()
- More obvious selection aura (especially for emotional process symbols)
- Add help for research data models.
- Presentation mode button placeholder disappears when clicked
- Windows: Video of install instructions.
- Markdown in notes?
- Remove all non-pip dependencies from server.
  - Qt: QEASEncryption
  - PyQt: Database
  - pkdiagram.constants
- Add "On Diagram" for personal events too?
- Add a way to show a basic emotional pattern
  - Can views work for this? Why can't a tag work for this?
- Can't cancel subscriptions? (main_qml.py :: AccountDialog)
- Optimize *.updateDetails|updateGeometry to single call in scene.read()
  - Each is called way too many times for Marriage.
- Windows: AppCenter Analytics REST API
- Click person note icon, click emotion|marriage w notes icon -> notes tab not retained.
  - Make PathItem.onShowNotes atomic operation w/ DocumentVew WRT selection+drawer swaps
- Licenses: Limit # of machine activations per license; show confirm box before deactivate.
- Add description of show items with notes feature to manual.
- Menu item to switch between light and dark mode.
- Flash event dot on bottom timeline when clicking on tabular timeline.
- Event notes sometimes not updating when opening new family (Laura).
- Event note icons move when undo/redo add event
- qrc:/qt-project.org/imports/QtQuick/Controls.2/ComboBox.qml:56: TypeError: Cannot read property 'width' of null


iOS
===============================================================================
- Font sizes too big
- Auto-capitalization of username/password fields is extremely cumbersome


v1.2.0
=============================================================================
- Verify default window size is big enough to fit account dialog.
- test_person.py::test_detailsText_pos - person.setDiagramNotes('here are some notes') adds two lines to ItemDetails
- +[NSXPCSharedListener endpointForReply:withListenerName:]: an error occurred while attempting to obtain endpoint for listener 'com.apple.view-bridge': Connection interrupted
  - Only on python?
- Ensure no LayerItem orphans when deleting layers.
- Excel export is broken
- Show "Editing (n) Events" in event properties title.
- Group box labels in diagram settings don't honor dark mode.
- Emotional process symbol colors all default to same value.
- File browser name issue is when modified date is changed in one file.
  - File mod times don't update when saved|touched
  - Was editing name for file created in morning (Peyton) when existing file edited afterwards (Siri) jumped into place.
    - Its like all the other entries didn't update to match.
- Discount codes (students)
- 'Update available' button
  +  https://stackoverflow.com/questions/9955676/add-buttons-to-mac-window-title-bars-system-wide
  +  https://stackoverflow.com/questions/54708798/get-window-handle-from-qt-on-mac
- add white fade to bottom of scroll area in AccountDialog
- Add file manager overlay with CTA to open account when app is disabled b/c of no alpha license, or b/c of crucial update.
  - Remove existing QMessageBox alert in setActiveFeatures()
  - Verify that deactivating last license on alpha version shows CTA.
- Re-add Edit -> Cut|Copy|Paste for text
  - Use Text[Field|Input|Edit].canPaste|paste
- Be able to use keyboard arrows, etc in Callout.
- Speed up QGV performance
  - Text rendering
  - https://stackoverflow.com/questions/43826317/how-to-optimize-qgraphicsviews-performance
  - https://stackoverflow.com/questions/19113532/qgraphicsview-zooming-in-and-out-under-mouse-position-using-mouse-wheel
  - https://doc.qt.io/qt-5/qgraphicsview.html#cacheMode-prop
  - https://forum.qt.io/topic/113144/qpainter-painttext-very-slow-in-qgraphicsview/6
- Custody does not show for unamed person.
- Callout box position doesn't save with Priscilla's diagram [Braud copy.fd]
  - Could be because of transition of adding "Store geometry" to layers"
- Allow typing only months or only years and automatically fill in month/day as `1`
- Add event from personal timeline doesnreturns to person props not personal timeline
- Can't edit multiple marriages.
- Fix date buddy contextX bug
- Add + notify of extra cc charge (from Stripe guide)
- Validate zip code against credit card: https://stripe.com/docs/disputes/prevention/verification
- Not deceased but with deceased date still shows date in timeline.
  - test_timelinemodel.py::test_dont_show_not_deceased_with_deceased_date
  - Adding a person to the scene with deceased date already set calls
    scene().addItem(self.deceasedDate) from Person.itemChange which
    emits Scene.eventAdded, then event is added to timeline in TimelineModel._do_addItem
    which obiovusly doesn't consider Person.deceased.
  - It is not clear how to handle this yet.
- [Debug build only] Zooming way into pencil stroke -> 
  - painting/qtriangulatingstroker_p.h(139): ASSERT: "dx != 0 || dy != 0" in file painting/qtriangulatingstroker_p.h, line 139
- Add color setting to LayerItemProperties
- Snap Callout points to person|marriage
- Move session token to second Auth header.
  - Sort out what the session is for if not authorization now that user secret is used.
- Sex-defined stillbirth symbol
- Allow to "hide names" in file browser view?
- Scroll Timeline to end on init
- Separate Scene.itemRegistry into &.eventRegistry, etc?

- NOTE: Qt-5.13.1 bugs:
  // - Qt-5.13: commented out assertion in qcocoascreen.mm::QCocoaScreen::primaryScreen()
  - qtdeclarative/src/quick/items/qquicktableview.cpp
    - commented out dumping table to image file in QQuickTableViewPrivate::dumpTable b/c was raising openGL exception
  - qtbase/src/gui/painting/qcoregraphics.mm
    - commented out: qWarning() << "QMacCGContext:: Unsupported paint engine type" << paintEngine->type();
  - qtbase/mkspecs/win32-msvc/qmake.conf
    - QMAKE_CFLAGS           += /MP8
    - QMAKE_CXXFLAGS         += /MP8
  - PyQtPurchasing-5.13.0: In _apply_sysroot(): CHANGE TO: ```if dir_name is not None and dir_name.startswith(sys.prefix):```
  - qtbase/src/plugins/platforms/cocoa/qcocoaglcontext.mm (fixed in 5.10)
    - https://codereview.qt-project.org/c/qt/qtbase/+/278235/4/src/plugins/platforms/cocoa/qcocoaglcontext.mm  
    - BUG REPORT: https://bugreports.qt.io/browse/QTBUG-79139
  

v1.x.x
===============================================================================
- Associate multiple people for events?
- Add Pair-Bond beginning date
- Duplicate FD file, work on one copy, paste and replace into another.
- Think through replacing Event.parent with arbitrary person list
- Refine looks of date tumbler to look more like iOS
- Fade tag show|hide: Port tag/layer animation in LayerItem.onActiveLayers to PathItem to respond to tags
- Scalable unit test for copy+paste; include multiple births
  - Probably refactor into item.read|write
- Clone layer props [X0000]
  - Copy|paste when layer is selected resets item offset
  - Ensure layer properties are removed on delete item, cloned on copy (or maybe paste) item
  - Layer.itemProperties entries are not mapped in Layer.clone()
  - Copy, paste, undo ->
      File "/Users/patrick/dev/pkdiagram/pkdiagram/objects/person.py", line 833, in sceneBoundingRect
      if self.hasTags(forTags, self.scene().reverseTags()):
    AttributeError: 'NoneType' object has no attribute 'reverseTags'
- Add Callout outline color
- Move QmlUtils to separate file (set util as globalContext?)
- Proof User Manual
- Set KeyNavigation.backTab to work with DatePickerButtons
- Init colors being called three times on macos accent color change?
- Type name in combobox to select person in add dlgs
- Refactor qml styling to use `palette` qml attr to allow cbuilt-in controls to not need so much styling
- Standardize keyboard interface for list|table views
- Add 'Reviewed' checkbox for server files to admin mode.
- First run of animate hide toolbars isn't smooth.
- Event props hides when editing person props and selecting text in notes edit with mouse release over other Item/QWidget
- Block wheel-zooming when animating zoomFit
- Timeline Search reset function is not optimized.
  - Add modelReset signal
- Drag snap to inner box of primary person.
- Ask Qt forum about consolidating DatePickerButtons, DatePicker inside Gridlayout
- Make it possible to only export selected tags.
  - Add private tag to Patrick Stinson diagram
- Move hideColumns into TableView?
- Make Drawer and graphical timeline top-level peers to View, shrinking on showing
  - Add toolbar on the right to balance out toolbars/collapse, add drawer buttons
  - Buttons
    - Timeline: Always show
    - Person, pair-bond, emotion, layer item based on selection
    - Add event: Always show
    - Add emotion: Always show
- Events
  - Pair-bond events.
    - Together
    - Separation
    - Marriage
    - Divorce
    - Moves
  - Refactor TimelineModel to only use events?
    - Refactor Emotions to have startEvent, endEvent?
- Set maximum zoom to prevent just showing 1, or two people in full screen.
- Figure out how to add arbitrary events which also update diagram
  - Adoption, met/bonded, married, separated, divorced
- Welcome Screen:
  - "All diagrams and symbols of family emotional process are at risk for being simplistic or reductionistic. Diagrams are also at risk for honeying the image of a static situation rather than a dynamic process." (Kerr, 1987, p. 156)
- Server logging: http://flask.pocoo.org/docs/1.0/logging/?highlight=log
  - Get server.log to store in separate file (currently going to syslog?)
  - Email errors to admins
- scene.jumpToNow() doesn't compress layer[s].setActive(False) into the other commands.
- Need to add generic events to Pair-Bonds
- Allow import to free diagram so clinicians can share with clients.
- iCloud. (post to stackoverflow for setUbiquitous)
  - Disable iCloud doesn't copy files to local
  - Enable iCloud doesn't copy files to iCloud
- Profile/Optimize view resizing, timeline animation, etc.
  - TimelineTable is unbelievably slow
- Aesthetics
  - Style welcome screen after iMovie, Photos, iWork welcome screens.
  - Include citations to demonstrate theoretical concepts for symbols, etc.
- Autocomplete person name box for add event dlg.
- Need a way show emotional distance/cutoff to more than one member.
- Allow excluding tags from export to make 'private' tags.
- Print visual timeline with transparent bg for PNG (ask qt forum: render w/o bg)
- Investigate not being able to select people in Katherine's diagram on High Sierra.
- Katherine's diagram on server [Barker] has 'Patrick' == '<not set>' in timeline
- Persistant 'Purchase' button.
- Reset command ids for scene?
  - Or actually, associate undo stack with scene?
- Feature Subscriptions
  - 1) `Personal`: Free; One diagram (trial period?)
  - 2) `Professional`: Many diagrams
  - 3) `Presenter`: Presentation tools
  - 4) `Geneologist`: Files and photos.
  - 5) `Researcher: Server access (need curated data)
  - Stand-alone Files feature?
  - Promo codes: Education; Bowen Center; Individuals
  - Limit presentation features for free license?
- Secure purchases.
  - Using Apple receipt validation? (official Apple pathway)
  - Using KeyChain?
  - Using pkdiagram server?
  - https://developer.apple.com/library/archive/releasenotes/General/ValidateAppStoreReceipt/Introduction.html#//apple_ref/doc/uid/TP40010573-CH105-SW1/
  - Test that license is loaded before app handles QEvent.FileOpen event on dbl-click in Finder.
- What about user accounts?
  - What would they be used for?
  - Do I need a back end?
  - What isn't covered in the apple id login?
- Dismantle vedana forum in favor of google groups (duh!)
- Write documentation
  - Help -> Documentation => http://vedanamedia.com/our-products/family-diagram/beta-program/

Maybes
--------------------------------------------------------------------------------
- Move download button to pinButton location
- Accidental zoom fit on scene load doesn't set dirty.
- Show[middle|last|nick]name boxes set partially checked when all values are simply None (QT BUG)
- Draw selection outline for pencil paths
  - https://forum.qt.io/topic/62142/qpainterpath-from-list-of-points/22
- Flash parent item on event when selected in timeline.
- Add progress indicator on load file


iOS
------------------------------------------
- Rigorously test orientation changes + screen resizing and auto zoomFit()
- Add prev/next layer buttons to scene toolbar
- Add prev/next date buttons to scene toolbar
- Slow down drag-scroll on tableview on iOS
- "Syncing to Server..." Dialog gets stuck in simulator when host not connected to wifi.
- File Browser buttons scrunched in portrait on iPhone.
- List views don't scroll with drag.
- Hide ios status bar


Inclusion of Literature
-------------------------------------------------------------------------------
- Laura's framework
  - Link to journal article.
  - Laura's email 2019-02-11 email Re: "symptom" VS "functioning"
- Papero's framework
  - Link to journal article.


Version 2.0.0
================================================================================
- Track triangles?
- Create diagram from Questionairre (Mike)
- Search function; useful for large diagrams.
- Prevent prefs.sync in favor of automatic sync behavior.
- Allow operating system to handle saving changes to documents as in Pages.
- Add date bookmarks, bookmark menu to main app menu.
- Clean up orphaned files function (some files may exist for people who don't exist?).
- Add ctrl-click for multi-select layers.
- Add duplicate layer action, or maybe copy|paste later data.
- How to link relationships to events timeline? Cycling through events can skip relationship shifts.
- Add place detection to Events.
- Prioritize showing nodal events in visual timeline.
- Autosave
- Item descriptors (shift symbols)
  - Dotted person pen for differentiation level
    - "Defined self" as dashed lines of increased interval
    - Automatically scale dash length based on overall shifts up and down in person.
  - Fill color/saturation for anxiety
  - blur / jagged lines for something else
  - Arrow overlay on emotional process symbol for direction
  - Need 'distance' symbol for one person to group (slash toward people?)
- Sort tags on rename tag
- Set icon for file from scene rendering
  - https://stackoverflow.com/questions/38486934/how-to-programmatically-set-the-file-icon-on-os-x
- Find a way to enforce relative event order. More important than precise dates.
  - Maybe enforce a mix of drag-order and dates?
- Add tag/date search to personal history.
- Consolidate add|edit event|emotion properties
- Redundant setTextWidth in Callout.onText?
- Set 'One moment...' dialog to show after timeout?
  - this dialog is annoying, anyway


WISHLIST
===============================================
- Events
  - Add photos/video for family collections.
  - Find a way to show "fuzzy" date ranges (add estimated end-date)
    - Allow just year, just year+month, or season+year.
  - Think about necessity of "unsure" for relative order.
  - Display anxiety shade on anxiety shift.
- Items
  - Add photos with dates
  - Think of some way to show frequency of contact between people.
  - Ecomap-ish symbols to account for extra-familial relationships
- iPad/Apple Pencil
  - Handwritting recognition!
    - Allow drawing in males and females.
    - Allow writing in QLineEdit.
  - Check event order for jagged lines
  - Splining (QSplineSeries/SplineChartItem, stackoverflow)
  - Feedback indicating pencil strokes are associated with person when person selected
  - eraser
    - paint eraser path
    - highlight intersected strokes
    - delete strokes on release
- Review PDF expert for scene toolbar examples
- Files
  - Share file to collaborate with others (no idea how to implement)
  - Import/export selection to excel for working on planes
  - Collaboration between client & coach
    - Powerful considering free status of app
    - Will help propagate the app
- EHR
  - Core Principle: Keep it centered on the family
    - Don't get sucked into full-blown bloated EHR project unless compatible with family theory
  - Sharing multiple families together - Social? Business? School?


Videos
==========================================
- Use tags
- Navigation: pinch-zoom|alt-drag|alt-zoom|callout anchor-drag.


OPTIMIZATION
------------------------------------------
- Move emotion painting to _cutils, especially Jig
- Optimize copy/paste, import
  - Import should not duplicate imported items to paste
  - Clipboard.copy should not have to clone+remap items to determine if they should be copied?
    - Currently has to call Scene.deregister, which is overkill...
  - Refactor Clipboard.__init__|copy to single method?




Test Protocol
==========================================
- Check for deleted objects; avoid memory leaks
- Double-tap hotspot
- Test on older macOS


RELEASE STEPS
==========================================
- update version.VERSION_*
- verify version.VERSION_COMPAT
- build osx-release
- update server source

