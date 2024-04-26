import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import "./PK" 1.0 as PK
import PK.Models 1.0
import "js/Global.js" as Global
import "js/Underscore.js" as Underscore

PK.Drawer {

    id: root
    objectName: 'AddAnythingDialog'

    signal cancel

    property int margin: util.QML_MARGINS
    property var focusResetter: addPage
    property bool canInspect: false
    property var peopleModel: ListModel { }
    property var selectedPeopleModel: ListModel {
        objectName: 'selectedPeopleModel'
    }

    // Keys.onPressed: {
    //     if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
    //         done()
    //     }
    // }

    property var kind: null
    property var description: descriptionEdit.text
    property var isDateRange: isDateRangeBox.checked
    property var startDateTime: startDatePicker.dateTime
    property var startDateUnsure: startDatePicker.unsure
    property var endDateTime: endDatePicker.dateTime
    property var endDateUnsure: endDatePicker.unsure
    property var location: locationEdit.text
    property var nodal: nodalBox.checked
    property var anxiety: anxietyBox.value
    property var functioning: functioningBox.value
    property var symptom: symptomBox.value
    property var notes: notesEdit.text

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
        notesEdit.clear()
        addPage.scrollToTop()

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
    }
    function initWithMultiplePeople(peopleIds) {
        print(peopleIds)
        var people = [];
        for(var i=0; i < peopleIds.length; i++) {
            people.push(sceneModel.item(peopleIds[i]))
        }
        kindBox.setCurrentValue(util.EventKind.CustomIndividual)
        // print('initWithMultiplePeople: ' + people.length)
        peoplePicker.setExistingPeople(people)
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
            objectName: 'cancelButton'
            text: 'Cancel'
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: cancel()
        }
        PK.ToolButton {
            id: clearFormButton
            objectName: 'clearFormButton'
            text: "Clear"
            x: cancelButton.x + width + margin
            onClicked: {
                print('clear()')
                root.clear()
            }
        }
        PK.Label {
            text: 'Add Data Point'
            anchors.centerIn: parent
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            width: (submitButton.x) - (cancelButton.x + cancelButton.width) - root.margin * 2
            font.family: util.FONT_FAMILY_TITLE
            font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
        }
        PK.ToolButton {
            id: submitButton
            objectName: 'AddEverything_submitButton'
            text: 'Add'
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: {
                done()
            }
        }
    }

    background: Rectangle { color: util.QML_WINDOW_BG; anchors.fill: parent }

    StackLayout {

        id: stack
        objectName: 'stack'
        currentIndex: 0
        anchors.fill: parent

        Flickable {
            id: addPage
            objectName: 'addPage'
            contentWidth: width
            contentHeight: addPageInner.childrenRect.height + root.margin * 2
            function scrollToTop() { contentY = 0 }
            Rectangle {
                id: addPageInner
                anchors.fill: parent
                anchors.margins: margin
                color: 'transparent'

                MouseArea {
                    width: parent.width
                    height: parent.height
                    onClicked: parent.forceActiveFocus()
                }

                ColumnLayout { // necessary to expand anything vertically

                    width: parent.width

                    GridLayout {
                        id: mainGrid
                        columns: 2
                        columnSpacing: util.QML_MARGINS / 2

                        PK.Text {
                            id: kindLabel
                            objectName: "kindLabel"
                            text: "Event"
                        }

                        PK.ComboBox {
                            id: kindBox
                            objectName: "kindBox"
                            model: util.eventKindLabels()
                            property var valuesForIndex: util.eventKindValues()
                            property var lastCurrentIndex: -1
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            KeyNavigation.tab: personPicker.firstTabItem
                            KeyNavigation.backtab: notesEdit
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

                        PK.Text {
                            id: kindHelpText
                            objectName: "kindHelpText"
                            font.pixelSize: util.HELP_FONT_SIZE
                            wrapMode: Text.WordWrap
                            visible: text != ''
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                        }

                        // ////////////////////////////////////////////////

                        PK.FormDivider {
                            Layout.columnSpan: 2
                        }

                        // Person

                        PK.Text {
                            id: personLabel
                            objectName: "personLabel"
                            text: 'Person'
                            visible: util.isMonadicEventKind(root.kind)
                        }

                        PK.PersonPicker {
                            id: personPicker
                            objectName: "personPicker"
                            scenePeopleModel: root.peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            visible: personLabel.visible
                            borderWidth: 1
                            borderColor: util.QML_ITEM_BORDER_COLOR
                            backTabItem: kindBox
                            tabItem: peoplePicker.firstTabItem
                            Layout.minimumHeight: util.QML_FIELD_HEIGHT
                            Layout.maximumHeight: util.QML_FIELD_HEIGHT
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                        }

                        // People

                        PK.Text {
                            id: peopleLabel
                            objectName: "peopleLabel"
                            text: 'People'
                            visible: root.kind == util.EventKind.CustomIndividual
                        }

                        PK.PeoplePicker {
                            id: peoplePicker
                            objectName: "peoplePicker"
                            scenePeopleModel: root.peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            visible: peopleLabel.visible
                            backTabItem: personPicker.lastTabItem
                            tabItem: personAPicker.firstTabItem
                            Layout.fillHeight: true
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        }

                        // Person A

                        PK.Text {
                            id: personALabel
                            objectName: "personALabel"
                            text: util.isChildEventKind(root.kind) ? 'Parent A' : 'Person A'
                            visible: util.isPairBondEventKind(root.kind) || util.isChildEventKind(root.kind)
                        }

                        PK.PersonPicker {
                            id: personAPicker
                            objectName: "personAPicker"
                            scenePeopleModel: root.peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            visible: personALabel.visible
                            backTabItem: peoplePicker.lastTabItem
                            tabItem: personBPicker.firstTabItem
                            Layout.fillHeight: true
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            Layout.minimumHeight: util.QML_FIELD_HEIGHT
                            Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        }

                        // Person B

                        PK.Text {
                            id: personBLabel
                            objectName: "personBLabel"
                            text: util.isChildEventKind(root.kind) ? 'Parent B' : 'Person B'
                            visible: personALabel.visible
                        }

                        PK.PersonPicker {
                            id: personBPicker
                            objectName: "personBPicker"
                            scenePeopleModel: root.peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            visible: personALabel.visible
                            backTabItem: personAPicker.lastTabItem
                            tabItem: moversPicker.firstTabItem
                            Layout.fillHeight: true
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            Layout.minimumHeight: util.QML_FIELD_HEIGHT
                            Layout.maximumHeight: util.QML_FIELD_HEIGHT
                        }

                        // Mover(s)

                        PK.Text {
                            id: moversLabel
                            objectName: "moversLabel"
                            text: 'Mover(s)'
                            visible: util.isDyadicEventKind(root.kind)
                        }

                        PK.PeoplePicker {
                            id: moversPicker
                            objectName: "moversPicker"
                            visible: moversLabel.visible
                            scenePeopleModel: root.peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            backTabItem: personBPicker.lastTabItem
                            tabItem: receiversPicker.firstTabItem
                            Layout.fillHeight: true
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        }

                        // Receiver(s)

                        PK.Text {
                            id: receiversLabel
                            objectName: "receiversLabel"
                            visible: moversLabel.visible
                            text: 'Receiver(s)'
                        }

                        PK.PeoplePicker {
                            id: receiversPicker
                            objectName: "receiversPicker"
                            visible: moversLabel.visible
                            scenePeopleModel: root.peopleModel
                            selectedPeopleModel: root.selectedPeopleModel
                            backTabItem: moversPicker.lastTabItem
                            tabItem: descriptionEdit
                            Layout.fillHeight: true
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        }

                        PK.Text {
                            id: peopleHelpText
                            objectName: "peopleHelpText"
                            wrapMode: Text.WordWrap
                            visible: text != ''
                            font.pixelSize: util.HELP_FONT_SIZE
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                        }

                        // ////////////////////////////////////////////////

                        PK.FormDivider {
                            Layout.columnSpan: 2
                            visible: kindBox.currentIndex != -1
                        }


                        PK.Text {
                            id: descriptionLabel
                            objectName: "descriptionLabel"
                            text: "Description"
                            visible: util.isCustomEventKind(root.kind)
                        }

                        PK.TextField {
                            id: descriptionEdit
                            objectName: "descriptionEdit"
                            visible: util.isCustomEventKind(kindBox.valuesForIndex[kindBox.currentIndex])
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            KeyNavigation.backtab: receiversPicker.lastTabItem
                            KeyNavigation.tab: startDateButtons.firstTabItem
                            function clear() { text = '' }
                            // Keys.onPressed: {
                            //     if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
                            //         done()
                            //     }
                            // }
                        }

                        PK.FormDivider {
                            Layout.columnSpan: 2
                            visible: descriptionEdit.visible
                        }

                        PK.Text {
                            id: startDateTimeLabel
                            objectName: "startDateTimeLabel"
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
                            objectName: 'startDateButtons'
                            datePicker: startDatePicker
                            timePicker: startTimePicker
                            dateTime: root.startDateTime
                            showInspectButton: true
                            backTabItem: descriptionEdit
                            tabItem: endDateButtons.firstTabItem
                            Layout.preferredHeight: implicitHeight - 10
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
                            objectName: 'startDatePicker'
                            dateTime: root.startDateTime                            
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
                            objectName: 'startTimePicker'
                            dateTime: root.startDateTime                            
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
                            objectName: "endDateTimeLabel"
                            text: "Ended"
                            visible: root.isDateRange
                        }

                        PK.DatePickerButtons {
                            id: endDateButtons
                            objectName: 'endDateButtons'
                            datePicker: endDatePicker
                            timePicker: endTimePicker
                            dateTime: root.endDateTime                            
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
                            objectName: 'endDatePicker'
                            dateTime: root.endDateTime                            
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
                            objectName: 'endTimePicker'
                            dateTime: root.endDateTime
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
                            objectName: 'isDateRangeBox'
                            text: "Is Date Range" 
                            visible: isDateRangeLabel.visible
                            KeyNavigation.backtab: endDateButtons.lastTabItem
                            KeyNavigation.tab: locationEdit
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
                            objectName: "locationLabel"
                            text: "Location"
                        }

                        PK.TextField {
                            id: locationEdit
                            objectName: "locationEdit"
                            Layout.maximumWidth: root.fieldWidth
                            Layout.minimumWidth: root.fieldWidth
                            KeyNavigation.tab: nodalBox
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
                            // Keys.onPressed: {
                            //     if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
                            //         done()
                            //     }
                            // }

                        }

                        PK.FormDivider {
                            Layout.columnSpan: 2
                        }
                        
                        PK.Text { id: nodalLabel; text: "Nodal" }

                        PK.CheckBox {
                            id: nodalBox
                            objectName: "nodalBox"
                            KeyNavigation.tab: anxietyBox.firstTabItem
                            KeyNavigation.backtab: locationEdit
                            function clear() { checked = false }
                        }

                        PK.Text { text: "Anxiety" }

                        PK.VariableBox {
                            id: anxietyBox
                            objectName: "anxietyBox"
                            Layout.fillWidth: true
                            tabItem: functioningBox.firstTabItem
                            backTabItem: nodalBox
                        }

                        PK.Text { text: "Functioning" }

                        PK.VariableBox {
                            id: functioningBox
                            objectName: "functioningBox"
                            Layout.fillWidth: true
                            backTabItem: anxietyBox.lastTabItem
                            tabItem: symptomBox.firstTabItem
                        }

                        PK.Text { text: "Symptom" }

                        PK.VariableBox {
                            id: symptomBox
                            objectName: "symptomBox"
                            Layout.fillWidth: true
                            backTabItem: functioningBox.lastTabItem
                            tabItem: notesEdit
                        }

                        PK.FormDivider {
                            Layout.columnSpan: 2
                        }

                        PK.Text {
                            id: notesLabel
                            objectName: "notesLabel"
                            text: "Notes"
                        }

                        Rectangle { // for border
                            Layout.fillWidth: true
                            Layout.minimumHeight: 150
                            Layout.maximumHeight: 150
                            color: 'transparent'
                            border {
                                width: 1
                                color: util.QML_ITEM_BORDER_COLOR
                            }

                            PK.TextEdit {
                                id: notesEdit
                                objectName: "notesEdit"
                                wrapMode: TextEdit.Wrap
                                anchors.fill: parent
                                padding: margin
                                KeyNavigation.tab: kindBox
                                KeyNavigation.backtab: symptomBox.lastTabItem
                                function clear() { text = '' }
                                // Keys.onPressed: {
                                //     if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
                                //         done()
                                //     }
                                // }
                            }
                        }
                    }
                }
            }
        }       

    }            

}
