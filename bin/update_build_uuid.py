import os.path, uuid

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

fpath = os.path.join(ROOT, "pkdiagram", "build_uuid.py")
with open(fpath, "w") as f:
    id = str(uuid.uuid4())
    f.write("BUILD_UUID = '%s'" % id)
