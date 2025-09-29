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
    property var tagsLabel: tagsLabel
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

    property var lifeChange: null
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
    property var parentALabel: parentALabel
    property var parentPersonBLabel: parentPersonBLabel
    property var moversLabel: moversLabel
    property var receiversLabel: receiversLabel
    property var lifeChangeLabel: lifeChangeLabel
    property var descriptionLabel: descriptionLabel
    property var startDateTimeLabel: startDateTimeLabel
    property var endDateTimeLabel: endDateTimeLabel
    property var isDateRangeLabel: isDateRangeLabel

    property var lifeChangeBox: lifeChangeBox
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
    function __onLifeChangeChanged: {
        var newKind = lifeChangeBox.currentValue()
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

        if(util.isMonadicLifeChange(lastKind)) {
            if(util.isMonadicLifeChange(newKind)) {
                if(personEntry) personPicker.setExistingPerson(personEntry.person)
            } else if(newKind == util.LifeChange.CustomIndividual) {
                if(personEntry) peoplePicker.addExistingPerson(personEntry.person)
                if(personAEntry) peoplePicker.addExistingPerson(personAEntry.person)
                if(personBEntry) peoplePicker.addExistingPerson(personBEntry.person)
            } else if (util.isPairBondLifeChange(newKind)) {
                if(personEntry) personAPicker.setExistingPerson(personEntry.person)
                if(personAEntry) personBPicker.setExistingPerson(personAEntry.person)
            } else if (util.isDyadicLifeChange(newKind)) {
                if(personEntry) moversPicker.addExistingPerson(personEntry.person)
                if(personAEntry) receiversPicker.addExistingPerson(personAEntry.person)
                if(personBEntry) receiversPicker.addExistingPerson(personBEntry.person)
            }
        } else if(lastKind == util.LifeChange.CustomIndividual) {
            if(util.isMonadicLifeChange(newKind)) {
                if(peopleEntries.length >= 1) personPicker.setExistingPerson(peopleEntries[0].person)
                if(peopleEntries.length >= 2) personAPicker.setExistingPerson(peopleEntries[1].person)
                if(peopleEntries.length >= 3) personBPicker.setExistingPerson(peopleEntries[2].person)
            } else if(util.isPairBondLifeChange(newKind)) {
                if(peopleEntries.length >= 1) personAPicker.setExistingPerson(peopleEntries[0].person)
                if(peopleEntries.length >= 2) personBPicker.setExistingPerson(peopleEntries[1].person)
            } else if(util.isDyadicLifeChange(newKind)) {
                if(peopleEntries.length >= 1) moversPicker.addExistingPerson(peopleEntries[0].person)
                if(peopleEntries.length >= 2) {
                    for(var i=1; i < peopleEntries.length; i++) {
                        receiversPicker.addExistingPerson(peopleEntries[i].person)
                    }
                }
            }
        } else if(util.isPairBondLifeChange(lastKind)) {
            if(util.isPairBondLifeChange(newKind)) {
                if(personAEntry) personAPicker.setExistingPerson(personAEntry.person)
                if(personBEntry) personBPicker.setExistingPerson(personBEntry.person)
            } else if(util.isMonadicLifeChange(newKind)) {
                var isBirth = (newKind == util.LifeChange.Birth)
                if(personAEntry) personPicker.setExistingPerson(personAEntry.person)
                if(isBirth && personAEntry) personAPicker.setExistingPerson(personBEntry.person)
            } else if(newKind == util.LifeChange.CustomIndividual) {
                if(personAEntry) peoplePicker.addExistingPerson(personAEntry.person)
                if(personBEntry) peoplePicker.addExistingPerson(personBEntry.person)
            } else if (util.isDyadicLifeChange(newKind)) {
                if(personAEntry) moversPicker.addExistingPerson(personAEntry.person)
                if(personBEntry) receiversPicker.addExistingPerson(personBEntry.person)
            }
        } else if(util.isDyadicLifeChange(lastKind)) {
            if(util.isDyadicLifeChange(newKind)) {
                for(var i=0; i < moverEntries.length; i++) {
                    moversPicker.addExistingPerson(moverEntries[i].person)
                }
                for(var i=0; i < receiverEntries.length; i++) {
                    receiversPicker.addExistingPerson(receiverEntries[i].person)
                }
            } else if(util.isMonadicLifeChange(newKind)) {
                var isBirth = (newKind == util.LifeChange.Birth)
                if(moverEntries.length >= 1) personPicker.setExistingPerson(moverEntries[0].person)
                if(isBirth && moverEntries.length >= 2) personAPicker.setExistingPerson(moverEntries[1].person)
                if(isBirth && moverEntries.length >= 3) personBPicker.setExistingPerson(moverEntries[2].person)
            } else if(newKind == util.LifeChange.CustomIndividual) {
                print('onKindChanged[2]: ' + moverEntries.length + ', ' + receiverEntries.length)
                for(var i=0; i < moverEntries.length; i++) {
                    peoplePicker.addExistingPerson(moverEntries[i].person)
                }
            } else if (util.isPairBondLifeChange(newKind)) {
                if(moverEntries.length >= 1) personAPicker.setExistingPerson(moverEntries[0].person)
                if(moverEntries.length >= 2) personBPicker.setExistingPerson(moverEntries[1].person)
            }
        }

        lastKind = kindBox.currentValue()
    }

    function onRelationshipKindChanged() {
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
        kindBox.setCurrentValue(util.LifeChange.CustomPairBond)
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
        kindBox.setCurrentValue(util.LifeChange.CustomIndividual)
        // print('initWithMultiplePeople: ' + people.length)
        peoplePicker.setExistingPeople(people)
        tagsEdit.isDirty = false
    }
    function initWithNoSelection() {
        kindBox.currentIndex = -1
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

                    // People

                    PK.Text {
                        id: peopleLabel
                        text: 'People'
                    }

                    PK.FormField {
                        id: peopleField
                        visible: peopleLabel.visible
                        backTabItem: personField.lastTabItem
                        tabItem: parentAField.firstTabItem
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

                    // ////////////////////////////////////////////////

                    PK.FormDivider {
                        Layout.columnSpan: 2
                        visible: kindBox.currentIndex != -1
                    }


                    PK.Text {
                        id: descriptionLabel
                        text: "Description"
                    }

                    PK.FormField {
                        id: descriptionField
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
                        text: " "
                        visible: util.isDyadicLifeChange(root.kind) || root.kind == util.LifeChange.Cutoff
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
                        text: kindBox.valuesForIndex[kindBox.currentIndex] == util.LifeChange.Moved ? "Destination" : "Location"
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
                    }

                    PK.Text {
                        id: lifeChangeLabel
                        text: "Life Change"
                    }

                    PK.ComboBox {
                        id: lifeChangeBox
                        model: ListModel {
                            ListElement { label: "Birth"; value: 'birth' }
                            ListElement { label: "Adopted"; value: 'adopted' }
                            ListElement { label: "Death"; value: 'death' }
                            ListElement { label: "Bonded"; value: 'bonded' }
                            ListElement { label: "Married"; value: 'married' }
                            ListElement { label: "Separated"; value: 'separated' }
                            ListElement { label: "Divorced"; value: 'divorced' }
                            ListElement { label: "Moved"; value: 'moved' }
                        }
                        property var lastCurrentIndex: -1
                        Layout.maximumWidth: root.fieldWidth - 28
                        Layout.minimumWidth: root.fieldWidth - 28
                        KeyNavigation.tab: personPicker.firstTabItem
                        KeyNavigation.backtab: notesEdit
                        // property var firstInSections: [5, 11]
                        // delegate: ItemDelegate {
                        //     width: ListView.view.width
                        //     text: lifeChangeBox.textRole ? (Array.isArray(lifeChangeBox.model) ? modelData[lifeChangeBox.textRole] : model[lifeChangeBox.textRole]) : modelData
                        //     palette.text: lifeChangeBox.palette.text
                        //     palette.highlightedText: lifeChangeBox.palette.highlightedText
                        //     font.weight: lifeChangeBox.currentIndex === index ? Font.DemiBold : Font.Normal
                        //     highlighted: lifeChangeBox.highlightedIndex === index
                        //     hoverEnabled: lifeChangeBox.hoverEnabled
                        //     Rectangle {
                        //         x: 0
                        //         y: 0
                        //         width: parent.width
                        //         height: 1
                        //         color: util.QML_ACTIVE_TEXT_COLOR
                        //         visible: index == 5 || index == 11
                        //     }
                        // }
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

                    // Parent A

                    PK.Text {
                        id: parentALabel
                        text: 'Parent A'
                        visible: ['birth', 'adopted'].indexOf(root.lifeChange) != -1
                    }

                    PK.FormField {
                        id: parentAField
                        visible: parentALabel.visible
                        backTabItem: peopleField.lastTabItem
                        tabItem: parentBField.firstTabItem
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

                    // Parent B

                    PK.Text {
                        id: parentBLabel
                        text: 'Parent B'
                        visible: ['birth', 'adopted'].indexOf(root.lifeChange) != -1
                    }

                    PK.FormField {
                        id: parentBField
                        visible: parentBLabel.visible
                        backTabItem: parentBField.lastTabItem
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

                    // Spouse

                    PK.Text {
                        id: spouseLabel
                        text: 'Spouse'
                        visible: ['birth', 'adopted'].indexOf(root.lifeChange) != -1
                    }

                    PK.FormField {
                        id: spouseField
                        visible: spouseLabel.visible
                        backTabItem: spouseField.lastTabItem
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


                    PK.FormDivider {
                        Layout.columnSpan: 2
                    }

                    /////////////////////////////////////////////////
                    // Variables
                    /////////////////////////////////////////////////

                    // Symptom

                    PK.Text {
                        text: "Δ Symptom"
                    }

                    PK.VariableBox {
                        id: symptomBox
                        Layout.fillWidth: true
                        backTabItem: functioningBox.lastTabItem
                        tabItem: nodalBox
                    }

                    PK.HelpText {
                        text: util.S_SYMPTOM_HELP_TEXT
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    // Anxiety

                    PK.Text {
                        text: "Δ Anxiety"
                    }

                    PK.VariableBox {
                        id: anxietyBox
                        Layout.fillWidth: true
                        tabItem: functioningBox.firstTabItem
                        backTabItem: locationField.lastTabItem
                    }

                    PK.HelpText {
                        text: util.S_ANXIETY_HELP_TEXT
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    // Functioning

                    PK.Text {
                        text: "Δ Functioning"
                    }

                    PK.VariableBox {
                        id: functioningBox
                        Layout.fillWidth: true
                        backTabItem: anxietyBox.lastTabItem
                        tabItem: symptomBox.firstTabItem
                    }

                    PK.HelpText {
                        text: util.S_FUNCTIONING_HELP_TEXT
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                    }

                    // Relationship

                    PK.Text {
                        text: "Δ Relationship"
                    }

                    PK.ComboBox {
                        id: relationshipBox
                        model: ListModel {
                            ListElement { label: "Conflict"; value: util.ITEM_CONFLICT }
                            ListElement { label: "Distance"; value: util.ITEM_DISTANCE }
                            ListElement { label: "Reciprocity"; value: util.ITEM_RECIPROCITY }
                            ListElement { label: "Child-Focus"; value: util.ITEM_PROJECTION }
                            ListElement { label: "Cutoff"; value: util.ITEM_CUTOFF }
                            ListElement { label: "Triangle, to inside"; value: util.ITEM_INSIDE }
                            ListElement { label: "Triangle, to outside"; value: util.ITEM_OUTSIDE }
                            ListElement { label: "Toward"; value: util.ITEM_TOWARD }
                            ListElement { label: "Away"; value: util.ITEM_AWAY }
                        }
                        property var lastCurrentIndex: -1
                        Layout.maximumWidth: root.fieldWidth - 28
                        Layout.minimumWidth: root.fieldWidth - 28
                        KeyNavigation.tab: nodalBox
                        KeyNavigation.backtab: functioningBox.lastTabItem
                        // delegate: ItemDelegate {
                        //     width: ListView.view.width
                        //     text: kindBox.textRole ? (Array.isArray(kindBox.model) ? modelData[kindBox.textRole] : model[kindBox.textRole]) : modelData
                        //     palette.text: kindBox.palette.text
                        //     palette.highlightedText: kindBox.palette.highlightedText
                        //     font.weight: kindBox.currentIndex === index ? Font.DemiBold : Font.Normal
                        //     highlighted: kindBox.highlightedIndex === index
                        //     hoverEnabled: kindBox.hoverEnabled
                        //     Rectangle {
                        //         x: 0
                        //         y: 0
                        //         width: parent.width
                        //         height: 1
                        //         color: util.QML_ACTIVE_TEXT_COLOR
                        //         visible: index == 5 || index == 11
                        //     }
                        // }
                        onCurrentIndexChanged: {
                            if (currentIndex != lastCurrentIndex) {
                                lastCurrentIndex = currentIndex
                                root.relationship = selectedValue
                            }
                        }
                        function clear() { currentIndex = -1 }
                        function currentValue() {
                            return selectedValue
                            if(currentIndex == -1) {
                                return null
                            } else {
                                return model.get(currentIndex).value
                            }
                        }
                    }                    

                    // Inside(s)

                    PK.Text {
                        id: insidesLabel
                        text: 'Inside(s)'
                        visible: root.relationship == util.ITEM_INSIDE || root.relationship == util.ITEM_OUTSIDE
                    }

                    PK.FormField {
                        id: insidesField
                        visible: insidesLabel.visible
                        backTabItem: spouseField.lastTabItem
                        tabItem: outsidesField.firstTabItem
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        Layout.minimumHeight: insidesPicker.height
                        Layout.maximumHeight: insidesPicker.height
                        PK.PeoplePicker {
                            id: insidesPicker
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        }
                    }

                    // Outside(s)

                    PK.Text {
                        id: outsidesLabel
                        text: 'Outside(s)'
                        visible: root.relationship == util.ITEM_INSIDE || root.relationship == util.ITEM_OUTSIDE
                    }

                    PK.FormField {
                        id: outsidesField
                        visible: outsidesLabel.visible
                        backTabItem: parentBField.lastTabItem
                        tabItem: receiversField.firstTabItem
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        Layout.minimumHeight: outsidesPicker.height
                        Layout.maximumHeight: outsidesPicker.height
                        PK.PeoplePicker {
                            id: outsidesPicker
                            scenePeopleModel: peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        }
                    }

                    // Person B

                    PK.Text {
                        id: personBLabel
                        text: {
                            if([util.ITEM_CONFLICT, util.ITEM_DISTANCE, util.ITEM_RECIPROCITY].indexOf(root.relationship) != -1) {
                                return "Recipient"
                            } else if(root.relationship == util.ITEM_RECIPROCITY) {
                                return "Overfunctioner"
                            } else if(root.relationship == util.ITEM_PROJECTION) {
                                return "Focused"
                            } else if(root.relationship == util.ITEM_DEFINED_SELF) {
                                return "Defined Self"
                            } else {
                                return "???"
                            }
                        }
                        visible: [util.ITEM_CONFLICT, util.ITEM_DISTANCE, util.ITEM_RECIPROCITY, util.ITEM_PROJECTION, util.ITEM_DEFINED_SELF].indexOf(root.relationship) != -1
                    }

                    PK.FormField {
                        id: personBField
                        visible: personBLabel.visible
                        backTabItem: peopleField.lastTabItem
                        tabItem: parentBField.firstTabItem
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

                    PK.FormDivider { Layout.columnSpan: 2; visible: sceneModel.isInEditorMode}
                    
                    PK.Text {
                        id: tagsLabel
                        text: "Tags"
                        visible: sceneModel.isInEditorMode
                    }

                    PK.FormField {

                        Layout.maximumWidth: root.fieldWidth
                        Layout.minimumWidth: root.fieldWidth
                        Layout.maximumHeight: util.QML_ITEM_HEIGHT * 15
                        Layout.minimumHeight: util.QML_LIST_VIEW_MINIMUM_HEIGHT
                        tabItem: notesField.firstTabItem
                        backTabItem: nodalBox
                        visible: sceneModel.isInEditorMode
                        onVisibleChanged: print('tagsField visible: ' + visible)

                        PK.ActiveListEdit {
                            id: tagsEditItem
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            model: TagsModel {
                                id: tagsModel
                                scene: sceneModel ? sceneModel.scene : undefined
                                items: eventModel.items
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
