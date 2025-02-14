import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "./PK" 1.0 as PK
import PK.Models 1.0
import "js/Global.js" as Global
import "js/Underscore.js" as Underscore

Page {

    id: root
    title: "Copilot Chat UI"

    property var chatModel: chatModel
    property var textInput: textInput
    property var sendButton: sendButton

    background: Rectangle {
        color: util.QML_WINDOW_BG
        anchors.fill: parent
    }

    function clear() {
        chatModel.clear()
    }

    signal chatBubbleAdded(Item item)
    signal chatBubbleRemoved(Item item)

    function submit(message) {
        chatModel.append({ "message": message, "fromUser": true });
        textInput.text = "";
        chatModel.append({ "message": message, "fromUser": false });
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // Chat message list
        ListView {
            id: chatListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: chatModel
            clip: true
            delegate: RowLayout {

                id: dRoot
                width: parent.width
                spacing: 5

                // Rectangle {
                //     color: "transparent"
                //     visible: fromUser
                //     width: util.QML_MARGINS * 3
                // }

                // The chat bubble itself.
                Rectangle {
                    id: bubble
                    color: fromUser ? util.QML_ITEM_ALTERNATE_BG : "transparent"
                    border.color: fromUser ? "#ccc" : "transparent"
                    radius: 8
                    Layout.maximumWidth: parent.width * 0.7
                    Layout.minimumWidth: parent.width * 0.7
                    implicitHeight: bubbleText.implicitHeight + 20
                    Layout.alignment: fromUser ? Qt.AlignRight : Qt.AlignLeft

                    Text {
                        id: bubbleText
                        text: message
                        color: fromUser ? util.QML_TEXT_COLOR : util.QML_TEXT_COLOR
                        wrapMode: Text.WordWrap
                        anchors.fill: parent
                        anchors.margins: 10
                    }
                }

                // Rectangle {
                //     color: "transparent"
                //     visible: ! fromUser
                //     width: util.QML_MARGINS * 3
                // }

                Component.onCompleted: {
                    root.chatBubbleAdded(dRoot)
                }
                Component.onDestruction: {
                    root.chatBubbleRemoved(dRoot)
                }
            }
        }

        // Input area for typing messages
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            PK.TextField {
                id: textInput
                placeholderText: "Type your message..."
                Layout.fillWidth: true
                onAccepted: {
                    if (text.trim().length > 0) {
                        root.submit(text);
                    }
                }
            }

            Button {
                id: sendButton
                text: "Send"
                onClicked: {
                    if (textInput.text.trim().length > 0) {
                        submit(textInput.text);
                    }
                }
            }
        }
    }

    // Model holding chat messages
    ListModel {
        id: chatModel
        // Starting conversation with a copilot (agent) message.
        // ListElement { message: "Hello! I'm your copilot. How can I help you today?"; fromUser: false }
    }

}