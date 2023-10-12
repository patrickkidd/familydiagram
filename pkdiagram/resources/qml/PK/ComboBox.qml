import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Controls.impl 2.12
import QtQuick.Templates 2.12 as T
import "../js/Global.js" as Global

ComboBox {

    id: root

    // really just for test so far
    property bool opened: popup.opened
    function close() { popup.close(); }

    font.pixelSize: util.TEXT_FONT_SIZE

    onActivated: root.forceActiveFocus()

    indicator: ColorImage {
        x: root.mirrored ? root.padding : root.width - width - root.padding
        y: root.topPadding + (root.availableHeight - height) / 2
        color: util.IS_UI_DARK_MODE ? root.palette.light : root.palette.dark
        defaultColor: "#353637"
        source: "qrc:/qt-project.org/imports/QtQuick/Controls.2/images/double-arrow.png"
        opacity: enabled ? 1 : 0.3
    }

    palette.text: root.enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
    palette.buttonText: root.enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
    palette.mid: util.QML_ITEM_BORDER_COLOR
    palette.button: util.QML_CONTROL_BG
    palette.window: util.QML_WINDOW_BG
    palette.highlight: util.QML_HIGHLIGHT_COLOR

    background: Rectangle {
        implicitWidth: 140
        implicitHeight: 40

        color: root.down ? root.palette.mid : root.palette.button
        border.color: root.down || root.visualFocus ? root.palette.highlight : root.palette.mid
        border.width: !root.editable && (root.down || root.visualFocus) ? 2 : 1
        visible: !root.flat || root.down
    }

}


