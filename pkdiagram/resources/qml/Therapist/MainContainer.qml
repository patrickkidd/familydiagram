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

    StackLayout {

        id: stack
        currentIndex: tabBar.currentIndex
        anchors.fill: parent

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
    }

    footer: PK.TabBar {
        id: tabBar
        currentIndex: stack.currentIndex
        PK.TabButton { text: "Discuss" }
        PK.TabButton { text: "Learn" }
        PK.TabButton { text: "Plan" }
    }

}
