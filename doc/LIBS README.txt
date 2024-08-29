WINDOWS CD
==============================================================
scp bin/setup_windows.ps1 windows11:C:\\Users\\patrick\\ && ssh windows11 "powershell -ExecutionPolicy Bypass -File C:\\Users\\patrick\\setup_windows.ps1"

MACOS DEV
==============================================================
- Install Qt from qt.io installer
- brew install python3 direnv pyenv
    - https://blog.adam-uhlir.me/python-virtual-environments-made-super-easy-with-direnv-307611c3a49a
- pyenv install $PYTHON_VERSION
    - Possibly have to use this command line (use patch for any version):
    - CFLAGS="-I$(brew --prefix openssl)/include -I$(brew --prefix bzip2)/include -I$(brew --prefix readline)/include -I$(xcrun --show-sdk-path)/usr/include" LDFLAGS="-L$(brew --prefix openssl)/lib -L$(brew --prefix readline)/lib -L$(brew --prefix zlib)/lib -L$(brew --prefix bzip2)/lib" \
pyenv install --patch 3.7.8 < <(curl -sSL https://github.com/python/cpython/commit/8ea6353.patch\?full_index\=1)
- familydiagram/.envrc:
    export PATH="$HOME/dev/familydiagram/vendor/lib/Qt/5.15.1/clang_64/bin:$PATH"
    layout_python3
    use python 3.7.8
- ~/.direnvrc:
  local python_root=$(pyenv root)/versions/$1
    load_prefix "$python_root"
    if [[ -x "$python_root/bin/python" ]]; then
        layout python "$python_root/bin/python"
    else
        echo "Error: $python_root/bin/python can't be executed."
        exit
    fi
  }
- cd familydiagram # loads direnv + pyenv
- env LDFLAGS="-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib" pip install psycopg2
- Install `act` for testing github workflows locally.
    - brew install act
    - https://github.com/nektos/act
- brew install create-dmg

- Optional: Build from git
  - perl init-repository -f --module-subset=default,-qt3d,-qtactiveqt,-qtcanvas3d,-qtgamepad,-qtlocation,-qtremoteobjects,-qtserialbus,-qtserialport,-qtspeech,-qtwayland,-qtwebchannel,-qtwebengine,-qtwebglplugin,-qtwebsockets,-qtwebview,-qtlottie,-qtdatavis3d,-qtconnectivity,-qtcharts,-qtandroidextras,-qtdoc,-qtnetworkauth,-qtqa,-qtrepotools,-qtscxml,-qtsensors,-qttools,-qttranslations,-qtwinextras,-qtx11extras,-qtxmlpatterns,-qtmultimedia,-qtpurchasing


WINDOWS DEV
==============================================================
- Install git from git-scm.org
    - Includes shell tools like find, which, grep, ls, etc
- git clone git@github.com:patrickkidd/familydiagram.git
- git submodule update --init
    - Pulls in all code for all submodules
- Install appropriate Python 3 version in default location using web installer from python.org
    - Add .\bin to PATH (if not already in bin\dev-console.bat)
- Install appropriate Qt version from qt.io web installer
    - No MinGW, CMakeUtils, etc
    - Add .\bin to PATH
    - Required to get qmake, headers, libs, etc for _pkdiagram, _vedana extensions
- Install VS Community MSBuild Tools from Visual Studio 2019 Installer (latest v142 + v140, C++ CMake Tools)
- SET Computer\HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled
    - https://github.com/dotnet/msbuild/issues/53
- Add familydiagram\bin\PyQt Command Prompt.lnk to task bar (loads VS Community x64 vars).
- pip install sip PyQt-Builder pyqt5 pyqtdeploy
- cmake -G "NMake Makefiles" .
- nmake
- python main.py


WINDOWS RELEASE SYSROOT
==============================================================
- Follow `WINDOWS DEV` instructions above
- Install StrawberryPerl (required to build OpenSSL)
- Install python 2.7
- pyqtdeploy-sysroot --verbose sysroot.toml


LINUX SERVER PRODUCTION
===============================================================
- Build qt in ./lib/qt-xxxxx with prefix set to ./lib/Qt-5.x.x, and install
  - ./configure -prefix $SYSROOT -opensource release -confirm-license -nomake examples -nomake tests
  - cd qtbase
  - make module-qtbase
  - make install
- apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl direnv
- git clone https://github.com/pyenv/pyenv.git ~/.pyenv
- export PYENV_ROOT="$HOME/.pyenv
- export PATH="$PYENV_ROOT/bin:$PATH"
- if command -v pyenv 1>/dev/null 2>&1; then
    eval "$(pyenv init -)"
  fi
- sudo apt install libgl1-mesa-dev


IOS RELEASE SYSROOT
=============================================================
- Fix mkspecs/features/toolchain.prf to avoid Qt buig where platforms are confused.
    - https://bugreports.qt.io/browse/QTBUG-86718
    - https://codereview.qt-project.org/c/qt/qtbase/+/314636/3/mkspecs/features/toolchain.prf#187






LINUX DEV
====================================
- sudo apt-get install -y build-essential postgresql libpq-dev cmake libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl git 
- git clone https://github.com/pyenv/pyenv.git ~/.pyenv
- echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
- echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
- 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile
- ~/.direnvrc
use_python() {
  local python_root=$(pyenv root)/versions/$1
  load_prefix "$python_root"
  if [[ -x "$python_root/bin/python" ]]; then
    layout python "$python_root/bin/python"
  else
    echo "Error: $python_root/bin/python can't be executed."
    exit
  fi
}
- install linux qt installer in familydiagram/3rdparty/Qt; add bin to PATH
- pip install -r requirements.txt




BUILD INSTRUCTIONS
==============================================================

EDIT BASH PROFILE:

    # call the appropriate one before building/using each SYSROOT
    function pyqt-dev {
        export SYSROOT=$HOME/dev/vendor/pyqt-sysroot-dev
        export DYLD_LIBRARY_PATH=$SYSROOT/lib
        export PATH=$SYSROOT/bin:$PATH
    }
    function pyqt-ios {
        export SYSROOT=$HOME/dev/vendor/pyqt-sysroot-ios-64
        export DYLD_LIBRARY_PATH=$SYSROOT/lib
        export PATH=$SYSROOT/bin:$PATH
    }
    function pyqt-simulator {
        export SYSROOT=$HOME/dev/vendor/pyqt-sysroot-iphonesimulator
        export DYLD_LIBRARY_PATH=$SYSROOT/lib
        export PATH=$SYSROOT/bin:$PATH
    }
    function pyqt-osx {
        export SYSROOT=$HOME/dev/vendor/pyqt-sysroot-osx-64
        export DYLD_LIBRARY_PATH=$SYSROOT/lib
        export PATH=$SYSROOT/bin:$PATH
    }


IF USING qt5 from Git
===================================================

    - git clone https://code.qt.io/qt/qt5.git ~/dev/vendor/pyqt-sysroot-base/src/qt5-src
    - ./init-repository --module-subset=qtbase,qtdeclarative,qtgraphicaleffects,qtimageformats,qtlocation,qtmacextras,qtpurchasing,qtquickcontrols,qtquickcontrols2
    - ./init-repository --module-subset=default,-qt3d,-qtactiveqt,-qtcanvas3d,-qtgamepad,-qtremoteobjects,-qtlocation,-qtpositioning,-qtscript,-qtserialbus,-qtserialport,-qtspeech,-qtwayland,-qtwebchannel,-qtwebengine,-qtwebglplugin,-qtwebsockets,-qtwebview,-qtlottie,-qtdatavis3d,-qtconnectivity,-qtcharts,-qtandroidextras,-qtdoc,-qtnetworkauth,-qtqa,-qtrepotools,-qtscxml,-qtsensors,-qtsvg,-qttools,-qttranslations,-qtwinextras,-qtx11extras,-qtxmlpatterns,-qtmultimedia,-qtpurchasing


BUILD QT 6

macOS
    - cmake -GNinja -DCMAKE_INSTALL_PREFIX=/Users/patrick/dev/lib/Qt-6.4.0 -DBUILD_qtactiveqt=OFF -DBUILD_qtcanvas3d=OFF -DBUILD_qtgamepad=OFF -DBUILD_qtremoteobjects=OFF -DBUILD_qtscript=OFF -DBUILD_qtspeech=OFF -DBUILD_qtvirtualkeyboard=OFF -DBUILD_qtwayland=OFF -DBUILD_qtwebview=OFF -DBUILD_qtwebengine=OFF -DBUILD_qtwebchannel=OFF -DBUILD_qtwebglplugin=OFF -DBUILD_qtwebsockets=OFF -DBUILD_qtserialbus=OFF -DBUILD_qtserialport 




