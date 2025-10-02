import QtQuick 2.12
import QtQml.Models 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "./PK" 1.0 as PK
import PK.Models 1.0
import "js/Global.js" as Global
import "js/Underscore.js" as Underscore




ColumnLayout {

    PK.Text { text: "Anxiety" }

    PK.VariableField {
        id: anxietyField
        objectName: "anxietyField"
        Layout.fillWidth: true
        KeyNavigation.tab: functioningField
        // KeyNavigation.backtab: anxietyField
    }

    PK.Text { text: "Functioning" }

    PK.VariableField {
        id: functioningField
        objectName: "functioningField"
        Layout.fillWidth: true
        KeyNavigation.tab: symptomField
        // KeyNavigation.backtab: functioningField
    }

    PK.Text { text: "Symptom" }

    PK.VariableField {
        id: symptomField
        objectName: "symptomField"
        Layout.fillWidth: true
        KeyNavigation.tab: anxietyField
        // KeyNavigation.backtab: functioningField
    }
}