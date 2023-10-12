import QtQuick 2.12
import QtQuick.Controls 2.5 as QQC

QQC.ToolBar {
    id: root
    property bool bottomBorder: true
    property bool topBorder: false
    background: Rectangle {
        implicitHeight: util.QML_HEADER_HEIGHT
        color: util.QML_HEADER_BG
        Rectangle {
            visible: root.topBorder
            width: parent.width
            height: 1
            anchors.top: parent.top
            color: util.QML_ITEM_BORDER_COLOR
        }
        Rectangle {
            visible: root.bottomBorder
            width: parent.width
            height: 1
            anchors.bottom: parent.bottom
            color: util.QML_ITEM_BORDER_COLOR
        }
    }
}
