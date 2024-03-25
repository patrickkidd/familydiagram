import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.0
import "." 1.0 as PK
import PK.Models 1.0

Rectangle {

    id: root

    property var personName: ''
    property var person: null
    property var gender: null
    property bool isNewPerson: false
    property bool isSubmitted: false
    property var textEdit: pickerTextEdit

    signal submitted(var entry)

    // The list of people already selected in the AddAnythingDialog
    property var selectedPeopleModel: ListModel {
        objectName: 'selectedPeopleModel'
        // onCountChanged: print('onCountChanged: ' + count)
    }

    // The list of people used for auto-complete
    property var scenePeopleModel: ListModel {}

    height: util.QML_ITEM_HEIGHT
    color: util.QML_ITEM_BG // util.itemBgColor(true, true, true)

    function clear() {
        root.personName = ''
        root.person = null
        isNewPerson = false
        isSubmitted = false
    }

    function setFocus() {
        pickerTextEdit.forceActiveFocus()
    }

    function setExistingPerson(person) {
        // print('PersonPicker.setExistingPerson: ' + person)
        root.isSubmitted = true
        root.isNewPerson = false
        root.person = person
        root.personName = person.listLabel()
        root.selectedPeopleModel.append({ person: person, isNewPerson: false })
        autoCompletePopup.close()
        submitted(person)
    }

    function setNewPerson(personName) {
        // print('PersonPicker.setNewPerson: ' + personName)
        root.isSubmitted = true
        root.isNewPerson = true
        root.person = null
        root.personName = personName
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
            Layout.leftMargin: util.QML_MARGINS
        }
        PK.TextInput {
            id: pickerTextEdit
            objectName: "textEdit"
            color: util.textColor(true, true)
            text: root.person ? person.listLabel() : personName
            clip: true
            width: contentWidth
            visible: ! isSubmitted
            property bool selectingAutoCompleteItem: false
            Layout.leftMargin: util.QML_MARGINS
            Layout.minimumWidth: 40
            onTextChanged: {
                if(text && !isSubmitted) {
                    autoCompletePopup.matchText = text
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
            }
            onEditingFinished: {
                if(text && ! selectingAutoCompleteItem) {
                    // print('onEditingFinished: ' + text)
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
        id: genderComboBox
        objectName: "genderComboBox"
        width: 90
        height: util.QML_ITEM_HEIGHT - 10
        visible: isSubmitted
        model: util.PERSON_KIND_NAMES
        Layout.leftMargin: util.QML_MARGINS
        Layout.minimumWidth: 40
        anchors {
            right: parent.right
            verticalCenter: parent.verticalCenter
            rightMargin: 55
        }
        onCurrentIndexChanged: {
            root.gender = util.personKindFromIndex(currentIndex)
        }
        palette.button: 'transparent'
        indicator: Rectangle { color: 'transparent'; height: 0; width: 0}
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

    Popup {
        id: autoCompletePopup
        objectName: "autoCompletePopup"
        x: root.x - 10
        y: root.y + util.QML_ITEM_HEIGHT
        width: root.width + 20
        height: popupListView.height
        padding: 0
        property var matchText: ''
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
                for(var i=0; i < contentItem.children.length; i++) {
                    var child = contentItem.children[i]
                    if(child.isListItem && child.visible) {
                        ret += 1
                    }
                }
                return ret
            }
            delegate: ItemDelegate {
                id: dRoot
                property var isListItem: true
                property var person: scenePeopleModel.personForRow(index)
                property var matchesTypedPersonName: {
                    if(person && person.fullNameOrAlias().toLowerCase().indexOf(autoCompletePopup.matchText.toLowerCase()) !== -1) {
                        return true;
                    } else {
                        return false;
                    }
                }
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
                    textEdit.selectingAutoCompleteItem = true
                    root.forceActiveFocus()
                    var person = scenePeopleModel.personForRow(index)
                    root.setExistingPerson(person)
                    textEdit.selectingAutoCompleteItem = false
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
