// Variant C8: Horizontal-only zoom with native pan
// Timeline stretches horizontally, bar heights stay constant
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15

Window {
    id: root
    visible: true
    x: 50
    y: 100
    width: 390
    height: 380
    title: "C8: X-Axis Zoom + Pan"
    color: "#1e1e1e"

    property int selectedCluster: -1
    property real minZoom: 1.0
    property real maxZoom: 5.0
    property real zoomLevel: 1.0
    property real scrollX: 0  // Manual scroll position

    property real viewportWidth: graphContainer.width - 16
    property real baseContentWidth: viewportWidth  // At zoom 1x, content fits viewport
    property real contentWidth: baseContentWidth * zoomLevel

    property real graphHeight: 120
    property real barHeight: 32
    property real barSpacing: 4

    // Time range
    property real minYear: 2025.3
    property real maxYear: 2026.1
    property real yearSpan: maxYear - minYear

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

    function xPosForYear(year) {
        return ((year - minYear) / yearSpan) * contentWidth
    }

    function resetZoom() {
        zoomLevel = 1.0
        flickable.contentX = 0
    }

    // Title
    Text {
        x: 16; y: 10
        text: "C8: Horizontal Zoom + Pan"
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
            text: zoomLevel.toFixed(1) + "x"
            font.pixelSize: 11
            color: "#909098"
        }

        Rectangle {
            width: 50; height: 20; radius: 10
            color: "#3a3a4a"
            visible: zoomLevel > 1.05

            Text {
                anchors.centerIn: parent
                text: "Reset"
                font.pixelSize: 10
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
        x: 16; y: 36
        width: parent.width - 32
        height: 60
        radius: 12
        color: "#252535"
        border.color: selectedCluster >= 0 ? patternColor(clusters[selectedCluster].pattern) : "#3a3a4a"
        border.width: selectedCluster >= 0 ? 2 : 1

        Text {
            anchors.centerIn: parent
            text: selectedCluster >= 0 ? clusters[selectedCluster].title + " (" + clusters[selectedCluster].events + " events)" : "Pinch to zoom X • Drag to pan • Tap to select"
            font.pixelSize: 12
            font.bold: selectedCluster >= 0
            color: selectedCluster >= 0 ? "#ffffff" : "#606070"
        }
    }

    // Graph container
    Rectangle {
        id: graphContainer
        x: 12; y: 106
        width: parent.width - 24
        height: graphHeight + 20
        radius: 12
        color: "#151520"
        clip: true

        // Top-level wheel handler for pan (catches events before they reach children)
        MouseArea {
            id: wheelHandler
            anchors.fill: parent
            acceptedButtons: Qt.NoButton  // Don't steal clicks
            propagateComposedEvents: true

            onWheel: {
                var deltaX = wheel.angleDelta.x !== 0 ? wheel.angleDelta.x : wheel.angleDelta.y
                var panAmount = -deltaX * 0.5

                var maxScroll = Math.max(0, contentWidth - pinchArea.width)
                var newScrollX = Math.max(0, Math.min(scrollX + panAmount, maxScroll))

                scrollX = newScrollX
                wheel.accepted = true
            }
        }

        // Single PinchArea that handles both zoom AND pan during pinch
        // Moving fingers together = pan, spreading/pinching = zoom
        PinchArea {
            id: pinchArea
            anchors.fill: parent
            anchors.margins: 8

            property real startZoom: 1.0
            property real startScrollX: 0
            property point startCenter: Qt.point(0, 0)
            property point lastCenter: Qt.point(0, 0)
            property real accumulatedPan: 0  // Track pan separately

            onPinchStarted: {
                startZoom = zoomLevel
                startScrollX = scrollX
                startCenter = pinch.center
                lastCenter = pinch.center
                accumulatedPan = 0
            }

            onPinchUpdated: {
                // ZOOM: scale change
                var newZoom = Math.max(minZoom, Math.min(maxZoom, startZoom * pinch.scale))
                var newContentWidth = baseContentWidth * newZoom

                // Calculate scroll to keep original pinch point stationary
                var pinchXRatio = (startCenter.x + startScrollX) / (baseContentWidth * startZoom)
                var newScrollForZoom = pinchXRatio * newContentWidth - startCenter.x

                // PAN: accumulate center movement (both fingers moving together)
                var panDelta = lastCenter.x - pinch.center.x
                lastCenter = pinch.center
                accumulatedPan += panDelta

                // Combined: zoom position + accumulated pan
                var newScrollX = newScrollForZoom + accumulatedPan

                // Clamp scroll
                var maxScroll = Math.max(0, newContentWidth - pinchArea.width)
                newScrollX = Math.max(0, Math.min(newScrollX, maxScroll))

                zoomLevel = newZoom
                scrollX = newScrollX
            }

            // Content container that scrolls
            Item {
                id: contentContainer
                x: -scrollX
                width: contentWidth
                height: graphHeight

                // Year grid lines
                Repeater {
                    model: Math.ceil(yearSpan * 4 * zoomLevel) + 1
                    Rectangle {
                        property real yearVal: minYear + index / (4 * zoomLevel)
                        x: xPosForYear(yearVal)
                        y: 0
                        width: 1
                        height: graphHeight
                        color: "#252538"
                        visible: x >= -scrollX && x <= -scrollX + pinchArea.width + 50
                    }
                }

                // Cluster bars
                Repeater {
                    model: clusters

                    Rectangle {
                        id: bar
                        objectName: "clusterBar_" + index
                        property real rowY: modelData.row * (barHeight + barSpacing)
                        property bool isSelected: selectedCluster === index

                        x: xPosForYear(modelData.startYear)
                        y: rowY
                        width: Math.max(24, xPosForYear(modelData.endYear) - xPosForYear(modelData.startYear))
                        height: barHeight
                        radius: height / 2
                        color: patternColor(modelData.pattern)
                        opacity: isSelected ? 1.0 : 0.75
                        border.color: isSelected ? "#ffffff" : "transparent"
                        border.width: isSelected ? 2 : 0

                        Rectangle {
                            x: 2; y: 2; z: -1
                            width: parent.width; height: parent.height
                            radius: parent.radius
                            color: "#000000"
                            opacity: 0.3
                        }

                        Rectangle {
                            anchors.fill: parent
                            radius: parent.radius
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "#ffffff30" }
                                GradientStop { position: 0.5; color: "transparent" }
                                GradientStop { position: 1.0; color: "#00000030" }
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            width: parent.width - 16
                            text: parent.width > 100 ? modelData.title : modelData.title.split(" ")[0]
                            font.pixelSize: 10
                            font.bold: true
                            color: "white"
                            elide: Text.ElideRight
                            horizontalAlignment: Text.AlignHCenter
                            visible: parent.width > 30
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: selectedCluster = (selectedCluster === index) ? -1 : index
                        }
                    }
                }

                // Background: tap to deselect AND drag to pan (combined)
                MouseArea {
                    anchors.fill: parent
                    z: -1

                    property real dragStartX: 0
                    property real dragStartScrollX: 0
                    property bool isDragging: false

                    onPressed: {
                        dragStartX = mouse.x
                        dragStartScrollX = scrollX
                        isDragging = false
                    }

                    onPositionChanged: {
                        if (pressed) {
                            var delta = Math.abs(mouse.x - dragStartX)
                            if (delta > 5) isDragging = true

                            if (isDragging) {
                                var panDelta = dragStartX - mouse.x
                                var maxScroll = Math.max(0, contentWidth - pinchArea.width)
                                var newScrollX = Math.max(0, Math.min(dragStartScrollX + panDelta, maxScroll))
                                scrollX = newScrollX
                            }
                        }
                    }

                    onReleased: {
                        if (!isDragging) {
                            selectedCluster = -1
                        }
                    }
                }
            }
        }

        // Scroll position indicator
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 2
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.7
            height: 4
            radius: 2
            color: "#2a2a3a"
            visible: zoomLevel > 1.05

            Rectangle {
                x: parent.width * (scrollX / contentWidth)
                width: Math.max(20, parent.width / zoomLevel)
                height: parent.height
                radius: parent.radius
                color: "#707080"
            }
        }
    }

    // Static year labels (full range)
    Row {
        x: 24; y: graphContainer.y + graphContainer.height + 8
        spacing: (parent.width - 80) / 4

        Repeater {
            model: ["May'25", "Jul", "Sep", "Nov", "Jan'26"]
            Text {
                text: modelData
                font.pixelSize: 9
                color: "#505060"
            }
        }
    }

    // Instructions
    Column {
        x: 16; y: parent.height - 60
        spacing: 4

        Text { text: "Interactions:"; font.pixelSize: 11; font.bold: true; color: "#707080" }
        Text { text: "• Pinch to zoom timeline horizontally"; font.pixelSize: 10; color: "#505060" }
        Text { text: "• Drag to pan (when zoomed)"; font.pixelSize: 10; color: "#505060" }
        Text { text: "• Tap cluster to select"; font.pixelSize: 10; color: "#505060" }
    }
}
