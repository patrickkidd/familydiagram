import QtQuick 2.15
import QtQuick.Controls 2.15

// FINAL — FD-321 user-details, single-screen (variant A, chosen 2026-06-15).
// One reusable UserDetailsForm drives BOTH surfaces:
//   - first-launch wizard (this file shows wizardMode=true: title/subtitle + Get Started + Skip)
//   - Settings profile editor (wizardMode=false: header back + Save, no Skip)
// Real implementation maps:
//   firstName/lastName -> primary Person node name/lastName
//   birth date         -> a Birth EVENT on the primary node (not a scalar field)
//   skip               -> AppConfig pref "personalProfilePrompted" so the wizard never nags
//   fields             -> swap the inline cells for PK.TextField / PK.DatePicker in the app
Rectangle {
    id: root
    width: 390
    height: 844
    color: util.QML_WINDOW_BG

    property bool wizardMode: true   // demo: the wizard surface

    property color itemBg: util.QML_ITEM_BG
    property color textColor: util.QML_TEXT_COLOR
    property color secondaryText: util.QML_INACTIVE_TEXT_COLOR
    property color borderColor: util.QML_ITEM_BORDER_COLOR
    property color accent: util.QML_SELECTION_COLOR
    property color danger: "#ff453a"

    // ---- shared form component (the reusable piece) ----
    Component {
        id: userDetailsForm
        Flickable {
            id: form
            property string firstName: ""
            property string lastName: ""
            property string birthMonth: ""
            property string birthDay: ""
            property string birthYear: ""
            function dateEmpty() { return birthMonth === "" && birthDay === "" && birthYear === "" }
            function dateValid() {
                if (dateEmpty()) return true
                var m = parseInt(birthMonth), d = parseInt(birthDay), y = parseInt(birthYear)
                if (isNaN(m) || isNaN(d) || isNaN(y)) return false
                if (m < 1 || m > 12) return false
                if (d < 1 || d > 31) return false
                if (birthYear.length !== 4 || y < 1900 || y > 2025) return false
                return true
            }
            property bool nameValid: firstName.trim() !== ""
            property bool valid: nameValid && dateValid()

            contentHeight: col.height + 40
            clip: true

            Component {
                id: cell
                Item {
                    property alias text: ti.text
                    property string placeholder: ""
                    property int maxLen: 0
                    implicitHeight: 50
                    Text {
                        visible: ti.text === ""
                        anchors.left: parent.left; anchors.leftMargin: 14
                        anchors.verticalCenter: parent.verticalCenter
                        text: parent.placeholder; color: root.secondaryText; font.pixelSize: 16
                    }
                    TextInput {
                        id: ti
                        anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14
                        verticalAlignment: TextInput.AlignVCenter
                        color: root.textColor; font.pixelSize: 16; clip: true
                        maximumLength: parent.maxLen > 0 ? parent.maxLen : 32767
                    }
                }
            }

            Column {
                id: col
                x: 20; width: form.width - 40
                topPadding: root.wizardMode ? 80 : 20
                spacing: 18

                Text {
                    visible: root.wizardMode
                    text: "Welcome"; color: root.textColor; font.pixelSize: 30; font.bold: true
                }
                Text {
                    visible: root.wizardMode
                    width: col.width - 40
                    text: "Tell us who you are so your diagram and the assistant know which person is you."
                    color: root.secondaryText; font.pixelSize: 15; wrapMode: Text.WordWrap; lineHeight: 1.3
                }

                Text { text: "YOUR NAME"; color: root.secondaryText; font.pixelSize: 12; font.bold: true; leftPadding: 4; topPadding: root.wizardMode ? 12 : 0 }
                Rectangle {
                    width: col.width; height: 101; radius: 12; color: root.itemBg
                    border.width: 1
                    border.color: (!form.nameValid && form.firstName !== "") ? root.danger : root.borderColor
                    Column {
                        anchors.fill: parent
                        Loader { id: fl; width: parent.width; height: 50; sourceComponent: cell
                            onLoaded: item.placeholder = "First name"
                            Connections { target: fl.item; function onTextChanged() { form.firstName = fl.item.text } } }
                        Rectangle { x: 14; width: parent.width - 14; height: 1; color: root.borderColor }
                        Loader { id: ll; width: parent.width; height: 50; sourceComponent: cell
                            onLoaded: item.placeholder = "Last name"
                            Connections { target: ll.item; function onTextChanged() { form.lastName = ll.item.text } } }
                    }
                }
                Text { visible: !form.nameValid && form.firstName !== ""
                    text: "First name is required."; color: root.danger; font.pixelSize: 12; leftPadding: 4 }

                Text { text: "DATE OF BIRTH"; color: root.secondaryText; font.pixelSize: 12; font.bold: true; leftPadding: 4; topPadding: 12 }
                Rectangle {
                    width: col.width; height: 50; radius: 12; color: root.itemBg
                    border.width: 1; border.color: !form.dateValid() ? root.danger : root.borderColor
                    Row {
                        anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 14; spacing: 6
                        Loader { id: ml; width: 38; height: 40; sourceComponent: cell
                            onLoaded: { item.placeholder = "MM"; item.maxLen = 2 }
                            Connections { target: ml.item; function onTextChanged() { form.birthMonth = ml.item.text } } }
                        Text { text: "/"; color: root.secondaryText; font.pixelSize: 16; anchors.verticalCenter: parent.verticalCenter }
                        Loader { id: dl; width: 38; height: 40; sourceComponent: cell
                            onLoaded: { item.placeholder = "DD"; item.maxLen = 2 }
                            Connections { target: dl.item; function onTextChanged() { form.birthDay = dl.item.text } } }
                        Text { text: "/"; color: root.secondaryText; font.pixelSize: 16; anchors.verticalCenter: parent.verticalCenter }
                        Loader { id: yl; width: 64; height: 40; sourceComponent: cell
                            onLoaded: { item.placeholder = "YYYY"; item.maxLen = 4 }
                            Connections { target: yl.item; function onTextChanged() { form.birthYear = yl.item.text } } }
                    }
                }
                Text { visible: !form.dateValid()
                    text: "Enter a valid date (MM / DD / YYYY)."; color: root.danger; font.pixelSize: 12; leftPadding: 4 }
                Text { visible: form.dateValid()
                    text: "Optional — helps the assistant anchor ages and timelines."
                    color: root.secondaryText; font.pixelSize: 12; leftPadding: 4 }
            }
        }
    }

    Loader { id: formLoader; anchors.top: parent.top; anchors.bottom: bar.top; width: parent.width; sourceComponent: userDetailsForm }

    // ---- action bar (wizard: Get Started + Skip / settings: Save) ----
    Rectangle {
        id: bar
        anchors.bottom: parent.bottom; width: parent.width; height: root.wizardMode ? 120 : 86
        color: util.QML_WINDOW_BG
        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: root.borderColor }

        Rectangle {
            id: primaryBtn
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: 16
            width: parent.width - 40; height: 50; radius: 14
            property bool ok: formLoader.item ? formLoader.item.valid : false
            color: ok ? root.accent : root.borderColor
            opacity: ok ? 1.0 : 0.5
            Text { anchors.centerIn: parent; text: root.wizardMode ? "Get Started" : "Save"; color: "white"; font.pixelSize: 17; font.bold: true }
            MouseArea { anchors.fill: parent; enabled: primaryBtn.ok
                onClicked: console.log("SAVE", formLoader.item.firstName, formLoader.item.lastName,
                                       formLoader.item.birthMonth + "/" + formLoader.item.birthDay + "/" + formLoader.item.birthYear) }
        }
        Text {
            visible: root.wizardMode
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: primaryBtn.bottom; anchors.topMargin: 14
            text: "Skip for now"; color: root.accent; font.pixelSize: 15
            MouseArea { anchors.fill: parent; onClicked: console.log("SKIP -> set personalProfilePrompted=true") }
        }
    }
}
