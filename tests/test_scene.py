import os, os.path, pickle, itertools
import pytest
import conftest
from pkdiagram.pyqt import QDateTime, QPointF, QRectF
from pkdiagram import util, commands, Scene, Item, Person, Marriage, Emotion, Event, MultipleBirth, Layer, SceneLayerModel, SearchModel

# class AddPeopleTest(test_util.TestCase):

#     def setUp(self):
#         s = scene.Scene()

#     def tearDown(self):
#         s = None

#     def test_addPerson(self):
#         person = Person()
#         person.setName('Patrick')
#         s.addItem(person)
#         self.assertEqual(len(s.people()), 1)
#         self.assertEqual(s.people()[0], person)

def test_find_by_types(simpleScene):
    """ """
    people = simpleScene.find(types=Person)
    assert len(people) == 3

    people = simpleScene.find(types=[Person])
    assert len(people) == 3

    pairBonds = simpleScene.find(types=[Marriage])
    assert len(pairBonds) == 1


def test_find_by_tags(simpleScene):
    p1 = simpleScene.query1(name='p1')
    p = simpleScene.query1(name='p')
    p1.setTags(['hello'])
    p.setTags(['hello'])
    p1.birthEvent.setTags(['hello'])
    
    items = simpleScene.find(tags='hello')
    assert len(items) == 3
    
    items = simpleScene.find(tags=['hello'])
    assert len(items) == 3


def test_find_by_types_and_tags(simpleScene):
    p1 = simpleScene.query1(name='p1')
    p2 = simpleScene.query1(name='p2')
    p = simpleScene.query1(name='p')
    p1.setTags(['hello'])
    p.setTags(['hello'])
    p1.birthEvent.setTags(['hello'])
        
    items = simpleScene.find(tags='hello', types=Event)
    assert len(items) == 1
    
    items = simpleScene.find(tags=['hello'], types=Person)
    assert len(items) == 2
    
    
def test_undo_remove_child_selected(qtbot, simpleScene):
    """ People and pair-bond were selected but not child items after delete and undo. """

    p = simpleScene.query(name='p')[0]
    p1 = simpleScene.query(name='p1')[0]
    p2 = simpleScene.query(name='p2')[0]
    m = p1.marriages[0]

    assert p.childOf is not None

    m.setSelected(True)
    p.setSelected(True)
    p1.setSelected(True)
    p2.setSelected(True)

    qtbot.clickYesAfter(lambda: simpleScene.removeSelection())
    commands.stack().undo()
    
    assert not m.isSelected()
    assert not p.isSelected()
    assert not p1.isSelected()
    assert not p2.isSelected()
    assert not p.childOf.isSelected()


def test_no_duplicate_events_from_file(simpleScene):
    for i, person in enumerate(simpleScene.people()):
        person.setBirthDateTime(util.Date(1900, 1, 1 + i))
    events = simpleScene.events()
    for event in events:
        assert events.count(event) == 1


def _test_copy_paste_twin(simpleScene):
    s = simpleScene
    p1 = s.query1(name='p1')
    p2 = s.query1(name='p2')
    p = s.query1(name='p')

    t1 = Person(name='t1')
    t2 = Person(name='t2')
    s.addItem(t1)
    s.addItem(t2)
    multipleBirth = MultipleBirth(p.parents())
    t1.setParents(multipleBirth=multipleBirth)
    t2.setParents(multipleBirth=multipleBirth)

    t1.setSelected(True)
    s.copy()
    s.paste()

    
def _test_copy_paste_with_multipleBirth_selected(simpleScene):
    s = simpleScene
    p1 = s.query1(name='p1')
    p2 = s.query1(name='p2')
    p = s.query1(name='p')

    t1 = Person(name='t1')
    t2 = Person(name='t2')
    s.addItem(t1)
    s.addItem(t2)
    multipleBirth = MultipleBirth(p.parents())
    t1.setParents(multipleBirth=multipleBirth)
    t2.setParents(multipleBirth=multipleBirth)

    t1.setSelected(True)
    multipleBirth.setSelected(True)
    s.copy()
    s.paste()

    
