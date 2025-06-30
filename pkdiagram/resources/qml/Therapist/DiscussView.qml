/*
The outer view of the therapist feature.
*/

import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK


Page {

    id: root
    title: "Discuss"

    signal humanBubbleAdded(Item item)
    signal humanBubbleRemoved(Item item)
    signal aiBubbleAdded(Item item)
    signal aiBubbleRemoved(Item item)

    property var chatModel: chatModel
    property var textEdit: textEdit
    property var submitButton: submitButton
    property var noChatLabel: noChatLabel
    property var threadsDrawer: threadsDrawer
    property var threadList: threadList

    property var chatMargin: util.QML_MARGINS * 1.5

    background: Rectangle {
        color: util.QML_WINDOW_BG
        anchors.fill: parent
    }

    property bool initSelectedThread: false

    Connections {
        target: therapist
        function onThreadsChanged() {
            if(!initSelectedThread) {
                initSelectedThread = true
                var lastThread = therapist.threads[therapist.threads.length-1]
                print('initSelectedThread: ' + lastThread)
                if(lastThread !== undefined) {
                    therapist.setCurrentThread(lastThread.id)
                }
            }
        }
        function onMessagesChanged() {
            // print('onMessagesChanged: ' + therapist.messages.length + ' messages')
            chatModel.clear()
            for(var i=0; i < therapist.messages.length; i++) {
                var message = therapist.messages[i];
                // print('    message[' + i + '] (' + message.origin + '):', message.text)
                var fromUser = message.origin == 'user' ? true : false
                chatModel.append({ "message": message.text, "fromUser": fromUser })
            } 
            messagesList.delayedScrollToBottom()
        }
        function onRequestSent(text) {
            print('onRequestSent:', text)
            chatModel.append({ "message": text, "fromUser": true });
        }
        function onResponseReceived(text, added, removed, guidance) {
            print('onResponseReceived:', text, added, removed, guidance)
            chatModel.append({
                "message": text,
                "fromUser": false
            });
            messagesList.delayedScrollToBottom()
        }
        function onServerDown() {
            chatModel.append({
                "message": util.S_SERVER_IS_DOWN,
                "fromUser": false
            });
            messagesList.delayedScrollToBottom()
        }
        function onServerError() {
            chatModel.append({
                "message": util.S_SERVER_ERROR,
                "fromUser": false
            });
            messagesList.delayedScrollToBottom()
        }
    }

    function clear() {
        chatModel.clear()
    }

    function showThreads() {
        threadsDrawer.visible = true        
    }


    Drawer {
        id: threadsDrawer
        width: root.width - 20
        height: root.height
        dragMargin: 0
        edge: Qt.LeftEdge
        ListView {
            id: threadList

            signal rowAdded(Item item)
            signal rowRemoved(Item item)

            anchors.fill: parent
            model: therapist ? therapist.threads : undefined
            clip: true
            property int numDelegates: 0
            property var delegates: []

            delegate: ItemDelegate {
                id: dRoot
                property int dId: modelData.id
                
                text: 'Discussion id: ' + modelData.id
                width: threadList.width
                palette.text: util.QML_TEXT_COLOR

                Component.onCompleted: {
                    threadList.rowAdded(dRoot)
                    threadList.numDelegates += 1
                    threadList.delegates.push(this)
                }
                Component.onDestruction: {
                    threadList.rowRemoved(dRoot)
                    threadList.numDelegates -= 1
                    threadList.delegates.splice(threadList.delegates.indexOf(this), 1)
                }
                onClicked: {
                    therapist.setCurrentThread(modelData.id)
                    threadsDrawer.visible = false
                }
            }
        }
        background: Rectangle {
            color: util.QML_WINDOW_BG
            Rectangle {
                x: parent.width - 1
                height: parent.height
                width: 1
                color: util.QML_ITEM_BORDER_COLOR
            }
        }
        function hide() {
            position = 0
            visible = false
        }
    }


    header: PK.ToolBar {

        PK.ToolButton {
            id: resizeButton
            text: "Discussions"
            anchors.left: parent.left
            anchors.leftMargin: util.QML_MARGINS
            onClicked: root.showThreads()
        }

        PK.ToolButton {
            text: 'New'
            anchors {
                right: parent.right
                margins: util.QML_MARGINS
            }
            onClicked: therapist.createThread()
        }
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

        ListView {
            id: messagesList
            visible: chatModel.count > 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: ListModel {
                id: chatModel
            }
            clip: true
            delegate: Loader {
                width: messagesList.width
                property var dMessage: model.message
                sourceComponent: model.fromUser ? humanQuestion : aiResponse
            }

            function delayedScrollToBottom() {
                delayedScrollToEndTimer.running = true
            }

            // contentY was being reset on first scroll to bottom
            Timer {
                id: delayedScrollToEndTimer
                repeat: false
                running: false
                interval: 100
                onTriggered: messagesList.positionViewAtEnd()
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
                    width: Math.min(questionText.implicitWidth + util.QML_MARGINS, messagesList.width - util.QML_MARGINS * 6)
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

        Rectangle {
            id: inputField
            color: util.QML_ITEM_BG
            Layout.fillWidth: true
            implicitHeight: inputFlickable.height + 20

            function submit() {
                if (textEdit.text.trim().length > 0) {
                    print('>>> submit(): >>>' + textEdit.text + '<<<')
                    therapist.sendMessage(textEdit.text);
                    print('<<< submit()')
                    textEdit.text = ''
                    textEdit.focus = false
                    // Qt.inputMethod.hide()
                }
            }

            Rectangle {
                anchors.top: parent.top
                height: 1
                width: parent.width
                color: util.QML_ITEM_BORDER_COLOR
            }

            MouseArea {
                anchors.fill: parent
                onClicked: textEdit.forceActiveFocus()
            }

            Flickable {

                id: inputFlickable

                anchors {
                    left: parent.left
                    right: submitButton.left
                    verticalCenter: parent.verticalCenter
                    margins: 10
                }
                height: Math.min(textEdit.height + 10, 120)  // Cap at 120 px
                contentWidth: textEdit.width
                contentHeight: textEdit.height
                clip: true

                function positionViewAtEnd() {
                    if (contentHeight > height) {
                        contentY = contentHeight - height
                    }
                }

                PK.TextEdit {
                    id: textEdit
                    width: inputFlickable.width
                    // color: enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
                    selectByMouse: true
                    selectionColor: util.QML_HIGHLIGHT_COLOR
                    selectedTextColor: 'black'
                    wrapMode: TextEdit.WordWrap
                    textFormat: TextEdit.PlainText
                    cursorVisible: focus

                    background: Rectangle {
                        color: "transparent"
                        border.width: 0
                    }

                    onCursorRectangleChanged: {
                        if (cursorRectangle) {
                            var topLeft = Qt.point(cursorRectangle.x, cursorRectangle.y)
                            var mappedPos = mapToItem(inputFlickable, topLeft);
                            if (mappedPos.y < 0) {
                                inputFlickable.contentY += mappedPos.y;
                            } else if (mappedPos.y + cursorRectangle.height > inputFlickable.height) {
                                inputFlickable.contentY += (mappedPos.y + cursorRectangle.height - inputFlickable.height);
                            }
                        }
                    }

                    Keys.onReturnPressed: {
                        inputField.submit()
                        event.accepted = true
                        // if (event.modifiers & Qt.ControlModifier || event.modifiers & Qt.MetaModifier) {                        
                        //     inputField.submit()
                        //     event.accepted = true;
                        // } else {
                        //     event.accepted = false;
                        // }
                    }

                }
            }

            PK.Button {
                id: submitButton
                source: '../../up-submit-arrow.png'
                width: 18
                height: 20
                anchors {
                    right: parent.right
                    verticalCenter: parent.verticalCenter
                    margins: 10
                }

                // background: Rectangle {
                //     color: 'transparent' // util.QML_CONTROL_BG
                //     // border.color: root.palette.highlight
                //     // border.width: root.activeFocus ? 2 : 0
                //     // radius: submitButton.width / 2
                // }

                onClicked: inputField.submit()
            }
            
        }
    }
}