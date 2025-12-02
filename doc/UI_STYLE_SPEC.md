# UI Style Specification

This document defines the UI constants and theming system for the Family Diagram app.
Values are sourced from `pkdiagram/util.py` and exposed to QML via `pkdiagram/app/qmlutil.py:QmlUtil.CONSTANTS`.

## Typography

| Constant | Desktop | iOS | Description |
|----------|---------|-----|-------------|
| `FONT_FAMILY` | "SF Pro Text" | "SF Pro Text" | Primary body font |
| `FONT_FAMILY_TITLE` | "SF Pro Display" | "SF Pro Display" | Title/header font |
| `TEXT_FONT_SIZE` | 12 | 14 | Body text size (px) |
| `HELP_FONT_SIZE` | 11 | 13 | Helper/caption text (px) |
| `NO_ITEMS_FONT_FAMILY` | "Helvetica" | "Helvetica" | Empty state font |
| `NO_ITEMS_FONT_PIXEL_SIZE` | 20 | 20 | Empty state text size |
| `QML_TITLE_FONT_SIZE` | ~30.6 | ~44.9 | Computed: `QML_ITEM_HEIGHT * 1.2 * 0.85` |
| `QML_SMALL_TITLE_FONT_SIZE` | ~15 | ~17.6 | Section subtitle size |

## Layout & Spacing

| Constant | Desktop | iOS | Description |
|----------|---------|-----|-------------|
| `QML_MARGINS` | 20 | 20 | Outer container margins |
| `QML_ITEM_MARGINS` | 10 | 10 | Inner item padding |
| `QML_SPACING` | 10 | 10 | Gap between items |
| `QML_HEADER_HEIGHT` | 40 | 40 | Header bar height |
| `QML_FIELD_WIDTH` | 200 | 200 | Default input field width |
| `QML_FIELD_HEIGHT` | 40 | 40 | TextField/ComboBox height |
| `QML_ITEM_HEIGHT` | 30 | 44 | List item row height |
| `QML_ITEM_LARGE_HEIGHT` | 44 | 44 | Large list item height |
| `QML_LIST_VIEW_MINIMUM_HEIGHT` | 180 | 264 | Min ListView height (6 rows) |
| `DRAWER_WIDTH` | 400 | 400 | Side drawer width |
| `DRAWER_OVER_WIDTH` | 360 | 400 | Overlay drawer width |
| `BORDER_RADIUS` | 5 | 5 | Corner radius |
| `CURRENT_DATE_INDICATOR_WIDTH` | 4 | 4 | Timeline indicator stroke |

## Button Sizes

| Constant | Value | Description |
|----------|-------|-------------|
| `QML_SMALL_BUTTON_WIDTH` | 50 | Small action button |
| `QML_MICRO_BUTTON_WIDTH` | 21 | Icon-only button |
| `CLEAR_BUTTON_OPACITY` | 1.0 | Clear/reset button opacity |

## Animation

| Constant | Value | Description |
|----------|-------|-------------|
| `ANIM_DURATION_MS` | 250 | Standard animation duration |
| `ANIM_EASING` | `QEasingCurve.OutQuad` | Easing curve |

## Colors - Dark Mode

When `IS_UI_DARK_MODE = True`:

| Constant | Value | Description |
|----------|-------|-------------|
| `QML_WINDOW_BG` | `#1e1e1e` | Main background |
| `QML_HEADER_BG` | `#323232` | Header/toolbar background |
| `QML_CONTROL_BG` | `#2d2b2a` | Control surface background |
| `QML_ITEM_BG` | `#373534` | List item background |
| `QML_ITEM_ALTERNATE_BG` | `#2d2b2a` | Alternating row background |
| `QML_ITEM_BORDER_COLOR` | `#4d4c4c` | Item border/separator |
| `QML_TEXT_COLOR` | `#ffffff` | Primary text |
| `QML_ACTIVE_TEXT_COLOR` | `#ffffff` | Active/focused text |
| `QML_ACTIVE_HELP_TEXT_COLOR` | (white darker 120) | Active helper text |
| `QML_INACTIVE_TEXT_COLOR` | (control bg lighter 160) | Disabled/placeholder text |
| `QML_DROP_SHADOW_COLOR` | (header bg lighter 110) | Shadow color |
| `QML_NODAL_COLOR` | `#fcf5c9` | Nodal highlight (yellow) |
| `GRID_COLOR` | `#767676` | Canvas grid lines |

