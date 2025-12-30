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
    property real graphPadding: 20
    property real miniGraphY: 90
    property real miniGraphH: 100
    property real gLeft: graphPadding + 30
    property real gRight: width - graphPadding
    property real gWidth: gRight - gLeft

    background: Rectangle {
        color: bgColor
    }

    function xPos(year) {
        if (!sarfGraphModel) return gLeft
        var yearStart = sarfGraphModel.yearStart
        var yearSpan = sarfGraphModel.yearSpan
        if (yearSpan === 0) yearSpan = 60
        return gLeft + ((year - yearStart) / yearSpan) * gWidth
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

    function ensureItemVisible(idx) {
        var itemTop = idx * 100
        var itemBottom = itemTop + 200
        var viewTop = storyList.contentY
        var viewBottom = viewTop + storyList.height
        if (itemBottom > viewBottom) {
            var newY = itemBottom - storyList.height
            scrollAdjustAnimation.to = Math.max(0, newY)
            scrollAdjustAnimation.start()
        } else if (itemTop < viewTop) {
            scrollAdjustAnimation.to = Math.max(0, itemTop)
            scrollAdjustAnimation.start()
        }
    }

    function scrollToEventThenExpand(idx) {
        if (!sarfGraphModel) return
        var events = sarfGraphModel.events
        if (idx < 0 || idx >= events.length) return
        selectedEvent = -1
        highlightedEvent = idx
        pendingSelection = idx
        var targetY = Math.min(idx * 100, Math.max(0, events.length * 100 - storyList.height))
        scrollAnimation.to = targetY
        scrollAnimation.start()
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
            height: miniGraphY + miniGraphH + 80
            color: cardColor

            Text {
                x: 20; y: 20
                text: "The Story"
                font.pixelSize: 24
                font.weight: Font.Bold
                color: textPrimary
            }

            Text {
                x: 20; y: 48
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

                    var yearStart = sarfGraphModel.yearStart

                    // Draw Symptom line (red)
                    ctx.strokeStyle = symptomColor
                    ctx.lineWidth = 2
                    ctx.lineCap = "round"
                    ctx.lineJoin = "round"
                    ctx.beginPath()
                    ctx.moveTo(xPos(yearStart), yPosMini(0))
                    ctx.lineTo(xPos(cumulative[0].year), yPosMini(0))
                    ctx.lineTo(xPos(cumulative[0].year), yPosMini(cumulative[0].symptom))
                    for (var i = 1; i < cumulative.length; i++) {
                        ctx.lineTo(xPos(cumulative[i].year), yPosMini(cumulative[i-1].symptom))
                        ctx.lineTo(xPos(cumulative[i].year), yPosMini(cumulative[i].symptom))
                    }
                    ctx.lineTo(xPos(sarfGraphModel.yearEnd), yPosMini(cumulative[cumulative.length-1].symptom))
                    ctx.stroke()

                    // Draw Anxiety line (green)
                    ctx.strokeStyle = anxietyColor
                    ctx.beginPath()
                    ctx.moveTo(xPos(yearStart), yPosMini(0))
                    ctx.lineTo(xPos(cumulative[0].year), yPosMini(0))
                    ctx.lineTo(xPos(cumulative[0].year), yPosMini(cumulative[0].anxiety))
                    for (var j = 1; j < cumulative.length; j++) {
                        ctx.lineTo(xPos(cumulative[j].year), yPosMini(cumulative[j-1].anxiety))
                        ctx.lineTo(xPos(cumulative[j].year), yPosMini(cumulative[j].anxiety))
                    }
                    ctx.lineTo(xPos(sarfGraphModel.yearEnd), yPosMini(cumulative[cumulative.length-1].anxiety))
                    ctx.stroke()
                }
            }

            Connections {
                target: sarfGraphModel
                function onChanged() { graphCanvas.requestPaint() }
            }

            // Event dot markers on graph
            Repeater {
                model: sarfGraphModel ? sarfGraphModel.events : []
                Item {
                    x: xPos(modelData.year) - 20
                    y: yPosMini(0) - 20
                    width: 40
                    height: 50
                    z: 100

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
                        text: modelData.year.toString()
                        font.pixelSize: 8
                        color: textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: scrollToEventThenExpand(index)
                    }
                }
            }

            // Legend with symbols
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                y: miniGraphY + miniGraphH + 30
                spacing: 16

                Row {
                    spacing: 4
                    SymptomSymbol { size: 14; symbolColor: symptomColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Symptom"; font.pixelSize: 10; color: textSecondary }
                }
                Row {
                    spacing: 4
                    AnxietySymbol { size: 14; symbolColor: anxietyColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Anxiety"; font.pixelSize: 10; color: textSecondary }
                }
                Row {
                    spacing: 4
                    RelationshipSymbol { size: 14; symbolColor: relationshipColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Relation"; font.pixelSize: 10; color: textSecondary }
                }
                Row {
                    spacing: 4
                    FunctioningSymbol { size: 14; symbolColor: functioningColor; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Function"; font.pixelSize: 10; color: textSecondary }
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
                height: selectedEvent === index ? 140 : 100
                clip: true

                property var evt: modelData
                property bool isShift: evt.kind === "shift"
                property bool isDeathEvent: evt.kind === "death"
                property bool isLife: isLifeEvent(evt.kind)
                property real swipeX: 0
                property real actionWidth: 75

                Behavior on height { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }

                // Edit action (revealed on swipe right)
                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
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
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
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
                    x: delegateRoot.swipeX
                    width: parent.width
                    height: parent.height
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
