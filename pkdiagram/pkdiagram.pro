TEMPLATE = aux
CONFIG += no_link

include(../build/qmake_features/pyqt5.prf)


FORMS += \
    mainwindow.ui \
    preferences.ui \
    welcome.ui


RESOURCES += \
    ../resources/qml/qml.qrc \
    ../resources/pkdiagram.qrc


DISTFILES += \
    ../resources/qml/AccountDialog.qml \
    ../resources/qml/CaseProperties.qml \
    ../resources/qml/FileManager.qml \
    ../resources/qml/LayerItemProperties.qml \
    ../resources/qml/MarriageProperties.qml \
    ../resources/qml/PK/Button.qml \
    ../resources/qml/PK/ButtonEdit.qml \
    ../resources/qml/PK/ColorPicker.qml \
    ../resources/qml/PK/ComboBox.qml \
    ../resources/qml/PK/DatePicker.qml \
    ../resources/qml/PK/DatePickerButtons.qml \
    ../resources/qml/PK/EmotionProperties.qml \
    ../resources/qml/PK/EventProperties.qml \
    ../resources/qml/PK/FDListView.qml \
    ../resources/qml/PK/Globals.qml \
    ../resources/qml/PK/ListPicker.qml \
    ../resources/qml/PK/SearchBar.qml \
    ../resources/qml/PK/TabButton.qml \
    ../resources/qml/PK/TagEdit.qml \
    ../resources/qml/PK/TextEdit.qml \
    ../resources/qml/PK/TextField.qml \
    ../resources/qml/PK/TextInput.qml \
    ../resources/qml/PK/SearchView.qml \
    ../resources/qml/PK/TimelineView.qml \
    ../resources/qml/PK/Tumbler.qml \
    ../resources/qml/PK/qmldir \
    ../resources/qml/PersonProperties.qml