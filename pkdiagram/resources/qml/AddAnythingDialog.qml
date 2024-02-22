import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import "./PK" 1.0 as PK
import PK.Models 1.0


PK.Drawer {

    id: root
    objectName: 'AddAnythingDialog'

    signal cancel

    property int margin: util.QML_MARGINS
    property var focusResetter: addPage
    property bool canInspect: false

    onSceneModelChanged: {
        peoplePicker.peopleModel = sceneModel.peopleModel
    }

    Keys.onPressed: {
        if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
            submit()
        }
    }

    property var peopleModel: ListModel {}
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
    property var startDateUnsure: false;
    property var endDateTime: null;
    property var endDateUnsure: false;
    property var nodal: false;

    property var dirty: false;

    function clear() {
        root.peopleModel.clear()
        root.peopleToCreate = []; // [id]
        root.startDateTime = null;
        root.startDateUnsure = false
        root.endDateTime = null;
        root.endDateUnsure = false
        root.isDateRange = false;
        root.description = null;
        root.location = null;
        root.anxiety = null;
        root.functioning = null;
        root.symptom = null;
        root.customVariables = null; // { name: value }
        root.nodal = false;

        root.dirty = false;
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

    StackLayout {

        id: stack
        objectName: 'stack'
        currentIndex: 0
        anchors.fill: parent


        Flickable {
            id: addPage
            contentWidth: width
            contentHeight: addPageInner.childrenRect.height + root.margin * 2

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

                        PK.Text { text: "People" }

                        PK.PeoplePicker {
                            id: peoplePicker
                            objectName: "peoplePicker"
                            model: root.peopleModel
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 150
                            Layout.maximumHeight: 150
                            // KeyNavigation.tab: dateButtons.textInput
                        }

                        PK.Text { text: "Kind" }

                        RowLayout {
                            // Layout.fillWidth: true
                            PK.ComboBox {
                                id: kindBox
                                objectName: "kindBox"
                                model: ListModel {
                                    ListElement { header: true; text: "Individual" }
                                    ListElement { text: "Born" }
                                    ListElement { text: "Adopted" }
                                    ListElement { text: "Deceased" }
                                    ListElement { text: "Cutoff" }
                                    ListElement { header: true; text: "Pair-Bond" }
                                    ListElement { text: "Bonded" }
                                    ListElement { text: "Married" }
                                    ListElement { text: "Separated" }
                                    ListElement { text: "Divorced" }
                                    ListElement { text: "Moved" }
                                    ListElement { header: true; text: "Dyadic" }
                                    ListElement { text: "Distance" }
                                    ListElement { text: "Conflict" }
                                    ListElement { text: "Reciprocity" }
                                    ListElement { text: "Projection" }
                                    ListElement { text: "Inside" }
                                    ListElement { text: "Outside" }
                                    ListElement { text: "Toward" }
                                    ListElement { text: "Away" }
                                    ListElement { text: "Defined-Self" }
                                }
                                KeyNavigation.tab: startDateButtons
                                delegate: Item {
                                    Rectangle {
                                        width: parent.width
                                        height: parent.height
                                        // color: model.header ? "#efefef" : util.itemBgColor(false, false, index % 2 == 1)

                                        Text {
                                            text: model.text
                                            font.bold: model.header
                                            color: model.header ? "#000" : "#333"
                                            anchors.verticalCenter: parent.verticalCenter
                                            anchors.left: parent.left
                                            anchors.leftMargin: 5
                                        }
                                    }

                                    // Prevent selection of headers
                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: model.type === "header"
                                        onClicked: {
                                            comboBox.currentIndex = -1; // Deselect
                                        }
                                    }                                    
                                }
                            }
                            // Button {
                            //     id: resetUniqueIdButton
                            //     text: 'Reset'
                            //     objectName: 'resetUniqueIdButton'
                            //     opacity: kindBox.currentIndex > -1 ? 1 : 0
                            //     enabled: opacity > 0
                            //     KeyNavigation.tab: includeOnDiagramBox
                            //     onClicked: eventModel.uniqueId = undefined
                            //     Behavior on opacity {
                            //         NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
                            //     }
                            // }
                        }

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
                            // KeyNavigation.tab: endDateButtons.textInput
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

                        Rectangle { width: 1; height: 1; color: 'transparent'; Layout.columnSpan: 1 }

                        PK.CheckBox {
                            id: dateRangeBox
                            objectName: 'dateRangeBox'
                            text: "Is Date Range"
                            
                            enabled: sceneModel ? !sceneModel.readOnly : true
                            checked: root.isDateRange
                            Layout.fillWidth: true
                            onCheckedChanged: if(root.isDateRange != checked) root.isDateRange = checked
                        }

                        PK.Text { text: "Description" }

                        PK.TextField {
                            id: descriptionEdit
                            objectName: "descriptionEdit"
                            text: root.description
                            Layout.maximumWidth: util.QML_FIELD_WIDTH
                            Layout.minimumWidth: util.QML_FIELD_WIDTH
                            KeyNavigation.tab: locationEdit
                            onEditingFinished: {
                                var newValue = (text ? text : undefined)
                                if(root.description != newValue)
                                    root.description = newValue
                            }
                        }

                        PK.Text { text: "Location" }

                        PK.TextField {
                            id: locationEdit
                            objectName: "locationEdit"
                            text: root.location
                            Layout.maximumWidth: util.QML_FIELD_WIDTH
                            Layout.minimumWidth: util.QML_FIELD_WIDTH
                            KeyNavigation.tab: nodalBox
                            onEditingFinished: {
                                var newValue = (text ? text : undefined)
                                if(root.location != newValue) {
                                    root.location = newValue;
                                }
                            }
                            Keys.onPressed: {
                                if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
                                    done()
                                }
                            }
                        }


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

                        PK.Text { text: "Nodal" }

                        PK.CheckBox {
                            id: nodalBox
                            objectName: "nodalBox"
                            checkState: root.nodal ? 1 : 0
                            KeyNavigation.tab: kindBox
                            onCheckStateChanged: { if(root.nodal = checkState) root.nodal = checkState }
                        }

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

}

