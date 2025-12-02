import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

// FINAL: Header Dropdown for Discussions + Drawer for Diagrams/Account
// - Hamburger opens left drawer with Account, Diagrams, Settings
// - Tapping discussion title in header opens dropdown to switch discussions
// - Text-only tab bar (Discuss / Learn / Plan)
// - PDP badge in header (flat red circle)
// - iOS-style chat bubbles

Window {
    id: root
    visible: true
    width: 390
    height: 844
    title: "FINAL: App Shell"
    color: isDarkMode ? "#1e1e1e" : "#f5f5f5"

    property bool isDarkMode: true
    property int currentTab: 0
    property string currentDiagram: "Smith Family"
    property string currentDiscussion: "Session 1"
    property bool discussionMenuOpen: false

    property color headerBg: isDarkMode ? "#2d2b2a" : "#ffffff"
    property color itemBg: isDarkMode ? "#373534" : "#ffffff"
    property color borderColor: isDarkMode ? "#4d4c4c" : "#d8d8d8"
    property color textColor: isDarkMode ? "#ffffff" : "#000000"
    property color secondaryText: isDarkMode ? "#888888" : "#666666"
    property color accentColor: "#007AFF"
    property color tabBarBg: isDarkMode ? "#1c1c1e" : "#f8f8f8"
    property color drawerBg: isDarkMode ? "#252525" : "#ffffff"

    // Header
    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 56
        color: headerBg
        z: 50

        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: borderColor }

        // Hamburger
        Rectangle {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 40
            height: 40
            radius: 8
            color: drawer.position > 0 ? (isDarkMode ? "#4a4a4a" : "#e0e0e0") : "transparent"

            Column {
                anchors.centerIn: parent
                spacing: 5
                Repeater {
                    model: 3
                    Rectangle { width: 20; height: 2; radius: 1; color: textColor }
                }
            }
            MouseArea { anchors.fill: parent; onClicked: drawer.open() }
        }

        // Discussion title (tappable dropdown) - only on Discuss tab
        Rectangle {
            anchors.centerIn: parent
            width: titleRow.width + 16
            height: 36
            radius: 8
            color: (discussionMenuOpen && currentTab === 0) ? (isDarkMode ? "#4a4a4a" : "#e0e0e0") : "transparent"
            visible: currentTab === 0

            Row {
                id: titleRow
                anchors.centerIn: parent
                spacing: 6

                Text {
                    text: currentDiscussion
                    font.pixelSize: 17
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
                onClicked: discussionMenuOpen = !discussionMenuOpen
            }
        }

        // Static title for other tabs
        Text {
            anchors.centerIn: parent
            text: currentTab === 1 ? "Learn" : "Plan"
            font.pixelSize: 17
            font.bold: true
            color: textColor
            visible: currentTab !== 0
        }

        // PDP Badge
        Rectangle {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 28
            height: 28
            radius: 14
            color: "#FF3B30"
            Text { anchors.centerIn: parent; text: "3"; font.pixelSize: 13; font.bold: true; color: "white" }
            MouseArea { anchors.fill: parent; onClicked: console.log("Open PDP sheet") }
        }
    }

    // Content
    StackLayout {
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: tabBar.top
        currentIndex: currentTab

        // Discuss tab
        Rectangle {
            color: "transparent"
            ListView {
                anchors.fill: parent
                anchors.margins: 15
                anchors.bottomMargin: 70
                spacing: 10
                clip: true
                model: ListModel {
                    ListElement { isAI: false; msg: "My father was very distant growing up." }
                    ListElement { isAI: true; msg: "That sounds difficult. Can you tell me more about your relationship with him?" }
                    ListElement { isAI: false; msg: "He worked a lot. I barely saw him." }
                    ListElement { isAI: true; msg: "I've added an event to capture this. How old were you during this time?" }
                    ListElement { isAI: false; msg: "I was probably 8 or 9. My mom would make excuses for him." }
                    ListElement { isAI: true; msg: "It sounds like your mother played a mediating role. How did that affect your relationship with her?" }
                }
                delegate: Item {
                    width: parent.width
                    height: bubble.height
                    Rectangle {
                        id: bubble
                        width: Math.min(msgText.implicitWidth + 24, parent.width * 0.8)
                        height: msgText.implicitHeight + 20
                        radius: 18
                        color: model.isAI ? (isDarkMode ? "#373534" : "#e5e5ea") : accentColor
                        anchors.right: model.isAI ? undefined : parent.right
                        anchors.left: model.isAI ? parent.left : undefined
                        Text {
                            id: msgText
                            anchors.fill: parent
                            anchors.margins: 12
                            text: model.msg
                            wrapMode: Text.WordWrap
                            color: model.isAI ? textColor : "white"
                            font.pixelSize: 15
                        }
                    }
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 56
                color: headerBg
                Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: borderColor }
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width - 30
                    height: 36
                    radius: 18
                    color: isDarkMode ? "#3a3a3c" : "#e5e5ea"
                    Text { anchors.left: parent.left; anchors.leftMargin: 16; anchors.verticalCenter: parent.verticalCenter; text: "Message"; color: secondaryText; font.pixelSize: 15 }
                }
            }
        }

        // Learn tab
        Rectangle { color: "transparent"; Text { anchors.centerIn: parent; text: "Learn"; color: secondaryText; font.pixelSize: 16 } }

        // Plan tab
        Rectangle { color: "transparent"; Text { anchors.centerIn: parent; text: "Plan"; color: secondaryText; font.pixelSize: 16 } }
    }

    // Tab Bar
    Rectangle {
        id: tabBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 50
        color: tabBarBg
        z: 10

        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: borderColor }

        Row {
            anchors.fill: parent
            Repeater {
                model: ["Discuss", "Learn", "Plan"]
                Rectangle {
                    width: root.width / 3
                    height: parent.height
                    color: "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        font.pixelSize: 15
                        font.weight: currentTab === index ? Font.DemiBold : Font.Normal
                        color: currentTab === index ? accentColor : secondaryText
                    }
                    MouseArea { anchors.fill: parent; onClicked: { currentTab = index; discussionMenuOpen = false } }
                }
            }
        }
    }

    // Overlay for dropdown
    Rectangle {
        anchors.fill: parent
        color: isDarkMode ? "rgba(0,0,0,0.4)" : "rgba(0,0,0,0.2)"
        visible: discussionMenuOpen
        z: 55
        MouseArea { anchors.fill: parent; onClicked: discussionMenuOpen = false }
    }

    // Discussion dropdown
    Rectangle {
        anchors.top: header.bottom
        anchors.topMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        width: 220
        height: discussionDropdown.height
        radius: 12
        color: itemBg
        border.width: 1
        border.color: borderColor
        visible: discussionMenuOpen
        z: 60

        Column {
            id: discussionDropdown
            width: parent.width
            padding: 8

            // Current diagram label
            Rectangle {
                width: parent.width - 16
                height: 32
                color: "transparent"
                x: 8

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: currentDiagram
                    font.pixelSize: 12
                    font.bold: true
                    color: secondaryText
                }
            }

            Repeater {
                model: ListModel {
                    ListElement { name: "Session 1" }
                    ListElement { name: "Session 2" }
                    ListElement { name: "Intake Notes" }
                }

                Rectangle {
                    width: parent.width - 16
                    height: 44
                    radius: 8
                    color: currentDiscussion === model.name ? (isDarkMode ? "#4a4a4a" : "#e8e8e8") : "transparent"
                    x: 8

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        spacing: 8

                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 6
                            height: 6
                            radius: 3
                            color: currentDiscussion === model.name ? accentColor : "transparent"
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: model.name
                            color: textColor
                            font.pixelSize: 15
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: { currentDiscussion = model.name; discussionMenuOpen = false }
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
                    spacing: 6
                    Text { anchors.verticalCenter: parent.verticalCenter; text: "+"; color: accentColor; font.pixelSize: 16; font.bold: true }
                    Text { anchors.verticalCenter: parent.verticalCenter; text: "New Discussion"; color: accentColor; font.pixelSize: 15 }
                }
                MouseArea { anchors.fill: parent; onClicked: { discussionMenuOpen = false; console.log("New discussion") } }
            }
        }
    }

    // Drawer (diagrams + account)
    Drawer {
        id: drawer
        width: parent.width * 0.85
        height: parent.height
        edge: Qt.LeftEdge
        background: Rectangle { color: drawerBg }

        contentItem: Flickable {
            contentHeight: drawerContent.height
            clip: true

            Column {
                id: drawerContent
                width: parent.width
                spacing: 20
                topPadding: 16
                leftPadding: 16
                rightPadding: 16
                bottomPadding: 40

                // Account section
                Text { text: "ACCOUNT"; font.pixelSize: 12; font.bold: true; color: secondaryText; leftPadding: 4 }

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
                            width: 36; height: 36; radius: 18; color: accentColor
                            Text { anchors.centerIn: parent; text: "PK"; color: "white"; font.pixelSize: 14; font.bold: true }
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            Text { text: "Patrick Kidd"; color: textColor; font.pixelSize: 15 }
                            Text { text: "patrick@example.com"; color: secondaryText; font.pixelSize: 13 }
                        }
                    }
                    Text { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: "›"; color: secondaryText; font.pixelSize: 20 }
                    MouseArea { anchors.fill: parent; onClicked: console.log("Open account") }
                }

                // Diagrams section
                Text { text: "DIAGRAMS"; font.pixelSize: 12; font.bold: true; color: secondaryText; leftPadding: 4 }

                Rectangle {
                    width: parent.width - 32
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

                                    Rectangle {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: model.isCurrent ? accentColor : "transparent"
                                    }
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: model.name
                                        color: textColor
                                        font.pixelSize: 15
                                        font.weight: model.isCurrent ? Font.DemiBold : Font.Normal
                                    }
                                }

                                Rectangle {
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.leftMargin: 28
                                    anchors.right: parent.right
                                    height: 1
                                    color: borderColor
                                    visible: index < 2
                                }

                                MouseArea { anchors.fill: parent; onClicked: { currentDiagram = model.name; drawer.close() } }
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 50
                            color: "transparent"

                            Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: borderColor }

                            Row {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                spacing: 8
                                Text { anchors.verticalCenter: parent.verticalCenter; text: "+"; color: accentColor; font.pixelSize: 18; font.bold: true }
                                Text { anchors.verticalCenter: parent.verticalCenter; text: "New Diagram"; color: accentColor; font.pixelSize: 15 }
                            }
                            MouseArea { anchors.fill: parent; onClicked: console.log("New diagram") }
                        }
                    }
                }

                // Settings section
                Text { text: "SETTINGS"; font.pixelSize: 12; font.bold: true; color: secondaryText; leftPadding: 4 }

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
                            model: ["Notifications", "Privacy", "Help & Support"]
                            Rectangle {
                                width: parent.width
                                height: 50
                                color: "transparent"
                                Text { anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: textColor; font.pixelSize: 15 }
                                Text { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: "›"; color: secondaryText; font.pixelSize: 20 }
                                Rectangle { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.leftMargin: 12; anchors.right: parent.right; height: 1; color: borderColor; visible: index < 2 }
                                MouseArea { anchors.fill: parent; onClicked: console.log("Open " + modelData) }
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
                    Text { anchors.centerIn: parent; text: "Log Out"; color: "#FF3B30"; font.pixelSize: 15 }
                    MouseArea { anchors.fill: parent; onClicked: console.log("Log out") }
                }
            }
        }
    }
}
