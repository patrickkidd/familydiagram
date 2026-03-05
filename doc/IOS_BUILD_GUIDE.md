# iOS Build Guide

Guide for building the Personal app (Family Diagram) for iPhone simulator and TestFlight distribution.

## Architecture

The iOS build uses `pyqtdeploy` to bundle a Python 3.11 + PyQt5 app into a native iOS binary.
The pipeline: `pyqtdeploy-build` generates an Xcode project from `familydiagram.pdt`,
which is then built with `xcodebuild`.

**Key files:**
- `familydiagram.pdt` - pyqtdeploy project descriptor
- `sysroot/sysroot.toml` - cross-compilation sysroot config (Qt 5.15.2 for iOS, Python 3.11.6)
- `build/ios-config/` - iOS-specific Xcode config, icons, entitlements, Info.plist
- `bin/build.sh ios` - main build entry point
- `bin/run_ios_sim.sh` - simulator launcher
- `bin/build_ios_testflight.sh` - TestFlight archive & upload

## Prerequisites

### 1. Xcode (REQUIRED - currently missing on hurin)

Full Xcode.app is required (not just Command Line Tools):

```bash
# Install from Mac App Store or:
xcode-select --install  # CLI tools only - NOT sufficient
# Need full Xcode.app from https://developer.apple.com/xcode/

# After installing, set the active developer directory:
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer

# Accept license:
sudo xcodebuild -license accept

# Install iOS simulator runtimes:
xcodebuild -downloadPlatform iOS
```

### 2. iOS Sysroot (`sysroot/sysroot-ios-64`)

The iOS sysroot contains cross-compiled Python 3.11.6 + PyQt5 + dependencies for arm64.
This was previously built on Patrick's dev machine.

**To build from scratch** (takes several hours):

```bash
# Install pyqtdeploy
pip install pyqtdeploy==3.3.0

# Build the sysroot (cross-compiles everything for iOS)
cd sysroot
pyqtdeploy-sysroot --target ios-64 --verbose sysroot.toml
```

This builds:
- Python 3.11.6 (cross-compiled for arm64-ios)
- Qt 5.15.2 (iOS SDK, static)
- PyQt5 5.15.11 (cross-compiled bindings)
- SIP (abi v12)
- zlib 1.3.1
- All wheel dependencies (dateutil, sortedcontainers, xlsxwriter, six)

**Alternatively**, copy from Patrick's machine:
```bash
rsync -avz patrick@devmachine:~/dev/familydiagram/sysroot/sysroot-ios-64 sysroot/
```

### 3. Qt 5.15.2 iOS SDK

The `build.sh` expects Qt iOS tools on PATH at `../lib/Qt/5.15.2/ios/bin`.
For the sysroot-based build, qmake comes from `sysroot/sysroot-ios-64/Qt/bin/qmake`.

If using a pre-built Qt:
```bash
# Download Qt 5.15.2 iOS from qt.io installer
# Install to ../lib/Qt/5.15.2/ios/
```

### 4. pyqtdeploy

```bash
pip install pyqtdeploy==3.3.0
# or
uv pip install pyqtdeploy==3.3.0
```

### 5. Apple Developer Account

- Team ID: `8KJB799CU7`
- Bundle ID: `com.vedanamedia.familydiagram`
- Signing identity: `Apple Development: Patrick Stinson (J5VYQMUDH6)` (dev) / `Apple Distribution` (release)
- Provisioning profiles need to be current in Apple Developer portal
- For TestFlight: App Store Connect access + API key

### 6. iPhone Simulator

```bash
# List available simulators:
xcrun simctl list devices available | grep iPhone

# Create iPhone 14 simulator if not present:
xcrun simctl create "iPhone 14" "com.apple.CoreSimulator.SimDeviceType.iPhone-14" \
    "com.apple.CoreSimulator.SimRuntime.iOS-17-5"
```

## Build Commands

### Debug (simulator)

```bash
# Generate Xcode project and open it:
bin/build.sh ios

# Or build for simulator from CLI:
bin/build.sh ios-sim

# Launch in simulator:
bin/run_ios_sim.sh
```

### Release (TestFlight)

```bash
# Full archive + TestFlight upload:
bin/build_ios_testflight.sh

# Or step by step:
bin/build.sh ios-release          # Archive
bin/build_ios_testflight.sh       # Upload to TestFlight
```

## Environment Variables (for release builds)

| Variable | Description |
|----------|-------------|
| `FD_BUILD_PEPPER` | App encryption pepper |
| `FD_BUILD_PROVISIONING_PROFILE_BASE64` | Base64-encoded provisioning profile |
| `FD_BUILD_CERTIFICATE_BASE64` | Base64-encoded signing certificate |
| `FD_BUILD_PRIVATE_KEY_BASE64` | Base64-encoded private key |
| `FD_BUILD_CERTIFICATE_PASSWORD` | Keychain password |
| `FD_BUILD_AC_AUTH_KEY_ID` | App Store Connect API key ID |
| `FD_BUILD_AC_AUTH_KEY_BASE64` | Base64-encoded API key (.p8) |
| `FD_BUILD_AC_AUTH_KEY_ISSUER` | App Store Connect issuer ID |

## Blocker Status (as of 2026-03-04, hurin Mac Mini M4)

| Prerequisite | Status | Action Required |
|---|---|---|
| Xcode.app | MISSING - only CLI tools installed | Install full Xcode from App Store |
| iOS Simulator runtimes | MISSING | Install after Xcode (`xcodebuild -downloadPlatform iOS`) |
| `sysroot-ios-64` | MISSING | Build with pyqtdeploy-sysroot or copy from dev machine |
| `sysroot-macos-64` | MISSING | Build or copy (needed for _pkdiagram SIP build step) |
| Qt 5.15.2 iOS SDK | MISSING | Included in sysroot build, or install separately |
| `pyqtdeploy` | NOT INSTALLED | `pip install pyqtdeploy==3.3.0` |
| `qmake` | NOT INSTALLED | Comes with sysroot or Qt SDK |
| Apple signing certs | UNKNOWN | Check Apple Developer portal |
| Provisioning profiles | LIKELY STALE | Regenerate in Apple Developer portal |

### Critical Path

1. Install Xcode.app (biggest blocker - ~12GB download)
2. Build or obtain iOS sysroot (several hours if from source)
3. Run `bin/build.sh ios` to generate Xcode project
4. Build for simulator to validate
5. Configure signing for device/TestFlight
6. Archive and upload via `bin/build_ios_testflight.sh`

## Troubleshooting

### "unable to find utility simctl"
Full Xcode.app not installed, or `xcode-select` not pointing to it.

### PrintSupport errors on iOS
The build script strips PrintSupport references (not available on iOS).
If you see linker errors about QtPrintSupport, check that the sed
commands in `build.sh` ran correctly.

### Code signing failures
Ensure provisioning profiles match the bundle ID and team ID.
For simulator builds, code signing can be set to "Automatically manage signing"
in Xcode.
