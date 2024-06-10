// https://code.qt.io/cgit/qt/qtdeclarative.git/tree/examples/quick/customitems/tabwidget/TabWidget.qml?h=5.15
import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import "." 1.0 as PK
import PK.Models 1.0
import "../js/Global.js" as Global
import "../js/Underscore.js" as Underscore


Rectangle {
    id: root
    color: 'transparent'


    // The first item in this chain for KeyNavigation.tab on an external item
    readonly property var firstTabItem: wrappedItem
    // The first item in this chain for KeyNavigation.backtab on an external item
    readonly property var lastTabItem: clearButton
    // Explicit keyNavigation.tab set on the last item in this chain
    property var tabItem
    // Explicit keyNavigation.backtab set on the first item in this chain
    property var backTabItem

    property var fieldWidth: 275

    default property Item wrappedItem: wrappedItem
    property var clearButton: clearButton
    property var container: container

    RowLayout {
        spacing: 2
        anchors.fill: parent

        RowLayout {
            id: container
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        PK.Button {
            id: clearButton
            objectName: "clearButton"
            source: '../../clear-button.png'
            clip: true
            implicitWidth: util.QML_MICRO_BUTTON_WIDTH
            implicitHeight: util.QML_MICRO_BUTTON_WIDTH
            opacity: wrappedItem.isDirty ? util.CLEAR_BUTTON_OPACITY : 0
            enabled: opacity > 0
            onClicked: {
                print('clearButton.onClicked')
                wrappedItem.clear()
            }
            Layout.leftMargin: 5
            KeyNavigation.backtab: wrappedItem.lastTabItem
            KeyNavigation.tab: root.tabItem
            Behavior on opacity {
                NumberAnimation { duration: util.ANIM_DURATION_MS / 3; easing.type: Easing.InOutQuad }
            }
        }

        Component.onCompleted: {
            wrappedItem.parent = container
            wrappedItem.Layout.fillWidth = true
        }
    }

}