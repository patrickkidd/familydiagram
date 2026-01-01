/*
The outer view of the personal feature.
*/

import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK
import "." 1.0 as Personal
import ".." 1.0 as Root

Page {

    id: root
    title: "Discuss"

    signal humanBubbleAdded(Item item)
    signal humanBubbleRemoved(Item item)
    signal aiBubbleAdded(Item item)
    signal aiBubbleRemoved(Item item)

    property var chatModel: chatModel
    property var textEdit: textEdit
    property var submitButton: sendButton
    property var noChatLabel: noChatLabel
    property var statementsList: statementsList
    property var pdpSheet: pdpSheet

    property var chatMargin: util.QML_MARGINS * 1.5

    background: Rectangle {
        color: util.QML_WINDOW_BG
        anchors.fill: parent
    }

    property bool initSelectedDiscussion: false

    Connections {
        target: personalApp
        function onDiscussionsChanged() {
            if (!initSelectedDiscussion) {
                initSelectedDiscussion = true
                var lastDiscussion = personalApp.discussions[personalApp.discussions.length-1]
                if(lastDiscussion !== undefined) {
                    personalApp.setCurrentDiscussion(lastDiscussion.id)
                }
            }
        }
        function onStatementsChanged() {
            chatModel.clear()
            for (var i = 0; i < personalApp.statements.length; i++) {
                var statement = personalApp.statements[i]
                var speakerType = statement.speaker.type
                chatModel.append({ "text": statement.text, "speakerType": speakerType })
            }
            statementsList.delayedScrollToBottom()
        }
        function onRequestSent(text) {
            chatModel.append({ "text": text, "speakerType": 'subject' })
        }
        function onResponseReceived(text, added) {
            chatModel.append({
                "text": text,
                "speakerType": 'expert'
            })
            statementsList.delayedScrollToBottom()
        }
        function onServerDown() {
            chatModel.append({
                "text": util.S_SERVER_IS_DOWN,
                "speakerType": 'expert'
            });
            statementsList.delayedScrollToBottom()
        }
        function onServerError() {
            chatModel.append({
                "text": util.S_SERVER_ERROR,
                "speakerType": 'expert'
            });
            statementsList.delayedScrollToBottom()
        }
        function onPdpChanged() {
            if (pdpSheet.editOverlayVisible) {
                return
            }
            var pdp = personalApp.pdp
            if (pdp) {
                pdpSheet.pdp = pdp
                pdpSheet.updateItems()
            }
        }
        function onJournalImportCompleted(summary) {
            util.informationBox("Import Complete",
                "Added " + summary.people + " people, " + summary.events + " events to pending items.")
        }
        function onJournalImportFailed(error) {
            util.criticalBox("Import Failed", error)
        }
    }

    function clear() {
        chatModel.clear()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

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
            id: statementsList
            visible: model.count > 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: ListModel {
                id: chatModel
            }
            clip: true
            delegate: Loader {
                width: statementsList.width
                property var dText: model.text
                property var dSpeakerType: model.speakerType
                sourceComponent: model.speakerType == 'subject' ? humanQuestion : aiResponse
            }
            footer: Item {
                width: statementsList.width
                height: 15
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
                onTriggered: statementsList.positionViewAtEnd()
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
                    height: 10
                    color: 'transparent'
                }

                Rectangle {
                    id: bubble
                    color: "#1190F9"
                    radius: 18
                    width: Math.min(questionText.implicitWidth + 24, statementsList.width * 0.8)
                    implicitHeight: questionText.implicitHeight + 20
                    anchors.right: parent.right
                    anchors.rightMargin: 15

                    TextEdit {
                        id: questionText
                        text: dText
                        color: "white"
                        readOnly: true
                        selectByMouse: true
                        wrapMode: Text.WordWrap
                        font.pixelSize: 15
                        anchors.fill: parent
                        anchors.margins: 12
                    }
                }
            }
        }

        Component {
            id: aiResponse

            Column {

                id: dRoot

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
                    height: 10
                    color: 'transparent'
                }

                Rectangle {
                    id: aiBubble
                    color: util.IS_UI_DARK_MODE ? "#373534" : "#e5e5ea"
                    radius: 18
                    width: Math.min(responseText.implicitWidth + 24, statementsList.width * 0.8)
                    implicitHeight: responseText.implicitHeight + 20
                    anchors.left: parent.left
                    anchors.leftMargin: 15

                    TextEdit {
                        id: responseText
                        text: dText
                        color: util.QML_TEXT_COLOR
                        readOnly: true
                        selectByMouse: true
                        wrapMode: Text.WordWrap
                        font.pixelSize: 15
                        anchors.fill: parent
                        anchors.margins: 12
                    }
                }
            }
        }

        Rectangle {
            id: inputField
            color: "transparent"
            Layout.fillWidth: true
            implicitHeight: Math.max(36, inputContainer.height + 16)

            function submit() {
                if (textEdit.text.trim().length > 0) {
                    personalApp.sendStatement(textEdit.text);
                    textEdit.text = ''
                    textEdit.focus = false
                }
            }

            Rectangle {
                id: inputContainer
                anchors {
                    left: parent.left
                    right: parent.right
                    bottom: parent.bottom
                    leftMargin: 15
                    rightMargin: 15
                    bottomMargin: 10
                }
                height: Math.min(inputFlickable.contentHeight + 8, 100)
                radius: 18
                color: util.IS_UI_DARK_MODE ? "#252526" : "#F7F7F7"
                border.width: textEdit.activeFocus ? 1 : 0
                border.color: util.IS_UI_DARK_MODE ? "#636366" : "#c7c7cc"

                MouseArea {
                    anchors.fill: parent
                    onClicked: textEdit.forceActiveFocus()
                }

                Text {
                    id: placeholderText
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Message"
                    color: util.IS_UI_DARK_MODE ? "#636366" : "#8E8E93"
                    font.pixelSize: 15
                    visible: textEdit.text.length === 0 && !textEdit.activeFocus
                }

                Flickable {
                    id: inputFlickable
                    anchors {
                        left: parent.left
                        right: sendButton.visible ? sendButton.left : parent.right
                        top: parent.top
                        bottom: parent.bottom
                        leftMargin: 12
                        rightMargin: sendButton.visible ? 4 : 12
                        topMargin: 4
                        bottomMargin: 4
                    }
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
                        selectByMouse: true
                        selectionColor: util.QML_HIGHLIGHT_COLOR
                        selectedTextColor: 'black'
                        wrapMode: TextEdit.WordWrap
                        textFormat: TextEdit.PlainText
                        cursorVisible: focus
                        font.pixelSize: 15

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

                        property int prevTextLength: 0

                        Keys.onReturnPressed: {
                            if (event.modifiers & Qt.ShiftModifier) {
                                event.accepted = false
                            } else {
                                inputField.submit()
                                event.accepted = true
                            }
                        }

                        onTextChanged: {
                            // Detect paste: large text delta in single change (works on iOS and desktop)
                            var delta = text.length - prevTextLength
                            if (delta > 20 && prevTextLength === 0) {
                                var pastedText = text
                                text = ""
                                prevTextLength = 0
                                if (util.questionBox("Import Journal Notes?",
                                    "Import as bulk data instead of chat message?")) {
                                    personalApp.importJournalNotes(pastedText)
                                } else {
                                    text = pastedText
                                    prevTextLength = pastedText.length
                                }
                                return
                            }
                            prevTextLength = text.length
                        }
                    }
                }

                Rectangle {
                    id: sendButton
                    visible: textEdit.text.trim().length > 0
                    anchors {
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                        rightMargin: 4
                    }
                    width: 28
                    height: 28
                    radius: 14
                    color: "#007AFF"

                    Text {
                        anchors.centerIn: parent
                        text: "↑"
                        font.pixelSize: 16
                        font.bold: true
                        color: "white"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: inputField.submit()
                    }
                }
            }

        }
    }

    Personal.PDPSheet {
        id: pdpSheet
        parent: Overlay.overlay

        onItemAccepted: function(id) {
            personalApp.acceptPDPItem(id)
            pdpSheet.removeItemById(id)
        }
        onItemRejected: function(id) {
            personalApp.rejectPDPItem(id)
            pdpSheet.removeItemById(id)
        }
        onAcceptAllClicked: {
            personalApp.acceptAllPDPItems()
            pdpSheet.close()
        }
        onFieldChanged: function(id, field, value) {
            personalApp.updatePDPItem(id, field, value)
        }
    }
}