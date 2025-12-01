/*
The content of the left navigation drawer. Contains account info, diagram list,
settings, and logout.
*/

import QtQuick 2.15
import QtQuick.Controls 2.15
import "../PK" 1.0 as PK

Flickable {
    id: root

    property color itemBg: util.QML_ITEM_BG
    property color borderColor: util.QML_ITEM_BORDER_COLOR
    property color textColor: util.QML_TEXT_COLOR
    property color secondaryText: util.QML_INACTIVE_TEXT_COLOR
    property color accentColor: util.QML_SELECTION_COLOR

    signal logoutClicked()
    signal accountClicked()
    signal diagramClicked(var diagram)
    signal newDiagramClicked()
    signal settingsClicked(string setting)

    contentHeight: content.height
    clip: true

    Column {
        id: content
        width: parent.width
        spacing: 20
        topPadding: 16
        leftPadding: 16
        rightPadding: 16
        bottomPadding: 40

        // Account section
        Text {
            text: "ACCOUNT"
            font.pixelSize: 12
            font.bold: true
            color: secondaryText
            leftPadding: 4
        }

        Rectangle {
            width: parent.width - 32
            height: 60
            radius: 12
            color: itemBg
            border.width: 1
            border.color: borderColor

            Row {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                Rectangle {
                    width: 36
                    height: 36
                    radius: 18
                    color: accentColor

                    Text {
                        anchors.centerIn: parent
                        text: {
                            if (session && session.userDict) {
                                var fn = session.userDict.first_name || ""
                                var ln = session.userDict.last_name || ""
                                return (fn.charAt(0) + ln.charAt(0)).toUpperCase()
                            }
                            return "?"
                        }
                        color: "white"
                        font.pixelSize: 14
                        font.bold: true
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        text: {
                            if (session && session.userDict) {
                                var fn = session.userDict.first_name || ""
                                var ln = session.userDict.last_name || ""
                                return fn + " " + ln
                            }
                            return "User"
                        }
                        color: textColor
                        font.pixelSize: 15
                    }

                    Text {
                        text: session && session.userDict ? (session.userDict.username || "") : ""
                        color: secondaryText
                        font.pixelSize: 13
                    }
                }
            }

            Text {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "›"
                color: secondaryText
                font.pixelSize: 20
            }

            MouseArea {
                anchors.fill: parent
                onClicked: root.accountClicked()
            }
        }

        // Diagrams section
        Text {
            text: "DIAGRAMS"
            font.pixelSize: 12
            font.bold: true
            color: secondaryText
            leftPadding: 4
        }

        Rectangle {
            width: parent.width - 32
            height: diagramsColumn.height
            radius: 12
            color: itemBg
            border.width: 1
            border.color: borderColor

            Column {
                id: diagramsColumn
                width: parent.width

                Repeater {
                    model: personalApp ? personalApp.diagrams : []

                    Rectangle {
                        width: parent.width
                        height: 50
                        color: "transparent"

                        property bool isCurrent: personalApp && personalApp.diagram && personalApp.diagram.id === modelData.id

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            Rectangle {
                                anchors.verticalCenter: parent.verticalCenter
                                width: 8
                                height: 8
                                radius: 4
                                color: isCurrent ? accentColor : "transparent"
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.name || "Diagram"
                                color: textColor
                                font.pixelSize: 15
                                font.weight: isCurrent ? Font.DemiBold : Font.Normal
                            }
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.left: parent.left
                            anchors.leftMargin: 28
                            anchors.right: parent.right
                            height: 1
                            color: borderColor
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.diagramClicked(modelData)
                        }
                    }
                }

                Rectangle {
                    id: newDiagramItem
                    width: parent.width
                    height: 50
                    color: "transparent"

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        spacing: 8

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "+"
                            color: accentColor
                            font.pixelSize: 18
                            font.bold: true
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "New Diagram"
                            color: accentColor
                            font.pixelSize: 15
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.newDiagramClicked()
                    }
                }
            }
        }

        // Settings section
        Text {
            text: "SETTINGS"
            font.pixelSize: 12
            font.bold: true
            color: secondaryText
            leftPadding: 4
        }

        Rectangle {
            width: parent.width - 32
            height: settingsCol.height
            radius: 12
            color: itemBg
            border.width: 1
            border.color: borderColor

            Column {
                id: settingsCol
                width: parent.width

                Repeater {
                    model: ["Privacy", "Help & Support"]

                    Rectangle {
                        width: parent.width
                        height: 50
                        color: "transparent"

                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData
                            color: textColor
                            font.pixelSize: 15
                        }

                        Text {
                            anchors.right: parent.right
                            anchors.rightMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            text: "›"
                            color: secondaryText
                            font.pixelSize: 20
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.left: parent.left
                            anchors.leftMargin: 12
                            anchors.right: parent.right
                            height: 1
                            color: borderColor
                            visible: index < 2
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.settingsClicked(modelData)
                        }
                    }
                }
            }
        }

        // Logout
        Rectangle {
            width: parent.width - 32
            height: 50
            radius: 12
            color: itemBg
            border.width: 1
            border.color: borderColor

            Text {
                anchors.centerIn: parent
                text: "Log Out"
                color: "#FF3B30"
                font.pixelSize: 15
            }

            MouseArea {
                anchors.fill: parent
                onClicked: root.logoutClicked()
            }
        }
    }
}
