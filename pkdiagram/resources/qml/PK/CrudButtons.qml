import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.12
import "." 1.0 as PK


PK.ToolBar {
    id: root
    height: util.QML_ITEM_HEIGHT
    spacing: height / 2
    property int margin: util.QML_MARGINS / 2

    position: PK.ToolBar.Footer

    signal add
    signal addEvent
    signal addEmotion
    signal remove
    signal duplicate
    signal inspect
    signal filter
    signal exclusive
    signal done

    property bool addButton: false
    property bool addEventButton: false
    property bool addEmotionButton: false
    property bool removeButton: false
    property bool duplicateButton: false
    property bool inspectButton: false
    property bool filterButton: false
    property bool exclusiveBox: false
    property bool storePositionsBox: false
    property bool doneButton: false

    property bool addButtonEnabled: true
    property bool addEventButtonEnabled: true
    property bool addEmotionButtonEnabled: true
    property bool removeButtonEnabled: true
    property bool duplicateButtonEnabled: true
    property bool inspectButtonEnabled: true
    property bool filterButtonEnabled: true
    property bool storePositionsBoxEnabled: true
    property bool storePositions: false
    property bool exclusiveBoxEnabled: true
    property bool exclusiveChecked: false
    property bool doneButtonEnabled: true
    
    property int buttonHeight: 21
    
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: margin
        anchors.rightMargin: margin
        spacing: margin
        PK.Button {
            objectName: 'addButton'
            source: '../../plus-button.png'
            visible: addButton
            enabled: addButtonEnabled
            onClicked: root.add()
            Layout.maximumHeight: buttonHeight
            Layout.maximumWidth: buttonHeight
        }
        PK.Button {
            objectName: 'addEventButton'
            source: '../../add-event-button.png'
            visible: addEventButton
            enabled: addEventButtonEnabled
            onClicked: root.addEvent()
            Layout.maximumHeight: buttonHeight
            Layout.maximumWidth: buttonHeight
        }
        PK.Button {
            objectName: 'addEmotionButton'
            source: '../../add-emotion-button.png'
            visible: addEmotionButton
            enabled: addEmotionButtonEnabled
            onClicked: root.addEmotion()
            Layout.maximumHeight: buttonHeight
            Layout.maximumWidth: buttonHeight
        }
        PK.Button {
            objectName: 'detailsButton'
            source: '../../details-button.png'
            visible: inspectButton
            enabled: inspectButtonEnabled
            Layout.maximumHeight: buttonHeight
            Layout.maximumWidth: buttonHeight
            onClicked: inspect()
        }
        PK.Button {
            objectName: 'duplicateButton'
            source: '../../duplicate-button.png'
            visible: duplicateButton
            enabled: duplicateButtonEnabled
            Layout.maximumHeight: buttonHeight
            Layout.maximumWidth: buttonHeight
            onClicked: duplicate()
        }
        Rectangle { Layout.fillWidth: true }
        PK.CheckBox {
            text: 'Store positions'
            id: storePositionsCheckBox
            objectName: root.objectName + '_storePositionsCheckBox'
            visible: storePositionsBox
            enabled: storePositionsBoxEnabled
            checked: storePositions
            onCheckedChanged: storePositions = checked
        }
        PK.CheckBox {
            text: 'Exclusive'
            id: exclusiveCheckBox
            objectName: root.objectName + '_exclusiveBox'
            visible: exclusiveBox
            enabled: exclusiveBoxEnabled
            checked: exclusiveChecked
            onCheckedChanged: exclusiveChecked = checked
        }
        PK.Button {
            objectName: 'searchButton'
            source: '../../search-button.png'
            visible: filterButton
            enabled: filterButtonEnabled
            Layout.maximumHeight: buttonHeight
            Layout.maximumWidth: buttonHeight
            onClicked: filter()
        }
        PK.Button {
            source: '../../delete-button.png'
            objectName: root.objectName + '_removeButton'
            visible: removeButton
            enabled: removeButtonEnabled
            Layout.maximumHeight: buttonHeight
            Layout.maximumWidth: buttonHeight
            onClicked: remove()
        }        
        PK.ToolButton {
            objectName: 'doneButton'
            text: 'Done'
            visible: doneButton
            enabled: doneButtonEnabled
            Layout.maximumHeight: buttonHeight
            onClicked: done()
        }
    }
}
