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

    property var listView: list // for tests
    // for testing since delegate creation is async
    signal itemAddDone(Item item);

    function onRowClicked(mouse, row) {
        if(mouse && mouse.modifiers & Qt.ControlModifier) {
            root.currentIndex = -1
        } else {
            root.currentIndex = row
        }
        print('onRowClicked, root.currentIndex:' + root.currentIndex)
    }

    function clear() {
        root.model.clear()
    }

    function setExistingPeople(people) {
        root._existingPeople = people
        for(var i = 0; i < people.length; i++) {
            var person = people[i];
            model.append({ personName: person.listLabel(), person: person, isNewPerson: false})
        }
    }
    function existingPeople() {
        var people = []
        for(var i = 0; i < root.model.count; i++) {
            var personEntry = root.model.get(i)
            var person = sceneModel.item(personEntry.person.itemId())
            people.push(person)
        }
        return people
    }

    function alreadyInList(person) {
        if(person) {
            for(var i = 0; i < root.model.count; i++) {
                var personEntry = root.model.get(i)
                if(!personEntry.isNewPerson && personEntry.person.itemId() === person.itemId()) {
                    return true
                }
            }
        }
        return false
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
            signal currentTextChanged(string text)

            delegate: Rectangle {

                id: dRoot

                property bool selected: index == root.currentIndex
                property bool current: false

                width: parent ? parent.width : 0
                height: util.QML_ITEM_HEIGHT
                color: util.itemBgColor(selected, current, index % 2 == 1)

                MouseArea {
                    anchors.fill: parent
                    onClicked: onRowClicked(mouse, index)
                    onDoubleClicked: {
                        if(isNewPerson && !textEdit.visible) {
                            print('Opening for onDoubleClicked: ' + textEdit.text)
                            autoCompletePopup.open()
                            textEdit.forceActiveFocus()
                            textEdit.selectAll()
                        }
                    }
                }

                Component.onCompleted: {
                    if (isNewPerson) { // index === root.model.count - 1) {
                        textEdit.forceActiveFocus()
                        print('Component.onCompleted[isNewPerson]: ' + index + ', ' + root.model.count + ', focus: ' + textEdit.focus)                        
                    }
                    // for testing since delegate creation is async
                    root.itemAddDone(this)
                }

                RowLayout {

                    id: rowLayout
                    anchors.fill: parent
                    spacing: 0
                    PK.Text {
                        text: personName
                        visible: ! isNewPerson
                        Layout.leftMargin: util.QML_MARGINS
                    }
                    PK.TextInput {
                        id: textEdit
                        objectName: "textEdit"
                        color: util.textColor(selected, current)
                        text: model.person ? person.listLabel() : personName
                        clip: true
                        width: contentWidth
                        visible: isNewPerson
                        // selectByMouse: false
                        activeFocusOnPress: true
                        Layout.leftMargin: util.QML_MARGINS
                        Layout.minimumWidth: 40
                        onTextChanged: {
                            // list.currentPersonTextEdit = textEdit
                            print('onTextChanged: ' + text)
                            autoCompletePopup.matchText = text
                            list.currentTextChanged(text)
                            if(text == '') {
                                autoCompletePopup.close()
                            } else if(visible) {
                                // print('onTextChanged - filtering: ' + text + ', ' + scenePeopleModel.rowCount())
                                var total = 0
                                for(var i=0; i < scenePeopleModel.rowCount(); i++) {
                                    var person = scenePeopleModel.personForRow(i)
                                    var personName = person.fullNameOrAlias()
                                    // print(
                                    //     '    ' + i + ', ' + personName + 
                                    //     ', ' + personName.toLowerCase().indexOf(text.toLowerCase())
                                    // )
                                    if(personName.toLowerCase().indexOf(text.toLowerCase()) !== -1 && !root.alreadyInList(person)) {
                                        total += 1
                                    }
                                }
                                if(total > 0) {
                                    popupListView.height = total * util.QML_ITEM_HEIGHT
                                    autoCompletePopup.open()
                                } else {
                                    autoCompletePopup.close()
                                }
                            }
                        }
                        onEditingFinished: {
                            personName = text
                            focus = false
                        }
                    }
                    Rectangle { // spacer
                        height: 1
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        color: 'transparent'
                    }
                }

                // add a transparent png with the path "resource/checkbox-check.png"
                // to the project to use the following image
                PK.Image {
                    id: checkImage
                    source: "../checkbox-check.png"
                    width: 15
                    height: 15
                    invert: util.IS_UI_DARK_MODE
                    visible: ! isNewBox.visible 
                    anchors {
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                        rightMargin: 25
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
                    visible: isNewPerson && textEdit.visible
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
            x: list.x - 10
            y: list.y + (util.QML_ITEM_HEIGHT * list.model.count)
            width: list.width + 20
            height: popupListView.height
            padding: 0
            property var matchText: ''
            contentItem: ListView {
                id: popupListView
                objectName: "popupListView"
                model: scenePeopleModel
                delegate: ItemDelegate {
                    id: dRoot
                    text: fullNameOrAlias // modelData
                    width: autoCompletePopup.width
                    property var person: scenePeopleModel.personForRow(index)
                    property var matchesTypedPersonName: person && person.fullNameOrAlias().toLowerCase().indexOf(autoCompletePopup.matchText.toLowerCase()) !== -1
                    property var alreadyInList: root.alreadyInList(person)
                    height: visible ? util.QML_ITEM_HEIGHT : 0
                    visible: matchesTypedPersonName && ! alreadyInList
                    palette.text: util.QML_TEXT_COLOR
                    background: Rectangle {
                        color: util.QML_ITEM_BG
                    }
                    property var isListItem: true
                    onClicked: {
                        root.forceActiveFocus()
                        var person = scenePeopleModel.personForRow(index)
                        // print("list.model.set(" + root.currentIndex + ", {'personName': " + name + ", person: " + person + "})")
                        list.model.set(root.currentIndex, {personName: person.fullNameOrAlias(), person: person, isNewPerson: false });
                        autoCompletePopup.close();
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
            onAdd: {
                root.model.append({ personName: '', isNewPerson: true })
                root.currentIndex = root.model.count - 1
            }
            addButtonToolTip: 'Add a new person'
            removeButtonEnabled: list.count > 0 && root.currentIndex >= 0
            removeButton: true
            removeButtonToolTip: 'Remove the selected person from this event'
            onRemove: model.remove(root.currentIndex)
        }
    }
}
