/*
The outer content container, shown within the device's safe areas. Contains the
header, drawer, tabs and switches between the main views.
*/

import QtQuick 2.15
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK
import ".." 1.0 as Root
import "." 1.0 as Personal


Page {
    id: root

    property var stack: stack
    property var tabBar: tabBar
    property var discussView: discussView
    property var learnView: learnView
    property var planView: planView
    property var accountDialog: accountDialogLoader.item
    property var drawer: drawer
    property var eventFormDrawer: eventFormDrawer
    property var eventForm: eventForm
    property var pdpSheet: discussView.pdpSheet

    property bool discussionMenuOpen: false
    property int pdpCount: 0
    property real safeAreaTop: 0

    // Colors
    property color headerBg: util.QML_HEADER_BG
    property color itemBg: util.QML_ITEM_BG
    property color borderColor: util.QML_ITEM_BORDER_COLOR
    property color textColor: util.QML_TEXT_COLOR
    property color secondaryText: util.QML_INACTIVE_TEXT_COLOR
    property color accentColor: util.QML_SELECTION_COLOR
    property color tabBarBg: util.QML_HEADER_BG
    property color drawerBg: util.QML_WINDOW_BG

    background: Rectangle {
        color: util.QML_WINDOW_BG
    }

    // Track PDP count from discussView
    Connections {
        target: personalApp
        function onPdpChanged() {
            var pdp = personalApp.pdp
            if (pdp) {
                var count = 0
                if (pdp.people) count += pdp.people.length
                if (pdp.events) count += pdp.events.length
                if (pdp.pair_bonds) count += pdp.pair_bonds.length
                root.pdpCount = count
            } else {
                root.pdpCount = 0
            }
        }
    }

    // Get current discussion summary for header title
    function currentDiscussionSummary() {
        if (personalApp && personalApp.discussions) {
            for (var i = 0; i < personalApp.discussions.length; i++) {
                var d = personalApp.discussions[i]
                if (d.id === personalApp.currentDiscussionId) {
                    return d.summary || "Discussion"
                }
            }
        }
        return "Discuss"
    }

    // Header
    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 56
        color: headerBg
        visible: session && session.loggedIn
        z: 10

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: borderColor
        }

        // Hamburger menu button
        Rectangle {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 40
            height: 40
            radius: 8
            color: drawer.position > 0 ? util.QML_ITEM_ALTERNATE_BG : "transparent"

            Column {
                anchors.centerIn: parent
                spacing: 5
                Repeater {
                    model: 3
                    Rectangle { width: 20; height: 2; radius: 1; color: textColor }
                }
            }
            MouseArea {
                anchors.fill: parent
                onClicked: drawer.open()
            }
        }

        // Discussion title (tappable dropdown) - only on Discuss tab
        Rectangle {
            anchors.centerIn: parent
            width: titleRow.width + 16
            height: 36
            radius: 8
            color: (discussionMenuOpen && tabBar.currentIndex === 0) ? util.QML_ITEM_ALTERNATE_BG : "transparent"
            visible: tabBar.currentIndex === 0

            Row {
                id: titleRow
                anchors.centerIn: parent
                spacing: 6

                Text {
                    text: currentDiscussionSummary()
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
            text: tabBar.currentIndex === 1 ? "Learn" : "Plan"
            font.pixelSize: 17
            font.bold: true
            color: textColor
            visible: tabBar.currentIndex !== 0
        }

        // PDP Badge (Discuss tab only)
        Rectangle {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 28
            height: 28
            radius: 14
            color: "#FF3B30"
            visible: pdpCount > 0 && tabBar.currentIndex === 0

            Text {
                anchors.centerIn: parent
                text: pdpCount.toString()
                font.pixelSize: 13
                font.bold: true
                color: "white"
            }
            MouseArea {
                anchors.fill: parent
                onClicked: pdpSheet.open()
            }
        }

        // Add Event button (Learn tab only)
        Rectangle {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 28
            height: 28
            radius: 14
            color: accentColor
            visible: tabBar.currentIndex === 1

            Text {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -1
                text: "+"
                font.pixelSize: 20
                font.weight: Font.Normal
                color: "#ffffff"
            }
            MouseArea {
                anchors.fill: parent
                onClicked: learnView.addEventRequested()
            }
        }
    }

    // Main content
    StackLayout {
        id: stack
        currentIndex: tabBar.currentIndex
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: tabBar.top
        visible: session && session.loggedIn

        Personal.DiscussView {
            id: discussView
            Layout.fillHeight: true
            Layout.fillWidth: true
        }

        Personal.LearnView {
            id: learnView
            Layout.fillHeight: true
            Layout.fillWidth: true
        }

        Personal.PlanView {
            id: planView
            Layout.fillHeight: true
            Layout.fillWidth: true
        }
    }

    // Tab Bar
    Rectangle {
        id: tabBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 50
        color: tabBarBg
        visible: session && session.loggedIn
        z: 10

        property int currentIndex: 0

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: borderColor
        }

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
                        font.weight: tabBar.currentIndex === index ? Font.DemiBold : Font.Normal
                        color: tabBar.currentIndex === index ? accentColor : secondaryText
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            tabBar.currentIndex = index
                            discussionMenuOpen = false
                        }
                    }
                }
            }
        }
    }

    // Invisible tap catcher for dropdown dismissal
    MouseArea {
        anchors.fill: parent
        visible: discussionMenuOpen
        z: 55
        onClicked: discussionMenuOpen = false
    }

    // Discussion dropdown
    Rectangle {
        id: discussionDropdownRect
        anchors.top: header.bottom
        anchors.topMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        width: 220
        height: discussionDropdown.height
        radius: 12
        color: itemBg
        border.width: 1
        border.color: borderColor
        visible: opacity > 0
        opacity: discussionMenuOpen ? 1 : 0
        scale: discussionMenuOpen ? 1 : 0.9
        transformOrigin: Item.Top
        z: 60

        Behavior on opacity {
            NumberAnimation { duration: 150; easing.type: Easing.OutQuad }
        }
        Behavior on scale {
            NumberAnimation { duration: 150; easing.type: Easing.OutBack; easing.overshoot: 1.5 }
        }

        // Shadow
        Rectangle {
            anchors.fill: parent
            anchors.margins: -1
            radius: parent.radius + 1
            color: "transparent"
            border.width: 0
            z: -1

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 4
                radius: parent.radius
                color: util.IS_UI_DARK_MODE ? "rgba(0,0,0,0.4)" : "rgba(0,0,0,0.15)"
                z: -1
            }
        }

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
                    text: personalApp && personalApp.diagram ? (personalApp.diagram.name || "Diagram") : "Diagram"
                    font.pixelSize: 12
                    font.bold: true
                    color: secondaryText
                }
            }

            Repeater {
                model: personalApp ? personalApp.discussions : []

                Rectangle {
                    width: discussionDropdown.width - 16
                    height: 44
                    radius: 8
                    color: personalApp && personalApp.currentDiscussionId === modelData.id ? util.QML_ITEM_ALTERNATE_BG : "transparent"
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
                            color: personalApp && personalApp.currentDiscussionId === modelData.id ? accentColor : "transparent"
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.summary || "Discussion"
                            color: textColor
                            font.pixelSize: 15
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            personalApp.setCurrentDiscussion(modelData.id)
                            discussionMenuOpen = false
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
                    spacing: 6
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
                    onClicked: {
                        discussionMenuOpen = false
                        personalApp.createDiscussion()
                    }
                }
            }
        }
    }

    // Left Drawer
    Drawer {
        id: drawer
        width: parent.width * 0.85
        height: parent.height
        edge: Qt.LeftEdge

        background: Rectangle { color: drawerBg }

        contentItem: Personal.AccountDrawer {
            anchors.fill: parent
            itemBg: root.itemBg
            borderColor: root.borderColor
            textColor: root.textColor
            secondaryText: root.secondaryText
            accentColor: root.accentColor
            safeAreaTop: root.safeAreaTop

            onLogoutClicked: {
                drawer.close()
                session.logout()
            }
            onAccountClicked: console.log("Open account settings")
            onDiagramClicked: function(diagram) {
                drawer.close()
                personalApp.loadDiagram(diagram.id)
            }
            onNewDiagramClicked: {
                drawer.close()
                personalApp.createDiagram()
            }
            onSettingsClicked: function(setting) {
                if (setting === "Privacy") {
                    privacyPopup.open()
                } else if (setting === "Help & Support") {
                    helpPopup.open()
                }
            }
        }
    }

    // Bottom sheet for EventForm (like PDPSheet)
    Drawer {
        id: eventFormDrawer
        width: parent.width
        height: parent.height
        edge: Qt.BottomEdge

        background: Rectangle { color: drawerBg }

        Root.EventForm {
            id: eventForm
            anchors.fill: parent
            showClearButton: false
            onCancel: eventFormDrawer.close()
            Component.onCompleted: personalApp.initEventForm(eventForm)
        }
    }

    // Connect LearnView add event signal
    Connections {
        target: learnView
        function onAddEventRequested() {
            eventForm.clear()
            eventForm.initWithNoSelection()
            eventFormDrawer.open()
        }
    }

    // Connect PersonalApp event form done signal
    Connections {
        target: personalApp
        function onEventFormDoneEditing() {
            eventFormDrawer.close()
        }
    }

    // Privacy settings popup
    Popup {
        id: privacyPopup
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: root.width
        height: root.height
        modal: true
        closePolicy: Popup.NoAutoClose
        padding: 0
        background: Rectangle { color: "transparent" }

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150 }
        }
        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 150 }
        }

        Personal.SettingsPage {
            anchors.fill: parent
            pageTitle: "Privacy"
            onBackClicked: privacyPopup.close()
        }
    }

    // Help & Support settings popup
    Popup {
        id: helpPopup
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: root.width
        height: root.height
        modal: true
        closePolicy: Popup.NoAutoClose
        padding: 0
        background: Rectangle { color: "transparent" }

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150 }
        }
        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 150 }
        }

        Personal.SettingsPage {
            anchors.fill: parent
            pageTitle: "Help & Support"
            onBackClicked: helpPopup.close()
        }
    }

    // Account Dialog overlay - shown when not logged in
    Loader {
        id: accountDialogLoader
        anchors.fill: parent
        active: session && !session.loggedIn
        source: "../AccountDialog.qml"

        onLoaded: {
            if (item) {
                item.done.connect(function() {
                    // Force refresh of session state
                })
            }
        }
    }

    focus: true
}
