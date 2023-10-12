import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.12
import "." 1.0 as PK


ColumnLayout {
    
    id: root
    spacing: 0
    
    property var model: null
    property bool showButtons: true
    property int currentIndex: -1
    property int count: list.count

    function onRowClicked(mouse, row) {
        if(mouse && mouse.modifiers & Qt.ControlModifier) {
            currentIndex = -1
        } else {
            currentIndex = row
        }
    }

    ListView {
        id: list
        clip: true
        model: root.model
        Layout.fillWidth: true
        Layout.fillHeight: true
        
        delegate: Rectangle {

            property bool selected: index == currentIndex
            property bool current: false

            width: parent ? parent.width : 0
            height: util.QML_ITEM_HEIGHT // rowLayout.height
            color: util.itemBgColor(selected, current, index % 2 == 1)

            MouseArea {
                anchors.fill: parent
                onClicked: onRowClicked(mouse, index)
            }
            
            /* Rectangle { */
            /*     anchors.top: parent.top */
            /*     width: parent.width */
            /*     height: 1 */
            /*     color: util.QML_ITEM_BORDER_COLOR */
            /*     visible: index > 0 */
            /* } */
            
            RowLayout {

                id: rowLayout
                width: parent.width
                Layout.minimumHeight: height
                spacing: 6
                PK.CheckBox {
                    id: checkBox
                    textColor: util.textColor(selected, current)
                    checkState: active
                    onClicked: onRowClicked(null, index)
                    onCheckStateChanged: active = checkState
                }
                PK.TextInput {
                    property bool editMode: false
                    
                    id: textEdit
                    color: util.textColor(selected, current)
                    text: name == undefined ? '' : name
                    clip: true
                    readOnly: !editMode
                    selectByMouse: !readOnly
                    width: contentWidth
                    onEditingFinished: {
                        name = text
                        editMode = false
                    }
                    MouseArea {
                        width: parent.contentWidth
                        height: parent.contentHeight
                        enabled: !textEdit.editMode
                        onClicked: onRowClicked(mouse, index)
                        onDoubleClicked: {
                            if(flags & Qt.ItemIsEditable) {
                                textEdit.editMode = true
                                textEdit.forceActiveFocus()
                                textEdit.selectAll()
                            }
                        }
                    }
                }
                Rectangle { // spacer
                    height: 1
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    color: 'transparent'
                }
            }
        }
    }

    Rectangle { // border-bottom
        color: util.QML_ITEM_BORDER_COLOR
        height: 1
        Layout.fillWidth: true
    }

    PK.CrudButtons {
        id: buttons
        visible: showButtons
        Layout.fillWidth: true
        bottomBorder: false
        width: parent.width
        addButton: true
        addButtonEnabled: sceneModel ? !sceneModel.readOnly : false
        onAdd: model.addTag()
        removeButtonEnabled: list.count > 0 && currentIndex >= 0 && !sceneModel.readOnly
        removeButton: true
        onRemove: model.removeTag(currentIndex)
    }    

}
