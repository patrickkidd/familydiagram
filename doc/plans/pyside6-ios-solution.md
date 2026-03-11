# PySide6 iOS: The QtRuntime.framework Solution

## The Problem

PySide6 on iOS has been blocked for 8+ months by duplicate symbols. Here's why:

1. **iOS requires all dynamic code in `.framework` bundles** (since iOS 8, App Store enforced)
2. **Python extension modules must be separate `.framework` bundles** (CPython 3.13+ PEP 730)
3. **Qt 6 on iOS ships ONLY as static `.a` libraries** (enforced by a `FATAL_ERROR` in CMake)
4. **Each PySide6 module is a separate dynamic `.framework`** that wraps one Qt module

When PySide6 modules (QtCore.abi3.so, QtGui.abi3.so, QtWidgets.abi3.so) are built as
separate dynamic frameworks and linked against Qt's static `.a` files, each framework
**absorbs its own copy** of the Qt code it depends on. When the app loads multiple
frameworks at runtime, identical Qt symbols exist in multiple frameworks → duplicate
symbol errors (specifically: duplicate ObjC classes like `_OBJC_CLASS_$_RunLoopModeTracker`,
`_OBJC_CLASS_$_KeyValueObserver`, and `AppleUnifiedLogger::messageHandler`).

## Why the Qt Company Is Stuck

The WIP Gerrit change (651061, 16 patch sets, last updated 2026-01-26) reveals their
approach: build each PySide6 module as a shared `.so` that absorbs static Qt code, then
try to strip duplicate ObjC symbols post-link. This is fundamentally wrong — it's treating
a symptom rather than the architectural cause. They're trying to make "shared libs linking
static Qt" work on iOS, when the correct answer is to not embed static Qt into each module
at all.

The Qt Company has also been blocked by:
- **The `qt_main_wrapper` / `_main` symbol problem**: Qt's iOS platform plugin references
  `main()` at link time, which doesn't exist in a dynamic library
- **OpenGL/OpenGLES confusion**: Shiboken may parse desktop GL headers during cross-compilation
- **General static-only mindset**: Qt has enforced `BUILD_SHARED_LIBS=OFF` on iOS since Qt 6.0

## The Solution: QtRuntime.framework

**Create a single dynamic framework from Qt's static iOS libraries.** PySide6 modules link
against this ONE framework instead of absorbing static Qt code individually.

### Architecture

```
YourApp.app/
├── YourApp                          (host executable: CPython + main() + UIApplicationMain)
├── Frameworks/
│   ├── Python.framework/            (CPython 3.13+ XCFramework)
│   ├── QtRuntime.framework/         (ALL Qt static libs merged into ONE dynamic framework)
│   ├── libshiboken6.abi3.framework/ (links against QtRuntime + Python)
│   ├── libpyside6.abi3.framework/   (links against QtRuntime + libshiboken6 + Python)
│   ├── QtCore.abi3.framework/       (links against QtRuntime + libpyside6)
│   ├── QtGui.abi3.framework/        (links against QtRuntime + libpyside6)
│   ├── QtWidgets.abi3.framework/    (links against QtRuntime + libpyside6)
│   ├── QtQml.abi3.framework/        (links against QtRuntime + libpyside6)
│   ├── QtQuick.abi3.framework/      (links against QtRuntime + libpyside6)
│   └── ...
├── lib/python3.13/
│   └── (pure Python stdlib + app code + .fwork marker files)
└── Info.plist
```

**Key insight**: QtRuntime.framework is the ONLY place Qt native code exists. Every PySide6
module references it dynamically. Zero duplication. Zero duplicate symbols.

### The qt_main_wrapper Problem: Solved by Not Using It

Qt's `qt_main_wrapper` uses setjmp/longjmp to bounce between the iOS run loop and
`QEventLoop::exec()`. This is incompatible with Python (which owns the stack and has GC
state that would be corrupted by longjmp).

**Solution**: Use the `qt-inside-ios-native` pattern (github.com/kambala-decapitator/qt-inside-ios-native):

1. The host executable is a normal iOS app — it owns `main()` and calls `UIApplicationMain`
2. In `applicationDidFinishLaunching:`, the host starts CPython and runs the user's script
3. Python imports PySide6, creates `QApplication`
4. Qt detects `UIApplication` already exists, uses `QIOSEventDispatcher` (the non-jumping
   variant) which integrates with `CFRunLoop`
5. The qios platform plugin sees a running UIApplication and creates `QIOSIntegration` normally

