# Family Diagram App

## Developer setup

```
$ mkdir .venv
$ pipenv install --dev
$ python main.py
```

## Release Processes
- Set up build env
    - All secrets, provisioning, etc set through env (complains if something missing)
        - Example: `base64 <path-to-provisioning-profile> | pbcopy` -> `export FD_PROVISIONING_PROFILE="<PASTE HERE>"`
    - Set in .env file on dev machine

- Build
    - Entire env comes through vars (validates on run)
    - App secret set via pepper.py from `$FD_BUILD_PEPPER`
    - macOS
        - `bin/build.sh [osx-release|osx-alpha|osx-beta]`
            - Creates `build/osx` from `build/osx-config`
        - CD setup in `./.github`
    - Windows
        - `bin\build.bat`
            - Creates `build/win32` from `build/win32-config`
- Versioning
    - VERSION_COMPAT in `version.py`
    - `Info.plist` updated according to `version.py` at build time
