import QtQuick 2.12
import QtQuick.Controls 2.5
import LineEditBackEnd 1.0

// maybe a better text input that actually raises the kb on iOS
    
TextField {

    id: root

    LineEditBackEnd { id: backend }

    property bool syncing: false
    property bool ios: Qt.platform.os == 'ios'
    property bool givenFocus: false
    property color defaultTextColor: enabled ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
    property color defaultBackgroundColor: util.QML_WINDOW_BG
    color: defaultTextColor
    selectionColor: util.QML_HIGHLIGHT_COLOR
    selectByMouse: true
    selectedTextColor: 'black'
    palette.base: defaultBackgroundColor
    palette.highlight: util.QML_HIGHLIGHT_COLOR
    palette.mid: util.QML_ITEM_BORDER_COLOR

    font.pixelSize: util.TEXT_FONT_SIZE

    onFocusChanged: {
        if(ios && !syncing && focus) {
            syncing = true
            backend.beginFocus(text, root, cursorPosition, selectionStart, selectionEnd)
            givenFocus = true
            syncing = false
        } else if(ios && givenFocus && !focus) {
            backend.endFocus()
            givenFocus = false
        }
        if(focus) {
            selectAll()
//            background.border.color = util.QML_HIGHLIGHT_COLOR
        } else {
//            background.border.color = util.QML_ITEM_BORDER_COLOR
        }
    }

    onSelectionStartChanged: {
        if(ios && !syncing) {
            syncing = true
            backend.do_setSelection(text, selectionStart, selectionEnd)
            syncing = false
        }
    }
    onSelectionEndChanged: {
        if(ios && !syncing) {
            syncing = true
            backend.do_setSelection(text, selectionStart, selectionEnd)
            syncing = false
        }
    }

    
    onCursorPositionChanged: {
        if(ios && !syncing) {
            syncing = true
            backend.do_setCursorPosition(cursorPosition, selectionStart, selectionEnd)
            syncing = false
        }
    }

    Connections {
        target: backend
        function onTextChanged() {
            if(ios && !syncing) {
                syncing = true
                root.text = backend.getText()
                root.cursorPosition = backend.getCursorPosition()
                syncing = false
            }
        }
        function onCursorPositionChanged(_old, _new) {
            if(ios && !syncing) {
                syncing = true
                cursorPosition = _new
                syncing = false
            }
        }
        function onSelectionChanged() {
            if(ios && !syncing) {
                syncing = true
                select(backend.selectionStart(), backend.selectionEnd())
                syncing = false
            }
        }
        
        function onEditingFinished() { root.parent.forceActiveFocus() }
    }
    
}    

