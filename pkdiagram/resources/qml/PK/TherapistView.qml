import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "./" 1.0 as PK


Page {

    id: root
    title: "Therapist"

    signal humanBubbleAdded(Item item)
    signal humanBubbleRemoved(Item item)
    signal aiBubbleAdded(Item item)
    signal aiBubbleRemoved(Item item)

    property var chatModel: chatModel
    property var textEdit: textEdit
    property var noChatLabel: noChatLabel

    property var chatMargin: util.QML_MARGINS * 1.5

    background: Rectangle {
        color: util.QML_WINDOW_BG
        anchors.fill: parent
    }

    Connections {
        target: therapist
        function onRequestSent(message) {
            chatModel.append({ "message": message, "fromUser": true });
        }
        function onResponseReceived(responseText) {
            chatModel.append({
                "message": responseText,
                "fromUser": false
            });
        }
        function onServerDown() {
            chatModel.append({
                "message": util.S_SERVER_IS_DOWN,
                "fromUser": false
            });
        }
        function onServerError() {
            chatModel.append({
                "message": util.S_SERVER_ERROR,
                "fromUser": false
            });
        }
    }

    function clear() {
        chatModel.clear()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"
            visible: chatModel.count == 0

            PK.NoDataText {
                id: noChatLabel
                text: util.S_THERAPIST_NO_CHAT_TEXT
            }
        }

        // Chat message list
        ListView {
            id: chatListView
            visible: chatModel.count > 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: ListModel {
                id: chatModel
            }
            clip: true
            delegate: Loader {
                width: chatListView.width
                property var dMessage: model.message
                property var dSources: model.sources
                property var dNumSources: model.numSources
                sourceComponent: model.fromUser ? humanQuestion : aiResponse
            }
        }

        Component {
            id: humanQuestion

            Column {

                id: dRoot

                Component.onCompleted: {
                    root.humanBubbleAdded(dRoot)
                }
                Component.onDestruction: {
                    root.humanBubbleRemoved(dRoot)
                }

                // top padding
                Rectangle {
                    width: dRoot.width
                    height: util.QML_MARGINS
                    color: 'transparent'
                }

                Rectangle {
                    id: bubble
                    color: util.QML_ITEM_ALTERNATE_BG
                    border.color: "#ccc"
                    radius: 8
                    width: Math.min(questionText.implicitWidth + util.QML_MARGINS, chatListView.width - util.QML_MARGINS * 6)
                    implicitHeight: questionText.implicitHeight + 20
                    anchors.right: parent.right
                    anchors.rightMargin: root.chatMargin

                    TextEdit {
                        id: questionText
                        text: dMessage
                        color: util.QML_TEXT_COLOR
                        readOnly: true
                        selectByMouse: true
                        wrapMode: Text.WordWrap
                        anchors.fill: parent
                        anchors.margins: 10
                    }
                }
            }
        }

        Component {
            id: aiResponse

            Column {

                id: dRoot
                x: root.chatMargin

                property var responseText: responseText.text

                Component.onCompleted: {
                    root.aiBubbleAdded(dRoot)
                }
                Component.onDestruction: {
                    root.aiBubbleRemoved(dRoot)
                }

                // top padding
                Rectangle {
                    width: dRoot.width
                    height: util.QML_MARGINS
                    color: 'transparent'
                }

                TextEdit {
                    id: responseText
                    text: dMessage
                    color: util.QML_TEXT_COLOR
                    readOnly: true
                    selectByMouse: true
                    wrapMode: Text.WordWrap
                    width: dRoot.width - dRoot.x * 2
                    bottomPadding: font.pixelSize
                }
            }    
        }

        // Text input field at the bottom (respects iOS keyboard)
        Rectangle {
            id: inputField
            color: util.QML_ITEM_BG
            Layout.fillWidth: true
            implicitHeight: textEdit.height + 20

            MouseArea {
                anchors.fill: parent
                onClicked: textEdit.focus()
            }

            PK.TextEdit {
                id: textEdit
                anchors {
                    left: parent.left
                    right: sendButton.left
                    verticalCenter: parent.verticalCenter
                    margins: 10
                }

                background: Rectangle {
                    color: "transparent"
                    border.width: 0
                }

                focus: true
                // color: enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
                selectByMouse: true
                selectionColor: util.QML_HIGHLIGHT_COLOR
                selectedTextColor: 'black'
            }

            Button {
                id: sendButton
                text: "Send"
                anchors {
                    right: parent.right
                    verticalCenter: parent.verticalCenter
                    margins: 10
                }
                onClicked: {
                    if (textEdit.text.trim().length > 0) {
                        therapist.sendMessage(textEdit.text);
                        textEdit.text = ''
                    }
                }
            }
            
        }
    }
}