def test_hide_emotional_process(simpleScene):
    s = simpleScene

    p1 = s.query1(name='p1')
    p2 = s.query1(name='p2')
    p = s.query1(name='p')
    
    e1 = Emotion(p1, p2, kind=util.ITEM_CONFLICT)
    s.addItem(e1)
    e2 = Emotion(p2, p1, kind=util.ITEM_PROJECTION)
    s.addItem(e2)
    e3 = Emotion(p1, p, kind=util.ITEM_DISTANCE)
    s.addItem(e3)

    assert e1.isVisible() == True
    assert e2.isVisible() == True
    assert e3.isVisible() == True

    s.setHideEmotionalProcess(True)

    assert e1.isVisible() == False
    assert e2.isVisible() == False
    assert e3.isVisible() == False

    s.setHideEmotionalProcess(False)
    
    assert e1.isVisible() == True
    assert e2.isVisible() == True
    assert e3.isVisible() == True


def test_hide_names():
    scene = Scene()
    person = Person(name='Person A')
    person.setDiagramNotes("""A multi-line
string""")
    person.birthEvent.setDateTime(util.Date(2001, 1, 1))
    scene.addItem(person)
    assert person.detailsText.text() == """Person A
b. 01/01/2001
A multi-line
string"""

    scene.setHideNames(True)
    assert person.detailsText.text() == """b. 01/01/2001
A multi-line
string"""

    scene.setHideNames(False)
    assert person.detailsText.text() == """Person A
b. 01/01/2001
A multi-line
string"""


def test_rename_tag_retains_tag_on_items():

    s = Scene()
    s.setTags(['aaa', 'ccc', 'ddd'])
    item = Item()
    s.addItem(item)
    item.setTags(['ddd'])

    s.renameTag('ddd', 'bbb')

    assert s.tags() == ['aaa', 'bbb', 'ccc']
    assert item.tags() == ['bbb']


def test_nextTaggedDate_prevTaggedDateTime():
    scene = Scene()
    scene.replaceEventProperties(['Var 1', 'Var 2'])
    person1 = Person()
    person1.setBirthDateTime(util.Date(2000, 1, 1)) # 0
    scene.addItem(person1)
    event1 = Event(parent=person1, dateTime=util.Date(2001, 1, 1)) # 1
    event1.dynamicProperty('var-1').set('One')
    event2 = Event(parent=person1, dateTime=util.Date(2002, 1, 1)) # 2
    event3 = Event(parent=person1, dateTime=util.Date(2003, 1, 1)) # 3
    event3.dynamicProperty('var-2').set('Two')
    scene.setCurrentDateTime(person1.birthDateTime()) # 0
    scene.nextTaggedDateTime() # 1
    assert scene.currentDateTime() == event1.dateTime()
    
    scene.nextTaggedDateTime() # 2
    assert scene.currentDateTime() == event2.dateTime()

    scene.nextTaggedDateTime() # 3
    assert scene.currentDateTime() == event3.dateTime()

    scene.nextTaggedDateTime() # 4
    assert scene.currentDateTime() == scene.nowEvent.dateTime()

    scene.prevTaggedDateTime() # 3
    assert scene.currentDateTime() == event3.dateTime()

    scene.prevTaggedDateTime() # 2
    assert scene.currentDateTime() == event2.dateTime()

    scene.prevTaggedDateTime() # 1
    assert scene.currentDateTime() == event1.dateTime()

    scene.prevTaggedDateTime() # 0
    assert scene.currentDateTime() == person1.birthDateTime()


