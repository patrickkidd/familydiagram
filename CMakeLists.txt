# https://doc.qt.io/qt-5/cmake-get-started.html

cmake_minimum_required(VERSION 3.9)

project(FamilyDiagram)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt5 COMPONENTS Widgets REQUIRED)


##
## _pkdiagram
##

if(APPLE)
#    set(PKDIAGRAM_MOD_FILENAME "_pkdiagram/build/_pkdiagram/_pkdiagram.cpython-39-darwin.so")
    set(PKDIAGRAM_MOD_FILENAME ".venv/lib/python3.11/site-packages/_pkdiagram.cpython-311-darwin.so")
elseif(WIN32)
    set(PKDIAGRAM_MOD_FILENAME "_pkdiagram/build/_pkdiagram/_pkdiagram.pyd")
else()
    set(PKDIAGRAM_MOD_FILENAME "_pkdiagram/build/_pkdiagram/lib_pkdiagram.so")
endif (APPLE)

add_custom_command(
    OUTPUT ${PKDIAGRAM_MOD_FILENAME}
    COMMAND sip-install --jobs 8 --build-dir build
    DEPENDS _pkdiagram/pyproject.toml _pkdiagram/sip/_pkdiagram/_pkdiagrammod.sip _pkdiagram/*.cpp _pkdiagram/*.h _pkdiagram/*.mm
    BYPRODUCTS _pkdiagram/build # _pkdiagram/build/_pkdiagram/moc__pkdiagram.cpp _pkdiagram/build/_pkdiagram/sip_pkdiagramFDDocument.cpp _pkdiagram/build/_pkdiagram/sip_pkdiagramQMap0100QString0100QString.cpp _pkdiagram/build/_pkdiagram/moc_unsafearea.cpp _pkdiagram/build/_pkdiagram/sip_pkdiagramPathItemBase.cpp _pkdiagram/build/_pkdiagram/sip_pkdiagramcmodule.cpp _pkdiagram/build/_pkdiagram/sip_pkdiagramAppFilter.cpp _pkdiagram/build/_pkdiagram/sip_pkdiagramPathItemDelegate.cpp _pkdiagram/build/_pkdiagram/sip_pkdiagramCUtil.cpp _pkdiagram/build/_pkdiagram/sip_pkdiagramPersonDelegate.cpp
    WORKING_DIRECTORY _pkdiagram
)

add_custom_target(
    _pkdiagram
    ALL
    DEPENDS ${PKDIAGRAM_MOD_FILENAME}
)


##
## pkdiagram
##

add_custom_command(
    OUTPUT pkdiagram/mainwindow/mainwindow_form.py
    DEPENDS pkdiagram/mainwindow/mainwindow.ui
    COMMAND pyuic5 pkdiagram/mainwindow/mainwindow.ui -o pkdiagram/mainwindow/mainwindow_form.py
)

add_custom_command(
    OUTPUT pkdiagram/mainwindow/preferences_form.py
    DEPENDS pkdiagram/mainwindow/preferences.ui
    COMMAND pyuic5 pkdiagram/mainwindow/preferences.ui -o pkdiagram/mainwindow/preferences_form.py
)

add_custom_command(
    OUTPUT pkdiagram/mainwindow/welcome_form.py
    DEPENDS pkdiagram/mainwindow/welcome.ui
    COMMAND pyuic5 pkdiagram/mainwindow/welcome.ui -o pkdiagram/mainwindow/welcome_form.py
)

add_custom_target(
    pkdiagram
    ALL
    DEPENDS pkdiagram/mainwindow/mainwindow_form.py pkdiagram/mainwindow/preferences_form.py pkdiagram/mainwindow/welcome_form.py
)


##
## Dev targets
##

add_custom_target(
    run
    DEPENDS _pkdiagram
    COMMAND python main.py
)

add_custom_target(
    run-attach
    DEPENDS _pkdiagram
    COMMAND python main.py --attach
)

add_custom_target(
    server
    DEPENDS _pkdiagram
    COMMAND cd server && FLASK_CONFIG=development FLASK_APP=fdserver flask run --host 0.0.0.0 --without-threads --port=8888
)

add_custom_target(
    server-attach
    DEPENDS _pkdiagram
    COMMAND cd server && FLASK_CONFIG=development FLASK_APP=fdserver flask run --host 0.0.0.0 --port=8888 --attach
)
