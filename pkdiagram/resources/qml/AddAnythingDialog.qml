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

    property int margin: util.QML_MARGINS
    property var focusResetter: addPage
    property bool canInspect: false
    property var selectedPeopleModel: ListModel {}

    property var tagsEdit: tagsEditItem
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

    property var kind: null
    property var description: descriptionEdit.text
    property var isDateRange: isDateRangeBox.checked
    property var startDateButtons: startDateButtons
    property var startDateTime: startDatePicker.dateTime
    property var startDateUnsure: startDatePicker.unsure
    property var endDateButtons: endDateButtons
    property var endDateTime: endDatePicker.dateTime
    property var endDateUnsure: endDatePicker.unsure
    property var location: locationEdit.text
    property var nodal: nodalBox.checked
    property var anxiety: anxietyBox.value
    property var functioning: functioningBox.value
    property var symptom: symptomBox.value
    property var notes: notesEdit.text
    property var eventModel: EventPropertiesModel {}

    property var personPicker: personPicker
    property var peoplePicker: peoplePicker
    property var personAPicker: personAPicker
    property var personBPicker: personBPicker
    property var moversPicker: moversPicker
    property var receiversPicker: receiversPicker

    property var personLabel: personLabel
    property var peopleLabel: peopleLabel
    property var personALabel: personALabel
    property var personBLabel: personBLabel
    property var moversLabel: moversLabel
    property var receiversLabel: receiversLabel
    property var kindLabel: kindLabel
    property var descriptionLabel: descriptionLabel
    property var startDateTimeLabel: startDateTimeLabel
    property var endDateTimeLabel: endDateTimeLabel
    property var isDateRangeLabel: isDateRangeLabel

    property var kindBox: kindBox
    property var descriptionEdit: descriptionEdit
    property var startDatePicker: startDatePicker
    property var startTimePicker: startTimePicker
    property var isDateRangeBox: isDateRangeBox
    property var endDatePicker: endDatePicker
    property var endTimePicker: endTimePicker
    property var locationEdit: locationEdit
    property var anxietyBox: anxietyBox
    property var functioningBox: functioningBox
    property var symptomBox: symptomBox
    property var nodalBox: nodalBox
    property var notesEdit: notesEdit

    function onStartDateTimeChanged() {
        startDatePicker.dateTime = startDateTime
        print('onStartDateTimeChanged: ' + startDateTime)
    }

    readonly property var fieldWidth: 275

    property var dirty: false

    property var lastKind: null
    onKindChanged: {
        var newKind = kindBox.currentValue()
        var personEntry = personPicker.isSubmitted ? root.personEntry() : null
        var personAEntry = personAPicker.isSubmitted ? root.personAEntry() : null
        var personBEntry = personBPicker.isSubmitted ? root.personBEntry() : null
        var peopleEntries = root.peopleEntries()
        var moverEntries = root.moverEntries()
        var receiverEntries = root.receiverEntries()

        personPicker.clear()
        peoplePicker.clear()
        personAPicker.clear()
        personBPicker.clear()
        moversPicker.clear()
        receiversPicker.clear()
        selectedPeopleModel.clear()

        if(newKind == null || lastKind == null) {
            lastKind = newKind
            return
        }

        if(util.isMonadicEventKind(lastKind)) {
            if(util.isMonadicEventKind(newKind)) {
                if(personEntry) personPicker.setExistingPerson(personEntry.person)
            } else if(newKind == util.EventKind.CustomIndividual) {
                if(personEntry) peoplePicker.addExistingPerson(personEntry.person)
                if(personAEntry) peoplePicker.addExistingPerson(personAEntry.person)
                if(personBEntry) peoplePicker.addExistingPerson(personBEntry.person)
            } else if (util.isPairBondEventKind(newKind)) {
                if(personEntry) personAPicker.setExistingPerson(personEntry.person)
                if(personAEntry) personBPicker.setExistingPerson(personAEntry.person)
            } else if (util.isDyadicEventKind(newKind)) {
                if(personEntry) moversPicker.addExistingPerson(personEntry.person)
                if(personAEntry) receiversPicker.addExistingPerson(personAEntry.person)
                if(personBEntry) receiversPicker.addExistingPerson(personBEntry.person)
            }
        } else if(lastKind == util.EventKind.CustomIndividual) {
            if(util.isMonadicEventKind(newKind)) {
                if(peopleEntries.length >= 1) personPicker.setExistingPerson(peopleEntries[0].person)
                if(peopleEntries.length >= 2) personAPicker.setExistingPerson(peopleEntries[1].person)
                if(peopleEntries.length >= 3) personBPicker.setExistingPerson(peopleEntries[2].person)
            } else if(util.isPairBondEventKind(newKind)) {
                if(peopleEntries.length >= 1) personAPicker.setExistingPerson(peopleEntries[0].person)
                if(peopleEntries.length >= 2) personBPicker.setExistingPerson(peopleEntries[1].person)
            } else if(util.isDyadicEventKind(newKind)) {
                if(peopleEntries.length >= 1) moversPicker.addExistingPerson(peopleEntries[0].person)
                if(peopleEntries.length >= 2) {
                    for(var i=1; i < peopleEntries.length; i++) {
                        receiversPicker.addExistingPerson(peopleEntries[i].person)
                    }
                }
            }
        } else if(util.isPairBondEventKind(lastKind)) {
            if(util.isPairBondEventKind(newKind)) {
                if(personAEntry) personAPicker.setExistingPerson(personAEntry.person)
                if(personBEntry) personBPicker.setExistingPerson(personBEntry.person)
            } else if(util.isMonadicEventKind(newKind)) {
                var isBirth = (newKind == util.EventKind.Birth)
                if(personAEntry) personPicker.setExistingPerson(personAEntry.person)
                if(isBirth && personAEntry) personAPicker.setExistingPerson(personBEntry.person)
            } else if(newKind == util.EventKind.CustomIndividual) {
                if(personAEntry) peoplePicker.addExistingPerson(personAEntry.person)
                if(personBEntry) peoplePicker.addExistingPerson(personBEntry.person)
            } else if (util.isDyadicEventKind(newKind)) {
                if(personAEntry) moversPicker.addExistingPerson(personAEntry.person)
                if(personBEntry) receiversPicker.addExistingPerson(personBEntry.person)
            }
        } else if(util.isDyadicEventKind(lastKind)) {
            if(util.isDyadicEventKind(newKind)) {
                for(var i=0; i < moverEntries.length; i++) {
                    moversPicker.addExistingPerson(moverEntries[i].person)
                }
                for(var i=0; i < receiverEntries.length; i++) {
                    receiversPicker.addExistingPerson(receiverEntries[i].person)
                }
            } else if(util.isMonadicEventKind(newKind)) {
                var isBirth = (newKind == util.EventKind.Birth)
                if(moverEntries.length >= 1) personPicker.setExistingPerson(moverEntries[0].person)
                if(isBirth && moverEntries.length >= 2) personAPicker.setExistingPerson(moverEntries[1].person)
                if(isBirth && moverEntries.length >= 3) personBPicker.setExistingPerson(moverEntries[2].person)
            } else if(newKind == util.EventKind.CustomIndividual) {
                print('onKindChanged[2]: ' + moverEntries.length + ', ' + receiverEntries.length)
                for(var i=0; i < moverEntries.length; i++) {
                    peoplePicker.addExistingPerson(moverEntries[i].person)
                }
            } else if (util.isPairBondEventKind(newKind)) {
                if(moverEntries.length >= 1) personAPicker.setExistingPerson(moverEntries[0].person)
                if(moverEntries.length >= 2) personBPicker.setExistingPerson(moverEntries[1].person)
            }
        }

        lastKind = kindBox.currentValue()
    }

    function clear() {
        kindBox.currentIndex = -1
        personPicker.clear()
        peoplePicker.clear()
        personAPicker.clear()
        personBPicker.clear()
        moversPicker.clear()
        receiversPicker.clear()
        startDatePicker.clear()
        endDatePicker.clear()
        isDateRangeBox.checked = false
        descriptionEdit.clear()
        locationEdit.clear()
        anxietyBox.clear()
        functioningBox.clear()
        symptomBox.clear()
        nodalBox.clear()
        notesFrame.clear()
        addPage.scrollToTop()
        tagsEditItem.clear()
        eventModel.tags = []

        kindBox.forceActiveFocus()
        root.dirty = false;
    }

    function currentTab() { return 0 }
    function setCurrentTab(tab) {}

    function initWithPairBond(pairBondId) {
        var pairBond = sceneModel.item(pairBondId)
        kindBox.setCurrentValue(util.EventKind.CustomPairBond)
        var personA = pairBond.personA()
        var personB = pairBond.personB()
        // print('initWithPairBond: ' + personA + ', ' + personB)
        personAPicker.setExistingPerson(personA)
        personBPicker.setExistingPerson(personB)
        tagsEdit.isDirty = false
    }
    function initWithMultiplePeople(peopleIds) {
        var people = [];
        for(var i=0; i < peopleIds.length; i++) {
            people.push(sceneModel.item(peopleIds[i]))
        }
        kindBox.setCurrentValue(util.EventKind.CustomIndividual)
        // print('initWithMultiplePeople: ' + people.length)
        peoplePicker.setExistingPeople(people)
        tagsEdit.isDirty = false
    }
    function initWithNoSelection() {
        kindBox.currentIndex = -1
        print('initWithNoSelection')
        tagsEdit.isDirty = false
    }

    function setVariable(attr, x) {
        if(attr == 'anxiety') {
            anxietyBox.setValue(x)
        } else if(attr == 'functioning') {
            functioningBox.setValue(x)
        } if(attr == 'symptom') {
            symptomBox.setValue(x)
        }
    }

    // attr statuses

    function personEntry() {
        return personPicker.personEntry()
    }

    function personAEntry() {
        return personAPicker.personEntry()
    }

    function personBEntry() {
        return personBPicker.personEntry()
    }

    function peopleEntries() {
        return peoplePicker.peopleEntries()
    }

    function moverEntries() {
        return moversPicker.peopleEntries()
    }

    function receiverEntries() {
        return receiversPicker.peopleEntries()
    }

    function setPeopleHelpText(text) {
        peopleHelpText.text = text
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
            onClicked: root.clear()
        }
        PK.Label {
            text: 'Add Data Point'
            anchors.centerIn: parent
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            width: (addButton.x) - (cancelButton.x + cancelButton.width) - root.margin * 2
            font.family: util.FONT_FAMILY_TITLE
            font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
        }
        PK.ToolButton {
            id: addButton
            text: 'Add'
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

                    PK.Text {
                        id: kindLabel
                        text: "Event"
                    }

                    PK.ComboBox {
                        id: kindBox
                        model: util.eventKindLabels()
                        property var valuesForIndex: util.eventKindValues()
                        property var lastCurrentIndex: -1
                        Layout.maximumWidth: root.fieldWidth - 28
                        Layout.minimumWidth: root.fieldWidth - 28
                        KeyNavigation.tab: personPicker.firstTabItem
                        KeyNavigation.backtab: notesEdit
                        // property var firstInSections: [5, 11]
                        delegate: ItemDelegate {
                            width: ListView.view.width
                            text: kindBox.textRole ? (Array.isArray(kindBox.model) ? modelData[kindBox.textRole] : model[kindBox.textRole]) : modelData
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
                                visible: index == 5 || index == 11
                            }
                        }
                        onCurrentIndexChanged: {
                            if (currentIndex != lastCurrentIndex) {
                                lastCurrentIndex = currentIndex
                                root.kind = currentValue()
                                descriptionEdit.text = util.eventKindEventLabelFor(currentValue())
                            }
                        }
                        function setCurrentValue(value) { currentIndex = valuesForIndex.indexOf(value)}
                        function clear() { currentIndex = -1 }
                        function currentValue() {
                            if(currentIndex == -1) {
                                return null
                            } else {
                                return valuesForIndex[currentIndex]
                            }
                        }
                    }

                    PK.HelpText {
                        id: kindHelpText
                        text: util.S_EVENT_KIND_HELP_TEXT
                        visible: text != ''
                        Layout.columnSpan: 2
                    }

                    // ////////////////////////////////////////////////

                    PK.FormDivider {
                        Layout.columnSpan: 2
                    }

                    // Person

                    PK.Text {
                        id: personLabel
                        text: 'Person'
                        visible: util.isMonadicEventKind(root.kind)
                    }

                    PK.FormField {
                        id: personField
                        visible: personLabel.visible
                        backTabItem: kindBox
                        tabItem: peopleField.firstTabItem
                        Layout.maximumWidth: root.fieldWidth
                        Layout.minimumWidth: root.fieldWidth
                        Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        Layout.minimumHeight: util.QML_FIELD_HEIGHT
                        PK.PersonPicker {
                            id: personPicker
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            border.width: 1
                            border.color: util.QML_ITEM_BORDER_COLOR
                            Layout.maximumHeight: util.QML_FIELD_HEIGHT
                            Layout.minimumHeight: util.QML_FIELD_HEIGHT
                        }
                    }

                    // People

                    PK.Text {
                        id: peopleLabel
                        text: 'People'
                        visible: root.kind == util.EventKind.CustomIndividual
                    }

                    PK.FormField {
                        id: peopleField
                        visible: peopleLabel.visible
                        backTabItem: personField.lastTabItem
                        tabItem: personAField.firstTabItem
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        Layout.minimumHeight: peoplePicker.height
                        Layout.maximumHeight: peoplePicker.height
                        PK.PeoplePicker {
                            id: peoplePicker
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            // width: peopleField.width - peopleField.clearButton.width
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        }
                    }

                    // Person A

                    PK.Text {
                        id: personALabel
                        text: util.isChildEventKind(root.kind) ? 'Parent A' : 'Person A'
                        visible: util.isPairBondEventKind(root.kind) || util.isChildEventKind(root.kind)
                    }

                    PK.FormField {
                        id: personAField
                        visible: personALabel.visible
                        backTabItem: peopleField.lastTabItem
                        tabItem: personBField.firstTabItem
                        Layout.maximumWidth: root.fieldWidth
                        Layout.minimumWidth: root.fieldWidth
                        Layout.minimumHeight: util.QML_FIELD_HEIGHT
                        Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        PK.PersonPicker {
                            id: personAPicker
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            border.width: 1
                            border.color: util.QML_ITEM_BORDER_COLOR
                            Layout.minimumHeight: util.QML_FIELD_HEIGHT
                            Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        }
                    }

                    // Person B

                    PK.Text {
                        id: personBLabel
                        text: util.isChildEventKind(root.kind) ? 'Parent B' : 'Person B'
                        visible: personALabel.visible
                    }

                    PK.FormField {
                        id: personBField
                        visible: personALabel.visible
                        backTabItem: personAField.lastTabItem
                        tabItem: moversField.firstTabItem
                        Layout.maximumWidth: root.fieldWidth
                        Layout.minimumWidth: root.fieldWidth
                        Layout.minimumHeight: util.QML_FIELD_HEIGHT
                        Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        PK.PersonPicker {
                            id: personBPicker
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            border.width: 1
                            border.color: util.QML_ITEM_BORDER_COLOR
                            Layout.minimumHeight: util.QML_FIELD_HEIGHT
                            Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        }
                    }

                    // Mover(s)

                    PK.Text {
                        id: moversLabel
                        text: 'Mover(s)'
                        visible: util.isDyadicEventKind(root.kind)
                    }

                    PK.FormField {
                        id: moversField
                        visible: moversLabel.visible
                        backTabItem: personBField.lastTabItem
                        tabItem: receiversField.firstTabItem
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        Layout.minimumHeight: moversPicker.height
                        Layout.maximumHeight: moversPicker.height
                        PK.PeoplePicker {
                            id: moversPicker
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        }
                    }

                    // Receiver(s)

                    PK.Text {
                        id: receiversLabel
                        visible: moversLabel.visible
                        text: 'Receiver(s)'
                    }

                    PK.FormField {
                        id: receiversField
                        visible: moversLabel.visible
                        backTabItem: moversField.lastTabItem
                        tabItem: descriptionField.firstTabItem
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        Layout.minimumHeight: receiversPicker.height
                        Layout.maximumHeight: receiversPicker.height
                        PK.PeoplePicker {
                            id: receiversPicker
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        }
                    }

                    PK.HelpText {
                        id: peopleHelpText
                        text: util.S_PEOPLE_HELP_TEXT
                        visible: text != '' && kindBox.kindBox != -1
                        Layout.columnSpan: 2
                    }

                    // ////////////////////////////////////////////////

                    PK.FormDivider {
                        Layout.columnSpan: 2
                        visible: kindBox.currentIndex != -1
                    }


                    PK.Text {
                        id: descriptionLabel
                        text: "Description"
                        visible: util.isCustomEventKind(root.kind)
                    }

                    PK.FormField {
                        id: descriptionField
                        visible: descriptionLabel.visible
                        KeyNavigation.backtab: receiversPicker.lastTabItem
                        KeyNavigation.tab: startDateButtons.firstTabItem
                        tabItem: startDateButtons.firstTabItem
                        backTabItem: receiversField.lastTabItem
                        Layout.fillWidth: true
                        Layout.minimumHeight: util.QML_FIELD_HEIGHT
                        Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        PK.TextField {
                            id: descriptionEdit
                            property Item firstTabItem: this
                            property Item lastTabItem: this
                            property bool isDirty: text != ''
                            function clear() { text = '' }
                        }
                    }

                    PK.HelpText {
                        text: util.S_DESCRIPTION_HELP_TEXT
                        visible: descriptionField.visible
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    PK.FormDivider {
                        Layout.columnSpan: 2
                        visible: descriptionEdit.visible
                    }

                    PK.Text {
                        id: startDateTimeLabel
                        text: {
                            if(root.isDateRange) {
                                return "Began"
                            } else {
                                return "When"
                            }
                        }
                    }

                    PK.DatePickerButtons {
                        id: startDateButtons
                        datePicker: startDatePicker
                        timePicker: startTimePicker
                        // dateTime: root.startDateTime
                        showInspectButton: false
                        backTabItem: descriptionField.backTabItem
                        tabItem: endDateButtons.firstTabItem
                        Layout.preferredHeight: implicitHeight - 10
                        Layout.fillWidth: true
                        onDateTimeChanged: root.startDateTime = dateTime
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
                        showInspectButton: true
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
                        text: "Is Date Range"
                        visible: util.isDyadicEventKind(root.kind) || root.kind == util.EventKind.Cutoff
                    }

                    PK.CheckBox {
                        id: isDateRangeBox
                        text: "Is Date Range" 
                        visible: isDateRangeLabel.visible
                        KeyNavigation.backtab: endDateButtons.lastTabItem
                        KeyNavigation.tab: locationField
                        Layout.fillWidth: true
                        Layout.columnSpan: 1
                        onCheckedChanged: {
                            if(root.isDateRange != checked) {
                                root.isDateRange = checked
                            }
                        }
                    }

                    PK.Text {
                        id: locationLabel
                        text: kindBox.valuesForIndex[kindBox.currentIndex] == util.EventKind.Moved ? "Destination" : "Location"
                    }

                    PK.FormField {
                        id: locationField
                        Layout.maximumWidth: root.fieldWidth
                        Layout.minimumWidth: root.fieldWidth
                        Layout.minimumHeight: util.QML_FIELD_HEIGHT
                        Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        tabItem: anxietyBox
                        backTabItem: isDateRangeBox
                        PK.TextField {
                            id: locationEdit
                            property bool isDirty: text != ''
                            property Item firstTabItem: this
                            property Item lastTabItem: this
                            KeyNavigation.tab: anxietyBox
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
                        Layout.columnSpan: 2
                        visible: ! util.isRSymbolEventKind(root.kind)
                    }
                    
                    PK.Text {
                        text: "Δ Anxiety"
                        visible: ! util.isRSymbolEventKind(root.kind)
                    }

                    PK.VariableBox {
                        id: anxietyBox
                        visible: ! util.isRSymbolEventKind(root.kind)
                        Layout.fillWidth: true
                        tabItem: functioningBox.firstTabItem
                        backTabItem: locationField.lastTabItem
                    }

                    PK.HelpText {
                        text: util.S_ANXIETY_HELP_TEXT
                        visible: ! util.isRSymbolEventKind(root.kind)
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    PK.Text {
                        text: "Δ Functioning"
                        visible: ! util.isRSymbolEventKind(root.kind)
                    }

                    PK.VariableBox {
                        id: functioningBox
                        visible: ! util.isRSymbolEventKind(root.kind)
                        Layout.fillWidth: true
                        backTabItem: anxietyBox.lastTabItem
                        tabItem: symptomBox.firstTabItem
                    }

                    PK.HelpText {
                        text: util.S_FUNCTIONING_HELP_TEXT
                        visible: ! util.isRSymbolEventKind(root.kind)
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }
                    PK.Text {
                        text: "Δ Symptom"
                        visible: ! util.isRSymbolEventKind(root.kind)
                    }

                    PK.VariableBox {
                        id: symptomBox
                        visible: ! util.isRSymbolEventKind(root.kind)
                        Layout.fillWidth: true
                        backTabItem: functioningBox.lastTabItem
                        tabItem: nodalBox
                    }

                    PK.HelpText {
                        text: util.S_SYMPTOM_HELP_TEXT
                        visible: ! util.isRSymbolEventKind(root.kind)
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    PK.Text {
                        id: nodalLabel
                        text: "Nodal"
                        visible: false
                    }

                    PK.CheckBox {
                        id: nodalBox
                        visible: false
                        KeyNavigation.tab: notesEdit
                        KeyNavigation.backtab: anxietyBox.lastTabItem
                        function clear() { checked = false }
                    }

                    PK.FormDivider { Layout.columnSpan: 2 }
                    
                    PK.Text { id: tagsLabel; text: "Tags" }

                    PK.FormField {

                        Layout.maximumWidth: root.fieldWidth
                        Layout.minimumWidth: root.fieldWidth
                        Layout.maximumHeight: util.QML_ITEM_HEIGHT * 15
                        Layout.minimumHeight: util.QML_LIST_VIEW_MINIMUM_HEIGHT
                        tabItem: notesField.firstTabItem
                        backTabItem: nodalBox

                        PK.ActiveListEdit {
                            id: tagsEditItem
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            model: TagsModel {
                                id: tagsModel
                                scene: sceneModel ? sceneModel.scene : undefined
                                items: eventModel.items
                                onDataChanged: {
                                    print('TagsModel::onDataChanged')
                                    tagsEditItem.isDirty = true
                                }
                                onModelReset: {
                                    print('TagsModel::onModelReset')
                                    tagsEditItem.isDirty = true
                                }
                            }
                            property var isDirty: false
                            property var lastTabItem: this
                            property var firstTabItem: this
                            function clear() {
                                model.resetToSceneTags()
                                print('TagsEditItem::clear')
                                isDirty = false
                            }
                        }

                    }

                    PK.HelpText {
                        text: util.S_TAGS_HELP_TEXT
                        wrapMode: Text.Wrap
                        Layout.columnSpan: 2
                    }

                    PK.FormDivider {
                        Layout.columnSpan: 2
                    }

                    PK.Text {
                        id: notesLabel
                        text: "Details"
                    }

                    PK.FormField {
                        id: notesField
                        height: notesFrame.height
                        tabItem: kindBox
                        backTabItem: symptomBox.lastTabItem
                        Layout.minimumHeight: notesFrame.height
                        Layout.maximumHeight: notesFrame.height
                        Layout.fillWidth: true
                        Rectangle { // for border
                            id: notesFrame
                            property bool isDirty: notesEdit.text != ''
                            color: 'transparent'
                            Layout.minimumHeight: 250
                            Layout.maximumHeight: 250
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
                                    KeyNavigation.tab: kindBox
                                    KeyNavigation.backtab: symptomBox.lastTabItem
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
                }
            }
        }
    }
}
