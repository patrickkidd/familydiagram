import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." 1.0 as PK
import PK.Models 1.0

Rectangle {
    id: root

    // Stores the outputed list of people
    property var model: ListModel {}
    property var peopleModel: ListModel {}
    onPeopleModelChanged: autoCompleteModel.sourceModel = peopleModel

    signal personAdded(string firstName, string lastName, bool isNew)
    signal personRemoved(int index)

    function clear() {
        root.model.clear()
        autoCompleteModel.updateFilter('')
    }

    // Timer {
    //     running: true
    //     repeat: true
    //     onTriggered: {
    //         print('height: ' + autoCompletePopup.height + ', ' + autoCompleteModel.rowCount())
    //     }
    // }


    ListModel {
        id: autoCompleteModel
        property var sourceModel: peopleModel

        function updateFilter(filterText) {
            this.clear()
            if (sourceModel) {
                for (let i = 0; i < sourceModel.rowCount(); ++i) {
                    let index = sourceModel.index(i, 0);
                    let name = sourceModel.data(index);
                    // print(i + ', ' + name + ': ' + name.toLowerCase().indexOf(filterText.toLowerCase()))
                    if (name.toLowerCase().indexOf(filterText.toLowerCase()) !== -1) {
                        // print('   ->> ' + name)
                        this.append({ name: name });
                    }
                }
            }            
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PK.TextField {
            id: nameInput
            placeholderText: "Person's name..."
            Layout.fillWidth: true
            Keys.onReturnPressed: nameInput.add()

            function add() {
                var names = nameInput.text.split(" ");
                root.model.append({"firstName": names[0], "lastName": names[1] || "", "isNew": true});
                nameInput.text = "";
                personAdded(names[0], names[1] || "", true);
            }

            PK.Button {
                id: addNewButton
                objectName: 'addNewButton'
                source: '../../plus-button.png'
                onClicked: nameInput.add()
                visible: nameInput.text.length > 0
                width: util.QML_MICRO_BUTTON_WIDTH
                height: util.QML_MICRO_BUTTON_WIDTH
                anchors.right: nameInput.right
                anchors.rightMargin: util.QML_MARGINS / 2
                anchors.verticalCenter: parent.verticalCenter
            }

            // // Adjust TextField padding to make space for the button
            // rightPadding: addButtonContainer.width + 10

            Popup {
                id: autoCompletePopup
                y: nameInput.height
                width: nameInput.width
                height: Math.min(autoCompleteModel.count * util.QML_ITEM_HEIGHT, 200)
                padding: 0
                contentItem: ListView {
                    id: popupListView
                    implicitHeight: model ? (model.count * delegate.height) : 0
                    model: autoCompleteModel
                    delegate: ItemDelegate {
                        text: name // modelData
                        width: autoCompletePopup.width
                        palette.text: util.QML_TEXT_COLOR
                        background: Rectangle {
                            color: util.QML_ITEM_BG
                        }
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
                    autoCompleteModel.updateFilter(nameInput.text)
                    autoCompletePopup.open();
                } else {
                    autoCompletePopup.close();
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: util.QML_WINDOW_BG
            border.color: util.QML_ITEM_BORDER_COLOR

            ListView {
                anchors.fill: parent
                clip: true
                model: root.model
                contentWidth: width
                delegate: Rectangle {
                    width: parent ? parent.width : 0
                    height: util.QML_ITEM_HEIGHT
                    onHeightChanged: print('height: ' + height)
                    color: util.itemBgColor(false, false, index % 2 == 1)
                    RowLayout {
                        anchors.fill: parent
                        anchors.verticalCenter: parent.verticalCenter

                        PK.Text {
                            text: firstName + " " + lastName + (isNew ? " (New)" : "")
                            leftPadding: util.QML_MARGINS / 2
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignLeft                        
                        }

                        PK.Button {
                            source: '../../delete-button.png'
                            objectName: root.objectName + '_removeButton'
                            Layout.alignment: Qt.AlignRight
                            Layout.rightMargin: util.QML_MARGINS / 2
                            Layout.maximumHeight: util.QML_MICRO_BUTTON_WIDTH
                            Layout.maximumWidth: util.QML_MICRO_BUTTON_WIDTH
                            onClicked: {
                                root.model.remove(index);
                                personRemoved(index);
                            }
                        }
                    }
                    Rectangle {
                        border {
                            width: 1
                            color: 'grey'
                        }
                        color: 'transparent'
                        anchors.fill: parent
                    }
                }
            }
        }
    }
}
