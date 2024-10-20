import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12


Text {
    wrapMode: Text.WordWrap
    font.pixelSize: util.HELP_FONT_SIZE
    color: util.QML_ACTIVE_HELP_TEXT_COLOR
    leftPadding: util.HELP_FONT_SIZE
    rightPadding: util.HELP_FONT_SIZE
    Layout.fillWidth: true
    Layout.bottomMargin: util.HELP_FONT_SIZE
}
