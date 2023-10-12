import QtQuick 2.15
import com.tester.stuff 1.0

Item {
    id: root

    property var mine: Mine {}
    property var theirs: null

    onMineChanged: print('onMineChanged:', mine)
    
    Connections {
        target: mine
        function onYoursChanged() {
            print('onYoursChanged', mine.yours)
        }
    }

    Connections {

        // this connects to the first value of &.yours,
        // but does not switch to new values of &.yours,
        // even when `mine.yoursChanged` is emitted.
        target: mine.yours 

        function onTheirsChanged() { // never called
            print('onTheirsChanged', theirs)
            root.theirs = mine.yours.theirs
        }
    }
}