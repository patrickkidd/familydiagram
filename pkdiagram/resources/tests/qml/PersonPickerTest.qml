import QtQuick 2.12
import QtQuick.Layouts 1.15
import "../../qml/PK" 1.0 as PK

Rectangle {

    id: root

    anchors.fill: parent

    property var model: null
    property var sceneModel: null // just a dummy to be a false/null condition
    property var peopleModel: null
    signal done;
    color: util.QML_ITEM_BG

    function setCurrentTab(x) {}
    function setPersonIdSelected(personId) {
        var person = sceneModel.item(personId) // had trouble passing the Person directly
        personPicker.selectedPeopleModel.append({ person: person, isNewPerson: false })
    }
    function clear() { personPicker.clear() }

    ColumnLayout {
        id: testLayout
        anchors.fill: parent

        PK.PersonPicker {
            id: personPicker
            scenePeopleModel: peopleModel
            objectName: "personPicker"
            Layout.fillWidth: true
            Layout.minimumHeight: util.QML_ITEM_HEIGHT
            Layout.maximumHeight: util.QML_ITEM_HEIGHT
        }

        Rectangle {
            id: rect
            color: 'green'
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    Connections {
        target: model
        function onDateTimeChanged() {
            dateButtons.dateTime = model.dateTime
            datePickerTumbler.dateTime = model.dateTime
        }
    }

}
