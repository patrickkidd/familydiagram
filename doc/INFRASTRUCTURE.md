Backend Database (Proprietary)
-----------------------------------------
- Manually deployed to VPS

Github Actions
-----------------------------------------
- .github/workflows/release.yml
    - Build macOS + windows releases
    - Update appcast
    - Takes version from version.py

Sparkle Appcasts
-----------------------------------------
- bin/github_releases_2_appcast.py
    - Called from .github/workflows/release.yml
https://familydiagram.com/appcast_windows.xml
https://familydiagram.com/appcast_windows_beta.xml
https://familydiagram.com/appcast_macos.xml
https://familydiagram.com/appcast_macos_beta.xml
