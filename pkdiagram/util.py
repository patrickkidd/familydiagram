import sys, os, os.path, enum, pickle, subprocess, hashlib, bisect, logging, urllib.parse, wsgiref.handlers, bisect, contextlib
from functools import wraps
import sys, os.path, logging
from pathlib import Path
from . import appdirs, util


log = logging.getLogger(__name__)


# to import vendor packages like xlsxwriter
try:
    import pdytools

    IS_BUNDLE = True
except:
    IS_BUNDLE = False

try:
    import PyQt5.QtQml

    IS_BAREBONES = False
except ImportError as e:
    ("No qml, so not importing gui and object modules")
    IS_BAREBONES = True

import vedana
from _pkdiagram import *
from _pkdiagram import CUtil


from PyQt5.QtCore import QSysInfo

if not hasattr(QSysInfo, "macVersion") or not QSysInfo.macVersion() & QSysInfo.MV_IOS:
    IS_IOS = False
else:
    IS_IOS = True

IS_TEST = "pytest" in sys.modules
IS_APPLE = bool(CUtil.operatingSystem() & CUtil.OS_Mac)
IS_WINDOWS = bool(CUtil.operatingSystem() & CUtil.OS_Windows)
IS_IPHONE = bool(CUtil.operatingSystem() & CUtil.OS_iPhone)
IS_DEV = CUtil.isDev()
IS_MOD_TEST = False
IS_UI_DARK_MODE = False
BUNDLE_ID = None
if IS_BUNDLE:
    if IS_IOS:
        BUNDLE_ID = "com.vedanamedia.familydiagram"
    else:
        BUNDLE_ID = "com.vedanamedia.familydiagrammac"

import os, os.path, time, math, operator, collections.abc, subprocess, random
from datetime import datetime
from .pyqt import *
from . import version
from .pepper import PEPPER
from .eventkind import EventKind

try:
    from .build_uuid import *  # not sure if this is even needed any more
except ImportError as e:
    pass


if IS_IOS:
    HARDWARE_UUID = "<ios>"  # no device-id protection required on iOS
elif "nt" in os.name:
    # s = subprocess.check_output('wmic csproduct get uid')
    # self.hardwareUUID = s.split('\n')[1].strip().decode('utf-8').strip()
    HARDWARE_UUID = (
        subprocess.check_output("wmic csproduct get name,identifyingnumber,uuid")
        .decode("utf-8")
        .split()[-1]
    )
elif os.uname()[0] == "Darwin":
    HARDWARE_UUID = (
        subprocess.check_output(
            "system_profiler SPHardwareDataType | awk '/UUID/ { print $3; }'",
            shell=True,
        )
        .decode("utf-8")
        .strip()
    )
else:
    HARDWARE_UUID = None
MACHINE_NAME = QSysInfo.machineHostName()

PEPPER = "123"
DEBUG_PENCIL = False
CONFIRM_SAVE = True
ENABLE_PINCH_PAN_ZOOM = IS_IOS
ENABLE_WHEEL_PAN = True
ENABLE_SERVER_VIEW = True
ENABLE_SERVER_UPLOADER = True
ENABLE_PENCIL = False
ENABLE_DROP_SHADOWS = False
ENABLE_DUPLICATES_CHECK = False
ENABLE_OPENGL = True  # bool(not IS_IOS) # QQuickWidget automatically introduces OpenGL
ENABLE_FILES = False
ENABLE_COPY_PASTE = False
ENABLE_ITEM_COPY_PASTE = False
ENABLE_DATE_BUDDIES = False


if not IS_DEV:
    SERVER_URL_ROOT = "https://database.familydiagram.com"
elif IS_TEST:
    SERVER_URL_ROOT = (
        "http://127.0.0.1:10000"  # so it doesn't connect to the dev server on 8888
    )
else:  # IS_DEV
    if IS_WINDOWS:
        SERVER_URL_ROOT = "http://turin.local:8888"
    elif IS_IOS:
        SERVER_URL_ROOT = "http://turin.local:8888"
    else:
        SERVER_URL_ROOT = "http://127.0.0.1:8888"


# if version.IS_BETA or version.IS_ALPHA:
#     Debug('SERVER_URL_ROOT:', SERVER_URL_ROOT)


def serverUrl(path):
    return "%s/%s%s" % (SERVER_URL_ROOT, vedana.SERVER_API_VERSION, path)


# TODO: Deprecate
try:
    from .sales_tax_rates import zips as SALES_TAX_RATES
except:
    SALES_TAX_RATES = []


def pretty(x, exclude=[], noNone=True):
    if not isinstance(exclude, list):
        exclude = [exclude]
    s = ""
    if isinstance(x, dict):
        parts = []
        for k, v in x.items():
            if k not in exclude and (noNone and v is not None):
                parts.append(f"{k}: {v}")
        s += ", ".join(parts)
    return s


def LONG_TEXT(s):
    """filter multi-line text as one long string for qml help text."""
    return s.replace("\n", " ").replace("<br>", "\n\n")


def init_logging():

    def allFilter(record: logging.LogRecord):
        """Add filenames for non-Qt records."""
        if not hasattr(record, "pk_fileloc"):
            record.pk_fileloc = f"{record.filename}:{record.lineno}"
        return True

    LOG_FORMAT = "%(asctime)s %(pk_fileloc)-26s %(message)s"

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.addFilter(allFilter)
    consoleHandler.setFormatter(logging.Formatter(LOG_FORMAT))

    appDataDir = appdirs.user_data_dir("Family Diagram", appauthor="")
    if not os.path.isdir(appDataDir):
        Path(appDataDir).mkdir()
    fileName = "log.txt" if util.IS_BUNDLE else "log_dev.txt"
    filePath = os.path.join(appDataDir, fileName)
    if not os.path.isfile(filePath):
        Path(filePath).touch()
    fileHandler = logging.FileHandler(filePath, mode="a+")
    fileHandler.addFilter(allFilter)
    fileHandler.setFormatter(logging.Formatter(LOG_FORMAT))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[consoleHandler, fileHandler],
    )


##
## Constants
##


EXTENSION = "fd"
DOT_EXTENSION = "." + EXTENSION
OPEN_FILE_TYPES = "Family Diagrams (%s)" % ",".join(["*." + i for i in [EXTENSION]])
SAVE_FILE_TYPES = (
    "Family Diagram (*.%s);;Image JPEG (*.jpg *.jpeg);;Image PNG (*.png);;Excel (*.xlsx)"
    % EXTENSION
)
DROP_EXTENSIONS = ["jpeg"]
MAX_RECENT_FILES = 10
AUTOSAVE_INTERVAL_S = 60 * 30  # 30 minutes
SURFACE_FORMAT = QSurfaceFormat()
SURFACE_FORMAT.setSamples(8)

PREFS_UI_HONOR_SYSTEM_DARKLIGHT_MODE = "system"
PREFS_UI_DARK_MODE = "dark"
PREFS_UI_LIGHT_MODE = "light"

ITEM_NONE = None
ITEM_MALE = 0
ITEM_FEMALE = 1
ITEM_MARRY = 2
ITEM_CHILD = 3
ITEM_PENCIL = 4
ITEM_ERASER = 5
ITEM_FUSION = 6
ITEM_CUTOFF = 7
ITEM_CONFLICT = 8
ITEM_PROJECTION = 9
ITEM_DISTANCE = 10
ITEM_TOWARD = 11
ITEM_AWAY = 12
ITEM_DEFINED_SELF = 13
ITEM_CALLOUT = 14
ITEM_RECIPROCITY = 15
ITEM_INSIDE = 16
ITEM_OUTSIDE = 17

