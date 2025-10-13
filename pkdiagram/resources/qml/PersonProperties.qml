import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Controls 2.5 as QQC
import QtQuick.Layouts 1.15
import QtQuick.Window 2.2
import "./PK" 1.0 as PK
import PK.Models 1.0


PK.Drawer {
    
    id: root

    signal toggleExpand
    signal editBirthEvent
    signal editDeathEvent

    property bool isDrawerOpen: false
    property var resetItemPosButton: resetItemPosButton

    property int margin: util.QML_MARGINS
    property var focusResetter: personPageInner
    property int numPeople: personModel.items.length
    property string itemTitle: {
        if(numPeople == 1) {
            if(personModel.fullNameOrAlias) {
                personModel.fullNameOrAlias
            } else {
                'Unnamed Person'
            }
        } else {
            numPeople + ' People'
        }
    }
    property var personModel: PersonPropertiesModel {
        scene: sceneModel.scene
    }

    property bool isReadOnly: (sceneModel && sceneModel.readOnly) ? true : false
    property bool canRemove: false
    property bool canInspect: false

    property var personPage: personPage
    property var firstNameEdit: firstNameEdit
    property var middleNameEdit: middleNameEdit
    property var lastNameEdit: lastNameEdit
    property var nickNameEdit: nickNameEdit
    property var birthNameEdit: birthNameEdit
    property var adoptedBox: adoptedBox
    property var deceasedBox: deceasedBox
    property var notesEdit: notesEdit
    property var deemphasizeBox: deemphasizeBox
    property var resetDeemphasizeButton: resetDeemphasizeButton
    property var resetColorButton: resetColorButton
    property var colorBox: colorBox
    property var sizeBox: sizeBox
    property var kindBox: kindBox
    property var ageBox: ageBox
    property var primaryBox: primaryBox
    property var hideDetailsBox: hideDetailsBox
    property var hideDatesBox: hideDatesBox
    property var hideVariablesBox: hideVariablesBox
    property var diagramNotesEdit: diagramNotesEdit
    property var layerList: layerList

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
    
    header: PK.ToolBar {
        PK.ToolButton {
            id: resizeButton
            text: root.expanded ? "Contract" : "Expand"
            anchors.left: parent.left
            anchors.leftMargin: margin
            onClicked: resize()
        }
        PK.Label {
            id: titleBar
            text: itemTitle
            elide: Text.ElideRight
            anchors.centerIn: parent
            horizontalAlignment: Text.AlignHCenter
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
        currentIndex: stack.currentIndex
        PK.TabButton { text: "Person" }
        PK.TabButton { text: "Notes" }
        PK.TabButton { text: "Views" }
    }

    background: Rectangle {
        anchors.fill: parent
        color: util.QML_WINDOW_BG
    }

    KeyNavigation.tab: firstNameEdit
    
    StackLayout {

        id: stack
        currentIndex: tabBar.currentIndex
        anchors.fill: parent

        Flickable {
            id: personPage
            contentWidth: width
            contentHeight: personPageInner.childrenRect.height + 50
        
            Rectangle {

                id: personPageInner
                anchors.fill: parent
                anchors.margins: margin
                color: 'transparent'

                MouseArea {
                    x: 0; y: 0
                    width: personPage.width
                    height: personPage.height
                    onClicked: parent.forceActiveFocus()
                }

                ColumnLayout { // necessary to expand DatePicker

                    GridLayout {
                        
                        
                        id: mainGrid
                        columns: 3
                        columnSpacing: util.QML_MARGINS / 2
                        
                        // First Name
                        
                        PK.Text {
                            id: firstNameLabel
                            text: qsTr("First Name")
                        }
                        
                        PK.TextField {
                            id: firstNameEdit
                            Layout.fillWidth: true
                            text: sceneModel.showAliases ? personModel.fullNameOrAlias : personModel.name
                            enabled: !root.isReadOnly && !sceneModel.showAliases
                            KeyNavigation.tab: middleNameEdit
                            onEditingFinished: personModel.name = (text ? text : undefined)
                        }

                        Rectangle { width: 1; height: 1; color: 'transparent' }

                        // Middle Name

                        PK.Text {
                            id: middleNameLabel
                            text: qsTr("Middle Name")
                        }

                        PK.TextField {
                            id: middleNameEdit
                            Layout.fillWidth: true
                            text: sceneModel.showAliases ? '' : personModel.middleName
                            enabled: !root.isReadOnly && !sceneModel.showAliases
                            KeyNavigation.tab: middleNameBox
                            onEditingFinished: personModel.middleName = (text ? text : undefined)
                        }

                        PK.CheckBox {
                            id: middleNameBox
                            checkState: personModel.showMiddleName
                            enabled: !root.isReadOnly
                            KeyNavigation.tab: lastNameEdit
                            onClicked: personModel.showMiddleName = checkState
                        }

                        // Last Name

                        PK.Text {
                            id: lastNameLabel
                            text: qsTr("Last Name")
                        }

                        PK.TextField {
                            id: lastNameEdit
                            Layout.fillWidth: true
                            text: sceneModel.showAliases ? '' : personModel.lastName
                            enabled: !root.isReadOnly && !sceneModel.showAliases
                            KeyNavigation.tab: lastNameBox
                            onEditingFinished: personModel.lastName = (text ? text : undefined)
                        }

                        PK.CheckBox {
                            id: lastNameBox
                            checkState: personModel.showLastName
                            enabled: !root.isReadOnly
                            KeyNavigation.tab: nickNameEdit
                            onClicked: personModel.showLastName = checkState
                        }
                        
                        // Nick Name

                        PK.Text {
                            id: nickNameLabel
                            text: qsTr("Nick Name")
                        }

                        PK.TextField {
                            id: nickNameEdit
                            Layout.fillWidth: true
                            enabled: !root.isReadOnly && !sceneModel.showAliases
                            text: sceneModel.showAliases ? '' : personModel.nickName
                            KeyNavigation.tab: showNickNameBox
                            onEditingFinished: personModel.nickName = (text ? text : undefined)
                        }

                        PK.CheckBox {
                            id: showNickNameBox
                            /* text: 'Show' */
                            checked: personModel.showNickName
                            enabled: !root.isReadOnly
                            KeyNavigation.tab: birthNameEdit
                            onClicked: personModel.showNickName = checkState
                        }
                        
                        // Birth Name

                        PK.Text {
                            id: birthNameLabel
                            text: qsTr("Birth Name")
                        }

                        PK.TextField {
                            id: birthNameEdit
                            Layout.fillWidth: true
                            text: sceneModel.showAliases ? '' : personModel.birthName
                            enabled: !root.isReadOnly && !sceneModel.showAliases
                            KeyNavigation.tab: kindBox
                            onEditingFinished: personModel.birthName = (text ? text : undefined)
                        }

                        Rectangle { width: 1; height: 20; color: 'transparent' }

                        PK.FormDivider { Layout.columnSpan: 3 }
                        
                        // Kind

                        PK.Text {
                            id: kindLabel
                            text: qsTr("Kind")
                        }

                        PK.ComboBox {
                            id: kindBox
                            enabled: !root.isReadOnly
                            Layout.fillWidth: true
                            model: util.PERSON_KIND_NAMES
                            currentIndex: personModel.genderIndex
                            KeyNavigation.tab: sizeBox
                            onCurrentIndexChanged: personModel.genderIndex = currentIndex
                        }
                                                                        
                        Rectangle { width: 1; height: 1; color: 'transparent' }

                        // Size

                        PK.Text {
                            id: sizeLabel
                            text: qsTr("Size")
                        }

                        PK.ComboBox {
                            id: sizeBox
                            Layout.fillWidth: true
                            currentIndex: personModel.sizeIndex
                            model: util.PERSON_SIZE_NAMES
                            enabled: !root.isReadOnly
                            KeyNavigation.tab: ageBox
                            onCurrentIndexChanged: {
                                if(currentIndex != personModel.sizeIndex) {
                                    personModel.sizeIndex = currentIndex
                                }
                            }
                        }

                        Rectangle { width: 1; height: 1; color: 'transparent' }

                        // Age

                        PK.Text { text: "Age" }

                        RowLayout {
                            Layout.columnSpan: 2
                            PK.TextField {
                                id: ageBox
                                enabled: !root.isReadOnly
                                palette.base: util.QML_ITEM_BG
                                Layout.maximumWidth: 100
                                KeyNavigation.tab: editBirthEventButton
                                Keys.onReturnPressed: setAge()
                                Keys.onEnterPressed: setAge()
                                property bool blocked: false
                                function setAge() {
                                    if(blocked) // when setting age from personProps below
                                        return
                                    var years = parseInt(text)
                                    if(isNaN(years)) {
                                        return
                                    }
                                    blocked = true
                                    personModel.age = years
                                    blocked = false
                                }
                                inputMethodHints: Qt.ImhDigitsOnly
                                function updateFromPerson() {
                                    if(ageBox.blocked) {
                                    } else if(personModel.age == -1) {
                                        ageBox.text = ''
                                    } else if(personModel.birthDateTime === undefined) {
                                        ageBox.text = ''
                                    } else if(isNaN(personModel.birthDateTime)) {
                                        ageBox.text = ''
                                    } else {
                                        ageBox.text = personModel.age
                                    }
                                }
                                Connections {
                                    target: personModel
                                    function onBirthDateTimeChanged() { ageBox.updateFromPerson() }
                                    function onDeceasedDateTimeChanged() { ageBox.updateFromPerson() }
                                    function onDeceasedChanged() { ageBox.updateFromPerson() }
                                }
                            }

                            PK.Text {
                                text: '(Press enter to estimate birth date)'
                                wrapMode: Text.WordWrap
                                font.pixelSize: util.HELP_FONT_SIZE
                                Layout.maximumWidth: 120
                            }
                        }
                        
                        PK.Text { text: " " }

                        PK.Button {
                            id: editBirthEventButton
                            text: "→ Edit Birth Event"
                            visible: personModel.birthDateTime
                            onClicked: root.editBirthEvent()
                        }

                        PK.Text { text: " " }

                        PK.Button {
                            id: editDeathEventButton
                            text: "→ Edit Death Event"
                            visible: personModel.deceasedDateTime
                            onClicked: root.editDeathEvent()
                        }

                        PK.GroupBox {

                            title: "Provisional Settings"
                            Layout.columnSpan: 2
                            Layout.bottomMargin: margin
                            Layout.fillWidth: true

                            ColumnLayout {
                                anchors.fill: parent

                                PK.CheckBox {
                                    id: adoptedBox
                                    objectName: 'adoptedBox'
                                    text: "Show Adopted'
                                    enabled: !personModel.anyMarriedEvents && !personModel.everAdopted
                                    checkState: personModel.adopted
                                    Layout.columnSpan: 2
                                    KeyNavigation.tab: separatedBox
                                    onCheckStateChanged: personModel.adopted = checkState
                                }

                                PK.CheckBox {
                                    id: deceasedBox
                                    objectName: 'deceasedBox'
                                    text: "Show Deceased"
                                    enabled: !personModel.anySeparatedEvents && !personModel.everDivorced
                                    checkState: personModel.deceased
                                    Layout.columnSpan: 2
                                    KeyNavigation.tab: diagramNotesEdit
                                    onCheckStateChanged: personModel.deceased = checkState
                                }

                                PK.Text {
                                    text: "These options show adopted and deceased status prior to adding adopted and death events to this person. These options are unavailable as soon as at least one of the respective events are added to this person."
                                    font.pixelSize: util.HELP_FONT_SIZE
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                               }
                            }


                        // Spacer line

                        Rectangle {
                            height: 1
                            Layout.fillWidth: true
                            Layout.columnSpan: 3
                            Layout.topMargin: margin
                            Layout.bottomMargin: margin
                            color: util.QML_ITEM_BORDER_COLOR
                        }

                        ColumnLayout {
                            Layout.columnSpan: 3

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
                                    text: personModel.diagramNotes
                                    // wrapMode: TextEdit.Wrap
                                    anchors.fill: parent
                                    padding: margin
                                    enabled: !root.isReadOnly
                                    KeyNavigation.tab: primaryBox
                                    onTextChanged: personModel.diagramNotes = (text ? text : undefined)
                                }
                            }
                        }

                        // Spacer line

                        PK.FormDivider { Layout.columnSpan: 3 }

                        Row {

                            Layout.fillWidth: true
                            Layout.columnSpan: 3                            
                        
                            PK.CheckBox {
                                id: primaryBox
                                text: "Primary"
                                enabled: !root.isReadOnly
                                checkState: personModel.primary
                                KeyNavigation.tab: bigFontBox
                                onCheckStateChanged: personModel.primary = checkState
                            }

                            PK.CheckBox {
                                id: bigFontBox
                                text: "Big Font"
                                enabled: !root.isReadOnly
                                checkState: personModel.bigFont
                                KeyNavigation.tab: hideDetailsBox
                                onCheckStateChanged: personModel.bigFont = checkState
                            }
                        }

                        Row {

                            Layout.fillWidth: true
                            Layout.columnSpan: 3                            
                        
                            PK.CheckBox {
                                id: hideDetailsBox
                                text: "Hide Details"
                                enabled: !root.isReadOnly
                                checkState: personModel.hideDetails
                                KeyNavigation.tab: firstNameEdit
                                onCheckStateChanged: personModel.hideDetails = checkState
                            }

                            PK.CheckBox {
                                id: hideDatesBox
                                text: "Hide Dates"
                                enabled: !root.isReadOnly
                                checkState: personModel.hideDates
                                KeyNavigation.tab: firstNameEdit
                                onCheckStateChanged: personModel.hideDates = checkState
                            }

                            PK.CheckBox {
                                id: hideVariablesBox
                                text: "Hide Variables"
                                enabled: !root.isReadOnly
                                checkState: personModel.hideVariables
                                KeyNavigation.tab: firstNameEdit
                                onCheckStateChanged: personModel.hideVariables = checkState
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
                text: personModel.notes
                padding: margin
                wrapMode: TextEdit.Wrap
                enabled: !root.isReadOnly
                anchors.fill: parent
                onEditingFinished: personModel.notes = (text ? text : undefined)
            }
        }

        Item {
            id: metaPage
            Layout.fillHeight: true
            Layout.fillWidth: true
            Rectangle {
                anchors.fill: parent
                anchors.margins: margin
                color: 'transparent'
                
                ColumnLayout {
                    anchors.fill: parent

                    PK.GroupBox {
                        title: "Properties Stored in diagram views"
                        Layout.fillWidth: true
                        enabled: sceneModel.hasActiveLayers && !sceneModel.readOnly
                        GridLayout {
                            columns: 3
                            columnSpacing: util.QML_MARGINS / 2

                            // Color

                            PK.Label { text: "Color"; }
                            
                            PK.ColorPicker {
                                id: colorBox
                                color: personModel.color != undefined ? personModel.color : 'transparent'
                                onCurrentIndexChanged: personModel.color = model[currentIndex]
                            }
                            
                            PK.Button {
                                id: resetColorButton
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.color != '' || personModel.items.length > 1
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.color = undefined
                            }

                            // Deemphasize

                            PK.Label { text: "Deemphasize"; }
                            
                            PK.CheckBox {
                                id: deemphasizeBox
                                checkState: personModel.deemphasize
                                onClicked: personModel.deemphasize = checkState
                            }

                            PK.Button {
                                id: resetDeemphasizeButton
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.deemphasize || personModel.items.length > 1
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.deemphasize = undefined
                            }

                            // Size

                            PK.Label { text: "Size" }
                            
                            PK.ComboBox {
                                id: layerSizeBox
                                model: util.PERSON_SIZE_NAMES
                                currentIndex: personModel.sizeIndex
                                onCurrentIndexChanged: personModel.sizeIndex = currentIndex
                            }
                            
                            PK.Button {
                                id: resetSizeButton
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.sizeIndex != -1 || personModel.items.length > 1
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.sizeIndex = undefined
                            }
                            
                            // Position

                            PK.Label { text: "Position" }
                            
                            PK.Label {
                                id: positionBox
                                text: formatPos(personModel.itemPos)

                                function formatPos(pos) {
                                    return '(' + pos.x.toFixed(0) + ', ' + pos.y.toFixed(0) + ')';
                                }
                            }
                            
                            PK.Button {
                                id: resetItemPosButton
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.isItemPosSetInCurrentLayer
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.itemPos = undefined
                            }
                            
                            // Big Font

                            PK.Label { text: "Big Font" }
                            
                            PK.CheckBox {
                                id: layerBigFontBox
                                checkState: personModel.bigFont
                                onClicked: personModel.bigFont = checkState
                            }

                            PK.Button {
                                id: resetBigFontButton
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.bigFont || personModel.items.length > 1
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.bigFont = undefined
                            }

                            // Hide Details

                            PK.Label { text: "Hide Details" }
                            
                            PK.CheckBox {
                                id: layerHideDetailsBox
                                checkState: personModel.hideDetails
                                onClicked: personModel.hideDetails = checkState
                            }

                            PK.Button {
                                id: resetHideDetailsButton
                                source: '../../clear-button.png'
                                clip: true
                                implicitWidth: 20
                                implicitHeight: 20
                                enabled: personModel.hideDetails || personModel.items.length > 1
                                opacity: enabled ? 1.0 : 0.0
                                onClicked: personModel.hideDetails = undefined
                            }

                        }
                    }
                    PK.GroupBox {
                        title: "Diagram views this person is added to"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        enabled: !root.isReadOnly
                        padding: 1
                        ColumnLayout {
                            anchors.fill: parent
                            PK.ItemLayerList {
                                id: layerList
                                model: LayerItemLayersModel {
                                    scene: sceneModel.scene
                                    items: personModel.items ? personModel.items : []
                                }
                                Layout.fillHeight: true
                                Layout.fillWidth: true
                                Layout.minimumHeight: 10
                            }
                        }
                    }
                }
            }
        }
    }
}
