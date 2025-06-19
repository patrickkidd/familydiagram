import sys, os, os.path, pickle, subprocess, hashlib, bisect, logging, bisect, contextlib
import enum
import json
from functools import wraps
import sys, os.path
from pathlib import Path
from typing import Callable


log = logging.getLogger(__name__)


# to import vendor packages like xlsxwriter
try:
    import pdytools  # type: ignore

    IS_BUNDLE = True
except:
    IS_BUNDLE = False

import vedana
from _pkdiagram import CUtil

from PyQt5.QtCore import QSysInfo
from pkdiagram.pyqt import pyqtProperty

IS_DEBUGGER = bool(sys.gettrace() is not None)
IS_TEST = "pytest" in sys.modules
IS_WINDOWS = bool(
    CUtil.operatingSystem() & CUtil.OperatingSystem.OS_Windows
    == CUtil.OperatingSystem.OS_Windows
)
IS_MAC = bool(
    CUtil.operatingSystem() & CUtil.OperatingSystem.OS_Mac
    == CUtil.OperatingSystem.OS_Mac
)
IS_IPAD = bool(
    CUtil.operatingSystem() & CUtil.OperatingSystem.OS_iPad
    == CUtil.OperatingSystem.OS_iPad
)
IS_IPHONE = bool(
    CUtil.operatingSystem() & CUtil.OperatingSystem.OS_iPhone
    == CUtil.OperatingSystem.OS_iPhone
)
IS_IPHONE_SIMULATOR = bool(
    CUtil.operatingSystem() & CUtil.OperatingSystem.OS_iPhoneSimulator
    == CUtil.OperatingSystem.OS_iPhoneSimulator
)
IS_IOS = bool(IS_IPHONE or IS_IPAD)  # Separate into IS_IOS and IS_IPADOS
IS_APPLE = bool(IS_MAC or IS_IPHONE or IS_IPAD)
IS_DEV = CUtil.isDev()
IS_UI_DARK_MODE = False

# print(
#     f"IS_WINDOWS: {IS_WINDOWS}, IS_MAC: {IS_MAC}, IS_IPAD: {IS_IPAD}, IS_IPHONE: {IS_IPHONE}, IS_IPHONE_SIMULATOR: {IS_IPHONE_SIMULATOR}, IS_IOS: {IS_IOS}"
# )
# print(
#     f"IS_DEV: {IS_DEV}, IS_DEBUGGER: {IS_DEBUGGER}, IS_TEST: {IS_TEST}, IS_BUNDLE: {IS_BUNDLE}"
# )

BUNDLE_ID = None
if IS_BUNDLE:
    if IS_IOS:
        BUNDLE_ID = "com.vedanamedia.familydiagram"
    else:
        BUNDLE_ID = "com.vedanamedia.familydiagrammac"

import os, os.path, time, math, operator, collections.abc, subprocess, random
from datetime import datetime
from pkdiagram.pyqt import *
from . import version
from .pepper import PEPPER

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


SERVER_URL_ROOT = "https://database.familydiagram.com"
# SERVER_URL_ROOT = "http://127.0.0.1:8888"

# if version.IS_BETA or version.IS_ALPHA:
#     Debug('SERVER_URL_ROOT:', SERVER_URL_ROOT)


def serverUrl(path):
    return "%s/%s%s" % (SERVER_URL_ROOT, vedana.SERVER_API_VERSION, path)


def summarizeReplyShort(reply: QNetworkReply):
    request = reply.request()
    url = request.url().toString()
    verb = reply.attribute(QNetworkRequest.CustomVerbAttribute)
    status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
    return f"{verb} {url} {status_code}"


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


def logging_allFilter(record: logging.LogRecord):
    """Add filenames for non-Qt records."""
    if not hasattr(record, "pk_fileloc"):
        record.pk_fileloc = f"{record.filename}:{record.lineno}"
    return True


LOG_FORMAT = "%(asctime)s %(levelname)s %(pk_fileloc)-26s %(message)s"


