import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.0
import "." 1.0 as PK
import PK.Models 1.0
import "../js/Global.js" as Global


Rectangle {

    id: root

    // The first item in this chain for KeyNavigation.tab on an external item
    readonly property var firstTabItem: pickerTextEdit
    // The first item in this chain for KeyNavigation.backtab on an external item
    readonly property var lastTabItem: genderBox
    // Explicit keyNavigation.tab set on the last item in this chain
    property var tabItem: null
    // Explicit keyNavigation.backtab set on the first item in this chain
    property var backTabItem: null

    color: util.QML_ITEM_BG
    property var personName: ''
    property var borderWidth: 0
    property var borderColor: 'transparent'
    property var spacing: util.QML_ITEM_MARGINS - 5

    property var person: null
    property var gender: null
    property bool isNewPerson: false
    property bool isSubmitted: false
    property bool isDirty: false
    property var textEdit: pickerTextEdit // still need this one?

    signal numVisibleAutoCompleteItemsUpdated(var numVisibleItems) // for testing
    signal submitted(var entry)

    // The list of people already selected in the AddAnythingDialog
    property var selectedPeopleModel: ListModel {
        objectName: 'selectedPeopleModel'
        // onCountChanged: print('onCountChanged: ' + count)
    }

    // The list of people used for auto-complete
    property var scenePeopleModel: ListModel {}

    function clear() {
        // print('>>> PersonPicker.clear() ' + root.objectName)
        if(isSubmitted) {
            for(var i=0; i < root.selectedPeopleModel.rowCount(); i++) {
                var entry = root.selectedPeopleModel.get(i);
                print('    ' + i + ', ' + entry.person)
                if(entry.person && root.person && entry.person.itemId() === root.person.itemId()) {
                    print('    removing ' + entry.person.fullNameOrAlias())
                    root.selectedPeopleModel.remove(i)
                    break
                }
            }
            
        }
        root.personName = ''
        root.person = null
        root.gender = null
        root.isNewPerson = false
        root.isSubmitted = false
        root.isDirty = false
        // print('<<< PersonPicker.clear()')
    }

    function setFocus() {
        pickerTextEdit.forceActiveFocus()
    }

    function personEntry() {
        // print('PersonPicker.personEntry: ' + root.personName + ', ' + root.person + ', ' + person.gender())
        return {
            person: root.person,
            personName: root.personName,
            gender: root.gender,
            isNewPerson: root.isNewPerson
        }
    }

    function setExistingPerson(person) {
        print('PersonPicker[' + root.objectName + '].setExistingPerson: ' + person.listLabel())
        root.isDirty = true
        root.isSubmitted = true
        root.isNewPerson = false
        root.person = person
        root.personName = person.listLabel()
        root.gender = person.gender()
        genderBox.currentIndex = util.personKindIndexFromKind(root.gender)
        // print('genderBox.currentIndex: ' + genderBox.currentIndex)
        root.selectedPeopleModel.append({ person: person, isNewPerson: false, gender: person.gender()})
        autoCompletePopup.close()
        submitted(person)
    }

    function setNewPerson(personName) {
        print('PersonPicker.setNewPerson: ' + personName)
        root.isDirty = true
        root.isSubmitted = true
        root.isNewPerson = true
        root.person = null
        root.personName = personName
        root.gender = util.PERSON_KIND_MALE
        autoCompletePopup.close()
        submitted(personName)
    }

    function alreadySelected(person) {
        // print('alreadySelected: ' + root.selectedPeopleModel.count + ' people selected')
        for(var i = 0; i < root.selectedPeopleModel.count; i++) {
            var selectedPerson = root.selectedPeopleModel.get(i)
            // print('    ' + i + ', selectedPerson: ' + selectedPerson.person.fullNameOrAlias())
            // print(
            //     '   ' + i + ', ' + selectedPerson.person.fullNameOrAlias() + 
            //     ', selectedPerson.isNewPerson: ' + selectedPerson.isNewPerson + 
            //     ', ' + selectedPerson.person.itemId() + ', ' + person.itemId()
            // )
            if(!selectedPerson.isNewPerson && selectedPerson.person.itemId() === person.itemId()) {
                return true
            }
        }
        return false
    }

    RowLayout {

        id: rowLayout
        anchors.fill: parent
        spacing: 0
        PK.Text {
            id: personNameText
            text: root.personName
            visible: isSubmitted
            Layout.leftMargin: util.QML_ITEM_MARGINS
        }
        PK.TextInput {
            id: pickerTextEdit
            objectName: "textEdit"
            color: util.textColor(true, true)
            text: root.person ? root.person.listLabel() : root.personName
            clip: true
            width: contentWidth
            visible: ! isSubmitted
            KeyNavigation.tab: genderBox
            KeyNavigation.backtab: root.backTabItem
            property bool selectingAutoCompleteItem: false
            Layout.leftMargin: util.QML_ITEM_MARGINS
            Layout.minimumWidth: 40
            onTextChanged: {
                // print('[' + root.objectName + '].onTextChanged: ' + text)
                if(text && !isSubmitted) {
                    var numMatches = 0
                    var debug_matches = [];
                    for(var i=0; i < scenePeopleModel.rowCount(); i++) {
                        var rowPerson = scenePeopleModel.personForRow(i)
                        var personName = rowPerson.fullNameOrAlias()
                        var textMatches = personName.toLowerCase().indexOf(text.toLowerCase()) != -1 ? true : false
                        if(textMatches && !root.alreadySelected(rowPerson)) {
                            numMatches += 1
                            debug_matches.push(personName)
                        }
                    }
                    // print('onTextChanged - filtering: "' + text + '" ' + debug_matches)
                    if(numMatches > 0) {
                        popupListView.height = numMatches * util.QML_ITEM_HEIGHT
                        // print('Showing ' + numMatches + ' matches for ' + text + ' , setting height: ' + popupListView.height)
                        autoCompletePopup.open()
                    } else if(autoCompletePopup.visible) {
                        // print('Hiding autoCompletePopup for no text match.')
                        autoCompletePopup.close()
                    }
                }
                if(text) {
                    root.isDirty = true
                }
            }
            Keys.onTabPressed: {
                Global.focusNextItemInFocusChain(KeyNavigation.tab, true)
                event.accepted = true
            }
            onAccepted: {
                if(text && ! selectingAutoCompleteItem) {
                    // print('onAccepted: ' + text)
                    root.setNewPerson(text)
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

    PK.ComboBox {
        id: genderBox
        objectName: "genderBox"
        z: 2
        width: 90
        height: util.QML_ITEM_HEIGHT - 10
        visible: isSubmitted
        model: util.PERSON_KIND_NAMES
        indicator: Rectangle { color: 'transparent'; height: 0; width: 0}
        property var test_popup: popup
        KeyNavigation.backtab: pickerTextEdit
        KeyNavigation.tab: root.tabItem
        Layout.leftMargin: util.QML_ITEM_MARGINS
        Layout.minimumWidth: 40
        anchors {
            right: checkImage.left
            verticalCenter: parent.verticalCenter
            rightMargin: root.spacing + 10
        }
        palette.button: 'transparent'
        onCurrentIndexChanged: {
            var newGender = util.personKindFromIndex(currentIndex)
            if(newGender != root.gender) {
                // print('genderBox.currentIndexChanged: ' + currentIndex + ', ' + newGender)
                root.gender = util.personKindFromIndex(currentIndex)
            }
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
            rightMargin: util.QML_ITEM_MARGINS
        }
    }

    Rectangle {
        id: isNewBox
        objectName: "isNewBox"
        width: newText.width + 7
        height: newText.height + 3
        color: "transparent"
        radius: 3
        opacity: 0.5
        visible: isSubmitted && isNewPerson
        border.color: util.QML_TEXT_COLOR
        border.width: 1
        Text {
            id: newText
            text: "new"
            color: util.QML_TEXT_COLOR
            visible: true
            font.pixelSize: 10
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -1 // render nudge
            anchors.horizontalCenterOffset: 1 // render nudge
        }
        anchors {
            right: parent.right
            verticalCenter: parent.verticalCenter
            rightMargin: root.spacing
        }
    }

    Popup {
        id: autoCompletePopup
        objectName: "autoCompletePopup"
        x: -10
        y: util.QML_ITEM_HEIGHT // show just below the picker
        width: root.width + 20
        height: popupListView.height
        padding: 0
        contentItem: ListView {
            id: popupListView
            objectName: "popupListView"
            model: scenePeopleModel
            layer.enabled: true
            layer.effect: DropShadow {
                color: "black"
                radius: 8
                samples: 16
                source: popupListView
            }
            property var numVisibleItems: {
                var ret = 0
                // print("numVisibleItems: pickerTextEdit.text == '" + pickerTextEdit.text + "'")
                for(var i=0; i < contentItem.children.length; i++) {
                    var child = contentItem.children[i]
                    // print('    child: ' + child.isListItem + ', visible: ' + child.visible)
                    if(child.isListItem && child.visible) {
                        ret += 1
                    }
                }
                // print('    <--- numVisibleItems: ' + ret)
                root.numVisibleAutoCompleteItemsUpdated(ret)
                return ret
            }
            delegate: ItemDelegate {
                id: dRoot
                property var isListItem: true
                property var person: scenePeopleModel.personForRow(index)
                property var matchesTypedPersonName: person && person.matchesName(pickerTextEdit.text)
                property var alreadySelected: if(person) root.alreadySelected(person)
                text: fullNameOrAlias // modelData
                width: autoCompletePopup.width
                height: visible ? util.QML_ITEM_HEIGHT : 0
                visible: matchesTypedPersonName && ! alreadySelected
                palette.text: util.QML_TEXT_COLOR
                background: Rectangle {
                    color: util.QML_ITEM_BG
                }
                onClicked: {
                    // print('selectingAutoCompleteItem = true')
                    textEdit.selectingAutoCompleteItem = true
                    root.forceActiveFocus()
                    var person = scenePeopleModel.personForRow(index)
                    root.setExistingPerson(person)
                    textEdit.selectingAutoCompleteItem = false
                    // print('selectingAutoCompleteItem = false')
                }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: !root.isSubmitted
        onClicked: pickerTextEdit.forceActiveFocus()
    }
}

