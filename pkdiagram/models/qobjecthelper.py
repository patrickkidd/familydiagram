import inspect
import enum
from ..pyqt import (
    pyqtProperty,
    pyqtSignal,
    QVariant,
    QMetaObject,
    Qt,
    Q_ARG,
    Q_RETURN_ARG,
    QJSValue,
    QDate,
    QDateTime,
)
from .. import objects


CLASS_PROPERTIES = {}


class QObjectHelper:
    """Add QObject properties via python dict."""

    PRINT_EMITS = False
    DEBUG = True

    def registerQtProperties(attrEntries=None, itemType=None, globalContext={}):
        """
        Dynamically add Qt properties, signals, and slots to match
        objects.Property. 'convertTo' sets the type on the property for the
        pyqtProperty while leaving 'type' in place. This allows converting types
        between the model and the items.
        """
        classAttrs = inspect.currentframe().f_back.f_locals
        classAttrs["qsignals"] = qsignals = classAttrs.get("qsignals", [])
        classAttrs["qproperties"] = qproperties = classAttrs.get("qproperties", [])
        # classAttrs['qslots'] = qslots = classAttrs.get('qslots', [])
        classAttrs["qpropertyNames"] = qpropertyNames = classAttrs.get(
            "qpropertyNames", []
        )
        classAttrs["qsignalNames"] = qsignalNames = classAttrs.get("qsignalNames", [])
        if attrEntries is None:
            attrEntries = objects.Item.classProperties(itemType)
        for kwargs in attrEntries:
            kwargs["globalContext"] = globalContext

            def closure(kwargs, globalContext):
                attr = kwargs["attr"]

                if not "type" in kwargs:
                    kwargs["type"] = str

                if not "convertTo" in kwargs:
                    kind = kwargs["type"]
                else:
                    kind = kwargs.get("convertTo")

                signalName = "%sChanged" % attr
                getterName = attr
                setterName = "set" + attr[0].upper() + attr[1:]
                resetterName = "reset" + attr[0].upper() + attr[1:]
                #
                qsignal = pyqtSignal(QVariant)

                # These are separated out into instance methods to provide
                # a way for the instance to access them directly.
                # If they are just closures then there is no way to call them.
                def propGetter(self):
                    return self._cachedPropGetter(kwargs)

                def propSetter(self, value):
                    self._cachedPropSetter(kwargs, value)

                def propResetter(self):
                    self._cachedPropResetter(kwargs)

                #
                if not isinstance(type(kind), type) and not kind == "QVariant":
                    raise TypeError(
                        "'kind' attribute must be a type, instead got: %" % kind
                    )
                if kwargs.get("constant"):
                    qproperty = pyqtProperty(
                        kind,
                        fget=propGetter,
                        freset=propResetter,
                        notify=qsignal,
                        constant=True,
                    )
                else:
                    qproperty = pyqtProperty(
                        kind,
                        fget=propGetter,
                        fset=propSetter,
                        freset=propResetter,
                        notify=qsignal,
                    )
                #
                ret = {}
                ret[signalName] = qsignal
                ret[getterName] = qproperty
                ret[resetterName] = propResetter
                if not kwargs.get("constant"):
                    ret[setterName] = propSetter
                    # qslots.append(propSetter)
                qsignals.append(qsignal)
                qproperties.append(qproperty)
                qpropertyNames.append(getterName)
                qsignalNames.append(signalName)
                return ret

            propAttrs = closure(kwargs, globalContext)
            classAttrs.update(propAttrs)

        # inheritance
        global CLASS_PROPERTIES
        __qualname__ = classAttrs["__qualname__"]
        CLASS_PROPERTIES[__qualname__] = attrEntries

    @staticmethod
    def classProperties(kind):
        ret = []
        for ctor in reversed(kind.mro()):
            classAttrs = CLASS_PROPERTIES.get(ctor.__qualname__, [])
            for kwargs in classAttrs:
                ret.append(kwargs)
        return ret

    def registerQmlMethods(entries):
        """
        TODO: Move this to QmlWidgetHelper?

        Forwards calls to QObject class methods to their qml-javascript correlates.
        """
        classAttrs = inspect.currentframe().f_back.f_locals
        for entry in entries:

            def make_meth(entry):
                def meth(self, *args):
                    self.checkInitQml()
                    qobject = self.qml.rootObject()
                    name = entry["name"]
                    if len(args) == 1:
                        qargs = (Q_ARG(QVariant, args[0]),)
                    elif len(args) > 1:
                        qargs = (Q_ARG(QVariant, arg) for arg in args)
                    else:
                        qargs = ()
                    try:
                        if entry.get("return"):
                            if qargs:
                                ret = QMetaObject.invokeMethod(
                                    qobject,
                                    name,
                                    Qt.DirectConnection,
                                    Q_RETURN_ARG(QVariant),
                                    *qargs,
                                )
                            else:
                                ret = QMetaObject.invokeMethod(
                                    qobject,
                                    name,
                                    Qt.DirectConnection,
                                    Q_RETURN_ARG(QVariant),
                                )
                        else:
                            if qargs:
                                ret = QMetaObject.invokeMethod(
                                    qobject, name, Qt.DirectConnection, *qargs
                                )
                            else:
                                ret = QMetaObject.invokeMethod(
                                    qobject, name, Qt.DirectConnection
                                )
                    except RuntimeError as e:
                        pass
                    # raise RuntimeError('QMetaObject.invokeMethod failed on %s.%s' % (self.__class__.__name__, name))
                    else:
                        if entry.get("parser"):
                            if ret:
                                return entry.get("parser")(ret)
                        elif isinstance(ret, QJSValue):
                            return ret.toVariant()
                        else:
                            return ret

                return meth

            name = entry["name"]
            if not name in classAttrs:
                classAttrs[name] = make_meth(entry)

    def initQObjectHelper(self, storage=False):
        if hasattr(self, "_propCache"):
            return
        self._propCache = {}  # should be the converted (i.e. qml-exposed) value
        self._refreshingAllProperties = False
        self._refreshingAttr = None
        self._blockRefresh = False
        self._defaultStorage = {}
        if storage:
            # Set all to defaults. Let's see if this shoudl be reusable.
            attrs = self.classProperties(self.__class__)
            for kwargs in attrs:
                attr = kwargs["attr"]
                x = self.defaultFor(attr)
                self._defaultStorage[attr] = x
        self.refreshAllProperties()

    def _emitAttrChanged(self, attr, x):
        """Provides a way to capture signal emissions in a specific subclass
        when debugging, and also provide a way to force emission for certain
        strange property instances."""
        if self.PRINT_EMITS:
            print(f"{attr}Changed({x})")
        getattr(self, attr + "Changed").emit(x)

    def refreshingAttr(self):
        """Don't emit any changed signals for this prop name."""
        return self._refreshingAttr

    def refreshAllProperties(self):
        if self._refreshingAllProperties:
            return
        if self._blockRefresh:
            return
        self._refreshingAllProperties = True
        for kwargs in self.classProperties(self.__class__):
            attr = kwargs["attr"]
            self.refreshProperty(attr)
        self._refreshingAllProperties = False

    def refreshProperty(self, attr):
        """
        The only place the changed signal is emitted for locally stored variables.
        Should not be called from &.set() or it won't have access to prop values set in &.set().
        """
        if self._blockRefresh:
            return
        kwargs = self.propAttrsFor(attr)
        if kwargs:
            x = self.get(attr)
            if not attr in self._propCache or x != self._propCache[attr]:
                if self.refreshingAttr() != attr:
                    # refreshProperty will be called again from _cachedPropSetter() immediately following this call.
                    self._propCache[attr] = x
                    self._emitAttrChanged(attr, x)

    def propAttrsFor(self, attr):
        """Return the most recent property attributes for property,
        potentially updated using registerModelProperties."""
        attrs = self.classProperties(self.__class__)
        for entry in attrs:
            if entry["attr"] == attr:
                return entry

    def defaultFor(self, attr):
        """Calculate a prop's default value based on either ['default'] or ['type']."""
        attrs = self.propAttrsFor(attr)
        if attrs:
            if "convertTo" in attrs:
                return attrs.get("convertTo")()
            elif "default" in attrs:
                return attrs.get("default")
            else:
                return attrs.get("type")()
        else:
            raise AttributeError("There is no property named %s" % attr)

    ## Value conversions

    def getterConvertTo(self, attr, x):
        value = x
        attrs = self.propAttrsFor(attr)
        if not attrs:
            return value
        convertTo = attrs.get("convertTo")
        if convertTo == Qt.CheckState:
            if x is True:
                value = Qt.Checked
            elif x is False:
                value = Qt.Unchecked
            elif x is None:
                value = Qt.Unchecked
            else:
                value = Qt.PartiallyChecked
        elif convertTo == QDateTime:
            if isinstance(x, QDate):
                value = QDateTime(x)
        return value

    def setterConvertTo(self, attr, value):
        """Must be called explicitly in set()."""
        convertTo = self.propAttrsFor(attr).get("convertTo")
        x = value
        if convertTo == Qt.CheckState:
            if value == Qt.PartiallyChecked:
                x = True
            elif value == Qt.Checked:
                x = True
            elif value == Qt.Unchecked:
                x = False
        elif convertTo == QDateTime:
            x = value.dateTime()
        return x

    # Property behavior

    def _cachedPropGetter(self, kwargs):
        """The first call directly from the Qt property.
        Should only access the cache; Cache should be explicitly updated with refreshProperty().
        """
        attr = kwargs["attr"]
        ret = self._propCache[attr]  # should be appropriately updated elsewhere
        return ret

    def _cachedPropSetter(self, kwargs, value):
        """The first call directly from the Qt property."""
        attr = kwargs["attr"]
        if kwargs.get("global"):
            if value != kwargs["globalContext"][attr]:
                kwargs["globalContext"][attr] = value
                self._emitAttrChanged(attr, value)
        else:
            if value != self._propCache.get(attr):
                was = self._refreshingAttr
                self._refreshingAttr = attr
                # may trigger onItemProperty, which emits changed signal from refreshProperty
                self.set(attr, value)
                self._refreshingAttr = was
                self.refreshProperty(attr)

    def _cachedPropResetter(self, kwargs):
        """The first call directly from the Qt property."""
        attr = kwargs["attr"]
        x = self.defaultFor(attr)
        if x != self._propCache[attr]:
            was = self._refreshingAttr
            self._refreshingAttr = attr
            self.reset(attr)
            self._refreshingAttr = was
            self.refreshProperty(attr)

    ## Virtuals

    def get(self, attr):
        """Virtual. Should never return None."""
        kwargs = self.propAttrsFor(attr)
        if kwargs and kwargs.get("global"):
            x = kwargs["globalContext"][attr]
            if isinstance(x, enum.Enum):
                x = {y.name: y.value for y in x}
            return x
        elif self._defaultStorage:
            if kwargs:
                x = self._defaultStorage.get(attr)
                x = self.getterConvertTo(attr, x)
                return x
            else:
                raise RuntimeError(
                    "The property `%s` does not exist on %s" % (attr, self)
                )

    def set(self, attr, x):
        """Virtual"""
        if self._defaultStorage:
            if self.propAttrsFor(attr):
                x = self.setterConvertTo(attr, x)
                self._defaultStorage[attr] = x
                self.refreshProperty(attr)
            else:
                raise RuntimeError(
                    "The property `%s` does not exist on %s" % (attr, self)
                )

    def reset(self, attr):
        """Virtual. Reimplement for new properties defined in model."""
        if self._defaultStorage:
            if self.propAttrsFor(attr):
                # self._defaultStorage[attr] = self.defaultFor(attr)
                default = self.defaultFor(attr)
                if default != self._defaultStorage[attr]:
                    self._defaultStorage[attr] = default
                    self.refreshProperty(attr)
            else:
                raise RuntimeError(
                    "The property `%s` does not exist on %s" % (attr, self)
                )