def test_nextTaggedDate_uses_search_tags():
    scene = Scene()
    tags = ['test']

    person1 = Person()
    person1.setBirthDateTime(util.Date(1980, 1, 1))
    person2 = Person()
    person2.setBirthDateTime(util.Date(1990, 2, 2))
    person3 = Person()
    person3.setBirthDateTime(util.Date(2000, 3, 3))
    scene.addItem(person1)
    scene.addItem(person2)
    scene.addItem(person3)

    # test first before setting tags
    
    scene.setCurrentDateTime(person1.birthDateTime())
    assert scene.currentDateTime() == person1.birthDateTime()
    
    scene.prevTaggedDateTime() # noop
    assert scene.currentDateTime() == person1.birthDateTime()

    scene.nextTaggedDateTime()
    assert scene.currentDateTime() == person2.birthDateTime()
    
    scene.nextTaggedDateTime()
    assert scene.currentDateTime() == person3.birthDateTime()
    
    scene.nextTaggedDateTime()
    assert scene.currentDateTime() == scene.nowEvent.dateTime()
    
    scene.nextTaggedDateTime() # noop
    assert scene.currentDateTime() == scene.nowEvent.dateTime()

    # then test after setting tags
    person1.birthEvent.setTags(tags)
    person3.birthEvent.setTags(tags)
    scene.searchModel.setTags(tags)

    taggedEvents = [e for e in scene.events() if e.hasTags(tags)]
    scene.setCurrentDateTime(taggedEvents[0].dateTime())
    assert scene.currentDateTime() == person1.birthDateTime()
    
    scene.prevTaggedDateTime() # noop
    assert scene.currentDateTime() == person1.birthDateTime()

    scene.nextTaggedDateTime() # skip person 2 for tags
    assert scene.currentDateTime() == person3.birthDateTime()
    
    scene.nextTaggedDateTime() # noop
    assert scene.currentDateTime() == person3.birthDateTime()


def test_nextTaggedDate_uses_searchModel():
    scene = Scene()
    tags = ['test']

    person1 = Person(name="One")
    person1.setBirthDateTime(util.Date(1980, 1, 1))
    person2 = Person(name="Two")
    person2.setBirthDateTime(util.Date(1990, 2, 2))
    person3 = Person(name="Three")
    person3.setBirthDateTime(util.Date(2000, 3, 3))
    scene.addItem(person1)
    scene.addItem(person2)
    scene.addItem(person3)

    # test first before setting tags
    
    scene.setCurrentDateTime(person1.birthDateTime())
    assert scene.currentDateTime() == person1.birthDateTime()
    
    scene.prevTaggedDateTime() # noop
    assert scene.currentDateTime() == person1.birthDateTime()

    scene.nextTaggedDateTime()
    assert scene.currentDateTime() == person2.birthDateTime()
    
    scene.nextTaggedDateTime()
    assert scene.currentDateTime() == person3.birthDateTime()
    
    scene.nextTaggedDateTime()
    assert scene.currentDateTime() == scene.nowEvent.dateTime()
    
    scene.nextTaggedDateTime() # noop
    assert scene.currentDateTime() == scene.nowEvent.dateTime()

    # then test after setting tags
    person1.birthEvent.setTags(tags)
    person3.birthEvent.setTags(tags)
    scene.searchModel.setTags(tags)

    taggedEvents = [e for e in scene.events() if e.hasTags(tags)]
    scene.setCurrentDateTime(taggedEvents[0].dateTime())
    assert scene.currentDateTime() == person1.birthDateTime()
    
    scene.prevTaggedDateTime() # noop
    assert scene.currentDateTime() == person1.birthDateTime()

    scene.nextTaggedDateTime() # skip person 2 for tags
    assert scene.currentDateTime() == person3.birthDateTime()
        
    scene.nextTaggedDateTime() # noop
    assert scene.currentDateTime() == person3.birthDateTime()

    scene.prevTaggedDateTime()
    assert scene.currentDateTime() == person1.birthDateTime()

    scene.prevTaggedDateTime() # noop
    assert scene.currentDateTime() == person1.birthDateTime()


def test_new_persons_get_current_layers():

    s = Scene()
    layer1 = Layer()
    s.addItem(layer1)
    p1 = Person(name='p1')
    assert p1.layers() == []

    layer1.setActive(True)
    assert layer1.id not in p1.layers()

    p2 = Person(name='p2')
    s.addItem(p2)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]
    
    layer2 = Layer(active=True)
    s.addItem(layer2)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]
     
    p3 = Person(name='p3')
    s.addItem(p3)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]
    assert p3.layers() == [layer1.id, layer2.id]

    layer1.setActive(False)
    p4 = Person(name='p4')
    s.addItem(p4)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]
    assert p3.layers() == [layer1.id, layer2.id]
    assert p4.layers() == [layer2.id]
    

