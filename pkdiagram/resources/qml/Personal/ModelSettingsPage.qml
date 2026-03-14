import QtQuick 2.15
import QtQuick.Controls 2.15

Page {
    id: root

    property color headerBg: util.QML_HEADER_BG
    property color itemBg: util.QML_ITEM_BG
    property color textColor: util.QML_TEXT_COLOR
    property color secondaryText: util.QML_INACTIVE_TEXT_COLOR
    property color borderColor: util.QML_ITEM_BORDER_COLOR
    property color accentColor: util.QML_SELECTION_COLOR

    signal backClicked()

    background: Rectangle {
        color: util.QML_WINDOW_BG
    }

    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 56
        color: headerBg
        z: 10

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: borderColor
        }

        Rectangle {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 40
            height: 40
            radius: 8
            color: backMouseArea.pressed ? util.QML_ITEM_ALTERNATE_BG : "transparent"

            Text {
                anchors.centerIn: parent
                text: "\u2039"
                font.pixelSize: 28
                color: accentColor
            }

            MouseArea {
                id: backMouseArea
                anchors.fill: parent
                onClicked: root.backClicked()
            }
        }

        Text {
            anchors.centerIn: parent
            text: "Model"
            font.pixelSize: 17
            font.bold: true
            color: textColor
        }
    }

    Flickable {
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        contentHeight: contentColumn.height
        clip: true

        Column {
            id: contentColumn
            width: parent.width
            topPadding: 20
            leftPadding: 16
            rightPadding: 16
            bottomPadding: 40
            spacing: 20

            Text {
                text: "CONVERSATIONAL MODEL"
                font.pixelSize: 12
                font.bold: true
                color: secondaryText
                leftPadding: 4
            }

            Rectangle {
                width: parent.width - 32
                height: modelColumn.height
                radius: 12
                color: itemBg
                border.width: 1
                border.color: borderColor

                Column {
                    id: modelColumn
                    width: parent.width

                    Repeater {
                        id: modelRepeater
                        model: personalApp ? personalApp.availableModels : []

                        Rectangle {
                            width: parent.width
                            height: 50
                            color: "transparent"

                            property bool isCurrent: personalApp && personalApp.responseModel === modelData.id

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 12
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.name
                                color: textColor
                                font.pixelSize: 15
                            }

                            Text {
                                id: checkmark
                                anchors.right: parent.right
                                anchors.rightMargin: 12
                                anchors.verticalCenter: parent.verticalCenter
                                text: "\u2713"
                                color: accentColor
                                font.pixelSize: 18
                                visible: isCurrent
                            }

                            Rectangle {
                                anchors.bottom: parent.bottom
                                anchors.left: parent.left
                                anchors.leftMargin: 12
                                anchors.right: parent.right
                                height: 1
                                color: borderColor
                                visible: index < modelRepeater.count - 1
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: personalApp.setResponseModel(modelData.id)
                            }
                        }
                    }
                }
            }

            Text {
                width: parent.width - 32
                text: "The model used for conversation responses. Changing this does not affect data extraction."
                color: secondaryText
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                leftPadding: 4
            }
        }
    }
}
