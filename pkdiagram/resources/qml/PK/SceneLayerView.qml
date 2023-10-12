import QtQuick 2.12
import QtQuick.Layouts 1.12
import QtQuick.Controls 2.12
import "." 1.0 as PK
import PK.Models 1.0


ColumnLayout {
    id: root

    spacing: 0

    property int cellPadding: 3
    property var model: SceneLayerModel {
        scene: sceneModel.scene
        items: sceneModel.scene ? [sceneModel.scene] : []
    }

    property int responsive1: width >= 500

    ListView {
        id: layerList
        model: root.model
        clip: true
        currentIndex: -1
        Layout.fillWidth: true
        Layout.fillHeight: true
        function onRowClicked(e, row) {
            if(e.modifiers & Qt.ControlModifier) {
                layerList.currentIndex = -1
            } else {
                layerList.currentIndex = row
            }
        }

        delegate: Rectangle {
            id: dRoot

            property bool selected: index == layerList.currentIndex
            property bool current: false
            property bool alternate: index % 2 == 1
            property int dIndex: index

            width: parent ? parent.width : 0
            height: rowLayout.height
            color: util.itemBgColor(selected, current, alternate)
            
            property int layerIndex: index // b/c just `index` to model.layerForRow was getting hijacked to zero.
            clip: true

            // drag and drop

            property int thisIndex: model.index
            property bool underDrag: false // when another item is being dragged over this one
            property bool dragging: dMouseArea.drag.active
            opacity: dragging ? .8 : 1
            z: dragging ? 2 : 1
            
            onDraggingChanged: {
                if(dragging) {
                    layerList.currentIndex = -1
                    layerList.interactive = false
                } else {
                    layerList.interactive = true
                }
            }
            
            Rectangle {
                id: dropIndicator
                anchors.fill: parent
                opacity: dRoot.underDrag ? 1.0 : 0
                Behavior on opacity {
                    NumberAnimation { duration: 50 }
                }
                color: 'grey'
            }
            
            MouseArea {
                id: dMouseArea
                anchors.fill: parent
                onClicked: {
                    if(!dRoot.dragging) {
                        layerList.onRowClicked(mouse, index)
                    }
                }

                // drag and drop

                drag.axis: Drag.YAxis
                drag.target: dRoot
                property var lastDropTarget: null
                onPositionChanged: {
                    var globalPos = dMouseArea.mapToGlobal(mouseX, mouseY)
                    var delegates = layerList.contentItem.children
                    lastDropTarget = null
                    for(var i=0; i < delegates.length; i++) {
                        var delegate = delegates[i];
                        if(delegate.thisIndex !== undefined && delegate.thisIndex != dRoot.thisIndex) {
                            var localPos = delegate.mapFromGlobal(globalPos.x, globalPos.y)
                            if(delegate.contains(localPos) && lastDropTarget == null) {
                                delegate.underDrag = true
                                lastDropTarget = delegate
                            } else {
                                delegate.underDrag = false
                            }
                        }
                    }
                }
                onReleased: {
                    if(dRoot.dragging) {
                        if(lastDropTarget) {
                            // drop
                            var fromIndex = thisIndex
                            var toIndex = lastDropTarget.thisIndex
                            root.model.moveLayer(fromIndex, toIndex)
                            lastDropTarget.underDrag = false
                            lastDropTarget = null
                        } else {
                            // cancel drag
                            dRoot.x = 0
                            dRoot.y = dRoot.thisIndex * util.QML_ITEM_HEIGHT // hope this works
                            Drag.cancel()
                        }
                    }
                }
            }

            Component {
                id: divider
                Rectangle {
                    Layout.fillHeight: true
                    width: 1
                    implicitHeight: dRoot.height
                    color: 'transparent'
                    Rectangle {
                        y: root.cellPadding
                        width: 1
                        height: parent.height - (root.cellPadding * 2)
                        color: util.QML_ITEM_BORDER_COLOR
                    }
                }
            }

            RowLayout {
                id: rowLayout
                width: parent.width
                spacing: 6
                height: util.QML_ITEM_HEIGHT
                Behavior on height {
                    NumberAnimation { duration: util.ANIM_DURATION_MS }
                }

                Rectangle { width: 1; color: 'transparent' } // just trigger cell spacing
                    
                ColumnLayout {
                    width: 10
                    height: util.QML_ITEM_HEIGHT
                    spacing: 3
                    Rectangle { height: 1; width: parent.width; color: util.textColor(selected, current) }
                    Rectangle { height: 1; width: parent.width; color: util.textColor(selected, current) }
                    Rectangle { height: 1; width: parent.width; color: util.textColor(selected, current) }
                }

                PK.CheckBox {
                    id: activeBox
                    text: 'Active'
                    textColor: util.textColor(selected, current)
                    checkState: active
                    property bool blocked: false
                    onCheckStateChanged: {
                        if(blocked)
                            return
                        blocked = true
                        if(sceneModel.exclusiveLayerSelection && checkState != Qt.Unchecked) {
                            root.model.setActiveExclusively(dIndex)
                        } else {
                            active = checkState
                        }
                        blocked = false
                    }
                    Layout.minimumWidth: implicitWidth + util.QML_MARGINS
                }

                Loader { sourceComponent: divider }          

                PK.TextInput {
                    property bool editing: false

                    id: nameEdit
                    text: name
                    color: util.textColor(selected, current)
                    clip: true
                    readOnly: !editing
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignVCenter
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: responsive1 ? dRoot.width * .4: implicitWidth
                    leftPadding: cellPadding
                    rightPadding: cellPadding

                    Text {
                        id: storeGoemetryIndicator
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: '(x,y)'
                        visible: ! responsive1 && storeGeometry
                        color: util.QML_ACTIVE_TEXT_COLOR
                        font.pixelSize: 10
                        rightPadding: cellPadding * 2
                    }

                    onEditingFinished: {
                        name = text
                        cursorPosition = 0
                        editing = false
                    }
                    onTextChanged: {
                        if(!editing) {
                            cursorPosition = 0
                        }
                    }
                    onReadOnlyChanged: {
                        if(!readOnly && cursorPosition != 0) {
                            cursorPosition = 0
                        }
                    }
                    onCursorPositionChanged: {
                        if(!editing && cursorPosition != 0) {
                            cursorPosition = 0
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        // width: parent.contentWidth
                        // height: parent.contentHeight
                        enabled: nameEdit.readOnly
                        propagateComposedEvents: true

                        onDoubleClicked: {
                            nameEdit.editing = true
                            nameEdit.selectAll()
                            nameEdit.forceActiveFocus()
                        }
                    }
                }

                Loader {
                    sourceComponent: divider;
                    visible: responsive1
                    opacity: 1
                    Behavior on opacity {
                        NumberAnimation { duration: util.ANIM_DURATION_MS }
                    }
                }

                Rectangle {
                    id: storeGeometryCell

                    visible: responsive1
                    height: geoBox.height
                    Layout.minimumWidth: responsive1 ? geoBox.implicitWidth : 0
                    Layout.maximumWidth: responsive1 ? geoBox.implicitWidth + 1 : 0
                    color: 'transparent'

                    PK.CheckBox {
                        id: geoBox
                        text: 'Store Geometry'
                        textColor: util.textColor(selected, current)
                        checked: storeGeometry // avoid popping question box on init, because this is called before changed slot
                        onCheckedChanged: {
                            // This is a good example pattern for canceling a checkbox click
                            if(storeGeometry && !checked) {
                                var yes = util.questionBox('Are you sure?',
                                    'Are you sure you want to clear all item sizes and positions in this layer, returning them to match the default layer?'
                                )
                                if(!yes) {
                                    // This is what makes this pattern possible, otherwise binding is lost.
                                    checked = Qt.binding(function() { return storeGeometry })
                                    return
                                }
                            }
                            storeGeometry = checked
                        }
                    }
                }
            }
        }
    }

    Rectangle { // border-bottom
        color: util.QML_ITEM_BORDER_COLOR
        height: 1
        Layout.fillWidth: true
    }

    PK.CrudButtons {
        id: crudButtons
        Layout.fillWidth: true
        bottomBorder: false
        addButton: true
        removeButton: true
        duplicateButton: true
        addButtonEnabled: !sceneModel.readOnly
        removeButtonEnabled: !sceneModel.readOnly && layerList.currentIndex != -1
        duplicateButtonEnabled: !sceneModel.readOnly && layerList.currentIndex != -1
        onAdd: root.model.addRow()
        onDuplicate: root.model.duplicateRow(layerList.currentIndex)
        onRemove: root.model.removeRow(layerList.currentIndex)
        exclusiveBox: true
        exclusiveChecked: sceneModel.exclusiveLayerSelection
        onExclusiveCheckedChanged: sceneModel.exclusiveLayerSelection = exclusiveChecked
        Connections {
            target: sceneModel
            function onExclusiveLayerSelectionChanged() {
                crudButtons.exclusiveChecked = sceneModel.exclusiveLayerSelection
            }
        }
    }    
}
