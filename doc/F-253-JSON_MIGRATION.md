# JSON Migration

## Overview

Migrating from pickle to JSON serialization for .fd diagram files to remove Qt dependencies from persisted data and improve portability.

## Motivation

- **Qt Dependency**: Pickle serializes QPointF and QDateTime objects directly, creating tight coupling with Qt internals
- **Portability**: JSON is more portable and easier to debug/inspect than binary pickle
- **Version Control**: JSON files are human-readable and diff-friendly
- **Security**: Removes pickle deserialization risks

## File Format Changes

### Before (Pickle)
```
MyDiagram.fd/
└── diagram.pickle  (binary pickle data with Qt objects)
```

### After (JSON)
```
MyDiagram.fd/
└── diagram.json  (JSON with Python native types)
```

## Qt Type Conversions

| Qt Type | JSON Representation |
|---------|---------------------|
| `QPointF(x, y)` | `{"x": float, "y": float}` |
| `QDateTime` | ISO 8601 string via `.toString(Qt.ISODate)` |
| `QDate` | ISO date string via `.toString(Qt.ISODate)` |
| `EventKind enum` | `.value` property (string) |
| `RelationshipKind enum` | `.value` property (string) |

## Implementation Status

### ✅ Completed
- [x] Created `pkdiagram/schema.py` with Qt conversion functions
- [x] Created `btcopilot/btcopilot/schema.py` with pure Python dataclasses
- [x] Created `doc/JSON_MIGRATION.md`
- [x] Added `USE_JSON_DIAGRAMS` feature flag to `util.py`
- [x] Updated `Item.write()` to convert Qt types
- [x] Updated `compat.py` for Qt conversions
- [x] Updated `util.py` touchFD function with flag support
- [x] Updated `mainwindow.py` save operations (3 locations) with flag support
- [x] Updated `serverfilemanagermodel.py` with flag support
- [x] Updated C++ extension constant to diagram.pickle
- [x] Rebuilt C++ extension
- [x] Centralized backwards compatibility in `schema.loadFromBytes()`

### ⏳ Pending
- [ ] Test backwards compatibility with real pickle files
- [ ] Test JSON format when flag is enabled
- [ ] Test server sync functionality
- [ ] Update btcopilot server to handle JSON data dict format

## Feature Flag

The JSON format is controlled by `util.USE_JSON_DIAGRAMS` flag (default: False).

### When USE_JSON_DIAGRAMS = False (Current State)
- All diagram files written in pickle format (diagram.pickle)
- Maintains full compatibility with older app versions
- Server sync uses pickle-based data internally, sends JSON to server
- Safe for gradual Sparkle-based rollout

### When USE_JSON_DIAGRAMS = True (Future State)
- All diagram files written in JSON format (diagram.json)
- Requires all users to have updated to version with JSON support
- Server sync uses JSON throughout
- Better portability and debugging

### Migration Path
1. Deploy with `USE_JSON_DIAGRAMS = False`
2. Wait for user adoption via Sparkle updates (2-4 weeks)
3. Change flag to `True` in util.py
4. Rebuild C++ extension (`pipenv run make`)
5. Deploy new version with JSON enabled
6. All versions can read both formats (permanent backwards compatibility)

## Backwards Compatibility

Both old and new files work regardless of flag setting:
1. `schema.loadFromBytes()` tries JSON first, falls back to pickle
2. C++ reads diagram.json first, falls back to diagram.pickle
3. `compat.py` migrations convert Qt types to Python natives
4. File saved in format matching current flag setting

## Server Integration

Server API (btcopilot) needs coordinated update:
- `PUT /diagrams/{id}` must accept JSON data
- `GET /diagrams/{id}` must return JSON data
- Database migration may be needed for existing diagrams

## Testing Checklist

- [ ] Load old pickle .fd file → verify conversion works
- [ ] Save new .fd file → verify JSON format
- [ ] Load newly saved JSON file → verify roundtrip
- [ ] Verify all Qt types converted correctly
- [ ] Test selection-only export
- [ ] Test server sync (requires btcopilot changes)
- [ ] Run full test suite

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| C++ extension not rebuilt | Add to build documentation, fail fast if version mismatch |
| Server API breaking change | Coordinate with btcopilot deployment |
| Old files won't load | Maintain pickle fallback indefinitely |
| Qt type conversion bugs | Comprehensive unit tests for conversion functions |

## Files Modified

### Core Changes
- `pkdiagram/schema.py` - New file with Qt conversion functions and centralized loadFromBytes()
- `btcopilot/btcopilot/schema.py` - New file with pure Python dataclass definitions (no Qt)
- `pkdiagram/util.py` - Added USE_JSON_DIAGRAMS flag, getDiagramDataFileName(), updated touchFD()
- `_pkdiagram/_pkdiagram.cpp` - Reverted DiagramDataFileName to "diagram.pickle" (line 120)
- `_pkdiagram/_pkdiagram_mac.mm` - Updated LegacyDiagramDataFileName to "diagram.json" (line 148)
- `pkdiagram/scene/item.py` - Convert Qt types in write(), convert back in read()
- `pkdiagram/models/compat.py` - Add Qt conversion in UP_TO("2.0.12b1") migration
- `pkdiagram/mainwindow/mainwindow.py` - Flag-gated serialization in 3 save locations
- `pkdiagram/models/serverfilemanagermodel.py` - Flag-gated deserialization for server uploads
- `pkdiagram/documentview/legend.py` - Use centralized loadFromBytes()

### Documentation
- `doc/JSON_MIGRATION.md` - This file

## Notes

- Schema dataclasses serve as documentation and optional validation
- Existing dict-based write() methods preserved
- Qt type conversion happens during serialization
- No changes to in-memory object structure
