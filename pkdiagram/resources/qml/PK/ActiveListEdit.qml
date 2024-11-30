import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.12
import "." 1.0 as PK



Rectangle {

    id: root

    color: 'transparent'
    border {
        width: 1
        color: util.QML_ITEM_BORDER_COLOR
    }

    property var model: null
    property bool showButtons: true
    property int currentIndex: -1
    property int count: listViewItem.count
    property var listView: listViewItem // doesn't work with `alias` for some reason
    property alias crudButtons: crudButtons
    property var addButton: true
    property var removeButton: true

    property var emptyText: ''
    property var noItemsText: noItemsText

    function onRowClicked(mouse, row) {
        if(mouse && mouse.modifiers & Qt.ControlModifier) {
            currentIndex = -1
        } else {
            currentIndex = row
        }
    }

    property bool noItemsShown: {
        if(model == null) {
            return true
        } else if(listViewItem.count == 0) {
            return true
        } else {
            return false
        }
    }

    Rectangle {
        color: "transparent"
        visible: noItemsShown
        anchors.fill: parent

        PK.NoDataText {
            id: noItemsText
            text: root.emptyText
        }
    }

    ColumnLayout {
        
        spacing: 0
        anchors.fill: parent
        anchors.margins: 1
        visible: ! noItemsShown

        ListView {
            id: listViewItem
            clip: true
            model: root.model
            Layout.fillWidth: true
            Layout.fillHeight: true

            property var delegates: []
            
            delegate: Rectangle {

                property bool selected: index == currentIndex
                property bool current: false
                property int iTag: index
                property var itemName: name
                property alias checkBox: checkBox
                property alias textEdit: textEdit

                width: parent ? parent.width : 0
                height: util.QML_ITEM_HEIGHT // rowLayout.height
                color: util.itemBgColor(selected, current, index % 2 == 1)

                Component.onCompleted: {
                    listViewItem.delegates.push(this)
                }

                Component.onDestruction: {
                    listViewItem.delegates.splice(listViewItem.delegates.indexOf(this), 1)
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
                        onCheckStateChanged: {
                            if(active != checkState) {
                                active = checkState
                            }
                        }
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
                    }

                    Rectangle { // spacer
                        height: 1
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        color: 'transparent'
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    anchors.leftMargin: checkBox.y + checkBox.width
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
        }

        Rectangle { // border-bottom
            color: util.QML_ITEM_BORDER_COLOR
            height: 1
            Layout.fillWidth: true
        }

        PK.CrudButtons {
            id: crudButtons
            objectName: "crudButtons"
            visible: showButtons
            Layout.fillWidth: true
            bottomBorder: false
            width: parent.width
            addButton: root.addButton
            addButtonEnabled: sceneModel ? !sceneModel.readOnly : false
            onAdd: model.addTag()
            removeButtonEnabled: listViewItem.count > 0 && currentIndex >= 0 && !sceneModel.readOnly
            removeButton: root.removeButton
            onRemove: model.removeTag(currentIndex)
        }

    }

}
