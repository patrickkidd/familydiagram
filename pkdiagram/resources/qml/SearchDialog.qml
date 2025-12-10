import QtQuick 2.12
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import "./PK" 1.0 as PK
import PK.Models 1.0



Page {

    id: root

    signal done

    width: 450
    height: 600

    function onShown() {
        Edit.forceActiveFocus()
    }

    Connections {
        target: sceneModel
        function onSceneChanged() {
            propsPage.contentY = 0
        }
    }

    property alias descriptionEdit: descriptionEdit
    property alias tagsEdit: tagsEdit
    property alias emotionalUnitsEdit: emotionalUnitsEdit
    property alias peoplePicker: peoplePicker
    property var propsPage: propsPage

    property int margin: util.QML_MARGINS
    property bool canInspect: false

    // Get around ActiveListEdit.searchModel attr name
    property var searchDialogSearchModel: searchModel

    header: PK.ToolBar {
        PK.ToolButton {
            id: resetButton
            text: 'Reset'
            visible: ! searchModel.isBlank || emotionalUnitsEdit.model.anyActive || peoplePicker.count > 0
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: {
                peoplePicker.clear()
                searchModel.clear()
                sceneModel.scene.clearActiveLayers()
            }
        }
        PK.Label {
            text: "Find"
            elide: Text.ElideRight
            anchors.centerIn: parent
            font.family: util.FONT_FAMILY_TITLE
            font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
            dropShadow: true
        }
        PK.ToolButton {
            id: doneButton
            text: 'Done'
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: done()
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
            clip: true
            flickableDirection: Flickable.VerticalFlick
            contentWidth: width
            contentHeight: pageInner.height

            function scrollToItem(item) {
                if (item) {
                    var itemY = item.y;
                    var itemHeight = item.height;
                    var flickableHeight = propsPage.height;
                    var contentY = propsPage.contentY;

                    if (itemY < contentY) {
                        propsPage.contentY = itemY;
                    } else if (itemY + itemHeight > contentY + flickableHeight) {
                        propsPage.contentY = itemY + itemHeight - flickableHeight;
                    }
                }
            }

            ColumnLayout {

                id: pageInner
                anchors.centerIn: parent

                MouseArea {
                    width: propsPage.width
                    height: propsPage.height
                    onClicked: parent.forceActiveFocus()
                }

                GridLayout {

                    id: grid
                    columns: 2
                    columnSpacing: util.QML_MARGINS / 2
                    Layout.margins: util.QML_MARGINS

                    PK.Label {
                        text: "Timeline"
                        font.family: util.FONT_FAMILY_TITLE
                        font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
                        Layout.columnSpan: 2
                    }

                    PK.FormDivider { Layout.columnSpan: 2 }

                    PK.Text { text: "People" }

                    PK.PeoplePicker {
                        id: peoplePicker
                        objectName: 'peoplePicker'
                        scenePeopleModel: peopleModel
                        selectedPeopleModel: ListModel {}
                        existingOnly: true
                        Layout.fillWidth: true
                        Layout.minimumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        Layout.maximumHeight: Math.max(model.count + 2, 4) * util.QML_ITEM_HEIGHT
                        function syncToSearchModel() {
                            var people = []
                            for(var i = 0; i < model.count; i++) {
                                var entry = model.get(i)
                                if(entry.person) {
                                    people.push(entry.person)
                                }
                            }
                            searchModel.people = people
                        }
                        onItemAddDone: syncToSearchModel()
                        onItemRemoveDone: syncToSearchModel()
                        onItemSubmitted: syncToSearchModel()
                    }

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
                        text: "Logged Start"
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
                        text: "Logged End"
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
                        tabItem: tagsEdit
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

                    // PK.Text { text: "Nodal" }

                    // PK.CheckBox {
                    //     id: nodalBox
                    //     objectName: 'nodalBox'
                    //     checked: searchModel.nodal
                    //     KeyNavigation.tab: hideRelationshipsBox
                    //     KeyNavigation.backtab: loggedEndDateTimeButtons.lastTabItem
                    //     onCheckedChanged: if(searchModel.nodal != checked) searchModel.nodal = checked
                    // }

                    // PK.Text { text: "Hide Relationships" }

                    // PK.CheckBox {
                    //     id: hideRelationshipsBox
                    //     objectName: 'hideRelationshipsBox'
                    //     checked: searchModel.hideRelationships
                    //     onCheckedChanged: if(searchModel.hideRelationships != checked) searchModel.hideRelationships = checked
                    // }

                    /* PK.Text { text: "Hide Brackets" } */

                    /* PK.CheckBox { */
                    /*     id: hideBracketsBox */
                    /*     objectName: 'hideBracketsBox' */
                    /*     /\* checked: sceneModel.hideDateBuddies *\/ */
                    /*     /\* onCheckedChanged: sceneModel.hideDateBuddies = checked *\/ */
                    /* } */

                    PK.Text { 
                        text: "Tags"
                    }

                    PK.ActiveListEdit {
                        id: tagsEdit
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.margins: 1
                        Layout.minimumHeight: 200
                        KeyNavigation.tab: emotionalUnitsEdit
                        KeyNavigation.backtab: loggedEndDateTimeButtons
                        model: TagsModel {
                            id: tagsModel
                            scene: sceneModel.scene
                            searchModel: searchDialogSearchModel
                        }
                    }
                    
                    PK.HelpText {
                        text: "The timeline will only show events that have the tags selected in this list. If no tags are selected, then all events are shown on the timeline.\nNOTE: The graphical timeline will show tag rows from bottom up in the order they are clicked."
                        Layout.columnSpan: 2
                    }

                    PK.Label {
                        text: "Diagram"
                        font.family: util.FONT_FAMILY_TITLE
                        font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
                        Layout.columnSpan: 2
                        Layout.topMargin: util.QML_ITEM_HEIGHT / 2
                    }

                    PK.FormDivider { Layout.columnSpan: 2 }

                    PK.Text { text: "Emotional Units" }

                    PK.ActiveListEdit {
                        id: emotionalUnitsEdit
                        showButtons: false
                        emptyText: {
                            if(sceneModel.hideNames) {
                                util.S_NO_EMOTIONAL_UNITS_SHOWN_NAMES_HIDDEN
                            } else if(model.noPairBondsWithNames) {
                                util.S_NO_EMOTIONAL_UNITS_SHOWN_NO_PAIRBONDS_WITH_NAMES
                            } else {
                                ''
                            }
                        }                        
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.margins: 1
                        Layout.minimumHeight: 180
                        KeyNavigation.tab: sceneLayerView
                        KeyNavigation.backtab: tagsEdit
                        model: EmotionalUnitsModel {
                            id: emotionalUnitsModel
                            scene: sceneModel.scene
                        }
                    }

                    PK.HelpText {
                        text: util.S_EMOTIONAL_UNITS_HELP_TEXT
                        Layout.columnSpan: 2
                    }

                    PK.Text {
                        text: "Custom Views"
                        visible: sceneModel.isInEditorMode
                    }

                    PK.SceneLayerView {
                        id: sceneLayerView
                        visible: sceneModel.isInEditorMode
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.margins: 1
                        Layout.minimumHeight: 200
                        model: SceneLayerModel {
                            id: layerModel
                            scene: sceneModel.scene
                            items: sceneModel.scene ? [sceneModel.scene] : []
                        }
                    }

                    PK.HelpText {
                        visible: sceneModel.isInEditorMode
                        text: "Custom views are like powerpoint slides that focus on a sub-set of family members, with alterations like position, color, deemphasize. Diagram views can also be annotated with text callouts, pencil strokes. They are for small tweaks to get a point across that do not affect the data of the family. Expand the left edge of this drawer further to the left to show the 'Store Geometry' column." + (sceneLayerView.responsive1 ? "\n\n'Store Goemetry' will store the positions for items in that view, and rearrange the diagram to reflect those positions when you activate the view." : '');
                        Layout.columnSpan: 2
                    }

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
