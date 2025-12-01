// Mobile B: Graph Focus Design
// Larger graph area, detail appears inline below graph

import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Shapes 1.15

Window {
    id: root
    visible: true
    width: 390
    height: 750
    title: "Mobile B - Graph Focus"

    property bool darkMode: true
    property int selectedEvent: -1

    property color bg: darkMode ? "#0d1117" : "#f6f8fa"
    property color card: darkMode ? "#161b22" : "#ffffff"
    property color text1: darkMode ? "#f0f6fc" : "#1f2328"
    property color text2: darkMode ? "#8b949e" : "#656d76"
    property color accent: "#58a6ff"

    property color symptom: "#f85149"
    property color anxiety: "#3fb950"
    property color relationship: "#58a6ff"
    property color functioning: darkMode ? "#8b949e" : "#57606a"

    color: bg

    property var events: [
        { year: 1925, s: "up", a: null, f: null, r: null, desc: "Pneumonia", who: "Heidi" },
        { year: 1940, s: null, a: null, f: null, r: "conflict", desc: "Family rift", who: "Family" },
        { year: 1952, s: null, a: null, f: "down", r: null, desc: "Birth", who: "Child" },
        { year: 1960, s: null, a: null, f: null, r: "projection", desc: "Child focus", who: "Parents" },
        { year: 1969, s: "up", a: "up", f: null, r: null, desc: "Diagnosis", who: "Person A" },
        { year: 1970, s: null, a: "up", f: null, r: null, desc: "DUI", who: "Person B" },
        { year: 1974, s: null, a: "up", f: null, r: "distance", desc: "DUI #2", who: "Person B" }
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

    property real gLeft: 20
    property real gRight: width - 20
    property real gTop: 100
    property real gHeight: 300
    property real gWidth: gRight - gLeft
    property real minY: -2
    property real maxY: 4

    function xPos(year) { return gLeft + ((year - 1920) / 60) * gWidth }
    function yPos(val) { return gTop + gHeight - ((val - minY) / (maxY - minY)) * gHeight }

    // Header
    Rectangle {
        width: parent.width; height: 80
        color: card

        Text {
            x: 20; y: 35
            text: "Pattern Analysis"
            font.pixelSize: 20
            font.weight: Font.Bold
            color: text1
        }

        Row {
            x: parent.width - 150; y: 30
            spacing: 8
            Repeater {
                model: [
                    { c: symptom, n: "S" },
                    { c: anxiety, n: "A" },
                    { c: functioning, n: "F" },
                    { c: relationship, n: "R" }
                ]
                Rectangle {
                    width: 28; height: 28; radius: 6
                    color: darkMode ? "#21262d" : "#f3f4f6"
                    Rectangle {
                        anchors.centerIn: parent
                        width: 10; height: 10; radius: 5
                        color: modelData.c
                    }
                }
            }
        }
    }

    // Full-width graph background
    Rectangle {
        y: gTop - 20
        width: parent.width
        height: gHeight + 60
        color: card
    }

    // Soft gradient fills
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeWidth: 0
            fillColor: Qt.rgba(symptom.r, symptom.g, symptom.b, 0.1)
            startX: xPos(1920); startY: yPos(0)
            PathLine { x: xPos(cumulative[0].year); y: yPos(0) }
            PathLine { x: xPos(cumulative[0].year); y: yPos(cumulative[0].s) }
            PathLine { x: xPos(cumulative[1].year); y: yPos(cumulative[1].s) }
            PathLine { x: xPos(cumulative[2].year); y: yPos(cumulative[2].s) }
            PathLine { x: xPos(cumulative[3].year); y: yPos(cumulative[3].s) }
            PathLine { x: xPos(cumulative[4].year); y: yPos(cumulative[4].s) }
            PathLine { x: xPos(cumulative[5].year); y: yPos(cumulative[5].s) }
            PathLine { x: xPos(cumulative[6].year); y: yPos(cumulative[6].s) }
            PathLine { x: xPos(1980); y: yPos(cumulative[6].s) }
            PathLine { x: xPos(1980); y: yPos(0) }
        }
    }

    Shape {
        anchors.fill: parent
        ShapePath {
            strokeWidth: 0
            fillColor: Qt.rgba(anxiety.r, anxiety.g, anxiety.b, 0.1)
            startX: xPos(1920); startY: yPos(0)
            PathLine { x: xPos(cumulative[0].year); y: yPos(0) }
            PathLine { x: xPos(cumulative[0].year); y: yPos(cumulative[0].a) }
            PathLine { x: xPos(cumulative[1].year); y: yPos(cumulative[1].a) }
            PathLine { x: xPos(cumulative[2].year); y: yPos(cumulative[2].a) }
            PathLine { x: xPos(cumulative[3].year); y: yPos(cumulative[3].a) }
            PathLine { x: xPos(cumulative[4].year); y: yPos(cumulative[4].a) }
            PathLine { x: xPos(cumulative[5].year); y: yPos(cumulative[5].a) }
            PathLine { x: xPos(cumulative[6].year); y: yPos(cumulative[6].a) }
            PathLine { x: xPos(1980); y: yPos(cumulative[6].a) }
            PathLine { x: xPos(1980); y: yPos(0) }
        }
    }

    // Baseline with label
    Rectangle { x: gLeft; y: yPos(0); width: gWidth; height: 2; color: darkMode ? "#30363d" : "#d0d7de" }
    Text { x: 5; y: yPos(0) - 6; text: "0"; font.pixelSize: 9; color: text2 }

    // Lines
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeColor: symptom; strokeWidth: 3; fillColor: "transparent"
            startX: xPos(1920); startY: yPos(0)
            PathLine { x: xPos(cumulative[0].year); y: yPos(0) }
            PathLine { x: xPos(cumulative[0].year); y: yPos(cumulative[0].s) }
            PathLine { x: xPos(cumulative[1].year); y: yPos(cumulative[1].s) }
            PathLine { x: xPos(cumulative[2].year); y: yPos(cumulative[2].s) }
            PathLine { x: xPos(cumulative[3].year); y: yPos(cumulative[3].s) }
            PathLine { x: xPos(cumulative[4].year); y: yPos(cumulative[4].s) }
            PathLine { x: xPos(cumulative[5].year); y: yPos(cumulative[5].s) }
            PathLine { x: xPos(cumulative[6].year); y: yPos(cumulative[6].s) }
            PathLine { x: xPos(1980); y: yPos(cumulative[6].s) }
        }
    }
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeColor: anxiety; strokeWidth: 3; fillColor: "transparent"
            startX: xPos(1920); startY: yPos(0)
            PathLine { x: xPos(cumulative[0].year); y: yPos(0) }
            PathLine { x: xPos(cumulative[0].year); y: yPos(cumulative[0].a) }
            PathLine { x: xPos(cumulative[1].year); y: yPos(cumulative[1].a) }
            PathLine { x: xPos(cumulative[2].year); y: yPos(cumulative[2].a) }
            PathLine { x: xPos(cumulative[3].year); y: yPos(cumulative[3].a) }
            PathLine { x: xPos(cumulative[4].year); y: yPos(cumulative[4].a) }
            PathLine { x: xPos(cumulative[5].year); y: yPos(cumulative[5].a) }
            PathLine { x: xPos(cumulative[6].year); y: yPos(cumulative[6].a) }
            PathLine { x: xPos(1980); y: yPos(cumulative[6].a) }
        }
    }
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeColor: functioning; strokeWidth: 3; fillColor: "transparent"
            startX: xPos(1920); startY: yPos(0)
            PathLine { x: xPos(cumulative[0].year); y: yPos(0) }
            PathLine { x: xPos(cumulative[0].year); y: yPos(cumulative[0].f) }
            PathLine { x: xPos(cumulative[1].year); y: yPos(cumulative[1].f) }
            PathLine { x: xPos(cumulative[2].year); y: yPos(cumulative[2].f) }
            PathLine { x: xPos(cumulative[3].year); y: yPos(cumulative[3].f) }
            PathLine { x: xPos(cumulative[4].year); y: yPos(cumulative[4].f) }
            PathLine { x: xPos(cumulative[5].year); y: yPos(cumulative[5].f) }
            PathLine { x: xPos(cumulative[6].year); y: yPos(cumulative[6].f) }
            PathLine { x: xPos(1980); y: yPos(cumulative[6].f) }
        }
    }

    // Event markers with touch areas
    Repeater {
        model: events
        Item {
            x: xPos(modelData.year); y: yPos(0)

            Rectangle {
                x: -20; y: -30; width: 40; height: 60
                color: "transparent"
                MouseArea { anchors.fill: parent; onClicked: selectedEvent = (selectedEvent === index) ? -1 : index }
            }

            Rectangle {
                visible: modelData.r === null
                x: -8; y: -8; width: 16; height: 16; radius: 8
                color: modelData.s ? symptom : (modelData.a ? anxiety : functioning)
                border.color: selectedEvent === index ? text1 : "transparent"
                border.width: 3
                scale: selectedEvent === index ? 1.3 : 1
                Behavior on scale { NumberAnimation { duration: 100 } }
            }
            Rectangle {
                visible: modelData.r !== null
                x: -9; y: -9; width: 18; height: 18; rotation: 45
                color: relationship
                border.color: selectedEvent === index ? text1 : "transparent"
                border.width: 2
                scale: selectedEvent === index ? 1.3 : 1
                Behavior on scale { NumberAnimation { duration: 100 } }
            }
        }
    }

    // Year axis
    Row {
        x: gLeft; y: gTop + gHeight + 15
        spacing: (gWidth - 120) / 3
        Repeater {
            model: ["1920", "1940", "1960", "1980"]
            Text { text: modelData; font.pixelSize: 11; color: text2 }
        }
    }

    // Selected event detail (inline below graph)
    Rectangle {
        visible: selectedEvent >= 0
        x: 16; y: gTop + gHeight + 60
        width: parent.width - 32
        height: 120
        radius: 12
        color: card
        border.color: accent
        border.width: 2

        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8

            Item {
                width: parent.width
                height: 24
                Text {
                    text: selectedEvent >= 0 ? events[selectedEvent].desc : ""
                    font.pixelSize: 18
                    font.weight: Font.Bold
                    color: text1
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: "✕"
                    font.pixelSize: 20
                    color: text2
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea { anchors.fill: parent; anchors.margins: -8; onClicked: selectedEvent = -1 }
                }
            }

            Text {
                text: selectedEvent >= 0 ? events[selectedEvent].year + " • " + events[selectedEvent].who : ""
                font.pixelSize: 13
                color: text2
            }

            Row {
                spacing: 8
                Rectangle {
                    visible: selectedEvent >= 0 && events[selectedEvent].s
                    width: 80; height: 30; radius: 6; color: symptom
                    Text { anchors.centerIn: parent; text: "Symptom ↑"; font.pixelSize: 11; color: "#fff" }
                }
                Rectangle {
                    visible: selectedEvent >= 0 && events[selectedEvent].a
                    width: 80; height: 30; radius: 6; color: anxiety
                    Text { anchors.centerIn: parent; text: "Anxiety ↑"; font.pixelSize: 11; color: "#fff" }
                }
                Rectangle {
                    visible: selectedEvent >= 0 && events[selectedEvent].f
                    width: 90; height: 30; radius: 6; color: functioning
                    Text { anchors.centerIn: parent; text: "Function ↓"; font.pixelSize: 11; color: "#fff" }
                }
                Rectangle {
                    visible: selectedEvent >= 0 && events[selectedEvent].r
                    width: 90; height: 30; radius: 6; color: relationship
                    Text {
                        anchors.centerIn: parent
                        text: selectedEvent >= 0 && events[selectedEvent].r ? events[selectedEvent].r.charAt(0).toUpperCase() + events[selectedEvent].r.slice(1) : ""
                        font.pixelSize: 11; color: "#fff"
                    }
                }
            }
        }
    }

    // Scrollable event list
    ListView {
        visible: selectedEvent < 0
        x: 16; y: gTop + gHeight + 60
        width: parent.width - 32
        height: 280
        clip: true
        spacing: 6
        model: events

        delegate: Rectangle {
            width: ListView.view.width
            height: 56
            radius: 10
            color: card

            MouseArea { anchors.fill: parent; onClicked: selectedEvent = index }

            Row {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                Rectangle {
                    width: 32; height: 32; radius: 16
                    color: modelData.r ? relationship : (modelData.s ? symptom : (modelData.a ? anxiety : functioning))
                    opacity: 0.2
                    Rectangle {
                        anchors.centerIn: parent
                        width: 12; height: 12; radius: 6
                        color: modelData.r ? relationship : (modelData.s ? symptom : (modelData.a ? anxiety : functioning))
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text { text: modelData.desc; font.pixelSize: 13; font.weight: Font.Medium; color: text1 }
                    Text { text: modelData.year + " • " + modelData.who; font.pixelSize: 11; color: text2 }
                }
            }
        }
    }

    // Dark mode toggle
    Rectangle {
        x: parent.width - 60; y: parent.height - 60
        width: 44; height: 44; radius: 22
        color: card

        Text {
            anchors.centerIn: parent
            text: darkMode ? "☀" : "🌙"
            font.pixelSize: 18
        }
        MouseArea { anchors.fill: parent; onClicked: darkMode = !darkMode }
    }
}