@pytest.mark.skip(reason="Probahly doesn't apply any more since layers don't have tags any more")
def test_update_set_tag_on_inspected_items_out_of_layer():
    """ Show layer with people that have emotional process
    symbols that don’t have the layer’s tags, inspect those
    symbols from personal timeline, add tag for the layer -> symbols don’t appear.
    """
    tags = ['here']
    s = Scene()
    s.setTags(tags)
    layer1 = Layer(tags=tags)
    s.addItem(layer1)
    p1 = Person(name='p1', tags=tags)
    p2 = Person(name='p2', tags=tags)
    s.addItems(p1, p2)
    cutoff = Emotion(kind=util.ITEM_CUTOFF, personA=p1, personB=p2)
    s.addItems(cutoff)
    layer1.setActive(True)
    dateTime = QDateTime.currentDateTime()
    assert p1.shouldShowFor(dateTime, tags) == True
    assert p2.shouldShowFor(dateTime, tags) == True
    assert cutoff.shouldShowFor(dateTime, tags) == False
    assert cutoff.isVisible() == False

    # Simulate inspecting a hidden emotion from person props
    cutoff.setTags(tags)
    assert cutoff.shouldShowFor(dateTime, tags) == True
    assert cutoff.isVisible() == True
    

def test_read():
    """ Just try to break the most basic object constructors. """
    stuff = []
    def byId(id):
        return None

    data = {
        'items': [
            {
                'kind': 'Person',
                'id': 1,
                'events': [
                    {
                        'id': 2
                    }
                ],
                'parents': None,
                'marriages': []
            }
        ]
    }
    
    scene = Scene()
    scene.read(data, byId)



# def test_read_fd():
#     """ Just test reading in an actual fd. """
#     with open(os.path.join(conftest.TIMELINE_TEST_FD, 'diagram.pickle'), 'rb') as f:
#         bdata = f.read()
#     scene = Scene()
#     data = pickle.loads(bdata)
#     assert scene.read(data) == None


def test_clean_stale_refs():
    with open(os.path.join(conftest.DATA_ROOT, 'stale-refs.fd/diagram.pickle'), 'rb') as f:
        bdata = f.read()
    scene = Scene()
    data = pickle.loads(bdata)
    assert len(scene.prune(data)) == 9


def test_hasActiveLayers():
    scene = Scene()
    assert scene.hasActiveLayers == False
    
    layer = Layer(active=True)
    scene.addItem(layer)
    assert scene.hasActiveLayers == True

    layer.setActive(False)
    assert scene.hasActiveLayers == False
    
    
def __test_getPrintRect(): # was always changing by a few pixels...
    s = Scene()
    s.setTags(['NW', 'NE', 'SW', 'SE'])
    northWest = Person(name='NW', pos=QPointF(-1000, -1000), tags=['NW'])
    northEast = Person(name='NE', pos=QPointF(1000, -1000), tags=['NE'])
    southWest = Person(name='SW', pos=QPointF(-1000, 1000), tags=['SW'])
    southEast = Person(name='SE', pos=QPointF(1000, 1000), tags=['SE'])
    s.addItems(northWest, northEast, southWest, southEast)

    fullRect = s.getPrintRect()
    assert fullRect == QRectF(-1162.5, -1181.25, 2407.5, 2343.75)

    nwRect = s.getPrintRect(forTags=['NW'])
    assert nwRect == QRectF(-1162.5, -1181.25, 417.5, 343.75)

    ## TODO: account for ChildOf, Emotions, and other Item's that don't have a layerPos()

    
def test_anonymize():
    scene = Scene()
    patrick = Person(name='Patrick', alias='Marco', notes='Patrick Bob')
    bob = Person(name='Bob', nickName='Robby', alias='John')
    e1 = Event(parent=patrick, description='Bob came home')
    e2 = Event(parent=patrick, description="robby came home, took Robby's place")
    e3 = Event(parent=bob, description='Patrick came home with bob')
    distance = Emotion(kind=util.ITEM_DISTANCE, personA=patrick, personB=bob,
                       notes="""
Here is a story about Patrick
and Bob
and Robby robby
""")    
    scene.addItems(patrick, bob, distance)
    assert patrick.notes() == 'Patrick Bob'
    assert e1.description() == 'Bob came home'
    assert e2.description() == "robby came home, took Robby's place"
    assert e3.description() == 'Patrick came home with bob'
    assert distance.notes() == """
Here is a story about Patrick
and Bob
and Robby robby
"""
    
    scene.setShowAliases(True)
    patrick.notes() == '[Marco] [John]'
    assert e1.description() == '[John] came home'
    assert e2.description() == "[John] came home, took [John]'s place"
    assert e3.description() == '[Marco] came home with [John]'
    assert distance.notes() == """
Here is a story about [Marco]
and [John]
and [John] [John]
"""


