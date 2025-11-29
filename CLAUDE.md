# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Code / design rules

- keep as much app logic in python as possible. qml javascript is hard to debug

### UI/UX Changes

When modifying QML files, UI components, or any visual elements in the Pro or Personal apps, read and follow the design system in `doc/agents/ui-planner.md` before making changes. This includes the Liquid Glass style guide and existing app patterns.
- For undoable app verbs, keep with the pattern of a verb method with `undo=False` and then a `def _do_<VERB>` method that does the actual work.

## Development Commands

### Environment Setup
- **Virtual environment**: Managed by uv workspace (run from repository root)
- **Environment File**: ../.env
- **Python entry point**: `uv run python main.py` (starts the desktop application)

### Testing
- **Run all tests**: `uv run pytest -vv`
- **Single test**: `uv run pytest tests/path/to/test_file.py::test_function -v`
- **Test with debugging**: `uv run pytest tests/path/to/test_file.py::test_function -v --log-cli-level=DEBUG`
- **Ignores**: Tests automatically ignore `lib/`, `sysroot/`, and `test_qml.py` directories

### Build System
- **CMake-based build**: Uses CMakeLists.txt for C++ extensions and Qt UI compilation
- **Build C++ extension and Qt UI Forms**: `cd familydiagram && uv run --env-file ../.env make` (builds the native _pkdiagram module using SIP, compiles .ui files to _form.py files)
- **Run application**: `python -m pkdiagram`

### Linting and Type Checking
- **Configurations**: pyrightconfig.json configures Pyright/Pylance
- **Always run linting**: Check for type errors and imports before committing code
- **Always run black formatter**: `uv run black <filename>`

## Architecture Overview

### Core Application Structure
- **Pro/Desktop App**: PyQt5-based family diagramming application with QML UI
- **Pro/Mobile App**: PyQt5-based family diagramming application with QML UI
- **Main Entry**: `pkdiagram/__main__.py` - application startup and configuration
- **Application Class**: `pkdiagram/app/application.py:Application` - custom QApplication with Qt message handling and extensions
- **PyQt Bridge**: `pkdiagram/pyqt.py` - centralized PyQt5 imports and platform detection

### Key Modules
- **Scene System** (`pkdiagram/scene/`): Core data model / QGraphicsItem types
  (Person, Event, Marriage, etc.) with property system. See
  `pkdiagram/scene/CLAUDE.md`
- **Models** (`pkdiagram/models/`): Qt model classes for QML data binding using QObjectHelper pattern
- **Document/View** (`pkdiagram/documentview/`): Document management, QML engine, and main canvas view
- **QML Engine** (`pkdiagram/documentview/qmlengine.py`): Manages QML context properties and model instances
- **Main Window** (`pkdiagram/mainwindow/`): Native Qt widgets UI with .ui files compiled to Python
- **Personal Module** (`pkdiagram/personal/`): Personal mobile app integration with AI-powered features

### QML/UI Architecture
- **QML Resources**: `pkdiagram/resources/qml/` - QML components organized by module (PK/, Personal/, etc.)
- **Custom Components**: `pkdiagram/resources/qml/PK/` - reusable QML components (ListView, Button, etc.)
- **Property System**: `pkdiagram/models/qobjecthelper.py` - dynamic Qt property generation from scene properties
- **Widget Helpers**: `pkdiagram/widgets/qmlwidgethelper.py` - Python-QML interaction utilities
- **QML Views Notes**:
  - QML is basically just used for the right-side drawer in DocumentView. This right-side drawer becomes the mobile app since QML is mobile-compatible.
  - Every QML view is loaded in a QmlWidgetHelper.
  - The test framework used QQuickItem.objectName() to access items within a view, whcih is now deprecated. We now correctly create root-level properties in each view and access them from QmlWidgetHelper, e.g. DocumentView.caseProps.qml.rootProp('editButton')
  

### Native C++ Integration
- **_pkdiagram Module**: C++ extension built with SIP providing platform utilities (CUtil, AppFilter, etc.)
- **Platform Detection**: `pkdiagram/pyqt.py` detects iOS, macOS, Windows for platform-specific behavior
- **Build System**: CMake handles SIP compilation and Qt UI form generation

