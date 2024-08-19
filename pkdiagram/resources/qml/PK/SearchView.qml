import QtQuick 2.12
import QtQuick.Layouts 1.12
import QtQuick.Controls 2.12
import "." 1.0 as PK
import PK.Models 1.0



Page {

    id: root

    signal done

    property string headerLabel: 'Timeline Search';

    function onShown() {
        Edit.forceActiveFocus()
    }

    property int margin: util.QML_MARGINS
    property bool canInspect: false

    property var model: sceneModel.searchModel

    // Read-Only: Just here to have reliable signals to connect to
    property var description: model ? model.description : ''
    property var startDateTime: model ? model.startDateTime : new Date
    property var endDateTime: model ? model.endDateTime : new Date
    property var loggedStartDateTime: model ? model.loggedStartDateTime : new Date
    property var loggedEndDateTime: model ? model.loggedEndDateTime : new Date
    property var tags: model ? model.tags : []
    property var nodal: model ? model.nodal : false
    property var hideRelationships: model ? model.hideRelationships : false

    Keys.enabled: true
    Keys.onPressed: {
        if(event.key == Qt.Key_Enter || event.key == Qt.Key_Return) {
            root.done()
        }
    }

    Rectangle {
        color: util.QML_WINDOW_BG
        anchors.fill: parent
    }

    StackLayout {

        id: stack
        anchors.fill: parent

        Flickable {
            id: propsPage
            flickableDirection: Flickable.VerticalFlick
            contentWidth: width
            contentHeight: contentArea.childrenRect.height
            clip: true

            Rectangle {
                color: util.QML_WINDOW_BG
                anchors.fill: parent
            }

            MouseArea {
                width: propsPage.width
                height: propsPage.height
                onClicked: parent.forceActiveFocus()
            }
            
            ColumnLayout {

                id: contentArea
                x: margin
                y: margin
                width: parent.width - margin * 2

                GridLayout {

                    id: grid
                    columns: 2
                    Layout.fillWidth: true
                    width: contentArea.width

                    PK.Text { text: "Description" }

                    PK.TextField {
                        id: descriptionEdit
                        objectName: 'descriptionEdit'
                        Layout.fillWidth: true
                        Layout.bottomMargin: 5
                        onTextChanged: if(model.description != text) model.description = text
                        KeyNavigation.tab: startDateButtons.firstTabItem
                        Connections {
                            target: root
                            function onDescriptionChanged() { if(model) descriptionEdit.text = model.description }
                        }
                    }

                    PK.Text { text: "Start Date" }

                    PK.DatePickerButtons {
                        id: startDateButtons
                        objectName:'startDateButtons'
                        datePicker: startDatePicker
                        timePicker: startTimePicker
                        dateTime: model ? root.startDateTime : undefined
                        hideUnsure: true
                        onDateTimeChanged: if(model && model.startDateTime != dateTime) model.startDateTime = dateTime
                        backTabItem: descriptionEdit
                        tabItem: endDateButtons.firstTabItem
                        Connections {
                            target: root
                            function onStartDateTimeChanged() { startDateButtons.dateTime = root.startDateTime }
                        }
                    }

                    PK.DatePicker {
                        id: startDatePicker
                        objectName: 'startDatePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(model && model.startDateTime != dateTime) model.startDateTime = dateTime
                        Connections {
                            target: root
                            function onStartDateTimeChanged() { startDatePicker.dateTime = root.startDateTime }
                        }
                    }

                    PK.TimePicker {
                        id: startTimePicker
                        objectName: 'startTimePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(model && model.startDateTime != dateTime) model.startDateTime = dateTime
                        Connections {
                            target: root
                            function onStartDateTimeChanged() { startTimePicker.dateTime = root.startDateTime }
                        }
                    }

                    PK.Text { text: "End Date" }

                    PK.DatePickerButtons {
                        id: endDateButtons
                        objectName:'endDateButtons'
                        datePicker: endDatePicker
                        timePicker: endTimePicker
                        dateTime: model.endDateTime
                        hideUnsure: true
                        onDateTimeChanged: if(model && model.endDateTime != dateTime) model.endDateTime = dateTime
                        backTabItem: startDateButtons.lastTabItem
                        tabItem: loggedStartDateTimeButtons.firstTabItem
                        Connections {
                            target: root
                            function onEndDateTimeChanged() { endDateButtons.dateTime = root.endDateTime }
                        }
                    }

                    PK.DatePicker {
                        id: endDatePicker
                        objectName: 'endDatePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(model && model.endDateTime != dateTime) model.endDateTime = dateTime
                        Connections {
                            target: root
                            function onEndDateTimeChanged() { endDatePicker.dateTime = root.endDateTime }
                        }
                    }

                    PK.TimePicker {
                        id: endTimePicker
                        objectName: 'endTimePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(model && model.endDateTime != dateTime) model.endDateTime = dateTime
                        Connections {
                            target: root
                            function onEndDateTimeChanged() { endTimePicker.dateTime = root.endDateTime }
                        }
                    }

                    PK.Text { text: "Logged Start Date" }

                    PK.DatePickerButtons {
                        id: loggedStartDateTimeButtons
                        objectName:'loggedStartDateTimeButtons'
                        datePicker: loggedStartDateDatePicker
                        timePicker: loggedStartDateTimePicker
                        dateTime: model.loggedStartDateTime
                        hideUnsure: true
                        onDateTimeChanged: if(model && model.loggedStartDateTime != dateTime) model.loggedStartDateTime = dateTime
                        backTabItem: endDateButtons.lastTabItem
                        tabItem: loggedEndDateTimeButtons.firstTabItem
                        Connections {
                            target: root
                            function onLoggedStartDateTimeChanged() { loggedStartDateTimeButtons.dateTime = root.loggedStartDateTime }
                        }
                    }

                    PK.DatePicker {
                        id: loggedStartDateDatePicker
                        objectName: 'loggedStartDateDatePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(model && model.loggedStartDateTime != dateTime) model.loggedStartDateTime = dateTime
                        Connections {
                            target: root
                            function onLoggedStartDateTimeChanged() { loggedStartDateDatePicker.dateTime = root.loggedStartDateTime }
                        }
                    }

                    PK.TimePicker {
                        id: loggedStartDateTimePicker
                        objectName: 'loggedStartDateTimePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(model && model.loggedStartDateTime != dateTime) model.loggedStartDateTime = dateTime
                        Connections {
                            target: root
                            function onLoggedStartDateTimeChanged() { loggedStartDateTimePicker.dateTime = root.loggedStartDateTime }
                        }
                    }                    

                    PK.Text { text: "Logged End Date" }

                    PK.DatePickerButtons {
                        id: loggedEndDateTimeButtons
                        objectName:'loggedEndDateTimeButtons'
                        datePicker: loggedEndDateDatePicker
                        timePicker: loggedEndDateTimePicker
                        dateTime: model.loggedEndDateTime
                        hideUnsure: true
                        onDateTimeChanged: if(model && model.loggedEndDateTime != dateTime) model.loggedEndDateTime = dateTime
                        backTabItem: loggedStartDateTimeButtons.lastTabItem
                        tabItem: nodalBox
                        Connections {
                            target: root
                            function onLoggedEndDateTimeChanged() { loggedEndDateTimeButtons.dateTime = root.loggedEndDateTime }
                        }
                    }

                    PK.DatePicker {
                        id: loggedEndDateDatePicker
                        objectName: 'loggedEndDateDatePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(model && model.loggedEndDateTime != dateTime) model.loggedEndDateTime = dateTime
                        Connections {
                            target: root
                            function onLoggedEndDateTimeChanged() { loggedEndDateDatePicker.dateTime = root.loggedEndDateTime }
                        }
                    }

                    PK.TimePicker {
                        id: loggedEndDateTimePicker
                        objectName: 'loggedEndDateTimePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(model && model.loggedEndDateTime != dateTime) model.loggedEndDateTime = dateTime
                        Connections {
                            target: root
                            function onLoggedEndDateTimeChanged() { loggedEndDateTimePicker.dateTime = root.loggedEndDateTime }
                        }
                    }

                    PK.Text { text: "Nodal" }

                    PK.CheckBox {
                        id: nodalBox
                        objectName: 'nodalBox'
                        checked: model ? model.nodal : false                        
                        KeyNavigation.tab: hideRelationshipsBox
                        KeyNavigation.backtab: loggedEndDateTimeButtons.lastTabItem
                        onCheckedChanged: if(model && model.nodal != checked) model.nodal = checked
                    }

                    PK.Text { text: "Hide Relationships" }

                    PK.CheckBox {
                        id: hideRelationshipsBox
                        objectName: 'hideRelationshipsBox'
                        checked: model ? model.hideRelationships : false
                        onCheckedChanged: if(model && model.hideRelationships != checked) model.hideRelationships = checked
                    }

                    /* PK.Text { text: "Hide Brackets" } */

                    /* PK.CheckBox { */
                    /*     id: hideBracketsBox */
                    /*     objectName: 'hideBracketsBox' */
                    /*     /\* checked: sceneModel.hideDateBuddies *\/ */
                    /*     /\* onCheckedChanged: sceneModel.hideDateBuddies = checked *\/ */
                    /* } */

                    PK.GroupBox {

                        id: tagsAndLayersBox
                        objectName: 'tagsAndLayersBox'

                        padding: 0
                        Layout.fillWidth: true
                        Layout.topMargin: util.QML_MARGINS / 2
                        Layout.columnSpan: 2
                        visible: sceneModel.isInEditorMode

                        ColumnLayout {
                            id: tagsAndLayersCL

                            spacing: 0
                            anchors.fill: parent                            

                            PK.TabBar {
                                id: tagsAndLayersTabs
                                currentIndex: tagsAndLayersStack.currentIndex
                                Layout.fillWidth: true
                                Layout.margins: 1

                                PK.TabButton { text: "Event Tags" }
                                PK.TabButton { text: "Diagram Views" }
                            }

                            StackLayout {

                                id: tagsAndLayersStack

                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                currentIndex: tagsAndLayersTabs.currentIndex

                                ColumnLayout {

                                    PK.Text {
                                        text: "The timeline will only show events that have the tags selected in this list. If no tags are selected, then all events are shown on the timeline.\nNOTE: The graphical timeline will show tag rows from bottom up in the order they are clicked.";
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: util.HELP_FONT_SIZE
                                        Layout.fillWidth: true
                                        Layout.margins: util.QML_MARGINS / 3
                                        Layout.columnSpan: 2 
                                    }

                                    Rectangle { // border-top
                                        height: 1
                                        color: util.QML_ITEM_BORDER_COLOR
                                        Layout.fillWidth: true
                                    }

                                    PK.TagEdit {
                                        id: tagsList
                                        objectName: root.objectName + 'tagsList'
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Layout.margins: 1
                                        Layout.minimumHeight: 200
                                        model: TagsModel {
                                            id: tagsModel
                                            objectName: 'SearchView_tagsModel'
                                            scene: sceneModel.scene
                                            items: [sceneModel.scene]
                                        }
                                    }
                                }

                                ColumnLayout {

                                    PK.Text {
                                        text: "Diagram Views are like powerpoint slides that focus on a sub-set of family members, with alterations like position, color, deemphasize. Diagram views can also be annotated with text callouts, pencil strokes. They are for small tweaks to get a point across that do not affect the data of the family. Expand the left edge of this drawer further to the left to show the 'Store Geometry' column." + (sceneLayerView.responsive1 ? "\n\n'Store Goemetry' will store the positions for items in that view, and rearrange the diagram to reflect those positions when you activate the view." : '');
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: util.HELP_FONT_SIZE
                                        Layout.fillWidth: true
                                        Layout.margins: util.QML_MARGINS / 3
                                        Layout.columnSpan: 2 
                                    }

                                    Rectangle { // border-top
                                        height: 1
                                        color: util.QML_ITEM_BORDER_COLOR
                                        Layout.fillWidth: true
                                    }

                                    PK.SceneLayerView {
                                        id: sceneLayerView
                                        objectName: root.objectName + '_sceneLayerView'
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Layout.margins: 1
                                        Layout.minimumHeight: 200
                                        model: SceneLayerModel {
                                            id: layerModel
                                            objectName: root.objectName + 'timelineSearch_layerModel'
                                            scene: sceneModel.scene
                                            items: sceneModel.scene ? [sceneModel.scene] : []
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Rectangle {
                    //     width: 1
                    //     Layout.columnSpan: 2
                    //     Layout.fillHeight: true
                    // }
                }
                Rectangle {
                    height: util.QML_ITEM_HEIGHT
                    width: parent.width
                    color: 'transparent'
                }
            }            

        }
    }
}
