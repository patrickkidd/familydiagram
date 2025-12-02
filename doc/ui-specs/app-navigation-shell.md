# App Navigation Shell - Final Spec

## Overview

Redesign of the Personal app's top-level navigation to support:
- Multiple diagrams per account
- Discussion switching within current diagram
- Cleaner separation of account-level vs view-level controls

## Design Decision

**Selected: Header Dropdown for Discussions + Drawer for Diagrams**

Prototype: `doc/ui-prototyping/2-App-Navigation/FINAL-app-shell.qml`

## Layout Structure

```
+----------------------------------+
| [≡]    Session 1 ▼        [3]   |  <- Global header
+----------------------------------+
|                                  |
|         View Content             |
|         (Discuss/Learn/Plan)     |
|                                  |
+----------------------------------+
|   Discuss    Learn    Plan       |  <- Text-only tab bar
+----------------------------------+
```

## Components

### 1. Global Header (56px height)

**Left: Hamburger Menu Button**
- 3-line icon (20px wide lines, 5px spacing)
- Opens left drawer
- Highlight when drawer is open

**Center: Contextual Title**
- Discuss tab: Discussion name + ▼ dropdown indicator
  - Tappable to open discussion switcher dropdown
- Learn tab: Static "Learn" text
- Plan tab: Static "Plan" text

**Right: PDP Badge**
- Red circle (28px diameter) with count
- Opens PDP sheet on tap

### 2. Discussion Dropdown (Discuss tab only)

**Trigger**: Tap on discussion title in header

**Layout**:
```
+------------------------------+
| SMITH FAMILY (diagram label) |
+------------------------------+
| ● Session 1                  |
|   Session 2                  |
|   Intake Notes               |
+------------------------------+
| + New Discussion             |
+------------------------------+
```

**Behavior**:
- Shows current diagram name as section header
- Lists all discussions for current diagram
- Blue dot indicates current selection
- Modal overlay dismisses on tap outside
- Closes after selection

### 3. Left Drawer (QtQuick Drawer)

**Width**: 85% of screen

**Sections** (grouped cards with 12px radius):

1. **ACCOUNT**
   - Avatar (initials) + name + email
   - Tappable to open account settings

2. **DIAGRAMS**
   - List of user's diagrams
   - Blue dot indicates current
   - "+ New Diagram" action

3. **SETTINGS**
   - Notifications
   - Privacy
   - Help & Support

4. **Log Out** (red text, separate card)

### 4. Tab Bar (50px height)

**Style**: Text-only, no icons
- Active tab: Blue (#007AFF), DemiBold weight
- Inactive tab: Gray (#888888), Normal weight

**Tabs**:
- Discuss
- Learn
- Plan

### 5. Content Area

Occupies space between header and tab bar. Each tab loads its respective view component.

## Colors (Dark Mode)

| Element | Color |
|---------|-------|
| Window BG | #1e1e1e |
| Header/Tab BG | #2d2b2a / #1c1c1e |
| Item BG | #373534 |
| Border | #4d4c4c |
| Text | #ffffff |
| Secondary | #888888 |
| Accent | #007AFF |
| Destructive | #FF3B30 |

## Interactions

1. **Open drawer**: Tap hamburger
2. **Switch diagram**: Open drawer → tap diagram → drawer closes
3. **Switch discussion**: Tap header title → dropdown → tap discussion → dropdown closes
4. **New discussion**: Header dropdown → "+ New Discussion"
5. **New diagram**: Drawer → "+ New Diagram"
6. **Open PDP**: Tap badge in header
7. **Log out**: Drawer → "Log Out"

## Migration from Current Design

### Remove from DiscussView:
- Header toolbar with Logout button
- Discussions drawer/button
- PDP badge (moves to global header)

### Add to PersonalContainer:
- Global header component
- Left drawer with account/diagrams/settings
- Discussion dropdown component

### Keep in DiscussView:
- Chat ListView
- Input area
- Event form popup

## Files to Modify

1. `pkdiagram/resources/qml/Personal/PersonalContainer.qml` - Add header, drawer, restructure layout
2. `pkdiagram/resources/qml/Personal/DiscussView.qml` - Remove header, PDP badge, discussions drawer
3. `pkdiagram/personal/personalappcontroller.py` - Add diagram list property, diagram switching methods