BORDER_RADIUS = 5
#
DEFAULT_USE_TIME = QDateTime(
    QDate(2000, 1, 1), QTime(0, 0, 0)
)  # the date portion is irrelevant
CURRENT_DATE_INDICATOR_WIDTH = 4
RESIZE_HANDLE_WIDTH = IS_IOS and 25 or 10
FONT_FAMILY = "SF Pro Text"
FONT_FAMILY_TITLE = "SF Pro Display"
TEXT_FONT_SIZE = IS_IOS and 14 or 12  # ios default: 17
HELP_FONT_SIZE = IS_IOS and 13 or 11  # ios default: 15
CURRENT_DATE_FONT = QFont(FONT_FAMILY, 36)
AGE_FONT = QFont("Helvetica Neue", 12, QFont.Medium)
DETAILS_FONT = QFont(FONT_FAMILY, 16, QFont.Light)
DETAILS_BIG_FONT = QFont(FONT_FAMILY, 26, QFont.Light)
DRAWER_WIDTH = 400
DRAWER_OVER_WIDTH = IS_IOS and DRAWER_WIDTH or DRAWER_WIDTH * 0.9

# Variables

VAR_VALUE_DOWN = "down"
VAR_VALUE_SAME = "same"
VAR_VALUE_UP = "up"

VAR_ANXIETY_DOWN = VAR_VALUE_DOWN
VAR_ANXIETY_SAME = VAR_VALUE_SAME
VAR_ANXIETY_UP = VAR_VALUE_UP

VAR_FUNCTIONING_DOWN = VAR_VALUE_DOWN
VAR_FUNCTIONING_SAME = VAR_VALUE_SAME
VAR_FUNCTIONING_UP = VAR_VALUE_UP

VAR_SYMPTOM_DOWN = VAR_VALUE_DOWN
VAR_SYMPTOM_SAME = VAR_VALUE_SAME
VAR_SYMPTOM_UP = VAR_VALUE_UP

ATTR_ANXIETY = "Anxiety"
ATTR_FUNCTIONING = "Functioning"
ATTR_SYMPTOM = "Symptom"

# Person

PERSON_RECT = QRectF(-50, -50, 100, 100)
DEFAULT_PERSON_SIZE = 5
PERSON_SIZES = [
    {"name": "Large", "size": 5},
    {"name": "Medium", "size": 4},
    {"name": "Small", "size": 3},
    {"name": "Micro", "size": 2},
    {"name": "Nano", "size": 1},
]
PERSON_SIZE_NAMES = [entry["name"] for entry in PERSON_SIZES]
PERSON_KIND_MALE = "male"
PERSON_KIND_FEMALE = "female"
PERSON_KIND_ABORTION = "abortion"
PERSON_KIND_MISCARRIAGE = "miscarriage"
PERSON_KIND_UNKNOWN = "unknown"
PERSON_KINDS = [
    {"name": "Male", "kind": PERSON_KIND_MALE},
    {"name": "Female", "kind": PERSON_KIND_FEMALE},
    {"name": "Abortion", "kind": PERSON_KIND_ABORTION},
    {"name": "Miscarriage", "kind": PERSON_KIND_MISCARRIAGE},
    {"name": "Unknown", "kind": PERSON_KIND_UNKNOWN},
]
PERSON_KIND_NAMES = [entry["name"] for entry in PERSON_KINDS]

# Emotion

EMOTION_INTENSITIES = [
    {"name": "Small", "intensity": 1},
    {"name": "Medium", "intensity": 2},
    {"name": "Large", "intensity": 3},
]
EMOTION_INTENSITY_NAMES = [entry["name"] for entry in EMOTION_INTENSITIES]
DEFAULT_EMOTION_INTENSITY = 1
DEFAULT_SCENE_SCALE = 0.33  # so default person size is largest size
DEEMPHASIZED_OPACITY = 0.1
BUTTON_SIZE = 36
MARGIN_Y = round(BUTTON_SIZE / 5)
MARGIN_X = round(BUTTON_SIZE / 5)
MINIMUM_SCENE_RECT = QRectF(-1000, -800, 2000, 1600)
MAXIMUM_SCENE_RECT = QRectF(-100000, -100000, 200000, 200000)
PASTE_OFFSET = 50
DEFAULT_SHAPE_MARGIN = 5.0
SCENE_MARGIN = 1000
PRINT_MARGIN = 100
# ZOOM_FIT_MARGIN = .45
PRINT_DEVICE_PIXEL_RATIO = 3
PERSON_Z = 5
MARRIAGE_Z = 4
DETAILS_Z = 1
EMOTION_Z = 6
NOTE_Z = 7
LAYERITEM_Z = 10
SELECTED_Z_DELTA = 50
# ANIM_TIMER_MS = 16.66 # 60Hz = 16.66ms
ANIM_TIMER_MS = 10
ANIM_DURATION_MS = 250
ANIM_EASING = QEasingCurve.OutQuad
LAYER_ANIM_DURATION_MS = ANIM_DURATION_MS  # obsolete in favor of ANIM_DURATION_MS?
OPENGL_SAMPLES = 16
SNAP_THRESHOLD_PERCENT = 0.25  # percent of dragging person height
SNAP_PEN = QPen(QColor(0, 0, 255, 100), 0.5)
DEFAULT_LEGEND_SIZE = QSize(309, 175)
GRAPHICAL_TIMELINE_SLIDER_HEIGHT = int(BUTTON_SIZE + MARGIN_Y * 2)

BIRTH_TEXT = "Birth"
DEATH_TEXT = "Death"
ADOPTED_TEXT = "Adopted"
EMPTY_TEXT = "<empty>"
MULTIPLE_TEXT = ""
BLANK_DATE_TEXT = "--/--/----"
BLANK_TIME_TEXT = "--:-- pm"
UNNAMED_TEXT = "[unnamed]"

CLICK_TO_ADD_TEXT = "<double-click to add>"

