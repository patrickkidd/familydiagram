import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.15
import "../PK" 1.0 as PK

Rectangle {
    id: root

    property var vignetteData
    property bool expanded: false
    property bool selected: vignetteModel && vignetteModel.selectedVignetteId === (vignetteData ? vignetteData.id : "")

    signal clicked(string vignetteId)
    signal eventClicked(int eventId)

    color: selected ? Qt.rgba(util.QML_HIGHLIGHT_COLOR.r, util.QML_HIGHLIGHT_COLOR.g, util.QML_HIGHLIGHT_COLOR.b, 0.15) : util.QML_ITEM_ALTERNATE_BG
    radius: 12
    border.color: selected ? util.QML_HIGHLIGHT_COLOR : util.QML_ITEM_BORDER_COLOR
    border.width: selected ? 2 : 1

    implicitHeight: contentColumn.height + 24

    layer.enabled: true
    layer.effect: DropShadow {
        transparentBorder: true
        horizontalOffset: 0
        verticalOffset: 2
        radius: 8
        samples: 17
        color: "#30000000"
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
        if (!pattern) return util.QML_INACTIVE_TEXT_COLOR
        switch (pattern) {
            case "anxiety_cascade": return "#e74c3c"
            case "triangle_activation": return "#9b59b6"
            case "conflict_resolution": return "#27ae60"
            case "reciprocal_disturbance": return "#e67e22"
            case "functioning_gain": return "#3498db"
            case "work_family_spillover": return "#f39c12"
            default: return util.QML_INACTIVE_TEXT_COLOR
        }
    }

    function dominantVariableColor(variable) {
        switch (variable) {
            case "S": return "#e05555"
            case "A": return "#40a060"
            case "R": return "#5080d0"
            case "F": return "#909090"
            default: return util.QML_INACTIVE_TEXT_COLOR
        }
    }

    function dominantVariableLabel(variable) {
        switch (variable) {
            case "S": return "Symptom"
            case "A": return "Anxiety"
            case "R": return "Relationship"
            case "F": return "Functioning"
            default: return ""
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            if (vignetteData) {
                root.clicked(vignetteData.id)
            }
        }
    }

    ColumnLayout {
        id: contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: vignetteData ? vignetteData.title : ""
                font.pixelSize: 14
                font.bold: true
                color: util.QML_TEXT_COLOR
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Rectangle {
                visible: vignetteData && vignetteData.dominantVariable !== undefined && vignetteData.dominantVariable !== null && vignetteData.dominantVariable !== ""
                Layout.preferredWidth: 24
                Layout.preferredHeight: 24
                radius: 12
                color: dominantVariableColor(vignetteData ? vignetteData.dominantVariable : null)
                opacity: 0.9

                Text {
                    anchors.centerIn: parent
                    text: vignetteData ? vignetteData.dominantVariable : ""
                    font.pixelSize: 11
                    font.bold: true
                    color: "white"
                }
            }

            Image {
                source: root.expanded ? "../../collapse-arrow.png" : "../../expand-arrow.png"
                Layout.preferredWidth: 16
                Layout.preferredHeight: 16
                opacity: 0.6

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        root.expanded = !root.expanded
                    }
                }
            }
        }

        Text {
            visible: vignetteData && vignetteData.startDate !== undefined && vignetteData.startDate !== null && vignetteData.startDate !== ""
            text: {
                if (!vignetteData) return ""
                var start = vignetteData.startDate || ""
                var end = vignetteData.endDate || ""
                if (start === end) return start
                return start + " - " + end
            }
            font.pixelSize: 11
            color: util.QML_INACTIVE_TEXT_COLOR
            Layout.fillWidth: true
        }

        Rectangle {
            visible: vignetteData && vignetteData.pattern !== undefined && vignetteData.pattern !== null && vignetteData.pattern !== ""
            Layout.preferredWidth: patternText.width + 16
            Layout.preferredHeight: 20
            radius: 10
            color: patternColor(vignetteData ? vignetteData.pattern : null)
            opacity: 0.85

            Text {
                id: patternText
                anchors.centerIn: parent
                text: patternLabel(vignetteData ? vignetteData.pattern : null)
                font.pixelSize: 10
                font.bold: true
                color: "white"
            }
        }

        Text {
            visible: vignetteData && vignetteData.summary !== undefined && vignetteData.summary !== null && vignetteData.summary !== ""
            text: vignetteData ? vignetteData.summary : ""
            font.pixelSize: 12
            color: util.QML_TEXT_COLOR
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            opacity: 0.85
        }

        Rectangle {
            visible: root.expanded
            Layout.fillWidth: true
            height: 1
            color: util.QML_ITEM_BORDER_COLOR
            opacity: 0.5
        }

        ColumnLayout {
            visible: root.expanded
            Layout.fillWidth: true
            spacing: 4

            Text {
                text: vignetteData && vignetteData.eventIds ? vignetteData.eventIds.length + " events" : "0 events"
                font.pixelSize: 11
                font.bold: true
                color: util.QML_INACTIVE_TEXT_COLOR
            }

            Repeater {
                model: vignetteData && vignetteData.eventIds ? vignetteData.eventIds : []

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
                    color: "transparent"
                    radius: 4

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        Text {
                            text: "Event #" + modelData
                            font.pixelSize: 11
                            color: util.QML_TEXT_COLOR
                            Layout.fillWidth: true
                        }

                        Text {
                            text: "View"
                            font.pixelSize: 10
                            color: util.QML_HIGHLIGHT_COLOR
                            opacity: 0.8

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.eventClicked(modelData)
                                }
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: parent.color = Qt.rgba(util.QML_HIGHLIGHT_COLOR.r, util.QML_HIGHLIGHT_COLOR.g, util.QML_HIGHLIGHT_COLOR.b, 0.1)
                        onExited: parent.color = "transparent"
                        onClicked: root.eventClicked(modelData)
                    }
                }
            }
        }
    }
}
