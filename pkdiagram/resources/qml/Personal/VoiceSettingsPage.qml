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
    property color chatPlaceholder: util.IS_UI_DARK_MODE ? "#636366" : "#8E8E93"

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
            text: "Voice"
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

            // Read Aloud toggle
            Text {
                text: "PLAYBACK"
                font.pixelSize: 12
                font.bold: true
                color: secondaryText
                leftPadding: 4
            }

            Rectangle {
                width: parent.width - 32
                height: 50
                radius: 12
                color: itemBg
                border.width: 1
                border.color: borderColor

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Read Aloud"
                    color: textColor
                    font.pixelSize: 15
                }

                Switch {
                    id: readAloudSwitch
                    anchors.right: parent.right
                    anchors.rightMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    checked: personalApp && personalApp.settings ? personalApp.settings.value("autoReadAloud", false) === true : false
                    onToggled: if (personalApp && personalApp.settings) personalApp.settings.setValue("autoReadAloud", checked)

                    indicator: Rectangle {
                        implicitWidth: 51
                        implicitHeight: 31
                        x: readAloudSwitch.leftPadding
                        y: parent.height / 2 - height / 2
                        radius: height / 2
                        color: readAloudSwitch.checked ? accentColor : util.QML_ITEM_ALTERNATE_BG

                        Behavior on color {
                            ColorAnimation { duration: 150 }
                        }

                        Rectangle {
                            x: readAloudSwitch.checked ? parent.width - width - 2 : 2
                            y: 2
                            width: 27
                            height: 27
                            radius: height / 2
                            color: util.QML_WINDOW_BG

                            Behavior on x {
                                NumberAnimation { duration: 150; easing.type: Easing.InOutQuad }
                            }
                        }
                    }
                    background: Item {}
                }
            }

            // Voice picker
            Text {
                text: "VOICE"
                font.pixelSize: 12
                font.bold: true
                color: secondaryText
                leftPadding: 4
            }

            // Download more voices
            Rectangle {
                width: parent.width - 32
                height: 50
                radius: 12
                color: itemBg
                border.width: 1
                border.color: borderColor

                Text {
                    anchors.centerIn: parent
                    text: "Download Voices\u2026"
                    color: accentColor
                    font.pixelSize: 15
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: personalApp.openSystemVoiceSettings()
                }
            }

            Rectangle {
                width: parent.width - 32
                height: voiceColumn.height
                radius: 12
                color: itemBg
                border.width: 1
                border.color: borderColor

                Column {
                    id: voiceColumn
                    width: parent.width

                    Repeater {
                        id: voiceRepeater
                        model: personalApp ? personalApp.ttsVoices : []

                        Rectangle {
                            width: parent.width
                            height: 50
                            color: "transparent"

                            property bool isCurrent: personalApp && personalApp.ttsVoiceName === modelData.name

                            // Preview play button
                            Rectangle {
                                id: previewBtn
                                anchors.left: parent.left
                                anchors.leftMargin: 8
                                anchors.verticalCenter: parent.verticalCenter
                                width: 32
                                height: 32
                                radius: 16
                                color: previewArea.pressed ? util.QML_ITEM_ALTERNATE_BG : "transparent"

                                Canvas {
                                    anchors.centerIn: parent
                                    width: 12
                                    height: 12
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.clearRect(0, 0, width, height)
                                        ctx.fillStyle = root.chatPlaceholder
                                        ctx.beginPath()
                                        ctx.moveTo(1, 0)
                                        ctx.lineTo(12, 6)
                                        ctx.lineTo(1, 12)
                                        ctx.closePath()
                                        ctx.fill()
                                    }
                                }

                                MouseArea {
                                    id: previewArea
                                    anchors.fill: parent
                                    onClicked: personalApp.previewVoice(modelData.name)
                                }
                            }

                            Text {
                                anchors.left: previewBtn.right
                                anchors.leftMargin: 4
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.name
                                color: textColor
                                font.pixelSize: 15
                            }

                            // Locale subtitle
                            Text {
                                anchors.right: checkmark.visible ? checkmark.left : parent.right
                                anchors.rightMargin: checkmark.visible ? 8 : 12
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.locale
                                color: secondaryText
                                font.pixelSize: 12
                            }

                            // Checkmark
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

                            // Separator
                            Rectangle {
                                anchors.bottom: parent.bottom
                                anchors.left: parent.left
                                anchors.leftMargin: 12
                                anchors.right: parent.right
                                height: 1
                                color: borderColor
                                visible: index < voiceRepeater.count - 1
                            }

                            MouseArea {
                                anchors.fill: parent
                                z: -1
                                onClicked: personalApp.setTtsVoice(modelData.name)
                            }
                        }
                    }
                }
            }

        }
    }
}
