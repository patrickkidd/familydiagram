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
    property var submitButton: submitButton
    property var noChatLabel: noChatLabel
    property var newDiscussionButton: newDiscussionButton
    property var discussionsButton: discussionsButton
    property var discussionsDrawer: discussionsDrawer
    property var discussionList: discussionList
    property var statementsList: statementsList
    property var pdpSheet: pdpSheet
    property var pdpBadge: pdpBadge

    property var chatMargin: util.QML_MARGINS * 1.5
    property var eventDrawer: eventDrawer
    property var eventForm: eventForm
    property int pdpCount: 0

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
                // print('initSelectedDiscussion: ' + lastDiscussion)
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
                var count = 0
                if (pdp.people) count += pdp.people.length
                if (pdp.events) count += pdp.events.length
                if (pdp.pair_bonds) count += pdp.pair_bonds.length
                root.pdpCount = count
                pdpSheet.pdp = pdp
                pdpSheet.updateItems()
            } else {
                root.pdpCount = 0
            }
        }
    }

    function clear() {
        chatModel.clear()
    }

    function showDiscussions() {
        discussionsDrawer.visible = true
    }

    function showEventForm() {
        eventDrawer.open()
    }


    Drawer {
        id: discussionsDrawer
        width: root.width - 20
        height: root.height
        dragMargin: 0
        edge: Qt.LeftEdge
        ListView {
            id: discussionList

            anchors.fill: parent
            model: personalApp ? personalApp.discussions : undefined
            clip: true

            delegate: ItemDelegate {
                id: dRoot
                property int dId: modelData.id
                property var dText: modelData.summary

                text: dText
                width: discussionList.width
                palette.text: util.QML_TEXT_COLOR

                onClicked: {
                    personalApp.setCurrentDiscussion(modelData.id)
                    discussionsDrawer.visible = false
                }
            }

            PK.Button {
                id: newDiscussionButton
                source: '../../plus-button.png'
                width: 18
                height: 20
                anchors {
                    right: parent.right
                    margins: util.QML_MARGINS
                }
                onClicked: personalApp.createDiscussion()
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

    Popup {
        id: eventDrawer
        width: parent.width
        height: parent.height
        modal: true
        closePolicy: Popup.CloseOnEscape
        parent: Overlay.overlay
        padding: 0

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 200 }
            NumberAnimation { property: "y"; from: parent.height; to: 0; duration: 250; easing.type: Easing.OutQuad }
        }

        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 200 }
            NumberAnimation { property: "y"; from: 0; to: parent.height; duration: 250; easing.type: Easing.InQuad }
        }

        Root.EventForm {
            id: eventForm
            anchors.fill: parent
            onCancel: eventDrawer.close()
        }

        background: Rectangle {
            color: util.QML_WINDOW_BG
        }
    }


    header: PK.ToolBar {
        PK.ToolButton {
            text: "Logout"
            Layout.maximumWidth: 25
            anchors.centerIn: parent
            onClicked: session.logout()
        }

        PK.ToolButton {
            id: discussionsButton
            text: "Discussions"
            visible: personalApp && personalApp.discussions.length > 0
            anchors.left: parent.left
            anchors.leftMargin: util.QML_MARGINS
            onClicked: root.showDiscussions()
        }

        PK.Button {
            id: addButton
            source: '../../plus-button-green.png'
            invertForDarkMode: false
            height: 25
            width: 25
            anchors {
                right: parent.right
                verticalCenter: parent.verticalCenter
                margins: util.QML_MARGINS
            }
            onClicked: root.showEventForm()
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
                    height: util.QML_MARGINS
                    color: 'transparent'
                }

                Rectangle {
                    id: bubble
                    color: util.QML_ITEM_ALTERNATE_BG
                    border.color: util.QML_ITEM_BORDER_COLOR
                    radius: 8
                    width: Math.min(questionText.implicitWidth + util.QML_MARGINS, statementsList.width - util.QML_MARGINS * 6)
                    implicitHeight: questionText.implicitHeight + 20
                    anchors.right: parent.right
                    anchors.rightMargin: root.chatMargin

                    TextEdit {
                        id: questionText
                        text: dText
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
                    text: dText
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
                    personalApp.sendStatement(textEdit.text);
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

    Rectangle {
        id: pdpBadge
        visible: root.pdpCount > 0
        width: 48
        height: 48
        radius: 24
        color: "transparent"
        border.color: util.QML_ITEM_BORDER_COLOR
        border.width: 1.5
        z: 100

        x: parent.width - width - util.QML_MARGINS
        y: util.QML_MARGINS

        Text {
            anchors.centerIn: parent
            text: root.pdpCount.toString()
            font.pixelSize: 18
            font.bold: true
            color: util.QML_TEXT_COLOR
        }

        MouseArea {
            anchors.fill: parent
            onClicked: pdpSheet.open()
        }

        Behavior on opacity {
            NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
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