import QtQuick 2.12
import QtQuick.Layouts 1.12
import QtQuick.Controls 2.12
import "." 1.0 as PK
import PK.Models 1.0


ListView {
    id: root

    clip: true
    contentWidth: width

    model: LayerItemLayersModel {
        scene: sceneModel.scene
    }

    delegate: Rectangle {
        property bool selected: false
        property bool current: false
        property bool alternate: index % 2 == 1
        width: root.width
        height: util.QML_ITEM_HEIGHT
        color: util.itemBgColor(selected, current, alternate)
        Row {
            PK.CheckBox {
                id: activeBox
                textColor: util.textColor(selected, current, alternate)
                checkState: active !== undefined ? active : Qt.Unchecked
                onCheckStateChanged: active = checkState
            }
            PK.Text {
                text: name !== undefined ? name : ''
                color: util.textColor(selected, current, alternate)
                anchors.verticalCenter: parent.verticalCenter
                Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
            }
        }
        MouseArea {
            anchors.fill: parent
            onClicked: activeBox.checked = !activeBox.checked
        }
    }
    Rectangle {
        border {
            width: 1
            color: 'grey'
        }
        color: 'transparent'
        anchors.fill: parent
    }
}

