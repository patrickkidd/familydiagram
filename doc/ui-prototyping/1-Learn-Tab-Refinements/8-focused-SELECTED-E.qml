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

    // FOCUSED VIEW: D-based with even bigger close button
    property int heroMargin: 16
    property int heroRadius: 16
    property int titleBarHeight: 36  // Slightly taller to fit bigger button
    property int navButtonSize: 40
    property int closeBtnSize: 44  // Full iOS tap target

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
            height: 240

            Rectangle {
                id: heroCard
                anchors.fill: parent
                anchors.margins: heroMargin
                radius: heroRadius
                color: "#151520"
                border.color: patternColor
                border.width: 2

                // Title bar - taller to accommodate bigger close button
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
                        x: 14
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Work Stress and Initial Reactions"
                        font.pixelSize: 14
                        font.bold: true
                        color: "white"
                        width: parent.width - closeBtnSize - 80
                        elide: Text.ElideRight
                    }

                    Text {
                        anchors.right: closeBtn.left
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: "5 events"
                        font.pixelSize: 12
                        color: "#ffffffdd"
                    }

                    // 44px close button - full iOS tap target
                    Rectangle {
                        id: closeBtn
                        anchors.right: parent.right
                        anchors.rightMargin: -4  // Slight overhang OK
                        anchors.verticalCenter: parent.verticalCenter
                        width: closeBtnSize; height: closeBtnSize; radius: closeBtnSize / 2
                        color: "#00000050"

                        Text {
                            anchors.centerIn: parent
                            text: "\u2715"
                            font.pixelSize: 20
                            font.bold: true
                            color: "#ffffff"
                        }
                    }
                }

                // Graph area mock
                Item {
                    anchors.top: titleBar.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 10

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
                        font.pixelSize: 11
                        font.italic: true
                        color: textSecondary
                        opacity: 0.7
                    }
                }
            }
        }

        // Navigation row
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 16
            height: 52

            Rectangle {
                width: navButtonSize; height: navButtonSize; radius: navButtonSize / 2
                color: "#333340"
                anchors.verticalCenter: parent.verticalCenter
                Text { anchors.centerIn: parent; text: "\u25C0"; font.pixelSize: 15; color: textPrimary }
            }

            Column {
                width: 160
                anchors.verticalCenter: parent.verticalCenter
                spacing: 3
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Work Stress and..."; font.pixelSize: 14; font.bold: true; color: patternColor; elide: Text.ElideRight; width: parent.width; horizontalAlignment: Text.AlignHCenter }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "1 / 13"; font.pixelSize: 13; color: textSecondary }
            }

            Rectangle {
                width: navButtonSize; height: navButtonSize; radius: navButtonSize / 2
                color: "#333340"
                anchors.verticalCenter: parent.verticalCenter
                Text { anchors.centerIn: parent; text: "\u25B6"; font.pixelSize: 15; color: textPrimary }
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - 342
            color: "#1a1a22"

            Text {
                anchors.centerIn: parent
                text: "(Event list - not part of this mockup)"
                font.pixelSize: 13
                color: textSecondary
                opacity: 0.5
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 10
        width: labelText.width + 16; height: 24; radius: 4; color: "#333340"
        Text { id: labelText; anchors.centerIn: parent; text: "E: 44px close button (full iOS tap target)"; font.pixelSize: 11; color: textSecondary }
    }
}
