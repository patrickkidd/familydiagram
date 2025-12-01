// Mobile D: Story/Narrative Design
// Iteration 17: Centered SARF, better spacing, sized shapes
// - SARF symbols centered around timeline, bigger (30px), more separation
// - Birth/Death shapes smaller (26px)
// - Cluster calculation for dynamic centering

import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Shapes 1.15

Window {
    id: root
    visible: true
    width: 390
    height: 750
    title: "Mobile D - Event Kinds"

    property bool darkMode: true
    property int selectedEvent: -1
    property int highlightedEvent: -1
    property int pendingSelection: -1

    // WCAG AA colors
    property color bg: darkMode ? "#0f0f18" : "#f8f8fc"
    property color card: darkMode ? "#1a1a28" : "#ffffff"
    property color text1: darkMode ? "#f0f0f5" : "#1a1a2e"
    property color text2: darkMode ? "#909098" : "#606070"
    property color divider: darkMode ? "#2a2a38" : "#e0e0e8"
    property color highlight: darkMode ? "#2a2a40" : "#f0f0ff"

    property color symptom: "#e05555"
    property color anxiety: "#40a060"
    property color relationship: "#5080d0"
    property color functioning: darkMode ? "#909090" : "#505060"

    color: bg

    // Event kinds matching EventKind enum
    readonly property string kindBirth: "birth"
    readonly property string kindDeath: "death"
    readonly property string kindMarried: "married"
    readonly property string kindSeparated: "separated"
    readonly property string kindDivorced: "divorced"
    readonly property string kindMoved: "moved"
    readonly property string kindBonded: "bonded"
    readonly property string kindAdopted: "adopted"
    readonly property string kindShift: "shift"

    property var events: [
        { year: 1925, date: "Mar 15, 1925", kind: "shift", s: "up", a: null, f: null, r: null, desc: "Pneumonia", who: "Heidi", note: "First significant health event" },
        { year: 1940, date: "Jun 3, 1940", kind: "shift", s: null, a: null, f: null, r: "conflict", desc: "Family rift", who: "Family", note: "Conflict pattern emerges" },
        { year: 1952, date: "Sep 22, 1952", kind: "birth", s: null, a: null, f: null, r: null, desc: "Birth", who: "Child", note: "Family expansion" },
        { year: 1960, date: "Jan 8, 1960", kind: "shift", s: null, a: null, f: null, r: "projection", desc: "Child focus", who: "Parents", note: "Triangulation begins" },
        { year: 1965, date: "Aug 14, 1965", kind: "married", s: null, a: null, f: null, r: null, desc: "Wedding", who: "Couple", note: "Marriage ceremony" },
        { year: 1969, date: "Nov 30, 1969", kind: "shift", s: "up", a: "up", f: null, r: null, desc: "Diagnosis", who: "Person A", note: "Major health crisis" },
        { year: 1970, date: "Feb 17, 1970", kind: "shift", s: null, a: "up", f: null, r: null, desc: "DUI", who: "Person B", note: "Stress response" },
        { year: 1974, date: "Dec 5, 1974", kind: "shift", s: null, a: "up", f: null, r: "distance", desc: "DUI #2", who: "Person B", note: "Pattern continues" },
        { year: 1978, date: "Apr 21, 1978", kind: "death", s: null, a: null, f: null, r: null, desc: "Passed", who: "Elder", note: "End of life" }
    ]

    property var cumulative: {
        var r = [], cs = 0, ca = 0, cf = 0
        for (var i = 0; i < events.length; i++) {
            var e = events[i]
            if (e.s === "up") cs++; else if (e.s === "down") cs--
            if (e.a === "up") ca++; else if (e.a === "down") ca--
            if (e.f === "up") cf++; else if (e.f === "down") cf--
            r.push({ year: e.year, s: cs, a: ca, f: cf, r: e.r })
        }
        return r
    }

    // Graph properties
    property real graphPadding: 20
    property real miniGraphY: 90
    property real miniGraphH: 100
    property real gLeft: graphPadding + 30
    property real gRight: width - graphPadding
    property real gWidth: gRight - gLeft

    function xPos(year) { return gLeft + ((year - 1920) / 60) * gWidth }
    function yPosMini(val) { return miniGraphY + miniGraphH - ((val + 2) / 6) * miniGraphH }

    // Check if event kind is a "life event" (not shift or death)
    function isLifeEvent(kind) {
        return kind === kindBirth || kind === kindMarried || kind === kindSeparated ||
               kind === kindDivorced || kind === kindMoved || kind === kindBonded || kind === kindAdopted
    }

    // Count how many SARF values are set
    function sarfCount(evt) {
        var count = 0
        if (evt.s) count++
        if (evt.a) count++
        if (evt.r) count++
        if (evt.f) count++
        return count
    }

    // Get array of set SARF types
    function sarfTypes(evt) {
        var types = []
        if (evt.s) types.push("s")
        if (evt.a) types.push("a")
        if (evt.r) types.push("r")
        if (evt.f) types.push("f")
        return types
    }

    function primaryColor(evt) {
        if (evt.r) return relationship
        if (evt.s) return symptom
        if (evt.a) return anxiety
        if (evt.f) return functioning
        return text1
    }

    // Timers
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
        if (idx < 0 || idx >= events.length) return
        selectedEvent = -1
        highlightedEvent = idx
        pendingSelection = idx
        var targetY = Math.min(idx * 100, Math.max(0, events.length * 100 - storyList.height))
        scrollAnimation.to = targetY
        scrollAnimation.start()
        expandTimer.restart()
    }

    // ============ SARF Symbol Components ============

    // S: Medical Cross
    component SymptomSymbol: Item {
        property real size: 24
        property color symbolColor: symptom
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

    // A: Lightning Bolt
    component AnxietySymbol: Canvas {
        property real size: 24
        property color symbolColor: anxiety
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

    // R: Chain Links
    component RelationshipSymbol: Item {
        property real size: 24
        property color symbolColor: relationship
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

    // F: Gauge/Meter
    component FunctioningSymbol: Canvas {
        property real size: 24
        property color symbolColor: functioning
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

    // ============ Header with mini graph ============
    Rectangle {
        id: headerCard
        width: parent.width
        height: miniGraphY + miniGraphH + 80
        color: card

        Text {
            x: 20; y: 20
            text: "The Story"
            font.pixelSize: 24
            font.weight: Font.Bold
            color: text1
        }

        Rectangle {
            x: parent.width - 55; y: 18
            width: 40; height: 24; radius: 12
            color: darkMode ? "#333" : "#ccc"
            Rectangle {
                x: darkMode ? 18 : 3; y: 3
                width: 18; height: 18; radius: 9
                color: "#fff"
                Behavior on x { NumberAnimation { duration: 100 } }
            }
            MouseArea { anchors.fill: parent; onClicked: darkMode = !darkMode }
        }

        Text {
            x: 20; y: 48
            text: "1920 — 1980"
            font.pixelSize: 12
            color: text2
        }

        // Graph background
        Rectangle {
            x: graphPadding
            y: miniGraphY - 10
            width: parent.width - graphPadding * 2
            height: miniGraphH + 35
            radius: 10
            color: darkMode ? "#151520" : "#f5f5fa"
        }

        // Baseline
        Rectangle {
            x: gLeft; y: yPosMini(0)
            width: gWidth; height: 1
            color: divider
        }

        // Smooth anti-aliased lines using Canvas
        Canvas {
            id: graphCanvas
            anchors.fill: parent
            antialiasing: true

            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)

                // Draw Symptom line (red)
                ctx.strokeStyle = symptom
                ctx.lineWidth = 2
                ctx.lineCap = "round"
                ctx.lineJoin = "round"
                ctx.beginPath()
                ctx.moveTo(xPos(1920), yPosMini(0))
                ctx.lineTo(xPos(cumulative[0].year), yPosMini(0))
                ctx.lineTo(xPos(cumulative[0].year), yPosMini(cumulative[0].s))
                for (var i = 1; i < cumulative.length; i++) {
                    ctx.lineTo(xPos(cumulative[i].year), yPosMini(cumulative[i-1].s))
                    ctx.lineTo(xPos(cumulative[i].year), yPosMini(cumulative[i].s))
                }
                ctx.lineTo(xPos(1980), yPosMini(cumulative[cumulative.length-1].s))
                ctx.stroke()

                // Draw Anxiety line (green)
                ctx.strokeStyle = anxiety
                ctx.beginPath()
                ctx.moveTo(xPos(1920), yPosMini(0))
                ctx.lineTo(xPos(cumulative[0].year), yPosMini(0))
                ctx.lineTo(xPos(cumulative[0].year), yPosMini(cumulative[0].a))
                for (var j = 1; j < cumulative.length; j++) {
                    ctx.lineTo(xPos(cumulative[j].year), yPosMini(cumulative[j-1].a))
                    ctx.lineTo(xPos(cumulative[j].year), yPosMini(cumulative[j].a))
                }
                ctx.lineTo(xPos(1980), yPosMini(cumulative[cumulative.length-1].a))
                ctx.stroke()
            }

            Component.onCompleted: requestPaint()
        }

        Connections {
            target: root
            function onDarkModeChanged() { graphCanvas.requestPaint() }
        }

        // Event dot markers on graph - simple filled circles
        Repeater {
            model: events
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
                    color: highlightedEvent === index ? text1 : primaryColor(modelData)
                    scale: highlightedEvent === index ? 1.5 : 1
                    Behavior on scale { NumberAnimation { duration: 150 } }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 28
                    text: modelData.year.toString()
                    font.pixelSize: 8
                    color: text2
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: scrollToEventThenExpand(index)
                }
            }
        }

        // Legend with symbols - S-A-R-F order
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            y: miniGraphY + miniGraphH + 30
            spacing: 16

            Row {
                spacing: 4
                SymptomSymbol { size: 14; symbolColor: symptom; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Symptom"; font.pixelSize: 10; color: text2 }
            }
            Row {
                spacing: 4
                AnxietySymbol { size: 14; symbolColor: anxiety; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Anxiety"; font.pixelSize: 10; color: text2 }
            }
            Row {
                spacing: 4
                RelationshipSymbol { size: 14; symbolColor: relationship; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Relation"; font.pixelSize: 10; color: text2 }
            }
            Row {
                spacing: 4
                FunctioningSymbol { size: 14; symbolColor: functioning; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Function"; font.pixelSize: 10; color: text2 }
            }
        }
    }

    // ============ Story List ============
    ListView {
        id: storyList
        x: 0; y: headerCard.height + 5
        width: parent.width
        height: parent.height - headerCard.height - 5
        clip: true
        spacing: 0
        model: events

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

        delegate: Rectangle {
            id: delegateRoot
            width: ListView.view.width
            height: selectedEvent === index ? 200 : 100
            color: selectedEvent === index ? highlight : "transparent"

            property var evt: modelData
            property bool isShift: evt.kind === "shift"
            property bool isDeathEvent: evt.kind === "death"
            property bool isLife: isLifeEvent(evt.kind)

            Behavior on height { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    if (selectedEvent === index) {
                        selectedEvent = -1
                    } else {
                        selectedEvent = index
                        highlightedEvent = index
                        scrollAdjustTimer.restart()
                    }
                }
            }

            // Timeline line
            Rectangle {
                x: 35; y: 0
                width: 2
                height: parent.height
                color: divider
            }

            // Node symbol based on event kind - centered on timeline at x: 35
            Item {
                id: nodeContainer
                x: 8; y: 8
                width: 56; height: 56

                // Life events (birth, married, etc): foreground filled circle - smaller
                Rectangle {
                    visible: delegateRoot.isLife
                    anchors.centerIn: parent
                    width: 26; height: 26; radius: 13
                    color: text2
                }

                // Death: grey box - smaller
                Rectangle {
                    visible: delegateRoot.isDeathEvent
                    anchors.centerIn: parent
                    width: 26; height: 26; radius: 3
                    color: functioning
                }

                // Shift events: stacked SARF symbols - bigger, more spread, centered
                Item {
                    id: sarfStack
                    visible: delegateRoot.isShift
                    anchors.centerIn: parent
                    width: 50; height: 50

                    property real symSize: 30
                    property real staggerX: 8
                    property real staggerY: 10
                    property int symbolCount: (delegateRoot.evt.s ? 1 : 0) + (delegateRoot.evt.a ? 1 : 0) + (delegateRoot.evt.r ? 1 : 0) + (delegateRoot.evt.f ? 1 : 0)
                    property int sIdx: 0
                    property int aIdx: delegateRoot.evt.s ? 1 : 0
                    property int rIdx: aIdx + (delegateRoot.evt.a ? 1 : 0)
                    property int fIdx: rIdx + (delegateRoot.evt.r ? 1 : 0)

                    // Calculate cluster dimensions for centering
                    property real clusterW: (symbolCount - 1) * staggerX + symSize
                    property real clusterH: (symbolCount - 1) * staggerY + symSize
                    property real offsetX: (width - clusterW) / 2
                    property real offsetY: (height - clusterH) / 2

                    SymptomSymbol {
                        visible: delegateRoot.evt.s !== null
                        size: sarfStack.symSize
                        symbolColor: symptom
                        x: sarfStack.offsetX + sarfStack.sIdx * sarfStack.staggerX
                        y: sarfStack.offsetY + sarfStack.sIdx * sarfStack.staggerY
                    }
                    AnxietySymbol {
                        visible: delegateRoot.evt.a !== null
                        size: sarfStack.symSize
                        symbolColor: anxiety
                        x: sarfStack.offsetX + sarfStack.aIdx * sarfStack.staggerX
                        y: sarfStack.offsetY + sarfStack.aIdx * sarfStack.staggerY
                    }
                    RelationshipSymbol {
                        visible: delegateRoot.evt.r !== null
                        size: sarfStack.symSize
                        symbolColor: relationship
                        x: sarfStack.offsetX + sarfStack.rIdx * sarfStack.staggerX
                        y: sarfStack.offsetY + sarfStack.rIdx * sarfStack.staggerY
                    }
                    FunctioningSymbol {
                        visible: delegateRoot.evt.f !== null
                        size: sarfStack.symSize
                        symbolColor: functioning
                        x: sarfStack.offsetX + sarfStack.fIdx * sarfStack.staggerX
                        y: sarfStack.offsetY + sarfStack.fIdx * sarfStack.staggerY
                    }
                }
            }

            // Content
            Column {
                x: 70; y: 12
                width: parent.width - 90
                spacing: 4

                // Date and Who on same row with fixed positions
                Item {
                    width: parent.width
                    height: 18
                    Text {
                        text: evt.date
                        font.pixelSize: 12
                        font.weight: Font.Bold
                        color: primaryColor(evt)
                    }
                    Text {
                        x: 95  // Fixed position for who
                        text: evt.who
                        font.pixelSize: 12
                        color: text2
                    }
                }

                Text {
                    text: evt.desc
                    font.pixelSize: 15
                    font.weight: Font.Medium
                    color: text1
                }

                // Expanded content - compact
                Column {
                    visible: selectedEvent === index
                    opacity: selectedEvent === index ? 1 : 0
                    spacing: 6

                    Behavior on opacity { NumberAnimation { duration: 200 } }

                    Text {
                        text: evt.note
                        font.pixelSize: 12
                        color: text2
                        topPadding: 4
                    }

                    // Relationship pill - ONLY for Shift events with relationship set
                    Rectangle {
                        visible: delegateRoot.isShift && evt.r !== null
                        width: 110; height: 28; radius: 14
                        color: relationship

                        Row {
                            anchors.centerIn: parent
                            spacing: 5
                            RelationshipSymbol { size: 12; symbolColor: "#fff"; anchors.verticalCenter: parent.verticalCenter }
                            Text {
                                text: evt.r ? evt.r.charAt(0).toUpperCase() + evt.r.slice(1) : ""
                                font.pixelSize: 10
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
                color: text2
            }
        }
    }
}
