import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "./PK" 1.0 as PK
import PK.Models 1.0
import "js/Global.js" as Global
import "js/Underscore.js" as Underscore

PK.Drawer {

    id: root

    signal cancel
    signal inspectEmotions(var events)

    property int margin: util.QML_MARGINS
    property var focusResetter: addPage
    property bool canInspect: false
    property var selectedPeopleModel: ListModel {}

    // Controls

    property var addPage: addPage
    property var addButton: addButton
    property var clearButton: clearButton
    property var cancelButton: cancelButton

    // Keys.onPressed: {
    //     // TODO: Not clear when focus makes this happen. Need to nail down field
    //     // focus auras.
    //     if((event.key == Qt.Key_Return || event.key == Qt.Key_Enter) && event.modifiers & Qt.ControlModifier) {
    //         done()
    //     }
    // }

    // State

    property var events: []
    property var isEditing: false
    property var kind: null
    property var description: null
    property var isDateRange: isDateRangeBox.checked
    property var isDateRangeDirty: isDateRangeBox.dirty
    property var startDateTime: startDatePicker.dateTime
    property var startDateUnsure: startDatePicker.unsure
    property var endDateTime: endDatePicker.dateTime
    property var endDateUnsure: endDatePicker.unsure
    property var location: locationEdit.text
    property var symptom: symptomField.value
    property var anxiety: anxietyField.value
    property var relationship: relationshipField.value
    property var functioning: functioningField.value
    property var color: colorBox.color
    property var notes: notesEdit.text
    property var tagsModel: tagsModel


    // Who

    property var personLabel: personLabel
    property var spouseLabel: spouseLabel
    property var childLabel: childLabel
    property var targetsLabel: targetsLabel  

    property var personPicker: personPicker
    property var spousePicker: spousePicker
    property var childPicker: childPicker
    property var targetsPicker: targetsPicker
    property var trianglesPicker: trianglesPicker

    // What

    property var kindBox: kindBox
    property var kindLabel: kindLabel

    property var descriptionLabel: descriptionLabel
    property var descriptionEdit: descriptionEdit

    property var symptomLabel: symptomLabel
    property var anxietyLabel: anxietyLabel
    property var relationshipLabel: relationshipLabel
    property var functioningLabel: functioningLabel
    property var inspectEmotionButton: inspectEmotionButton

    property var symptomField: symptomField
    property var anxietyField: anxietyField
    property var relationshipField: relationshipField
    property var functioningField: functioningField

    // When

    property var startDateButtons: startDateButtons
    property var endDateButtons: endDateButtons

    property var startDateTimeLabel: startDateTimeLabel
    property var endDateTimeLabel: endDateTimeLabel
    property var isDateRangeLabel: isDateRangeLabel

    property var startDatePicker: startDatePicker
    property var startTimePicker: startTimePicker
    property var isDateRangeBox: isDateRangeBox
    property var endDatePicker: endDatePicker
    property var endTimePicker: endTimePicker

    // Where

    property var locationEdit: locationEdit

    // How
    
    property var notesEdit: notesEdit

    // Meta

    property var colorBox: colorBox
    property var tagsEdit: tagsEditItem
    property var tagsLabel: tagsLabel

    onKindChanged: {
        spousePicker.clear()
        childPicker.clear()
        targetsPicker.clear()
        trianglesPicker.clear()
        descriptionEdit.clear()
        symptomField.clear()
        anxietyField.clear()
        relationshipField.clear()
        functioningField.clear()
    }

    function onStartDateTimeChanged() { // used anymore?
        startDatePicker.dateTime = startDateTime
    }

    readonly property var fieldWidth: 231

    property var dirty: false

    // TODO: Re-add migration logic

    function clear() {

        // Who

        personPicker.clear()
        spousePicker.clear()
        childPicker.clear()
        targetsPicker.clear()

        // What

        root.description = null
        
        kindBox.currentIndex = -1
        descriptionEdit.clear()
        symptomField.clear()
        anxietyField.clear()
        relationshipField.clear()
        functioningField.clear()

        // When

        startDatePicker.clear()
        endDatePicker.clear()
        isDateRangeBox.checked = false
        isDateRangeBox.dirty = false // Checkboxes need their own dirty attr

        // Where

        locationEdit.clear()

        // How
        notesFrame.clear()

        addPage.scrollToTop()
        tagsEditItem.clear()
        personPicker.focusTextEdit()
        root.dirty = false;
    }

    function currentTab() { return 0 }
    function setCurrentTab(tab) {}

    function initWithPerson(personId) {
        var person = sceneModel.item(personId)
        personPicker.setExistingPerson(person)
        tagsEdit.isDirty = false
    }

    function initWithNoSelection() {
        kindBox.clear()
        root.initPersonPicker()
        tagsEdit.isDirty = false
    }

    function initPersonPicker() {
        personPicker.clear()
        // util.debug('>>> initPeoplePicker() callback')
        personPicker.focusTextEdit()
        // util.debug('<<< initPeoplePicker() callback')
    }

    function setKind(x) {
        kindBox.setCurrentValue(x)
    }

    function setVariable(attr, x) {
        if(attr == 'symptom') {
            symptomField.setValue(x)
        } else if(attr == 'anxiety') {
            anxietyField.setValue(x)
        } else if(attr == 'relationship') {
            relationshipField.setValue(x)
        } else if(attr == 'functioning') {
            functioningField.setValue(x)
        }
    }

    // attr statuses

    function personEntry() {
        return personPicker.personEntry()
    }

    function spouseEntry() {
        return spousePicker.personEntry()
    }

    function childEntry() {
        return childPicker.personEntry()
    }

    function targetsEntries() {
        return targetsPicker.peopleEntries()
    }

    function trianglesEntries() {
        return trianglesPicker.peopleEntries()
    }

    header: PK.ToolBar {
        PK.ToolButton {
            id: cancelButton
            text: 'Cancel'
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: cancel()
        }
        PK.ToolButton {
            id: clearButton
            text: "Clear"
            x: cancelButton.x + width + margin
            visible: root.isEditing == false
            onClicked: root.clear()
        }
        PK.Label {
            text: root.isEditing ? 'Edit Data Point(s)' : 'Add Data Point'
            anchors.centerIn: parent
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            width: (addButton.x) - (cancelButton.x + cancelButton.width) - root.margin * 2
            font.family: util.FONT_FAMILY_TITLE
            font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
        }
        PK.ToolButton {
            id: addButton
            text: root.isEditing ? 'Save' : 'Add'
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: {
                done()
            }
        }
    }

    background: Rectangle {
        color: util.QML_WINDOW_BG
        anchors.fill: parent
    }

    StackLayout {

        id: stack
        currentIndex: 0
        anchors.fill: parent

        Flickable {
            id: addPage
            clip: true
            flickableDirection: Flickable.VerticalFlick
            contentWidth: width
            contentHeight: pageInner.height

            function scrollToTop() { contentY = 0 }

            ColumnLayout { // necessary to expand anything vertically

                id: pageInner
                width: parent.width

                MouseArea {
                    width: parent.width
                    height: parent.height
                    onClicked: parent.forceActiveFocus()
                }

                GridLayout {
                    id: mainGrid
                    columns: 2
                    columnSpacing: util.QML_MARGINS / 2
                    Layout.margins: util.QML_MARGINS

                    // Who

                    PK.FormDivider {
                        text: "Who"
                        Layout.columnSpan: 2
                    }

                    PK.Text {
                        id: personLabel
                        text: 'Actor'
                    }

                    PK.FormField {
                        id: personField
                        visible: personLabel.visible
                        enabled: ! root.isEditing
                        backTabItem: notesField.lastTabItem
                        tabItem: kindBox
                        Layout.minimumHeight: personPicker.height
                        Layout.maximumHeight: personPicker.height
                        PK.PersonPicker {
                            id: personPicker
                            objectName: 'personPicker'
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            border.width: 1
                            border.color: util.QML_ITEM_BORDER_COLOR
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            Layout.minimumHeight: util.QML_FIELD_HEIGHT
                            Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        }
                    }

                    // What

                    PK.FormDivider {
                        text: "What"
                        Layout.columnSpan: 2
                    }

                    PK.Text {
                        id: kindLabel
                        text: "Event"
                        Layout.minimumWidth: 90
                    }

                    PK.ComboBox {
                        id: kindBox
                        model: ListModel {
                            ListElement { label: "Shift"; value: 'shift' }
                            //
                            ListElement { label: "Birth"; value: 'birth' }
                            ListElement { label: "Adopted"; value: 'adopted' }
                            //
                            ListElement { label: "Bonded"; value: 'bonded' }
                            ListElement { label: "Married"; value: 'married' }
                            ListElement { label: "Separated"; value: 'separated' }
                            ListElement { label: "Divorced"; value: 'divorced' }
                            ListElement { label: "Moved"; value: 'moved' }
                            //
                            ListElement { label: "Death"; value: 'death' }
                        }
                        enabled: ! isEditing
                        textRole: "label"
                        property var lastCurrentIndex: -1
                        Layout.maximumWidth: root.fieldWidth
                        Layout.minimumWidth: root.fieldWidth
                        KeyNavigation.tab: spouseField.firstTabItem
                        KeyNavigation.backtab: personField.lastTabItem
                        delegate: ItemDelegate {
                            width: ListView.view.width
                            text: label
                            palette.text: kindBox.palette.text
                            palette.highlightedText: kindBox.palette.highlightedText
                            font.weight: kindBox.currentIndex === index ? Font.DemiBold : Font.Normal
                            highlighted: kindBox.highlightedIndex === index
                            hoverEnabled: kindBox.hoverEnabled
                            Rectangle {
                                x: 0
                                y: 0
                                width: parent.width
                                height: 1
                                color: util.QML_ACTIVE_TEXT_COLOR
                                visible: index == 1 || index == 3 || index == 8
                            }
                        }
                        onCurrentIndexChanged: {
                            // print('kindBox.onCurrentIndexChanged: ' + currentIndex + ' / ' + currentValue())
                            if (currentIndex != lastCurrentIndex) {
                                lastCurrentIndex = currentIndex
                                root.kind = currentValue()
                            }
                        }
                        function setCurrentValue(value) {
                            for (var i = 0; i < model.count; i++) {
                                // print('setCurrentValue: ' + i + ' / ' + model.get(i).value + ' == ' + value)
                                if (model.get(i).value === value) {
                                    currentIndex = i;
                                    print
                                    return;
                                }
                            }
                            currentIndex = -1;
                        }
                        function clear() { currentIndex = -1 }
                        function currentValue() {
                            if(currentIndex == -1) {
                                return null
                            } else {
                                return model.get(currentIndex).value
                            }
                        }
                    }

                    PK.HelpText {
                        id: kindHelpText
                        text: util.S_EVENT_KIND_HELP_TEXT
                        visible: text != ''
                        Layout.columnSpan: 2
                    }

                    PK.Text {
                        id: spouseLabel
                        text: 'Spouse'
                        visible: [
                            util.EventKind.Bonded,
                            util.EventKind.Married,
                            util.EventKind.Separated,
                            util.EventKind.Divorced,
                            util.EventKind.Moved,
                            util.EventKind.Pregnancy,
                            util.EventKind.Birth,
                            util.EventKind.Adopted,
                        ].indexOf(root.kind) != -1
                    }

                    PK.FormField {
                        id: spouseField
                        visible: spouseLabel.visible
                        enabled: ! root.isEditing
                        backTabItem: kindBox
                        tabItem: childField.firstTabItem
                        Layout.minimumHeight: util.QML_FIELD_HEIGHT
                        Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        PK.PersonPicker {
                            id: spousePicker
                            objectName: 'spousePicker'
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            border.width: 1
                            border.color: util.QML_ITEM_BORDER_COLOR
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            Layout.minimumHeight: util.QML_FIELD_HEIGHT
                            Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        }
                    }

                    PK.Text {
                        id: childLabel
                        text: 'Child'
                        visible: [
                            util.EventKind.Birth,
                            util.EventKind.Pregnancy,
                            util.EventKind.Adopted,
                        ].indexOf(root.relationship) != -1 || root.kind == util.EventKind.Birth || root.kind == util.EventKind.Adopted
                    }

                    PK.FormField {
                        id: childField
                        visible: childLabel.visible
                        enabled: ! root.isEditing
                        backTabItem: targetsField.lastTabItem
                        tabItem: spouseField.firstTabItem
                        Layout.minimumHeight: util.QML_FIELD_HEIGHT
                        Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        PK.PersonPicker {
                            id: childPicker
                            objectName: 'childPicker'
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            border.width: 1
                            border.color: util.QML_ITEM_BORDER_COLOR
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            Layout.minimumHeight: util.QML_FIELD_HEIGHT
                            Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        }
                    }

                    PK.HelpText {
                        text: 'The person that was born or adopted.'
                        visible: childField.visible
                        Layout.columnSpan: 2
                    }

                    PK.Text {
                        id: descriptionLabel
                        text: "Summary"
                        visible: root.kind == util.EventKind.Shift
                    }

                    PK.FormField {
                        id: descriptionField
                        visible: root.kind == util.EventKind.Shift
                        tabItem: symptomField.firstTabItem
                        backTabItem: childField.lastTabItem
                        Layout.minimumHeight: util.QML_FIELD_HEIGHT
                        Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        PK.TextField {
                            id: descriptionEdit
                            enabled: root.events.length < 2
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            property Item firstTabItem: this
                            property Item lastTabItem: this
                            property bool isDirty: text != '' 
                            onEditingFinished: {
                                if(! text || text.length == 0) {
                                    root.description = ''
                                } else {
                                    root.description = text
                                }
                            }
                        }
                    }

                    PK.HelpText {
                        text: util.S_DESCRIPTION_HELP_TEXT
                        visible: descriptionField.visible
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    // Symptom

                    PK.Text {
                        id: symptomLabel
                        text: "Δ Symptom"
                        visible: root.kind == util.EventKind.Shift
                    }

                    PK.VariableField {
                        id: symptomField
                        objectName: "symptomField"
                        visible: root.kind == util.EventKind.Shift
                        Layout.fillWidth: true
                        backTabItem: spouseField.lastTabItem
                        tabItem: anxietyField.firstTabItem
                    }

                    PK.HelpText {
                        text: util.S_SYMPTOM_HELP_TEXT
                        visible: root.kind == util.EventKind.Shift
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    // Anxiety

                    PK.Text {
                        id: anxietyLabel
                        text: "Δ Anxiety"
                        visible: root.kind == util.EventKind.Shift
                    }

                    PK.VariableField {
                        id: anxietyField
                        objectName: "anxietyField"
                        visible: root.kind == util.EventKind.Shift
                        Layout.fillWidth: true
                        backTabItem: symptomField.lastTabItem
                        tabItem: relationshipField
                    }

                    PK.HelpText {
                        text: util.S_ANXIETY_HELP_TEXT
                        visible: root.kind == util.EventKind.Shift
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    // Relationship

                    PK.Text {
                        id: relationshipLabel
                        text: "Δ Relationship"
                        visible: root.kind == util.EventKind.Shift
                    }

                    PK.VariableField {
                        id: relationshipField
                        objectName: "relationshipField"
                        visible: relationshipLabel.visible
                        tabItem: targetsField.firstTabItem
                        backTabItem: anxietyField.lastTabItem
                        model: [
                            { 'name': "Conflict", 'value': 'conflict' },
                            { 'name': "Distance", 'value': 'distance' },
                            { 'name': "Overfunctioning", 'value': 'overfunctioning' },
                            { 'name': "Underfunctioning", 'value': 'underfunctioning' },
                            { 'name': "Projection", 'value': 'projection' },
                            { 'name': "Cutoff", 'value': 'cutoff' },
                            { 'name': "Triangle to inside", 'value': 'inside' },
                            { 'name': "Triangle to outside", 'value': 'outside' },
                            { 'name': "Toward", 'value': 'toward' },
                            { 'name': "Away", 'value': 'away' },
                            { 'name': "Defined Self", 'value': 'defined-self' },
                        ]
                    }

                    PK.HelpText {
                        visible: relationshipLabel.visible
                        text: util.S_RELATIONSHIP_HELP_TEXT
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    Rectangle {
                        height: 1
                        color: 'transparent'
                        visible: inspectEmotionButton.visible
                        Layout.minimumWidth: 75
                    }

                    PK.Button {
                        id: inspectEmotionButton
                        text: "→ Inspect Symbol(s)"
                        visible: relationshipField.value !== undefined && root.events.length == 1
                        onClicked: root.inspectEmotions(root.events[0])
                    }

                    // Target(s)

                    Rectangle {
                        height: 1
                        Layout.fillWidth: true
                        color: 'transparent'
                        visible: targetsLabel.visible
                    }

                    PK.Text {
                        id: targetsLabel
                        text: {
                            if(root.relationship == util.RelationshipKind.Conflict) {
                                "Other(s)"
                            } else if(root.relationship == util.RelationshipKind.Distance) {
                                "Other(s)"
                            } else if(root.relationship == util.RelationshipKind.Overfunctioning) {
                                "Underfunctioner(s)"
                            } else if(root.relationship == util.RelationshipKind.Underfunctioning) {
                                "Overfunctioner(s)"
                            } else if(root.relationship == util.RelationshipKind.Projection) {
                                "Focused"
                            } else if(root.relationship == util.RelationshipKind.Inside) {
                                "Inside(s)"
                            } else if(root.relationship == util.RelationshipKind.Outside) {
                                "Outside(s)"
                            } else if(root.relationship == util.RelationshipKind.Toward) {
                                "To"
                            } else if(root.relationship == util.RelationshipKind.Away) {
                                "From"
                            } else if (root.relationship == util.RelationshipKind.DefinedSelf) {
                                "Other(s)"
                            } else {
                                "Other(s)"
                            }
                        }
                        visible: root.kind == util.EventKind.Shift && root.relationship != null
                    }

                    Rectangle {
                        height: 1
                        Layout.fillWidth: true
                        color: 'transparent'
                        visible: targetsLabel.visible
                    }

                    PK.FormField {
                        id: targetsField
                        visible: targetsLabel.visible
                        enabled: ! root.isEditing
                        backTabItem: relationshipField
                        tabItem: trianglesField.firstTabItem
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        Layout.minimumHeight: targetsPicker.height
                        Layout.maximumHeight: targetsPicker.height
                        PK.PeoplePicker {
                            id: targetsPicker
                            objectName: 'targetsPicker'
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        }
                    }

                    Rectangle {
                        height: 1
                        Layout.fillWidth: true
                        color: 'transparent'
                        visible: trianglesLabel.visible
                    }

                    PK.Text {
                        id: trianglesLabel
                        text: {
                            if(root.relationship == util.RelationshipKind.Inside) {
                                "Outside(s)"
                            } else if(root.relationship == util.RelationshipKind.Outside) {
                                "Inside(s)"
                            } else {
                                ""
                            }
                        }
                        visible: root.relationship == util.RelationshipKind.Inside || root.relationship == util.RelationshipKind.Outside
                    }

                    Rectangle {
                        height: 1
                        Layout.fillWidth: true
                        color: 'transparent'
                        visible: trianglesLabel.visible
                    }

                    PK.FormField {
                        id: trianglesField
                        visible: trianglesLabel.visible
                        enabled: ! root.isEditing
                        backTabItem: targetsField
                        tabItem: functioningField.firstTabItem
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        Layout.minimumHeight: trianglesPicker.height
                        Layout.maximumHeight: trianglesPicker.height
                        PK.PeoplePicker {
                            id: trianglesPicker
                            objectName: 'trianglesPicker'
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        }
                    }

                    Rectangle {
                        visible: root.relationship
                        width: 1
                        height: util.HELP_FONT_SIZE
                        color: 'transparent'
                        Layout.columnSpan: 2
                    }

                    // Functioning

                    PK.Text {
                        id: functioningLabel
                        text: "Δ Functioning"
                        visible: root.kind == util.EventKind.Shift
                    }

                    PK.VariableField {
                        id: functioningField
                        objectName: "functioningField"
                        visible: root.kind == util.EventKind.Shift
                        Layout.fillWidth: true
                        backTabItem: targetsField.lastTabItem
                        tabItem: startDateButtons.firstTabItem
                    }

                    PK.HelpText {
                        text: util.S_FUNCTIONING_HELP_TEXT
                        visible: root.kind == util.EventKind.Shift
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    // When

                    PK.FormDivider {
                        text: "When"
                        Layout.columnSpan: 2
                    }

                    PK.Text {
                        id: startDateTimeLabel
                        text: {
                            if(root.isDateRange) {
                                return "Began"
                            } else {
                                return "Date"
                            }
                        }
                    }

                    PK.DatePickerButtons {
                        id: startDateButtons
                        datePicker: startDatePicker
                        timePicker: startTimePicker
                        // dateTime: root.startDateTime
                        backTabItem: descriptionField.backTabItem
                        tabItem: endDateButtons.firstTabItem
                        Layout.preferredHeight: implicitHeight - 10
                        Layout.fillWidth: true
                        onDateTimeChanged: {
                            root.startDateTime = dateTime
                            if(!Global.isValidDateTime(dateTime)) {
                                root.endDateTime = null
                                root.isDateRange = false
                            }
                        }
                        onUnsureChanged: root.startDateUnsure = unsure
                        Connections {
                            target: root
                            function onStartDateTimeChanged() { if (startDateButtons.dateTime != root.startDateTime) startDateButtons.dateTime = root.startDateTime }
                            function onStartDateUnsureChanged() {  if (startDateButtons.unsure != root.startDateUnsure) startDateButtons.unsure = root.startDateUnsure }
                        }
                    }

                    PK.DatePicker {
                        id: startDatePicker
                        // dateTime: root.startDateTime                            
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: root.startDateTime = dateTime
                        Connections {
                            target: root
                            function onStartDateTimeChanged() { if(startDatePicker.dateTime != root.startDateTime) startDatePicker.dateTime = root.startDateTime }
                        }                                
                    }

                    PK.TimePicker {
                        id: startTimePicker
                        // dateTime: root.startDateTime                            
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: root.startDateTime = dateTime
                        Connections {
                            target: root
                            function onStartDateTimeChanged() { if(startTimePicker.dateTime != root.startDateTime) startTimePicker.dateTime = root.startDateTime }
                        }                               
                    }

                    PK.Text {
                        id: endDateTimeLabel
                        text: "Ended"
                        visible: root.isDateRange
                    }

                    PK.DatePickerButtons {
                        id: endDateButtons
                        datePicker: endDatePicker
                        timePicker: endTimePicker
                        // dateTime: root.endDateTime
                        visible: root.isDateRange
                        backTabItem: startDateButtons.lastTabItem
                        tabItem: isDateRangeBox
                        Layout.preferredHeight: implicitHeight - 10
                        onDateTimeChanged: root.endDateTime = dateTime
                        onUnsureChanged: root.endDateUnsure = unsure
                        Connections {
                            target: root
                            function onEndDateTimeChanged() { if(endDateButtons.dateTime != root.endDateTime) endDateButtons.dateTime = root.endDateTime }
                            function onEndDateUnsureChanged() { if(startDateButtons.unsure != root.endDateUnsure) startDateButtons.unsure = root.endDateUnsure }
                        }                              
                    }

                    PK.DatePicker {
                        id: endDatePicker
                        // dateTime: root.endDateTime
                        visible: root.isDateRange
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: root.endDateTime = dateTime
                        Connections {
                            target: root
                            function onEndDateTimeChanged() { if(endDatePicker.dateTime != root.endDateTime) endDatePicker.dateTime = root.endDateTime }
                        }                            
                    }

                    PK.TimePicker {
                        id: endTimePicker
                        // dateTime: root.endDateTime
                        visible: root.isDateRange
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: root.endDateTime = dateTime
                        Connections {
                            target: root
                            function onEndDateTimeChanged() { if(endTimePicker.dateTime != root.endDateTime) endTimePicker.dateTime = root.endDateTime }
                        }                            
                    }

                    PK.Text {
                        id: isDateRangeLabel
                        text: " "
                        visible: root.kind != null
                    }

                    PK.CheckBox {
                        id: isDateRangeBox
                        text: "Is Date Range"
                        visible: isDateRangeLabel.visible
                        property var dirty: false
                        KeyNavigation.backtab: endDateButtons.lastTabItem
                        KeyNavigation.tab: locationField
                        Layout.fillWidth: true
                        Layout.columnSpan: 1
                        onCheckedChanged: {
                            if(root.isDateRange != checked) {
                                root.isDateRange = checked
                                dirty = true
                            }
                        }
                        Connections {
                            target: root
                            function onIsDateRangeChanged() { isDateRangeBox.checked = root.isDateRange }
                        }
                    }

                    PK.FormDivider {
                        text: "Where"
                        Layout.columnSpan: 2
                    }

                    PK.Text {
                        id: locationLabel
                        text: root.kind == util.EventKind.Moved ? "Destination" : "Location"
                    }

                    PK.FormField {
                        id: locationField
                        Layout.minimumHeight: util.QML_FIELD_HEIGHT
                        Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        tabItem: kindBox
                        backTabItem: isDateRangeBox
                        PK.TextField {
                            id: locationEdit
                            property bool isDirty: text != ''
                            property Item firstTabItem: this
                            property Item lastTabItem: this
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            KeyNavigation.tab: anxietyField
                            KeyNavigation.backtab: endDateButtons.lastTabItem
                            Keys.onTabPressed: {
                                Global.focusNextItemInFocusChain(KeyNavigation.tab, true)
                                event.accepted = true
                            }
                            Keys.onBacktabPressed: {
                                Global.focusNextItemInFocusChain(KeyNavigation.backtab, false)
                                event.accepted = true
                            }
                            function clear() { text = '' }
                        }
                    }

                    PK.FormDivider {
                        text: "How"
                        Layout.columnSpan: 2
                    }

                    PK.Text {
                        id: notesLabel
                        text: "Details"
                    }

                    PK.FormField {
                        id: notesField
                        height: notesFrame.height
                        tabItem: colorBox
                        backTabItem: locationField.lastTabItem
                        Layout.minimumHeight: notesFrame.height
                        Layout.maximumHeight: notesFrame.height
                        Layout.fillWidth: true
                        Rectangle { // for border
                            id: notesFrame
                            property bool isDirty: notesEdit.text != ''
                            color: 'transparent'
                            Layout.minimumHeight: 150
                            Layout.maximumHeight: 150
                            border {
                                width: 1
                                color: util.QML_ITEM_BORDER_COLOR
                            }
                            property Item firstTabItem: notesEdit
                            property Item lastTabItem: notesEdit
                            ScrollView {
                                id: notesScrollView
                                width: notesFrame.width - 4
                                height: notesFrame.height - 4
                                contentWidth: notesEdit.width
                                anchors.fill: parent
                                clip: true

                                PK.TextEdit {
                                    id: notesEdit
                                    wrapMode: TextEdit.Wrap
                                    height: 400
                                    width: notesFrame.width - 2
                                    topPadding: margin
                                    leftPadding: margin
                                    rightPadding: margin
                                    KeyNavigation.tab: tagsField.firstTabItem
                                    KeyNavigation.backtab: locationField.lastTabItem
                                    onWidthChanged: notesScrollView.contentWidth = width
                                }
                            }
                            function clear() { notesEdit.text = '' }
                        }
                    }

                    PK.HelpText {
                        text: util.S_NOTES_HELP_TEXT
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    // Meta

                    PK.FormDivider {
                        text: "Meta"
                        Layout.columnSpan: 2
                    }

                    PK.Text { text: "Color" }

                    PK.ColorPicker {
                        id: colorBox
                        KeyNavigation.tab: tagsField.firstTabItem
                        KeyNavigation.backtab: notesField.lastTabItem
                        onCurrentIndexChanged: root.color = model[currentIndex]
                    }
                    
                    PK.Text {
                        id: tagsLabel
                        text: "Tags"
                        visible: sceneModel.isInEditorMode
                    }

                    PK.FormField {
                        id: tagsField
                        Layout.maximumWidth: root.fieldWidth
                        Layout.minimumWidth: root.fieldWidth
                        Layout.maximumHeight: util.QML_ITEM_HEIGHT * 15
                        Layout.minimumHeight: util.QML_LIST_VIEW_MINIMUM_HEIGHT
                        tabItem: notesField.firstTabItem
                        backTabItem: tagsField.firstTabItem
                        visible: sceneModel.isInEditorMode

                        PK.ActiveListEdit {
                            id: tagsEditItem
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            model: TagsModel {
                                id: tagsModel
                                scene: sceneModel ? sceneModel.scene : undefined
                                onDataChanged: {
                                    tagsEditItem.isDirty = true
                                }
                                onModelReset: {
                                    tagsEditItem.isDirty = true
                                }
                            }
                            property var isDirty: false
                            property var lastTabItem: this
                            property var firstTabItem: this
                            function clear() {
                                model.resetToSceneTags()
                                isDirty = false
                            }
                        }
                    }

                    PK.HelpText {
                        text: util.S_TAGS_HELP_TEXT
                        wrapMode: Text.Wrap
                        Layout.columnSpan: 2
                        visible: sceneModel.isInEditorMode
                    }

                }
            }
        }
    }
}
