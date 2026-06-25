import QtQuick 2.12
import QtQuick.Controls 2.15
import "../PK" 1.0 as PK

Rectangle {
    id: root

    property string text: "Loading..."
    // progress < 0: indeterminate spinner (legacy importOverlay behaviour, unchanged).
    // progress >= 0: determinate ProgressBar (0-100) + percent label.
    property real progress: -1
    // When true, show a Cancel button (used by the long rebuild) that emits cancelClicked().
    property bool cancellable: false
    signal cancelClicked()

    parent: Overlay.overlay
    anchors.fill: parent
    visible: false
    color: util.QML_HEADER_BG
    z: 1000

    MouseArea {
        anchors.fill: parent
        onClicked: {}
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -42
        spacing: 20
        width: parent.width * 0.7

        BusyIndicator {
            id: busyIndicator
            anchors.horizontalCenter: parent.horizontalCenter
            running: root.visible && root.progress < 0
            visible: root.progress < 0
            width: 64
            height: 64
            contentItem: Item {
                implicitWidth: 64
                implicitHeight: 64
                Rectangle {
                    id: spinner
                    width: parent.width
                    height: parent.height
                    radius: width / 2
                    color: "transparent"
                    border.width: 4
                    border.color: util.QML_INACTIVE_TEXT_COLOR
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: util.QML_SELECTION_COLOR
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 2
                    }
                    RotationAnimator {
                        target: spinner
                        from: 0
                        to: 360
                        duration: 1000
                        loops: Animation.Infinite
                        running: busyIndicator.running
                    }
                }
            }
        }

        ProgressBar {
            id: progressBar
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            height: 6
            visible: root.progress >= 0
            from: 0; to: 100
            value: Math.max(0, root.progress)
            // Explicit track + fill so the bar is visible on the dark overlay
            // (the default style's track blends into QML_HEADER_BG).
            background: Rectangle {
                implicitHeight: 6
                radius: 3
                color: util.IS_UI_DARK_MODE ? "#4d4c4c" : "#d8d8d8"
            }
            contentItem: Item {
                Rectangle {
                    width: progressBar.visualPosition * progressBar.width
                    height: parent.height
                    radius: 3
                    color: util.QML_SELECTION_COLOR
                }
            }
        }

        PK.Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.progress >= 0 ? root.text + "  ·  " + Math.round(root.progress) + "%" : root.text
            color: util.QML_TEXT_COLOR
            font.pixelSize: 16
            horizontalAlignment: Text.AlignHCenter
        }

        Rectangle {
            objectName: "rebuildOverlayCancelButton"
            anchors.horizontalCenter: parent.horizontalCenter
            visible: root.cancellable
            width: 130
            height: 40
            radius: 10
            color: util.QML_ITEM_ALTERNATE_BG
            PK.Text {
                anchors.centerIn: parent
                text: "Cancel"
                color: util.QML_TEXT_COLOR
                font.pixelSize: 15
            }
            MouseArea {
                anchors.fill: parent
                onClicked: root.cancelClicked()
            }
        }
    }
}
