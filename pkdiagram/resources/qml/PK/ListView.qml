import QtQuick 2.12
import QtQuick.Controls 2.5

ListView {
    id: root

    signal rowAdded(Item item)
    signal rowRemoved(Item item)

    property int numDelegates: 0
    property var delegates: []

    clip: true

    function handleDelegateCompleted(delegateItem) {
        root.numDelegates += 1
        root.delegates.push(delegateItem)
        root.rowAdded(delegateItem)
    }

    function handleDelegateDestruction(delegateItem) {
        root.numDelegates -= 1
        var index = root.delegates.indexOf(delegateItem)
        if (index !== -1) {
            root.delegates.splice(index, 1)
        }
        root.rowRemoved(delegateItem)
    }


    // The actual delegate - this will be combined with user-provided delegate
    property Component _delegate: Item {
        id: delegateItem

        // This will hold the user's delegate content
        property Item contentItem: userDelegateLoader.item

        Loader {
            id: userDelegateLoader
            sourceComponent: root.delegate
            onItemChanged: if (item) item.parent = delegateItem
        }

        Component.onCompleted: internal.handleDelegateCompleted(delegateItem)
        Component.onDestruction: internal.handleDelegateDestruction(delegateItem)
    }

    // Override the delegate property to use our enhanced delegate
    delegate: _delegate

}

