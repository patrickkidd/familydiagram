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
    title: "BT Copilot"

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

    function scrollToBottom() {
        chatListView.contentY = chatListView.contentHeight - chatListView.height
    }

    signal humanBubbleAdded(Item item)
    signal humanBubbleRemoved(Item item)
    signal aiBubbleAdded(Item item)
    signal aiBubbleRemoved(Item item)

    function submit(message) {
        chatModel.append({ "message": message, "fromUser": true });
        textInput.text = "";
        var args = {
            session: session.token,
            question: message
        };
        Global.server(util, session, "POST", "/copilot/chat", args, function(response) {
            if(response.status_code == 200) {
                var s_aiResponse = util.formatChatResponse(response)
                chatModel.append({
                    "message": s_aiResponse,
                    "sources": [],
                    // "sources": response.data.sources, // was causing crash
                    "fromUser": false
                });
            } else if(response.status_code == 0) {
                chatModel.append({
                    "message": util.S_SERVER_IS_DOWN,
                    "sources": [],
                    "fromUser": false
                });
            } else {
                print('Server error: ' + response.status_code)
                chatModel.append({
                    "message": util.S_SERVER_ERROR,
                    "sources": [],
                    "fromUser": false
                });
            }
            scrollToBottom()
        });
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
                width: parent? parent.width : 0
                spacing: 5
                property var text: bubbleText.text

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
                    if(fromUser) {
                        root.humanBubbleAdded(dRoot)
                    } else {
                        root.aiBubbleAdded(dRoot)
                    }
                }
                Component.onDestruction: {
                    if(fromUser) {
                        root.humanBubbleRemoved(dRoot)
                    } else {
                        root.aiBubbleRemoved(dRoot)
                    }
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