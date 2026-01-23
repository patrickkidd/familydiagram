// Variant C11: Variable height bars based on event count
// More events = taller bar, provides visual weight
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15

Window {
    id: root
    visible: true
    x: 870
    y: 100
    width: 390
    height: 300
    title: "C11: Variable Height"
    color: "#1e1e1e"

    property int selectedCluster: -1
    property real minZoom: 1.0
    property real maxZoom: 5.0
    property real zoomLevel: 1.0
    property real scrollX: 0

    property real viewportWidth: graphContainer.width - 16
    property real baseContentWidth: viewportWidth
    property real contentWidth: baseContentWidth * zoomLevel

    property real graphHeight: 160
    property real minBarHeight: 16
    property real maxBarHeight: 40

    property real minYear: 2025.3
    property real maxYear: 2026.1
    property real yearSpan: maxYear - minYear

    property var clusters: [
        {title: "Race Committee", pattern: "conflict_resolution", startYear: 2025.37, endYear: 2025.42, row: 0, events: 7},
        {title: "Sleep Issues", pattern: "reciprocal_disturbance", startYear: 2025.40, endYear: 2025.45, row: 1, events: 4},
        {title: "Work Stress", pattern: "anxiety_cascade", startYear: 2025.41, endYear: 2025.48, row: 2, events: 5},
        {title: "Family Triangle", pattern: "triangle_activation", startYear: 2025.48, endYear: 2025.53, row: 0, events: 6},
        {title: "Job Uncertainty", pattern: "anxiety_cascade", startYear: 2025.51, endYear: 2025.57, row: 1, events: 3},
        {title: "Sailing", pattern: "functioning_gain", startYear: 2025.54, endYear: 2025.58, row: 2, events: 4},
        {title: "August Conflict", pattern: "conflict_resolution", startYear: 2025.58, endYear: 2025.64, row: 0, events: 8},
        {title: "Relocation", pattern: "anxiety_cascade", startYear: 2025.61, endYear: 2025.67, row: 1, events: 3},
        {title: "September", pattern: "anxiety_cascade", startYear: 2025.66, endYear: 2025.74, row: 0, events: 4},
        {title: "Wedding", pattern: "functioning_gain", startYear: 2025.71, endYear: 2025.77, row: 1, events: 2},
        {title: "IVF Start", pattern: "reciprocal_disturbance", startYear: 2025.78, endYear: 2025.84, row: 2, events: 3},
        {title: "IVF Result", pattern: "anxiety_cascade", startYear: 2025.82, endYear: 2025.89, row: 0, events: 5},
        {title: "Family Visit", pattern: "triangle_activation", startYear: 2025.85, endYear: 2025.90, row: 1, events: 2},
        {title: "Holiday Tension", pattern: "conflict_resolution", startYear: 2025.94, endYear: 2026.02, row: 2, events: 11},
        {title: "New Year", pattern: "functioning_gain", startYear: 2025.98, endYear: 2026.04, row: 0, events: 4},
        {title: "Planning", pattern: "functioning_gain", startYear: 2026.02, endYear: 2026.07, row: 1, events: 2}
    ]

    // Find max events for scaling
    property int maxEvents: {
        var max = 0
        for (var i = 0; i < clusters.length; i++) {
            if (clusters[i].events > max) max = clusters[i].events
        }
        return max
    }

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

    function barHeightForEvents(events) {
        var ratio = events / maxEvents
        return minBarHeight + ratio * (maxBarHeight - minBarHeight)
    }

    // Zoom
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 12
        y: 6
        spacing: 6
        visible: zoomLevel > 1.05

        Text {
            text: zoomLevel.toFixed(1) + "x"
            font.pixelSize: 9
            color: "#505060"
        }

        Rectangle {
            width: 36; height: 16; radius: 8
            color: "#3a3a4a"

            Text {
                anchors.centerIn: parent
                text: "Reset"
                font.pixelSize: 8
                color: "#ffffff"
            }

            MouseArea {
                anchors.fill: parent
                onClicked: { zoomLevel = 1.0; scrollX = 0 }
            }
        }
    }

    // Graph
    Rectangle {
        id: graphContainer
        x: 8; y: 24
        width: parent.width - 16
        height: graphHeight + 12
        radius: 8
        color: "#0c0c14"
        clip: true

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.NoButton
            onWheel: {
                var deltaX = wheel.angleDelta.x !== 0 ? wheel.angleDelta.x : wheel.angleDelta.y
                var maxScroll = Math.max(0, contentWidth - pinchArea.width)
                scrollX = Math.max(0, Math.min(scrollX - deltaX * 0.5, maxScroll))
                wheel.accepted = true
            }
        }

        PinchArea {
            id: pinchArea
            anchors.fill: parent
            anchors.margins: 6

            property real startZoom: 1.0
            property real startScrollX: 0
            property point startCenter: Qt.point(0, 0)

            onPinchStarted: {
                startZoom = zoomLevel
                startScrollX = scrollX
                startCenter = pinch.center
            }

            onPinchUpdated: {
                var newZoom = Math.max(minZoom, Math.min(maxZoom, startZoom * pinch.scale))
                var newContentWidth = baseContentWidth * newZoom
                var pinchXRatio = (startCenter.x + startScrollX) / (baseContentWidth * startZoom)
                var newScrollX = pinchXRatio * newContentWidth - startCenter.x
                var maxScroll = Math.max(0, newContentWidth - pinchArea.width)
                scrollX = Math.max(0, Math.min(newScrollX, maxScroll))
                zoomLevel = newZoom
            }

            Item {
                x: -scrollX
                width: contentWidth
                height: graphHeight

                // Row baselines
                Repeater {
                    model: 3
                    Rectangle {
                        x: 0
                        y: (index + 1) * (graphHeight / 3) - 2
                        width: contentWidth
                        height: 1
                        color: "#1a1a24"
                    }
                }

                Repeater {
                    model: clusters

                    Rectangle {
                        objectName: "clusterBar_" + index
                        property bool isSelected: selectedCluster === index
                        property real barH: barHeightForEvents(modelData.events)
                        property real rowBaseline: (modelData.row + 1) * (graphHeight / 3) - 4

                        x: xPosForYear(modelData.startYear)
                        y: rowBaseline - barH
                        width: Math.max(16, xPosForYear(modelData.endYear) - xPosForYear(modelData.startYear))
                        height: barH
                        radius: 4
                        color: patternColor(modelData.pattern)
                        opacity: isSelected ? 1.0 : 0.8
                        border.color: isSelected ? "white" : "transparent"
                        border.width: isSelected ? 2 : 0

                        // Gradient for depth
                        Rectangle {
                            anchors.fill: parent
                            radius: parent.radius
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "#ffffff20" }
                                GradientStop { position: 1.0; color: "#00000020" }
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: modelData.title
                            font.pixelSize: 8
                            font.bold: true
                            color: "white"
                            elide: Text.ElideRight
                            width: parent.width - 8
                            horizontalAlignment: Text.AlignHCenter
                            visible: parent.width > 35 && parent.height > 20
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: selectedCluster = (selectedCluster === index) ? -1 : index
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    z: -1
                    property real dragStartX: 0
                    property real dragStartScrollX: 0
                    property bool isDragging: false

                    onPressed: { dragStartX = mouse.x; dragStartScrollX = scrollX; isDragging = false }
                    onPositionChanged: {
                        if (pressed && Math.abs(mouse.x - dragStartX) > 5) {
                            isDragging = true
                            var maxScroll = Math.max(0, contentWidth - pinchArea.width)
                            scrollX = Math.max(0, Math.min(dragStartScrollX + dragStartX - mouse.x, maxScroll))
                        }
                    }
                    onReleased: if (!isDragging) selectedCluster = -1
                }
            }
        }

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 2
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.5
            height: 3
            radius: 1.5
            color: "#18181f"
            visible: zoomLevel > 1.05

            Rectangle {
                x: parent.width * (scrollX / contentWidth)
                width: Math.max(14, parent.width / zoomLevel)
                height: parent.height
                radius: parent.radius
                color: "#505060"
            }
        }
    }

    // Year labels
    Row {
        x: 14; y: graphContainer.y + graphContainer.height + 4
        spacing: (parent.width - 80) / 4

        Repeater {
            model: ["May'25", "Jul", "Sep", "Nov", "Jan'26"]
            Text { text: modelData; font.pixelSize: 8; color: "#404050" }
        }
    }

    // Selected info
    Rectangle {
        visible: selectedCluster >= 0
        x: 8; y: parent.height - 44
        width: parent.width - 16
        height: 36
        radius: 6
        color: "#202030"
        border.color: selectedCluster >= 0 ? patternColor(clusters[selectedCluster].pattern) : "transparent"
        border.width: 2

        Row {
            anchors.centerIn: parent
            spacing: 16

            Text {
                text: selectedCluster >= 0 ? clusters[selectedCluster].title : ""
                font.pixelSize: 11
                font.bold: true
                color: "white"
            }

            Text {
                text: selectedCluster >= 0 ? clusters[selectedCluster].events + " events" : ""
                font.pixelSize: 10
                color: "#909098"
            }

            Text {
                text: selectedCluster >= 0 ? "Height shows event count" : ""
                font.pixelSize: 9
                color: "#606070"
            }
        }
    }
}
