// Variant C4: Dense compact bars with pattern icons and smart stacking
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

Window {
    id: root
    visible: true
    x: 870
    y: 100
    width: 390
    height: 340
    title: "C4: Compact Dense"
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
    property real barHeight: 20
    property real barSpacing: 3

    property var clusters: [
        {title: "Race Committee Conflict", pattern: "conflict_resolution", startYear: 2025.37, endYear: 2025.41, row: 0, events: 7},
        {title: "Sleep Issues", pattern: "reciprocal_disturbance", startYear: 2025.41, endYear: 2025.44, row: 1, events: 4},
        {title: "Work Stress Peak", pattern: "anxiety_cascade", startYear: 2025.42, endYear: 2025.46, row: 2, events: 5},
        {title: "Family Triangle", pattern: "triangle_activation", startYear: 2025.49, endYear: 2025.52, row: 0, events: 6},
        {title: "Job Uncertainty", pattern: "anxiety_cascade", startYear: 2025.53, endYear: 2025.56, row: 1, events: 3},
        {title: "Sailing Weekend", pattern: "functioning_gain", startYear: 2025.55, endYear: 2025.57, row: 2, events: 4},
        {title: "August Conflict", pattern: "conflict_resolution", startYear: 2025.59, endYear: 2025.63, row: 0, events: 8},
        {title: "Relocation News", pattern: "anxiety_cascade", startYear: 2025.62, endYear: 2025.66, row: 1, events: 3},
        {title: "September Shock", pattern: "anxiety_cascade", startYear: 2025.68, endYear: 2025.74, row: 0, events: 4},
        {title: "Wedding Trip", pattern: "functioning_gain", startYear: 2025.72, endYear: 2025.76, row: 1, events: 2},
        {title: "IVF Start", pattern: "reciprocal_disturbance", startYear: 2025.79, endYear: 2025.83, row: 0, events: 3},
        {title: "IVF Result", pattern: "anxiety_cascade", startYear: 2025.83, endYear: 2025.88, row: 1, events: 5},
        {title: "Family Visit", pattern: "triangle_activation", startYear: 2025.85, endYear: 2025.88, row: 2, events: 2},
        {title: "Holiday Tension", pattern: "conflict_resolution", startYear: 2025.95, endYear: 2026.01, row: 0, events: 11},
        {title: "New Year Reset", pattern: "functioning_gain", startYear: 2025.99, endYear: 2026.02, row: 1, events: 4},
        {title: "Planning Ahead", pattern: "functioning_gain", startYear: 2026.01, endYear: 2026.04, row: 2, events: 2}
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

    function patternIcon(pattern) {
        switch (pattern) {
            case "anxiety_cascade": return "⚡"
            case "triangle_activation": return "△"
            case "conflict_resolution": return "⟷"
            case "reciprocal_disturbance": return "↔"
            case "functioning_gain": return "↑"
            default: return "•"
        }
    }

    function xPos(year) {
        return gLeft + ((year - minYear) / yearSpan) * gWidth
    }

    // Title
    Text {
        x: 16; y: 12
        text: "C4: Compact Dense + Icons"
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
                    width: patternRow.width + 12
                    height: 18
                    radius: 9
                    color: selectedCluster >= 0 ? patternColor(clusters[selectedCluster].pattern) : "transparent"
                    visible: selectedCluster >= 0

                    Row {
                        id: patternRow
                        anchors.centerIn: parent
                        spacing: 4

                        Text {
                            text: selectedCluster >= 0 ? patternIcon(clusters[selectedCluster].pattern) : ""
                            font.pixelSize: 10
                            color: "white"
                        }

                        Text {
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
    }

    // Graph background - fills space
    Rectangle {
        x: 12; y: graphTop - 8
        width: parent.width - 24
        height: graphHeight + 16
        radius: 12
        color: "#151520"

        // Subtle grid
        Repeater {
            model: 6
            Rectangle {
                x: 0
                y: 8 + index * (parent.height - 16) / 5
                width: parent.width
                height: 1
                color: "#1f1f2f"
            }
        }
    }

    // Year markers with vertical guides
    Repeater {
        model: [2025.4, 2025.6, 2025.8, 2026.0]
        Item {
            Rectangle {
                x: xPos(modelData)
                y: graphTop - 4
                width: 1
                height: graphHeight + 8
                color: "#252538"
            }
            Text {
                x: xPos(modelData) - 8
                y: graphBottom + 8
                text: {
                    if (modelData === 2026.0) return "'26"
                    var month = Math.round((modelData - 2025) * 12)
                    var months = ["J","F","M","A","M","J","J","A","S","O","N","D"]
                    return months[month] || ""
                }
                font.pixelSize: 9
                color: "#505060"
            }
        }
    }

    // Cluster bars - compact with icons
    Repeater {
        model: clusters

        Rectangle {
            objectName: "clusterBar_" + index
            property real rowY: graphTop + 8 + (modelData.row * (barHeight + barSpacing))
            property bool isSelected: selectedCluster === index

            x: xPos(modelData.startYear)
            y: rowY
            width: Math.max(24, xPos(modelData.endYear) - xPos(modelData.startYear))
            height: barHeight
            radius: 4
            color: patternColor(modelData.pattern)
            opacity: isSelected ? 1.0 : 0.8
            border.color: isSelected ? "#ffffff" : "transparent"
            border.width: isSelected ? 2 : 0

            Behavior on opacity { NumberAnimation { duration: 150 } }

            // Pattern icon on left
            Text {
                x: 4
                anchors.verticalCenter: parent.verticalCenter
                text: patternIcon(modelData.pattern)
                font.pixelSize: 11
                color: "white"
                opacity: 0.9
            }

            // Event count on right
            Text {
                anchors.right: parent.right
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.events
                font.pixelSize: 9
                font.bold: true
                color: "white"
                opacity: 0.9
                visible: parent.width > 35
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: selectedCluster = (selectedCluster === index) ? -1 : index
            }
        }
    }

    // Pattern legend at bottom
    Row {
        x: 16; y: parent.height - 28
        spacing: 12

        Repeater {
            model: [
                {p: "anxiety_cascade", l: "Anxiety"},
                {p: "conflict_resolution", l: "Conflict"},
                {p: "triangle_activation", l: "Triangle"},
                {p: "functioning_gain", l: "Gain"}
            ]

            Row {
                spacing: 3
                Rectangle {
                    width: 8; height: 8; radius: 2
                    color: patternColor(modelData.p)
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: modelData.l
                    font.pixelSize: 9
                    color: "#606070"
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
