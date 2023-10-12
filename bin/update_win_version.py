
import os, os.path, sys, plistlib

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
sys.path.append(ROOT)

VERSION_PY_FPATH = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'pkdiagram', 'version.py'))

import importlib.util
spec = importlib.util.spec_from_file_location("version", VERSION_PY_FPATH)
version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version)

win32_plist = os.path.join(ROOT, 'build', 'win32-config', 'win32-config.prf')

for fpath in [win32_plist]:
    print('Writing', fpath, 'with version', version.VERSION)
    with open(fpath, 'w') as f:
        f.write("VERSION = %s" % version.VERSION)

