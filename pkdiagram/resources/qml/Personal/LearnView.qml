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
    property real miniGraphY: 0
    property real miniGraphH: 260
    property real gLeft: 0
    property real gRight: width
    property real gWidth: gRight - gLeft

    // Controls area (shared between unfocused and focused modes)
    property real controlsY: miniGraphY + miniGraphH  // Controls start at bottom of graph
    property real controlsHeight: 52  // Fixed height for both control sets
    property real graphAreaBottom: controlsY  // Hero must stay above this

    // Timeline zoom/pan properties (overview mode)
    property real timelineZoom: 2.0 // default
    property real timelineScrollX: 0
    property real minZoom: 1.0
    property real maxZoom: 20.0
    property int lastClusterCount: 0  // Track to detect re-detection

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
        if (!showClusters) return xPos(year)
        // Always use cluster year range for cluster bars, regardless of focus state
        var yearStart = clusterMinYearFrac
        var yearSpan = clusterYearSpan
        if (yearSpan === 0) yearSpan = 1
        var baseX = ((year - yearStart) / yearSpan) * gWidth
        return gLeft + baseX * timelineZoom - timelineScrollX
    }

    // Minimum bar width for tappable clusters
    readonly property real minBarWidth: 30

    // Calculate optimal zoom so clusters are readable
    function calculateOptimalZoom() {
        if (!clusterModel || !clusterModel.clusters || clusterModel.clusters.length === 0) {
            return 1.0
        }
        var clusters = clusterModel.clusters
        var yearSpan = clusterYearSpan
        if (yearSpan < 0.001) yearSpan = 1

        // Find the narrowest cluster's time span
        var minClusterSpan = yearSpan
        for (var i = 0; i < clusters.length; i++) {
            var c = clusters[i]
            var startFrac = dateToYearFrac(c.startDate) || clusterMinYearFrac
            var endFrac = dateToYearFrac(c.endDate) || clusterMaxYearFrac
            var span = Math.max(0.01, endFrac - startFrac)  // At least ~4 days
            if (span < minClusterSpan) minClusterSpan = span
        }

        // Calculate zoom needed for narrowest cluster to be minBarWidth pixels
        // barWidth = (clusterSpan / yearSpan) * gWidth * zoom
        // minBarWidth = (minClusterSpan / yearSpan) * gWidth * zoom
        // zoom = minBarWidth / ((minClusterSpan / yearSpan) * gWidth)
        var baseWidth = (minClusterSpan / yearSpan) * gWidth
        if (baseWidth < 1) baseWidth = 1
        var optimalZoom = minBarWidth / baseWidth

        // Clamp to reasonable range
        return Math.max(minZoom, Math.min(optimalZoom, maxZoom))
    }

    // defaults
    function applyOptimalZoom() {
        timelineZoom = 2.0
        timelineScrollX = 0
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
        // Clean up any running scroll animations and timers to avoid race conditions
        clusterScrollTimer.stop()
        clusterScrollAdjustTimer.stop()
        scrollAnimation.stop()
        clusterScrollAdjustAnimation.stop()
        pendingClusterScroll = -1
        pendingClusterExpand = ""
        pendingScrollAdjustIndex = -1
        console.log("focusCluster: idx=" + idx + ", cleaned up previous animations")

        var cluster = clusterModel.clusters[idx]
        // Calculate bar position from cluster data if not provided
        if (barX === undefined && cluster) {
            var startFrac = dateToYearFrac(cluster.startDate) || clusterMinYearFrac
            var endFrac = dateToYearFrac(cluster.endDate) || clusterMaxYearFrac
            var row = idx % 3
            barX = xPosZoomed(startFrac) - gLeft
            barY = 18 + row * 38 + 4  // +4 for barRect offset within delegate
            barW = Math.max(minBarWidth, xPosZoomed(endFrac) - xPosZoomed(startFrac))
            barH = 28
        }
        // Capture hero start position from the bar
        heroStartX = barX !== undefined ? barX : 0
        heroStartY = barY !== undefined ? barY : 0
        heroStartW = barW !== undefined ? barW : gWidth
        heroStartH = barH !== undefined ? barH : 28
        // Reset focused view zoom (not timeline zoom)
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
        // Start animation from 0
        animProgress = 0
        focusAnim.start()
    }

    property int pendingClusterScroll: -1
    property string pendingClusterExpand: ""

    function scrollToClusterIndex(eventIndex) {
        // Use focusedClusterIndex directly - we already know which cluster we're focusing on
        var targetClusterIdx = focusedClusterIndex

        console.log("scrollToClusterIndex: eventIndex=" + eventIndex + ", targetClusterIdx=" + targetClusterIdx)

        if (targetClusterIdx < 0) return storyList.contentY

        // When all clusters are collapsed, each shows only its header (84px)
        var collapsedHeaderHeight = 84
        var targetY = targetClusterIdx * collapsedHeaderHeight - 20

        // Use actual contentHeight (more reliable after layout settles)
        var minY = 0
        var maxY = Math.max(0, storyList.contentHeight - storyList.height)
        var clampedY = Math.max(minY, Math.min(targetY, maxY))

        console.log("  targetClusterIdx=" + targetClusterIdx + ", collapsedHeaderHeight=" + collapsedHeaderHeight)
        console.log("  targetY=" + targetY + " (clusterIdx * 84 - 20)")
        console.log("  storyList.contentHeight=" + storyList.contentHeight + ", storyList.height=" + storyList.height)
        console.log("  maxY=" + maxY + ", clampedY=" + clampedY)
        console.log("  storyList.contentY (before)=" + storyList.contentY)

        return clampedY
    }

    Timer {
        id: clusterScrollTimer
        interval: 300  // Must exceed delegate height animation (250ms) to avoid race condition
        onTriggered: {
            if (pendingClusterScroll >= 0) {
                storyList.forceLayout()
                console.log("clusterScrollTimer triggered, pendingClusterScroll=" + pendingClusterScroll)
                var targetY = scrollToClusterIndex(pendingClusterScroll)
                var maxY = Math.max(0, storyList.contentHeight - storyList.height)
                targetY = Math.max(0, Math.min(targetY, maxY))
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
        interval: 300  // Must exceed delegate height animation (250ms) to avoid race condition
        onTriggered: {
            if (pendingScrollAdjustIndex >= 0) {
                storyList.forceLayout()
                // Now that cluster is expanded, recalculate and scroll to correct position
                var targetY = pendingScrollAdjustIndex > 0 ? scrollToClusterIndex(pendingScrollAdjustIndex) : 0
                var maxY = Math.max(0, storyList.contentHeight - storyList.height)
                targetY = Math.max(0, Math.min(targetY, maxY))
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
        // Clean up any running scroll animations and timers
        clusterScrollTimer.stop()
        clusterScrollAdjustTimer.stop()
        scrollAnimation.stop()
        clusterScrollAdjustAnimation.stop()
        pendingClusterScroll = -1
        pendingClusterExpand = ""
        pendingScrollAdjustIndex = -1
        console.log("clearFocus: cleaned up scroll animations")

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

    // Deductively calculate total story list height from model state
    function calculateStoryListHeight() {
        if (!sarfGraphModel) return 0
        var events = sarfGraphModel.events
        if (!events || events.length === 0) return 0
        var total = 12  // ListView header height
        var hasClusters = clusterModel && clusterModel.hasClusters
        for (var i = 0; i < events.length; i++) {
            var cluster = showClusters ? clusterForEventIndex(i) : null
            var isFirst = showClusters && isFirstEventInCluster(i)
            var isCollapsed = showClusters && cluster && collapsedClusters[cluster.id] === true
            var hideCompletely = (showClusters && hasClusters && cluster === null) || (isCollapsed && !isFirst)
            if (hideCompletely) continue
            var headerH = isFirst ? 84 : 0
            var showContent = !isCollapsed || !cluster
            var eventH = showContent ? (selectedEvent === i ? 200 : 110) : 0
            total += headerH + eventH
        }
        return total
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

    readonly property var clusterPalette: [
        "#e74c3c",  // Red
        "#9b59b6",  // Purple
        "#3498db",  // Blue
        "#27ae60",  // Green
        "#e67e22",  // Orange
        "#f39c12",  // Gold
        "#1abc9c",  // Teal
        "#e91e63",  // Pink
        "#00bcd4",  // Cyan
        "#8bc34a"   // Lime
    ]

    function clusterColor(clusterId) {
        if (!clusterId) return textSecondary
        var hash = 0
        for (var i = 0; i < clusterId.length; i++) {
            hash = ((hash << 5) - hash) + clusterId.charCodeAt(i)
            hash = hash & hash
        }
        return clusterPalette[Math.abs(hash) % clusterPalette.length]
    }

    readonly property var monthNames: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    readonly property var monthDays: [31,28,31,30,31,30,31,31,30,31,30,31]

    function dayOfYearToMonthDay(dayOfYear) {
        var month = 0, dayInMonth = dayOfYear
        for (var i = 0; i < 12; i++) {
            if (dayInMonth < monthDays[i]) { month = i; break }
            dayInMonth -= monthDays[i]
        }
        return { month: month, day: Math.round(dayInMonth) + 1 }
    }

    function formatDateRange(start, end) {
        if (!start) return ""
        var sp = start.split("-")
        if (sp.length < 3) return start
        var sYear = parseInt(sp[0]), sMonth = parseInt(sp[1]) - 1, sDay = parseInt(sp[2])
        var shortYear = "'" + String(sYear).slice(-2)
        if (!end || start === end) {
            return monthNames[sMonth] + " " + sDay + ", " + shortYear
        }
        var ep = end.split("-")
        if (ep.length < 3) return start + " - " + end
        var eYear = parseInt(ep[0]), eMonth = parseInt(ep[1]) - 1, eDay = parseInt(ep[2])
        if (sYear === eYear && sMonth === eMonth) {
            return monthNames[sMonth] + " " + sDay + "-" + eDay + ", " + shortYear
        }
        return monthNames[sMonth] + " " + sDay + ", " + shortYear + " - " + monthNames[eMonth] + " " + eDay
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
            height: controlsY + controlsHeight + 6
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
                y: 0
                width: parent.width
                height: controlsY + controlsHeight + 6
                radius: 0
                color: util.IS_UI_DARK_MODE ? "#151520" : "#f5f5fa"
            }

            // // Baseline
            // Rectangle {
            //     x: gLeft; y: yPosMini(0)
            //     width: gWidth; height: 1
            //     color: dividerColor
            // }

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
                    // Check if clusters were re-detected (count changed)
                    var currentCount = clusterModel && clusterModel.clusters ? clusterModel.clusters.length : 0
                    if (currentCount !== lastClusterCount) {
                        lastClusterCount = currentCount
                        // Reset to unfocused mode with all clusters collapsed
                        collapseAllClusters()
                        // Auto-zoom only when clusters are re-detected
                        applyOptimalZoom()
                    }
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
                objectName: "clusterBarsContainer"
                x: gLeft
                y: miniGraphY
                width: gWidth
                height: miniGraphH
                clip: true
                visible: showClusters
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

                // Pinch to zoom (with drag-to-pan MouseArea as child)
                PinchArea {
                    id: clusterPinchArea
                    anchors.fill: parent

                    property real startZoom: 1.0
                    property real startScrollX: 0
                    property point startCenter: Qt.point(0, 0)
                    property point lastCenter: Qt.point(0, 0)
                    property real accumulatedPan: 0

                    onPinchStarted: {
                        startZoom = timelineZoom
                        startScrollX = timelineScrollX
                        startCenter = pinch.center
                        lastCenter = pinch.center
                        accumulatedPan = 0
                    }

                    onPinchUpdated: {
                        var newZoom = Math.max(minZoom, Math.min(maxZoom, startZoom * pinch.scale))
                        var baseWidth = gWidth
                        var newContentWidth = baseWidth * newZoom
                        var pinchXRatio = (startCenter.x + startScrollX) / (baseWidth * startZoom)
                        var newScrollForZoom = pinchXRatio * newContentWidth - startCenter.x

                        // Pan during pinch (both fingers moving together)
                        var panDelta = lastCenter.x - pinch.center.x
                        lastCenter = pinch.center
                        accumulatedPan += panDelta

                        var newScrollX = newScrollForZoom + accumulatedPan
                        var maxScroll = Math.max(0, newContentWidth - baseWidth)
                        timelineScrollX = Math.max(0, Math.min(newScrollX, maxScroll))
                        timelineZoom = newZoom
                    }

                    // Drag to pan (must be child of PinchArea to receive single-touch events)
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
                }

                // Time markers on x-axis (adaptive granularity)
                Repeater {
                    id: timeMarkers

                    // Calculate visible range and appropriate interval
                    property real visibleSpan: clusterYearSpan / timelineZoom
                    property string intervalType: {
                        if (visibleSpan > 10) return "year5"
                        if (visibleSpan > 4) return "year1"
                        if (visibleSpan > 1.5) return "month6"
                        if (visibleSpan > 0.6) return "month3"
                        if (visibleSpan > 0.25) return "month1"
                        if (visibleSpan > 0.08) return "week1"
                        return "day1"
                    }
                    property real interval: {
                        if (intervalType === "year5") return 5
                        if (intervalType === "year1") return 1
                        if (intervalType === "month6") return 0.5
                        if (intervalType === "month3") return 0.25
                        if (intervalType === "month1") return 1/12
                        if (intervalType === "week1") return 1/52
                        return 1/365
                    }

                    model: {
                        var markers = []
                        var start = Math.floor(clusterMinYearFrac / interval) * interval
                        var end = clusterMaxYearFrac + interval * 0.1  // Minimal padding
                        for (var t = start; t <= end; t += interval) {
                            markers.push(t)
                        }
                        return markers
                    }

                    Item {
                        property real markerX: xPosZoomed(modelData) - gLeft
                        property bool isYear: Math.abs(modelData - Math.round(modelData)) < 0.001
                        x: markerX
                        y: 0
                        width: 1
                        height: parent.height
                        visible: markerX > -20 && markerX < gWidth + 20

                        // Vertical line - stops above text
                        Rectangle {
                            x: 0
                            y: 0
                            width: 1
                            height: parent.height - 18
                            color: util.IS_UI_DARK_MODE
                                ? (isYear ? "#404050" : "#282838")
                                : (isYear ? "#c0c0c8" : "#e0e0e8")
                        }

                        // Label at bottom
                        Text {
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 4
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: {
                                if (isYear) return Math.round(modelData)
                                var year = Math.floor(modelData)
                                var dayOfYear = (modelData - year) * 365
                                var md = dayOfYearToMonthDay(dayOfYear)
                                var iType = timeMarkers.intervalType
                                if (iType === "month6" || iType === "month3" || iType === "month1") return monthNames[md.month]
                                if (iType === "week1") return monthNames[md.month] + " " + md.day
                                return md.day
                            }
                            font.pixelSize: isYear ? 10 : 8
                            font.bold: isYear
                            color: util.IS_UI_DARK_MODE
                                ? (isYear ? "#606070" : "#404050")
                                : (isYear ? "#808088" : "#a0a0a8")
                        }
                    }
                }

                // Cluster boundary markers (dashed lines)
                Repeater {
                    model: clusterModel ? clusterModel.clusters : []

                    Item {
                        property real startFrac: dateToYearFrac(modelData.startDate) || clusterMinYearFrac
                        property real endFrac: dateToYearFrac(modelData.endDate) || clusterMaxYearFrac
                        property bool isSingleDay: Math.abs(endFrac - startFrac) < 0.003
                        property real startX: xPosZoomed(startFrac) - gLeft
                        property real endX: xPosZoomed(endFrac) - gLeft

                        // Start line
                        Column {
                            x: startX
                            y: 0
                            width: 1
                            height: parent.height - 18
                            visible: startX > -20 && startX < gWidth + 20
                            spacing: 3

                            Repeater {
                                model: Math.floor((parent.height) / 6)
                                Rectangle {
                                    width: 1
                                    height: 3
                                    color: util.IS_UI_DARK_MODE ? "#606070" : "#a0a0a8"
                                }
                            }
                        }

                        // End line (only if different from start)
                        Column {
                            x: endX
                            y: 0
                            width: 1
                            height: parent.height - 18
                            visible: !isSingleDay && endX > -20 && endX < gWidth + 20
                            spacing: 3

                            Repeater {
                                model: Math.floor((parent.height) / 6)
                                Rectangle {
                                    width: 1
                                    height: 3
                                    color: util.IS_UI_DARK_MODE ? "#606070" : "#a0a0a8"
                                }
                            }
                        }
                    }
                }

                Repeater {
                    model: clusterModel ? clusterModel.clusters : []

                    Item {
                        id: clusterBarDelegate
                        objectName: "clusterBar_" + index
                        property real startYearFrac: dateToYearFrac(modelData.startDate) || clusterMinYearFrac
                        property real endYearFrac: dateToYearFrac(modelData.endDate) || clusterMaxYearFrac
                        property int row: index % 4
                        property bool isSelected: clusterModel && clusterModel.selectedClusterId === modelData.id
                        property bool isHero: focusedClusterIndex === index
                        property real barX: xPosZoomed(startYearFrac) - gLeft
                        property real naturalWidth: xPosZoomed(endYearFrac) - xPosZoomed(startYearFrac)
                        property real barWidth: Math.max(minBarWidth, naturalWidth)
                        property bool isNarrow: naturalWidth < minBarWidth
                        property real delegateOpacity: isSelected ? 1.0 : 0.7

                        x: barX
                        y: 20 + row * 55
                        width: barWidth
                        height: 32
                        visible: delegateOpacity > 0 && barX + barWidth > 0 && barX < gWidth

                        // Label above bar for narrow clusters
                        Text {
                            visible: clusterBarDelegate.isNarrow
                            anchors.horizontalCenter: barRect.horizontalCenter
                            anchors.bottom: barRect.top
                            anchors.bottomMargin: 2
                            text: modelData.title
                            font.pixelSize: 10
                            font.bold: true
                            color: clusterColor(modelData.id)
                            elide: Text.ElideRight
                            width: 240
                            horizontalAlignment: Text.AlignHCenter
                            opacity: clusterBarDelegate.delegateOpacity
                        }

                        Rectangle {
                            id: barRect
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 28
                            radius: 4
                            color: clusterColor(modelData.id)
                            opacity: clusterBarDelegate.delegateOpacity

                            // Label inside bar for wide clusters
                            Text {
                                visible: !clusterBarDelegate.isNarrow
                                anchors.centerIn: parent
                                text: modelData.title
                                font.pixelSize: 11
                                font.bold: true
                                color: "white"
                                elide: Text.ElideRight
                                width: Math.max(0, parent.width - 10)
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }

                        MouseArea {
                            id: barMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: if (!isFocused) focusCluster(index, clusterBarDelegate.x, clusterBarDelegate.y + 4, clusterBarDelegate.width, barRect.height)
                        }
                    }
                }
            }

            // Scroll indicator (shown when zoomed)
            Rectangle {
                visible: showClusters && !isFocused && timelineZoom > 1.05
                x: 0; y: 0
                width: parent.width; height: 3; radius: 0
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
                property real graphBgY: 0
                property real barsBaseY: miniGraphY  // Where cluster bars container starts
                property color clusterCol: focusedCluster ? clusterColor(focusedCluster.id) : "transparent"
                property color bgCol: util.IS_UI_DARK_MODE ? "#0a0a12" : "#f8f8fc"

                // Animate from bar position to fill the graph area with even margins (left, right, top)
                x: gLeft + heroStartX + (heroMargin - heroStartX) * animProgress
                // Start at bar position (barsBaseY + heroStartY), animate to graphBgY + heroMargin
                y: barsBaseY + heroStartY + (graphBgY + heroMargin - barsBaseY - heroStartY) * animProgress
                width: heroStartW + (gWidth - heroMargin * 2 - heroStartW) * animProgress
                height: heroStartH + (graphAreaBottom - heroMargin - heroStartH) * animProgress
                radius: 4 + 4 * animProgress
                // Start with cluster color, transition to background color
                color: Qt.rgba(
                    clusterCol.r + (bgCol.r - clusterCol.r) * animProgress,
                    clusterCol.g + (bgCol.g - clusterCol.g) * animProgress,
                    clusterCol.b + (bgCol.b - clusterCol.b) * animProgress,
                    1
                )
                border.color: clusterCol
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
                    color: focusedCluster ? clusterColor(focusedCluster.id) : textSecondary
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
                        objectName: "heroCloseButton"
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
                    anchors.bottomMargin: 38
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
                                color: focusedCluster ? clusterColor(focusedCluster.id) : textSecondary
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
                                var relationshipXs = []
                                var baseline = {symptom: 0, anxiety: 0, functioning: 0}
                                var foundBaseline = false

                                for (var i = 0; i < eventIds.length; i++) {
                                    var eventId = eventIds[i]
                                    for (var j = 0; j < events.length; j++) {
                                        if (events[j].id === eventId) {
                                            // For baseline: use cumulative value BEFORE first cluster event
                                            if (!foundBaseline) {
                                                if (j > 0) {
                                                    baseline = {
                                                        symptom: cumulative[j-1].symptom,
                                                        anxiety: cumulative[j-1].anxiety,
                                                        functioning: cumulative[j-1].functioning
                                                    }
                                                }
                                                foundBaseline = true
                                            }

                                            // Store relative values (cumulative minus baseline)
                                            dataPoints.push({
                                                yearFrac: events[j].yearFrac,
                                                symptom: cumulative[j].symptom - baseline.symptom,
                                                anxiety: cumulative[j].anxiety - baseline.anxiety,
                                                functioning: cumulative[j].functioning - baseline.functioning
                                            })
                                            if (events[j].relationship) {
                                                relationshipXs.push(events[j].yearFrac)
                                            }
                                            break
                                        }
                                    }
                                }

                                if (dataPoints.length === 0) return

                                // Draw relationship vertical lines first (behind other lines)
                                if (relationshipXs.length > 0) {
                                    ctx.strokeStyle = relationshipColor.toString()
                                    ctx.lineWidth = 1.5
                                    for (var r = 0; r < relationshipXs.length; r++) {
                                        var rx = zoomableContent.xForYearFrac(relationshipXs[r])
                                        ctx.beginPath()
                                        ctx.moveTo(rx, 0)
                                        ctx.lineTo(rx, height)
                                        ctx.stroke()
                                    }
                                }

                                var colors = [symptomColor.toString(), anxietyColor.toString(), functioningColor.toString()]
                                var keys = ['symptom', 'anxiety', 'functioning']

                                // Check if each variable has any changes within the cluster
                                var hasChanges = [false, false, false]
                                for (var k = 0; k < 3; k++) {
                                    if (dataPoints.length > 1) {
                                        var firstVal = dataPoints[0][keys[k]]
                                        for (var p = 1; p < dataPoints.length; p++) {
                                            if (dataPoints[p][keys[k]] !== firstVal) {
                                                hasChanges[k] = true
                                                break
                                            }
                                        }
                                    }
                                }

                                // Draw lines (thinner/transparent for variables without changes)
                                for (k = 0; k < 3; k++) {
                                    ctx.strokeStyle = colors[k]
                                    ctx.lineWidth = hasChanges[k] ? 2.5 : 1.0
                                    ctx.globalAlpha = hasChanges[k] ? 1.0 : 0.3
                                    ctx.lineCap = "round"
                                    ctx.lineJoin = "round"
                                    ctx.beginPath()

                                    for (p = 0; p < dataPoints.length; p++) {
                                        var x = zoomableContent.xForYearFrac(dataPoints[p].yearFrac)
                                        var y = zoomableContent.yForValue(dataPoints[p][keys[k]])

                                        if (p === 0) {
                                            ctx.moveTo(x, y)
                                        } else {
                                            ctx.lineTo(x, y)
                                        }
                                    }
                                    ctx.stroke()
                                    ctx.globalAlpha = 1.0
                                }

                                // Draw dots at each event position
                                for (k = 0; k < 3; k++) {
                                    if (!hasChanges[k]) continue
                                    ctx.fillStyle = colors[k]
                                    for (p = 0; p < dataPoints.length; p++) {
                                        x = zoomableContent.xForYearFrac(dataPoints[p].yearFrac)
                                        y = zoomableContent.yForValue(dataPoints[p][keys[k]])
                                        ctx.beginPath()
                                        ctx.arc(x, y, 4, 0, Math.PI * 2)
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

                // SARF Legend
                Row {
                    id: heroLegend
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 8
                    spacing: 12
                    opacity: animProgress

                    Row {
                        spacing: 4
                        SymptomSymbol { size: 12; symbolColor: symptomColor; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: "Symptom"; font.pixelSize: 11; font.bold: true; color: symptomColor }
                    }
                    Row {
                        spacing: 4
                        AnxietySymbol { size: 12; symbolColor: anxietyColor; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: "Anxiety"; font.pixelSize: 11; font.bold: true; color: anxietyColor }
                    }
                    Row {
                        spacing: 4
                        RelationshipSymbol { size: 12; symbolColor: relationshipColor; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: "Relationship"; font.pixelSize: 11; font.bold: true; color: relationshipColor }
                    }
                    Row {
                        spacing: 4
                        FunctioningSymbol { size: 12; symbolColor: functioningColor; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: "Functioning"; font.pixelSize: 11; font.bold: true; color: functioningColor }
                    }
                }
            }

            // Graph controls container (fixed position, switches content based on focus)
            Item {
                id: graphControlsContainer
                x: 0
                y: controlsY
                width: parent.width
                height: controlsHeight
                z: 100

                // Navigation arrows for cycling clusters (shown when focused)
                Row {
                    visible: isFocused
                    anchors.centerIn: parent
                    spacing: 16
                    height: parent.height

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
                        color: focusedCluster ? clusterColor(focusedCluster.id) : textPrimary
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

                // Action buttons row (shown when unfocused)
                Row {
                    visible: !isFocused
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12
                    height: 36

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
        }

        // Divider between header and list
        Rectangle {
            x: 0
            y: controlsY + controlsHeight + 6
            width: parent.width
            height: 1
            color: util.IS_UI_DARK_MODE ? "#404050" : "#c0c0c8"
        }

        // Story List
        ListView {
            id: storyList
            objectName: "storyList"
            x: 0; y: controlsY + controlsHeight + 7
            width: parent.width
            height: parent.height - y
            clip: true
            spacing: 0
            boundsBehavior: Flickable.StopAtBounds
            model: sarfGraphModel ? sarfGraphModel.events : []
            header: Item { height: 12 }  // Top margin for first cluster card

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
                property real clusterHeaderHeight: isFirstInCluster ? 84 : 0
                property real eventHeight: selectedEvent === index ? 200 : 110

                Behavior on height { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }

                // Cluster section header (shown when this is first event in a cluster)
                Rectangle {
                    id: clusterHeader
                    visible: delegateRoot.isFirstInCluster
                    width: parent.width - 32
                    height: 76
                    x: 16
                    y: 4
                    radius: 14
                    color: util.IS_UI_DARK_MODE ? "#252535" : "#f0f0f8"
                    border.color: cluster ? clusterColor(cluster.id) : dividerColor
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
                        anchors.right: parent.right
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 12

                        // Expand/collapse indicator
                        Text {
                            id: expandIndicator
                            text: delegateRoot.cluster && collapsedClusters[delegateRoot.cluster.id] ? "\u25B6" : "\u25BC"
                            font.pixelSize: 14
                            color: textSecondary
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Column {
                            width: parent.width - expandIndicator.width - parent.spacing - eventCountText.width - 8
                            spacing: 6

                            Text {
                                text: delegateRoot.cluster ? delegateRoot.cluster.title : ""
                                font.pixelSize: 16
                                font.bold: true
                                color: textPrimary
                                elide: Text.ElideRight
                                width: parent.width
                            }

                            // Date range
                            Text {
                                text: delegateRoot.cluster ? learnView.formatDateRange(delegateRoot.cluster.startDate, delegateRoot.cluster.endDate) : ""
                                font.pixelSize: 13
                                color: textSecondary
                            }
                        }
                    }

                    // Event count (right-aligned)
                    Text {
                        id: eventCountText
                        anchors.right: parent.right
                        anchors.rightMargin: 16
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 12
                        text: delegateRoot.cluster && delegateRoot.cluster.eventIds ? "(" + delegateRoot.cluster.eventIds.length + " events)" : ""
                        font.pixelSize: 13
                        color: textSecondary
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
                    clip: true

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

                        // Expanded content - only shown when selected
                        Item {
                            width: parent.width
                            height: selectedEvent === index ? expandedCol.implicitHeight : 0
                            visible: height > 0
                            clip: true

                            Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

                            Column {
                                id: expandedCol
                                width: parent.width
                                spacing: 6

                                // Relationship info row
                                Row {
                                    visible: delegateRoot.isShift && evt.relationship !== null && evt.relationship !== undefined
                                    spacing: 8
                                    height: 24

                                    // Relationship kind pill
                                    Rectangle {
                                        width: relPillContent.width + 16; height: 24; radius: 12
                                        color: relationshipColor

                                        Row {
                                            id: relPillContent
                                            anchors.centerIn: parent
                                            spacing: 4
                                            RelationshipSymbol { size: 10; symbolColor: "#fff"; anchors.verticalCenter: parent.verticalCenter }
                                            Text {
                                                text: evt.relationship ? evt.relationship.charAt(0).toUpperCase() + evt.relationship.slice(1) : ""
                                                font.pixelSize: 11
                                                color: "#fff"
                                            }
                                        }
                                    }

                                    Text {
                                        visible: evt.relationshipTargets && evt.relationshipTargets.length > 0
                                        text: evt.relationship === "inside" ? "Inside: " + evt.relationshipTargets.join(", ") : "with " + evt.relationshipTargets.join(", ")
                                        font.pixelSize: 13
                                        color: textSecondary
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                Text {
                                    visible: evt.relationshipTriangles && evt.relationshipTriangles.length > 0
                                    text: evt.relationship === "inside" ? "Outside: " + evt.relationshipTriangles.join(", ") : "△ " + evt.relationshipTriangles.join(", ")
                                    font.pixelSize: 13
                                    color: textSecondary
                                }

                                // Notes with wrapping and scroll
                                Flickable {
                                    visible: evt.notes && evt.notes.length > 0
                                    width: parent.width
                                    height: visible ? Math.min(notesContent.implicitHeight, 60) : 0
                                    contentWidth: width
                                    contentHeight: notesContent.implicitHeight
                                    clip: true
                                    flickableDirection: Flickable.VerticalFlick
                                    boundsBehavior: Flickable.StopAtBounds

                                    Text {
                                        id: notesContent
                                        text: evt.notes || ""
                                        font.pixelSize: 14
                                        color: textSecondary
                                        width: parent.width
                                        wrapMode: Text.WordWrap
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

        // Vertical scroll indicator for story list (deductive calculation from model)
        Rectangle {
            id: storyListScrollbar
            property real totalHeight: calculateStoryListHeight()
            property real viewportHeight: storyList.height
            property real maxScroll: Math.max(0, totalHeight - viewportHeight)
            property real scrollRatio: maxScroll > 0 ? Math.max(0, Math.min(1, storyList.contentY / maxScroll)) : 0
            property real thumbSize: Math.max(16, viewportHeight > 0 && totalHeight > 0 ? height * viewportHeight / totalHeight : height)

            visible: totalHeight > viewportHeight
            anchors.right: parent.right
            y: storyList.y
            width: 3
            height: storyList.height
            radius: 0
            color: util.IS_UI_DARK_MODE ? "#1a1a2a" : "#d0d0d8"
            z: 160

            Rectangle {
                y: storyListScrollbar.scrollRatio * (parent.height - height)
                width: parent.width
                height: storyListScrollbar.thumbSize
                radius: parent.radius
                color: util.IS_UI_DARK_MODE ? "#505060" : "#808090"
            }
        }
    }
}
