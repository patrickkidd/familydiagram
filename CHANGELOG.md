# Changelog

All notable changes to Family Diagram are documented in this file.

## 2.1.18

## 2.1.18b1

- Very large diagrams load in seconds instead of minutes.

## 2.1.17

## 2.1.17b1

- Click row in timeline sets the diagram to that date.
- Fixed broked "Add birth" and "Edit birth" buttons in person properties
- Fixed person picker in add form not showing renamed people in auto-complete.
- Can now use down/up arrows + enter/return to pick a person via autocomplete in add event form.
- Visual timeline shows person names now.

## 2.1.16

## 2.1.16b2

- Fixed error when re-opening diagram after deleting a view with people in it.

## 2.1.16b1

- Added date certainty field

## 2.1.15

## 2.1.15b2

- Fixed bug where birth events would disappear when the person being born was listed on any other events.

## 2.1.15b1

- Fixed bug where SARF shifts show on diagram for people other than the one
  mover person in the event.


## 2.1.14

## 2.1.14b1

- Fixed bug opening diagrams with error about `hideSARFGraphics`


## 2.1.13

## 2.1.13b1

- Added people field to SearchDialog
- Rearranged and re-named person fields in EventForm to be more intuitive
- Edit SARF variables in timeline
- Add option to hide variable graphics in diagram
- Auto-focus people picker on click to add person for easier typing


## 2.1.12

## 2.1.12b1

- Moved autosave out of documents folder to app data folder

## 2.1.11

## 2.1.11b1

- Server-stored diagram format updates to allow syncing documents with coming
  personal/mobile app

## 2.1.10

## 2.1.10b1
- Added autosave
    Implements automatic saving of diagrams to a dedicated "Family Diagram Autosaves"
    folder in the user's documents directory.
    
    Features:
    - Immediate auto-save when a document is opened
    - Periodic auto-save every 30 minutes while document is open
    - Timestamped filenames (YYYYMMDD_HHMMSS format) compatible with tiered retention
    - Auto-save stops when document is closed or for read-only documents
- Added changelog to auto updates

## 1.5.2
- Flash associated items on the diagram for newly highlighted events in next / previous event.
- Fixed deleting a large selection of events in the timeline.
- Fix emotions not fanning out when changing search tags

## 1.5.1
- Shift-Command-F (Shift-Ctrl-F on Windows) to search
- Toward description now says: "Person A to Person B" instead of "Person A & Person B"
- Away description now says: "Person A from Person B" instead of "Person A & Person B"
- Add "Is Date Range" checkbox to Relationships.
- Added preferences setting to override OS dark mode setting.
- Fixed bug preventing new users being unable to run the app.

## 1.5.0
- Setting a tag on a relationship symbol sets it on start/end events, and vice-versa.
- Add button to Stripe customer web portal in account manager view.
- Added tags column to timeline.
- Stretch parent column somewhat in timeline view.
- Renamed all remaining instances of "Layer" to "View"
- Graphical timeline: View now limited to entered search date range.
- Graphical timeline: Shows day date under mouse cursor.
- Graphical timeline: Click to jump to current date in graphical timeline
- Graphical timeline: Fixed wheel-scrolling for graphical timeline on Windows.
- Fix bug making it difficult to double-click and edit variable values.

## 1.4.3
- FIx some problems loading app in strange deployments.

## 1.4.2
- Fixed automatic updates.

## 1.4.1
- Don't encrypt files unless saving to free diagram.

## 1.4.0
- Store free diagram on server for better backups
- Added important update button in top tool bar

## 1.3.3
- Much easier to follow Relationship symbols as they animate for shifts.

## 1.3.2
- Fixed multiple emotions between the same people.
- Fixed clearing dates for emotions.
- Fixed bug in person color animations.

## 1.3.1
- Fixed zoom-fit button.

