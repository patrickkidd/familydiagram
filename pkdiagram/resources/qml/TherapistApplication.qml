import QtQuick 2.12

import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15

import "./PK" 1.0 as PK

ApplicationWindow {
    visible: true
    width: 400
    height: 600

    // Material.theme: Material.Light // Use light theme for iOS-like look
    // Material.accent: "#007AFF" // iOS blue for accents
    // Material.primary: "#F2F2F7" // iOS-like background color

    PK.TherapistView {
        id: therapistView
        anchors.fill: parent
    }
}