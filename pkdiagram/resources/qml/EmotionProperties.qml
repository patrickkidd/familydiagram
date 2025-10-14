import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "./PK" 1.0 as PK
import "js/Global.js" as Global
import PK.Models 1.0


Page {
    
    id: root
    objectName: 'emotionProps'

    signal cancel
    signal done
    signal resize
    signal editEvent

    property int margin: util.QML_MARGINS
    property var focusResetter: emotionPage
    property string emotionTitle: emotionModel.itemName

    property var emotionModel: EmotionPropertiesModel {
        id: emotionModel
        scene: sceneModel.scene
        onItemsChanged: {
            if(items.length == 0) {
                focusResetter.forceActiveFocus()
            }
        }
    }

    property var titleLabel: titleLabel
    property var intensityBox: intensityBox
    property var colorBox: colorBox
    property var notesEdit: notesEdit
    property var tagsList: tagsList
    property alias notesHiddenHelpText: notesHiddenHelpText

    property bool isReadOnly: (sceneModel && sceneModel.readOnly) ? true : false
    property bool canInspect: false
    function onInspect(tab) {
        // translate MainWindow kb shortcut tab indexes to local tab indexes
        setCurrentTab(tab)
    }

    function setCurrentTab(tab) {}

    function currentTab() {}

    KeyNavigation.tab: editEventButton

    header: PK.ToolBar {
        PK.ToolButton {
            id: doneButton
            text: 'Done'
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: done()
        }
        PK.Label {
            id: titleLabel
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
            text: 'Cancel'
            visible: false
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: cancel()
        }
    }
    
    background: Rectangle {
        anchors.fill: parent
        color: util.QML_WINDOW_BG
    }

    Flickable {
        id: emotionPage
        anchors.fill: parent
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
                width: parent.width
                GridLayout {
                    id: mainGrid
                    columns: 2
                    columnSpacing: util.QML_MARGINS / 2
                    // columnSpacing: util.QML_SPACING
                    // rowSpacing: util.QML_SPACING
                    width: parent.width


                    
                    // PK.ComboBox {
                    //     id: emotionKindBox // differentiate from PersonProperties.kindBox in tests
                    //     objectName: 'emotionKindBox'
                    //     textRole: 'label'
                    //     model: ListModel { }
                    //     Component.onCompleted: {
                    //         var entries = emotionModel.kindsMap
                    //         for(var i=0; i < entries.length; i++) {
                    //             var entry = entries[i]
                    //             model.append(entry)
                    //         }
                    //     }
                    //     currentIndex: emotionModel.kindIndex
                    //     Layout.fillWidth: true
                    //     Layout.maximumWidth: 200
                    //     KeyNavigation.tab: personBox
                    //     onCurrentIndexChanged: emotionModel.kindIndex = currentIndex
                    // }

                    PK.Text { text: " "; Layout.minimumWidth: 75}

                    PK.Button {
                        id: editEventButton
                        text: "→ Edit Event"
                        visible: emotionModel.startDateTime
                        onClicked: root.editEvent()
                    }

                    Rectangle { width: 1; height: 1; color: 'transparent'; Layout.columnSpan: 2 }

                    PK.Text { text: "Intensity" }

                    PK.ComboBox {
                        id: intensityBox
                        model: util.EMOTION_INTENSITY_NAMES
                        currentIndex: emotionModel.intensityIndex
                        KeyNavigation.tab: colorBox
                        KeyNavigation.backtab: editEventButton
                        onCurrentIndexChanged: emotionModel.intensityIndex = currentIndex
                    }

                    PK.Text { text: "Color" }

                    PK.ColorPicker {
                        id: colorBox
                        color: emotionModel.color
                        KeyNavigation.tab: notesEdit
                        KeyNavigation.backtab: intensityBox
                        onCurrentIndexChanged: emotionModel.color = model[currentIndex]
                    }

                    PK.Text {
                        text: "Details"
                    }

                    PK.TextEdit {
                        id: notesEdit
                        text: emotionModel.notes
                        padding: margin
                        width: parent.width
                        wrapMode: TextEdit.Wrap
                        visible: ! Global.isValidDateTime(emotionModel.startDateTime)
                        readOnly: sceneModel.readOnly
                        Layout.fillWidth: true
                        Layout.minimumHeight: 300
                        Layout.maximumHeight: 300
                        onEditingFinished: emotionModel.notes = (text ? text : undefined)
                    }

                    Rectangle {

                        Layout.fillWidth: true
                        Layout.minimumHeight: 200
                        Layout.maximumHeight: 200
                        color: 'transparent'
                        visible: ! notesEdit.visible

                        PK.NoDataText {
                            id: notesHiddenHelpText
                            text: util.S_EMOTION_SYMBOL_NOTES_HIDDEN
                            Connections {
                                target: emotionModel
                                function onStartDateTimeChanged() {
                                    notesHiddenHelpText.visible = Global.isValidDateTime(emotionModel.startDateTime)
                                }
                            }
                        }
                    }

                    PK.Text { text: "Tags" }


                    PK.ActiveListEdit {
                        id: tagsList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 200
                        Layout.maximumHeight: 200
                        model: TagsModel {
                            scene: sceneModel.scene
                            items: emotionModel.items
                        }
                    }

                }
            }
        }
    }
}
