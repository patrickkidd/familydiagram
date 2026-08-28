import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK

Item {
    id: root

    property var pairBondData
    property var pdp

    signal accepted(int id)
    signal rejected(int id)
    signal horizontalWheel(real deltaX)

    readonly property string personAName: pdpController && pairBondData ? pdpController.resolvePersonName(pairBondData.person_a) : ""
    readonly property string personBName: pdpController && pairBondData ? pdpController.resolvePersonName(pairBondData.person_b) : ""
    readonly property string childNames: pdpController && pairBondData ? pdpController.resolvePairBondChildren(pairBondData.id) : ""

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 12
            color: util.QML_ITEM_BG
            border.color: util.QML_ITEM_BORDER_COLOR
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 6

                Text {
                    text: pairBondData && pairBondData.id > 0 ? "Update" : "Add"
                    font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
                    font.bold: true
                    color: util.QML_HIGHLIGHT_COLOR
                }

                Text {
                    text: "Pair Bond"
                    font.pixelSize: util.QML_TITLE_FONT_SIZE
                    font.family: util.FONT_FAMILY_TITLE
                    color: util.QML_TEXT_COLOR
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
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
                                visible: root.personAName !== ""

                                Text {
                                    text: "Person A"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: root.personAName
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    color: util.QML_TEXT_COLOR
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: root.personBName !== ""

                                Text {
                                    text: "Person B"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: root.personBName
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    color: util.QML_TEXT_COLOR
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: root.childNames !== ""

                                Text {
                                    text: "Parents of"
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: util.QML_TEXT_COLOR
                                    opacity: 0.7
                                }
                                Text {
                                    text: root.childNames
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
                onClicked: pairBondData && root.accepted(pairBondData.id)
            }
            PK.Button {
                objectName: "pdpRejectButton"
                text: "Reject"
                Layout.fillWidth: true
                pill: true
                textColor: "#FF4500"
                onClicked: pairBondData && root.rejected(pairBondData.id)
            }
        }
    }
}
