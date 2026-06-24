/*
FD-321 — reusable user-details body. Drives BOTH surfaces:
  - first-launch wizard (wizardMode: true): Welcome title/subtitle + Get Started + Skip
  - Settings profile editor (wizardMode: false): plain form, Save lives in the page chrome

firstName/lastName map to the primary Person node's name/lastName; the date maps
to a Birth EVENT on that node (a fully-empty date is allowed/optional). Exposes
firstName, lastName, birth Y/M/D, and `valid` for the host's primary button.

The birth date reuses the EventForm idiom: a clickable/focusable DatePickerButtons
text field plus a DatePicker tumbler, both syncing to a single canonical
`birthDateTime` (a bare DatePicker can't be clicked into).
*/

import QtQuick 2.15
import QtQuick.Controls 2.15
import "../PK" 1.0 as PK

Flickable {
    id: form

    property bool wizardMode: true

    property color itemBg: util.QML_ITEM_BG
    property color textColor: util.QML_TEXT_COLOR
    property color secondaryText: util.QML_INACTIVE_TEXT_COLOR
    property color borderColor: util.QML_ITEM_BORDER_COLOR
    property color danger: "#FF453A"

    property alias firstName: firstNameField.text
    property alias lastName: lastNameField.text

    // Canonical birth date; both date controls write to it and sync back from it.
    property var birthDateTime

    function _dateValid() {
        return birthDateTime !== undefined && birthDateTime !== null && !isNaN(birthDateTime)
    }

    // Birth date as separate ints so the controller takes them directly; 0 = unset.
    readonly property int birthYear: _dateValid() ? birthDateTime.getFullYear() : 0
    readonly property int birthMonth: _dateValid() ? birthDateTime.getMonth() + 1 : 0
    readonly property int birthDay: _dateValid() ? birthDateTime.getDate() : 0

    // First name required; date is optional and the controls only ever produce a
    // real calendar date, so there is no "entered-but-invalid" state.
    readonly property bool nameValid: firstNameField.text.trim() !== ""
    readonly property bool valid: nameValid

    property bool firstNameTouched: false

    function loadProfile(profile) {
        firstNameField.text = profile.firstName || ""
        lastNameField.text = profile.lastName || ""
        if (profile.birthYear && profile.birthMonth && profile.birthDay) {
            form.birthDateTime = new Date(
                parseInt(profile.birthYear),
                parseInt(profile.birthMonth) - 1,
                parseInt(profile.birthDay))
        } else {
            form.birthDateTime = undefined
        }
        firstNameTouched = false
    }

    contentHeight: col.height + 40
    clip: true

    Column {
        id: col
        x: 20
        width: form.width - 40
        topPadding: form.wizardMode ? 60 : 20
        spacing: 16

        Text {
            visible: form.wizardMode
            text: "Welcome"
            color: form.textColor
            font.pixelSize: 30
            font.bold: true
        }
        Text {
            visible: form.wizardMode
            width: col.width
            text: "Tell us who you are so your diagram and the assistant know which person is you."
            color: form.secondaryText
            font.pixelSize: 15
            wrapMode: Text.WordWrap
            lineHeight: 1.3
            bottomPadding: 8
        }

        Text {
            text: "YOUR NAME"
            color: form.secondaryText
            font.pixelSize: 12
            font.bold: true
            leftPadding: 4
        }
        Rectangle {
            width: col.width
            height: 101
            radius: 12
            color: form.itemBg
            border.width: 1
            border.color: (form.firstNameTouched && !form.nameValid) ? form.danger : form.borderColor

            Column {
                anchors.fill: parent

                PK.TextField {
                    id: firstNameField
                    objectName: "firstNameField"
                    width: parent.width
                    height: 50
                    leftPadding: 14
                    placeholderText: "First name"
                    background: Item {}
                    focus: true
                    KeyNavigation.tab: lastNameField
                    onTextChanged: form.firstNameTouched = true
                    onEditingFinished: form.firstNameTouched = true
                }
                Rectangle {
                    x: 14
                    width: parent.width - 14
                    height: 1
                    color: form.borderColor
                }
                PK.TextField {
                    id: lastNameField
                    objectName: "lastNameField"
                    width: parent.width
                    height: 50
                    leftPadding: 14
                    placeholderText: "Last name"
                    background: Item {}
                    KeyNavigation.tab: birthDateButtons.firstTabItem
                    KeyNavigation.backtab: firstNameField
                }
            }
        }
        Text {
            visible: form.firstNameTouched && !form.nameValid
            text: "First name is required."
            color: form.danger
            font.pixelSize: 12
            leftPadding: 4
        }

        Text {
            text: "DATE OF BIRTH"
            color: form.secondaryText
            font.pixelSize: 12
            font.bold: true
            leftPadding: 4
            topPadding: 8
        }
        Rectangle {
            width: col.width
            radius: 12
            color: form.itemBg
            border.width: 1
            border.color: form.borderColor
            height: dateColumn.height + 16

            Column {
                id: dateColumn
                x: 14
                width: parent.width - 28
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4

                PK.DatePickerButtons {
                    id: birthDateButtons
                    objectName: "birthDateButtons"
                    datePicker: birthDatePicker
                    hideTime: true
                    backTabItem: lastNameField
                    width: parent.width
                    onDateTimeChanged: form.birthDateTime = dateTime
                    Connections {
                        target: form
                        function onBirthDateTimeChanged() {
                            if (birthDateButtons.dateTime != form.birthDateTime)
                                birthDateButtons.dateTime = form.birthDateTime
                        }
                    }
                }

                PK.DatePicker {
                    id: birthDatePicker
                    objectName: "birthDatePicker"
                    // No shouldShow: matches EventForm — the tumbler stays collapsed
                    // (implicitHeight 0) until birthDateButtons focuses it via updateState().
                    width: parent.width
                    onDateTimeChanged: form.birthDateTime = dateTime
                    Connections {
                        target: form
                        function onBirthDateTimeChanged() {
                            if (birthDatePicker.dateTime != form.birthDateTime)
                                birthDatePicker.dateTime = form.birthDateTime
                        }
                    }
                }
            }
        }
        Text {
            text: "Optional — helps the assistant anchor ages and timelines."
            color: form.secondaryText
            font.pixelSize: 12
            leftPadding: 4
        }
    }
}
