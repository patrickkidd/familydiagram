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
    signal inspectEvent

    property int margin: util.QML_MARGINS
    property var focusResetter: emotionPage
    property string emotionTitle: emotionModel.itemName
    property var hasEvent: Global.isValidDateTime(emotionModel.startDateTime)

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

    property bool isReadOnly: (sceneModel && sceneModel.readOnly) ? true : false
    property bool canInspect: false
    function onInspect(tab) {
        // translate MainWindow kb shortcut tab indexes to local tab indexes
        setCurrentTab(tab)
    }

    function setCurrentTab(tab) {}

    function currentTab() {}

    function scrollToItem(item) {
        if (item) {
            var itemY = item.y;
            var itemHeight = item.height;
            var flickableHeight = emotionPage.height;
            var contentY = emotionPage.contentY;

            if (itemY < contentY) {
                emotionPage.contentY = itemY;
            } else if (itemY + itemHeight > contentY + flickableHeight) {
                emotionPage.contentY = itemY + itemHeight - flickableHeight;
            }
        }
    }

    function scrollToNotes() {
        scrollToItem(notesEdit)
        notesEdit.forceActiveFocus()
    }

    function scrollToMeta() {
        scrollToItem(tagsList)
        tagsList.forceActiveFocus()
    }

    KeyNavigation.tab: inspectEventButton

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

                    PK.FormDivider {
                        text: "Relationship"
                        Layout.columnSpan: 2
                    }

                    PK.Label { text: " " }

                    ColumnLayout {

                        PK.Button {
                            id: inspectEventButton
                            text: "→ Inspect Event"
                            visible: root.hasEvent
                            onClicked: root.inspectEvent()
                        }

                        PK.HelpText {
                            visible: root.hasEvent
                            text: "This relationship symbol was automatically created by an event, so you can edit the intensity, color, etc from there."
                        }

                    }

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

                    PK.Text {
                        text: "Intensity"
                        visible: ! root.hasEvent
                    }

                    PK.ComboBox {
                        id: intensityBox
                        visible: ! root.hasEvent
                        model: util.EMOTION_INTENSITY_NAMES
                        currentIndex: emotionModel.intensityIndex
                        KeyNavigation.tab: colorBox
                        KeyNavigation.backtab: inspectEventButton
                        onCurrentIndexChanged: emotionModel.intensityIndex = currentIndex
                    }

                    PK.Text {
                        text: "Color"
                        visible: ! root.hasEvent
                    }

                    PK.ColorPicker {
                        id: colorBox
                        visible: ! root.hasEvent
                        color: emotionModel.color
                        KeyNavigation.tab: notesEdit
                        KeyNavigation.backtab: intensityBox
                        onCurrentIndexChanged: emotionModel.color = model[currentIndex]
                    }

                    PK.Text {
                        text: "Details"
                        visible: ! root.hasEvent
                    }

                    PK.TextEdit {
                        id: notesEdit
                        text: emotionModel.notes
                        visible: ! root.hasEvent
                        padding: margin
                        width: parent.width
                        wrapMode: TextEdit.Wrap
                        readOnly: sceneModel.readOnly
                        Layout.fillWidth: true
                        Layout.minimumHeight: 150
                        Layout.maximumHeight: 150
                        onEditingFinished: emotionModel.notes = (text ? text : undefined)
                    }

                    // Meta

                    PK.FormDivider {
                        text: "Meta"
                        visible: ! root.hasEvent && sceneModel.isInEditorMode
                        Layout.columnSpan: 2
                    }

                    PK.Text {
                        text: "Views"
                        visible: ! root.hasEvent && sceneModel.isInEditorMode
                    }

                    PK.ItemLayerList {
                        id: layerList
                        visible: ! root.hasEvent && sceneModel.isInEditorMode
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 200
                        Layout.maximumHeight: 200
                        model: LayerItemLayersModel {
                            scene: sceneModel.scene
                            items: emotionModel.items ? emotionModel.items : []
                        }
                    }

                }
            }
        }
    }
}
