
import QtQuick 2.12
import QtQuick.Window 2.2
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." 1.0 as PK
import "../js/Global.js" as Global


RowLayout {

    id: root

    // The first item in this chain for KeyNavigation.tab on an external item
    readonly property var firstTabItem: valueBox
    // The first item in this chain for KeyNavigation.backtab on an external item
    readonly property var lastTabItem: clearButton
    // Explicit keyNavigation.tab set on the last item in this chain
    property var tabItem
    // Explicit keyNavigation.backtab set on the first item in this chain
    property var backTabItem


    property var value: null;
    property var model: [
        { 'name': 'Up', 'value': util.VAR_VALUE_UP },
        { 'name': 'Down', 'value': util.VAR_VALUE_DOWN },
        { 'name': 'Same', 'value': util.VAR_VALUE_SAME }
    ];
    property var boxModel: model.map(function(item) { return item.name; })
    property var comboBox: valueBox

    function clear() {
        valueBox.currentIndex = -1
    }

    function setValue(value) {
        let index = model.findIndex(function(item) { return item.value == value; })
        if(index != -1)
            valueBox.currentIndex = index
    }

    PK.ComboBox {
        id: valueBox
        objectName: root.objectName + "_valueBox"
        width: 130
        model: boxModel
        focus: true
        currentIndex: {
            var newCurrentIndex = model.findIndex(function(item) { return item.value == value; })
            if(newCurrentIndex != currentIndex)
                newCurrentIndex = -1
            else
                currentIndex
        }
        KeyNavigation.tab: clearButton
        KeyNavigation.backtab: root.backTabItem
        onCurrentIndexChanged: {
            if(currentIndex != -1) {                
                let newValue = root.model[currentIndex].value
                if(root.value != newValue)
                    root.value = newValue
            } else {
                root.value = null
            }
        }
    }

    PK.Button {
        id: clearButton
        objectName: "clearButton"
        source: '../../clear-button.png'
        clip: true
        implicitWidth: util.QML_MICRO_BUTTON_WIDTH
        implicitHeight: util.QML_MICRO_BUTTON_WIDTH
        Layout.leftMargin: 2
        opacity: valueBox.currentIndex != -1 ? util.CLEAR_BUTTON_OPACITY : 0
        enabled: opacity > 0
        KeyNavigation.tab: root.tabItem
        KeyNavigation.backtab: valueBox
        onClicked: {
            root.forceActiveFocus()
            valueBox.currentIndex = -1
        }
        Behavior on opacity {
            NumberAnimation { duration: util.ANIM_DURATION_MS / 3; easing.type: Easing.InOutQuad }
        }
    }

    Keys.onPressed: {
        if(event.key == Qt.Key_Backspace || event.key == Qt.Key_Delete) {
            clearButton.clicked()
        }
    }
}
