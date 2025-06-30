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
            console.log('Person:', JSON.stringify(person) );
            pdpModel.append({ "kind": "Person", "data": JSON.stringify(person) });
        }
        for(var i=0; i < pdp.events.length; i++) {
            var event = pdp.events[i];
            console.log('Event:', JSON.stringify(event));
            pdpModel.append({ "kind": "Event", "data": JSON.stringify(event) });
        }
    }

    Connections {
        target: therapist

        // function onResponseReceived(text, pdp) {
        //     print('onResponseReceived:', text, pdp)
        //     root.updatePDP(pdp)
        // }
        function onPdpChanged() {
            console.log('onPdpChanged:', therapist.pdp);
            root.updatePDP(therapist.pdp);
        }
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

        PK.ListView {
            id: pdpList
            visible: pdpModel.count > 0
            clip: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: ListModel {
                id: pdpModel
            }
            delegate: Item {
                width: pdpList.width
                height: util.QML_ITEM_HEIGHT
                clip: true
                ColumnLayout {
                    anchors.fill: parent

                        Text {
                            text: model.data
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }

                    // RowLayout {
                    //     Layout.fillWidth: true
                    //     Layout.preferredHeight: util.QML_ITEM_HEIGHT
                    //     Layout.alignment: Qt.AlignVCenter
                    //     spacing: 5
                    //     Text {
                    //         text: model.kind
                    //         width: 20
                    //     }
                    //     Text {
                    //         text: model.data
                    //         wrapMode: Text.Wrap
                    //         Layout.fillWidth: true
                    //     }
                    // }
                    // PK.Button {
                    //     text: "Accept"
                    //     onClicked: {
                    //         pdpModel.remove(index)
                    //         therapist.acceptPDPItem(model.id)
                    //     }
                    // }
                    // PK.Button {
                    //     text: "Reject"
                    //     onClicked: {
                    //         pdpModel.remove(index)
                    //         therapist.rejectPDPItem(model.id)
                    //     }
                    // }
                }
            }
        }
    }
}