def init_logging():

    from pkdiagram import appdirs

    FD_LOG_LEVEL = os.getenv("FD_LOG_LEVEL", "INFO").upper()
    if FD_LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        sys.stderr.write(
            f"Invalid FD_LOG_LEVEL: '{FD_LOG_LEVEL}', must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL\n"
        )
        sys.exit(1)

    handlers = []

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.addFilter(logging_allFilter)
    consoleHandler.setFormatter(logging.Formatter(LOG_FORMAT))
    consoleHandler.setLevel(getattr(logging, FD_LOG_LEVEL))
    handlers.append(consoleHandler)

    if not IS_IOS:
        appDataDir = appdirs.user_data_dir("Family Diagram", appauthor="")
        if not os.path.isdir(appDataDir):
            Path(appDataDir).mkdir()
        fileName = "log.txt" if IS_BUNDLE else "log_dev.txt"
        filePath = os.path.join(appDataDir, fileName)
        if not os.path.isfile(filePath):
            Path(filePath).touch()
        fileHandler = logging.FileHandler(filePath, mode="a+")
        fileHandler.addFilter(logging_allFilter)
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(logging.Formatter(LOG_FORMAT))
        handlers.append(fileHandler)

    def findTheMainWindow():
        app = QApplication.instance()
        if not app:
            return
        windows = app.topLevelWidgets()
        if len(windows) == 1:
            window = windows[0]
        else:
            window = app.activeWindow()
        if window and hasattr(window, "session"):
            return window

    class DatadogHandler(logging.Handler):

        def emit(self, record):

            mainwindow = findTheMainWindow()
            if not mainwindow:
                return

            mainwindow.session.handleLog(record)

    datadogHandler = DatadogHandler()
    handlers.append(datadogHandler)

    logging.basicConfig(level=logging.INFO, handlers=handlers)


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
CURRENT_DATE_FONT = QFont(FONT_FAMILY, 26)
AGE_FONT = QFont("Helvetica Neue", 12, QFont.Medium)
DETAILS_FONT = QFont(FONT_FAMILY, 16, QFont.Light)
DETAILS_BIG_FONT = QFont(FONT_FAMILY, 26, QFont.Light)
NO_ITEMS_FONT_FAMILY = "Helvetica"
NO_ITEMS_FONT_PIXEL_SIZE = 20
DRAWER_WIDTH = 400
DRAWER_OVER_WIDTH = IS_IOS and DRAWER_WIDTH or DRAWER_WIDTH * 0.9
OVERLAY_OPACITY = 0.5

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

ATTR_ANXIETY = "Δ Anxiety"
ATTR_FUNCTIONING = "Δ Functioning"
ATTR_SYMPTOM = "Δ Symptom"

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
NORMAL_PERSON_SIZE = 4


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
CLEAR_BUTTON_OPACITY = 1.0
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
ACTIVE_HELP_TEXT_COLOR = None
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
QML_ACTIVE_HELP_TEXT_COLOR = ""
QML_HIGHLIGHT_COLOR = ""  # synonym for 'CURRENT'
QML_SELECTION_COLOR = ""
QML_ITEM_ALTERNATE_BG = ""
QML_ITEM_BORDER_COLOR = ""  # '#d0cfd1'
QML_SAME_DATE_HIGHLIGHT_COLOR = ""
QML_NODAL_COLOR = ""
# Qml misc constants
QML_MARGINS = 20
QML_ITEM_MARGINS = 10
QML_SPACING = 10
QML_HEADER_HEIGHT = 40
QML_FIELD_WIDTH = 200
QML_FIELD_HEIGHT = (
    40  # not sure where this comes from but TextField and ComboBox are 40
)
QML_ITEM_HEIGHT = IS_IOS and 44 or 30  # iOS portait: 44, iOS landscape: 32
QML_LIST_VIEW_MINIMUM_HEIGHT = QML_ITEM_HEIGHT * 6
QML_ITEM_LARGE_HEIGHT = 44
QML_TITLE_FONT_SIZE = QML_ITEM_HEIGHT * 1.2 * 0.85  # iOS portait: 44, iOS landscape: 32
QML_SMALL_TITLE_FONT_SIZE = (
    IS_IOS and (QML_ITEM_HEIGHT * 0.4) or (QML_ITEM_HEIGHT * 0.50)
)  # iOS portait: 44, iOS landscape: 32
QML_DROP_SHADOW_COLOR = ""
QML_IMPORT_PATHS = [":/qml"]
QML_SMALL_BUTTON_WIDTH = 50
QML_MICRO_BUTTON_WIDTH = 21

