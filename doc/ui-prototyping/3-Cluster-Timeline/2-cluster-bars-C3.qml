// Variant C3: Variable height bars - height indicates event count/intensity
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

Window {
    id: root
    visible: true
    x: 460
    y: 100
    width: 390
    height: 340
    title: "C3: Variable Height"
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
    property real minBarHeight: 16
    property real maxBarHeight: graphHeight * 0.9
    property int maxEvents: 11  // max events in any cluster

    property var clusters: [
        {title: "Race Committee Conflict", pattern: "conflict_resolution", startYear: 2025.37, endYear: 2025.41, events: 7},
        {title: "Sleep Issues", pattern: "reciprocal_disturbance", startYear: 2025.41, endYear: 2025.43, events: 4},
        {title: "Work Stress Peak", pattern: "anxiety_cascade", startYear: 2025.44, endYear: 2025.47, events: 5},
        {title: "Family Triangle", pattern: "triangle_activation", startYear: 2025.49, endYear: 2025.51, events: 6},
        {title: "Job Uncertainty", pattern: "anxiety_cascade", startYear: 2025.54, endYear: 2025.56, events: 3},
        {title: "Sailing Weekend", pattern: "functioning_gain", startYear: 2025.57, endYear: 2025.58, events: 4},
        {title: "August Conflict", pattern: "conflict_resolution", startYear: 2025.60, endYear: 2025.62, events: 8},
        {title: "Relocation News", pattern: "anxiety_cascade", startYear: 2025.63, endYear: 2025.65, events: 3},
        {title: "September Shock", pattern: "anxiety_cascade", startYear: 2025.69, endYear: 2025.73, events: 4},
        {title: "Wedding Trip", pattern: "functioning_gain", startYear: 2025.74, endYear: 2025.76, events: 2},
        {title: "IVF Start", pattern: "reciprocal_disturbance", startYear: 2025.80, endYear: 2025.82, events: 3},
        {title: "IVF Result", pattern: "anxiety_cascade", startYear: 2025.84, endYear: 2025.87, events: 5},
        {title: "Family Visit", pattern: "triangle_activation", startYear: 2025.88, endYear: 2025.89, events: 2},
        {title: "Holiday Tension", pattern: "conflict_resolution", startYear: 2025.96, endYear: 2026.00, events: 11},
        {title: "New Year Reset", pattern: "functioning_gain", startYear: 2026.01, endYear: 2026.02, events: 4},
        {title: "Planning Ahead", pattern: "functioning_gain", startYear: 2026.03, endYear: 2026.05, events: 2}
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

    function barHeightForEvents(events) {
        var ratio = events / maxEvents
        return minBarHeight + ratio * (maxBarHeight - minBarHeight)
    }

    // Title
    Text {
        x: 16; y: 12
        text: "C3: Variable Height (by event count)"
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

    // Graph background
    Rectangle {
        x: 12; y: graphTop - 8
        width: parent.width - 24
        height: graphHeight + 16
        radius: 12
        color: "#151520"
    }

    // Baseline
    Rectangle {
        x: gLeft; y: graphBottom
        width: gWidth; height: 1
        color: "#3a3a4a"
    }

    // Year markers
    Repeater {
        model: [2025.5, 2026.0]
        Item {
            Rectangle {
                x: xPos(modelData)
                y: graphTop
                width: 1
                height: graphHeight
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

    // Cluster bars - height based on event count, all anchored to baseline
    Repeater {
        model: clusters

        Rectangle {
            objectName: "clusterBar_" + index
            property real bHeight: barHeightForEvents(modelData.events)

            x: xPos(modelData.startYear)
            y: graphBottom - bHeight
            width: Math.max(12, xPos(modelData.endYear) - xPos(modelData.startYear))
            height: bHeight
            radius: 4
            color: patternColor(modelData.pattern)
            opacity: selectedCluster === index ? 1.0 : 0.7
            border.color: selectedCluster === index ? "#ffffff" : "transparent"
            border.width: selectedCluster === index ? 2 : 0

            Behavior on opacity { NumberAnimation { duration: 150 } }

            // Gradient overlay for depth
            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#ffffff20" }
                    GradientStop { position: 0.3; color: "transparent" }
                    GradientStop { position: 1.0; color: "#00000030" }
                }
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
            text: "Bar height = event count"
            font.pixelSize: 10
            color: "#606070"
        }

        Text {
            text: "|"
            font.pixelSize: 10
            color: "#404050"
        }

        Text {
            text: "Taller = more events"
            font.pixelSize: 10
            color: "#606070"
        }
    }
}
