// Mobile D: Story/Narrative Design
// Iteration 9: Fix graph click - simpler approach
// Scroll first, then expand via timer after scroll completes
// Year labels under event dots only

import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Shapes 1.15

Window {
    id: root
    visible: true
    width: 390
    height: 750
    title: "Mobile D - Story Mode"

    property bool darkMode: true
    property int selectedEvent: -1
    property int highlightedEvent: -1
    property int pendingSelection: -1

    // WCAG AA colors
    property color bg: darkMode ? "#0f0f18" : "#f8f8fc"
    property color card: darkMode ? "#1a1a28" : "#ffffff"
    property color text1: darkMode ? "#f0f0f5" : "#1a1a2e"
    property color text2: darkMode ? "#909098" : "#606070"
    property color divider: darkMode ? "#2a2a38" : "#e0e0e8"
    property color highlight: darkMode ? "#2a2a40" : "#f0f0ff"

    property color symptom: "#e05555"
    property color anxiety: "#40a060"
    property color relationship: "#5080d0"
    property color functioning: darkMode ? "#909090" : "#505060"

    color: bg

    property var events: [
        { year: 1925, s: "up", a: null, f: null, r: null, desc: "Pneumonia", who: "Heidi", note: "First significant health event" },
        { year: 1940, s: null, a: null, f: null, r: "conflict", desc: "Family rift", who: "Family", note: "Conflict pattern emerges" },
        { year: 1952, s: null, a: null, f: "down", r: null, desc: "Birth", who: "Child", note: "Family expansion" },
        { year: 1960, s: null, a: null, f: null, r: "projection", desc: "Child focus", who: "Parents", note: "Triangulation begins" },
        { year: 1969, s: "up", a: "up", f: null, r: null, desc: "Diagnosis", who: "Person A", note: "Major health crisis" },
        { year: 1970, s: null, a: "up", f: null, r: null, desc: "DUI", who: "Person B", note: "Stress response" },
        { year: 1974, s: null, a: "up", f: null, r: "distance", desc: "DUI #2", who: "Person B", note: "Pattern continues" }
    ]

    property var cumulative: {
        var r = [], cs = 0, ca = 0, cf = 0
        for (var i = 0; i < events.length; i++) {
            var e = events[i]
            if (e.s === "up") cs++; else if (e.s === "down") cs--
            if (e.a === "up") ca++; else if (e.a === "down") ca--
            if (e.f === "up") cf++; else if (e.f === "down") cf--
            r.push({ year: e.year, s: cs, a: ca, f: cf, r: e.r })
        }
        return r
    }

    // Graph properties - even padding
    property real graphPadding: 20
    property real miniGraphY: 90
    property real miniGraphH: 100
    property real gLeft: graphPadding + 30
    property real gRight: width - graphPadding
    property real gWidth: gRight - gLeft

    function xPos(year) { return gLeft + ((year - 1920) / 60) * gWidth }
    function yPosMini(val) { return miniGraphY + miniGraphH - ((val + 2) / 6) * miniGraphH }

    // Timer to expand after scroll completes
    Timer {
        id: expandTimer
        interval: 550  // Slightly longer than scroll duration
        onTriggered: {
            if (pendingSelection >= 0) {
                selectedEvent = pendingSelection
                pendingSelection = -1
            }
        }
    }

    // Scroll to event, then expand after delay
    function scrollToEventThenExpand(idx) {
        if (idx < 0 || idx >= events.length) return

        console.log("Clicked event: " + idx)

        // Collapse any currently selected item first
        selectedEvent = -1
        highlightedEvent = idx
        pendingSelection = idx

        // Calculate scroll position (all items collapsed = 100px each)
        var targetY = idx * 100
        targetY = Math.max(0, targetY)

        // Clamp to valid scroll range
        var totalContentHeight = events.length * 100
        var maxScroll = Math.max(0, totalContentHeight - storyList.height)
        targetY = Math.min(targetY, maxScroll)

        scrollAnimation.to = targetY
        scrollAnimation.start()
        expandTimer.restart()
    }

    // Header with mini graph
    Rectangle {
        id: headerCard
        width: parent.width
        height: miniGraphY + miniGraphH + 45
        color: card

        Text {
            x: 20; y: 20
            text: "The Story"
            font.pixelSize: 24
            font.weight: Font.Bold
            color: text1
        }

        // Toggle
        Rectangle {
            x: parent.width - 55; y: 18
            width: 40; height: 24; radius: 12
            color: darkMode ? "#333" : "#ccc"
            Rectangle {
                x: darkMode ? 18 : 3; y: 3
                width: 18; height: 18; radius: 9
                color: "#fff"
                Behavior on x { NumberAnimation { duration: 100 } }
            }
            MouseArea { anchors.fill: parent; onClicked: darkMode = !darkMode }
        }

        // Year range
        Text {
            x: 20; y: 48
            text: "1920 — 1980"
            font.pixelSize: 12
            color: text2
        }

        // Graph background - even padding
        Rectangle {
            x: graphPadding
            y: miniGraphY - 10
            width: parent.width - graphPadding * 2
            height: miniGraphH + 40
            radius: 10
            color: darkMode ? "#151520" : "#f5f5fa"
        }

        // Baseline
        Rectangle {
            x: gLeft; y: yPosMini(0)
            width: gWidth; height: 1
            color: divider
        }

        // Mini lines
        Shape {
            anchors.fill: parent
            ShapePath {
                strokeColor: symptom; strokeWidth: 1.5; fillColor: "transparent"
                startX: xPos(1920); startY: yPosMini(0)
                PathLine { x: xPos(cumulative[0].year); y: yPosMini(0) }
                PathLine { x: xPos(cumulative[0].year); y: yPosMini(cumulative[0].s) }
                PathLine { x: xPos(cumulative[1].year); y: yPosMini(cumulative[1].s) }
                PathLine { x: xPos(cumulative[2].year); y: yPosMini(cumulative[2].s) }
                PathLine { x: xPos(cumulative[3].year); y: yPosMini(cumulative[3].s) }
                PathLine { x: xPos(cumulative[4].year); y: yPosMini(cumulative[4].s) }
                PathLine { x: xPos(cumulative[5].year); y: yPosMini(cumulative[5].s) }
                PathLine { x: xPos(cumulative[6].year); y: yPosMini(cumulative[6].s) }
                PathLine { x: xPos(1980); y: yPosMini(cumulative[6].s) }
            }
        }
        Shape {
            anchors.fill: parent
            ShapePath {
                strokeColor: anxiety; strokeWidth: 1.5; fillColor: "transparent"
                startX: xPos(1920); startY: yPosMini(0)
                PathLine { x: xPos(cumulative[0].year); y: yPosMini(0) }
                PathLine { x: xPos(cumulative[0].year); y: yPosMini(cumulative[0].a) }
                PathLine { x: xPos(cumulative[1].year); y: yPosMini(cumulative[1].a) }
                PathLine { x: xPos(cumulative[2].year); y: yPosMini(cumulative[2].a) }
                PathLine { x: xPos(cumulative[3].year); y: yPosMini(cumulative[3].a) }
                PathLine { x: xPos(cumulative[4].year); y: yPosMini(cumulative[4].a) }
                PathLine { x: xPos(cumulative[5].year); y: yPosMini(cumulative[5].a) }
                PathLine { x: xPos(cumulative[6].year); y: yPosMini(cumulative[6].a) }
                PathLine { x: xPos(1980); y: yPosMini(cumulative[6].a) }
            }
        }

        // Event dots on mini graph - with year labels underneath
        // Using z: 100 to ensure they're on top
        Repeater {
            model: events
            Item {
                x: xPos(modelData.year) - 20
                y: yPosMini(0) - 20
                width: 40
                height: 55
                z: 100  // Ensure dots are on top of everything

                // Dot
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 16
                    width: 8; height: 8; radius: 4
                    color: highlightedEvent === index ? text1 : (modelData.r ? relationship : (modelData.s ? symptom : (modelData.a ? anxiety : functioning)))
                    scale: highlightedEvent === index ? 1.5 : 1
                    Behavior on scale { NumberAnimation { duration: 150 } }
                }

                // Year label under dot
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 30
                    text: modelData.year.toString()
                    font.pixelSize: 8
                    color: text2
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        scrollToEventThenExpand(index)
                    }
                }
            }
        }
    }

    // Story scroll (timeline as narrative)
    ListView {
        id: storyList
        x: 0; y: headerCard.height + 5
        width: parent.width
        height: parent.height - headerCard.height - 55
        clip: true
        spacing: 0
        model: events

        // Smooth scroll animation
        NumberAnimation {
            id: scrollAnimation
            target: storyList
            property: "contentY"
            duration: 500
            easing.type: Easing.InOutQuad
        }

        onCurrentIndexChanged: highlightedEvent = currentIndex

        delegate: Rectangle {
            width: ListView.view.width
            height: selectedEvent === index ? 200 : 100
            color: selectedEvent === index ? highlight : "transparent"

            Behavior on height { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    selectedEvent = (selectedEvent === index) ? -1 : index
                    highlightedEvent = index
                }
            }

            // Timeline line
            Rectangle {
                x: 35; y: 0
                width: 2
                height: parent.height
                color: divider
            }

            // Year node
            Rectangle {
                x: 24; y: 20
                width: 24; height: 24
                radius: modelData.r ? 0 : 12
                rotation: modelData.r ? 45 : 0
                color: modelData.r ? relationship : (modelData.s ? symptom : (modelData.a ? anxiety : functioning))
                border.color: selectedEvent === index ? text1 : "transparent"
                border.width: 2

                scale: selectedEvent === index ? 1.2 : 1
                Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
            }

            // Content
            Column {
                x: 65; y: 15
                width: parent.width - 85
                spacing: 6

                Row {
                    spacing: 12
                    Text {
                        text: modelData.year.toString()
                        font.pixelSize: 13
                        font.weight: Font.Bold
                        color: modelData.r ? relationship : (modelData.s ? symptom : (modelData.a ? anxiety : functioning))
                    }
                    Text {
                        text: modelData.who
                        font.pixelSize: 13
                        color: text2
                    }
                }

                Text {
                    text: modelData.desc
                    font.pixelSize: 16
                    font.weight: Font.Medium
                    color: text1
                }

                // Expanded content
                Column {
                    visible: selectedEvent === index
                    opacity: selectedEvent === index ? 1 : 0
                    spacing: 10

                    Behavior on opacity { NumberAnimation { duration: 200 } }

                    Text {
                        text: modelData.note
                        font.pixelSize: 13
                        color: text2
                        topPadding: 8
                    }

                    // Shift badges
                    Flow {
                        width: parent.width
                        spacing: 8

                        Rectangle {
                            visible: modelData.s
                            width: 90; height: 32; radius: 16
                            color: symptom
                            Text {
                                anchors.centerIn: parent
                                text: "Symptom ↑"
                                font.pixelSize: 12
                                color: "#fff"
                            }
                        }
                        Rectangle {
                            visible: modelData.a
                            width: 90; height: 32; radius: 16
                            color: anxiety
                            Text {
                                anchors.centerIn: parent
                                text: "Anxiety ↑"
                                font.pixelSize: 12
                                color: "#fff"
                            }
                        }
                        Rectangle {
                            visible: modelData.f
                            width: 95; height: 32; radius: 16
                            color: functioning
                            Text {
                                anchors.centerIn: parent
                                text: "Function ↓"
                                font.pixelSize: 12
                                color: "#fff"
                            }
                        }
                        Rectangle {
                            visible: modelData.r
                            width: 95; height: 32; radius: 16
                            color: relationship
                            Text {
                                anchors.centerIn: parent
                                text: modelData.r ? modelData.r.charAt(0).toUpperCase() + modelData.r.slice(1) : ""
                                font.pixelSize: 12
                                color: "#fff"
                            }
                        }
                    }
                }
            }

            // Chevron
            Text {
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                text: selectedEvent === index ? "▼" : "▶"
                font.pixelSize: 12
                color: text2
            }
        }
    }

    // Legend at bottom
    Rectangle {
        x: 0; y: parent.height - 50
        width: parent.width; height: 50
        color: card

        Row {
            anchors.centerIn: parent
            spacing: 20

            Repeater {
                model: [
                    { c: symptom, n: "Symptom" },
                    { c: anxiety, n: "Anxiety" },
                    { c: functioning, n: "Function" },
                    { c: relationship, n: "Relation" }
                ]
                Row {
                    spacing: 5
                    Rectangle { width: 10; height: 10; radius: 5; color: modelData.c }
                    Text { text: modelData.n; font.pixelSize: 10; color: text2 }
                }
            }
        }
    }
}
