import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK

Rectangle {
    id: root

    anchors.fill: parent

    property var personData
    property var pdp

    signal accepted(int id)
    signal rejected(int id)
    signal editRequested(var personData)
    signal horizontalWheel(real deltaX)

    color: util.QML_ITEM_BG
    radius: 12
    border.color: util.QML_ITEM_BORDER_COLOR
    border.width: 1

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
                    } else {
                        root.horizontalWheel(event.angleDelta.x)
                    }
                    event.accepted = true
                }
            }

            Flickable {
                id: flickable
                anchors.fill: parent
                contentHeight: fieldsColumn.height
                clip: true
                flickableDirection: Flickable.VerticalFlick
                boundsBehavior: Flickable.StopAtBounds

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
                        visible: personData !== null && personData !== undefined && personData.parents !== null && personData.parents !== undefined && personalApp.resolveParentNames(personData.parents) !== ""

                        Text {
                            text: "Parents"
                            font.pixelSize: 10
                            font.bold: true
                            color: util.QML_TEXT_COLOR
                            opacity: 0.7
                        }
                        Text {
                            text: personalApp ? personalApp.resolveParentNames(personData ? personData.parents : null) : ""
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
