/*
    Edit the time portion of a JS Date/QDateTime.
    Should never modify the date portion.
*/

import QtQuick 2.12
import QtQuick.Window 2.2
import QtQuick.Controls 2.15
import "." 1.0 as PK


Rectangle {

    id: root

    function _isValid(_dateTime) { return _dateTime !== undefined && _dateTime !== null && !isNaN(_dateTime)}

    property var dateTime
    property var isValid: root._isValid(root.dateTime)
    property bool shouldShow: false
    property bool moving: hourColumn.isMouseControlling || minuteColumn.isMouseControlling || amPmColumn.isMouseControlling
    color: 'transparent'

    width: tumblers.implicitWidth + 10
//    height: tumblers.implicitHeight + 10
//    clip: true

    property var hours: {
        var ret = ['12']
        for(var i=1; i < 12; i++) {
            ret.push('' + i)
        }
        return ret
    }
    property var minutes: {
        var ret = []
        for(var i=0; i < 60; i++) {
            ret.push(('' + i).padStart(2, '0'))
        }
        return ret
    }
    
    FontMetrics { id: fontMetrics }

    // tumblers were changed so set the date property
    property bool blocked: true
    function onTumbler() {
        if(blocked)
            return
        blocked = true
        var hour = hourColumn.currentIndex
        var minute = minuteColumn.currentIndex
        var second = 0
        var millisecond = 0
        if(amPmColumn.currentIndex == 1) {
            hour += 12
        }
        var datePart
        if(isValid) {
            datePart = root.dateTime
        } else {
            datePart = new Date()
        }
        root.dateTime = new Date(
            datePart.getFullYear(),
            datePart.getMonth(),
            datePart.getDate(),
            hour, minute, second, millisecond
        )
        blocked = false
    }

    signal mousePressed
//    onMousePressed: forceActiveFocus()

    Component.onCompleted: {
        if(root._isValid(root.dateTime)) {
            var hour = dateTime.getHours()
            if(hour < 12) {
                amPmColumn.positionViewAtIndex(0, Tumbler.Center)
            } else {
                hour -= 12
                amPmColumn.positionViewAtIndex(0, Tumbler.Center)
            }
            hourColumn.positionViewAtIndex(util.DEFAULT_USE_TIME.getHours(), Tumbler.Center)
            minuteColumn.positionViewAtIndex(util.DEFAULT_USE_TIME.getMinutes(), Tumbler.Center)
        }
        blocked = false
    }

    onDateTimeChanged: {
        if(blocked)
            return
        blocked = true
        if(root._isValid(root.dateTime)) {
            var hour = dateTime.getHours()
            if(hour < 12) {
                if(amPmColumn.currentIndex != 0) {
                    amPmColumn.currentIndex = 0
                }
            } else {
                hour -= 12
                if(amPmColumn.currentIndex != 1) {
                    amPmColumn.currentIndex = 1
                }
            }
            if(hourColumn.currentIndex != hour) {
                hourColumn.currentIndex = hour
            }
            if(minuteColumn.currentIndex != dateTime.getMinutes()) {
                minuteColumn.currentIndex = dateTime.getMinutes()
            }
        } else {
            if(hourColumn.currentIndex != -1)
                hourColumn.currentIndex = -1
            if(minuteColumn.currentIndex != -1)
                minuteColumn.currentIndex = -1
            if(amPmColumn.currentIndex != -1)
                amPmColumn.currentIndex = -1
        }
        blocked = false
    }
    
    state: shouldShow ? (isNaN(dateTime) ? 'invalid' : 'shown') : 'hidden'    
    states: [
        State {
            name: "invalid"
            PropertyChanges { target: root; implicitHeight: hourColumn.height }
            PropertyChanges { target: tumblers; height: hourColumn.height }
            PropertyChanges { target: root; opacity: 1 }
        },
        State {
            name: "shown"
            PropertyChanges { target: root; implicitHeight: hourColumn.height }
            PropertyChanges { target: tumblers; height: hourColumn.height }
            PropertyChanges { target: root; opacity: 1 }
        },
        State {
            name: "hidden"
            PropertyChanges { target: root; implicitHeight: 0 }
            PropertyChanges { target: tumblers; height: 0 }
            PropertyChanges { target: root; opacity: 0 }
        }
    ]
    Behavior on implicitHeight {
        NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
    }
    Behavior on opacity {
        NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
    }
    
    Component {
        id: delegateComponent
        Item {
            id: dRoot
            opacity: 1.0 - Math.abs(Tumbler.displacement) / (Tumbler.tumbler.visibleItemCount / 2)
            Label {
                id: label
                anchors.fill: parent
                antialiasing: true
                text: modelData // formatText(Tumbler.tumbler.count, modelData)
                color: isValid ? util.QML_ACTIVE_TEXT_COLOR : util.QML_INACTIVE_TEXT_COLOR
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: fontMetrics.font.pixelSize * 1.25
                /* property real yScaleVal: 1.0 - Math.abs(Tumbler.displacement) / (Tumbler.tumbler.visibleItemCount / 2) */
                /* height: Tumbler.tumbler.visibleItemCount * 5 */
                /* transform: Matrix4x4 { */
                /*     matrix: Qt.matrix4x4(1,           0,            0, 0, */
                /*                          0,           1,            0, 0, */
                /*                          0,           0,            1, 0, */
                /*                          0,           0,            0, 1) */
                /* } */
            }
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    Tumbler.tumbler.isHandlingClick = true
                    if(index == Tumbler.tumbler.currentIndex) {
                        Tumbler.tumbler.onCurrentIndexChanged()
                    } else {
                        if(Tumbler.tumbler.currentIndex != index)
                            Tumbler.tumbler.currentIndex = index
                    }
                    root.mousePressed()
                    Tumbler.tumbler.isHandlingClick = false
                }
            }
        }
    }
    

    Rectangle {
        id: tumblers
        width: parent.width
        height: parent.height
        clip: true
        color: 'transparent'

        Behavior on height {
            NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
        }
        
        Row {
            id: row
            anchors.horizontalCenter: parent.horizontalCenter
            height: parent.height

            PK.Tumbler {
                id: hourColumn
                width: 15
                wrap: true
                delegate: delegateComponent
                model: hours
                property bool isHandlingClick: false
                property bool isMouseControlling: moving || isHandlingClick
                onCurrentIndexChanged: root.onTumbler()
                onMovingChanged: if(moving) mousePressed()
            }

            PK.Tumbler {
                id: colonColumn
                width: 15
                model: [':']
                delegate: delegateComponent
            }
            
            PK.Tumbler {
                id: minuteColumn
                delegate: delegateComponent
                width: 20
                wrap: true
                model: minutes
                property bool isHandlingClick: false
                property bool isMouseControlling: moving || isHandlingClick
                onCurrentIndexChanged: root.onTumbler()
                onMovingChanged: if(moving) mousePressed()
            }
            
            PK.Tumbler {
                id: amPmColumn
                delegate: delegateComponent
                width: 35
                wrap: true
                model: ['am', 'pm']
                property bool isHandlingClick: false
                property bool isMouseControlling: moving || isHandlingClick
                onCurrentIndexChanged: root.onTumbler()
                onMovingChanged: if(moving) mousePressed()
            }
        }
    }

    Rectangle {
        anchors.horizontalCenter: parent.left
        y: parent.height * 0.4
        width: 100000
        height: 1
        color: util.QML_ITEM_BORDER_COLOR
    }
    
    Rectangle {
        anchors.horizontalCenter: parent.left
        y: parent.height * 0.6
        width: 100000
        height: 1
        color: util.QML_ITEM_BORDER_COLOR
    }
            
}



