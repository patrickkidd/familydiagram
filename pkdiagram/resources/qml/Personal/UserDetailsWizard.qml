/*
FD-321 — first-launch wizard surface. Hosts UserDetailsForm (wizardMode) plus
the bottom action bar (Get Started enabled only when valid, Skip always).
Saving lands the profile on the primary node and sets the prompt pref; Skip just
sets the pref. Either way the wizard never reappears.
*/

import QtQuick 2.15
import QtQuick.Controls 2.15
import "." 1.0 as Personal

Rectangle {
    id: root

    property real safeAreaTop: 0
    property real safeAreaBottom: 0

    property color borderColor: util.QML_ITEM_BORDER_COLOR
    property color accent: util.QML_SELECTION_COLOR

    signal done()

    color: util.QML_WINDOW_BG

    Personal.UserDetailsForm {
        id: formItem
        objectName: "userDetailsForm"
        wizardMode: true
        anchors.top: parent.top
        anchors.topMargin: root.safeAreaTop
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: bar.top
    }

    Rectangle {
        id: bar
        anchors.bottom: parent.bottom
        anchors.bottomMargin: root.safeAreaBottom
        width: parent.width
        height: 120
        color: util.QML_WINDOW_BG

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: root.borderColor
        }

        Rectangle {
            id: getStartedBtn
            objectName: "getStartedButton"
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 16
            width: parent.width - 40
            height: 50
            radius: 14
            color: formItem.valid ? root.accent : root.borderColor
            opacity: formItem.valid ? 1.0 : 0.5

            Text {
                anchors.centerIn: parent
                text: "Get Started"
                color: "white"
                font.pixelSize: 17
                font.bold: true
            }
            MouseArea {
                anchors.fill: parent
                enabled: formItem.valid
                onClicked: {
                    personalApp.saveUserProfile(
                        formItem.firstName, formItem.lastName,
                        formItem.birthYear, formItem.birthMonth, formItem.birthDay)
                    root.done()
                }
            }
        }

        Text {
            objectName: "skipButton"
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: getStartedBtn.bottom
            anchors.topMargin: 14
            text: "Skip for now"
            color: root.accent
            font.pixelSize: 15

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    personalApp.markProfilePrompted()
                    root.done()
                }
            }
        }
    }
}
