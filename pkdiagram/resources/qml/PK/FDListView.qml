import QtQuick 2.12
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.5
import "." 1.0 as PK
import "../js/Global.js" as Global


ListView {
    id: root

    property int itemHeight: util.QML_ITEM_HEIGHT * 1.2 // 1.2 // read in file manager
    property int margin: util.QML_MARGINS
    property int editOffset: margin
    property string fontFamily: util.FONT_FAMILY
    property bool editMode: false
    property bool adminMode: false
    property bool isServer: false
    property bool canShowServer: session.hash && session.hasFeature(vedana.LICENSE_PROFESSIONAL) && util.ENABLE_SERVER_VIEW

    signal selected(string path)
    signal finishedEditingTitle;

    property var itemDelegates: [] // for testing
    signal itemAddDone(var item) // for testing

    clip: true
    focus: true

    function isValidDate(d) {
        return d instanceof Date && !isNaN(d);
    }

    function formatModTime(pyTime) {
        var dateTime = new Date(0);
        dateTime.setSeconds(pyTime);
        if(isValidDate(dateTime)) {
            var ret = Qt.formatDateTime(dateTime, 'MMM dd yyyy hh mm ap').split(' ');
            var mon = ret[0],
                day = ret[1],
                year = ret[2],
                hour = ret[3],
                min = ret[4],
                ampm = ret[5];
            if(day[0] === '0')
                day = day[1];
            if(hour[0] === '0')
                hour = hour[1];
            ret = '%1 %2 %3 %4:%5%6'.arg(mon).arg(day).arg(year).arg(hour).arg(min).arg(ampm);
            return ret;
        } else {
            return 'NaN'
        }
    }

    delegate: Item {

        id: dRoot
        width: parent ? parent.width : 0
        height: itemHeight
        property bool selected: false
        property bool current: ListView.isCurrentItem || mouseArea.containsPress
        property bool alternate: index % 2 == 1
        property color textColor: util.textColor(selected, current)
        property bool isFileItem: true // for testing
        property string dPath: path
        function onClicked() {
            if(!editMode) {
                root.currentIndex = index
                root.selected(path)
            }
        }

        // async
        Component.onCompleted: {
            root.itemDelegates.push(this)
            root.itemAddDone(this)
        }
        Component.onDestruction: root.itemDelegates = root.itemDelegates.filter(item => item != this)

        Rectangle { // background
            color: util.itemBgColor(selected, current, alternate)
            width: root.width
            height: parent.height
        }

        PK.Text {
            id: modText
            text: formatModTime(modified)
            y: parent.height - (dRoot.height * .25)
            color: dRoot.textColor
            font {
                pixelSize: dRoot.height * .15
                family: fontFamily
            }
        }

        PK.Image {
            id: openImage
            invert: util.IS_UI_DARK_MODE
            source: '../iOS-disclosure-arrow.png'
            width: 10
            height: 18
            anchors.verticalCenter: parent.verticalCenter
        }

        MouseArea {
            id: mouseArea
            objectName: 'mouseArea'
            width: root.width
            height: parent.height
            enabled: !editMode
            x: 0
            y: 0
            onClicked: dRoot.onClicked()
        }

        PK.TextInput {
            id: fdTitleText
            text: name
            color: dRoot.textColor
            anchors.verticalCenter: parent.verticalCenter
            font {
                pixelSize: dRoot.height * .45
                family: fontFamily
            }
            selectByMouse: !readOnly && !isServer
            readOnly: !editMode || isServer
            onEditingFinished: {
                name = text
                root.finishedEditingTitle()
            }
            enabled: !readOnly && !isServer
        }

        PK.Text {
            id: idText
            visible: isServer && (id !== undefined) && x > (fdTitleText.x + fdTitleText.width) + margin
            text: 'ID:' + id
            color: dRoot.textColor
            y: 0
            x: parent.width - width - 70
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            font.family: "Monaco"
        }

        PK.Text {
            id: ownerText
            visible: isServer && root.canShowServer && x > (fdTitleText.x + fdTitleText.width) + margin
            text: owner ? owner : ''
            color: dRoot.textColor
            y: 0
            x: parent.width - width - 350
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            font.family: "Monaco"
        }

        // PK.CheckBox {
        //     id: shownOnServerBox
        //     visible: isServer && adminMode && x > (fdTitleText.x + fdTitleText.width) + margin
        //     text: 'Show on Server'
        //     textColor: dRoot.textColor
        //     x: idText.x - width - margin
        //     checked: shown
        //     onCheckedChanged: shown = checked
        //     anchors.verticalCenter: parent.verticalCenter
        // }
        
        PK.Button {
            id: deleteImage
            source: '../../delete-button.png'
            height: parent.height - root.margin
            width: height
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.model.deleteFileAtRow(index)
        }                
        
        state: editMode ? 'edit' : 'normal'

        states: [
            State {
                name: 'normal'
                PropertyChanges { target: fdTitleText; x: (margin / 2) }
                PropertyChanges { target: modText; x: (margin / 2) }
                PropertyChanges { target: deleteImage; x: -deleteImage.width }
                PropertyChanges { target: openImage; x: root.width - width - margin }
            },
            State {
                name: 'edit'
                PropertyChanges { target: fdTitleText; x: margin + deleteImage.width }
                PropertyChanges { target: modText; x: margin + deleteImage.width }
                PropertyChanges { target: deleteImage; x: (margin / 2) }
                PropertyChanges { target: openImage; x: root.width + openImage.width }
            }
        ]
        transitions: Transition {
            PropertyAnimation { target: fdTitleText; properties: 'x';
                                duration: util.ANIM_DURATION_MS
                                easing.type: util.ANIM_EASING }
            PropertyAnimation { target: modText; properties: 'x';
                                duration: util.ANIM_DURATION_MS
                                easing.type: util.ANIM_EASING }
            PropertyAnimation { target: deleteImage; properties: 'x';
                                duration: util.ANIM_DURATION_MS
                                easing.type: util.ANIM_EASING }
            PropertyAnimation { target: openImage; properties: 'x';
                                duration: util.ANIM_DURATION_MS
                                easing.type: util.ANIM_EASING }
        }
    }
}

