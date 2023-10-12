import QtQuick 2.5
import QtQuick.Controls 2.5
import QtQuick.Window 2.13
import "." 1.0 as PK


PK.ComboBox {
    
    property string color: model[currentIndex] != undefined ? model[currentIndex] : 'transparent'
    currentIndex: model.indexOf(color)
    
    id: root
    model: util.ABLETON_COLORS
    delegate: ItemDelegate {
        rightPadding: 15
        Rectangle {
            color: modelData
            width: root.implicitWidth
            height: root.implicitHeight
        }
    }

    // take from default
    contentItem: TextField {
        leftPadding: !root.mirrored ? 12 : root.editable && activeFocus ? 3 : 1
        rightPadding: root.mirrored ? 12 : root.editable && activeFocus ? 3 : 1
        topPadding: 6 - root.padding
        bottomPadding: 6 - root.padding

        text: root.editable ? root.editText : root.displayText

        enabled: root.editable
        autoScroll: root.editable
        readOnly: root.down
        inputMethodHints: root.inputMethodHints
        validator: root.validator

        font: root.font
        /* color: root.editable ? root.palette.text : root.palette.buttonText */
        color: 'transparent' // PK.Globals.isDarkColor(root.color) ? 'white' : 'black'
        selectionColor: root.palette.highlight
        selectedTextColor: root.palette.highlightedText
        verticalAlignment: Text.AlignVCenter

        background: Rectangle {
            visible: root.enabled && root.editable && !root.flat
            border.width: parent && parent.activeFocus ? 2 : 1
            border.color: parent && parent.activeFocus ? root.palette.highlight : root.palette.button
            color: root.palette.base
        }
    }

    background: Rectangle {
        implicitWidth: 140
        implicitHeight: 40

        // color: root.down ? root.palette.mid : root.palette.button
        color: {
            if(root.model[currentIndex] != undefined) {
                if(root.down) {
                    return Qt.lighter(root.model[currentIndex], 2.0)
                } else {
                    return root.model[currentIndex]
                }
            } else {
                return 'transparent'
            }
        } 
        border.color: root.down || root.activeFocus ? root.palette.highlight : root.palette.mid
        border.width: !root.editable && (root.down || root.visualFocus) ? 2 : 1
        visible: !root.flat || root.down
    }
    
}
