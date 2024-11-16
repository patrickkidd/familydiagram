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

    property alias tagsModel: tagsModel
    property alias tagEdit: tagEdit
    property alias editorMode_tagsModel: editorMode_tagsModel
    property alias editorMode_tagEdit: editorMode_tagEdit

    property int margin: util.QML_MARGINS
    property bool canInspect: false

    // Get around TagEdit.searchModel attr name
    property var searchViewSearchModel: searchModel

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
                        onTextChanged: {
                            if(searchModel.description != text) {
                                searchModel.description = text
                            }
                        }
                        KeyNavigation.tab: startDateButtons.firstTabItem
                        Connections {
                            target: searchModel
                            function onDescriptionChanged() {
                                if(descriptionEdit.text != searchModel.description) {
                                    descriptionEdit.text = searchModel.description
                                }
                            }
                        }
                    }

                    PK.Text { text: "Start Date" }

                    PK.DatePickerButtons {
                        id: startDateButtons
                        objectName:'startDateButtons'
                        datePicker: startDatePicker
                        timePicker: startTimePicker
                        dateTime: searchModel.startDateTime
                        hideUnsure: true
                        onDateTimeChanged: { if(searchModel.startDateTime != dateTime) searchModel.startDateTime = dateTime }
                        backTabItem: descriptionEdit
                        tabItem: endDateButtons.firstTabItem
                        Connections {
                            target: searchModel
                            function onStartDateTimeChanged() { startDateButtons.dateTime = searchModel.startDateTime }
                        }
                    }

                    PK.DatePicker {
                        id: startDatePicker
                        objectName: 'startDatePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(searchModel.startDateTime != dateTime) searchModel.startDateTime = dateTime
                        Connections {
                            target: searchModel
                            function onStartDateTimeChanged() { startDatePicker.dateTime = searchModel.startDateTime }
                        }
                    }

                    PK.TimePicker {
                        id: startTimePicker
                        objectName: 'startTimePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(searchModel.startDateTime != dateTime) searchModel.startDateTime = dateTime
                        Connections {
                            target: searchModel
                            function onStartDateTimeChanged() { startTimePicker.dateTime = searchModel.startDateTime }
                        }
                    }

                    PK.Text { text: "End Date" }

                    PK.DatePickerButtons {
                        id: endDateButtons
                        objectName:'endDateButtons'
                        datePicker: endDatePicker
                        timePicker: endTimePicker
                        dateTime: searchModel.endDateTime
                        hideUnsure: true
                        onDateTimeChanged: if(searchModel.endDateTime != dateTime) searchModel.endDateTime = dateTime
                        backTabItem: startDateButtons.lastTabItem
                        tabItem: loggedStartDateTimeButtons.firstTabItem
                        Connections {
                            target: searchModel
                            function onEndDateTimeChanged() { endDateButtons.dateTime = searchModel.endDateTime }
                        }
                    }

                    PK.DatePicker {
                        id: endDatePicker
                        objectName: 'endDatePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(searchModel.endDateTime != dateTime) searchModel.endDateTime = dateTime
                        Connections {
                            target: searchModel
                            function onEndDateTimeChanged() { endDatePicker.dateTime = searchModel.endDateTime }
                        }
                    }

                    PK.TimePicker {
                        id: endTimePicker
                        objectName: 'endTimePicker'
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(searchModel.endDateTime != dateTime) searchModel.endDateTime = dateTime
                        Connections {
                            target: searchModel
                            function onEndDateTimeChanged() { endTimePicker.dateTime = searchModel.endDateTime }
                        }
                    }

                    PK.Text {
                        text: "Logged Start Date"
                        visible: sceneModel.isInEditorMode
                    }

                    PK.DatePickerButtons {
                        id: loggedStartDateTimeButtons
                        objectName:'loggedStartDateTimeButtons'
                        datePicker: loggedStartDateDatePicker
                        timePicker: loggedStartDateTimePicker
                        dateTime: searchModel.loggedStartDateTime
                        hideUnsure: true
                        visible: sceneModel.isInEditorMode
                        onDateTimeChanged: if(searchModel.loggedStartDateTime != dateTime) searchModel.loggedStartDateTime = dateTime
                        backTabItem: endDateButtons.lastTabItem
                        tabItem: loggedEndDateTimeButtons.firstTabItem
                        Connections {
                            target: searchModel
                            function onLoggedStartDateTimeChanged() { loggedStartDateTimeButtons.dateTime = searchModel.loggedStartDateTime }
                        }
                    }

                    PK.DatePicker {
                        id: loggedStartDateDatePicker
                        objectName: 'loggedStartDateDatePicker'
                        visible: sceneModel.isInEditorMode
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(searchModel.loggedStartDateTime != dateTime) searchModel.loggedStartDateTime = dateTime
                        Connections {
                            target: searchModel
                            function onLoggedStartDateTimeChanged() { loggedStartDateDatePicker.dateTime = searchModel.loggedStartDateTime }
                        }
                    }

                    PK.TimePicker {
                        id: loggedStartDateTimePicker
                        objectName: 'loggedStartDateTimePicker'
                        visible: sceneModel.isInEditorMode
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(searchModel.loggedStartDateTime != dateTime) searchModel.loggedStartDateTime = dateTime
                        Connections {
                            target: searchModel
                            function onLoggedStartDateTimeChanged() { loggedStartDateTimePicker.dateTime = searchModel.loggedStartDateTime }
                        }
                    }                    

                    PK.Text {
                        text: "Logged End Date"
                        visible: sceneModel.isInEditorMode
                    }

                    PK.DatePickerButtons {
                        id: loggedEndDateTimeButtons
                        objectName:'loggedEndDateTimeButtons'
                        datePicker: loggedEndDateDatePicker
                        timePicker: loggedEndDateTimePicker
                        dateTime: searchModel.loggedEndDateTime
                        hideUnsure: true
                        visible: sceneModel.isInEditorMode
                        onDateTimeChanged: if(searchModel.loggedEndDateTime != dateTime) searchModel.loggedEndDateTime = dateTime
                        backTabItem: loggedStartDateTimeButtons.lastTabItem
                        tabItem: nodalBox
                        Connections {
                            target: searchModel
                            function onLoggedEndDateTimeChanged() { loggedEndDateTimeButtons.dateTime = searchModel.loggedEndDateTime }
                        }
                    }

                    PK.DatePicker {
                        id: loggedEndDateDatePicker
                        objectName: 'loggedEndDateDatePicker'
                        visible: sceneModel.isInEditorMode
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(searchModel.loggedEndDateTime != dateTime) searchModel.loggedEndDateTime = dateTime
                        Connections {
                            target: searchModel
                            function onLoggedEndDateTimeChanged() { loggedEndDateDatePicker.dateTime = searchModel.loggedEndDateTime }
                        }
                    }

                    PK.TimePicker {
                        id: loggedEndDateTimePicker
                        objectName: 'loggedEndDateTimePicker'
                        visible: sceneModel.isInEditorMode
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        onDateTimeChanged: if(searchModel.loggedEndDateTime != dateTime) searchModel.loggedEndDateTime = dateTime
                        Connections {
                            target: searchModel
                            function onLoggedEndDateTimeChanged() { loggedEndDateTimePicker.dateTime = searchModel.loggedEndDateTime }
                        }
                    }

                    PK.FormDivider { Layout.columnSpan: 2 }

                    PK.Text { text: "Nodal" }

                    PK.CheckBox {
                        id: nodalBox
                        objectName: 'nodalBox'
                        checked: searchModel.nodal
                        KeyNavigation.tab: hideRelationshipsBox
                        KeyNavigation.backtab: loggedEndDateTimeButtons.lastTabItem
                        onCheckedChanged: if(searchModel.nodal != checked) searchModel.nodal = checked
                    }

                    PK.Text { text: "Hide Relationships" }

                    PK.CheckBox {
                        id: hideRelationshipsBox
                        objectName: 'hideRelationshipsBox'
                        checked: searchModel.hideRelationships
                        onCheckedChanged: if(searchModel.hideRelationships != checked) searchModel.hideRelationships = checked
                    }

                    /* PK.Text { text: "Hide Brackets" } */

                    /* PK.CheckBox { */
                    /*     id: hideBracketsBox */
                    /*     objectName: 'hideBracketsBox' */
                    /*     /\* checked: sceneModel.hideDateBuddies *\/ */
                    /*     /\* onCheckedChanged: sceneModel.hideDateBuddies = checked *\/ */
                    /* } */

                    PK.Text { 
                        text: "Tags"
                        visible: ! sceneModel.isInEditorMode
                    }

                    PK.TagEdit {
                        id: tagEdit
                        visible: ! sceneModel.isInEditorMode
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.margins: 1
                        Layout.minimumHeight: 200
                        KeyNavigation.tab: descriptionEdit
                        KeyNavigation.backtab: hideRelationshipsBox
                        model: TagsModel {
                            id: tagsModel
                            scene: sceneModel.scene
                            searchModel: searchViewSearchModel
                        }
                    }

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
                                        id: editorMode_tagEdit
                                        objectName: 'SearchView_editorMode_tagEdit'
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Layout.margins: 1
                                        Layout.minimumHeight: 200
                                        model: TagsModel {
                                            id: editorMode_tagsModel
                                            objectName: 'SearchView_editorMode_tagsModel'
                                            scene: sceneModel.scene
                                            searchModel: searchViewSearchModel
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
