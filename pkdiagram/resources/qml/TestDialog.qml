import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import "./PK" 1.0 as PK
import PK.Models 1.0
import "js/Global.js" as Global
import "js/Underscore.js" as Underscore




ColumnLayout {

    PK.Text { text: "Anxiety" }

    PK.VariableBox {
        id: anxietyBox
        objectName: "anxietyBox"
        Layout.fillWidth: true
        KeyNavigation.tab: functioningBox
        // KeyNavigation.backtab: anxietyBox
    }

    PK.Text { text: "Functioning" }

    PK.VariableBox {
        id: functioningBox
        objectName: "functioningBox"
        Layout.fillWidth: true
        KeyNavigation.tab: symptomBox
        // KeyNavigation.backtab: functioningBox
    }

    PK.Text { text: "Symptom" }

    PK.VariableBox {
        id: symptomBox
        objectName: "symptomBox"
        Layout.fillWidth: true
        KeyNavigation.tab: anxietyBox
        // KeyNavigation.backtab: functioningBox
    }
}