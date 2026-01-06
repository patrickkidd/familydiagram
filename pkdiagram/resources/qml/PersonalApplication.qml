/*
Manages the safe areas and any application-level handlers and logic.
*/

import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import "./Personal" 1.0 as Personal

ApplicationWindow {
    id: root
    visible: true
    width: 393
    height: 852

    flags: Qt.Window | Qt.MaximizeUsingFullscreenGeometryHint
    color: util.QML_WINDOW_BG

    property real safeAreaLeft: 0
    property real safeAreaRight: 0
    property real safeAreaTop: 0
    property real safeAreaBottom: 0

    property var personalView: personalView

    function adjustScreenMargins() {
        var margins = util.safeAreaMargins()
        safeAreaLeft = margins.left
        safeAreaRight = margins.right
        safeAreaTop = margins.top
        safeAreaBottom = margins.bottom
    }

    Component.onCompleted: adjustScreenMargins()

    Connections {
        target: CUtil
        function onSafeAreaMarginsChanged() {
            util.info("PersonalApplication.onSafeAreaMarginsChanged")
            root.adjustScreenMargins()
        }
    }

    Rectangle {
        id: contentArea
        anchors {
            fill: parent
            leftMargin: safeAreaLeft
            rightMargin: safeAreaRight
            topMargin: safeAreaTop
            bottomMargin: Qt.inputMethod.visible ? 0 : safeAreaBottom
        }

        Personal.PersonalContainer {
            id: personalView
            anchors.fill: parent
            safeAreaTop: root.safeAreaTop
            safeAreaBottom: root.safeAreaBottom
        }
    }
}