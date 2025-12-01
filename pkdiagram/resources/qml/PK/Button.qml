import QtQuick 2.12
import QtQuick.Controls 2.5
import QtGraphicalEffects 1.13


Control {

    id: root
    property string source
    property string text
    property bool pill: false

    signal clicked
    property bool down: mouseArea.pressed
    opacity: enabled && !down ? 1.0 : .5
    property string defaultBackgroundColor: pill ? 'transparent' : (text ? util.QML_CONTROL_BG : 'transparent')
    property string textColor: root.enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
    property bool invertForDarkMode: true

    implicitHeight: preferred_implicitHeight
    readonly property var preferred_implicitHeight: pill ? 32 : 40

    width: text ? Math.max(textItem.contentWidth + util.QML_MARGINS * 2, height) : height

    palette.highlight: util.QML_HIGHLIGHT_COLOR

    background: Rectangle {
        color: defaultBackgroundColor
        radius: pill ? height / 2 : 0
        border.color: pill ? util.QML_ITEM_BORDER_COLOR : root.palette.highlight
        border.width: pill ? 1.5 : (root.activeFocus ? 2 : 0)
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        onClicked: root.clicked()
    }
    
    Keys.onPressed: {
        if(event.key == Qt.Key_Space || event.key == Qt.Key_Enter || event.key == Qt.Key_Return) {
            event.accepted = true
            clicked()
        }
    }

    Behavior on opacity {
        NumberAnimation {
            duration: util.ANIM_DURATION_MS / 3
            easing.type: Easing.OutQuad
        }
    }

    contentItem: Item {

        onActiveFocusChanged: print(border.color, border.width)

        Text {
            id: textItem
            text: root.text
            height: root.height
            width: Math.max(root.width, contentWidth)
            visible: root.text
            color: root.textColor
            font.bold: root.pill
            horizontalAlignment: Qt.AlignHCenter
            verticalAlignment: Qt.AlignVCenter
        }

        Image {
            id: mainImage
            source: root.source
            anchors.fill: parent
            visible: (!invertForDarkMode || !util.IS_UI_DARK_MODE) && !root.text
        }

        Image {
            id: allWhite
            visible: false
            source: '../../all-white.png'
        }

        Blend {
            visible: (invertForDarkMode && util.IS_UI_DARK_MODE) && !root.text
            source: mainImage
            foregroundSource: allWhite
            mode: 'negation'
            anchors.fill: parent
        }

    }
}
