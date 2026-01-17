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
    property var collapsedVignettes: ({})  // vignetteId -> true if collapsed
    property int focusedVignetteIndex: -1  // Index of vignette being focused in graph

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

    // Focused vignette state for graph zooming
    property var focusedVignette: focusedVignetteIndex >= 0 && vignetteModel && vignetteModel.vignettes.length > focusedVignetteIndex ? vignetteModel.vignettes[focusedVignetteIndex] : null
    property bool isFocused: focusedVignetteIndex >= 0
    // Compute actual min/max yearFrac from events in focused vignette
    property var focusedEventYearFracs: {
        if (!isFocused || !focusedVignette || !focusedVignette.eventIds || !sarfGraphModel) return []
        var events = sarfGraphModel.events
        var fracs = []
        for (var i = 0; i < focusedVignette.eventIds.length; i++) {
            var eventId = focusedVignette.eventIds[i]
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

    background: Rectangle {
        color: bgColor
    }

    function xPos(year) {
        if (!sarfGraphModel) return gLeft
        var yearStart = isFocused ? focusedMinYearFrac : sarfGraphModel.yearStart
        var yearSpan = isFocused ? focusedYearSpan : sarfGraphModel.yearSpan
        if (yearSpan === 0) yearSpan = 60
        return gLeft + ((year - yearStart) / yearSpan) * gWidth
    }

    function focusVignette(idx) {
        if (!vignetteModel || !vignetteModel.vignettes || idx < 0 || idx >= vignetteModel.vignettes.length) {
            focusedVignetteIndex = -1
            return
        }
        focusedVignetteIndex = idx
        var vignette = vignetteModel.vignettes[idx]
        if (vignette && vignette.id) {
            vignetteModel.selectVignette(vignette.id)
            // Scroll to first event in this vignette
            if (vignette.eventIds && vignette.eventIds.length > 0 && sarfGraphModel) {
                var events = sarfGraphModel.events
                for (var i = 0; i < events.length; i++) {
                    if (events[i].id === vignette.eventIds[0]) {
                        highlightedEvent = i
                        storyList.positionViewAtIndex(i, ListView.Beginning)
                        break
                    }
                }
            }
        }
    }

    function focusNextVignette() {
        if (!vignetteModel || !vignetteModel.vignettes || vignetteModel.vignettes.length === 0) return
        var nextIdx = focusedVignetteIndex + 1
        if (nextIdx >= vignetteModel.vignettes.length) nextIdx = 0
        focusVignette(nextIdx)
    }

    function focusPrevVignette() {
        if (!vignetteModel || !vignetteModel.vignettes || vignetteModel.vignettes.length === 0) return
        var prevIdx = focusedVignetteIndex - 1
        if (prevIdx < 0) prevIdx = vignetteModel.vignettes.length - 1
        focusVignette(prevIdx)
    }

    function clearFocus() {
        focusedVignetteIndex = -1
        if (vignetteModel) vignetteModel.selectVignette("")
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

    function vignetteForEventIndex(idx) {
        if (!vignetteModel || !vignetteModel.hasVignettes) return null
        if (!sarfGraphModel) return null
        var events = sarfGraphModel.events
        if (idx < 0 || idx >= events.length) return null
        var eventId = events[idx].id
        var vignetteId = vignetteModel.vignetteForEvent(eventId)
        if (!vignetteId) return null
        return vignetteModel.vignetteById(vignetteId)
    }

    function isFirstEventInVignette(idx) {
        var vignette = vignetteForEventIndex(idx)
        if (!vignette || !vignette.eventIds || vignette.eventIds.length === 0) return false
        var events = sarfGraphModel.events
        if (idx < 0 || idx >= events.length) return false
        return vignette.eventIds[0] === events[idx].id
    }

    function isEventVignetteCollapsed(idx) {
        var vignette = vignetteForEventIndex(idx)
        if (!vignette) return false
        return collapsedVignettes[vignette.id] === true
    }

    function toggleVignetteCollapsed(vignetteId) {
        var newCollapsed = {}
        for (var key in collapsedVignettes) {
            newCollapsed[key] = collapsedVignettes[key]
        }
        newCollapsed[vignetteId] = !newCollapsed[vignetteId]
        collapsedVignettes = newCollapsed
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
                text: sarfGraphModel ? (sarfGraphModel.yearStart + " - " + sarfGraphModel.yearEnd) : ""
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

            // Vignette region shading (only shown in non-focused mode, or for the focused vignette)
            Repeater {
                model: vignetteModel ? vignetteModel.vignettes : []

                Rectangle {
                    property var startYear: dateToYear(modelData.startDate)
                    property var endYear: dateToYear(modelData.endDate)
                    property bool isSelected: vignetteModel && vignetteModel.selectedVignetteId === modelData.id
                    property bool isCollapsed: collapsedVignettes[modelData.id] === true
                    property bool isFocusedVignette: focusedVignetteIndex === index

                    visible: (startYear !== null && endYear !== null) && (!isFocused || isFocusedVignette)
                    x: startYear !== null ? xPos(startYear) - 4 : 0
                    y: miniGraphY - 6
                    width: (startYear !== null && endYear !== null) ? Math.max(12, xPos(endYear) - xPos(startYear) + 8) : 12
                    height: miniGraphH + 12
                    radius: 6
                    color: patternColor(modelData.pattern)
                    opacity: isFocusedVignette ? 0.35 : (isSelected ? 0.25 : (isCollapsed ? 0.08 : 0.12))
                    border.color: patternColor(modelData.pattern)
                    border.width: (isSelected || isFocusedVignette) ? 2 : 0

                    Behavior on opacity { NumberAnimation { duration: 200 } }
                    Behavior on x { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                    Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (isFocused && isFocusedVignette) {
                                // Already focused, unfocus
                                clearFocus()
                            } else {
                                focusVignette(index)
                            }
                        }
                    }

                    // Vignette label on selection (hidden when focused - nav shows vignette info)
                    Rectangle {
                        visible: parent.isSelected && !isFocused
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: parent.height + 4
                        width: vignetteLabel.width + 8
                        height: 16
                        radius: 8
                        color: patternColor(modelData.pattern)
                        z: 200

                        Text {
                            id: vignetteLabel
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
                    if (cumulative.length === 0) return

                    // Use focused range when in focused mode
                    var drawYearStart = isFocused ? focusedMinYearFrac : sarfGraphModel.yearStart
                    var drawYearEnd = isFocused ? focusedMaxYearFrac : sarfGraphModel.yearEnd

                    // Filter cumulative data to focused range and find boundary values
                    var filteredData = []
                    var prevSymptom = 0
                    var prevAnxiety = 0
                    var prevFunctioning = 0
                    for (var k = 0; k < cumulative.length; k++) {
                        var yf = cumulative[k].yearFrac !== undefined ? cumulative[k].yearFrac : cumulative[k].year
                        if (yf < drawYearStart) {
                            prevSymptom = cumulative[k].symptom
                            prevAnxiety = cumulative[k].anxiety
                            prevFunctioning = cumulative[k].functioning
                        } else if (yf <= drawYearEnd) {
                            filteredData.push(cumulative[k])
                        }
                    }

                    // Helper to get yearFrac from data point
                    function getYearFrac(d) {
                        return d.yearFrac !== undefined ? d.yearFrac : d.year
                    }

                    // Draw Relationship vertical lines (blue) - draw first so they're behind other lines
                    ctx.strokeStyle = relationshipColor
                    ctx.lineWidth = 2
                    ctx.globalAlpha = 0.5
                    for (var r = 0; r < filteredData.length; r++) {
                        if (filteredData[r].relationship) {
                            var rx = xPos(getYearFrac(filteredData[r]))
                            ctx.beginPath()
                            ctx.moveTo(rx, miniGraphY)
                            ctx.lineTo(rx, miniGraphY + miniGraphH)
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
                    ctx.moveTo(xPos(drawYearStart), yPosMini(prevFunctioning))
                    if (filteredData.length > 0) {
                        ctx.lineTo(xPos(getYearFrac(filteredData[0])), yPosMini(prevFunctioning))
                        ctx.lineTo(xPos(getYearFrac(filteredData[0])), yPosMini(filteredData[0].functioning))
                        for (var f = 1; f < filteredData.length; f++) {
                            ctx.lineTo(xPos(getYearFrac(filteredData[f])), yPosMini(filteredData[f-1].functioning))
                            ctx.lineTo(xPos(getYearFrac(filteredData[f])), yPosMini(filteredData[f].functioning))
                        }
                        ctx.lineTo(xPos(drawYearEnd), yPosMini(filteredData[filteredData.length-1].functioning))
                    } else {
                        ctx.lineTo(xPos(drawYearEnd), yPosMini(prevFunctioning))
                    }
                    ctx.stroke()

                    // Draw Symptom line (red)
                    ctx.strokeStyle = symptomColor
                    ctx.lineWidth = 2
                    ctx.beginPath()
                    ctx.moveTo(xPos(drawYearStart), yPosMini(prevSymptom))
                    if (filteredData.length > 0) {
                        ctx.lineTo(xPos(getYearFrac(filteredData[0])), yPosMini(prevSymptom))
                        ctx.lineTo(xPos(getYearFrac(filteredData[0])), yPosMini(filteredData[0].symptom))
                        for (var i = 1; i < filteredData.length; i++) {
                            ctx.lineTo(xPos(getYearFrac(filteredData[i])), yPosMini(filteredData[i-1].symptom))
                            ctx.lineTo(xPos(getYearFrac(filteredData[i])), yPosMini(filteredData[i].symptom))
                        }
                        ctx.lineTo(xPos(drawYearEnd), yPosMini(filteredData[filteredData.length-1].symptom))
                    } else {
                        ctx.lineTo(xPos(drawYearEnd), yPosMini(prevSymptom))
                    }
                    ctx.stroke()

                    // Draw Anxiety line (green)
                    ctx.strokeStyle = anxietyColor
                    ctx.beginPath()
                    ctx.moveTo(xPos(drawYearStart), yPosMini(prevAnxiety))
                    if (filteredData.length > 0) {
                        ctx.lineTo(xPos(getYearFrac(filteredData[0])), yPosMini(prevAnxiety))
                        ctx.lineTo(xPos(getYearFrac(filteredData[0])), yPosMini(filteredData[0].anxiety))
                        for (var j = 1; j < filteredData.length; j++) {
                            ctx.lineTo(xPos(getYearFrac(filteredData[j])), yPosMini(filteredData[j-1].anxiety))
                            ctx.lineTo(xPos(getYearFrac(filteredData[j])), yPosMini(filteredData[j].anxiety))
                        }
                        ctx.lineTo(xPos(drawYearEnd), yPosMini(filteredData[filteredData.length-1].anxiety))
                    } else {
                        ctx.lineTo(xPos(drawYearEnd), yPosMini(prevAnxiety))
                    }
                    ctx.stroke()
                }
            }

            Connections {
                target: sarfGraphModel
                function onChanged() { graphCanvas.requestPaint() }
            }

            Connections {
                target: vignetteModel
                function onChanged() { graphCanvas.requestPaint() }
            }

            Connections {
                target: root
                function onFocusedVignetteIndexChanged() { graphCanvas.requestPaint() }
            }

            // Event dot markers on graph (only shown if not focused, or event is in focused vignette)
            Repeater {
                model: sarfGraphModel ? sarfGraphModel.events : []
                Item {
                    property bool isInFocusedVignette: {
                        if (!isFocused || !focusedVignette || !focusedVignette.eventIds) return true
                        return focusedVignette.eventIds.indexOf(modelData.id) >= 0
                    }
                    // In focused mode, spread events evenly by index
                    property int indexInVignette: {
                        if (!isFocused || !focusedVignette || !focusedVignette.eventIds) return -1
                        return focusedVignette.eventIds.indexOf(modelData.id)
                    }
                    property int vignetteEventCount: focusedVignette && focusedVignette.eventIds ? focusedVignette.eventIds.length : 1
                    property real focusedX: {
                        if (!isFocused || indexInVignette < 0) return xPos(modelData.year)
                        // Spread evenly: first event at left, last at right
                        var edgePad = 25
                        var usableWidth = gWidth - edgePad * 2
                        if (vignetteEventCount <= 1) return gLeft + gWidth / 2
                        var pos = indexInVignette / (vignetteEventCount - 1)
                        return gLeft + edgePad + pos * usableWidth
                    }

                    visible: isInFocusedVignette
                    x: isFocused ? focusedX - 20 : xPos(modelData.year) - 20
                    y: yPosMini(0) - 20
                    width: 40
                    height: 50
                    z: 100 + indexInVignette  // Stack order by index

                    Behavior on x { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 16
                        width: 8; height: 8; radius: 4
                        color: highlightedEvent === index ? textPrimary : primaryColorForEvent(modelData)
                        scale: highlightedEvent === index ? 1.5 : 1
                        Behavior on scale { NumberAnimation { duration: 150 } }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 28
                        text: isFocused ? modelData.date : modelData.year.toString()
                        font.pixelSize: isFocused ? 7 : 8
                        color: textSecondary
                        rotation: isFocused ? -45 : 0
                        transformOrigin: Item.Top
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            // Find and focus the vignette containing this event
                            if (vignetteModel && vignetteModel.hasVignettes) {
                                var vignetteId = vignetteModel.vignetteForEvent(modelData.id)
                                if (vignetteId) {
                                    for (var i = 0; i < vignetteModel.vignettes.length; i++) {
                                        if (vignetteModel.vignettes[i].id === vignetteId) {
                                            focusVignette(i)
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

            // Navigation arrows for cycling vignettes (shown when focused)
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
                        onClicked: focusPrevVignette()
                    }
                }

                // Current vignette title and count
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 0

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: focusedVignette ? focusedVignette.title : ""
                        font.pixelSize: 10
                        font.bold: true
                        color: focusedVignette ? patternColor(focusedVignette.pattern) : textPrimary
                        elide: Text.ElideRight
                        width: Math.min(implicitWidth, 180)
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: (focusedVignetteIndex + 1) + " / " + (vignetteModel ? vignetteModel.count : 0)
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
                        onClicked: focusNextVignette()
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

            // Action buttons row (hidden when focused on a vignette)
            Row {
                visible: !isFocused
                anchors.right: parent.right
                anchors.rightMargin: 8
                y: miniGraphY + miniGraphH + 8
                spacing: 8

                // Collapse/Expand all button (only shown when vignettes exist)
                Rectangle {
                    visible: vignetteModel && vignetteModel.hasVignettes
                    width: collapseText.width + 12
                    height: 24
                    radius: 12
                    color: util.IS_UI_DARK_MODE ? "#333340" : "#e0e0e8"

                    Text {
                        id: collapseText
                        anchors.centerIn: parent
                        text: {
                            var allCollapsed = true
                            if (vignetteModel && vignetteModel.vignettes) {
                                for (var i = 0; i < vignetteModel.vignettes.length; i++) {
                                    if (!collapsedVignettes[vignetteModel.vignettes[i].id]) {
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
                            if (!vignetteModel || !vignetteModel.vignettes) return
                            var allCollapsed = true
                            for (var i = 0; i < vignetteModel.vignettes.length; i++) {
                                if (!collapsedVignettes[vignetteModel.vignettes[i].id]) {
                                    allCollapsed = false
                                    break
                                }
                            }
                            var newCollapsed = {}
                            for (var j = 0; j < vignetteModel.vignettes.length; j++) {
                                newCollapsed[vignetteModel.vignettes[j].id] = !allCollapsed
                            }
                            collapsedVignettes = newCollapsed
                        }
                    }
                }

                // Vignette count
                Text {
                    visible: vignetteModel && vignetteModel.hasVignettes
                    text: vignetteModel ? vignetteModel.count + " episodes" : ""
                    font.pixelSize: 10
                    color: textSecondary
                    anchors.verticalCenter: parent.verticalCenter
                }

                // Detect Episodes button
                Rectangle {
                    width: detectRow.width + 12
                    height: 24
                    radius: 12
                    color: vignetteModel && vignetteModel.detecting ? textSecondary : util.QML_HIGHLIGHT_COLOR
                    opacity: vignetteModel && vignetteModel.detecting ? 0.6 : 0.9

                    Row {
                        id: detectRow
                        anchors.centerIn: parent
                        spacing: 4

                        Text {
                            text: vignetteModel && vignetteModel.detecting ? "..." : (vignetteModel && vignetteModel.hasVignettes ? "Re-detect" : "Find Episodes")
                            font.pixelSize: 10
                            font.bold: true
                            color: "white"
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: vignetteModel && !vignetteModel.detecting
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: {
                            if (vignetteModel) {
                                vignetteModel.detect()
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
                height: hideCompletely ? 0 : (vignetteHeaderHeight + (showEventContent ? eventHeight : 0))
                clip: true
                visible: !hideCompletely

                property var evt: modelData
                property bool isShift: evt.kind === "shift"
                property bool isDeathEvent: evt.kind === "death"
                property bool isLife: isLifeEvent(evt.kind)
                property real swipeX: 0
                property real actionWidth: 75

                // Vignette grouping properties
                property var vignette: vignetteForEventIndex(index)
                property bool isFirstInVignette: isFirstEventInVignette(index)
                property bool isVignetteCollapsed: vignette && isEventVignetteCollapsed(index)
                property bool hideCompletely: isVignetteCollapsed && !isFirstInVignette
                property bool showEventContent: !isVignetteCollapsed || !vignette
                property real vignetteHeaderHeight: isFirstInVignette ? 72 : 0
                property real eventHeight: selectedEvent === index ? 140 : 100

                Behavior on height { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }

                // Vignette section header (shown when this is first event in a vignette)
                Rectangle {
                    id: vignetteHeader
                    visible: delegateRoot.isFirstInVignette
                    width: parent.width - 24
                    height: 64
                    x: 12
                    y: 4
                    radius: 12
                    color: util.IS_UI_DARK_MODE ? "#252535" : "#f0f0f8"
                    border.color: vignette ? patternColor(vignette.pattern) : dividerColor
                    border.width: 1

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (delegateRoot.vignette) {
                                toggleVignetteCollapsed(delegateRoot.vignette.id)
                                // Also focus/select this vignette in the graph
                                if (vignetteModel && vignetteModel.vignettes) {
                                    for (var i = 0; i < vignetteModel.vignettes.length; i++) {
                                        if (vignetteModel.vignettes[i].id === delegateRoot.vignette.id) {
                                            focusVignette(i)
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
                            text: delegateRoot.vignette && collapsedVignettes[delegateRoot.vignette.id] ? "\u25B6" : "\u25BC"
                            font.pixelSize: 10
                            color: textSecondary
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Column {
                            spacing: 4

                            Row {
                                spacing: 8

                                Text {
                                    text: delegateRoot.vignette ? delegateRoot.vignette.title : ""
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: textPrimary
                                }

                                // Dominant variable badge
                                Rectangle {
                                    visible: delegateRoot.vignette && delegateRoot.vignette.dominantVariable !== undefined && delegateRoot.vignette.dominantVariable !== null && delegateRoot.vignette.dominantVariable !== ""
                                    width: 20
                                    height: 20
                                    radius: 10
                                    color: delegateRoot.vignette ? dominantVariableColor(delegateRoot.vignette.dominantVariable) : textSecondary
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        anchors.centerIn: parent
                                        text: delegateRoot.vignette ? delegateRoot.vignette.dominantVariable : ""
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
                                        if (!delegateRoot.vignette) return ""
                                        var start = delegateRoot.vignette.startDate || ""
                                        var end = delegateRoot.vignette.endDate || ""
                                        if (start === end) return start
                                        return start + " - " + end
                                    }
                                    font.pixelSize: 10
                                    color: textSecondary
                                }

                                // Pattern badge
                                Rectangle {
                                    visible: delegateRoot.vignette && delegateRoot.vignette.pattern !== undefined && delegateRoot.vignette.pattern !== null && delegateRoot.vignette.pattern !== ""
                                    width: patternLabelText.width + 10
                                    height: 16
                                    radius: 8
                                    color: delegateRoot.vignette ? patternColor(delegateRoot.vignette.pattern) : textSecondary
                                    opacity: 0.85

                                    Text {
                                        id: patternLabelText
                                        anchors.centerIn: parent
                                        text: delegateRoot.vignette ? patternLabel(delegateRoot.vignette.pattern) : ""
                                        font.pixelSize: 9
                                        font.bold: true
                                        color: "white"
                                    }
                                }

                                // Event count
                                Text {
                                    text: delegateRoot.vignette && delegateRoot.vignette.eventIds ? delegateRoot.vignette.eventIds.length + " events" : ""
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
                    y: delegateRoot.vignetteHeaderHeight
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
                    y: delegateRoot.vignetteHeaderHeight
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
                    y: delegateRoot.vignetteHeaderHeight
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
