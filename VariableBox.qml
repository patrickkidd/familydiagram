import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12



FocusScope {
    id: root
    objectName: 'root'
    x: outer.x
    y: outer.y
    width: outer.width
    height: outer.height

    property var model: null
    // property alias tabChain: tabChainObject

    proeprty var tabChain: TabChain {}
    
    RowLayout {

        id: outer

        ComboBox {
            id: valueBox
            objectName: root.objectName + "_valueBox"
            model: root.model
            KeyNavigation.tab: clearButton
            KeyNavigation.backtab: tabChain.backtab
        }

        Button {
            id: clearButton
            objectName: root.objectName + "_clearButton"
            text: "X"
            Layout.leftMargin: 2
            width: 50
            onClicked: valueBox.currentIndex = -1
            KeyNavigation.tab: tabChain.tab
        }
    }
}