def test_layered_properties():
    """ Ensure correct layered prop updates for marriage+marriage-indicators. """
    scene = Scene()
    male = Person(name='Male', kind='male')
    female = Person(name='Female', kind='female')
    marriage = Marriage(personA=male, personB=female)
    divorcedEvent = Event(parent=marriage, uniqueId='divorced', dateTime=util.Date(1900, 1, 1))
    layer = Layer(name='View 1')
    scene.addItems(male, female, marriage, layer)
    #
    unlayered = {
        'male': QPointF(-100, -50),
        'maleDetails': QPointF(100, 100),
        'female': QPointF(100, -50),
        'femaleDetails': QPointF(-100,-200),
        'marriageSep': QPointF(100, 0),
        'marriageDetails': QPointF(-25, 0),
    }
    layered = {
        'male': QPointF(-200, -150),
        'maleDetails': QPointF(-100, -100),
        'female': QPointF(100, 50),
        'femaleDetails': QPointF(100, 200),
        'marriageSep': QPointF(100, 0),
        'marriageDetails': QPointF(25, -100),
    }
    # layered
    layer.setItemProperty(male.id, 'itemPos', layered['male'])
    layer.setItemProperty(male.detailsText.id, 'itemPos', layered['maleDetails'])
    layer.setItemProperty(female.id, 'itemPos', layered['female'])
    layer.setItemProperty(female.detailsText.id, 'itemPos', layered['femaleDetails'])
    layer.setItemProperty(marriage.detailsText.id, 'itemPos', layered['marriageDetails'])
    layer.setItemProperty(marriage.separationIndicator.id, 'itemPos', layered['marriageSep'])
    # unlayered
    male.setItemPos(unlayered['male'], undo=False)
    male.detailsText.setItemPos(unlayered['maleDetails'], undo=False)
    female.setItemPos(unlayered['female'], undo=False)
    female.detailsText.setItemPos(unlayered['femaleDetails'], undo=False)
    # marriage.setDivorced(True, undo=False)
    marriage.separationIndicator.setItemPos(unlayered['marriageSep'], undo=False)
    marriage.detailsText.setItemPos(unlayered['marriageDetails'], undo=False)
    
    assert male.pos() == unlayered['male']
    assert male.detailsText.pos() == unlayered['maleDetails']
    assert female.pos() == unlayered['female']
    assert female.detailsText.pos() == unlayered['femaleDetails']
    assert marriage.detailsText.pos() == unlayered['marriageDetails']
    assert marriage.separationIndicator.pos() == unlayered['marriageSep']

    layer.setActive(True)
    assert male.pos() == layered['male']
    assert male.detailsText.pos() == layered['maleDetails']
    assert female.pos() == layered['female']
    assert female.detailsText.pos() == layered['femaleDetails']
    assert marriage.detailsText.pos() == layered['marriageDetails']
    assert marriage.separationIndicator.pos() == layered['marriageSep']
    
    layer.setActive(False)
    assert male.pos() == unlayered['male']
    assert male.detailsText.pos() == unlayered['maleDetails']
    assert female.pos() == unlayered['female']
    assert female.detailsText.pos() == unlayered['femaleDetails']
    assert marriage.detailsText.pos() == unlayered['marriageDetails']
    assert marriage.separationIndicator.pos() == unlayered['marriageSep']
 
    layer.resetItemProperty(male.prop('itemPos'))
    layer.resetItemProperty(male.detailsText.prop('itemPos'))
    layer.resetItemProperty(female.prop('itemPos'))
    layer.resetItemProperty(female.detailsText.prop('itemPos'))
    layer.resetItemProperty(marriage.detailsText.prop('itemPos'))
    layer.resetItemProperty(marriage.separationIndicator.prop('itemPos'))
    layer.setActive(True)
    assert male.pos() == unlayered['male']
    assert male.detailsText.pos() == unlayered['maleDetails']
    assert female.pos() == unlayered['female']
    assert female.detailsText.pos() == unlayered['femaleDetails']
    assert marriage.detailsText.pos() == unlayered['marriageDetails']
    assert marriage.separationIndicator.pos() == unlayered['marriageSep']
   


