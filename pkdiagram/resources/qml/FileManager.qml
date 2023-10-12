import QtQuick 2.12
import QtQuick.Controls 2.14
import QtQuick.Controls.Universal 2.12
import QtQuick.Layouts 1.12
import './PK' 1.0 as PK
import PK.Models 1.0
import 'js/Global.js' as Global


Rectangle {

    id: root

    signal localFileClicked(string path)
    signal serverFileClicked(string path)
    signal newButtonClicked

    property int margin: util.QML_MARGINS
    property int cbMinWidth: 160
    property var session: Session {}
    property bool adminMode: session.isAdmin
    property var localFileModel: LocalFileManagerModel {
        searchText: localSearchBar.text
    }
    property var serverFileModel: ServerFileManagerModel {
        searchText: serverSearchBar.text
    }
    property bool localFilesShown: stack.currentIndex == 0
    property bool canShowServer: session.hash && session.hasFeature(vedana.LICENSE_PROFESSIONAL) && util.ENABLE_SERVER_VIEW

    // onAdminModeChanged: print('onAdminModeChanged:', adminMode)

    Universal.theme: Universal.Light

    function clearSelection() {
        localFileList.currentIndex = -1
        serverFileList.currentIndex = -1
    }

    function showLocalFiles(on) {
        if(on) {
            tabBar.currentIndex = 0
        } else {
            tabBar.currentIndex = 1
        }
    }

    PropertyAnimation { // just adds a little flicker distraction localFileList.initScroll() to work
        property: 'opacity'
        id: initOpacity
        target: stack
        from: 0
        to: 1
        duration: 0
    }
    color: util.QML_WINDOW_BG

    StackLayout {
        id: stack
        height: root.height - tabBar.height
        width: root.width
        currentIndex: tabBar.currentIndex
        opacity: 0

        Rectangle {
            id: localView
            visible: false
            color: util.QML_WINDOW_BG
            
            Rectangle {
                height: localSearchBar.height
                Layout.fillWidth: true
            }

            PK.FDListView {
                id: localFileList
                objectName: 'localFileList'
                anchors.fill: parent
                model: localFileModel
                property var localToolBar: null
                adminMode: root.adminMode

                Timer { // there has to be a better way..
                    interval: 10
                    running: true
                    onTriggered: {
                        localFileList.initScroll()
                        running = false
                    }
                }
                function initScroll() {
                    // scroll a little to initially hide the tool bar
                    // assumes `margin` in PK.ToolBar
                    if(model.rowCount() > 0) {
                        contentY = -headerItem.height + localToolBar.height // + margin
                    } else {
                        contentY = -headerItem.height // + margin
                    }
                    initOpacity.running = true
                }
                onContentYChanged: function() {
                    var itemHeight = localFileList.itemHeight
                    var titleY = 0;
                    if(contentY > -itemHeight) {
                        titleY = -itemHeight - contentY
                    } else {
                        titleY = 0
                    }
                    localTitleText.y = titleY;
                    //
                    titleY += itemHeight
                    var searchY = localTitleText.y + localTitleText.height
                    localSearchBar.y = Math.max(0, searchY)
                }

                onFinishedEditingTitle: function() {
                    editMode = false
                }

                header: ColumnLayout {
                    spacing: 0
                    width: parent.width

                    Rectangle { // spacer for search bar, tool bar
                        color: util.QML_WINDOW_BG
                        height: localTitleText.height + localSearchBar.height
                        width: parent.width
                    }

                    PK.ToolBar {
                        id: localToolBar
                        Layout.fillWidth: true
                        // Layout.topMargin: margin // assumed in initScroll()
                        
                        Component.onCompleted: localFileList.localToolBar = this

                        Rectangle {
                            anchors.fill: parent
                            anchors.leftMargin: margin / 2
                            anchors.rightMargin: margin
                            anchors.bottomMargin: 1 // don't overlap PK.ToolBar border
                            color: util.QML_HEADER_BG
                            RowLayout {
                                width: parent.width
                                height: 40
                                anchors.fill: parent
                                
                                PK.Button {
                                    id: newButton
                                    source: '../../plus-button.png'
                                    enabled: !localFileList.editMode
                                    Layout.maximumHeight: margin
                                    Layout.maximumWidth: margin
                                    onClicked: newButtonClicked()
                                }
                                Rectangle { Layout.fillWidth: true }
                                Switch {
                                    id: localSortSwitch
                                    text: 'Sort by date'
                                    checked: localFileModel.sortBy == 'modified'
                                    onToggled: {
                                        localFileModel.sortBy = checked ? 'modified' : 'name'
                                    }
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    palette.dark: util.QML_SELECTION_COLOR
                                    palette.midlight: util.QML_CONTROL_BG
                                    palette.windowText: util.QML_ACTIVE_TEXT_COLOR
                                }
                                Rectangle { Layout.fillWidth: true }
                                PK.ToolButton {
                                    text: localFileList.editMode /* localEditMode */ ? "Done" : "Edit"
                                    onClicked: localFileList.editMode = !localFileList.editMode
                                    Layout.maximumWidth: 50
                                    Layout.maximumHeight: parent.height - 1 // don't overlap PK.ToolBar bottom border
                                    Layout.rightMargin: localFileList.margins
                                }
                            }
                        }

                    }
                    
                }
                onSelected: function(path) {
                    localFileClicked(path)
                }
                
            }

            Rectangle {
                id: localTitleText
                width: parent.width
                height: localFileList.itemHeight + localSearchBar.margin
                color: util.QML_WINDOW_BG
                clip: true
                PK.Text {
                    text: 'Family Diagram'
                    font.family: util.FONT_FAMILY_TITLE
                    font.pixelSize: localFileList.itemHeight * .85
                    anchors.fill: parent
                    anchors.leftMargin: margin
                    verticalAlignment: Text.AlignBottom
                }
            }

            PK.SearchBar {
                id: localSearchBar
                objectName: 'localSearchBar'
                y: localFileList.itemHeight
                width: parent.width
            }

        }

        Rectangle {
            id: serverView
            color: util.QML_WINDOW_BG

            visible: util.ENABLE_SERVER_VIEW
            
            Rectangle {
                height: serverSearchBar.height;
                Layout.fillWidth: true
            } // spacer for titleText
            
            PK.FDListView {
                id: serverFileList
                objectName: 'serverFileList'
                anchors.fill: parent
                model: serverFileModel
                isServer: true
                // property var serverToolBar: null // delayed scroll init
                adminMode: root.adminMode
                header: ColumnLayout {

                    spacing: 0
                    width: parent.width

                    // // delayed scroll init
                    // Component.onCompleted: {
                    //     serverFileList.serverToolBar = serverToolBar
                    //     serverFileList.initScroll()
                    // }

                    Rectangle { // spacer for search bar, tool bar
                        color: util.QML_WINDOW_BG
                        height: serverTitleText.height + serverSearchBar.height
                        width: parent.width
                    }

                    PK.ToolBar {
                        id: serverToolBar
                        Layout.fillWidth: true
                        //Layout.topMargin: margin // assumed in initScroll
                        
                        Rectangle {
                            color: util.QML_HEADER_BG
                            anchors.fill: parent
                            anchors.leftMargin: margin
                            anchors.rightMargin: margin
                            anchors.bottomMargin: 1 // don't overlap PK.ToolBar border
                            RowLayout {
                                width: parent.width
                                height: 40
                                anchors.fill: parent
                                
                                Rectangle { Layout.fillWidth: true }
                                Switch {
                                    id: serverSortSwitch
                                    text: 'Sort by date'
                                    checked: serverFileModel.sortBy == 'modified'
                                    onToggled: {
                                        serverFileModel.sortBy = checked ? 'modified' : 'name'
                                    }
                                    font.pixelSize: util.TEXT_FONT_SIZE
                                    palette.dark: util.QML_SELECTION_COLOR
                                    palette.midlight: util.QML_CONTROL_BG
                                    palette.windowText: util.QML_ACTIVE_TEXT_COLOR
                                }
                                // Rectangle { Layout.fillWidth: true }
                                // PK.TextField {
                                //     id: serverSearchTextEdit
                                //     objectName: 'serverSearchTextEdit'
                                //     text: serverFileModel.searchText
                                //     placeholderText: 'Search'
                                //     onTextChanged: serverFileModel.searchText = text
                                // }
                                Rectangle { Layout.fillWidth: true }
                                PK.ToolButton {
                                    text: serverFileList.editMode /* serverEditMode */ ? "Done" : "Edit"
                                    visible: root.adminMode
                                    onClicked: serverFileList.editMode = !serverFileList.editMode
                                    // palette.button: 'white'
                                    Layout.maximumWidth: 50
                                    Layout.maximumHeight: parent.height - 1 // don't overlap PK.ToolBar bottom border
                                    Layout.rightMargin: serverFileList.margins
                                }
                            }
                        }
                    }
                }
                
                onSelected: function(path) {
                    serverFileClicked(path)
                }

                // // delayed scroll init
                // property bool bScrollInit: false
                // function initScroll() {
                //     if(!bScrollInit) {
                //         bScrollInit = true
                //         print('initScroll()', headerItem, serverToolBar)
                //         // assumes Layout.topMargin in PK.ToolBar
                //         contentY = -headerItem.height + serverToolBar.height // + margin
                //     }
                // }

                // onVisibleChanged: {
                //     if(visible) {
                //         initScroll()
                //     }
                // }
                // scroll behavior
                onContentYChanged: function() { // (on scroll)
                    var itemHeight = serverFileList.itemHeight
                    var titleY = 0;
                    if(contentY > -itemHeight) {
                        titleY = -itemHeight - contentY
                    } else {
                        titleY = 0
                    }
                    serverTitleText.y = titleY;
                    
                    titleY += itemHeight
                    var searchY = serverTitleText.y + serverTitleText.height
                    serverSearchBar.y = Math.max(0, searchY)
                }
            }
            
            Rectangle {
                id: serverTitleText
                width: parent.width
                height: serverFileList.itemHeight + serverSearchBar.margin
                color: util.QML_WINDOW_BG
                clip: true
                PK.Text {
                    text: 'Family Diagram Server'
                    font.family: util.FONT_FAMILY_TITLE
                    font.pixelSize: serverFileList.itemHeight * .85
                    anchors.fill: parent
                    anchors.leftMargin: margin
                    verticalAlignment: Text.AlignBottom
                }
            }

            PK.SearchBar {
                id: serverSearchBar
                objectName: 'serverSearchBar'
                y: serverFileList.itemHeight
                width: parent.width
            }            
        }
    }
    
    PK.TabBar {
        objectName: 'tabBar'
        id: tabBar
        y: root.height - height
        height: root.canShowServer ? implicitHeight : 0
        width: root.width
        visible: root.canShowServer

        TabButton {
            objectName: 'localViewButton'
            icon.source: '../presentation-mode.png'
        }
        TabButton {
            objectName: 'serverViewButton'
            icon.source: '../cloud.png'
        }
    }

}
