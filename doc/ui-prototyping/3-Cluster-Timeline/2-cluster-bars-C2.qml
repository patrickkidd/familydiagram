// Variant C2: Full-height stacked bars using all available vertical space
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

Window {
    id: root
    visible: true
    x: 50
    y: 100
    width: 390
    height: 340
    title: "C2: Full-Height Bars"
    color: "#1e1e1e"

    property int selectedCluster: -1
    property real gLeft: 24
    property real gRight: width - 16
    property real gWidth: gRight - gLeft
    property real graphTop: 120
    property real graphBottom: 280
    property real graphHeight: graphBottom - graphTop
    property real minYear: 2025.3
    property real maxYear: 2026.1
    property real yearSpan: maxYear - minYear
    property int maxRows: 4
    property real barHeight: (graphHeight - (maxRows - 1) * 4) / maxRows

    property var clusters: [
        {title: "Race Committee Conflict", pattern: "conflict_resolution", startYear: 2025.37, endYear: 2025.41, row: 0, events: 7},
        {title: "Sleep Issues", pattern: "reciprocal_disturbance", startYear: 2025.41, endYear: 2025.43, row: 1, events: 4},
        {title: "Work Stress Peak", pattern: "anxiety_cascade", startYear: 2025.42, endYear: 2025.45, row: 2, events: 5},
        {title: "Family Triangle", pattern: "triangle_activation", startYear: 2025.49, endYear: 2025.51, row: 0, events: 6},
        {title: "Job Uncertainty", pattern: "anxiety_cascade", startYear: 2025.54, endYear: 2025.56, row: 0, events: 3},
        {title: "Sailing Weekend", pattern: "functioning_gain", startYear: 2025.55, endYear: 2025.56, row: 1, events: 4},
        {title: "August Conflict", pattern: "conflict_resolution", startYear: 2025.60, endYear: 2025.62, row: 0, events: 8},
        {title: "Relocation News", pattern: "anxiety_cascade", startYear: 2025.63, endYear: 2025.65, row: 0, events: 3},
        {title: "September Shock", pattern: "anxiety_cascade", startYear: 2025.69, endYear: 2025.73, row: 0, events: 4},
        {title: "Wedding Trip", pattern: "functioning_gain", startYear: 2025.73, endYear: 2025.75, row: 1, events: 2},
        {title: "IVF Start", pattern: "reciprocal_disturbance", startYear: 2025.80, endYear: 2025.82, row: 0, events: 3},
        {title: "IVF Result", pattern: "anxiety_cascade", startYear: 2025.84, endYear: 2025.87, row: 0, events: 5},
        {title: "Family Visit", pattern: "triangle_activation", startYear: 2025.86, endYear: 2025.87, row: 1, events: 2},
        {title: "Holiday Tension", pattern: "conflict_resolution", startYear: 2025.98, endYear: 2026.00, row: 0, events: 11},
        {title: "New Year Reset", pattern: "functioning_gain", startYear: 2026.00, endYear: 2026.01, row: 1, events: 4},
        {title: "Planning Ahead", pattern: "functioning_gain", startYear: 2026.01, endYear: 2026.02, row: 0, events: 2}
    ]

    function patternColor(pattern) {
        switch (pattern) {
            case "anxiety_cascade": return "#e74c3c"
            case "triangle_activation": return "#9b59b6"
            case "conflict_resolution": return "#27ae60"
            case "reciprocal_disturbance": return "#e67e22"
            case "functioning_gain": return "#3498db"
            default: return "#909098"
        }
    }

    function xPos(year) {
        return gLeft + ((year - minYear) / yearSpan) * gWidth
    }

    // Title
    Text {
        x: 16; y: 12
        text: "C2: Full-Height Stacked Bars"
        font.pixelSize: 13
        font.bold: true
        color: "#ffffff"
    }

    // Selected cluster info area
    Rectangle {
        x: 16; y: 38
        width: parent.width - 32
        height: 70
        radius: 12
        color: "#252535"
        border.color: selectedCluster >= 0 ? patternColor(clusters[selectedCluster].pattern) : "#3a3a4a"
        border.width: selectedCluster >= 0 ? 2 : 1

        Column {
            anchors.centerIn: parent
            spacing: 4

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: selectedCluster >= 0 ? clusters[selectedCluster].title : "Tap a bar to select"
                font.pixelSize: 13
                font.bold: selectedCluster >= 0
                color: selectedCluster >= 0 ? "#ffffff" : "#606070"
            }

            Row {
                visible: selectedCluster >= 0
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 12

                Text {
                    text: selectedCluster >= 0 ? clusters[selectedCluster].events + " events" : ""
                    font.pixelSize: 11
                    color: "#909098"
                }

                Rectangle {
                    width: patternText.width + 12
                    height: 18
                    radius: 9
                    color: selectedCluster >= 0 ? patternColor(clusters[selectedCluster].pattern) : "transparent"
                    visible: selectedCluster >= 0

                    Text {
                        id: patternText
                        anchors.centerIn: parent
                        text: {
                            if (selectedCluster < 0) return ""
                            var p = clusters[selectedCluster].pattern
                            return p.replace(/_/g, " ").replace(/\b\w/g, function(l){ return l.toUpperCase() })
                        }
                        font.pixelSize: 9
                        font.bold: true
                        color: "white"
                    }
                }
            }
        }
    }

    // Graph background - fills available space
    Rectangle {
        x: 12; y: graphTop - 8
        width: parent.width - 24
        height: graphHeight + 16
        radius: 12
        color: "#151520"
    }

    // Year markers
    Repeater {
        model: [2025.5, 2026.0]
        Item {
            Rectangle {
                x: xPos(modelData)
                y: graphTop - 4
                width: 1
                height: graphHeight + 8
                color: "#2a2a3a"
            }
            Text {
                x: xPos(modelData) - 20
                y: graphBottom + 8
                text: modelData === 2026.0 ? "2026" : "Mid '25"
                font.pixelSize: 9
                color: "#505060"
            }
        }
    }

    // Cluster bars - full height rows
    Repeater {
        model: clusters

        Rectangle {
            objectName: "clusterBar_" + index
            property real rowY: graphTop + (modelData.row * (barHeight + 4))

            x: xPos(modelData.startYear)
            y: rowY
            width: Math.max(12, xPos(modelData.endYear) - xPos(modelData.startYear))
            height: barHeight
            radius: 6
            color: patternColor(modelData.pattern)
            opacity: selectedCluster === index ? 1.0 : 0.75
            border.color: selectedCluster === index ? "#ffffff" : "transparent"
            border.width: selectedCluster === index ? 2 : 0

            Behavior on opacity { NumberAnimation { duration: 150 } }

            // Event count indicator
            Text {
                anchors.centerIn: parent
                text: modelData.events
                font.pixelSize: 10
                font.bold: true
                color: "white"
                opacity: 0.9
                visible: parent.width > 20
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: selectedCluster = (selectedCluster === index) ? -1 : index
            }
        }
    }

    // Legend
    Row {
        x: 16; y: parent.height - 28
        spacing: 8

        Text {
            text: "16 clusters"
            font.pixelSize: 10
            color: "#606070"
        }

        Text {
            text: "|"
            font.pixelSize: 10
            color: "#404050"
        }

        Text {
            text: "Numbers = event count"
            font.pixelSize: 10
            color: "#606070"
        }
    }
}
