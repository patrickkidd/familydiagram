import QtQuick 2.12
import QtQuick.Controls 2.5

ListView {
    id: root

    signal rowAdded(Item item)
    signal rowRemoved(Item item)

    property int numDelegates: 0
    property var delegates: []
    property Component userDelegate

    clip: true

    function handleDelegateCompleted(delegateItem) {
        root.numDelegates += 1
        root.delegates.push(delegateItem)
        // print('PK.ListView.rowAdded: ' + delegateItem)
        root.rowAdded(delegateItem)
    }

    function handleDelegateDestruction(delegateItem) {
        root.numDelegates -= 1
        var index = root.delegates.indexOf(delegateItem)
        if (index !== -1) {
            root.delegates.splice(index, 1)
        }
        // print('PK.ListView.rowRemoved: ' + delegateItem)
        root.rowRemoved(delegateItem)
    }

    // Enhanced delegate that preserves model context
    property Component _delegate: Loader {
        id: delegateLoader
        sourceComponent: root.userDelegate
        
        Component.onCompleted: {
            // print('PK.ListView._delegate.onCompleted: ' + delegateLoader)
            root.handleDelegateCompleted(delegateLoader)
        }
        Component.onDestruction: {
            // print('PK.ListView._delegate.onDestruction: ' + delegateLoader)
            root.handleDelegateDestruction(delegateLoader)
        }
    }

    // Capture user's delegate and use our enhanced one
    onDelegateChanged: {
        if (delegate !== _delegate) {
            userDelegate = delegate
            delegate = _delegate
        }
    }
}