def test_undo_add_remove_layered_item_props(qtbot):
    scene = Scene()
    male = Person(name='Male', kind='male')
    female = Person(name='Female', kind='female')
    marriage = Marriage(personA=male, personB=female)
    divorcedEvent = Event(parent=marriage, uniqueId='divorced', dateTime=util.Date(1900, 1, 1))
    layer = Layer(name='View 1')
    scene.addItems(male, female, marriage, layer)
    #
    unlayered = {
        'male': QPointF(-100, -50),
        'maleDetails': QPointF(100, 100),
        'female': QPointF(100, -50),
        'femaleDetails': QPointF(-100,-200),
        'marriageSep': QPointF(100, 0),
        'marriageDetails': QPointF(-25, 0),
    }
    layered = {
        'male': QPointF(-200, -150),
        'maleDetails': QPointF(-100, -100),
        'female': QPointF(100, 50),
        'femaleDetails': QPointF(100, 200),
        'marriageSep': QPointF(100, 0),
        'marriageDetails': QPointF(25, -100),
    }
    # layered
    layer.setItemProperty(male.id, 'itemPos', layered['male'])
    layer.setItemProperty(male.detailsText.id, 'itemPos', layered['maleDetails'])
    layer.setItemProperty(female.id, 'itemPos', layered['female'])
    layer.setItemProperty(female.detailsText.id, 'itemPos', layered['femaleDetails'])
    layer.setItemProperty(marriage.detailsText.id, 'itemPos', layered['marriageDetails'])
    layer.setItemProperty(marriage.separationIndicator.id, 'itemPos', layered['marriageSep'])
    # unlayered
    male.setItemPos(unlayered['male'], undo=False)
    male.detailsText.setItemPos(unlayered['maleDetails'], undo=False)
    female.setItemPos(unlayered['female'], undo=False)
    female.detailsText.setItemPos(unlayered['femaleDetails'], undo=False)
    # marriage.setDivorced(True, undo=False)
    marriage.separationIndicator.setItemPos(unlayered['marriageSep'], undo=False)
    marriage.detailsText.setItemPos(unlayered['marriageDetails'], undo=False)
    assert len(scene.items()) == 22

    scene.selectAll()
    qtbot.clickYesAfter(lambda: scene.removeSelection())
    assert len(scene.items()) == 0

    commands.stack().undo()
    assert len(scene.items()) == 22

    commands.stack().redo()
    assert len(scene.items()) == 0


def test_read_write_layered_props():
    """ Item.write was not explicitly requesting non-layered prop values. """
    scene = Scene()
    person = Person()
    layer = Layer(name='View 1', active=True)
    scene.addItems(person, layer)
    person.setLayers([layer.id])
    person.setItemPos(QPointF(10, 10))
    person.setColor('#ff0000')
    #
    data = {}
    scene.write(data)
    scene = Scene()
    scene.read(data)
    assert scene.people()[0].pos() == QPointF(10, 10)
    assert scene.people()[0].color() == '#ff0000'
    assert scene.people()[0].pen().color().name() == '#ff0000'
    
    scene.layers()[0].setActive(False)
    assert scene.people()[0].color() == None
    assert scene.people()[0].pen().color().name() == util.PEN.color().name()
    
    scene.layers()[0].setActive(True)
    assert scene.people()[0].color() == '#ff0000'
    assert scene.people()[0].pen().color().name() == '#ff0000'



def test_reset_layered_props():
    """ Item.write was not explicitly requesting non-layered prop values. """
    scene = Scene()
    person = Person()
    layer = Layer(name='View 1', active=True, storeGeometry=True)
    scene.addItems(person, layer)
    person.setItemPos(QPointF(10, 10))
    assert layer.active() == True
    assert person.pos() == QPointF(10, 10)
    
    scene.resetAll() # was throwing exception in commands.py
    assert person.itemPos() == QPointF()
    assert person.pos() == QPointF()


def test_exclusiveLayerSelection():
    scene = Scene()
    layerModel = SceneLayerModel()
    layerModel.scene = scene
    layerModel.items = [scene]
    layer1 = Layer(name='View 1', active=True)
    layer2 = Layer(name='View 2')
    scene.addItems(layer1, layer2)
    assert layer1.active() == True

    layerModel.setActiveExclusively(1)
    assert layer1.active() == False
    assert layer2.active() == True


