import QtQuick 2.12
//import QtQuick.Controls 2.5
import "." 1.0 as PK


// A TextField with margins

Rectangle {

    property string text: searchBox.text
    property int margin: 10
    implicitHeight: searchBox.implicitHeight + margin * 2
    color: util.QML_WINDOW_BG

    Rectangle { // border-bottom
        y: parent.height - 1
        width: parent.width
        height: 1
        color: util.QML_ITEM_BORDER_COLOR
    }
    
    PK.TextField {
        id: searchBox
        objectName: 'searchBox'
        anchors.fill: parent
        anchors.topMargin: margin
        anchors.leftMargin: margin
        anchors.rightMargin: margin
        anchors.bottomMargin: margin
        font.family: util.FONT_FAMILY
        font.pixelSize: 17
        placeholderText: 'Search'
        placeholderTextColor: 'lightGrey'
        color: util.QML_ACTIVE_TEXT_COLOR
        background: Rectangle {
            width: parent.width
            height: searchBox.height
            color: searchBox.enabled ? util.QML_WINDOW_BG : Qt.darker(util.QML_WINDOW_BG, 2.0)
            border.color: searchBox.enabled ? util.QML_ITEM_BORDER_COLOR : "transparent"
            radius: 5
        }
    }

    PK.Button {
        source: '../../icloud-cancel.png'
        height: searchBox.height * .5
        width: height
        visible: searchBox.text ? true : false
        opacity: .3
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: margin * 2
        onClicked: searchBox.text = ''
    }
}
