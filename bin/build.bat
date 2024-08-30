setlocal



set ACTION=%1
set ROOT=%~dp0..
rmdir /s /q %ROOT%\\build\\win32
IF %ERRORLEVEL% NEQ 0 goto :error

echo %ACTION%

REM set QMAKE=C:\Qt\5.15.2\msvc2019_64\bin\qmake.exe
set QMAKE=C:\sysroots\sysroot-win-64\Qt\bin\qmake.exe
set PYTHONPATH=%ROOT%\lib\site-packages

echo %PYTHONPATH%

set CL=/MP8

python bin\update_build_info.py

pyqtdeploy-build --verbose --resources 12 --build-dir build\\win32 --target win-64 --qmake %QMAKE% familydiagram.pdt


copy build\common-config\* build\win32\
copy build\win32-config\* build\win32\
cd build\win32
%QMAKE% -tp vc "CONFIG-=debug"
REM msbuild "Family Diagram.vcxproj" /property:Configuration=Release
devenv "Family Diagram.vcxproj" /ProjectConfig Release

if "%ACTION%" == "" goto :skip-sign
    signtool sign /f windows-certificate.p21 /p %SIGNPASS% "release\\Family Diagram.exe"
:skip-sign

cd %ROOT%
    
:exit
endlocal
exit /b 0

:error
echo "Error in build script"
endlocal
exit /b 1
