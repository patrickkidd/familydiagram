import QtQuick 2.12 as Q
import QtQuick.Controls 2.15 as QC
import QtGraphicalEffects 1.13


QC.Label {
    color: enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR    
    property bool dropShadow: false
    layer.enabled: dropShadow
    layer.effect: DropShadow {
        verticalOffset: 2
        horizontalOffset: 2
        color: util.QML_DROP_SHADOW_COLOR
        radius: 1
        samples: 3
    }
}

