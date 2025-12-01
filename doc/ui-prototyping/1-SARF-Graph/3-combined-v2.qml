// SARF Timeline Graph - Final Prototype v2
// Updates: Smooth scroll, vertical timeline, event shapes in list
// D-style timeline with inline expansion

import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Shapes 1.15

Window {
    id: root
    visible: true
    width: 390
    height: 844
    title: "SARF Timeline"

    property bool darkMode: true
    property int selectedEvent: -1
    property int previousSelected: -1

    // Colors from familydiagram/doc/agents/ui-planner.md
    property color windowBg: darkMode ? "#1e1e1e" : "#ffffff"
    property color itemBg: darkMode ? "#373534" : "#ffffff"
    property color itemAltBg: darkMode ? "#2d2b2a" : "#eeeeee"
    property color itemBorder: darkMode ? "#4d4c4c" : "#d3d3d3"
    property color headerBg: darkMode ? "#323232" : "#ffffff"
    property color controlBg: darkMode ? "#2d2b2a" : "#e0e0e0"
    property color textColor: darkMode ? "#ffffff" : "#000000"
    property color inactiveText: darkMode ? "#7a7878" : "#808080"
    property color selectionColor: "#007aff"
    property color highlightColor: Qt.rgba(0, 0.48, 1, 0.5)
    property color timelineLineColor: darkMode ? "#4d4c4c" : "#d0d0d0"

    // SARF colors
    property color symptomColor: "#e05050"
    property color anxietyColor: "#40b060"
    property color relationshipColor: "#5080d0"
    property color functioningColor: darkMode ? "#909090" : "#505050"

    color: windowBg

    // Test data with relationship details
    property var events: [
        {
            id: 1, year: 1925, dateTime: "1925-10-14",
            description: "Pneumonia",
            person: "Heidi", personId: 201,
            symptom: "up", anxiety: null, functioning: null,
            relationship: null, relationshipTargets: [], relationshipTriangles: [],
            summary: "Health crisis marked increased symptom presentation"
        },
        {
            id: 2, year: 1940, dateTime: "1940-06-01",
            description: "Family rift",
            person: "Family", personId: 0,
            symptom: null, anxiety: null, functioning: null,
            relationship: "conflict", relationshipTargets: [201, 251], relationshipTriangles: [],
            targetNames: ["Heidi", "Manuel"],
            summary: "Conflict pattern emerged between Heidi and Manuel"
        },
        {
            id: 3, year: 1952, dateTime: "1952-10-14",
            description: "Birth of child",
            person: "Child", personId: 21056,
            symptom: null, anxiety: null, functioning: "down",
            relationship: null, relationshipTargets: [], relationshipTriangles: [],
            summary: "Family expansion coincided with functioning decrease"
        },
        {
            id: 4, year: 1960, dateTime: "1960-03-15",
            description: "Child focus begins",
            person: "Parents", personId: 0,
            symptom: null, anxiety: null, functioning: null,
            relationship: "projection", relationshipTargets: [21056], relationshipTriangles: [201, 251],
            targetNames: ["Child"], triangleNames: ["Heidi", "Manuel"],
            summary: "Anxiety channeled through child (inside position)"
        },
        {
            id: 5, year: 1965, dateTime: "1965-08-20",
            description: "Emotional distance",
            person: "Heidi", personId: 201,
            symptom: null, anxiety: null, functioning: null,
            relationship: "cutoff", relationshipTargets: [], relationshipTriangles: [],
            summary: "Complete cutoff from extended family"
        },
        {
            id: 6, year: 1969, dateTime: "1969-10-14",
            description: "Schizophrenia diagnosis",
            person: "Person A", personId: 257,
            symptom: "up", anxiety: "up", functioning: null,
            relationship: null, relationshipTargets: [], relationshipTriangles: [],
            summary: "Major health crisis with symptom and anxiety increase"
        },
        {
            id: 7, year: 1970, dateTime: "1970-10-14",
            description: "DUI arrest",
            person: "Person B", personId: 251,
            symptom: null, anxiety: "up", functioning: null,
            relationship: null, relationshipTargets: [], relationshipTriangles: [],
            summary: "Behavioral incident indicating elevated anxiety"
        },
        {
            id: 8, year: 1974, dateTime: "1974-10-14",
            description: "Second DUI",
            person: "Person B", personId: 251,
            symptom: null, anxiety: "up", functioning: null,
            relationship: "distance", relationshipTargets: [201], relationshipTriangles: [],
            targetNames: ["Heidi"],
            summary: "Repeated pattern; distancing from Heidi"
        }
    ]

    // Compute cumulative values
    property var cumulative: {
        var r = [], cs = 0, ca = 0, cf = 0
        for (var i = 0; i < events.length; i++) {
            var e = events[i]
            if (e.symptom === "up") cs++
            else if (e.symptom === "down") cs--
            if (e.anxiety === "up") ca++
            else if (e.anxiety === "down") ca--
            if (e.functioning === "up") cf++
            else if (e.functioning === "down") cf--
            r.push({ year: e.year, s: cs, a: ca, f: cf, r: e.relationship })
        }
        return r
    }

    // Graph dimensions
    property real qmlMargins: 15
    property real gLeft: 45
    property real gRight: width - 20
    property real gTop: 155
    property real gHeight: 180
    property real gWidth: gRight - gLeft
    property real minYear: 1920
    property real maxYear: 1980
    property real minY: -2
    property real maxY: 4

    function yearToX(year) { return gLeft + ((year - minYear) / (maxYear - minYear)) * gWidth }
    function valueToY(val) { return gTop + gHeight - ((val - minY) / (maxY - minY)) * gHeight }

    function getEventColor(evt) {
        if (evt.relationship) return relationshipColor
        if (evt.symptom) return symptomColor
        if (evt.anxiety) return anxietyColor
        return functioningColor
    }

    // Smooth scroll function
    function scrollToEvent(idx) {
        if (idx >= 0 && idx < events.length) {
            scrollAnim.to = eventList.itemAtIndex(idx) ?
                Math.max(0, Math.min(
                    eventList.contentHeight - eventList.height,
                    eventList.itemAtIndex(idx).y - eventList.height / 3
                )) : 0
            scrollAnim.start()
        }
    }

    // Header
    Rectangle {
        id: header
        width: parent.width
        height: 60
        color: headerBg

        Text {
            x: qmlMargins
            anchors.verticalCenter: parent.verticalCenter
            text: "Timeline Analysis"
            font.pixelSize: 18
            font.bold: true
            color: textColor
        }

        // Dark/Light toggle
        Rectangle {
            x: parent.width - 60
            anchors.verticalCenter: parent.verticalCenter
            width: 44
            height: 28
            radius: 14
            color: controlBg

            Rectangle {
                x: darkMode ? 18 : 4
                y: 4
                width: 20
                height: 20
                radius: 10
                color: darkMode ? inactiveText : textColor
                Behavior on x { NumberAnimation { duration: 200; easing.type: Easing.OutQuad } }
            }
            MouseArea { anchors.fill: parent; onClicked: darkMode = !darkMode }
        }
    }

    // Legend with full names
    Row {
        id: legend
        x: qmlMargins
        y: 70
        spacing: 12

        Repeater {
            model: [
                { color: symptomColor, name: "Symptom" },
                { color: anxietyColor, name: "Anxiety" },
                { color: functioningColor, name: "Functioning" },
                { color: relationshipColor, name: "Relationship" }
            ]
            Row {
                spacing: 5
                Rectangle {
                    width: 10; height: 10; radius: 5
                    color: modelData.color
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: modelData.name
                    font.pixelSize: 11
                    color: inactiveText
                }
            }
        }
    }

    // Graph card
    Rectangle {
        x: qmlMargins
        y: gTop - 15
        width: parent.width - qmlMargins * 2
        height: gHeight + 35
        radius: 12
        color: itemBg
        border.color: itemBorder
        border.width: 1
    }

    // Baseline
    Rectangle {
        x: gLeft
        y: valueToY(0)
        width: gWidth
        height: 1
        color: itemBorder
    }
    Text {
        x: 10
        y: valueToY(0) - 6
        text: "0"
        font.pixelSize: 9
        color: inactiveText
    }

    // Y-axis hints
    Text { x: 10; y: valueToY(2) - 6; text: "+2"; font.pixelSize: 9; color: inactiveText }
    Text { x: 10; y: valueToY(-1) - 6; text: "-1"; font.pixelSize: 9; color: inactiveText }

    // Soft fill under symptom line
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeWidth: 0
            fillColor: Qt.rgba(symptomColor.r, symptomColor.g, symptomColor.b, 0.15)
            startX: yearToX(1920); startY: valueToY(0)
            PathLine { x: yearToX(cumulative[0].year); y: valueToY(0) }
            PathLine { x: yearToX(cumulative[0].year); y: valueToY(cumulative[0].s) }
            PathLine { x: yearToX(cumulative[1].year); y: valueToY(cumulative[1].s) }
            PathLine { x: yearToX(cumulative[2].year); y: valueToY(cumulative[2].s) }
            PathLine { x: yearToX(cumulative[3].year); y: valueToY(cumulative[3].s) }
            PathLine { x: yearToX(cumulative[4].year); y: valueToY(cumulative[4].s) }
            PathLine { x: yearToX(cumulative[5].year); y: valueToY(cumulative[5].s) }
            PathLine { x: yearToX(cumulative[6].year); y: valueToY(cumulative[6].s) }
            PathLine { x: yearToX(cumulative[7].year); y: valueToY(cumulative[7].s) }
            PathLine { x: yearToX(1980); y: valueToY(cumulative[7].s) }
            PathLine { x: yearToX(1980); y: valueToY(0) }
        }
    }

    // Symptom line
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeColor: symptomColor; strokeWidth: 2; fillColor: "transparent"
            startX: yearToX(1920); startY: valueToY(0)
            PathLine { x: yearToX(cumulative[0].year); y: valueToY(0) }
            PathLine { x: yearToX(cumulative[0].year); y: valueToY(cumulative[0].s) }
            PathLine { x: yearToX(cumulative[1].year); y: valueToY(cumulative[1].s) }
            PathLine { x: yearToX(cumulative[2].year); y: valueToY(cumulative[2].s) }
            PathLine { x: yearToX(cumulative[3].year); y: valueToY(cumulative[3].s) }
            PathLine { x: yearToX(cumulative[4].year); y: valueToY(cumulative[4].s) }
            PathLine { x: yearToX(cumulative[5].year); y: valueToY(cumulative[5].s) }
            PathLine { x: yearToX(cumulative[6].year); y: valueToY(cumulative[6].s) }
            PathLine { x: yearToX(cumulative[7].year); y: valueToY(cumulative[7].s) }
            PathLine { x: yearToX(1980); y: valueToY(cumulative[7].s) }
        }
    }

    // Anxiety line
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeColor: anxietyColor; strokeWidth: 2; fillColor: "transparent"
            startX: yearToX(1920); startY: valueToY(0)
            PathLine { x: yearToX(cumulative[0].year); y: valueToY(0) }
            PathLine { x: yearToX(cumulative[0].year); y: valueToY(cumulative[0].a) }
            PathLine { x: yearToX(cumulative[1].year); y: valueToY(cumulative[1].a) }
            PathLine { x: yearToX(cumulative[2].year); y: valueToY(cumulative[2].a) }
            PathLine { x: yearToX(cumulative[3].year); y: valueToY(cumulative[3].a) }
            PathLine { x: yearToX(cumulative[4].year); y: valueToY(cumulative[4].a) }
            PathLine { x: yearToX(cumulative[5].year); y: valueToY(cumulative[5].a) }
            PathLine { x: yearToX(cumulative[6].year); y: valueToY(cumulative[6].a) }
            PathLine { x: yearToX(cumulative[7].year); y: valueToY(cumulative[7].a) }
            PathLine { x: yearToX(1980); y: valueToY(cumulative[7].a) }
        }
    }

    // Functioning line
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeColor: functioningColor; strokeWidth: 2; fillColor: "transparent"
            startX: yearToX(1920); startY: valueToY(0)
            PathLine { x: yearToX(cumulative[0].year); y: valueToY(0) }
            PathLine { x: yearToX(cumulative[0].year); y: valueToY(cumulative[0].f) }
            PathLine { x: yearToX(cumulative[1].year); y: valueToY(cumulative[1].f) }
            PathLine { x: yearToX(cumulative[2].year); y: valueToY(cumulative[2].f) }
            PathLine { x: yearToX(cumulative[3].year); y: valueToY(cumulative[3].f) }
            PathLine { x: yearToX(cumulative[4].year); y: valueToY(cumulative[4].f) }
            PathLine { x: yearToX(cumulative[5].year); y: valueToY(cumulative[5].f) }
            PathLine { x: yearToX(cumulative[6].year); y: valueToY(cumulative[6].f) }
            PathLine { x: yearToX(cumulative[7].year); y: valueToY(cumulative[7].f) }
            PathLine { x: yearToX(1980); y: valueToY(cumulative[7].f) }
        }
    }

    // Event markers on graph
    Repeater {
        model: events
        Item {
            id: graphMarker
            x: yearToX(modelData.year)
            y: valueToY(0)

            property bool isSelected: selectedEvent === index

            // Touch area
            Rectangle {
                x: -20; y: -25
                width: 40; height: 50
                color: "transparent"
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        previousSelected = selectedEvent
                        selectedEvent = (selectedEvent === index) ? -1 : index
                        if (selectedEvent >= 0) {
                            scrollToEvent(selectedEvent)
                        }
                    }
                }
            }

            // Dot for S/A/F events
            Rectangle {
                visible: modelData.relationship === null
                x: -6; y: -6
                width: 12; height: 12
                radius: 6
                color: modelData.symptom ? symptomColor : (modelData.anxiety ? anxietyColor : functioningColor)
                border.color: isSelected ? textColor : "transparent"
                border.width: 2
                scale: isSelected ? 1.4 : 1
                Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
            }

            // Diamond for relationship events
            Rectangle {
                visible: modelData.relationship !== null
                x: -7; y: -7
                width: 14; height: 14
                rotation: 45
                color: relationshipColor
                border.color: isSelected ? textColor : "transparent"
                border.width: 2
                scale: isSelected ? 1.4 : 1
                Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
            }
        }
    }

    // Year labels
    Row {
        x: gLeft - 5
        y: gTop + gHeight + 8
        spacing: (gWidth - 90) / 2
        Repeater {
            model: ["1920", "1950", "1980"]
            Text { text: modelData; font.pixelSize: 10; color: inactiveText }
        }
    }

    // Events header
    Text {
        x: qmlMargins
        y: gTop + gHeight + 45
        text: "Events"
        font.pixelSize: 14
        font.bold: true
        color: textColor
    }

    // Event list with vertical timeline (D-style)
    ListView {
        id: eventList
        x: qmlMargins
        y: gTop + gHeight + 70
        width: parent.width - qmlMargins * 2
        height: parent.height - y - qmlMargins
        clip: true
        spacing: 0
        model: events
        cacheBuffer: 1000

        // Smooth scroll animation
        NumberAnimation on contentY {
            id: scrollAnim
            duration: 400
            easing.type: Easing.InOutQuad
            running: false
        }

        delegate: Item {
            id: eventDelegate
            width: ListView.view.width
            height: contentColumn.height + 16

            property bool isSelected: selectedEvent === index
            property bool isLast: index === events.length - 1

            // Vertical timeline line (D-style)
            Rectangle {
                x: 23
                y: 0
                width: 2
                height: parent.height
                color: timelineLineColor
                visible: !isLast
            }

            // Timeline node - shape matches graph
            Item {
                id: nodeContainer
                x: 12
                y: 8
                width: 24
                height: 24

                // Circle for S/A/F
                Rectangle {
                    visible: modelData.relationship === null
                    anchors.centerIn: parent
                    width: isSelected ? 22 : 18
                    height: width
                    radius: width / 2
                    color: getEventColor(modelData)
                    border.color: isSelected ? textColor : "transparent"
                    border.width: 2
                    Behavior on width { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
                }

                // Diamond for relationship
                Rectangle {
                    visible: modelData.relationship !== null
                    anchors.centerIn: parent
                    width: isSelected ? 18 : 14
                    height: width
                    rotation: 45
                    color: relationshipColor
                    border.color: isSelected ? textColor : "transparent"
                    border.width: 2
                    Behavior on width { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
                }
            }

            // Content area
            Rectangle {
                id: contentRect
                x: 48
                y: 4
                width: parent.width - 56
                height: contentColumn.height + 12
                radius: 10
                color: isSelected ? highlightColor : "transparent"
                border.color: isSelected ? selectionColor : "transparent"
                border.width: isSelected ? 2 : 0

                Behavior on color { ColorAnimation { duration: 200 } }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        previousSelected = selectedEvent
                        selectedEvent = (selectedEvent === index) ? -1 : index
                    }
                }

                Column {
                    id: contentColumn
                    x: 10
                    y: 6
                    width: parent.width - 30
                    spacing: 4

                    // Year badge + person
                    Row {
                        spacing: 10

                        Text {
                            text: modelData.year.toString()
                            font.pixelSize: 12
                            font.bold: true
                            color: getEventColor(modelData)
                        }

                        Text {
                            text: modelData.person
                            font.pixelSize: 12
                            color: inactiveText
                        }
                    }

                    // Description
                    Text {
                        text: modelData.description
                        font.pixelSize: 15
                        font.weight: Font.Medium
                        color: textColor
                    }

                    // Expanded details (D-style inline)
                    Column {
                        visible: isSelected
                        opacity: isSelected ? 1 : 0
                        width: parent.width
                        spacing: 8
                        topPadding: 6

                        Behavior on opacity { NumberAnimation { duration: 200 } }

                        // Summary
                        Text {
                            width: parent.width
                            text: modelData.summary || ""
                            font.pixelSize: 12
                            font.italic: true
                            color: inactiveText
                            wrapMode: Text.WordWrap
                        }

                        // SARF shift badges
                        Flow {
                            width: parent.width
                            spacing: 6

                            Rectangle {
                                visible: modelData.symptom !== null
                                width: 85; height: 28; radius: 14
                                color: symptomColor
                                Text {
                                    anchors.centerIn: parent
                                    text: "Symptom " + (modelData.symptom === "up" ? "↑" : "↓")
                                    font.pixelSize: 11
                                    color: "#ffffff"
                                }
                            }

                            Rectangle {
                                visible: modelData.anxiety !== null
                                width: 80; height: 28; radius: 14
                                color: anxietyColor
                                Text {
                                    anchors.centerIn: parent
                                    text: "Anxiety " + (modelData.anxiety === "up" ? "↑" : "↓")
                                    font.pixelSize: 11
                                    color: "#ffffff"
                                }
                            }

                            Rectangle {
                                visible: modelData.functioning !== null
                                width: 95; height: 28; radius: 14
                                color: functioningColor
                                Text {
                                    anchors.centerIn: parent
                                    text: "Function " + (modelData.functioning === "up" ? "↑" : "↓")
                                    font.pixelSize: 11
                                    color: "#ffffff"
                                }
                            }
                        }

                        // Relationship details (vary by type)
                        Column {
                            visible: modelData.relationship !== null
                            spacing: 4
                            width: parent.width

                            Rectangle {
                                width: Math.min(110, parent.width)
                                height: 28
                                radius: 14
                                color: relationshipColor

                                Text {
                                    anchors.centerIn: parent
                                    text: {
                                        var r = modelData.relationship
                                        if (r) return r.charAt(0).toUpperCase() + r.slice(1)
                                        return ""
                                    }
                                    font.pixelSize: 11
                                    color: "#ffffff"
                                }
                            }

                            // Targets (for conflict, distance, fusion, toward, away)
                            Text {
                                visible: modelData.relationshipTargets && modelData.relationshipTargets.length > 0 && modelData.relationship !== "cutoff"
                                text: "Target: " + (modelData.targetNames ? modelData.targetNames.join(", ") : "")
                                font.pixelSize: 11
                                color: inactiveText
                            }

                            // Triangle members (for projection)
                            Text {
                                visible: modelData.relationship === "projection" && modelData.relationshipTriangles && modelData.relationshipTriangles.length > 0
                                text: "Triangle (inside): " + (modelData.targetNames ? modelData.targetNames.join(", ") : "")
                                font.pixelSize: 11
                                color: inactiveText
                            }

                            Text {
                                visible: modelData.relationship === "projection" && modelData.triangleNames
                                text: "Triangle (outside): " + (modelData.triangleNames ? modelData.triangleNames.join(", ") : "")
                                font.pixelSize: 11
                                color: inactiveText
                            }

                            // Cutoff (no targets)
                            Text {
                                visible: modelData.relationship === "cutoff"
                                text: "Complete emotional cutoff"
                                font.pixelSize: 11
                                color: inactiveText
                            }
                        }
                    }
                }

                // Chevron
                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    y: 10
                    text: isSelected ? "▼" : "▶"
                    font.pixelSize: 10
                    color: inactiveText
                }
            }
        }
    }
}
