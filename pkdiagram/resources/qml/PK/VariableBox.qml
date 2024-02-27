
import QtQuick 2.12
import QtQuick.Window 2.2
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import "." 1.0 as PK
import "../js/Global.js" as Global

RowLayout {

    id: root

    Layout.fillWidth: true
    property var value: null;
    property var model: [
        { 'name': 'Up', 'value': util.VAR_VALUE_UP },
        { 'name': 'Down', 'value': util.VAR_VALUE_DOWN },
        { 'name': 'Same', 'value': util.VAR_VALUE_SAME }
    ];
    property var boxModel: model.map(function(item) { return item.name; })

    function clear() {
        comboBox.currentIndex = -1
    }

    PK.ComboBox {
        id: comboBox
        objectName: root.objectName + "_comboBox"
        width: 100
        model: boxModel
        currentIndex: model.findIndex(function(item) { return item.value == value; })
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
        id: clearAnxietyButton
        objectName: "clearAnxietyButton"
        source: '../../clear-button.png'
        clip: true
        implicitWidth: util.QML_MICRO_BUTTON_WIDTH
        implicitHeight: util.QML_MICRO_BUTTON_WIDTH
        Layout.leftMargin: 2
        opacity: comboBox.currentIndex != -1 ? 1 : 0
        enabled: opacity > 0
        onClicked: {
            root.forceActiveFocus()
            comboBox.currentIndex = -1
        }
        Behavior on opacity {
            NumberAnimation { duration: util.ANIM_DURATION_MS / 3; easing.type: Easing.InOutQuad }
        }
    }
}