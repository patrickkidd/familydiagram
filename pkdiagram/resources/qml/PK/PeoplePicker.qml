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
    property var currentEditingItemDelegate: null; // testing

    property var _existingPeople: []

    property var listView: list // for tests
    // for testing since delegate creation is async
    signal itemAddDone(Item item)
    signal itemRemoveDone(Item item)

    // function personDelegates() {
    //     var ret = []
    //     for(var i=0; i < list.contentItem.children.length; i++) {
    //         var child = list.contentItem.children[i]
    //         print('    ' + i + ', ' + child + ', ' + child.isPersonDelegate)
    //         if(child.isPersonDelegate)
    //             ret.push(child)
    //     }
    //     return ret
    // }

    function onPersonRowClicked(mouse, row) {
        if(mouse && mouse.modifiers & Qt.ControlModifier) {
            root.currentIndex = -1
        } else {
            root.currentIndex = row
        }
        print('onPersonRowClicked, root.currentIndex:' + root.currentIndex)
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
                property bool isPersonDelegate: true
                property bool isSubmitted: false
                onIsSubmittedChanged: {
                    print('isSubmitted: autoCompletePopup.close()')
                    autoCompletePopup.close()
                }

                width: parent ? parent.width : 0
                height: util.QML_ITEM_HEIGHT
                color: util.itemBgColor(selected, current, index % 2 == 1)

                MouseArea {
                    anchors.fill: parent
                    onClicked: onPersonRowClicked(mouse, index)
                }

                Component.onCompleted: {
                    if (isNewPerson) { // index === root.model.count - 1) {
                        textEdit.forceActiveFocus()
                        dRoot.isSubmitted = false
                        // print('Component.onCompleted[isNewPerson]: ' + index + ', ' + root.model.count + ', focus: ' + textEdit.focus)                        
                    } else {
                        dRoot.isSubmitted = true
                    }
                    // for testing since delegate creation is async
                    root.itemAddDone(dRoot)
                }

                Component.onDestruction: {
                    // for testing since
                    root.itemRemoveDone(this)
                }

                RowLayout {

                    id: rowLayout
                    anchors.fill: parent
                    spacing: 0
                    PK.Text {
                        id: personNameText
                        text: personName
                        visible: isSubmitted
                        Layout.leftMargin: util.QML_MARGINS
                    }
                    PK.TextInput {
                        id: textEdit
                        objectName: "textEdit"
                        color: util.textColor(selected, current)
                        text: model.person ? person.listLabel() : personName
                        clip: true
                        width: contentWidth
                        visible: ! isSubmitted
                        onVisibleChanged: print('textEdit.visible: ' + visible + ', isSubmitted: ' + isSubmitted)
                        Layout.leftMargin: util.QML_MARGINS
                        Layout.minimumWidth: 40
                        onFocusChanged: {
                            if(focus) {
                                root.currentEditingItemDelegate = dRoot
                                print('onFocusChanged: root.currentEditingItemDelegate = ' + dRoot)
                            }
                        }
                        onTextChanged: {
                            // list.currentTextChanged(text)
                            if(text && !isSubmitted) {
                                // print('onTextChanged - filtering: ' + text + ', isNewPerson: ' + isNewPerson + ', visible: ' + visible + ', ' + scenePeopleModel.rowCount())
                                autoCompletePopup.matchText = text
                                // root.currentEditingItemDelegate = dRoot
                                // print('onClicked: root.currentEditingItemDelegate = ' + dRoot)
                                var numMatches = 0
                                for(var i=0; i < scenePeopleModel.rowCount(); i++) {
                                    var person = scenePeopleModel.personForRow(i)
                                    var personName = person.fullNameOrAlias()
                                    var textMatches = personName.toLowerCase().indexOf(text.toLowerCase()) != -1 ? true : false
                                    // print(
                                    //     '    ' + i + ', ' + personName + 
                                    //     ', ' + textMatches
                                    // )
                                    if(textMatches && !root.alreadyInList(person)) {
                                        numMatches += 1
                                    }
                                }
                                if(numMatches > 0) {
                                    popupListView.height = numMatches * util.QML_ITEM_HEIGHT
                                    // print('Showing ' + numMatches + ' matches for ' + text + ' , setting height: ' + popupListView.height)
                                    autoCompletePopup.open()
                                } else if(autoCompletePopup.visible) {
                                    // print('Hiding autoCompletePopup for no text match.')
                                    autoCompletePopup.close()
                                }
                            }
                        }
                        onEditingFinished: {
                            if(text) {
                                personName = text
                                print('onEditingFinished: ' + text + ', ' + root.currentEditingItemDelegate + ', isSubmitted = true')
                                if(root.currentEditingItemDelegate) {
                                    root.currentEditingItemDelegate.isSubmitted = true
                                    root.currentEditingItemDelegate = null
                                }
                                focus = false
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

                // add a transparent png with the path "resource/checkbox-check.png"
                // to the project to use the following image
                PK.Image {
                    id: checkImage
                    objectName: "checkImage"
                    source: "../checkbox-check.png"
                    width: 15
                    height: 15
                    invert: util.IS_UI_DARK_MODE
                    visible: isSubmitted && ! isNewPerson
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
                    visible: isSubmitted && isNewPerson
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
            objectName: "autoCompletePopup"
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
                        print('onClicked: isSubmitted = true')
                        root.currentEditingItemDelegate.isSubmitted = true
                        root.currentEditingItemDelegate = null
                        list.model.set(root.currentIndex, {personName: person.fullNameOrAlias(), person: person, isNewPerson: false });
                        // if(autoCompletePopup.visible) {
                        //     print('Hiding autoCompletePopup for item selected: ' + person.fullNameOrAlias())
                        //     autoCompletePopup.close();
                        // }
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
