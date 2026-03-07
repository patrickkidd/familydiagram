#!/bin/bash
# Build _pkdiagram C++ SIP extension on Linux (headless server)
#
# Prerequisites (one-time setup):
#   1. Qt 5.15.2 installed via aqtinstall at ~/.openclaw/qt/
#   2. Python 3.12 dev headers at ~/.openclaw/python-headers/
#   3. OpenGL headers + libs at ~/.openclaw/python-headers/GL/ and ~/.openclaw/lib/
#
# One-time setup commands:
#   # Install aqtinstall and download Qt 5.15.2
#   uv pip install aqtinstall --python .venv/bin/python
#   .venv/bin/aqt install-qt linux desktop 5.15.2 gcc_64 --outputdir ~/.openclaw/qt
#
#   # Get Python dev headers (no sudo needed)
#   mkdir -p /tmp/pydeb && cd /tmp/pydeb
#   apt-get download libpython3.12-dev
#   dpkg-deb -x libpython3.12-dev*.deb extracted/
#   mkdir -p ~/.openclaw/python-headers
#   cp -r extracted/usr/include/python3.12/* ~/.openclaw/python-headers/
#   cp -r extracted/usr/include/x86_64-linux-gnu ~/.openclaw/python-headers/
#
#   # Get OpenGL headers and libs (no sudo needed)
#   apt-get download libgl-dev libglx-dev libgl1-mesa-dev
#   for f in libgl*.deb; do dpkg-deb -x "$f" gl_extracted/; done
#   cp -r gl_extracted/usr/include/GL ~/.openclaw/python-headers/
#   cp -r gl_extracted/usr/include/KHR ~/.openclaw/python-headers/
#
#   apt-get download libgl1 libglx0 libglx-mesa0 libglvnd0
#   for f in libgl1*.deb libglx0*.deb libglx-mesa0*.deb libglvnd0*.deb; do dpkg-deb -x "$f" gl_runtime/; done
#   mkdir -p ~/.openclaw/lib
#   cp gl_runtime/usr/lib/x86_64-linux-gnu/libGL.so.1.7.0 ~/.openclaw/lib/
#   cp gl_runtime/usr/lib/x86_64-linux-gnu/libGLdispatch.so.0.0.0 ~/.openclaw/lib/
#   cp gl_runtime/usr/lib/x86_64-linux-gnu/libGLX.so.0.0.0 ~/.openclaw/lib/
#   cp gl_runtime/usr/lib/x86_64-linux-gnu/libGLX_mesa.so.0.0.0 ~/.openclaw/lib/
#   cd ~/.openclaw/lib
#   ln -sf libGL.so.1.7.0 libGL.so.1 && ln -sf libGL.so.1 libGL.so
#   ln -sf libGLdispatch.so.0.0.0 libGLdispatch.so.0
#   ln -sf libGLX.so.0.0.0 libGLX.so.0
#   ln -sf libGLX_mesa.so.0.0.0 libGLX_mesa.so.0

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
WORKSPACE_DIR="$(dirname "$REPO_DIR")"
VENV_DIR="$WORKSPACE_DIR/.venv"
QT_DIR="$HOME/.openclaw/qt/5.15.2/gcc_64"
PYTHON_HEADERS="$HOME/.openclaw/python-headers"
GL_LIB_DIR="$HOME/.openclaw/lib"

echo "=== Building _pkdiagram C++ SIP extension ==="
echo "Repo:           $REPO_DIR"
echo "Qt:             $QT_DIR"
echo "Python headers: $PYTHON_HEADERS"
echo "GL libs:        $GL_LIB_DIR"
echo ""

# Verify prerequisites
if [ ! -f "$QT_DIR/bin/qmake" ]; then
    echo "ERROR: Qt 5.15.2 not found at $QT_DIR"
    echo "Run: .venv/bin/aqt install-qt linux desktop 5.15.2 gcc_64 --outputdir ~/.openclaw/qt"
    exit 1
fi

if [ ! -f "$PYTHON_HEADERS/Python.h" ]; then
    echo "ERROR: Python headers not found at $PYTHON_HEADERS"
    echo "See setup instructions in this script header."
    exit 1
fi

if [ ! -f "$GL_LIB_DIR/libGL.so" ]; then
    echo "ERROR: GL libraries not found at $GL_LIB_DIR"
    echo "See setup instructions in this script header."
    exit 1
fi

# Clean previous build
rm -rf "$REPO_DIR/_pkdiagram/build"

# Build
cd "$REPO_DIR/_pkdiagram"
"$VENV_DIR/bin/sip-build" \
    --qmake "$QT_DIR/bin/qmake" \
    --qmake-setting "INCLUDEPATH += $PYTHON_HEADERS" \
    --qmake-setting "LIBS += -L$GL_LIB_DIR"

# Install to site-packages
cp "$REPO_DIR/_pkdiagram/build/_pkdiagram/_pkdiagram.cpython-312-x86_64-linux-gnu.so" \
   "$VENV_DIR/lib/python3.12/site-packages/"

echo ""
echo "=== Build complete ==="
echo "Installed to: $VENV_DIR/lib/python3.12/site-packages/"
echo ""
echo "To test:"
echo "  LD_LIBRARY_PATH=$QT_DIR/lib:$GL_LIB_DIR:\$LD_LIBRARY_PATH \\"
echo "  $VENV_DIR/bin/python -c 'from _pkdiagram import CUtil; print(CUtil.operatingSystem())'"
