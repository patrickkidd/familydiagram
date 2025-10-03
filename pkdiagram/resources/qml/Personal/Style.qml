// Style.qml
pragma Singleton
import QtQuick 2.15

QtObject {
    id: style

    // Light mode colors
    readonly property color lightBackground: "#FFFFFF" // systemBackground
    readonly property color lightSecondaryBackground: "#F2F2F7" // secondarySystemBackground
    readonly property color lightLabel: "#000000" // label
    readonly property color lightPlaceholder: "#8E8E93" // placeholderText
    readonly property color lightButton: "#007AFF" // systemBlue

    // Dark mode colors
    readonly property color darkBackground: util.QML_WINDOW_BG // systemBackground
    readonly property color darkSecondaryBackground: "#1C1C1E" // secondarySystemBackground
    readonly property color darkLabel: "#FFFFFF" // label
    readonly property color darkPlaceholder: "#636366" // placeholderText
    readonly property color darkButton: "#0A84FF" // systemBlue (adjusted for dark mode)

    // Active colors based on theme
    property bool isDarkMode: util.IS_UI_DARK_MODE
    readonly property color background: isDarkMode ? darkBackground : lightBackground
    readonly property color secondaryBackground: isDarkMode ? darkSecondaryBackground : lightSecondaryBackground
    readonly property color label: isDarkMode ? darkLabel : lightLabel
    readonly property color placeholder: isDarkMode ? darkPlaceholder : lightPlaceholder
    readonly property color button: isDarkMode ? darkButton : lightButton

    // Spacing and sizing
    readonly property int spacingSmall: 8
    readonly property int spacingMedium: 16
    readonly property int spacingLarge: 20
    readonly property int buttonHeight: 44
    readonly property int cornerRadius: 10

}


    // property var safeLeftMargin: 0
    // property var safeRightMargin: 0
    // property var safeTopMargin: 0
    // property var safeBottomMargin: 0
    // anchors.leftMargin: safeLeftMargin
    // anchors.rightMargin: safeRightMargin
    // anchors.topMargin: safeTopMargin
    // anchors.bottomMargin: safeBottomMargin    

    // function adjustScreenMargins() {
    //     var safeAreaMargins = util.safeAreaMargins()
    //     root.safeLeftMargin = safeAreaMargins.left
    //     root.safeRightMargin = safeAreaMargins.right
    //     root.safeTopMargin = safeAreaMargins.top
    //     root.safeBottomMargin = safeAreaMargins.bottom
    //     print('left:', safeLeftMargin, 'right:', safeRightMargin, 'top:', safeTopMargin, 'bottom:', safeBottomMargin)
    // }

    // Connections {
    //     target: CUtil
    //     function onScreenOrientationChanged() {
    //         root.adjustScreenMargins()
    //     }
    // }

    // Component.onCompleted: {
    //     root.adjustScreenMargins()
    // }