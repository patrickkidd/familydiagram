import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.15
import "../PK" 1.0 as PK

Rectangle {
    id: root

    property var personData
    property var pdp

    signal accepted(int id)
    signal rejected(int id)
    signal editRequested(var personData)

    color: util.QML_ITEM_BG
    radius: 12
    border.color: util.QML_ITEM_BORDER_COLOR
    border.width: 1

    layer.enabled: true
    layer.effect: DropShadow {
        transparentBorder: true
        horizontalOffset: 0
        verticalOffset: 4
        radius: 12
        samples: 25
        color: "#40000000"
    }

    function resolveParentNames() {
        if (!personData || !personData.parents || !pdp || !pdp.pair_bonds) {
            return ""
        }
        for (var i = 0; i < pdp.pair_bonds.length; i++) {
            var pb = pdp.pair_bonds[i]
            if (pb.id === personData.parents) {
                var nameA = resolvePersonName(pb.person_a)
                var nameB = resolvePersonName(pb.person_b)
                if (nameA && nameB) {
                    return nameA + " & " + nameB
                } else if (nameA) {
                    return nameA
                } else if (nameB) {
                    return nameB
                }
            }
        }
        return ""
    }

    function resolvePersonName(personId) {
        if (!personId || !pdp || !pdp.people) {
            return ""
        }
        for (var i = 0; i < pdp.people.length; i++) {
            var p = pdp.people[i]
            if (p.id === personId) {
                return p.name || ""
            }
        }
        return ""
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                radius: 14
                color: util.QML_HIGHLIGHT_COLOR
                opacity: 0.2

                Text {
                    anchors.centerIn: parent
                    text: "\u263A"
                    font.pixelSize: 16
                    color: util.QML_TEXT_COLOR
                }
            }

            Text {
                text: "Person"
                font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
                font.family: util.FONT_FAMILY_TITLE
                color: util.QML_TEXT_COLOR
                Layout.fillWidth: true
            }

            Text {
                visible: true
                text: "Tap to edit"
                font.pixelSize: 11
                color: util.QML_HIGHLIGHT_COLOR
                opacity: 0.8

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (personData) {
                            root.editRequested(personData)
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
                        event.accepted = true
                    } else {
                        event.accepted = false
                    }
                }
            }

            Flickable {
                id: flickable
                anchors.fill: parent
                contentHeight: fieldsColumn.height
                clip: true
                flickableDirection: Flickable.VerticalFlick
                boundsBehavior: Flickable.StopAtBounds
                interactive: false

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AlwaysOn
                    visible: flickable.contentHeight > flickable.height
                }

                ColumnLayout {
                    id: fieldsColumn
                    width: flickable.width - 12
                    spacing: 6

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: personData !== null && personData !== undefined && typeof personData.name === "string" && personData.name.length > 0

                        Text {
                            text: "Name"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personData ? (personData.name || "") : ""
                            font.pixelSize: util.QML_TITLE_FONT_SIZE
                            font.family: util.FONT_FAMILY_TITLE
                            color: util.QML_TEXT_COLOR
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: personData !== null && personData !== undefined && typeof personData.last_name === "string" && personData.last_name.length > 0

                        Text {
                            text: "Last Name"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personData ? (personData.last_name || "") : ""
                            font.pixelSize: util.TEXT_FONT_SIZE
                            color: util.QML_TEXT_COLOR
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: resolveParentNames() !== ""

                        Text {
                            text: "Parents"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: resolveParentNames()
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
                    if (personData) {
                        root.rejected(personData.id)
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
                    if (personData) {
                        root.accepted(personData.id)
                    }
                }
            }
        }
    }
}
