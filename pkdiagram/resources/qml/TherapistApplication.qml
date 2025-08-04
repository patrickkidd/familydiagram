/*
Manages the safe areas and any application-level handlers and logic.
*/

import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import "./Therapist" 1.0 as Therapist

ApplicationWindow {
    visible: true
    width: 400
    height: 600

    flags: Qt.Window | Qt.MaximizeUsingFullscreenGeometryHint
    color: util.QML_WINDOW_BG

    property var safeAreaMargins_left: 0
    property var safeAreaMargins_right: 0
    property var safeAreaMargins_top: 0
    property var safeAreaMargins_bottom: 0

    Rectangle {
        id: contentArea
        anchors {
            fill: parent
            leftMargin: safeAreaMargins_left
            rightMargin: safeAreaMargins_right
            topMargin: safeAreaMargins_top
            bottomMargin: Qt.inputMethod.visible ? 0 : safeAreaMargins_bottom
        }

        function adjustScreenMargins() {
            var safeAreaMargins = util.safeAreaMargins()
            // print('left:', safeAreaMargins.left, 'right:', safeAreaMargins.right, 'top:', safeAreaMargins.top, 'bottom:', safeAreaMargins.bottom)

            safeAreaMargins_left = safeAreaMargins.left
            safeAreaMargins_right = safeAreaMargins.right
            safeAreaMargins_top = safeAreaMargins.top
            safeAreaMargins_bottom = safeAreaMargins.bottom
        }

        Component.onCompleted: adjustScreenMargins()

        Connections {
            target: CUtil
            function onSafeAreaMarginsChanged() {
                contentArea.adjustScreenMargins()
            }
        }

        Therapist.TherapistContainer {
            id: therapistView
            anchors.fill: parent
        }

    }
}