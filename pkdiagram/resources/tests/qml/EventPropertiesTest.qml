import QtQuick 2.12
import "../../qml/PK" 1.0 as PK
import PK.Models 1.0

Rectangle {

    id: root
    objectName: 'root'

    signal done

    width: 800
    height: 600
    
    property var eventModel: EventPropertiesModel { }
    property var sceneModel: null // just a dummy to be a false/null condition

    function setCurrentTab(x) { }

    PK.EventProperties {
        anchors.fill: parent
        eventModel: root.eventModel
    }

}
