/*
The outer content container, shown within the device's safe areas. Contains the
header, drawer, tabs and switches between the main views.
*/

import QtQuick 2.15
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Qt.labs.platform 1.0
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
    property var drawer: drawerLoader.item
    property var eventFormDrawer: eventFormDrawer
    property var eventForm: eventForm
    property var pdpSheet: discussView.pdpSheet

    // Hosted inside Pro's case drawer, on Pro's already-open case: everything
    // that picks or replaces the diagram, or that belongs to the phone user's
    // own account, is dropped (FD-336).
    property bool embedded: false

    property bool discussionMenuOpen: false
    property bool storyMenuOpen: false
    property bool importMenuOpen: false
    property int pdpCount: 0
    property real safeAreaTop: 0
    property real safeAreaBottom: 0

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
        target: pdpController
        function onPdpChanged() {
            var pdp = pdpController.pdp
            if (pdp) {
                // Every PDP entry is a reviewable pending change; the badge
                // must match the card count in PDPSheet (people + pair bonds
                // + events), or a non-empty PDP can show a "0" badge.
                // Parents-only edit rows render no card (PDPSheet filter).
                var count = 0
                if (pdp.people) {
                    for (var i = 0; i < pdp.people.length; i++) {
                        if (!pdpController.isParentsEdit(pdp.people[i]))
                            count += 1
                    }
                }
                if (pdp.pair_bonds) count += pdp.pair_bonds.length
                if (pdp.events) count += pdp.events.length
                if (pdp.delete) count += pdp.delete.length
                root.pdpCount = count
            } else {
                root.pdpCount = 0
            }
        }
    }

    Connections {
        target: pdpSheet
        function onItemAccepted() { root.pdpCount = Math.max(0, root.pdpCount - 1) }
        function onItemRejected() { root.pdpCount = Math.max(0, root.pdpCount - 1) }
    }

    // Get current discussion summary for header title
    function currentDiscussionSummary() {
        if (discussion && discussion.discussions) {
            for (var i = 0; i < discussion.discussions.length; i++) {
                var d = discussion.discussions[i]
                if (d.id === discussion.currentDiscussionId) {
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
            objectName: "hamburgerButton"
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 40
            height: 40
            radius: 8
            visible: !root.embedded
            color: root.drawer && root.drawer.position > 0 ? util.QML_ITEM_ALTERNATE_BG : "transparent"

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
                onClicked: root.drawer.open()
            }
        }

        // Discussion title (tappable dropdown) - only on Discuss tab
        Rectangle {
            objectName: "discussionHeaderDropdown"
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

        // The Story title (tappable dropdown) - Learn tab
        Rectangle {
            anchors.centerIn: parent
            width: storyTitleRow.width + 16
            height: 36
            radius: 8
            color: storyMenuOpen ? util.QML_ITEM_ALTERNATE_BG : "transparent"
            visible: tabBar.currentIndex === 1

            Row {
                id: storyTitleRow
                anchors.centerIn: parent
                spacing: 6

                Text {
                    text: "The Story"
                    font.pixelSize: 17
                    font.bold: true
                    color: textColor
                }
                Text {
                    text: "▼"
                    font.pixelSize: 10
                    color: secondaryText
                    anchors.verticalCenter: parent.verticalCenter
                    visible: !root.embedded
                }
            }

            MouseArea {
                anchors.fill: parent
                enabled: !root.embedded
                onClicked: storyMenuOpen = !storyMenuOpen
            }
        }

        // Static title for Plan tab
        Text {
            anchors.centerIn: parent
            text: "Plan"
            font.pixelSize: 17
            font.bold: true
            color: textColor
            visible: tabBar.currentIndex === 2
        }

        // PDP Badge (Discuss tab, left of rebuild button if visible, else left of extract button)
        Rectangle {
            id: pdpBadge
            objectName: "pdpBadge"
            anchors.right: rebuildButton.visible ? rebuildButton.left : extractButton.left
            anchors.rightMargin: 8
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

        // Rebuild button (Discuss tab, when canRebuild — left of extract button)
        Rectangle {
            id: rebuildButton
            objectName: "rebuildButton"
            anchors.right: extractButton.left
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            width: 28
            height: 28
            radius: 14
            color: util.IS_UI_DARK_MODE ? "#3A3938" : "#E9E9EB"
            visible: tabBar.currentIndex === 0 && !!pdpController && pdpController.canRebuild
            Canvas {
                anchors.centerIn: parent
                width: 16
                height: 16
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    ctx.strokeStyle = textColor
                    ctx.lineWidth = 1.5
                    ctx.lineCap = "round"
                    ctx.beginPath()
                    ctx.arc(8, 8, 5.2, -0.6, 3.6)
                    ctx.stroke()
                    ctx.beginPath()
                    ctx.moveTo(11.6, 3.2)
                    ctx.lineTo(13.2, 5.2)
                    ctx.lineTo(10.6, 5.6)
                    ctx.stroke()
                }
            }
            MouseArea {
                anchors.fill: parent
                onClicked: rebuildDialog.open()
            }
        }

        // Extract button (Discuss tab, only when there are statements after
        // the re-extraction cursor — i.e. unextracted/"dirty" content)
        Rectangle {
            id: extractButton
            objectName: "extractButton"
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 28
            height: 28
            radius: 14
            color: util.IS_UI_DARK_MODE ? "#4495F7" : "#007AFF"
            visible: tabBar.currentIndex === 0 && !!discussion && discussion.canExtract && !pdpController.extracting

            Canvas {
                anchors.centerIn: parent
                width: 14
                height: 14
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    ctx.strokeStyle = "white"
                    ctx.lineWidth = 1.5
                    ctx.lineCap = "round"
                    // Arrow down
                    ctx.beginPath()
                    ctx.moveTo(7, 1)
                    ctx.lineTo(7, 9)
                    ctx.stroke()
                    ctx.beginPath()
                    ctx.moveTo(3.5, 6)
                    ctx.lineTo(7, 10)
                    ctx.lineTo(10.5, 6)
                    ctx.stroke()
                    // Tray
                    ctx.beginPath()
                    ctx.moveTo(1, 10)
                    ctx.lineTo(1, 13)
                    ctx.lineTo(13, 13)
                    ctx.lineTo(13, 10)
                    ctx.stroke()
                }
            }
            MouseArea {
                anchors.fill: parent
                onClicked: pdpController.extractFull()
            }
        }

        // Import button (Learn tab only)
        Rectangle {
            id: importButton
            objectName: "importButton"
            anchors.right: addEventButton.left
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            width: 28
            height: 28
            radius: 14
            color: accentColor
            visible: tabBar.currentIndex === 1

            Image {
                anchors.centerIn: parent
                width: 16
                height: 16
                source: "../../paper-clip-white.png"
                fillMode: Image.PreserveAspectFit
                smooth: true
            }
            MouseArea {
                anchors.fill: parent
                onClicked: importMenuOpen = !importMenuOpen
            }
        }

        // Add Event button (Learn tab only)
        Rectangle {
            id: addEventButton
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
            objectName: "discussView"
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
            objectName: "planView"
            Layout.fillHeight: true
            Layout.fillWidth: true
        }
    }

    // Tab Bar
    Rectangle {
        id: tabBar
        objectName: "tabBar"
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
                    objectName: modelData.toLowerCase() + "Tab"
                    width: root.width / 3
                    height: parent.height
                    color: "transparent"

                    Text {
                        id: tabLabel
                        anchors.centerIn: parent
                        text: modelData
                        font.pixelSize: 15
                        font.weight: tabBar.currentIndex === index ? Font.DemiBold : Font.Normal
                        color: tabBar.currentIndex === index ? accentColor : secondaryText
                    }

                    // iOS-style notification badge (Discuss tab only)
                    Rectangle {
                        visible: index === 0 && pdpCount > 0
                        anchors.left: tabLabel.right
                        anchors.leftMargin: 2
                        anchors.bottom: tabLabel.top
                        anchors.bottomMargin: -6
                        width: Math.max(18, badgeText.width + 8)
                        height: 18
                        radius: 9
                        color: "#FF3B30"

                        Text {
                            id: badgeText
                            anchors.centerIn: parent
                            text: pdpCount > 99 ? "99+" : pdpCount.toString()
                            font.pixelSize: 11
                            font.bold: true
                            color: "white"
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            tabBar.currentIndex = index
                            discussionMenuOpen = false
                            storyMenuOpen = false
                            importMenuOpen = false
                        }
                    }
                }
            }
        }
    }

    // Invisible tap catcher for dropdown dismissal
    MouseArea {
        anchors.fill: parent

        visible: discussionMenuOpen || storyMenuOpen || importMenuOpen
        z: 55
        onClicked: {
            discussionMenuOpen = false
            storyMenuOpen = false
            importMenuOpen = false
        }
    }

    // Discussion dropdown
    Rectangle {
        id: discussionDropdownRect
        objectName: "discussionDropdownRect"
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
                    text: diagramLoader && diagramLoader.diagram ? (diagramLoader.diagram.name || "Diagram") : "Diagram"
                    font.pixelSize: 12
                    font.bold: true
                    color: secondaryText
                }
            }

            Repeater {
                model: discussion ? discussion.discussions : []

                Rectangle {
                    objectName: "discussionItem_" + modelData.id
                    width: discussionDropdown.width - 16
                    height: 44
                    radius: 8
                    color: discussion && discussion.currentDiscussionId === modelData.id ? util.QML_ITEM_ALTERNATE_BG : "transparent"
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
                            color: discussion && discussion.currentDiscussionId === modelData.id ? accentColor : "transparent"
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
                            discussion.setCurrentDiscussion(modelData.id)
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
                objectName: "newDiscussionItem"
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
                        discussion.createDiscussion()
                    }
                }
            }
        }
    }

    // The Story dropdown (Learn tab)
    Rectangle {
        id: storyDropdownRect
        anchors.top: header.bottom
        anchors.topMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        width: 200
        height: storyDropdown.height
        radius: 12
        color: itemBg
        border.width: 1
        border.color: borderColor
        visible: opacity > 0
        opacity: storyMenuOpen ? 1 : 0
        scale: storyMenuOpen ? 1 : 0.9
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
            id: storyDropdown
            width: parent.width
            padding: 8

            // Clear Data option
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
                        text: "Clear Data..."
                        color: "#FF3B30"
                        font.pixelSize: 15
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        storyMenuOpen = false
                        clearDataDialog.open()
                    }
                }
            }
        }
    }

    // Import dropdown (Learn tab)
    Rectangle {
        id: importDropdownRect
        anchors.top: header.bottom
        anchors.topMargin: 4
        anchors.right: parent.right
        anchors.rightMargin: 8
        width: 250
        height: importDropdownColumn.implicitHeight
        radius: 13
        color: itemBg
        border.width: 1
        border.color: borderColor
        visible: opacity > 0
        opacity: importMenuOpen ? 1 : 0
        scale: importMenuOpen ? 1 : 0.92
        transformOrigin: Item.TopRight
        z: 60

        Behavior on opacity {
            NumberAnimation { duration: 150; easing.type: Easing.OutQuad }
        }
        Behavior on scale {
            NumberAnimation { duration: 150; easing.type: Easing.OutBack; easing.overshoot: 1.5 }
        }

        Rectangle {
            anchors.fill: parent
            anchors.topMargin: 4
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
            id: importDropdownColumn
            width: parent.width
            topPadding: 8
            bottomPadding: 8
            spacing: 0

            Rectangle {
                objectName: "attachFileButton"
                width: parent.width
                height: 44
                color: "transparent"
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    text: "Attach file..."
                    font.pixelSize: 15
                    color: textColor
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        importMenuOpen = false
                        importFileDialog.open()
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.right: parent.right
                height: 1
                color: borderColor
            }

            Rectangle {
                objectName: "pasteTextButton"
                width: parent.width
                height: 44
                color: "transparent"
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    text: "Paste text..."
                    font.pixelSize: 15
                    color: textColor
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        importMenuOpen = false
                        pasteTextDrawer.open()
                    }
                }
            }
        }
    }

    FileDialog {
        id: importFileDialog
        title: "Import Notes"
        nameFilters: ["Text files (*.txt *.md)", "All files (*)"]
        onAccepted: pdpController.importFromFile(file)
    }

    // Import signal handlers (triggered from Learn tab; overlay is app-level)
    Connections {
        target: pdpController
        function onJournalImportStarted() { importOverlay.visible = true }
        function onJournalImportCompleted(summary) {
            importOverlay.visible = false
            pasteTextEdit.text = ""
            pasteTextDrawer.close()
            util.informationBox("Import Complete",
                "Added " + summary.people + " people, " + summary.events + " events to pending items.")
        }
        function onJournalImportFailed(error) {
            importOverlay.visible = false
            util.criticalBox("Import Failed", error)
        }
    }

    Personal.LoadingOverlay {
        fallbackParent: root
        id: importOverlay
        objectName: "importOverlay"
        text: "Importing notes..."
    }

    // Paste text drawer (full-height bottom sheet)
    Drawer {
        id: pasteTextDrawer
        width: parent.width
        height: parent.height
        edge: Qt.BottomEdge
        interactive: false
        closePolicy: Popup.CloseOnEscape
        background: Rectangle { color: drawerBg }
        onClosed: pasteTextEdit.text = ""

        Item {
            anchors.fill: parent
            anchors.topMargin: root.safeAreaTop
            anchors.bottomMargin: Qt.inputMethod.visible ? 0 : root.safeAreaBottom

            // Header
            Rectangle {
                id: pasteDrawerHeader
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 56
                color: "transparent"

                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 1
                    color: borderColor
                }

                Text {
                    anchors.centerIn: parent
                    text: "Import Notes"
                    font.pixelSize: 17
                    font.weight: Font.DemiBold
                    color: textColor
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    width: 64
                    height: 44
                    color: "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
                        font.pixelSize: 17
                        color: accentColor
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            pasteTextEdit.text = ""
                            pasteTextDrawer.close()
                        }
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.rightMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    width: 64
                    height: 44
                    color: "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: "Import"
                        font.pixelSize: 17
                        font.weight: Font.DemiBold
                        color: pasteTextEdit.text.trim().length > 0 ? accentColor : secondaryText
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: pasteTextEdit.text.trim().length > 0
                        onClicked: pdpController.importJournalNotes(pasteTextEdit.text)
                    }
                }
            }

            // Text edit area — fills all space below header
            Flickable {
                id: pasteFlickable
                anchors.top: pasteDrawerHeader.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                clip: true
                contentWidth: width
                contentHeight: pasteTextEdit.height

                TextEdit {
                    id: pasteTextEdit
                    width: pasteFlickable.width
                    height: Math.max(pasteFlickable.height, implicitHeight)
                    leftPadding: 16
                    rightPadding: 16
                    topPadding: 16
                    bottomPadding: 16
                    wrapMode: TextEdit.WordWrap
                    font.pixelSize: 15
                    color: textColor
                    selectByMouse: true

                    Text {
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.topMargin: parent.topPadding
                        anchors.leftMargin: parent.leftPadding
                        text: "Paste your notes here..."
                        font.pixelSize: 15
                        color: secondaryText
                        visible: pasteTextEdit.text.length === 0
                    }
                }
            }
        }
    }

    // Clear Data confirmation dialog
    Popup {
        id: clearDataDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(root.width - 40, 320)
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 0

        background: Rectangle {
            radius: 14
            color: itemBg
            border.width: 1
            border.color: borderColor
        }

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150 }
            NumberAnimation { property: "scale"; from: 0.9; to: 1; duration: 150; easing.type: Easing.OutBack }
        }
        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 }
        }

        contentItem: Column {
            spacing: 0
            padding: 20

            Text {
                text: "Clear Diagram Data"
                font.pixelSize: 17
                font.bold: true
                color: textColor
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: 12 }

            Text {
                text: "Your discussions will be preserved.\nChoose what to clear:"
                font.pixelSize: 14
                color: secondaryText
                horizontalAlignment: Text.AlignHCenter
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: 20 }

            // Clear Events Only button
            Rectangle {
                width: clearDataDialog.width - 40
                height: 44
                radius: 10
                color: util.QML_ITEM_ALTERNATE_BG

                Text {
                    anchors.centerIn: parent
                    text: "Clear Events Only"
                    font.pixelSize: 15
                    color: textColor
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        clearDataDialog.close()
                        pdpController.clearDiagramData(false)
                    }
                }
            }

            Item { width: 1; height: 10 }

            // Clear Events and People button
            Rectangle {
                width: clearDataDialog.width - 40
                height: 44
                radius: 10
                color: "#FF3B30"

                Text {
                    anchors.centerIn: parent
                    text: "Clear Events and People"
                    font.pixelSize: 15
                    font.weight: Font.Medium
                    color: "white"
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        clearDataDialog.close()
                        pdpController.clearDiagramData(true)
                    }
                }
            }

            Item { width: 1; height: 10 }

            // Cancel button
            Rectangle {
                width: clearDataDialog.width - 40
                height: 44
                radius: 10
                color: "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "Cancel"
                    font.pixelSize: 15
                    color: accentColor
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: clearDataDialog.close()
                }
            }
        }
    }

    // TEMPORARY: remove this cost-confirmation dialog once a customer pricing model is added to the app.
    property bool maxFidelity: false
    Popup {
        id: rebuildDialog
        objectName: "rebuildDialog"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(root.width - 40, 340)
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 0

        background: Rectangle {
            radius: 14
            color: itemBg
            border.width: 1
            border.color: borderColor
        }

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150 }
            NumberAnimation { property: "scale"; from: 0.9; to: 1; duration: 150; easing.type: Easing.OutBack }
        }
        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 }
        }

        contentItem: Column {
            spacing: 0
            padding: 20
            width: rebuildDialog.width

            Text {
                text: "Rebuild Diagram"
                font.pixelSize: 17
                font.bold: true
                color: textColor
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: 12 }

            Text {
                width: rebuildDialog.width - 40
                text: "This re-runs the AI to reconstruct a more complete, better-connected diagram from your discussions. It costs Alaska Family Systems about " + (root.maxFidelity ? "$0.60" : "$0.10") + " each time. Please check with patrick@alaskafamilysystems.com before continuing."
                wrapMode: Text.WordWrap
                font.pixelSize: 14
                color: secondaryText
                horizontalAlignment: Text.AlignHCenter
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: 18 }

            Rectangle {
                width: rebuildDialog.width - 40
                height: 52
                radius: 10
                color: util.QML_ITEM_ALTERNATE_BG
                anchors.horizontalCenter: parent.horizontalCenter

                Column {
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    Text {
                        text: "Max fidelity"
                        font.pixelSize: 15
                        color: textColor
                    }
                    Text {
                        text: root.maxFidelity ? "Best accuracy, about $0.60" : "Faster, about $0.10"
                        font.pixelSize: 11
                        color: secondaryText
                    }
                }

                Switch {
                    objectName: "rebuildMaxFidelitySwitch"
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    checked: root.maxFidelity
                    onToggled: root.maxFidelity = checked
                }
            }

            Item { width: 1; height: 16 }

            Row {
                spacing: 10
                anchors.horizontalCenter: parent.horizontalCenter

                Rectangle {
                    objectName: "rebuildCancelButton"
                    width: (rebuildDialog.width - 50) / 2
                    height: 44
                    radius: 10
                    color: util.QML_ITEM_ALTERNATE_BG
                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
                        font.pixelSize: 15
                        color: textColor
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: rebuildDialog.close()
                    }
                }

                Rectangle {
                    objectName: "rebuildContinueButton"
                    width: (rebuildDialog.width - 50) / 2
                    height: 44
                    radius: 10
                    color: accentColor
                    Text {
                        anchors.centerIn: parent
                        text: "Continue"
                        font.pixelSize: 15
                        color: "white"
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            pdpController.rebuildDiagram(root.maxFidelity ? 8 : 1)
                            rebuildDialog.close()
                        }
                    }
                }
            }
        }
    }

    // Left Drawer — the account, the diagram list and logout, none of which
    // exist when Pro owns the open case.
    Loader {
        id: drawerLoader
        active: !root.embedded

        sourceComponent: Drawer {
            width: root.width * 0.85
            height: root.height
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
                    root.drawer.close()
                    session.logout()
                }
                onAccountClicked: {
                    root.drawer.close()
                    profilePopupLoader.item.open()
                }
                onDiagramClicked: function(diagram) {
                    root.drawer.close()
                    diagramLoader.loadDiagram(diagram.id)
                }
                onNewDiagramClicked: {
                    root.drawer.close()
                    diagramLoader.createDiagram()
                }
                onSettingsClicked: function(setting) {
                    if (setting === "Coaching Style") {
                        modelPopup.open()
                    } else if (setting === "Voice") {
                        voicePopup.open()
                    } else if (setting === "Privacy") {
                        privacyPopup.open()
                    } else if (setting === "Help & Support") {
                        helpPopup.open()
                    }
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
        interactive: false  // Disable drag-to-close so Flickable can scroll

        background: Rectangle { color: drawerBg }

        Root.EventForm {
            id: eventForm
            anchors.fill: parent
            safeAreaTop: root.safeAreaTop
            safeAreaBottom: Qt.inputMethod.visible ? 0 : root.safeAreaBottom
            showClearButton: false
            onCancel: eventFormDrawer.close()
            Component.onCompleted: personalApp.initEventForm(eventForm)
        }
    }

    // Connect LearnView signals
    Connections {
        target: learnView
        function onAddEventRequested() {
            eventForm.clear()
            eventForm.initWithNoSelection()
            eventFormDrawer.open()
        }
        function onEditEventRequested(eventId) {
            personalApp.editEvent(eventId)
            eventFormDrawer.open()
        }
        function onDeleteEventRequested(eventId) {
            personalApp.deleteEvent(eventId)
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

    // Model settings popup
    Popup {
        id: modelPopup
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

        Personal.ModelSettingsPage {
            anchors.fill: parent
            onBackClicked: modelPopup.close()
        }
    }

    // Voice settings popup
    Popup {
        id: voicePopup
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

        Personal.VoiceSettingsPage {
            anchors.fill: parent
            onBackClicked: voicePopup.close()
        }
    }

    // Profile settings popup (FD-321) — opened from the AccountDrawer ACCOUNT
    // entry. Reads the account holder's own node, which a Pro case is not.
    Loader {
        id: profilePopupLoader
        active: !root.embedded

        sourceComponent: Popup {
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

            Personal.ProfileSettingsPage {
                anchors.fill: parent
                onBackClicked: profilePopupLoader.item.close()
            }
        }
    }

    // First-launch user-details wizard (FD-321). Shown once when the
    // profile-prompt pref is unset AND the primary node has no name. Save or
    // Skip sets the pref so it never reappears.
    Loader {
        id: wizardLoader
        anchors.fill: parent
        active: !root.embedded && session && session.loggedIn && personalApp && personalApp.shouldPromptProfile
        z: 100

        sourceComponent: Personal.UserDetailsWizard {
            objectName: "userDetailsWizard"
            safeAreaTop: root.safeAreaTop
            safeAreaBottom: root.safeAreaBottom
            onDone: wizardLoader.active = false
        }
    }

    // Account Dialog overlay - shown when not logged in
    Loader {
        id: accountDialogLoader
        anchors.fill: parent
        active: !root.embedded && session && !session.loggedIn
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
    Keys.onEscapePressed: {
        discussionMenuOpen = false
        storyMenuOpen = false
        importMenuOpen = false
        if (pasteTextDrawer.position > 0) {
            pasteTextEdit.text = ""
            pasteTextDrawer.close()
        }
        if (root.drawer && root.drawer.position > 0)
            root.drawer.close()
    }
}
