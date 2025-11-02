from btcopilot.schema import EventKind
from pkdiagram.scene import Person, Event
from pkdiagram.models import EventVariablesModel


def test_init_deinit(scene):
    scene.addEventProperty("var1")
    scene.addEventProperty("var2")
    scene.addEventProperty("var3")
    person = scene.addItem(Person(name="p1"))
    event1 = scene.addItem(Event(EventKind.Shift, person))
    event2 = scene.addItem(Event(EventKind.Shift, person))
    event3 = scene.addItem(Event(EventKind.Shift, person))

    event1.dynamicProperty("var1").set("here")
    event2.dynamicProperty("var1").set("here")
    event3.dynamicProperty("var1").set("here")

    event1.dynamicProperty("var2").set("we")
    event2.dynamicProperty("var2").set("we")
    event3.dynamicProperty("var2").set("we")

    event1.dynamicProperty("var3").set("are")
    event2.dynamicProperty("var3").set("")
    event3.dynamicProperty("var3").set("")

    model = EventVariablesModel()
    model.scene = scene
    model.items = [event1, event2, event3]
    assert model.rowCount() == 3  # 3 variables
    assert model.data(model.index(0, 0)) == "var1"
    assert model.data(model.index(1, 0)) == "var2"
    assert model.data(model.index(2, 0)) == "var3"
    assert model.data(model.index(0, 1)) == "here"
    assert model.data(model.index(1, 2)) == None
    assert model.data(model.index(2, 3)) == None


def test_set_value(scene):
    parent = scene.addItem(Person())
    event1 = scene.addItem(Event(EventKind.Shift, parent))
    event2 = scene.addItem(Event(EventKind.Shift, parent))
    scene.addEventProperty("var1")
    model = EventVariablesModel()
    model.scene = scene
    model.items = [event1, event2]
    assert model.data(model.index(0, 1)) == None

    model.setData(model.index(0, 1), "here")
    assert model.data(model.index(0, 1)) == "here"
    assert event1.dynamicProperty("var1").get() == "here"
    assert event2.dynamicProperty("var1").get() == "here"

    model.setData(model.index(0, 1), "")
    assert model.data(model.index(0, 1)) == None
    assert event1.dynamicProperty("var1").get() == None
    assert event2.dynamicProperty("var1").get() == None
