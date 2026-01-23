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

    property color symptomColor: "#e05555"
    property color anxietyColor: "#40a060"
    property color relationshipColor: "#5080d0"
    property color functioningColor: "#909090"

    // MARGINS: Generous (20px horizontal, 16px card spacing)
    property int hMargin: 20
    property int cardSpacing: 16
    property int cardPadding: 16

    Column {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            width: parent.width; height: 50; color: "#323232"
            Text { anchors.centerIn: parent; text: "The Story"; font.pixelSize: 17; font.bold: true; color: textPrimary }
        }

        Rectangle {
            width: parent.width; height: 160; color: "#151520"
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom; anchors.bottomMargin: 14
                spacing: 12
                Row { spacing: 4; Rectangle { width: 12; height: 12; radius: 2; color: symptomColor } Text { text: "Symptom"; font.pixelSize: 12; font.bold: true; color: symptomColor } }
                Row { spacing: 4; Rectangle { width: 12; height: 12; radius: 2; color: anxietyColor } Text { text: "Anxiety"; font.pixelSize: 12; font.bold: true; color: anxietyColor } }
                Row { spacing: 4; Rectangle { width: 12; height: 12; radius: 2; color: relationshipColor } Text { text: "Relationship"; font.pixelSize: 12; font.bold: true; color: relationshipColor } }
                Row { spacing: 4; Rectangle { width: 12; height: 12; radius: 2; color: functioningColor } Text { text: "Functioning"; font.pixelSize: 12; font.bold: true; color: functioningColor } }
            }
        }

        Rectangle {
            width: parent.width; height: 52; color: "#1a1a28"
            Row {
                x: hMargin; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                Rectangle { width: 40; height: 24; radius: 12; color: accentColor
                    Rectangle { width: 20; height: 20; radius: 10; color: "white"; x: parent.width - width - 2; anchors.verticalCenter: parent.verticalCenter }
                }
                Text { text: "Clusters"; font.pixelSize: 13; color: textSecondary; anchors.verticalCenter: parent.verticalCenter }
            }
            Row {
                anchors.right: parent.right; anchors.rightMargin: hMargin; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                Text { text: "13 clusters"; font.pixelSize: 13; color: textSecondary; anchors.verticalCenter: parent.verticalCenter }
                Rectangle { width: 90; height: 32; radius: 16; color: accentColor
                    Text { anchors.centerIn: parent; text: "Re-detect"; font.pixelSize: 13; font.bold: true; color: "white" }
                }
            }
        }

        ListView {
            width: parent.width
            height: parent.height - 262
            clip: true
            spacing: cardSpacing
            topMargin: cardSpacing
            model: 4

            delegate: Rectangle {
                width: ListView.view.width - (hMargin * 2)
                height: 72
                x: hMargin
                radius: 14
                color: cardBg
                border.color: index === 0 ? "#e67e22" : "#4d4c4c"
                border.width: 1

                Row {
                    anchors.left: parent.left; anchors.leftMargin: cardPadding
                    anchors.verticalCenter: parent.verticalCenter; spacing: 10
                    Text { text: "\u25BC"; font.pixelSize: 12; color: textSecondary }
                    Column {
                        spacing: 5
                        Row {
                            spacing: 8
                            Text { text: "Work Stress and Initial Reactions"; font.pixelSize: 15; font.bold: true; color: textPrimary }
                            Rectangle { width: 22; height: 22; radius: 11; color: anxietyColor
                                Text { anchors.centerIn: parent; text: "A"; font.pixelSize: 11; font.bold: true; color: "white" }
                            }
                        }
                        Row {
                            spacing: 8
                            Text { text: "2025-05-16 - 2025-05-17"; font.pixelSize: 12; color: textSecondary }
                            Rectangle { width: 100; height: 20; radius: 10; color: "#e67e22"
                                Text { anchors.centerIn: parent; text: "Work-Family"; font.pixelSize: 11; font.bold: true; color: "white" }
                            }
                            Text { text: "5 events"; font.pixelSize: 12; color: textSecondary }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 10
        width: labelText.width + 16; height: 24; radius: 4; color: "#333340"
        Text { id: labelText; anchors.centerIn: parent; text: "C: Generous (20px margins, 16px gaps)"; font.pixelSize: 11; color: textSecondary }
    }
}
