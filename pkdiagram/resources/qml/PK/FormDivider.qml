import QtQuick 2.12
import QtQuick.Layouts 1.15


ColumnLayout {
    id: root

    property var text: ""
    Layout.fillWidth: true

    Text {
        id: label
        text: root.text
        visible: text
        color: util.QML_TEXT_COLOR
        font.family: util.FONT_FAMILY_TITLE
        font.pixelSize: util.TEXT_FONT_SIZE * 1.5
        Layout.fillWidth: true
    }

    Rectangle {
        height: 1
        Layout.fillWidth: true
        color: util.QML_ITEM_BORDER_COLOR
    }
    
    Layout.topMargin: margin / 2
    Layout.bottomMargin: margin / 2
}
