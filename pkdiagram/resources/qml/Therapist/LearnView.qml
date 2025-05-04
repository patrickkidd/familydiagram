import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../PK" 1.0 as PK


Page {

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: util.QML_WINDOW_BG

            PK.NoDataText {
                id: noChatLabel
                text: 'Visualizations, Concepts go here.'
            }
        }
    }
}
