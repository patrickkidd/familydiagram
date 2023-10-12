import QtQuick 2.12
import QtQuick.Controls 2.5


Button {
    id: root
    
    property bool editing: false

    TextInput {
        id: textInput
        visible: editing
        width: parent.width
        height: parent.height
        onHeightChanged: print(height, text)
        anchors.centerIn: parent
        verticalAlignment: TextInput.AlignVCenter
        horizontalAlignment: TextInput.AlignHCenter
        onTextChanged: if(root.text != text) root.text = text
    }
    onTextChanged: if(textInput.text != text) textInput.text = text
}
