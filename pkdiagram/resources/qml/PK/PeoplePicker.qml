import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property ListModel model: ListModel {}

    // property var autoCompleteModel: sceneModel.peopleModel.autoCompleteNames
    // onAutoCompleteModelChanged: print('onAutoCompleteModelChanged:' + root.autoCompleteModel)

    signal personAdded(string firstName, string lastName, bool isNew)
    signal personRemoved(int index)

    function clear() {
        root.model.clear()
        autoCompleteModel.updateFilter()
    }

    ListModel {
        id: autoCompleteModel
        property var sourceModel: sceneModel ? sceneModel.peopleModel : null
        property string filterText: ""

        function updateFilter() {
            this.clear()
            if (sourceModel) {
                for (let i = 0; i < sourceModel.count; ++i) {
                    let item = sourceModel.get(i);
                    if (item.name.toLowerCase().indexOf(filterText.toLowerCase()) !== -1) {
                        this.append(item);
                    }
                }
            }            
        }
    }    

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        TextField {
            id: nameInput
            placeholderText: "Person's name..."
            Layout.fillWidth: true

            // Embedded Button inside TextField
            Item {
                id: addButtonContainer
                width: addNewButton.width
                height: nameInput.height
                anchors.right: nameInput.right
                anchors.verticalCenter: parent.verticalCenter

                Button {
                    id: addNewButton
                    objectName: "addNewButton"
                    text: "+"
                    anchors.verticalCenter: parent.verticalCenter
                    visible: nameInput.text.length > 0
                    onClicked: {
                        var names = nameInput.text.split(" ");
                        root.model.append({"firstName": names[0], "lastName": names[1] || "", "isNew": true});
                        nameInput.text = "";
                        personAdded(names[0], names[1] || "", true);
                    }
                }
            }

            // Adjust TextField padding to make space for the button
            rightPadding: addButtonContainer.width + 10

            // Autocomplete Popup
            Popup {
                id: autoCompletePopup
                y: nameInput.height
                width: nameInput.width
                // Adjust height based on item count, up to a maximum
                height: Math.min(root.autoCompleteModel ? (root.autoCompleteModel.length * 40) : 0, 200)
                contentItem: ListView {
                    implicitHeight: model ? (model.count * delegate.height) : 0 // Adjust list height based on content
                    model: root.autoCompleteModel
                    delegate: ItemDelegate {
                        text: modelData
                        width: autoCompletePopup.width
                        onClicked: {
                            var names = modelData.split(" ");
                            root.model.append({"firstName": names[0], "lastName": names[1], "isNew": false});
                            nameInput.text = "";
                            autoCompletePopup.close();
                            personAdded(names[0], names[1], false);
                        }
                    }
                }
            }

            onTextChanged: {
                if (text.length > 0) {
                    // Filter autoCompleteModel based on input, for simplicity this is skipped
                    autoCompletePopup.open();
                } else {
                    autoCompletePopup.close();
                }
            }
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.model
            delegate: Rectangle {
                width: parent.width
                height: 40
                color: "#f0f0f0"
                RowLayout {
                    anchors.fill: parent
//                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10

                    Text {
                        text: firstName + " " + lastName + (isNew ? " (New)" : "")
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignLeft                        
                    }

                    Button {
                        text: "Remove"
                        Layout.alignment: Qt.AlignRight
                        onClicked: {
                            root.model.remove(index);
                            personRemoved(index);
                        }
                    }
                }
            }
        }

        Button {
            text: "Clear All"
            Layout.fillWidth: true
            onClicked: {
                root.model.clear();
            }
        }
    }
}