def test_setPathItemVisible():
    scene = Scene(exclusiveLayerSelection=True)
    layer1 = Layer(name='View 1')
    layer2 = Layer(name='View 2')
    layer3 = Layer(name='View 3')
    layer4 = Layer(name='View 4')
    personA = Person(name='A')
    personB = Person(name='B')
    marriage = Marriage(personA=personA, personB=personB)
    divorcedEvent = Event(parent=marriage, uniqueId='divorced', dateTime=util.Date(1900, 1, 1))
    scene.addItems(layer1, layer2, layer3, layer4, personA, personB, marriage)
    personA.setLayers([layer2.id, layer4.id])
    personB.setLayers([layer3.id])
    layerModel = SceneLayerModel()
    layerModel.scene = scene
    layerModel.items = [scene]
    OPACITY = 0.1
    personA.setItemOpacity(OPACITY, forLayers=[layer2, layer4])

    assert personA.opacity() == 1.0
    assert personB.opacity() == 1.0
    assert marriage.opacity() == 1.0
    assert personA.isVisible() == True
    assert personB.isVisible() == True
    assert marriage.isVisible() == True

    layerModel.setActiveExclusively(0)
    assert personA.opacity() == 0.0
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == False
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    # deemphasis and other marriage-person hidden should not show marriage
    layerModel.setActiveExclusively(1)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    layerModel.setActiveExclusively(2)
    assert personA.opacity() == 0.0
    assert personB.opacity() == 1.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == False
    assert personB.isVisible() == True
    assert marriage.isVisible() == False

    # deemphasis and other marriage-person hidden should not show marriage
    layerModel.setActiveExclusively(3)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    layerModel.setActiveExclusively(1)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False


def test_setPathItemVisible_2():
    scene = Scene(exclusiveLayerSelection=True)
    layer1 = Layer(name='View 1')
    layer2 = Layer(name='View 2')
    personA = Person(name='A')
    personB = Person(name='B')
    marriage = Marriage(personA=personA, personB=personB)
    divorcedEvent = Event(parent=marriage, uniqueId='divorced', dateTime=util.Date(1900, 1, 1))
    scene.addItems(layer1, layer2, personA, personB, marriage)
    personA.setLayers([layer1.id, layer2.id])
    layerModel = SceneLayerModel()
    layerModel.scene = scene
    layerModel.items = [scene]
    OPACITY = 0.1
    personA.setItemOpacity(OPACITY, forLayers=[layer2])

    # Only personA shown, and at full opacity
    layerModel.setActiveExclusively(0)
    assert personA.opacity() == 1.0
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    # Only personA shown, and at partial opacity
    layerModel.setActiveExclusively(1)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False


def test_save_load_delete_items(qtbot):
    """ ItemDetails and SeparationIndicator that were saved to disk were
    not retaining ids stored in the fd, causing addItem() to asign new ids.
    Then item properties in layers would be out of sync, etc.
    Fixed by not adding items until after read().
    """
    scene = Scene()
    person = Person()
    person.setDiagramNotes('here are some notes')
    scene.addItem(person)
    data = {}
    scene.write(data)
    bdata = pickle.dumps(data)
    #
    scene = Scene()
    scene.read(data)
    ## added to ensure that ItemDetails|SeparationIndicator id's match the id's in the file
    for id, item in scene.itemRegistry.items():
        assert id == item.id
    scene.selectAll()
    qtbot.clickYesAfter(lambda: scene.removeSelection()) # would throw exception


@pytest.mark.skip(reason="Import into non-free diagram relies on paste which is not supported yet.")
def test_import(simpleScene):
    scene = Scene()
    simpleScene.selectAll()
    commands.importItems(scene, simpleScene.selectedItems())
    assert len(scene.items()) == len(simpleScene.items())


