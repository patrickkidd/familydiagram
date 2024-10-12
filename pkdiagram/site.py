"""
Mocked module installed by python installation
"""

ENABLE_USER_SITE = True

USER_SITE = "/tmp/familydiagram"


def getsitepackages():
    return "/tmp/familydiagram"


def getusersitepackages():
    global USER_SITE
    return USER_SITE
