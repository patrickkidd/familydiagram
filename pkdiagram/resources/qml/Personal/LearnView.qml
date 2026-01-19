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
    property real graphPadding: 8
    property real miniGraphY: 20
    property real miniGraphH: 130
    property real gLeft: graphPadding + 24
    property real gRight: width - graphPadding
    property real gWidth: gRight - gLeft

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
        return minVal - 0.5  // Add padding
    }
    property real clusterMaxYearFrac: {
        var fracs = clusterEventYearFracs
        if (!fracs || fracs.length === 0) return sarfGraphModel ? sarfGraphModel.yearEnd : 2025
        var maxVal = fracs[0]
        for (var i = 1; i < fracs.length; i++) {
            if (fracs[i] > maxVal) maxVal = fracs[i]
        }
        return maxVal + 0.5  // Add padding
    }
    property real clusterYearSpan: Math.max(1, clusterMaxYearFrac - clusterMinYearFrac)

    background: Rectangle {
        color: bgColor
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

    function focusCluster(idx) {
        if (!clusterModel || !clusterModel.clusters || idx < 0 || idx >= clusterModel.clusters.length) {
            focusedClusterIndex = -1
            return
        }
        focusedClusterIndex = idx
        var cluster = clusterModel.clusters[idx]
        if (cluster && cluster.id) {
            clusterModel.selectCluster(cluster.id)
            // Scroll to first event in this cluster
            if (cluster.eventIds && cluster.eventIds.length > 0 && sarfGraphModel) {
                var events = sarfGraphModel.events
                for (var i = 0; i < events.length; i++) {
                    if (events[i].id === cluster.eventIds[0]) {
                        highlightedEvent = i
                        storyList.positionViewAtIndex(i, ListView.Beginning)
                        break
                    }
                }
            }
        }
    }

    function focusNextCluster() {
        if (!clusterModel || !clusterModel.clusters || clusterModel.clusters.length === 0) return
        var nextIdx = focusedClusterIndex + 1
        if (nextIdx >= clusterModel.clusters.length) nextIdx = 0
        focusCluster(nextIdx)
    }

    function focusPrevCluster() {
        if (!clusterModel || !clusterModel.clusters || clusterModel.clusters.length === 0) return
        var prevIdx = focusedClusterIndex - 1
        if (prevIdx < 0) prevIdx = clusterModel.clusters.length - 1
        focusCluster(prevIdx)
    }

    function clearFocus() {
        focusedClusterIndex = -1
        if (clusterModel) clusterModel.selectCluster("")
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
            height: miniGraphY + miniGraphH + 45
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
                x: graphPadding
                y: miniGraphY - 10
                width: parent.width - graphPadding * 2
                height: miniGraphH + 35
                radius: 10
                color: util.IS_UI_DARK_MODE ? "#151520" : "#f5f5fa"
            }

            // Cluster region shading (only shown when focused on a specific cluster)
            Repeater {
                model: showClusters && clusterModel ? clusterModel.clusters : []

                Rectangle {
                    property var startYear: dateToYear(modelData.startDate)
                    property var endYear: dateToYear(modelData.endDate)
                    property bool isSelected: clusterModel && clusterModel.selectedClusterId === modelData.id
                    property bool isCollapsed: collapsedClusters[modelData.id] === true
                    property bool isFocusedCluster: focusedClusterIndex === index

                    // Only show shading when focused on this specific cluster (not in overview mode)
                    visible: isFocused && isFocusedCluster && (startYear !== null && endYear !== null)
                    x: startYear !== null ? xPos(startYear) - 4 : 0
                    y: miniGraphY - 6
                    width: (startYear !== null && endYear !== null) ? Math.max(12, xPos(endYear) - xPos(startYear) + 8) : 12
                    height: miniGraphH + 12
                    radius: 6
                    color: patternColor(modelData.pattern)
                    opacity: isFocusedCluster ? 0.35 : (isSelected ? 0.25 : (isCollapsed ? 0.08 : 0.12))
                    border.color: patternColor(modelData.pattern)
                    border.width: (isSelected || isFocusedCluster) ? 2 : 0

                    Behavior on opacity { NumberAnimation { duration: 200 } }
                    Behavior on x { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                    Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (isFocused && isFocusedCluster) {
                                // Already focused, unfocus
                                clearFocus()
                            } else {
                                focusCluster(index)
                            }
                        }
                    }

                    // Cluster label on selection (hidden when focused - nav shows cluster info)
                    Rectangle {
                        visible: parent.isSelected && !isFocused
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: parent.height + 4
                        width: clusterLabel.width + 8
                        height: 16
                        radius: 8
                        color: patternColor(modelData.pattern)
                        z: 200

                        Text {
                            id: clusterLabel
                            anchors.centerIn: parent
                            text: modelData.title
                            font.pixelSize: 9
                            font.bold: true
                            color: "white"
                        }
                    }
                }
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

                    var cumulative = sarfGraphModel.cumulative
                    var events = sarfGraphModel.events
                    if (cumulative.length === 0) return
    
                    // In focused mode, use index-based positioning matching event dots
                    if (isFocused && focusedCluster && focusedCluster.eventIds) {
                        var eventIds = focusedCluster.eventIds
                        var eventCount = eventIds.length
                        if (eventCount === 0) return

                        // Build event data with cumulative values and index-based x positions
                        var edgePad = 25
                        var usableWidth = gWidth - edgePad * 2
                        var focusedEvents = []
                        var prevS = 0, prevA = 0, prevF = 0

                        // Find cumulative values before the cluster starts
                        for (var p = 0; p < events.length; p++) {
                            var foundInCluster = false
                            for (var v = 0; v < eventIds.length; v++) {
                                if (events[p].id === eventIds[v]) {
                                    foundInCluster = true
                                    break
                                }
                            }
                            if (foundInCluster) break
                            prevS = cumulative[p].symptom
                            prevA = cumulative[p].anxiety
                            prevF = cumulative[p].functioning
                        }

                        // Build focused event data with x positions
                        for (var vi = 0; vi < eventIds.length; vi++) {
                            var eventId = eventIds[vi]
                            for (var ei = 0; ei < events.length; ei++) {
                                if (events[ei].id === eventId) {
                                    var xFrac = eventCount <= 1 ? 0.5 : vi / (eventCount - 1)
                                    var xVal = gLeft + edgePad + xFrac * usableWidth
                                    focusedEvents.push({
                                        x: xVal,
                                        symptom: cumulative[ei].symptom,
                                        anxiety: cumulative[ei].anxiety,
                                        functioning: cumulative[ei].functioning,
                                        relationship: cumulative[ei].relationship
                                    })
                                    break
                                }
                            }
                        }

                        if (focusedEvents.length === 0) return

                        var xStart = gLeft + edgePad
                        var xEnd = gLeft + edgePad + usableWidth

                        // Draw Relationship vertical lines (blue)
                        ctx.strokeStyle = relationshipColor
                        ctx.lineWidth = 2
                        ctx.globalAlpha = 0.5
                        for (var r = 0; r < focusedEvents.length; r++) {
                            if (focusedEvents[r].relationship) {
                                ctx.beginPath()
                                ctx.moveTo(focusedEvents[r].x, miniGraphY)
                                ctx.lineTo(focusedEvents[r].x, miniGraphY + miniGraphH)
                                ctx.stroke()
                            }
                        }
                        ctx.globalAlpha = 1.0

                        // Draw Functioning line (grey)
                        ctx.strokeStyle = functioningColor
                        ctx.lineWidth = 2
                        ctx.lineCap = "round"
                        ctx.lineJoin = "round"
                        ctx.beginPath()
                        ctx.moveTo(xStart, yPosMini(prevF))
                        ctx.lineTo(focusedEvents[0].x, yPosMini(prevF))
                        ctx.lineTo(focusedEvents[0].x, yPosMini(focusedEvents[0].functioning))
                        for (var f = 1; f < focusedEvents.length; f++) {
                            ctx.lineTo(focusedEvents[f].x, yPosMini(focusedEvents[f-1].functioning))
                            ctx.lineTo(focusedEvents[f].x, yPosMini(focusedEvents[f].functioning))
                        }
                        ctx.lineTo(xEnd, yPosMini(focusedEvents[focusedEvents.length-1].functioning))
                        ctx.stroke()

                        // Draw Symptom line (red)
                        ctx.strokeStyle = symptomColor
                        ctx.beginPath()
                        ctx.moveTo(xStart, yPosMini(prevS))
                        ctx.lineTo(focusedEvents[0].x, yPosMini(prevS))
                        ctx.lineTo(focusedEvents[0].x, yPosMini(focusedEvents[0].symptom))
                        for (var i = 1; i < focusedEvents.length; i++) {
                            ctx.lineTo(focusedEvents[i].x, yPosMini(focusedEvents[i-1].symptom))
                            ctx.lineTo(focusedEvents[i].x, yPosMini(focusedEvents[i].symptom))
                        }
                        ctx.lineTo(xEnd, yPosMini(focusedEvents[focusedEvents.length-1].symptom))
                        ctx.stroke()

                        // Draw Anxiety line (green)
                        ctx.strokeStyle = anxietyColor
                        ctx.beginPath()
                        ctx.moveTo(xStart, yPosMini(prevA))
                        ctx.lineTo(focusedEvents[0].x, yPosMini(prevA))
                        ctx.lineTo(focusedEvents[0].x, yPosMini(focusedEvents[0].anxiety))
                        for (var j = 1; j < focusedEvents.length; j++) {
                            ctx.lineTo(focusedEvents[j].x, yPosMini(focusedEvents[j-1].anxiety))
                            ctx.lineTo(focusedEvents[j].x, yPosMini(focusedEvents[j].anxiety))
                        }
                        ctx.lineTo(xEnd, yPosMini(focusedEvents[focusedEvents.length-1].anxiety))
                        ctx.stroke()

                        return  // Done with focused mode
                    }

                    // Non-focused mode: just show cluster spans, no SARF lines
                    // (SARF lines removed for mobile - cluster rectangles handle this)
                }
            }

            Connections {
                target: sarfGraphModel
                function onChanged() { graphCanvas.requestPaint() }
            }

            Connections {
                target: clusterModel
                function onChanged() { graphCanvas.requestPaint() }
            }

            Connections {
                target: root
                function onFocusedClusterIndexChanged() { graphCanvas.requestPaint() }
            }

            // Event dot markers on graph (filtered by cluster membership when showClusters is ON)
            Repeater {
                model: sarfGraphModel ? sarfGraphModel.events : []
                Item {
                    property bool isInAnyCluster: {
                        if (!clusterModel || !clusterModel.hasClusters) return true
                        return clusterModel.clusterForEvent(modelData.id) !== ""
                    }
                    property bool isInFocusedCluster: {
                        if (!isFocused || !focusedCluster || !focusedCluster.eventIds) return true
                        return focusedCluster.eventIds.indexOf(modelData.id) >= 0
                    }
                    // In focused mode, spread events evenly by index
                    property int indexInCluster: {
                        if (!isFocused || !focusedCluster || !focusedCluster.eventIds) return -1
                        return focusedCluster.eventIds.indexOf(modelData.id)
                    }
                    property int clusterEventCount: focusedCluster && focusedCluster.eventIds ? focusedCluster.eventIds.length : 1
                    // Index among all visible cluster events (for even spacing in non-focused cluster mode)
                    property int globalClusterIndex: {
                        if (!showClusters || !clusterModel || !clusterModel.hasClusters || !isInAnyCluster) return -1
                        var count = 0
                        var events = sarfGraphModel.events
                        for (var i = 0; i < events.length && i < index; i++) {
                            if (clusterModel.clusterForEvent(events[i].id) !== "") count++
                        }
                        return count
                    }
                    property int totalClusterEvents: {
                        if (!showClusters || !clusterModel || !clusterModel.hasClusters) return 1
                        var count = 0
                        var events = sarfGraphModel.events
                        for (var i = 0; i < events.length; i++) {
                            if (clusterModel.clusterForEvent(events[i].id) !== "") count++
                        }
                        return Math.max(1, count)
                    }
                    property real focusedX: {
                        if (!isFocused || indexInCluster < 0) return xPos(modelData.year)
                        // Spread evenly: first event at left, last at right
                        var edgePad = 25
                        var usableWidth = gWidth - edgePad * 2
                        if (clusterEventCount <= 1) return gLeft + gWidth / 2
                        var pos = indexInCluster / (clusterEventCount - 1)
                        return gLeft + edgePad + pos * usableWidth
                    }
                    // Even spacing for non-focused cluster mode
                    property real clusterModeX: {
                        if (!showClusters || globalClusterIndex < 0) return xPos(modelData.yearFrac)
                        var edgePad = 25
                        var usableWidth = gWidth - edgePad * 2
                        if (totalClusterEvents <= 1) return gLeft + gWidth / 2
                        var pos = globalClusterIndex / (totalClusterEvents - 1)
                        return gLeft + edgePad + pos * usableWidth
                    }

                    visible: (showClusters ? isInAnyCluster : true) && isInFocusedCluster
                    x: isFocused ? focusedX - 20 : (showClusters && clusterModel && clusterModel.hasClusters ? clusterModeX - 20 : xPos(modelData.yearFrac) - 20)
                    y: yPosMini(0) - 20
                    width: 40
                    height: 50
                    z: 100 + (isFocused ? indexInCluster : globalClusterIndex)

                    Behavior on x { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 16
                        width: 8; height: 8; radius: 4
                        color: highlightedEvent === index ? textPrimary : primaryColorForEvent(modelData)
                        scale: highlightedEvent === index ? 1.5 : 1
                        Behavior on scale { NumberAnimation { duration: 150 } }
                    }

                    // Only show date labels in focused mode or when highlighted
                    Text {
                        visible: isFocused || highlightedEvent === index
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
                        onClicked: {
                            // Find and focus the cluster containing this event
                            if (clusterModel && clusterModel.hasClusters) {
                                var clusterId = clusterModel.clusterForEvent(modelData.id)
                                if (clusterId) {
                                    for (var i = 0; i < clusterModel.clusters.length; i++) {
                                        if (clusterModel.clusters[i].id === clusterId) {
                                            focusCluster(i)
                                            break
                                        }
                                    }
                                }
                            }
                            scrollToEventThenExpand(index)
                        }
                    }
                }
            }

            // Navigation arrows for cycling clusters (shown when focused)
            Row {
                visible: isFocused
                anchors.horizontalCenter: parent.horizontalCenter
                y: miniGraphY + miniGraphH + 8
                spacing: 8
                z: 100

                // Prev button
                Rectangle {
                    width: 24; height: 24; radius: 12
                    color: util.IS_UI_DARK_MODE ? "#333340" : "#e0e0e8"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "\u25C0"
                        font.pixelSize: 10
                        color: textPrimary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: focusPrevCluster()
                    }
                }

                // Current cluster title and count
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 0

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: focusedCluster ? focusedCluster.title : ""
                        font.pixelSize: 10
                        font.bold: true
                        color: focusedCluster ? patternColor(focusedCluster.pattern) : textPrimary
                        elide: Text.ElideRight
                        width: Math.min(implicitWidth, 180)
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: (focusedClusterIndex + 1) + " / " + (clusterModel ? clusterModel.count : 0)
                        font.pixelSize: 9
                        color: textSecondary
                    }
                }

                // Next button
                Rectangle {
                    width: 24; height: 24; radius: 12
                    color: util.IS_UI_DARK_MODE ? "#333340" : "#e0e0e8"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "\u25B6"
                        font.pixelSize: 10
                        color: textPrimary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: focusNextCluster()
                    }
                }

                // Exit focus button
                Rectangle {
                    width: exitText.width + 12; height: 24; radius: 12
                    color: util.IS_UI_DARK_MODE ? "#444450" : "#d0d0d8"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        id: exitText
                        anchors.centerIn: parent
                        text: "All"
                        font.pixelSize: 9
                        color: textPrimary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: clearFocus()
                    }
                }
            }

            // Legend inside graph (bottom) - centered
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                y: miniGraphY + miniGraphH - 18
                spacing: 10
                z: 50

                Row {
                    spacing: 3
                    SymptomSymbol { size: 12; symbolColor: symptomColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Symptom"; font.pixelSize: 9; font.bold: true; color: symptomColor }
                }
                Row {
                    spacing: 3
                    AnxietySymbol { size: 12; symbolColor: anxietyColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Anxiety"; font.pixelSize: 9; font.bold: true; color: anxietyColor }
                }
                Row {
                    spacing: 3
                    RelationshipSymbol { size: 12; symbolColor: relationshipColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Relationship"; font.pixelSize: 9; font.bold: true; color: relationshipColor }
                }
                Row {
                    spacing: 3
                    FunctioningSymbol { size: 12; symbolColor: functioningColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Functioning"; font.pixelSize: 9; font.bold: true; color: functioningColor }
                }
            }

            // Action buttons row (hidden when focused on a cluster)
            Row {
                visible: !isFocused
                anchors.right: parent.right
                anchors.rightMargin: 8
                y: miniGraphY + miniGraphH + 8
                spacing: 8

                // Show Clusters toggle
                Row {
                    visible: clusterModel && clusterModel.hasClusters
                    spacing: 4
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        width: 32; height: 18; radius: 9
                        color: showClusters ? util.QML_HIGHLIGHT_COLOR : (util.IS_UI_DARK_MODE ? "#444450" : "#c0c0c8")
                        anchors.verticalCenter: parent.verticalCenter

                        Rectangle {
                            width: 14; height: 14; radius: 7
                            color: "white"
                            x: showClusters ? parent.width - width - 2 : 2
                            anchors.verticalCenter: parent.verticalCenter

                            Behavior on x { NumberAnimation { duration: 150 } }
                        }

                        MouseArea {
                            anchors.fill: parent
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
                        font.pixelSize: 10
                        color: textSecondary
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                // Collapse/Expand all button (only shown when clusters exist and enabled)
                Rectangle {
                    visible: showClusters && clusterModel && clusterModel.hasClusters
                    width: collapseText.width + 12
                    height: 24
                    radius: 12
                    color: util.IS_UI_DARK_MODE ? "#333340" : "#e0e0e8"

                    Text {
                        id: collapseText
                        anchors.centerIn: parent
                        text: {
                            var allCollapsed = true
                            if (clusterModel && clusterModel.clusters) {
                                for (var i = 0; i < clusterModel.clusters.length; i++) {
                                    if (!collapsedClusters[clusterModel.clusters[i].id]) {
                                        allCollapsed = false
                                        break
                                    }
                                }
                            }
                            return allCollapsed ? "Expand All" : "Collapse All"
                        }
                        font.pixelSize: 10
                        color: textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (!clusterModel || !clusterModel.clusters) return
                            var allCollapsed = true
                            for (var i = 0; i < clusterModel.clusters.length; i++) {
                                if (!collapsedClusters[clusterModel.clusters[i].id]) {
                                    allCollapsed = false
                                    break
                                }
                            }
                            var newCollapsed = {}
                            for (var j = 0; j < clusterModel.clusters.length; j++) {
                                newCollapsed[clusterModel.clusters[j].id] = !allCollapsed
                            }
                            collapsedClusters = newCollapsed
                        }
                    }
                }

                // Cluster count
                Text {
                    visible: showClusters && clusterModel && clusterModel.hasClusters
                    text: clusterModel ? clusterModel.count + " clusters" : ""
                    font.pixelSize: 10
                    color: textSecondary
                    anchors.verticalCenter: parent.verticalCenter
                }

                // Detect Clusters button
                Rectangle {
                    width: detectRow.width + 12
                    height: 24
                    radius: 12
                    color: clusterModel && clusterModel.detecting ? textSecondary : util.QML_HIGHLIGHT_COLOR
                    opacity: clusterModel && clusterModel.detecting ? 0.6 : 0.9

                    Row {
                        id: detectRow
                        anchors.centerIn: parent
                        spacing: 4

                        Text {
                            text: clusterModel && clusterModel.detecting ? "..." : (clusterModel && clusterModel.hasClusters ? "Re-detect" : "Find Clusters")
                            font.pixelSize: 10
                            font.bold: true
                            color: "white"
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
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
                property real clusterHeaderHeight: isFirstInCluster ? 72 : 0
                property real eventHeight: selectedEvent === index ? 140 : 100

                Behavior on height { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }

                // Cluster section header (shown when this is first event in a cluster)
                Rectangle {
                    id: clusterHeader
                    visible: delegateRoot.isFirstInCluster
                    width: parent.width - 24
                    height: 64
                    x: 12
                    y: 4
                    radius: 12
                    color: util.IS_UI_DARK_MODE ? "#252535" : "#f0f0f8"
                    border.color: cluster ? patternColor(cluster.pattern) : dividerColor
                    border.width: 1

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (delegateRoot.cluster) {
                                toggleClusterCollapsed(delegateRoot.cluster.id)
                                // Also focus/select this cluster in the graph
                                if (clusterModel && clusterModel.clusters) {
                                    for (var i = 0; i < clusterModel.clusters.length; i++) {
                                        if (clusterModel.clusters[i].id === delegateRoot.cluster.id) {
                                            focusCluster(i)
                                            break
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 10

                        // Expand/collapse indicator
                        Text {
                            text: delegateRoot.cluster && collapsedClusters[delegateRoot.cluster.id] ? "\u25B6" : "\u25BC"
                            font.pixelSize: 10
                            color: textSecondary
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Column {
                            spacing: 4

                            Row {
                                spacing: 8

                                Text {
                                    text: delegateRoot.cluster ? delegateRoot.cluster.title : ""
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: textPrimary
                                }

                                // Dominant variable badge
                                Rectangle {
                                    visible: delegateRoot.cluster && delegateRoot.cluster.dominantVariable !== undefined && delegateRoot.cluster.dominantVariable !== null && delegateRoot.cluster.dominantVariable !== ""
                                    width: 20
                                    height: 20
                                    radius: 10
                                    color: delegateRoot.cluster ? dominantVariableColor(delegateRoot.cluster.dominantVariable) : textSecondary
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        anchors.centerIn: parent
                                        text: delegateRoot.cluster ? delegateRoot.cluster.dominantVariable : ""
                                        font.pixelSize: 10
                                        font.bold: true
                                        color: "white"
                                    }
                                }
                            }

                            Row {
                                spacing: 8

                                // Date range
                                Text {
                                    text: {
                                        if (!delegateRoot.cluster) return ""
                                        var start = delegateRoot.cluster.startDate || ""
                                        var end = delegateRoot.cluster.endDate || ""
                                        if (start === end) return start
                                        return start + " - " + end
                                    }
                                    font.pixelSize: 10
                                    color: textSecondary
                                }

                                // Pattern badge
                                Rectangle {
                                    visible: delegateRoot.cluster && delegateRoot.cluster.pattern !== undefined && delegateRoot.cluster.pattern !== null && delegateRoot.cluster.pattern !== ""
                                    width: patternLabelText.width + 10
                                    height: 16
                                    radius: 8
                                    color: delegateRoot.cluster ? patternColor(delegateRoot.cluster.pattern) : textSecondary
                                    opacity: 0.85

                                    Text {
                                        id: patternLabelText
                                        anchors.centerIn: parent
                                        text: delegateRoot.cluster ? patternLabel(delegateRoot.cluster.pattern) : ""
                                        font.pixelSize: 9
                                        font.bold: true
                                        color: "white"
                                    }
                                }

                                // Event count
                                Text {
                                    text: delegateRoot.cluster && delegateRoot.cluster.eventIds ? delegateRoot.cluster.eventIds.length + " events" : ""
                                    font.pixelSize: 10
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
                        font.pixelSize: 15
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
                        font.pixelSize: 15
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
                        x: 70; y: 12
                        width: parent.width - 90
                        spacing: 4

                        // Date and Who on same row
                        Item {
                            width: parent.width
                            height: 18
                            Text {
                                text: evt.date
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                color: primaryColorForEvent(evt)
                            }
                            Text {
                                x: 95
                                text: evt.who
                                font.pixelSize: 12
                                color: textSecondary
                            }
                        }

                        Text {
                            text: evt.description
                            font.pixelSize: 15
                            font.weight: Font.Medium
                            color: textPrimary
                        }

                        // Expanded content
                        Column {
                            visible: selectedEvent === index
                            opacity: selectedEvent === index ? 1 : 0
                            spacing: 4

                            Behavior on opacity { NumberAnimation { duration: 200 } }

                            Text {
                                text: evt.notes || ""
                                font.pixelSize: 12
                                color: textSecondary
                                visible: evt.notes && evt.notes.length > 0
                            }

                            // Relationship pill for Shift events with relationship set
                            Rectangle {
                                visible: delegateRoot.isShift && evt.relationship !== null && evt.relationship !== undefined
                                width: 100; height: 24; radius: 12
                                color: relationshipColor

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 4
                                    RelationshipSymbol { size: 10; symbolColor: "#fff"; anchors.verticalCenter: parent.verticalCenter }
                                    Text {
                                        text: evt.relationship ? evt.relationship.charAt(0).toUpperCase() + evt.relationship.slice(1) : ""
                                        font.pixelSize: 9
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
                        font.pixelSize: 12
                        color: textSecondary
                    }
                }
            }
        }
    }
}
