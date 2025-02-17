import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    id: window
    visible: true
    width: 400
    height: 600
    title: "ListView with Loader Delegate Example"

    // Define a simple model with role names "name" and "message"
    ListModel {
        id: chatModel
        ListElement { name: "Alice"; message: "Hello there!" }
        ListElement { name: "Bob"; message: "Hi, how are you?" }
        ListElement { name: "Charlie"; message: "Good morning!" }
    }

    ListView {
        id: listView
        anchors.fill: parent
        model: chatModel
        spacing: 10

        // Use a Loader as the delegate to dynamically load the component.
        delegate: Loader {
            id: delegateLoader
            // The sourceComponent loads the external component defined below.
            sourceComponent: chatDelegate

            // The loaded item automatically inherits the delegate context,
            // so it can access the model roles "name" and "message".
            onLoaded: {
                console.log("Loaded delegate for " + item.name + ": " + item.message);
            }
        }
    }

    // Define the delegate component.
    Component {
        id: chatDelegate
        Rectangle {
            width: listView.width - 20
            height: 50
            color: "lightblue"
            border.color: "gray"
            radius: 5
            anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined

            // Here we access the model roles directly.
            Text {
                text: name + ": " + message
                anchors.centerIn: parent
                font.pixelSize: 16
            }
        }
    }
}
