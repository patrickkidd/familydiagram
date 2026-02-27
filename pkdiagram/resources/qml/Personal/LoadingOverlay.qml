import QtQuick 2.12
import QtQuick.Controls 2.15
import "../PK" 1.0 as PK

Rectangle {
    id: root

    property string text: "Loading..."

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

        BusyIndicator {
            id: busyIndicator
            anchors.horizontalCenter: parent.horizontalCenter
            running: root.visible
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

        PK.Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.text
            color: util.QML_TEXT_COLOR
            font.pixelSize: 16
        }
    }
}