def test_write_excel_no_exception(simpleScene, tmp_path):
    p1 = simpleScene.query1(name='p1')
    p2 = simpleScene.query1(name='p2')
    kinds = itertools.cycle([util.ITEM_CUTOFF,
                             util.ITEM_CONFLICT,
                             util.ITEM_PROJECTION,
                             util.ITEM_DISTANCE,
                             util.ITEM_TOWARD,
                             util.ITEM_AWAY,
                             util.ITEM_DEFINED_SELF,
                             util.ITEM_RECIPROCITY,
                             util.ITEM_INSIDE,
                             util.ITEM_OUTSIDE])
    iDay = 0
    stride = 2
    firstDate = QDateTime.currentDateTime().addDays(-365 * 5)
    for i in range(100):
        for parent in (p1, p2):
            iDay += stride
            dateTime = firstDate.addDays(iDay)
            Event(parent, description='Test event %i' % iDay, dateTime=dateTime)
        iDay += stride
        dateTime = firstDate.addDays(iDay)
        Emotion(personA=p1, personB=p2, kind=next(kinds), dateTime=dateTime)
    # util.printModel(simpleScene.timelineModel)
    filePath = os.path.join(tmp_path, 'test.xlsx')
    simpleScene.writeExcel(filePath)



# PRISCILLA_SCENE = {
#     'items': [{
#         'adopted': False,
#         'adoptedEvent': {
#             'dateTime': None,
#             'description': 'Adopted',
#             'dynamicProperties': {},
#             'id': 1526,
#             'includeOnDiagram': False,
#             'location': None,
#             'loggedDateTime': util.Date(2020, 12, 26),
#             'nodal': False,
#             'notes': None,
#             'parentName': None,
#             'tags': [],
#             'uniqueId': 'adopted',
#             'unsure': True
#         },
#         'alias': 'Annabel',
#         'bigFont': False,
#         'birthEvent': {
#             'dateTime': None,
#             'description': 'Birth',
#             'dynamicProperties': {},
#             'id': 1524,
#             'includeOnDiagram': False,
#             'location': None,
#             'loggedDateTime': util.Date(2020, 12, 26),
#             'nodal': False,
#             'notes': None,
#             'parentName': 'Elsie',
#             'tags': [],
#             'uniqueId': 'birth',
#             'unsure': False
#         },
#         'birthName': 'Harder',
#         'childOf': {},
#         'color': None,
#         'deathEvent': {
#             'dateTime': util.Date(2002, 11, 25),
#             'description': 'Death',
#             'dynamicProperties': {},
#             'id': 1525,
#             'location': None,
#             'loggedDateTime': util.Date(2020, 12, 26),
#             'nodal': False,
#             'notes': None,
#             'parentName': None,
#             'tags': [],
#             'uniqueId': 'death',
#             'unsure': False
#         },
#         'deceased': True,
#         'deceasedReason': None,
#         'detailsText': {
#             'id': 1523,
#             'itemPos': QPointF(70.0, -50.0),
#             'loggedDateTime': util.Date(2020, 12, 26),
#             'tags': []
#         },
#         'diagramNotes': None,
#         'events': []
#         'gender': 'female',
#         'hideDetails': True,
#         'id': 1527,
#         'itemOpacity': None,
#         'itemPos': QPointF(2782.64741504785, 7531.047913485266),
#         'kind': 'Person',
#         'lastName': 'Friesen',
#         'loggedDateTime': util.Date(2020, 12, 26),
#         'marriages': [],
#         'middleName': None,
#         'name': 'Elsie',
#         'nickName': None,
#         'notes': None,
#         'primary': False,
#         'showLastName': True,
#         'showMiddleName': True,
#         'showNickName': True,
#         'size': 4,
#         'tags': []
#     }
#     ],
#     'lastItemId': 8026,
# }


PRISCILLA_SCENE = {
    'lastItemId': 8026,
    'version': '1.3.0',
    'items': [
        {
            'id': 1527,
            'deathEvent': {
                'id': 1525,
                'dateTime': util.Date(2002, 11, 25),
                'parentName': None,
                'uniqueId': 'death',
            },
            'deceased': True,
            'kind': 'Person',
            'lastName': 'Friesen',
            'name': 'Elsie'
        }
    ]
}


def test_parentName_not_None():
    scene = Scene()
    scene.read(PRISCILLA_SCENE)
    model = scene.timelineModel
    index = scene.timelineModel.index(0, 5)
    person = scene.people()[0]
    assert index.data(model.ParentIdRole) == person.id

    # event = Event(person, description='Mine')

    # data2 = {}
    # scene.write(data2)
    # Debug(data2)

    display = index.data()
    assert display