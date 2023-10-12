import QtQuick 2.12
import QtQuick.Controls 2.5 as C


C.ToolButton {
    id: root

    font.pixelSize: util.TEXT_FONT_SIZE

    height: parent.height - 1 // was covering bottom-border

    contentItem: Text {
        text: root.text
        font: root.font
        opacity: enabled ? 1.0 : 0.3
        color: root.down ? util.QML_INACTIVE_TEXT_COLOR : util.QML_ACTIVE_TEXT_COLOR
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    palette.mid: 'transparent'
    palette.button: util.QML_HEADER_BG
///    Component.onCompleted: background.color = 'transparent'
}
