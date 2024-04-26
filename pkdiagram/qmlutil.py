#####################################################
##
##  Qml
##
#####################################################

import pickle, json, datetime, time, logging
from .pyqt import *
from . import util
from .util import CUtil, EventKind
from .models import QObjectHelper
from .server_types import User, Server, HTTPError
from .session import Session


log = logging.getLogger(__name__)


def find_global_type(attr):
    value = getattr(util, attr)
    if isinstance(value, int):  # true for int's and PyQt enums
        return int
    else:
        return type(value)


class QmlUtil(QObject, QObjectHelper):
    """This module exposed to qml."""

    CONSTANTS = [
        "QRC",
        "QRC_QML",
        "IS_IOS",
        "IS_DEV",
        "EMPTY_TEXT",
        "DEFAULT_USE_TIME",
        "ENABLE_DATE_BUDDIES",
        "ENABLE_SERVER_UPLOADER",
        "ENABLE_SERVER_VIEW",
        "HARDWARE_UUID",
        "MACHINE_NAME",
        "IS_UI_DARK_MODE",
        "DRAWER_WIDTH",
        "DRAWER_OVER_WIDTH",
        "BLANK_DATE_TEXT",
        "BLANK_TIME_TEXT",
        "PERSON_SIZE_NAMES",
        "PERSON_KIND_NAMES",
        "EMOTION_INTENSITY_NAMES",
        "ABLETON_COLORS",
        "ANIM_DURATION_MS",
        "ANIM_EASING",
        "FONT_FAMILY",
        "FONT_FAMILY_TITLE",
        "TEXT_FONT_SIZE",
        "HELP_FONT_SIZE",
        "NODAL_COLOR",
        "QML_MARGINS",
        "QML_ITEM_MARGINS",
        "QML_SPACING",
        "QML_FIELD_WIDTH",
        "QML_FIELD_HEIGHT",
        "QML_TITLE_FONT_SIZE",
        "QML_SMALL_TITLE_FONT_SIZE",
        "QML_ITEM_HEIGHT",
        "QML_ITEM_LARGE_HEIGHT",
        "QML_ITEM_BG",
        "QML_ITEM_ALTERNATE_BG",
        "QML_ITEM_BORDER_COLOR",
        "QML_SMALL_BUTTON_WIDTH",
        "QML_MICRO_BUTTON_WIDTH",
        "QML_HEADER_HEIGHT",
        "QML_HEADER_BG",
        "QML_WINDOW_BG",
        "QML_CONTROL_BG",
        "QML_TEXT_COLOR",
        "QML_DROP_SHADOW_COLOR",
        "QML_SELECTION_TEXT_COLOR",
        "QML_HIGHLIGHT_TEXT_COLOR",
        "QML_ACTIVE_TEXT_COLOR",
        "QML_INACTIVE_TEXT_COLOR",
        "QML_HIGHLIGHT_COLOR",
        "QML_SELECTION_COLOR",
        "QML_SAME_DATE_HIGHLIGHT_COLOR",
        "QML_NODAL_COLOR",
        "EVENT_PROPS_HELP_TEXT",
        "EMOTION_PROPS_HELP_TEXT",
        "CURRENT_DATE_INDICATOR_WIDTH",
        "ITEM_CUTOFF",
        "ITEM_FUSION",
        "ITEM_CONFLICT",
        "ITEM_PROJECTION",
        "ITEM_DISTANCE",
        "ITEM_AWAY",
        "ITEM_TOWARD",
        "ITEM_DEFINED_SELF",
        "ITEM_INSIDE",
        "ITEM_OUTSIDE",
        "ITEM_RECIPROCITY",
        "VAR_VALUE_UP",
        "VAR_VALUE_DOWN",
        "VAR_VALUE_SAME",
        "VAR_ANXIETY_UP",
        "VAR_ANXIETY_DOWN",
        "VAR_ANXIETY_SAME",
        "VAR_FUNCTIONING_UP",
        "VAR_FUNCTIONING_DOWN",
        "VAR_FUNCTIONING_SAME",
        "S_PERSON_NOT_FOUND",
    ]
    QObjectHelper.registerQtProperties(
        [
            {
                "attr": attr,
                "global": True,
                # 'constant': True,
                "type": find_global_type(attr),
            }
            for attr in CONSTANTS
        ]
        + [{"attr": "EventKind", "type": "QVariant"}],
        globalContext=util.__dict__,
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("util")
        QApplication.instance().paletteChanged.connect(self.initColors)
        self._httpReplies = {}
        self._lastHttpRequestId = 0
        self._httpRequests = []
        self.initQObjectHelper()

    def initColors(self):
        darkLightMode = util.prefs().value(
            "darkLightMode", defaultValue=util.PREFS_UI_HONOR_SYSTEM_DARKLIGHT_MODE
        )
        if darkLightMode == util.PREFS_UI_HONOR_SYSTEM_DARKLIGHT_MODE:
            util.IS_UI_DARK_MODE = CUtil.instance().isUIDarkMode()
        elif darkLightMode == util.PREFS_UI_DARK_MODE:
            util.IS_UI_DARK_MODE = True
        elif darkLightMode == util.PREFS_UI_LIGHT_MODE:
            util.IS_UI_DARK_MODE = False
        #
        util.HIGHLIGHT_COLOR = None
        util.SAME_DATE_HIGHLIGHT_COLOR = None
        if QApplication.instance():
            util.SELECTION_COLOR = (
                CUtil.instance().appleControlAccentColor()
            )  # requires app instance?
            # attempt to make very light selection colors show up better on white background
            # if not IS_UI_DARK_MODE and luminanceOf(SELECTION_COLOR) > .7:
            #     SELECTION_COLOR = QColor(255, 0, 0, 150) # from 1.0.0b9
            util.HIGHLIGHT_COLOR = util.lightenOpacity(util.SELECTION_COLOR, 0.5)
            util.SAME_DATE_HIGHLIGHT_COLOR = util.lightenOpacity(
                util.SELECTION_COLOR, 0.35
            )
            if QApplication.activeWindow():
                palette = QApplication.activeWindow().palette()
            else:
                palette = QApplication.palette()  # should probably replace with
        else:
            util.SELECTION_COLOR = QColor(255, 0, 0, 150)  # from 1.0.0b9
            palette = QPalette()
        # QColor
        # util.TEXT_COLOR = palette.color(QPalette.Text)
        # util.ACTIVE_TEXT_COLOR = palette.color(QPalette.Active, QPalette.Text)
        if util.IS_UI_DARK_MODE:
            util.TEXT_COLOR = QColor(Qt.white)
            util.ACTIVE_TEXT_COLOR = QColor(Qt.white)
        else:
            util.TEXT_COLOR = QColor(Qt.black)
            util.ACTIVE_TEXT_COLOR = QColor(Qt.black)
        util.PEN = QPen(
            QBrush(util.TEXT_COLOR), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin
        )
        if util.HIGHLIGHT_COLOR is None:
            util.HIGHLIGHT_COLOR = palette.color(QPalette.Highlight)
        if util.SAME_DATE_HIGHLIGHT_COLOR is None:
            util.SAME_DATE_HIGHLIGHT_COLOR = lightenOpacity(util.SELECTION_COLOR, 0.7)
        util.SELECTION_TEXT_COLOR = util.contrastTo(util.SELECTION_COLOR)
        util.HIGHLIGHT_TEXT_COLOR = util.contrastTo(util.HIGHLIGHT_COLOR)
        util.HOVER_COLOR = util.SELECTION_COLOR
        # Dark mode theming
        if util.IS_UI_DARK_MODE:
            util.WINDOW_BG = QColor("#1e1e1e")
            util.SNAP_PEN = QPen(util.SELECTION_COLOR.lighter(150), 0.5)
            util.GRID_COLOR = QColor("#767676")
            util.NODAL_COLOR = QColor("#fcf5c9")
            util.QML_ITEM_BG = "#373534"
            util.QML_ITEM_ALTERNATE_BG = "#2d2b2a"
            util.QML_ITEM_BORDER_COLOR = "#4d4c4c"
            util.QML_HEADER_BG = "#323232"
            util.CONTROL_BG = QColor(util.QML_ITEM_ALTERNATE_BG)
            # util.INACTIVE_TEXT_COLOR = palette.color(QPalette.Disabled, QPalette.Text) # doesn't work
            util.INACTIVE_TEXT_COLOR = util.CONTROL_BG.lighter(160)  # workaround
            util.DROP_SHADOW_COLOR = QColor(util.QML_HEADER_BG).lighter(110)
        else:
            util.WINDOW_BG = QColor("white")
            util.CONTROL_BG = QColor("#e0e0e0")
            util.GRID_COLOR = QColor("lightGrey")
            util.SNAP_PEN = QPen(QColor(0, 0, 255, 100), 0.5)
            util.NODAL_COLOR = QColor("pink")
            util.QML_ITEM_BG = "white"
            util.QML_ITEM_ALTERNATE_BG = "#eee"
            util.QML_ITEM_BORDER_COLOR = "lightGrey"
            util.QML_HEADER_BG = "white"
            # util.QML_CONTROL_BG = '#ffffff'
            # util.INACTIVE_TEXT_COLOR = palette.color(QPalette.Disabled, QPalette.Text) # doesn't work
            util.INACTIVE_TEXT_COLOR = QColor("grey")  # workaround
            util.DROP_SHADOW_COLOR = QColor(util.QML_HEADER_BG).darker(105)
        util.SELECTION_PEN = QPen(util.SELECTION_COLOR, 3)
        # c = QColor(util.SELECTION_COLOR.lighter(150))
        # c.setAlpha(30)
        util.SELECTION_BRUSH = QBrush(util.HIGHLIGHT_COLOR)
        util.HOVER_PEN = util.SELECTION_PEN
        util.HOVER_BRUSH = util.SELECTION_BRUSH
        # Qml
        util.QML_WINDOW_BG = util.WINDOW_BG.name()
        util.QML_CONTROL_BG = util.CONTROL_BG.name()
        util.QML_TEXT_COLOR = util.TEXT_COLOR.name()
        util.QML_DROP_SHADOW_COLOR = util.DROP_SHADOW_COLOR.name()
        util.QML_INACTIVE_TEXT_COLOR = util.INACTIVE_TEXT_COLOR.name()
        util.QML_ACTIVE_TEXT_COLOR = util.ACTIVE_TEXT_COLOR.name()
        util.QML_SELECTION_COLOR = util.SELECTION_COLOR.name()
        util.QML_SELECTION_TEXT_COLOR = util.SELECTION_TEXT_COLOR.name()
        util.QML_HIGHLIGHT_TEXT_COLOR = util.HIGHLIGHT_TEXT_COLOR.name()
        util.QML_HIGHLIGHT_COLOR = util.HIGHLIGHT_COLOR.name()  # also current
        util.QML_SAME_DATE_HIGHLIGHT_COLOR = util.SAME_DATE_HIGHLIGHT_COLOR.name()
        util.QML_NODAL_COLOR = util.NODAL_COLOR.name()
        #
        self.refreshAllProperties()

    def get(self, attr):
        if attr == "EventKind":
            return {k.name: k.value for k in util.EventKind}
        else:
            return super().get(attr)

    # If no time zone is entered, js Date parses a string as if it were UTC,
    # then adjusts it to local time. So '1/1/2018' becomes 1/1/2018 0:00 GMT, then
    # the returned Date object is 12/31/2017 16:00 GMT-8 for Alaska. All we need is
    # year, month, and day, to be accurate so it is automatically converted to
    # a QDateTime by Qml (which uses local tz), then to QDate by ModelHelper.
    # So add the tz offset so the time is local but also represents the actual string parsed.
    @pyqtSlot(str, str, result=QDateTime)
    def validatedDateTimeText(self, dateText, timeText=None):
        """Parse a date as if it were local TZ, instead of JS Date which assumes
        UTC and then automatically adjusting to to local time resulting in incorrect
        mm, dd, yyyy values.
        """
        dateText = dateText.strip()
        timeText = timeText.strip()
        ret = util.validatedDateTimeText(dateText, timeText)
        if ret:
            return ret
        else:
            return QDateTime()

    @pyqtSlot(QDateTime, result=str)
    def dateString(self, dateTime):
        if dateTime.isNull():
            return util.BLANK_DATE_TEXT
        else:
            return dateTime.toString("MM/dd/yyyy")

    @pyqtSlot(QDateTime, result=str)
    def timeString(self, dateTime):
        if dateTime.isNull():
            return util.BLANK_DATE_TEXT
        else:
            return dateTime.toString("h:mm ap")

    @pyqtSlot(QVariant, str, result=QVariant)
    def pyCall(self, o, attr):
        x = getattr(o, attr)
        if callable(x):
            return x()
        else:
            return x

    @pyqtSlot(result=str)
    def newPassword(self):
        return util.newPassword()

    @pyqtSlot(QItemSelectionModel, QModelIndex, QModelIndex, int)
    def doItemSelection(self, selectionModel, fromIndex, toIndex, flags):
        """Don't know how to call `select(selection, flags)` from Qml."""
        _flags = QItemSelectionModel.SelectionFlags(flags)
        selectionModel.select(QItemSelection(fromIndex, toIndex), _flags)

    @pyqtSlot(QItemSelectionModel, list, int)
    def doRowsSelection(self, selectionModel, rows, flags):
        _flags = QItemSelectionModel.SelectionFlags(flags)
        model = selectionModel.model()
        selection = QItemSelection()
        for row in rows:
            index = model.index(row, 1)
            selection.select(index, index)
        selectionModel.select(selection, _flags)

    @pyqtSlot(QItemSelectionModel, int, result=bool)
    def isRowSelected(self, selectionModel, row):
        if row >= selectionModel.model().rowCount():  # occurs on deinit
            return False
        else:
            return selectionModel.isRowSelected(
                row, selectionModel.model().index(-1, -1)
            )

    @pyqtSlot(int, result=str)
    def personSizeNameFromSize(self, size):
        return util.personSizeNameFromSize(size)

    @pyqtSlot(QAbstractItemModel)
    def printModel(self, model):
        util.printModel(model)

    @pyqtSlot(bool, bool, bool, result=str)
    def itemBgColor(self, selected, current, alternate):
        """Dynamic color depends on item disposition."""
        if selected:
            return self.QML_SELECTION_COLOR
        elif current:
            return self.QML_HIGHLIGHT_COLOR
        elif alternate:
            return self.QML_ITEM_ALTERNATE_BG
        else:
            return self.QML_ITEM_BG

    @pyqtSlot(bool, bool, result=str)
    def textColor(self, selected, current):
        """Dynamic color depends on item disposition."""
        if selected:
            return self.QML_SELECTION_TEXT_COLOR
        elif current:
            return self.QML_HIGHLIGHT_TEXT_COLOR
        else:
            return self.QML_TEXT_COLOR

    @pyqtSlot(QColor, result=QColor)
    def contrastTo(self, color):
        return util.contrastTo(color)

    @pyqtSlot(str)
    def openUrl(self, urlString):
        QDesktopServices.openUrl(QUrl(urlString))

    jsServerHttpFinished = pyqtSignal(int, QJSValue, arguments=["id", "response"])

    @pyqtSlot(QVariant, int, str, str)
    @pyqtSlot(QVariant, int, str, str, QVariant)
    def jsServerHttp(self, session, requestId, method, path, args=None):
        # log.info(f"{session}, {requestId}, {method}, {path}, {args}")
        if args is not None:
            data = args.toVariant()
            bdata = pickle.dumps(data)
        else:
            bdata = b""
        reply = session.server().nonBlockingRequest(method, path, bdata)

        class HTTPRequest:
            def __init__(self, qmlUtil, jsId, reply):
                self.qmlUtil = qmlUtil
                self.jsId = jsId
                self.reply = reply
                self.reply.sslErrors.connect(self._onSSLErrors)
                self.reply.finished.connect(self.onFinished)

            def _onSSLErrors(self):
                pass

            def onFinished(self):
                self.reply.sslErrors.disconnect(self._onSSLErrors)
                self.reply.finished.disconnect(self.onFinished)
                # Super janky signal-and-id based callback-based mechanism because
                # `callback` (QJSValue) was becoming not callable by the time the http
                # request finished!  WTF!?!?!
                # Can maybe try QJSValue(callback) to retain callable status?
                # - https://wiki.python.org/moin/PyQt/QML%20callback%20function
                # self.here(requestId, reply.url(), reply.attribute(QNetworkRequest.HttpStatusCodeAttribute))
                args = QApplication.instance().qmlEngine().newObject()
                try:
                    session.server().checkHTTPReply(reply, quiet=False)
                except HTTPError as e:
                    pass
                bdata = reply.readAll().data()
                if bdata:
                    try:
                        data = pickle.loads(bdata)
                    except pickle.UnpicklingError:
                        data = bdata.decode("utf-8")

                    def myconverter(o):
                        if isinstance(o, datetime.datetime):
                            return o.isoformat()

                    jsonString = json.dumps(
                        data, default=myconverter
                    )  # How to PyObject to QJSValue?
                    args.setProperty("_data", jsonString)
                httpCode = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
                if httpCode is None:
                    httpCode = 0
                args.setProperty("status_code", httpCode)
                if httpCode != 200 and reply.hasRawHeader(b"FD-User-Message"):
                    user_message = bytes(reply.rawHeader(b"FD-User-Message")).decode(
                        "utf-8"
                    )
                    args.setProperty("user_message", user_message)
                self.qmlUtil.jsServerHttpFinished.emit(self.jsId, args)
                self.qmlUtil._httpRequests.remove(self)

        self._httpRequests.append(HTTPRequest(self, requestId, reply))

    @pyqtSlot(str, str, result=bool)
    def questionBox(self, title, text):
        btn = QMessageBox.question(QApplication.activeWindow(), title, text)
        return btn == QMessageBox.Yes

    @pyqtSlot(str, str)
    def informationBox(self, title, text):
        QMessageBox.information(QApplication.activeWindow(), title, text)

    @pyqtSlot(str, str)
    def criticalBox(self, title, text):
        QMessageBox.critical(QApplication.activeWindow(), title, text)

    @pyqtSlot(str, result=float)
    def salesTaxRate(self, zipCode):
        ret = util.SALES_TAX_RATES.get(zipCode)
        if ret is None:
            return -1
        else:
            return ret

    @pyqtSlot(result=float)
    def time(self):
        return time.time()

    @pyqtSlot(str, result=bool)
    def isMonadicEventKind(self, x):
        if x == "":
            return False
        return EventKind.isMonadic(EventKind(x))

    @pyqtSlot(str, result=bool)
    def isDyadicEventKind(self, x):
        if x == "":
            return False
        return EventKind.isDyadic(EventKind(x))

    @pyqtSlot(str, result=bool)
    def isPairBondEventKind(self, x):
        if x == "":
            return False
        return EventKind.isPairBond(EventKind(x))

    @pyqtSlot(str, result=bool)
    def isChildEventKind(self, x):
        if x == "":
            return False
        return EventKind.isChild(EventKind(x))

    @pyqtSlot(str, result=bool)
    def isCustomEventKind(self, x):
        if x == "":
            return False
        return EventKind.isCustom(EventKind(x))

    @pyqtSlot(str, result=str)
    def eventKindEventLabelFor(self, x: str):
        if x:
            return EventKind.eventLabelFor(EventKind(x))
        else:
            return ""

    @pyqtSlot(result=list)
    def eventKindMenuItems(self):
        return [self.eventKindEventLabelFor(x) for x in EventKind]

        def _section(x: str):
            kind = EventKind(x)
            if EventKind.isPairBond(kind):
                return "Pair-Bond"
            elif EventKind.isMonadic(kind):
                return "Monadic"
            elif EventKind.isDyadic(kind):
                return "Move"
            elif kind == EventKind.CustomIndividual:
                return "Custom"
            else:
                raise ValueError(f"Unknown EventKind: {x}")

        ret = []
        lastSection = None
        for i, x in enumerate(self.eventKindValues()):
            section = _section(x)
            if i > 0 and lastSection != section:
                isFirstInSection = True
            else:
                isFirstInSection = False
            lastSection = section
            ret.append(
                {
                    "label": EventKind.menuLabelFor(EventKind(x)),
                    "section": _section(x),
                    "isFirstInSection": isFirstInSection,
                }
            )
        # import pprint

        # log.info(pprint.pformat(ret, indent=4))
        return ret

    @pyqtSlot(result=list)
    def eventKindLabels(self):
        return [EventKind.menuLabelFor(EventKind(x)) for x in self.eventKindValues()]

    @pyqtSlot(result=list)
    def eventKindValues(self):
        return EventKind.menuOrder()

    @pyqtSlot(int, result=str)
    def personKindFromIndex(self, index):
        return util.personKindFromIndex(index)

    @pyqtSlot(str, result=int)
    def personKindIndexFromKind(self, index):
        return util.personKindIndexFromKind(index)

    @pyqtSlot(QObject, result=QObject)
    def nextItemInFocusChain(self, item):
        nextItem = item.nextItemInFocusChain()
        while not nextItem.isVisible() or not nextItem.isEnabled():
            nextItem = item.nextItemInFocusChain()
        nextItemParent = nextItem.parent()
        while not nextItemParent.objectName():
            nextItemParent = nextItemParent.parent()
        log.info(
            f"nextItemInFocusChain: {nextItemParent.objectName()}.{nextItem.objectName()}"
        )
        return nextItemParent
