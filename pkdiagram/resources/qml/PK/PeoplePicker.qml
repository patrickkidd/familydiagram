import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." 1.0 as PK
import PK.Models 1.0

PK.GroupBox {

    id: root
    padding: 1

    // Stores the outputed list of people
    property var model: ListModel {}
    property var scenePeopleModel: ListModel {}
    property int currentIndex: -1
    property int count: list.count
    property var listView: list // for tests

    // for testing since delegate creation is async
    signal itemAddDone(Item item);

    onScenePeopleModelChanged: autoCompleteModel.sourceModel = scenePeopleModel

    function onRowClicked(mouse, row) {
        if(mouse && mouse.modifiers & Qt.ControlModifier) {
            currentIndex = -1
        } else {
            currentIndex = row
        }
    }

    function clear() {
        root.model.clear()
        autoCompleteModel.updateFilter('')
    }

    ListModel {
        id: autoCompleteModel
        property var sourceModel: ListModel {}

        function updateFilter(filterText) {
            this.clear()
            if (sourceModel) {
                for (let i = 0; i < sourceModel.rowCount(); ++i) {
                    let index = sourceModel.index(i, 0);
                    let name = sourceModel.data(index);
                    // print(i + ', ' + name + ': ' + name.toLowerCase().indexOf(filterText.toLowerCase()))
                    if (name.toLowerCase().indexOf(filterText.toLowerCase()) !== -1) {
                        // print('   ->> ' + name)
                        this.append({ name: name });
                    }
                }
            }            
        }
    }

    function test_listViewItem(index) {
        return list.contentItem.children[index]
    }

    // property var listContentItem: list.contentItem

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ListView {
            id: list
            objectName: "list"
            clip: true
            model: root.model
            contentWidth: width
            Layout.fillWidth: true
            Layout.fillHeight: true

            delegate: Rectangle {

                // for testing since delegate creation is async
                Component.onCompleted: root.itemAddDone(this)

                property bool selected: index == currentIndex
                property bool current: false

                width: parent ? parent.width : 0
                height: util.QML_ITEM_HEIGHT
                onHeightChanged: print('height: ' + height)
                color: util.itemBgColor(selected, current, index % 2 == 1)

                MouseArea {
                    anchors.fill: parent
                    onClicked: onRowClicked(mouse, index)
                }

                RowLayout {

                    id: rowLayout
                    anchors.fill: parent
                    spacing: 0
                    PK.TextInput {
                        property bool editMode: false
                        
                        id: textEdit
                        objectName: "textEdit"
                        color: util.textColor(selected, current)
                        text: fullNameOrAlias + (isNew ? " (New)" : "")
                        clip: true
                        width: contentWidth
                        Layout.leftMargin: util.QML_MARGINS
                        onTextChanged: print(text)
                        onEditingFinished: {
                            print('fullNameOrAlias: ' + fullNameOrAlias + ', ' + text)
                            fullNameOrAlias = text
                            editMode = false
                            focus = false
                        }
                        MouseArea {
                            width: parent.contentWidth
                            height: parent.contentHeight
                            enabled: !textEdit.editMode
                            onClicked: onRowClicked(mouse, index)
                            onDoubleClicked: {
    //                            if(flags & Qt.ItemIsEditable) {
                                    textEdit.editMode = true
                                    textEdit.forceActiveFocus()
                                    textEdit.selectAll()                                
    //                          }
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

        Popup {
            id: autoCompletePopup
            y: list.y + list.height
            width: list.width
            height: Math.min(autoCompleteModel.count * util.QML_ITEM_HEIGHT, 200)
            padding: 0
            contentItem: ListView {
                id: popupListView
                implicitHeight: model ? (model.count * delegate.height) : 0
                model: autoCompleteModel
                delegate: ItemDelegate {
                    text: name // modelData
                    width: autoCompletePopup.width
                    palette.text: util.QML_TEXT_COLOR
                    background: Rectangle {
                        color: util.QML_ITEM_BG
                    }
                    onClicked: {
                        root.model.append({"fullNameOrAlias": modelData, id: 123, "isNew": false});
                        autoCompletePopup.close();
                        personAdded(names[0], names[1], false);
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
            objectName: "buttons"
            Layout.fillWidth: true
            bottomBorder: false
            width: parent.width
            addButton: true
            onAdd: model.append({ fullNameOrAlias: '', id: -1, isNew: true })
            removeButtonEnabled: list.count > 0 && currentIndex >= 0 && !sceneModel.readOnly
            removeButton: true
            onRemove: model.remove(currentIndex)
        }
    }
}
