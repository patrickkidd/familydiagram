"""
Write a new build UUID to pkdiagram/build_uuid.py.
"""

import os.path, uuid

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

print("Writing new build UUID to pkdiagram/build_uuid.py")
fpath = os.path.join(ROOT, "pkdiagram", "build_uuid.py")
with open(fpath, "w") as f:
    id = str(uuid.uuid4())
    f.write("BUILD_UUID = '%s'" % id)


print("Writing new pepper to pkdiagram/pepper.py")
fpath = os.path.join(ROOT, "pkdiagram", "pepper.py")
with open(fpath, "w") as f:
    FD_BUILD_PEPPER = os.getenv("FD_BUILD_PEPPER")
    f.write(f"PEPPER = '{FD_BUILD_PEPPER}'\n")
    FD_BUILD_BUGSNAG_API_KEY = os.getenv("FD_BUILD_BUGSNAG_API_KEY")
    f.write(f"BUGSNAG_API_KEY = '{FD_BUILD_BUGSNAG_API_KEY}'\n")


# Update version in platform-specific locations

VERSION_PY_FPATH = os.path.realpath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "..", "pkdiagram", "version.py"
    )
)

import importlib.util

spec = importlib.util.spec_from_file_location("version", VERSION_PY_FPATH)
version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version)

if os.name != "nt":

    osx_plist = os.path.join(ROOT, "build", "osx-config", "Info.plist")
    ios_plist = os.path.join(ROOT, "build", "ios-config", "Info.plist")

    for fpath in [osx_plist, ios_plist]:
        print("Patching", fpath, "to version", version.VERSION)
        # plutil -replace CFBundleVersion -string '0.1.0d1' build/osx-config/Info.plist && less build/osx-config/Info.plist
        cmd = "plutil -replace CFBundleVersion -string '%s' %s" % (
            version.VERSION,
            osx_plist,
        )
        print(cmd)
        os.system(cmd)
        cmd = "plutil -replace CFBundleShortVersionString -string '%s' %s" % (
            version.VERSION,
            osx_plist,
        )
        print(cmd)
        os.system(cmd)

else:

    win32_plist = os.path.join(ROOT, "build", "win32-config", "win32-config.prf")

    for fpath in [win32_plist]:
        print("Writing", fpath, "with version", version.VERSION)
        with open(fpath, "w") as f:
            f.write("VERSION = %s" % version.VERSION)