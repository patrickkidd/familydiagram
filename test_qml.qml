import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import "./PK" 1.0 as PK


ApplicationWindow {

    onActiveFocusControlChanged: {
        if(activeFocusControl) {
            print("activeFocusControl: " + activeFocusControl.objectName)
        } else {
            print("activeFocusControl: null")
        }
    }

    height: 800
    width: 300

    ColumnLayout {

        id: root
        property var model: ["Bob", "Alice", "Charlie"];
        anchors.fill: parent

        VariableBox {
            id: variableBox1
            objectName: 'variableBox1'
            model: root.model
            tabChain.tab: comboBox1
            tabChain.backtab: comboBox2
        }
        
        ComboBox {
            id: comboBox1
            objectName: 'comboBox1'
            model: root.model
            KeyNavigation.backtab: variableBox1.tabChain.lastTabFocusItem
            KeyNavigation.tab: comboBox2
        }

        ComboBox {
            id: comboBox2
            objectName: 'comboBox2'
            model: root.model
            KeyNavigation.tab: variableBox1.tabChain.firstTabFocusItem
        }

        // ComboBox {
        //     id: comboBox3
        //     objectName: 'comboBox3'
        //     model: root.model
        //     KeyNavigation.tab: textField1
        // }

        // TextField {
        //     id: textField1
        //     objectName: 'textField1'
        //     KeyNavigation.tab: variableBox1
        // }

        // Rectangle {
        //     objectName: 'textAreaField'
        //     border.width: textArea1.focus ? 2 : 1
        //     border.color: textArea1.focus ? 'blue' : 'grey'
        //     height: 200
        //     Layout.fillWidth: true
        //     TextArea {
        //         id: textArea1
        //         objectName: 'textArea1'
        //         wrapMode: TextArea.Wrap
        //         anchors.fill: parent
        //         KeyNavigation.tab: variableBox1
        //         Keys.onTabPressed: variableBox1.forceActiveFocus(Qt.TabFocusReason)
        //     }
        // }

        // Rectangle {
        //     color: 'transparent'
        //     Layout.fillHeight: true
        // }
    }
}