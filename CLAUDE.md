# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
- **Virtual environment**: `pipenv run` (uses Pipfile for dependencies, required for all bash commands to add dependencies to PYTHONPATH via .env file)
- **Environment File**: ./.env
- **Python entry point**: `python main.py` (starts the desktop application)

### Testing
- **Run all tests**: `python -m pytest -vv`
- **Single test**: `python -m pytest tests/path/to/test_file.py::test_function -v`
- **Test with debugging**: `python -m pytest tests/path/to/test_file.py::test_function -v --log-cli-level=DEBUG`
- **Ignores**: Tests automatically ignore `lib/`, `sysroot/`, and `test_qml.py` directories

### Build System
- **CMake-based build**: Uses CMakeLists.txt for C++ extensions and Qt UI compilation
- **Build C++ extension and Qt UI Forms**: `make` (builds the native _pkdiagram module using SIP, compiles .ui files to _form.py files)
- **Run application**: `python -m pkdiagram`

### Linting and Type Checking
- **Configurations**: pyrightconfig.json configures Pyright/Pylance
- **Always run linting**: Check for type errors and imports before committing code
- **Always run black formatter**: `pipenv run black <filename>`

## Architecture Overview

### Core Application Structure
- **Desktop Application**: PyQt5-based family diagramming application with QML UI
- **Main Entry**: `pkdiagram/main.py` - application startup and configuration
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

## Code Rules

- Keep all names, e.g. variables, functions, classes, methods, modules, etc, as
  short, accurate, and precise as possible.
- Use consistent naming and code organization conventions.
- Use the minimum amount of code as possible.
- Never use "process" in a callable name.
- Keep code self-documenting.
- Strictly adhere to D.R.Y.
- Never simply catch `Exception` unless explicitly adding an exception router or filter.
- Don't return errors back to the frontend via jsonify() unless there is a
  specific place that the frontend reads and displays the error in a usable
  manner. Otherwise just let the backend blow up with an exception so that it is
  obvious during testing.- Assume that exceptions are already handled in the blueprint and jsonfiy() is
  called with an error string and 5xx code.
- Never add redundant comments or doc strings that aren't already self-evident
  in the code.
- Don't use the class-based pytest pattern and instead use only module-level functions.
- Keep flask endpoints oriented around updating entries in database tables, not
  just adding a new endpoint for every application verb.
- For python enum items, keep only the first letter of each word capitalized. Do
  not capitalize all letters.
- Create a re-usable component or template whenever markup or logic is
  duplicated.
- Always use `black` to format all source files after changes.