CREATE BUILD ENVIRONMENTS


sysroot-dev (debug):
    - export SYSROOT=/Users/patrick/dev/vendor/sysroot-dev # *DO NOT USE* `pyqt-dev`; causes compiler errors
    - mkdir -p $SYSROOT/build $SYSROOT/bin && cd $SYSROOT/build
    - export PATH=$SYSROOT/bin:$PATH
    - openssl (ubuntu)
        - config && make install
    - Qt:
        - tar zxf ../../src/qt-everywhere-src-5.12.3.tar.xz
        - cd qt-everywhere-src-5.12.3
        - (for qt-5.12.0) cp ../../src/src_plugins_platforms_cocoa_qcocoahelpers.mm qtbase/src/plugins/platforms/cocoa/qcocoahelpers.mm
        - ./configure -opensource -confirm-license -debug -no-framework -nomake examples -nomake tests -prefix $SYSROOT -skip qtactiveqt -skip qtcanvas3d -skip qtgamepad -skip qtremoteobjects -skip qtscript -skip qtspeech -skip qtvirtualkeyboard -skip qtwayland -skip qtwebview -skip qtwebengine
        - # ./configure -prefix $SYSROOT -opensource release -confirm-license -nomake examples -nomake tests -skip qtactiveqt -skip qtcanvas3d -skip qtgamepad -skip qtremoteobjects -skip qtscript -skip qtspeech -skip qtvirtualkeyboard -skip qtwayland -skip qtwebview -skip qtwebengine -skip qtwebchannel -skip qtwebglplugin -skip qtwebsockets -skip qtserialbus -skip qtserialport 
        - make -j10 && make -j10 install
    - Python:
        - tar zxf ../../src/Python-3.6.4-patched.tgz
        - cd Python-3.6.4-patched
        - export CFLAGS="-I$(brew --prefix openssl)/include -I$(xcrun --show-sdk-path)/usr/include -Wno-nullability-completeness -Wno-strict-prototypes"
        - export LDFLAGS="-L$(brew --prefix openssl)/lib -I$(xcrun --show-sdk-path)/usr/lib"
        - uncomment/set SSL chunk in Modules/Setup.dist to look like this (simply uncomment on ubuntu):
            # Socket module helper for socket(2)
            _socket socketmodule.c

            # Socket module helper for SSL support; you must comment out the other
            # socket line above, and possibly edit the SSL variable:
            SSL=/usr/local/Cellar/openssl/1.0.2r/
            _ssl _ssl.c \
            -DUSE_SSL -I$(SSL)/include -I$(SSL)/include/openssl \
            -L$(SSL)/lib -lssl -lcrypto
        - ./configure --prefix=$SYSROOT -with-ensurepip=install --with-system-expat --with-pydebug # need to try to build with debug flag
        - make -j10 && make -j10 install
        - export PATH=$SYSROOT/bin:$PATH
        - cd $SYSROOT/bin && ln -s python3 python && ln -s pip3 pip
        - $SYSROOT/bin/pip install --upgrade pip
    - Python (Windows):
        - PCBuild\build.bat
    - sip:
        - tar zxvf ../../src/sip-4.19.17.tar.gz && cd sip-4.19.17/
        - python configure.py --sip-module PyQt5.sip --debug --sysroot=$SYSROOT
        - make -j10 && make -j10 install
    - PyQt:
        - tar zxf ../../src/PyQt5_gpl-5.12.2.tar.gz && cd PyQt5_gpl-5.12.2
        - # comment out waitForEvents() in qtestmouse.sip if PyQt5-5.10.1 and Qt-5.11.0
        - python configure.py --enable QtCore --enable QtGui --enable QtWidgets --enable QtPrintSupport --enable QtNetwork --enable QtQuick --enable QtQuickWidgets --enable QtLocation --enable QtQml --enable QtPositioning --enable QtMacExtras --enable QtTest --concatenate -b $SYSROOT/bin --qmake `which qmake` --no-designer-plugin --no-qml-plugin --debug  --confirm-license
        - # python configure.py --enable=QtCore --enable=QtGui --enable=QtWidgets --enable QtPrintSupport --enable QtNetwork --enable QtQuick --enable QtQuickWidgets --enable QtLocation --enable QtQml --enable QtPositioning --enable QtMacExtras --enable QtTest --enable QtWebEngineWidgets --enable QtWebEngineCore --enable QtWebChannel --concatenate -b $SYSROOT/bin --qmake `which qmake` --no-designer-plugin --no-qml-plugin --debug  --confirm-license
        - make -j12 && make -j12 install
    - PyQtPurchasing
        - tar zxf ../../src/PyQtPurchasing_gpl-5.12.tar.gz && cd PyQtPurchasing_gpl-5.12
        - python configure.py --debug --sysroot=$SYSROOT
        - make -j12 install
    - QScintilla
        - tar zxf ../../src/QScintilla_gpl-2.11.1.tar.gz && cd QScintilla_gpl-2.11.1
        - cd Qt4Qt5 && qmake && make -j12 install
        - cd ../Python && python configure.py --pyqt=PyQt5 --debug && make -j12 install
    - Python packages
        - pip install profilehooks netifaces pytest pytest-qt requests flask pycallgraph python-dateutil coverage pytest-cov



