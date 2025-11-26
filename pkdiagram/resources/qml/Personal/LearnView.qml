import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK
import "../js/Global.js" as Global

Page {

    id: root

    property var pdpList: pdpList

    function _addPDPItem(kind, text, id) {
        pdpModel.append({ "kind": kind, "text": text, "id": id });
    }

    function _removePDPItemById(id) {
        for(var i=0; i < pdpModel.count; i++) {
            if(pdpModel.get(i).id === id) {
                pdpModel.remove(i);
                return;
            }
        }
    }

    function updatePDP(pdp) {
        pdpModel.clear()
        // print('clear()')
        if(!pdp) {
            return
        }
        // print(pdp, 'people:', pdp.people, 'events:', pdp.events)
        if(pdp.people && pdp.people.length > 0) {
            for(var i=0; i < pdp.people.length; i++) {
                var person = pdp.people[i];
                _addPDPItem("Person", person.name, person.id);
            }
        }
        if(pdp.events && pdp.events.length > 0) {
            for(var i=0; i < pdp.events.length; i++) {
                var event = pdp.events[i];
                _addPDPItem("Event", event.description, event.id);
            }
        }
    }

    Connections {
        target: personal
        function onPdpChanged() {
            // console.log('onPdpChanged:', personal.pdp);
            root.updatePDP(personal.pdp);
        }
        function onPdpItemAdded(item) {
            util.info('onPdpItemAdded:', item.id, 'personal.pdp:', personal.pdp);
            Global.printObject(item)
            _addPDPItem(item.kind, item.text, item.id);
        }
        function onPdpItemRemoved(id) {
            util.info('onPdpItemRemoved:', id, 'personal.pdp:', personal.pdp);
            Global.printObject(item)
            _removePDPItemById(id);
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
                    text: dText ? dText : ''
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
                        personal.acceptPDPItem(model.id)
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
                        personal.rejectPDPItem(model.id)
                    }
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                }
            }
        }
    }
}
