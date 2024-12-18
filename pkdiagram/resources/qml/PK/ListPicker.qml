import QtQuick 2.12
import QtQuick.Window 2.2
import QtQuick.Controls 2.15


Tumbler {

    id: listPicker
    width: implicitWidth + 10
    height: implicitHeight + 10
    clip: true
    state: 'hidden'

    Rectangle {
        anchors.horizontalCenter: parent.left
        y: parent.height * 0.4
        width: parent.parent.width * 4
        height: 1
        color: "lightGray"
    }
    
    Rectangle {
        anchors.horizontalCenter: parent.left
        y: parent.height * 0.6
        width: parent.parent.width * 4
        height: 1
        color: "lightGray"
    }
 
}
