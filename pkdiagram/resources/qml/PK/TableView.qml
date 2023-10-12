import QtQuick 2.12


TableView {

    id: root

    onWidthChanged: updateLayout()
    property bool delayUpdates: false // currently when removing event properties
    
    Timer {
        id: delayTimer
        running: false
        repeat: false
        interval: 1
        property int count: 0
        property bool inTimer: false
        onTriggered: {
            inTimer = true
            root.updateLayout()
            running = false
            inTimer = false
        }
    }

    // rows and model.rowCount(), column and model.columnCount() are not always in sync.
    // and QQuickTableView throws assertions when internal indexes are out of row/col bounds.
    // that must occur when an update is called while the table is updating or something
    // so wait until they are all non-zero and equal.
    // Geeze...
    function updateLayout() {

        if(model && !delayTimer.inTimer) {
            if(delayUpdates) {
                delayTimer.running = true
                return
            } else if(model.rowCount() != rows || model.columnCount() != columns) {
                delayTimer.running = true
                return
            } else if(model.rowCount() == 0 || model.columnCount() == 0 ) {
                delayTimer.running = true
                return
            }
        }

        forceLayout()
    }
}
