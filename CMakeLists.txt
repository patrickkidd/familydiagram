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
#    set(PKDIAGRAM_MOD_FILENAME "pkdiagram/_pkdiagram/build/_pkdiagram/_pkdiagram.cpython-39-darwin.so")
    set(PKDIAGRAM_MOD_FILENAME ".venv/lib/python3.10/site-packages/_pkdiagram.cpython-310-darwin.so")
elseif(WIN32)
    set(PKDIAGRAM_MOD_FILENAME "pkdiagram/_pkdiagram/build/_pkdiagram/_pkdiagram.pyd")
else()
    set(PKDIAGRAM_MOD_FILENAME "pkdiagram/_pkdiagram/build/_pkdiagram/lib_pkdiagram.so")
endif (APPLE)

add_custom_command(
    OUTPUT ${PKDIAGRAM_MOD_FILENAME}
    COMMAND sip-install --jobs 8 --build-dir build
    DEPENDS pkdiagram/_pkdiagram/pyproject.toml pkdiagram/_pkdiagram/sip/_pkdiagram/_pkdiagrammod.sip pkdiagram/_pkdiagram/*.cpp pkdiagram/_pkdiagram/*.h pkdiagram/_pkdiagram/*.mm
    BYPRODUCTS pkdiagram/_pkdiagram/build # pkdiagram/_pkdiagram/build/_pkdiagram/moc__pkdiagram.cpp pkdiagram/_pkdiagram/build/_pkdiagram/sip_pkdiagramFDDocument.cpp pkdiagram/_pkdiagram/build/_pkdiagram/sip_pkdiagramQMap0100QString0100QString.cpp pkdiagram/_pkdiagram/build/_pkdiagram/moc_unsafearea.cpp pkdiagram/_pkdiagram/build/_pkdiagram/sip_pkdiagramPathItemBase.cpp pkdiagram/_pkdiagram/build/_pkdiagram/sip_pkdiagramcmodule.cpp pkdiagram/_pkdiagram/build/_pkdiagram/sip_pkdiagramAppFilter.cpp pkdiagram/_pkdiagram/build/_pkdiagram/sip_pkdiagramPathItemDelegate.cpp pkdiagram/_pkdiagram/build/_pkdiagram/sip_pkdiagramCUtil.cpp pkdiagram/_pkdiagram/build/_pkdiagram/sip_pkdiagramPersonDelegate.cpp
    WORKING_DIRECTORY pkdiagram/_pkdiagram
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
    OUTPUT pkdiagram/mainwindow_form.py
    DEPENDS pkdiagram/mainwindow.ui
    COMMAND pyuic5 pkdiagram/mainwindow.ui -o pkdiagram/mainwindow_form.py
)

add_custom_command(
    OUTPUT pkdiagram/preferences_form.py
    DEPENDS pkdiagram/preferences.ui
    COMMAND pyuic5 pkdiagram/preferences.ui -o pkdiagram/preferences_form.py
)

add_custom_command(
    OUTPUT pkdiagram/welcome_form.py
    DEPENDS pkdiagram/welcome.ui
    COMMAND pyuic5 pkdiagram/welcome.ui -o pkdiagram/welcome_form.py
)

add_custom_target(
    pkdiagram
    ALL
    DEPENDS pkdiagram/mainwindow_form.py pkdiagram/preferences_form.py pkdiagram/welcome_form.py
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
