import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.0
import "." 1.0 as PK
import PK.Models 1.0

PK.GroupBox {

    id: root
    padding: 1

    // Stores the outputed list of people
    property var model: ListModel {}
    // The list of people used for auto-complete
    property var scenePeopleModel: ListModel {}
    property var selectedPeopleModel: ListModel {
        objectName: 'selectedPeopleModel'
    }
    property int currentIndex: -1
    property int count: list.count
    property var currentEditingItemDelegate: null; // testing

    property var listView: list // for tests
    // for testing since delegate creation is async
    signal itemAddDone(Item item)
    signal itemRemoveDone(Item item)

    function onPersonRowClicked(mouse, row) {
        if(mouse && mouse.modifiers & Qt.ControlModifier) {
            root.currentIndex = -1
        } else {
            root.currentIndex = row
        }
    }

    function clear() {
        root.model.clear()
    }

    function peopleEntries() {
        var entries = []
        for(var i = 0; i < root.model.count; i++) {
            var personPicker = root.pickerAtIndex(i)
            entries.append(picker.personEntry())
        }
        return entries
    }

    function setExistingPeople(people) {
        for(var i = 0; i < people.length; i++) {
            var person = people[i];
            // print('setExistingPeople: ' + i + ', ' + person.listLabel() + ', ' + person)
            model.append({ personName: person.listLabel(), person: person, isNewPerson: false})
        }
    }
    // function existingPeople() {
    //     var people = []
    //     for(var i = 0; i < root.model.count; i++) {
    //         var personEntry = root.model.get(i)
    //         var person = sceneModel.item(personEntry.person.itemId())
    //         people.push(person)
    //     }
    //     return people
    // }
    function pickerAtIndex(index) {
        var personPickerIndex = -1;
        print('pickerAtIndex(' + index + ')')
        for(var i=0; i < list.contentItem.children.length; i++) {
            var item = list.contentItem.children[i];
            if(item.isPersonPicker) {
                personPickerIndex++
                print(' found PK.PersonPicker at index: ' + personPickerIndex)
                if(personPickerIndex == index) {
                    print(' <---- Returning PersonPicker: '  + item)
                    return item
                }
            }
        }
        print('Could not find genderBox for index: ' + index)
    }

    function genderBox(index) {
        var personPickerIndex = -1;
        print('genderBox(' + index + ')')
        var picker = pickerAtIndex(index)
        if(picker) {
            print('picker: ' + picker)
            return picker.genderBox
        }
        print('Could not find genderBox for index: ' + index)
    }

    Component.onCompleted: background.border.color = util.QML_ITEM_BORDER_COLOR

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

            delegate: PK.PersonPicker {

                id: dRoot

                // assign this PK.PersonPicker property `person` to the model's `person` property
                // so that the model can be updated when the person is updated

                property bool isPersonPicker: true
                property bool selected: index == root.currentIndex
                property bool current: false
                width: parent ? parent.width : 0
                height: util.QML_ITEM_HEIGHT
                color: util.itemBgColor(selected, current, index % 2 == 1)
                scenePeopleModel: root.scenePeopleModel
                selectedPeopleModel: root.selectedPeopleModel
                property bool isInitializingWithSubmission: false

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        print('PersonPicker.onClick: ' + index + ', ' + mouse.modifiers + ', ' + mouse.accepted)
                        onPersonRowClicked(mouse, index)
                        mouse.accepted = false
                    }
                    propagateComposedEvents: true
                }

                Component.onCompleted: {
                    if(model.person !== undefined) {
                        dRoot.isInitializingWithSubmission = true
                        setExistingPerson(model.person)
                    } else {
                        dRoot.setFocus()
                    }
                    // for testing since delegate creation is async
                    root.itemAddDone(dRoot)
                }

                Component.onDestruction: root.itemRemoveDone(dRoot)
                onSubmitted: function(personOrName) {
                    // print('onSubmitted: ' + personOrName + ', isInitializingWithSubmission: ' + isInitializingWithSubmission)
                    if(!isInitializingWithSubmission) {
                        // print('   root.model.set(' + model.index + '): ' + personOrName)
                        if(typeof personOrName === 'string') {
                            root.model.set(model.index, { personName: personOrName, isNewPerson: true })
                        } else {
                            root.model.set(model.index, { person: personOrName, isNewPerson: false })
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
            id: buttons
            objectName: "buttons"
            Layout.fillWidth: true
            bottomBorder: false
            width: parent.width
            addButton: true
            onAdd: {
                root.model.append({ personName: "", isNewPerson: true })
                root.currentIndex = root.model.count - 1
            }
            addButtonToolTip: 'Add a new person'
            removeButtonEnabled: list.count > 0 && root.currentIndex >= 0
            removeButton: true
            removeButtonToolTip: 'Remove the selected person from this event'
            onRemove: {
                var entry = model.get(root.currentIndex)
                if(entry.person) {
                    for(var i = 0; i < selectedPeopleModel.count; i++) {
                        var person = selectedPeopleModel.get(i)
                        if(person.person.itemId() === entry.person.itemId()) {
                            selectedPeopleModel.remove(i)
                        }
                    }
                }
                model.remove(root.currentIndex)
                root.currentIndex = -1
            } 
        }
    }
}
