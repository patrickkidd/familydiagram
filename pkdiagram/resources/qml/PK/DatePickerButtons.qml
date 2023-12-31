import QtQuick 2.12
import QtQuick.Window 2.2
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import "." 1.0 as PK
import "../js/Global.js" as Global


Rectangle {

    id: root

    implicitHeight: layout.implicitHeight
    implicitWidth: layout.implicitWidth

    property var datePicker: null
    property var timePicker: null
    property var dateTime
    property int unsure: Qt.Unchecked
    property bool hideUnsure: false
    property bool hideReset: false
    property bool showInspectButton: false
    property bool blocked: false
    readonly property var textInput: dateTextInput

    signal inspect

    color: 'transparent'

    function isValid() {
        return dateTime !== undefined && dateTime !== null && !isNaN(dateTime)
    }

    state: 'tumblers-hidden'
    // states: [
    //     State {
    //         name: "date-tumbler-shown"
    //     //    PropertyChanges { target: root; implicitHeight: dateTextInput.height + buttonsRow.height }
    //         // PropertyChanges { target: buttonsRow; height: unsureBox.preferred_implicitHeight; implicitHeight: unsureBox.preferred_implicitHeight; }
    //         PropertyChanges { target: datePicker; shouldShow: true }
    //         PropertyChanges { target: timePicker; shouldShow: false }
    //     },
    //     State {
    //         name: "time-tumbler-shown"
    //         // PropertyChanges { target: root; implicitHeight: dateTextInput.height }
    //         // PropertyChanges { target: buttonsRow; height: 0; implicitHeight: 0 }
    //         PropertyChanges { target: datePicker; shouldShow: false }
    //         PropertyChanges { target: timePicker; shouldShow: true }
    //     },
    //     State {
    //         name: "tumblers-hidden"
    //         // PropertyChanges { target: root; implicitHeight: dateTextInput.height }
    //         // PropertyChanges { target: buttonsRow; height: 0; implicitHeight: 0 }
    //         PropertyChanges { target: datePicker; shouldShow: false }
    //         PropertyChanges { target: timePicker; shouldShow: false }
    //     }
    // ]

    function updateState() {
        if(dateTextInput.focus || clearButton.focus /* || unsureBox.focus */) {
            state = 'date-tumbler-shown'
            datePicker.shouldShow = true
            timePicker.shouldShow = false
        } else if(timeTextInput.focus) {
            state = 'time-tumbler-shown'
            datePicker.shouldShow = false
            timePicker.shouldShow = true
        } else {
            state = 'tumblers-hidden'
            datePicker.shouldShow = false
            timePicker.shouldShow = false
        }
    }

    // onUnsureChanged: unsureBox.checkState = unsure

    onDateTimeChanged: {

        // update date text
        if(!dateTextInput.focus || datePicker.moving) {
            root.blocked = true
            if(isValid()) {
                dateTextInput.text = util.dateString(dateTime)
            } else {
                dateTextInput.text = util.BLANK_DATE_TEXT
            }
            root.blocked = false
        }

        // update time text
        if(!timeTextInput.focus || timePicker.moving) {
            root.blocked = true
            if(isValid()) {
                timeTextInput.text = util.timeString(dateTime)
            } else {
                timeTextInput.text = util.BLANK_TIME_TEXT
            }
            root.blocked = false
        }
    }

    function validatedTextInputs(dateText, timeText) {
        var newDateTime
        if(dateText && timeText) {
            newDateTime = util.validatedDateTimeText(dateText, timeText)
        } else if(dateText && ! timeText) {
            newDateTime = util.validatedDateTimeText(dateText, '')
        } else if(! dateText && timeText) {
            newDateTime = util.validatedDateTimeText('', timeText)
        }
        if(!isNaN(newDateTime)) {
            return newDateTime
        }
        return false
    }

    RowLayout {

        id: layout

        Rectangle {
            width: 100
            height: 40
            color: util.QML_CONTROL_BG
            PK.TextField {
                id: dateTextInput
                objectName: "dateTextInput"
                anchors.fill: parent
                verticalAlignment: TextInput.AlignVCenter
                horizontalAlignment: TextInput.AlignHCenter
                color: root.enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
                onEditingFinished: onChanged()
                onTextChanged: onChanged()
                function onChanged() {
                    if(blocked)
                        return
                    blocked = true
                    var newDateTime = undefined
                    if(text) {
                        var validated = validatedTextInputs(text, timeTextInput.text)
                        if(validated) {
                            newDateTime = validated
                        }
                    }
                    root.dateTime = newDateTime
                    blocked = false
                }
                onFocusChanged: root.updateState()
                MouseArea {
                    propagateComposedEvents: true
                    onClicked: dateTextInput.selectAll()
                }
                Connections {
                    target: root
                    function onStateChanged() {
                        if(root.state == 'date-tumbler-shown') {
                            if(dateTextInput.text == util.BLANK_DATE_TEXT) {
                                dateTextInput.text = ''
                            }
                        } else if(root.state == 'tumblers-hidden') {
                            if(!validatedTextInputs(dateTextInput.text, '')) {
                                dateTextInput.text = util.BLANK_DATE_TEXT
                            }
                        }
                    }
                }            
            }
        }

        Rectangle {
            width: 95
            height: 40
            color: util.QML_CONTROL_BG
            PK.TextField {
                id: timeTextInput
                objectName: "timeTextInput"
                anchors.fill: parent
                verticalAlignment: TextInput.AlignVCenter
                horizontalAlignment: TextInput.AlignHCenter
                enabled: isValid(root.dateTime)
                color: (root.enabled && enabled) ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
                onTextChanged: onChanged()
                function onChanged() {
                    if(blocked)
                        return
                    if(!isValid(root.dateTime) && (text == util.BLANK_TIME_TEXT || text == ''))
                        return // avoid binding loop with `enabled`
                    blocked = true
                    var newDateTime = undefined
                    if(text) {
                        var validated = validatedTextInputs(dateTextInput.text, text)
                        if(validated) {
                            newDateTime = validated
                        }
                    }
                    root.dateTime = newDateTime
                    blocked = false
                }
                onFocusChanged: root.updateState()
                MouseArea {
                    propagateComposedEvents: true
                    onClicked: timeTextInput.selectAll()
                }
                Connections {
                    target: root
                    function onStateChanged() {
                        if(root.state == 'time-tumbler-shown') {
                            if(timeTextInput.text == util.BLANK_TIME_TEXT) {
                                timeTextInput.text = ''
                            }
                        }
                        else if(root.state == 'tumblers-hidden') {
                            if(!validatedTextInputs('', timeTextInput.text)) {
                                timeTextInput.text = util.BLANK_TIME_TEXT
                            }
                        }
                    }
                }
            }
        }

        PK.Button {
            id: inspectButton
            objectName: "inspectButton"
            enabled: root.showInspectButton && Global.isValidDateTime(root.dateTime)
            visible: root.showInspectButton
            source: '../../details-button.png'
            clip: true
            implicitWidth: 20
            implicitHeight: 20
            opacity: enabled ? .5 : 0
            Layout.leftMargin: 2
            onClicked: root.inspect()
            Behavior on opacity {
                NumberAnimation { duration: util.ANIM_DURATION_MS / 3; easing.type: Easing.InOutQuad }
            }
        }

        PK.Button {
            id: clearButton
            objectName: "clearButton"
            source: '../../clear-button.png'
            clip: true
            implicitWidth: 20
            implicitHeight: 20
            Layout.leftMargin: 2
            opacity: (isValid(root.dateTime) && dateTextInput.text != util.BLANK_DATE_TEXT && ! root.hideReset) ? .5 : 0
            enabled: opacity > 0 && ! root.hideReset
            onClicked: {
                root.forceActiveFocus()
                dateTime = undefined
                root.state = 'tumblers-hidden'
            }
            onFocusChanged: root.updateState()
            Behavior on opacity {
                NumberAnimation { duration: util.ANIM_DURATION_MS / 3; easing.type: Easing.InOutQuad }
            }
        }

    }


    //     id: buttonsRow
    //     height: 0
    //     implicitHeight: unsureBox.implicitHeight
    //     onHeightChanged: print('buttonsRow.onHeightChanged:', height)

    //     PK.CheckBox {
    //         id: unsureBox
    //         objectName: "unsureBox"
    //         text: 'Unsure'
    //         checkState: unsure
    //         // opacity: datePicker == null || (datePicker.state == 'shown' || datePicker.state == 'invalid') ? 1 : 0
    //         clip: true
    //         enabled: opacity > 0
    //         visible: !root.hideUnsure
    //         onCheckStateChanged: unsure = checkState
    //         onFocusChanged: root.updateState()
    //         Behavior on opacity {
    //             NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
    //         }
    //     }
}