This means:
- **No `-Wl,-e,_qt_main_wrapper`** entry point override
- **No setjmp/longjmp** stack manipulation
- **No `_main` symbol resolution** problem in the dynamic framework
- The qios platform plugin (`libqios.a`) is included in QtRuntime.framework with
  `-Wl,-U,_main` to leave the `main` reference unresolved (it won't be called)

### The OpenGL Problem: Solved by Exclusion + Correct Cross-Compilation

1. **Don't build PySide6's QtOpenGL module for iOS** (same as pyqtdeploy's
   `PyQt_Desktop_OpenGL` disabled). Qt 6 uses Metal via RHI on iOS — Python code never
   touches GL directly.
2. **Ensure shiboken uses the iOS Qt config** during header parsing so it doesn't try to
   parse desktop GL headers. The CMakeLists.txt already handles the `opengles2` feature
   check correctly — the issue is shiboken's Clang parser using the wrong sysroot.
3. **For QtGui's embedded OpenGL classes** (QOpenGLContext, QSurfaceFormat), the ES2
   variant headers are correct on iOS and should work if shiboken targets the right platform.

## Implementation Plan

### Phase 1: Validate the QtRuntime.framework Concept (1-2 days)

**Goal**: Prove that a dynamic framework built from Qt's static iOS libraries works.

```bash
# 1. Get Qt's iOS static libraries
# (From the official Qt 6.x iOS binary installation)
QT_IOS="/path/to/Qt/6.x/ios"

# 2. Check symbol visibility (CRITICAL first step)
nm -gU "$QT_IOS/lib/libQt6Core.a" | head -50
# If symbols show 'T' (global text), we're good
# If symbols show 't' (local text), we have a visibility problem

# 3. Create the dynamic framework
SDK=$(xcrun --sdk iphoneos --show-sdk-path)

mkdir -p QtRuntime.framework

clang++ -dynamiclib -arch arm64 \
  -isysroot "$SDK" \
  -miphoneos-version-min=16.0 \
  -install_name @rpath/QtRuntime.framework/QtRuntime \
  -o QtRuntime.framework/QtRuntime \
  -Wl,-force_load,"$QT_IOS/lib/libQt6Core.a" \
  -Wl,-force_load,"$QT_IOS/lib/libQt6Gui.a" \
  -Wl,-force_load,"$QT_IOS/lib/libQt6Widgets.a" \
  -Wl,-force_load,"$QT_IOS/lib/libQt6Qml.a" \
  -Wl,-force_load,"$QT_IOS/lib/libQt6Quick.a" \
  -Wl,-force_load,"$QT_IOS/lib/libQt6Network.a" \
  -Wl,-force_load,"$QT_IOS/lib/libQt6QuickWidgets.a" \
  -Wl,-force_load,"$QT_IOS/plugins/platforms/libqios.a" \
  -Wl,-U,_main \
  -framework UIKit -framework Foundation -framework CoreFoundation \
  -framework CoreGraphics -framework CoreText -framework QuartzCore \
  -framework Metal -framework ImageIO -framework Security \
  -framework AVFoundation -framework AudioToolbox \
  -framework SystemConfiguration -framework CoreMotion \
  -framework MobileCoreServices \
  -lz -lsqlite3 -lc++ \
  -Wl,-dead_strip

# 4. Create Info.plist for the framework
cat > QtRuntime.framework/Info.plist << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleIdentifier</key>
  <string>com.vedanamedia.qtruntime</string>
  <key>CFBundleExecutable</key>
  <string>QtRuntime</string>
  <key>CFBundleVersion</key>
  <string>6.9</string>
  <key>CFBundlePackageType</key>
  <string>FMWK</string>
  <key>MinimumOSVersion</key>
  <string>16.0</string>
</dict>
</plist>
PLIST

# 5. Verify it's a proper dynamic library
file QtRuntime.framework/QtRuntime
# Should show: "Mach-O 64-bit dynamically linked shared library arm64"

otool -L QtRuntime.framework/QtRuntime
# Should show: @rpath/QtRuntime.framework/QtRuntime (compatibility ...)

# 6. Check exported symbols
nm -gU QtRuntime.framework/QtRuntime | grep "QApplication" | head -5
# Should show Qt symbols are accessible
```

**If symbol visibility is a problem** (step 2 shows hidden symbols):

Option A: Build Qt from source with `-DCMAKE_CXX_VISIBILITY_PRESET=default`:
```bash
# Patch QtAutoDetectHelpers.cmake to remove the FATAL_ERROR for iOS
# Then configure:
cmake -S qt6 -B build-ios \
  -DCMAKE_SYSTEM_NAME=iOS \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=16.0 \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_CXX_VISIBILITY_PRESET=default \
  -DCMAKE_C_VISIBILITY_PRESET=default \
  -DQT_BUILD_EXAMPLES=OFF -DQT_BUILD_TESTS=OFF \
  -DINPUT_opengl=no \
  -G Ninja
```

Option B: Use `-Wl,-exported_symbols_list` with an auto-generated list:
```bash
# Extract all global symbols from the static libs
nm -gU libQt6Core.a libQt6Gui.a ... | awk '{print $3}' | sort -u > qt_exports.txt
# Use during framework creation:
clang++ -dynamiclib ... -Wl,-exported_symbols_list,qt_exports.txt
```

### Phase 2: Cross-Compile a Minimal PySide6 Module Against QtRuntime (2-3 days)

**Goal**: Build QtCore.abi3.so that links against QtRuntime.framework instead of static Qt.

This requires:
1. Cross-compile shiboken6-generator on macOS (host tool, already works)
2. Cross-compile libshiboken6 for iOS arm64, linking against QtRuntime.framework
3. Run shiboken to generate QtCore wrapper code (using iOS Qt headers)
4. Cross-compile the generated QtCore wrapper, linking against QtRuntime.framework
5. Package as QtCore.abi3.framework

The key CMake change in PySide6's build:
```cmake
# Instead of finding static Qt libs:
# find_package(Qt6 COMPONENTS Core REQUIRED)  # finds static .a

# Link against QtRuntime.framework:
target_link_libraries(QtCore PRIVATE
  "-F${CMAKE_CURRENT_SOURCE_DIR}/../QtRuntime"
  "-framework QtRuntime"
)
```

### Phase 3: Build the Host App + Integration Test (2-3 days)

**Goal**: A working iOS app that runs Python + PySide6 with a Qt Quick UI.

Host app (Objective-C):
```objc
// main.m
#import <UIKit/UIKit.h>
#import "AppDelegate.h"

int main(int argc, char *argv[]) {
    @autoreleasepool {
        return UIApplicationMain(argc, argv, nil,
            NSStringFromClass([AppDelegate class]));
    }
}

// AppDelegate.m
#import <Python/Python.h>

@implementation AppDelegate
- (BOOL)application:(UIApplication *)application
    didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {

    // Set up Python paths
    NSString *resourcePath = [[NSBundle mainBundle] resourcePath];
    NSString *pythonHome = [resourcePath stringByAppendingPathComponent:@"lib"];
    setenv("PYTHONHOME", [pythonHome UTF8String], 1);

    // Initialize Python
    Py_Initialize();

    // Run the user's app
    FILE *fp = fopen([[resourcePath stringByAppendingPathComponent:@"app.py"]
                      UTF8String], "r");
    PyRun_SimpleFile(fp, "app.py");
    fclose(fp);

    return YES;
}
@end
```

User's Python app:
```python
# app.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl

app = QApplication(sys.argv)
view = QQuickView()
view.setSource(QUrl("qrc:/main.qml"))
view.show()
app.exec()
```

### Phase 4: Adapt for Family Diagram (1-2 weeks)

1. Add all needed Qt modules to QtRuntime.framework (QtSensors, QtTextToSpeech, etc.)
2. Build all needed PySide6 modules
3. Port the existing pyqtdeploy-based build scripts to the new architecture
4. Handle QML resource bundling (QRC files → app bundle)
5. Handle the _pkdiagram C++ extension module
6. Code signing, provisioning, App Store submission

## Risk Assessment

### Risk 1: Symbol Visibility (HIGH priority, verify FIRST)
- **Problem**: Qt's iOS static libs may be compiled with `-fvisibility=hidden` and no export
  macros, making symbols invisible when merged into a dynamic framework
- **Likelihood**: Medium. Qt typically only uses hidden visibility for shared builds, but
  this needs empirical verification
- **Mitigation**: Check with `nm -gU`. If hidden, build Qt from source with default visibility
  or use `-exported_symbols_list`
- **Verification**: `nm -gU libQt6Core.a | grep -c " T "` — if count > 0, symbols are exported

### Risk 2: QIOSEventDispatcher Without qt_main_wrapper (MEDIUM)
- **Problem**: Qt's non-jumping event dispatcher may not integrate correctly with Python's
  event loop on the main thread
- **Likelihood**: Low. The `qt-inside-ios-native` project proves this pattern works for C++ apps.
  Python adds complexity but doesn't fundamentally change the run loop integration.
- **Mitigation**: Test early. If QIOSEventDispatcher doesn't work, consider a thin native
  shim that handles the run loop and calls Python via a callback.

### Risk 3: Shiboken Cross-Compilation for iOS (MEDIUM)
- **Problem**: Shiboken must parse iOS Qt headers on a macOS host. The Clang parser may not
  correctly detect the target platform's Qt configuration.
- **Likelihood**: Medium. This is a known issue (PYSIDE-802) but the Qt Company has made
  progress on it for Android, which has the same cross-compilation challenge.
- **Mitigation**: Use `--sysroot` and platform-specific Clang flags when invoking shiboken.
  The Android build path in PySide6 already demonstrates how to do this.

### Risk 4: Qt Plugin Loading (LOW)
- **Problem**: Qt needs to find the qios platform plugin. In static builds, `Q_IMPORT_PLUGIN`
  handles this. In our architecture, qios is inside QtRuntime.framework.
- **Likelihood**: Low. Since qios is linked into QtRuntime.framework (via `-force_load`), its
  static initialization code will register the plugin when the framework is loaded.
- **Mitigation**: If auto-registration fails, explicitly register via
  `QT_QPA_PLATFORM_PLUGIN_PATH` or call `Q_IMPORT_PLUGIN` from shiboken init code.

### Risk 5: App Store Rejection (LOW)
- **Problem**: Apple might reject a large dynamic framework or flag dlopen usage.
- **Likelihood**: Very low. Dynamic frameworks are the standard iOS mechanism. Many production
  apps ship large frameworks (Flutter, React Native, Unity). Python's AppleFrameworkLoader
  uses dlopen on signed bundle content, which is explicitly permitted.
- **Mitigation**: Ensure all frameworks are properly code-signed and have correct Info.plist.

## Comparison with Alternatives

| Approach | Effort | Risk | Maintainability | Upstream Contribution |
|----------|--------|------|-----------------|----------------------|
| **QtRuntime.framework (this proposal)** | Medium | Medium | Good — decoupled from Qt build | High — solves the root cause |
| Wait for PySide6 6.11/6.12 | Zero | High (timeline risk) | N/A | N/A |
| pyqtdeploy hack (OforOshima) | High | High | Poor — fragile patches | None |
| Stay on PyQt5/Qt5 | Zero | Low | Declining (Qt5 EOL) | None |
| Patch Qt for dynamic iOS builds | Very High | Very High | Poor — deep Qt surgery | High but years of work |

## Contributing Back to Qt Company

If this approach works, it can be contributed to the PySide6 project:

1. **Immediate value**: Share the QtRuntime.framework build script and the architectural
   insight that merging static Qt into one dynamic framework eliminates duplicate symbols.
   This bypasses the need to build Qt itself as dynamic on iOS.

2. **Integration point**: The PySide6 build system could automate QtRuntime.framework creation
   as part of `pyside6-deploy --target ios`. The static Qt iOS SDK is the input; the dynamic
   framework is a build artifact.

3. **PYSIDE-2352**: Post findings to the Jira ticket and the Gerrit review (651061).

4. **Qt Forum**: Post to the existing thread (forum.qt.io/topic/161694) that you started.

5. **Long-term**: Push for QTBUG-85974 (dynamic Qt for iOS) to be prioritized, which would
   make QtRuntime.framework unnecessary. But QtRuntime.framework works TODAY with the
   existing Qt iOS SDK, while dynamic Qt builds require deep changes to Qt's build system
   and platform plugin architecture.

## Summary

The Qt Company has been trying to make "shared PySide6 modules + static Qt" work, which is
architecturally impossible without duplicate symbols. The solution is a thin layer that
converts Qt's static iOS libraries into a single dynamic framework (QtRuntime.framework)
that all PySide6 modules link against. This:

- Eliminates duplicate symbols by construction (Qt code exists in exactly ONE place)
- Avoids patching Qt's build system (uses official static iOS SDK as input)
- Avoids the qt_main_wrapper/setjmp/longjmp problem (host app owns lifecycle)
- Is App Store compliant (dynamic frameworks are standard since iOS 8)
- Can be contributed back to the Qt Company as the missing architectural piece

The primary risk is symbol visibility in Qt's static libraries, which must be verified
empirically before proceeding.
