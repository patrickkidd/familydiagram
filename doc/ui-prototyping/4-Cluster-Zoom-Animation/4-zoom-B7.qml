// Variant B7: Event bands behind SARF lines
// - Events shown as subtle vertical bands in background
// - Same-day events share a band (wider)
// - Labels appear on hover/tap
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
    property int hoveredEventIndex: -1

    property real zoomLevel: 1.0
    property real scrollX: 0
    property real minZoom: 1.0
    property real maxZoom: 5.0

    property real focusedZoom: 1.0
    property real focusedScrollX: 0

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

    // Group events by day
    function groupEventsByDay(data) {
        var groups = []
        var currentGroup = null

        for (var i = 0; i < data.length; i++) {
            var item = data[i]
            if (currentGroup && Math.abs(item.year - currentGroup.year) < 0.001) {
                currentGroup.events.push(item)
            } else {
                if (currentGroup) groups.push(currentGroup)
                currentGroup = { year: item.year, events: [item] }
            }
        }
        if (currentGroup) groups.push(currentGroup)
        return groups
    }

    property var clusters: [
        {title: "Race Committee", pattern: "conflict_resolution", startYear: 2025.37, endYear: 2025.42, row: 0,
         data: [
            {year: 2025.37, label: "Conflict starts", s: 0.6, a: 0.3, r: 0.4, f: 0.7},
            {year: 2025.38, label: "Escalation", s: 0.5, a: 0.6, r: 0.7, f: 0.5},
            {year: 2025.38, label: "Sleepless night", s: 0.4, a: 0.7, r: 0.7, f: 0.45},
            {year: 2025.39, label: "Discussion", s: 0.4, a: 0.7, r: 0.8, f: 0.4},
            {year: 2025.40, label: "Resolution attempt", s: 0.5, a: 0.5, r: 0.6, f: 0.5},
            {year: 2025.41, label: "Agreement", s: 0.6, a: 0.3, r: 0.4, f: 0.6},
            {year: 2025.42, label: "Closure", s: 0.7, a: 0.2, r: 0.3, f: 0.8}
         ]
        },
        {title: "Work Stress", pattern: "anxiety_cascade", startYear: 2025.41, endYear: 2025.48, row: 2,
         data: [
            {year: 2025.41, label: "Deadline pressure", s: 0.7, a: 0.3, r: 0.3, f: 0.7},
            {year: 2025.41, label: "Boss criticism", s: 0.65, a: 0.45, r: 0.4, f: 0.6},
            {year: 2025.43, label: "Workload increase", s: 0.5, a: 0.5, r: 0.5, f: 0.5},
            {year: 2025.45, label: "Sleep issues", s: 0.3, a: 0.7, r: 0.7, f: 0.3},
            {year: 2025.45, label: "Headaches start", s: 0.25, a: 0.75, r: 0.7, f: 0.28},
            {year: 2025.47, label: "Burnout signs", s: 0.2, a: 0.9, r: 0.8, f: 0.2},
            {year: 2025.48, label: "Time off", s: 0.4, a: 0.6, r: 0.5, f: 0.4}
         ]
        },
        {title: "Family Triangle", pattern: "triangle_activation", startYear: 2025.48, endYear: 2025.53, row: 0,
         data: [
            {year: 2025.48, label: "Tension", s: 0.6, a: 0.4, r: 0.5, f: 0.6},
            {year: 2025.49, label: "Side-taking", s: 0.4, a: 0.6, r: 0.7, f: 0.4},
            {year: 2025.50, label: "Peak conflict", s: 0.3, a: 0.8, r: 0.9, f: 0.3},
            {year: 2025.51, label: "Mediation", s: 0.4, a: 0.6, r: 0.7, f: 0.4},
            {year: 2025.52, label: "Resolution", s: 0.5, a: 0.4, r: 0.5, f: 0.5},
            {year: 2025.53, label: "Equilibrium", s: 0.6, a: 0.3, r: 0.4, f: 0.6}
         ]
        },
        {title: "Holiday Tension", pattern: "conflict_resolution", startYear: 2025.94, endYear: 2026.02, row: 0,
         data: [
            {year: 2025.94, label: "Planning stress", s: 0.7, a: 0.2, r: 0.3, f: 0.7},
            {year: 2025.96, label: "Family arrives", s: 0.5, a: 0.5, r: 0.5, f: 0.5},
            {year: 2025.97, label: "Tension builds", s: 0.3, a: 0.7, r: 0.8, f: 0.3},
            {year: 2025.97, label: "Old conflict resurfaces", s: 0.28, a: 0.75, r: 0.85, f: 0.28},
            {year: 2025.98, label: "Major argument", s: 0.2, a: 0.9, r: 0.9, f: 0.2},
            {year: 2026.00, label: "Apologies", s: 0.5, a: 0.4, r: 0.4, f: 0.5},
            {year: 2026.02, label: "Departure", s: 0.7, a: 0.2, r: 0.2, f: 0.8}
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
        focusedZoom = 1.0
        focusedScrollX = 0
        hoveredEventIndex = -1
        focusAnim.start()
    }

    function clearFocus() {
        isFocused = false
        hoveredEventIndex = -1
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
        ScriptAction { script: { focusedClusterIndex = -1; selectedCluster = -1; focusedZoom = 1.0; focusedScrollX = 0 } }
    }

    Text {
        x: 12; y: 4
        text: "B7: Event Bands + Tap Labels"
        font.pixelSize: 10
        font.bold: true
        color: "#808090"
    }

    // Pattern legend
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

    // SARF legend
    Row {
        x: 12; y: 18
        spacing: 10
        opacity: animProgress

        Repeater {
            model: [
                {color: sarfS, label: "Self"},
                {color: sarfA, label: "Anxiety"},
                {color: sarfR, label: "Reactivity"},
                {color: sarfF, label: "Function"}
            ]
            Row {
                spacing: 3
                Rectangle { width: 10; height: 3; radius: 1; color: modelData.color; anchors.verticalCenter: parent.verticalCenter }
                Text { text: modelData.label; font.pixelSize: 8; color: "#808090" }
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
            id: overviewPinch
            anchors.fill: parent
            anchors.margins: 8
            enabled: animProgress < 0.1

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
                var pinchXRatio = (startCenter.x + startScrollX) / (baseContentWidth * startZoom)
                var newScrollX = pinchXRatio * baseContentWidth * newZoom - startCenter.x
                var maxScroll = Math.max(0, baseContentWidth * newZoom - viewportWidth)
                scrollX = Math.max(0, Math.min(newScrollX, maxScroll))
                zoomLevel = newZoom
            }

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.NoButton
                onWheel: {
                    if (animProgress > 0.1) return
                    var deltaX = wheel.angleDelta.x !== 0 ? wheel.angleDelta.x : wheel.angleDelta.y
                    var maxScroll = Math.max(0, contentWidth - viewportWidth)
                    scrollX = Math.max(0, Math.min(scrollX - deltaX * 0.5, maxScroll))
                    wheel.accepted = true
                }
            }

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

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 2
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.6; height: 3; radius: 1.5
            color: "#1a1a2a"
            visible: animProgress < 0.5 && zoomLevel > 1.05

            Rectangle {
                x: parent.width * (scrollX / contentWidth)
                width: Math.max(16, parent.width / zoomLevel)
                height: parent.height; radius: parent.radius
                color: "#505060"
            }
        }

        // HERO
        Rectangle {
            id: heroRect
            visible: focusedClusterIndex >= 0

            x: heroStartX + (8 - heroStartX) * animProgress
            y: heroStartY + (8 - heroStartY) * animProgress
            width: heroStartW + (graphContainer.width - 16 - heroStartW) * animProgress
            height: heroStartH + (graphHeight - heroStartH) * animProgress
            radius: 4 + 4 * animProgress
            color: "#0a0a12"
            border.color: focusedClusterIndex >= 0 ? patternColor(clusters[focusedClusterIndex].pattern) : "transparent"
            border.width: 2
            clip: true

            property var cluster: focusedClusterIndex >= 0 ? clusters[focusedClusterIndex] : null
            property var eventGroups: cluster ? groupEventsByDay(cluster.data) : []
            property real clusterStart: cluster ? cluster.startYear : 0
            property real clusterEnd: cluster ? cluster.endYear : 1
            property real clusterSpan: Math.max(0.01, clusterEnd - clusterStart)
            property real focusedContentWidth: (width - 12) * focusedZoom

            Rectangle {
                id: titleBar
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 22
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

                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    text: heroRect.cluster ? heroRect.cluster.data.length + " events" : ""
                    font.pixelSize: 8
                    color: "#ffffffaa"
                    opacity: animProgress
                }
            }

            PinchArea {
                id: focusedPinch
                anchors.fill: parent
                anchors.topMargin: titleBar.height
                anchors.margins: 6
                enabled: animProgress > 0.9

                property real startZoom: 1.0
                property real startScrollX: 0
                property point startCenter: Qt.point(0, 0)

                onPinchStarted: {
                    startZoom = focusedZoom
                    startScrollX = focusedScrollX
                    startCenter = pinch.center
                }

                onPinchUpdated: {
                    var newZoom = Math.max(minZoom, Math.min(maxZoom, startZoom * pinch.scale))
                    var baseW = heroRect.width - 12
                    var pinchXRatio = (startCenter.x + startScrollX) / (baseW * startZoom)
                    var newScrollX = pinchXRatio * baseW * newZoom - startCenter.x
                    var maxScroll = Math.max(0, baseW * newZoom - baseW)
                    focusedScrollX = Math.max(0, Math.min(newScrollX, maxScroll))
                    focusedZoom = newZoom
                }

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.NoButton
                    onWheel: {
                        if (animProgress < 0.9) return
                        var deltaX = wheel.angleDelta.x !== 0 ? wheel.angleDelta.x : wheel.angleDelta.y
                        var baseW = heroRect.width - 12
                        var maxScroll = Math.max(0, baseW * focusedZoom - baseW)
                        focusedScrollX = Math.max(0, Math.min(focusedScrollX - deltaX * 0.5, maxScroll))
                        wheel.accepted = true
                    }
                }

                Item {
                    id: sarfGraph
                    anchors.fill: parent
                    opacity: Math.max(0, (animProgress - 0.25) / 0.75)
                    visible: animProgress > 0.2

                    function xForYear(year) {
                        var baseW = width
                        return ((year - heroRect.clusterStart) / heroRect.clusterSpan) * baseW * focusedZoom - focusedScrollX
                    }
                    function yForValue(val) { return height * (1 - val * 0.85) - 4 }

                    // Event bands in background
                    Repeater {
                        model: heroRect.eventGroups

                        Rectangle {
                            property var group: modelData
                            property int groupIndex: index
                            property bool isHovered: hoveredEventIndex === groupIndex

                            x: sarfGraph.xForYear(group.year) - (8 + group.events.length * 4)
                            y: 0
                            width: 16 + group.events.length * 8
                            height: sarfGraph.height
                            color: focusedClusterIndex >= 0 ? patternColor(clusters[focusedClusterIndex].pattern) : "#ffffff"
                            opacity: isHovered ? 0.25 : 0.08
                            radius: 4

                            Behavior on opacity { NumberAnimation { duration: 150 } }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                onEntered: hoveredEventIndex = groupIndex
                                onExited: hoveredEventIndex = -1
                                onClicked: hoveredEventIndex = (hoveredEventIndex === groupIndex) ? -1 : groupIndex
                            }

                            // Tooltip showing event labels
                            Rectangle {
                                visible: isHovered
                                anchors.horizontalCenter: parent.horizontalCenter
                                y: 4
                                width: labelCol.width + 8
                                height: labelCol.height + 6
                                radius: 4
                                color: "#2a2a3a"
                                border.color: focusedClusterIndex >= 0 ? patternColor(clusters[focusedClusterIndex].pattern) : "#404050"
                                border.width: 1
                                z: 100

                                Column {
                                    id: labelCol
                                    anchors.centerIn: parent
                                    spacing: 2

                                    Repeater {
                                        model: group.events
                                        Text {
                                            text: modelData.label
                                            font.pixelSize: 7
                                            color: "#c0c0d0"
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // SARF lines on top
                    Canvas {
                        anchors.fill: parent

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)

                            if (!heroRect.cluster || !heroRect.cluster.data) return

                            var data = heroRect.cluster.data
                            var colors = [sarfS.toString(), sarfA.toString(), sarfR.toString(), sarfF.toString()]
                            var keys = ['s', 'a', 'r', 'f']

                            for (var k = 0; k < 4; k++) {
                                ctx.strokeStyle = colors[k]
                                ctx.lineWidth = 2.5
                                ctx.lineCap = "round"
                                ctx.lineJoin = "round"
                                ctx.beginPath()

                                for (var i = 0; i < data.length; i++) {
                                    var x = sarfGraph.xForYear(data[i].year)
                                    var y = sarfGraph.yForValue(data[i][keys[k]])

                                    if (i === 0) {
                                        ctx.moveTo(x, y)
                                    } else {
                                        ctx.lineTo(x, y)
                                    }
                                }
                                ctx.stroke()

                                // Dots
                                ctx.fillStyle = colors[k]
                                for (i = 0; i < data.length; i++) {
                                    x = sarfGraph.xForYear(data[i].year)
                                    y = sarfGraph.yForValue(data[i][keys[k]])
                                    ctx.beginPath()
                                    ctx.arc(x, y, 3, 0, Math.PI * 2)
                                    ctx.fill()
                                }
                            }
                        }

                        Connections {
                            target: root
                            function onAnimProgressChanged() { if (animProgress > 0.25) parent.requestPaint() }
                            function onFocusedClusterIndexChanged() { parent.requestPaint() }
                            function onFocusedZoomChanged() { parent.requestPaint() }
                            function onFocusedScrollXChanged() { parent.requestPaint() }
                        }
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 2
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width * 0.5; height: 3; radius: 1.5
                color: "#1a1a2a"
                visible: animProgress > 0.9 && focusedZoom > 1.05

                Rectangle {
                    x: parent.width * (focusedScrollX / heroRect.focusedContentWidth)
                    width: Math.max(12, parent.width / focusedZoom)
                    height: parent.height; radius: parent.radius
                    color: "#505060"
                }
            }
        }
    }

    Row {
        x: 16; y: graphContainer.y + graphContainer.height + 6
        spacing: (parent.width - 80) / 4
        opacity: 1 - animProgress

        Repeater {
            model: ["May'25", "Jul", "Sep", "Nov", "Jan'26"]
            Text { text: modelData; font.pixelSize: 8; color: "#404050" }
        }
    }

    Text {
        x: 16; y: graphContainer.y + graphContainer.height + 6
        opacity: animProgress
        visible: focusedClusterIndex >= 0
        text: formatClusterRange()
        font.pixelSize: 8
        color: "#606070"

        function formatClusterRange() {
            if (focusedClusterIndex < 0) return ""
            var c = clusters[focusedClusterIndex]
            var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            var sm = Math.floor((c.startYear - 2025) * 12)
            var em = Math.floor((c.endYear - 2025) * 12)
            var sy = c.startYear < 2026 ? "'25" : "'26"
            var ey = c.endYear < 2026 ? "'25" : "'26"
            return months[((sm % 12) + 12) % 12] + sy + " – " + months[((em % 12) + 12) % 12] + ey
        }
    }

    // Hint text
    Text {
        anchors.right: parent.right
        anchors.rightMargin: 16
        y: graphContainer.y + graphContainer.height + 6
        opacity: animProgress * 0.6
        text: "tap bands for details"
        font.pixelSize: 7
        font.italic: true
        color: "#505060"
        visible: focusedZoom < 1.1
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: 16
        y: graphContainer.y + graphContainer.height + 6
        opacity: animProgress * (focusedZoom > 1.05 ? 1 : 0)
        text: focusedZoom.toFixed(1) + "x"
        font.pixelSize: 8
        color: "#505060"
    }
}
