import QtQuick 2.12
import QtQuick.Layouts 1.15
import "../../qml/PK" 1.0 as PK

Rectangle {

    id: root
    objectName: 'root'

    anchors.fill: parent

    property var model: null
    property var sceneModel: null; // just a dummy to be a false/null condition
    signal done;

    ColumnLayout {
        id: testLayout
        anchors.fill: parent

        // Timer {
        //     running: true
        //     repeat: true
        //     onTriggered: print("testLayout: (" + testLayout.width + ', ' + testLayout.height + "), child: (" + rect.x + ", " + rect.y + ")")
        // }


        PK.PeoplePicker {
            id: peoplePicker

            Layout.fillWidth: true
            Layout.minimumHeight: 300
            Layout.maximumHeight: 300
            color: 'red';
            // width: 400
            // height: 600
            onWidthChanged: print(root.width)
            onHeightChanged: print(root.height)
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
