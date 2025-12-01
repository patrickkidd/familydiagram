# App Navigation Shell - Storyboard Proposals

## Problem Statement

The current Personal app has a patchwork layout with several UX issues:

1. **Logout button** - Centered in DiscussView toolbar, conflicts with other header elements
2. **Add Event button** - Right-aligned in Discuss header, may overlap with PDP badge
3. **PDP badge** - Fixed position top-right, fragile for responsive layouts, no semantic parent
4. **No diagram selection** - Currently only supports single user diagram, no UI to switch
5. **Discussions drawer** - 75% width modal, limits discoverability

These issues stem from cramming account-level and document-level controls into a view-level header.

## Established Patterns Research

### Pattern 1: Tab Bar with Profile Tab (iOS Native)
**Used by**: Instagram, Twitter/X, Apple Music, App Store

```
+----------------------------------+
|  [Title]              [Actions]  |  <- View-specific header
+----------------------------------+
|                                  |
|         View Content             |
|                                  |
+----------------------------------+
| [Home] [Search] [+] [Notif] [Me] |  <- Tab bar includes profile
+----------------------------------+
```

**Pros**:
- Clear separation of concerns
- Profile/settings always accessible
- iOS users expect this pattern

**Cons**:
- Uses tab bar real estate for non-content tab
- Diagram switching would need another mechanism

### Pattern 2: Header Avatar Menu (Slack/Discord)
**Used by**: Slack, Discord, Notion, Gmail

```
+----------------------------------+
| [≡] [Workspace ▼]    [🔔] [👤]  |  <- Global header
+----------------------------------+
|                                  |
|         View Content             |
|                                  |
+----------------------------------+
| [Channel 1] [Channel 2] [+]      |  <- Context tabs/list
+----------------------------------+
```

**Pros**:
- Workspace/diagram switching built into header
- Avatar provides clear account access point
- Notifications badge naturally fits

**Cons**:
- More complex header
- May feel less native on iOS

### Pattern 3: Floating Action Button (Material Design)
**Used by**: Google apps, many Android apps, some iOS apps

```
+----------------------------------+
| [←] Discussion Title    [⋮]     |  <- Contextual header
+----------------------------------+
|                                  |
|         View Content             |
|                                  |
|                           [+]    |  <- FAB for primary action
+----------------------------------+
| [Discuss] [Learn] [Plan]         |  <- Tab bar for navigation
+----------------------------------+
```

**Pros**:
- Primary action always visible and accessible
- Header stays clean
- Good for touch ergonomics (thumb zone)

**Cons**:
- FAB can overlap content
- Less native on iOS
- Multiple FABs become awkward

### Pattern 4: Contextual Sheets (Apple Maps/Files)
**Used by**: Apple Maps, Files, Apple Music

```
+----------------------------------+
|         [Handle]                 |  <- Draggable sheet
+----------------------------------+
|  [Search...]         [👤] [⚙️]  |  <- Sheet header
+----------------------------------+
|  Recent Diagrams                 |
|  +---------------------------+   |
|  | Diagram 1              → |   |
|  +---------------------------+   |
|  | Diagram 2              → |   |
+----------------------------------+
```

**Pros**:
- Rich, explorable interface
- Natural for document selection
- iOS-native gesture model

**Cons**:
- Takes over screen
- Not suitable for always-visible elements

## Proposed Variants

### Variant A: Profile Tab Pattern
Add a "Me" tab to house account, settings, and diagram selection.

```
MAIN VIEW (any tab):
+----------------------------------+
|  Discuss              [🔔 3]    |  <- PDP badge in header
+----------------------------------+
|  [≡ Discussions]                 |
|                                  |
|  Chat content...                 |
|                                  |
|  [+] Add event button            |  <- Inline in chat area
+----------------------------------+
| [💬] [📊] [📅] [👤]              |  <- 4 tabs: Discuss,Learn,Plan,Me
+----------------------------------+

ME TAB:
+----------------------------------+
|  Account                         |
+----------------------------------+
|  +---------------------------+   |
|  | patrick@example.com    → |   |  <- Tap for account details
|  +---------------------------+   |
|                                  |
|  Diagrams                        |
|  +---------------------------+   |
|  | ★ Smith Family         → |   |  <- Current diagram starred
|  +---------------------------+   |
|  | Jones Family           → |   |
|  +---------------------------+   |
|  | [+ New Diagram]           |   |
|                                  |
|  [Log Out]                       |
+----------------------------------+
| [💬] [📊] [📅] [👤]              |
+----------------------------------+
```

### Variant B: Header Workspace Switcher
Diagram selection in header, avatar for account menu.

```
+----------------------------------+
| [Smith Family ▼]      [🔔] [👤] |  <- Diagram picker + avatar
+----------------------------------+
|  [≡] Discussions                 |
|                                  |
|  Chat content...                 |
|                                  |
+----------------------------------+
| [Discuss] [Learn] [Plan] [+]     |  <- 3 tabs + add event
+----------------------------------+

DIAGRAM DROPDOWN (on tap):
+----------------------------------+
| [Smith Family ▼]      [🔔] [👤] |
+----------------------------------+
| +------------------------------+ |
| | ★ Smith Family            ✓ | |
| +------------------------------+ |
| | Jones Family                | |
| +------------------------------+ |
| | [+ New Diagram]             | |
| +------------------------------+ |
+----------------------------------+

AVATAR MENU (on tap):
+----------------------------------+
| [Smith Family ▼]      [🔔] [👤] |
+----------------------------------+
|                    +------------+|
|                    | Settings   ||
|                    | Help       ||
|                    | Log Out    ||
|                    +------------+|
```

### Variant C: Contextual Header + FAB
Clean header that changes per view, FAB for primary action.

```
DISCUSS VIEW:
+----------------------------------+
| [≡]  Current Discussion   [🔔]  |  <- Discussion title in header
+----------------------------------+
|                                  |
|  Chat content...                 |
|                                  |
|                           [+]    |  <- FAB for add event
+----------------------------------+
| [💬] [📊] [📅]                   |  <- 3 content tabs
+----------------------------------+

DRAWER (swipe from left):
+----------------------------------+
| patrick@example.com              |
| [Settings] [Log Out]             |
+----------------------------------+
| DIAGRAMS                         |
| ★ Smith Family                   |
|   Jones Family                   |
| [+ New]                          |
+----------------------------------+
| DISCUSSIONS                      |
|   Discussion 1                   |
|   Discussion 2                   |
| [+ New]                          |
+----------------------------------+
```

## Component Mapping

| Component | Variant A | Variant B | Variant C |
|-----------|-----------|-----------|-----------|
| Logout | Me tab | Avatar menu | Left drawer |
| Add Event | Inline button | Tab bar button | FAB |
| PDP Badge | Header right | Header (🔔) | Header right |
| Diagram Select | Me tab list | Header dropdown | Left drawer |
| Discussions | Left drawer | Left drawer | Left drawer |
| Account Settings | Me tab | Avatar menu | Left drawer |

## Recommendation

**Variant B (Header Workspace Switcher)** provides the best balance:

1. **Diagram switching** is prominent and always accessible
2. **Account/logout** tucked into avatar - common, understood pattern
3. **PDP badge** as notification bell - maps to user mental model
4. **Add event** in tab bar keeps Discuss view clean
5. **3 content tabs** preserved - no extra navigation overhead

**Risks**:
- Header may feel crowded on small phones
- Dropdown menu is less native iOS than full sheet

## Next Steps

1. Run QML prototype to compare variants visually
2. Get user feedback on preferred pattern
3. Create detailed component specs for chosen variant
