import QtQuick 2.12
import QtQuick.Controls 2.5
import "." 1.0 as PK


GroupBox {
    id: root
    property bool showFrame: true

    Component.onCompleted: {
        label.wrapMode = Text.WrapAnywhere
        label.color = Qt.binding(function() { return util.QML_ACTIVE_TEXT_COLOR })
        if(!showFrame) {
            background.border.color = 'transparent'
        }
    }
}
