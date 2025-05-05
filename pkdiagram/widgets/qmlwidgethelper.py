import time
import logging
from typing import Union

from pkdiagram.pyqt import (
    pyqtSignal,
    Q_ARG,
    Q_RETURN_ARG,
    Qt,
    QObject,
    QApplication,
    QQuickWidget,
    QQuickItem,
    QUrl,
    QRectF,
    QMetaObject,
    QAbstractItemModel,
    QVariant,
    QApplication,
    QPointF,
)
from pkdiagram import util
from pkdiagram.models import QObjectHelper


log = logging.getLogger(__name__)


class QmlWidgetHelper(QObjectHelper):

    DEBUG = False
    DEFER_UNTIL_SHOW = True

    qmlFocusItemChanged = pyqtSignal(QQuickItem)

    _cache = {}

    def initQmlWidgetHelper(self, engine, source: Union[str, QUrl]):
        self._engine = engine
        if isinstance(source, QUrl):
            self._qmlSource = source
        else:
            self._qmlSource = util.QRC_QML + source
        self._qmlItemCache = {}
        self.qml = None
        self.initQObjectHelper()

    def qmlEngine(self):
        return self._engine

    def isQmlReady(self):
        return bool(self.qml)

    def onStatusChanged(self, status):
        pass
        # if util.IS_TEST:
        #     self.here(util.qenum(QQuickWidget, self.qml.status()))

    def checkInitQml(self):
        """Returns True if initialized on this call."""
        if self.qml:
            return False

        start_time = time.time()
        self.qml = QQuickWidget(self._engine, self)
        self.qml.statusChanged.connect(self.onStatusChanged)
        self.qml.setFormat(util.SURFACE_FORMAT)
        self.qml.setResizeMode(QQuickWidget.SizeRootObjectToView)
        if isinstance(self._qmlSource, QUrl):
            fpath = self._qmlSource
        elif self._qmlSource.startswith("qrc:"):
            fpath = QUrl(self._qmlSource)
        else:
            fpath = QUrl.fromLocalFile(self._qmlSource)
        # log.info(f"Loading QML: {fpath}")
        self.qml.setSource(fpath)
        if self.qml.status() == QQuickWidget.Error:
            for error in self.qml.errors():
                log.error(error.toString(), exc_info=True)
            raise RuntimeError(
                "Could not load qml component from: %s" % self._qmlSource
            )
        for k, v in self.qml.rootObject().__dict__:
            if not hasattr(self, k) and isinstance(v, pyqtSignal):
                self.info(f"Mapped pyqtSignal on [{self.objectName()}]: {k}")
                setattr(self, k, v)

        self.onInitQml()
        tot_time = time.time() - start_time
        # log.info(f"QmlWidgetHelper.initQmlWidgetHelper() took {tot_time:.2f}s")
        return True

    def onInitQml(self):
        self.qml.rootObject().window().activeFocusItemChanged.connect(
            self.onActiveFocusItemChanged
        )

    def deinit(self):
        if getattr(self, "qml", None):
            # Prevent qml exceptions when context props are set to null
            self.qml.rootObject().window().activeFocusItemChanged.disconnect(
                self.onActiveFocusItemChanged
            )
            self.qml.setSource(QUrl(""))
            self.qml = None

    def onActiveFocusItemChanged(self):
        """Allow to avoid prev/next layer shortcut for cmd-left|right"""
        item = self.qml.rootObject().window().activeFocusItem()
        self.qmlFocusItemChanged.emit(item)

    ##
    ## Test utils
    ##

    @classmethod
    def deepFind(cls, parent, objectName):
        """more in-depth recursive QObject search."""
        ret = None
        for child in parent.children():
            if child.objectName() == objectName:
                ret = child
            else:
                ret = cls.deepFind(child, objectName)
            if ret:
                return ret

    def findItem(self, objectName: str, noerror=False) -> QQuickItem:
        if isinstance(objectName, QQuickItem):
            return objectName
        if objectName in self._qmlItemCache:
            return self._qmlItemCache[objectName]
        parts = objectName.split(".")
        item = self.qml.rootObject()
        foundParts = []
        for partName in parts:
            _item = item.findChild(QObject, partName)
            if _item:
                item = _item
            else:
                _item = item.property(partName)
                if not _item and not noerror:
                    raise RuntimeError(
                        "Could not find item: %s" % ".".join(foundParts + [partName])
                    )
            foundParts.append(partName)
        self._qmlItemCache[objectName] = item
        return item

    def hasItem(self, objectName):
        return self.findItem(objectName, noerror=True) is not None

    def rootProp(self, attr):
        """
        This goes away an in ideal design where this is just a QQuickWidget and
        there is no self.qml. Then you just do
        widget.property('myItem').property('visible'), etc.
        """
        return self.qml.rootObject().property(attr)

    def setRootProp(self, attr, value):
        self.qml.rootObject().setProperty(attr, value)

    def itemProp(self, objectName, attr):
        item = self.findItem(objectName)
        propertyNames = [
            item.metaObject().property(i).name()
            for i in range(item.metaObject().propertyCount())
        ]
        if not attr in propertyNames:
            raise AttributeError(f"Property '{attr}' not found on {objectName}")
        return item.property(attr)

    def setItemProp(self, objectName, attr, value):
        item = self.findItem(objectName)
        item.setProperty(attr, value)

    def focusItem(self, item: Union[QQuickItem, str]):
        if isinstance(item, str):
            item = self.findItem(item)
        if not self.isActiveWindow():
            # self.here('Setting active window to %s, currently %s' % (self, QApplication.activeWindow()))
            QApplication.setActiveWindow(self)
            if self.DEBUG:
                log.info(f'QmlWidgetHelper.focusItem("{item.objectName()}")')
            util.qtbot.waitActive(self)
            if not self.isActiveWindow():
                raise RuntimeError(
                    "Could not set activeWindow to %s, currently is %s"
                    % (self, QApplication.activeWindow())
                )
            # else:
            #     Debug('Success setting active window to', self)
        assert (
            item.property("enabled") == True
        ), f"The item {item.objectName()} cannot be focused if it is not enabled."
        if self.DEBUG:
            log.info(f'QmlWidgetHelper.focusItem("{item.objectName()}")')
        self.mouseClickItem(item)
        if not item.hasActiveFocus():
            item.forceActiveFocus()  # in case mouse doesn't work if item out of view
            util.waitUntil(lambda: item.hasActiveFocus())
        if not item.hasFocus():
            item.setFocus(True)
            util.waitUntil(lambda: item.hasFocus())
        if not item.hasActiveFocus():
            msg = "Could not set active focus on `%s`" % item.objectName()
            if not self.isActiveWindow():
                raise RuntimeError(msg + ", window is not active.")
            elif not item.isEnabled():
                raise RuntimeError(msg + ", item is not enabled.")
            elif not item.isVisible():
                raise RuntimeError(msg + ", item is not visible.")
            else:
                if False and util.IS_TEST:
                    pngPath = util.dumpWidget(self)
                else:
                    pngPath = None
                itemRect = QRectF(
                    item.property("x"),
                    item.property("y"),
                    item.property("width"),
                    item.property("height"),
                )
                msg += ", reason unknown (item rect: %s)" % itemRect
                if pngPath:
                    msg += "\n    - Widget dumped to: %s" % pngPath
                msg += "\n    - self.qml                  : %s" % self.qml
                msg += (
                    "\n    - QApplication.focusWidget(): %s"
                    % QApplication.focusWidget()
                )
                msg += "\n    - root item size: %s, %s" % (
                    self.qml.rootObject().property("width"),
                    self.qml.rootObject().property("height"),
                )
                raise RuntimeError(msg)
        return item

    def resetFocusItem(self, item: QQuickItem):
        if self.DEBUG:
            log.info(f"QmlWidgetHelper.resetFocus({self._itemString(item)})")
        item.setProperty("focus", False)
        if item.hasActiveFocus():
            self.qml.rootObject().forceActiveFocus()  # TextField?
            if item.hasActiveFocus():
                raise RuntimeError("Could not re-set active focus.")

    def resetFocus(self, objectName):
        item = self.findItem(objectName)
        self.resetFocusItem(item)

    def keyClickItem(self, item: QQuickItem, key, resetFocus=True):
        self.focusItem(item)
        if self.DEBUG:
            log.info(f'QmlWidgetHelper.keyClick("{self._itemString(item)}", {key})')
        util.qtbot.keyClick(self.qml, key)
        if resetFocus:
            self.resetFocus(item)
        QApplication.processEvents()

    def keyClick(self, objectName, key, resetFocus=True):
        item = self.findItem(objectName)

    def keyClicksItem(
        self, item: QQuickItem, s: str, resetFocus=True, returnToFinish=True
    ):
        objectName = item.objectName()
        self.focusItem(item)
        if self.DEBUG:
            log.info(
                f'QmlWidgetHelper.keyClicksItem("{objectName}", "{s}", resetFocus={resetFocus}, returnToFinish={returnToFinish})'
            )
        util.qtbot.keyClicks(self.qml, s)
        if returnToFinish:
            if self.DEBUG:
                log.info(
                    f'QmlWidgetHelper.keyClicksItem[returnToFinish]("{objectName}", {s})'
                )
            util.qtbot.keyClick(self.qml, Qt.Key_Return)  # only for TextInput?
        if resetFocus:
            self.resetFocusItem(item)
        QApplication.processEvents()

    def keyClicks(self, objectName: str, s, resetFocus=True, returnToFinish=True):
        item = self.findItem(objectName)
        self.keyClicksItem(
            item, s, resetFocus=resetFocus, returnToFinish=returnToFinish
        )

    def keyClicksClearItem(self, item: QQuickItem):
        self.focusItem(item)
        item.selectAll()
        while item.property("text") not in (
            "",
            util.BLANK_DATE_TEXT,
            util.BLANK_TIME_TEXT,
        ):
            prevText = item.property("text")
            self.keyClickItem(item, Qt.Key_Backspace)
            # if item.property("text") != prevText:
            #     break
        self.resetFocusItem(item)
        itemText = item.property("text")
        assert itemText in (
            "",
            util.BLANK_DATE_TEXT,
            util.BLANK_TIME_TEXT,
        ), f"Could not clear text for {self._itemString(item)} (text = '{itemText}')"

    def keyClicksClear(self, objectName):
        item = self.findItem(objectName)
        self.keyClicksClearItem(item)

    def _itemString(self, item: QQuickItem) -> str:
        if item:
            return f'{item.metaObject().className()}["{item.objectName()}"], parent: {item.parent().metaObject().className()}]'
        else:
            return "None"

    def mouseClickItem(self, item: QQuickItem, button=Qt.LeftButton, pos=None):
        if pos is None:
            rect = item.mapRectToScene(
                QRectF(0, 0, item.property("width"), item.property("height"))
            ).toRect()
            pos = rect.center()

        # validation checks
        if not item.property("visible"):
            log.warning(f"Cannot click '{item.objectName()}' since it is not visible")
        if not item.property("enabled"):
            log.warning(f"Cannot click '{item.objectName()}' since it is not enabled")
        if self.DEBUG:
            log.info(
                f"QmlWidgetHelper.mouseClickItem('{self._itemString(item)}', {button}, {pos}) (rect: {rect})"
            )
        util.qtbot.mouseClick(self.qml, button, Qt.NoModifier, pos)

    def mouseClick(self, objectName, button=Qt.LeftButton, pos=None):
        if isinstance(objectName, str):
            item = self.findItem(objectName)
        else:
            item = objectName
        assert (
            item.property("enabled") == True
        ), f"{self.rootProp('objectName')}.{objectName} is not enabled"
        self.mouseClickItem(item, button=button)

    def mouseDClickItem(self, item: QQuickItem, button=Qt.LeftButton, pos=None):
        if not item.property("visible"):
            log.warning(
                f"Cannot double-click '{item.objectName()}' since it is not visible"
            )
        if not item.property("enabled"):
            log.warning(
                f"Cannot double-click '{item.objectName()}' since it is not enabled"
            )
        if pos is None:
            rect = item.mapRectToScene(
                QRectF(0, 0, item.property("width"), item.property("height"))
            ).toRect()
            pos = rect.center()
        if self.DEBUG:
            log.info(
                f'QmlWidgetHelper.mouseDClickItem("{item.objectName()}", {button})'
            )
        util.qtbot.mouseDClick(self.qml, button, Qt.NoModifier, pos)

    def mouseDClick(self, objectName, button=Qt.LeftButton, pos=None):
        if isinstance(objectName, str):
            item = self.findItem(objectName)
        else:
            item = objectName
        assert item.property("enabled") == True
        self.mouseDClickItem(item, button=button)

    def clickTabBarButton(self, item: Union[QQuickWidget, str], iTab):
        if isinstance(item, str):
            item = self.findItem(item)
        rect = item.mapRectToItem(
            self.qml.rootObject(), QRectF(0, 0, item.width(), item.height())
        ).toRect()
        # count = item.property('count')
        # tabWidth = rect.width() / count
        # tabStartX = tabWidth * iTab
        # tabEndX = tabWidth * iTab + tabWidth
        # tabCenterX = tabStartX + ((tabEndX - tabStartX) / 2)
        # tabCenterY = rect.height() / 2
        # tabCenter = QPoint(tabCenterX, tabCenterY)
        # self.qml.setFocus()
        # util.qtbot.mouseClick(self.qml, Qt.LeftButton, Qt.NoModifier, tabCenter)
        item.setProperty("currentIndex", iTab)
        currentIndex = item.property("currentIndex")
        if not currentIndex == iTab:
            focusItem = self.rootProp("focusItem")
            raise RuntimeError(
                "Unable to click tab bar button index %i for `%s`. `currentIndex` is still %i (focus widget: %s, focusItem: %s)"
                % (
                    iTab,
                    item.objectName(),
                    currentIndex,
                    QApplication.focusWidget(),
                    focusItem.objectName(),
                )
            )

    def clickListViewItem(self, item: Union[QQuickItem, str], index):
        if isinstance(item, str):
            item = self.findItem(item)
        item.setProperty("currentIndex", index)

    def clickListViewItem_actual(
        self, item: Union[QQuickItem, str], rowText, modifiers=Qt.NoModifier
    ):
        if isinstance(item, str):
            item = self.findItem(item)

        assert (
            item.property("enabled") == True
        ), "Cannot click ListView item if the ListView is disabled"

        model = item.property("model")
        delegate = None
        for newCurrentIndex, row in enumerate(range(model.rowCount())):
            text = model.data(model.index(row, 0))
            if text == rowText:
                delegate = item.itemAtIndex(row)
                break
        assert delegate, f"ListView row with text '{rowText}' not found"

        prevCurrentIndex = item.property("currentIndex")
        assert isinstance(
            prevCurrentIndex, int
        ), f'Expected "currentIndex" to be an int, is {item.objectName()} actually a ComboBox?'
        log.debug(f"Clicking ListView item: '{rowText}' (index: {row})")
        self.mouseClickItem(item)
        if hasattr(item, "model") and isinstance(item.model, callable):
            model = item.model()
        else:
            model = item.property("model")
        assert model.data(model.index(row, 0)) == rowText
        # assert (
        #     item.property("currentIndex") == newCurrentIndex
        # ), f"Could not set currentIndex to {newCurrentIndex} for {objectName} (was {prevCurrentIndex})"

    def clickTimelineViewItem(
        self, objectName, cellText, column=0, modifiers=Qt.NoModifier
    ):
        item = self.findItem(objectName)
        model = item.property("model")
        for row in range(model.rowCount()):
            text = model.data(model.index(row, column))
            if text == cellText:
                break
        assert text == cellText  # cell found
        assert self.itemProp(objectName, "enabled") == True
        # calc visual rect
        columnWidth = lambda x: QMetaObject.invokeMethod(
            item,
            "columnWidthProvider",
            Qt.DirectConnection,
            Q_RETURN_ARG(QVariant),
            Q_ARG(QVariant, x),
        )
        x = sum([columnWidth(i) for i in range(column)])
        y = util.QML_ITEM_HEIGHT * row - 1
        w = columnWidth(column)
        h = util.QML_ITEM_HEIGHT
        self.findItem("ensureVisAnimation").setProperty("duration", 1)
        ensureVisible = lambda x: QMetaObject.invokeMethod(
            item, "ensureVisible", Qt.DirectConnection, Q_ARG(QVariant, row)
        )
        ensureVisible(row)
        forceLayout = lambda: QMetaObject.invokeMethod(
            item, "test_updateLayout", Qt.DirectConnection
        )
        forceLayout()
        selModel = item.property("selectionModel")
        prevSelection = selModel.selectedRows()
        rect = item.mapRectToScene(QRectF(x, y, w, h))
        self.mouseClick(objectName, Qt.LeftButton, rect.center().toPoint())
        newSelection = selModel.selectedRows()
        assert prevSelection != newSelection

    def clickComboBoxItem(self, objectName, itemText, force=True):
        if isinstance(objectName, str):
            item = self.findItem(objectName)
        else:
            item = objectName
        self.mouseClick(objectName)  # for focus
        model = item.property("model")
        if isinstance(model, list):
            itemTexts = model
        elif isinstance(model, QAbstractItemModel):
            if not item.property("textRole"):
                raise TypeError(f"Expected a Qml ComboBox, got {item.objectName()}")
            textRole = item.property("textRole").encode("utf-8")
            for role, roleName in model.roleNames().items():
                if textRole == roleName:
                    break
            itemTexts = [
                model.data(model.index(row, 0), role) for row in range(model.rowCount())
            ]
        currentIndex = None
        for i, text in enumerate(itemTexts):
            if text == itemText:
                currentIndex = i
                break
        assert (
            currentIndex is not None
        ), f'Could not find ComboBox item with text "{itemText}" on "{objectName}", available values {itemTexts}'
        if self.DEBUG:
            log.info(f"Clicking ComboBox item: '{itemText}' (index: {currentIndex})")
        if force:
            item.setProperty("currentIndex", -1)
        item.setProperty("currentIndex", currentIndex)
        item.close()
        assert (
            item.property("currentText") == itemText
        ), f'Could not set `currentText` to "{itemText}" (currentIndex: {currentIndex}) on {objectName}'

        # popup = item.findChildren(QQuickItem, 'popup')[0]
        # self.recursivePrintChildren(item, 0)
        # for child in item.childItems():
        #     self.here(child.metaObject().className())
        #     for _child in child.childItems():
        #         self.here('    ', _child.metaObject().className())

    # def clickComboBoxItem_actual(self, objectName, itemText, comboBox=None):
    #     if isinstance(objectName, str):
    #         comboBox = self.findItem(objectName)
    #     else:
    #         comboBox = objectName
    #     self.mouseClick(objectName)  # for focus
    #     model = comboBox.property("model")
    #     if isinstance(model, list):
    #         itemTexts = model
    #     elif isinstance(model, QAbstractItemModel):
    #         if not comboBox.property("textRole"):
    #             raise TypeError(f"Expected a Qml ComboBox, got {comboBox.objectName()}")
    #         textRole = comboBox.property("textRole").encode("utf-8")
    #         for role, roleName in model.roleNames().items():
    #             if textRole == roleName:
    #                 break
    #         itemTexts = [
    #             model.data(model.index(row, 0), role) for row in range(model.rowCount())
    #         ]
    #     currentIndex = None
    #     for i, text in enumerate(itemTexts):
    #         if text == itemText:
    #             currentIndex = i
    #             break
    #     assert (
    #         currentIndex is not None
    #     ), f'Could not find ComboBox item with text "{itemText}" on "{objectName}", available values {itemTexts}'
    #     if self.DEBUG:
    #         log.info(f"Clicking ComboBox item: '{itemText}' (index: {currentIndex})")
    #     self.mouseClick(comboBox)
    #     util.dumpWidget(self)
    #     popup = comboBox.property("test_popup")
    #     popupDelegate = popup.findChild(QQuickItem, "delegate")
    #     assert self.itemProp(comboBox, "opened") == True
    #     # comboBox.setProperty("currentIndex", -1)
    #     # comboBox.setProperty("currentIndex", currentIndex)
    #     comboBox.close()
    #     if not comboBox.property("currentText") == itemText:
    #         raise RuntimeError(
    #             'Could not set `currentText` to "%s" (currentIndex: %i) on %s'
    #             % (itemText, currentIndex, objectName)
    #         )

    def assertNoTableViewItem(self, objectName, text, column):
        model = self.itemProp(objectName, "model")
        count = 0
        for row in range(model.rowCount()):
            index = model.index(row, column)
            itemS = model.index(row, column).data(Qt.DisplayRole)
            if itemS == text:
                count += 1
        assert count == 0

    def recursivePrintChildren(self, item, level):
        for child in item.childItems():
            self.here(
                "%s%s: %s"
                % ((" " * level), item.objectName(), child.metaObject().className())
            )
            self.recursivePrintChildren(child, level + 1)

    def scrollToVisible(self, flickableObjectName: str, visibleObjectName: str):
        y = self.itemProp(visibleObjectName, "y")
        self.setItemProp(flickableObjectName, "contentY", -1 * y)

    def scrollToItem(self, flickable: QQuickItem, item: QQuickItem):
        y = item.y()
        itemHeight = item.height()
        flickableHeight = flickable.property("height")
        contentY = flickable.property("contentY")
        if y < contentY:
            log.debug(f"Scrolling {flickable.objectName()} to contentY: {y}")
            flickable.setProperty("contentY", y)
        elif y + itemHeight > contentY + flickableHeight:
            log.debug(
                f"Scrolling {flickable.objectName()} to contentY: {y + itemHeight}"
            )
            flickable.setProperty("contentY", y + itemHeight)
        QApplication.processEvents()

    def scrollChildToVisible(self, flickable: QQuickItem, item: QQuickItem):
        positionInContent = item.mapToItem(
            flickable.property("contentItem"), QPointF(0, 0)
        )
        targetY = positionInContent.y()

        # Calculate the new contentY value
        contentHeight = flickable.property("contentItem").height()
        maxContentY = contentHeight - flickable.height()
        contentY = min(max(targetY, 0), maxContentY)

        # Set the contentY property to scroll
        flickable.setProperty("contentY", contentY)
