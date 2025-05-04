import QtQuick 2.12

import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15

import "./PK" 1.0 as PK

ApplicationWindow {
    visible: true
    width: 400
    height: 600

    flags: Qt.Window | Qt.MaximizeUsingFullscreenGeometryHint
    color: util.QML_WINDOW_BG

    Rectangle {
        id: contentArea
        anchors {
            fill: parent
            leftMargin: 0
            rightMargin: 0
            topMargin: 0
            bottomMargin: 0
        }

        function adjustScreenMargins() {
            var safeAreaMargins = util.safeAreaMargins()
            // print('left:', safeAreaMargins.left, 'right:', safeAreaMargins.right, 'top:', safeAreaMargins.top, 'bottom:', safeAreaMargins.bottom)

            anchors.leftMargin = safeAreaMargins.left
            anchors.rightMargin = safeAreaMargins.right
            anchors.topMargin = safeAreaMargins.top
            anchors.bottomMargin = safeAreaMargins.bottom
        }

        Component.onCompleted: adjustScreenMargins()

        Connections {
            target: CUtil
            function onSafeAreaMarginsChanged() {
                contentArea.adjustScreenMargins()
            }
        }


        PK.TherapistView {
            id: therapistView
            anchors.fill: parent
        }

    }
}