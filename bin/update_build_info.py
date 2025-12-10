"""
Write a new build UUID to pkdiagram/build_uuid.py.

This file must be self-contained, no python dependencies.
"""

import os.path, uuid, platform

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
    f.write(f"PEPPER = b'{FD_BUILD_PEPPER}'\n")
    FD_BUILD_DATADOG_API_KEY = os.getenv("FD_BUILD_DATADOG_API_KEY")
    f.write(f"DATADOG_API_KEY = {repr(FD_BUILD_DATADOG_API_KEY)}\n")


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


def remove_after_substring(text, substring):
    index = text.find(substring)
    if index != -1:
        return text[:index]
    return text


if platform.system() == "Darwin":

    osx_plist = os.path.join(ROOT, "build", "osx-config", "Info.plist")
    ios_plist = os.path.join(ROOT, "build", "ios-config", "Info.plist")

    for fpath in [osx_plist, ios_plist]:

        if fpath == ios_plist:
            VERSION = remove_after_substring(version.VERSION, "b")
        else:
            VERSION = version.VERSION

        print(f"Patching {fpath} to version {VERSION}")
        # plutil -replace CFBundleVersion -string '0.1.0d1' build/osx-config/Info.plist && less build/osx-config/Info.plist
        cmd = "plutil -replace CFBundleVersion -string '%s' %s" % (
            VERSION,
            fpath,
        )
        print(cmd)
        os.system(cmd)
        cmd = "plutil -replace CFBundleShortVersionString -string '%s' %s" % (
            VERSION,
            fpath,
        )
        print(cmd)
        os.system(cmd)

elif platform.system() == "Windows":

    win32_plist = os.path.join(ROOT, "build", "win32-config", "win32-config.prf")
    VERSION = version.VERSION

    for fpath in [win32_plist]:
        print(f"Patching {fpath} to version {VERSION}")
        with open(fpath, "w") as f:
            f.write("VERSION = %s" % VERSION)
