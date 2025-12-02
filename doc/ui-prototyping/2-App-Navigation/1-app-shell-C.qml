import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Variant C: Contextual Header + FAB + Left Drawer
// Clean header that changes per view, FAB for primary action, drawer for account/diagrams

Rectangle {
    id: root
    anchors.fill: parent
    color: isDarkMode ? "#1e1e1e" : "#f5f5f5"

    property bool isDarkMode: true
    property int currentTab: 0
    property string currentDiagram: "Smith Family"
    property string currentDiscussion: "Session 1"
    property bool drawerOpen: false

    // Colors
    property color windowBg: isDarkMode ? "#1e1e1e" : "#f5f5f5"
    property color headerBg: isDarkMode ? "#2d2b2a" : "#ffffff"
    property color itemBg: isDarkMode ? "#373534" : "#ffffff"
    property color borderColor: isDarkMode ? "#4d4c4c" : "#d8d8d8"
    property color textColor: isDarkMode ? "#ffffff" : "#000000"
    property color secondaryText: isDarkMode ? "#888888" : "#666666"
    property color accentColor: "#007AFF"
    property color tabBarBg: isDarkMode ? "#1c1c1e" : "#f8f8f8"
    property color drawerBg: isDarkMode ? "#252525" : "#ffffff"
    property color overlayBg: isDarkMode ? "rgba(0,0,0,0.5)" : "rgba(0,0,0,0.3)"

    // Contextual Header
    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60
        color: headerBg
        z: 40

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: borderColor
        }

        // Hamburger menu
        Rectangle {
            id: menuBtn
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 40
            height: 40
            radius: 8
            color: drawerOpen ? (isDarkMode ? "#4a4a4a" : "#e0e0e0") : "transparent"

            Column {
                anchors.centerIn: parent
                spacing: 4

                Repeater {
                    model: 3
                    Rectangle {
                        width: 18
                        height: 2
                        radius: 1
                        color: textColor
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: drawerOpen = !drawerOpen
            }
        }

        // Contextual title
        Text {
            anchors.centerIn: parent
            text: {
                switch(currentTab) {
                    case 0: return currentDiscussion
                    case 1: return "Timeline"
                    case 2: return "Plan"
                    default: return ""
                }
            }
            font.pixelSize: 17
            font.bold: true
            color: textColor
        }

        // PDP Badge (right side)
        Rectangle {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
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

            // Chat placeholder
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

            // FAB (Floating Action Button)
            Rectangle {
                id: fab
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.rightMargin: 20
                anchors.bottomMargin: 80
                width: 56
                height: 56
                radius: 28
                color: "#34C759"
                z: 30

                // Shadow
                layer.enabled: true
                layer.effect: Item {
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -4
                        radius: 32
                        color: "transparent"
                        border.width: 0

                        Rectangle {
                            anchors.fill: parent
                            anchors.topMargin: 4
                            radius: 32
                            color: isDarkMode ? "#000000" : "#00000030"
                            opacity: 0.3
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    text: "+"
                    font.pixelSize: 28
                    font.bold: true
                    color: "white"
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: console.log("Open event form")
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

    // Tab Bar
    Rectangle {
        id: tabBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 83
        color: tabBarBg
        z: 35

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
                    { icon: "📅", label: "Plan" }
                ]

                Rectangle {
                    width: root.width / 3
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

    // Drawer overlay
    Rectangle {
        anchors.fill: parent
        color: overlayBg
        visible: drawerOpen
        z: 50

        MouseArea {
            anchors.fill: parent
            onClicked: drawerOpen = false
        }
    }

    // Left Drawer
    Rectangle {
        id: drawer
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        width: parent.width * 0.8
        color: drawerBg
        visible: drawerOpen
        z: 60

        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: borderColor
        }

        Flickable {
            anchors.fill: parent
            anchors.topMargin: 60 // Safe area
            contentHeight: drawerContent.height
            clip: true

            Column {
                id: drawerContent
                width: parent.width
                spacing: 24
                padding: 16

                // Account section
                Rectangle {
                    width: parent.width - 32
                    height: 70
                    radius: 12
                    color: itemBg
                    border.width: 1
                    border.color: borderColor

                    Row {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12

                        Rectangle {
                            width: 46
                            height: 46
                            radius: 23
                            color: accentColor

                            Text {
                                anchors.centerIn: parent
                                text: "PK"
                                color: "white"
                                font.pixelSize: 16
                                font.bold: true
                            }
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter

                            Text {
                                text: "Patrick Kidd"
                                color: textColor
                                font.pixelSize: 16
                                font.bold: true
                            }

                            Text {
                                text: "patrick@example.com"
                                color: secondaryText
                                font.pixelSize: 13
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: console.log("Open account settings")
                    }
                }

                // Diagrams section
                Column {
                    width: parent.width - 32
                    spacing: 8

                    Text {
                        text: "DIAGRAMS"
                        font.pixelSize: 12
                        font.bold: true
                        color: secondaryText
                        leftPadding: 4
                    }

                    Repeater {
                        model: ListModel {
                            ListElement { name: "Smith Family"; isCurrent: true }
                            ListElement { name: "Jones Family"; isCurrent: false }
                            ListElement { name: "Work Team"; isCurrent: false }
                        }

                        Rectangle {
                            width: parent.width
                            height: 48
                            radius: 10
                            color: model.isCurrent ? (isDarkMode ? "#4a4a4a" : "#e8e8e8") : "transparent"

                            Row {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 10

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
                                    font.bold: model.isCurrent
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    currentDiagram = model.name
                                    drawerOpen = false
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 48
                        radius: 10
                        color: "transparent"

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            spacing: 10

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

                // Discussions section
                Column {
                    width: parent.width - 32
                    spacing: 8

                    Text {
                        text: "DISCUSSIONS"
                        font.pixelSize: 12
                        font.bold: true
                        color: secondaryText
                        leftPadding: 4
                    }

                    Repeater {
                        model: ["Session 1", "Session 2", "Intake Notes"]

                        Rectangle {
                            width: parent.width
                            height: 44
                            radius: 10
                            color: modelData === currentDiscussion ? (isDarkMode ? "#4a4a4a" : "#e8e8e8") : "transparent"

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 12
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData
                                color: textColor
                                font.pixelSize: 15
                                font.bold: modelData === currentDiscussion
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    currentDiscussion = modelData
                                    drawerOpen = false
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 44
                        radius: 10
                        color: "transparent"

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            spacing: 10

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "+"
                                color: accentColor
                                font.pixelSize: 16
                                font.bold: true
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "New Discussion"
                                color: accentColor
                                font.pixelSize: 15
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: console.log("Create new discussion")
                        }
                    }
                }

                // Spacer
                Item { width: 1; height: 20 }

                // Settings and Logout
                Column {
                    width: parent.width - 32
                    spacing: 4

                    Repeater {
                        model: ["Settings", "Help & Support"]

                        Rectangle {
                            width: parent.width
                            height: 44
                            radius: 10
                            color: "transparent"

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
                                onClicked: console.log("Open " + modelData)
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 44
                        radius: 10
                        color: "transparent"

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
                            onClicked: console.log("Log out")
                        }
                    }
                }
            }
        }
    }

    // Mode toggle (for prototype only)
    Rectangle {
        anchors.bottom: tabBar.top
        anchors.left: parent.left
        anchors.margins: 8
        width: 50
        height: 24
        radius: 12
        color: isDarkMode ? "#373534" : "#e0e0e0"
        z: 30
        visible: !drawerOpen

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
