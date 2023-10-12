import QtQuick 2.12
import "./PK" 1.0 as PK
import PK.Models 1.0

PK.EventProperties {

    id: root
    objectName: 'eventProps'

    signal resize

    property var sceneModel: SceneModel {
        objectName: 'EventProperties_default_sceneModel'
    } // just to allow for a slight delay before setProperty in DocumentView
}