## 1.3.0
- New more accurate symbols for Toward and Away as singular moves.
- Old "Toward" and "Away" symbols become new "Inside" and "Outside" symbols, respectively. - Old "Toward" and "Away" symbols become new "Inside" and "Outside" symbols, respectively.
- Made defined self symbol more visually accurate as a momentary move.
- Duplicate rows are not added when symbol start/end dates are the same. Makes it easier to track momentary shifts.
- Allow setting time of day on events for tracking rapid emotional process. Allows for daily/vignette logging.
- Reorganize Layers, Tags, Search
- Renamed Layers to "Views" - Renamed Layers to "Views"
- Views become diagram/structure only, and don't have tags any more - Views become diagram/structure only, and don't have tags any more
- Tags become timeline/function only - Tags become timeline/function only
- People don't have tags now, they are just added to Views. - People don't have tags now, they are just added to Views.
- Replace tag list on Person Properties with views list - Replace tag list on Person Properties with views list
- Only one search panel for entire app now, includes "Views" list. - Only one search panel for entire app now, includes "Views" list.
- Search tab replaces "Meta" Tab under family timeline - Search tab replaces "Meta" Tab under family timeline
- Top, Left, and Right toolbars are scrollable now.
- Simplified timeline buttons with only inspect, delete.
- Only one add event button / add emotion button now, found in timeline.
- Moved diagram delete button from top tool bar to right tool bar.
- Better selection aura on the diagram

## 1.2.8
- Fixed miscellaneous bug.

## 1.2.6
- Next/Prev event honor timeline tags.

## 1.2.5
- Fixed freeze when clicking on bottom timeline.

## 1.2.4
- Included Bugsnag reporting for python and ObjectiveC.

## 1.2.3
- Patched Qt-5.15.2 to fix font rendering.

## 1.2.3a1
- Fixed some names not showing up in the timeline.
- Improved labels for layers and tags list, timeline search.
- Added help text to Layer list and Scene Tags list.

## 1.2.2
- Fixed some names not showing up in the timeline.
- Improved labels for layers and tags list, timeline search.
- Added help text to Layer list and Scene Tags list.
- Improved clicking to select items when the item text overlaps the item.
- Fixed scrolling for notes fields.
- Fixed excel export.

## 1.2.1a1
- Improved clicking to select items when the item text overlaps the item.
- Fixed scrolling for notes fields.
- Fixed excel export.

## 1.2.0
- First windows release.
- Allow adding arbitrary events to Pair-Bonds
- Renamed married, separated, divorced checkboxes to "Show XXX" for pairbond. - Renamed married, separated, divorced checkboxes to "Show XXX" for pairbond.
- Useful for showing a state the pair-bond achieved prior to knowing specific dates - Useful for showing a state the pair-bond achieved prior to knowing specific dates
- Added new event types: Bonded, Married, Separated, Divorced, Moved - Added new event types: Bonded, Married, Separated, Divorced, Moved
- Added "On Diagram" checkbox to include the event in the Pair-Bond's diagram notes - Added "On Diagram" checkbox to include the event in the Pair-Bond's diagram notes
- Added ability to show which items have notes (Ctrl-Shift-N)
- Stop on all events when timeline is shown.
- Added Stinson data model.
- Always fan out multiple emotions between the same people (no more mouse hover)
- Fixed bugs in pair-bond events.
- Fix cutoff symbol filling with black on click in timeline.
- Fix user manual on windows.
- Fixed emotion|layeritem properties getting stuck open.
- Fixed help tips not lining up correctly.
- Tidied up drawing for married events.
- Fix showing person/pair-bond name in add event / emotion dialogs.
- Don't show very high age when age at death is unknown.
- Fixed excel export.
- Invert pencil drawings when black in dark mode.
- Made the account dialog work on smaller screens.

## 1.2.0a4
- Tidied up drawing for married events.

## 1.2.0a3
- Fix showing person/pair-bond name in add event / emotion dialogs.

## 1.2.0a2
- Added Stinson data model.
- Fixed bugs in pair-bond events.
- Added provisional married, separated, divorced states for Pair-Bond
- Useful for showing a state the pair-bond achieved prior to knowing specific dates - Useful for showing a state the pair-bond achieved prior to knowing specific dates

