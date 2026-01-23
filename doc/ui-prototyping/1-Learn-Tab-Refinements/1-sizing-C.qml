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
    property color dividerColor: "#2a2a38"
    property color accentColor: "#0a84ff"

    property color symptomColor: "#e05555"
    property color anxietyColor: "#40a060"
    property color relationshipColor: "#5080d0"
    property color functioningColor: "#909090"

    Column {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 0

        // Header
        Rectangle {
            width: parent.width
            height: 50
            color: "#323232"

            Text {
                anchors.centerIn: parent
                text: "The Story"
                font.pixelSize: 17
                font.bold: true
                color: textPrimary
            }
        }

        // Graph area mock
        Rectangle {
            width: parent.width
            height: 180
            color: "#151520"

            // Legend - LARGE
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 16
                spacing: 14

                Row {
                    spacing: 5
                    Rectangle { width: 14; height: 14; radius: 3; color: symptomColor }
                    Text { text: "Symptom"; font.pixelSize: 14; font.bold: true; color: symptomColor }
                }
                Row {
                    spacing: 5
                    Rectangle { width: 14; height: 14; radius: 3; color: anxietyColor }
                    Text { text: "Anxiety"; font.pixelSize: 14; font.bold: true; color: anxietyColor }
                }
                Row {
                    spacing: 5
                    Rectangle { width: 14; height: 14; radius: 3; color: relationshipColor }
                    Text { text: "Relationship"; font.pixelSize: 14; font.bold: true; color: relationshipColor }
                }
                Row {
                    spacing: 5
                    Rectangle { width: 14; height: 14; radius: 3; color: functioningColor }
                    Text { text: "Functioning"; font.pixelSize: 14; font.bold: true; color: functioningColor }
                }
            }
        }

        // Controls row - LARGE (iOS 44pt touch targets)
        Rectangle {
            width: parent.width
            height: 56
            color: "#1a1a28"

            Row {
                x: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                Rectangle {
                    width: 50; height: 30; radius: 15
                    color: accentColor

                    Rectangle {
                        width: 26; height: 26; radius: 13
                        color: "white"
                        x: parent.width - width - 2
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                Text {
                    text: "Clusters"
                    font.pixelSize: 15
                    color: textSecondary
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                Text {
                    text: "13 clusters"
                    font.pixelSize: 15
                    color: textSecondary
                    anchors.verticalCenter: parent.verticalCenter
                }

                Rectangle {
                    width: 100
                    height: 40
                    radius: 20
                    color: accentColor

                    Text {
                        anchors.centerIn: parent
                        text: "Re-detect"
                        font.pixelSize: 15
                        font.bold: true
                        color: "white"
                    }
                }
            }
        }

        // Cluster cards
        ListView {
            width: parent.width
            height: parent.height - 286
            clip: true
            spacing: 12
            model: 4

            delegate: Rectangle {
                width: ListView.view.width - 32
                height: 84
                x: 16
                radius: 16
                color: cardBg
                border.color: "#e67e22"
                border.width: 1.5

                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12

                    Text {
                        text: "\u25B6"
                        font.pixelSize: 14
                        color: textSecondary
                    }

                    Column {
                        spacing: 6

                        Row {
                            spacing: 10
                            Text {
                                text: "Work Stress and Initial Reactions"
                                font.pixelSize: 17
                                font.bold: true
                                color: textPrimary
                            }
                            Rectangle {
                                width: 26; height: 26; radius: 13
                                color: anxietyColor
                                Text {
                                    anchors.centerIn: parent
                                    text: "A"
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: "white"
                                }
                            }
                        }

                        Row {
                            spacing: 10
                            Text {
                                text: "2025-05-16 - 2025-05-17"
                                font.pixelSize: 14
                                color: textSecondary
                            }
                            Rectangle {
                                width: 110; height: 24; radius: 12
                                color: "#e67e22"
                                Text {
                                    anchors.centerIn: parent
                                    text: "Work-Family"
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: "white"
                                }
                            }
                            Text {
                                text: "5 events"
                                font.pixelSize: 14
                                color: textSecondary
                            }
                        }
                    }
                }
            }
        }
    }

    // Label
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 10
        width: labelText.width + 16
        height: 24
        radius: 4
        color: "#333340"

        Text {
            id: labelText
            anchors.centerIn: parent
            text: "C: Large (14-17px fonts, 40px buttons)"
            font.pixelSize: 11
            color: textSecondary
        }
    }
}
