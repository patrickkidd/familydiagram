import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK


Page {

    id: root

    background: Rectangle {
        color: util.QML_WINDOW_BG
        anchors.fill: parent
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: util.QML_MARGINS

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            PK.NoDataText {
                text: "Graphs and insights coming soon."
            }
        }
    }
}
