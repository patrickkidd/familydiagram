import QtQuick 2.15
import QtQuick.Controls 2.15

// Variant B — multi-step paged wizard. Welcome -> Name -> Birth date -> Done.
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
    function canAdvance() {
        if (swipe.currentIndex === 1) return nameValid
        if (swipe.currentIndex === 2) return dateValid()
        return true
    }

    Component {
        id: fieldCell
        Item {
            property alias text: input.text
            property string placeholder: ""
            property int maxLen: 0
            implicitHeight: 50
            Text {
                visible: input.text === ""
                anchors.left: parent.left; anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                text: parent.placeholder; color: root.secondaryText; font.pixelSize: 16
            }
            TextInput {
                id: input
                anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14
                verticalAlignment: TextInput.AlignVCenter
                color: root.textColor; font.pixelSize: 16; clip: true
                maximumLength: parent.maxLen > 0 ? parent.maxLen : 32767
            }
        }
    }

    // Skip top-right
    Text {
        anchors.top: parent.top; anchors.topMargin: 40
        anchors.right: parent.right; anchors.rightMargin: 20
        text: "Skip"; color: root.accent; font.pixelSize: 15; z: 50
        MouseArea { anchors.fill: parent; onClicked: console.log("SKIP") }
    }

    SwipeView {
        id: swipe
        anchors.top: parent.top; anchors.topMargin: 90
        anchors.left: parent.left; anchors.right: parent.right
        anchors.bottom: footer.top
        interactive: false
        clip: true

        // Page 0 — Welcome
        Item {
            Column {
                anchors.centerIn: parent
                width: parent.width - 60
                spacing: 18
                Text { text: "👋"; font.pixelSize: 56; anchors.horizontalCenter: parent.horizontalCenter }
                Text { text: "Welcome to\nFamily Diagram"; color: root.textColor; font.pixelSize: 28; font.bold: true
                    horizontalAlignment: Text.AlignHCenter; width: parent.width; wrapMode: Text.WordWrap }
                Text { text: "A couple of quick details so your diagram knows which person is you."
                    color: root.secondaryText; font.pixelSize: 16; horizontalAlignment: Text.AlignHCenter
                    width: parent.width; wrapMode: Text.WordWrap; lineHeight: 1.3 }
            }
        }

        // Page 1 — Name
        Item {
            Column {
                x: 30; width: parent.width - 60; topPadding: 20; spacing: 16
                Text { text: "What's your name?"; color: root.textColor; font.pixelSize: 24; font.bold: true }
                Text { text: "This labels your own node on the diagram."
                    color: root.secondaryText; font.pixelSize: 15; width: parent.width; wrapMode: Text.WordWrap }
                Rectangle {
                    width: parent.width; height: 101; radius: 12; color: root.itemBg
                    border.width: 1; border.color: root.borderColor
                    Column {
                        anchors.fill: parent
                        Loader { id: fL; width: parent.width; height: 50; sourceComponent: fieldCell
                            onLoaded: { item.placeholder = "First name"; item.text = root.firstName }
                            Connections { target: fL.item; function onTextChanged() { root.firstName = fL.item.text } } }
                        Rectangle { x: 14; width: parent.width - 14; height: 1; color: root.borderColor }
                        Loader { id: lL; width: parent.width; height: 50; sourceComponent: fieldCell
                            onLoaded: { item.placeholder = "Last name"; item.text = root.lastName }
                            Connections { target: lL.item; function onTextChanged() { root.lastName = lL.item.text } } }
                    }
                }
                Text { visible: !root.nameValid && root.firstName !== ""
                    text: "First name is required."; color: root.danger; font.pixelSize: 12 }
            }
        }

        // Page 2 — Birth date
        Item {
            Column {
                x: 30; width: parent.width - 60; topPadding: 20; spacing: 16
                Text { text: "When were you born?"; color: root.textColor; font.pixelSize: 24; font.bold: true }
                Text { text: "Optional. Helps anchor ages and dates the assistant hears."
                    color: root.secondaryText; font.pixelSize: 15; width: parent.width; wrapMode: Text.WordWrap }
                Rectangle {
                    width: parent.width; height: 50; radius: 12; color: root.itemBg
                    border.width: 1; border.color: !root.dateValid() ? root.danger : root.borderColor
                    Row {
                        anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 14; spacing: 6
                        Loader { id: mL; width: 40; height: 40; sourceComponent: fieldCell
                            onLoaded: { item.placeholder = "MM"; item.maxLen = 2 }
                            Connections { target: mL.item; function onTextChanged() { root.birthMonth = mL.item.text } } }
                        Text { text: "/"; color: root.secondaryText; font.pixelSize: 16; anchors.verticalCenter: parent.verticalCenter }
                        Loader { id: dL; width: 40; height: 40; sourceComponent: fieldCell
                            onLoaded: { item.placeholder = "DD"; item.maxLen = 2 }
                            Connections { target: dL.item; function onTextChanged() { root.birthDay = dL.item.text } } }
                        Text { text: "/"; color: root.secondaryText; font.pixelSize: 16; anchors.verticalCenter: parent.verticalCenter }
                        Loader { id: yL; width: 66; height: 40; sourceComponent: fieldCell
                            onLoaded: { item.placeholder = "YYYY"; item.maxLen = 4 }
                            Connections { target: yL.item; function onTextChanged() { root.birthYear = yL.item.text } } }
                    }
                }
                Text { visible: !root.dateValid(); text: "Enter a valid date (MM / DD / YYYY)."
                    color: root.danger; font.pixelSize: 12 }
            }
        }

        // Page 3 — Done
        Item {
            Column {
                anchors.centerIn: parent; width: parent.width - 60; spacing: 16
                Text { text: "✓"; font.pixelSize: 56; color: root.accent; anchors.horizontalCenter: parent.horizontalCenter }
                Text { text: root.firstName !== "" ? ("You're all set, " + root.firstName + ".") : "You're all set."
                    color: root.textColor; font.pixelSize: 24; font.bold: true
                    horizontalAlignment: Text.AlignHCenter; width: parent.width; wrapMode: Text.WordWrap }
                Text { text: "You can change these any time in Settings."
                    color: root.secondaryText; font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter
                    width: parent.width; wrapMode: Text.WordWrap }
            }
        }
    }

    PageIndicator {
        anchors.bottom: footer.top; anchors.bottomMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        count: swipe.count; currentIndex: swipe.currentIndex
    }

    // Footer Back / Next
    Rectangle {
        id: footer
        anchors.bottom: parent.bottom; width: parent.width; height: 96
        color: util.QML_WINDOW_BG
        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: root.borderColor }

        Text {
            visible: swipe.currentIndex > 0
            anchors.left: parent.left; anchors.leftMargin: 24
            anchors.top: parent.top; anchors.topMargin: 28
            text: "Back"; color: root.accent; font.pixelSize: 17
            MouseArea { anchors.fill: parent; onClicked: swipe.currentIndex-- }
        }
        Rectangle {
            anchors.right: parent.right; anchors.rightMargin: 20
            anchors.top: parent.top; anchors.topMargin: 16
            width: 120; height: 50; radius: 14
            color: root.canAdvance() ? root.accent : root.borderColor
            opacity: root.canAdvance() ? 1.0 : 0.5
            Text { anchors.centerIn: parent
                text: swipe.currentIndex === swipe.count - 1 ? "Finish" : "Next"
                color: "white"; font.pixelSize: 17; font.bold: true }
            MouseArea { anchors.fill: parent; enabled: root.canAdvance()
                onClicked: {
                    if (swipe.currentIndex === swipe.count - 1) console.log("SAVE+FINISH name=" + root.firstName)
                    else swipe.currentIndex++
                }
            }
        }
    }
}
