// Variant A: Thin vertical lines at cluster start positions
// Selected cluster shows label in fixed area above timeline
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
    height: 300
    title: "A: Vertical Lines"
    color: "#1e1e1e"

    property int selectedCluster: -1
    property real gLeft: 40
    property real gRight: width - 20
    property real gWidth: gRight - gLeft
    property real timelineY: 180
    property real minYear: 2024.5
    property real maxYear: 2026.2
    property real yearSpan: maxYear - minYear

    // Mock cluster data: 16 clusters with varying date ranges
    property var clusters: [
        {title: "Race Committee Conflict", pattern: "conflict_resolution", startYear: 2025.37, endYear: 2025.41},
        {title: "Work Stress Peak", pattern: "anxiety_cascade", startYear: 2025.42, endYear: 2025.45},
        {title: "Sleep Issues", pattern: "reciprocal_disturbance", startYear: 2025.41, endYear: 2025.43},
        {title: "Family Triangle", pattern: "triangle_activation", startYear: 2025.49, endYear: 2025.51},
        {title: "Job Uncertainty", pattern: "anxiety_cascade", startYear: 2025.54, endYear: 2025.56},
        {title: "Sailing Weekend", pattern: "functioning_gain", startYear: 2025.55, endYear: 2025.56},
        {title: "August Conflict", pattern: "conflict_resolution", startYear: 2025.60, endYear: 2025.62},
        {title: "Relocation News", pattern: "anxiety_cascade", startYear: 2025.63, endYear: 2025.65},
        {title: "September Shock", pattern: "anxiety_cascade", startYear: 2025.69, endYear: 2025.73},
        {title: "Wedding Trip", pattern: "functioning_gain", startYear: 2025.73, endYear: 2025.75},
        {title: "IVF Start", pattern: "reciprocal_disturbance", startYear: 2025.80, endYear: 2025.82},
        {title: "IVF Result", pattern: "anxiety_cascade", startYear: 2025.84, endYear: 2025.87},
        {title: "Family Visit", pattern: "triangle_activation", startYear: 2025.86, endYear: 2025.87},
        {title: "Holiday Tension", pattern: "conflict_resolution", startYear: 2025.98, endYear: 2026.00},
        {title: "New Year Reset", pattern: "functioning_gain", startYear: 2026.00, endYear: 2026.01},
        {title: "Planning Ahead", pattern: "functioning_gain", startYear: 2026.01, endYear: 2026.02}
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
        x: 20; y: 15
        text: "A: Thin Vertical Lines"
        font.pixelSize: 14
        font.bold: true
        color: "#ffffff"
    }

    Text {
        x: 20; y: 35
        text: "Lines at cluster start. Tap to select."
        font.pixelSize: 11
        color: "#909098"
    }

    // Selected cluster label area (fixed position)
    Rectangle {
        x: 20; y: 60
        width: parent.width - 40
        height: 50
        radius: 10
        color: "#252535"
        border.color: selectedCluster >= 0 ? patternColor(clusters[selectedCluster].pattern) : "#3a3a4a"
        border.width: selectedCluster >= 0 ? 2 : 1

        Column {
            anchors.centerIn: parent
            spacing: 2

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: selectedCluster >= 0 ? clusters[selectedCluster].title : "Tap a line to select cluster"
                font.pixelSize: 12
                font.bold: selectedCluster >= 0
                color: selectedCluster >= 0 ? "#ffffff" : "#606070"
            }

            Text {
                visible: selectedCluster >= 0
                anchors.horizontalCenter: parent.horizontalCenter
                text: selectedCluster >= 0 ? "Cluster " + (selectedCluster + 1) + " of 16" : ""
                font.pixelSize: 10
                color: "#909098"
            }
        }
    }

    // Timeline background
    Rectangle {
        x: 20; y: 120
        width: parent.width - 40
        height: 90
        radius: 10
        color: "#151520"
    }

    // Baseline
    Rectangle {
        x: gLeft; y: timelineY
        width: gWidth; height: 1
        color: "#3a3a4a"
    }

    // Year labels
    Repeater {
        model: [2025, 2026]
        Text {
            x: xPos(modelData) - 15
            y: timelineY + 10
            text: modelData
            font.pixelSize: 9
            color: "#606070"
        }
    }

    // Cluster vertical lines
    Repeater {
        model: clusters

        Rectangle {
            objectName: "clusterLine_" + index
            x: xPos(modelData.startYear) - 1.5
            y: timelineY - 50
            width: 3
            height: 50
            radius: 1.5
            color: patternColor(modelData.pattern)
            opacity: selectedCluster === index ? 1.0 : 0.7

            // Selection highlight
            Rectangle {
                visible: selectedCluster === index
                anchors.centerIn: parent
                width: 11
                height: 11
                radius: 5.5
                color: "transparent"
                border.color: patternColor(modelData.pattern)
                border.width: 2
            }

            MouseArea {
                anchors.fill: parent
                anchors.margins: -10
                cursorShape: Qt.PointingHandCursor
                onClicked: selectedCluster = (selectedCluster === index) ? -1 : index
            }
        }
    }

    // Instructions
    Text {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 15
        anchors.horizontalCenter: parent.horizontalCenter
        text: "16 clusters shown as thin colored lines"
        font.pixelSize: 10
        color: "#606070"
    }
}
