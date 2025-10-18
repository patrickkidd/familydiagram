import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Controls 2.5 as QQC
import QtQuick.Layouts 1.15
import QtQuick.Window 2.2
import "./PK" 1.0 as PK
import PK.Models 1.0


PK.Drawer {
    
    id: root
    objectName: 'caseProps'

    signal addEvent
    signal hidden
    signal flashTimelineRow(int index)
    signal flashTimelineSelection(var selectionModel)
    signal eventPropertiesTemplateIndexChanged(int index)

    property int margin: util.QML_MARGINS
    property bool isDrawerOpen: false
    property bool canRemove: timelineView.canRemove
    property bool canInspect: timelineView.canInspect
    property bool notJustFreeLicense: {
        sceneModel.session ? (sceneModel.session.hash && sceneModel.session.hasFeature(
            vedana.LICENSE_CLIENT, vedana.LICENSE_PROFESSIONAL, vedana.LICENSE_ALPHA, vedana.LICENSE_BETA
        )) : false
    }

    property var variablesList: variablesList
    property var variablesCrudButtons: variablesCrudButtons
    property var timelineView: timelineView
    property var copilotView: copilotView

    onCanRemoveChanged: sceneModel.selectionChanged()

    function removeSelection() {
        timelineView.removeSelection()
    }

    function setCurrentTab(tab) {
        var index = 0
        if(tab == 'timeline')
            index = 0
        else if(tab == 'settings')
            index = 1
        else if(tab == 'copilot')
            index = 2
        tabBar.setCurrentIndex(index)
    }

    function currentTab() {
        return {
            0: 'timeline',
            1: 'settings',
            2: 'copilot'
        }[tabBar.currentIndex]
    }
    
    // function onInspect() {
    //     print('CaseProperties.onInspect(): canInspect =', canInspect, 'selectedEvents.length =', timelineView.selectedEvents.length)
    //     if(canInspect && timelineView.selectedEvents.length) {
    //         print('CaseProperties.onInspect(): inspecting', timelineView.selectedEvents.length, 'events')
    //         root.inspectEvents(timelineView.selectedEvents)
    //     }
    // }

    function onInspectNotes(row) {
        session.trackView('Edit event notes')
        eventProperties.eventModel.items = timelineView.selectedEvents
        eventProperties.setCurrentTab('notes')
        eventPropertiesDrawer.visible = true
    }

    function scrollSettingsToBottom() {
        // for testing
        settingsView.contentY = settingsView.contentHeight // - root.height - util.QML_MARGINS
    }

    function scrollTimelineToDateTime(dateTime) {
        timelineView.scrollToDateTime(dateTime, true)
    }
    
    header: PK.ToolBar {
        id: toolBar
        Layout.fillWidth: true
        PK.ToolButton {
            id: resizeButton
            text: root.expanded ? "Contract" : "Expand"
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: resize()
        }

        PK.Label {
            text: {
                if(tabBar.currentIndex == 0) {
                    return "Timeline"
                } else if(tabBar.currentIndex == 1) {
                    return "Settings"
                } else if(tabBar.currentIndex == 2) {
                    return "BT Copilot"
                }
            }
            elide: Text.ElideRight
            anchors.centerIn: parent
            font.family: util.FONT_FAMILY_TITLE
            font.pixelSize: util.QML_SMALL_TITLE_FONT_SIZE
            dropShadow: true
        }
        PK.ToolButton {
            id: doneButton
            text: "Done"
            objectName: 'doneButton'
            anchors.right: parent.right
            anchors.rightMargin: margin
            onClicked: done()
        }
    }

    footer: PK.TabBar {
        id: tabBar
        objectName: 'tabBar'
        currentIndex: stack.currentIndex
        Layout.fillWidth: true
        PK.TabButton { text: "Timeline" }
        PK.TabButton { text: "Settings" }
        PK.TabButton { text: "Copilot" }
        /* onCurrentIndexChanged: { */
        /*     hackTimer.running = false // cancel hack to avoid canceling out change from QmlDrawer.setCurrentTab() */
        /* } */
    }

    Rectangle {
        color: util.QML_WINDOW_BG
        anchors.fill: parent
    }

    StackLayout {
        id: stack
        objectName: 'stack'
        anchors.fill: parent
        currentIndex: tabBar.currentIndex
        // hack to avoid "implicitWidth must be greater than zero" warning when timeline is shown but not yet sized to parent QWidget
        /* Timer { */
        /*     id: hackTimer */
        /*     running: true; repeat: false; interval: 0 */
        /*     onTriggered: stack.currentIndex = 0 */
        /* } */

        PK.TimelineView {
            id: timelineView
            enabled: Qt.binding(function() { model.count > 0 })
            model: timelineModel
            showFilterButton: false
            Connections {
                target: timelineModel
                function onItemsChanged() { timelineView.clearSelection() }
            }
            margin: root.margin
            Layout.fillHeight: true
            Layout.fillWidth: true
            onSelectionChanged: {
                sceneModel.selectionChanged()
                root.flashTimelineSelection(timelineView.selectionModel)
            }
            onRowClicked: function(row) {
                root.flashTimelineRow(row)
            }
            onInspect: root.onInspect()
            onInspectNotes: root.onInspectNotes(row)
        }
        
        Flickable {

            id: settingsView
            objectName: 'settingsView'
            flickableDirection: Flickable.VerticalFlick
            contentWidth: width
            clip: true

            // Avoid binding loop on contentHeight
            Timer {
                interval: 10
                running: true
                repeat: false
                onTriggered: settingsView.hack_setContentHeight()
            }

            Connections {
                target: sceneModel
                function onIsInEditorModeChanged() { settingsView.hack_setContentHeight() }
            }

            function hack_setContentHeight() {
                settingsView.contentY = 0
                settingsView.contentHeight = settingsLayout.implicitHeight + root.margin * 2
            }

            Rectangle {
                color: util.QML_WINDOW_BG
                anchors.fill: parent
            }

            ColumnLayout {
                id: settingsLayout
                y: margin
                x: margin
                width: parent.width - margin * 2
                
                PK.GroupBox {
                    title: 'Timeline Variables'
                    id: variablesBox
                    objectName: "variablesBox"
                    enabled: !sceneModel.readOnly
                    visible: sceneModel.isInEditorMode
                    Layout.fillWidth: true
                    padding: 1 // bring variables ListView flush with group box

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0
                        RowLayout {
                            spacing: 0
                            ListView {
                                id: variablesList
                                Layout.fillWidth: true
                                Layout.minimumWidth: 230
                                Layout.minimumHeight: 150
                                property bool readOnly: sceneModel.readOnly
                                currentIndex: -1
                                clip: true

                                // delegate items are added asynchronously
                                signal itemAddDone(Item item)
                                signal itemRemoveDone(Item item)

                                model: SceneVariablesModel {
                                    id: sceneVariablesModel
                                    scene: sceneModel.scene
                                    onSceneChanged: variablesList.currentIndex = -1
                                }
                                delegate: Item {
                                    id: dRoot
                                    property bool selected: variablesList.currentIndex == index
                                    property bool current: false
                                    property bool alternate: index % 2 == 1
                                    property var nameEdit: nameEdit

                                    width: variablesList.width
                                    height: util.QML_ITEM_HEIGHT
                                    property bool editMode: false

                                    Component.onCompleted: variablesList.itemAddDone(dRoot)
                                    Component.onDestruction: variablesList.itemRemoveDone(dRoot)

                                    Rectangle { // background
                                        anchors.fill: parent
                                        color: util.itemBgColor(selected, current, alternate)
                                    }
                                    PK.TextInput {
                                        id: nameEdit
                                        color: util.textColor(selected, current)
                                        anchors.fill: parent
                                        verticalAlignment: TextInput.AlignVCenter
                                        readOnly: !dRoot.editMode
                                        text: display
                                        leftPadding: margin
                                        onEditingFinished: {
                                            display = text
                                            dRoot.editMode = false
                                        }
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: !dRoot.editMode
                                        onClicked: {
                                            if(mouse.modifiers & Qt.ControlModifier) {
                                                variablesList.currentIndex = -1
                                            } else {
                                                variablesList.currentIndex = index
                                            }
                                            
                                        }
                                        onDoubleClicked: {
                                            if(variablesList.readOnly)
                                                return
                                            editMode = true
                                            nameEdit.selectAll()
                                            nameEdit.forceActiveFocus()
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle { // border-bottom for variables ListView
                            color: util.QML_ITEM_BORDER_COLOR
                            height: 1
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            spacing: 0

                            PK.CrudButtons {
                                id: variablesCrudButtons
                                Layout.fillWidth: true
                                bottomBorder: true
                                addButton: true
                                addButtonEnabled: !sceneModel.readOnly
                                removeButton: true
                                removeButtonEnabled: variablesList.currentIndex > -1 && !sceneModel.readOnly
                                onAdd: sceneVariablesModel.addRow()
                                onRemove: {
                                    // workaround to possibly prevent QQuickTableView assertion when removing visible column
                                    timelineView.delayUpdates = true
                                    sceneModel.scene.removeEventPropertyByIndex(variablesList.currentIndex)
                                    timelineView.delayUpdates = false
                                    variablesList.currentIndex = -1
                                }
                            }

                            PK.ComboBox {
                                id: templateBox
                                Layout.minimumWidth: 180
                                currentIndex: -1
                                displayText: currentIndex == -1 ? 'Set from template' : model.get(currentIndex)
                                model: ['Havstad Model', 'Papero Model', "Stinson Model"]
                                onCurrentIndexChanged: {
                                    root.eventPropertiesTemplateIndexChanged(currentIndex)
                                    currentIndex = -1 // change back
                                    variablesList.currentIndex = -1
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.margins: viewSettingsBox.padding

                            PK.CheckBox {
                                id: hideVariablesOnDiagramBox
                                text: "Hide Variables on Diagram"
                                enabled: !sceneModel.readOnly
                                checked: sceneModel.hideVariablesOnDiagram
                                Layout.fillWidth: true
                                onCheckedChanged: sceneModel.hideVariablesOnDiagram = checked
                            }

                            PK.HelpText {
                                text: "This prevents variable values from being shown on the diagram. This can clean up the diagram for presentation purposes.";
                                Layout.fillWidth: true
                            }

                            PK.CheckBox {
                                text: "Hide Variable Steady States"
                                enabled: !sceneModel.readOnly && !hideVariablesOnDiagramBox.checked
                                checked: sceneModel.hideVariableSteadyStates
                                Layout.fillWidth: true
                                onCheckedChanged: sceneModel.hideVariableSteadyStates = checked
                            }
                            PK.HelpText {
                                text: "This makes it so variable values are only shown when the diagram shows the exact date that a variable shift occured. For example, if a variable has the value `up` on 1/1/1970, and `down` on 1/1/1980, then be no value shown on the diagram for 1/1/1972." ;
                                enabled: !sceneModel.readOnly && !hideVariablesOnDiagramBox.checked
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
                
                PK.GroupBox {
                    id: viewSettingsBox
                    objectName: 'viewSettingsBox'
                    title: 'View'
                    Layout.fillWidth: true
                    Layout.topMargin: sceneModel.isInEditorMode ? margin: 0

                    ColumnLayout {
                        anchors.fill: parent                        
                        PK.CheckBox {
                            text: "Hide Names"
                            enabled: !sceneModel.readOnly || sceneModel.useRealNames
                            checked: sceneModel.showAliases
                            Layout.fillWidth: true
                            onCheckedChanged: sceneModel.trySetShowAliases(checked)
                        }
                        PK.HelpText {
                            text: "This ensures anonymity for presentations. <b>NOTE:</b> Event descriptions and notes are not hidden and may reveal names if you have entered them into those fields." ;
                            Layout.fillWidth: true
                        }

                        PK.CheckBox {
                            text: "Hide Relationships"
                            checked: sceneModel.hideEmotionalProcess
                            Layout.fillWidth: true
                            onCheckedChanged: sceneModel.hideEmotionalProcess = checked
                        }
                        PK.HelpText {
                            text: "This is useful when you want to focus on geoneological data and not emotional process."
                            Layout.fillWidth: true
                        }

                        PK.CheckBox {
                            text: "Hide Relationship Colors"
                            checked: sceneModel.hideEmotionColors
                            Layout.fillWidth: true
                            onCheckedChanged: sceneModel.hideEmotionColors = checked
                        }
                        PK.HelpText {
                            text: "Check this to show all emotional process symbols in black instead of their own color."
                            Layout.fillWidth: true
                        }

                        PK.CheckBox {
                            text: "Hide tool bars"
                            checked: sceneModel.hideToolBars
                            Layout.fillWidth: true
                            onCheckedChanged: sceneModel.hideToolBars = checked
                        }
                        PK.HelpText {
                            text: "Don't show toolbars for use in presentations."
                            Layout.fillWidth: true
                        }
                    }
                }

                PK.GroupBox {
                    id: serverBox
                    objectName: 'serverBox'
                    title: {
                        if(sceneModel.isOnServer) {
                            if(enabled) {
                                'Server Settings for Diagram'
                            } else {
                                'Server Settings (Client or Pro license required)'
                            }
                        } else {
                            'Upload Diagram to Server'
                        }
                    }
                    enabled: root.notJustFreeLicense && util.ENABLE_SERVER_VIEW
                    Layout.fillWidth: true
                    Layout.topMargin: margin
                    padding: 1 // bring variables ListView flush with group box
                    // enabled: shouldShow // false when obscured so not usable in tests
                    property bool showAccessRightsBox: sceneModel.isOnServer && ! sceneModel.readOnly && sceneModel.isMyDiagram
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: util.QML_MARGINS

                        PK.HelpText {
                            visible: sceneModel.isOnServer
                            enabled: accessRightsBox.enabled
                            property string header: "This diagram is stored securely on the server. ";
                            text: {
                                if(sceneModel.readOnly)
                                    header + "It is owned by " + accessRightsModel.owner + "\n\nYou have been granted read-only access by the owner. You have access to all of the data, but cannot save your changes and cannot make a copy of this diagram."
                                else if(sceneModel.isMyDiagram)
                                    header + "You own it.";
                                else
                                    header + "It is owned by " + accessRightsModel.owner + "\n\nYou are able to save changes to it, but only the owner can who can view and save changes to it."
                            }
                            Layout.fillWidth: true
                            padding: util.QML_MARGINS / 2
                        }

                        RowLayout {
                            spacing: 0
                            visible: serverBox.showAccessRightsBox
                            ListView {
                                id: accessRightsBox
                                objectName: 'accessRightsBox'
                                Layout.fillWidth: true
                                Layout.minimumWidth: 230
                                Layout.minimumHeight: 150

                                enabled: sceneModel.isOnServer && root.notJustFreeLicense && util.ENABLE_SERVER_VIEW
                                // onEnabledChanged: print('serverAccessRightsBox.onEnabledChanged()[' + enabled + ']:', 'isOnServer:', sceneModel.isOnServer, 'notJustFreeLicense:', root.notJustFreeLicense)
                                currentIndex: -1
                                clip: true
                                model: accessRightsModel

                                property var accessRightItems: { // for testing
                                    var ret = []
                                    for(var i=0; i < contentItem.children.length; i++) {
                                        var child = contentItem.children[i]
                                        if(child.accessRightIndex !== undefined) {
                                            ret.push(child)
                                        }
                                    }
                                    return ret
                                }

                                delegate: Item {

                                    id: dRoot
                                    property bool selected: accessRightsBox.currentIndex == index
                                    property bool current: false
                                    property bool alternate: index % 2 == 1
                                    property int accessRightIndex: index
                                    width: accessRightsBox.width
                                    height: rightBox.height // util.QML_ITEM_HEIGHT

                                    Rectangle { // background
                                        anchors.fill: parent
                                        color: util.itemBgColor(selected, current, alternate)
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: {
                                            if(mouse.modifiers & Qt.ControlModifier) {
                                                accessRightsBox.currentIndex = -1
                                            } else {
                                                accessRightsBox.currentIndex = index
                                            }
                                            
                                        }
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        spacing: 0

                                        PK.Text {
                                            text: username
                                            objectName: 'userBox'
                                            Layout.leftMargin: util.QML_MARGINS / 2
                                        }

                                        PK.ComboBox {
                                            id: rightBox
                                            objectName: 'rightBox'
                                            model: ['Read Only', 'Read+Write']
                                            // Layout.rightMargin: -(util.QML_MARGINS * 2) // no idea
                                            Layout.alignment: Qt.AlignRight
                                            currentIndex: {
                                                if(rightCode == undefined) {
                                                    return -1
                                                } else if (rightCode == vedana.ACCESS_READ_ONLY) {
                                                    return 0
                                                } else if (rightCode == vedana.ACCESS_READ_WRITE) {
                                                    return 1
                                                }
                                            }
                                            onCurrentIndexChanged: {
                                                if(currentIndex == -1) {
                                                    rightCode = undefined
                                                } else if(currentIndex == 0) {
                                                    rightCode = vedana.ACCESS_READ_ONLY
                                                } else if(currentIndex == 1) {
                                                    rightCode = vedana.ACCESS_READ_WRITE
                                                }
                                            }
                                        }
                                    }

                                }
                            }
                        }

                        RowLayout {
                            // enabled: accessRightsBox.enabled
                            visible: serverBox.showAccessRightsBox
                            spacing: 0

                            PK.CrudButtons {
                                objectName: 'accessRightsCrudButtons'
                                Layout.fillWidth: true
                                bottomBorder: true
                                addButton: true
                                addButtonEnabled: addAccessRightBox.isValidUsername && !sceneModel.readOnly
                                removeButton: true
                                removeButtonEnabled: accessRightsBox.currentIndex > -1 && !sceneModel.readOnly
                                onAdd: addAccessRightBox.addAccessRight()
                                onRemove: {
                                    accessRightsModel.deleteRight(accessRightsBox.currentIndex)
                                    accessRightsBox.currentIndex = -1
                                }
                            }

                            PK.TextField {
                                id: addAccessRightBox
                                objectName: 'addAccessRightBox'
                                placeholderText: 'some.user@somewhere.com'
                                Layout.minimumWidth: 180
                                property bool isValidUsername: accessRightsModel.findUser(text) !== undefined
                                property var greenColor: util.IS_UI_DARK_MODE ? '#801aa260' : '#8056d366'
                                property var redColor: util.IS_UI_DARK_MODE ? '#80ff0000' : '#80e8564e'
                                property var currentUser: accessRightsModel.findUser(text)
                                // onCurrentUserChanged: print(currentUser ? currentUser.username : currentUser)
                                palette.base: {
                                    if(text == '') {
                                        'transparent'
                                    } else if (currentUser) {
                                        greenColor
                                    } else {
                                        redColor
                                    }
                                }
                                validator: RegExpValidator { regExp:/\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*/ }
                                function addAccessRight() {
                                    if(text) {
                                        var success = accessRightsModel.addRight(text)
                                        if(success)
                                            text = ''
                                    }
                                }
                                Keys.onReturnPressed: addAccessRight()
                            }

                        }

                        PK.HelpText {
                            visible: serverBox.showAccessRightsBox
                            enabled: accessRightsBox.enabled
                            text: "Here you can set access rights for other users using their email. Each person you add can either have read-only access or write access. In either case, your diagram will appear in their own server view in the app and you will be listed as the diagram\'s owner.\n\nEnter the username of the account you want to share this diagram with, and hit enter or click the add button. The text input will turn from red to green when a matching user is found."
                            Layout.fillWidth: true
                            padding: util.QML_MARGINS / 2
                            topPadding: 0
                        }

                        RowLayout {
                            id: uploadBox
                            objectName: 'uploadBox'
                            visible: !sceneModel.isOnServer
                            // enabled: !sceneModel.isOnServer
                            spacing: 0
                            Rectangle {
                                color: 'transparent'
                                Layout.fillWidth: true
                            }
                            PK.Button {
                                id: uploadButton
                                objectName: 'uploadButton'
                                text: 'Upload to Server'
                                Layout.fillWidth: true
                                Layout.margins: util.QML_MARGINS / 2
                                Layout.bottomMargin: 0
                                onClicked: sceneModel.onUploadToServer()
                            }
                        }

                        PK.HelpText {
                            visible: uploadBox.visible
                            // enabled: uploadBox.enabled
                            text: 'Click upload if you want to copy this diagram to the server so that you can share it with others. You will have an option to keep the copy on your local computer if you wish.'
                            Layout.fillWidth: true
                            padding: util.QML_MARGINS / 2
                            topPadding: 0
                        }
                    }
                }

                PK.GroupBox {
                    title: 'Research'
                    Layout.fillWidth: true
                    Layout.topMargin: margin
                    visible: false // util.ENABLE_SERVER_VIEW
                    ColumnLayout {
                        id: columnLayout
                        anchors.fill: parent

                        PK.CheckBox {
                            id: contributeBox
                            text: "Contribute this project to research."
                            enabled: !sceneModel.readOnly
                            checked: sceneModel.contributeToResearch
                            Layout.fillWidth: true
                            onCheckedChanged: sceneModel.contributeToResearch = checked
                        }

                        RowLayout {
                            PK.Text { text: "Server Alias:" }
                            PK.Text { id: aliasText; text: "[%1]".arg(sceneModel.alias) ; wrapMode: Text.WordWrap }
                            Layout.fillWidth: true
                        }

                        PK.HelpText {
                            text: "If this option is checked then an anonymized copy of this diagram will be maintained on the research server. All names will be replaced with aliases and notes will be excluded unless \"Use real names for research\" is checked below. It will be accessible on the server using the alias above."
                            Layout.fillWidth: true
                        }

                        PK.CheckBox {
                            text: "Use real names for research."
                            enabled: contributeBox.checked && !sceneModel.readOnly
                            checked: sceneModel.useRealNames
                            Layout.fillWidth: true
                            onCheckedChanged: sceneModel.useRealNames = checked
                        }

                        PK.HelpText {
                            enabled: contributeBox.checked
                            text: "Family identities are protected by default on diagrams that are contributed to family systems research. However, it makes sense to use real names when the family has consented to their release, or when using data that is publically availble as in the case of celebrities or political figures."
                            Layout.fillWidth: true
                        }

                        PK.CheckBox {
                            id: passwordBox
                            text: "Require password to view real names."
                            enabled: contributeBox.checked && sceneModel.useRealNames &&!sceneModel.readOnly
                            checked: sceneModel.requirePasswordForRealNames
                            onCheckedChanged: sceneModel.requirePasswordForRealNames = checked
                            Layout.fillWidth: true
                        }
                        RowLayout {
                            id: passwordEditor
                            enabled: contributeBox.checked && passwordBox.checked && sceneModel.requirePasswordForRealNames && !sceneModel.readOnly
                            Layout.fillWidth: true
                            Button {
                                id: resetPasswordButton
                                text: "Reset"
                                onClicked: sceneModel.password = util.newPassword()
                            }
                            PK.TextEdit {
                                id: passwordText
                                text: "PASSWORD: %1".arg(sceneModel.password)
                                readOnly: true
                                selectByMouse: true
                            }
                        }

                        PK.HelpText {
                            text: "If checked, this will allow only people with this password to view the real names stored in this case. This can be useful when using the server to share sensitive case data with others. The server administrators will also not be able to see identifying information unless you provide them with the password."
                            enabled: contributeBox.checked && passwordBox.checked && sceneModel.useRealNames
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        CopilotView {
            id: copilotView
        }
    }
}

