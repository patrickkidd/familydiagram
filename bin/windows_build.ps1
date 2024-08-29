$ErrorActionPreference = "Stop"

# Ensure Git is in the PATH
$gitPath = "C:\Program Files\Git\bin"
if ($env:Path -notlike "*$gitPath*") {
    $env:Path += ";$gitPath"
    [System.Environment]::SetEnvironmentVariable('Path', $env:Path, 'Machine')
    Write-Host "Added Git to the PATH."
}


# $sshDir = "$env:USERPROFILE\.ssh"
# $publicKeyPath = "$sshDir\id_rsa.pub"
# $privateKeyPath = "$sshDir\id_rsa"

# # Ensure the ssh-agent service is installed, enabled, and started
# Write-Host "Ensuring ssh-agent service is installed, enabled, and started..."
# Get-Service -Name ssh-agent -ErrorAction SilentlyContinue | Set-Service -StartupType Manual
# Start-Service -Name ssh-agent

# ssh-add $privateKeyPath

cd C:\
if (Test-Path "C:\familydiagram") {
    Write-Host "Deleting C:\familydiagram..."
    Remove-Item -Recurse -Force "C:\familydiagram"
}


# Add C:\Qt\5.15.2\bin to the current session's PATH
$qtBinPath = "C:\Qt\5.15.2\msvc2019_64\bin"
if ($env:Path -notlike "*$qtBinPath*") {
    $env:Path += ";$qtBinPath"
    Write-Host "Added $qtBinPath to the current session's PATH."
} else {
    Write-Host "$qtBinPath is already in the current session's PATH."
}


# Add Python to the current session's PATH
$pythonPath = "C:\Python310\"
if ($env:Path -notlike "*$pythonPath*") {
    $env:Path += ";$pythonPath"
    Write-Host "Added $pythonPath to the current session's PATH."
} else {
    Write-Host "$pythonPath is already in the current session's PATH."
}


# Add Python to the current session's PATH
$pythonScriptsPath = "C:\Python310\Scripts\"
if ($env:Path -notlike "*$pythonScriptsPath*") {
    $env:Path += ";$pythonScriptsPath"
    Write-Host "Added $pythonScriptsPath to the current session's PATH."
} else {
    Write-Host "$pythonScriptsPath is already in the current session's PATH."
}



Write-Host "PATH: $env:Path"

$env:GIT_SSH_COMMAND = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
git clone -b 2.0.0 git@github.com:patrickkidd/familydiagram.git ./familydiagram
cd familydiagram
mkdir .venv
C:\Python310\python.exe -m pipenv install --dev
& .\bin\build.bat
