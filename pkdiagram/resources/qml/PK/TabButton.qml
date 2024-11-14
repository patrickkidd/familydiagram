import QtQuick 2.12
import QtQuick.Controls 2.5 as C
import QtQuick.Controls.impl 2.12

// just disable key activity for crying out loud
C.TabButton {

    id: root

    font.pixelSize: util.TEXT_FONT_SIZE

    Keys.priority: Keys.BeforeItem
    Keys.onPressed: event.accepted = true
    Keys.onReleased: event.accepted = true
    
    contentItem: IconLabel {
        spacing: root.spacing
        mirrored: root.mirrored
        display: root.display

        icon: root.icon
        text: root.text
        font: root.font
        color: {
            if(enabled) {
                if(util.QML_ACTIVE_TEXT_COLOR) {
                    util.QML_ACTIVE_TEXT_COLOR
                } else {
                    '#f00'
                    // '#ffffff'
                }
            }
            else {
                if (util.QML_INACTIVE_TEXT_COLOR) {
                    util.QML_INACTIVE_TEXT_COLOR
                } else {
                    '#0f0'
                    // '#ffffff'
                }
            }
        }
    }

    Connections {
        target: background
        function onColorChanged() { contentItem.color = util.contrastTo(background.color) }
    }
    
}


