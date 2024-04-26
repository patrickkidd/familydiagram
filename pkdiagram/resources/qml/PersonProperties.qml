import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Controls 2.5 as QQC
import QtQuick.Layouts 1.12
import QtQuick.Window 2.2
import "./PK" 1.0 as PK
import PK.Models 1.0


PK.Drawer {
    
    id: root
    objectName: 'personProps'

    signal toggleExpand
    signal editTimelineItem

    property bool isDrawerOpen: eventPropertiesDrawer.visible

    property int margin: util.QML_MARGINS
    property var focusResetter: personPageInner
    property int numPeople: personModel.items.length
    property string itemTitle: {
        if(numPeople == 1) {
            if(personModel.fullNameOrAlias) {
                personModel.fullNameOrAlias
            } else {
                'Unnamed Person'
            }
        } else {
            numPeople + ' People'
        }
    }
    property var personModel: PersonPropertiesModel {
        scene: sceneModel.scene
        onItemsChanged: {
            if(items.length == 0) {
                eventPropertiesDrawer.position = 0
            }            
        }
    }

    property bool isReadOnly: (sceneModel && sceneModel.readOnly) ? true : false
    property bool canRemove: tabBar.currentIndex == 1 && timelineView.canRemove
    property bool canInspect: tabBar.currentIndex == 1 && timelineView.canInspect

    onCanRemoveChanged: sceneModel.selectionChanged()

    function removeSelection() {
        timelineView.removeSelection()
    }

    function setCurrentTab(tab) {
        var index = 0
        if(tab == 'item')
            index = 0
        else if(tab == 'timeline')
            index = 1
        else if(tab == 'notes')
            index = 2
        else if(tab == 'meta')
            index = 3
        tabBar.setCurrentIndex(index)
    }

    function currentTab() {
        return {
            0: 'item',
            1: 'timeline',
            2: 'notes',
            3: 'meta'
        }[tabBar.currentIndex]
    }
    
    function onInspect(tab) {
        if(canInspect && timelineView.selectedEvents.length) {
            commands.trackView('Edit person events')
            if(tab !== undefined) {
                eventProperties.setCurrentTab(tab)
            } else {
                eventProperties.setCurrentTab('item')
            }
            eventProperties.eventModel.items = timelineView.selectedEvents
            eventPropertiesDrawer.visible = true
        }
    }

    function onInspectNotes(row) {
        commands.trackView('Edit event notes')
        eventProperties.eventModel.items = timelineView.selectedEvents
        eventProperties.setCurrentTab('notes')
        eventPropertiesDrawer.visible = true
    }

    header: PK.ToolBar {
        PK.ToolButton {
            id: resizeButton
            text: root.expanded ? "Contract" : "Expand"
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: resize()
        }
        PK.Label {
            id: titleBar
            text: itemTitle
            elide: Text.ElideRight
            anchors.centerIn: parent
            horizontalAlignment: Text.AlignHCenter
            width: (doneButton.x) - (resizeButton.x + resizeButton.width) - root.margin * 2
            font.family: util.FONT_FAMILY_TITLE
            font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
        }
        PK.ToolButton {
            id: doneButton
            text: "Done"
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: done()
        }
    }

    footer: PK.TabBar {
        id: tabBar
        objectName: "tabBar"
        currentIndex: stack.currentIndex
        PK.TabButton { text: "Person" }
        PK.TabButton { text: "Timeline" }
        PK.TabButton { text: "Notes" }
        PK.TabButton { text: "Views" }
    }

    background: Rectangle {
        anchors.fill: parent
        color: util.QML_WINDOW_BG
    }

    QQC.Drawer {
        id: eventPropertiesDrawer
        objectName: 'eventPropertiesDrawer'
        width: util.DRAWER_OVER_WIDTH
        height: root.height
        dragMargin: 0
        edge: Qt.RightEdge
        PK.EventProperties {
            id: eventProperties
            objectName: 'eventProperties'
            anchors.fill: parent
        }
        onPositionChanged: if(position == 0) eventProperties.eventModel.items = undefined
        Connections {
            target: eventProperties
            function onDone() { eventPropertiesDrawer.visible = false }
        }
    }

    KeyNavigation.tab: firstNameEdit
    
    StackLayout {

        id: stack
        objectName: 'stack'
        currentIndex: tabBar.currentIndex
        anchors.fill: parent

        Flickable {
            id: personPage
            objectName: 'personPage'
            contentWidth: width
            contentHeight: personPageInner.childrenRect.height + 50
        
            Rectangle {

                id: personPageInner
                anchors.fill: parent
                anchors.margins: margin
                color: 'transparent'

                MouseArea {
                    x: 0; y: 0
                    width: personPage.width
                    height: personPage.height
                    onClicked: parent.forceActiveFocus()
                }

                ColumnLayout { // necessary to expand DatePicker

                    GridLayout {
                        
                        
                        id: mainGrid
                        columns: 3
                        columnSpacing: util.QML_MARGINS / 2
                        
                        // First Name
                        
                        PK.Text {
                            id: firstNameLabel
                            text: qsTr("First Name")
                        }
                        
                        PK.TextField {
                            id: firstNameEdit
                            objectName: 'firstNameEdit'
                            Layout.fillWidth: true
                            text: sceneModel.showAliases ? personModel.fullNameOrAlias : personModel.name
                            enabled: !root.isReadOnly && !sceneModel.showAliases
                            KeyNavigation.tab: middleNameEdit
                            onEditingFinished: personModel.name = (text ? text : undefined)
                        }

                        Rectangle { width: 1; height: 1; color: 'transparent' }

                        // Middle Name

                        PK.Text {
                            id: middleNameLabel
                            text: qsTr("Middle Name")
                        }

                        PK.TextField {
                            id: middleNameEdit
                            objectName: 'middleNameEdit'
                            Layout.fillWidth: true
                            text: sceneModel.showAliases ? '' : personModel.middleName
                            enabled: !root.isReadOnly && !sceneModel.showAliases
                            KeyNavigation.tab: middleNameBox
                            onEditingFinished: personModel.middleName = (text ? text : undefined)
                        }

                        PK.CheckBox {
                            id: middleNameBox
                            objectName: 'middleNameBox'
                            checkState: personModel.showMiddleName
                            enabled: !root.isReadOnly
                            KeyNavigation.tab: lastNameEdit
                            onClicked: personModel.showMiddleName = checkState
                        }

                        // Last Name

                        PK.Text {
                            id: lastNameLabel
                            text: qsTr("Last Name")
                        }

                        PK.TextField {
                            id: lastNameEdit
                            objectName: 'lastNameEdit'
                            Layout.fillWidth: true
                            text: sceneModel.showAliases ? '' : personModel.lastName
                            enabled: !root.isReadOnly && !sceneModel.showAliases
                            KeyNavigation.tab: lastNameBox
                            onEditingFinished: personModel.lastName = (text ? text : undefined)
                        }

                        PK.CheckBox {
                            id: lastNameBox
                            objectName: 'lastNameBox'
                            checkState: personModel.showLastName
                            enabled: !root.isReadOnly
                            KeyNavigation.tab: nickNameEdit
                            onClicked: personModel.showLastName = checkState
                        }
                        
                        // Nick Name

                        PK.Text {
                            id: nickNameLabel
                            text: qsTr("Nick Name")
                        }

                        PK.TextField {
                            id: nickNameEdit
                            objectName: 'nickNameEdit'
                            Layout.fillWidth: true
                            enabled: !root.isReadOnly && !sceneModel.showAliases
                            text: sceneModel.showAliases ? '' : personModel.nickName
                            KeyNavigation.tab: showNickNameBox
                            onEditingFinished: personModel.nickName = (text ? text : undefined)
                        }

                        PK.CheckBox {
                            id: showNickNameBox
                            objectName: 'showNickNameBox'
                            /* text: 'Show' */
                            checked: personModel.showNickName
                            enabled: !root.isReadOnly
                            KeyNavigation.tab: birthNameEdit
                            onClicked: personModel.showNickName = checkState
                        }
                        
                        // Birth Name

                        PK.Text {
                            id: birthNameLabel
                            text: qsTr("Birth Name")
                        }

                        PK.TextField {
                            id: birthNameEdit
                            objectName: 'birthNameEdit'
                            Layout.fillWidth: true
                            text: sceneModel.showAliases ? '' : personModel.birthName
                            enabled: !root.isReadOnly && !sceneModel.showAliases
                            KeyNavigation.tab: kindBox
                            onEditingFinished: personModel.birthName = (text ? text : undefined)
                        }

                        Rectangle { width: 1; height: 20; color: 'transparent' }

                        PK.FormDivider { Layout.columnSpan: 3 }
                        
                        // Kind

                        PK.Text {
                            id: kindLabel
                            text: qsTr("Kind")
                        }

                        PK.ComboBox {
                            id: kindBox
                            objectName: 'kindBox'
                            enabled: !root.isReadOnly
                            Layout.fillWidth: true
                            model: util.PERSON_KIND_NAMES
                            currentIndex: personModel.genderIndex
                            KeyNavigation.tab: sizeBox
                            onCurrentIndexChanged: personModel.genderIndex = currentIndex
                        }
                                                                        
                        Rectangle { width: 1; height: 1; color: 'transparent' }

                        // Size

                        PK.Text {
                            id: sizeLabel
                            text: qsTr("Size")
                        }

                        PK.ComboBox {
                            id: sizeBox
                            objectName: 'sizeBox'
                            Layout.fillWidth: true
                            currentIndex: personModel.sizeIndex
                            model: util.PERSON_SIZE_NAMES
                            enabled: !root.isReadOnly
                            KeyNavigation.tab: ageBox
                            onActivated: personModel.sizeIndex = currentIndex
                        }

                        Rectangle { width: 1; height: 1; color: 'transparent' }

                        // Age

                        PK.Text { text: "Age" }

                        RowLayout {
                            Layout.columnSpan: 2
                            PK.TextField {
                                id: ageBox
                                objectName: 'ageBox'
                                enabled: !root.isReadOnly
                                Layout.maximumWidth: 100
                                KeyNavigation.tab: birthDateButtons.textInput
                                Keys.onReturnPressed: setAge()
                                Keys.onEnterPressed: setAge()
                                property bool blocked: false
                                function setAge() {
                                    if(blocked) // when setting age from personProps below
                                        return
                                    var years = parseInt(text)
                                    if(isNaN(years)) {
                                        return
                                    }
                                    blocked = true
                                    personModel.age = years
                                    personModel.birthDateUnsure = Qt.Checked
                                    blocked = false
                                }
                                inputMethodHints: Qt.ImhDigitsOnly
                                function updateFromPerson() {
                                    if(ageBox.blocked) {
                                    } else if(personModel.age == -1) {
                                        ageBox.text = ''
                                    } else if(personModel.birthDateTime === undefined) {
                                        ageBox.text = ''
                                    } else if(isNaN(personModel.birthDateTime)) {
                                        ageBox.text = ''
                                    } else {
                                        ageBox.text = personModel.age
                                    }
                                }
                                Connections {
                                    target: personModel
                                    function onBirthDateTimeChanged() { ageBox.updateFromPerson() }
                                    function onDeceasedDateTimeChanged() { ageBox.updateFromPerson() }
                                    function onDeceasedChanged() { ageBox.updateFromPerson() }
                                }
                            }

                            PK.Text {
                                text: '(Press enter to estimate birth date)'
                                wrapMode: Text.WordWrap
                                font.pixelSize: util.HELP_FONT_SIZE
                                Layout.maximumWidth: 120
                            }
                        }
                        
                        // Born Date

                        PK.Text { text: "Born" }

                        PK.DatePickerButtons {
                            id: birthDateButtons
                            objectName: 'birthDateButtons'
                            datePicker: birthDatePicker
                            timePicker: birthTimePicker
                            dateTime: personModel.birthDateTime
                            enabled: !root.isReadOnly
                            backTabItem: ageBox
                            tabItem: birthLocationEdit
                            onDateTimeChanged: personModel.birthDateTime = dateTime
                            onUnsureChanged: personModel.birthDateUnsure = unsure
                            Layout.columnSpan: 2
                            Layout.preferredHeight: implicitHeight - 10
                            Connections {
                                target: personModel
                                function onBirthDateTimeChanged() { birthDateButtons.dateTime = personModel.birthDateTime }
                                function onBirthDateUnsureChanged() { birthDateButtons.unsure = personModel.birthDateUnsure }
                            }
                        }

                        PK.DatePicker {
                            id: birthDatePicker
                            objectName: 'birthDatePicker'
                            dateTime: personModel.birthDateTime
                            Layout.columnSpan: 3
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            onDateTimeChanged: personModel.birthDateTime = dateTime
                            Connections {
                                target: personModel
                                function onBirthDateTimeChanged() { birthDatePicker.dateTime = personModel.birthDateTime }
                            }                            
                        }

                        PK.TimePicker {
                            id: birthTimePicker
                            objectName: "birthTimePicker"
                            dateTime: personModel.birthDateTime
                            Layout.columnSpan: 3
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            onDateTimeChanged: personModel.birthDateTime = dateTime
                            Connections {
                                target: personModel
                                function onBirthDateTimeChanged() { birthTimePicker.dateTime = personModel.birthDateTime }
                            }
                        }

                        // Birth Location

                        Rectangle { width: 10; height: 10; color: 'transparent' }

                        PK.TextField {
                            id: birthLocationEdit
                            objectName: 'birthLocationEdit'
                            text: personModel.birthLocation
                            enabled: !root.isReadOnly
                            Layout.fillWidth: true
                            KeyNavigation.tab: adoptedBox
                            KeyNavigation.backtab: birthDateButtons.lastTabItem
                            placeholderText: 'Location'
                            onEditingFinished: personModel.birthLocation = (text ? text : undefined)
                        }

                        Rectangle { width: 10; height: 10; color: 'transparent' }

                        // Adopted Date
                        
                        PK.CheckBox {
                            id: adoptedBox
                            objectName: 'adoptedBox'
                            text: 'Adopted'
                            checkState: personModel.adopted
                            enabled: !root.isReadOnly
                            KeyNavigation.tab: adoptedBox.checked ? adoptedDateButtons.textInput : deceasedBox
                            onClicked: personModel.adopted = checkState
                        }
                        
                        PK.DatePickerButtons {
                            id: adoptedDateButtons
                            objectName: 'adoptedDateButtons'
                            datePicker: adoptedDatePicker
                            timePicker: adoptedTimePicker
                            dateTime: personModel.adoptedDateTime
                            enabled: adoptedBox.checkState != Qt.Unchecked && !sceneModel.readOnly
                            Layout.columnSpan: 2
                            Layout.preferredHeight: implicitHeight - 10
                            backTabItem: adoptedBox
                            tabItem: deceasedBox
                            onDateTimeChanged: personModel.adoptedDateTime = dateTime
                            onUnsureChanged: personModel.adoptedDateUnsure = unsure
                            Connections {
                                target: personModel
                                function onAdoptedDateTimeChanged() { adoptedDateButtons.dateTime = personModel.adoptedDateTime }
                                function onAdoptedDateUnsureChanged() { adoptedDateButtons.unsure = personModel.adoptedDateUnsure }
                            }
                        }

                        PK.DatePicker {
                            id: adoptedDatePicker
                            objectName: 'adoptedDatePicker'
                            dateTime: personModel.adoptedDateTime
                            Layout.columnSpan: 3
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            state: adoptedBox.checkState != Qt.Unchecked && shouldShow ? 'shown' : 'hidden'
                            onDateTimeChanged: personModel.adoptedDateTime = dateTime
                            Connections {
                                target: personModel
                                function onAdoptedDateTimeChanged() { adoptedDatePicker.dateTime = personModel.adoptedDateTime }
                            }                            
                        }
                       
                        PK.TimePicker {
                            id: adoptedTimePicker
                            objectName: 'adoptedTimePicker'
                            dateTime: personModel.adoptedDateTime
                            Layout.columnSpan: 3
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            state: adoptedBox.checkState != Qt.Unchecked && shouldShow ? 'shown' : 'hidden'
                            onDateTimeChanged: personModel.adoptedDateTime = dateTime
                            Connections {
                                target: personModel
                                function onAdoptedDateTimeChanged() { adoptedTimePicker.dateTime = personModel.adoptedDateTime }
                            }                            
                        } 
                        // Deceased
                        
                        PK.CheckBox {
                            id: deceasedBox
                            objectName: 'deceasedBox'
                            text: 'Deceased'
                            checkState: personModel.deceased
                            enabled: !root.isReadOnly
                            KeyNavigation.tab: deceasedBox.checked ? deceasedDateButtons.textInput : deceasedLocationEdit
                            onClicked: personModel.deceased = checkState
                        }
                        
                        PK.DatePickerButtons {
                            id: deceasedDateButtons
                            objectName: 'deceasedDateButtons'
                            datePicker: deceasedDatePicker
                            timePicker: deceasedTimePicker
                            dateTime: personModel.deceasedDateTime
                            enabled: deceasedBox.checkState != Qt.Unchecked && !sceneModel.readOnly
                            Layout.columnSpan: 2
                            Layout.preferredHeight: implicitHeight - 10
                            backTabItem: deceasedBox
                            tabItem: deceasedReasonEdit
                            onDateTimeChanged: personModel.deceasedDateTime = dateTime
                            onUnsureChanged: personModel.deceasedDateUnsure = unsure
                            Connections {
                                target: personModel
                                function onDeceasedDateTimeChanged() { deceasedDateButtons.dateTime = personModel.deceasedDateTime }
                                function onDeceasedDateUnsureChanged() { deceasedDateButtons.unsure = personModel.deceasedDateUnsure }
                            }
                        }

                        PK.DatePicker {
                            id: deceasedDatePicker
                            objectName: 'deceasedDatePicker'
                            dateTime: personModel.deceasedDateTime
                            Layout.columnSpan: 3
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            onDateTimeChanged: personModel.deceasedDateTime = dateTime
                            Connections {
                                target: personModel
                                function onDeceasedDateTimeChanged() { deceasedDatePicker.dateTime = personModel.deceasedDateTime }
                            }                            
                        }

                        PK.TimePicker {
                            id: deceasedTimePicker
                            objectName: 'deceasedTimePicker'
                            dateTime: personModel.deceasedDateTime
                            Layout.columnSpan: 3
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            onDateTimeChanged: personModel.deceasedDateTime = dateTime
                            Connections {
                                target: personModel
                                function onDeceasedDateTimeChanged() { deceasedTimePicker.dateTime = personModel.deceasedDateTime }
                            }                            
                        }                    
                        
                        // Deceased Reason

                        Rectangle {
                            width: 1; height: 1
                            color: 'transparent'
                            visible: deceasedBox.checkState != Qt.Unchecked
                        }

                        PK.TextField {
                            id: deceasedReasonEdit
                            objectName: 'deceasedReasonEdit'
                            text: personModel.deceasedReason
                            enabled: deceasedBox.checkState != Qt.Unchecked && !sceneModel.readOnly
                            visible: deceasedBox.checkState != Qt.Unchecked
                            placeholderText: 'Cause of death'
                            KeyNavigation.tab: deceasedLocationEdit
                            KeyNavigation.backtab: deceasedDateButtons.lastTabItem
                            onEditingFinished: personModel.deceasedReason = (text ? text : undefined)
                        }

                        Rectangle {
                            width: 10; height: 10
                            color: 'transparent'
                            visible: deceasedBox.checkState != Qt.Unchecked
                        }

                        // Deceased Location

                        Rectangle {
                            width: 1; height: 1
                            color: 'transparent'
                            visible: deceasedBox.checkState != Qt.Unchecked
                        }

                        PK.TextField {
                            id: deceasedLocationEdit
                            objectName: 'deceasedLocationEdit'
                            text: personModel.deceasedLocation
                            enabled: deceasedBox.checkState != Qt.Unchecked && !sceneModel.readOnly
                            visible: deceasedBox.checkState != Qt.Unchecked
                            placeholderText: 'Location'
                            Layout.fillWidth: true
                            KeyNavigation.tab: diagramNotesEdit
                            KeyNavigation.backtab: deceasedReasonEdit
                            onEditingFinished: personModel.deceasedLocation = (text ? text : undefined)
                        }

                        Rectangle {
                            width: 10; height: 10
                            color: 'transparent'
                            visible: deceasedBox.checkState != Qt.Unchecked
                       }

                        // Spacer line

                        Rectangle {
                            height: 1
                            Layout.fillWidth: true
                            Layout.columnSpan: 3
                            Layout.topMargin: margin
                            Layout.bottomMargin: margin
                            color: util.QML_ITEM_BORDER_COLOR
                        }

                        ColumnLayout {
                            Layout.columnSpan: 3

                            PK.Label {
                                text: 'Diagram Notes'
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
                                    id: diagramNotesEdit
                                    objectName: 'diagramNotesEdit'
                                    text: personModel.diagramNotes
                                    // wrapMode: TextEdit.Wrap
                                    anchors.fill: parent
                                    padding: margin
                                    enabled: !root.isReadOnly
                                    KeyNavigation.tab: primaryBox
                                    onTextChanged: personModel.diagramNotes = (text ? text : undefined)
                                }
                            }
                        }

                        // Spacer line

                        PK.FormDivider { Layout.columnSpan: 3 }

                        Row {

                            Layout.fillWidth: true
                            Layout.columnSpan: 3                            
                        
                            PK.CheckBox {
                                id: primaryBox
                                objectName: 'primaryBox'
                                text: "Primary"
                                enabled: !root.isReadOnly
                                checkState: personModel.primary
                                KeyNavigation.tab: bigFontBox
                                onCheckStateChanged: personModel.primary = checkState
                            }

                            PK.CheckBox {
                                id: bigFontBox
                                objectName: 'bigFontBox'
                                text: "Big Font"
                                enabled: !root.isReadOnly
                                checkState: personModel.bigFont
                                KeyNavigation.tab: hideDetailsBox
                                onCheckStateChanged: personModel.bigFont = checkState
                            }

                            PK.CheckBox {
                                id: hideDetailsBox
                                objectName: 'hideDetailsBox'
                                text: "Hide Details"
                                enabled: !root.isReadOnly
                                checkState: personModel.hideDetails
                                KeyNavigation.tab: firstNameEdit
                                onCheckStateChanged: personModel.hideDetails = checkState
                            }

                        }
                    }

                }
            }
        }

        Page {

            id: timelinePage
            objectName: 'timelinePage'
            Layout.fillHeight: true
            Layout.fillWidth: true
            padding: 0
            enabled: timelineView.model.items.length > 0
            
            Rectangle { color: util.QML_WINDOW_BG ; anchors.fill: parent }

            PK.TimelineView {
                id: timelineView
                objectName: 'personProps_timelineView'
                model: TimelineModel {
                    objectName: 'personTimelineModel'
                    scene: sceneModel.scene
                    items: personModel.items.length > 0 ? personModel.items : undefined
                }
                margin: root.margin
                anchors.fill: parent
                onSelectionChanged: sceneModel.selectionChanged()
                onInspect: root.onInspect()
                onInspectNotes: root.onInspectNotes(row)
            }

        }

        Flickable {
            id: notesEditFlickable
            contentX: 0
            contentHeight: Math.max(notesEdit.paintedHeight + 50, height) // allow scrolling
            Layout.fillHeight: true
            Layout.fillWidth: true
            
            PK.TextEdit {
                id: notesEdit
                objectName: 'notesEdit'
                width: parent.width
                text: personModel.notes
                padding: margin
                wrapMode: TextEdit.Wrap
                enabled: !root.isReadOnly
                anchors.fill: parent
                onEditingFinished: personModel.notes = (text ? text : undefined)
            }
        }

        Item {
            id: metaPage
            Layout.fillHeight: true
            Layout.fillWidth: true
            Rectangle {
                anchors.fill: parent
                anchors.margins: margin
                color: 'transparent'
                
                ColumnLayout {
                    anchors.fill: parent

                    PK.GroupBox {
                        title: "Properties Stored in diagram views"
                        Layout.fillWidth: true
                        enabled: sceneModel.hasActiveLayers && !sceneModel.readOnly
                        GridLayout {
                            columns: 3
                            columnSpacing: util.QML_MARGINS / 2

                            // Color

                            PK.Label { text: "Color"; }
                            
                            PK.ColorPicker {
                                id: colorBox
                                objectName: 'colorBox'
                                color: personModel.color != undefined ? personModel.color : 'transparent'
                                onCurrentIndexChanged: personModel.color = model[currentIndex]
                            }
                            
                            PK.Button {
                                id: resetColorButton
                                objectName: 'resetColorButton'
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.color != '' || personModel.items.length > 1
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.color = undefined
                            }

                            // Deemphasize

                            PK.Label { text: "Deemphasize"; }
                            
                            PK.CheckBox {
                                id: deemphasizeBox
                                objectName: 'deemphasizeBox'
                                checkState: personModel.deemphasize
                                onClicked: personModel.deemphasize = checkState
                            }

                            PK.Button {
                                id: resetDeemphasizeButton
                                objectName: 'resetDeemphasizeButton'
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.deemphasize || personModel.items.length > 1
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.deemphasize = undefined
                            }

                            // Size

                            PK.Label { text: "Size" }
                            
                            PK.ComboBox {
                                id: layerSizeBox
                                model: util.PERSON_SIZE_NAMES
                                currentIndex: personModel.sizeIndex
                                onCurrentIndexChanged: personModel.sizeIndex = currentIndex
                            }
                            
                            PK.Button {
                                id: resetSizeButton
                                objectName: 'resetSizeButton'
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.sizeIndex != -1 || personModel.items.length > 1
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.sizeIndex = undefined
                            }
                            
                            // Position

                            PK.Label { text: "Position" }
                            
                            PK.Label {
                                id: positionBox
                                text: formatPos(personModel.itemPos)

                                function formatPos(pos) {
                                    return '(' + pos.x.toFixed(0) + ', ' + pos.y.toFixed(0) + ')';
                                }
                            }
                            
                            PK.Button {
                                id: resetItemPosButton
                                objectName: 'resetItemPosButton'
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.isItemPosSetInCurrentLayer
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.itemPos = undefined
                            }
                            
                            // Big Font

                            PK.Label { text: "Big Font" }
                            
                            PK.CheckBox {
                                id: layerBigFontBox
                                objectName: 'layerBigFontBox'
                                checkState: personModel.bigFont
                                onClicked: personModel.bigFont = checkState
                            }

                            PK.Button {
                                id: resetBigFontButton
                                objectName: 'resetBigFontButton'
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.bigFont || personModel.items.length > 1
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.bigFont = undefined
                            }

                            // Hide Details

                            PK.Label { text: "Hide Details" }
                            
                            PK.CheckBox {
                                id: layerHideDetailsBox
                                objectName: 'layerHideDetailsBox'
                                checkState: personModel.hideDetails
                                onClicked: personModel.hideDetails = checkState
                            }

                            PK.Button {
                                id: resetHideDetailsButton
                                objectName: 'resetHideDetailsButton'
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.hideDetails || personModel.items.length > 1
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.hideDetails = undefined
                            }

                        }
                    }
                    PK.GroupBox {
                        title: "Diagram views this person is added to"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        enabled: !root.isReadOnly
                        padding: 1
                        ColumnLayout {
                            anchors.fill: parent
                            PK.ItemLayerList {
                                id: layerList
                                objectName: 'layerList'
                                model: LayerItemLayersModel {
                                    objectName: 'personProps_layerList'
                                    scene: sceneModel.scene
                                    items: personModel.items ? personModel.items : []
                                }
                                Layout.fillHeight: true
                                Layout.fillWidth: true
                                Layout.minimumHeight: 10
                            }
                        }
                    }
                }
            }
        }
    }
}