PEN = QPen(QBrush(Qt.black), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

# QColor
WINDOW_BG = None
CONTROL_BG = None
SELECTION_COLOR = None
SELECTION_PEN = None
SELECTION_BRUSH = None
HIGHLIGHT_TEXT_COLOR = None
HOVER_COLOR = None
HOVER_PEN = None
HOVER_BRUSH = None
TEXT_COLOR = None
DROP_SHADOW_COLOR = None
ACTIVE_TEXT_COLOR = None
INACTIVE_TEXT_COLOR = None
GRID_COLOR = None
SAME_DATE_HIGHLIGHT_COLOR = None
NODAL_COLOR = None
FLASH_COLOR = QColor(200, 0, 0, 100)
FLASH_SCALE_DELTA = 1.3
QML_LAZY_DELAY_INTERVAL_MS = 1  # 1000
# Qml colors
QML_ITEM_BG = ""
QML_HEADER_BG = ""
QML_WINDOW_BG = ""
QML_CONTROL_BG = ""
QML_TEXT_COLOR = ""
QML_SELECTION_TEXT_COLOR = ""
QML_HIGHLIGHT_TEXT_COLOR = (
    ""  # synonym for 'CURRENT', not same as QPalette.HighlightedText
)
QML_ACTIVE_TEXT_COLOR = ""
QML_INACTIVE_TEXT_COLOR = ""
QML_HIGHLIGHT_COLOR = ""  # synonym for 'CURRENT'
QML_SELECTION_COLOR = ""
QML_ITEM_ALTERNATE_BG = ""
QML_ITEM_BORDER_COLOR = ""  # '#d0cfd1'
QML_SAME_DATE_HIGHLIGHT_COLOR = ""
QML_NODAL_COLOR = ""
# Qml misc constants
QML_MARGINS = 20
QML_SPACING = 10
QML_HEADER_HEIGHT = 40
QML_FIELD_WIDTH = 200
QML_ITEM_HEIGHT = IS_IOS and 44 or 30  # iOS portait: 44, iOS landscape: 32
QML_ITEM_LARGE_HEIGHT = 44
QML_TITLE_FONT_SIZE = QML_ITEM_HEIGHT * 1.2 * 0.85  # iOS portait: 44, iOS landscape: 32
QML_SMALL_TITLE_FONT_SIZE = (
    IS_IOS and (QML_ITEM_HEIGHT * 0.4) or (QML_ITEM_HEIGHT * 0.50)
)  # iOS portait: 44, iOS landscape: 32
QML_DROP_SHADOW_COLOR = ""
QML_IMPORT_PATHS = [":/qml"]
QML_SMALL_BUTTON_WIDTH = 50
QML_MICRO_BUTTON_WIDTH = 21

EVENT_PROPS_HELP_TEXT = LONG_TEXT(
    """Events are occurrences in time.
They are the core of a systems model. A systems model is at least one which
defines how a change in one area of a system occurs in response to a change in another area of the system.
<br>A systems model is based on systems thinking.
At its simplest, systems thinking has to do with defining how processes unfold over time.
Thinking in terms of a process through time automatically generates some degree of objectivity.
<br>Events on the timeline should be factual. The description should be the shortest possible
summary of what occurred. It should only contain a fact.
<br>If the description of an event is a subjective opinion,
it can be converted to a fact using the "functional fact" tool: It is a fact that a
person dreams at a particular time. What the person dreams is not necessarily a fact.
<br>Together with relationships, events are the backbone of the timeline.
"""
)

EMOTION_PROPS_HELP_TEXT = LONG_TEXT(
    """Relationships describe
automatic emotional responses that occur between individuals.
Because they are automatic, they are descriptive of the functioning of the emotional system.
<br>Relationships can be used in a number of ways. They can describe the hypothesis for a basic pattern,
or a singal factual state, or a discrete move in time.
<br>When a basic pattern hypothesis, they have no dates. When a factual state,
they may indicate a period of time where there was mutual conflict, distance, positive emotional valence, etc. between two people.
When a discrete move, they may be a move toward, away, or defined self by a single person at a particular time.
<br>Together with events, relationships are the backbone of the timeline.
"""
)

S_PERSON_NOT_FOUND = LONG_TEXT(
    """A person with that name does not exist. Do you want to add it?"""
)


EVENT_KIND_NAMES = [x.name for x in EventKind]

___DATA_PATH = None
___DATA_PATH_LOCAL = None
___DATA_PATH_ICLOUD = None

NORMAL_PERSON_SIZE = 4

# if IS_DEV:
#     from profilehooks import profile
# else:

#     def profile(fn=None, skip=0, filename=None, immediate=False, dirs=False,
#             sort=None, entries=40,
#             profiler=('cProfile', 'profile', 'hotshot'),
#             stdout=True):

#         if fn is None:  # @profile() syntax -- we are a decorator maker
#             def decorator(fn):
#                 return profile(fn, skip=skip, filename=filename,
#                                immediate=immediate, dirs=dirs,
#                                sort=sort, entries=entries,
#                                profiler=profiler, stdout=stdout)
#             return decorator
#         else:
#             return fn


QRC = QFileInfo(__file__).absolutePath() + "/resources/"
QRC_QML = "qrc:/pkdiagram/resources/" if QRC.startswith(":") else QRC


def personKindIndexFromName(name):
    return PERSON_KIND_NAMES.index(name)


def personKindNameFromIndex(index):
    return PERSON_KIND_NAMES[index]


def personKindFromIndex(index):
    return PERSON_KINDS[index]["kind"]


def personKindNameFromKind(kind):
    for i, v in enumerate(PERSON_KINDS):
        if v["kind"] == kind:
            return v["name"]


def personKindIndexFromKind(kind):
    for i, v in enumerate(PERSON_KINDS):
        if v["kind"] == kind:
            return i


def personSizeFromIndex(index):
    return PERSON_SIZES[index]["size"]


def personSizeFromName(name):
    for entry in PERSON_SIZES:
        if entry["name"] == name:
            return entry["size"]


def personSizeNameFromSize(size):
    for entry in PERSON_SIZES:
        if entry["size"] == size:
            return entry["name"]


def personSizeIndexFromName(name):
    for i, entry in enumerate(PERSON_SIZES):
        if entry["name"] == name:
            return i


def personSizeIndexFromSize(size):
    for i, entry in enumerate(PERSON_SIZES):
        if entry["size"] == size:
            return i


def scaleForPersonSize(size):
    if size > NORMAL_PERSON_SIZE:
        return 1.0 + 0.25 * (size - NORMAL_PERSON_SIZE)
    elif size == NORMAL_PERSON_SIZE:
        return 0.8
    elif size < NORMAL_PERSON_SIZE:
        return 0.4 ** abs(size - NORMAL_PERSON_SIZE)


def personRectForSize(size):
    coeff = scaleForPersonSize(size)
    width = PERSON_RECT.width() * coeff
    ret = QRectF(-width / 2.0, -width / 2.0, width, width)
    return ret


def sizeForPeople(personA, personB=None):
    if personA and personB:
        size = max(personA.size(), personB.size())
    elif personA and not personB:
        size = personA.size()
    else:
        size = 3
    return size


def penWidthForSize(size):
    return PEN.widthF() * scaleForPersonSize(size)


def emotionIntensityFromIndex(index):
    return EMOTION_INTENSITIES[index]["intensity"]


def emotionIntensityIndexFromIntensity(intensity):
    for i, entry in enumerate(EMOTION_INTENSITIES):
        if entry["intensity"] == intensity:
            return i


def emotionIntensityNameForIntensity(intensity):
    for i, v in enumerate(EMOTION_INTENSITIES):
        if v["intensity"] == intensity:
            return v["name"]


def csToBool(cs):
    if cs == Qt.Checked:
        return True
    elif cs == Qt.PartiallyChecked:
        return True
    elif cs == Qt.Unchecked:
        return False


def blocked_recursive(f):
    """Block recursive class"""
    f._blocked = False

    @wraps(f)
    def go(self, *args, **kwargs):
        if not f._blocked:
            f._blocked = True
            f(self, *args, **kwargs)
            f._blocked = False

    go.__name__ = f.__name__
    return go


@contextlib.contextmanager
def blocker(o):
    """Temporarily unblock an object blocked by `blocked` or `fblocked`."""
    was = getattr(o, "_blocked", False)
    o._blocked = True

    try:
        yield was
    except Exception as e:
        raise e
    finally:
        o._blocked = was


def blocked(f):
    """Block access to every method in a class when one is called."""

    @wraps(f)
    def go(self, *args, **kwargs):

        with blocker(f) as wasBlocked:
            ret = None
            if not wasBlocked:
                if args and kwargs:
                    ret = f(self, *args, **kwargs)
                elif args and not kwargs:
                    ret = f(self, *args)
                elif not args and kwargs:
                    ret = f(self, **kwargs)
                else:
                    ret = f(self)
        return ret

    go.__name__ = f.__name__
    return go


def fblocked(f):
    """Block access to a single method in a class when that method is called."""

    @wraps(f)
    def go(self, *args, **kwargs):
        if f._blocked:
            return
        was = f._blocked
        f._blocked = True
        ret = None
        if args and kwargs:
            ret = f(self, *args, **kwargs)
        elif args and not kwargs:
            ret = f(self, *args)
        elif not args and kwargs:
            ret = f(self, **kwargs)
        else:
            ret = f(self)
        f._blocked = was
        return ret

    f._blocked = False
    go.__name__ = f.__name__
    return go


@contextlib.contextmanager
def monkeypatch(obj, attr, value):
    was = getattr(obj, attr)
    setattr(obj, attr, value)
    yield was
    setattr(obj, attr, was)


@contextlib.contextmanager
def painter_state(painter):
    """Call painter.save() and painter.restore() even if there is an exception."""

    painter.save()
    try:
        yield painter
    except Exception as e:
        raise e
    finally:
        painter.restore()


@contextlib.contextmanager
def paint_event(painter):
    """Call painter.end() even if there is an exception."""

    try:
        yield painter
    except Exception as e:
        raise e
    finally:
        painter.end()


def _perimeter_lightning_bolt(degrees, width, length=50):
    """
    Create a lightning bolt path at a specified angle.
    """
    path = QPainterPath()
    path.addPolygon(
        QPolygonF(
            [
                QPointF(0, 0),
                QPointF(width * -0.2, width * 0.4),
                QPointF(width / 10, width * 0.35),
                QPointF(width * -0.2, width * 0.9),  # peak
                # QPointF(width / -5, width * .55),
                # QPointF(width / -2, width * .60),
                # QPointF(width * -.2, 0),
                # QPointF(0, 0),
            ]
        )
    )

    nudge = QTransform()
    nudge.rotate(-10)
    path *= nudge

    # Ensure bolt starts from center and goes outward
    path.translate(0, -length * 2)

    transform = QTransform()
    transform.rotate(degrees)
    return path * transform


def bolts_path(width, num):
    WIDTH = width * 0.2
    SPACING = 11
    path = QPainterPath()
    for angle in [45, 135, 225, 315]:
        if num == 1:
            path.addPath(_perimeter_lightning_bolt(angle, WIDTH))
        elif num == 2:
            path.addPath(_perimeter_lightning_bolt(angle - SPACING * 0.5, WIDTH))
            path.addPath(_perimeter_lightning_bolt(angle + SPACING * 0.5, WIDTH))
        elif num == 3:
            path.addPath(_perimeter_lightning_bolt(angle - SPACING, WIDTH))
            path.addPath(_perimeter_lightning_bolt(angle, WIDTH))
            path.addPath(_perimeter_lightning_bolt(angle + SPACING, WIDTH))
    return path


def Date(year, month, day, hour=None, minute=None, seconds=None):
    """Backwards compatibility for QDate(x, y, z)"""
    ret = QDateTime(QDate(year, month, day))
    if not None in (hour, minute, seconds):
        ret.setTime(QTime(hour, minute, seconds))
    elif not None in (hour, minute):
        ret.setTime(QTime(hour, minute))
    return ret


def Date_from_datetime(dt):
    return Date(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def validatedDateTimeText(dateText, timeText=None):
    """mm/dd/yyyy. useTime is a QDateTime to take the time from."""
    import dateutil.parser

    ret = None
    if len(dateText) == 8 and "/" in dateText:  # 05111980
        try:
            x = int(dateText)
        except ValueError:
            x = None
        if x is not None:
            mm = int(s[:2])
            dd = int(s[2:4])
            yyyy = int(s[4:8])
            ret = QDateTime(QDate(yyyy, mm, dd))
    if ret is None and dateText not in (None, "", BLANK_DATE_TEXT):
        # normal route
        try:
            dt = dateutil.parser.parse(dateText)
        except ValueError:
            ret = QDateTime()
        if ret is None:
            ret = Date(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    if timeText not in (None, "", BLANK_TIME_TEXT):
        try:
            dt2 = dateutil.parser.parse(timeText)
        except ValueError:
            dt2 = None
        if dt2:
            if not ret:
                ret = QDateTime.currentDateTime()
            ret.setTime(
                QTime(dt2.hour, dt2.minute, dt2.second, int(dt2.microsecond / 1000))
            )
    return ret


def dateString(dateTime):
    if dateTime:
        return dateTime.toString("MM/dd/yyyy")
        # return x.toString('yyyy-MM-dd')
    else:
        return ""


def timeString(dateTime):
    if dateTime:
        return dateTime.toString("h:mm ap")
    else:
        return ""


def dateTimeString(dateTime):
    if dateTime:
        return dateTime.toString("MM/dd/yyyy h:mm ap")
    else:
        return ""


def dateRangesOverlap(startA, endA, startB, endB):
    if (not startA and not endA) or (not startB and not endB):
        return True
    if startA is None:
        startA = QDateTime()
    if endA is None:
        endA = QDateTime()
    if startB is None:
        startB = QDateTime()
    if endB is None:
        endB = QDateTime()
    return startA <= endB and endA >= startB


def frange(start, end, step):
    while start < end:
        yield start
        start += step


def setButtonToolTip(button, action):
    text = "%s (%s)" % (
        action.toolTip(),
        action.shortcut().toString(QKeySequence.NativeText),
    )
    button.setToolTip(text)


def setBackground(w, c):
    p = QPalette(w.palette())
    w._orig_bg = p.color(QPalette.Window)
    w.setAutoFillBackground(True)
    if isinstance(w, QLineEdit):
        p.setColor(QPalette.Base, c)
    elif isinstance(w, QDateEdit):
        p.setColor(QPalette.Base, c)
    else:
        p.setColor(QPalette.Window, c)
    w.setPalette(p)


def clearBackground(w):
    w.setAutoFillBackground(False)


# https://stackoverflow.com/questions/596216/formula-to-determine-brightness-of-rgb-color
# https://www.w3.org/TR/AERT/#color-contrast
def luminanceOf(color):
    return 0.299 * color.redF() + 0.587 * color.greenF() + 0.114 * color.blueF()


def isLightColor(color):
    return color.alphaF() < 1 or luminanceOf(color) >= 0.7


def contrastTo(color):
    if isLightColor(color):
        return QColor(Qt.black)
    else:
        return QColor(Qt.white)


# https://stackoverflow.com/questions/12228548/finding-equivalent-color-with-opacity
def lightenOpacity(c, a):
    w = QColor("white")
    r1, g1, b1 = c.red(), c.green(), c.blue()
    r2, g2, b2 = w.red(), w.green(), w.blue()
    r3 = r2 + (r1 - r2) * a
    g3 = g2 + (g1 - g2) * a
    b3 = b2 + (b1 - b2) * a
    return QColor(int(r3), int(g3), int(b3))


class NullGraphicsEffect(QGraphicsEffect):
    def draw(self, painter):
        self.drawSource(painter)


def makeDropShadow(offset=1, blurRadius=45, color=QColor(100, 100, 100, 100)):
    eff = QGraphicsDropShadowEffect()
    eff.setColor(color)
    eff.setBlurRadius(blurRadius)
    eff.setOffset(offset)
    return eff


# https://www.qtcentre.org/threads/3205-Toplevel-widget-with-rounded-corners
def roundedRectRegion(rect, radius, parts):
    """parts = ('bottom-left', 'top-right', ...)
    USAGE:
        self.setMask(util.roundedRectRegion(self.rect(), util.BORDER_RADIUS))
    """
    region = QRegion()
    # middle and borders
    region += rect.adjusted(radius, 0, -radius, 0)
    region += rect.adjusted(0, radius, 0, -radius)
    corner = QRect(QPoint(0, 0), QSize(radius * 2, radius * 2))
    if "top-left" in parts:
        corner.moveTopLeft(rect.topLeft())
        region += QRegion(corner, QRegion.Ellipse)
    if "top-right" in parts:
        corner.moveTopRight(rect.topRight())
        region += QRegion(corner, QRegion.Ellipse)
    if "bottom-left" in parts:
        corner.moveBottomLeft(rect.bottomLeft())
        region += QRegion(corner, QRegion.Ellipse)
    if "bottom-right" in parts:
        corner.moveBottomRight(rect.bottomRight())
        region += QRegion(corner, QRegion.Ellipse)
    return region


def isInstance(o, className):
    """To avoid an import or circular import reference."""
    return bool(o.__class__.__name__ == className)


def deepMerge(d, u, ignore=[]):
    """Recursively merge dict `u` in to dict `d`."""
    if not isinstance(ignore, list):
        ignore = [ignore]
    for k, v in u.items():
        if k in ignore:
            continue
        if isinstance(v, collections.abc.Mapping) and (k in d):
            d[k] = deepMerge(d.get(k, {}), v, ignore=ignore)
        else:
            d[k] = v
    return d


def invertPixmap(p):
    img = p.toImage()
    img.invertPixels()
    return QPixmap.fromImage(img)


def rindex(lst, val, start=None):
    if start is None:
        start = len(lst) - 1
    for i in xrange(start, -1, -1):
        if lst[i] == val:
            return i


def rindex(li, x):
    for i in reversed(range(len(li))):
        if li[i] == x:
            return i
    raise ValueError("{} is not in list".format(x))


def qtHTTPReply2String(reply):
    if reply.operation() == QNetworkAccessManager.HeadOperation:
        verb = "HEAD"
    elif reply.operation() == QNetworkAccessManager.GetOperation:
        verb = "GET"
    elif reply.operation() == QNetworkAccessManager.PutOperation:
        verb = "PUT"
    elif reply.operation() == QNetworkAccessManager.PostOperation:
        verb = "POST"
    elif reply.operation() == QNetworkAccessManager.DeleteOperation:
        verb = "DELETE"
    elif reply.operation() == QNetworkAccessManager.CustomOperation:
        verb = "<custom>"
    else:
        verb = None
    message = "\n".join(
        [
            f"{verb} {reply.request().url().toString()}",
            f"    STATUS: {reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)}",
            f"    RESPONSE HEADERS:",
            *[
                f"        {bytes(k).decode()}, {bytes(v).decode()}"
                for k, v in reply.rawHeaderPairs()
            ],
        ]
    )
    return message


# def reportException(etype, value, tb):
#     """ Email reporting """
#     fpath, lineno, func, text = traceback.extract_tb(tb)[-1]
#     lines = traceback.format_exception(etype, value, tb)
#     toaddy = 'Patrick Stinson <patrick@vedanamedia.com>'
#     fromaddy = 'Family Diagram Reporter <no-reply@vedanamedia.com>'
#     subject = '[Family Diagram Exception] %s:%s' % (fpath, lineno) # traceback.format_exception_only(etype, value)[-1]
#     message = """From: %s\nTo: %s\nSubject: %s\n\n%s""" % (fromaddy, toaddy, subject, ''.join(lines))
#     server = smtplib.SMTP('smtp.gmail.com', 587)
#     server.ehlo()
#     server.starttls()
#     server.login('patrick@vedanamedia.com', '67roverP4tr1ck')
#     server.sendmail(fromaddy, toaddy, message)
#     server.close()
#     Debug('Reported exception via email to:', toaddy)


def newPassword():
    chars = "abcdefghijklmnopqrstuvwxyz!@#$%^&*()_+"
    return "".join([random.choice(chars) for i in range(16)])


def sameProp(items, attr):
    """Used for property sheets."""
    if not items:
        return None
    for item in items:
        if item.prop(attr).get() != items[0].prop(attr).get():
            return None
    return items[0].prop(attr).get()


def sameOf(items, getter):
    """Return the same value for self.items as determined by getter(item)."""
    if not items:
        return None
    stuff = [getter(item) for item in items]
    mismatch = False
    first = stuff[0]
    for i in stuff[1:]:
        if i != first:
            mismatch = True
            break
    if mismatch or first is None:
        return None
    else:
        return first


def newNameOf(items, tmpl, key):
    if not items:
        return tmpl % 1
    name = None
    for i in range(10000):
        name = tmpl % (i + 1)
        found = False
        for row, item in enumerate(items):
            if key(item) == name:
                found = True
                break
        if not found:
            break
    return name


def printQObject(o):
    mo = o.metaObject()
    properties = []
    signals = []
    slots = []
    etc = []
    for i in range(mo.propertyCount()):
        properties.append(mo.property(i).name())
    for i in range(mo.methodCount()):
        meth = mo.method(i)
        if meth.methodType() == QMetaMethod.Signal:
            signals.append(bytes(meth.methodSignature()).decode())
        elif meth.methodType() == QMetaMethod.Slot:
            slots.append(bytes(meth.methodSignature()).decode())
        else:
            etc.append(bytes(meth.methodSignature()).decode())
    s += f'QOBJECT: {o.__class__.__name__}, objectName: "{o.objectName()}"'
    for i in sorted(properties):
        s += f"\n    PROPERTY: {i}"
    for i in sorted(signals):
        s += f"    SIGNAL:   {i}"
    for i in sorted(slots):
        s += f"    SLOT:     {i}"
    for i in sorted(etc):
        s += f"    METHOD:   {i}"


def dumpWidget(widget):
    import os.path, time

    ROOT = os.path.join(os.path.dirname(__file__), "..")
    pixmap = QPixmap(widget.size())
    widget.render(pixmap)
    fileDir = os.path.realpath(os.path.join(ROOT, "dumps"))
    pngPath = os.path.join(fileDir, "dump_%s.png" % time.time())
    os.makedirs(fileDir, exist_ok=True)
    if not pixmap.isNull():
        pixmap.save(pngPath)
        log.info(f"Dumped widget to: {pngPath}")
        os.system('open "%s"' % pngPath)


def lelide(data, length):
    return (
        ("..." + data[len(data) - (length - 4) :]) if len(data) > (length - 4) else data
    )


def ljust(data, length):
    if len(data) > length:
        data = lelide(data, length)
    return data.ljust(length)


def runModel(model, silent=True, columns=None):
    WIDTH = 25
    if not silent:
        Debug(
            "MODEL:", model.__class__.__name__, 'objectName: "%s"' % model.objectName()
        )
        sys.stdout.write(" %s|" % ljust("Column", 10))
    nCols = model.columnCount()
    for col in range(model.columnCount()):
        if columns is not None and not col in columns:
            continue
        header = model.headerData(col, Qt.Horizontal)
        if not silent:
            if col < nCols - 1:
                sys.stdout.write(" %s|" % ljust(header, WIDTH))
            else:
                sys.stdout.write(" %ss" % ljust(header, WIDTH))
    if not silent:
        print()
    for row in range(model.rowCount()):
        if not silent:
            sys.stdout.write(" %s|" % ljust(str(row), 10))
        for col in range(model.columnCount()):
            if columns is not None and not col in columns:
                continue
            index = model.index(row, col)
            if -1 in (index.row(), index.column()):
                raise ValueError("invalid index: row: %s, col: %s" % (row, col))
            value = model.data(index, Qt.DisplayRole)
            if not silent:
                if col < nCols - 1:
                    sys.stdout.write(" %s|" % ljust(str(value), WIDTH))
                else:
                    sys.stdout.write(" %s" % ljust(str(value), WIDTH))
        if not silent:
            print()


def printModel(model, columns=None):
    runModel(model, silent=False, columns=columns)


def initPersonBox(scene, cb, selected=None, exclude=[]):
    if not isinstance(exclude, list):
        exclude = [exclude]
    cb.clear()
    index = 0
    entries = []
    for person in scene.people():
        if person.id in exclude:
            continue
        name = person.fullNameOrAlias()
        if name:
            entries.append((person.id, name))
    for id, name in sorted(entries, key=operator.itemgetter(1)):
        cb.addItem(name)
        cb.setItemData(index, id)
        index = index + 1
    if selected and isInstance(selected, "Person"):
        index = cb.findData(selected.id)
        cb.setCurrentIndex(index)
    else:
        cb.setCurrentIndex(-1)


def modTest(__test__, loadfile=True, useMW=False):
    """Run a test app with __test__(scene) as callback."""
    global IS_MOD_TEST
    IS_MOD_TEST = True
    import sys, inspect, signal
    from .util import CUtil
    from .scene import Scene
    from .pyqt import QTimer
    from .application import Application
    from .models import SceneModel

    sys.path.append(os.path.realpath(os.path.join(__file__, "..", "..", "tests")))
    import test_util

    app = Application(sys.argv)

    def _quit(x, y):
        app.quit()

    signal.signal(signal.SIGINT, _quit)

    if useMW:
        parent = QMainWindow()
        modTest.Layout = None
    else:
        parent = QWidget()
        Layout = modTest.Layout = QHBoxLayout(parent)
        Layout.setContentsMargins(0, 0, 0, 0)
        parent.setLayout(Layout)

    class EventFilter(QObject):
        def eventFilter(self, o, e):
            print(e.type(), qenum(QEvent, e.type()))
            if e.type() == QEvent.Close:
                app.quit()
            return False

    sig = inspect.signature(__test__)
    # app.installEventFilter(EventFilter(app))
    parent.show()

    def onFileOpened(document):
        scene = modTest.scene = Scene(document=document)
        bdata = document.diagramData()
        data = pickle.loads(bdata)
        ret = scene.read(data)
        scene.setCurrentDateTime(QDateTime.currentDateTime())
        if len(sig.parameters) == 2:
            w = __test__(modTest.scene, parent)
        elif len(sig.parameters) == 3:
            sceneModel = SceneModel()
            sceneModel.scene = modTest.scene
            w = __test__(modTest.scene, parent, sceneModel)
        if w is None:
            log.error("modTest returned None")
            Application.quit()
            return
        if useMW:
            parent.setCentralWidget(w)
        else:
            modTest.Layout.addWidget(w)

    def noFileOpened():
        scene = modTest.scene = Scene()
        if len(sig.parameters) == 2:
            w = __test__(modTest.scene, parent)
        elif len(sig.parameters) == 3:
            sceneModel = SceneModel()
            sceneModel.scene = modTest.scene
            w = __test__(modTest.scene, parent, sceneModel)
        modTest.Layout.addWidget(w)

    def onInit():
        ROOT = os.path.realpath(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
        )

        filePath = os.path.join(ROOT, "tests", "data", "mod_test.fd")
        # filePath = os.path.join(ROOT, "tests", "data", "TIMELINE_TEST.fd")

        CUtil.instance().openExistingFile(QUrl.fromLocalFile(filePath))

    if loadfile:
        QTimer.singleShot(0, onInit)
    else:
        noFileOpened()

    CUtil.instance().init()
    CUtil.instance().fileOpened[FDDocument].connect(onFileOpened)

    app.exec()
    app.deinit()


modTest.scene = None


def import_source(modname, filePath):
    import importlib.util

    spec = importlib.util.spec_from_file_location(modname, filePath)
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    return foo


### Geometry functions


def ___distance(p1, p2):
    """pythagorean"""
    a = p1.x() - p2.x()
    b = p1.y() - p2.y()
    return math.sqrt(a * a + b * b)


def ___pointOnRay(orig, dest, distance):
    """Calculate a point on ray (orig, dest) <distance> from orig"""
    a = dest.x() - orig.x()
    b = dest.y() - orig.y()
    c = math.sqrt(pow(a, 2) + pow(b, 2))  # pythagorean
    if c > 0:
        p = distance / c
    else:
        p = 0
    return QPointF(orig.x() + p * a, orig.y() + p * b)


def ____perpendicular(pointA, pointB, reverse=False, width=None):
    """Return pointC such that ray
    (pointC, pointB) is perpendicular to ray (pointA, pointB).
    """
    if reverse:
        pointB, pointA = pointA, pointB
    x1 = pointA.x()
    x2 = pointB.x()
    y1 = pointA.y()
    y2 = pointB.y()
    a = x1 - x2
    b = y1 - y2
    if reverse is True:
        x3 = x2 - b
        y3 = y2 + a
    else:
        x3 = x2 + b
        y3 = y2 - a
    if width is None:
        return QPointF(x3, y3)
    else:
        return QPointF(pointOnRay(pointB, QPointF(x3, y3), width))


# def drawTextAroundPoint(painter, x, y, flags, text, boundingRect=None):
#     size = 32767.0
#     corner = QPointF(x, y - size)
#     if flags & Qt.AlignHCenter:
#         corner.setX(corner.x() - (size / 2.0))
#     elif flags & Qt.AlignRight:
#         corner.setX(corner.x() - size)
#     if flags & Qt.AlignVCenter:
#         corner.setY(corner.y() + size / 2.0)
#     elif flags & Qt.AlignTop:
#         corner.setY(corner.y() + size)
#     else:
#         flags |= Qt.AlignBottom
#     rect = QRectF(corner.x(), corner.y(), size, size)
#     painter.drawText(rect, flags, text, boundingRect)


def appResourcesPath():
    if IS_APPLE:
        return QApplication.applicationDirPath() + "/../Resources"


class SortedList:
    """sortedcontainers.SortedList was throwing ValueError for items in the list."""

    def __init__(self):
        self._list = []

    def __repr__(self):
        return self._list.__repr__()

    def __len__(self):
        return len(self._list)

    def __getitem__(self, i):
        return self._list[i]

    def bisect_right(self, x):
        return bisect.bisect_right(self._list, x)

    def add(self, x):
        bisect.insort_right(self._list, x)

    def remove(self, x):
        self._list.remove(x)

    def index(self, x):
        return self._list.index(x)

    def to_list(self):
        return list(self._list)


class Center(QGraphicsItem):
    def __init__(self):
        super().__init__()
        self.rect = QRectF(-50, -50, 100, 100)
        self.setPos(QPointF(0, 0))

    def boundingRect(self):
        return self.rect

    def paint(self, painter, options, widget):
        painter.setPen(QColor("black"))
        # bounding rect
        c = QColor("blue")
        c.setAlpha(100)
        painter.setBrush(QColor("green"))
        painter.drawRect(self.rect)
        # exposed rect
        c = QColor("red")
        c.setAlpha(100)
        painter.setBrush(c)
        painter.drawRect(options.exposedRect)
        # center point
        painter.setBrush(QColor("black"))
        painter.drawEllipse(QRectF(0, 0, 5, 5))


class Settings(QSettings):
    """Currently only used for auto save feature."""

    # valueChanged = pyqtSignal(str, QVariant)

    def __init__(self, *args):
        super().__init__(*args)
        self._autoSave = False
        # self.block = False

    def autoSave(self):
        return self._autoSave

    def setAutoSave(self, x):
        self._autoSave = bool(x)
        return self._autoSave

    autoSave = pyqtProperty(bool, autoSave, setAutoSave)

    def setValue(self, *args, **kwargs):
        super().setValue(*args, **kwargs)
        # if not self.block:
        #     self.valueChanged.emit(args[0], args[1])
        if self.autoSave:
            self.sync()

    # def blockSignals(self, on):
    #     self.block = on


class ClickFilter(QObject):
    """differentiate between double and single clicks for a widget
    by waiting for the double click timeout before sending single click."""

    clicked = pyqtSignal()
    doubleClicked = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.lastRelease = QTime.currentTime()
        self.singleClickTimer = QTimer(self)
        self.singleClickTimer.setSingleShot(True)
        self.singleClickTimer.timeout.connect(self.onSingleClickElapsed)
        parent.installEventFilter(self)

    def eventFilter(self, o, e):
        if o == self.parent():
            if e.type() == QEvent.MouseButtonRelease:
                diff = self.lastRelease.elapsed()
                self.lastRelease.start()
                log.debug(diff)
                if diff < QApplication.doubleClickInterval():
                    # double click
                    self.doubleClicked.emit()
                    self.singleClickTimer.stop()
                else:
                    self.singleClickTimer.start()
                return True
        return super().eventFilter(o, e)

    def onSingleClickElapsed(self):
        self.clicked.emit()


class QNAM(QNetworkAccessManager):

    _instance = None

    @staticmethod
    def instance():
        if not QNAM._instance:
            QNAM._instance = QNAM()
        return QNAM._instance


# class WebEnginePage(QWebEnginePage):

#     # https://stackoverflow.com/questions/40170180/link-clicked-signal-qwebengineview
#     def acceptNavigationRequest(self, url, type, isMainFrame):
#         QDesktopServices.openUrl(url)
#         return False

# class ReturnFilter(QObject):
#     def __init__(self, item, parent):
#         super().__init__(parent)
#         self.item = item
#     def eventFilter(self, o, e):
#         if e.type() == QEvent.KeyRelease and e.key() in [Qt.Key_Return or Qt.Key_Enter]:
#             self.item.onNameChanged()
#             return True
#         return super().eventFilter(o, e)


def usingOrSimulatingiCloud():
    if IS_DEV and prefs().value("iCloudWasOn", defaultValue=False, type=bool):
        ret = True  # simulate in dev
    else:
        ret = CUtil.instance().iCloudOn()
    return ret


def ____iCloudInitialized():
    global prefs, instance
    DATA_PATH_LOCAL = os.path.join(
        QStandardPaths.standardLocations(QStandardPaths.DataLocation)[0], "Documents"
    )
    DATA_PATH_ICLOUD = instance.iCloudDocumentsPath()
    useiCloud = prefs.value("useiCloudDrive", type=bool, defaultValue=False)
    if not IS_BUNDLE and not IS_IOS and prefs.value("iCloudDataPath"):  # dev only
        DATA_PATH = DATA_PATH_ICLOUD = prefs.value("iCloudDataPath")
        Debug("iCloud disabled, using last iCloud Documents path:", DATA_PATH)
    elif instance.iCloudAvailable() and useiCloud:
        prefs.setValue("iCloudDataPath", DATA_PATH_ICLOUD)
        DATA_PATH = DATA_PATH_ICLOUD
        Debug("Using iCloud folder:", DATA_PATH_ICLOUD)
    else:
        Debug("Using local Documents folder")
        DATA_PATH = DATA_PATH_LOCAL
        dir = QDir(DATA_PATH)
        if not dir.exists():
            Debug(
                "util.init(): creating dir for QStandardPaths.DataLocation:", DATA_PATH
            )
            dir.mkpath(DATA_PATH)
    from .. import util

    DATA_PATH = DATA_PATH
    DATA_PATH_LOCAL = DATA_PATH_LOCAL
    DATA_PATH_ICLOUD = DATA_PATH_ICLOUD

    # for i in os.listdir('/private/var/mobile/Library/Mobile Documents/iCloud~com~vedanamedia~familydiagram/Documents'):
    #     iCloud_ensureDownloaded(os.path.join(DATA_PATH, 'Patrick Stinson.fd'))


def suffix(s):
    if "." in s:
        return s[s.rfind(".") + 1 :]
    else:
        return None


def fileName(filePath):
    return filePath[filePath.rfind(os.sep) + 1 :]


def relativeDocPath(filePath):
    if isinstance(filePath, QUrl):
        filePath = filePath.toLocalFile()
    docsPath = CUtil.instance().documentsFolderPath()
    ret = filePath.replace(docsPath, "")
    if ret[0] == os.sep:
        ret = ret[1:]
    return ret


def packagePath(filePath):
    if isinstance(filePath, QUrl):
        filePath = filePath.toLocalFile()
    fileInfo = QFileInfo(filePath)
    if fileInfo.isDir() and suffix(fileName(filePath)) == EXTENSION:
        return filePath
    dir = QFileInfo(filePath).dir()
    while suffix(dir.dirName()) != EXTENSION and not dir.isRoot():
        dir.cdUp()
    return dir.absolutePath()


def packageName(filePath):
    name = fileName(packagePath(filePath))
    name = name[: name.rfind("." + EXTENSION)]
    return name


def isDocumentPackage(filePath):
    if isinstance(filePath, QUrl):
        filePath = filePath.toLocalFile()
    fileInfo = QFileInfo(filePath)
    return fileInfo.isDir() and suffix(filePath) == EXTENSION


def packageContainerPath(filePath):
    _packagePath = packagePath(filePath)
    fileInfo = QFileInfo(_packagePath)
    return fileInfo.dir().absolutePath()


def file_md5(fpath):
    if not QFileInfo(fpath).isFile():
        return
    hash_md5 = hashlib.md5()
    f = QFile(fpath)
    if not f.open(QIODevice.ReadOnly):
        log.error(f"Could not open file for reading: {fpath}")
        return
    for chunk in iter(lambda: f.read(4096), b""):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


def fileEquals(filePath1, filePath2):
    if not QFileInfo(filePath1).isFile() or not QFileInfo(filePath2).isFile():
        return False
    md5_1 = file_md5(filePath1)
    md5_2 = file_md5(filePath2)
    return md5_1 == md5_2


def copyFileOrDir(src, dst):
    """cp -R <src> <dst>"""
    log.debug(f"copyFileOrDir: +++ {src}")
    log.debug(f"copyFileOrDir: --- {dst}")
    if QFileInfo(src).isFile():
        if not QFileInfo(dst).isFile() or not fileEquals(src, dst):
            dest_dir = os.path.dirname(dst)
            os.makedirs(dest_dir, exist_ok=True)
            if QFile.copy(src, dst):
                log.info(f"Wrote file {dst}")
            else:
                log.error(f"Could not write file {dst}")
    else:
        dir = QDir(src)

        for d in dir.entryList(QDir.Dirs | QDir.NoDotAndDotDot):
            dst_path = os.path.join(dst, d)
            dir.mkpath(dst_path)
            copyFileOrDir(os.path.join(src, d), dst_path)

        for f in dir.entryList(QDir.Files):
            dirPath = QFileInfo(os.path.join(dst, f)).absolutePath()
            if not QDir(dirPath).exists():
                if not QDir(dirPath).mkpath("."):
                    log.error("Could not create path {dirPath}")
                    continue
            copyFileOrDir(os.path.join(src, f), os.path.join(dst, f))


def find(_list, key):
    for x in _list:
        if key(x):
            return x


def qenum(base, value):
    """Convert a Qt Enum value to its key as a string.

    Args:
        base: The object the enum is in, e.g. QFrame.
        value: The value to get.

    Return:
        The key associated with the value as a string, or None.
    """
    klass = value.__class__
    try:
        idx = klass.staticMetaObject.indexOfEnumerator(klass.__name__)
    except AttributeError:
        idx = -1
    keyName = None
    if idx != -1:
        keyName = klass.staticMetaObject.enumerator(idx).valueToKey(value)
    else:
        for name, obj in vars(base).items():
            if isinstance(obj, klass) and obj == value:
                keyName = name
                break
    if keyName:
        return "%s.%s" % (base.__name__, keyName)


import pickle


def invoke(qobject: QObject, name: str, *args, returns=False):
    _args = (Q_RETURN_ARG(QVariant), *args) if returns else args
    ret = QMetaObject.invokeMethod(qobject, name, Qt.DirectConnection, *_args)
    return ret.toVariant()


def touchFD(filePath, bdata=None):
    os.makedirs(filePath, exist_ok=True)
    picklePath = os.path.join(filePath, "diagram.pickle")
    if not os.path.isfile(picklePath):
        with open(picklePath, "wb") as f:
            if not bdata:
                bdata = pickle.dumps({})
            f.write(bdata)


def appDataDir():
    return QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)


def shouldFullScreen():
    IS_IPHONE = bool(CUtil.instance().operatingSystem() == CUtil.OS_iPhone)
    # self.here(CUtil.instance().operatingSystem(), CUtil.OS_iPhone)
    return IS_IPHONE


class FileTamperedWithError(Exception):
    pass


HASH_SUFFIX = "protect"


def hashFor(bdata):
    hasher = hashlib.sha256()
    hasher.update(bdata)
    return hasher.hexdigest()


def writeWithHash(fpath, bdata):
    import pkdiagram

    if not isinstance(bdata, bytes):
        bdata = bdata.encode("utf-8")

    with open(fpath, "wb") as f:
        f.write(bdata)

    hashToWrite = hashFor(pkdiagram.PEPPER + bdata).encode()
    hashFpath = os.path.join(fpath + "." + HASH_SUFFIX)
    with open(hashFpath, "wb") as f:
        f.write(hashToWrite)


def readWithHash(fpath):
    import pkdiagram

    with open(fpath, "rb") as f:
        bdata = f.read()

    hashFpath = os.path.join(fpath + "." + HASH_SUFFIX)
    if os.path.isfile(hashFpath):
        with open(hashFpath, "rb") as f:
            hashOnDisk = f.read()
    else:
        hashOnDisk = None
    if hashOnDisk != hashFor(pkdiagram.PEPPER + bdata).encode():
        raise FileTamperedWithError(f"Protected file tampered with: {fpath}")
    return bdata


import uuid


def validate_uuid4(uuid_string):
    """
    Validate that a UUID string is in
    fact a valid uuid4.
    Happily, the uuid module does the actual
    checking for us.
    It is vital that the 'version' kwarg be passed
    to the UUID() call, otherwise any 32-character
    hex string is considered valid.
    """

    try:
        val = uuid.UUID(uuid_string, version=4)
    except ValueError:
        # If it's a value error, then the string
        # is not a valid hex code for a UUID.
        return False
    except:
        # pks: Well, if it's an error at all then it isn't valid
        return False

    # If the uuid_string is a valid hex code,
    # but an invalid uuid4,
    # the UUID.__init__ will convert it to a
    # valid uuid4. This is bad for validation purposes.

    return val.hex == uuid_string.replace("-", "")


_profile = None


def startProfile():
    global _profile

    ### Std Python profiler
    import cProfile

    _profile = cProfile.Profile()
    _profile.enable()

    import atexit

    atexit.register(_profile_atexit)

    ### pyinstrument
    # import pyinstrument
    # self.profile = pyinstrument.Profiler()

    ### pycallgraph
    # from pycallgraph import PyCallGraph
    # from pycallgraph.output import GraphvizOutput
    # graphviz = GraphvizOutput(output_file='profile.png')
    # self.profiler = PyCallGraph(output=graphviz)
    # self.profiler.start()


def stopProfile():
    global _profile

    ### Std python profiler
    _profile.disable()
    import io, pstats

    s = io.StringIO()
    sortby = "cumulative"
    ps = pstats.Stats(_profile, stream=s).sort_stats(sortby)
    ps.print_stats()  # ('pksampler')
    log.info(s.getvalue())
    _profile = None

    import atexit

    atexit.unregister(_profile_atexit)

    ### pyinstrument
    # self.profiler.stop()
    # self.here(profiler.output_text(unicode=True, color=True))
    # self.profiler = None

    ### pycallgraph
    # self.profiler.done()
    # self.profiler = None # saves file
    # os.system('open profile.png')


def _profile_atexit():
    global _profile
    if _profile:
        stopProfile()


ABLETON_COLORS = [
    "#000000",
    "#ff2b00",
    "#c95c00",
    "#b68b00",
    "#809800",
    "#31a30d",
    "#009f8e",
    "#007ac3",
    "#2100ff",
    "#2850a8",
    "#6846b3",
    "#7b7b7b",
    "#3c3c3c",
    "#ff0000",
    "#bfbfbf",
    "#9fc100",
    "#5fca00",
    "#00c800",
    "#00c3af",
    "#00a5f5",
    "#4c7eeb",
    "#8f66ec",
    "#af40b2",
    "#c52e69",
    "#9f542c",
    "#ff6200",
    "#adff00",
    "#50ff47",
    "#00ff00",
    "#00ffa0",
    "#00ffcf",
    "#00edff",
    "#7dc6ff",
    "#8fa5ff",
    "#c187ff",
    "#e75feb",
    "#ff00da",
]


class LoggedContext:
    def __init__(self, scope):
        self._scope = scope

    def __enter__(self):
        print(f">>> {self._scope}")

    def __exit__(self):
        print(f"<<< {self._scope}")


class Condition(QObject):
    """Allows you to wait for a signal to be called."""

    triggered = pyqtSignal()

    def __init__(self, signal=None, only=None, condition=None, name=None):
        super().__init__()
        self.callCount = 0
        self.callArgs = []
        self.senders = []
        self.lastCallArgs = None
        self.only = only
        self.condition = condition
        self.name = name
        self.signal = signal
        if signal:
            signal.connect(self)

    def __deinit__(self):
        if self.signal:
            self.signal.disconnect(self)

    def reset(self):
        self.callCount = 0
        self.callArgs = []
        self.senders = []
        self.lastCallArgs = None

    def test(self):
        """Return true if the condition is true."""
        if self.condition:
            return self.condition()
        else:
            return self.callCount > 0

    def set(self, *args):
        """Set the condition to true. Alias for condition()."""
        self.callCount += 1
        self.senders.append(QObject().sender())
        self.lastCallArgs = args
        self.callArgs.append(args)

    def __call__(self, *args):
        """Called by whatever signal that triggers the condition."""
        if self.only:
            only = self.only
            if not only(*args):
                return
        self.set(*args)
        if self.test():
            self.triggered.emit()

    def wait(self, maxMS=1000, onError=None, interval=10):
        """Wait for the condition to be true. onError is a callback."""
        startTime = time.time()
        success = True
        app = QApplication.instance()
        while app and not self.test():
            try:
                app.processEvents(QEventLoop.WaitForMoreEvents, interval)
            except KeyboardInterrupt as e:
                if onError:
                    onError()
                break
            elapsed = (time.time() - startTime) * 1000
            if elapsed >= maxMS:
                break
            # else:
            #     time.sleep(.1) # replace with some way to release loop directly from signal
        ret = self.test()
        return ret

    def assertWait(self, *args, **kwargs):
        assert self.wait(*args, **kwargs) == True


def wait(signal, maxMS=1000):
    return Condition(signal).wait(maxMS=maxMS)


class SignalCollector(QObject):

    triggered = pyqtSignal()

    def __init__(self, signals):
        super().__init__()
        self._signals = signals
        self._awaiting = list(signals)
        for signal in signals:
            signal.connect(self._make_slot(signal))

    def _make_slot(self, signal):
        def slot():
            signal.disconnect(slot)
            self._awaiting.remove(signal)
            if not self._awaiting:
                self.triggered.emit()

        return slot


#####################################################
##
##  Test utils
##
#####################################################


def test_finish_anim(anim):
    anim.valueChanged.emit(anim.endValue())
    anim.finished.emit()


def test_finish_group(group):
    for i in range(group.animationCount()):
        child = group.animationAt(i)
        if isinstance(child, QParallelAnimationGroup):
            test_finish_group(child)
        elif isinstance(child, QVariantAnimation):
            test_finish_anim(child)
        else:
            log.error(f"TEST: Unknown animation type: {animation}")


def wait_for_attach():
    PORT = 3001
    log.info(f"Waiting for debugger to attach to port {PORT}...")
    # import ptvsd
    # ptvsd.enable_attach(address=('127.0.0.1', PORT)) #, redirect_output=True)
    # ptvsd.wait_for_attach()
    import debugpy

    debugpy.listen(PORT)
    debugpy.wait_for_client()


#####################################################
##
##  Init
##
#####################################################


_prefs = None


def prefs():
    global _prefs
    return _prefs
