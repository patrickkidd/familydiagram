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

    property var peopleListContentItem: peoplePicker.listView.contentItem;

    // Keys.onPressed: {
    //     if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
    //         done()
    //     }
    // }

    // who
    property var peopleModel: peoplePicker.model
    // what
    property var kind: kindBox.valueForIndex(kindBox.currentIndex);
    property var description: descriptionEdit.text
    property var anxiety: anxietyBox.value
    property var functioning: functioningBox.value
    property var symptom: symptomBox.value
    // where
    property var location: locationEdit.text
    // when
    property var isDateRange: isDateRangeBox.checked
    property var startDateTime: startDatePicker.dateTime
    property var startDateUnsure: startDatePicker.unsure
    property var endDateTime: endDatePicker.dateTime
    property var endDateUnsure: endDatePicker.unsure
    property var nodal: nodalBox.checked

    onKindChanged: {
        print('AddAnythingDialog.onKindChanged: ' + kind)
    }

    property var dirty: false;

    function clear() {
        peoplePicker.clear()
        kindBox.clear()
        startDatePicker.clear()
        endDatePicker.clear()
        isDateRangeBox.checked = false
        descriptionEdit.clear()
        locationEdit.clear()
        anxietyBox.clear()
        functioningBox.clear()
        symptomBox.clear()
        nodalBox.clear()

        root.dirty = false;
    }

    function currentTab() { return 0 }
    function setCurrentTab(tab) {}

    header: PK.ToolBar {
        PK.ToolButton {
            id: submitButton
            objectName: 'AddEverything_submitButton'
            text: 'Add'
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: {
                print('AddEverything_submitButton.onClicked')
                done()
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

                        PK.Text {
                            id: peopleLabel
                            objectName: "peopleLabel"
                            text: "People"
                        }

                        PK.PeoplePicker {
                            id: peoplePicker
                            objectName: "peoplePicker"
                            Layout.fillHeight: true
                            Layout.maximumWidth: util.QML_FIELD_WIDTH
                            Layout.minimumWidth: util.QML_FIELD_WIDTH
                            Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                            // // KeyNavigation.tab: dateButtons.textInput
                            Connections {
                                target: root
                                function onSceneModelChanged() {
                                    peoplePicker.scenePeopleModel = sceneModel.peopleModel
                                }
                            }
                        }

                        PK.FormDivider {}

                        PK.Text { id: descriptionLabel; objectName: "descriptionLabel"; text: "Description" }

                        PK.TextField {
                            id: descriptionEdit
                            objectName: "descriptionEdit"
                            text: root.description
                            Layout.maximumWidth: util.QML_FIELD_WIDTH
                            Layout.minimumWidth: util.QML_FIELD_WIDTH
                            KeyNavigation.tab: kindBox
                            function clear() { text = '' }
                            // Keys.onPressed: {
                            //     if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
                            //         done()
                            //     }
                            // }
                        }

                        PK.Text { id: kindLabel; objectName: "kindLabel"; text: "Relationship" }

                        RowLayout {
                            Layout.fillWidth: true
                            PK.ComboBox {
                                id: kindBox
                                objectName: "kindBox"
                                Layout.maximumWidth: util.QML_FIELD_WIDTH
                                Layout.minimumWidth: util.QML_FIELD_WIDTH
                                model: Object.keys(util.EventKinds)

                                    // "Individual - Born",
                                    // "Individual - Adopted",
                                    // "Individual - Deceased",
                                    // "Individual - Cutoff",
                                    // "Pair-Bond - Bonded",
                                    // "Pair-Bond - Married",
                                    // "Pair-Bond - Separated",
                                    // "Pair-Bond - Divorced",
                                    // "Pair-Bond - Moved",
                                    // "Dyad - Distance",
                                    // "Dyad - Conflict",
                                    // "Dyad - Reciprocity",
                                    // "Dyad - Projection",
                                    // "Dyad - Inside",
                                    // "Dyad - Outside",
                                    // "Dyad - Toward",
                                    // "Dyad - Away",
                                    // "Dyad - Defined-Self",
                                    // "Custom",
                                // ]
                                KeyNavigation.tab: startDateButtons
                                function clear() { currentIndex = -1 }
                                function valueForIndex(index) {
                                    if(index >= 0)
                                        return model[index]
                                    else
                                        return ''
                                }
                            }
                        }

                        PK.FormDivider {}

                        PK.Text { id: startDateTimeLabel; objectName: "startDateTimeLabel"; text: root.isDateRange ? "Began" : "When" }

                        PK.DatePickerButtons {
                            id: startDateButtons
                            objectName: 'startDateButtons'
                            datePicker: startDatePicker
                            timePicker: startTimePicker
                            dateTime: root.startDateTime
                            showInspectButton: true
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

                        PK.Text { id: endDateTimeLabel; objectName: "endDateTimeLabel"; text: "Ended"; visible: root.isDateRange }

                        PK.DatePickerButtons {
                            id: endDateButtons
                            objectName: 'endDateButtons'
                            datePicker: endDatePicker
                            timePicker: endTimePicker
                            dateTime: root.endDateTime                            
                            showInspectButton: true
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
                            id: isDateRangeBox
                            objectName: 'isDateRangeBox'
                            text: "Is Date Range"                            
                            enabled: sceneModel ? !sceneModel.readOnly : true
                            Layout.fillWidth: true
                            onCheckedChanged: {
                                if(root.isDateRange != checked) {
                                    root.isDateRange = checked
                                }
                            }
                        }

                        PK.Text { id: locationLabel; objectName: "locationLabel"; text: "Location" }

                        PK.TextField {
                            id: locationEdit
                            objectName: "locationEdit"
                            text: root.location
                            Layout.maximumWidth: util.QML_FIELD_WIDTH
                            Layout.minimumWidth: util.QML_FIELD_WIDTH
                            // KeyNavigation.tab: nodalBox
                            function clear() { text = '' }
                            // Keys.onPressed: {
                            //     if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
                            //         done()
                            //     }
                            // }
                        }

                        PK.FormDivider {}
                        
                        PK.Text { id: nodalLabel; text: "Nodal" }

                        PK.CheckBox {
                            id: nodalBox
                            objectName: "nodalBox"
                            KeyNavigation.tab: anxietyBox
                            function clear() { checked = false }
                        }

                        PK.Text { text: "Anxiety" }

                        PK.VariableBox { id: anxietyBox }

                        PK.Text { text: "Functioning" }

                        PK.VariableBox { id: functioningBox }

                        PK.Text { text: "Symptom" }

                        PK.VariableBox { id: symptomBox }
                    }
                }
            }
        }       

    }            

}

