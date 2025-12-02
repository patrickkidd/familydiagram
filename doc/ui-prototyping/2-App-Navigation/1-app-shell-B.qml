import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Variant B: Header Workspace Switcher
// Diagram selection in global header, avatar for account menu

Rectangle {
    id: root
    anchors.fill: parent
    color: isDarkMode ? "#1e1e1e" : "#f5f5f5"

    property bool isDarkMode: true
    property int currentTab: 0
    property string currentDiagram: "Smith Family"
    property bool diagramMenuOpen: false
    property bool avatarMenuOpen: false

    // Colors
    property color windowBg: isDarkMode ? "#1e1e1e" : "#f5f5f5"
    property color headerBg: isDarkMode ? "#2d2b2a" : "#ffffff"
    property color itemBg: isDarkMode ? "#373534" : "#ffffff"
    property color borderColor: isDarkMode ? "#4d4c4c" : "#d8d8d8"
    property color textColor: isDarkMode ? "#ffffff" : "#000000"
    property color secondaryText: isDarkMode ? "#888888" : "#666666"
    property color accentColor: "#007AFF"
    property color tabBarBg: isDarkMode ? "#1c1c1e" : "#f8f8f8"
    property color overlayBg: isDarkMode ? "rgba(0,0,0,0.5)" : "rgba(0,0,0,0.3)"

    // Global Header with Workspace Switcher
    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60
        color: headerBg
        z: 50

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: borderColor
        }

        // Diagram Picker (left side)
        Rectangle {
            id: diagramPicker
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: diagramRow.width + 24
            height: 36
            radius: 8
            color: diagramMenuOpen ? (isDarkMode ? "#4a4a4a" : "#e0e0e0") : "transparent"

            Row {
                id: diagramRow
                anchors.centerIn: parent
                spacing: 6

                Text {
                    text: currentDiagram
                    font.pixelSize: 16
                    font.bold: true
                    color: textColor
                }

                Text {
                    text: "▼"
                    font.pixelSize: 10
                    color: secondaryText
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    diagramMenuOpen = !diagramMenuOpen
                    avatarMenuOpen = false
                }
            }
        }

        // Right side: PDP badge + Avatar
        Row {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            // PDP Badge (notification bell)
            Rectangle {
                width: 40
                height: 40
                radius: 20
                color: "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "🔔"
                    font.pixelSize: 20
                }

                Rectangle {
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.topMargin: 2
                    anchors.rightMargin: 2
                    width: 18
                    height: 18
                    radius: 9
                    color: "#FF3B30"

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

            // Avatar
            Rectangle {
                id: avatarBtn
                width: 36
                height: 36
                radius: 18
                color: accentColor
                border.width: avatarMenuOpen ? 2 : 0
                border.color: textColor

                Text {
                    anchors.centerIn: parent
                    text: "PK"
                    color: "white"
                    font.pixelSize: 13
                    font.bold: true
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        avatarMenuOpen = !avatarMenuOpen
                        diagramMenuOpen = false
                    }
                }
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
                anchors.bottom: inputArea.top
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
    }

    // Tab Bar with Add Event button
    Rectangle {
        id: tabBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 83
        color: tabBarBg
        z: 40

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
                    { icon: "💬", label: "Discuss", isAdd: false },
                    { icon: "📊", label: "Learn", isAdd: false },
                    { icon: "📅", label: "Plan", isAdd: false },
                    { icon: "+", label: "Event", isAdd: true }
                ]

                Rectangle {
                    width: root.width / 4
                    height: 49
                    color: "transparent"

                    Column {
                        anchors.centerIn: parent
                        spacing: 2

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: modelData.isAdd ? 32 : 28
                            height: modelData.isAdd ? 32 : 28
                            radius: modelData.isAdd ? 16 : 0
                            color: modelData.isAdd ? "#34C759" : "transparent"

                            Text {
                                anchors.centerIn: parent
                                text: modelData.icon
                                font.pixelSize: modelData.isAdd ? 20 : 22
                                font.bold: modelData.isAdd
                                color: modelData.isAdd ? "white" : textColor
                                opacity: (!modelData.isAdd && currentTab === index) ? 1.0 : (modelData.isAdd ? 1.0 : 0.5)
                            }
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.label
                            font.pixelSize: 10
                            color: modelData.isAdd ? "#34C759" : (currentTab === index ? accentColor : secondaryText)
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (modelData.isAdd) {
                                console.log("Open event form")
                            } else {
                                currentTab = index
                            }
                        }
                    }
                }
            }
        }
    }

    // Overlay for menus
    Rectangle {
        anchors.fill: parent
        color: overlayBg
        visible: diagramMenuOpen || avatarMenuOpen
        z: 60

        MouseArea {
            anchors.fill: parent
            onClicked: {
                diagramMenuOpen = false
                avatarMenuOpen = false
            }
        }
    }

    // Diagram dropdown menu
    Rectangle {
        id: diagramMenu
        anchors.top: header.bottom
        anchors.topMargin: -1
        anchors.left: parent.left
        anchors.leftMargin: 12
        width: 220
        height: diagramMenuContent.height
        radius: 12
        color: itemBg
        border.width: 1
        border.color: borderColor
        visible: diagramMenuOpen
        z: 70

        Column {
            id: diagramMenuContent
            width: parent.width
            padding: 8

            Repeater {
                model: ListModel {
                    ListElement { name: "Smith Family"; isCurrent: true }
                    ListElement { name: "Jones Family"; isCurrent: false }
                    ListElement { name: "Work Team"; isCurrent: false }
                }

                Rectangle {
                    width: parent.width - 16
                    height: 44
                    radius: 8
                    color: model.isCurrent ? (isDarkMode ? "#4a4a4a" : "#e8e8e8") : "transparent"
                    x: 8

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 8

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: model.isCurrent ? "★" : "☆"
                            color: model.isCurrent ? "#FFD60A" : secondaryText
                            font.pixelSize: 14
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
                        text: "✓"
                        color: accentColor
                        font.pixelSize: 14
                        visible: model.isCurrent
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            currentDiagram = model.name
                            diagramMenuOpen = false
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width - 16
                height: 1
                color: borderColor
                x: 8
            }

            Rectangle {
                width: parent.width - 16
                height: 44
                radius: 8
                color: "transparent"
                x: 8

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    spacing: 8

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "+"
                        color: accentColor
                        font.pixelSize: 16
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
                    onClicked: {
                        diagramMenuOpen = false
                        console.log("Create new diagram")
                    }
                }
            }
        }
    }

    // Avatar dropdown menu
    Rectangle {
        id: avatarMenu
        anchors.top: header.bottom
        anchors.topMargin: -1
        anchors.right: parent.right
        anchors.rightMargin: 12
        width: 180
        height: avatarMenuContent.height
        radius: 12
        color: itemBg
        border.width: 1
        border.color: borderColor
        visible: avatarMenuOpen
        z: 70

        Column {
            id: avatarMenuContent
            width: parent.width
            padding: 8

            Repeater {
                model: ["Settings", "Help & Support"]

                Rectangle {
                    width: parent.width - 16
                    height: 44
                    radius: 8
                    color: "transparent"
                    x: 8

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData
                        color: textColor
                        font.pixelSize: 15
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            avatarMenuOpen = false
                            console.log("Open " + modelData)
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width - 16
                height: 1
                color: borderColor
                x: 8
            }

            Rectangle {
                width: parent.width - 16
                height: 44
                radius: 8
                color: "transparent"
                x: 8

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Log Out"
                    color: "#FF3B30"
                    font.pixelSize: 15
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        avatarMenuOpen = false
                        console.log("Log out")
                    }
                }
            }
        }
    }

    // Mode toggle (for prototype only)
    Rectangle {
        anchors.bottom: tabBar.top
        anchors.right: parent.right
        anchors.margins: 8
        width: 50
        height: 24
        radius: 12
        color: isDarkMode ? "#373534" : "#e0e0e0"
        z: 30

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
