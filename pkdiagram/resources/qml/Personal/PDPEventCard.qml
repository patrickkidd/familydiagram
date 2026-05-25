import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK

Item {
    id: root

    property var eventData
    property var pdp

    signal accepted(int id)
    signal rejected(int id)
    signal editRequested(var eventData)
    signal horizontalWheel(real deltaX)

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
        var d = new Date(dt)
        var formatted = Qt.formatDateTime(d, "MM/dd/yyyy hh:mm AP")
        if (certainty && certainty !== "certain" && personalApp) {
            return formatted + " (" + personalApp.dateCertaintyLabel(certainty) + ")"
        }
        return formatted
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 12
            color: util.QML_ITEM_ALTERNATE_BG
            border.color: isShiftEvent ? util.QML_HIGHLIGHT_COLOR : util.QML_ITEM_BORDER_COLOR
            border.width: isShiftEvent ? 2 : 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 6

                Text {
                    text: eventData && eventData.id > 0 ? "Update" : "Add"
                    font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
                    font.bold: true
                    color: util.QML_HIGHLIGHT_COLOR
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        text: personalApp ? personalApp.eventKindLabel(eventData ? eventData.kind : null) : ""
                        font.pixelSize: util.QML_TITLE_FONT_SIZE
                        font.family: util.FONT_FAMILY_TITLE
                        color: eventKindColor(eventData ? eventData.kind : null)
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }

                    Item {
                        id: editButton
                        objectName: "pdpEditButton"
                        Layout.preferredWidth: 28
                        Layout.preferredHeight: 28
                        opacity: editMouseArea.pressed ? 0.5 : 1.0

                        Image {
                            anchors.fill: parent
                            source: util.IS_UI_DARK_MODE ? '../../pencil-button-white.png' : '../../pencil-button.png'
                        }

                        MouseArea {
                            id: editMouseArea
                            anchors.fill: parent
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
                        acceptedButtons: Qt.NoButton
                        onWheel: function(event) {
                            if (Math.abs(event.angleDelta.y) > Math.abs(event.angleDelta.x)) {
                                flickable.contentY = Math.max(0,
                                    Math.min(flickable.contentHeight - flickable.height,
                                        flickable.contentY - event.angleDelta.y))
                            } else {
                                root.horizontalWheel(event.angleDelta.x)
                            }
                            event.accepted = true
                        }
                    }

                    Flickable {
                        id: flickable
                        anchors.fill: parent
                        contentHeight: summaryColumn.height
                        clip: true
                        flickableDirection: Flickable.VerticalFlick
                        boundsBehavior: Flickable.StopAtBounds

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
                                    text: personalApp ? personalApp.resolvePersonName(eventData ? eventData.person : null) : ""
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    color: util.QML_TEXT_COLOR
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: (isPairBondEvent || isOffspringEvent) && eventData !== null && eventData !== undefined && hasValue(eventData.spouse) && personalApp && personalApp.resolvePersonName(eventData.spouse) !== ""

                                Text {
                                    text: "Spouse"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: personalApp ? personalApp.resolvePersonName(eventData ? eventData.spouse : null) : ""
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    color: util.QML_TEXT_COLOR
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: isOffspringEvent && eventData !== null && eventData !== undefined && hasValue(eventData.child) && personalApp && personalApp.resolvePersonName(eventData.child) !== ""

                                Text {
                                    text: "Child"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: personalApp ? personalApp.resolvePersonName(eventData ? eventData.child : null) : ""
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
                                visible: eventData !== null && eventData !== undefined && hasValue(eventData.notes)

                                Text {
                                    text: "Notes"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: eventData ? (eventData.notes || "") : ""
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    color: util.QML_TEXT_COLOR
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: isShiftEvent && eventData !== null && eventData !== undefined && hasSarfValue(eventData.symptom)

                                Text {
                                    text: "Symptom"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: personalApp ? personalApp.variableLabel(eventData ? eventData.symptom : null) : ""
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    color: variableColor(eventData ? eventData.symptom : null, false)
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: isShiftEvent && eventData !== null && eventData !== undefined && hasSarfValue(eventData.anxiety)

                                Text {
                                    text: "Anxiety"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: personalApp ? personalApp.variableLabel(eventData ? eventData.anxiety : null) : ""
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    color: variableColor(eventData ? eventData.anxiety : null, false)
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: isShiftEvent && eventData !== null && eventData !== undefined && hasValue(eventData.relationship)

                                Text {
                                    text: "Relationship"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: personalApp ? personalApp.relationshipLabel(eventData ? eventData.relationship : null) : ""
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    color: util.QML_TEXT_COLOR
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: isShiftEvent && eventData && eventData.relationshipTargets && eventData.relationshipTargets.length > 0 && personalApp && personalApp.resolvePersonNames(eventData.relationshipTargets) !== ""

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
                                visible: isShiftEvent && eventData && eventData.relationshipTriangles && eventData.relationshipTriangles.length > 0 && personalApp && personalApp.resolvePersonNames(eventData.relationshipTriangles) !== ""

                                Text {
                                    text: "Triangles"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: personalApp ? personalApp.resolvePersonNames(eventData ? eventData.relationshipTriangles : []) : ""
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    color: util.QML_TEXT_COLOR
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: isShiftEvent && eventData !== null && eventData !== undefined && hasSarfValue(eventData.functioning)

                                Text {
                                    text: "Functioning"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: personalApp ? personalApp.variableLabel(eventData ? eventData.functioning : null) : ""
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    color: variableColor(eventData ? eventData.functioning : null, true)
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
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            PK.Button {
                objectName: "pdpAcceptButton"
                text: "Accept"
                Layout.fillWidth: true
                pill: true
                onClicked: eventData && root.accepted(eventData.id)
            }
            PK.Button {
                objectName: "pdpRejectButton"
                text: "Reject"
                Layout.fillWidth: true
                pill: true
                textColor: "#FF4500"
                onClicked: eventData && root.rejected(eventData.id)
            }
        }
    }
}
