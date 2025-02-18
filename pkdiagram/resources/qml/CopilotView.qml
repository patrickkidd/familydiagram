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

    signal humanBubbleAdded(Item item)
    signal humanBubbleRemoved(Item item)
    signal aiBubbleAdded(Item item)
    signal aiBubbleRemoved(Item item)

    property var chatModel: chatModel
    property var textInput: textInput
    property var sendButton: sendButton
    property var noChatLabel: noChatLabel
    property var tagsCheckbox: tagsCheckbox

    property var chatMargin: util.QML_MARGINS * 1.5
    property var tagsSummary: {
        var summary = ""
        for (var i = 0; i < searchModel.tags.length; i++) {
            summary += searchModel.tags[i];
            if (i < searchModel.tags.length - 1) {
                summary += ", "
            }
        }
        if(summary.length > 0) {
            summary = "" + searchModel.tags.length + " tags"
        }
        return summary;
    }

    background: Rectangle {
        color: util.QML_WINDOW_BG
        anchors.fill: parent
    }

    Connections {
        target: copilot
        function onRequestSent(questionText) {
            chatModel.append({ "message": questionText, "sources": '', 'numSources': 0, "fromUser": true, });
        }
        function onResponseReceived(responseText, sourceText, numSources) {
            chatModel.append({
                "message": responseText,
                "sources": sourceText,
                "numSources": numSources,
                "fromUser": false
            });
        }
        function onServerDown() {
            chatModel.append({
                "message": util.S_SERVER_IS_DOWN,
                "sources": '',
                "numSources": 0,
                "fromUser": false
            });
        }
        function onServerError() {
            chatModel.append({
                "message": util.S_SERVER_ERROR,
                "sources": '',
                "numSources": 0,
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
                text: util.S_NO_CHAT_TEXT
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
                        onClicked: sourcesText.toggle()
                    }
                }

                Text {
                    id: sourcesText
                    text: dSources
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

        RowLayout {
            PK.CheckBox {
                id: tagsCheckbox
                text: "Include Tags: " + tagsSummary
                checked: false
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            PK.TextField {
                id: textInput
                placeholderText: "Type your message..."
                Layout.fillWidth: true
                onAccepted: {
                    if (text.trim().length > 0) {
                        copilot.ask(text, tagsCheckbox.checked);
                    }
                }
            }

            PK.Button {
                id: sendButton
                source: '../../up-arrow.png'
                Layout.maximumHeight: 18
                Layout.maximumWidth: 10
                Layout.rightMargin: 10
                Layout.topMargin: 3
                Layout.bottomMargin: 3
                onClicked: {
                    if (textInput.text.trim().length > 0) {
                        copilot.ask(textInput.text, tagsCheckbox.checked);
                    }
                }
            }
        }
    }

}