### Testing Framework
- **QML Testing**: `tests/widgets/qmlwidgets.py` - QML component testing utilities with ListView synchronization
- **Scene Testing**: Comprehensive scene manipulation and property testing
- **Model Testing**: Qt model behavior verification with mock data
- **Snapshot Testing**: Uses snapshottest for regression testing
- **Updating test suite to new scene api**: Test suite in `./tests` needs to be
  updated to the new scene API. That means:
  - using the new Event() constructor params
  - Creating Item objects in a scene.addItems call like `personA, personB = scene.addItems(Person(), Person())` instead of
  - understanding the new implicit Emotion creation modes creating the items and
  then adding them later
  - Not using composed special events like person.birthEvent and instead adding
    an event with the proper `EventKind` and then using `Scene.eventsFor(item,
    kinds=...)`
  - Using `Scene.find(...)` api where possible, etc.

### External Dependencies
- **Server Integration**: Connects to btcopilot (separate Flask application) for cloud features
- **Personal API**: JSON-based communication with mobile personal application
- **Qt Framework**: PyQt5 with QML for modern UI components
- **Native Libraries**: Platform-specific integrations via C++ extensions

## Development Notes

### QML ListView Testing
- **Deterministic Testing**: Use `waitForListViewDelegates()` from `tests/widgets/qmlwidgets.py`
- **ListView Helper**: `pkdiagram/app/listviewhelper.py` provides synchronous delegate completion detection
- **Component Cache**: QML engine includes `clearComponentCache()` to prevent test isolation issues

### Scene Property System
- **Dynamic Properties**: Scene items use `QObjectHelper.registerQtProperties()` for automatic Qt property generation
- **Property Types**: Supports conversion between Python types and Qt types (QDateTime, Qt.CheckState, etc.)
- **Property Persistence**: Scene items can be serialized/deserialized with full property state
- **Python Object Model**: Adding properties declaratively via Item.registerProperties automatically adds getter and set*() setter methods to the class.

### Build Configuration
- **Multi-platform**: Supports macOS, Windows, and iOS builds with platform-specific configurations
- **Provisioning**: Release builds require environment variables for code signing and app store deployment
- **UI Compilation**: Qt .ui files automatically compiled to Python _form.py files via CMake

### Code Conventions
- **Import Structure**: Always import from `pkdiagram.pyqt` for Qt classes to ensure proper platform handling
- **Testing Patterns**: Use function-based pytest patterns, not class-based
- **QML Integration**: Context properties exposed via QmlEngine for data binding
- **Model Updates**: Use `refreshAllProperties()` to sync model changes to QML bindings
- Use camelCasing for all method and variable names. Capitalize class names like MyNewClass.

## Release and Beta Process

**IMPORTANT**: Read `doc/RELEASE_PROCESS.md` for the complete release workflow. Key points:

### Release/Beta Relationship
- **Beta and release versions are separate**: Beta version `2.1.9b1` and release `2.1.9` appear in **different appcasts**
- **Changelog aggregation**: When release section is empty (`## 2.1.9` with no content), the system automatically aggregates all matching beta versions (e.g., `2.1.9b1`, `2.1.9b2`)
- **Separate feeds**: Beta users see beta appcast with prerelease versions. Release users see release appcast without beta versions
- **GitHub prerelease flag**: Beta versions must have `"prerelease": true`, release versions have `"prerelease": false`

### Changelog Format
```markdown
## 2.1.9           # Empty = auto-aggregate from beta versions

## 2.1.9b2
- Fix edge case from b1

## 2.1.9b1
- New feature X
```

When release `2.1.9` is published with empty section, users upgrading from `2.1.8` to `2.1.9` see combined changelog from both `2.1.9b1` and `2.1.9b2`.

### Test Data
- Test changelog: `pkdiagram/tests/data/test_changelog.md`
- GitHub release data: `pkdiagram/tests/data/github_releases.json`
- Appcast generation: `pkdiagram/extras.py:actions_2_appcast()` and `bin/github_releases_2_appcast.py`
- Changelog extraction: `bin/extract_changelog.py` (handles version parsing and markdown→HTML conversion)