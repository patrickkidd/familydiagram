import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Controls 2.5 as QQC
import QtQuick.Layouts 1.15
import "./PK" 1.0 as PK
import PK.Models 1.0


PK.Drawer {
    id: root

    objectName: 'marriageProps'

    property int margin: util.QML_MARGINS
    property var focusResetter: marriagePageInner
    property bool isDrawerOpen: false
    property string itemTitle: {
        if(marriageModel.personAName && marriageModel.personBName) {
            "(Pair-Bond): %1 & %2".arg(marriageModel.personAName).arg(marriageModel.personBName)
        } else if(marriageModel.personAName && !marriageModel.personBName) {
            "(Pair-Bond): %1 & Unnamed".arg(marriageModel.personAName)
        } else if(!marriageModel.personAName && marriageModel.personBName) {
            "(Pair-Bond): Unnamed & %1".arg(marriageModel.personBName)
        } else {
            "(Pair-Bond): 2 Unnamed People"
        }
    }
    property var marriageModel: MarriagePropertiesModel {
        scene: sceneModel.scene
        objectName: 'marriageModel'
    }
    
    property bool canRemove: false
    property bool canInspect: false

    onCanRemoveChanged: sceneModel.selectionChanged()


    function setCurrentTab(tab) {
        var index = 0
        if(tab == 'item')
            index = 0
        else if(tab == 'notes')
            index = 1
        else if(tab == 'meta')
            index = 2
        tabBar.setCurrentIndex(index)
    }

    function currentTab() {
        return {
            0: 'item',
            1: 'notes',
            2: 'meta'
        }[tabBar.currentIndex]
    }    

    KeyNavigation.tab: marriedBox

    header: PK.ToolBar {
        PK.ToolButton {
            id: resizeButton
            text: root.expanded ? "Contract" : "Expand"
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: resize()
        }
        PK.Label {
            text: itemTitle
            objectName: 'itemTitle'
            anchors.centerIn: parent
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            width: (doneButton.x) - (resizeButton.x + resizeButton.width) - root.margin * 2
            font.family: util.FONT_FAMILY_TITLE
            font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
        }
        PK.ToolButton {
            id: doneButton
            text: "Done"
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: done()
        }
    }

    footer: PK.TabBar {
        id: tabBar
        objectName: 'tabBar'
        currentIndex: stack.currentIndex
        PK.TabButton { text: "Pair-Bond" }
        PK.TabButton { text: "Notes" }
//        PK.TabButton { text: "Meta" }
    }
    
    background: Rectangle {
        anchors.fill: parent
        color: util.QML_WINDOW_BG
    }

    StackLayout {

        id: stack
        objectName: 'stack'
        currentIndex: tabBar.currentIndex
        anchors.fill: parent
        enabled: !sceneModel.readOnly

        Flickable {
            id: marriagePage
            contentWidth: width
            contentHeight: marriagePageInner.childrenRect.height + root.margin * 2

            Rectangle {

                id: marriagePageInner
                anchors.fill: parent
                anchors.margins: margin
                color: 'transparent'

                MouseArea {
                    anchors.fill: parent
                    onClicked: parent.forceActiveFocus()
                }

                ColumnLayout { // necessary to expand DatePicker

                    width: parent.width

                    GridLayout {
                        id: mainGrid
                        columns: 2
                        columnSpacing: util.QML_MARGINS / 2

                        PK.GroupBox {

                            title: "Provisional Settings"
                            Layout.columnSpan: 2
                            Layout.bottomMargin: margin
                            Layout.fillWidth: true

                            ColumnLayout {
                                anchors.fill: parent

                                PK.CheckBox {
                                    id: marriedBox
                                    objectName: 'marriedBox'
                                    text: "Show Married"
                                    enabled: !marriageModel.anyMarriedEvents && !marriageModel.everDivorced
                                    checkState: marriageModel.married
                                    Layout.columnSpan: 2
                                    KeyNavigation.tab: separatedBox
                                    onCheckStateChanged: marriageModel.married = checkState
                                }

                                PK.CheckBox {
                                    id: separatedBox
                                    objectName: 'separatedBox'
                                    text: "Show Separated"
                                    enabled: !marriageModel.anySeparatedEvents && !marriageModel.everSeparated
                                    checkState: marriageModel.separated
                                    Layout.columnSpan: 2
                                    KeyNavigation.tab: divorcedBox
                                    onCheckStateChanged: marriageModel.separated = checkState                            
                                }

                                PK.CheckBox {
                                    id: divorcedBox
                                    objectName: 'divorcedBox'
                                    text: "Show Divorced"
                                    enabled: !marriageModel.anyDivorcedEvents
                                    checkState: marriageModel.divorced
                                    Layout.columnSpan: 2
                                    KeyNavigation.tab: custodyBox
                                    onCheckStateChanged: marriageModel.divorced = checkState
                                }

                                PK.Text {
                                    text: "These options show bonded, married, separated, and divorced status prior to adding bonded, married, separated, divorced events to the Pair-Bond. These options are unavailable as soon as at least one of the respective events are added to this pair-bond."
                                    font.pixelSize: util.HELP_FONT_SIZE
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                               }
                            }
                        }

                        Rectangle { width: 1; height: 1; color: 'transparent';  Layout.columnSpan: 2 }
                        
                        PK.Text { text: "Custody" }

                        RowLayout {
                            Layout.fillWidth: true

                            PK.ComboBox {
                                id: custodyBox
                                model: ListModel {}
                                textRole: 'name'
                                enabled: marriageModel.everSeparated || marriageModel.everDivorced
                                displayText: (marriageModel.custody != -1 && currentIndex != -1) ? currentText : (currentIndex != -1) ? 'Unnamed Person' : ''
                                Layout.fillWidth: true
                                KeyNavigation.tab: resetCustodyButton.enabled ? resetCustodyButton : diagramNotesEdit
                                function updateModel() {
                                    model.clear()
                                    model.append({
                                        name: marriageModel.personAName != '' ? marriageModel.personAName : 'Unnamed Person',
                                        personId: marriageModel.personAId
                                    })
                                    model.append({
                                        name: marriageModel.personBName != '' ? marriageModel.personBName : 'Unnamed Person',
                                        personId: marriageModel.personBId
                                    })
                                    updateCustody()
                                }
                                function updateCustody() {
                                    for(var i=0; i < custodyBox.model.count; i++) {
                                        if(custodyBox.model.get(i).personId == marriageModel.custody) {
                                            custodyBox.currentIndex = i;
                                            return;
                                        }
                                    }
                                    custodyBox.currentIndex = -1
                                }
                                Connections {
                                    target: marriageModel
                                    function onItemsChanged() { custodyBox.updateModel() }
                                    function onCustodyChanged() { custodyBox.updateCustody() }
                                }
                                onCurrentIndexChanged: {
                                    var entry = model.get(currentIndex)
                                    if(entry) {
                                        marriageModel.custody = entry.personId
                                    }
                                }
                            }
                            Button {
                                id: resetCustodyButton
                                text: 'Reset'
                                objectName: 'resetCustodyButton'
                                opacity: custodyBox.currentIndex > -1 ? 1 : 0
                                enabled: opacity > 0
                                KeyNavigation.tab: hideDetailsBox
                                onClicked: marriageModel.custody = undefined
                                Behavior on opacity {
                                    NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
                                }
                            }
                        }

                        Rectangle { width: 1; height: 1; color: 'transparent';  Layout.columnSpan: 2 }

                        // Spacer line

                        Rectangle {
                            height: 1
                            Layout.fillWidth: true
                            Layout.columnSpan: 2
                            Layout.topMargin: margin
                            Layout.bottomMargin: margin
                            color: util.QML_ITEM_BORDER_COLOR
                        }

                        ColumnLayout {
                            Layout.columnSpan: 2

                            PK.Label {
                                text: 'Diagram Notes'
                            }
                            
                            Rectangle { // for border
                                Layout.fillWidth: true
                                Layout.minimumHeight: 150
                                Layout.maximumHeight: 150
                                color: 'transparent'
                                border {
                                    width: 1
                                    color: util.QML_ITEM_BORDER_COLOR
                                }
                                PK.TextEdit {
                                    id: diagramNotesEdit
                                    objectName: 'diagramNotesEdit'
                                    text: marriageModel.diagramNotes
                                    // wrapMode: TextEdit.Wrap
                                    anchors.fill: parent
                                    padding: margin
                                    enabled: !sceneModel.readOnly
                                    KeyNavigation.tab: bigFontBox
                                    onTextChanged: marriageModel.diagramNotes = (text ? text : undefined)
                                }
                            }
                        }

                        // Spacer line

                        Rectangle {
                            height: 1
                            Layout.fillWidth: true
                            Layout.columnSpan: 2
                            Layout.topMargin: margin
                            Layout.bottomMargin: margin
                            color: util.QML_ITEM_BORDER_COLOR
                        }

                        Row {
                        
                            Layout.fillWidth: true
                            Layout.columnSpan: 2
                            
                            PK.CheckBox {
                                id: bigFontBox
                                objectName: 'bigFontBox'
                                text: "Big Font"
                                KeyNavigation.tab: hideDetailsBox
                                checkState: marriageModel.bigFont
                                onCheckStateChanged: marriageModel.bigFont = checkState
                            }

                        }

                        Row {

                            Layout.fillWidth: true
                            Layout.columnSpan: 2                            
                            
                            PK.CheckBox {
                                id: hideDetailsBox
                                objectName: 'hideDetailsBox'
                                text: "Hide Details"
                                KeyNavigation.tab: marriedBox
                                KeyNavigation.backtab: bigFontBox
                                checkState: marriageModel.hideDetails
                                onCheckStateChanged: marriageModel.hideDetails = checkState
                            }

                            PK.CheckBox {
                                id: hideDatesBox
                                objectName: 'hideDatesBox'
                                text: "Hide Dates"
                                KeyNavigation.tab: marriedBox
                                KeyNavigation.backtab: bigFontBox
                                checkState: marriageModel.hideDates
                                onCheckStateChanged: marriageModel.hideDates = checkState
                            }

                        }
                    }
                }
            }            
        }

        Flickable {
            id: notesEditFlickable
            contentX: 0
            contentHeight: Math.max(notesEdit.paintedHeight + 50, height) // allow scrolling
            Layout.fillHeight: true
            Layout.fillWidth: true

            PK.TextEdit {
                id: notesEdit
                width: parent.width
                text: marriageModel.notes
                padding: margin
                wrapMode: TextEdit.Wrap
                enabled: !sceneModel.readOnly
                anchors.fill: parent
                onEditingFinished: marriageModel.notes = (text ? text : undefined)
            }
        }

        // Item {

        //     id: metaPage
        //     Layout.fillHeight: true
        //     Layout.fillWidth: true            
        //     Rectangle {
        //         anchors.fill: parent
        //         anchors.margins: margin
        //         color: 'transparent'
        //         ColumnLayout {
        //             anchors.fill: parent
        //             PK.GroupBox {
        //                 title: "Tags Added to this Pair-Bond"
        //                 Layout.fillWidth: true
        //                 Layout.fillHeight: true
        //                 padding: 1
        //                 ColumnLayout {
        //                     anchors.fill: parent
        //                     PK.TagsEdit {
        //                         id: tagsList
        //                         Layout.fillWidth: true
        //                         Layout.fillHeight: true
        //                         model: TagsModel {
        //                             searchModel: searchModel
        //                             scene: sceneModel.scene
        //                             items: marriageModel.items
        //                         }
        //                     }
        //                 }
        //             }
        //         }
        //     }
        // }
    }    
}
