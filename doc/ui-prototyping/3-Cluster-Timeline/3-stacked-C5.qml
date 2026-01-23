// Variant C5: Aggressive stacking with semi-transparency for overlaps
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
    height: 360
    title: "C5: Translucent Overlap"
    color: "#1e1e1e"

    property int selectedCluster: -1
    property real gLeft: 20
    property real gRight: width - 16
    property real gWidth: gRight - gLeft
    property real graphTop: 115
    property real graphBottom: 300
    property real graphHeight: graphBottom - graphTop
    property real minYear: 2025.3
    property real maxYear: 2026.1
    property real yearSpan: maxYear - minYear
    property real barHeight: 28
    property real barSpacing: 2

    // Clusters with overlapping time ranges - 5 rows to show density
    property var clusters: [
        {title: "Race Committee Conflict", pattern: "conflict_resolution", startYear: 2025.37, endYear: 2025.42, row: 0, events: 7},
        {title: "Sleep Issues", pattern: "reciprocal_disturbance", startYear: 2025.40, endYear: 2025.45, row: 1, events: 4},
        {title: "Work Stress Peak", pattern: "anxiety_cascade", startYear: 2025.41, endYear: 2025.48, row: 2, events: 5},
        {title: "Family Triangle", pattern: "triangle_activation", startYear: 2025.48, endYear: 2025.53, row: 0, events: 6},
        {title: "Job Uncertainty", pattern: "anxiety_cascade", startYear: 2025.51, endYear: 2025.57, row: 1, events: 3},
        {title: "Sailing Weekend", pattern: "functioning_gain", startYear: 2025.54, endYear: 2025.58, row: 2, events: 4},
        {title: "August Conflict", pattern: "conflict_resolution", startYear: 2025.58, endYear: 2025.64, row: 0, events: 8},
        {title: "Relocation News", pattern: "anxiety_cascade", startYear: 2025.61, endYear: 2025.67, row: 1, events: 3},
        {title: "September Shock", pattern: "anxiety_cascade", startYear: 2025.66, endYear: 2025.74, row: 0, events: 4},
        {title: "Wedding Trip", pattern: "functioning_gain", startYear: 2025.71, endYear: 2025.77, row: 1, events: 2},
        {title: "IVF Start", pattern: "reciprocal_disturbance", startYear: 2025.78, endYear: 2025.84, row: 0, events: 3},
        {title: "IVF Result", pattern: "anxiety_cascade", startYear: 2025.82, endYear: 2025.89, row: 1, events: 5},
        {title: "Family Visit", pattern: "triangle_activation", startYear: 2025.85, endYear: 2025.90, row: 2, events: 2},
        {title: "Holiday Tension", pattern: "conflict_resolution", startYear: 2025.94, endYear: 2026.02, row: 0, events: 11},
        {title: "New Year Reset", pattern: "functioning_gain", startYear: 2025.98, endYear: 2026.04, row: 1, events: 4},
        {title: "Planning Ahead", pattern: "functioning_gain", startYear: 2026.02, endYear: 2026.07, row: 2, events: 2}
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
        x: 16; y: 10
        text: "C5: Translucent Overlapping"
        font.pixelSize: 13
        font.bold: true
        color: "#ffffff"
    }

    // Selected cluster info
    Rectangle {
        x: 16; y: 34
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

            Text {
                visible: selectedCluster >= 0
                anchors.horizontalCenter: parent.horizontalCenter
                text: selectedCluster >= 0 ? clusters[selectedCluster].events + " events" : ""
                font.pixelSize: 11
                color: "#909098"
            }
        }
    }

    // Graph background
    Rectangle {
        x: 12; y: graphTop - 6
        width: parent.width - 24
        height: graphHeight + 12
        radius: 12
        color: "#151520"
    }

    // Cluster bars - translucent with visible overlaps
    Repeater {
        model: clusters

        Rectangle {
            objectName: "clusterBar_" + index
            property real rowY: graphTop + 4 + (modelData.row * (barHeight + barSpacing))
            property bool isSelected: selectedCluster === index

            x: xPos(modelData.startYear)
            y: rowY
            width: Math.max(20, xPos(modelData.endYear) - xPos(modelData.startYear))
            height: barHeight
            radius: 6
            color: patternColor(modelData.pattern)
            opacity: isSelected ? 0.95 : 0.6
            border.color: isSelected ? "#ffffff" : Qt.lighter(patternColor(modelData.pattern), 1.3)
            border.width: isSelected ? 2 : 1

            Behavior on opacity { NumberAnimation { duration: 150 } }

            // Inner glow effect
            Rectangle {
                anchors.fill: parent
                anchors.margins: 2
                radius: 4
                color: "transparent"
                border.color: "#ffffff"
                border.width: 1
                opacity: 0.15
            }

            // Title text (truncated)
            Text {
                anchors.centerIn: parent
                width: parent.width - 8
                text: modelData.title.split(" ")[0]  // First word only
                font.pixelSize: 10
                font.bold: true
                color: "white"
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                visible: parent.width > 30
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: selectedCluster = (selectedCluster === index) ? -1 : index
            }
        }
    }

    // Year labels
    Row {
        x: gLeft; y: graphBottom + 8
        spacing: (gWidth - 60) / 3

        Repeater {
            model: ["May", "Jul", "Sep", "Nov", "Jan"]
            Text {
                text: modelData
                font.pixelSize: 9
                color: "#505060"
                width: 30
            }
        }
    }

    // Legend
    Text {
        x: 16; y: parent.height - 24
        text: "Overlapping bars show concurrent clusters"
        font.pixelSize: 10
        color: "#505060"
    }
}
