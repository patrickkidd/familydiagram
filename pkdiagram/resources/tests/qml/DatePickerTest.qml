import QtQuick 2.12
import "../../qml/PK" 1.0 as PK

Rectangle {

    id: root
    objectName: 'root'

    width: 800
    height: 600
    
    property var model: null
    property var sceneModel: null; // just a dummy to be a false/null condition

    function resetModelDateTime() {
        model.dateTime = undefined
    }

    function resetButtonsDateTimeByProp() {
        dateButtons.dateTime = undefined
        datePickerTumbler.dateTime = undefined
    }

    Item {
        objectName: 'holder'
        property var myModel: model
    }
    
    PK.DatePickerButtons {
        id: dateButtons
        objectName: 'dateButtons'
        
        dateTime: model ? model.dateTime : undefined
        datePicker: datePickerTumbler
        timePicker: timePickerTumbler
        backTabItem: datePickerTumbler
        tabItem: datePickerTumbler
        onDateTimeChanged: {
            if(model) {
                model.dateTime = dateTime
            }
        }
        // MouseArea {
        //     anchors.fill: parent
        //     propagateComposedEvents: true
        //     onPressed: print('onPressed:', Window.activeFocusItem)
        //     onReleased: print('onReleased:', Window.activeFocusItem)
        // }
    }
    PK.DatePicker {
        id: datePickerTumbler
        objectName: 'datePickerTumbler'
        dateTime: model ? model.dateTime : undefined
        onDateTimeChanged: {
            if(model) {
                model.dateTime = dateTime
            }
        }
    }

    PK.TimePicker {
        id: timePickerTumbler
        objectName: 'timePickerTumbler'
        dateTime: model ? model.dateTime : undefined
        onDateTimeChanged: if(model) model.dateTime = dateTime
    }

    Connections {
        target: model
        function onDateTimeChanged() {
            dateButtons.dateTime = model.dateTime
            datePickerTumbler.dateTime = model.dateTime
        }
    }

}
