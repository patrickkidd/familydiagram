import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK
import "." 1.0 as Personal

Drawer {
    id: root

    property var pdp
    property int itemCount: 0
    property bool showTutorial: false
    property var editingItem: null
    property string editingItemType: ""
    property bool isInitializingFields: false
    readonly property bool editOverlayVisible: editOverlay.visible

    readonly property bool editingPairBondEvent: editingItemType === "event" && editingItem && [
        util.EventKind.Bonded,
        util.EventKind.Married,
        util.EventKind.Separated,
        util.EventKind.Divorced,
        util.EventKind.Moved
    ].indexOf(editingItem.kind) !== -1
    readonly property bool editingOffspringEvent: editingItemType === "event" && editingItem && [
        util.EventKind.Birth,
        util.EventKind.Adopted
    ].indexOf(editingItem.kind) !== -1

    signal itemAccepted(int id)
    signal itemRejected(int id)
    signal acceptAllClicked()
    signal fieldChanged(int id, string field, var value)

    function updateField(field, value) {
        if (editingItem) {
            editingItem[field] = value
            editingItemChanged()
            fieldChanged(editingItem.id, field, value)
        }
    }

    edge: Qt.BottomEdge
    width: parent.width
    height: parent.height * 0.75
    dragMargin: 0

    onOpened: {
        if (itemCount > 1 && showTutorial) {
            tutorialOverlay.visible = true
        }
    }

    function updateItems() {
        itemsModel.clear()
        if (!pdp) {
            itemCount = 0
            return
        }

        // Events first - accepting them cascade-adds their associated people
        if (pdp.events) {
            for (var i = 0; i < pdp.events.length; i++) {
                itemsModel.append({
                    "itemType": "event",
                    "itemId": pdp.events[i].id
                })
            }
        }
        if (pdp.people) {
            for (var i = 0; i < pdp.people.length; i++) {
                itemsModel.append({
                    "itemType": "person",
                    "itemId": pdp.people[i].id
                })
            }
        }
        itemCount = itemsModel.count
    }

    function findItemById(items, id) {
        if (!items) return null
        for (var i = 0; i < items.length; i++) {
            if (items[i].id == id) return items[i]
        }
        return null
    }

    function findPersonById(id) {
        return findItemById(pdp ? pdp.people : null, id)
    }

    function findEventById(id) {
        return findItemById(pdp ? pdp.events : null, id)
    }

    function removeItemById(id) {
        for (var i = 0; i < itemsModel.count; i++) {
            if (itemsModel.get(i).itemId === id) {
                itemsModel.remove(i)
                break
            }
        }
        itemCount = itemsModel.count

        if (itemCount === 0) {
            autoCloseTimer.start()
        } else if (cardStack.currentIndex >= itemCount) {
            cardStack.currentIndex = itemCount - 1
        }
    }

    function handleAccept(id) {
        root.itemAccepted(id)
        advanceTimer.targetIndex = Math.min(cardStack.currentIndex + 1, itemsModel.count - 1)
        advanceTimer.start()
    }

    function handleReject(id) {
        root.itemRejected(id)
        advanceTimer.targetIndex = Math.min(cardStack.currentIndex + 1, itemsModel.count - 1)
        advanceTimer.start()
    }

    function dismissTutorial() {
        showTutorial = false
        tutorialOverlay.visible = false
    }

    function resolvePersonName(personId) {
        if (personId === null || personId === undefined || !pdp) return ""
        // Check pending PDP people first (negative IDs)
        if (pdp.people) {
            for (var i = 0; i < pdp.people.length; i++) {
                var p = pdp.people[i]
                if (p.id == personId) {
                    return p.name || p.last_name || ""
                }
            }
        }
        // Check committed people (positive IDs)
        if (pdp.committedPeople) {
            for (var i = 0; i < pdp.committedPeople.length; i++) {
                var p = pdp.committedPeople[i]
                if (p.id == personId) {
                    return p.name || ""
                }
            }
        }
        return "Person #" + personId
    }

    function eventKindLabel(kind) {
        if (!kind) return "Event"
        if (kind === util.EventKind.Bonded) return "Bonded"
        if (kind === util.EventKind.Married) return "Married"
        if (kind === util.EventKind.Birth) return "Birth"
        if (kind === util.EventKind.Adopted) return "Adopted"
        if (kind === util.EventKind.Moved) return "Moved"
        if (kind === util.EventKind.Separated) return "Separated"
        if (kind === util.EventKind.Divorced) return "Divorced"
        if (kind === util.EventKind.Death) return "Death"
        if (kind === util.EventKind.Shift) return "Shift"
        if (kind === util.EventKind.Custom) return "Event"
        return "Event"
    }

    function eventKindColor(kind) {
        if (!kind) return util.QML_INACTIVE_TEXT_COLOR
        if (kind === util.EventKind.Bonded) return "#FF69B4"
        if (kind === util.EventKind.Married) return "#FF1493"
        if (kind === util.EventKind.Birth) return "#32CD32"
        if (kind === util.EventKind.Adopted) return "#32CD32"
        if (kind === util.EventKind.Moved) return "#4169E1"
        if (kind === util.EventKind.Separated) return "#FFA500"
        if (kind === util.EventKind.Divorced) return "#FF4500"
        if (kind === util.EventKind.Shift) return util.QML_HIGHLIGHT_COLOR
        if (kind === util.EventKind.Death) return "#808080"
        return util.QML_INACTIVE_TEXT_COLOR
    }

    function stringToDate(dateStr) {
        if (!dateStr || dateStr === "") return null
        var parts = dateStr.split("-")
        if (parts.length >= 3) {
            return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]))
        }
        return null
    }

    function dateToString(dt) {
        if (!dt || isNaN(dt.getTime())) return ""
        var year = dt.getFullYear()
        var month = (dt.getMonth() + 1).toString().padStart(2, '0')
        var day = dt.getDate().toString().padStart(2, '0')
        return year + "-" + month + "-" + day
    }

    function openEventEditOverlay(eventData) {
        editingItem = eventData
        editingItemType = "event"
        initEditFields()
        editOverlay.visible = true
    }

    function openPersonEditOverlay(personData) {
        editingItem = personData
        editingItemType = "person"
        editOverlay.visible = true
    }

    function closeEditOverlay() {
        editOverlay.visible = false
    }

    function initEditFields() {
        if (editingItemType === "event" && editingItem) {
            isInitializingFields = true
            editSymptomField.value = editingItem.symptom !== undefined ? editingItem.symptom : null
            editAnxietyField.value = editingItem.anxiety !== undefined ? editingItem.anxiety : null
            editFunctioningField.value = editingItem.functioning !== undefined ? editingItem.functioning : null
            editRelationshipField.value = editingItem.relationship !== undefined ? editingItem.relationship : null
            editDateCertaintyBox.setCurrentValue(editingItem.dateCertainty || "approximate")
            editDateButtons.dateTime = stringToDate(editingItem.dateTime)
            editEndDateButtons.dateTime = stringToDate(editingItem.endDateTime)
            isInitializingFields = false
        }
    }

    Timer {
        id: advanceTimer
        property int targetIndex: 0
        interval: 300
        repeat: false
        onTriggered: {
            if (itemsModel.count > 0 && targetIndex < itemsModel.count) {
                cardStack.currentIndex = targetIndex
            }
        }
    }

    Timer {
        id: autoCloseTimer
        interval: 300
        repeat: false
        onTriggered: {
            root.close()
        }
    }

    ListModel {
        id: itemsModel
    }

    background: Rectangle {
        color: util.QML_WINDOW_BG
        radius: 16
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: parent.height / 2
            color: util.QML_WINDOW_BG
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 4
            Layout.topMargin: 8
            Layout.leftMargin: parent.width / 2 - 20
            Layout.rightMargin: parent.width / 2 - 20
            radius: 2
            color: util.QML_ITEM_BORDER_COLOR
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            Layout.margins: util.QML_MARGINS

            Text {
                text: "Review"
                font.pixelSize: util.QML_TITLE_FONT_SIZE
                font.family: util.FONT_FAMILY_TITLE
                color: util.QML_TEXT_COLOR
                Layout.fillWidth: true
            }

            PK.Button {
                text: "Accept All"
                pill: true
                onClicked: root.acceptAllClicked()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: util.QML_ITEM_BORDER_COLOR
        }

        SwipeView {
            id: cardStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: util.QML_MARGINS
            clip: true
            interactive: true

            Repeater {
                id: cardRepeater
                model: itemsModel

                Item {
                    id: cardContainer
                    width: cardStack.width
                    height: cardStack.height
                    clip: true

                    Loader {
                        id: cardLoader
                        anchors.fill: parent
                        anchors.margins: 16

                        sourceComponent: {
                            if (model.itemType === "person") {
                                return personCardComponent
                            } else if (model.itemType === "event") {
                                return eventCardComponent
                            }
                            return null
                        }

                        onLoaded: {
                            if (model.itemType === "person") {
                                item.personData = root.findPersonById(model.itemId)
                                item.pdp = root.pdp
                            } else if (model.itemType === "event") {
                                item.eventData = root.findEventById(model.itemId)
                                item.pdp = root.pdp
                            }
                        }
                    }
                }
            }
        }

        PageIndicator {
            id: pageIndicator
            Layout.alignment: Qt.AlignHCenter
            Layout.bottomMargin: util.QML_MARGINS
            count: itemsModel.count
            currentIndex: cardStack.currentIndex
            interactive: false

            delegate: Rectangle {
                implicitWidth: 8
                implicitHeight: 8
                radius: 4
                color: index === pageIndicator.currentIndex ? util.QML_HIGHLIGHT_COLOR : util.QML_ITEM_BORDER_COLOR
                opacity: index === pageIndicator.currentIndex ? 1.0 : 0.5

                Behavior on opacity {
                    NumberAnimation { duration: 100 }
                }

                MouseArea {
                    anchors.centerIn: parent
                    width: 24
                    height: 24
                    onClicked: cardStack.currentIndex = index
                }
            }
        }
    }

    Rectangle {
        id: tutorialOverlay
        anchors.fill: parent
        color: "#80000000"
        visible: false
        z: 2000

        MouseArea {
            anchors.fill: parent
            onClicked: root.dismissTutorial()
        }

        Rectangle {
            anchors.centerIn: parent
            width: tutorialContent.width + 48
            height: tutorialContent.height + 48
            radius: 16
            color: util.QML_ITEM_BG
            border.color: util.QML_ITEM_BORDER_COLOR
            border.width: 1

            ColumnLayout {
                id: tutorialContent
                anchors.centerIn: parent
                spacing: 20

                Row {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 8

                    Text {
                        text: "←"
                        font.pixelSize: 24
                        color: util.QML_TEXT_COLOR
                        opacity: 0.5
                    }
                    Text {
                        text: "swipe"
                        font.pixelSize: 16
                        color: util.QML_TEXT_COLOR
                        opacity: 0.7
                    }
                    Text {
                        text: "→"
                        font.pixelSize: 24
                        color: util.QML_TEXT_COLOR
                        opacity: 0.5
                    }
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Swipe left or right\nto browse items"
                    font.pixelSize: 14
                    color: util.QML_TEXT_COLOR
                    horizontalAlignment: Text.AlignHCenter
                }

                PK.Button {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Got it"
                    pill: true
                    onClicked: root.dismissTutorial()
                }
            }
        }
    }

    Rectangle {
        id: editOverlay
        anchors.fill: parent
        color: util.QML_WINDOW_BG
        visible: false
        z: 3000

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: util.QML_MARGINS
            spacing: 12

            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: "← Done"
                    font.pixelSize: 16
                    color: util.QML_TEXT_COLOR

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.closeEditOverlay()
                    }
                }

                Item { Layout.fillWidth: true }

                RowLayout {
                    spacing: 8

                    Text {
                        text: "Edit"
                        font.pixelSize: util.QML_TITLE_FONT_SIZE
                        font.family: util.FONT_FAMILY_TITLE
                        color: util.QML_TEXT_COLOR
                    }

                    Rectangle {
                        visible: root.editingItemType === "event"
                        Layout.preferredWidth: 70
                        Layout.preferredHeight: 22
                        radius: 11
                        color: eventKindColor(root.editingItem ? root.editingItem.kind : null)
                        opacity: 0.9

                        Text {
                            anchors.centerIn: parent
                            text: eventKindLabel(root.editingItem ? root.editingItem.kind : null)
                            font.pixelSize: 11
                            font.bold: true
                            color: "white"
                        }
                    }

                    Text {
                        visible: root.editingItemType === "person"
                        text: "Person"
                        font.pixelSize: util.QML_TITLE_FONT_SIZE
                        font.family: util.FONT_FAMILY_TITLE
                        color: util.QML_TEXT_COLOR
                    }
                }

                Item { Layout.fillWidth: true }

                Item { width: 50 }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: util.QML_ITEM_BORDER_COLOR
            }

            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentHeight: editFieldsColumn.height
                clip: true
                flickableDirection: Flickable.VerticalFlick
                boundsBehavior: Flickable.StopAtBounds

                ColumnLayout {
                    id: editFieldsColumn
                    width: parent.width
                    spacing: 16

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingItemType === "person"

                        Text {
                            text: "Name"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.TextField {
                            id: editPersonNameField
                            Layout.fillWidth: true
                            text: root.editingItem && root.editingItemType === "person" ? (root.editingItem.name || "") : ""
                            onTextEdited: {
                                if (root.editingItem && root.editingItemType === "person") {
                                    root.updateField("name", text)
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingItemType === "person"

                        Text {
                            text: "Last Name"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.TextField {
                            id: editPersonLastNameField
                            Layout.fillWidth: true
                            text: root.editingItem && root.editingItemType === "person" ? (root.editingItem.last_name || "") : ""
                            onTextEdited: {
                                if (root.editingItem && root.editingItemType === "person") {
                                    root.updateField("last_name", text)
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingItemType === "event" && root.editingItem && root.editingItem.person !== null && root.editingItem.person !== undefined

                        Text {
                            text: "Person"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.TextField {
                            id: editEventPersonField
                            Layout.fillWidth: true
                            text: root.resolvePersonName(root.editingItem ? root.editingItem.person : null)
                            enabled: false
                            color: util.QML_INACTIVE_TEXT_COLOR
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: (root.editingPairBondEvent || root.editingOffspringEvent) && root.editingItem && root.editingItem.spouse

                        Text {
                            text: "Spouse"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.TextField {
                            id: editEventSpouseField
                            Layout.fillWidth: true
                            text: root.resolvePersonName(root.editingItem ? root.editingItem.spouse : null)
                            enabled: false
                            color: util.QML_INACTIVE_TEXT_COLOR
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingOffspringEvent && root.editingItem && root.editingItem.child

                        Text {
                            text: "Child"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.TextField {
                            id: editEventChildField
                            Layout.fillWidth: true
                            text: root.resolvePersonName(root.editingItem ? root.editingItem.child : null)
                            enabled: false
                            color: util.QML_INACTIVE_TEXT_COLOR
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingItemType === "event" && root.editingItem && root.editingItem.kind === util.EventKind.Shift

                        Text {
                            text: "Description"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.TextField {
                            id: editDescriptionField
                            Layout.fillWidth: true
                            text: root.editingItem && root.editingItemType === "event" ? (root.editingItem.description || "") : ""
                            onTextEdited: {
                                if (root.editingItem && root.editingItemType === "event") {
                                    root.updateField("description", text)
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingItemType === "event" && root.editingItem && root.editingItem.kind === util.EventKind.Shift

                        Text {
                            text: "Symptom"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.VariableField {
                            id: editSymptomField
                            Layout.fillWidth: true
                            onValueChanged: {
                                if (!root.isInitializingFields && root.editingItem && root.editingItemType === "event" && value !== root.editingItem.symptom) {
                                    root.updateField("symptom", value)
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingItemType === "event" && root.editingItem && root.editingItem.kind === util.EventKind.Shift

                        Text {
                            text: "Anxiety"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.VariableField {
                            id: editAnxietyField
                            Layout.fillWidth: true
                            onValueChanged: {
                                if (!root.isInitializingFields && root.editingItem && root.editingItemType === "event" && value !== root.editingItem.anxiety) {
                                    root.updateField("anxiety", value)
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingItemType === "event" && root.editingItem && root.editingItem.kind === util.EventKind.Shift

                        Text {
                            text: "Relationship"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.VariableField {
                            id: editRelationshipField
                            Layout.fillWidth: true
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
                                { 'name': "Defined Self", 'value': 'defined-self' }
                            ]
                            onValueChanged: {
                                if (!root.isInitializingFields && root.editingItem && root.editingItemType === "event" && value !== root.editingItem.relationship) {
                                    root.updateField("relationship", value)
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingItemType === "event" && root.editingItem && root.editingItem.kind === util.EventKind.Shift

                        Text {
                            text: "Functioning"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.VariableField {
                            id: editFunctioningField
                            Layout.fillWidth: true
                            onValueChanged: {
                                if (!root.isInitializingFields && root.editingItem && root.editingItemType === "event" && value !== root.editingItem.functioning) {
                                    root.updateField("functioning", value)
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingItemType === "event"

                        Text {
                            text: "Date"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            PK.DatePickerButtons {
                                id: editDateButtons
                                datePicker: editDatePicker
                                timePicker: null
                                hideReset: true
                                hideTime: true
                                onDateTimeChanged: {
                                    if (!root.isInitializingFields && root.editingItem && root.editingItemType === "event") {
                                        root.updateField("dateTime", dateToString(dateTime))
                                    }
                                }
                            }
                            PK.ComboBox {
                                id: editDateCertaintyBox
                                Layout.preferredWidth: 130
                                model: ListModel {
                                    ListElement { label: "Unknown"; value: "unknown" }
                                    ListElement { label: "Approximate"; value: "approximate" }
                                    ListElement { label: "Certain"; value: "certain" }
                                }
                                currentIndex: 1
                                textRole: "label"
                                function setCurrentValue(value) {
                                    for (var i = 0; i < model.count; i++) {
                                        if (model.get(i).value === value) {
                                            currentIndex = i
                                            return
                                        }
                                    }
                                    currentIndex = 1
                                }
                                function currentValue() {
                                    if (currentIndex === -1) return "approximate"
                                    return model.get(currentIndex).value
                                }
                                onCurrentIndexChanged: {
                                    if (!root.isInitializingFields && root.editingItem && root.editingItemType === "event") {
                                        var val = currentValue()
                                        if (val !== root.editingItem.dateCertainty) {
                                            root.updateField("dateCertainty", val)
                                        }
                                    }
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }
                        PK.DatePicker {
                            id: editDatePicker
                            Layout.fillWidth: true
                            Layout.preferredHeight: shouldShow ? implicitHeight : 0
                            visible: shouldShow
                            onDateTimeChanged: editDateButtons.dateTime = dateTime
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.editingItemType === "event"

                        Text {
                            text: "End Date"
                            font.pixelSize: 14
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                        }
                        PK.DatePickerButtons {
                            id: editEndDateButtons
                            datePicker: editEndDatePicker
                            timePicker: null
                            hideReset: true
                            hideTime: true
                            onDateTimeChanged: {
                                if (!root.isInitializingFields && root.editingItem && root.editingItemType === "event") {
                                    root.updateField("endDateTime", dateToString(dateTime))
                                }
                            }
                        }
                        PK.DatePicker {
                            id: editEndDatePicker
                            Layout.fillWidth: true
                            Layout.preferredHeight: shouldShow ? implicitHeight : 0
                            visible: shouldShow
                            onDateTimeChanged: editEndDateButtons.dateTime = dateTime
                        }
                    }

                    Item { height: 20 }
                }
            }
        }
    }

    Component {
        id: personCardComponent

        Personal.PDPPersonCard {
            onAccepted: root.handleAccept(id)
            onRejected: root.handleReject(id)
            onEditRequested: function(personData) {
                root.openPersonEditOverlay(personData)
            }
        }
    }

    Component {
        id: eventCardComponent

        Personal.PDPEventCard {
            onAccepted: root.handleAccept(id)
            onRejected: root.handleReject(id)
            onEditRequested: function(eventData) {
                root.openEventEditOverlay(eventData)
            }
        }
    }

}