## 1.2.0a1
- Allow adding arbitrary events to Pair-Bonds
- Removed Married, Separated, Divorced checkboxes - Removed Married, Separated, Divorced checkboxes
- *NOTE*: These values will be lost! You will need to add events with these types to reflect the status on the timeline. - *NOTE*: These values will be lost! You will need to add events with these types to reflect the status on the timeline.
- Added new event types: Bonded, Married, Separated, Divorced, Moved - Added new event types: Bonded, Married, Separated, Divorced, Moved
- Added "On Diagram" checkbox to include the event in the Pair-Bond's diagram notes - Added "On Diagram" checkbox to include the event in the Pair-Bond's diagram notes
- Don't show very high age when age at death is unknown.

## 1.1.4a7
- Stop on all events when timeline is shown.
- Always fan out multiple emotions between the same people (no more mouse hover)

## 1.1.4a6
- Made the account dialog work on smaller screens.
- Fixed excel export.
- Invert pencil drawings when black in dark mode.
- Fix cutoff symbol filling with black on click in timeline.

## 1.1.4a5
- Fix user manual on windows.
- Fixed emotion|layeritem properties getting stuck open.

## 1.1.4a1
- Added ability to show which items have notes.

## 1.1.4a0
- Fixed help tips not lining up correctly.

## 1.1.3
- Added notes indicator to timeline
- Fix bug preventing quit or show account when using free license.
- Fixed timeline search drawer and bug preventing closing of timeline.

## 1.1.3a1
- Fix bug preventing quit or show account when using free license.
- Fixed timeline search drawer and bug preventing closing of timeline.

## 1.1.3a0
- Added notes indicator to timeline.
- Fixed exception in TimelineModel.nowEvent on exit.

## 1.1.2
- Fixed bug that rejected CVC code with a leading zero.

## 1.1.1
- Fix printing.
- Add help tip to age box.
- Retain selected person properties tab when selecting new person (e.g. for timeline).
- Upgrade to Qt-5.15.0.

## 1.1.1a0
- Fixed bug with printing.
- Update software toolkits.
- Other bug fixes.

## 1.1.0
- Show variable values on diagram!
- Checkbox to hide variables on diagram. - Checkbox to hide variables on diagram.
- Checkbox to show variable states on diagram versus just changes. - Checkbox to show variable states on diagram versus just changes.
- Variable changes bold on diagram, steady states semi-opaque. - Variable changes bold on diagram, steady states semi-opaque.
- Unify timeline search into single search for whole diagram.
- Add help overlay in Help -> Show tips... or command-shift-H
- Fade items when animating diagram.
- Fade labels when zooming in and out.
- Hide item details when too small to read.
- Fix timeline search for person and marriage.
- Remove meta tab from pair-bond properties.
- Confirm discarding changes for add event or emotion dialog.
- Fixed clearing timeline search when clicking "Reset Diagram"
- Fixed clearing timeline search when opening a second diagram.
- Decrease width of person column in timeline.
- Additions to user manual.
- Other bug fixes.

## 1.1.0a5
- Fade items when animating diagram.
- Fade labesl when zooming in and out.
- Fix timeline search for person and marriage.
- Remove meta tab from pair-bonds b/c tags on a pair-bond don't make sense.
- Other bug fixes.

## 1.1.0a4
- Checkbox to hide variables on diagram.
- Checkbox to show variable states versus just changes.
- Confirm discard changes for add event or emotion dialog.
- Additions to user manual.
- Clear timeline search when clicking "Reset Diagram"
- Fixed clearing timeline search when opening a second diagram.

## 1.1.0a3
- Unify timeline search into single search for whole diagram.
- Decrease width of person column.

## 1.1.0a2
- Add help overlay in Help -> Show tips... or command-shift-H
- Make variable changes bold on diagram, steady states semi-opaque.
- Hide item details when too small to read.

