import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK


Page {

    id: root

    property var pdpList: pdpList

    function updatePDP(pdp) {
        pdpModel.clear()
        for(var i=0; i < pdp.people.length; i++) {
            var person = pdp.people[i];
            console.log('Person:', JSON.stringify(person));
            pdpModel.append({ "kind": "Person", "text": person.name, "id": person.id });
        }
        for(var i=0; i < pdp.events.length; i++) {
            var event = pdp.events[i];
            console.log('Event:', JSON.stringify(event));
            pdpModel.append({ "kind": "Event", "text": event.description, "id": event.id });
        }
    }

    Connections {
        target: therapist
        function onPdpChanged() {
            console.log('onPdpChanged:', therapist.pdp);
            root.updatePDP(therapist.pdp);
        }
    }

    background: Rectangle {
        color: util.QML_WINDOW_BG
        anchors.fill: parent
    }


    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: util.QML_WINDOW_BG
            visible: pdpModel.count == 0

            PK.NoDataText {
                id: noChatLabel
                text: 'No data yet.'
            }
        }

        ListView {
            id: pdpList
            visible: pdpModel.count > 0
            clip: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: ListModel {
                id: pdpModel
            }
            delegate: RowLayout {
                height: util.QML_ITEM_HEIGHT
                clip: true

                property var dText: model.text

                Text {
                    text: dText
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    color: util.QML_TEXT_COLOR
                    // Ensure text does not take space reserved for buttons
                    Layout.preferredWidth: Math.max(0, pdpList.width - (acceptButton.width + rejectButton.width + 16))
                }
                PK.Button {
                    id: acceptButton
                    source: '../../plus-button-green.png'
                    Layout.maximumHeight: util.QML_MICRO_BUTTON_WIDTH
                    Layout.maximumWidth: util.QML_MICRO_BUTTON_WIDTH
                    onClicked: {
                        print('onClicked: Accepting item:', model.id);
                        therapist.acceptPDPItem(model.id)
                        pdpModel.remove(index)
                    }
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                }
                PK.Button {
                    id: rejectButton
                    source: '../../clear-button.png'
                    Layout.maximumHeight: util.QML_MICRO_BUTTON_WIDTH
                    Layout.maximumWidth: util.QML_MICRO_BUTTON_WIDTH
                    onClicked: {
                        print('onClicked: Rejecting item:', model.id);
                        therapist.rejectPDPItem(model.id)
                        pdpModel.remove(index)
                    }
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                }
            }
        }
    }
}
