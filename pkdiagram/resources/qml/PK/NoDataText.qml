import QtQuick 2.15
import QtQuick.Controls 2.15

Text {
    color: util.QML_INACTIVE_TEXT_COLOR
    anchors.centerIn: parent
    width: parent.width - util.QML_MARGINS * 2
    height: parent.height - util.QML_MARGINS * 2

    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    wrapMode: Text.WordWrap
    font.family: util.NO_ITEMS_FONT_FAMILY
    font.pixelSize: util.NO_ITEMS_FONT_PIXEL_SIZE
    font.bold: true
}
