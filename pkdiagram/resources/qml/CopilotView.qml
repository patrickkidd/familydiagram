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

    property var chatMargin: util.QML_MARGINS * 1.5

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
        chatModel.append({ "message": message, "fromUser": true, 'numSources': 0, 'sources': ''});
        textInput.text = "";
        var args = {
            session: session.token,
            question: message
        };
        Global.server(util, session, "POST", "/copilot/chat", args, function(response) {
            if(response.status_code == 200) {
                var s_aiResponse = util.formatChatResponse(response)
                var s_aiSources = util.formatChatSources(response)
                chatModel.append({
                    "message": s_aiResponse,
                    "sources": s_aiSources,
                    "numSources": response.data.sources.length,
                    // "sources": response.data.sources, // was causing crash
                    "fromUser": false
                });
            } else if(response.status_code == 0) {
                chatModel.append({
                    "message": util.S_SERVER_IS_DOWN,
                    "sources": '',
                    "numSources": 0,
                    "fromUser": false
                });
            } else {
                print('Server error: ' + response.status_code)
                chatModel.append({
                    "message": util.S_SERVER_ERROR,
                    "sources": [],
                    "numSources": 0,
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
            model: ListModel {
                id: chatModel
            }
            clip: true
            delegate: Loader {
                width: chatListView.width
                // spacing: util.QML_MARGINS
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

                    Text {
                        id: questionText
                        text: dMessage
                        color: util.QML_TEXT_COLOR
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
                property var sourcesText: sourcesText.text

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

                Text {
                    id: responseText
                    text: dMessage
                    color: util.QML_TEXT_COLOR
                    wrapMode: Text.WordWrap
                    width: dRoot.width - dRoot.x * 2
                    bottomPadding: font.pixelSize
                }

                Text {
                    text: '' + dNumSources + ' Sources >'
                    font.underline: true
                    color: Qt.darker(util.QML_TEXT_COLOR, 1.2)
                    width: dRoot.width - dRoot.x * 2
                    bottomPadding: font.pixelSize
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            sourcesText.toggle()
                        }
                    }
                }

                Text {
                    id: sourcesText
                    text: dSources // 'Lorem ipsum odor amet, consectetuer adipiscing elit. Nunc metus at platea inceptos eros urna curabitur. Id primis maximus tortor egestas nostra suspendisse cubilia nibh.'
                    color: Qt.darker(util.QML_TEXT_COLOR, 1.2)
                    width: dRoot.width - dRoot.x * 2
                    wrapMode: Text.WordWrap
                    clip: true
                    height: 0
                    opacity: height / implicitHeight

                    Behavior on height {
                        NumberAnimation { duration: 200 }
                    }

                    function toggle() {
                        if(height == 0) {
                            height = implicitHeight
                        } else {
                            height = 0
                        }
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

}