sysroot-dev (linux; server)
    - export SYSROOT=~/vendor/sysroot-dev
    - mkdir -p $SYSROOT/build && cd $SYSROOT/build
    - Qt-5.12.0
        - sudo apt-get install libgles2-mesa-dev
        - ./configure -opensource -confirm-license -release -nomake examples -nomake tests -prefix $SYSROOT -skip qtactiveqt -skip qtcanvas3d -skip qtgamepad -skip qtremoteobjects -skip qtscript -skip qtspeech -skip qtvirtualkeyboard -skip qtwayland -skip qtwebview
        - # ./configure -opensource -confirm-license -release -nomake examples -nomake tests -prefix $SYSROOT -skip qtgui -skip qtwidgets -skip qtactiveqt -skip qtcanvas3d -skip qtgamepad -skip qtremoteobjects -skip qtscript -skip qtspeech -skip qtvirtualkeyboard -skip qtwayland -skip qtwebview -no-opengl 
    - Python
        - sudo apt-get install libssl-dev libffi-dev
        - ./configure --prefix=$SYSROOT -with-ensurepip=install --with-system-expat --with-ssl
    - sip
        - python configure.py --sip-module PyQt5.sip --sysroot=$SYSROOT
    - PyQt5
        - python configure.py --enable QtCore --enable QtGui --enable QtWidgets --concatenate -b $SYSROOT/bin --qmake `which qmake` --no-designer-plugin --no-qml-plugin --no-python-dbus --verbose --confirm-license --disable-feature=PyQt_OpenGL --disable-feature PyQt_Desktop_OpenGL
        

sysroot-win-32 (via pyqtdeploy-sysroot)
    - Install ActivePerl (required by openssl build)
    - Install Python-2.7 using binary installer (required by pyqtdeploy)
    - http://www.nasm.us/pub/nasm/releasebuilds/2.13.03/win64/nasm-2.13.03-installer-x64.exe
    - pyqtdeploy-sysroot --source src --target win-32 --verbose ..\pkdiagram\sysroot.json

