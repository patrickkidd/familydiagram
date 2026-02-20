# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Code / design rules

- keep as much app logic in python as possible. qml javascript is hard to debug

### UI/UX Changes

- For UI constants (colors, spacing, typography, animation), reference
  `doc/UI_STYLE_SPEC.md`. Values come from `pkdiagram/util.py` and are exposed
  to QML via `QmlUtil.CONSTANTS` in `pkdiagram/app/qmlutil.py`.
- **MANDATORY**: When creating new QML components or interactive UI elements
  requiring design decisions, follow the prototyping process in
  `doc/agents/ui-planner.md` before writing production code. Skip for bug fixes
  and single-property tweaks.
- For undoable app verbs, keep with the pattern of a verb method with
  `undo=False` and then a `def _do_<VERB>` method that does the actual work.

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

## MCP Testing with familydiagram-testing Server

### Critical Rules

1. **Close previous app instances first**: Before launching a new app, ALWAYS call `close_app(force=True)` first. Multiple app instances cause port conflicts (bridge server on 9876) and the MCP bridge will connect to the wrong app.

2. **Pro vs Personal app detection**: The `get_app_state()` checks for Pro app MainWindow first. If a Pro app is running, it will always be detected even if you launched Personal. Kill all instances before switching app types.

3. **Wait for full startup**: After launching the Personal app, wait at least 5-6 seconds. The QML UI takes longer to initialize than the Pro app's native widgets.

4. **Verify app type after launch**: Always check `get_app_state()` returns the expected `appType` ("pro" or "personal") before proceeding with tests. Don't assume the launch worked correctly.

5. **One app at a time**: Never attempt to run Pro and Personal apps simultaneously during MCP testing. The bridge server port conflict will cause failures.

### Common Mistakes to Avoid

- **Launching without closing**: Starting a new app while another is running causes bridge connection to wrong process
- **Wrong app type detection**: Seeing `appType: "pro"` when you expected "personal" means there's a stale Pro app running
- **Ignoring port errors**: "Address already in use" on port 9876 means close all app instances before retrying
- **Insufficient wait time**: Personal app needs more startup time than Pro app due to QML engine initialization

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

### Qt 5.15 SwipeView + QtGraphicalEffects Pitfalls

- `layer.effect: DropShadow` and `Blend` from QtGraphicalEffects cause **blank rendering** inside SwipeView delegates (nested OpenGL framebuffer conflict)
- Fix for DropShadow: remove `layer.enabled`/`layer.effect` entirely from cards
- Fix for Blend (PK.Button dark mode inversion): bypass PK.Button, use inline `Image` with dark/light icon variants selected via `util.IS_UI_DARK_MODE` ternary
- White icon variants: created via PIL `ImageOps.invert()` on RGB channels, preserving alpha (e.g. `pencil-button-white.png`)

### Build System Notes

- Custom qmake config goes in `build/ios-config/` or `build/osx-config/` (.pri files)
- `build/ios/` is the build output directory (generated files get copied there)
- Qt iOS SDK: `/Users/patrick/dev/lib/Qt/5.15.2/ios/`
- Sysroot: `sysroot/sysroot-ios-64/` — PyQt5 bindings in `lib/python3.11/site-packages/PyQt5/`
- `sysroot.toml` controls which Qt modules are built and which PyQt bindings are generated
- `Family Diagram.pro` is auto-generated by pyqtdeploy; customizations go in `.pri` files

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

## As-Built Documentation

**MANDATORY**: Before modifying any feature, check `doc/asbuilts/` for existing documentation. After completing code changes, update the relevant as-built doc (or create one for new features).

| Feature | Doc | Key Files |
|---------|-----|-----------|
| Triangle View | [TRIANGLE_VIEW.md](doc/asbuilts/TRIANGLE_VIEW.md) | `scene/triangle.py`, `models/trianglemodel.py`, `TriangleView.qml` |
| Learn View | [LEARN_VIEW.md](doc/asbuilts/LEARN_VIEW.md) | `resources/qml/Personal/LearnView.qml`, `personal/sarfgraphmodel.py`, `personal/clustermodel.py` |
| Data Sync | [DATA_SYNC_FLOW.md](doc/specs/DATA_SYNC_FLOW.md) | `server_types.py` (`mutate`, `pushToServer`, `save`), `personal/personalappcontroller.py` (`saveDiagram`, `_doAcceptPDPItem`, `_addCommittedItemsToScene`) |

As-built docs contain:
- Component relationships and data flow
- Entry points and exit handlers
- File change lists
- Test coverage
- Implementation details that aren't obvious from code alone

**When to update**: Any code change to files listed in an as-built doc requires updating that doc to keep it accurate. This includes bug fixes, behavior changes, and new features. The as-built doc is the authoritative specification for the feature's behavior.

## Release and Beta Process

See [doc/RELEASE_PROCESS.md](doc/RELEASE_PROCESS.md) for the complete workflow (appcast separation, changelog aggregation, GitHub prerelease flags, test data locations).
