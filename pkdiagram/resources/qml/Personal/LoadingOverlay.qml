import QtQuick 2.12
import QtQuick.Controls 2.15
import "../PK" 1.0 as PK

Rectangle {
    id: root

    property string text: "Loading..."
    // progress < 0: indeterminate spinner (legacy importOverlay behaviour, unchanged).
    // progress >= 0: determinate ProgressBar (0-100) + percent label.
    property real progress: -1

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
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            visible: root.progress >= 0
            from: 0; to: 100
            value: Math.max(0, root.progress)
        }

        PK.Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.progress >= 0 ? root.text + "  ·  " + Math.round(root.progress) + "%" : root.text
            color: util.QML_TEXT_COLOR
            font.pixelSize: 16
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
