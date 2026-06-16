/*
FD-321 — Settings "Profile" sub-page. Same 56px header + back-chevron chrome as
VoiceSettingsPage. Hosts UserDetailsForm (non-wizard) pre-populated from the
primary node, with a Save button enabled only when valid. Reached from the
AccountDrawer ACCOUNT entry.
*/

import QtQuick 2.15
import QtQuick.Controls 2.15
import "." 1.0 as Personal

Page {
    id: root

    property color headerBg: util.QML_HEADER_BG
    property color textColor: util.QML_TEXT_COLOR
    property color secondaryText: util.QML_INACTIVE_TEXT_COLOR
    property color borderColor: util.QML_ITEM_BORDER_COLOR
    property color accentColor: util.QML_SELECTION_COLOR

    signal backClicked()

    function reload() {
        formItem.loadProfile(personalApp.userProfile)
    }

    onVisibleChanged: if (visible) reload()
    Component.onCompleted: reload()

    background: Rectangle { color: util.QML_WINDOW_BG }

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
                text: "‹"
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
            text: "Profile"
            font.pixelSize: 17
            font.bold: true
            color: textColor
        }

        Rectangle {
            objectName: "saveButton"
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: saveLabel.width + 16
            height: 40
            radius: 8
            color: "transparent"

            Text {
                id: saveLabel
                anchors.centerIn: parent
                text: "Save"
                font.pixelSize: 16
                font.bold: true
                color: formItem.valid ? accentColor : secondaryText
            }
            MouseArea {
                anchors.fill: parent
                enabled: formItem.valid
                onClicked: {
                    personalApp.saveUserProfile(
                        formItem.firstName, formItem.lastName,
                        formItem.birthYear, formItem.birthMonth, formItem.birthDay)
                    root.backClicked()
                }
            }
        }
    }

    Personal.UserDetailsForm {
        id: formItem
        objectName: "profileForm"
        wizardMode: false
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}
