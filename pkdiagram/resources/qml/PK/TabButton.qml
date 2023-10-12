import QtQuick 2.12
import QtQuick.Controls 2.5 as C

// just disable key activity for crying out loud
C.TabButton {

    id: root

    font.pixelSize: util.TEXT_FONT_SIZE    

    Keys.priority: Keys.BeforeItem
    Keys.onPressed: event.accepted = true
    Keys.onReleased: event.accepted = true
    
    Connections {
        target: background
        function onColorChanged() { contentItem.color = util.contrastTo(background.color) }
    }
    
}


