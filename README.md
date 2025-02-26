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
    - Canonical entryopint: bin/build.sh
        - Entire env comes through (mostly confidential) env vars
    - Confidential env vars (validated in bin/build_env.sh):
        - FD_BUILD_PEPPER The app secret that is used for encrypted disk writes.
          Written to pepper.py and imported in python.
        - FD_BUILD_PROVISIONING_PROFILE_BASE64: Hashed contents of the provisioning profile.
        - FD_BUILD_CERTIFICATE_BASE64: Hashed contents of the signing certificate
        - FD_BUILD_PRIVATE_KEY_BASE64: Private key for the signing certificate
        - FD_BUILD_AC_AUTH_KEY_ID: AppCenter authorization key id
        - FD_BUILD_AC_AUTH_KEY_BASE64: AppCenter authorization key contents
        - FD_BUILD_AC_AUTH_KEY_ISSUER: App Developer Team ID (UUID)
    - Temporary confidential artifacts set up in bin/setup_provisioning_profile.sh
        - Deletest & recreates transient Keychain build.keychain-db
        - Imports provisioning profile into that keychain
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

