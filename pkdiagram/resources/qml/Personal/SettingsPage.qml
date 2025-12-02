import QtQuick 2.15
import QtQuick.Controls 2.15

Page {
    id: root

    property string pageTitle: "Settings"
    property color headerBg: util.QML_HEADER_BG
    property color textColor: util.QML_TEXT_COLOR
    property color secondaryText: util.QML_INACTIVE_TEXT_COLOR
    property color borderColor: util.QML_ITEM_BORDER_COLOR

    signal backClicked()

    background: Rectangle {
        color: util.QML_WINDOW_BG
    }

    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 56
        color: headerBg
        z: 10

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: borderColor
        }

        Rectangle {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 40
            height: 40
            radius: 8
            color: backMouseArea.pressed ? util.QML_ITEM_ALTERNATE_BG : "transparent"

            Text {
                anchors.centerIn: parent
                text: "‹"
                font.pixelSize: 28
                color: util.QML_SELECTION_COLOR
            }

            MouseArea {
                id: backMouseArea
                anchors.fill: parent
                onClicked: root.backClicked()
            }
        }

        Text {
            anchors.centerIn: parent
            text: root.pageTitle
            font.pixelSize: 17
            font.bold: true
            color: textColor
        }
    }

    Flickable {
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        contentHeight: contentColumn.height
        clip: true

        Column {
            id: contentColumn
            width: parent.width
            padding: 20
            spacing: 16

            Text {
                width: parent.width - 40
                text: "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
                color: textColor
                font.pixelSize: 15
                wrapMode: Text.WordWrap
                lineHeight: 1.4
            }

            Text {
                width: parent.width - 40
                text: "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
                color: textColor
                font.pixelSize: 15
                wrapMode: Text.WordWrap
                lineHeight: 1.4
            }

            Text {
                width: parent.width - 40
                text: "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo."
                color: textColor
                font.pixelSize: 15
                wrapMode: Text.WordWrap
                lineHeight: 1.4
            }

            Text {
                width: parent.width - 40
                text: "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet."
                color: textColor
                font.pixelSize: 15
                wrapMode: Text.WordWrap
                lineHeight: 1.4
            }
        }
    }
}
