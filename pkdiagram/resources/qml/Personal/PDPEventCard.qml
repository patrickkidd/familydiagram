import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.15
import "../PK" 1.0 as PK

Rectangle {
    id: root

    anchors.fill: parent

    property var eventData
    property var pdp

    signal accepted(int id)
    signal rejected(int id)
    signal editRequested(var eventData)

    color: util.QML_ITEM_ALTERNATE_BG
    radius: 12
    border.color: isShiftEvent ? util.QML_HIGHLIGHT_COLOR : util.QML_ITEM_BORDER_COLOR
    border.width: isShiftEvent ? 2 : 1

    layer.enabled: true
    layer.effect: DropShadow {
        transparentBorder: true
        horizontalOffset: 0
        verticalOffset: 4
        radius: 12
        samples: 25
        color: "#40000000"
    }

    readonly property bool isShiftEvent: eventData && eventData.kind === util.EventKind.Shift
    readonly property bool isPairBondEvent: eventData && [
        util.EventKind.Bonded,
        util.EventKind.Married,
        util.EventKind.Separated,
        util.EventKind.Divorced,
        util.EventKind.Moved
    ].indexOf(eventData.kind) !== -1
    readonly property bool isOffspringEvent: eventData && [
        util.EventKind.Birth,
        util.EventKind.Adopted
    ].indexOf(eventData.kind) !== -1

    function hasValue(val) {
        return val !== null && val !== undefined && val !== ""
    }

    function hasSarfValue(val) {
        return val !== null && val !== undefined && val !== "" && val !== 0
    }

    function eventKindColor(kind) {
        if (!kind) return util.QML_INACTIVE_TEXT_COLOR
        if (kind === util.EventKind.Bonded) return "#FF69B4"
        if (kind === util.EventKind.Married) return "#FF1493"
        if (kind === util.EventKind.Birth) return "#32CD32"
        if (kind === util.EventKind.Adopted) return "#32CD32"
        if (kind === util.EventKind.Moved) return "#4169E1"
        if (kind === util.EventKind.Separated) return "#FFA500"
        if (kind === util.EventKind.Divorced) return "#FF4500"
        if (kind === util.EventKind.Shift) return util.QML_HIGHLIGHT_COLOR
        if (kind === util.EventKind.Death) return "#808080"
        return util.QML_INACTIVE_TEXT_COLOR
    }

    function variableColor(val, isFunctioning) {
        if (isFunctioning) {
            if (val === util.VARIABLE_SHIFT_UP) return "#27ae60"
            if (val === util.VARIABLE_SHIFT_DOWN) return "#e74c3c"
        } else {
            if (val === util.VARIABLE_SHIFT_UP) return "#e74c3c"
            if (val === util.VARIABLE_SHIFT_DOWN) return "#27ae60"
        }
        if (val === util.VARIABLE_SHIFT_SAME) return "#95a5a6"
        return util.QML_TEXT_COLOR
    }

    function formatDateWithCertainty(dt, certainty) {
        if (!dt) return ""
        if (certainty && certainty !== "certain") {
            return dt + " (" + personalApp.dateCertaintyLabel(certainty) + ")"
        }
        return dt
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                Layout.preferredWidth: 70
                Layout.preferredHeight: 22
                radius: 11
                color: eventKindColor(eventData ? eventData.kind : null)
                opacity: 0.9

                Text {
                    anchors.centerIn: parent
                    text: personalApp.eventKindLabel(eventData ? eventData.kind : null)
                    font.pixelSize: 11
                    font.bold: true
                    color: "white"
                }
            }

            Item { Layout.fillWidth: true }

            Text {
                visible: false
                text: "Tap to edit"
                font.pixelSize: 11
                color: util.QML_HIGHLIGHT_COLOR
                opacity: 0.8

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (eventData) {
                            root.editRequested(eventData)
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: util.QML_ITEM_BORDER_COLOR
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            MouseArea {
                anchors.fill: parent
                z: 1
                onWheel: function(event) {
                    if (Math.abs(event.angleDelta.y) > Math.abs(event.angleDelta.x)) {
                        flickable.contentY = Math.max(0,
                            Math.min(flickable.contentHeight - flickable.height,
                                flickable.contentY - event.angleDelta.y))
                        event.accepted = true
                    } else {
                        event.accepted = false
                    }
                }
                onClicked: {
                    if (eventData) {
                        root.editRequested(eventData)
                    }
                }
            }

            Flickable {
                id: flickable
                anchors.fill: parent
                contentHeight: summaryColumn.height
                clip: true
                flickableDirection: Flickable.VerticalFlick
                boundsBehavior: Flickable.StopAtBounds
                interactive: false

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AlwaysOn
                    visible: flickable.contentHeight > flickable.height
                }

                ColumnLayout {
                    id: summaryColumn
                    width: flickable.width - 12
                    spacing: 6

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: eventData !== null && eventData !== undefined && hasValue(eventData.person)

                        Text {
                            text: "Person"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personalApp.resolvePersonName(eventData ? eventData.person : null)
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: util.QML_TEXT_COLOR
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: (isPairBondEvent || isOffspringEvent) && eventData !== null && eventData !== undefined && hasValue(eventData.spouse) && personalApp.resolvePersonName(eventData.spouse) !== ""

                        Text {
                            text: "Spouse"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personalApp.resolvePersonName(eventData ? eventData.spouse : null)
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: util.QML_TEXT_COLOR
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: isOffspringEvent && eventData !== null && eventData !== undefined && hasValue(eventData.child) && personalApp.resolvePersonName(eventData.child) !== ""

                        Text {
                            text: "Child"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personalApp.resolvePersonName(eventData ? eventData.child : null)
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: util.QML_TEXT_COLOR
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: isShiftEvent && eventData !== null && eventData !== undefined && hasValue(eventData.description)

                        Text {
                            text: "Description"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: eventData ? (eventData.description || "") : ""
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: util.QML_TEXT_COLOR
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: isShiftEvent && eventData && hasSarfValue(eventData.symptom)

                        Text {
                            text: "Symptom"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personalApp.variableLabel(eventData ? eventData.symptom : null)
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: variableColor(eventData ? eventData.symptom : null, false)
                            font.bold: true
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: isShiftEvent && eventData && hasSarfValue(eventData.anxiety)

                        Text {
                            text: "Anxiety"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personalApp.variableLabel(eventData ? eventData.anxiety : null)
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: variableColor(eventData ? eventData.anxiety : null, false)
                            font.bold: true
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: isShiftEvent && eventData && hasValue(eventData.relationship)

                        Text {
                            text: "Relationship"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personalApp.relationshipLabel(eventData ? eventData.relationship : null)
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: util.QML_TEXT_COLOR
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: isShiftEvent && eventData && eventData.relationshipTargets && eventData.relationshipTargets.length > 0 && personalApp.resolvePersonNames(eventData.relationshipTargets) !== ""

                        Text {
                            text: "Targets"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personalApp ? personalApp.resolvePersonNames(eventData ? eventData.relationshipTargets : []) : ""
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: util.QML_TEXT_COLOR
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: isShiftEvent && eventData && eventData.relationshipTriangles && eventData.relationshipTriangles.length > 0 && personalApp.resolvePersonNames(eventData.relationshipTriangles) !== ""

                        Text {
                            text: "Triangles"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personalApp.resolvePersonNames(eventData ? eventData.relationshipTriangles : [])
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: util.QML_TEXT_COLOR
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: isShiftEvent && eventData && hasSarfValue(eventData.functioning)

                        Text {
                            text: "Functioning"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personalApp.variableLabel(eventData ? eventData.functioning : null)
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: variableColor(eventData ? eventData.functioning : null, true)
                            font.bold: true
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: eventData !== null && eventData !== undefined && hasValue(eventData.dateTime)

                        Text {
                            text: "Date"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: formatDateWithCertainty(eventData ? eventData.dateTime : null, eventData ? eventData.dateCertainty : null)
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: util.QML_TEXT_COLOR
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: eventData !== null && eventData !== undefined && hasValue(eventData.endDateTime)

                        Text {
                            text: "End Date"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: eventData ? (eventData.endDateTime || "") : ""
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: util.QML_TEXT_COLOR
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: util.QML_ITEM_BORDER_COLOR
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            spacing: 8

            PK.Button {
                id: rejectButton
                source: '../../clear-button.png'
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                onClicked: {
                    if (eventData) {
                        root.rejected(eventData.id)
                    }
                }
            }

            Item { Layout.fillWidth: true }

            PK.Button {
                id: acceptButton
                source: '../../plus-button.png'
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                onClicked: {
                    if (eventData) {
                        root.accepted(eventData.id)
                    }
                }
            }
        }
    }
}