sysroot-dev-win-32:
	- mkdir sysroot-dev-win-32\build && cd sysroot-dev-win-32\build
    - set CL=/MP8
    - Qt
        - Install binaries to sysroot-dev-win-32\Qt-x.y.z
    - Python
        - Install binaries to sysroot-dev-win-32\Python-x.y.z
        - Copy libcrypt-1.dll, libssl-1.dll from openssl-1.1.1e.zip
    - sip
        - tar xf ..\..\src\sip-4.12.0.tar.gz
        - python configure.py --sip-module=PyQt5.sip
        - nmake install
    - PyQt5
        - tar xf ..\..\src\PyQt5-5.y.z.tar.gz
        - python configure.py --enable QtCore --enable QtGui --enable QtWidgets --enable QtQuick --enable QtQuickWidgets --enable QtQml --enable QtNetwork --enable QtPrintSupport --enable QtTest --concatenate --no-designer-plugin --no-qml-plugin --confirm-license
        - nmake install
    - PyQtPurchasing
        - tar xf ..\..\src\PyQtPurchasing-x.y.tar.gz
        - python configure.py
        - nmake install



    - PyQt5
        - tar xf ..\..\src\PyQt5_gpl-5.11.3.tar.gz
        - edit configure.py::add_sip_h_directives():
            - pro_lines.append('INCLUDEPATH += %s' % qmake_quote(self.py_inc_dir)+'\..\PC')
        - edit congigure.py::HostPythonConfiguration.__init__
            - self.lib_dir = base_prefix + '\\PCBuild\\amd64'
        - python_d configure.py --enable QtCore --enable QtGui --enable QtWidgets --enable QtPrintSupport --enable QtNetwork --enable QtQuick --enable QtQuickWidgets --enable QtLocation --enable QtQml --enable QtPositioning --enable QtWinExtras --enable QtTest --concatenate --no-designer-plugin --no-qml-plugin --debug --verbose --confirm-license
    - http://www.nasm.us/pub/nasm/releasebuilds/2.13.03/win64/nasm-2.13.03-installer-x64.exe
	- tar zxf ..\..\src\sip-4.19.13.tar.gz
	- tar zxf ..\..\src\PyQt5_gpl-5.11.3.tar.gz
	- _cutil:
		- delete dev\pkdiagram\_cutil\.qmake.stash
		- python configure.py --pyqt-sipdir=Z:\dev\vendor\sysroot-dev-win-32\build\PyQt5_gpl-5.11.3\sip --sip-incdir=Z:\dev\vendor\sysroot-dev-win-32\build\sip-4.19.13\sipliber

sysroot-win32:
    - Either ensure "-opensource" is in qt source filename or edit pyqtdeploy/sysroot/plugins/qt5.py to force "-opensource" license.
    - use pyqtdeploy-sysroot



macos-64:
    - SYSROOT
        - mkdir -p $SYSROOT/build
    - Qt:
        - cd $SYSROOT/build && makedir qt5
        - ../../../pyqt-sysroot-base/src/qt5/qtbase/configure -opensource -confirm-license -nomake examples -nomake tests -prefix $PWD -static
        - make install -j10
    - Python:
        - pyqtdeploycli --package python --target osx-64 configure
        - qmake SYSROOT=$SYSROOT
        - make -j10; make install
        - mkdir -p $SYSROOT/bin
        - cd $SYSROOT/bin
        - ln -s ../../pyqt-sysroot-dev/bin/python* .
        - ln -s ../build/qt5/bin/qmake .
        - pyqtdeploycli --package python --target osx-64 configure && qmake SYSROOT=$SYSROOT && make -j10 && make install
    - sip:
        - pyqtdeploycli --package sip --target osx-64 configure
        - python configure.py --static --sysroot=$SYSROOT --use-qmake --configuration=sip-osx.cfg
        - qmake
        - cp sipgen/sip ../../bin # ?????
    - PyQt:
        - pyqtdeploycli --package pyqt5 --target osx-64 configure
        - python configure.py --static --sysroot=$SYSROOT --no-qsci-api --no-designer-plugin --no-qml-plugin --configuration=pyqt5-osx.cfg -b $SYSROOT/bin --enable=QtCore --enable=QtGui --enable=QtNetwork --enable=QtWidgets --enable=QtPrintSupport --concatenate --qmake $SYSROOT/build/qt5/bin/qmake -u  --confirm-license
        - make -j10; make install
        - ## for i in `find . -name "*_debug.a"`; do ln -sf `echo $i | sed "s/.*\///"` "${i/_debug/}"; done # if doing a debug build
        - ## for i in `find . -name "*_debug.la"`; do ln -sf `echo $i | sed "s/.*\///"` "${i/_debug/}"; done # if doing a debug build


