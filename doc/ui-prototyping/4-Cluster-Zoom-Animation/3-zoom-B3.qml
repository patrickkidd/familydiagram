// Variant B3: Larger graph area, events as subtle vertical lines
// Events integrated into graph instead of separate timeline
import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    width: 390
    height: 300
    color: "#1e1e1e"

    property int selectedCluster: -1
    property bool isFocused: false
    property int focusedClusterIndex: -1
    property real animProgress: 0

    property real zoomLevel: 1.0
    property real scrollX: 0

    property real viewportWidth: graphContainer.width - 16
    property real baseContentWidth: viewportWidth
    property real contentWidth: baseContentWidth * zoomLevel

    property real graphHeight: 140
    property real barHeight: 28
    property real barSpacing: 6

    property real minYear: 2025.3
    property real maxYear: 2026.1
    property real yearSpan: maxYear - minYear

    property real heroStartX: 0
    property real heroStartY: 0
    property real heroStartW: 0
    property real heroStartH: 0

    readonly property color sarfS: "#3498db"
    readonly property color sarfA: "#e74c3c"
    readonly property color sarfR: "#9b59b6"
    readonly property color sarfF: "#27ae60"

    property var clusters: [
        {title: "Race Committee", pattern: "conflict_resolution", startYear: 2025.37, endYear: 2025.42, row: 0,
         events: [
            {year: 2025.37, label: "Conflict starts"},
            {year: 2025.38, label: "Escalation"},
            {year: 2025.39, label: "Discussion"},
            {year: 2025.40, label: "Resolution attempt"},
            {year: 2025.41, label: "Agreement"},
            {year: 2025.42, label: "Closure"}
         ],
         sarf: [
            {year: 2025.37, s: 0.6, a: 0.3, r: 0.4, f: 0.7},
            {year: 2025.38, s: 0.5, a: 0.6, r: 0.7, f: 0.5},
            {year: 2025.39, s: 0.4, a: 0.7, r: 0.8, f: 0.4},
            {year: 2025.40, s: 0.5, a: 0.5, r: 0.6, f: 0.5},
            {year: 2025.41, s: 0.6, a: 0.3, r: 0.4, f: 0.6},
            {year: 2025.42, s: 0.7, a: 0.2, r: 0.3, f: 0.8}
         ]
        },
        {title: "Work Stress", pattern: "anxiety_cascade", startYear: 2025.41, endYear: 2025.48, row: 2,
         events: [
            {year: 2025.41, label: "Deadline"},
            {year: 2025.43, label: "Workload"},
            {year: 2025.45, label: "Sleep issues"},
            {year: 2025.47, label: "Burnout"},
            {year: 2025.48, label: "Time off"}
         ],
         sarf: [
            {year: 2025.41, s: 0.7, a: 0.3, r: 0.3, f: 0.7},
            {year: 2025.43, s: 0.5, a: 0.5, r: 0.5, f: 0.5},
            {year: 2025.45, s: 0.3, a: 0.7, r: 0.7, f: 0.3},
            {year: 2025.47, s: 0.2, a: 0.9, r: 0.8, f: 0.2},
            {year: 2025.48, s: 0.4, a: 0.6, r: 0.5, f: 0.4}
         ]
        },
        {title: "Family Triangle", pattern: "triangle_activation", startYear: 2025.48, endYear: 2025.53, row: 0,
         events: [
            {year: 2025.48, label: "Tension"},
            {year: 2025.49, label: "Side-taking"},
            {year: 2025.50, label: "Peak"},
            {year: 2025.51, label: "Mediation"},
            {year: 2025.52, label: "Resolution"},
            {year: 2025.53, label: "Equilibrium"}
         ],
         sarf: [
            {year: 2025.48, s: 0.6, a: 0.4, r: 0.5, f: 0.6},
            {year: 2025.49, s: 0.4, a: 0.6, r: 0.7, f: 0.4},
            {year: 2025.50, s: 0.3, a: 0.8, r: 0.9, f: 0.3},
            {year: 2025.51, s: 0.4, a: 0.6, r: 0.7, f: 0.4},
            {year: 2025.52, s: 0.5, a: 0.4, r: 0.5, f: 0.5},
            {year: 2025.53, s: 0.6, a: 0.3, r: 0.4, f: 0.6}
         ]
        },
        {title: "Holiday Tension", pattern: "conflict_resolution", startYear: 2025.94, endYear: 2026.02, row: 0,
         events: [
            {year: 2025.94, label: "Planning"},
            {year: 2025.96, label: "Arrival"},
            {year: 2025.97, label: "Tension"},
            {year: 2025.98, label: "Argument"},
            {year: 2026.00, label: "Apologies"},
            {year: 2026.02, label: "Departure"}
         ],
         sarf: [
            {year: 2025.94, s: 0.7, a: 0.2, r: 0.3, f: 0.7},
            {year: 2025.96, s: 0.5, a: 0.5, r: 0.5, f: 0.5},
            {year: 2025.97, s: 0.3, a: 0.7, r: 0.8, f: 0.3},
            {year: 2025.98, s: 0.2, a: 0.9, r: 0.9, f: 0.2},
            {year: 2026.00, s: 0.5, a: 0.4, r: 0.4, f: 0.5},
            {year: 2026.02, s: 0.7, a: 0.2, r: 0.2, f: 0.8}
         ]
        }
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

    function focusCluster(index, barX, barY, barW, barH) {
        if (index < 0 || index >= clusters.length) return
        focusedClusterIndex = index
        selectedCluster = index
        heroStartX = barX - scrollX + 8
        heroStartY = barY + 8
        heroStartW = barW
        heroStartH = barH
        isFocused = true
        focusAnim.start()
    }

    function clearFocus() {
        isFocused = false
        unfocusAnim.start()
    }

    NumberAnimation {
        id: focusAnim
        target: root
        property: "animProgress"
        to: 1
        duration: 400
        easing.type: Easing.OutQuad
    }

    SequentialAnimation {
        id: unfocusAnim
        NumberAnimation { target: root; property: "animProgress"; to: 0; duration: 350; easing.type: Easing.OutQuad }
        ScriptAction { script: { focusedClusterIndex = -1; selectedCluster = -1 } }
    }

    Text {
        x: 12; y: 4
        text: "B3: Full Graph + Event Lines"
        font.pixelSize: 10
        font.bold: true
        color: "#808090"
    }

    // Pattern legend (overview)
    Row {
        x: 12; y: 18
        spacing: 10
        opacity: 1 - animProgress

        Repeater {
            model: [
                {pattern: "anxiety_cascade", label: "Anxiety"},
                {pattern: "triangle_activation", label: "Triangle"},
                {pattern: "conflict_resolution", label: "Conflict"}
            ]
            Row {
                spacing: 3
                Rectangle { width: 8; height: 8; radius: 4; color: patternColor(modelData.pattern); anchors.verticalCenter: parent.verticalCenter }
                Text { text: modelData.label; font.pixelSize: 8; color: "#606070" }
            }
        }
    }

    // SARF legend (focused)
    Row {
        x: 12; y: 18
        spacing: 8
        opacity: animProgress

        Repeater {
            model: [
                {color: sarfS, label: "S"},
                {color: sarfA, label: "A"},
                {color: sarfR, label: "R"},
                {color: sarfF, label: "F"}
            ]
            Row {
                spacing: 2
                Rectangle { width: 12; height: 3; radius: 1; color: modelData.color; anchors.verticalCenter: parent.verticalCenter }
                Text { text: modelData.label; font.pixelSize: 9; font.bold: true; color: modelData.color }
            }
        }
    }

    // Reset button
    Rectangle {
        anchors.right: parent.right
        anchors.rightMargin: 12
        y: 14
        width: 50; height: 20; radius: 10
        color: "#3a3a4a"
        opacity: animProgress
        visible: animProgress > 0.3

        Text {
            anchors.centerIn: parent
            text: "Reset"
            font.pixelSize: 9
            color: "#ffffff"
        }

        MouseArea {
            anchors.fill: parent
            onClicked: clearFocus()
        }
    }

    Rectangle {
        id: graphContainer
        x: 8; y: 40
        width: parent.width - 16
        height: graphHeight + 16
        radius: 8
        color: "#0f0f18"
        clip: true

        PinchArea {
            id: pinchArea
            anchors.fill: parent
            anchors.margins: 8
            enabled: animProgress < 0.1

            Item {
                x: -scrollX
                width: contentWidth
                height: graphHeight

                Repeater {
                    model: clusters

                    Rectangle {
                        id: barDelegate
                        property bool isHero: focusedClusterIndex === index

                        x: xPosForYear(modelData.startYear)
                        y: modelData.row * (barHeight + barSpacing) + 8
                        width: Math.max(20, xPosForYear(modelData.endYear) - xPosForYear(modelData.startYear))
                        height: barHeight
                        radius: 4
                        color: patternColor(modelData.pattern)
                        opacity: isHero ? 0 : (1 - animProgress) * 0.8
                        visible: opacity > 0

                        Text {
                            anchors.centerIn: parent
                            text: modelData.title
                            font.pixelSize: 9
                            font.bold: true
                            color: "white"
                            elide: Text.ElideRight
                            width: parent.width - 6
                            horizontalAlignment: Text.AlignHCenter
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: if (!isFocused) focusCluster(index, barDelegate.x, barDelegate.y, barDelegate.width, barDelegate.height)
                        }
                    }
                }
            }
        }

        // HERO - Full graph with events as vertical lines
        Rectangle {
            id: heroRect
            visible: focusedClusterIndex >= 0

            x: heroStartX + (8 - heroStartX) * animProgress
            y: heroStartY + (8 - heroStartY) * animProgress
            width: heroStartW + (graphContainer.width - 16 - heroStartW) * animProgress
            height: heroStartH + (graphHeight - heroStartH) * animProgress
            radius: 4 + 4 * animProgress
            color: "#08080f"
            border.color: focusedClusterIndex >= 0 ? patternColor(clusters[focusedClusterIndex].pattern) : "transparent"
            border.width: 2

            // Minimal title bar
            Rectangle {
                id: titleBar
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 20
                color: focusedClusterIndex >= 0 ? patternColor(clusters[focusedClusterIndex].pattern) : "#404050"
                radius: parent.radius

                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: parent.radius
                    color: parent.color
                }

                Text {
                    x: 6
                    anchors.verticalCenter: parent.verticalCenter
                    text: focusedClusterIndex >= 0 ? clusters[focusedClusterIndex].title : ""
                    font.pixelSize: 10
                    font.bold: true
                    color: "white"
                }
            }

            // Full SARF Graph with event lines
            Item {
                id: sarfGraph
                anchors.fill: parent
                anchors.topMargin: titleBar.height + 2
                anchors.margins: 4
                anchors.bottomMargin: 14
                opacity: Math.max(0, (animProgress - 0.25) / 0.75)
                visible: animProgress > 0.2
                clip: true

                property var cluster: focusedClusterIndex >= 0 ? clusters[focusedClusterIndex] : null
                property real clusterStart: cluster ? cluster.startYear : 0
                property real clusterEnd: cluster ? cluster.endYear : 1
                property real clusterSpan: clusterEnd - clusterStart

                function xForYear(year) { return ((year - clusterStart) / clusterSpan) * width }
                function yForValue(val) { return height * (1 - val * 0.9) - 2 }

                // Event vertical lines with labels
                Repeater {
                    model: sarfGraph.cluster ? sarfGraph.cluster.events : []

                    Item {
                        x: sarfGraph.xForYear(modelData.year)
                        y: 0
                        height: sarfGraph.height

                        // Vertical line
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 1
                            height: parent.height
                            color: "#ffffff20"
                        }

                        // Small tick at bottom
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            width: 5; height: 5; radius: 2.5
                            color: focusedClusterIndex >= 0 ? patternColor(clusters[focusedClusterIndex].pattern) : "white"
                            opacity: 0.8
                        }

                        // Label
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.top: parent.top
                            anchors.topMargin: 2
                            text: modelData.label
                            font.pixelSize: 6
                            color: "#606070"
                            rotation: -45
                            transformOrigin: Item.BottomLeft
                            visible: sarfGraph.width > 150
                        }
                    }
                }

                // SARF Canvas (on top of event lines)
                Canvas {
                    anchors.fill: parent

                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)

                        if (!sarfGraph.cluster || !sarfGraph.cluster.sarf) return

                        var data = sarfGraph.cluster.sarf
                        var colors = [
                            {line: sarfS.toString(), fill: Qt.rgba(0.2, 0.6, 0.85, 0.12).toString()},
                            {line: sarfA.toString(), fill: Qt.rgba(0.9, 0.3, 0.24, 0.12).toString()},
                            {line: sarfR.toString(), fill: Qt.rgba(0.61, 0.35, 0.71, 0.12).toString()},
                            {line: sarfF.toString(), fill: Qt.rgba(0.15, 0.68, 0.38, 0.12).toString()}
                        ]
                        var keys = ['s', 'a', 'r', 'f']

                        // Fills
                        for (var k = 3; k >= 0; k--) {
                            ctx.fillStyle = colors[k].fill
                            ctx.beginPath()
                            ctx.moveTo(sarfGraph.xForYear(data[0].year), height)
                            for (var i = 0; i < data.length; i++) {
                                ctx.lineTo(sarfGraph.xForYear(data[i].year), sarfGraph.yForValue(data[i][keys[k]]))
                            }
                            ctx.lineTo(sarfGraph.xForYear(data[data.length-1].year), height)
                            ctx.closePath()
                            ctx.fill()
                        }

                        // Lines
                        for (k = 0; k < 4; k++) {
                            ctx.strokeStyle = colors[k].line
                            ctx.lineWidth = 2
                            ctx.lineCap = "round"
                            ctx.beginPath()
                            for (i = 0; i < data.length; i++) {
                                var x = sarfGraph.xForYear(data[i].year)
                                var y = sarfGraph.yForValue(data[i][keys[k]])
                                if (i === 0) ctx.moveTo(x, y)
                                else ctx.lineTo(x, y)
                            }
                            ctx.stroke()
                        }
                    }

                    Connections {
                        target: root
                        function onAnimProgressChanged() { if (animProgress > 0.25) parent.requestPaint() }
                        function onFocusedClusterIndexChanged() { parent.requestPaint() }
                    }
                }

                // Y-axis hints
                Text { x: 2; y: 4; text: "Hi"; font.pixelSize: 6; color: "#404050" }
                Text { x: 2; y: sarfGraph.height - 10; text: "Lo"; font.pixelSize: 6; color: "#404050" }
            }

            // Time axis
            Row {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 4
                height: 10
                opacity: animProgress

                Text {
                    property var cluster: focusedClusterIndex >= 0 ? clusters[focusedClusterIndex] : null
                    text: cluster ? formatRange(cluster.startYear, cluster.endYear) : ""
                    font.pixelSize: 7
                    color: "#505060"

                    function formatRange(s, e) {
                        var m = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
                        return m[Math.floor((s-2025)*12)%12] + " → " + m[Math.floor((e-2025)*12)%12]
                    }
                }
            }
        }
    }

    // Year labels (overview)
    Row {
        x: 16; y: graphContainer.y + graphContainer.height + 6
        spacing: (parent.width - 80) / 4
        opacity: 1 - animProgress

        Repeater {
            model: ["May'25", "Jul", "Sep", "Nov", "Jan'26"]
            Text { text: modelData; font.pixelSize: 8; color: "#404050" }
        }
    }
}
