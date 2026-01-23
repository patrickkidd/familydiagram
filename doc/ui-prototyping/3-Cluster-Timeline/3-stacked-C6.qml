// Variant C6: Pinch-zoom enabled - test with trackpad pinch on macOS
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
    height: 360
    title: "C6: Pinch-Zoom"
    color: "#1e1e1e"

    property int selectedCluster: -1
    property real baseMinYear: 2025.3
    property real baseMaxYear: 2026.1
    property real minYear: baseMinYear
    property real maxYear: baseMaxYear
    property real yearSpan: maxYear - minYear

    // Zoom state
    property real zoomLevel: 1.0
    property real zoomCenterYear: (baseMinYear + baseMaxYear) / 2
    property real minZoom: 1.0
    property real maxZoom: 4.0

    property real gLeft: 20
    property real gRight: width - 16
    property real gWidth: gRight - gLeft
    property real graphTop: 115
    property real graphBottom: 300
    property real graphHeight: graphBottom - graphTop
    property real barHeight: 28
    property real barSpacing: 2

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

    function updateZoom(newZoom, centerX) {
        // Convert center pixel to year
        var centerYear = minYear + ((centerX - gLeft) / gWidth) * yearSpan

        // Clamp zoom
        newZoom = Math.max(minZoom, Math.min(maxZoom, newZoom))

        // Calculate new year range centered on pinch point
        var baseSpan = baseMaxYear - baseMinYear
        var newSpan = baseSpan / newZoom

        minYear = centerYear - newSpan / 2
        maxYear = centerYear + newSpan / 2

        // Clamp to base range
        if (minYear < baseMinYear) {
            minYear = baseMinYear
            maxYear = minYear + newSpan
        }
        if (maxYear > baseMaxYear) {
            maxYear = baseMaxYear
            minYear = maxYear - newSpan
        }

        zoomLevel = newZoom
    }

    function resetZoom() {
        minYear = baseMinYear
        maxYear = baseMaxYear
        zoomLevel = 1.0
    }

    // Title
    Text {
        x: 16; y: 10
        text: "C6: Pinch-Zoom (trackpad/touch)"
        font.pixelSize: 13
        font.bold: true
        color: "#ffffff"
    }

    // Zoom indicator
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 16
        y: 10
        spacing: 8

        Text {
            text: "Zoom: " + zoomLevel.toFixed(1) + "x"
            font.pixelSize: 11
            color: "#909098"
        }

        Rectangle {
            width: 50
            height: 18
            radius: 9
            color: "#3a3a4a"
            visible: zoomLevel > 1.0

            Text {
                anchors.centerIn: parent
                text: "Reset"
                font.pixelSize: 9
                color: "#ffffff"
            }

            MouseArea {
                anchors.fill: parent
                onClicked: resetZoom()
            }
        }
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
                text: selectedCluster >= 0 ? clusters[selectedCluster].title : "Pinch to zoom, tap to select"
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

    // Graph area with pinch handler
    Rectangle {
        id: graphArea
        x: 12; y: graphTop - 6
        width: parent.width - 24
        height: graphHeight + 12
        radius: 12
        color: "#151520"
        clip: true

        PinchArea {
            id: pinchArea
            anchors.fill: parent
            pinch.minimumScale: 0.5
            pinch.maximumScale: 4.0

            property real startZoom: 1.0

            onPinchStarted: {
                startZoom = zoomLevel
            }

            onPinchUpdated: {
                var newZoom = startZoom * pinch.scale
                updateZoom(newZoom, pinch.center.x + graphArea.x)
            }

            // Allow clicks through to bars
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    // Find which bar was clicked
                    var clickYear = minYear + ((mouse.x - (gLeft - graphArea.x)) / gWidth) * yearSpan
                    for (var i = 0; i < clusters.length; i++) {
                        if (clickYear >= clusters[i].startYear && clickYear <= clusters[i].endYear) {
                            var rowY = 10 + clusters[i].row * (barHeight + barSpacing)
                            if (mouse.y >= rowY && mouse.y <= rowY + barHeight) {
                                selectedCluster = (selectedCluster === i) ? -1 : i
                                return
                            }
                        }
                    }
                    selectedCluster = -1
                }
            }
        }

        // Cluster bars inside clipped area
        Repeater {
            model: clusters

            Rectangle {
                objectName: "clusterBar_" + index
                property real rowY: 10 + modelData.row * (barHeight + barSpacing)
                property bool isSelected: selectedCluster === index
                property real barX: xPos(modelData.startYear) - graphArea.x
                property real barW: Math.max(20, xPos(modelData.endYear) - xPos(modelData.startYear))

                x: barX
                y: rowY
                width: barW
                height: barHeight
                radius: 6
                color: patternColor(modelData.pattern)
                opacity: isSelected ? 0.95 : 0.65
                border.color: isSelected ? "#ffffff" : Qt.lighter(patternColor(modelData.pattern), 1.3)
                border.width: isSelected ? 2 : 1
                visible: (barX + barW > 0) && (barX < graphArea.width)

                Behavior on opacity { NumberAnimation { duration: 150 } }
                Behavior on x { NumberAnimation { duration: 100 } }
                Behavior on width { NumberAnimation { duration: 100 } }

                Text {
                    anchors.centerIn: parent
                    width: parent.width - 8
                    text: parent.width > 60 ? modelData.title : modelData.title.split(" ")[0]
                    font.pixelSize: 10
                    font.bold: true
                    color: "white"
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    visible: parent.width > 25
                }
            }
        }
    }

    // Year labels (dynamic based on zoom)
    Row {
        x: gLeft; y: graphBottom + 8
        spacing: gWidth / 4 - 15

        Repeater {
            model: {
                var labels = []
                var step = yearSpan / 4
                for (var y = minYear; y <= maxYear; y += step) {
                    var month = Math.round((y - Math.floor(y)) * 12)
                    var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
                    labels.push(months[month] + " '" + (Math.floor(y) % 100))
                }
                return labels.slice(0, 5)
            }
            Text {
                text: modelData
                font.pixelSize: 9
                color: "#505060"
            }
        }
    }

    // Instructions
    Text {
        x: 16; y: parent.height - 24
        text: "Pinch trackpad to zoom • Same gesture works on iPhone"
        font.pixelSize: 10
        color: "#505060"
    }
}
