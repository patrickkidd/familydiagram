/*
    Edit the date portion of a JS Date/QDateTime.
    Should never modify the time portion.
*/

import QtQuick 2.12
import QtQuick.Window 2.2
import QtQuick.Controls 2.12
import "." 1.0 as PK


Rectangle {

    id: root

    property var dateTime
    property bool isValid: dateTime !== undefined && dateTime !== null && !isNaN(dateTime)
    property bool shouldShow: false
    property bool moving: dayColumn.isMouseControlling || monthColumn.isMouseControlling || yearColumn.isMouseControlling
    color: 'transparent'

    width: tumblers.implicitWidth + 10
//    height: tumblers.implicitHeight + 10
//    clip: true

    // private
    property var months: ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                          'August', 'September', 'October', 'November', 'December']
    
    FontMetrics { id: fontMetrics }

    function formatText(count, modelData) {
        var data = count === 12 ? modelData : modelData;
        if(data === undefined) {
            return '';
        }
        var ret = data.toString().length < 2 ? "0" + data : data;
        return ret;
    }

    function updateDays() {
        // Month here is 1-indexed (January is 1, February is 2, etc). This is
        // because we're using 0 as the day so that it returns the last day
        // of the last month, so you have to add 1 to the month number 
        // so it returns the correct amount of days
        function daysInMonth (month, year) {
            return new Date(year, month, 0).getDate();
        }
        var month = monthColumn.model[monthColumn.currentIndex];
        var yearBit = yearColumn.model.get(yearColumn.currentIndex);
        if(yearBit === undefined) {
            return;
        }
        var year = yearBit.year;
        var days = daysInMonth(monthColumn.currentIndex+1, year);
        if(dayColumn.model.count === 0) {
            return;
        }
        while(dayColumn.model.get(dayColumn.model.count-1).day > days) {
            dayColumn.model.remove(dayColumn.model.count-1)
        }
        while(dayColumn.model.get(dayColumn.model.count-1).day < days) {
            dayColumn.model.insert(dayColumn.model.count,
                                   { day: dayColumn.model.get(dayColumn.model.count-1).day+1 })
        }
    }

    // tumblers were changed so set the date property
    property bool blocked: true
    function onTumbler() {
        if(blocked)
            return
        blocked = true
        var yearBit = yearColumn.model.get(yearColumn.currentIndex)
        var year = yearBit.year
        var month = monthColumn.currentIndex
        var day = dayColumn.currentIndex + 1
        var timePart
        if(isValid) {
            timePart = root.dateTime
        } else {
            timePart = util.DEFAULT_USE_TIME
        }
        root.dateTime = new Date(
            year, month, day,
            timePart.getHours(),
            timePart.getMinutes(),
            timePart.getSeconds(),
            timePart.getMilliseconds()
        )
        blocked = false
    }

    signal mousePressed
//    onMousePressed: forceActiveFocus()
    
    onDateTimeChanged: {
        if(blocked)
            return
        blocked = true
        monthColumn.currentIndex = root.dateTime.getMonth()
        dayColumn.currentIndex = root.dateTime.getDate() - 1
        var year = root.dateTime.getFullYear()
        for(var i=0; i < yearColumn.model.count; i++) {
            if(yearColumn.model.get(i).year == year) {
                yearColumn.currentIndex = i
                break
            }
        }
        blocked = false
    }
    
    Component.onCompleted: {
        // set up the days, months, and years of the tumblers
        // blocked is initially true until after onCompleted finishes
        var currentYear = (new Date()).getFullYear();
        for(var i=1700; i <= currentYear; i++) {
            yearColumn.model.append( { 'year': i } )
        }
        for(var i=1; i <= 31; i++) {
            dayColumn.model.append({ 'day': i })
        }
        monthColumn.positionViewAtIndex((new Date()).getMonth(), Tumbler.Center)
        dayColumn.positionViewAtIndex((new Date()).getDate() - 1, Tumbler.Center)
        yearColumn.positionViewAtIndex(yearColumn.model.count - 1, Tumbler.Center)
        blocked = false
    }

    state: shouldShow ? (isValid ? 'invalid' : 'shown') : 'hidden'
    
    states: [
        State {
            name: "invalid"
            PropertyChanges { target: root; implicitHeight: monthColumn.height }
            PropertyChanges { target: tumblers; height: monthColumn.height }
            PropertyChanges { target: root; opacity: 1 }
        },
        State {
            name: "shown"
            PropertyChanges { target: root; implicitHeight: monthColumn.height }
            PropertyChanges { target: tumblers; height: monthColumn.height }
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
                text: formatText(Tumbler.tumbler.count, modelData)
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
                id: monthColumn
                width: 100
                wrap: true
                delegate: delegateComponent
                model: months
                property bool isHandlingClick: false
                property bool isMouseControlling: moving || isHandlingClick
                onCurrentIndexChanged: {
                    root.updateDays()
                    root.onTumbler()
                }
                onMovingChanged: if(moving) mousePressed()
            }
            
            PK.Tumbler {
                id: dayColumn
                delegate: delegateComponent
                width: 40
                wrap: true
                model: ListModel { }
                property bool isHandlingClick: false
                property bool isMouseControlling: moving || isHandlingClick
                onCurrentIndexChanged: {
                    root.onTumbler()
                }
                onMovingChanged: if(moving) mousePressed()
            }
            
            PK.Tumbler {
                id: yearColumn
                delegate: delegateComponent
                wrap: true
                model: ListModel {}
                onCurrentIndexChanged: {
                    root.updateDays()
                    root.onTumbler()
                }
                property bool isHandlingClick: false
                property bool isMouseControlling: moving || isHandlingClick
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



