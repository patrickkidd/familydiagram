import QtQuick 2.15
import QtQuick.Controls 2.15

// Variant A — single-screen wizard. One scroll, name + birth date together.
// Root is sized by QQuickView (SizeRootObjectToView); do not anchor to parent.
Rectangle {
    id: root
    width: 390
    height: 844
    color: util.QML_WINDOW_BG

    property color itemBg: util.QML_ITEM_BG
    property color textColor: util.QML_TEXT_COLOR
    property color secondaryText: util.QML_INACTIVE_TEXT_COLOR
    property color borderColor: util.QML_ITEM_BORDER_COLOR
    property color accent: util.QML_SELECTION_COLOR
    property color danger: "#ff453a"

    // --- model state ---
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
    property bool canContinue: nameValid && dateValid()

    // ---------- field component ----------
    Component {
        id: fieldCell
        Item {
            property alias text: input.text
            property string placeholder: ""
            property bool showError: false
            property int maxLen: 0
            property var validator: null
            implicitHeight: 50
            Text {
                visible: input.text === ""
                anchors.left: parent.left; anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                text: parent.placeholder
                color: root.secondaryText
                font.pixelSize: 16
            }
            TextInput {
                id: input
                anchors.fill: parent
                anchors.leftMargin: 14; anchors.rightMargin: 14
                verticalAlignment: TextInput.AlignVCenter
                color: parent.showError ? root.danger : root.textColor
                font.pixelSize: 16
                clip: true
                maximumLength: parent.maxLen > 0 ? parent.maxLen : 32767
                validator: parent.validator
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: col.height + 40
        clip: true

        Column {
            id: col
            x: 20
            width: parent.width - 40
            topPadding: 80
            spacing: 18

            Text {
                text: "Welcome"
                color: root.textColor
                font.pixelSize: 30
                font.bold: true
            }
            Text {
                width: col.width - 40
                text: "Tell us who you are so your diagram and the assistant know which person is you."
                color: root.secondaryText
                font.pixelSize: 15
                wrapMode: Text.WordWrap
                lineHeight: 1.3
            }

            // YOUR NAME
            Text { text: "YOUR NAME"; color: root.secondaryText; font.pixelSize: 12; font.bold: true; leftPadding: 4; topPadding: 12 }
            Rectangle {
                width: col.width; height: 101; radius: 12
                color: root.itemBg; border.width: 1
                border.color: (!root.nameValid && root.firstName !== "") ? root.danger : root.borderColor
                Column {
                    anchors.fill: parent
                    Loader {
                        id: firstLoader
                        width: parent.width; height: 50
                        sourceComponent: fieldCell
                        onLoaded: { item.placeholder = "First name"; item.text = root.firstName }
                        Connections { target: firstLoader.item; function onTextChanged() { root.firstName = firstLoader.item.text } }
                    }
                    Rectangle { x: 14; width: parent.width - 14; height: 1; color: root.borderColor }
                    Loader {
                        id: lastLoader
                        width: parent.width; height: 50
                        sourceComponent: fieldCell
                        onLoaded: { item.placeholder = "Last name"; item.text = root.lastName }
                        Connections { target: lastLoader.item; function onTextChanged() { root.lastName = lastLoader.item.text } }
                    }
                }
            }
            Text {
                visible: !root.nameValid && root.firstName !== ""
                text: "First name is required."
                color: root.danger; font.pixelSize: 12; leftPadding: 4
            }

            // DATE OF BIRTH
            Text { text: "DATE OF BIRTH"; color: root.secondaryText; font.pixelSize: 12; font.bold: true; leftPadding: 4; topPadding: 12 }
            Rectangle {
                width: col.width; height: 50; radius: 12
                color: root.itemBg; border.width: 1
                border.color: !root.dateValid() ? root.danger : root.borderColor
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left; anchors.leftMargin: 14
                    spacing: 6
                    Loader { id: mLoader; width: 38; height: 40; sourceComponent: fieldCell
                        onLoaded: { item.placeholder = "MM"; item.maxLen = 2 }
                        Connections { target: mLoader.item; function onTextChanged() { root.birthMonth = mLoader.item.text } } }
                    Text { text: "/"; color: root.secondaryText; font.pixelSize: 16; anchors.verticalCenter: parent.verticalCenter }
                    Loader { id: dLoader; width: 38; height: 40; sourceComponent: fieldCell
                        onLoaded: { item.placeholder = "DD"; item.maxLen = 2 }
                        Connections { target: dLoader.item; function onTextChanged() { root.birthDay = dLoader.item.text } } }
                    Text { text: "/"; color: root.secondaryText; font.pixelSize: 16; anchors.verticalCenter: parent.verticalCenter }
                    Loader { id: yLoader; width: 64; height: 40; sourceComponent: fieldCell
                        onLoaded: { item.placeholder = "YYYY"; item.maxLen = 4 }
                        Connections { target: yLoader.item; function onTextChanged() { root.birthYear = yLoader.item.text } } }
                }
            }
            Text {
                visible: !root.dateValid()
                text: "Enter a valid date (MM / DD / YYYY)."
                color: root.danger; font.pixelSize: 12; leftPadding: 4
            }
            Text {
                visible: root.dateValid()
                text: "Optional — helps the assistant anchor ages and timelines."
                color: root.secondaryText; font.pixelSize: 12; leftPadding: 4
            }
        }
    }

    // ---------- bottom action bar ----------
    Rectangle {
        anchors.bottom: parent.bottom; width: parent.width; height: 120
        color: util.QML_WINDOW_BG
        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: root.borderColor }

        Rectangle {
            id: primaryBtn
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: 16
            width: parent.width - 40; height: 50; radius: 14
            color: root.canContinue ? root.accent : root.borderColor
            opacity: root.canContinue ? 1.0 : 0.5
            Text { anchors.centerIn: parent; text: "Get Started"; color: "white"; font.pixelSize: 17; font.bold: true }
            MouseArea { anchors.fill: parent; enabled: root.canContinue
                onClicked: console.log("SAVE name=" + root.firstName + " " + root.lastName + " dob=" + root.birthMonth + "/" + root.birthDay + "/" + root.birthYear) }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: primaryBtn.bottom; anchors.topMargin: 14
            text: "Skip for now"; color: root.accent; font.pixelSize: 15
            MouseArea { anchors.fill: parent; onClicked: console.log("SKIP") }
        }
    }
}
