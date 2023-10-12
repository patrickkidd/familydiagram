import QtQuick 2.12
import QtQuick.Controls 2.12
import PK.Models 1.0


Page {

    signal resize
    signal done

    property var sceneModel: SceneModel {
        objectName: 'PK.Drawer_default_sceneModel'
    } // just to allow for a slight delay before setProperty in DocumentView

    property bool expanded: false

}
