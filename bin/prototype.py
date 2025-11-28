#!/usr/bin/env python
"""
Minimal QML prototype runner for UI design iteration.

Usage:
    uv run python bin/prototype.py doc/ui-specs/prototypes/feature.qml
    uv run python bin/prototype.py doc/ui-specs/prototypes/feature.qml --dark
    uv run python bin/prototype.py doc/ui-specs/prototypes/feature.qml --light

Creates a minimal QmlUtil context so prototypes can use `util.*` properties.
"""

import sys
import argparse

from pkdiagram.pyqt import (
    Qt,
    QApplication,
    QQuickView,
    QUrl,
    QObject,
    pyqtProperty,
    QColor,
)


class PrototypeUtil(QObject):
    """Minimal util mock for prototyping. Mirrors QmlUtil constants."""

    def __init__(self, darkMode: bool = True):
        super().__init__()
        self._darkMode = darkMode
        self._initColors()

    def _initColors(self):
        if self._darkMode:
            self._windowBg = "#1e1e1e"
            self._itemBg = "#373534"
            self._itemAlternateBg = "#2d2b2a"
            self._itemBorderColor = "#4d4c4c"
            self._headerBg = "#323232"
            self._controlBg = "#2d2b2a"
            self._textColor = "#ffffff"
            self._inactiveTextColor = "#6b6a69"
            self._dropShadowColor = "#3a3a3a"
            self._selectionColor = "#0a84ff"
            self._highlightColor = "#0a84ff80"
        else:
            self._windowBg = "#ffffff"
            self._itemBg = "#ffffff"
            self._itemAlternateBg = "#eeeeee"
            self._itemBorderColor = "#d3d3d3"
            self._headerBg = "#ffffff"
            self._controlBg = "#e0e0e0"
            self._textColor = "#000000"
            self._inactiveTextColor = "#808080"
            self._dropShadowColor = "#f2f2f2"
            self._selectionColor = "#007aff"
            self._highlightColor = "#007aff80"

    # Dark mode flag
    @pyqtProperty(bool)
    def IS_UI_DARK_MODE(self):
        return self._darkMode

    @pyqtProperty(bool)
    def IS_IOS(self):
        return False

    # Colors
    @pyqtProperty(str)
    def QML_WINDOW_BG(self):
        return self._windowBg

    @pyqtProperty(str)
    def QML_ITEM_BG(self):
        return self._itemBg

    @pyqtProperty(str)
    def QML_ITEM_ALTERNATE_BG(self):
        return self._itemAlternateBg

    @pyqtProperty(str)
    def QML_ITEM_BORDER_COLOR(self):
        return self._itemBorderColor

    @pyqtProperty(str)
    def QML_HEADER_BG(self):
        return self._headerBg

    @pyqtProperty(str)
    def QML_CONTROL_BG(self):
        return self._controlBg

    @pyqtProperty(str)
    def QML_TEXT_COLOR(self):
        return self._textColor

    @pyqtProperty(str)
    def QML_INACTIVE_TEXT_COLOR(self):
        return self._inactiveTextColor

    @pyqtProperty(str)
    def QML_DROP_SHADOW_COLOR(self):
        return self._dropShadowColor

    @pyqtProperty(str)
    def QML_SELECTION_COLOR(self):
        return self._selectionColor

    @pyqtProperty(str)
    def QML_HIGHLIGHT_COLOR(self):
        return self._highlightColor

    @pyqtProperty(str)
    def QML_SELECTION_TEXT_COLOR(self):
        return "#ffffff"

    @pyqtProperty(str)
    def QML_HIGHLIGHT_TEXT_COLOR(self):
        return "#ffffff" if self._darkMode else "#000000"

    @pyqtProperty(str)
    def QML_ACTIVE_TEXT_COLOR(self):
        return self._textColor

    @pyqtProperty(str)
    def QML_ACTIVE_HELP_TEXT_COLOR(self):
        return "#cccccc" if self._darkMode else "#000000"

    @pyqtProperty(str)
    def QML_NODAL_COLOR(self):
        return "#fcf5c9" if self._darkMode else "#ffc0cb"

    @pyqtProperty(str)
    def QML_SAME_DATE_HIGHLIGHT_COLOR(self):
        return "#0a84ff59" if self._darkMode else "#007aff59"

    # Spacing
    @pyqtProperty(int)
    def QML_MARGINS(self):
        return 15

    @pyqtProperty(int)
    def QML_ITEM_MARGINS(self):
        return 10

    @pyqtProperty(int)
    def QML_SPACING(self):
        return 8

    @pyqtProperty(int)
    def QML_ITEM_HEIGHT(self):
        return 44

    @pyqtProperty(int)
    def QML_ITEM_LARGE_HEIGHT(self):
        return 66

    @pyqtProperty(int)
    def QML_HEADER_HEIGHT(self):
        return 60

    @pyqtProperty(int)
    def QML_FIELD_WIDTH(self):
        return 180

    @pyqtProperty(int)
    def QML_FIELD_HEIGHT(self):
        return 32

    @pyqtProperty(int)
    def QML_SMALL_BUTTON_WIDTH(self):
        return 32

    @pyqtProperty(int)
    def QML_MICRO_BUTTON_WIDTH(self):
        return 28

    # Typography
    @pyqtProperty(int)
    def TEXT_FONT_SIZE(self):
        return 13

    @pyqtProperty(int)
    def HELP_FONT_SIZE(self):
        return 11

    @pyqtProperty(int)
    def QML_TITLE_FONT_SIZE(self):
        return 18

    @pyqtProperty(int)
    def QML_SMALL_TITLE_FONT_SIZE(self):
        return 14

    @pyqtProperty(str)
    def FONT_FAMILY(self):
        return ""

    @pyqtProperty(str)
    def FONT_FAMILY_TITLE(self):
        return ""

    # Animation
    @pyqtProperty(int)
    def ANIM_DURATION_MS(self):
        return 200


def main():
    parser = argparse.ArgumentParser(description="Run QML prototype with util context")
    parser.add_argument("qml_file", help="Path to QML file")
    parser.add_argument("--dark", action="store_true", help="Use dark mode (default)")
    parser.add_argument("--light", action="store_true", help="Use light mode")
    parser.add_argument("--width", type=int, default=390, help="Window width (default: 390, iPhone 14)")
    parser.add_argument("--height", type=int, default=844, help="Window height (default: 844, iPhone 14)")
    args = parser.parse_args()

    darkMode = not args.light

    app = QApplication(sys.argv)

    util = PrototypeUtil(darkMode=darkMode)

    view = QQuickView()
    view.rootContext().setContextProperty("util", util)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setSource(QUrl.fromLocalFile(args.qml_file))

    if view.status() == QQuickView.Error:
        for error in view.errors():
            print(f"QML Error: {error.toString()}")
        sys.exit(1)

    view.setWidth(args.width)
    view.setHeight(args.height)
    view.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
