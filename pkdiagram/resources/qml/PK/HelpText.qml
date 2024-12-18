import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15


Text {
    wrapMode: Text.WordWrap
    textFormat: Text.MarkdownText
    color: util.QML_ACTIVE_HELP_TEXT_COLOR
    leftPadding: util.HELP_FONT_SIZE
    rightPadding: util.HELP_FONT_SIZE
    font.pixelSize: util.HELP_FONT_SIZE
    Layout.fillWidth: true
    Layout.maximumWidth: 400
    Layout.bottomMargin: util.HELP_FONT_SIZE
}
