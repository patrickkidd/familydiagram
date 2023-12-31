import logging
from .pyqt import Qt, QObject, QApplication, QQuickWidget, QQuickItem, QUrl, pyqtSignal, QRectF, QMetaObject, Q_ARG, Q_RETURN_ARG, QAbstractItemModel, QVariant
from . import util
from .models import QObjectHelper


log = logging.getLogger(__name__)


class QmlWidgetHelper(QObjectHelper):
    
    def initQmlWidgetHelper(self, source, sceneModel=None, session=None):
        self._qmlSource = util.QRC_QML + source
        self._qmlItemCache = {}
        self._sceneModel = sceneModel
        self._session = session
        self.initQObjectHelper()

    @property
    def sceneModel(self):
        return self._sceneModel

    @property
    def session(self):
        return self._session

    # def __getattr__(self, attr):
    #     if not hasattr(self, attr) and \
    #        hasattr(self, 'qml') and \
    #        hasattr(self.qml.rootObject(), attr) and \
    #        isinstance(getattr(self.qml.rootObject(), attr), pyqtSignal):
    #         return getattr(self.qml.rootObject(), attr)
    #     else:
    #         return super().__getattr__(self, o)

    def isQmlReady(self):
        return hasattr(self, 'qml')
        
    def onStatusChanged(self, status):
        pass
        # if util.IS_TEST:
        #     self.here(util.qenum(QQuickWidget, self.qml.status()))

    def checkInitQml(self):
        """ Returns True if initialized on this call. """
        if hasattr(self, 'qml'):
            return False
        self.qml = QQuickWidget(QApplication.instance().qmlEngine(), self)
        self.qml.statusChanged.connect(self.onStatusChanged)
        self.qml.setFormat(util.SURFACE_FORMAT)
        self.qml.setResizeMode(QQuickWidget.SizeRootObjectToView)
        if self.layout() is None:
            raise RuntimeError('A layout must be added to a QmlWidgetHelper prior to calling initQml()')
        if self._qmlSource.startswith('qrc:'):
            fpath = QUrl(self._qmlSource)
        else:
            fpath = QUrl.fromLocalFile(self._qmlSource)
        self.qml.setSource(fpath)
        if self.qml.status() == QQuickWidget.Error:
            if util.IS_TEST:
                for error in self.qml.errors():
                    log.error(error.toString(), exc_info=True)
            raise RuntimeError('Could not load qml component from: %s' % self._qmlSource)
        # map all signals

        # properties = []
        # signals = []
        # mo = self.qml.rootObject().metaObject()
        # for i in range(mo.propertyCount()):
        #     properties.append(mo.property(i).name())
        # for i in range(mo.methodCount()):
        #     meth = mo.method(i)
        #     if meth.methodType() == QMetaMethod.Signal:
        #         signature = bytes(meth.methodSignature()).decode()
        #         attr = signature[:signature.index('(')]
        #         x = getattr(self.qml.rootObject(), attr)
        #         isPyQtSignal = 'PYQT_SIGNAL' in str(type(x))
        #         print(signature, attr, isPyQtSignal)
        #         signals.append(x)
        #         if not hasattr(self, k) and isinstance(v, pyqtSignal):
        #             self.here('Mapped pyqtSignal on [%s]: %s' % (self.objectName(), k))
        #             setattr(self, k, v)
        
        for k, v in self.qml.rootObject().__dict__:
            if not hasattr(self, k) and isinstance(v, pyqtSignal):
                self.info(f"Mapped pyqtSignal on [{self.objectName()}]: {k}")
                setattr(self, k, v)
        # for k, v in self._qmlKWArgs.items():
        #     self.qml.rootObject().setProperty(k, v)
        self.layout().addWidget(self.qml)
        for child in self.qml.rootObject().findChildren(QQuickItem):
            if child.objectName():
                self._qmlItemCache[child.objectName()] = child
        if self.sceneModel:
            self.qml.rootObject().setProperty('sceneModel', self.sceneModel)
        if self.session:
            self.qml.rootObject().setProperty('session', self.session)
        self.onInitQml()
        return True

    def onInitQml(self):
        """ Virtual """

    ##
    ## Test utils
    ##

    def waitUntil(self, condition, timeout=2000):
        util.Condition(condition=condition).wait(maxMS=timeout)

    @classmethod
    def deepFind(cls, parent, objectName):
        """ more in-depth recursive QObject search. """
        ret = None
        for child in parent.children():
            if child.objectName() == objectName:
                ret = child
            else:
                ret = cls.deepFind(child, objectName)
            if ret:
                return ret
        
    def findItem(self, objectName, noerror=False):
        if objectName in self._qmlItemCache:
            return self._qmlItemCache[objectName]
        parts = objectName.split('.')
        item = self.qml.rootObject()
        for partName in parts:
            _item = item.findChild(QObject, partName)
            if _item:
                item = _item
            # Not tested well enough
            # else:
            #     item = self.deepFind(item, partName)
        if not item and not noerror:
            raise RuntimeError('Could not find item: %s' % objectName)
        self._qmlItemCache[objectName] = item
        return item

    def hasItem(self, objectName):
        return self.findItem(objectName, noerror=True) is not None

    def rootProp(self, attr):
        return self.qml.rootObject().property(attr)

    def setRootProp(self, attr, value):
        self.qml.rootObject().setProperty(attr, value)

    def itemProp(self, objectName, attr):
        item = self.findItem(objectName)
        return item.property(attr)

    def setItemProp(self, objectName, attr, value):
        item = self.findItem(objectName)
        item.setProperty(attr, value)
    
    def focusItem(self, objectName):
        if not self.isActiveWindow():
            # self.here('Setting active window to %s, currently %s' % (self, QApplication.activeWindow()))
            QApplication.setActiveWindow(self)
            util.qtbot.waitActive(self)
            if not self.isActiveWindow():
                raise RuntimeError('Could not set activeWindow to %s, currently is %s' % (self, QApplication.activeWindow()))
            # else:
            #     Debug('Success setting active window to', self)
        item = self.findItem(objectName)
        assert item.property('enabled') == True, f"The item {objectName} cannot be focused if it is not enabled."
        self.mouseClick(objectName)
        if not item.hasActiveFocus():
            item.forceActiveFocus() # in case mouse doesn't work if item out of view
            self.waitUntil(lambda: item.hasActiveFocus())
        if not item.hasFocus():
            item.setFocus(True)
            self.waitUntil(lambda: item.hasFocus())
        if not item.hasActiveFocus():
            msg = 'Could not set active focus on `%s`' % objectName
            if not self.isActiveWindow():
                raise RuntimeError(msg + ', window is not active.')
            elif not item.isEnabled():
                raise RuntimeError(msg + ', item is not enabled.')
            elif not item.isVisible():
                raise RuntimeError(msg + ', item is not visible.')
            else:
                if util.IS_TEST:
                    pngPath = util.dumpWidget(self)
                else:
                    pngPath = None
                itemRect = QRectF(item.property('x'), item.property('y'),
                                  item.property('width'), item.property('height'))
                msg += ', reason unknown (item rect: %s)' % itemRect
                if pngPath:
                    msg += '\n    - Widget dumped to: %s' % pngPath
                msg += '\n    - self.qml                  : %s' % self.qml
                msg += '\n    - QApplication.focusWidget(): %s' % QApplication.focusWidget()
                msg += '\n    - root item size: %s, %s' % (self.qml.rootObject().property('width'), self.qml.rootObject().property('height'))
                raise RuntimeError(msg)
        return item

    def resetFocus(self, objectName):
        item = self.findItem(objectName)
        item.setProperty('focus', False)
        if item.hasActiveFocus():
            self.qml.rootObject().forceActiveFocus() # TextField?
            if item.hasActiveFocus():
                raise RuntimeError('Could not re-set active focus.')

    def keyClick(self, objectName, key, resetFocus=True):
        self.focusItem(objectName)
        util.qtbot.keyClick(self.qml, key)
        if resetFocus:
            self.resetFocus(objectName)

    def keyClicks(self, objectName, s, resetFocus=True, returnToFinish=True):
        self.focusItem(objectName)
        util.qtbot.keyClicks(self.qml, s)
        if returnToFinish:
            util.qtbot.keyClick(self.qml, Qt.Key_Return) # only for TextInput?
        if resetFocus:
            self.resetFocus(objectName)

    def keyClicksClear(self, objectName):
        item = self.findItem(objectName)
        self.focusItem(objectName)
        item.selectAll()
        count = 0
        while item.property('text') not in ('', util.BLANK_DATE_TEXT) and count < 200:
            self.keyClick(objectName, Qt.Key_Backspace)
            count += 1
        self.resetFocus(objectName)
        itemText = item.property('text')
        if not (itemText == '' or itemText == util.BLANK_DATE_TEXT):
            raise RuntimeError('Could not clear text for %s (text = "%s")' % (objectName, itemText))

    def mouseClickItem(self, item, buttons=Qt.LeftButton, pos=None):
        if pos is None:
            rect = item.mapRectToScene(QRectF(0, 0, item.width(), item.height())).toRect()
            pos = rect.center()
        util.qtbot.mouseClick(self.qml, buttons, Qt.NoModifier, pos)
        
    def mouseClick(self, objectName, buttons=Qt.LeftButton, pos=None):
        if isinstance(objectName, str):
            item = self.findItem(objectName)
        else:
            item = objectName
        assert item.property('enabled') == True
        self.mouseClickItem(item)

    def clickTabBarButton(self, objectName, iTab):
        item = self.findItem(objectName)
        rect = item.mapRectToItem(self.qml.rootObject(),
                                  QRectF(0, 0, item.width(), item.height())).toRect()
        # count = item.property('count')
        # tabWidth = rect.width() / count
        # tabStartX = tabWidth * iTab
        # tabEndX = tabWidth * iTab + tabWidth
        # tabCenterX = tabStartX + ((tabEndX - tabStartX) / 2)
        # tabCenterY = rect.height() / 2
        # tabCenter = QPoint(tabCenterX, tabCenterY)
        # self.qml.setFocus()
        # util.qtbot.mouseClick(self.qml, Qt.LeftButton, Qt.NoModifier, tabCenter)
        item.setProperty('currentIndex', iTab)
        currentIndex = item.property('currentIndex')
        if not currentIndex == iTab:
            focusItem = self.rootProp('focusItem')
            raise RuntimeError('Unable to click tab bar button index %i for `%s`. `currentIndex` is still %i (focus widget: %s, focusItem: %s)' % (
                iTab, objectName, currentIndex,
                QApplication.focusWidget(), focusItem.objectName()
            ))

    def clickListViewItem(self, objectName, index):
        item = self.findItem(objectName)
        item.setProperty('currentIndex', index)

    def clickListViewItem_actual(self, objectName, rowText, modifiers=Qt.NoModifier):
        item = self.findItem(objectName)
        model = item.property('model')
        text = None
        textRows = []
        for row in range(model.rowCount()):
            text = model.data(model.index(row, 0))
            textRows.append(text)
            if text == rowText:
                break
        assert text == rowText, f"ListView row with text '{rowText}' not found (rows: {textRows}" # cell found
        assert self.itemProp(objectName, 'enabled') == True
        # calc visual rect
        x = 0
        y = util.QML_ITEM_HEIGHT * row - 1
        w = item.width()
        h = util.QML_ITEM_HEIGHT
        # ensureVisible = lambda x: QMetaObject.invokeMethod(item, 'ensureVisible',
        #                                                    Qt.DirectConnection,
        #                                                    Q_ARG(QVariant, row))
        # ensureVisible(row)
        prevCurrentIndex = item.property('currentIndex')
        rect = item.mapRectToScene(QRectF(x, y, w, h))
        self.mouseClick(objectName, Qt.LeftButton, rect.center().toPoint())

    def clickTimelineViewItem(self, objectName, cellText, column=0, modifiers=Qt.NoModifier):
        item = self.findItem(objectName)
        model = item.property('model')
        for row in range(model.rowCount()):
            text = model.data(model.index(row, column))
            if text == cellText:
                break
        assert text == cellText # cell found
        assert self.itemProp(objectName, 'enabled') == True
        # calc visual rect
        columnWidth = lambda x: QMetaObject.invokeMethod(item, 'columnWidthProvider',
                                                         Qt.DirectConnection,
                                                         Q_RETURN_ARG(QVariant),
                                                         Q_ARG(QVariant, x))
        x = sum([columnWidth(i) for i in range(column)])
        y = util.QML_ITEM_HEIGHT * row - 1
        w = columnWidth(column)
        h = util.QML_ITEM_HEIGHT
        self.findItem('ensureVisAnimation').setProperty('duration', 1)
        ensureVisible = lambda x: QMetaObject.invokeMethod(item, 'ensureVisible',
                                                           Qt.DirectConnection,
                                                           Q_ARG(QVariant, row))
        ensureVisible(row)
        forceLayout = lambda: QMetaObject.invokeMethod(item, 'test_updateLayout',
                                                       Qt.DirectConnection)
        forceLayout()
        selModel = item.property('selectionModel')
        prevSelection = selModel.selectedRows()
        rect = item.mapRectToScene(QRectF(x, y, w, h))
        self.mouseClick(objectName, Qt.LeftButton, rect.center().toPoint())
        newSelection = selModel.selectedRows()
        assert prevSelection != newSelection

    def clickComboBoxItem(self, objectName, itemText, comboBox=None):
        if isinstance(objectName, str):
            comboBox = self.findItem(objectName)
        else:
            comboBox = objectName
        self.mouseClick(objectName) # for focus
        model = comboBox.property('model')
        if isinstance(model, list):
            itemTexts = model
        elif isinstance(model, QAbstractItemModel):
            textRole = comboBox.property('textRole').encode('utf-8')
            for role, roleName in model.roleNames().items():
                if textRole == roleName:
                    break
            itemTexts = [model.data(model.index(row, 0), role) for row in range(model.rowCount())]
        currentIndex = None
        for i, text in enumerate(itemTexts):
            if text == itemText:
                currentIndex = i
        if currentIndex is None:
            raise RuntimeError('Could not find ComboBox item with text "%s" on `%s`' % (itemText, objectName))
        comboBox.setProperty('currentIndex', -1)
        comboBox.setProperty('currentIndex', currentIndex)
        comboBox.close()
        if not comboBox.property('currentText') == itemText:
            raise RuntimeError('Could not set `currentText` to "%s" (currentIndex: %i) on %s' % (
                itemText, currentIndex, objectName))
        
        # popup = item.findChildren(QQuickItem, 'popup')[0]
        # self.recursivePrintChildren(item, 0)
        # for child in item.childItems():
        #     self.here(child.metaObject().className())
        #     for _child in child.childItems():
        #         self.here('    ', _child.metaObject().className())

    def assertNoTableViewItem(self, objectName, text, column):
        model = self.itemProp(objectName, 'model')
        count = 0
        for row in range(model.rowCount()):
            index = model.index(row, column)
            itemS = model.index(row, column).data(Qt.DisplayRole)
            if itemS == text:
                count += 1
        assert count == 0        

    def recursivePrintChildren(self, item, level):
        for child in item.childItems():
            self.here('%s%s: %s' % ((' ' * level),
                                    item.objectName(),
                                    child.metaObject().className()))
            self.recursivePrintChildren(child, level + 1)
