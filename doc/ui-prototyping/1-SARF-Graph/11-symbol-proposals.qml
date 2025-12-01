// SARF Symbol Proposals
// Shows 5 different symbol sets for S, A, R, F variables
// Based on SARF whitepaper definitions

import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15

Window {
    id: root
    visible: true
    width: 420
    height: 850
    title: "SARF Symbol Proposals"

    property bool darkMode: true
    property color bg: darkMode ? "#0f0f18" : "#f8f8fc"
    property color card: darkMode ? "#1a1a28" : "#ffffff"
    property color text1: darkMode ? "#f0f0f5" : "#1a1a2e"
    property color text2: darkMode ? "#909098" : "#606070"
    property color divider: darkMode ? "#2a2a38" : "#e0e0e8"

    property color symptom: "#e05555"
    property color anxiety: "#40a060"
    property color relationship: "#5080d0"
    property color functioning: darkMode ? "#909090" : "#505060"

    color: bg

    Flickable {
        anchors.fill: parent
        contentHeight: contentColumn.height + 40
        clip: true

        Column {
            id: contentColumn
            width: parent.width
            spacing: 15
            padding: 20

            // Header
            Text {
                text: "SARF Symbol Proposals"
                font.pixelSize: 22
                font.weight: Font.Bold
                color: text1
            }

            Text {
                width: parent.width - 40
                text: "S=Symptom (clinical issues), A=Anxiety (threat response), R=Relationship (interpersonal shifts), F=Functioning (emotion/thinking balance)"
                font.pixelSize: 11
                color: text2
                wrapMode: Text.WordWrap
            }

            // Dark mode toggle
            Rectangle {
                width: 100; height: 30; radius: 8
                color: darkMode ? "#333" : "#ddd"
                Text {
                    anchors.centerIn: parent
                    text: darkMode ? "Dark" : "Light"
                    color: text1
                    font.pixelSize: 12
                }
                MouseArea { anchors.fill: parent; onClicked: darkMode = !darkMode }
            }

            // Proposal A: Medical/Clinical
            Rectangle {
                width: parent.width - 40
                height: 140
                radius: 12
                color: card

                Column {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    Text {
                        text: "A: Medical/Clinical Icons"
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        color: text1
                    }
                    Text {
                        text: "Cross (medical), Lightning (nervous system), Links (connection), Gear (cognition)"
                        font.pixelSize: 10
                        color: text2
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }

                    Row {
                        spacing: 30
                        anchors.horizontalCenter: parent.horizontalCenter

                        // S - Medical Cross
                        Column {
                            spacing: 5
                            Item {
                                width: 32; height: 32
                                Rectangle {
                                    anchors.centerIn: parent
                                    width: 20; height: 6; radius: 1
                                    color: symptom
                                }
                                Rectangle {
                                    anchors.centerIn: parent
                                    width: 6; height: 20; radius: 1
                                    color: symptom
                                }
                            }
                            Text { text: "S"; font.pixelSize: 11; color: symptom; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // A - Lightning bolt
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = anxiety
                                    ctx.beginPath()
                                    ctx.moveTo(18, 4)
                                    ctx.lineTo(10, 16)
                                    ctx.lineTo(15, 16)
                                    ctx.lineTo(12, 28)
                                    ctx.lineTo(22, 14)
                                    ctx.lineTo(17, 14)
                                    ctx.lineTo(18, 4)
                                    ctx.fill()
                                }
                            }
                            Text { text: "A"; font.pixelSize: 11; color: anxiety; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // R - Chain links
                        Column {
                            spacing: 5
                            Item {
                                width: 32; height: 32
                                Rectangle {
                                    x: 4; y: 10
                                    width: 14; height: 12; radius: 6
                                    color: "transparent"
                                    border.color: relationship; border.width: 3
                                }
                                Rectangle {
                                    x: 14; y: 10
                                    width: 14; height: 12; radius: 6
                                    color: "transparent"
                                    border.color: relationship; border.width: 3
                                }
                            }
                            Text { text: "R"; font.pixelSize: 11; color: relationship; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // F - Gear
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = functioning
                                    ctx.beginPath()
                                    ctx.arc(16, 16, 8, 0, Math.PI * 2)
                                    ctx.fill()
                                    // Gear teeth
                                    for (var i = 0; i < 8; i++) {
                                        ctx.save()
                                        ctx.translate(16, 16)
                                        ctx.rotate(i * Math.PI / 4)
                                        ctx.fillRect(-2, -12, 4, 5)
                                        ctx.restore()
                                    }
                                    // Inner hole
                                    ctx.fillStyle = card
                                    ctx.beginPath()
                                    ctx.arc(16, 16, 3, 0, Math.PI * 2)
                                    ctx.fill()
                                }
                            }
                            Text { text: "F"; font.pixelSize: 11; color: functioning; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }
                }
            }

            // Proposal B: Geometric Shapes
            Rectangle {
                width: parent.width - 40
                height: 140
                radius: 12
                color: card

                Column {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    Text {
                        text: "B: Geometric Shapes"
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        color: text1
                    }
                    Text {
                        text: "Circle (symptom), Triangle (anxiety/activation), Diamond (relationship), Square (stability)"
                        font.pixelSize: 10
                        color: text2
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }

                    Row {
                        spacing: 30
                        anchors.horizontalCenter: parent.horizontalCenter

                        // S - Circle
                        Column {
                            spacing: 5
                            Rectangle {
                                width: 24; height: 24; radius: 12
                                color: symptom
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text { text: "S"; font.pixelSize: 11; color: symptom; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // A - Triangle
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 28
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = anxiety
                                    ctx.beginPath()
                                    ctx.moveTo(16, 2)
                                    ctx.lineTo(28, 26)
                                    ctx.lineTo(4, 26)
                                    ctx.closePath()
                                    ctx.fill()
                                }
                            }
                            Text { text: "A"; font.pixelSize: 11; color: anxiety; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // R - Diamond
                        Column {
                            spacing: 5
                            Rectangle {
                                width: 20; height: 20
                                color: relationship
                                rotation: 45
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text { text: "R"; font.pixelSize: 11; color: relationship; anchors.horizontalCenter: parent.horizontalCenter; topPadding: 4 }
                        }

                        // F - Square
                        Column {
                            spacing: 5
                            Rectangle {
                                width: 22; height: 22; radius: 3
                                color: functioning
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text { text: "F"; font.pixelSize: 11; color: functioning; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }
                }
            }

            // Proposal C: Letter-Based
            Rectangle {
                width: parent.width - 40
                height: 140
                radius: 12
                color: card

                Column {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    Text {
                        text: "C: Letter Labels"
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        color: text1
                    }
                    Text {
                        text: "Direct S/A/R/F letters in colored circles - educational, unambiguous"
                        font.pixelSize: 10
                        color: text2
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }

                    Row {
                        spacing: 30
                        anchors.horizontalCenter: parent.horizontalCenter

                        Repeater {
                            model: [
                                { letter: "S", c: symptom },
                                { letter: "A", c: anxiety },
                                { letter: "R", c: relationship },
                                { letter: "F", c: functioning }
                            ]
                            Column {
                                spacing: 5
                                Rectangle {
                                    width: 28; height: 28; radius: 14
                                    color: modelData.c
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.letter
                                        font.pixelSize: 14
                                        font.weight: Font.Bold
                                        color: "#fff"
                                    }
                                }
                                Text { text: modelData.letter; font.pixelSize: 11; color: modelData.c; anchors.horizontalCenter: parent.horizontalCenter }
                            }
                        }
                    }
                }
            }

            // Proposal D: Organic/Nature
            Rectangle {
                width: parent.width - 40
                height: 140
                radius: 12
                color: card

                Column {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    Text {
                        text: "D: Organic/Nature Metaphors"
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        color: text1
                    }
                    Text {
                        text: "Droplet (manifestation), Flame (activation), Heart (connection), Leaf (growth)"
                        font.pixelSize: 10
                        color: text2
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }

                    Row {
                        spacing: 30
                        anchors.horizontalCenter: parent.horizontalCenter

                        // S - Droplet
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = symptom
                                    ctx.beginPath()
                                    ctx.moveTo(16, 4)
                                    ctx.bezierCurveTo(16, 4, 6, 16, 6, 20)
                                    ctx.bezierCurveTo(6, 26, 10, 28, 16, 28)
                                    ctx.bezierCurveTo(22, 28, 26, 26, 26, 20)
                                    ctx.bezierCurveTo(26, 16, 16, 4, 16, 4)
                                    ctx.fill()
                                }
                            }
                            Text { text: "S"; font.pixelSize: 11; color: symptom; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // A - Flame
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = anxiety
                                    ctx.beginPath()
                                    ctx.moveTo(16, 2)
                                    ctx.bezierCurveTo(16, 2, 24, 12, 24, 20)
                                    ctx.bezierCurveTo(24, 26, 20, 30, 16, 30)
                                    ctx.bezierCurveTo(12, 30, 8, 26, 8, 20)
                                    ctx.bezierCurveTo(8, 12, 16, 2, 16, 2)
                                    ctx.fill()
                                    // Inner flame
                                    ctx.fillStyle = darkMode ? "#60c080" : "#50b070"
                                    ctx.beginPath()
                                    ctx.moveTo(16, 14)
                                    ctx.bezierCurveTo(16, 14, 20, 20, 20, 23)
                                    ctx.bezierCurveTo(20, 27, 18, 28, 16, 28)
                                    ctx.bezierCurveTo(14, 28, 12, 27, 12, 23)
                                    ctx.bezierCurveTo(12, 20, 16, 14, 16, 14)
                                    ctx.fill()
                                }
                            }
                            Text { text: "A"; font.pixelSize: 11; color: anxiety; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // R - Heart
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = relationship
                                    ctx.beginPath()
                                    ctx.moveTo(16, 28)
                                    ctx.bezierCurveTo(4, 18, 4, 8, 10, 6)
                                    ctx.bezierCurveTo(14, 4, 16, 8, 16, 10)
                                    ctx.bezierCurveTo(16, 8, 18, 4, 22, 6)
                                    ctx.bezierCurveTo(28, 8, 28, 18, 16, 28)
                                    ctx.fill()
                                }
                            }
                            Text { text: "R"; font.pixelSize: 11; color: relationship; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // F - Leaf/Tree
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = functioning
                                    ctx.beginPath()
                                    // Leaf shape
                                    ctx.moveTo(16, 4)
                                    ctx.bezierCurveTo(24, 8, 26, 18, 16, 28)
                                    ctx.bezierCurveTo(6, 18, 8, 8, 16, 4)
                                    ctx.fill()
                                    // Stem
                                    ctx.strokeStyle = functioning
                                    ctx.lineWidth = 2
                                    ctx.beginPath()
                                    ctx.moveTo(16, 28)
                                    ctx.lineTo(16, 16)
                                    ctx.stroke()
                                }
                            }
                            Text { text: "F"; font.pixelSize: 11; color: functioning; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }
                }
            }

            // Proposal E: Pipeline-Inspired (R→A→S with F as modifier)
            Rectangle {
                width: parent.width - 40
                height: 160
                radius: 12
                color: card

                Column {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    Text {
                        text: "E: Pipeline-Inspired"
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        color: text1
                    }
                    Text {
                        text: "Arrow shapes showing R→A→S causal flow. F as shield/buffer icon."
                        font.pixelSize: 10
                        color: text2
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }

                    Row {
                        spacing: 20
                        anchors.horizontalCenter: parent.horizontalCenter

                        // R - Starting point (two people)
                        Column {
                            spacing: 5
                            Item {
                                width: 36; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                Rectangle {
                                    x: 4; y: 8
                                    width: 12; height: 12; radius: 6
                                    color: relationship
                                }
                                Rectangle {
                                    x: 20; y: 8
                                    width: 12; height: 12; radius: 6
                                    color: relationship
                                }
                                Rectangle {
                                    x: 14; y: 13
                                    width: 8; height: 3
                                    color: relationship
                                }
                            }
                            Text { text: "R"; font.pixelSize: 11; color: relationship; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        Text { text: "→"; font.pixelSize: 20; color: text2; anchors.verticalCenter: parent.verticalCenter }

                        // A - Heightened state (upward triangle)
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = anxiety
                                    ctx.beginPath()
                                    ctx.moveTo(16, 4)
                                    ctx.lineTo(28, 28)
                                    ctx.lineTo(4, 28)
                                    ctx.closePath()
                                    ctx.fill()
                                }
                            }
                            Text { text: "A"; font.pixelSize: 11; color: anxiety; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        Text { text: "→"; font.pixelSize: 20; color: text2; anchors.verticalCenter: parent.verticalCenter }

                        // S - Outcome (starburst)
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = symptom
                                    ctx.beginPath()
                                    for (var i = 0; i < 8; i++) {
                                        var angle = (i * Math.PI / 4) - Math.PI / 2
                                        var r = (i % 2 === 0) ? 12 : 6
                                        var x = 16 + Math.cos(angle) * r
                                        var y = 16 + Math.sin(angle) * r
                                        if (i === 0) ctx.moveTo(x, y)
                                        else ctx.lineTo(x, y)
                                    }
                                    ctx.closePath()
                                    ctx.fill()
                                }
                            }
                            Text { text: "S"; font.pixelSize: 11; color: symptom; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // F - Buffer/Shield (separate)
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.fillStyle = functioning
                                    // Shield shape
                                    ctx.beginPath()
                                    ctx.moveTo(16, 4)
                                    ctx.lineTo(26, 8)
                                    ctx.lineTo(26, 18)
                                    ctx.bezierCurveTo(26, 24, 20, 28, 16, 30)
                                    ctx.bezierCurveTo(12, 28, 6, 24, 6, 18)
                                    ctx.lineTo(6, 8)
                                    ctx.closePath()
                                    ctx.fill()
                                }
                            }
                            Text { text: "F"; font.pixelSize: 11; color: functioning; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }
                }
            }

            // Proposal F: Minimal/Modern
            Rectangle {
                width: parent.width - 40
                height: 140
                radius: 12
                color: card

                Column {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    Text {
                        text: "F: Minimal/Modern"
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        color: text1
                    }
                    Text {
                        text: "Thin-line icons with consistent stroke weight. Clean, scalable."
                        font.pixelSize: 10
                        color: text2
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }

                    Row {
                        spacing: 30
                        anchors.horizontalCenter: parent.horizontalCenter

                        // S - Pulse/heartbeat line
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.strokeStyle = symptom
                                    ctx.lineWidth = 2.5
                                    ctx.lineCap = "round"
                                    ctx.lineJoin = "round"
                                    ctx.beginPath()
                                    ctx.moveTo(2, 16)
                                    ctx.lineTo(8, 16)
                                    ctx.lineTo(11, 8)
                                    ctx.lineTo(16, 24)
                                    ctx.lineTo(21, 8)
                                    ctx.lineTo(24, 16)
                                    ctx.lineTo(30, 16)
                                    ctx.stroke()
                                }
                            }
                            Text { text: "S"; font.pixelSize: 11; color: symptom; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // A - Zigzag (nervous energy)
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.strokeStyle = anxiety
                                    ctx.lineWidth = 2.5
                                    ctx.lineCap = "round"
                                    ctx.lineJoin = "round"
                                    ctx.beginPath()
                                    ctx.moveTo(8, 6)
                                    ctx.lineTo(24, 6)
                                    ctx.lineTo(8, 16)
                                    ctx.lineTo(24, 16)
                                    ctx.lineTo(8, 26)
                                    ctx.lineTo(24, 26)
                                    ctx.stroke()
                                }
                            }
                            Text { text: "A"; font.pixelSize: 11; color: anxiety; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // R - Two people connected
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.strokeStyle = relationship
                                    ctx.lineWidth = 2.5
                                    ctx.lineCap = "round"
                                    // Person 1
                                    ctx.beginPath()
                                    ctx.arc(10, 10, 4, 0, Math.PI * 2)
                                    ctx.stroke()
                                    ctx.beginPath()
                                    ctx.moveTo(10, 14)
                                    ctx.lineTo(10, 24)
                                    ctx.stroke()
                                    // Person 2
                                    ctx.beginPath()
                                    ctx.arc(22, 10, 4, 0, Math.PI * 2)
                                    ctx.stroke()
                                    ctx.beginPath()
                                    ctx.moveTo(22, 14)
                                    ctx.lineTo(22, 24)
                                    ctx.stroke()
                                    // Connection
                                    ctx.beginPath()
                                    ctx.moveTo(14, 10)
                                    ctx.lineTo(18, 10)
                                    ctx.stroke()
                                }
                            }
                            Text { text: "R"; font.pixelSize: 11; color: relationship; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // F - Gauge/meter
                        Column {
                            spacing: 5
                            Canvas {
                                width: 32; height: 32
                                anchors.horizontalCenter: parent.horizontalCenter
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    ctx.strokeStyle = functioning
                                    ctx.lineWidth = 2.5
                                    ctx.lineCap = "round"
                                    // Arc
                                    ctx.beginPath()
                                    ctx.arc(16, 20, 12, Math.PI, 0)
                                    ctx.stroke()
                                    // Needle
                                    ctx.beginPath()
                                    ctx.moveTo(16, 20)
                                    ctx.lineTo(22, 10)
                                    ctx.stroke()
                                    // Center dot
                                    ctx.fillStyle = functioning
                                    ctx.beginPath()
                                    ctx.arc(16, 20, 2, 0, Math.PI * 2)
                                    ctx.fill()
                                }
                            }
                            Text { text: "F"; font.pixelSize: 11; color: functioning; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }
                }
            }

            // Size comparison at different scales
            Rectangle {
                width: parent.width - 40
                height: 100
                radius: 12
                color: card

                Column {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 8

                    Text {
                        text: "Scale Comparison (Option B shapes)"
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        color: text1
                    }

                    Row {
                        spacing: 25
                        anchors.horizontalCenter: parent.horizontalCenter

                        // 8px (graph dots)
                        Column {
                            spacing: 3
                            Row {
                                spacing: 4
                                Rectangle { width: 8; height: 8; radius: 4; color: symptom }
                                Canvas {
                                    width: 8; height: 8
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.fillStyle = anxiety
                                        ctx.beginPath()
                                        ctx.moveTo(4, 0); ctx.lineTo(8, 8); ctx.lineTo(0, 8)
                                        ctx.fill()
                                    }
                                }
                                Rectangle { width: 6; height: 6; color: relationship; rotation: 45 }
                                Rectangle { width: 7; height: 7; radius: 1; color: functioning }
                            }
                            Text { text: "8px"; font.pixelSize: 9; color: text2; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // 16px
                        Column {
                            spacing: 3
                            Row {
                                spacing: 6
                                Rectangle { width: 16; height: 16; radius: 8; color: symptom }
                                Canvas {
                                    width: 16; height: 16
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.fillStyle = anxiety
                                        ctx.beginPath()
                                        ctx.moveTo(8, 0); ctx.lineTo(16, 16); ctx.lineTo(0, 16)
                                        ctx.fill()
                                    }
                                }
                                Rectangle { width: 12; height: 12; color: relationship; rotation: 45 }
                                Rectangle { width: 14; height: 14; radius: 2; color: functioning }
                            }
                            Text { text: "16px"; font.pixelSize: 9; color: text2; anchors.horizontalCenter: parent.horizontalCenter }
                        }

                        // 24px (list nodes)
                        Column {
                            spacing: 3
                            Row {
                                spacing: 8
                                Rectangle { width: 24; height: 24; radius: 12; color: symptom }
                                Canvas {
                                    width: 24; height: 24
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.fillStyle = anxiety
                                        ctx.beginPath()
                                        ctx.moveTo(12, 2); ctx.lineTo(22, 22); ctx.lineTo(2, 22)
                                        ctx.fill()
                                    }
                                }
                                Rectangle { width: 18; height: 18; color: relationship; rotation: 45 }
                                Rectangle { width: 20; height: 20; radius: 3; color: functioning }
                            }
                            Text { text: "24px"; font.pixelSize: 9; color: text2; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }
                }
            }
        }
    }
}
