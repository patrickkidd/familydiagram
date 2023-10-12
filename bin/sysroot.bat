REM Mostly here to indicate that the sysroot needs to go outside the project folder
REM to work around qt builds failing b/c of the windows max path limitation.

setlocal

pyqtdeploy-sysroot --verbose --sysroots-dir C:\sysroots sysroot\sysroot.toml
