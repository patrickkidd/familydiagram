import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Layouts 1.12
import QtQuick.Shapes 1.12
import QtQuick.Controls 2.12
import QtQuick.Controls 2.5 as QQC
import "." 1.0 as PK
import PK.Models 1.0
import "../js/Global.js" as Global
import "../js/Underscore.js" as Underscore


ColumnLayout {

    id: root
    spacing: 0
    signal inspect
    signal selectionChanged
    signal rowClicked(int row)
    signal inspectNotes(int row)
    signal ensureVisibleSet(int destinationY) // for testing

    property var _: Qt._

    property int margin: 10
    property date currentDateTime: root.model ? root.model.dateTimeForRow(root.selectionModel.currentRow) : (new Date)
    property int contentY: table.contentY
    property int defaultColumnWidth: 100
    property bool delayUpdates: false
    property int rows: table.rows
    property int columns: table.columns
    property var innerTable: table

    property bool showFilterButton: true

    property bool canInspect: selectionModel.hasSelection
    property bool canRemove: selectionModel.hasSelection

    property var model: sceneModel.timelineModel
    property var modelItems: model ? model.items : []

    property var selectedEvents: []    
    property var selectionModel: ItemSelectionModel {

        property int currentRow: -1
        property bool resetter: false

        model: root.model
        onSelectionChanged: {
            var selectedEvents = []
            var selectedRows = selectionModel.selectedRows(1)
            for(var i=0; i < selectedRows.length; i++) {
                var row = selectedRows[i].row
                var event = model.eventForRow(row)
                if(selectedEvents.indexOf(event) == -1) {
                    selectedEvents.push(event)
                }
            }
            root.selectedEvents = selectedEvents
            resetter = ! resetter // update delegates
            // emit after table.updateSelectionItems() so selectedEvents|Emotions are already updated
            root.selectionChanged()
        }
        onCurrentIndexChanged: {
            if(currentIndex.row != currentRow) {
                currentRow = currentIndex.row
            }
        }
        onCurrentRowChanged: {
            if(currentRow != currentIndex.row) {
                if(currentRow > -1) {
                    setCurrentIndex(root.model.index(currentRow, 0, nullIndex()), ItemSelectionModel.Current)
                } else {
                    select(nullIndex(), ItemSelectionModel.Current | ItemSelectionModel.Rows | ItemSelectionModel.Clear)
                }
            }
        }
    }

    function nullIndex() {
        return root.model.index(-1, -1)
    }

    function removeSelection() {
        model.removeSelection(selectionModel)
    }
    
    function clearSelection() {
        selectionModel.clear()
        selectionModel.currentRow = -1
        selectedEvents = []
    }

    property var columnWidths: []

    function columnWidthProvider(column) {
        var ret = 0
        if(column >= 0 && column < columnWidths.length) {
            ret = columnWidths[column]
        }
        return ret
    }

    onModelItemsChanged: doResponsive()
    
    Connections {
        target: root.model
        function onRowsRemoved() {
            header.updateLayout()
            table.updateLayout()
        }
       function onRowsInserted() {
            header.updateLayout()
            table.updateLayout()
        }
        function onColumnsRemoved() {
            root.updateColumnWidths()
        }
        function onColumnsInserted() {
            root.updateColumnWidths()
        }
        function onModelReset() {
            root.updateColumnWidths()
            root.doResponsive()
            // doesn't really work...
            table.scrollToEnd()
        }
    }

    onWidthChanged: {
        updateColumnWidths()
    }
    
    function updateColumnWidths() {
        var MIN_STRETCH_WIDTH = 150

        // update column widths with stretch columns
        var _columnWidths = []
        var nColumns = model ? model.columnCount() : 0
        // add up non-stretch columns to calculate stretch column widths
        var colWidth
        var nonStretchWidth = 0
        for(var i=0; i < nColumns; i++) {
            var w
            if(hideColumns.indexOf(i) != -1) {
                w = 0
            } else {
                if(stretchColumns.indexOf(i) == -1) {
                    if(hideColumns.indexOf(i) > -1) { // hideColumns
                        w = 0
                    } else if(i == 0) { // date buddies
                        w = 20
                    } else if (i == 1) { // dateTime
                        if(expanded) {
                            w = defaultColumnWidth * 2
                        } else {
                            w = defaultColumnWidth
                        }
                    } else if(i == 4) { // locations
                        w = 130
                    } else if (i == 5) { // parent
                        w = 110 + (root.width * .07)
                    } else if (i == 9) { // tags
                        w = 120 + (root.width * .03)
                    } else {
                        w = defaultColumnWidth
                    }
                    nonStretchWidth += w
                } else {
                    w = null // place holder for stretch column
                }
            }
            _columnWidths.push(w)
        }

        var stretchWidth
        var minStretchWidth = stretchColumns.length * MIN_STRETCH_WIDTH
        if(nonStretchWidth + minStretchWidth > width) {
            // would ideally be min content width, but that might be costly to calculate
            stretchWidth = MIN_STRETCH_WIDTH
        } else {
            stretchWidth = (width - nonStretchWidth) / stretchColumns.length // stretch to fit width
        }
        for(var i=0; i < stretchColumns.length; i++) {
            var col = stretchColumns[i]
            _columnWidths[col] = stretchWidth
        }

        if(!Global.arraysEqual(_columnWidths, columnWidths)) {
            columnWidths = _columnWidths
        }

        var total = 0
        for(var i=0; i < columnWidths.length; i++) {
            total += columnWidths[i]
        }
        header.contentWidth = Math.max(width, total)
        table.contentWidth = Math.max(width, total)

        header.updateLayout()
        table.updateLayout()
    }

    property bool expanded: width >= responsiveBreakWidth
    property int responsiveBreakWidth: 700
    property var normalHideColumns: [0, 2, 4, 7, 8, 9]
    property var expandedHideColumns: util.ENABLE_DATE_BUDDIES ? [2, 7, 8] : [0, 2, 7, 8]
    property var normalStretchColumns: [3]
    property var expandedStretchColumns: [3]
    property var hideColumns: []
    property var stretchColumns: []
    onExpandedChanged: doResponsive()
    function doResponsive() {
        var changed = false
        var _hideColumns,
            _stretchColumns
        // test if a change needs to be made
        if(expanded) {
            _hideColumns = expandedHideColumns.slice(0)
            _stretchColumns = expandedStretchColumns.slice(0)
        } else {
            _hideColumns = normalHideColumns.slice(0)
            var headerColumns = header.model ? header.model.columnCount() : 0
            for(var i=6; i < headerColumns; i++) {
                _hideColumns.push(i)
            }
            _stretchColumns = normalStretchColumns.slice(0)
        }
        if(!Global.arraysEqual(_hideColumns, hideColumns)) {
            hideColumns = _hideColumns.slice(0)
            changed = true
        }
        if(!Global.arraysEqual(_stretchColumns, stretchColumns)) {
            stretchColumns = _stretchColumns.slice(0)
            changed = true
        }
        if(changed) {
            updateColumnWidths()
        }
    }

    function ensureVisible(row) {
        table.ensureVisible(row, false) // here for testing
    }
    

    function scrollToDateTime(dateTime) {
        // print('TimelineView.scrollToDateTime: ' + dateTime)
        var row = model.firstRowForDateTime(dateTime)
        if(row > -1) {
            table.ensureVisible(row, true)
        }
    }
    
    PK.TableView {
        id: header
        objectName: 'header'
        height: util.QML_ITEM_HEIGHT
        Layout.fillWidth: true
        clip: true
        reuseItems: false
        model: table.model ? table.model.headerModel : undefined
        delayUpdates: root.delayUpdates
        contentX: table.contentX
        boundsMovement: Flickable.StopAtBounds
        boundsBehavior: Flickable.DragOverBounds
        columnWidthProvider: root.columnWidthProvider
        rowHeightProvider: function() { return util.QML_ITEM_HEIGHT }
        
        delegate: Rectangle {
            height: util.QML_ITEM_HEIGHT
            property int thisColumn: column
            Rectangle {
                anchors.fill: parent
                color: util.QML_HEADER_BG
            }
/*             Rectangle { // border-top */
/*                 anchors.top: parent.top */
/*                 width: parent.width */
/*                 height: 1 */
/*                 color: util.QML_ITEM_BORDER_COLOR */
/* //                visible: index > 0 */
/*             } */
            Rectangle { // border-left
                width: 1
                height: parent.height
                visible: index != 0 && index != 1
                color: util.QML_ITEM_BORDER_COLOR
            }
            Rectangle { // border-bottom
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: util.QML_ITEM_BORDER_COLOR
            }
            PK.Text {
                id: text
                text: {
                    if(thisColumn == 1 && !expanded) { // dateTime
                        'Date'
                    } else {
                        display
                    }
                }
                visible: hideColumns.indexOf(column) < 0
                anchors.verticalCenter: parent.verticalCenter
                padding: margin
            }
        }
    }
    
    PK.TableView {
        id: table
        objectName: 'table'

        property int lastClickedRow: -1

        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        model: root.model
        visible: ! root.noEventsShown
        delayUpdates: root.delayUpdates
        boundsMovement: Flickable.StopAtBounds
        boundsBehavior: Flickable.DragOverBounds
        contentX: header.contentX
        rowHeightProvider: function(row) { return util.QML_ITEM_HEIGHT }
        columnWidthProvider: root.columnWidthProvider
        Keys.enabled: true
        Keys.onUpPressed: {
            var count = root.model.rowCount()
            if(count > 0) {
                if(selectionModel.currentRow < 0)
                    selectionModel.currentRow = 0
                else if(selectionModel.currentRow > 0)
                    selectionModel.currentRow = selectionModel.currentRow - 1
            } else {
                selectionModel.currentRow = -1
            }
        }
        Keys.onDownPressed: {
            var count = root.model.rowCount()
            if(count > 0) {
                var currentRow = selectionModel.currentRow + 1
                if(currentRow >= count)
                    currentRow = count - 1
                else if(currentRow < 0)
                    currentRow = 0
                selectionModel.currentRow = currentRow
            } else {
                selectionModel.currentRow = -1
            }
        }
        Keys.onPressed: {
            if(event.key == Qt.Key_A && (event.modifiers & Qt.ControlModifier)) {
                selectAll()
            }
        }

        function scrollToEnd() {
            // still doesn't work
            table.contentY = 0 // contentHeight - height
        }

        // reset scroll
        Connections {
            target: root
            function onModelItemsChanged() {
                root.clearSelection()
                table.scrollToEnd()
            }
        }

///        function updateInternalSelectionData() {
            // update existing delegates to avoid a callback for each one
            /* var nDelegates = 0 */
            /* var delegates = table.contentItem.children */
            /* for(var i=0; i < delegates.length; i++) { */
            /*     var delegate = delegates[i] */
            /*     if(delegate.thisColumn !== undefined) { // detect if cell delegate */
            /*         delegate.updateSelected() */
            /*     } */
            /* } */
//        }

        function selectAll() {
            var newRows = []
            for(var row=0; row < root.model.rowCount(); row++) {
                newRows.push(row)
            }
            util.doRowsSelection(selectionModel, newRows, ItemSelectionModel.Select | ItemSelectionModel.Rows)
        }

        // replace with positionViewAtRow|rowAt?
        function ensureVisible(row, anim) {
            // print('ensureVisible: row: ' + row + ' anim: ' + anim)
            if (moving || dragging)
                return;
            if(anim === undefined) {
                anim = true
            }
            var topY = util.QML_ITEM_HEIGHT * row // items are recycled
            var bottomY = util.QML_ITEM_HEIGHT + topY
            // print('topY: ' + topY + ' bottomY: ' + bottomY + ' contentY: ' + contentY + ' height: ' + height)
            // print('topY < contentY: ' + topY < contentY)
            // print('topY > contentY + height: ' + topY > contentY + height)
            // print('bottomY < contentY: ' + bottomY < contentY)
            // print('bottomY > contentY + height: ' + bottomY > contentY + height)
            if ( topY < contentY // begins before
                 || topY > contentY + height // begins after
                 || bottomY < contentY // ends before
                 || bottomY > contentY + height) { // ends after
                // don't exceed bounds
                var destinationY = topY
                /* var destinationY = Math.max(0, Math.min(topY - height + util.QML_ITEM_HEIGHT, */
                /*                                         contentHeight - height)) */
                if(anim && util.ANIM_DURATION_MS > 0) {
                    // print(
                    //     'ensureVisible: destinationY: ' + destinationY + 
                    //     ', ensureVisAnimation.to: ' + ensureVisAnimation.to + 
                    //     ', contentY: ' + contentY +
                    //     ' , ensureVisAnimation.from: ' + ensureVisAnimation.from
                    // )
                    if(destinationY != ensureVisAnimation.to || contentY != ensureVisAnimation.from) {
                        // print('ensureVisible: setting ensureVisAnimation.to: ' + destinationY + ' from: ' + contentY)
                        ensureVisAnimation.to = destinationY;
                        ensureVisAnimation.from = contentY;
                        ensureVisAnimation.start();
                    }
                } else {
                    // print('ensureVisible: setting contentY (' + contentY + ') to destinationY: ' + destinationY)
                    contentY = destinationY
                    // print('max contentY: ' + (table.contentHeight - table.height))
                    // print('contentY: ' + contentY)
                    ensureVisAnimation.finished()
                }
                root.ensureVisibleSet(destinationY)
            }
        }

        onContentYChanged: print('onContentYChanged: ' + contentY)
        //This animation is for the ensure-visible feature.
        NumberAnimation on contentY {
            id: ensureVisAnimation
            objectName: 'ensureVisAnimation'
            to: 0               //Dummy value - will be set up when this animation is called.
            duration: util.ANIM_DURATION_MS
            easing.type: Easing.OutQuad;
            // onFinished: print('ensureVisAnimation.finished; contentY: ' + contentY)
        }

        Rectangle {
            id: currentDateTimeIndicator
            x: 0
            z: 2 // show over delegates
            width: table.contentWidth
            visible: y > -1
            color: 'transparent'
            opacity: .5
            border {
                width: util.CURRENT_DATE_INDICATOR_WIDTH
                color: util.QML_SELECTION_COLOR
            }
            Component.onCompleted: updateRect()
            Connections {
                target: sceneModel
                function onSearchChanged() { currentDateTimeIndicator.updateRect() }
                function onCurrentDateTimeChanged() { currentDateTimeIndicator.updateRect() }
            }
            Connections {
                target: root.model
                function onRowsRemoved() { currentDateTimeIndicator.updateRect() }
                function onRowsInserted() { currentDateTimeIndicator.updateRect() }
                function onColumnsRemoved() { currentDateTimeIndicator.updateRect() }
                function onColumnsInserted() { currentDateTimeIndicator.updateRect() }
            }
            function updateRect() {
                var currentDateTime = sceneModel.currentDateTime
                var currentRows = []
                var betweenRow = table.model.dateBetweenRow(currentDateTime)
                if(betweenRow > -1) {
                    var h = currentDateTimeIndicator.border.width
                    currentDateTimeIndicator.y = (betweenRow + 1) * util.QML_ITEM_HEIGHT - (h * .5)
                    currentDateTimeIndicator.height = h
                } else {
                    var firstRow = table.model.firstRowForDateTime(currentDateTime, root.model)
                    var lastRow = table.model.lastRowForDateTime(currentDateTime, root.model)
                    if(firstRow != -1) {
                        var numRows = (lastRow + 1) - firstRow
                        currentDateTimeIndicator.y = firstRow * util.QML_ITEM_HEIGHT
                        currentDateTimeIndicator.height = numRows * util.QML_ITEM_HEIGHT
                    }
                    else if(firstRow == -1) {
                        currentDateTimeIndicator.y = -1
                        currentDateTimeIndicator.height = 0
                    }
                }
            }

        }

        Rectangle {
            id: buddyItem
            x: 0; y: 0; z: 2
            width: root.columnWidthProvider(0)
            height: table.contentHeight
            visible: width > 0
            color: 'transparent'
            Repeater {
                model: table.model ? table.model.dateBuddies : []
                id: repeater
                Shape {
                    id: box
//                    x: -width // no idea
                    y: modelData.startRow * util.QML_ITEM_HEIGHT
                    height: (modelData.endRow - modelData.startRow + 1) * util.QML_ITEM_HEIGHT
                    width: parent.width
                    ShapePath {
                        id: bracket
                        startX: box.width
                        startY: 0
                        strokeColor: modelData.color
                        strokeWidth: 1
                        fillColor: 'transparent'
                        PathQuad {
                            x: box.width
                            y: box.height
                            controlX: -box.width + 2
                            controlY: box.height / 2
                        }
                    }
                }
            }
        }

        Connections {
            target: root.model
            function onRowsInserted() { updateModel() }
            function onRowsRemoved() { updateModel() }
            function onModelReset() { updateModel() }
            function updateModel() {
                selectionModel.currentRow = -1
                table.lastClickedRow = -1
                doResponsive()
            }
        }

        delegate: Rectangle {

            id: dRoot
            property int thisRow: row
            property int thisColumn: column
            property bool thisNodal: !model.nodal ? false : true
            property bool shouldEdit: false
            property bool editMode: shouldEdit && selected
            property bool editable: flags & Qt.ItemIsEditable
            property bool selected: {
                selectionModel.resetter
                util.isRowSelected(selectionModel, thisRow)
            }
            property bool current: thisRow !== undefined && selectionModel.currentRow != -1 && selectionModel.currentRow == thisRow
            property bool alternate: dRoot.thisRow % 2 == 1
            property bool sameDateAsSelected: model.dateTime != undefined && !isNaN(root.currentDateTime.getTime()) && model.dateTime.getTime() == currentDateTime.getTime()
            clip: true
            implicitHeight: util.QML_ITEM_HEIGHT
            visible: height > 0 && column >= 0 && hideColumns.indexOf(column) < 0

            onEditModeChanged: {
                textEdit.forceActiveFocus()
                textEdit.selectAll()
            }
            onSelectedChanged: {
                if(selected == false && shouldEdit) {
                    textEdit.onEditingFinished()
                    shouldEdit = false // disable edit mode when deselected
                }
                updateColor()
            }
            onCurrentChanged: {
                updateColor()
            }
            onEditableChanged: updateColor()
            onSameDateAsSelectedChanged: updateColor()
            TableView.onReused: updateColor()
            Component.onCompleted: updateColor()

            function updateColor() {
                var c
                if(dRoot.selected || dRoot.current)
                    c = util.itemBgColor(dRoot.selected, dRoot.current, undefined)
                else {
                    if(dRoot.sameDateAsSelected)
                        c = util.QML_SAME_DATE_HIGHLIGHT_COLOR
                    else if(dRoot.thisNodal)
                        c = util.QML_NODAL_COLOR
                    else if(dRoot.alternate)
                        c = util.QML_ITEM_ALTERNATE_BG
                    else
                        c = util.QML_ITEM_BG
                }
                /* else if(!dRoot.editable) */
                /*     c = 'transparent' // '#77dddddd' */
                color = c
            }

            Rectangle { // border-top
                y: 0
                width: parent.width
                height: 1
                visible: thisColumn > 0 && util.ENABLE_DATE_BUDDIES
                color: (root.expanded && model.color != undefined && model.firstBuddy) ? model.color : 'transparent'
            }
            Rectangle { // border-bottom
                y: parent.height - 1
                width: parent.width
                height: 1
                visible: thisColumn > 0 && util.ENABLE_DATE_BUDDIES
                color: (root.expanded && model.color != undefined && model.secondBuddy) ? model.color : 'transparent'
            }

            Rectangle { // border-left
                y: 0
                width: 1
                height: parent.height
                visible: thisColumn > 0
                color: root.expanded ? util.QML_ITEM_BORDER_COLOR : 'transparent'
            }

            // Editors

            PK.TextInput {
                id: textEdit
                property var thisDisplay: expanded ? model.displayExpanded : model.display
                text: thisDisplay == undefined ? '' : thisDisplay
                anchors.verticalCenter: parent.verticalCenter
                visible: column != 5 || !editMode
                width: parent.width
                padding: margin
                readOnly: !editMode
                selectByMouse: !readOnly
                color: {
                    if(dRoot.selected || dRoot.current) {
                        return util.textColor(dRoot.selected, dRoot.current)
                    } else if(dRoot.thisNodal) {
                        return util.contrastTo(util.QML_NODAL_COLOR)
                    } else {
                        return util.contrastTo(dRoot.color)
                    }
                }
                onTextChanged: {
                    if(!editMode) {
                        cursorPosition = 0
                    }
                }
                onReadOnlyChanged: {
                    if(!readOnly && cursorPosition != 0) {
                        cursorPosition = 0
                    }
                }
                onCursorPositionChanged: {
                    if(!editMode && cursorPosition != 0) {
                        cursorPosition = 0
                    }
                }
                onEditingFinished: {
                    // test for edit mode as well b/c this apparently still has focus
                    // even after hitting enter, leading to editingFinished() emitted
                    // whenever enter is pressed again or app window is focused in.
                    if(thisColumn != 5 && editMode) {
                        if(thisDisplay != text) {
                            if(thisColumn == 1 && expanded) {
                                displayExpanded = text
                            } else {
                                display = text
                            }
                        }
                        shouldEdit = false
                    }
                }
            }

            Loader {
                active: editMode && column == 5
                sourceComponent: MouseArea  {
                    width: parentBox.implicitWidth
                    height: parentBox.implicitHeight
                    PK.ComboBox {
                        id: parentBox
                        objectName: 'parentBox'
                        visible: editMode && column == 5
                        anchors.verticalCenter: parent.verticalCenter
                        model: sceneModel.peopleModel
                        textRole: 'name'
                        currentIndex: {
                            model.resetter
                            model.rowForId(parentId)
                        }
                        onCurrentIndexChanged: {
                            if(currentIndex > -1) {
                                parentId = model.idForRow(currentIndex)
//                                shouldEdit = false
                            }
                        }
                        Component.onCompleted: popup.visible = true
                    }
                }
            }
            
            MouseArea {
                anchors.fill: parent
                enabled: !editMode
                onClicked: {
                    if((mouse.modifiers & Qt.ControlModifier) == Qt.ControlModifier) {
                        selectionModel.select(root.model.index(thisRow, 0), ItemSelectionModel.Toggle | ItemSelectionModel.Rows)
                    } else if((mouse.modifiers & Qt.ShiftModifier) == Qt.ShiftModifier && table.lastClickedRow > -1) {
                        var firstRow, lastRow
                        if(table.lastClickedRow <= thisRow) {
                            firstRow = table.lastClickedRow
                            lastRow = thisRow
                        } else {
                            firstRow = thisRow
                            lastRow = table.lastClickedRow
                        }
                        var newRows = []
                        var nRows = root.model.rowCount()
                        for(var row=firstRow; row <= lastRow; row++) {
                            newRows.push(row)
                        }
                        util.doRowsSelection(selectionModel, newRows, ItemSelectionModel.Select | ItemSelectionModel.Rows)
                    } else {
                        selectionModel.select(root.model.index(thisRow, 0), ItemSelectionModel.ClearAndSelect | ItemSelectionModel.Rows)
                        selectionModel.currentRow = thisRow
                    }
                    table.forceActiveFocus()
                    table.lastClickedRow = thisRow
                    // check for image item
                    if(dRoot.childAt(mouse.x, mouse.y) == dNoteIndicator) {
                        root.inspectNotes(thisRow)
                    }
                    root.rowClicked(thisRow)
                }
                onDoubleClicked: {
                    if(editable) {
                        shouldEdit = true
                    }
                }
            }

            Image {
                id: dNoteIndicator
                source: "../../notes-indicator.png"
                y: -2
                property int xDrift: 6 // randomized x axis position
                property var xOffset: (Math.random() * xDrift - (xDrift / 2.0))
                x: parent.width - this.width - (root.margin / 2) + xOffset
                fillMode: Image.PreserveAspectFit
                height: parent.height
                visible: thisColumn == 3 && model.hasNotes
            }            
        }
    }

    property bool noEventsShown: {
        if(table.model == null) {
            return false
        } else if(table.rows == 0) {
            return true
        } else {
            return false
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: "transparent"
        visible: noEventsShown

        Text {
            objectName: "noEventsLabel"
            text: util.S_NO_EVENTS_TEXT
            color: util.QML_INACTIVE_TEXT_COLOR
            anchors.centerIn: parent
            width: parent.width - util.QML_MARGINS * 2
            height: parent.height - util.QML_MARGINS * 2

            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
            font.family: util.NO_ITEMS_FONT_FAMILY
            font.pixelSize: util.NO_ITEMS_FONT_PIXEL_SIZE
            font.bold: true
        }
    }

    Rectangle { // border-bottom
        color: util.QML_ITEM_BORDER_COLOR
        height: 1
        Layout.fillWidth: true
    }


    PK.CrudButtons {
        id: buttons
        objectName: root.objectName + '_crudButtons'
        Layout.fillWidth: true
        addEventButton: true
        addEventButtonEnabled: root.model && root.model.items.length > 0 && !sceneModel.readOnly
        onAddEvent: sceneModel.addEvent(root.model.items, root)
        addEmotionButton: true
        addEmotionButtonEnabled: root.model && root.model.items.length > 0 && !sceneModel.readOnly
        onAddEmotion: sceneModel.addEmotion(root.model.items, root)
        inspectButton: true
        inspectButtonEnabled: root.canInspect
        onInspect: root.inspect()
        removeButton: true
        removeButtonEnabled: root.canRemove && !sceneModel.readOnly
        onRemove: root.removeSelection()
        onFilter: root.showSearchDrawer()
    }


    function test_updateLayout() { // for unit tests
        table.forceLayout()
    }
}
