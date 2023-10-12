import QtQuick 2.12 as Q
import QtQuick.Controls 2.12 as QC
import QtGraphicalEffects 1.13

Q.Item {

    id: root
    property var source
    property bool invert: false

    Q.Image {
        id: mainImage
        source: '../' + root.source
        anchors.fill: parent
    }

    Q.Image {
        id: allWhite
        visible: false
        source: '../../all-white.png'
    }

    Blend {
        visible: invert
        source: mainImage
        foregroundSource: allWhite
        mode: 'negation'
        anchors.fill: parent
    }
}