ios-64 (debug, release):
    - SYSROOT
        - mkdir -p $SYSROOT/build $SYSROOT/bin
        - ln -s $SYSROOT/../pyqt-sysroot-dev/bin/pyqtdeploy* $SYSROOT/bin
        - ln -s $SYSROOT/../pyqt-sysroot-dev/bin/python* $SYSROOT/bin
        - ln -s $SYSROOT/../pyqt-sysroot-dev/bin/sip $SYSROOT/bin
    - Qt
        - mkdir $SYSROOT/build/qt5 && cd $SYSROOT/build/qt5
        - ./configure -opensource -confirm-license -static -debug-and-release -xplatform macx-ios-clang --prefix=$HOME/dev/vendor/Qt-5.14.2-ios -nomake examples -nomake tests -qt-pcre -skip qtactiveqt -skip qtcanvas3d -skip qtgamepad -skip qtremoteobjects -skip qtscript -skip qtserialbus -skip qtserialport -skip qtspeech -skip qtvirtualkeyboard -skip qtwayland -skip qtwebchannel -skip qtwebengine -skip qtwebglplugin -skip qtwebsockets -skip qtwebview -skip qtlottie -skip qtdatavis3d -skip qtconnectivity -skip qtcharts -skip qtandroidextras -skip qtdoc -skip qtnetworkauth -skip qtqa -skip qtrepotools -skip qtscxml -skip qtsensors -skip qtsvg -skip qttools -skip qttranslations -skip qtwinextras -skip qtx11extras -skip qtxmlpatterns -skip qtmultimedia -skip qtpurchasing
        - make install -j10
    - Python
      - pyqtdeploycli --package python --target ios-64 configure
      - $SYSROOT/build/qt5/bin/qmake SYSROOT=$SYSROOT
      - make -j10 && make install
	- python.pro: # Modules/_scproxy.c
	- Modules/posixmodule.c: #undef HAVE_SYSTEM
    - sip:
        - pyqtdeploycli --package sip --target ios-64 configure
        - python configure.py --static --sysroot=$SYSROOT --no-tools --use-qmake --configuration=sip-ios.cfg
        - $SYSROOT/build/qt5/bin/qmake
        - make -j10 && make install
    - PyQt:
        - pyqtdeploycli --package pyqt5 --target ios-64 configure
        - python configure.py --static --sysroot=$SYSROOT --no-qsci-api --no-designer-plugin --no-qml-plugin --configuration=pyqt5-ios.cfg -b $SYSROOT/bin --enable=QtCore --enable=QtGui --enable=QtWidgets --enable=QtNetwork --concatenate --confirm-license --qmake=$SYSROOT/build/qt5/bin/qmake
        - make -j10 && make install

pyqt-sysroot-osx-64-release
    - SYSROOT
        - mkdir -p $SYSROOT/build $SYSROOT/bin
        - ln -s $SYSROOT/../pyqt-sysroot-dev/bin/pyqtdeploy* $SYSROOT/bin
        - ln -s $SYSROOT/../pyqt-sysroot-dev/bin/python* $SYSROOT/bin
        - ln -s $SYSROOT/../pyqt-sysroot-dev/bin/sip $SYSROOT/bin
    - Qt
        - ../../../pyqt-sysroot-base/src/qt5/qtbase/configure -static -release -opensource -confirm-license -nomake examples -nomake tests -prefix $PWD
        - make install -j10
    - Python:
        - pyqtdeploycli --package python --target osx-64 configure
        - $SYSROOT/build/qt5/bin/qmake SYSROOT=$SYSROOT
        - make -j10; make install
        - mkdir -p $SYSROOT/bin
        - cd $SYSROOT/bin
        - pyqtdeploycli --package python --target osx-64 configure && qmake SYSROOT=$SYSROOT && make -j10 && make install
    - sip:
        - pyqtdeploycli --package sip --target osx-64 configure
        - python configure.py --static --sysroot=$SYSROOT --use-qmake --configuration=sip-osx.cfg
        - qmake
        - cp sipgen/sip ../../bin # ?????
    - PyQt:
        - pyqtdeploycli --package pyqt5 --target osx-64 configure
        - python configure.py --static --sysroot=$SYSROOT --no-qsci-api --no-designer-plugin --no-qml-plugin --configuration=pyqt5-osx.cfg -b $SYSROOT/bin --enable=QtCore --enable=QtGui --enable=QtNetwork --enable=QtWidgets --enable=QtPrintSupport --concatenate --qmake $SYSROOT/build/qt5/bin/qmake --confirm-license
        - make -j10; make install


