import QtQuick 2.12
import QtQuick.Layouts 1.15
import "../../qml/PK" 1.0 as PK

Rectangle {

    id: root
    objectName: 'root'

    anchors.fill: parent

    property var model: null
    property var sceneModel: null; // just a dummy to be a false/null condition
    property var peopleModel: null;
    signal done;
    color: util.QML_ITEM_BG

    function setCurrentTab(x) {}

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