## 1.1.0a1
- Show variable values on diagram.
- Bug fixes.
- Disabled all research server functionality
- Proofed manuals.
- Other bug fixes.
- Show active layer sin window title bar and upper right corner of diagram.
- Fade transitions between layers.
- Print in dark mode.
- Other bug fixes.
- Removed "Store Positions" checkbox in layers in favor of per-layer "Store Geometry" checkboxes.
- Fixed double-click on diagram file to open file from Finder.
- Other bug fixes.
- Make right toolbar stay at edge of right drawer.
- Fixed button tooltips.
- Fixed setting emotion dates on timeline.
- Fixed text callouts and pencil drawings jumping around after opening the diagram.
- Fixed macOS promting saying it can't verify that the app is safe.
- Other bug fixes.
- Disable trackpad/wheel-panning by default in favor of option-drag.
- Updates to User Manual
- Fixed dragging pencil strokes.
- Bug fixes.

## 1.0.0
- Initial release

## 1.0.0b9
- Fixed separation / divorce symbol not showing on diagram until after closing and reopening diagram.
- Fixed mouse double click to use macOS system setting to make it consistent with other apps.

## 1.0.0b8
- New integrated timeline includes relationships (emotional process symbols) and events timelines.
- Time-span of emotional process symbols (conflcit, distance, projection, fusion, etc) are now visible as colored lines in timeline. - Time-span of emotional process symbols (conflcit, distance, projection, fusion, etc) are now visible as colored lines in timeline.
- Timeline highlights start date/end date of emotional process symbol when relationship symbol selected. - Timeline highlights start date/end date of emotional process symbol when relationship symbol selected.
- View -> Next/Prev Event action skips redundant dates for smoother animation. - View -> Next/Prev Event action skips redundant dates for smoother animation.
- Construct "scenes" by setting which tags to show in a layer.
- Allows switching focus between subsystems in larger family. - Allows switching focus between subsystems in larger family.
- Allows to use diagram as geneological project while still maintaining a focus on differentiation of self. - Allows to use diagram as geneological project while still maintaining a focus on differentiation of self.
- Can show/hide people based on tags (View -> Tags) - Can show/hide people based on tags (View -> Tags)
- Visual timeline now draws tags as separate rows of events.
- Includes "Sillivanian time" checkbox to line up tag rows in number of years since first event in each row. - Includes "Sillivanian time" checkbox to line up tag rows in number of years since first event in each row.
- Improved visual timeline zooming with <alt>-mouse wheel combo. - Improved visual timeline zooming with <alt>-mouse wheel combo.
- Twins are now drawn as in Harrison's book.
- Hover mouse over relationship symbols which overlap in time to expand them.
- Allows unlimited documenting of simultaneous triangle positions - Allows unlimited documenting of simultaneous triangle positions
- Added user manual to Help -> User Manual
- Added Welcome screen with links to seminal Bowen literature.
- Event search terms are saved in diagram.
- Can now add custom research model, w/ Havstad + Papero models as default.
- View -> Jump to Now action now serves as 'home' button; resets search terms, tags, current date, etc.
- Single-click on different person with person properties open edits the new person.
- Added button to reset person layered properties to default now.
- Added "Use Real Names" checkbox to avoid using aliases on server (e.g. for public figures)
- More obvious selection color
- Completely re-wrote server with strong encryption.
- Encrypted app config manages licenses per-machine.
- Beta versions are now deactivated when new version is released.

## 1.0.0b7
- Added layers to overlay notes onto data for presentations.
- Added text callouts to layers.
- ⌘-Shift-F to  "Add Parents to Selection".
- ⌘-delete to delete items now to prevent accidental deletions.
- Can drag pair-bond divorce/separation line left and right to avoid overlapping other items.
- More precise item sizing (existing details text may be off for people and pair-bonds).
- Alt-Wheel to zoom into cursor.
- Alt-Drag on diagram background to pan diagram.
- Added location fields to Pair-Bond (marriage, separation, divorce) events.
- Added Events tabs and geographical moves to pair-bonds.

