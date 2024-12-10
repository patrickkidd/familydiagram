# Store the original execution policy
$originalExecutionPolicy = Get-ExecutionPolicy

# Store the original security protocol settings
$originalSecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol

# Set the execution policy to Bypass for the current process
Set-ExecutionPolicy Bypass -Scope Process -Force

# Add TLS 1.2 to the security protocol settings
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072



# Uninstall Chocolatey if it exists
if (Test-Path "$env:ProgramData\chocolatey") {
    Write-Host "Uninstalling Chocolatey..."


    # Ensure Chocolatey is in the PATH
    $chocoPath = "$env:ProgramData\chocolatey\bin"
    if ($env:Path -notlike "*$chocoPath*") {
        $env:Path += ";$chocoPath"
        [System.Environment]::SetEnvironmentVariable('Path', $env:Path, 'Machine')
        Write-Host "Added Chocolatey to the PATH."
}

    Write-Host "Uninstalling Git..."
    choco uninstall git git.install -y

    if (Test-Path "C:\Python310") {
        Write-Host "Uninstalling Python..."
        choco uninstall python -y
        Write-Host "Uninstalled Python."
    } else {
        Write-Host "Python installation directory C:\Python310 does not exist, skipping uninstall."
    }

    if (Test-Path "C:\Qt") {
        Write-Host "Deleting C:\Qt..."
        Remove-Item -Recurse -Force "C:\Qt"
        Write-Host "Deleted C:\Qt"
    } else {
        Write-Host "Qt installation directory C:\Qt does not exist, skipping uninstall."
    }


    Remove-Item -Recurse -Force "$env:ProgramData\chocolatey"
    [System.Environment]::SetEnvironmentVariable('ChocolateyInstall', $null, 'Machine')
    [System.Environment]::SetEnvironmentVariable('ChocolateyToolsLocation', $null, 'Machine')
    [System.Environment]::SetEnvironmentVariable('Path', ($env:Path -split ';' | Where-Object { $_ -notlike '*chocolatey*' }) -join ';', 'Machine')

    # Remove Chocolatey from the current session's PATH
    $env:Path = ($env:Path -split ';' | Where-Object { $_ -notlike '*chocolatey*' }) -join ';'

    Write-Host "Uninstalled Chocolatey."
} else {
    Write-Host "Chocolatey installation directory does not exist."
}


# Install Everything

Write-Host "Installing Chocolatey..."
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

Write-Host "Installing git..."
choco install git -y

Write-Host "Installing Python..."
choco install python --version=3.11.6 -y

Write-Host "Installing pipenv, aqtinstall..."
python -m pip install pipenv aqtinstall -y

Write-Host "Installing qt5 with aqtinstall..."

# python -m aqt install-qt windows desktop 5.15.2 win64_msvc2019_64 --archives qtbase,qtdeclarative,qtgraphicaleffects,qtimageformats,qtquickcontrols,qtquickcontrols2,qttools,qtwinextras
#
# python -m aqt list-qt windows desktop --archives 5.15.2 win64_msvc2019_64
# d3dcompiler_47 opengl32sw qt3d qtactiveqt qtbase qtconnectivity qtdeclarative qtgamepad qtgraphicaleffects qtimageformats qtlocation qtmultimedia qtquickcontrols qtquickcontrols2 qtremoteobjects qtscxml qtsensors qtserialbus qtserialport qtspeech qtsvg qttools qttranslations qtwebchannel qtwebsockets qtwebview qtwinextras qtxmlpatterns
python -m aqt install-qt windows desktop 5.15.2 win64_msvc2019_64 --outputdir C:\Qt --archives qtbase qtdeclarative qtgraphicaleffects qtimageformats qtquickcontrols qtquickcontrols2 qttools qtwinextras
# python -m aqt install-src windows desktop 5.15.2 win64_msvc2019_64 --archives qtbase qtdeclarative qtgraphicaleffects qtimageformats qtquickcontrols qtquickcontrols2 qttools qtwinextras


# Add C:\Qt\5.15.2\bin to the system PATH
$qtBinPath = "C:\Qt\5.15.2\msvc2019_64\bin"
$existingPath = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
if ($existingPath -notlike "*$qtBinPath*") {
    $newPath = "$existingPath;$qtBinPath"
    [System.Environment]::SetEnvironmentVariable('Path', $newPath, 'Machine')
    Write-Host "Added $qtBinPath to the system PATH."
} else {
    Write-Host "$qtBinPath is already in the system PATH."
}

# Add C:\Qt\5.15.2\bin to the current session's PATH
if ($env:Path -notlike "*$qtBinPath*") {
    $env:Path += ";$qtBinPath"
    Write-Host "Added $qtBinPath to the current session's PATH."
} else {
    Write-Host "$qtBinPath is already in the current session's PATH."
}

# Print the PATH environment variable after installations
Write-Host "PATH environment variable after installations:"
Write-Host $env:Path

# Restore the original execution policy and security protocol
Set-ExecutionPolicy $originalExecutionPolicy -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = $originalSecurityProtocol
