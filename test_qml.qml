import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12


ApplicationWindow {

    onActiveFocusControlChanged: {
        if(activeFocusControl) {
            print("activeFocusControl: " + activeFocusControl.objectName)
        } else {
            print("activeFocusControl: null")
        }
    }

    height: 800
    width: 300

    ColumnLayout {

        id: root
        anchors.fill: parent

        MouseArea {
            anchors.fill: parent
            onPressed: print('pressed')
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 100
            color: 'blue'
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 100
            color: 'green'
        }


    }
}