## 1.0.0b6
- Added "Relationships" tab to edit emotional process over time.
- Added new experimental relationship symbols:
- Toward symbol - Toward symbol
- Away symbol - Away symbol
- Distance symbol - Distance symbol
- Defined-Self symbol - Defined-Self symbol
- Added "tags" to Events, Relationships, People
- Added search params for timeline (date range, logged date range)
- Added Undo history tab
- Added Quick-Add Event Tool (⌘-E)
- Added Quick-Add Relationship Tool (⌘-R)
- Added Graphical Timeline to holistically view events and nodal events over time.
- Added Keyboard commands for clinical use:
- ⌘-E       - Add Event - ⌘-E       - Add Event
- ⌘-R       - Add Relationship - ⌘-R       - Add Relationship
- ⌘-M       - Add Male - ⌘-M       - Add Male
- ⌘-F       - Add Female - ⌘-F       - Add Female
- ⌘-M       - Add Pair-Bond - ⌘-M       - Add Pair-Bond
- ⌘-C       - Add Child-Of - ⌘-C       - Add Child-Of
- ⌘-1       - Show Diagram - ⌘-1       - Show Diagram
- ⌘-2       - Show Timeline - ⌘-2       - Show Timeline
- ⌘-3       - Show Graphical Timeline - ⌘-3       - Show Graphical Timeline
- ⌘-4       - Show Relationships - ⌘-4       - Show Relationships
- ⌘-5       - Show Undo History - ⌘-5       - Show Undo History
- ⌘-]       - Next Event - ⌘-]       - Next Event
- ⌘-[       - Prev Event - ⌘-[       - Prev Event
- ⌘-0       - Jump to Today's date - ⌘-0       - Jump to Today's date
- ⌘-H       - Hide Emotional Process - ⌘-H       - Hide Emotional Process
- ⌘-T       - Hide Tool bars - ⌘-T       - Hide Tool bars
- ⌘-=       - Zoom In - ⌘-=       - Zoom In
- ⌘--       - Zoom Out - ⌘--       - Zoom Out
- ⌘-Shift-1 - Zoom Fit - ⌘-Shift-1 - Zoom Fit
- ⌘-Shift-2 - Center Diagram - ⌘-Shift-2 - Center Diagram
- Added shift-drag person to snap vertically to other people.
- Added View -> Center Diagram action.
- Improved performance of changing current date for complex diagrams.
- Can rename cases from within app now.
- Can delete cases from within app now.
- Made it easier to select overlapping items.
- Added (experimental macros to record keyboard and mouse events for often-used diagram elements.

## 1.0.0b5
- Added cutoff symbol with date range.
- Scroll timeline to show new event when added.
- Allow editing events from timeline.
- Can inspect selected event with <command>-i
- Fixed showing Family Alias in app title bar.
- Fixed showing, hiding names on server & timeline.
- Fixed bug in editing emotions.
- Added option to re-open last file.
- Added View -> Center Diagram.

## 1.0.0b4
- Added pinch-zoom for trackpads, and option to disable this in app preferences.
- You can now edit attributes of multiple people at once.
- Events can now be added via the timeline.
- Events can now be re-assigned to different people from the timeline.
- Added birth-name field to people.
- Changed fusion to to straight lines.
- Fixed exporting as image for presentations.
- Added "Check for updates..." to help-menu to automatically update the app when a new version is available.
- You can now set a separation date for marriages.
- Unmarried couples now have dashed lines.
- Separated couples now have one cross-out line.
- Divorced couples now have two cross-out lines.
- Adoptions now show as dashed lines.
- Child-custody is now indicated by slating top of divorce/separation lines toward appropriate parent.
- Added View -> "Hide Names" to replace all names with pseudonyms. Helpful for maintaining anonymity.
- Show server pseudonym under "Settings" tab on timeline, so you can pass your anonymous case on to others.
- Added keyboard shortcuts to "Insert" menu actions for quickly adding male, female, marriage, child, fusion, cutoff, conflict, projection.
- Disabled functioning up/down arrows for now. This symbol will be re-enabled when it is integrated with the principle of time. If you have already set a person to function up or down you will be able to keep it or clear it.
- Added link to Bowen Center for help on theory in about menu.
- Fixed bug where double-clicking on diagram file in Finder would crash app.
- Diagram modification dates are now shown in file manager.
- Fixed many bugs in undo functionality.
- Many other bug fixes.

## 1.0.0b3
- Initial functional beta release.

## 1.0.0b2
- Added auto-updater for when new app versions come out.
- Added "Check for Updates..." menu item.
- Fixed bug in editing birth date
- Fixed showing divorce line based on details
- Fixed enable/disable edit commands based on selection
- Fixed person properties covering child details
- Fixed maintaining relative position when person size changed
- Fixed adding more than one case file within one minute
- Fixed maintaining relative position when person size changed
- Fixed watching iCloud drive on dev.
- Added conditional post python exception.

## 1.0.0a21
- Bug fixes.

## 1.0.0a20
- Added user account dialog with license store - ALPHA LICENSE IS NOW REQUIRED!
- Updates to user manual.
- Added ability to choose between iCloud Drive and custom documents folder path.
- Added End User License Agreement dialog.
- Added checkbox to enable/disable storing item positions in layers.
- Fixed resetting person layer position.
- Fixed default marriage details position.
- Fixed crash for some diagrams.

## 1.0.0a19
- Fixed crash loading some diagrams (emotions with no parentItem()).
- Fix some scenes not centering on load.
- Slightly better diagram performance.
- Fix can't drag selected primary person.
- Other bug fixes.
- Increased font size
- Added "Big Font" checkbox for increasing font size on Person and Pair-Bond.
- Made "Big Font" and "Hide Details" settings stored in layers.
- Store Person and Pair-Bond text positions in layers.
- Improved functioning of layers.
- Added left-hand Ctrl+Shit+D shortcut to Pair-Bond
- Fix emotion size box.
- Many other big fixes.
- Added "Hide Relationship Colors" checkbox to show colors for emotional process symbols.
- Standardlized order of emotional process symbols as nuclear family process then cutoff
- Cleaned up cutoff symbol
- Added duplicate layer button.
- Moved inspect button to right toolbar.
- Flash people, pair-bonds, emotions when clicking/selecting on timeline
- Fixed bugs with selecting and editing a range of events in a timeline
- Fix some bugs with marriage text/separation indicator

## 1.0.0a14
- Show events for all selected people - very useful!
- Hide names in all descriptions and notes when "Hide Names" selected.
- Add "age" box to estimate person's birth date based on current age.
- Fixed bug where add event/emotion names didn't update when hiding names.
- Fixed bug where remove/inspect buttons don't activate on timeline selection
- Just list emotional process symbol type when dates are same day instead of 'started' or 'ended'
- Simpler graphical interface for similar look and feel across Windows/iPhone/iPad
- Added timeline control to bottom of diagram.
- Added dyadic Reciprocity arrows symbol.
- Added "Diagram Notes" field for people and pair-bond; Displays on diagram.
- Added option for unknown biological sex of person.
- Added search terms to visual timeline.
- Added search terms to personal timeline, pair-bond timeline
- Added Diagram toolbar to right-hand side
- Added button to reset diagram.
- Added button to fit diagram to screen.
- Added option to show real names on server, with optional password protection.
- Added support for Apple Dark Mode.
- Improved behavior of layers and tags.
- Improved performance of timeline views.
- Improved behavior of animations and window resizing.
- Added search in file manager.
- Major performance improvements for large diagrams.
- Added Many new and improved keyboard shortcuts, listed in "Edit" and "View" menus
- Command-I: Inspect Item/Timeline/Notes/Meta of selected Person/Pair-Bond/Relationship. - Command-I: Inspect Item/Timeline/Notes/Meta of selected Person/Pair-Bond/Relationship.
- Command-E: Add event for selected item. - Command-E: Add event for selected item.
- Command R: Add relationship for selected person. - Command R: Add relationship for selected person.
- Added buttons for next, previous layer for presentations.
- Improved mouse handling.
- Hold command + drag diagram to move up down/left right. - Hold command + drag diagram to move up down/left right.
- Hold command + scroll up / down to zoom into pointer. - Hold command + scroll up / down to zoom into pointer.
- Moved iPhone-like pinch-zoom-pan to optional checkbox in preferences. - Moved iPhone-like pinch-zoom-pan to optional checkbox in preferences.
- Added more extremely rough copy to User Manual.
- Many, many, many other bug fixes.

