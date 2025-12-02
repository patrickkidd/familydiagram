##
## NO DEPENDENCIES!!
##


ALPHABETA = ""  # set this to '' for release
ALPHABETA_SUFFIX = 1
VERSION_MAJOR = 2
VERSION_MINOR = 1
VERSION_MICRO = 12
VERSION_SUFFIX = ALPHABETA and "%s%s" % (ALPHABETA, ALPHABETA_SUFFIX) or ""
VERSION_SHORT = "%s.%s.%s" % (VERSION_MAJOR, VERSION_MINOR, VERSION_MICRO)
VERSION = "%s.%s.%s%s" % (VERSION_MAJOR, VERSION_MINOR, VERSION_MICRO, VERSION_SUFFIX)
IS_BETA = bool(ALPHABETA == "b")
IS_ALPHA = bool(ALPHABETA == "a")
IS_ALPHA_BETA = IS_BETA or IS_ALPHA
IS_RELEASE = not IS_ALPHA_BETA

# Oldest version that can open files saved with this version.
# Bump to current version when adding features that older versions will not be able to read.
VERSION_COMPAT = "1.3.0"


def verint(a, b, c, beta=None):
    # print('verint', a, b, c, type(a), type(b), type(c))
    return (a << 24) | (b << 16) | c


def split(text):
    text = text.strip()
    major, minor, micro = [i for i in text.split(".")]
    alphaBeta = None
    if "b" in micro:
        micro, beta = micro.split("b")
        alphaBeta = int(beta)
    elif "a" in micro:
        micro, alpha = micro.split("a")
        alphaBeta = int(alpha)
    major, minor, micro = int(major), int(minor), int(micro)
    return major, minor, micro, alphaBeta


def greaterThan(textA, textB):
    majorA, minorA, microA, betaA = split(textA)
    majorB, minorB, microB, betaB = split(textB)
    verA = verint(majorA, minorA, microA)
    verB = verint(majorB, minorB, microB)
    if verA == verB:
        if betaA and betaB:
            return betaA > betaB
        else:
            return False
    else:
        return verA > verB


def greaterThanOrEqual(textA, textB):
    majorA, minorA, microA, betaA = split(textA)
    majorB, minorB, microB, betaB = split(textB)
    verA = verint(majorA, minorA, microA)
    verB = verint(majorB, minorB, microB)
    if verA == verB:
        if betaA and betaB:
            return betaA >= betaB
        else:
            return True
    else:
        return verA > verB


def lessThan(textA, textB):
    return greaterThan(textB, textA)


def lessThanOrEqual(textA, textB):
    return greaterThanOrEqual(textB, textA)