HAVSTAD_MODEL = ["Δ Symptom", "Δ Anxiety", "Δ Functioning", "Δ Relationship"]
PAPERO_MODEL = [
    "Resourcefulness",
    "Tension Management",
    "Connectivity & Integration",
    "Systems Thinking",
    "Goal Structure",
]
STINSON_MODEL = ["Toward/Away", "Δ Arousal", "Δ Symptom", "Mechanism"]

S_EVENT_PROPS_HELP_TEXT = (
    "Events track anxiety, functioning, and symptoms, and how a person reacts to them over time. "
    "Looking back at a timeline of simple, factual events can help you see where you can make low-cost improvements in your life.\n\n"
    "Looking at the timeline and diagram together can help see how your own reactivity in relationships keeps you from your goals."
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

S_EVENT_KIND_HELP_TEXT = LONG_TEXT("")

S_DESCRIPTION_HELP_TEXT = LONG_TEXT(
    "What occurred written as a fact; opinions and other emotions go in quotes, or move into 'Details' below."
)

S_PEOPLE_HELP_TEXT = LONG_TEXT("")

S_PERSON_NOT_FOUND = LONG_TEXT(
    """A person with that name does not exist. Do you want to add it?"""
)

S_ANXIETY_HELP_TEXT = LONG_TEXT(
    "Shift in automatic response to real or imagined threat. "
    "Goes down when calm. "
    "Higher arousal, often subjectively felt as fear. "
    "Occurs in some urgent problem with no clear solution. "
)

S_SYMPTOM_HELP_TEXT = LONG_TEXT(
    "Shift up, down or same in any physical or emotional problem. "
    "Symptoms can increase or decrease with anxiety"
)

S_FUNCTIONING_HELP_TEXT = LONG_TEXT(
    "Shift up or down in managing anxiety / problems more efficiently toward your goals, AKA; "
    "mindfulness, leadership, in contact with emotion but not dominated by it."
)

S_NOTES_HELP_TEXT = LONG_TEXT(
    "Free-form notes about the event including opinions, "
    "emotional content, justification for coding anxiety, "
    "symptom, functioning, or event type."
)

S_NO_ITEMS_LABEL = LONG_TEXT(
    "Click the green (+) button in the upper right to add people and data points."
)

S_NO_EVENTS_TEXT = LONG_TEXT(
    "Widen your search criteria or click the green (+) button to add some data points to the timeline."
)

S_NO_CHAT_TEXT = LONG_TEXT(
    "Ask any question about the current diagram or biology and behavioral health. The more specific, the better."
)

S_EMAIL_SENT_TO_CHANGE_PASSWORD = LONG_TEXT(
    "An email was sent with instructions for how to change your password."
)

S_FAILED_TO_SEND_PASSWORD_RESET_EMAIL = LONG_TEXT(
    "Failed to send email to set or change your password."
    "Please contact support at info@alaskafamilysystems.com."
)

S_EMOTION_SYMBOL_NOTES_HIDDEN = LONG_TEXT(
    "The notes/details text is hidden for a relationship symbol when a start date/time is set for that symbol. "
    "Click the *i* button to the right of the start or end date/time to edit the notes for that event."
)

S_TAGS_HELP_TEXT = (
    "Add tags for periods of high anxiety, or high emotional or physical symptoms, or low thoughtfulness."
    "Name it something memorable, like 'Move-In Stress', 'Christmas \"'23\", 'Johnny's broken leg'. "
    "Then click the checkbox to activate it for this event.\n\n"
    "Then you can search for it later in the search view."
)

S_EMOTIONAL_UNITS_HELP_TEXT = (
    "Click to view shifts in anxiety, functioning, symptom, and reactivity within the context of "
    "A) a person's nuclear family, and B) each parent's nuclear family of origin. Shifts tend to "
    "correlate to events in this three-generation extended family system."
)

S_NO_EMOTIONAL_UNITS_SHOWN_NAMES_HIDDEN = "Emotional units are not shown because the 'Hide Names' option is checked in the 'View' menu."

S_NO_EMOTIONAL_UNITS_SHOWN_NO_PAIRBONDS_WITH_NAMES = (
    "Emotional units will show here when you add pair-bonds between people with names."
)

S_SERVER_IS_DOWN = "The server is down. Please try again later."
S_SERVER_ERROR = "The server responded but ran into a problem. Please try again later."


# Therapist

S_THERAPIST_NO_CHAT_TEXT = "What's on your mind?"

#


QRC = QFileInfo(__file__).absolutePath() + "/resources/"
QRC_QML = "qrc:/pkdiagram/resources/" if QRC.startswith(":") else QRC

from PyQt5.QtCore import QDir

QDir.addSearchPath("resources", os.path.join(os.path.dirname(__file__), "resources"))


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


def iblocked(f):
    """Ensure that an instance method is not called recursively."""

    @wraps(f)
    def go(self, *args, **kwargs):
        if not hasattr(self, "__blocked_methods"):
            self.__blocked_methods = {}
        if self.__blocked_methods.get(f.__name__):
            return
        was = self.__blocked_methods.get(f.__name__)
        self.__blocked_methods[f.__name__] = True
        ret = None
        if args and kwargs:
            ret = f(self, *args, **kwargs)
        elif args and not kwargs:
            ret = f(self, *args)
        elif not args and kwargs:
            ret = f(self, **kwargs)
        else:
            ret = f(self)
        self.__blocked_methods[f.__name__] = was
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
            mm = int(dateText[:2])
            dd = int(dateText[2:4])
            yyyy = int(dateText[4:8])
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


def pyDateTimeString(dateTime: datetime) -> str:
    # .strftime("%a %B %d, %I:%M%p")
    # .replace("AM", "am")
    # .replace("PM", "pm")

    return dateTime.strftime("%m/%d/%Y %I:%M %p")


def dateString(dateTime: QDateTime):
    if dateTime:
        return dateTime.toString("MM/dd/yyyy")
        # return x.toString('yyyy-MM-dd')
    else:
        return ""


def timeString(dateTime: QDateTime):
    if dateTime:
        return dateTime.toString("h:mm ap")
    else:
        return ""


def dateTimeString(dateTime: QDateTime):
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
    s_shortcut = action.shortcut().toString(QKeySequence.NativeText)
    if s_shortcut:
        text = "%s (%s)" % (action.toolTip(), s_shortcut)
    else:
        text = action.toolTip()
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


def qtHTTPReply2String(reply: QNetworkReply) -> str:
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
    body = reply.readAll().data().decode()
    if reply.rawHeader(b"Content-Type") == b"application/json":
        body = json.dumps(json.loads(body), indent=4)
    message = "\n".join(
        [
            f"{verb} {reply.request().url().toString()}",
            f"    STATUS: {reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)}",
            f"    RESPONSE HEADERS:",
            *[
                f"        {bytes(k).decode()}, {bytes(v).decode()}"
                for k, v in reply.rawHeaderPairs()
            ],
            f"    BODY: \n" + body,
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


def isTextItem(item: QQuickItem):
    if not item:
        return False
    elif any(
        x in item.metaObject().className()
        for x in ("TextEdit", "TextField", "TextInput")
    ):
        return True
    else:
        return False


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
    painter = QPainter(pixmap)
    widget.render(painter)

    quickWidgets = widget.findChildren(QQuickWidget)
    for quickWidget in quickWidgets:
        pos = quickWidget.mapTo(widget, quickWidget.rect().topLeft())
        image = quickWidget.grabFramebuffer()
        painter.drawImage(pos, image)

    painter.end()

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
        log.info(
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


def import_source(modname, filePath):
    import importlib.util

    spec = importlib.util.spec_from_file_location(modname, filePath)
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    return foo


def waitALittle(ms=10):
    log.debug(f"Waiting a little ({ms}ms)...")
    # Added for qml components since init is deferred. Works better than
    # QApplication.processEvents()
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)  # may need to be longer?
    loop.exec()


def waitUntil(condition: Callable, timeout=2000):
    Condition(condition=condition).wait(maxMS=timeout)


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
        return QPointF(CUtil.pointOnRay(pointB, QPointF(x3, y3), width))


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
    if IS_DEV and QApplication.instance().prefs().value(
        "iCloudWasOn", defaultValue=False, type=bool
    ):
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
        log.info("iCloud disabled, using last iCloud Documents path:", DATA_PATH)
    elif instance.iCloudAvailable() and useiCloud:
        prefs.setValue("iCloudDataPath", DATA_PATH_ICLOUD)
        DATA_PATH = DATA_PATH_ICLOUD
        log.info("Using iCloud folder:", DATA_PATH_ICLOUD)
    else:
        log.info("Using local Documents folder")
        DATA_PATH = DATA_PATH_LOCAL
        dir = QDir(DATA_PATH)
        if not dir.exists():
            log.info(
                "util.init(): creating dir for QStandardPaths.DataLocation:", DATA_PATH
            )
            dir.mkpath(DATA_PATH)
    from pkdiagram import util

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

    # triggered = pyqtSignal()

    def __init__(self, signal=None, only=None, condition=None, name=None):
        super().__init__()
        self.callCount = 0
        self.callArgs = []
        # self.senders = []
        self.testCount = 0
        self.lastCallArgs = None
        self.only = only
        self.condition = condition
        self.name = name
        self.signal = signal
        if signal:
            signal.connect(self)

    def deinit(self):
        if self.signal:
            self.signal.disconnect(self)
            self.signal = None

    def reset(self):
        self.callCount = 0
        self.callArgs = []
        # self.senders = []
        self.lastCallArgs = None

    def test(self):
        """Return true if the condition is true."""
        self.testCount += 1
        if self.condition:
            return self.condition()
        else:
            return self.callCount > 0

    def set(self, *args):
        """Set the condition to true. Alias for condition()."""
        self.callCount += 1
        # self.senders.append(QObject().sender())
        self.lastCallArgs = args
        self.callArgs.append(args)

    def __call__(self, *args):
        """Called by whatever signal that triggers the condition."""
        if self.only:
            only = self.only
            if not only(*args):
                return
        self.set(*args)
        # if self.test():
        #     self.triggered.emit()

    def wait(self, maxMS=1000, onError=None, interval=10):
        """Wait for the condition to be true. onError is a callback."""
        startTime = time.time()
        app = QApplication.instance()
        # sig_or_cond = self.signal or self.condition
        while app and not self.test():
            # log.debug(
            #     f"Condition[{sig_or_cond}].wait() still waiting... test count: {self.testCount}, interval (ms): {interval}"
            # )
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
        # log.debug(f"Condition[{sig_or_cond}].wait() returned {self.test()}")
        ret = self.test()
        return ret

    def waitForCallCount(self, callCount, maxMS=1000):
        log.info(f"Waiting for {callCount} calls to {self.signal}")
        start_time = time.time()
        ret = None
        while self.callCount < callCount:
            if time.time() - start_time > maxMS / 1000:
                ret = False
                log.info(
                    f"Time elapsed on Condition[{self.signal}].wait() (callCount={self.callCount})"
                )
                break
            ret = self.wait(maxMS=maxMS)
            if not ret:
                log.info(
                    f"Inner wait() returned False on Condition[{self.signal}].wait()  (callCount={self.callCount})"
                )
                break
        if ret is None:
            ret = self.callCount == callCount
            log.info(
                f"Returning {ret} with {self.callCount}/{callCount} calls to {self.signal}"
            )
        return ret

    def assertWait(self, *args, **kwargs):
        assert self.wait(*args, **kwargs) == True


def wait(signal, maxMS=1000):
    return Condition(signal).wait(maxMS=maxMS)


def waitForCallCount(signal, callCount, maxMS=1000):
    return Condition(signal).waitForCallCount(callCount, maxMS=maxMS)


def waitForCondition(condition: callable, maxMS=1000):
    INTERVAL_MS = 10
    startTime = time.time()

    app = QApplication.instance()
    ret = None
    while ret is None:
        app.processEvents(QEventLoop.WaitForMoreEvents, INTERVAL_MS)
        bleh = condition()
        if bleh:
            log.debug(
                f"Condition met on waitForCondition() using condition {condition}"
            )
            ret = True
        if (time.time() - startTime) > maxMS / 1000:
            log.error(f"Time elapsed on waitForCondition() using condition {condition}")
            ret = False
    return ret


def waitForActive(windowOrWidget, maxMS=1000):
    if not windowOrWidget.isWindow():
        window = windowOrWidget.window()
    else:
        window = windowOrWidget
    return waitForCondition(lambda: window.isActiveWindow(), maxMS=maxMS)


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
            log.error(f"TEST: Unknown animation type: {child}")


def exec_():
    """For troubleshooting."""
    QApplication.instance().exec_()
