import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." 1.0 as PK
import "../js/Global.js" as Global
import PK.Models 1.0


Page {
    
    id: root
    objectName: 'EmotionProperties'

    signal cancel
    signal done

    property alias emotionNotesEdit: emotionNotesEdit
    property alias notesHiddenHelpText: notesHiddenHelpText

    property int margin: util.QML_MARGINS
    property var focusResetter: emotionPage
    property string itemTitle: {
        if(emotionModel.items.length > 1) {
            emotionModel.items.length + ' Relationships'
        } else {
            emotionModel.parentName
        }
    }
    property string emotionTitle: {
        if(emotionModel.addMode) {
            if(emotionKindBox.currentText) {
                'New ' + emotionKindBox.currentText + ': ' + itemTitle

            } else {
                'New Relationship'
            }
        } else {
            if(emotionKindBox.currentText) {
                emotionKindBox.currentText + ': ' + itemTitle
            } else {
                'Edit Relationship'
            }
        }
    }
    property var emotionModel: EmotionPropertiesModel {
        id: emotionModel
        objectName: 'emotionModel'
        scene: sceneModel.scene
        onItemsChanged: {
            if(items.length == 0) {
                focusResetter.forceActiveFocus()
            }
        }
    }

    property bool isReadOnly: (sceneModel && sceneModel.readOnly) ? true : false
    property bool canInspect: false
    function onInspect(tab) {
        // translate MainWindow kb shortcut tab indexes to local tab indexes
        setCurrentTab(tab)
    }

    function setCurrentTab(tab) {
        var index = 0
        if(tab == 'item')
            index = 0
        else if(tab == 'notes')
            index = 1
        else if(tab == 'meta')
            index = 2
        tabBar.setCurrentIndex(index)
    }

    function currentTab() {
        return {
            0: 'item',
            1: 'notes',
            2: 'meta'
        }[tabBar.currentIndex]
    }    

    KeyNavigation.tab: emotionKindBox

    header: PK.ToolBar {
        PK.ToolButton {
            id: doneButton
            objectName: 'emotion_doneButton'
            text: emotionModel.addMode ? 'Add' : 'Done'
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: done()
        }
        PK.Label {
            text: emotionTitle
            elide: Text.ElideRight
            anchors.centerIn: parent
            horizontalAlignment: Text.AlignHCenter
            width: (doneButton.x) - (cancelButton.x + cancelButton.width) - root.margin * 2
            font.family: util.FONT_FAMILY_TITLE
            font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
        }
        PK.ToolButton {
            id: cancelButton
            objectName: 'cancelButton'
            text: 'Cancel'
            visible: emotionModel.addMode
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: cancel()
        }
    }

    footer: PK.TabBar {
        id: tabBar
        objectName: 'tabBar'
        currentIndex: stack.currentIndex
        PK.TabButton { text: "Relationship" }
        PK.TabButton { text: "Notes" }
        PK.TabButton { text: "Tags" }
    }
    
    background: Rectangle {
        anchors.fill: parent
        color: util.QML_WINDOW_BG
    }

    StackLayout {

        id: stack
        objectName: 'stack'
        currentIndex: tabBar.currentIndex
        enabled: !sceneModel.readOnly
        anchors.fill: parent
        
        Flickable {
            id: emotionPage
            contentWidth: width
            contentHeight: emotionPageInner.childrenRect.height + root.margin * 2

            MouseArea {
                width: parent.width
                height: parent.height
                onClicked: parent.forceActiveFocus()
            }

            Rectangle {

                id: emotionPageInner
                anchors.fill: parent
                anchors.margins: margin
                color: 'transparent'
                
                ColumnLayout { // necessary to expand DatePicker
                    id: cl
                    width: parent.width
                    GridLayout {
                        id: mainGrid
                        columns: 2
                        columnSpacing: util.QML_MARGINS / 2
                        // columnSpacing: util.QML_SPACING
                        // rowSpacing: util.QML_SPACING
                        width: parent.width

                        PK.Text { text: "Kind" }
                        
                        PK.ComboBox {
                            id: emotionKindBox // differentiate from PersonProperties.kindBox in tests
                            objectName: 'emotionKindBox'
                            textRole: 'label'
                            model: ListModel { }
                            Component.onCompleted: {
                                var entries = emotionModel.kindsMap
                                for(var i=0; i < entries.length; i++) {
                                    var entry = entries[i]
                                    model.append(entry)
                                }
                            }
                            currentIndex: emotionModel.kindIndex
                            Layout.fillWidth: true
                            Layout.maximumWidth: 200
                            KeyNavigation.tab: personABox
                            onCurrentIndexChanged: emotionModel.kindIndex = currentIndex
                        }

                        Rectangle { width: 1; height: 1; color: 'transparent'; Layout.columnSpan: 2 }

                        PK.Text { text: "Person A" }

                        PK.ComboBox {
                            id: personABox
                            objectName: 'personABox'
                            model: peopleModel
                            textRole: 'name'
                            displayText: {
                                if(emotionModel.personAId != -1 && currentIndex != -1)
                                    currentText
                                else if(currentIndex == -1)
                                    util.EMPTY_TEXT
                                else
                                    'Unnamed Person'
                            }
                            currentIndex: {
                                model.resetter
                                model.rowForId(emotionModel.personAId)
                            }
                            Layout.fillWidth: true
                            Layout.maximumWidth: 200
                            KeyNavigation.tab: swapButton
                            onCurrentIndexChanged: {
                                if(currentIndex > -1) {
                                    emotionModel.personAId = model.idForRow(currentIndex)
                                }
                            }
                        }
                        
                        Item {
                            height: swapButton.height
                            width: personABox.x + personABox.width // hack to center button b/c automatic sizing was alternating betwen 0 and parent.width
                            Layout.columnSpan: 2
                            PK.Button {
                                id: swapButton
                                objectName: 'swapButton'
                                x: personABox.x + ((personABox.width / 2) - width / 2)
                                source: '../../swap-refresh.png'
                                width: 30
                                height: 30
                                enabled: emotionModel.kind != util.ITEM_CUTOFF
                                KeyNavigation.tab: personBBox
                                onClicked: {
                                    var personAId = emotionModel.personAId
                                    var personBId = emotionModel.personBId
                                    emotionModel.personBId = personAId
                                    emotionModel.personAId = personBId
                                }
                            }
                        }

                        PK.Text { text: "Person B" }

                        PK.ComboBox {
                            id: personBBox
                            objectName: 'personBBox'
                            textRole: 'name'
                            displayText: {
                                if(emotionModel.personBId != -1 && currentIndex != -1)
                                    currentText
                                else if(currentIndex == -1)
                                    util.EMPTY_TEXT
                                else
                                    'Unnamed Person'
                            }
                            enabled: emotionModel.dyadic
                            model: peopleModel
                            currentIndex: {
                                model.resetter
                                model.rowForId(emotionModel.personBId)
                            }
                            Layout.fillWidth: true
                            Layout.maximumWidth: 200
                            KeyNavigation.tab: startDateButtons.firstTabItem
                            KeyNavigation.backtab: swapButton
                            onCurrentIndexChanged: {
                                if(currentIndex > -1) {
                                    emotionModel.personBId = model.idForRow(currentIndex)
                                }
                            }
                        }
                        
                        Rectangle { width: 1; height: 1; color: 'transparent'; Layout.columnSpan: 2 }

                        PK.Text { text: emotionModel.isDateRange ? "Start Date" : "Date" }

                        PK.DatePickerButtons {
                            id: startDateButtons
                            objectName: 'startDateButtons'
                            datePicker: startDatePicker
                            timePicker: startTimePicker
                            dateTime: emotionModel.startDateTime
                            unsure: emotionModel.startDateUnsure
                            showInspectButton: true
                            enabled: ! root.isReadOnly
                            Layout.preferredHeight: implicitHeight - 10
                            backTabItem: personBBox
                            tabItem: endDateButtons.firstTabItem
                            onDateTimeChanged: emotionModel.startDateTime = dateTime
                            onUnsureChanged: emotionModel.startDateUnsure = unsure
                            onInspect: sceneModel.inspectItem(emotionModel.startEventId)
                            Connections {
                                target: emotionModel
                                function onStartDateTimeChanged() { startDateButtons.dateTime = emotionModel.startDateTime }
                                function onStartDateUnsureChanged() { startDateButtons.unsure = emotionModel.startDateUnsure }
                            }
                        }

                        PK.DatePicker {
                            id: startDatePicker
                            objectName: 'startDatePicker'
                            dateTime: emotionModel.startDateTime
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            onDateTimeChanged: emotionModel.startDateTime = dateTime
                            Connections {
                                target: emotionModel
                                function onStartDateTimeChanged() { startDatePicker.dateTime = emotionModel.startDateTime }
                            }                            
                        }

                        PK.TimePicker {
                            id: startTimePicker
                            objectName: 'startTimePicker'
                            dateTime: emotionModel.startDateTime
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            onDateTimeChanged: emotionModel.startDateTime = dateTime
                            Connections {
                                target: emotionModel
                                function onStartDateTimeChanged() { startTimePicker.dateTime = emotionModel.startDateTime }
                            }                            
                        }

                        PK.Text { text: "End Date"; visible: emotionModel.isDateRange }

                        PK.DatePickerButtons {
                            id: endDateButtons
                            objectName: 'endDateButtons'
                            datePicker: endDatePicker
                            timePicker: endTimePicker
                            dateTime: emotionModel.endDateTime
                            unsure: emotionModel.startDateUnsure
                            showInspectButton: true
                            enabled: ! root.isReadOnly
                            visible: emotionModel.isDateRange
                            Layout.preferredHeight: implicitHeight - 10
                            backTabItem: startDateButtons.lastTabItem
                            tabItem: dateRangeBox
                            onDateTimeChanged: emotionModel.endDateTime = dateTime
                            onUnsureChanged: emotionModel.startDateUnsure = unsure
                            onInspect: sceneModel.inspectItem(emotionModel.endEventId)
                            Connections {
                                target: emotionModel
                                function onEndDateTimeChanged() { endDateButtons.dateTime = emotionModel.endDateTime }
                                function onEndDateUnsureChanged() { startDateButtons.unsure = emotionModel.startDateUnsure }
                            }                            
                        }

                        PK.DatePicker {
                            id: endDatePicker
                            objectName: 'endDatePicker'
                            dateTime: emotionModel.endDateTime
                            visible: emotionModel.isDateRange
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            onDateTimeChanged: emotionModel.endDateTime = dateTime
                            Connections {
                                target: emotionModel
                                function onEndDateTimeChanged() { endDatePicker.dateTime = emotionModel.endDateTime }
                            }
                        }

                        PK.TimePicker {
                            id: endTimePicker
                            objectName: 'endTimePicker'
                            dateTime: emotionModel.endDateTime
                            visible: emotionModel.isDateRange
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: implicitHeight
                            onDateTimeChanged: emotionModel.endDateTime = dateTime
                            Connections {
                                target: emotionModel
                                function onEndDateTimeChanged() { endTimePicker.dateTime = emotionModel.endDateTime }
                            }
                        }

                        Rectangle { width: 1; height: 1; color: 'transparent'; Layout.columnSpan: 1 }

                        PK.CheckBox {
                            id: dateRangeBox
                            objectName: 'dateRangeBox'
                            text: "Is Date Range"
                            enabled: !sceneModel.readOnly
                            checked: emotionModel.isDateRange
                            Layout.fillWidth: true
                            KeyNavigation.backtab: endDateButtons.lastTabItem
                            KeyNavigation.tab: intensityBox
                            onCheckedChanged: emotionModel.isDateRange = checked
                        }

                        Rectangle { width: 1; height: 1; color: 'transparent'; Layout.columnSpan: 2 }

                        PK.Text { text: "Size" }

                        PK.ComboBox {
                            id: intensityBox
                            objectName: 'intensityBox'
                            model: util.EMOTION_INTENSITY_NAMES
                            currentIndex: emotionModel.intensityIndex
                            KeyNavigation.tab: colorBox
                            KeyNavigation.backtab: dateRangeBox
                            onCurrentIndexChanged: emotionModel.intensityIndex = currentIndex
                        }

                        PK.Text { text: "Color" }

                        PK.ColorPicker {
                            id: colorBox
                            objectName: 'colorBox'
                            color: emotionModel.color
                            KeyNavigation.tab: emotionKindBox
                            KeyNavigation.backtab: intensityBox
                            onCurrentIndexChanged: emotionModel.color = model[currentIndex]
                        }
                    }
                }
            }            
        }

        Flickable {
            id: notesEditFlickable
            contentX: 0
            contentHeight: {
                if(emotionNotesEdit.visible) {
                    Math.max(emotionNotesEdit.paintedHeight + 50, height) // allow scrolling
                } else {
                    height
                }
            }
            Layout.fillHeight: true
            Layout.fillWidth: true

            PK.TextEdit {
                id: emotionNotesEdit
                objectName: 'emotionNotesEdit'
                text: emotionModel.notes
                padding: margin
                width: parent.width
                wrapMode: TextEdit.Wrap
                visible: ! Global.isValidDateTime(emotionModel.startDateTime)
                readOnly: sceneModel.readOnly
                anchors.fill: parent
                onEditingFinished: emotionModel.notes = (text ? text : undefined)
            }

            PK.NoDataText {
                id: notesHiddenHelpText
                text: util.S_EMOTION_SYMBOL_NOTES_HIDDEN
                visible: Global.isValidDateTime(emotionModel.startDateTime)
                Connections {
                    target: emotionModel
                    function onStartDateTimeChanged() {
                        notesHiddenHelpText.visible = Global.isValidDateTime(emotionModel.startDateTime)
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
                        title: "Event tags Added to this Relationship Symbol as well as its start and end events."
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        padding: 1
                        ColumnLayout {
                            anchors.fill: parent
                            PK.ActiveListEdit {
                                id: tagsList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                model: TagsModel {
                                    objectName: "EmotionProperties_tagsModel"
                                    scene: sceneModel.scene
                                    items: emotionModel.items
                                }
                            }
                        }
                    }
                }
            }
        }
    }    
}
