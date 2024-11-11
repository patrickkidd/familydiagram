import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import "." 1.0 as PK
import PK.Models 1.0


Page {
    
    id: root
    objectName: 'EventProperties'

    signal done
    signal submit
    signal cancel

    property int margin: util.QML_MARGINS
    property var focusResetter: eventPage
    property bool canInspect: false
    property int itemMode: -1 // for add dlg    
    property var eventModel: EventPropertiesModel {
        scene: sceneModel ? sceneModel.scene : undefined
        onItemsChanged: {
            if(items.length == 0) {
                focusResetter.forceActiveFocus()
            }
        }
    }

    function setCurrentTab(tab) {
        var index = 0
        if(tab == 'item')
            index = 0
        else if(tab == 'notes')
            index = 1
        else if(tab == 'meta')
            index = 3
        tabBar.setCurrentIndex(index)
    }

    function currentTab() {
        return {
            0: 'item',
            1: 'notes',
            3: 'meta'
        }[tabBar.currentIndex]
    }
    
    Keys.onPressed: {
        if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
            submit()
        }
    }
    KeyNavigation.tab: nameBox

    header: PK.ToolBar {
        PK.ToolButton {
            id: doneButton
            objectName: 'event_doneButton'
            text: eventModel.addMode ? 'Add' : 'Done'
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: done()
        }
        PK.Label {
            text: eventModel.editText
            anchors.centerIn: parent
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            width: (doneButton.x) - (cancelButton.x + cancelButton.width) - root.margin * 2
            font.family: util.FONT_FAMILY_TITLE
            font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
        }
        PK.ToolButton {
            id: cancelButton
            objectName: 'cancelButton'
            text: 'Cancel'
            visible: eventModel.addMode
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: cancel()
        }
    }

    background: Rectangle { color: util.QML_WINDOW_BG; anchors.fill: parent }

    footer: PK.TabBar {
        id: tabBar
        objectName: "tabBar"
        currentIndex: stack.currentIndex
        PK.TabButton { text: "Event" }
        PK.TabButton { text: "Notes" }
        PK.TabButton { text: "Variables" }
        PK.TabButton { text: "Tags" }
    }
    
    StackLayout {

        id: stack
        objectName: "stack"
        currentIndex: tabBar.currentIndex
        anchors.fill: parent
        enabled: sceneModel ? !sceneModel.readOnly : false

        Flickable {
            id: eventPage
            contentWidth: width
            contentHeight: eventPageInner.childrenRect.height + root.margin * 2

            MouseArea {
                width: parent.width
                height: parent.height
                onClicked: parent.forceActiveFocus()
            }
            
            Rectangle {
                id: eventPageInner                
                anchors.fill: parent
                anchors.margins: margin
                color: 'transparent'

                ColumnLayout { // necessary to expand DatePicker

                    width: parent.width

                    GridLayout {
                        id: mainGrid
                        columns: 2
                        columnSpacing: util.QML_MARGINS / 2

                        // a hack because the property bindings weren't working...
                        property bool isWritable: false
                        function updateWritable() {
                             this.isWritable = (sceneModel ? !sceneModel.readOnly : false) && eventModel.numWritable > 0
                        }
                        Connections {
                            target: eventModel
                            function onNumWritableChanged() { mainGrid.updateWritable() }
                        }

                        Connections {
                            target: sceneModel
                            function onReadOnlyChanged() { mainGrid.updateWritable() }
                        }
                        
                        PK.Text {
                            text: {
                                if(eventModel.parentIsPerson && !eventModel.parentIsMarriage && !eventModel.parentIsEmotion)
                                    "Person"
                                else if(eventModel.parentIsMarriage && !eventModel.parentIsPerson && !eventModel.parentIsEmotion)
                                    "Pair-Bond"
                                else if(eventModel.parentIsEmotion && !eventModel.parentIsMarriage && !eventModel.parentIsPerson)
                                    "Symbol"
                                else
                                    "Item"
                            }
                        }
                        
                        RowLayout {
                            PK.ComboBox {
                                id: nameBox
                                objectName: "nameBox"
                                visible: !eventModel.parentIsMarriage && !eventModel.parentIsEmotion
                                model: peopleModel
                                textRole: 'name'
                                currentIndex: {
                                    model ? model.resetter : undefined
                                    model ? model.rowForId(eventModel.parentId) : -1
                                }
                                enabled: mainGrid.isWritable
                                Layout.maximumWidth: util.QML_FIELD_WIDTH
                                Layout.minimumWidth: util.QML_FIELD_WIDTH
                                KeyNavigation.tab: dateButtons.firstTabItem
                                onCurrentIndexChanged: eventModel.parentId = model.idForRow(currentIndex)
                            }
                            PK.ComboBox {
                                objectName: "readOnlyNameBox"
                                visible: !nameBox.visible
                                enabled: !visible
                                currentIndex: visible ? 0 : -1
                                model: [eventModel.parentName]
                                Layout.maximumWidth: util.QML_FIELD_WIDTH
                                Layout.minimumWidth: util.QML_FIELD_WIDTH
                            }
                            PK.Button {
                                id: editParentButton
                                objectName: "editParentButton"
                                enabled: ! eventModel.addMode
                                source: '../../details-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                opacity: enabled ? .5 : 0
                                Layout.leftMargin: 2
                                onClicked: sceneModel.inspectItem(eventModel.parentId)
                                Behavior on opacity {
                                    NumberAnimation { duration: util.ANIM_DURATION_MS / 3; easing.type: Easing.InOutQuad }
                                }
                            }
                        }

                        PK.Text { text: "When" }
                        
                        PK.DatePickerButtons {
                            id: dateButtons
                            objectName: "dateButtons"
                            dateTime: eventModel.dateTime
                            datePicker: eventDatePicker
                            timePicker: eventTimePicker
                            unsure: eventModel.unsure
                            enabled: sceneModel ? ! sceneModel.readOnly : true
                            // hideReset: true
                            backTabItem: nameBox
                            tabItem: descriptionEdit
                            Layout.preferredHeight: implicitHeight - 10
                            onDateTimeChanged: eventModel.dateTime = dateTime
                            onUnsureChanged: eventModel.unsure = unsure
                            Connections {
                                target: eventModel
                                function onDateTimeChanged() { dateButtons.dateTime = eventModel.dateTime }
                                function onUnsureChanged() { dateButtons.unsure = eventModel.unsure }
                            }
                        }

                        PK.DatePicker {
                            id: eventDatePicker
                            objectName: "eventDatePicker"
                            dateTime: eventModel.dateTime
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            onDateTimeChanged: eventModel.dateTime = dateTime
                            Connections {
                                target: eventModel
                                function onDateTimeChanged() { eventDatePicker.dateTime = eventModel.dateTime }
                            }
                        }

                        PK.TimePicker {
                            id: eventTimePicker
                            objectName: "eventTimePicker"
                            dateTime: eventModel.dateTime
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            onDateTimeChanged: eventModel.dateTime = dateTime
                            Connections {
                                target: eventModel
                                function onDateTimeChanged() { eventTimePicker.dateTime = eventModel.dateTime }
                            }
                        }

                        PK.Text { text: "Description" }

                        PK.TextField {
                            id: descriptionEdit
                            objectName: "descriptionEdit"
                            text: eventModel.description
                            enabled: mainGrid.isWritable
                            readOnly: eventModel.parentIsMarriage && eventModel.uniqueId
                            Layout.maximumWidth: util.QML_FIELD_WIDTH
                            Layout.minimumWidth: util.QML_FIELD_WIDTH
                            KeyNavigation.tab: locationEdit
                            onEditingFinished: eventModel.description = (text ? text : undefined)
                        }

                        PK.Text { text: "Location" }

                        PK.TextField {
                            id: locationEdit
                            objectName: "locationEdit"
                            text: eventModel.location
                            Layout.maximumWidth: util.QML_FIELD_WIDTH
                            Layout.minimumWidth: util.QML_FIELD_WIDTH
                            KeyNavigation.tab: nodalBox
                            onEditingFinished: {
                                eventModel.location = (text ? text : undefined)
                            }
                            Keys.onPressed: {
                                if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
                                    done()
                                }
                            }
                        }

                        PK.Text { text: "Nodal" }

                        PK.CheckBox {
                            id: nodalBox
                            objectName: "nodalBox"
                            checkState: eventModel.nodal
                            KeyNavigation.tab: uniqueIdBox
                            onCheckStateChanged: eventModel.nodal = checkState
                        }

                        PK.Text { text: "On Diagram"; visible: eventModel.parentIsMarriage }

                        PK.CheckBox {
                            id: includeOnDiagramBox
                            objectName: "includeOnDiagramBox"
                            enabled: eventModel.uniqueId ? false : true
                            visible: eventModel.parentIsMarriage
                            checkState: eventModel.uniqueId ? Qt.Checked : eventModel.includeOnDiagram 
                            KeyNavigation.tab: nameBox
                            onCheckStateChanged: if(!eventModel.uniqueId) eventModel.includeOnDiagram = checkState
                        }                        

                        PK.FormDivider {
                            visible: eventModel.parentIsMarriage
                            Layout.columnSpan: 2
                        }

                        PK.Text { text: "Kind"; visible: eventModel.parentIsMarriage }

                        RowLayout {
                            // Layout.fillWidth: true
                            visible: eventModel.parentIsMarriage
                            PK.ComboBox {
                                id: uniqueIdBox
                                objectName: "uniqueIdBox"
                                model: ['Bonded', 'Married', 'Separated', 'Divorced', 'Moved']
                                currentIndex: ['bonded', 'married', 'separated', 'divorced', 'moved'].indexOf(eventModel.uniqueId)
                                KeyNavigation.tab: resetUniqueIdButton
                                onCurrentIndexChanged: {
                                    if(!eventModel.parentIsMarriage)
                                        return // Marriage is currently the only Item that uses uniqueId
                                    if(currentIndex == -1)
                                        eventModel.uniqueId = undefined
                                    else if(currentIndex == 0)
                                        eventModel.uniqueId = 'bonded'
                                    else if(currentIndex == 1)
                                        eventModel.uniqueId = 'married'
                                    else if(currentIndex == 2)
                                        eventModel.uniqueId = 'separated'
                                    else if(currentIndex == 3)
                                        eventModel.uniqueId = 'divorced'
                                    else if(currentIndex == 4)
                                        eventModel.uniqueId = 'moved'
                                }
                            }
                            Button {
                                id: resetUniqueIdButton
                                text: 'Reset'
                                objectName: 'resetUniqueIdButton'
                                opacity: uniqueIdBox.currentIndex > -1 ? 1 : 0
                                enabled: opacity > 0
                                KeyNavigation.tab: includeOnDiagramBox
                                onClicked: eventModel.uniqueId = undefined
                                Behavior on opacity {
                                    NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
                                }
                            }
                        }


                        PK.FormDivider { Layout.columnSpan: 2}

                        PK.Text {
                            text: util.EVENT_PROPS_HELP_TEXT
                            wrapMode: Text.WordWrap
                            font.pixelSize: util.HELP_FONT_SIZE
                            Layout.fillWidth: true
                            Layout.columnSpan: 2
                        }
                    }
                }
            }            
        }

        Flickable {
            id: notesEditFlickable
            contentX: 0
            contentHeight: Math.max(eventNotesEdit.paintedHeight + 50, height) // allow scrolling
            Layout.fillHeight: true
            Layout.fillWidth: true

            PK.TextEdit {
                id: eventNotesEdit
                objectName: "eventNotesEdit"
                text: eventModel.notes
                padding: margin
                width: parent.width
                wrapMode: TextEdit.Wrap
                anchors.fill: parent
                onEditingFinished: eventModel.notes = (text ? text : undefined)
            }
        }

        TableView {
            id: variablesTable
            property int currentIndex: -1
            model: EventVariablesModel {
                scene: sceneModel ? sceneModel.scene : undefined
                items: eventModel.items
            }
            property var selectionModel: ItemSelectionModel {

                property int currentRow: -1
                property bool resetter: false
                model: variablesTable.model
                onSelectionChanged: resetter = !resetter
            }

            Layout.fillHeight: true
            Layout.fillWidth: true
            columnWidthProvider: function() {
                var ret = contentWidth > 0 ? contentWidth / 2 : 50
                return ret
            }
            onWidthChanged: {
                contentWidth = contentItem.childrenRect.width > width ? contentItem.childrenRect.width : width
                if(rows > 0 && columns > 0)
                    forceLayout()
            }
            delegate: Rectangle {
                property int thisRow: row
                property int thisColumn: column
                implicitHeight: util.QML_ITEM_HEIGHT
                clip: true
                color: row == variablesTable.currentIndex ? util.QML_HIGHLIGHT_COLOR : 'transparent'
                property bool shouldEdit: false
                property bool editMode: shouldEdit && selected
                property bool editable: flags & Qt.ItemIsEditable
                property bool selected: {
                    variablesTable.selectionModel.resetter
                    util.isRowSelected(variablesTable.selectionModel, thisRow)
                }
                onSelectedChanged: {
                    if(selected == false && shouldEdit) {
                        textEdit.onEditingFinished()
                        shouldEdit = false // disable edit mode when deselected
                    }
                }
                Rectangle { // border-bottom
                    y: parent.height - 1
                    width: parent.width
                    height: 1
                    color: 'lightGrey'
                    visible: index >= 0
                }
                Rectangle { // border-left
                    width: 1
                    height: parent.height
                    visible: (row > 0 && column > 0) || (row == 0 && column == 1)
                    color: 'lightGrey'
                }
                PK.TextInput {
                    id: textEdit
                    text: display == undefined ? '' : display
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width
                    padding: margin
                    readOnly: !editMode
                    selectByMouse: !readOnly
                    onTextChanged: {
                        if(!editMode) {
                            cursorPosition = 0
                        }
                    }
                    onReadOnlyChanged: {
                        if(!readOnly && cursorPosition != 0) {
                            cursorPosition = 0
                        }
                    }
                    onCursorPositionChanged: {
                        if(!editMode && cursorPosition != 0) {
                            cursorPosition = 0
                        }
                    }
                    onEditingFinished: {
                        if(editMode) {
                            shouldEdit = false
                            display = (text ? text : undefined)
                        }
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: !editMode
                    onClicked: { 
                        variablesTable.currentIndex = thisRow
                        variablesTable.selectionModel.currentRow = thisRow
                        variablesTable.selectionModel.select(variablesTable.model.index(thisRow, 0), ItemSelectionModel.ClearAndSelect | ItemSelectionModel.Rows)
                    }
                    onDoubleClicked: {
                        if(flags & Qt.ItemIsEditable) {
                            shouldEdit = true
                            textEdit.forceActiveFocus()
                        }
                    }
                }
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
                        title: "Tags Added to this Event(s)"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        padding: 1
                        ColumnLayout {
                            anchors.fill: parent
                            PK.TagEdit {
                                id: tagsList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                model: TagsModel {
                                    objectName: "EventProperties_tagsModel"
                                    scene: sceneModel ? sceneModel.scene : undefined
                                    items: eventModel.items
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
}