## Colors - Light Mode

When `IS_UI_DARK_MODE = False`:

| Constant | Value | Description |
|----------|-------|-------------|
| `QML_WINDOW_BG` | `#ffffff` | Main background |
| `QML_HEADER_BG` | `#ffffff` | Header/toolbar background |
| `QML_CONTROL_BG` | `#e0e0e0` | Control surface background |
| `QML_ITEM_BG` | `#ffffff` | List item background |
| `QML_ITEM_ALTERNATE_BG` | `#eeeeee` | Alternating row background |
| `QML_ITEM_BORDER_COLOR` | `lightGrey` | Item border/separator |
| `QML_TEXT_COLOR` | `#000000` | Primary text |
| `QML_ACTIVE_TEXT_COLOR` | `#000000` | Active/focused text |
| `QML_ACTIVE_HELP_TEXT_COLOR` | `#000000` | Active helper text |
| `QML_INACTIVE_TEXT_COLOR` | `grey` | Disabled/placeholder text |
| `QML_DROP_SHADOW_COLOR` | (header bg darker 105) | Shadow color |
| `QML_NODAL_COLOR` | `pink` | Nodal highlight |
| `GRID_COLOR` | `lightGrey` | Canvas grid lines |

## Dynamic System Colors

These colors derive from the macOS/iOS system accent color:

| Constant | Derivation | Description |
|----------|------------|-------------|
| `QML_SELECTION_COLOR` | `CUtil.appleControlAccentColor()` | Selected item background |
| `QML_HIGHLIGHT_COLOR` | `lightenOpacity(SELECTION_COLOR, 0.5)` | Current/hover item |
| `QML_SAME_DATE_HIGHLIGHT_COLOR` | `lightenOpacity(SELECTION_COLOR, 0.35)` | Same-date indicator |
| `QML_SELECTION_TEXT_COLOR` | `contrastTo(SELECTION_COLOR)` | Text on selection |
| `QML_HIGHLIGHT_TEXT_COLOR` | `contrastTo(HIGHLIGHT_COLOR)` | Text on highlight |

## Helper Functions

From `util.py`:

```python
def itemBgColor(selected, current, alternate) -> str:
    """Returns appropriate background color for list item state."""
    if selected:
        return QML_SELECTION_COLOR
    elif current:
        return QML_HIGHLIGHT_COLOR
    elif alternate:
        return QML_ITEM_ALTERNATE_BG
    else:
        return QML_ITEM_BG

def textColor(selected, current) -> str:
    """Returns appropriate text color for item state."""
    if selected:
        return QML_SELECTION_TEXT_COLOR
    elif current:
        return QML_HIGHLIGHT_TEXT_COLOR
    else:
        return QML_TEXT_COLOR

def contrastTo(color) -> QColor:
    """Returns black for light colors, white for dark colors."""
    if isLightColor(color):
        return QColor(Qt.black)
    else:
        return QColor(Qt.white)

def lightenOpacity(color, alpha) -> QColor:
    """Blend color toward white by alpha factor."""
```

## Usage in QML

All constants are exposed via the `util` context property:

```qml
import QtQuick 2.15

Rectangle {
    color: util.QML_WINDOW_BG

    Text {
        text: "Hello"
        font.family: util.FONT_FAMILY
        font.pixelSize: util.TEXT_FONT_SIZE
        color: util.QML_TEXT_COLOR
    }

    ListView {
        delegate: Rectangle {
            height: util.QML_ITEM_HEIGHT
            color: util.itemBgColor(selected, current, index % 2)

            Text {
                color: util.textColor(selected, current)
            }
        }
    }
}
```

## Dark/Light Mode Detection

Mode is determined by user preference in app settings:

1. **System** (`PREFS_UI_HONOR_SYSTEM_DARKLIGHT_MODE`): Follow OS setting via `CUtil.isUIDarkMode()`
2. **Dark** (`PREFS_UI_DARK_MODE`): Force dark mode
3. **Light** (`PREFS_UI_LIGHT_MODE`): Force light mode

Colors are recalculated in `QmlUtil.initColors()` whenever palette changes.
