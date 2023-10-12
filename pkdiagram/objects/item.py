import copy
from .. import util
from ..pyqt import QDateTime
from .property import Property



CLASS_PROPERTIES = { }    


class Item:
    """Anything that is stored in the diagram. Has a unique id, write()
    and save() API, and property system. """

    
    @staticmethod
    def registerProperties(propAttrs):
        # set type attr
        for kwargs in propAttrs:
            if not 'type' in kwargs:
                default = kwargs.get('default')
                if default is not None:
                    kwargs['type'] = type(default)
                else:
                    kwargs['type'] = str
        
        import inspect
        classScope = inspect.currentframe().f_back.f_locals
        __qualname__ = classScope['__qualname__']
        CLASS_PROPERTIES[__qualname__] = propAttrs
        return propAttrs
        
    @staticmethod
    def classProperties(kind):
        ret = []
        for ctor in reversed(kind.mro()):
            propArgs = CLASS_PROPERTIES.get(ctor.__qualname__, [])
            for args in propArgs:
                ret.append(args)
        return ret

    @staticmethod
    def adjustedClassProperties(kind, newEntries):
        """ Return a copy of the property meta data dict with newEntries added or updated. """
        entries = copy.deepcopy(Item.classProperties(kind))
        for newEntry in newEntries:
            found = False
            for entry in entries:
                if newEntry['attr'] == entry['attr']:
                    entry.update(newEntry)
                    found = True
                    break
            if not found:
                entries.append(newEntry)
        return entries
    
    registerProperties.__get__(object)((
        { 'attr': 'tags', 'default': [] },
        { 'attr': 'loggedDateTime', 'default': QDateTime.currentDateTime() }
    ))

    def __init__(self, *args, **kwargs):
        self.id = None
        self._itemScene = None
        self.propertyListeners = []
        self.props = []
        self._propCache = {}
        propAttrs = self.classProperties(self.__class__)
        self.addProperties(propAttrs)
        self._readChunk = {} # forward compat
        self._hasDeinit = False
        #
        self.isScene = False
        self.isEvent = False
        self.isPathItem = False
        self.isPerson = False
        self.isMarriage = False
        self.isEmotion = False
        self.isLayer = False
        self.isLayerItem = False
        self.isPencilStroke = False
        self.isCallout = False
        self.isChildOf = False
        self.isMultipleBirth = False
        self.isItemDetails = False
        self.isSeparationIndicator = False
        # gui hacks?
        self.isInspecting = False
        self.setProperties(**kwargs)
        # debug
        self._n_onActiveLayersChanged = 0

    def __repr__(self, exclude=[]):
        if not isinstance(exclude, list):
            exclude = [exclude]
        if not 'id' in exclude:
            exclude.append('id')
        props = {}
        for prop in self.props:
            if not prop.layered and prop.get() != prop.default:
                props[prop.attr] = prop.get()
        s = util.pretty(props, exclude=exclude)
        if s:
            s = ': ' + s
        return '<%s[%s]%s>' % (self.__class__.__name__, self.id, s)

    def deinit(self):
        self._hasDeinit = False
        for prop in self.props:
            prop.deinit()
        self.props = []
        self._propCache = {}

    ## Data
    
    def write(self, chunk):
        """ virtual """
        # forward compatibility, must be before the rest
        # This call also should be called at the top of subclass impl..
        chunk.update(self._readChunk)
        chunk['id'] = self.id
        for prop in self.props:
            chunk[prop.attr] = prop.get(forLayers=[])
        
    def read(self, chunk, byId):
        """ virtual """
        self._readChunk = chunk # copy.deepcopy(chunk) # forward compat
        self.id = chunk.get('id', None)
        for prop in self.props:
            value = chunk.get(prop.attr, prop.default)
            if not isinstance(value, prop.type) and value != prop.default:
                try:
                    value = prop.type(value)
                except TypeError:
                    value = None
            prop.set(value, notify=False)

    ## Cloning

    def clone(self, scene):
        """ Virtual """
        y = self.__class__()
        if hasattr(y, 'boundingRect'): # PathItem (avoid import)
            scene.addItem(y)
        else:
            scene.addItem(y)
        y._readChunk = copy.deepcopy(self._readChunk)
        for prop in self.props:
            y.prop(prop.attr).set(prop.get(), notify=False)
        y.setLoggedDateTime(QDateTime.currentDateTime(), notify=False)
        return y

    def remap(self, map):
        """ Virtual; return True if not possible to build coherent item. """
        return True

    ## Internal Data

    def scene(self):
        """ Virtual. """
        return self._itemScene

    def itemName(self):
        """ Virtual """
        return self.__class__.__name__

    def addProperties(self, meta):
        """ append to property list: [
            { 'attr': 'married', 'type': bool, 'default': True, 'update': True },
            { 'attr': 'marriedDate', 'update': True },
        ]
        """
        for kwargs in meta:
            if kwargs['attr'] in ['properties', 'opacity']:
                raise ValueError('`%s` is a reserved method name for Item' % kwargs['attr'])
            p = Property(self, **kwargs)
            attr = kwargs['attr']
            setterName = 'set' + attr[0].upper() + attr[1:]
            if not hasattr(self, setterName):
                setattr(self, setterName, p.set)
            getterName = kwargs['attr']
            if not hasattr(self, getterName):
                setattr(self, getterName, p.get)
            resetterName = 'reset' + attr[0].upper() + attr[1:]
            if not hasattr(self, resetterName):
                setattr(self, resetterName, p.reset)
            self.props.append(p)
            self._propCache[attr] = p
            
    def setProperties(self, **kwargs):
        """ Convenience method for bulk assignment.
        Ignore kwargs without a registered property.
        """
        for k, v in kwargs.items():
            prop = self.prop(k)
            if prop:
                prop.set(v, notify=False)

    def onProperty(self, prop):
        """ virtual """
        for x in self.propertyListeners:
            x.onItemProperty(prop)

    def addPropertyListener(self, x):
        if not x in self.propertyListeners:
            self.propertyListeners.append(x)

    def removePropertyListener(self, x):
        if x in self.propertyListeners:
            self.propertyListeners.remove(x)

    def propertyNames(self):
        return self._propCache.keys()
        # return [p.name() for p in self.props]

    def prop(self, name):
        return self._propCache.get(name)

    ## Scene Events

    def onRegistered(self, scene):
        """ virtual """
        self._itemScene = scene

    def onDeregistered(self, scene):
        """ virtual """
        self._itemScene = None

    def onActiveLayersChanged(self):
        """ Update layered properties. """
        self._n_onActiveLayersChanged += 1
        #
        changed = []
        for prop in self.props:
            if prop.layered:
                was = prop.get()
                prop.onActiveLayersChanged()
                now = prop.get()
                itemName = prop.item.itemName() and prop.item.itemName() or prop.item.__class__.__name__
                if now != was:
                    changed.append(prop)
        for prop in changed:
            self.onProperty(prop)

    def beginUpdateFrame(self):
        """ Virtual """
        self._n_onActiveLayersChanged = 0

    def endUpdateFrame(self):
        """ Virtual """

    def setTag(self, x, notify=True, undo=None):
        tags = list(self.tags())
        if not x in tags:
            tags.append(x)
            tags.sort()
            self.prop('tags').set(tags, notify=notify, undo=undo)

    def addTags(self, newTags, notify=True, undo=None):
        itemTags = list(self.tags())
        for tag in newTags:
            if not tag in itemTags:
                 itemTags.append(tag)
        itemTags.sort()
        if itemTags != self.tags():
            self.prop('tags').set(itemTags, notify=notify, undo=undo)

    def unsetTag(self, x, notify=True, undo=None):
        tags = list(self.tags())
        if x in tags:
            tags.remove(x)
            tags.sort()
            self.prop('tags').set(tags, notify=notify, undo=undo)

    def hasTags(self, tags):
        if not tags:
            return True
        elif set(tags) & set(self.tags()):
            return True
        else:
            return False

    def onTagRenamed(self, old, new):
        """ Called right from Scene.renameTag() """
        tags = []
        for index, tag in enumerate(self.tags()):
            if tag == old:
                tags.append(new)
            else:
                tags.append(tag)
        tags.sort()
        self.prop('tags').set(tags, notify=False, undo=False)
