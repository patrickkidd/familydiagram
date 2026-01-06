import QtQuick 2.12
import QtQuick.Window 2.2
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." 1.0 as PK
import "../js/Global.js" as Global


Rectangle {

    id: root

    implicitHeight: layout.implicitHeight
    implicitWidth: layout.implicitWidth

    // The first item in this chain for KeyNavigation.tab on an external item
    readonly property var firstTabItem: dateTextInput
    // The first item in this chain for KeyNavigation.backtab on an external item
    readonly property var lastTabItem: timeTextInput
    // Explicit keyNavigation.tab set on the last item in this chain
    property var tabItem
    // Explicit keyNavigation.backtab set on the first item in this chain
    property var backTabItem

    property var dateTextInput: dateTextInput
    property var timeTextInput: timeTextInput
    property var clearButton: clearButton
    property var datePicker: null
    property var timePicker: null
    property var dateTime
    property int unsure: Qt.Unchecked
    property bool hideUnsure: false
    property bool hideReset: false
    property bool hideTime: false
    property bool showInspectButton: false
    property bool blocked: false
    readonly property var textInput: dateTextInput

    signal inspect

    color: 'transparent'

    function isValid(_dateTime) {
        return _dateTime !== undefined && _dateTime !== null && !isNaN(_dateTime)
    }

    function clear() {
        root.dateTime = undefined
        root.unsure = Qt.Unchecked
    }

    Keys.onPressed: {
        if(event.key == Qt.Key_Return || event.key == Qt.Key_Enter) {
            event.accepted = true
            root.forceActiveFocus()
        }
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
            if (datePicker) datePicker.shouldShow = true
            if (timePicker) timePicker.shouldShow = false
        } else if(timeTextInput.focus) {
            state = 'time-tumbler-shown'
            if (datePicker) datePicker.shouldShow = false
            if (timePicker) timePicker.shouldShow = true
        } else {
            state = 'tumblers-hidden'
            if (datePicker) datePicker.shouldShow = false
            if (timePicker) timePicker.shouldShow = false
        }
    }

    // onUnsureChanged: unsureBox.checkState = unsure

    onDateTimeChanged: {

        // update date text
        if(!dateTextInput.focus || (datePicker && datePicker.moving)) {
            root.blocked = true
            if(isValid(root.dateTime)) {
                dateTextInput.text = util.dateString(dateTime)
            } else {
                dateTextInput.text = util.BLANK_DATE_TEXT
            }
            root.blocked = false
        }

        // update time text
        if(!timeTextInput.focus || (timePicker && timePicker.moving)) {
            root.blocked = true
            if(isValid(root.dateTime)) {
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
                palette.base: util.QML_ITEM_BG
                KeyNavigation.tab: timeTextInput
                KeyNavigation.backtab: root.backTabItem ? root.backTabItem : null
                Keys.onTabPressed: {
                    Global.focusNextItemInFocusChain(KeyNavigation.tab, true)
                    event.accepted = true
                }
                Keys.onBacktabPressed: {
                    Global.focusNextItemInFocusChain(KeyNavigation.backtab, false)
                    event.accepted = true
                }
                onEditingFinished: onChanged()
                onTextChanged: onChanged()
                function onChanged() {
                    if(root.blocked)
                        return
                    root.blocked = true
                    var newDateTime = undefined
                    if(text) {
                        var validated = validatedTextInputs(text, timeTextInput.text)
                        if(validated) {
                            newDateTime = validated
                        }
                    }
                    root.dateTime = newDateTime
                    root.blocked = false
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
            visible: !root.hideTime
            color: util.QML_CONTROL_BG
            PK.TextField {
                id: timeTextInput
                objectName: "timeTextInput"
                anchors.fill: parent
                verticalAlignment: TextInput.AlignVCenter
                horizontalAlignment: TextInput.AlignHCenter
                enabled: isValid(root.dateTime)
                color: (root.enabled && enabled) ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
                palette.base: util.QML_ITEM_BG
                KeyNavigation.tab: root.tabItem ? root.tabItem : null
                KeyNavigation.backtab: inspectButton
                Keys.onTabPressed: {
                    Global.focusNextItemInFocusChain(KeyNavigation.tab, true)
                    event.accepted = true
                }
                Keys.onBacktabPressed: {
                    Global.focusNextItemInFocusChain(KeyNavigation.backtab, false)
                    event.accepted = true
                }
                onEditingFinished: onChanged()
                onTextChanged: onChanged()
                function onChanged() {
                    if(root.blocked)
                        return
                    if(!isValid(root.dateTime) && (text == util.BLANK_TIME_TEXT || text == ''))
                        return // avoid binding loop with `enabled`
                    if(text) {
                        root.blocked = true
                        var newDateTime = validatedTextInputs(dateTextInput.text, text)
                        // print("newDateTime: " + newDateTime + ', ' + text)
                        if(!newDateTime) {
                            // just allow clearing the time section
                            newDateTime = new Date(
                                root.dateTime.getFullYear(),
                                root.dateTime.getMonth(),
                                root.dateTime.getDate(),
                                0, 0, 0, 0
                            )
                        }
                        if(newDateTime.getTime() !== root.dateTime.getTime()) {
                            // print('onChanged: root.dateTime (' + root.dateTime + ') = newDateTime (' + newDateTime + ')')
                            root.dateTime = newDateTime
                        }
                        root.blocked = false
                    }
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
            KeyNavigation.tab: clearButton
            KeyNavigation.backtab: timeTextInput
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
            opacity: (isValid(root.dateTime) && dateTextInput.text != util.BLANK_DATE_TEXT && ! root.hideReset) ? .5 : 0
            enabled: opacity > 0 && ! root.hideReset
            Layout.leftMargin: 2
            KeyNavigation.tab: root.tabItem ? root.tabItem : null
            KeyNavigation.backtab: inspectButton
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
