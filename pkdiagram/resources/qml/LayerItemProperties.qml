import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import "./PK" 1.0 as PK
import PK.Models 1.0


PK.Drawer {
    
    id: root
    objectName: 'layerItemProps'

    property bool canInspect: false
    property int margin: util.QML_MARGINS
    property var layerItemModel: LayerItemPropertiesModel {
        scene: sceneModel.scene
    }

    KeyNavigation.tab: parentBox
    focus: true // not sure why this one needs this and not the others

    header: PK.ToolBar {
        PK.Label {
            text: layerItemModel.items.length + ' Layer Items'
            anchors.centerIn: parent
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            width: (root.width - 2) - (root.width - doneButton.x) - root.margin * 2
            font.family: util.FONT_FAMILY_TITLE
            font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
            dropShadow: true
        }
        PK.ToolButton {
            id: doneButton
            text: "Done"
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: done()
        }
    }

    function setCurrentTab(tab) { }

    /* footer: PK.TabBar { */
    /*     id: tabBar */
    /*     currentIndex: stack.currentIndex */
    /*     PK.TabButton { text: "Layer Item" } */
    /*     onCurrentIndexChanged: stack.currentIndex = currentIndex */
    /* } */
    
    background: Rectangle {
        anchors.fill: parent
        color: util.QML_WINDOW_BG
    }

    StackLayout {

        id: stack
        currentIndex: 0 // tabBar.currentIndex
        anchors.fill: parent

        Flickable {
            id: layerItemPage
            contentWidth: width
            contentHeight: layerItemPageInner.childrenRect.height

            ColumnLayout {

                id: layerItemPageInner
                anchors.fill: parent
                anchors.margins: margin
                
                PK.Text {
                    text: "Parent"
                    Layout.leftMargin: 7
                    Layout.bottomMargin: 4
                }

                RowLayout {
                    Layout.fillWidth: true
                    PK.ComboBox {
                        id: parentBox
                        model: peopleModel
                        textRole: 'name'
                        currentIndex: {
                            model.resetter
                            model.rowForId(layerItemModel.parentId)
                        }
                        Layout.fillWidth: true
                        Layout.maximumWidth: 200
                        KeyNavigation.tab: resetParentButton
                        onCurrentIndexChanged: {
                            if(currentIndex > -1) {
                                layerItemModel.parentId = model.idForRow(currentIndex)
                            }
                        }
                    }
                    PK.Button {
                        id: resetParentButton
                        text: 'Reset'
                        objectName: 'resetParentButton'
                        opacity: parentBox.currentIndex > -1 ? 1 : 0
                        enabled: opacity > 0
                        KeyNavigation.tab: parentBox
                        onClicked: layerItemModel.parentId = undefined
                        Behavior on opacity {
                            NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
                        }
                    }
                }

                PK.Text {
                    text: "Color"
                    Layout.topMargin: margin / 2
                    Layout.leftMargin: 7
                    Layout.bottomMargin: 4
                }

                RowLayout {
                    Layout.fillWidth: true
                    PK.ColorPicker {
                        id: colorBox
                        objectName: 'colorBox'
                        color: layerItemModel.color != undefined ? layerItemModel.color : 'transparent'
                        onCurrentIndexChanged: layerItemModel.color = model[currentIndex]
                    }
                }

                PK.Text {
                    text: "Diagram Views"
                    Layout.topMargin: margin / 2
                    Layout.leftMargin: 7
                    Layout.bottomMargin: 4
                }

                PK.ItemLayerList {
                    id: layersView
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    Layout.minimumHeight: 300
                    model: LayerItemLayersModel {
                        scene: sceneModel.scene
                        items: layerItemModel.items
                    }
                }

                ListView {
                    clip: true
                    contentWidth: width
                    model: root.model
                    delegate: Rectangle {
                        property bool selected: false
                        property bool current: false
                        property bool alternate: index % 2 == 1
                        width: layersView.width
                        height: util.QML_ITEM_HEIGHT
                        color: util.itemBgColor(selected, current, alternate)
                        Row {
                            PK.CheckBox {
                                id: activeBox
                                textColor: util.textColor(selected, current, alternate)
                                checkState: active
                                onCheckStateChanged: active = checkState
                            }
                            PK.Text {
                                text: name
                                color: util.textColor(selected, current, alternate)
                                anchors.verticalCenter: parent.verticalCenter
                                Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: activeBox.checked = !activeBox.checked
                        }
                    }
                    Rectangle {
                        border {
                            width: 1
                            color: 'grey'
                        }
                        color: 'transparent'
                        anchors.fill: parent
                    }
                }
            }
        }
    }
}
