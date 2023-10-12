import QtQuick 2.12
import QtQuick.Controls 2.12


Tumbler {
    id: root
    background: Rectangle {
        color: 'transparent'
    }
    contentItem: ListView {
        model: root.model
        delegate: root.delegate
        snapMode: ListView.SnapToItem
        highlightRangeMode: ListView.StrictlyEnforceRange
        preferredHighlightBegin: height / 2 - (height / root.visibleItemCount / 2)
        preferredHighlightEnd: height / 2 + (height / root.visibleItemCount / 2)
        clip: true
        highlightMoveVelocity: 100
        highlightMoveDuration: 700
    }
}
