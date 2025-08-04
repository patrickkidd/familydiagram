/*
The outer content container, shown within the device's safe areas. Contains the
tabs and switches between the main views.
*/

import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK
import "." 1.0 as Therapist


Page {

    property var stack: stack
    property var tabBar: tabBar
    property var discussView: discussView
    property var learnView: learnView
    property var planView: planView
    property var accountDialog: accountDialogLoader.item
    property var showingAccount: false

    // Main content - only visible when logged in
    StackLayout {

        id: stack
        currentIndex: tabBar.currentIndex
        anchors.fill: parent
        visible: session.isLoggedIn()

        Therapist.DiscussView {
            id: discussView
            Layout.fillHeight: true
            Layout.fillWidth: true

        }

        Therapist.LearnView {
            id: learnView
            Layout.fillHeight: true
            Layout.fillWidth: true
        }

        Therapist.PlanView {
            id: planView
            Layout.fillHeight: true
            Layout.fillWidth: true
        }
        Rectangle {
            Button {
                text: "Show Account"
                onClicked: showingAccount = true
            }
        }
    }

    footer: PK.TabBar {
        id: tabBar
        currentIndex: stack.currentIndex
        visible: session.isLoggedIn()
        PK.TabButton { text: "Discuss" }
        PK.TabButton { text: "Learn" }
        PK.TabButton { text: "Plan" }
        PK.TabButton { icon.source: "../../settings-button.png"; Layout.maximumWidth: 25 }
    }

    // Account Dialog overlay - shown when not logged in
    Loader {
        id: accountDialogLoader
        anchors.fill: parent
        active: !session.isLoggedIn() || showingAccount
        source: "../AccountDialog.qml"
        
        onLoaded: {
            if (item) {
                item.done.connect(function() {
                    showingAccount = false
                    // Force refresh of session state
                    // session.changed()
                })
            }
        }
    }

    // Keys.onPressed: {
    //     if (event.modifiers & Qt.MetaModifier) {
    //         if (event.key === Qt.Key_1) {
    //             tabBar.currentIndex = 0;
    //             event.accepted = true;
    //         } else if (event.key === Qt.Key_2) {
    //             tabBar.currentIndex = 1;
    //             event.accepted = true;
    //         } else if (event.key === Qt.Key_3) {
    //             tabBar.currentIndex = 2;
    //             event.accepted = true;
    //         }
    //     }
    // }
    focus: true

}
