import QtQuick 2.12
import "../../qml/PK" 1.0 as PK
import PK.Models 1.0

PK.SearchView {
    property var sceneModel: SceneModel {
        objectName: "dummy_SearchModel";
    }
}
