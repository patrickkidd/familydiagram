import QtQuick 2.12
import QtQuick.Layouts 1.15
import "../../qml/PK" 1.0 as PK

Rectangle {

    id: root

    anchors.fill: parent

    property var model: null
    signal done;
    color: util.QML_ITEM_BG

    function setCurrentTab(x) {}
    function setExistingPeople(x) { peoplePicker.setExistingPeople(x) }
    function peopleEntries() { return peoplePicker.peopleEntries() }

    ColumnLayout {
        id: testLayout
        anchors.fill: parent

        PK.PeoplePicker {
            id: peoplePicker
            scenePeopleModel: peopleModel
            objectName: "peoplePicker"
            Layout.fillWidth: true
            Layout.minimumHeight: 300
            Layout.maximumHeight: 300
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
