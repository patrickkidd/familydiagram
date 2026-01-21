import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    anchors.fill: parent
    color: "#1e1e1e"

    property color textPrimary: "#ffffff"
    property color textSecondary: "#909098"
    property color cardBg: "#252535"
    property color accentColor: "#0a84ff"
    property color patternColor: "#e67e22"

    property color symptomColor: "#e05555"
    property color anxietyColor: "#40a060"
    property color relationshipColor: "#5080d0"
    property color functioningColor: "#909090"

    // FOCUSED VIEW: Tight spacing
    property int heroMargin: 8
    property int heroRadius: 12
    property int titleBarHeight: 24
    property int navButtonSize: 28
    property int eventSpacing: 6

    Column {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            width: parent.width; height: 50; color: "#323232"
            Text { anchors.centerIn: parent; text: "The Story"; font.pixelSize: 17; font.bold: true; color: textPrimary }
        }

        // Focused cluster hero view
        Item {
            width: parent.width
            height: 280

            Rectangle {
                id: heroCard
                anchors.fill: parent
                anchors.margins: heroMargin
                radius: heroRadius
                color: "#151520"
                border.color: patternColor
                border.width: 2

                // Title bar
                Rectangle {
                    id: titleBar
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: titleBarHeight
                    color: patternColor
                    radius: heroRadius

                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: heroRadius
                        color: parent.color
                    }

                    Text {
                        x: 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Work Stress and Initial Reactions"
                        font.pixelSize: 11
                        font.bold: true
                        color: "white"
                    }

                    Text {
                        anchors.right: closeBtn.left
                        anchors.rightMargin: 6
                        anchors.verticalCenter: parent.verticalCenter
                        text: "5 events"
                        font.pixelSize: 9
                        color: "#ffffffaa"
                    }

                    Rectangle {
                        id: closeBtn
                        anchors.right: parent.right
                        anchors.rightMargin: 4
                        anchors.verticalCenter: parent.verticalCenter
                        width: 18; height: 18; radius: 9
                        color: "#00000030"
                        Text { anchors.centerIn: parent; text: "\u2715"; font.pixelSize: 10; color: "#ffffffcc" }
                    }
                }

                // Graph area mock
                Item {
                    anchors.top: titleBar.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 6

                    // Mock graph lines
                    Canvas {
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.strokeStyle = anxietyColor
                            ctx.lineWidth = 2
                            ctx.beginPath()
                            ctx.moveTo(20, height * 0.7)
                            ctx.lineTo(width * 0.3, height * 0.5)
                            ctx.lineTo(width * 0.6, height * 0.4)
                            ctx.lineTo(width - 20, height * 0.3)
                            ctx.stroke()

                            ctx.strokeStyle = symptomColor
                            ctx.beginPath()
                            ctx.moveTo(20, height * 0.3)
                            ctx.lineTo(width * 0.3, height * 0.4)
                            ctx.lineTo(width * 0.6, height * 0.5)
                            ctx.lineTo(width - 20, height * 0.6)
                            ctx.stroke()
                        }
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        text: "tap bands for details"
                        font.pixelSize: 8
                        font.italic: true
                        color: textSecondary
                        opacity: 0.6
                    }
                }
            }
        }

        // Navigation row
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8
            height: 36

            Rectangle {
                width: navButtonSize; height: navButtonSize; radius: navButtonSize / 2
                color: "#333340"
                Text { anchors.centerIn: parent; text: "\u25C0"; font.pixelSize: 11; color: textPrimary }
            }

            Column {
                width: 120
                anchors.verticalCenter: parent.verticalCenter
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Work Stress and..."; font.pixelSize: 11; font.bold: true; color: patternColor; elide: Text.ElideRight; width: parent.width; horizontalAlignment: Text.AlignHCenter }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "1 / 13"; font.pixelSize: 10; color: textSecondary }
            }

            Rectangle {
                width: navButtonSize; height: navButtonSize; radius: navButtonSize / 2
                color: "#333340"
                Text { anchors.centerIn: parent; text: "\u25B6"; font.pixelSize: 11; color: textPrimary }
            }
        }

        // Event list
        ListView {
            width: parent.width
            height: parent.height - 366
            clip: true
            spacing: eventSpacing
            topMargin: 8
            model: 5

            delegate: Rectangle {
                width: ListView.view.width - 24
                x: 12
                height: 56
                color: "transparent"

                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10
                    x: 8

                    Rectangle { width: 3; height: 40; radius: 1.5; color: index % 2 == 0 ? anxietyColor : symptomColor }

                    Column {
                        spacing: 2
                        Row {
                            spacing: 8
                            Text { text: "May 16, 2025"; font.pixelSize: 12; font.bold: true; color: anxietyColor }
                            Text { text: "User"; font.pixelSize: 12; color: textSecondary }
                        }
                        Text { text: "Stressed with race committee"; font.pixelSize: 14; color: textPrimary }
                    }
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: "#2a2a38"
                }
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 10
        width: labelText.width + 16; height: 24; radius: 4; color: "#333340"
        Text { id: labelText; anchors.centerIn: parent; text: "A: Tight (8px hero margin, 24px title)"; font.pixelSize: 11; color: textSecondary }
    }
}
