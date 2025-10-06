import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.0
import "." 1.0 as PK
import PK.Models 1.0


PK.GroupBox {

    id: root

    padding: 1

    // The first item in this chain for KeyNavigation.tab on an external item
    readonly property var firstTabItem: buttons.addButtonItem
    // The first item in this chain for KeyNavigation.backtab on an external item
    readonly property var lastTabItem: buttons.removeButtonItem
    // Explicit keyNavigation.tab set on the last item in this chain
    property var tabItem
    // Explicit keyNavigation.backtab set on the first item in this chain
    property var backTabItem


    Component.onCompleted: background.border.color = util.QML_ITEM_BORDER_COLOR

    // Stores the outputed list of people
    property var model: ListModel {}
    // The list of people used for auto-complete
    property var scenePeopleModel: ListModel {}
    property var selectedPeopleModel: ListModel {}
    property int currentIndex: -1
    property int count: list.count
    property var currentEditingItemDelegate: null; // testing

    // Only so FormField will show the clear button
    property var isDirty: root.model.count > 0

    property var listView: list // for tests
    property var buttons: buttons
    // for testing since delegate creation is async
    signal itemAddDone(Item item)
    signal itemRemoveDone(Item item)
    property var callAfterDone: null

    function onPersonRowClicked(mouse, row) {
        if(mouse && mouse.modifiers & Qt.ControlModifier) {
            root.currentIndex = -1
        } else {
            root.currentIndex = row
        }
    }

    function clear() {
        // Remove all entries in model from selectedPeopleModel
        for(var i = 0; i < root.model.count; i++) {
            var entry = root.model.get(i)
            if(entry.person) {
                for(var j = 0; j < selectedPeopleModel.count; j++) {
                    var person = selectedPeopleModel.get(j)
                    if(person.person.itemId() === entry.person.itemId()) {
                        selectedPeopleModel.remove(j)
                        break
                    }
                }
            }
        }


        // print('>>> PeoplePicker.clear() ' + root.objectName)
        root.model.clear()
        // print('<<< PeoplePicker.clear()')

    }

    function addEntry(callback) {
        root.model.append({ personName: "", isNewPerson: true, personId: -1 })
        root.currentIndex = root.model.count - 1
        // util.debug('addEntry() root.model.count: ' + root.model.count + ', callback: ' + callback)
        callAfterDone = callback
    }

    function focusEntry(index) {
        // print('>>> PeoplePicker.focusEntry(' + index + ') ')
        pickerAtIndex(index).focusTextEdit()
        // print('<<< PeoplePicker.focusEntry(' + index + ') ')
    }

    function peopleEntries() {
        var entries = []
        // print(root.objectName + '.peopleEntries -  rowCount: ' + root.model.rowCount() + ', list.contentItem.children.length: ' + list.contentItem.children.length)
        for(var i = 0; i < root.model.rowCount(); i++) {
            var personPicker = root.pickerAtIndex(i)
            var entry = personPicker.personEntry()
            // print(entry.gender)
            entries.push(entry)
        }
        // print('    entries.length: ' + entries.length)
        return entries
    }

    function setExistingPeopleIds(personIds) {
        print(root.objectName + '.setExistingPeopleIds: ' + personIds.length)
        var people = []
        for(var i = 0; i < personIds.length; i++) {
            people.push(sceneModel.item(personIds[i]))
        }
        root.setExistingPeople(people)
    }

    function setExistingPeople(people) {
        // print(root.objectName + '.setExistingPeople: ' + people.length)
        for(var i = 0; i < people.length; i++) {
            addExistingPerson(people[i])
        }
    }

    function addExistingPerson(person) {
        // print(root.objectName + '.addExistingPerson: ' + person)
        root.model.append({ personName: person.listLabel(), person: person, isNewPerson: false, gender: person.gender(), personId: person.itemId()})
        // print('    ' + i + ': ' + person.listLabel() + ', ' + person + ', ' + person.gender())
    }

    function pickerAtIndex(index) {
        var personPickerIndex = -1;
        util.debug(root.objectName + '.pickerAtIndex(' + index + ')')
        for(var i=0; i < list.contentItem.children.length; i++) {
            var item = list.contentItem.children[i];
            if(item.isPersonPicker) {
                personPickerIndex++
                util.debug(' found PK.PersonPicker at index: ' + personPickerIndex)
                if(personPickerIndex == index) {
                    util.debug(' <---- Returning PersonPicker: '  + item + ', personName: ' + item.personName + ', person: ' + item.person + ', gender: ' + item.gender)
                    return item
                }
            }
        }
        util.warning('Could not find picker for index: ' + index)
    }

    function genderBox(index) {
        var personPickerIndex = -1;
        // print('genderBox(' + index + ')')
        var picker = pickerAtIndex(index)
        if(picker) {
            // print('picker: ' + picker)
            return picker.genderBox
        }
        util.warning('Could not find genderBox for index: ' + index)
    }

    function allSubmitted() {
        // print('allSubmitted: ' + root.objectName + ', model.count: ' + root.model.count)
        var allSubmitted = true
        for(var i = 0; i < root.model.count; i++) {
            var personPicker = pickerAtIndex(i)
            // print('  personPicker ' + i + ': ' + personPicker + ', isSubmitted: ' + personPicker.isSubmitted)
            if(!personPicker.isSubmitted) {
                return false
            }
        }
        return true
    }


    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ListView {
            id: list
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
                    z: 1 // below controls still active after submitted, e.g. genderBox
                    onClicked: {
                        // print('PeoplePicker.onClick: ' + index + ', ' + mouse.modifiers + ', ' + mouse.accepted)
                        onPersonRowClicked(mouse, index)
                        mouse.accepted = false
                    }
                    propagateComposedEvents: true
                }
                Component.onCompleted: {
                    // Turns out that QObject references in the model index
                    // data, e.g. model.person, are not initialized before the
                    // delegate and can sometimes be null. Even adding a signal
                    // handler for model.person changed is not reliable, making
                    // it impossible to have a reliable constructor that
                    // actually has all the model data. However, it turns out
                    // that primitives like bool and int are available right
                    // from the beginning, so we pass person id's and then get
                    // the QObject instance later.
                    if(model.personId == -1) {
                        dRoot.textEdit.focus = true
                        root.itemAddDone(dRoot)
                        if(callAfterDone) {
                            util.debug('callAfterDone: ' + callAfterDone)
                            callAfterDone()
                            callAfterDone = null
                        }
                    } else {
                        dRoot.isInitializingWithSubmission = true
                        dRoot.setExistingPerson(sceneModel.item(model.personId))
                        root.itemAddDone(dRoot)
                    }
                }
                Component.onDestruction: root.itemRemoveDone(dRoot)
                onSubmitted: function(personOrName) {
                    // print('onSubmitted: ' + personOrName + ', isInitializingWithSubmission: ' + isInitializingWithSubmission)
                    if(!isInitializingWithSubmission) {
                        // print('   root.model.set(' + model.index + '): ' + personOrName)
                        if(typeof personOrName === 'string') {
                            root.model.set(model.index, { personName: personOrName, isNewPerson: true, gender: util.PERSON_KIND_MALE, personId: -1})
                        } else {
                            root.model.set(model.index, { person: personOrName, isNewPerson: false, gender: person.gender(), personId: person.itemId()})
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
            Layout.fillWidth: true
            bottomBorder: false
            width: parent.width
            addButton: true
            onAdd: {
                root.addEntry(function() {
                    util.debug('callAfterDone: ' + (root.model.count - 1))
                    root.focusEntry(root.model.count - 1)
                })
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
