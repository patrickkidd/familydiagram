import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Variant A: Profile Tab Pattern
// Adds a 4th "Me" tab for account, settings, and diagram selection

Rectangle {
    id: root
    anchors.fill: parent
    color: isDarkMode ? "#1e1e1e" : "#f5f5f5"

    property bool isDarkMode: true
    property int currentTab: 0
    property string currentDiagram: "Smith Family"

    // Colors
    property color windowBg: isDarkMode ? "#1e1e1e" : "#f5f5f5"
    property color headerBg: isDarkMode ? "#2d2b2a" : "#ffffff"
    property color itemBg: isDarkMode ? "#373534" : "#ffffff"
    property color borderColor: isDarkMode ? "#4d4c4c" : "#d8d8d8"
    property color textColor: isDarkMode ? "#ffffff" : "#000000"
    property color secondaryText: isDarkMode ? "#888888" : "#666666"
    property color accentColor: "#007AFF"
    property color tabBarBg: isDarkMode ? "#1c1c1e" : "#f8f8f8"

    // Header
    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60
        color: headerBg
        z: 10

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: borderColor
        }

        // Title based on current tab
        Text {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            text: {
                switch(currentTab) {
                    case 0: return "Discuss"
                    case 1: return "Learn"
                    case 2: return "Plan"
                    case 3: return "Account"
                    default: return ""
                }
            }
            font.pixelSize: 20
            font.bold: true
            color: textColor
        }

        // PDP Badge (notification style) - only on content tabs
        Rectangle {
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            width: 40
            height: 40
            radius: 20
            color: "transparent"
            visible: currentTab < 3

            Text {
                anchors.centerIn: parent
                text: "🔔"
                font.pixelSize: 20
            }

            // Badge count
            Rectangle {
                anchors.top: parent.top
                anchors.right: parent.right
                width: 18
                height: 18
                radius: 9
                color: "#FF3B30"
                visible: true

                Text {
                    anchors.centerIn: parent
                    text: "3"
                    font.pixelSize: 11
                    font.bold: true
                    color: "white"
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: console.log("Open PDP sheet")
            }
        }
    }

    // Content area
    StackLayout {
        id: contentStack
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: tabBar.top
        currentIndex: currentTab

        // Discuss Tab
        Rectangle {
            color: "transparent"

            // Discussions button
            Rectangle {
                id: discussionsBtn
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.margins: 15
                width: discussionsRow.width + 20
                height: 36
                radius: 8
                color: itemBg
                border.width: 1
                border.color: borderColor

                Row {
                    id: discussionsRow
                    anchors.centerIn: parent
                    spacing: 6
                    Text { text: "≡"; font.pixelSize: 16; color: textColor }
                    Text { text: "Discussions"; font.pixelSize: 14; color: textColor }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: console.log("Open discussions drawer")
                }
            }

            // Chat placeholder
            ListView {
                anchors.top: discussionsBtn.bottom
                anchors.topMargin: 15
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: addEventBtn.top
                anchors.bottomMargin: 15
                anchors.leftMargin: 15
                anchors.rightMargin: 15
                spacing: 10
                clip: true

                model: ListModel {
                    ListElement { isAI: false; msg: "My father was very distant growing up." }
                    ListElement { isAI: true; msg: "That sounds difficult. Can you tell me more about your relationship with him?" }
                    ListElement { isAI: false; msg: "He worked a lot. I barely saw him." }
                    ListElement { isAI: true; msg: "I've added an event to capture this. How old were you during this time?" }
                }

                delegate: Rectangle {
                    width: ListView.view.width * 0.8
                    height: msgText.implicitHeight + 20
                    radius: 12
                    color: model.isAI ? (isDarkMode ? "#373534" : "#e8e8e8") : accentColor
                    anchors.right: model.isAI ? undefined : parent.right
                    anchors.left: model.isAI ? parent.left : undefined

                    Text {
                        id: msgText
                        anchors.fill: parent
                        anchors.margins: 10
                        text: model.msg
                        wrapMode: Text.WordWrap
                        color: model.isAI ? textColor : "white"
                        font.pixelSize: 14
                    }
                }
            }

            // Add event button (inline)
            Rectangle {
                id: addEventBtn
                anchors.bottom: inputArea.top
                anchors.bottomMargin: 10
                anchors.left: parent.left
                anchors.leftMargin: 15
                width: addEventRow.width + 16
                height: 32
                radius: 16
                color: "#34C759"

                Row {
                    id: addEventRow
                    anchors.centerIn: parent
                    spacing: 4
                    Text { text: "+"; font.pixelSize: 16; font.bold: true; color: "white" }
                    Text { text: "Add Event"; font.pixelSize: 13; color: "white" }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: console.log("Open event form")
                }
            }

            // Input area
            Rectangle {
                id: inputArea
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 60
                color: headerBg

                Rectangle {
                    anchors.top: parent.top
                    width: parent.width
                    height: 1
                    color: borderColor
                }

                Rectangle {
                    anchors.centerIn: parent
                    anchors.leftMargin: 15
                    anchors.rightMargin: 15
                    width: parent.width - 30
                    height: 40
                    radius: 20
                    color: itemBg
                    border.width: 1
                    border.color: borderColor

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Type a message..."
                        color: secondaryText
                        font.pixelSize: 14
                    }
                }
            }
        }

        // Learn Tab
        Rectangle {
            color: "transparent"
            Text {
                anchors.centerIn: parent
                text: "SARF Graph View"
                color: secondaryText
                font.pixelSize: 16
            }
        }

        // Plan Tab
        Rectangle {
            color: "transparent"
            Text {
                anchors.centerIn: parent
                text: "Plan View"
                color: secondaryText
                font.pixelSize: 16
            }
        }

        // Me Tab (Account)
        Rectangle {
            color: "transparent"

            Flickable {
                anchors.fill: parent
                anchors.margins: 15
                contentHeight: meContent.height
                clip: true

                Column {
                    id: meContent
                    width: parent.width
                    spacing: 20

                    // Account section
                    Column {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: "ACCOUNT"
                            font.pixelSize: 12
                            font.bold: true
                            color: secondaryText
                        }

                        Rectangle {
                            width: parent.width
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
                                        text: "PK"
                                        color: "white"
                                        font.pixelSize: 14
                                        font.bold: true
                                    }
                                }

                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    Text {
                                        text: "Patrick Kidd"
                                        color: textColor
                                        font.pixelSize: 15
                                    }
                                    Text {
                                        text: "patrick@example.com"
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
                        }
                    }

                    // Diagrams section
                    Column {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: "DIAGRAMS"
                            font.pixelSize: 12
                            font.bold: true
                            color: secondaryText
                        }

                        Rectangle {
                            width: parent.width
                            height: diagramsCol.height
                            radius: 12
                            color: itemBg
                            border.width: 1
                            border.color: borderColor

                            Column {
                                id: diagramsCol
                                width: parent.width

                                Repeater {
                                    model: ListModel {
                                        ListElement { name: "Smith Family"; isCurrent: true }
                                        ListElement { name: "Jones Family"; isCurrent: false }
                                        ListElement { name: "Work Team"; isCurrent: false }
                                    }

                                    Rectangle {
                                        width: parent.width
                                        height: 50
                                        color: "transparent"

                                        Row {
                                            anchors.fill: parent
                                            anchors.leftMargin: 12
                                            anchors.rightMargin: 12
                                            spacing: 8

                                            Text {
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: model.isCurrent ? "★" : "☆"
                                                color: model.isCurrent ? "#FFD60A" : secondaryText
                                                font.pixelSize: 16
                                            }

                                            Text {
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: model.name
                                                color: textColor
                                                font.pixelSize: 15
                                            }
                                        }

                                        Text {
                                            anchors.right: parent.right
                                            anchors.rightMargin: 12
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: model.isCurrent ? "✓" : "›"
                                            color: model.isCurrent ? accentColor : secondaryText
                                            font.pixelSize: model.isCurrent ? 16 : 20
                                        }

                                        Rectangle {
                                            anchors.bottom: parent.bottom
                                            anchors.left: parent.left
                                            anchors.leftMargin: 44
                                            anchors.right: parent.right
                                            height: 1
                                            color: borderColor
                                            visible: index < 2
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: console.log("Switch to diagram: " + model.name)
                                        }
                                    }
                                }

                                // Add new diagram
                                Rectangle {
                                    width: parent.width
                                    height: 50
                                    color: "transparent"

                                    Rectangle {
                                        anchors.top: parent.top
                                        width: parent.width
                                        height: 1
                                        color: borderColor
                                    }

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
                                        onClicked: console.log("Create new diagram")
                                    }
                                }
                            }
                        }
                    }

                    // Settings section
                    Column {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: "SETTINGS"
                            font.pixelSize: 12
                            font.bold: true
                            color: secondaryText
                        }

                        Rectangle {
                            width: parent.width
                            height: settingsCol.height
                            radius: 12
                            color: itemBg
                            border.width: 1
                            border.color: borderColor

                            Column {
                                id: settingsCol
                                width: parent.width

                                Repeater {
                                    model: ["Notifications", "Privacy", "Help & Support"]

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
                                    }
                                }
                            }
                        }
                    }

                    // Logout button
                    Rectangle {
                        width: parent.width
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
                            onClicked: console.log("Log out")
                        }
                    }
                }
            }
        }
    }

    // Tab Bar
    Rectangle {
        id: tabBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 83 // 49 + 34 home indicator
        color: tabBarBg

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: borderColor
        }

        Row {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 4
            height: 49
            spacing: 0

            Repeater {
                model: [
                    { icon: "💬", label: "Discuss" },
                    { icon: "📊", label: "Learn" },
                    { icon: "📅", label: "Plan" },
                    { icon: "👤", label: "Me" }
                ]

                Rectangle {
                    width: root.width / 4
                    height: 49
                    color: "transparent"

                    Column {
                        anchors.centerIn: parent
                        spacing: 2

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.icon
                            font.pixelSize: 22
                            opacity: currentTab === index ? 1.0 : 0.5
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.label
                            font.pixelSize: 10
                            color: currentTab === index ? accentColor : secondaryText
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: currentTab = index
                    }
                }
            }
        }
    }

    // Mode toggle (for prototype only)
    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 8
        width: 50
        height: 24
        radius: 12
        color: isDarkMode ? "#373534" : "#e0e0e0"
        z: 100

        Text {
            anchors.centerIn: parent
            text: isDarkMode ? "🌙" : "☀️"
            font.pixelSize: 12
        }

        MouseArea {
            anchors.fill: parent
            onClicked: isDarkMode = !isDarkMode
        }
    }
}
