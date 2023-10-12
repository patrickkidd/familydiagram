import QtQuick 2.12 as Q
import QtGraphicalEffects 1.13

Q.Text {
    color: enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
    font.pixelSize: util.TEXT_FONT_SIZE
}
