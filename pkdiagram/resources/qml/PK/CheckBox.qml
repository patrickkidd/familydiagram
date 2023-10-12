import QtQuick 2.12
import QtQuick.Controls 2.5
import "." 1.0 as PK

CheckBox {
    id: root
    property color textColor: enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
    property bool large: false
    font.pixelSize: util.TEXT_FONT_SIZE
    implicitHeight: preferred_implicitHeight
    readonly property var preferred_implicitHeight: large ? util.QML_ITEM_LARGE_HEIGHT : util.QML_ITEM_HEIGHT
    indicator: Rectangle {
        id: iRoot
        width: root.height * .7
        height: root.height * .7
        x: root.leftPadding
        y: parent.height / 2 - height / 2
        radius: root.height * .075
        color: util.IS_UI_DARK_MODE ? Qt.lighter(util.QML_ITEM_BG, 2.0) : util.QML_ITEM_BG
        border.width: root.visualFocus ? 2 : 1
        border.color: root.visualFocus ? util.QML_HIGHLIGHT_COLOR : util.QML_ITEM_BORDER_COLOR
        opacity: root.enabled ? 1.0 : .5

        Rectangle {
            width: down ? parent.height * .75 : (root.checkState ? parent.height * .65 : parent.height * .3)
            height: down ? parent.height * .75 : (root.checkState ? parent.height * .65 : parent.height * .3) // shrink down while animating opacity
            x: (parent.width / 2) - (width / 2)
            y: (parent.height / 2) - (height / 2)
            radius: root.height * .05
            opacity: root.checkState == Qt.Checked ? 1.0 : (root.checkState == Qt.PartiallyChecked ? .3 : 0.0)
            //color: root.down ? Qt.darker(util.SELECTION_COLOR, 1.5) : util.SELECTION_COLOR
            color: util.IS_UI_DARK_MODE ? Qt.lighter(util.QML_SELECTION_COLOR, 1.0) : util.QML_SELECTION_COLOR
            border {
                width: util.IS_UI_DARK_MODE ? 1 : 0
                color: util.QML_ITEM_BORDER_COLOR
            }
            Behavior on opacity {
                NumberAnimation {
                    duration: util.ANIM_DURATION_MS // 3
                    easing.type: Easing.OutQuad
                }
            }
            Behavior on width {
                NumberAnimation {
                    duration: util.ANIM_DURATION_MS // 3
                    easing.type: Easing.OutQuad
                }
            }
            Behavior on height {
                NumberAnimation {
                    duration: util.ANIM_DURATION_MS // 3
                    easing.type: Easing.OutQuad
                }
            }

        }

    }    
    contentItem: PK.Text {
        text: root.text
        font: root.font
        verticalAlignment: Text.AlignVCenter
        leftPadding: root.indicator.width + root.spacing
        color: root.textColor // enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
    }
}