APPENDIX 1: PYQTDEPLOY PATCHES

    - site-packages/pyqtdeploy/python/configurations/config_py3.c:

        extern PyObject* PyInit_time(void);
        extern PyObject* PyInit_math(void); extern PyObject* PyInit__pickle(void); extern PyObject* PyInit__datetime(void); extern PyObject* PyInit__struct(void);
        extern PyObject* PyInit_binascii(void);
        extern PyObject* PyInit__decimal(void);
        extern PyObject* PyInit__sha512(void);
        extern PyObject* PyInit__sha256(void);
        extern PyObject* PyInit__sha1(void);
        extern PyObject* PyInit__md5(void);
        extern PyObject* PyInit__random(void);
        extern PyObject* PyInit_zlib(void);
        extern PyObject* PyInit__socket(void);
        extern PyObject* PyInit_select(void);
        --
        {"time", PyInit_time},
        {"math", PyInit_math},
        {"pickle", PyInit__pickle},
        {"_datetime", PyInit__datetime},
        {"_struct", PyInit__struct},
        { "binascii", PyInit_binascii},
        { "_sha512", PyInit__sha512},
        { "_sha256", PyInit__sha256},
        { "_sha1", PyInit__sha1},
        { "_md5", PyInit__md5},
        { "_random", PyInit__random},
        { "_zlib", PyInit_zlib},
        { "_socket", PyInit__socket},
        { "select", PyInit_select},

    - $PYTHON/site-packages/pyqtdeploy/python/configurations/python.pro:

        Modules/timemodule.c \
        Modules/mathmodule.c \
        Modules/_math.c \
        Modules/_pickle.c Modules/_scproxy.c \
        Modules/_datetimemodule.c \
        Modules/_struct.c \
        Modules/binascii.c \
        Modules/sha512module.c \
        Modules/_randommodule.c \
        Modules/sha256module.c \
        Modules/sha1module.c \
        Modules/md5module.c \
        Modules/zlibmodule.c \
        Modules/socketmodule.c

    - FUTURE (for xlsxwriter compression support):

        Modules/zlib/adler32.c \
        Modules/zlib/deflate.c \
        Modules/zlib/gzlib.c \
        Modules/zlib/infback.c \
        Modules/zlib/inftrees.c \
        Modules/zlib/uncompr.c \
        Modules/zlib/compress.c \
        Modules/zlib/example.c \
        Modules/zlib/gzread.c \
        Modules/zlib/inffast.c \
        Modules/zlib/minigzip.c \
        Modules/zlib/zutil.c \
        Modules/zlib/crc32.c \
        Modules/zlib/gzclose.c \
        Modules/zlib/gzwrite.c \
        Modules/zlib/inflate.c \
        Modules/zlib/trees.c

    - site-packages/pyqtdeploy/builder/builder.py: (make sure vars are not random in .pro output for source control)
        - replace: " = {}" => " = Orderedict()"
        - replace: "set()" => "OrderedSet()"

    - $PYTHON/pyqtdeploy/builder/orderedset.py:

        import collections
        class OrderedSet(collections.MutableSet):

            def __init__(self, iterable=None):
                self.end = end = []
                end += [None, end, end]         # sentinel node for doubly linked list
                self.map = collections.OrderedDict()                   # key --> [key, prev, next]
                if iterable is not None:
                    self |= iterable

            def __len__(self):
                return len(self.map)

            def __contains__(self, key):
                return key in self.map

            def add(self, key):
                if key not in self.map:
                    end = self.end
                    curr = end[1]
                    curr[2] = end[1] = self.map[key] = [key, curr, end]

            def discard(self, key):
                if key in self.map:
                    key, prev, next = self.map.pop(key)
                    prev[2] = next
                    next[1] = prev

            def update(self, keys):
                for k in keys:
                    self.add(k)

            def __iter__(self):
                end = self.end
                curr = end[2]
                while curr is not end:
                    yield curr[0]
                    curr = curr[2]

            def __reversed__(self):
                end = self.end
                curr = end[1]
                while curr is not end:
                    yield curr[0]
                    curr = curr[1]

            def pop(self, last=True):
                if not self:
                    raise KeyError('set is empty')
                key = self.end[1][0] if last else self.end[2][0]
                self.discard(key)
                return key

            def __repr__(self):
                if not self:
                    return '%s()' % (self.__class__.__name__,)
                return '%s(%r)' % (self.__class__.__name__, list(self))

            def __eq__(self, other):
                if isinstance(other, OrderedSet):
                    return len(self) == len(other) and list(self) == list(other)
                return set(self) == set(other)


APPENDIX 2: HockeyApp deployment

    - Add sdk framework
      - File -> "Add files to Family Diagram..."
    - Run script build phase
        FILE="${SRCROOT}/HockeySDK-Mac/BuildAgent"
        if [ -f "$FILE" ]; then
           "$FILE"
        fi
    - Copy Files build phase
      - HockeyAppSDK.framework -> Frameworks
    - Linker flags:
      - rpath @executable_path/../Frameworks
