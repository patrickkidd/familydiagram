import QtQuick 2.12
import QtQuick.Layouts 1.15
import "../../qml/PK" 1.0 as PK

Rectangle {

    id: root
    objectName: 'root'

    anchors.fill: parent

    width: 400
    height: 600
    onWidthChanged: print(root.width)
    onHeightChanged: print(root.height)

    Timer {
        running: true
        repeat: true
        onTriggered: print(root.parent.width + ', ' + root.parent.height)
    }
    
    property var model: null
    property var sceneModel: null; // just a dummy to be a false/null condition
    signal done;
    color: 'red';

    ColumnLayout {
        anchors.fill: parent

        PK.PeoplePicker {
            id: peoplePicker
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
