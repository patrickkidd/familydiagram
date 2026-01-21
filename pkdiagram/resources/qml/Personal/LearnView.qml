import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK


Page {
    id: root
    objectName: "learnView"

    signal addEventRequested
    signal editEventRequested(int eventId)
    signal deleteEventRequested(int eventId)

    property int selectedEvent: -1
    property int swipedEvent: -1
    property int highlightedEvent: -1
    property int pendingSelection: -1
    property var collapsedClusters: ({})  // clusterId -> true if collapsed
    property int focusedClusterIndex: -1  // Index of cluster being focused in graph
    property bool showClusters: true  // Toggle between cluster view and raw data view

    // WCAG AA colors for SARF
    readonly property color symptomColor: "#e05555"
    readonly property color anxietyColor: "#40a060"
    readonly property color relationshipColor: "#5080d0"
    readonly property color functioningColor: util.IS_UI_DARK_MODE ? "#909090" : "#505060"

    // Theme colors from util
    readonly property color bgColor: util.QML_WINDOW_BG
    readonly property color cardColor: util.IS_UI_DARK_MODE ? "#1a1a28" : "#ffffff"
    readonly property color textPrimary: util.QML_TEXT_COLOR
    readonly property color textSecondary: util.IS_UI_DARK_MODE ? "#909098" : "#606070"
    readonly property color dividerColor: util.IS_UI_DARK_MODE ? "#2a2a38" : "#e0e0e8"
    readonly property color highlightColor: util.IS_UI_DARK_MODE ? "#2a2a40" : "#f0f0ff"

    // Graph properties
    property real graphPadding: 0
    property real miniGraphY: 20
    property real miniGraphH: 145
    property real gLeft: 0
    property real gRight: width
    property real gWidth: gRight - gLeft

    // Timeline zoom/pan properties (overview mode)
    property real timelineZoom: 1.0
    property real timelineScrollX: 0
    property real minZoom: 1.0
    property real maxZoom: 5.0

    // Focused view zoom/pan properties
    property real focusedZoom: 1.0
    property real focusedScrollX: 0
    property int hoveredEventGroup: -1

    // B8-style animation properties
    property real animProgress: 0
    property real heroStartX: 0
    property real heroStartY: 0
    property real heroStartW: 0
    property real heroStartH: 0

    // Focused cluster state for graph zooming
    property var focusedCluster: focusedClusterIndex >= 0 && clusterModel && clusterModel.clusters.length > focusedClusterIndex ? clusterModel.clusters[focusedClusterIndex] : null
    property bool isFocused: focusedClusterIndex >= 0
    // Compute actual min/max yearFrac from events in focused cluster
    property var focusedEventYearFracs: {
        if (!isFocused || !focusedCluster || !focusedCluster.eventIds || !sarfGraphModel) return []
        var events = sarfGraphModel.events
        var fracs = []
        for (var i = 0; i < focusedCluster.eventIds.length; i++) {
            var eventId = focusedCluster.eventIds[i]
            for (var j = 0; j < events.length; j++) {
                if (events[j].id === eventId) {
                    fracs.push(events[j].yearFrac)
                    break
                }
            }
        }
        return fracs
    }
    property real focusedMinYearFrac: {
        var fracs = focusedEventYearFracs
        if (!fracs || fracs.length === 0) return 2025
        var minVal = fracs[0]
        for (var i = 1; i < fracs.length; i++) {
            if (fracs[i] < minVal) minVal = fracs[i]
        }
        return minVal
    }
    property real focusedMaxYearFrac: {
        var fracs = focusedEventYearFracs
        if (!fracs || fracs.length === 0) return 2025
        var maxVal = fracs[0]
        for (var i = 1; i < fracs.length; i++) {
            if (fracs[i] > maxVal) maxVal = fracs[i]
        }
        return maxVal
    }
    property real focusedYearSpan: Math.max(0.001, focusedMaxYearFrac - focusedMinYearFrac)

    // Year range for all cluster events (excludes birth events and other outliers)
    property var clusterEventYearFracs: {
        if (!showClusters || !clusterModel || !clusterModel.hasClusters || !sarfGraphModel) return []
        var events = sarfGraphModel.events
        var fracs = []
        for (var i = 0; i < clusterModel.clusters.length; i++) {
            var cluster = clusterModel.clusters[i]
            if (!cluster.eventIds) continue
            for (var j = 0; j < cluster.eventIds.length; j++) {
                var eventId = cluster.eventIds[j]
                for (var k = 0; k < events.length; k++) {
                    if (events[k].id === eventId) {
                        fracs.push(events[k].yearFrac)
                        break
                    }
                }
            }
        }
        return fracs
    }
    property real clusterMinYearFrac: {
        var fracs = clusterEventYearFracs
        if (!fracs || fracs.length === 0) return sarfGraphModel ? sarfGraphModel.yearStart : 2020
        var minVal = fracs[0]
        for (var i = 1; i < fracs.length; i++) {
            if (fracs[i] < minVal) minVal = fracs[i]
        }
        return minVal
    }
    property real clusterMaxYearFrac: {
        var fracs = clusterEventYearFracs
        if (!fracs || fracs.length === 0) return sarfGraphModel ? sarfGraphModel.yearEnd : 2025
        var maxVal = fracs[0]
        for (var i = 1; i < fracs.length; i++) {
            if (fracs[i] > maxVal) maxVal = fracs[i]
        }
        return maxVal
    }
    property real clusterYearSpan: Math.max(1, clusterMaxYearFrac - clusterMinYearFrac)

    background: Rectangle {
        color: bgColor
    }

    Component.onCompleted: collapseAllClusters()

    // B8-style focus animations
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
        ScriptAction { script: { focusedClusterIndex = -1; focusedZoom = 1.0; focusedScrollX = 0; hoveredEventGroup = -1; if (clusterModel) clusterModel.selectCluster("") } }
    }

    function xPos(year) {
        if (!sarfGraphModel) return gLeft
        var yearStart, yearSpan
        if (isFocused) {
            yearStart = focusedMinYearFrac
            yearSpan = focusedYearSpan
        } else if (showClusters && clusterModel && clusterModel.hasClusters) {
            yearStart = clusterMinYearFrac
            yearSpan = clusterYearSpan
        } else {
            yearStart = sarfGraphModel.yearStart
            yearSpan = sarfGraphModel.yearSpan
        }
        if (yearSpan === 0) yearSpan = 60
        return gLeft + ((year - yearStart) / yearSpan) * gWidth
    }

    function xPosZoomed(year) {
        if (!showClusters || isFocused) return xPos(year)
        var yearStart = clusterMinYearFrac
        var yearSpan = clusterYearSpan
        if (yearSpan === 0) yearSpan = 1
        var baseX = ((year - yearStart) / yearSpan) * gWidth
        return gLeft + baseX * timelineZoom - timelineScrollX
    }

    function groupEventsByDay(eventIds) {
        if (!eventIds || !sarfGraphModel) return []
        var events = sarfGraphModel.events
        var groups = []
        var currentGroup = null

        for (var i = 0; i < eventIds.length; i++) {
            var eventId = eventIds[i]
            var evt = null
            for (var j = 0; j < events.length; j++) {
                if (events[j].id === eventId) {
                    evt = events[j]
                    break
                }
            }
            if (!evt) continue

            var yearFrac = evt.yearFrac
            if (currentGroup && Math.abs(yearFrac - currentGroup.yearFrac) < 0.003) {
                currentGroup.events.push(evt)
            } else {
                if (currentGroup) groups.push(currentGroup)
                currentGroup = { yearFrac: yearFrac, events: [evt] }
            }
        }
        if (currentGroup) groups.push(currentGroup)
        return groups
    }

    function focusCluster(idx, barX, barY, barW, barH) {
        if (!clusterModel || !clusterModel.clusters || idx < 0 || idx >= clusterModel.clusters.length) {
            focusedClusterIndex = -1
            return
        }
        // Capture hero start position from the clicked bar
        heroStartX = barX !== undefined ? barX : 0
        heroStartY = barY !== undefined ? barY : 0
        heroStartW = barW !== undefined ? barW : gWidth
        heroStartH = barH !== undefined ? barH : 28
        // Reset zoom
        timelineZoom = 1.0
        timelineScrollX = 0
        focusedZoom = 1.0
        focusedScrollX = 0
        hoveredEventGroup = -1
        // Collapse ALL clusters first (ensures consistent heights for scroll calculation)
        var newCollapsed = {}
        for (var c = 0; c < clusterModel.clusters.length; c++) {
            newCollapsed[clusterModel.clusters[c].id] = true
        }
        collapsedClusters = newCollapsed

        focusedClusterIndex = idx
        var cluster = clusterModel.clusters[idx]
        if (cluster && cluster.id) {
            clusterModel.selectCluster(cluster.id)
            // Find first event index, scroll to it, then expand after
            if (cluster.eventIds && cluster.eventIds.length > 0 && sarfGraphModel) {
                var events = sarfGraphModel.events
                for (var i = 0; i < events.length; i++) {
                    if (events[i].id === cluster.eventIds[0]) {
                        pendingClusterScroll = i
                        pendingClusterExpand = cluster.id
                        clusterScrollTimer.restart()
                        break
                    }
                }
            }
        }
        // Start animation
        focusAnim.start()
    }

    property int pendingClusterScroll: -1
    property string pendingClusterExpand: ""

    function scrollToClusterIndex(eventIndex) {
        // Find which cluster index this event belongs to
        var targetClusterIdx = -1
        for (var i = 0; i < clusterModel.clusters.length; i++) {
            var cluster = clusterModel.clusters[i]
            if (cluster.eventIds) {
                for (var j = 0; j < cluster.eventIds.length; j++) {
                    if (sarfGraphModel.events[eventIndex].id === cluster.eventIds[j]) {
                        targetClusterIdx = i
                        break
                    }
                }
            }
            if (targetClusterIdx >= 0) break
        }

        console.log("scrollToClusterIndex: eventIndex=" + eventIndex + ", targetClusterIdx=" + targetClusterIdx)

        if (targetClusterIdx < 0) return storyList.contentY

        // When all clusters are collapsed, each shows only its header (92px)
        var collapsedHeaderHeight = 92
        var targetY = targetClusterIdx * collapsedHeaderHeight - 20

        // Use actual contentHeight (more reliable after layout settles)
        var minY = 0
        var maxY = Math.max(0, storyList.contentHeight - storyList.height)
        var clampedY = Math.max(minY, Math.min(targetY, maxY))

        console.log("  targetClusterIdx=" + targetClusterIdx + ", collapsedHeaderHeight=" + collapsedHeaderHeight)
        console.log("  targetY=" + targetY + " (clusterIdx * 92 - 20)")
        console.log("  storyList.contentHeight=" + storyList.contentHeight + ", storyList.height=" + storyList.height)
        console.log("  maxY=" + maxY + ", clampedY=" + clampedY)
        console.log("  storyList.contentY (before)=" + storyList.contentY)

        return clampedY
    }

    Timer {
        id: clusterScrollTimer
        interval: 150  // Allow layout to settle after collapsing clusters
        onTriggered: {
            if (pendingClusterScroll >= 0) {
                storyList.forceLayout()
                console.log("clusterScrollTimer triggered, pendingClusterScroll=" + pendingClusterScroll)
                var targetY = scrollToClusterIndex(pendingClusterScroll)
                console.log("  scrollAnimation.to = " + targetY + ", starting animation...")
                scrollAnimation.to = targetY
                scrollAnimation.start()
                pendingClusterScroll = -1
            }
        }
    }

    property int pendingScrollAdjustIndex: -1

    Connections {
        target: scrollAnimation
        function onStopped() {
            console.log("scrollAnimation stopped, contentY=" + storyList.contentY + ", pendingClusterExpand=" + pendingClusterExpand)
            // Expand cluster after scroll animation completes
            if (pendingClusterExpand !== "") {
                // Find the event index for this cluster to use in scroll adjustment
                for (var i = 0; i < clusterModel.clusters.length; i++) {
                    if (clusterModel.clusters[i].id === pendingClusterExpand) {
                        var cluster = clusterModel.clusters[i]
                        if (cluster.eventIds && cluster.eventIds.length > 0) {
                            for (var j = 0; j < sarfGraphModel.events.length; j++) {
                                if (sarfGraphModel.events[j].id === cluster.eventIds[0]) {
                                    pendingScrollAdjustIndex = j
                                    break
                                }
                            }
                        }
                        break
                    }
                }

                if (collapsedClusters[pendingClusterExpand]) {
                    var newCollapsed = {}
                    for (var key in collapsedClusters) {
                        if (key !== pendingClusterExpand) {
                            newCollapsed[key] = collapsedClusters[key]
                        }
                    }
                    collapsedClusters = newCollapsed
                }
                console.log("  Expanded cluster: " + pendingClusterExpand)
                pendingClusterExpand = ""
                // Trigger scroll adjustment after expansion
                clusterScrollAdjustTimer.restart()
            }
        }
    }

    Timer {
        id: clusterScrollAdjustTimer
        interval: 100
        onTriggered: {
            if (pendingScrollAdjustIndex >= 0) {
                storyList.forceLayout()
                // Now that cluster is expanded, recalculate and scroll to correct position
                var targetY = pendingScrollAdjustIndex > 0 ? scrollToClusterIndex(pendingScrollAdjustIndex) : 0
                console.log("clusterScrollAdjustTimer: adjusting to targetY=" + targetY + ", current contentY=" + storyList.contentY)
                if (Math.abs(targetY - storyList.contentY) > 10) {
                    clusterScrollAdjustAnimation.to = targetY
                    clusterScrollAdjustAnimation.start()
                }
                pendingScrollAdjustIndex = -1
            }
        }
    }

    NumberAnimation {
        id: clusterScrollAdjustAnimation
        target: storyList
        property: "contentY"
        duration: 300
        easing.type: Easing.OutQuad
    }

    function focusNextCluster() {
        if (!clusterModel || !clusterModel.clusters || clusterModel.clusters.length === 0) return
        var nextIdx = focusedClusterIndex + 1
        if (nextIdx >= clusterModel.clusters.length) nextIdx = 0
        // For next/prev, animate from current hero position
        focusCluster(nextIdx, 0, 0, gWidth, miniGraphH)
    }

    function focusPrevCluster() {
        if (!clusterModel || !clusterModel.clusters || clusterModel.clusters.length === 0) return
        var prevIdx = focusedClusterIndex - 1
        if (prevIdx < 0) prevIdx = clusterModel.clusters.length - 1
        focusCluster(prevIdx, 0, 0, gWidth, miniGraphH)
    }

    function clearFocus() {
        hoveredEventGroup = -1
        // Collapse all clusters without changing scroll position
        if (clusterModel && clusterModel.clusters) {
            var newCollapsed = {}
            for (var i = 0; i < clusterModel.clusters.length; i++) {
                newCollapsed[clusterModel.clusters[i].id] = true
            }
            collapsedClusters = newCollapsed
        }
        unfocusAnim.start()
    }

    function yPosMini(val) {
        return miniGraphY + miniGraphH - ((val + 2) / 6) * miniGraphH
    }

    function primaryColorForEvent(evt) {
        if (evt.relationship) return relationshipColor
        if (evt.symptom) return symptomColor
        if (evt.anxiety) return anxietyColor
        if (evt.functioning) return functioningColor
        return textPrimary
    }

    function isLifeEvent(kind) {
        if (!sarfGraphModel) return false
        return sarfGraphModel.isLifeEvent(kind)
    }

    function clusterForEventIndex(idx) {
        if (!clusterModel || !clusterModel.hasClusters) return null
        if (!sarfGraphModel) return null
        var events = sarfGraphModel.events
        if (idx < 0 || idx >= events.length) return null
        var eventId = events[idx].id
        var clusterId = clusterModel.clusterForEvent(eventId)
        if (!clusterId) return null
        return clusterModel.clusterById(clusterId)
    }

    function isEventInAnyCluster(idx) {
        return clusterForEventIndex(idx) !== null
    }

    function isFirstEventInCluster(idx) {
        var cluster = clusterForEventIndex(idx)
        if (!cluster || !cluster.eventIds || cluster.eventIds.length === 0) return false
        var events = sarfGraphModel.events
        if (idx < 0 || idx >= events.length) return false
        return cluster.eventIds[0] === events[idx].id
    }

    function isEventClusterCollapsed(idx) {
        var cluster = clusterForEventIndex(idx)
        if (!cluster) return false
        return collapsedClusters[cluster.id] === true
    }

    function toggleClusterCollapsed(clusterId) {
        var newCollapsed = {}
        for (var key in collapsedClusters) {
            newCollapsed[key] = collapsedClusters[key]
        }
        newCollapsed[clusterId] = !newCollapsed[clusterId]
        collapsedClusters = newCollapsed
    }

    function collapseAllClusters() {
        focusedClusterIndex = -1
        if (clusterModel && clusterModel.clusters) {
            var newCollapsed = {}
            for (var i = 0; i < clusterModel.clusters.length; i++) {
                newCollapsed[clusterModel.clusters[i].id] = true
            }
            collapsedClusters = newCollapsed
        }
    }

    function patternLabel(pattern) {
        if (!pattern) return ""
        switch (pattern) {
            case "anxiety_cascade": return "Anxiety Cascade"
            case "triangle_activation": return "Triangle Activation"
            case "conflict_resolution": return "Conflict Resolution"
            case "reciprocal_disturbance": return "Reciprocal Disturbance"
            case "functioning_gain": return "Functioning Gain"
            case "work_family_spillover": return "Work-Family Spillover"
            default: return pattern
        }
    }

    function patternColor(pattern) {
        if (!pattern) return textSecondary
        switch (pattern) {
            case "anxiety_cascade": return "#e74c3c"
            case "triangle_activation": return "#9b59b6"
            case "conflict_resolution": return "#27ae60"
            case "reciprocal_disturbance": return "#e67e22"
            case "functioning_gain": return "#3498db"
            case "work_family_spillover": return "#f39c12"
            default: return textSecondary
        }
    }

    function dominantVariableColor(variable) {
        switch (variable) {
            case "S": return symptomColor
            case "A": return anxietyColor
            case "R": return relationshipColor
            case "F": return functioningColor
            default: return textSecondary
        }
    }

    function dateToYear(dateStr) {
        if (!dateStr) return null
        var parts = dateStr.split("-")
        if (parts.length >= 1) {
            var year = parseInt(parts[0])
            if (!isNaN(year)) return year
        }
        return null
    }

    function dateToYearFrac(dateStr) {
        if (!dateStr) return null
        var parts = dateStr.split("-")
        if (parts.length < 3) return dateToYear(dateStr)
        var year = parseInt(parts[0])
        var month = parseInt(parts[1])
        var day = parseInt(parts[2])
        if (isNaN(year) || isNaN(month) || isNaN(day)) return dateToYear(dateStr)
        // Approximate fractional year: (month-1)*30 + day gives rough day of year
        var dayOfYear = (month - 1) * 30.4 + day
        var daysInYear = 365
        return year + (dayOfYear / daysInYear)
    }

    function ensureItemVisible(idx) {
        storyList.positionViewAtIndex(idx, ListView.Contain)
    }

    function scrollToEventThenExpand(idx) {
        if (!sarfGraphModel) return
        var events = sarfGraphModel.events
        if (idx < 0 || idx >= events.length) return
        selectedEvent = -1
        highlightedEvent = idx
        pendingSelection = idx
        storyList.positionViewAtIndex(idx, ListView.Beginning)
        expandTimer.restart()
    }

    Timer {
        id: expandTimer
        interval: 550
        onTriggered: {
            if (pendingSelection >= 0) {
                selectedEvent = pendingSelection
                pendingSelection = -1
                scrollAdjustTimer.restart()
            }
        }
    }

    Timer {
        id: scrollAdjustTimer
        interval: 300
        onTriggered: {
            if (selectedEvent >= 0) {
                ensureItemVisible(selectedEvent)
            }
        }
    }

    // SARF Symbol Components

    component SymptomSymbol: Item {
        property real size: 24
        property color symbolColor: symptomColor
        width: size; height: size
        Rectangle {
            anchors.centerIn: parent
            width: parent.size * 0.7; height: parent.size * 0.25
            radius: 1; color: parent.symbolColor
        }
        Rectangle {
            anchors.centerIn: parent
            width: parent.size * 0.25; height: parent.size * 0.7
            radius: 1; color: parent.symbolColor
        }
    }

    component AnxietySymbol: Canvas {
        property real size: 24
        property color symbolColor: anxietyColor
        width: size; height: size
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.fillStyle = symbolColor
            var s = size / 32
            ctx.beginPath()
            ctx.moveTo(18*s, 2*s)
            ctx.lineTo(8*s, 15*s)
            ctx.lineTo(14*s, 15*s)
            ctx.lineTo(10*s, 30*s)
            ctx.lineTo(24*s, 13*s)
            ctx.lineTo(17*s, 13*s)
            ctx.lineTo(18*s, 2*s)
            ctx.fill()
        }
        onSymbolColorChanged: requestPaint()
    }

    component RelationshipSymbol: Item {
        property real size: 24
        property color symbolColor: relationshipColor
        width: size; height: size
        Rectangle {
            x: size * 0.1; y: size * 0.3
            width: size * 0.45; height: size * 0.4; radius: size * 0.2
            color: "transparent"
            border.color: parent.symbolColor; border.width: size * 0.12
        }
        Rectangle {
            x: size * 0.45; y: size * 0.3
            width: size * 0.45; height: size * 0.4; radius: size * 0.2
            color: "transparent"
            border.color: parent.symbolColor; border.width: size * 0.12
        }
    }

    component FunctioningSymbol: Canvas {
        property real size: 24
        property color symbolColor: functioningColor
        width: size; height: size
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = symbolColor
            ctx.lineWidth = size * 0.1
            ctx.lineCap = "round"
            var s = size / 32
            ctx.beginPath()
            ctx.arc(16*s, 20*s, 10*s, Math.PI, 0)
            ctx.stroke()
            ctx.beginPath()
            ctx.moveTo(16*s, 20*s)
            ctx.lineTo(21*s, 11*s)
            ctx.stroke()
            ctx.fillStyle = symbolColor
            ctx.beginPath()
            ctx.arc(16*s, 20*s, 2*s, 0, Math.PI * 2)
            ctx.fill()
        }
        onSymbolColorChanged: requestPaint()
    }

    // No data state
    Item {
        anchors.fill: parent
        visible: sarfGraphModel ? !sarfGraphModel.hasData : false

        PK.NoDataText {
            text: "Add events with dates to see the SARF graph."
        }
    }

    // Main content when data exists
    Item {
        anchors.fill: parent
        visible: sarfGraphModel ? sarfGraphModel.hasData : false

        // Header with mini graph
        Rectangle {
            id: headerCard
            width: parent.width
            height: miniGraphY + miniGraphH + 58
            color: cardColor

            // Date range label
            Text {
                x: graphPadding + 8
                y: 8
                text: {
                    if (!sarfGraphModel) return ""
                    if (isFocused) {
                        return Math.floor(focusedMinYearFrac) + " - " + Math.ceil(focusedMaxYearFrac)
                    } else if (showClusters && clusterModel && clusterModel.hasClusters) {
                        return Math.floor(clusterMinYearFrac) + " - " + Math.ceil(clusterMaxYearFrac)
                    }
                    return sarfGraphModel.yearStart + " - " + sarfGraphModel.yearEnd
                }
                font.pixelSize: 12
                color: textSecondary
            }

            // Graph background
            Rectangle {
                x: 0
                y: miniGraphY - 10
                width: parent.width
                height: miniGraphH + 68
                radius: 0
                color: util.IS_UI_DARK_MODE ? "#151520" : "#f5f5fa"
            }

            // Baseline
            Rectangle {
                x: gLeft; y: yPosMini(0)
                width: gWidth; height: 1
                color: dividerColor
            }

            // Graph lines
            Canvas {
                id: graphCanvas
                anchors.fill: parent
                antialiasing: true

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    // Focused mode is handled by focusedViewContainer - nothing to draw here
                    // Non-focused mode: cluster bars handle visualization
                }
            }

            Connections {
                target: sarfGraphModel
                function onChanged() { graphCanvas.requestPaint() }
            }

            Connections {
                target: clusterModel
                function onChanged() {
                    graphCanvas.requestPaint()
                    // Reset to unfocused mode with all clusters collapsed
                    collapseAllClusters()
                }
            }

            Connections {
                target: root
                function onFocusedClusterIndexChanged() { graphCanvas.requestPaint() }
            }

            // Cluster bars in zoomed-out mode (show clusters on timeline by date range)
            // Clipped container for zoom/pan
            Item {
                id: clusterBarsContainer
                x: gLeft
                y: miniGraphY
                width: gWidth
                height: miniGraphH
                clip: true
                visible: showClusters && !isFocused
                z: 150

                // Wheel scroll for panning
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.NoButton
                    onWheel: {
                        var deltaX = wheel.angleDelta.x !== 0 ? wheel.angleDelta.x : wheel.angleDelta.y
                        var maxScroll = Math.max(0, gWidth * timelineZoom - gWidth)
                        timelineScrollX = Math.max(0, Math.min(timelineScrollX - deltaX * 0.5, maxScroll))
                        wheel.accepted = true
                    }
                }

                // Drag to pan
                MouseArea {
                    anchors.fill: parent
                    z: -1
                    property real dragStartX: 0
                    property real dragStartScrollX: 0
                    property bool isDragging: false

                    onPressed: { dragStartX = mouse.x; dragStartScrollX = timelineScrollX; isDragging = false }
                    onPositionChanged: {
                        if (pressed && Math.abs(mouse.x - dragStartX) > 5) {
                            isDragging = true
                            var maxScroll = Math.max(0, gWidth * timelineZoom - gWidth)
                            timelineScrollX = Math.max(0, Math.min(dragStartScrollX + dragStartX - mouse.x, maxScroll))
                        }
                    }
                    onReleased: isDragging = false
                }

                // Pinch to zoom
                PinchArea {
                    id: clusterPinchArea
                    anchors.fill: parent

                    property real startZoom: 1.0
                    property real startScrollX: 0
                    property point startCenter: Qt.point(0, 0)

                    onPinchStarted: {
                        startZoom = timelineZoom
                        startScrollX = timelineScrollX
                        startCenter = pinch.center
                    }

                    onPinchUpdated: {
                        var newZoom = Math.max(minZoom, Math.min(maxZoom, startZoom * pinch.scale))
                        var baseWidth = gWidth
                        var newContentWidth = baseWidth * newZoom
                        var pinchXRatio = (startCenter.x + startScrollX) / (baseWidth * startZoom)
                        var newScrollX = pinchXRatio * newContentWidth - startCenter.x
                        var maxScroll = Math.max(0, newContentWidth - baseWidth)
                        timelineScrollX = Math.max(0, Math.min(newScrollX, maxScroll))
                        timelineZoom = newZoom
                    }
                }

                Repeater {
                    model: clusterModel ? clusterModel.clusters : []

                    Rectangle {
                        id: clusterBarDelegate
                        objectName: "clusterBar_" + index
                        property real startYearFrac: dateToYearFrac(modelData.startDate) || clusterMinYearFrac
                        property real endYearFrac: dateToYearFrac(modelData.endDate) || clusterMaxYearFrac
                        property int row: index % 3
                        property bool isSelected: clusterModel && clusterModel.selectedClusterId === modelData.id
                        property bool isHero: focusedClusterIndex === index
                        property real barX: xPosZoomed(startYearFrac) - gLeft
                        property real barWidth: Math.max(20, xPosZoomed(endYearFrac) - xPosZoomed(startYearFrac))

                        x: barX
                        y: 8 + row * 34
                        width: barWidth
                        height: 28
                        radius: 4
                        color: patternColor(modelData.pattern)
                        opacity: isHero ? 0 : (1 - animProgress) * (isSelected ? 1.0 : 0.7)
                        visible: opacity > 0 && barX + barWidth > 0 && barX < gWidth

                        Text {
                            anchors.centerIn: parent
                            text: modelData.title
                            font.pixelSize: 9
                            font.bold: true
                            color: "white"
                            elide: Text.ElideRight
                            width: Math.max(0, parent.width - 6)
                            horizontalAlignment: Text.AlignHCenter
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: if (!isFocused) focusCluster(index, clusterBarDelegate.x, clusterBarDelegate.y, clusterBarDelegate.width, clusterBarDelegate.height)
                        }
                    }
                }
            }

            // Scroll indicator (shown when zoomed)
            Rectangle {
                visible: showClusters && !isFocused && timelineZoom > 1.05
                anchors.bottom: parent.bottom
                anchors.bottomMargin: miniGraphY + miniGraphH + 25
                anchors.horizontalCenter: parent.horizontalCenter
                width: gWidth * 0.6; height: 3; radius: 1.5
                color: util.IS_UI_DARK_MODE ? "#1a1a2a" : "#d0d0d8"
                z: 160

                Rectangle {
                    x: {
                        var maxScroll = Math.max(1, gWidth * timelineZoom - gWidth)
                        return parent.width * (timelineScrollX / maxScroll) * (1 - 1/timelineZoom)
                    }
                    width: Math.max(16, parent.width / timelineZoom)
                    height: parent.height; radius: parent.radius
                    color: util.IS_UI_DARK_MODE ? "#505060" : "#808090"
                }
            }

            // Reset zoom button
            Rectangle {
                visible: showClusters && !isFocused && timelineZoom > 1.05
                anchors.right: parent.right
                anchors.rightMargin: graphPadding + 8
                y: miniGraphY
                width: 40; height: 18; radius: 9
                color: util.IS_UI_DARK_MODE ? "#3a3a4a" : "#d0d0d8"
                z: 160

                Text {
                    anchors.centerIn: parent
                    text: "Reset"
                    font.pixelSize: 9
                    color: util.IS_UI_DARK_MODE ? "#ffffff" : "#404050"
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: { timelineZoom = 1.0; timelineScrollX = 0 }
                }
            }

            // Event dot markers on graph (only shown in raw data mode - not cluster mode)
            Repeater {
                model: sarfGraphModel && !showClusters ? sarfGraphModel.events : []
                Item {
                    x: xPos(modelData.yearFrac) - 20
                    y: yPosMini(0) - 20
                    width: 40
                    height: 50
                    z: 100 + index

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 16
                        width: 8; height: 8; radius: 4
                        color: highlightedEvent === index ? textPrimary : primaryColorForEvent(modelData)
                        scale: highlightedEvent === index ? 1.5 : 1
                        Behavior on scale { NumberAnimation { duration: 150 } }
                    }

                    Text {
                        visible: highlightedEvent === index
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 28
                        text: modelData.date
                        font.pixelSize: 7
                        color: textSecondary
                        rotation: -45
                        transformOrigin: Item.Top
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: scrollToEventThenExpand(index)
                    }
                }
            }

            // B8-style HERO - focused cluster view with animated transition
            Rectangle {
                id: heroRect
                visible: focusedClusterIndex >= 0
                z: 200

                property int heroMargin: 8
                property real graphBgY: miniGraphY - 10

                // Animate from bar position to fill the graph area with even margins (left, right, top)
                x: gLeft + heroStartX + (heroMargin - heroStartX) * animProgress
                y: graphBgY + heroStartY + (heroMargin - heroStartY) * animProgress
                width: heroStartW + (gWidth - heroMargin * 2 - heroStartW) * animProgress
                height: heroStartH + (miniGraphH + 10 - heroMargin - heroStartH) * animProgress
                radius: 4 + 4 * animProgress
                color: util.IS_UI_DARK_MODE ? "#0a0a12" : "#f8f8fc"
                border.color: focusedCluster ? patternColor(focusedCluster.pattern) : "transparent"
                border.width: 2
                clip: true

                property var eventGroups: focusedCluster ? groupEventsByDay(focusedCluster.eventIds) : []

                // Title bar
                Rectangle {
                    id: heroTitleBar
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 36
                    color: focusedCluster ? patternColor(focusedCluster.pattern) : textSecondary
                    radius: parent.radius
                    opacity: animProgress

                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: parent.radius
                        color: parent.color
                    }

                    Text {
                        x: 14
                        anchors.verticalCenter: parent.verticalCenter
                        text: focusedCluster ? focusedCluster.title : ""
                        font.pixelSize: 14
                        font.bold: true
                        color: "white"
                        elide: Text.ElideRight
                        width: parent.width - 110
                    }

                    Text {
                        anchors.right: heroCloseButton.left
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: focusedCluster && focusedCluster.eventIds ? focusedCluster.eventIds.length + " events" : ""
                        font.pixelSize: 12
                        color: "#ffffffdd"
                    }

                    // Close button - 44px full iOS tap target
                    Rectangle {
                        id: heroCloseButton
                        anchors.right: parent.right
                        anchors.rightMargin: -4
                        anchors.verticalCenter: parent.verticalCenter
                        width: 44; height: 44; radius: 22
                        color: "#00000050"

                        Text {
                            anchors.centerIn: parent
                            text: "\u2715"
                            font.pixelSize: 20
                            font.bold: true
                            color: "#ffffff"
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: clearFocus()
                        }
                    }
                }

                // Content area below title bar
                Item {
                    id: heroContentArea
                    anchors.fill: parent
                    anchors.topMargin: heroTitleBar.height * animProgress
                    anchors.margins: 8
                    clip: true
                    opacity: animProgress > 0.3 ? 1 : 0

                    // Zoomable/pannable content
                    Item {
                        id: zoomableContent
                        x: -focusedScrollX
                        y: 0
                        width: heroContentArea.width * focusedZoom
                        height: heroContentArea.height

                        function xForYearFrac(yearFrac) {
                            if (!focusedCluster) return 0
                            var span = focusedYearSpan
                            if (span < 0.001) span = 0.001
                            var padding = 30
                            var usableWidth = width - (padding * 2)
                            return padding + ((yearFrac - focusedMinYearFrac) / span) * usableWidth
                        }

                        function yForValue(val) {
                            return heroContentArea.height * (1 - (val + 2) / 6) - 4
                        }

                        // Event bands in background
                        Repeater {
                            model: heroRect.eventGroups

                            Rectangle {
                                property var group: modelData
                                property int groupIndex: index
                                property bool isHovered: hoveredEventGroup === groupIndex
                                property real bandX: zoomableContent.xForYearFrac(group.yearFrac)

                                x: bandX - (8 + group.events.length * 4)
                                y: 0
                                width: 16 + group.events.length * 8
                                height: zoomableContent.height
                                color: focusedCluster ? patternColor(focusedCluster.pattern) : textSecondary
                                opacity: isHovered ? 0.25 : 0.08
                                radius: 4

                                Behavior on opacity { NumberAnimation { duration: 150 } }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: hoveredEventGroup = groupIndex
                                    onExited: hoveredEventGroup = -1
                                    onClicked: {
                                        hoveredEventGroup = (hoveredEventGroup === groupIndex) ? -1 : groupIndex
                                        if (group.events.length > 0 && sarfGraphModel) {
                                            var events = sarfGraphModel.events
                                            for (var i = 0; i < events.length; i++) {
                                                if (events[i].id === group.events[0].id) {
                                                    scrollToEventThenExpand(i)
                                                    break
                                                }
                                            }
                                        }
                                    }
                                }

                            }
                        }

                        // SARF lines canvas - inside zoomable content so it scales with zoom
                        Canvas {
                            id: heroSarfCanvas
                            anchors.fill: parent

                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.clearRect(0, 0, width, height)

                                if (!focusedCluster || !focusedCluster.eventIds || !sarfGraphModel) return

                                var events = sarfGraphModel.events
                                var cumulative = sarfGraphModel.cumulative
                                var eventIds = focusedCluster.eventIds

                                var dataPoints = []
                                for (var i = 0; i < eventIds.length; i++) {
                                    var eventId = eventIds[i]
                                    for (var j = 0; j < events.length; j++) {
                                        if (events[j].id === eventId) {
                                            dataPoints.push({
                                                yearFrac: events[j].yearFrac,
                                                symptom: cumulative[j].symptom,
                                                anxiety: cumulative[j].anxiety,
                                                functioning: cumulative[j].functioning
                                            })
                                            break
                                        }
                                    }
                                }

                                if (dataPoints.length === 0) return

                                var colors = [symptomColor.toString(), anxietyColor.toString(), functioningColor.toString()]
                                var keys = ['symptom', 'anxiety', 'functioning']

                                for (var k = 0; k < 3; k++) {
                                    ctx.strokeStyle = colors[k]
                                    ctx.lineWidth = 2.5
                                    ctx.lineCap = "round"
                                    ctx.lineJoin = "round"
                                    ctx.beginPath()

                                    for (var p = 0; p < dataPoints.length; p++) {
                                        var x = zoomableContent.xForYearFrac(dataPoints[p].yearFrac)
                                        var y = zoomableContent.yForValue(dataPoints[p][keys[k]])

                                        if (p === 0) {
                                            ctx.moveTo(x, y)
                                        } else {
                                            ctx.lineTo(x, y)
                                        }
                                    }
                                    ctx.stroke()

                                    ctx.fillStyle = colors[k]
                                    for (p = 0; p < dataPoints.length; p++) {
                                        x = zoomableContent.xForYearFrac(dataPoints[p].yearFrac)
                                        y = zoomableContent.yForValue(dataPoints[p][keys[k]])
                                        ctx.beginPath()
                                        ctx.arc(x, y, 3, 0, Math.PI * 2)
                                        ctx.fill()
                                    }
                                }
                            }
                        }
                    }

                    // Pinch/pan handling overlay
                    PinchArea {
                        id: heroPinchArea
                        anchors.fill: parent
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
                            var baseW = heroContentArea.width
                            var pinchXRatio = (startCenter.x + startScrollX) / (baseW * startZoom)
                            var newScrollX = pinchXRatio * baseW * newZoom - startCenter.x
                            var maxScroll = Math.max(0, baseW * newZoom - baseW)
                            focusedScrollX = Math.max(0, Math.min(newScrollX, maxScroll))
                            focusedZoom = newZoom
                            heroSarfCanvas.requestPaint()
                        }

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.NoButton
                            onWheel: {
                                if (animProgress < 0.9) return
                                var deltaX = wheel.angleDelta.x !== 0 ? wheel.angleDelta.x : wheel.angleDelta.y
                                var baseW = heroContentArea.width
                                var maxScroll = Math.max(0, baseW * focusedZoom - baseW)
                                focusedScrollX = Math.max(0, Math.min(focusedScrollX - deltaX * 0.5, maxScroll))
                                heroSarfCanvas.requestPaint()
                                wheel.accepted = true
                            }
                        }
                    }

                    Connections {
                        target: root
                        function onFocusedZoomChanged() { heroSarfCanvas.requestPaint() }
                        function onFocusedScrollXChanged() { heroSarfCanvas.requestPaint() }
                        function onFocusedClusterIndexChanged() { heroSarfCanvas.requestPaint() }
                        function onAnimProgressChanged() { if (animProgress > 0.25) heroSarfCanvas.requestPaint() }
                    }
                }

                // Scroll indicator
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 2
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width * 0.5; height: 3; radius: 1.5
                    color: util.IS_UI_DARK_MODE ? "#1a1a2a" : "#d0d0d8"
                    visible: animProgress > 0.9 && focusedZoom > 1.05

                    Rectangle {
                        x: {
                            var maxScroll = Math.max(1, heroContentArea.width * focusedZoom - heroContentArea.width)
                            return parent.width * (focusedScrollX / maxScroll) * (1 - 1/focusedZoom)
                        }
                        width: Math.max(12, parent.width / focusedZoom)
                        height: parent.height; radius: parent.radius
                        color: util.IS_UI_DARK_MODE ? "#505060" : "#808090"
                    }
                }

                // Tap bands hint
                Text {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 6
                    text: "tap bands for details"
                    font.pixelSize: 10
                    font.italic: true
                    color: textSecondary
                    opacity: animProgress * 0.7
                    visible: focusedZoom < 1.1
                }
            }

            // Navigation arrows for cycling clusters (shown when focused)
            Row {
                visible: isFocused
                anchors.horizontalCenter: parent.horizontalCenter
                y: miniGraphY + miniGraphH + 6
                spacing: 16
                z: 100
                height: 52

                // Prev button
                Rectangle {
                    width: 40; height: 40; radius: 20
                    color: util.IS_UI_DARK_MODE ? "#333340" : "#e0e0e8"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "\u25C0"
                        font.pixelSize: 15
                        color: textPrimary
                    }

                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -2  // Extend tap area to 44pt
                        cursorShape: Qt.PointingHandCursor
                        onClicked: focusPrevCluster()
                    }
                }

                // Current cluster title and count (fixed width to prevent button movement)
                Column {
                    width: 160
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: focusedCluster ? focusedCluster.title : ""
                        font.pixelSize: 14
                        font.bold: true
                        color: focusedCluster ? patternColor(focusedCluster.pattern) : textPrimary
                        elide: Text.ElideRight
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: (focusedClusterIndex + 1) + " / " + (clusterModel ? clusterModel.count : 0)
                        font.pixelSize: 13
                        color: textSecondary
                    }
                }

                // Next button
                Rectangle {
                    width: 40; height: 40; radius: 20
                    color: util.IS_UI_DARK_MODE ? "#333340" : "#e0e0e8"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "\u25B6"
                        font.pixelSize: 15
                        color: textPrimary
                    }

                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -2  // Extend tap area to 44pt
                        cursorShape: Qt.PointingHandCursor
                        onClicked: focusNextCluster()
                    }
                }
            }

            // Legend inside graph (bottom) - centered
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                y: miniGraphY + miniGraphH - 22
                spacing: 12
                z: 50

                Row {
                    spacing: 4
                    SymptomSymbol { size: 12; symbolColor: symptomColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Symptom"; font.pixelSize: 12; font.bold: true; color: symptomColor }
                }
                Row {
                    spacing: 4
                    AnxietySymbol { size: 12; symbolColor: anxietyColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Anxiety"; font.pixelSize: 12; font.bold: true; color: anxietyColor }
                }
                Row {
                    spacing: 4
                    RelationshipSymbol { size: 12; symbolColor: relationshipColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Relationship"; font.pixelSize: 12; font.bold: true; color: relationshipColor }
                }
                Row {
                    spacing: 4
                    FunctioningSymbol { size: 12; symbolColor: functioningColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Functioning"; font.pixelSize: 12; font.bold: true; color: functioningColor }
                }
            }

            // Clusters toggle (left side, hidden when focused)
            Row {
                visible: !isFocused && clusterModel && clusterModel.hasClusters
                x: 12
                y: miniGraphY + miniGraphH + 8
                spacing: 8
                height: 44

                Rectangle {
                    width: 40; height: 24; radius: 12
                    color: showClusters ? util.QML_HIGHLIGHT_COLOR : (util.IS_UI_DARK_MODE ? "#444450" : "#c0c0c8")
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        width: 20; height: 20; radius: 10
                        color: "white"
                        x: showClusters ? parent.width - width - 2 : 2
                        anchors.verticalCenter: parent.verticalCenter

                        Behavior on x { NumberAnimation { duration: 150 } }
                    }

                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -10  // Extend tap area to 44pt
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            showClusters = !showClusters
                            if (!showClusters) {
                                focusedClusterIndex = -1
                            }
                        }
                    }
                }

                Text {
                    text: "Clusters"
                    font.pixelSize: 14
                    color: textSecondary
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            // Action buttons row (right side, hidden when focused)
            Row {
                visible: !isFocused
                anchors.right: parent.right
                anchors.rightMargin: 12
                y: miniGraphY + miniGraphH + 8
                spacing: 12
                height: 44

                // Cluster count
                Text {
                    visible: showClusters && clusterModel && clusterModel.hasClusters
                    text: clusterModel ? clusterModel.count + " clusters" : ""
                    font.pixelSize: 14
                    color: textSecondary
                    anchors.verticalCenter: parent.verticalCenter
                }

                // Detect Clusters button
                Rectangle {
                    width: Math.max(detectRow.width + 24, 90)
                    height: 32
                    radius: 16
                    color: clusterModel && clusterModel.detecting ? textSecondary : util.QML_HIGHLIGHT_COLOR
                    opacity: clusterModel && clusterModel.detecting ? 0.6 : 0.9
                    anchors.verticalCenter: parent.verticalCenter

                    Row {
                        id: detectRow
                        anchors.centerIn: parent
                        spacing: 6

                        Text {
                            text: clusterModel && clusterModel.detecting ? "..." : (clusterModel && clusterModel.hasClusters ? "Re-detect" : "Find Clusters")
                            font.pixelSize: 13
                            font.bold: true
                            color: "white"
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -6  // Extend tap area to 44pt
                        enabled: clusterModel && !clusterModel.detecting
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: {
                            if (clusterModel) {
                                clusterModel.detect()
                            }
                        }
                    }
                }
            }
        }

        // Story List
        ListView {
            id: storyList
            objectName: "storyList"
            x: 0; y: headerCard.height + 5
            width: parent.width
            height: parent.height - headerCard.height - 5
            clip: true
            spacing: 0
            model: sarfGraphModel ? sarfGraphModel.events : []

            NumberAnimation {
                id: scrollAnimation
                target: storyList
                property: "contentY"
                duration: 500
                easing.type: Easing.InOutQuad
            }

            NumberAnimation {
                id: scrollAdjustAnimation
                target: storyList
                property: "contentY"
                duration: 200
                easing.type: Easing.OutQuad
            }

            onCurrentIndexChanged: highlightedEvent = currentIndex

            delegate: Item {
                id: delegateRoot
                width: ListView.view.width
                height: hideCompletely ? 0 : (clusterHeaderHeight + (showEventContent ? eventHeight : 0))
                clip: true
                visible: !hideCompletely

                property var evt: modelData
                property bool isShift: evt.kind === "shift"
                property bool isDeathEvent: evt.kind === "death"
                property bool isLife: isLifeEvent(evt.kind)
                property real swipeX: 0
                property real actionWidth: 75

                // Cluster grouping properties (only apply when showClusters is true)
                property var cluster: showClusters ? clusterForEventIndex(index) : null
                property bool isFirstInCluster: showClusters && isFirstEventInCluster(index)
                property bool isClusterCollapsed: showClusters && cluster && isEventClusterCollapsed(index)
                // Hide if: (1) showClusters is ON and event not in any cluster, or (2) cluster collapsed and not first
                property bool hideCompletely: (showClusters && clusterModel && clusterModel.hasClusters && cluster === null) || (isClusterCollapsed && !isFirstInCluster)
                property bool showEventContent: !isClusterCollapsed || !cluster
                property real clusterHeaderHeight: isFirstInCluster ? 92 : 0
                property real eventHeight: selectedEvent === index ? 150 : 110

                Behavior on height { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }

                // Cluster section header (shown when this is first event in a cluster)
                Rectangle {
                    id: clusterHeader
                    visible: delegateRoot.isFirstInCluster
                    width: parent.width - 32
                    height: 76
                    x: 16
                    y: 8
                    radius: 14
                    color: util.IS_UI_DARK_MODE ? "#252535" : "#f0f0f8"
                    border.color: cluster ? patternColor(cluster.pattern) : dividerColor
                    border.width: 1.5

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (delegateRoot.cluster) {
                                // Check if this cluster is currently focused
                                var clusterIdx = -1
                                if (clusterModel && clusterModel.clusters) {
                                    for (var i = 0; i < clusterModel.clusters.length; i++) {
                                        if (clusterModel.clusters[i].id === delegateRoot.cluster.id) {
                                            clusterIdx = i
                                            break
                                        }
                                    }
                                }
                                if (clusterIdx === focusedClusterIndex) {
                                    // Already focused - collapse and return to overview
                                    clearFocus()
                                } else {
                                    // Focus this cluster
                                    focusCluster(clusterIdx)
                                }
                            }
                        }
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 12

                        // Expand/collapse indicator
                        Text {
                            text: delegateRoot.cluster && collapsedClusters[delegateRoot.cluster.id] ? "\u25B6" : "\u25BC"
                            font.pixelSize: 14
                            color: textSecondary
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Column {
                            spacing: 6

                            Row {
                                spacing: 10
                                width: parent.parent.width - 60

                                Text {
                                    text: delegateRoot.cluster ? delegateRoot.cluster.title : ""
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: textPrimary
                                    elide: Text.ElideRight
                                    width: Math.min(implicitWidth, parent.width - 40)
                                }

                                // Dominant variable badge
                                Rectangle {
                                    visible: delegateRoot.cluster && delegateRoot.cluster.dominantVariable !== undefined && delegateRoot.cluster.dominantVariable !== null && delegateRoot.cluster.dominantVariable !== ""
                                    width: 24
                                    height: 24
                                    radius: 12
                                    color: delegateRoot.cluster ? dominantVariableColor(delegateRoot.cluster.dominantVariable) : textSecondary
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        anchors.centerIn: parent
                                        text: delegateRoot.cluster ? delegateRoot.cluster.dominantVariable : ""
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: "white"
                                    }
                                }
                            }

                            Row {
                                spacing: 10

                                // Date range
                                Text {
                                    text: {
                                        if (!delegateRoot.cluster) return ""
                                        var start = delegateRoot.cluster.startDate || ""
                                        var end = delegateRoot.cluster.endDate || ""
                                        if (start === end) return start
                                        return start + " - " + end
                                    }
                                    font.pixelSize: 13
                                    color: textSecondary
                                }

                                // Pattern badge
                                Rectangle {
                                    visible: delegateRoot.cluster && delegateRoot.cluster.pattern !== undefined && delegateRoot.cluster.pattern !== null && delegateRoot.cluster.pattern !== ""
                                    width: patternLabelText.width + 14
                                    height: 22
                                    radius: 11
                                    color: delegateRoot.cluster ? patternColor(delegateRoot.cluster.pattern) : textSecondary
                                    opacity: 0.9

                                    Text {
                                        id: patternLabelText
                                        anchors.centerIn: parent
                                        text: delegateRoot.cluster ? patternLabel(delegateRoot.cluster.pattern) : ""
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: "white"
                                    }
                                }

                                // Event count
                                Text {
                                    text: delegateRoot.cluster && delegateRoot.cluster.eventIds ? delegateRoot.cluster.eventIds.length + " events" : ""
                                    font.pixelSize: 13
                                    color: textSecondary
                                }
                            }
                        }
                    }
                }

                // Edit action (revealed on swipe right)
                Rectangle {
                    visible: delegateRoot.showEventContent
                    anchors.left: parent.left
                    y: delegateRoot.clusterHeaderHeight
                    height: delegateRoot.eventHeight
                    width: actionWidth
                    color: util.QML_SELECTION_COLOR

                    Text {
                        anchors.centerIn: parent
                        text: "Edit"
                        font.pixelSize: 17
                        font.weight: Font.Medium
                        color: "#fff"
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            swipeX = 0
                            swipedEvent = -1
                            editEventRequested(evt.id)
                        }
                    }
                }

                // Delete action (revealed on swipe left)
                Rectangle {
                    visible: delegateRoot.showEventContent
                    anchors.right: parent.right
                    y: delegateRoot.clusterHeaderHeight
                    height: delegateRoot.eventHeight
                    width: actionWidth
                    color: "#FF3B30"

                    Text {
                        anchors.centerIn: parent
                        text: "Delete"
                        font.pixelSize: 17
                        font.weight: Font.Medium
                        color: "#fff"
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            swipeX = 0
                            swipedEvent = -1
                            deleteEventRequested(evt.id)
                        }
                    }
                }

                // Swipeable content
                Rectangle {
                    id: contentRow
                    visible: delegateRoot.showEventContent
                    x: delegateRoot.swipeX
                    y: delegateRoot.clusterHeaderHeight
                    width: parent.width
                    height: delegateRoot.eventHeight
                    color: selectedEvent === index ? highlightColor : bgColor

                    Behavior on x {
                        enabled: !swipeArea.pressed
                        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
                    }

                    MouseArea {
                        id: swipeArea
                        anchors.fill: parent
                        property real startX: 0
                        property real startSwipeX: 0
                        property bool isDragging: false

                        onPressed: {
                            startX = mouse.x
                            startSwipeX = delegateRoot.swipeX
                            isDragging = false
                        }

                        onPositionChanged: {
                            var delta = mouse.x - startX
                            if (Math.abs(delta) > 10) {
                                isDragging = true
                            }

                            if (isDragging) {
                                var newX = startSwipeX + delta

                                // Close other swiped items
                                if (swipedEvent !== index && swipedEvent !== -1) {
                                    swipedEvent = -1
                                }

                                // Clamp swipe range
                                delegateRoot.swipeX = Math.max(-actionWidth, Math.min(actionWidth, newX))
                            }
                        }

                        onReleased: {
                            var threshold = actionWidth * 0.4
                            if (delegateRoot.swipeX > threshold) {
                                delegateRoot.swipeX = actionWidth
                                swipedEvent = index
                            } else if (delegateRoot.swipeX < -threshold) {
                                delegateRoot.swipeX = -actionWidth
                                swipedEvent = index
                            } else {
                                delegateRoot.swipeX = 0
                                if (swipedEvent === index) swipedEvent = -1
                            }
                            isDragging = false
                        }

                        onCanceled: {
                            // Reset to nearest snap position on cancel
                            var threshold = actionWidth * 0.4
                            if (delegateRoot.swipeX > threshold) {
                                delegateRoot.swipeX = actionWidth
                                swipedEvent = index
                            } else if (delegateRoot.swipeX < -threshold) {
                                delegateRoot.swipeX = -actionWidth
                                swipedEvent = index
                            } else {
                                delegateRoot.swipeX = 0
                                if (swipedEvent === index) swipedEvent = -1
                            }
                            isDragging = false
                        }

                        onClicked: {
                            if (!isDragging && Math.abs(delegateRoot.swipeX) < 5) {
                                // Reset any swiped item
                                if (swipedEvent !== -1) {
                                    swipedEvent = -1
                                    return
                                }
                                // Toggle expand
                                if (selectedEvent === index) {
                                    selectedEvent = -1
                                } else {
                                    selectedEvent = index
                                    highlightedEvent = index
                                    scrollAdjustTimer.restart()
                                }
                            }
                        }
                    }

                    // Reset swipe when another item is swiped
                    Connections {
                        target: root
                        function onSwipedEventChanged() {
                            if (swipedEvent !== index && delegateRoot.swipeX !== 0) {
                                delegateRoot.swipeX = 0
                            }
                        }
                    }

                    // Timeline line
                    Rectangle {
                        x: 35; y: 0
                        width: 2
                        height: parent.height
                        color: dividerColor
                    }

                    // Node symbol based on event kind
                    Item {
                        id: nodeContainer
                        x: 8; y: 8
                        width: 56; height: 56

                        // Life events: foreground filled circle
                        Rectangle {
                            visible: delegateRoot.isLife
                            anchors.centerIn: parent
                            width: 26; height: 26; radius: 13
                            color: textSecondary
                        }

                        // Death: grey box
                        Rectangle {
                            visible: delegateRoot.isDeathEvent
                            anchors.centerIn: parent
                            width: 26; height: 26; radius: 3
                            color: functioningColor
                        }

                        // Shift events: vertically stacked SARF symbols
                        Column {
                            id: sarfStack
                            visible: delegateRoot.isShift
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.top: parent.top
                            anchors.topMargin: 15
                            spacing: 1

                            property real symSize: 18

                            SymptomSymbol {
                                visible: delegateRoot.evt.symptom !== null && delegateRoot.evt.symptom !== undefined
                                size: sarfStack.symSize
                                symbolColor: symptomColor
                            }
                            AnxietySymbol {
                                visible: delegateRoot.evt.anxiety !== null && delegateRoot.evt.anxiety !== undefined
                                size: sarfStack.symSize
                                symbolColor: anxietyColor
                            }
                            RelationshipSymbol {
                                visible: delegateRoot.evt.relationship !== null && delegateRoot.evt.relationship !== undefined
                                size: sarfStack.symSize
                                symbolColor: relationshipColor
                            }
                            FunctioningSymbol {
                                visible: delegateRoot.evt.functioning !== null && delegateRoot.evt.functioning !== undefined
                                size: sarfStack.symSize
                                symbolColor: functioningColor
                            }
                        }
                    }

                    // Content
                    Column {
                        x: 70; y: 14
                        width: parent.width - 100
                        spacing: 6

                        // Date and Who on same row
                        Item {
                            width: parent.width
                            height: 22
                            Text {
                                text: evt.date
                                font.pixelSize: 14
                                font.weight: Font.Bold
                                color: primaryColorForEvent(evt)
                            }
                            Text {
                                x: 105
                                text: evt.who
                                font.pixelSize: 14
                                color: textSecondary
                            }
                        }

                        Text {
                            text: evt.description
                            font.pixelSize: 17
                            font.weight: Font.Medium
                            color: textPrimary
                            width: parent.width
                            wrapMode: Text.WordWrap
                        }

                        // Expanded content
                        Column {
                            visible: selectedEvent === index
                            opacity: selectedEvent === index ? 1 : 0
                            spacing: 6

                            Behavior on opacity { NumberAnimation { duration: 200 } }

                            Text {
                                text: evt.notes || ""
                                font.pixelSize: 14
                                color: textSecondary
                                visible: evt.notes && evt.notes.length > 0
                            }

                            // Relationship pill for Shift events with relationship set
                            Rectangle {
                                visible: delegateRoot.isShift && evt.relationship !== null && evt.relationship !== undefined
                                width: 110; height: 28; radius: 14
                                color: relationshipColor

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 6
                                    RelationshipSymbol { size: 12; symbolColor: "#fff"; anchors.verticalCenter: parent.verticalCenter }
                                    Text {
                                        text: evt.relationship ? evt.relationship.charAt(0).toUpperCase() + evt.relationship.slice(1) : ""
                                        font.pixelSize: 12
                                        color: "#fff"
                                    }
                                }
                            }
                        }
                    }

                    // Chevron
                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 20
                        anchors.verticalCenter: parent.verticalCenter
                        text: selectedEvent === index ? "\u25BC" : "\u25B6"
                        font.pixelSize: 14
                        color: textSecondary
                    }
                }
            }
        }
    }
}
