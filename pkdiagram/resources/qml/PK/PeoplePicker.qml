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
    // The list of people used for auto-complete
    property var scenePeopleModel: ListModel {}
    property int currentIndex: -1
    property int count: list.count

    property var _existingPeople: []

    signal personAdded(string fullNameOrAlias, var personId)

    property var listView: list // for tests
    // for testing since delegate creation is async
    signal itemAddDone(Item item);

    function onRowClicked(mouse, row) {
        if(mouse && mouse.modifiers & Qt.ControlModifier) {
            currentIndex = -1
        } else {
            currentIndex = row
        }
    }

    function clear() {
        root.model.clear()
    }

    function setExistingPeople(people) {
        root._existingPeople = people
        for(var i = 0; i < people.length; i++) {
            var person = people[i];
            model.append({ fullNameOrAlias: person.fullNameOrAlias(), personId: person.itemId() })
        }
    }
    function existingPeople() {
        var people = []
        for(var i = 0; i < root.model.count; i++) {
            var personEntry = root.model.get(i)
            var person = sceneModel.item(personEntry.personId)
            people.push(person)
        }
        return people
    }

    function test_listView_items() {
        var ret = []
        for(var i = 0; i < list.contentItem.children.length; i++) {
            ret.push({ fullNameOrAlias: list.contentItem.children[i].textEdit.text, personId: list.contentItem.children[i].personId })
        }
        return ret
    }

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
            property var currentPersonTextEdit: null
            property var currentPersonItem: null
            signal currentTextChanged(string text)

            delegate: Rectangle {

                id: dRoot

                // for testing since delegate creation is async
                Component.onCompleted: { root.itemAddDone(this) }

                property bool selected: index == currentIndex
                property bool current: false
            
                width: parent ? parent.width : 0
                height: util.QML_ITEM_HEIGHT
                color: util.itemBgColor(selected, current, index % 2 == 1)

                MouseArea {
                    anchors.fill: parent
                    onClicked: onRowClicked(mouse, index)
                    onDoubleClicked: {
                        if(personId == -1 && !textEdit.editMode) {
                            list.currentPersonTextEdit = textEdit
                            list.currentPersonItem = dRoot
                            autoCompletePopup.open()
                            textEdit.editMode = true
                            textEdit.forceActiveFocus()
                            textEdit.selectAll()
                        }
                    }

                }

                RowLayout {

                    id: rowLayout
                    anchors.fill: parent
                    spacing: 0
                    PK.Text {
                        text: fullNameOrAlias
                        visible: personId != -1
                        Layout.leftMargin: util.QML_MARGINS
                    }
                    PK.TextInput {
                        property bool editMode: false
                        
                        id: textEdit
                        objectName: "textEdit"
                        color: util.textColor(selected, current)
                        text: fullNameOrAlias
                        clip: true
                        width: contentWidth
                        visible: personId == -1
                        selectByMouse: false
                        Layout.leftMargin: util.QML_MARGINS
                        onTextChanged: {
                            list.currentPersonTextEdit = textEdit
                            list.currentTextChanged(text)
                            if(text == '') {
                                autoCompletePopup.close()
                            } else {
                                autoCompletePopup.open()
                            }
                        }
                        onEditingFinished: {
                            print('fullNameOrAlias: ' + fullNameOrAlias + ', ' + text)
                            fullNameOrAlias = text
                            editMode = false
                            focus = false
                        }
                        onEditModeChanged: print('editModeChanged: ' + editMode)
                    }
                    Rectangle { // spacer
                        height: 1
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        color: 'transparent'
                    }
                }

                Rectangle {
                    id: isNewBox
                    objectName: "isNewBox"
                    width: newText.width + 10
                    height: newText.height + 3
                    color: "transparent"
                    border.color: util.QML_TEXT_COLOR
                    border.width: 1
                    radius: 3
                    opacity: 0.5
                    visible: personId == -1 && ! textEdit.editMode
                    Text {
                        id: newText
                        text: "new"
                        color: util.QML_TEXT_COLOR
                        anchors.centerIn: parent
                        visible: true
                    }
                    anchors {
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                        rightMargin: 15
                    }
                }
            }
        }

        Popup {
            id: autoCompletePopup
            y: list.y + util.QML_ITEM_HEIGHT
            width: list.width
            height: popupListView.height
            padding: 0
            contentItem: ListView {
                id: popupListView
                // implicitHeight: model ? (model.count * delegate.height) : 0
                function updateHeight(){
                    var totalHeight = 0;
                    for (var i = 0; i < popupListView.contentItem.children.length; i++) {
                        var item = popupListView.contentItem.children[i];
                        if(item.isListItem) {
                            if (item && item.visible) {
                                totalHeight += item.height;
                            }
                        }
                    }
                    popupListView.height = totalHeight;
                }
                Connections {
                    target: list
                    function onCurrentTextChanged(text) {
                        popupListView.updateHeight()
                    }
                }
                model: scenePeopleModel
                delegate: ItemDelegate {
                    text: name // modelData
                    width: autoCompletePopup.width
                    height: (name.toLowerCase().indexOf(currentPersonText.toLowerCase()) !== -1) ? util.QML_ITEM_HEIGHT : 0
                    visible: height > 0
                    palette.text: util.QML_TEXT_COLOR
                    background: Rectangle {
                        color: util.QML_ITEM_BG
                    }
                    property var isListItem: true
                    property var currentPersonText: list.currentPersonTextEdit ? list.currentPersonTextEdit.text : ''
                    onClicked: {
                        if(list.currentPersonTextEdit) {
                            list.currentPersonTextEdit.text = name
                            list.currentPersonTextEdit.focus = false
                        }
                        print("list.model.set(list.currentIndex, {'fullNameOrAlias': " + name + ", personId: " + personId + "})")
                        list.model.set(list.currentIndex, {"fullNameOrAlias": name, personId: personId});
                        autoCompletePopup.close();
                        root.personAdded(name, personId);
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
            onAdd: model.append({ fullNameOrAlias: '<full name>', personId: -1 })
            addButtonToolTip: 'Add a new person'
            removeButtonEnabled: list.count > 0 && currentIndex >= 0 && !sceneModel.readOnly
            removeButton: true
            removeButtonToolTip: 'Remove the selected person from this event'
            onRemove: model.remove(currentIndex)
        }
    }
}
