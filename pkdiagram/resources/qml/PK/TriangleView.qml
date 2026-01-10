import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.15
import "." 1.0 as PK
import PK.Models 1.0


Rectangle {

    id: root

    color: 'transparent'
    border {
        width: 1
        color: util.QML_ITEM_BORDER_COLOR
    }

    property var model: TriangleModel {
        scene: sceneModel.scene
    }
    property int currentIndex: -1
    property int count: listViewItem.count

    property var emptyText: util.S_NO_TRIANGLES_TEXT

    function onRowClicked(mouse, row) {
        if(mouse && mouse.modifiers & Qt.ControlModifier) {
            currentIndex = -1
        } else {
            currentIndex = row
        }
    }

    property bool noItemsShown: {
        if(model == null) {
            return true
        } else if(listViewItem.count == 0) {
            return true
        } else {
            return false
        }
    }

    Rectangle {
        color: "transparent"
        visible: noItemsShown
        anchors.fill: parent
        PK.NoDataText {
            id: noItemsText
            text: root.emptyText
        }
    }

    ColumnLayout {

        spacing: 0
        anchors.fill: parent
        anchors.margins: 1

        ListView {
            id: listViewItem
            clip: true
            model: root.model
            Layout.fillWidth: true
            Layout.fillHeight: true

            delegate: Rectangle {

                property bool selected: index == currentIndex
                property bool current: false
                property int iTag: index
                property var itemName: name

                width: parent ? parent.width : 0
                height: util.QML_ITEM_HEIGHT
                color: util.itemBgColor(selected, current, index % 2 == 1)

                RowLayout {

                    id: rowLayout
                    width: parent.width
                    Layout.minimumHeight: height
                    spacing: 6

                    PK.CheckBox {
                        id: checkBox
                        textColor: util.textColor(selected, current)
                        checkState: active
                        onClicked: onRowClicked(null, index)
                        onCheckStateChanged: {
                            if(active != checkState) {
                                active = checkState
                            }
                        }
                    }

                    PK.Text {
                        id: dateText
                        color: util.textColor(selected, current)
                        text: date == undefined ? '' : date
                        Layout.preferredWidth: 80
                        elide: Text.ElideRight
                    }

                    PK.Text {
                        id: nameText
                        color: util.textColor(selected, current)
                        text: name == undefined ? '' : name
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Rectangle {
                        height: 1
                        Layout.preferredWidth: 5
                        color: 'transparent'
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    anchors.leftMargin: checkBox.y + checkBox.width
                    onClicked: {
                        onRowClicked(mouse, index)
                    }
                }
            }
        }

        Rectangle {
            color: util.QML_ITEM_BORDER_COLOR
            height: 1
            Layout.fillWidth: true
        }
    }
}
