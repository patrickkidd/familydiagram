import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import "./PK" 1.0 as PK
import PK.Models 1.0


Page {

    id: root
    objectName: 'AddAnythingDialog'

    signal done
    signal submit
    signal cancel

    property var sceneModel: null
    property int margin: util.QML_MARGINS
    property var focusResetter: addPage
    property bool canInspect: false

    Keys.onPressed: {
        if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
            submit()
        }
    }

    property var people: null; // [id]
    property var peopleToCreate: null; // [id]
    property var isDateRange: false;
    property var description: null;
    property var location: null;
    property var anxiety: null;
    property var functioning: null;
    property var symptom: null;
    property var customVariables: null; // { name: value }
    // when
    property var startDateTime: null;
    property var startDateUnsure: null;
    property var endDateTime: null;
    property var endDateUnsure: null;

    property var dirty: false;

    function clear() {
        root.people = []; // [id]
        root.peopleToCreate = []; // [id]
        root.startDateTime = null
        root.startDateUnsure = false
        root.endDateTime = null
        root.endDateUnsure = false
        root.isDateRange = false;
        root.description = null;
        root.location = null;
        root.anxiety = null;
        root.functioning = null;
        root.symptom = null;
        root.customVariables = null; // { name: value }

        self.dirty = false;
    }

    function setCurrentTab(tab) {}

    header: PK.ToolBar {
        PK.ToolButton {
            id: addButton
            objectName: 'AddEverything_addButton'
            text: 'Add'
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: done()
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
            id: cancelButton
            objectName: 'cancelButton'
            text: 'Cancel'
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: cancel()
        }
    }

    background: Rectangle { color: util.QML_WINDOW_BG; anchors.fill: parent }

    Flickable {
        id: addPage
        contentWidth: width
        contentHeight: addPageInner.childrenRect.height + root.margin * 2

        MouseArea {
            width: parent.width
            height: parent.height
            onClicked: parent.forceActiveFocus()
        }

        Rectangle {
            id: addPageInner
            anchors.fill: parent
            anchors.margins: margin
            color: 'transparent'

            ColumnLayout { // necessary to expand anything vertically

                width: parent.width

                GridLayout {
                    id: mainGrid
                    columns: 2
                    columnSpacing: util.QML_MARGINS / 2

                    // PK.Text { text: "People" }
                    
                    // PK.PeoplePicker {
                    //     id: peopleBox
                    //     objectName: "peoplePicker"
                    //     model: root.people
                    //     height: 400
                    //     Layout.columnSpan: 2
                    //     // KeyNavigation.tab: dateButtons.textInput
                    //     // onCurrentIndexChanged: eventModel.parentId = model.idForRow(currentIndex)
                    // }

                    // Rectangle { width: 1; height: 1; color: 'transparent'; Layout.columnSpan: 2 }

                    PK.Text { text: root.isDateRange ? "Began" : "When" }

                    PK.DatePickerButtons {
                        id: startDateButtons
                        objectName: 'startDateButtons'
                        datePicker: startDatePicker
                        timePicker: startTimePicker
                        dateTime: root.startDateTime
                        unsure: root.startDateUnsure
                        showInspectButton: true
                        enabled: ! root.isReadOnly
                        Layout.preferredHeight: implicitHeight - 10
                        KeyNavigation.tab: endDateButtons.textInput
                        onDateTimeChanged: root.startDateTime = dateTime
                        onUnsureChanged: root.startDateUnsure = unsure
                        Connections {
                            target: root
                            function onStartDateTimeChanged() { startDateButtons.dateTime = root.startDateTime }
                            function onStartDateUnsureChanged() { startDateButtons.unsure = root.startDateUnsure }
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
                            function onStartDateTimeChanged() { startDatePicker.dateTime = root.startDateTime }
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
                            function onStartDateTimeChanged() { startTimePicker.dateTime = root.startDateTime }
                        }                            
                    }

                    PK.Text { text: "Ended"; visible: root.isDateRange }

                    PK.DatePickerButtons {
                        id: endDateButtons
                        objectName: 'endDateButtons'
                        datePicker: endDatePicker
                        timePicker: endTimePicker
                        dateTime: root.endDateTime
                        unsure: root.endDateUnsure
                        showInspectButton: true
                        enabled: ! root.isReadOnly
                        visible: root.isDateRange
                        Layout.preferredHeight: implicitHeight - 10
                        // KeyNavigation.tab: intensityBox
                        onDateTimeChanged: root.endDateTime = dateTime
                        onUnsureChanged: root.endDateUnsure = unsure
                        Connections {
                            target: root
                            function onEndDateTimeChanged() { endDateButtons.dateTime = root.endDateTime }
                            function onEndDateUnsureChanged() { startDateButtons.unsure = root.endDateUnsure }
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
                            function onEndDateTimeChanged() { endDatePicker.dateTime = root.endDateTime }
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
                            function onEndDateTimeChanged() { endTimePicker.dateTime = root.endDateTime }
                        }
                    }

                    // Rectangle { width: 1; height: 1; color: 'transparent'; Layout.columnSpan: 1 }

                    // PK.CheckBox {
                    //     id: dateRangeBox
                    //     objectName: 'dateRangeBox'
                    //     text: "Is Date Range"
                    //     enabled: !sceneModel.readOnly
                    //     checked: root.isDateRange
                    //     Layout.fillWidth: true
                    //     onCheckedChanged: root.isDateRange = checked
                    // }

                    // Rectangle { width: 1; height: 1; color: 'transparent'; Layout.columnSpan: 2 }

                    // PK.Text { text: "Description" }

                    // PK.TextField {
                    //     id: descriptionEdit
                    //     objectName: "descriptionEdit"
                    //     text: eventModel.description
                    //     enabled: mainGrid.isWritable
                    //     readOnly: eventModel.parentIsMarriage && eventModel.uniqueId
                    //     Layout.maximumWidth: util.QML_FIELD_WIDTH
                    //     Layout.minimumWidth: util.QML_FIELD_WIDTH
                    //     KeyNavigation.tab: locationEdit
                    //     onEditingFinished: eventModel.description = (text ? text : undefined)
                    // }

                    // PK.Text { text: "Location" }

                    // PK.TextField {
                    //     id: locationEdit
                    //     objectName: "locationEdit"
                    //     text: eventModel.location
                    //     Layout.maximumWidth: util.QML_FIELD_WIDTH
                    //     Layout.minimumWidth: util.QML_FIELD_WIDTH
                    //     KeyNavigation.tab: nodalBox
                    //     onEditingFinished: {
                    //         eventModel.location = (text ? text : undefined)
                    //     }
                    //     Keys.onPressed: {
                    //         if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
                    //             done()
                    //         }
                    //     }
                    // }

                    // PK.Text { text: "Kind"; visible: eventModel.parentIsMarriage }

                    // RowLayout {
                    //     // Layout.fillWidth: true
                    //     visible: eventModel.parentIsMarriage
                    //     PK.ComboBox {
                    //         id: uniqueIdBox
                    //         objectName: "uniqueIdBox"
                    //         model: ['Bonded', 'Married', 'Separated', 'Divorced', 'Moved']
                    //         currentIndex: ['bonded', 'married', 'separated', 'divorced', 'moved'].indexOf(eventModel.uniqueId)
                    //         KeyNavigation.tab: resetUniqueIdButton
                    //         onCurrentIndexChanged: {
                    //             if(!eventModel.parentIsMarriage)
                    //                 return // Marriage is currently the only Item that uses uniqueId
                    //             if(currentIndex == -1)
                    //                 eventModel.uniqueId = undefined
                    //             else if(currentIndex == 0)
                    //                 eventModel.uniqueId = 'bonded'
                    //             else if(currentIndex == 1)
                    //                 eventModel.uniqueId = 'married'
                    //             else if(currentIndex == 2)
                    //                 eventModel.uniqueId = 'separated'
                    //             else if(currentIndex == 3)
                    //                 eventModel.uniqueId = 'divorced'
                    //             else if(currentIndex == 4)
                    //                 eventModel.uniqueId = 'moved'
                    //         }
                    //     }
                    //     Button {
                    //         id: resetUniqueIdButton
                    //         text: 'Reset'
                    //         objectName: 'resetUniqueIdButton'
                    //         opacity: uniqueIdBox.currentIndex > -1 ? 1 : 0
                    //         enabled: opacity > 0
                    //         KeyNavigation.tab: includeOnDiagramBox
                    //         onClicked: eventModel.uniqueId = undefined
                    //         Behavior on opacity {
                    //             NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
                    //         }
                    //     }
                    // }

                    // Rectangle {
                    //     height: 1
                    //     color: util.QML_ITEM_BORDER_COLOR
                    //     Layout.fillWidth: true
                    //     Layout.columnSpan: 2
                    //     Layout.topMargin: margin
                    //     Layout.bottomMargin: margin
                    // }

                    // PK.Text {
                    //     text: util.EVENT_PROPS_HELP_TEXT
                    //     wrapMode: Text.WordWrap
                    //     font.pixelSize: util.HELP_FONT_SIZE
                    //     Layout.fillWidth: true
                    //     Layout.columnSpan: 2
                    // }

                    // PK.Text { text: "Nodal" }

                    // PK.CheckBox {
                    //     id: nodalBox
                    //     objectName: "nodalBox"
                    //     checkState: eventModel.nodal
                    //     KeyNavigation.tab: uniqueIdBox
                    //     onCheckStateChanged: eventModel.nodal = checkState
                    // }

                    // Rectangle {
                    //     height: 1
                    //     visible: eventModel.parentIsMarriage 
                    //     color: util.QML_ITEM_BORDER_COLOR
                    //     Layout.fillWidth: true
                    //     Layout.columnSpan: 2
                    //     Layout.topMargin: margin
                    //     Layout.bottomMargin: margin
                    // }


                }
            }
        }       

    }            

}

