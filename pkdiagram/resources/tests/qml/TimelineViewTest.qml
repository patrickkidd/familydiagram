import QtQuick 2.12
import QtQuick.Layouts 1.12
import "../../qml/PK" 1.0 as PK
import PK.Models 1.0


ColumnLayout {

    property var sceneModel: SceneModel {}
    
    PK.TimelineView {
        id: timelineView
        objectName: 'timelineView'
    }

    function test_getDelegates() {
        var ret = []
        for(var i=0; i < timelineView.innerTable.children.length; i++) {
            var child = timelineView.innerTable.children[i]
            if(child.thisRow !== undefined) {
                print('Pushing:', child, child.thisRow)
                ret.push(child)
            } else {
                print('Skipping:', child)
            }
        }
        return ret
    } 
}
