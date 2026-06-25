import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// FD-338 "Rebuild diagram" prototype (iteration A).
// Run: uv run python bin/prototype.py doc/ui-prototyping/5-Rebuild-Diagram/1-rebuild-A.qml
//
// Demonstrates the three new pieces, all reusing existing house patterns:
//   1. rebuildButton  — 28px circular icon button (mirrors extractButton), left of Extract.
//   2. rebuildDialog  — cost-confirm modal (mirrors clearDataDialog) that CARRIES the
//                       "Max fidelity" toggle, so the K choice rides on the confirm step
//                       and the toolbar only gains one icon. TEMPORARY (remove post-pricing).
//   3. LoadingOverlay determinate variant — progress bar + label driven by a 0-100 signal.
Rectangle {
    id: root
    anchors.fill: parent
    color: util.QML_WINDOW_BG

    property string textColor: util.QML_TEXT_COLOR
    property string secondaryText: util.QML_INACTIVE_TEXT_COLOR
    property string itemBg: util.QML_ITEM_BG
    property string borderColor: util.QML_ITEM_BORDER_COLOR
    property string accentColor: util.IS_UI_DARK_MODE ? "#4495F7" : "#007AFF"

    // ── Mock top bar fragment (Discuss tab) ──────────────────────────────────
    Rectangle {
        id: topBar
        width: parent.width
        height: util.QML_HEADER_HEIGHT
        color: util.QML_HEADER_BG
        anchors.top: parent.top

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            text: "Discuss"
            color: textColor
            font.pixelSize: util.QML_TITLE_FONT_SIZE
            font.bold: true
        }

        // Extract button (existing) — kept for spatial reference
        Rectangle {
            id: extractButton
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 28; height: 28; radius: 14
            color: accentColor
            Canvas {
                anchors.centerIn: parent; width: 14; height: 14
                onPaint: {
                    var ctx = getContext("2d"); ctx.clearRect(0,0,width,height)
                    ctx.strokeStyle = "white"; ctx.lineWidth = 1.5; ctx.lineCap = "round"
                    ctx.beginPath(); ctx.moveTo(7,1); ctx.lineTo(7,9); ctx.stroke()
                    ctx.beginPath(); ctx.moveTo(3.5,6); ctx.lineTo(7,10); ctx.lineTo(10.5,6); ctx.stroke()
                    ctx.beginPath(); ctx.moveTo(1,10); ctx.lineTo(1,13); ctx.lineTo(13,13); ctx.lineTo(13,10); ctx.stroke()
                }
            }
        }

        // NEW: Rebuild button — 28px circle, left of Extract, circular-arrows glyph.
        Rectangle {
            id: rebuildButton
            objectName: "rebuildButton"
            anchors.right: extractButton.left
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            width: 28; height: 28; radius: 14
            color: util.IS_UI_DARK_MODE ? "#3A3938" : "#E9E9EB"
            Canvas {
                anchors.centerIn: parent; width: 16; height: 16
                onPaint: {
                    var ctx = getContext("2d"); ctx.clearRect(0,0,width,height)
                    ctx.strokeStyle = root.textColor; ctx.lineWidth = 1.5; ctx.lineCap = "round"
                    // two-thirds circular arc + arrowhead = "rebuild/refresh"
                    ctx.beginPath(); ctx.arc(8,8,5.2,-0.6,3.6); ctx.stroke()
                    ctx.beginPath(); ctx.moveTo(11.6,3.2); ctx.lineTo(13.2,5.2); ctx.lineTo(10.6,5.6); ctx.stroke()
                }
            }
            MouseArea { anchors.fill: parent; onClicked: rebuildDialog.open() }
        }
    }

    Text {
        anchors.centerIn: parent
        text: "Tap the rebuild glyph (top-right, left of Extract)\nto open the cost-confirm modal."
        horizontalAlignment: Text.AlignHCenter
        color: secondaryText
        font.pixelSize: 14
    }

    // ── NEW: cost-confirm modal with embedded Max-fidelity toggle ─────────────
    // TEMPORARY: remove this whole cost-confirmation dialog (and the cost copy)
    // once a customer pricing model is added to the app. Until then it gates the
    // spend and points the user at patrick@alaskafamilysystems.com.
    property bool maxFidelity: true
    Popup {
        id: rebuildDialog
        objectName: "rebuildDialog"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(root.width - 40, 340)
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 0
        background: Rectangle { radius: 14; color: itemBg; border.width: 1; border.color: borderColor }
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150 }
            NumberAnimation { property: "scale"; from: 0.9; to: 1; duration: 150; easing.type: Easing.OutBack }
        }
        exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 } }

        contentItem: Column {
            spacing: 0
            padding: 20
            width: rebuildDialog.width

            Text {
                text: "Rebuild Diagram"
                font.pixelSize: 17; font.bold: true; color: textColor
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Item { width: 1; height: 12 }
            Text {
                width: rebuildDialog.width - 40
                text: "This re-runs the AI several times to reconstruct a more complete, better-connected diagram from your discussions. It costs Alaska Family Systems about $0.50 each time. Please check with patrick@alaskafamilysystems.com before continuing."
                wrapMode: Text.WordWrap
                font.pixelSize: 14; color: secondaryText
                horizontalAlignment: Text.AlignHCenter
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Item { width: 1; height: 18 }

            // Max-fidelity toggle row (default ON = K=6). OFF = K=4.
            Rectangle {
                width: rebuildDialog.width - 40
                height: 52; radius: 10
                color: util.QML_ITEM_ALTERNATE_BG
                anchors.horizontalCenter: parent.horizontalCenter
                Column {
                    anchors.left: parent.left; anchors.leftMargin: 14
                    anchors.verticalCenter: parent.verticalCenter; spacing: 2
                    Text { text: "Max fidelity"; font.pixelSize: 15; color: textColor }
                    Text {
                        text: root.maxFidelity ? "Best accuracy, about $0.50" : "Faster, about $0.25"
                        font.pixelSize: 11; color: secondaryText
                    }
                }
                Switch {
                    anchors.right: parent.right; anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    checked: root.maxFidelity
                    onToggled: root.maxFidelity = checked
                }
            }
            Item { width: 1; height: 16 }

            Row {
                spacing: 10
                anchors.horizontalCenter: parent.horizontalCenter
                Rectangle {
                    width: (rebuildDialog.width - 50) / 2; height: 44; radius: 10
                    color: util.QML_ITEM_ALTERNATE_BG
                    Text { anchors.centerIn: parent; text: "Cancel"; font.pixelSize: 15; color: textColor }
                    MouseArea { anchors.fill: parent; onClicked: rebuildDialog.close() }
                }
                Rectangle {
                    width: (rebuildDialog.width - 50) / 2; height: 44; radius: 10
                    color: accentColor
                    Text { anchors.centerIn: parent; text: "Continue"; font.pixelSize: 15; color: "white" }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            // production: personalApp.rebuildDiagram(root.maxFidelity ? 6 : 4)
                            rebuildDialog.close()
                            demoOverlay.progress = 0
                            demoOverlay.text = "Rebuild 1 of " + (root.maxFidelity ? 6 : 4)
                            demoOverlay.visible = true
                            demoTimer.k = root.maxFidelity ? 6 : 4
                            demoTimer.n = 0
                            demoTimer.start()
                        }
                    }
                }
            }
        }
    }

    // ── LoadingOverlay determinate variant (progress bar + label) ─────────────
    Rectangle {
        id: demoOverlay
        property real progress: -1   // -1 = indeterminate (legacy importOverlay), >=0 = determinate
        property string text: "Loading..."
        anchors.fill: parent
        visible: false
        color: util.QML_HEADER_BG
        z: 1000
        MouseArea { anchors.fill: parent; onClicked: {} }
        Column {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -42
            spacing: 20; width: parent.width * 0.7
            ProgressBar {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                from: 0; to: 100
                indeterminate: demoOverlay.progress < 0
                value: Math.max(0, demoOverlay.progress)
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: demoOverlay.text + (demoOverlay.progress >= 0 ? "  ·  " + Math.round(demoOverlay.progress) + "%" : "")
                color: util.QML_TEXT_COLOR; font.pixelSize: 16
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
    Timer {
        id: demoTimer
        property int k: 6
        property int n: 0
        interval: 500; repeat: true
        onTriggered: {
            n += 1
            demoOverlay.progress = Math.min(100, n / (k * 2) * 100)
            demoOverlay.text = "Rebuild " + Math.min(k, Math.ceil(n / 2)) + " of " + k
            if (demoOverlay.progress >= 100) { stop(); demoOverlay.visible = false }
        }
    }
}
