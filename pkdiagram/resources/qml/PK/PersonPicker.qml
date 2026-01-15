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
    property var spacing: util.QML_ITEM_MARGINS - 5

    property var person: null
    property var gender: null
    property bool isNewPerson: false
    property bool isSubmitted: false
    property bool isDirty: false
    property bool existingOnly: false
    property var textEdit: pickerTextEdit // still need this one?
    property var popupListView: popupListView
    property var genderBox: genderBox
    property var isNewBox: isNewBox
    property var checkImage: checkImage

    signal numVisibleAutoCompleteItemsUpdated(var numVisibleItems) // for testing
    signal submitted(var entry)

    // testing
    function setPersonIdSelected(personId) {
        var person = sceneModel.item(personId) // had trouble passing the Person directly
        selectedPeopleModel.append({ person: person, isNewPerson: false })
    }

    // The list of people already selected in the EventForm
    property var selectedPeopleModel: ListModel { }

    // The list of people used for auto-complete
    property var scenePeopleModel: ListModel {}

    Keys.onPressed: {
        if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
            event.accepted = true
        }
    }

    function clear() {
        // print('>>> PersonPicker.clear() ' + root.objectName)
        if(isSubmitted) {
            for(var i=0; i < root.selectedPeopleModel.rowCount(); i++) {
                var entry = root.selectedPeopleModel.get(i);
                // print('    ' + i + ', ' + entry.person)
                if(entry.person && root.person && entry.person.itemId() === root.person.itemId()) {
                    // print('    removing ' + entry.person.fullNameOrAlias())
                    root.selectedPeopleModel.remove(i)
                    break
                }
            }
            
        }
        root.personName = ''
        root.person = null
        root.isNewPerson = false
        root.isSubmitted = false
        root.gender = util.PERSON_KIND_MALE
        genderBox.currentIndex = 0
        root.isDirty = false
        // print('<<< PersonPicker.clear() root.gender: ' + root.gender + ', ' + genderBox.currentIndex)
    }

    function focusTextEdit() {
        // util.debug('>>> PersonPicker.focusTextEdit()')
        pickerTextEdit.forceActiveFocus()
        // util.debug('<<< PersonPicker.focusTextEdit()')
    }

    function personEntry() {
        util.debug('PersonPicker.personEntry: ' + root.personName + ', ' + root.person + ', ' + root.gender)
        if(! root.isSubmitted) {
            return null
        }
        return {
            person: root.person,
            personName: root.personName,
            gender: root.gender,
            isNewPerson: root.isNewPerson
        }
    }

    function setExistingPersonId(personId) {
        setExistingPerson(sceneModel.item(personId))
    }

    function setExistingPerson(person) {
        if (!person) {
            util.warning('PersonPicker[' + root.objectName + '].setExistingPerson: null person')
            return
        }
        util.debug('PersonPicker[' + root.objectName + '].setExistingPerson: ' + person.listLabel())
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

    function setNewPerson(personName, gender) {
        // util.info('PersonPicker[' + root.objectName + '].setNewPerson: ' + personName + ', gender: ' + gender)
        root.isDirty = true
        root.isSubmitted = true
        root.isNewPerson = true
        root.person = null
        root.personName = personName
        if(gender) {
            root.gender = gender
        } else {
            root.gender = util.PERSON_KIND_MALE
        }
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

    function visibleItems() {
        var items = []
        for(var i = 0; i < popupListView.contentItem.children.length; i++) {
            var child = popupListView.contentItem.children[i]
            if(child.isListItem && child.visible) {
                items.push(child)
            }
        }
        return items
    }

    function visibleModelIndices() {
        var indices = []
        for(var i = 0; i < popupListView.contentItem.children.length; i++) {
            var child = popupListView.contentItem.children[i]
            if(child.isListItem && child.visible) {
                indices.push(child.modelIndex)
            }
        }
        return indices
    }

    function selectHighlightedPerson() {
        if(popupListView.highlightedModelIndex >= 0) {
            var person = scenePeopleModel.personForRow(popupListView.highlightedModelIndex)
            if(person) {
                pickerTextEdit.selectingAutoCompleteItem = true
                root.setExistingPerson(person)
                pickerTextEdit.selectingAutoCompleteItem = false
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
            elide: Text.ElideRight
            visible: isSubmitted
            Layout.leftMargin: util.QML_ITEM_MARGINS
            Layout.maximumWidth: 105
        }
        PK.TextInput {
            id: pickerTextEdit
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
                // print('[' + root.objectName + '].onTextChanged: >>' + text + '<< color: ' + color)
                popupListView.highlightedModelIndex = -1
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
                        popupListView.height = Math.min(numMatches, 8) * util.QML_ITEM_HEIGHT
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
            Keys.onDownPressed: {
                if(autoCompletePopup.visible) {
                    var visibleIndices = root.visibleModelIndices()
                    if(visibleIndices.length > 0) {
                        var currentPos = visibleIndices.indexOf(popupListView.highlightedModelIndex)
                        if(currentPos < 0) {
                            popupListView.highlightedModelIndex = visibleIndices[0]
                        } else if(currentPos < visibleIndices.length - 1) {
                            popupListView.highlightedModelIndex = visibleIndices[currentPos + 1]
                        }
                        popupListView.positionViewAtIndex(popupListView.highlightedModelIndex, ListView.Contain)
                    }
                    event.accepted = true
                }
            }
            Keys.onUpPressed: {
                if(autoCompletePopup.visible) {
                    var visibleIndices = root.visibleModelIndices()
                    if(visibleIndices.length > 0) {
                        var currentPos = visibleIndices.indexOf(popupListView.highlightedModelIndex)
                        if(currentPos > 0) {
                            popupListView.highlightedModelIndex = visibleIndices[currentPos - 1]
                        } else if(currentPos < 0) {
                            popupListView.highlightedModelIndex = visibleIndices[visibleIndices.length - 1]
                        }
                        popupListView.positionViewAtIndex(popupListView.highlightedModelIndex, ListView.Contain)
                    }
                    event.accepted = true
                }
            }
            onAccepted: {
                if(autoCompletePopup.visible && popupListView.highlightedModelIndex >= 0) {
                    if(root.selectHighlightedPerson()) {
                        focus = false
                        return
                    }
                }
                if(text && !selectingAutoCompleteItem && !root.existingOnly) {
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
        width: 70
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
        popup.width: genderBox.width + 25

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
        x: -10
        y: util.QML_ITEM_HEIGHT // show just below the picker
        width: root.width + 20
        height: popupListView.height
        padding: 0
        onClosed: {
            popupListView.highlightedModelIndex = -1
        }
        contentItem: ListView {
            id: popupListView
            model: scenePeopleModel
            property int highlightedModelIndex: -1
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
                property int modelIndex: index
                property var person: autoCompletePopup.visible ? scenePeopleModel.personForRow(index) : null
                property var matchesTypedPersonName: autoCompletePopup.visible && person && person.matchesName(pickerTextEdit.text)
                property var alreadySelected: autoCompletePopup.visible && person ? root.alreadySelected(person) : false
                property bool isHighlighted: dRoot.visible && index === popupListView.highlightedModelIndex
                text: fullNameOrAlias // modelData
                width: autoCompletePopup.width
                height: visible ? util.QML_ITEM_HEIGHT : 0
                visible: matchesTypedPersonName && ! alreadySelected
                palette.text: util.QML_TEXT_COLOR
                background: Rectangle {
                    color: dRoot.isHighlighted ? util.QML_HIGHLIGHT_COLOR : util.QML_ITEM_BG
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

